"""Creator Mode + experiment lifecycle routes (M13.9).

Reuses the cinema pipeline (RunRecord store, orchestrator, LivePipeline,
fixture demo, SSE, traces) with creator-specific seeds and decision
artefacts. Live runs fail honestly without a key; the demo path is fixture
and labelled; nothing here ever substitutes fixtures for failed live work.

Authorisation note: like the existing /run surface, this API is a local,
single-user tool with no auth model in the application today. These write
endpoints follow the same posture deliberately and are documented as such;
adding auth is a separate, explicit decision (see M13.9 verification report).
"""

from __future__ import annotations

import asyncio
import logging
import os
import traceback
from contextlib import suppress
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..domain.creator_analysis import (
    build_creator_test_card,
    build_positioning_bet,
    two_sided_signal_maps,
)
from ..domain.cultural_investigation import build_investigation, verify_evidence_refs
from ..domain.experiment_repository import (
    DuplicateRequest,
    ExperimentRepository,
)
from ..domain.llm_provider import (
    LLMProviderConfig,
    LLMUnavailableError,
    OpenAICompatibleProvider,
)
from ..domain.synthesis import synthesize_investigation
from ..public_demo import (
    acquire_public_demo_run,
    prune_public_run_cache,
    public_demo_enabled,
    safe_public_trace,
    safe_run_error,
    sanitize_public_stop,
)
from .routes import (
    DEMO_FIXTURE,
    RunEvent,
    RunResponse,
    RunStatus,
    _build_result,
    _emit_state_events,
    _record_to_response,
    run_store,
)

router = APIRouter()
logger = logging.getLogger(__name__)

#: Runtime experiment data — NOT committed (see .gitignore). Tests override
#: via ADJACENT_EXPERIMENTS_DB.
_DEFAULT_DB = Path(__file__).resolve().parents[3] / "data" / "processed" / "experiments.db"
EXPERIMENTS_DB_PATH = Path(os.environ.get("ADJACENT_EXPERIMENTS_DB", str(_DEFAULT_DB)))

_repo: ExperimentRepository | None = None


def get_repo() -> ExperimentRepository:
    global _repo
    if _repo is None:
        _repo = ExperimentRepository(EXPERIMENTS_DB_PATH)
    return _repo


def reset_repo_for_tests(db_path: str | Path | None = None) -> None:
    """Test hook: point the repository at a temporary database."""
    global _repo
    if _repo is not None:
        _repo.close()
    _repo = ExperimentRepository(db_path) if db_path else None


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ReferenceInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    year: int | None = Field(default=None, ge=1888, le=2100)


class CreatorRunRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    logline: str = Field(default="", max_length=2000)
    genre: str = Field(default="", max_length=120)
    language: str = Field(default="", max_length=80)
    themes: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(
        default_factory=list, max_length=5
    )
    references: list[ReferenceInput] = Field(default_factory=list, max_length=5)
    release_goal: str = Field(default="", max_length=300)
    #: Optional release-location context; geography is only analysed when set.
    city: str = Field(default="", max_length=120)
    demo: str | bool | None = Field(default=None)

    def seeds(self) -> list[dict[str, Any]]:
        """Return comparable film references only; theme text is resolved as Qloo tags."""
        return [
            {"title": r.title.strip(), "year": r.year, "imdb_id": None}
            for r in self.references
            if r.title.strip()
        ]


class SaveExperimentRequest(BaseModel):
    request_id: str = Field(..., min_length=8, max_length=120)
    film_title: str = Field(..., min_length=1, max_length=200)
    hypothesis: str = Field(..., min_length=1, max_length=3000)
    film_context: dict[str, Any] = Field(default_factory=dict, max_length=64)
    success_criteria: str = Field(default="", max_length=2000)
    observation_window: str = Field(default="", max_length=300)
    action_plan: str = Field(default="", max_length=3000)
    data_status: str = Field(default="unknown", max_length=32)
    source_run_id: str | None = Field(default=None, max_length=64)
    source_bet: dict[str, Any] = Field(default_factory=dict, max_length=64)
    provenance: dict[str, Any] = Field(default_factory=dict, max_length=64)
    # M13.12 (additive): carry the investigation's own record into provenance
    # so a saved experiment can be traced back to what justified it.
    investigation_summary: dict[str, Any] | None = Field(default=None, max_length=32)
    evidence_refs: list[str] = Field(default_factory=list, max_length=64)
    # M13.14 (additive): when the creator explicitly adopts a Decision Brief
    # proposal, an immutable sanitised snapshot of the synthesis and the
    # ORIGINAL proposal are stored in provenance — so a reviewer can always
    # tell what the model proposed from what the creator actually saved.
    synthesis_snapshot: dict[str, Any] | None = Field(default=None, max_length=64)
    adopted_proposal: dict[str, Any] | None = Field(default=None, max_length=32)


class ObservationRequest(BaseModel):
    request_id: str = Field(..., min_length=8, max_length=120)
    kind: str = Field(default="ANALYTICS", max_length=32)
    measurement_status: str = Field(
        ..., max_length=16, description="OBSERVED|PARTIAL|MISSING|UNAVAILABLE|FAILED"
    )
    observed_on: str | None = Field(default=None, max_length=32)
    metrics: dict[str, Any] = Field(default_factory=dict, max_length=64)
    interpretation: str | None = Field(default=None, max_length=2000)
    source: str | None = Field(default=None, max_length=120)
    evidence_ref: str | None = Field(default=None, max_length=4096)
    limitations: str | None = Field(default=None, max_length=2000)
    supersedes_id: str | None = Field(default=None, max_length=64)


