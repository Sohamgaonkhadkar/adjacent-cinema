"""Live pipeline runtime — runs the Adjacent analysis against real Qloo.

This module provides `LivePipeline` (implements `agent.tools.PipelineRuntime`)
and the `run_live()` entry point.  It uses the trusted resolver for entity
resolution and the real QlooClient for all other tools.

Key differences from `FixturePipeline`:
    1. Entity resolution uses /search with verification (not fixture mappings)
    2. All Qloo calls go to the live API
    3. Data status is "measured" (not "fixture")
    4. No fixture file is loaded

The orchestrator, evidence gate, and ranking logic are unchanged.
"""

from __future__ import annotations

import asyncio
from typing import Any

from . import evidence
from .agent.budget import Budget
from .agent.orchestrator import AgentOrchestrator
from .agent.state import AdjacentState, Finding, ProgrammeItem
from .agent.tools import (
    ExpandResult,
    RankResult,
    ResolveResult,
    TasteResult,
)
from .config import Settings
from .domain.cohorts import build_candidate_cohorts
from .domain.domain_selection import select_domains
from .domain.ledger import ProvenanceLedger
from .qloo.client import QlooClient
from .resolution.contract import MatchStatus
from .resolution.resolver import EntityResolver
from .runner import (
    _expand_candidates,
    _rank,
    _taste_profile,
    render_run_text,
)


