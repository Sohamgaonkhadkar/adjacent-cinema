"""API routes for the Adjacent run pipeline.

Routes:
    POST /run              Start a new analysis run
    GET  /run/{run_id}     Get run status and results
    GET  /run/{run_id}/stream  SSE stream of run events
    GET  /run/{run_id}/trace   Get trace rows
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..public_demo import (
    acquire_public_demo_run,
    prune_public_run_cache,
    public_demo_enabled,
    public_failure_message,
    safe_error_diagnostic,
    safe_public_event,
    safe_public_trace,
    safe_run_error,
    sanitize_public_stop,
)
from .store import RunEvent, RunRecord, RunStatus, run_store

if TYPE_CHECKING:
    from ..agent.state import AdjacentState

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------


class ProgrammeItemInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    year: int | None = Field(default=None, ge=1888, le=2100)
    imdb_id: str | None = Field(default=None, max_length=32)


class RunRequest(BaseModel):
    city: str = Field(..., min_length=1, max_length=120)
    venue_name: str = Field(default="", max_length=120)
    programme: list[ProgrammeItemInput] = Field(..., min_length=1, max_length=12)


class RunResponse(BaseModel):
    run_id: str
    status: str
    created_at: float
    city: str
    venue_name: str
    programme: list[dict[str, Any]]
    current_phase: str
    stop_reason: str | None
    stop_message: str | None
    error: str | None
    result: dict[str, Any] | None
    trace: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# POST /run — start a new analysis
# ---------------------------------------------------------------------------


@router.post("/run", response_model=RunResponse)
async def create_run(request: RunRequest) -> RunResponse:
    """Start a new Adjacent analysis run."""
    programme = [item.model_dump() for item in request.programme]

    record = run_store.create(
        city=request.city,
        venue_name=request.venue_name,
        programme=programme,
    )

    # Start the run in the background — store task reference to prevent GC
    _background_tasks = set()
    task = asyncio.create_task(_execute_run(record))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return _record_to_response(record)


# ---------------------------------------------------------------------------
# POST /run/demo — explicitly labelled fixture run (no Qloo key required)
# ---------------------------------------------------------------------------

#: The fixture used by the demo route. It is the same verified demo programme the
#: frontend offers as a sample; every artefact it produces is marked "fixture".
DEMO_FIXTURE = "portland_strong"


@router.post("/run/demo", response_model=RunResponse)
async def create_demo_run(request: Request) -> RunResponse:
    """Start a fixture-backed demo run.

    This route exists so the whole product journey is explorable without a Qloo
    key — but it never pretends to be live: `data_status` is "fixture" in the
    result, in every sub-artefact and in the stop notice.
    """
    permit = acquire_public_demo_run(request, live=False)
    try:
        prune_public_run_cache(max_records=99)
        record = run_store.create(
            city="",  # filled from the fixture once the run starts
            venue_name="Fixture Demo Cinema (offline)",
            programme=[],
        )

        _demo_tasks: set[asyncio.Task[None]] = set()
        task = asyncio.create_task(_execute_demo_run(record))
        _demo_tasks.add(task)

        def finish_demo(completed: asyncio.Task[None]) -> None:
            _demo_tasks.discard(completed)
            if permit is not None:
                permit.release()

        task.add_done_callback(finish_demo)
        return _record_to_response(record)
    except Exception:
        if permit is not None:
            permit.release()
        raise


# ---------------------------------------------------------------------------
# GET /run/{run_id} — get run status
# ---------------------------------------------------------------------------


@router.get("/run/{run_id}", response_model=RunResponse)
async def get_run(run_id: str) -> RunResponse:
    """Get the current state of a run."""
    prune_public_run_cache()
    record = run_store.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return _record_to_response(record)


# ---------------------------------------------------------------------------
# GET /run/{run_id}/stream — SSE stream
# ---------------------------------------------------------------------------


@router.get("/run/{run_id}/stream")
async def stream_run(run_id: str) -> StreamingResponse:
    """Server-Sent Events stream for a run."""
    prune_public_run_cache()
    record = run_store.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    async def event_generator():
        queue = record.subscribe()
        try:
            while True:
                event = await queue.get()
                safe_event = safe_public_event(event)
                yield safe_event.sse_format()
                if event.event in ("done", "insufficiency", "error"):
                    break
        finally:
            record.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# GET /run/{run_id}/trace — trace rows
# ---------------------------------------------------------------------------


@router.get("/run/{run_id}/trace")
async def get_trace(run_id: str) -> dict[str, Any]:
    """Get the trace rows for a completed or in-progress run."""
    prune_public_run_cache()
    record = run_store.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return {"run_id": run_id, "trace": safe_public_trace(record.trace)}


# ---------------------------------------------------------------------------
# Run execution
# ---------------------------------------------------------------------------


def _safe_state_failure_message(state: Any) -> str:
    """Expose useful stop diagnostics without serializing raw exception details."""
    stop = getattr(state, "stop", None)
    if stop is None:
        return "The analysis could not complete. Review the sanitized trace and retry."

    reason = getattr(getattr(stop, "reason", None), "value", getattr(stop, "reason", None))
    if reason != "error":
        return str(getattr(stop, "message", "") or "The analysis stopped before completion.")

    stats = getattr(stop, "stats", {})
    error = stats.get("error") if isinstance(stats, dict) else None
    error = error if isinstance(error, dict) else {}
    return safe_error_diagnostic(
        error_type=error.get("error_type") or getattr(stop, "detail_code", None),
        kind=error.get("kind"),
        status=error.get("status"),
        call_id=error.get("call_id"),
    )


async def _execute_run(record: RunRecord) -> None:
    """Execute the Adjacent pipeline and update the run record."""
    from ..agent.budget import Budget
    from ..agent.orchestrator import AgentOrchestrator
    from ..agent.state import AdjacentState, ProgrammeItem
    from ..config import Settings
    from ..domain.ledger import ProvenanceLedger
    from ..live_runner import LivePipeline
    from ..resolution.resolver import EntityResolver

    record.status = RunStatus.RUNNING
    record.emit(RunEvent("trace", {
        "phase": "INIT",
        "message": f"Starting analysis for {len(record.programme)} film(s) in {record.city}",
    }))

    settings = Settings.from_env()

    if not settings.has_api_key:
        record.status = RunStatus.FAILED
        record.error = "QLOO_API_KEY not configured"
        record.stop_message = record.error
        record.result = None
        record.emit(RunEvent("error", {"message": record.error}))
        return

    client = None
    state = None
    try:
        from ..qloo.client import QlooClient
        client = QlooClient(settings)
        resolver = EntityResolver(client, delay_s=2.0)

        # Seed programme items
        programme_items = [
            ProgrammeItem(
                title=str(item.get("title", "(unnamed)")),
                year=item.get("year"),
                imdb_id=item.get("imdb_id"),
                declared_entity_id=item.get("entity_id"),
            )
            for item in record.programme
        ]

        state = AdjacentState(
            run_id=record.run_id,
            fixture_name=None,
            fixture_path=None,
            scenario="live",
            fixture_notice="LIVE QLOO DATA",
            data_status="measured",
            description=f"Live analysis for {record.venue_name or 'venue'} in {record.city}",
            programme=programme_items,
            budget=Budget(),
        )
        state.ledger = ProvenanceLedger(recorder=client.recorder, data_status="measured")

        pipeline = LivePipeline(client, resolver, record.programme)
        orchestrator = AgentOrchestrator(pipeline)

        # Run the core pipeline
        state = await orchestrator.run(state)
        sanitize_public_stop(state)

        # Preserve safe diagnostics even when a later pipeline stage fails.
        record.stop_reason = state.stop_reason
        record.stop_message = state.stop_message
        record.trace = state.trace_rows
        _emit_state_events(record, state)

        if state.stop_reason not in ("complete", "insufficiency"):
            message = _safe_state_failure_message(state)
            record.status = RunStatus.FAILED
            record.error = message
            record.stop_message = message
            record.result = None
            record.emit(RunEvent("error", {
                "stop_reason": state.stop_reason,
                "stop_message": message,
                "message": message,
                "resolved": len(state.resolved_items),
                "total": len(state.programme),
            }))
            await client.aclose()
            return

        record.state_json = state.to_json()

        # --- Post-pipeline: Geography, Programme Bet, Test Card ---
        geography_result, programme_bet, test_card = await _post_pipeline_artifacts(
            record, state, client
        )

        record.result = _build_result(
            state, record.city,
            geography=geography_result,
            programme_bet=programme_bet,
            test_card=test_card,
        )

        if state.stop_reason == "complete":
            record.status = RunStatus.COMPLETED
            record.emit(RunEvent("done", {
                "stop_reason": state.stop_reason,
                "stop_message": state.stop_message,
                "resolved": len(state.resolved_items),
                "total": len(state.programme),
                "cohorts_ranked": len(state.ranked),
                "cohorts_rejected": len(state.rejected),
            }))
        else:
            record.status = RunStatus.INSUFFICIENT
            record.emit(RunEvent("insufficiency", {
                "stop_reason": state.stop_reason,
                "stop_message": state.stop_message,
            }))

        await client.aclose()

    except Exception as exc:
        message = safe_run_error(exc)
        record.status = RunStatus.FAILED
        record.error = message
        record.stop_message = message
        record.result = None
        if client is not None:
            with suppress(Exception):
                await client.aclose()
        if state is not None:
            with suppress(Exception):
                record.stop_reason = state.stop_reason
                record.trace = state.trace_rows
        record.emit(RunEvent("error", {"message": message}))


async def _post_pipeline_artifacts(
    record: RunRecord,
    state: AdjacentState,
    client: Any,
) -> tuple[Any, Any, Any]:
    """Geography → Programme Bet → Test Card, with truthful data_status.

    Shared by the live `/run` path and the fixture `/run/demo` path so both
    journeys produce identical artefact shapes; the only difference is the
    client (QlooClient vs MockQlooClient) and `state.data_status`.
    """
    geography_result = None
    programme_bet = None
    test_card = None
    data_status = getattr(state, "data_status", "measured") or "measured"

    if state.stop_reason == "complete" and state.ranked:
        record.emit(RunEvent("trace", {
            "phase": "LOCATE",
            "message": f"Analysing geographic concentration in {record.city}",
        }))

        # Geography: call heatmap
        try:
            from ..domain.geography import build_geography_result
            heatmap_response = await client.insights(
                filter_type="urn:heatmap",
                signal_interests_entities=state.resolved_ids,
                filter_location_query=record.city,
                filter_location_radius=0,
                output_heatmap_boundary="urn:geohash",
                take=50,
                tool="geography_heatmap",
            )
            geography_result = build_geography_result(
                city=record.city,
                response=heatmap_response,
                call_id=heatmap_response.call_id,
            )
            record.emit(RunEvent("heatmap", geography_result.to_dict()))
        except Exception as exc:
            record.emit(RunEvent("trace", {
                "phase": "LOCATE",
                "message": f"Geography failed: {safe_run_error(exc)}",
            }))

        # Programme Bet (M11.2: Two-sided with real Qloo evidence)
        record.emit(RunEvent("trace", {
            "phase": "DECIDE",
            "message": "Building Programme Bet from ranked cohorts with two-sided evidence",
        }))
        try:
            from ..domain.programme_bet import build_programme_bet

            # Build two-sided evidence from ranked cohorts
            # M11.3: Renamed for scientific accuracy
            # A. Programme adjacency: mean_affinity (cultural proximity)
            # B. Cohort breadth: qualifying_members ratio (coverage)
            programme_adjacency_scores = {}
            cohort_breadth_scores = {}
            programme_adjacency_bands = {}
            cohort_breadth_bands = {}
            programme_adjacency_call_ids = {}
            cohort_breadth_call_ids = {}

            for cohort in state.ranked:
                cid = cohort.cohort_id
                score = cohort.score

                # A. Programme adjacency: mean_affinity from Qloo scoring
                if score and score.mean_affinity is not None:
                    programme_adjacency_scores[cid] = score.mean_affinity
                    programme_adjacency_bands[cid] = (
                        "High" if score.mean_affinity >= 0.6
                        else "Medium" if score.mean_affinity >= 0.5
                        else "Low"
                    )
                    programme_adjacency_call_ids[cid] = score.call_id or ""

                # B. Cohort breadth: qualifying members ratio
                total = len(cohort.members) if cohort.members else 0
                qualifying = len(cohort.qualifying_members) if cohort.members else 0
                if total > 0:
                    breadth_ratio = qualifying / total
                    cohort_breadth_scores[cid] = breadth_ratio
                    cohort_breadth_bands[cid] = (
                        "High" if breadth_ratio >= 0.5
                        else "Medium" if breadth_ratio >= 0.3
                        else "Low"
                    )
                    cohort_breadth_call_ids[cid] = score.call_id if score and score.call_id else ""

            programme_bet = build_programme_bet(
                ranked_cohorts=state.ranked,
                taste_tags=state.taste_tags,
                geography=geography_result,
                resolved_names=[p.resolved_name or p.title for p in state.resolved_items],
                programme_adjacency_scores=programme_adjacency_scores,
                cohort_breadth_scores=cohort_breadth_scores,
                programme_adjacency_bands=programme_adjacency_bands,
                cohort_breadth_bands=cohort_breadth_bands,
                programme_adjacency_call_ids=programme_adjacency_call_ids,
                cohort_breadth_call_ids=cohort_breadth_call_ids,
                rejected_cohorts=state.rejected,
                data_status=data_status,
            )
            if programme_bet:
                record.emit(RunEvent("bet", programme_bet.to_dict()))
        except Exception as exc:
            record.emit(RunEvent("trace", {
                "phase": "DECIDE",
                "message": f"Programme Bet failed: {safe_run_error(exc)}",
            }))

        # Test Card
        if programme_bet:
            try:
                from ..domain.test_card import build_test_card
                test_card = build_test_card(
                    bet=programme_bet,
                    resolved_names=[p.resolved_name or p.title for p in state.resolved_items],
                    city=record.city,
                )
                record.emit(RunEvent("test_card", test_card.to_dict()))
            except Exception as exc:
                record.emit(RunEvent("trace", {
                    "phase": "DECIDE",
                    "message": f"Test Card failed: {safe_run_error(exc)}",
                }))

    return geography_result, programme_bet, test_card


async def _execute_demo_run(record: RunRecord) -> None:
    """Execute the fixture-backed pipeline (Milestone-1 spine + artefacts).

    No API key, no network. Every emitted artefact carries data_status="fixture".
    """
    from ..agent.budget import Budget
    from ..agent.orchestrator import AgentOrchestrator
    from ..agent.state import AdjacentState
    from ..config import Settings
    from ..domain.ledger import ProvenanceLedger
    from ..qloo.mock import MockQlooClient
    from ..runner import FixturePipeline, programme_items, resolve_fixture_path

    record.status = RunStatus.RUNNING
    record.emit(RunEvent("trace", {
        "phase": "INIT",
        "message": f"Starting FIXTURE demo run ({DEMO_FIXTURE}) — offline, no Qloo calls",
    }))

    try:
        settings = Settings.from_env()
        fixture_path = resolve_fixture_path(DEMO_FIXTURE, settings=settings)
        name = fixture_path.stem
        client = MockQlooClient(settings, fixture=name, run_id=record.run_id)
        fx = client.fixture

        record.city = fx.city_query or ""
        record.programme = [
            {
                "title": str(p.get("title", "(unnamed)")),
                "year": p.get("year"),
                "imdb_id": p.get("imdb_id"),
            }
            for p in fx.programme
        ]

        state = AdjacentState(
            run_id=record.run_id,
            fixture_name=name,
            fixture_path=str(fixture_path),
            scenario=fx.scenario,
            fixture_notice=client.notice,
            data_status="fixture",
            description=fx.description,
            programme=programme_items(fx.programme),
            budget=Budget(),
        )
        state.ledger = ProvenanceLedger(recorder=client.recorder, data_status="fixture")

        orchestrator = AgentOrchestrator(FixturePipeline(client, fx))
        state = await orchestrator.run(state)
        sanitize_public_stop(state)

        record.stop_reason = state.stop_reason
        record.stop_message = state.stop_message
        record.trace = state.trace_rows
        _emit_state_events(record, state)

        if state.stop_reason not in ("complete", "insufficiency"):
            message = _safe_state_failure_message(state)
            record.status = RunStatus.FAILED
            record.error = message
            record.stop_message = message
            record.result = None
            record.emit(RunEvent("error", {
                "stop_reason": state.stop_reason,
                "stop_message": message,
                "message": message,
                "resolved": len(state.resolved_items),
                "total": len(state.programme),
            }))
            return

        record.state_json = state.to_json()
        geography_result, programme_bet, test_card = await _post_pipeline_artifacts(
            record, state, client
        )
        record.result = _build_result(
            state, record.city,
            geography=geography_result,
            programme_bet=programme_bet,
            test_card=test_card,
        )

        if state.stop_reason == "complete":
            record.status = RunStatus.COMPLETED
            record.emit(RunEvent("done", {
                "stop_reason": state.stop_reason,
                "stop_message": state.stop_message,
                "resolved": len(state.resolved_items),
                "total": len(state.programme),
                "cohorts_ranked": len(state.ranked),
                "cohorts_rejected": len(state.rejected),
            }))
        elif state.stop_reason == "insufficiency":
            record.status = RunStatus.INSUFFICIENT
            record.emit(RunEvent("insufficiency", {
                "stop_reason": state.stop_reason,
                "stop_message": state.stop_message,
            }))
        else:
            record.status = RunStatus.FAILED
            record.emit(RunEvent("error", {
                "stop_reason": state.stop_reason,
                "stop_message": state.stop_message,
            }))

    except Exception as exc:
        message = safe_run_error(exc)
        record.status = RunStatus.FAILED
        record.error = message
        record.stop_message = message
        record.result = None
        record.emit(RunEvent("error", {"message": message}))


def _emit_state_events(record: RunRecord, state: AdjacentState) -> None:
    """Emit SSE events based on the final state."""
    # Resolution event
    record.emit(RunEvent("resolution", {
        "resolved": len(state.resolved_items),
        "total": len(state.programme),
        "items": [
            {
                "title": item.title,
                "year": item.year,
                "imdb_id": item.imdb_id,
                "resolved": item.resolved,
                "qloo_entity_id": item.resolved_entity_id,
                "qloo_name": item.resolved_name,
                "resolution_evidence": item.resolution_evidence,
            }
            for item in state.programme
        ],
    }))

    # Taste DNA event
    if state.taste_tags:
        record.emit(RunEvent("taste_dna", {
            "tag_count": len(state.taste_tags),
            "tags": [
                {
                    "tag_id": t.tag_id,
                    "name": t.name,
                    "affinity": t.affinity,
                    "band": t.band.value,
                    "popularity": t.popularity,
                }
                for t in state.taste_tags[:20]
            ],
        }))

    # Cohort events
    for cohort in state.ranked:
        record.emit(RunEvent("cohort", {
            "cohort_id": cohort.cohort_id,
            "domain": cohort.domain,
            "rank": cohort.rank,
            "member_count": cohort.member_count,
            "score": {
                "mean_affinity": cohort.score.mean_affinity if cohort.score else None,
                "novelty_proxy": cohort.score.novelty_proxy if cohort.score else None,
            } if cohort.score else None,
            "members": [
                {
                    "entity_id": m.entity_id,
                    "name": m.name,
                    "affinity": m.affinity,
                    "band": m.band.value if hasattr(m.band, 'value') else str(m.band),
                }
                for m in cohort.members[:10]
            ],
        }))


def _build_result(
    state: AdjacentState,
    city: str,
    geography: Any = None,
    programme_bet: Any = None,
    test_card: Any = None,
) -> dict[str, Any]:
    """Build the final result payload."""
    result: dict[str, Any] = {
        "data_status": getattr(state, "data_status", "unknown"),
        "programme": {
            "items": [
                {
                    "title": item.title,
                    "year": item.year,
                    "imdb_id": item.imdb_id,
                    "resolved": item.resolved,
                    "qloo_entity_id": item.resolved_entity_id,
                    "qloo_name": item.resolved_name,
                    "resolution_evidence": item.resolution_evidence,
                }
                for item in state.programme
            ],
            "resolved_count": len(state.resolved_items),
            "total_count": len(state.programme),
        },
        "taste_dna": {
            "tags": [
                {
                    "tag_id": t.tag_id,
                    "name": t.name,
                    "affinity": t.affinity,
                    "band": t.band.value,
                    "popularity": t.popularity,
                }
                for t in state.taste_tags
            ],
            "tag_count": len(state.taste_tags),
        },
        "cohorts": {
            "ranked": [
                {
                    "cohort_id": c.cohort_id,
                    "domain": c.domain,
                    "kind": c.kind,
                    "construction_reason": c.construction_reason,
                    "construction_evidence": c.construction_evidence,
                    "rank": c.rank,
                    "member_count": c.member_count,
                    "verdict": c.verdict.reason_code if c.verdict else None,
                    "score": {
                        "mean_affinity": c.score.mean_affinity if c.score else None,
                        "max_affinity": c.score.max_affinity if c.score else None,
                        "novelty_proxy": c.score.novelty_proxy if c.score else None,
                    } if c.score else None,
                    "members": [
                        {
                            "entity_id": m.entity_id,
                            "name": m.name,
                            "affinity": m.affinity,
                            "band": m.band.value if hasattr(m.band, 'value') else str(m.band),
                            "popularity": m.popularity,
                        }
                        for m in c.members
                    ],
                    # Exclusions are annotations, never deletions (reasons.py):
                    # surfaced with codes so the reader can disagree with them.
                    "qualifying_count": len(c.qualifying_members),
                    "excluded_members": [
                        {
                            "entity_id": e.entity_id,
                            "name": e.name,
                            "reason_code": e.code.value,
                            "affinity": e.affinity,
                        }
                        for e in c.excluded_members
                    ],
                }
                for c in state.ranked
            ],
            "rejected": [
                {
                    "cohort_id": c.cohort_id,
                    "domain": c.domain,
                    "rejection_reason": c.rejection.code.value if c.rejection else None,
                    "rejection_detail": c.rejection.detail if c.rejection else None,
                }
                for c in state.rejected
            ],
        },
        "evidence": {
            "qloo_calls": state.calls_made,
            "trace_rows": len(state.trace_rows),
            "stop_reason": state.stop_reason,
            "stop_message": state.stop_message,
        },
        "city": city,
    }

    # M7: Geography
    if geography is not None:
        result["geography"] = geography.to_dict()

    # M7: Programme Bet
    if programme_bet is not None:
        result["programme_bet"] = programme_bet.to_dict()

    # M7: Test Card
    if test_card is not None:
        result["test_card"] = test_card.to_dict()

    return result


def _record_to_response(record: RunRecord) -> RunResponse:
    stop_message = record.stop_message
    error = record.error
    # A failed terminal run must never serialize partial measured/fixture output,
    # even if an older execution path populated RunRecord.result before failing.
    result = None if record.status == RunStatus.FAILED else record.result
    if public_demo_enabled():
        if record.stop_reason == "error":
            stop_message = public_failure_message()
        if error:
            error = public_failure_message()
        if result is not None:
            result = dict(result)
            evidence = result.get("evidence")
            if isinstance(evidence, dict) and evidence.get("stop_reason") == "error":
                result["evidence"] = {
                    **evidence,
                    "stop_message": public_failure_message(),
                }
    return RunResponse(
        run_id=record.run_id,
        status=record.status.value,
        created_at=record.created_at,
        city=record.city,
        venue_name=record.venue_name,
        programme=record.programme,
        current_phase=record.current_phase,
        stop_reason=record.stop_reason,
        stop_message=stop_message,
        error=error,
        result=result,
        trace=safe_public_trace(record.trace),
    )