class EvaluationRequest(BaseModel):
    request_id: str = Field(..., min_length=8, max_length=120)
    outcome: str = Field(..., max_length=32, description="SUPPORTED|CONTRADICTED|INCONCLUSIVE")
    rationale: str = Field(..., min_length=1, max_length=3000)
    observation_ids: list[str] = Field(default_factory=list, max_length=64)
    unknowns: str | None = Field(default=None, max_length=2000)
    supersedes_id: str | None = Field(default=None, max_length=64)


class CreatorDemoRunRequest(BaseModel):
    title: str | None = Field(default=None, max_length=160)
    logline: str = Field(default="", max_length=2000)
    genre: str = Field(default="", max_length=120)
    language: str = Field(default="", max_length=80)
    themes: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(
        default_factory=list, max_length=5
    )
    references: list[ReferenceInput] = Field(default_factory=list, max_length=5)
    release_goal: str = Field(default="", max_length=300)
    city: str = Field(default="", max_length=120)
    demo: str | bool | None = Field(default=None)


# ---------------------------------------------------------------------------
# POST /creator/run — live creator analysis (fails honestly without a key)
# ---------------------------------------------------------------------------


@router.post("/creator/run", response_model=RunResponse)
async def create_creator_run(
    request: CreatorRunRequest,
    http_request: Request,
    demo: str | None = None,
) -> RunResponse:
    is_fixture = (
        demo == "fixture"
        or getattr(request, "demo", None) == "fixture"
        or getattr(request, "demo", None) is True
    )
    if is_fixture:
        permit = acquire_public_demo_run(http_request, live=False)
        try:
            prune_public_run_cache(max_records=99)
            record = run_store.create(
                city=request.city.strip(),
                venue_name=f"Creator Fixture Demo: {request.title}",
                programme=[],
            )
            record.creator_context = request.model_dump()
            _tasks: set[asyncio.Task[None]] = set()
            task = asyncio.create_task(_execute_creator_demo_run(record, request=request))
            _tasks.add(task)

            def finish_fixture(completed: asyncio.Task[None]) -> None:
                _tasks.discard(completed)
                if permit is not None:
                    permit.release()

            task.add_done_callback(finish_fixture)
            return _record_to_response(record)
        except Exception:
            if permit is not None:
                permit.release()
            raise

    seeds = request.seeds()
    themes = [theme.strip() for theme in request.themes if theme.strip()]
    if not seeds and not themes:
        raise HTTPException(
            status_code=422,
            detail="Add at least one reference work or theme to analyse.",
        )

    permit = acquire_public_demo_run(http_request, live=True)
    try:
        prune_public_run_cache(max_records=99)
        record = run_store.create(
            city=request.city.strip(),
            venue_name=f"Creator: {request.title}",
            programme=seeds,
        )
        record.creator_context = request.model_dump()  # type: ignore[attr-defined]

        _tasks: set[asyncio.Task[None]] = set()
        task = asyncio.create_task(_execute_creator_run(record, request))
        _tasks.add(task)

        def finish_live(completed: asyncio.Task[None]) -> None:
            _tasks.discard(completed)
            if permit is not None:
                permit.release()

        task.add_done_callback(finish_live)
        return _record_to_response(record)
    except Exception:
        if permit is not None:
            permit.release()
        raise


@router.post("/creator/run/demo", response_model=RunResponse)
async def create_creator_demo_run(
    http_request: Request,
    request: CreatorDemoRunRequest | None = None,
) -> RunResponse:
    """Fixture-backed creator demo — labelled `fixture` in every artefact."""
    permit = acquire_public_demo_run(http_request, live=False)
    try:
        prune_public_run_cache(max_records=99)
        run_req: CreatorRunRequest | None = None
        if request is not None and request.title:
            run_req = CreatorRunRequest(
                title=request.title,
                logline=request.logline,
                genre=request.genre,
                language=request.language,
                themes=request.themes,
                references=request.references,
                release_goal=request.release_goal,
                city=request.city,
                demo="fixture",
            )
        venue = (
            f"Creator Fixture Demo: {run_req.title}"
            if run_req and run_req.title
            else "Creator Fixture Demo (offline)"
        )
        city = run_req.city.strip() if run_req else ""
        record = run_store.create(
            city=city,
            venue_name=venue,
            programme=[],
        )
        if run_req is not None:
            record.creator_context = run_req.model_dump()
        _tasks: set[asyncio.Task[None]] = set()
        task = asyncio.create_task(_execute_creator_demo_run(record, request=run_req))
        _tasks.add(task)

        def finish_fixture(completed: asyncio.Task[None]) -> None:
            _tasks.discard(completed)
            if permit is not None:
                permit.release()

        task.add_done_callback(finish_fixture)
        return _record_to_response(record)
    except Exception:
        if permit is not None:
            permit.release()
        raise


# ---------------------------------------------------------------------------
# Execution — mirrors routes._execute_run with creator seeds + artefacts
# ---------------------------------------------------------------------------