class LivePipeline:
    """Live Qloo runtime — implements `agent.tools.PipelineRuntime`.

    Resolution uses the trusted resolver (EntityResolver) which verifies
    each entity via /search.  All other tools delegate to the existing
    step functions with the live QlooClient.
    """

    def __init__(
        self,
        client: QlooClient,
        resolver: EntityResolver,
        programme: list[dict[str, Any]],
    ) -> None:
        self.client = client
        self.resolver = resolver
        self._programme = programme

    @property
    def name(self) -> str:
        return f"live:{type(self.client).__name__}"

    @property
    def data_status(self) -> str:
        return "measured"

    async def resolve_programme(
        self, state: AdjacentState, budget: Budget
    ) -> ResolveResult:
        """Resolve film references as movies and Creator themes as Qloo tags."""
        theme_queries = [query.strip() for query in state.theme_queries if query.strip()]
        expected_calls = sum(
            1 + int(bool(item.get("imdb_id")))
            for item in self._programme
        ) + len(theme_queries)
        budget.ensure(expected_calls)
        rows_before = len(self.client.recorder.rows) if getattr(self.client, "recorder", None) else 0

        try:
            results = await self.resolver.resolve_programme(self._programme) if self._programme else []
            for item, resolution in zip(state.programme, results, strict=False):
                item.resolution_evidence = resolution.to_dict()
                for call_id in (resolution.call_id, *resolution.related_call_ids):
                    if call_id and call_id not in state.resolution_call_ids:
                        state.resolution_call_ids.append(call_id)

                if resolution.match_status == MatchStatus.VERIFIED:
                    item.resolved_entity_id = resolution.qloo_entity_id
                    item.resolved_name = resolution.qloo_name
                    item.entity_type = resolution.qloo_entity_type
                    item.subtype = None
                    item.popularity = resolution.qloo_popularity
                    item.source_call_id = resolution.call_id
                elif resolution.match_status == MatchStatus.AMBIGUOUS:
                    state.findings.append(Finding(
                        code="ambiguous_resolution",
                        message=(
                            f"{item.title!r}: {resolution.verification_notes[0] if resolution.verification_notes else 'ambiguous match'}"
                        ),
                        stats=resolution.to_dict(),
                    ))
                elif resolution.match_status == MatchStatus.MISMATCH:
                    state.findings.append(Finding(
                        code="mismatch_resolution",
                        message=(
                            f"{item.title!r}: {resolution.verification_notes[0] if resolution.verification_notes else 'title/year mismatch'}"
                        ),
                        stats=resolution.to_dict(),
                    ))
                else:
                    state.findings.append(Finding(
                        code="unresolved_entity",
                        message=f"{item.title!r}: not found in Qloo",
                        stats=resolution.to_dict(),
                    ))

            # Theme text is a separate input type. Resolve it through /v2/tags,
            # and only use a unique exact-name match; don't treat a theme as a film.
            import unicodedata

            def normalise(value: str) -> str:
                decomposed = unicodedata.normalize("NFKD", value).casefold()
                return " ".join(
                    "".join(ch for ch in decomposed if not unicodedata.combining(ch)).split()
                )

            state.theme_resolution = []
            state.theme_tag_ids = []
            for theme in theme_queries:
                response = await self.client.tags(
                    filter_query=theme,
                    take=20,
                    tool="resolve_creator_theme",
                )
                exact = {
                    tag.tag_id: tag
                    for tag in response.results
                    if tag.tag_id and tag.name and normalise(tag.name) == normalise(theme)
                }
                call_id = response.call_id
                if call_id and call_id not in state.resolution_call_ids:
                    state.resolution_call_ids.append(call_id)
                if len(exact) == 1:
                    tag_id, tag = next(iter(exact.items()))
                    state.theme_tag_ids.append(tag_id)
                    state.theme_resolution.append({
                        "input": theme,
                        "status": "matched",
                        "qloo_tag_id": tag_id,
                        "qloo_name": tag.name,
                        "call_id": call_id,
                    })
                elif len(exact) > 1:
                    state.theme_resolution.append({
                        "input": theme,
                        "status": "ambiguous",
                        "qloo_tag_id": None,
                        "qloo_name": None,
                        "call_id": call_id,
                        "candidate_count": len(exact),
                    })
                else:
                    state.theme_resolution.append({
                        "input": theme,
                        "status": "unresolved",
                        "qloo_tag_id": None,
                        "qloo_name": None,
                        "call_id": call_id,
                        "candidate_count": 0,
                    })

            state.theme_tag_ids = list(dict.fromkeys(state.theme_tag_ids))
            film_verdict = evidence.evaluate_programme_resolution(len(state.resolved_items))
            if state.theme_tag_ids:
                state.resolution_verdict = evidence.EvidenceVerdict(
                    True,
                    "seed_signals_resolved",
                    "",
                    {
                        "verified_reference_works": len(state.resolved_items),
                        "required_reference_works": evidence.MIN_RESOLVED_TITLES,
                        "resolved_theme_tags": len(state.theme_tag_ids),
                    },
                )
            else:
                state.resolution_verdict = film_verdict

            if state.resolution_verdict.insufficient:
                state.findings.append(Finding(
                    code=state.resolution_verdict.reason_code,
                    message=state.resolution_verdict.message,
                    stats=dict(state.resolution_verdict.stats),
                ))

            matched_themes = len(state.theme_tag_ids)
            return ResolveResult(
                tool="resolve_programme",
                action="resolve",
                detail=(
                    f"verified {len(state.resolved_items)}/{len(state.programme)} film reference(s); "
                    f"matched {matched_themes}/{len(theme_queries)} theme tag(s); "
                    f"gate={state.resolution_verdict.reason_code if state.resolution_verdict else 'not evaluated'}"
                ),
                call_ids=tuple(state.resolution_call_ids),
                resolved=len(state.resolved_items),
                unresolved=len(state.unresolved_items),
                verdict=state.resolution_verdict,
            )
        finally:
            recorder = getattr(self.client, "recorder", None)
            if recorder is not None:
                calls_made = max(0, len(recorder.rows) - rows_before)
                budget.record_calls(calls_made)

    async def get_taste_profile(
        self, state: AdjacentState, budget: Budget
    ) -> TasteResult:
        budget.ensure(1)
        await _taste_profile(self.client, state, budget)
        verdict = state.taste_verdict
        return TasteResult(
            tool="get_taste_profile",
            action="analyse",
            detail=(
                f"{len(state.taste_tags)} tag(s) scored from {len(state.resolved_ids)} signal id(s); "
                f"gate={verdict.reason_code if verdict else 'not evaluated'}"
            ),
            call_ids=(state.taste_call_id,) if state.taste_call_id else (),
            call_id=state.taste_call_id,
            tag_count=len(state.taste_tags),
            tags_above_high=sum(
                1 for tag in state.taste_tags if (tag.affinity or 0) >= evidence.BAND_HIGH
            ),
            verdict=verdict,
        )

    async def expand_candidates(
        self, state: AdjacentState, budget: Budget
    ) -> ExpandResult:
        # M11: Dynamic domain selection based on Taste DNA
        selection = select_domains(state.taste_tags)
        domains = selection.selected_domains
        state.domain_selection = selection  # Store for evidence export
        budget.ensure(len(domains))
        await _expand_candidates(self.client, state, budget, domains=domains)
        failed = tuple(
            d for d in domains if d not in state.expansion_call_ids
        )
        return ExpandResult(
            tool="expand_candidates",
            action="expand",
            detail=(
                f"{sum(len(v) for v in state.candidates_by_domain.values())} candidate(s) across "
                f"{len(state.candidates_by_domain)}/{len(domains)} domain(s); "
                f"{len(failed)} domain(s) failed; "
                f"{selection.qloo_calls_saved} calls saved by domain selection"
            ),
            call_ids=tuple(state.expansion_call_ids.values()),
            candidates=sum(len(v) for v in state.candidates_by_domain.values()),
            domains=domains,
            failed_domains=failed,
            per_domain={d: len(v) for d, v in state.candidates_by_domain.items()},
        )

    async def rank_cohorts(
        self, state: AdjacentState, budget: Budget
    ) -> RankResult:
        if not state.cohorts:
            state.cohorts = build_candidate_cohorts(
                state.candidates_by_domain,
                source_call_ids=state.expansion_call_ids,
            )
        contexts = len({c.domain for c in state.cohorts})
        budget.ensure(contexts)
        await _rank(self.client, state, budget)
        ranking = state.ranking
        return RankResult(
            tool="rank_cohorts",
            action="rank",
            detail=(
                f"ONE logical operation over {len(state.cohorts)} cohort(s) in "
                f"{len(ranking.contexts) if ranking else 0} context(s); "
                f"{len(state.ranked)} cleared, {len(state.rejected)} rejected"
            ),
            call_ids=tuple(ranking.scoring_call_ids) if ranking else (),
            operation_call_id=ranking.operation_call_id if ranking else None,
            contexts=len(ranking.contexts) if ranking else 0,
            cohorts_ranked=len(state.ranked),
            cohorts_rejected=len(state.rejected),
            entities_scored=ranking.scored_entity_count if ranking else 0,
        )