def _log_creator_stop_diagnostic(record: Any, state: Any) -> None:
    """Log only exception class, call ID and source-frame labels from a stop."""
    stop = getattr(state, "stop", None)
    if stop is None:
        return
    reason = getattr(getattr(stop, "reason", None), "value", getattr(stop, "reason", None))
    stats = getattr(stop, "stats", None)
    error = stats.get("error") if isinstance(stats, dict) else None
    if reason != "error" or not isinstance(error, dict):
        return
    frames = error.get("frames")
    safe_frames = [frame for frame in frames if isinstance(frame, str)] if isinstance(frames, list) else []
    logger.error(
        "Creator orchestrator failure: run_id=%s error_type=%s call_id=%s frames=%s",
        record.run_id,
        error.get("error_type") or "unknown",
        error.get("call_id") or "none",
        " > ".join(safe_frames) or "<traceback unavailable>",
    )


def _record_creator_stopped(record: Any, state: Any) -> None:
    """Record a non-exception terminal failure without exposing partial artefacts."""
    from .routes import RunEvent, RunStatus, _safe_state_failure_message

    message = _safe_state_failure_message(state)
    phase = getattr(getattr(state, "phase", None), "value", "")
    record.status = RunStatus.FAILED
    record.stop_reason = getattr(state, "stop_reason", "error")
    record.stop_message = message
    record.error = message
    record.result = None
    record.state_json = None
    record.current_phase = phase
    trace_rows = getattr(state, "trace_rows", None)
    record.trace = safe_public_trace(trace_rows) if isinstance(trace_rows, list) else []
    record.emit(RunEvent("error", {
        "message": message,
        "stop_reason": record.stop_reason,
    }))


def _record_creator_failure(record: Any, state: Any, exc: Exception) -> None:
    """Fail a Creator run without discarding the trace needed to diagnose it.

    Traceback logging deliberately records only file/function/line frames and
    the exception class. Exception messages can contain upstream response data,
    request values, or credentials and must not be copied into application logs.
    """
    from .routes import RunEvent, RunStatus

    message = safe_run_error(exc)
    frames = [
        f"{Path(frame.filename).name}:{frame.name}:{frame.lineno}"
        for frame in traceback.extract_tb(exc.__traceback__)[-16:]
    ]
    logger.error(
        "Creator run failed: run_id=%s error_type=%s frames=%s",
        record.run_id,
        type(exc).__name__,
        " > ".join(frames) or "<traceback unavailable>",
    )

    record.status = RunStatus.FAILED
    record.stop_reason = "error"
    record.stop_message = message
    record.error = message
    record.result = None
    record.state_json = None
    if state is not None:
        phase = getattr(state, "phase", None)
        record.current_phase = getattr(phase, "value", str(phase or ""))
        trace_rows = getattr(state, "trace_rows", None)
        if isinstance(trace_rows, list):
            # Store only the same sanitised trace exposed by the run API.
            record.trace = safe_public_trace(trace_rows)
    record.emit(RunEvent("error", {"message": message, "stop_reason": "error"}))


async def _execute_creator_run(record: Any, request: CreatorRunRequest) -> None:
    client = None
    state = None
    record.status = RunStatus.RUNNING
    record.current_phase = "INIT"
    record.emit(RunEvent("trace", {
        "phase": "INIT",
        "message": f"Creator analysis for '{request.title}' — {len(record.programme)} reference film(s), {len(request.themes)} theme input(s)",
    }))

    try:
        from ..agent.budget import Budget
        from ..agent.orchestrator import AgentOrchestrator
        from ..agent.state import AdjacentState, ProgrammeItem
        from ..config import Settings
        from ..domain.ledger import ProvenanceLedger
        from ..live_runner import LivePipeline
        from ..resolution.resolver import EntityResolver

        settings = Settings.from_env()
        if not settings.has_api_key:
            message = (
                "Live Qloo is not configured for this public demo. Try the labelled fixture."
                if public_demo_enabled()
                else "QLOO_API_KEY not configured"
            )
            record.status = RunStatus.FAILED
            record.stop_reason = "configuration"
            record.stop_message = message
            record.error = message
            record.result = None
            record.state_json = None
            record.current_phase = "INIT"
            record.emit(RunEvent("error", {"message": message, "stop_reason": "configuration"}))
            return

        from ..qloo.client import QlooClient
        client = QlooClient(settings)
        resolver = EntityResolver(client, delay_s=2.0)

        state = AdjacentState(
            run_id=record.run_id,
            fixture_name=None,
            fixture_path=None,
            scenario="live",
            fixture_notice="LIVE QLOO DATA",
            data_status="measured",
            description=f"Creator analysis for '{request.title}'",
            programme=[
                ProgrammeItem(
                    title=str(item.get("title", "(unnamed)")),
                    year=item.get("year"),
                    imdb_id=item.get("imdb_id"),
                    declared_entity_id=item.get("entity_id"),
                )
                for item in record.programme
            ],
            theme_queries=[theme.strip() for theme in request.themes if theme.strip()],
            budget=Budget(),
        )
        state.ledger = ProvenanceLedger(recorder=client.recorder, data_status="measured")

        pipeline = LivePipeline(client, resolver, record.programme)
        state = await AgentOrchestrator(pipeline, allow_title_search=True).run(state)
        _log_creator_stop_diagnostic(record, state)
        sanitize_public_stop(state)
        if state.stop_reason not in ("complete", "insufficiency"):
            _record_creator_stopped(record, state)
            return

        geography_result, bet, test_card, investigation = await _post_pipeline_creator(
            record, state, client, request
        )
        _emit_state_events(record, state)
        _finalize_creator(
            record, state, request, geography_result, bet, test_card, investigation
        )
    except Exception as exc:
        _record_creator_failure(record, state, exc)
    finally:
        if client is not None:
            with suppress(Exception):
                await client.aclose()


async def _execute_creator_demo_run(
    record: Any, request: CreatorRunRequest | None = None
) -> None:
    from ..agent.budget import Budget
    from ..agent.orchestrator import AgentOrchestrator
    from ..agent.state import AdjacentState
    from ..config import Settings
    from ..domain.ledger import ProvenanceLedger
    from ..qloo.mock import MockQlooClient
    from ..runner import FixturePipeline, programme_items, resolve_fixture_path
    from .routes import RunEvent, RunStatus

    record.status = RunStatus.RUNNING
    record.current_phase = "INIT"
    record.result = None
    record.state_json = None
    record.emit(RunEvent("trace", {
        "phase": "INIT",
        "message": f"Creator FIXTURE demo ({DEMO_FIXTURE}) — offline, no Qloo calls",
    }))

    client = None
    state = None
    try:
        settings = Settings.from_env()
        fixture_path = resolve_fixture_path(DEMO_FIXTURE, settings=settings)
        name = fixture_path.stem
        client = MockQlooClient(settings, fixture=name, run_id=record.run_id)
        fx = client.fixture

        record.programme = [
            {"title": str(p.get("title", "(unnamed)")), "year": p.get("year"), "imdb_id": p.get("imdb_id")}
            for p in fx.programme
        ]
        demo_request = request or CreatorRunRequest(
            title="Sample Short — 'Neon Harbour'",
            logline="A dockside night-shift romance told in three silent vignettes.",
            genre="drama",
            language="English",
            themes=[],  # Fixture demo does not claim to resolve creator-entered themes.
            release_goal="YouTube premiere after festival window",
        )
        if request is not None:
            record.creator_context = request.model_dump()
            if request.city.strip():
                record.city = request.city.strip()

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
        record.current_phase = getattr(getattr(state, "phase", None), "value", "INIT")

        state = await AgentOrchestrator(
            FixturePipeline(client, fx), allow_title_search=True
        ).run(state)
        record.current_phase = getattr(getattr(state, "phase", None), "value", record.current_phase)
        _log_creator_stop_diagnostic(record, state)
        sanitize_public_stop(state)
        if state.stop_reason not in ("complete", "insufficiency"):
            _record_creator_stopped(record, state)
            return

        geography_result, bet, test_card, investigation = await _post_pipeline_creator(
            record, state, client, demo_request
        )
        _emit_state_events(record, state)
        _finalize_creator(
            record, state, demo_request, geography_result, bet, test_card, investigation
        )
    except Exception as exc:
        _record_creator_failure(record, state, exc)
    finally:
        if client is not None:
            with suppress(Exception):
                await client.aclose()


async def _post_pipeline_creator(
    record: Any, state: Any, client: Any, request: CreatorRunRequest
) -> tuple[Any, Any, Any, Any]:
    """Geography (only with a city) → Bet → Test Card → structured Investigation."""
    from .routes import RunEvent

    geography_result = None
    data_status = getattr(state, "data_status", "measured") or "measured"

    if state.stop_reason == "complete" and state.ranked and record.city:
        try:
            from ..domain.geography import build_geography_result
            heatmap = await client.insights(
                filter_type="urn:heatmap",
                signal_interests_entities=state.resolved_ids or None,
                signal_interests_tags=state.theme_tag_ids or None,
                filter_location_query=record.city,
                filter_location_radius=0,
                output_heatmap_boundary="urn:geohash",
                take=50,
                tool="geography_heatmap",
            )
            geography_result = build_geography_result(
                city=record.city, response=heatmap, call_id=heatmap.call_id
            )
            record.emit(RunEvent("heatmap", geography_result.to_dict()))
        except Exception as exc:
            record.emit(RunEvent("trace", {
                "phase": "LOCATE",
                "message": f"Geography failed: {safe_run_error(exc)}",
            }))

    bet = None
    test_card = None
    if state.stop_reason == "complete" and state.ranked:
        record.emit(RunEvent("trace", {
            "phase": "DECIDE",
            "message": "Building Positioning Bet from ranked cultural worlds",
        }))
        try:
            seeds = [str(p.get("title")) for p in record.programme if p.get("title")]
            bet = build_positioning_bet(
                ranked_cohorts=state.ranked,
                taste_tags=state.taste_tags,
                film_title=request.title,
                seeds=seeds,
                signals=two_sided_signal_maps(state),
                geography=geography_result,
                rejected_cohorts=state.rejected,
                data_status=data_status,
            )
            if bet:
                record.emit(RunEvent("bet", bet.to_dict()))
                test_card = build_creator_test_card(
                    bet=bet,
                    film_title=request.title,
                    seeds=seeds,
                    release_goal=request.release_goal,
                )
                record.emit(RunEvent("test_card", test_card.to_dict()))
        except Exception as exc:
            record.emit(RunEvent("trace", {
                "phase": "DECIDE",
                "message": f"Positioning Bet failed: {safe_run_error(exc)}",
            }))

    # M13.11: the structured investigation account — built from the SAME state
    # the orchestrator filled, citing the call_ids that actually ran.
    investigation = build_investigation(
        state,
        film={
            "title": request.title,
            "logline": request.logline,
            "genre": request.genre,
            "language": request.language,
            "release_goal": request.release_goal,
            "themes": list(request.themes),
        },
        seeds=seeds if (seeds := [str(p.get("title")) for p in record.programme if p.get("title")]) else [],
        bet=bet,
        test_card=test_card,
        geography=geography_result,
        city=record.city or None,
        data_status=data_status,
    )
    # M13.12: dangling-reference defence — every evidence ref must resolve to a
    # call recorded in THIS run's trace, or it is removed (and the removal is
    # recorded as a limitation rather than silently ignored).
    known_call_ids = {
        row.get("call_id") for row in (state.trace_rows or []) if row.get("call_id")
    }
    investigation, _dropped_refs = verify_evidence_refs(investigation, known_call_ids)
    record.emit(RunEvent("investigation", investigation))

    # Comparables audit: one bounded compare call per reference pair, at most
    # three. It runs after the analysis so it can never affect the result, its
    # failures are values, and an unusable provider leaves the run intact.
    try:
        from ..domain.comparables import MAX_PAIRS, build_comparables_audit

        remaining = max(0, getattr(getattr(state, "budget", None), "remaining_calls", 0))
        state.comparables = await build_comparables_audit(
            client,
            state,
            budget_remaining=min(MAX_PAIRS, remaining),
        )
        record.emit(RunEvent("trace", {
            "phase": "COMPARE",
            "message": (
                "Comparables audit: "
                f"{state.comparables.get('summary', {}).get('pairs_attempted', 0)} pair(s) "
                f"attempted, {state.comparables.get('summary', {}).get('pairs_measured', 0)} measured"
            ),
        }))
    except Exception as exc:
        # The audit is optional evidence; the Creator result must not depend on it.
        state.comparables = None
        record.emit(RunEvent("trace", {
            "phase": "COMPARE",
            "message": f"Comparables audit unavailable: {safe_run_error(exc)}",
        }))

    return geography_result, bet, test_card, investigation