async def run_live_async(
    programme: list[dict[str, Any]],
    *,
    settings: Settings | None = None,
    render: bool = True,
    budget: Budget | None = None,
    resolver_delay_s: float = 2.0,
) -> AdjacentState:
    """Execute the full Adjacent pipeline against live Qloo.

    Args:
        programme: List of dicts with 'title', optional 'year', optional 'imdb_id'.
        settings: Settings (reads from env if not provided).
        render: Whether to render human-readable output.
        budget: Budget override.
        resolver_delay_s: Delay between /search calls (rate limit).
    """
    settings = settings or Settings.from_env()

    if settings.mode != "live":
        raise RuntimeError(
            "run_live_async requires a live Qloo API key. "
            "Set QLOO_API_KEY in your environment."
        )

    client = QlooClient(settings)
    resolver = EntityResolver(client, delay_s=resolver_delay_s)

    # Seed programme items BEFORE the orchestrator starts, so validate_input
    # sees them.  The resolver will populate entity IDs during RESOLVE.
    programme_items = [
        ProgrammeItem(
            title=str(item.get("title", "(unnamed)")),
            year=item.get("year"),
            imdb_id=item.get("imdb_id"),
            declared_entity_id=item.get("entity_id"),
        )
        for item in programme
    ]

    state = AdjacentState(
        run_id="live-demo",
        fixture_name=None,
        fixture_path=None,
        scenario="live",
        fixture_notice="LIVE QLOO DATA — every affinity below is a real Qloo response",
        data_status="measured",
        description="Live Adjacent analysis against real Qloo API",
        programme=programme_items,
        budget=budget or Budget(),
    )
    state.ledger = ProvenanceLedger(recorder=client.recorder, data_status="measured")

    pipeline = LivePipeline(client, resolver, programme)
    orchestrator = AgentOrchestrator(pipeline)

    try:
        state = await orchestrator.run(state)
    finally:
        await client.aclose()

    if render:
        state.rendered_text = render_live_run_text(state)
    return state


def run_live(
    programme: list[dict[str, Any]],
    *,
    settings: Settings | None = None,
    render: bool = True,
    budget: Budget | None = None,
    resolver_delay_s: float = 2.0,
) -> AdjacentState:
    """Synchronous entry point for CLI."""
    return asyncio.run(
        run_live_async(
            programme,
            settings=settings,
            render=render,
            budget=budget,
            resolver_delay_s=resolver_delay_s,
        )
    )


def render_live_run_text(run: AdjacentState) -> str:
    """Render a live run with LIVE QLOO labels."""
    text = render_run_text(run)
    # Replace fixture labels with live labels
    text = text.replace(
        "!! DATA STATUS: FIXTURE — SYNTHETIC, HAND-AUTHORED, NOT MEASURED QLOO OUTPUT !!",
        "!! DATA STATUS: LIVE — REAL QLOO RESPONSES, MEASURED AGAINST HACKATHON API !!",
    )
    text = text.replace(
        "!! This run made no live Qloo call. Every affinity below is a fixture value. !!",
        "!! This run used LIVE Qloo calls. Every affinity below is a measured value. !!",
    )
    text = text.replace(
        "ADJACENT — MILESTONE 1 (FIXTURE SPINE)",
        "ADJACENT — LIVE DEMO (TRUSTED RESOLUTION)",
    )
    text = text.replace(
        "REMINDER: every affinity above is FIXTURE DATA until docs/API_NOTES.md records a live probe.",
        "REMINDER: every affinity above is LIVE QLOO DATA measured against the hackathon API.",
    )
    return text