def _finalize_creator(
    record: Any,
    state: Any,
    request: CreatorRunRequest,
    geography_result: Any,
    bet: Any,
    test_card: Any,
    investigation: Any = None,
) -> None:
    from .routes import RunEvent, RunStatus

    sanitize_public_stop(state)
    record.state_json = state.to_json()
    record.stop_reason = state.stop_reason
    record.stop_message = state.stop_message

    result = _build_result(
        state, record.city,
        geography=geography_result,
        programme_bet=bet,
        test_card=test_card,
    )
    result["mode"] = "creator"
    result["film"] = {
        "title": request.title,
        "logline": request.logline,
        "genre": request.genre,
        "language": request.language,
        "release_goal": request.release_goal,
        "themes": list(request.themes),
    }
    result["theme_inputs"] = list(state.theme_resolution)
    result["investigation"] = investigation
    record.result = result
    record.trace = state.trace_rows

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


# ---------------------------------------------------------------------------
# Experiment lifecycle
# ---------------------------------------------------------------------------

#: M13.14: allowlists — a snapshot stores the decision context, never an
#: arbitrary object dump, and by construction can never carry credentials
#: (keys outside the allowlist are dropped, not forwarded).
_SNAPSHOT_KEYS = frozenset({
    "investigation_id", "source_run_id", "schema_version", "method",
    "provider_kind", "model", "validation", "summary", "hypothesis_restated",
    "claims", "caveats", "limitations", "evidence_refs", "data_status",
    "experiment_proposal",
})
_SNAPSHOT_CLAIM_KEYS = frozenset({
    "statement", "claim_type", "evidence_refs", "rationale", "limitations",
})
_PROPOSAL_KEYS = frozenset({
    "kind", "hypothesis", "action_plan", "success_criteria",
    "observation_window", "falsification", "relevant_metrics", "assumptions",
    "limitations",
})


def _sanitize_snapshot(
    snapshot: dict[str, Any], known_call_ids: set[str] | None
) -> dict[str, Any]:
    """Trim to the allowlist and verify every evidence ref against the source
    run's recorded trace. Unresolvable refs are never stored as proof: they
    are moved to `unresolved_evidence_refs` with an explicit status."""
    trimmed: dict[str, Any] = {
        k: v for k, v in snapshot.items() if k in _SNAPSHOT_KEYS
    }
    claims = trimmed.get("claims")
    if isinstance(claims, list):
        trimmed["claims"] = [
            {k: v for k, v in c.items() if k in _SNAPSHOT_CLAIM_KEYS}
            for c in claims[:12]
            if isinstance(c, dict)
        ]
    proposal = trimmed.get("experiment_proposal")
    if isinstance(proposal, dict):
        trimmed["experiment_proposal"] = {
            k: v for k, v in proposal.items() if k in _PROPOSAL_KEYS
        }

    unresolved: list[str] = []

    def _verify(refs: Any) -> list[str]:
        if not isinstance(refs, list):
            return []
        kept = []
        for r in refs:
            if not (isinstance(r, str) and r):
                continue
            if known_call_ids is None or r in known_call_ids:
                kept.append(r)
            else:
                unresolved.append(r)
        return kept

    trimmed["evidence_refs"] = _verify(trimmed.get("evidence_refs"))
    for claim in trimmed.get("claims") or []:
        claim["evidence_refs"] = _verify(claim.get("evidence_refs"))
    if known_call_ids is not None:
        trimmed["evidence_ref_status"] = "verified against source run trace"
    else:
        trimmed["evidence_ref_status"] = "unverified — source run not available"
    if unresolved:
        trimmed["unresolved_evidence_refs"] = sorted(set(unresolved))
    return trimmed


def _validate_cultural_positioning_snapshot(payload: dict[str, Any]) -> None:
    """Validate a new frozen strategy against the completed source run before persistence.

    Legacy experiments without this optional snapshot keep the existing contract.
    The completed run store is volatile, so freeze is only accepted while its
    source trace/result is still available; the resulting experiment JSON itself
    is persisted independently in the existing repository.
    """
    source_bet = payload.get("source_bet")
    if not isinstance(source_bet, dict) or "cultural_multiverse_snapshot" not in source_bet:
        return
    snapshot = source_bet.get("cultural_multiverse_snapshot")

    def reject(message: str, status_code: int = 422) -> None:
        raise HTTPException(status_code=status_code, detail=f"Cultural positioning snapshot rejected: {message}")

    if not isinstance(snapshot, dict):
        reject("snapshot must be an object")
    if snapshot.get("snapshot_version") != "cultural-positioning-snapshot-v1":
        reject("unsupported snapshot_version")
    if snapshot.get("calculation_version") != "cultural-positioning-v1":
        reject("unsupported calculation_version")
    run_id = payload.get("source_run_id")
    if not isinstance(run_id, str) or not run_id or snapshot.get("source_run_id") != run_id:
        reject("snapshot source_run_id must match the experiment source_run_id")
    record = run_store.get(run_id)
    if record is None:
        reject("completed source run is no longer available for verification", 409)
    if record.status != RunStatus.COMPLETED or not isinstance(record.result, dict):
        reject("source run is not completed", 409)

    result = record.result
    source_status = result.get("data_status")
    if source_status not in {"measured", "fixture"}:
        reject("source run has no usable measured/fixture data status")
    if payload.get("data_status") != source_status or snapshot.get("original_data_status") != source_status:
        reject("data status does not match the completed source run")
    film = result.get("film") if isinstance(result.get("film"), dict) else {}
    source_title = film.get("title")
    if not isinstance(source_title, str) or payload.get("film_title") != source_title:
        reject("experiment film title does not match the completed source run")
    if snapshot.get("original_test_card") != result.get("test_card"):
        reject("original Test Card does not match the completed source run")

    strategies = snapshot.get("strategies")
    if not isinstance(strategies, list) or len(strategies) != 3:
        reject("snapshot must preserve all three strategy alternatives")
    strategy_by_id = {
        strategy.get("id"): strategy
        for strategy in strategies
        if isinstance(strategy, dict) and isinstance(strategy.get("id"), str)
    }
    if set(strategy_by_id) != {"anchor", "bridge", "frontier"}:
        reject("strategy alternatives must contain anchor, bridge and frontier exactly once")
    selected_id = snapshot.get("selected_strategy_id")
    selected = snapshot.get("selected_strategy")
    if not isinstance(selected_id, str) or selected_id not in strategy_by_id or not isinstance(selected, dict):
        reject("selected strategy is missing from the alternatives")
    if strategy_by_id[selected_id] != selected or selected.get("availability") != "available":
        reject("selected strategy must exactly match an available alternative")
    if payload.get("hypothesis") != selected.get("falsifiable_hypothesis"):
        reject("saved hypothesis does not match the selected strategy")
    if payload.get("action_plan") != selected.get("creative_direction"):
        reject("saved action plan does not match the selected strategy")

    policy = snapshot.get("policy")
    if not isinstance(policy, dict) or policy.get("formula_version") != "weighted-ordinal-preference-v1":
        reject("unsupported or missing What-If formula version")
    values = policy.get("values")
    if not isinstance(values, dict) or set(values) != {"fit", "exploration", "breadth"}:
        reject("policy must preserve fit, exploration and breadth priorities")
    if any(not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100 for value in values.values()):
        reject("policy priorities must be integers from 0 through 100")

    trace_call_ids = {
        row.get("call_id") for row in (record.trace or [])
        if isinstance(row, dict) and isinstance(row.get("call_id"), str) and row.get("call_id")
    }
    ranked = result.get("cohorts", {}).get("ranked", []) if isinstance(result.get("cohorts"), dict) else []
    source_members: dict[tuple[str, str], str] = {}
    ranked_ids: set[str] = set()
    for cohort in ranked if isinstance(ranked, list) else []:
        if not isinstance(cohort, dict) or not isinstance(cohort.get("cohort_id"), str):
            continue
        cohort_id = cohort["cohort_id"]
        ranked_ids.add(cohort_id)
        for member in cohort.get("members", []):
            if isinstance(member, dict) and isinstance(member.get("entity_id"), str) and isinstance(member.get("call_id"), str):
                source_members[(cohort_id, member["entity_id"])] = member["call_id"]
    input_entity_ids: set[str] = set()
    programme = result.get("programme", {})
    for item in programme.get("items", []) if isinstance(programme, dict) else []:
        if not isinstance(item, dict) or item.get("resolved") is not True:
            continue
        resolution = item.get("resolution_evidence") if isinstance(item.get("resolution_evidence"), dict) else {}
        entity_id = resolution.get("qloo_entity_id") or item.get("qloo_entity_id")
        if isinstance(entity_id, str) and entity_id:
            input_entity_ids.add(entity_id)

    def check_call_ids(value: Any) -> None:
        if not isinstance(value, list) or any(not isinstance(call_id, str) or call_id not in trace_call_ids for call_id in value):
            reject("snapshot contains a call reference absent from the source run trace")

    for strategy in strategies:
        if not isinstance(strategy, dict):
            reject("strategy alternative must be an object")
        availability = strategy.get("availability")
        if availability not in {"available", "unavailable"}:
            reject("strategy availability must be explicit")
        cohort_ids = strategy.get("source_cohort_ids", [])
        entity_refs = strategy.get("entity_refs", [])
        if not isinstance(cohort_ids, list) or any(not isinstance(cohort_id, str) or cohort_id not in ranked_ids for cohort_id in cohort_ids):
            reject("strategy references a cohort outside the source run")
        if not isinstance(entity_refs, list) or (availability == "available" and not entity_refs):
            reject("available strategy has no source-linked entities")
        if availability == "available" and not cohort_ids:
            reject("available strategy has no source cohort")
        for entity in entity_refs:
            if not isinstance(entity, dict):
                reject("strategy entity reference must be an object")
            cohort_id = entity.get("cohort_id")
            entity_id = entity.get("entity_id")
            call_id = entity.get("call_id")
            if not all(isinstance(value, str) for value in (cohort_id, entity_id, call_id)):
                reject("strategy entity reference is missing a string cohort, entity, or call ID")
            key = (cohort_id, entity_id)
            if key not in source_members or source_members[key] != call_id:
                reject("strategy entity/call reference does not match a returned source member")
            check_call_ids([call_id])
        evidence_refs = strategy.get("evidence_refs", [])
        if not isinstance(evidence_refs, list):
            reject("strategy evidence_refs must be a list")
        for evidence in evidence_refs:
            if not isinstance(evidence, dict):
                reject("evidence reference must be an object")
            check_call_ids(evidence.get("call_ids", []))
            evidence_cohorts = evidence.get("cohort_ids", [])
            evidence_entities = evidence.get("entity_ids", [])
            if not isinstance(evidence_cohorts, list) or any(not isinstance(cohort_id, str) or cohort_id not in ranked_ids for cohort_id in evidence_cohorts):
                reject("evidence reference names a cohort outside the source run")
            if not isinstance(evidence_entities, list) or any(not isinstance(entity_id, str) or (entity_id not in input_entity_ids and not any(member_id == entity_id for _, member_id in source_members)) for entity_id in evidence_entities):
                reject("evidence reference names an entity outside the source run")
            seed_id = evidence.get("source_seed_id")
            if seed_id is not None and (not isinstance(seed_id, str) or seed_id not in input_entity_ids):
                reject("attribution reference does not match a resolved source input")
        challenge = strategy.get("evidence_challenge", {})
        if isinstance(challenge, dict):
            check_call_ids(challenge.get("supporting_call_ids", []))
            challenge_inputs = challenge.get("source_inputs", [])
            if not isinstance(challenge_inputs, list):
                reject("evidence challenge source_inputs must be a list")
            for input_ref in challenge_inputs:
                if isinstance(input_ref, dict):
                    check_call_ids(input_ref.get("call_ids", []))

    design = snapshot.get("experiment_design")
    if not isinstance(design, dict) or design.get("observation_window") != payload.get("observation_window"):
        reject("experiment protocol must preserve the saved observation window")


@router.post("/experiments", status_code=201)
async def save_experiment(request: SaveExperimentRequest) -> dict[str, Any]:
    payload = request.model_dump()
    _validate_cultural_positioning_snapshot(payload)
    summary = payload.pop("investigation_summary", None)
    refs = payload.pop("evidence_refs", [])
    provenance = dict(payload.get("provenance") or {})
    snapshot = payload.pop("synthesis_snapshot", None)
    adopted = payload.pop("adopted_proposal", None)
    if summary is not None:
        provenance.setdefault("investigation_summary", summary)
    if refs:
        provenance_refs = sorted({r for r in refs if isinstance(r, str) and r})
        # Honest resolution: when the source run is known, refs that do not
        # correspond to real recorded calls are dropped and reported.
        dropped: list[str] = []
        if payload.get("source_run_id"):
            record = run_store.get(str(payload["source_run_id"]))
            if record is not None:
                known = {
                    row.get("call_id") for row in (record.trace or []) if row.get("call_id")
                }
                dropped = [r for r in provenance_refs if r not in known]
                provenance_refs = [r for r in provenance_refs if r in known]
        provenance.setdefault("evidence_refs", provenance_refs)
        if dropped:
            provenance["unresolved_evidence_refs"] = dropped
    if isinstance(snapshot, dict) and snapshot:
        # Known-call set for snapshot verification (same trace used above).
        snap_known: set[str] | None = None
        if payload.get("source_run_id"):
            snap_record = run_store.get(str(payload["source_run_id"]))
            if snap_record is not None:
                snap_known = {
                    row.get("call_id") for row in (snap_record.trace or [])
                    if row.get("call_id")
                }
        provenance.setdefault("synthesis_snapshot", _sanitize_snapshot(snapshot, snap_known))
    if isinstance(adopted, dict) and adopted:
        provenance.setdefault("adopted_proposal", {
            k: v for k, v in adopted.items() if k in _PROPOSAL_KEYS
        })
        # What the creator changed relative to the model's original proposal —
        # the model is never credited with the creator's manual edits.
        provenance["creator_edits"] = [
            field
            for field in ("hypothesis", "action_plan", "success_criteria", "observation_window")
            if str(adopted.get(field) or "") != str(payload.get(field) or "")
        ]
        provenance["adoption"] = {
            "origin": "model_proposal",
            "method": (snapshot or {}).get("method"),
        }
    payload["provenance"] = provenance
    try:
        experiment = get_repo().save_experiment(**payload)
    except DuplicateRequest as dup:
        # Retry-safe: replaying the same request returns the original decision.
        return {"duplicate": True, "experiment": dup.existing}
    return {"duplicate": False, "experiment": experiment}


@router.get("/experiments")
async def list_experiments() -> dict[str, Any]:
    return {"experiments": get_repo().list_experiments()}


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str) -> dict[str, Any]:
    repo = get_repo()
    experiment = repo.get_experiment(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    return {
        "experiment": experiment,
        "observations": repo.list_observations(experiment_id),
        "evaluations": repo.list_evaluations(experiment_id),
    }


@router.post("/experiments/{experiment_id}/observations", status_code=201)
async def add_observation(experiment_id: str, request: ObservationRequest) -> dict[str, Any]:
    try:
        observation = get_repo().add_observation(
            experiment_id, **request.model_dump()
        )
    except DuplicateRequest as dup:
        return {"duplicate": True, "observation": dup.existing}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"duplicate": False, "observation": observation}


@router.post("/experiments/{experiment_id}/evaluations", status_code=201)
async def add_evaluation(experiment_id: str, request: EvaluationRequest) -> dict[str, Any]:
    try:
        evaluation = get_repo().add_evaluation(
            experiment_id, **request.model_dump()
        )
    except DuplicateRequest as dup:
        return {"duplicate": True, "evaluation": dup.existing}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"duplicate": False, "evaluation": evaluation}


# ---------------------------------------------------------------------------
# Role-B synthesis (M13.12) — optional, provider-gated, never silently stubbed
# ---------------------------------------------------------------------------

_synthesis_provider_override: Any = None


def reset_synthesis_for_tests(provider: Any = None) -> None:
    """Test hook: inject a deterministic synthesis provider (or clear it)."""
    global _synthesis_provider_override
    _synthesis_provider_override = provider


class SynthesizeRequest(BaseModel):
    run_id: str = Field(..., min_length=1)


@router.get("/creator/synthesis-status")
def synthesis_status() -> dict[str, Any]:
    """Provider status WITHOUT secrets. BLOCKED is an honest state."""
    if public_demo_enabled():
        return {
            "available": False,
            "provider": "none",
            "model": None,
            "blocked_reason": "Optional synthesis is disabled in public demo mode.",
        }
    if _synthesis_provider_override is not None:
        return {
            "available": True,
            "provider": _synthesis_provider_override.kind,
            "model": getattr(_synthesis_provider_override, "model", None),
            "note": "test/override provider injected",
        }
    config = LLMProviderConfig.from_env()
    return {
        "available": config.configured,
        "provider": "openai_compatible" if config.configured else "none",
        "model": config.model if config.configured else None,
        **({} if config.configured else {
            "blocked_reason": (
                "ADJACENT_LLM_API_KEY not configured — synthesis is BLOCKED. "
                "The deterministic investigation remains fully available."
            )
        }),
    }


@router.post("/creator/synthesize")
def creator_synthesize(request: SynthesizeRequest) -> dict[str, Any]:
    """Render a creator-facing brief from a completed run's investigation.

    The deterministic investigation is the decision engine; this is a bounded
    natural-language rendering with post-validation and an explicitly labelled
    deterministic fallback. It NEVER re-executes tools and NEVER fabricates:
    invalid model output is rejected and the fallback says so.
    """
    record = run_store.get(request.run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"run {request.run_id} not found")
    if record.status.value == "failed":
        raise HTTPException(
            status_code=409,
            detail="Failed runs cannot be synthesized; start from a completed or insufficient run.",
        )
    result = record.result or {}
    investigation = result.get("investigation")
    if not investigation:
        raise HTTPException(
            status_code=409,
            detail="run has no investigation to synthesize (not completed or not a creator run)",
        )

    if _synthesis_provider_override is not None:
        provider = _synthesis_provider_override
    else:
        config = LLMProviderConfig.from_env()
        if not config.configured:
            raise HTTPException(
                status_code=503,
                detail=(
                    "LLM synthesis not configured (ADJACENT_LLM_API_KEY unset). "
                    "The investigation itself is complete and deterministic; "
                    "synthesis is optional."
                ),
            )
        provider = OpenAICompatibleProvider(config)

    try:
        outcome = synthesize_investigation(investigation, provider)
    except LLMUnavailableError as exc:
        # Provider construction can still fail (e.g. transport issues upstream).
        raise HTTPException(status_code=502, detail=f"synthesis provider unavailable: {exc}") from exc
    return {"run_id": request.run_id, **outcome}
