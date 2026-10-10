"""The fixture runner — where the agent, the artefacts and the CLI meet.

This module owns three things and no more:

1. **The step implementations.** `_resolve_programme`, `_taste_profile`,
   `_expand_candidates` and `_rank` are the deterministic Milestone-1 steps,
   unchanged. They are the bodies of the agent's tools, reached through
   `FixturePipeline` (which implements `agent.tools.PipelineRuntime`). They are
   not a second pipeline: the only driver is `agent.orchestrator`.
2. **The run record and its rendering.** `AdjacentState` (aliased here as
   `MilestoneRun` for the Milestone-1 call sites) is rendered into the sections the
   CLI prints, with every number going through the provenance ledger.
3. **The entry points.** `run_fixture()` / `run_fixture_async()`.

    programme input
      → AgentOrchestrator: INIT → PLAN → {RESOLVE → ANALYSE → EXPAND → RANK} →
        EVALUATE each time → STOP
      → render_run_text()

The stop vocabulary is `agent.stop.StopReason`: `complete`, `insufficiency`,
`budget_exhausted`, `invalid_input`, `error`, `timeout`. A technical failure is
never reported as insufficient evidence.

Deliberately out of scope: geography (heatmap), the programme bet, the two-sided
score, and any live Qloo call.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import evidence
from .agent.budget import DEFAULT_MAX_QLOO_CALLS, Budget
from .agent.orchestrator import AgentOrchestrator
from .agent.state import (
    AdjacentState,
    Finding,
    ProgrammeItem,
)
from .agent.stop import StopReason
from .agent.tools import (
    ExpandResult,
    RankResult,
    ResolveResult,
    TasteResult,
    build_evidence_report,
)
from .config import Settings
from .domain.cohorts import (
    DEFAULT_EXPANSION_DOMAINS,
    CandidateCohort,
    build_candidate_cohorts,
)
from .domain.ledger import ProvenanceLedger
from .domain.reasons import RejectionCode
from .domain.scoring import CohortRanker
from .qloo import DEFAULT_FIXTURE, MockQlooClient
from .qloo.errors import NotFoundError, QlooError
from .qloo.models import ScoredEntity
from .qloo.params import EP_ENTITIES, EP_INSIGHTS

#: Canonical stop reasons, re-exported under the Milestone-1 names so existing
#: call sites and assertions keep working.
STOP_COMPLETE = StopReason.COMPLETE.value
STOP_INSUFFICIENCY = StopReason.INSUFFICIENCY.value
STOP_ERROR = StopReason.ERROR.value

#: The Qloo-call ceiling for one run. One definition, in the agent's budget.
MAX_PIPELINE_CALLS = DEFAULT_MAX_QLOO_CALLS

#: Milestone-1 name for the run record. It is the agent's state: one object, one
#: source of truth.
MilestoneRun = AdjacentState

#: The Milestone-1 name for the budget, kept so the step functions can be driven
#: directly in tests without going through the orchestrator.
_Budget = Budget

#: What the fixture replay does NOT simulate. Printed with every run so nobody
#: mistakes a fixture replay for a faithful simulation of the live API.
FIXTURE_SIMULATION_LIMITS = (
    "the fixture replays a fixed candidate set; request filters such as "
    "filter.popularity.min/max are passed to the mock but NOT applied by it",
    "filter.results.entities returns every id present in the fixture branch; the "
    "live behaviour of that filter is probe D and is still unverified",
    "no backfill results exist in these fixtures, so backfill detection is not exercised by this run",
)


def programme_items(raw_items: Sequence[Mapping[str, Any]]) -> list[ProgrammeItem]:
    """Map structured programme input to typed items. The only such mapping.

    The input is structured (a fixture today, a venue's programme export later);
    nothing here guesses or parses free text.
    """
    return [
        ProgrammeItem(
            title=str(item.get("title", "(unnamed)")),
            year=item.get("year"),
            imdb_id=item.get("imdb_id"),
            declared_entity_id=item.get("entity_id"),
        )
        for item in raw_items
    ]


# ---------------------------------------------------------------------------
# The step implementations — the bodies of the agent's tools
# ---------------------------------------------------------------------------


class FixturePipeline:
    """Milestone-1 deterministic steps, exposed as `agent.tools.PipelineRuntime`.

    This is the only place the agent's tools are wired to an implementation. A live
    runtime implements the same four methods over `QlooClient`; the orchestrator
    would not change by a character.
    """

    def __init__(self, client: Any, fixture: Any, *, data_status: str = "fixture") -> None:
        self.client = client
        self.fixture = fixture
        self._data_status = data_status

    @property
    def name(self) -> str:
        return f"{type(self.client).__name__}:{self.fixture.name}"

    @property
    def data_status(self) -> str:
        return self._data_status

    # -- resolve_programme -------------------------------------------------
    async def resolve_programme(self, state: AdjacentState, budget: Budget) -> ResolveResult:
        lookups = int(any(item.imdb_id for item in state.programme)) + int(
            any(item.declared_entity_id for item in state.programme)
        )
        budget.ensure(max(lookups, 1))
        await _resolve_programme(self.client, self.fixture, state, budget)
        verdict = state.resolution_verdict
        return ResolveResult(
            tool="resolve_programme",
            action="resolve",
            detail=(
                f"resolved {len(state.resolved_items)}/{len(state.programme)} programme item(s) "
                f"in {len(state.resolution_call_ids)} call(s); "
                f"gate={verdict.reason_code if verdict else 'not evaluated'}"
            ),
            call_ids=tuple(state.resolution_call_ids),
            resolved=len(state.resolved_items),
            unresolved=len(state.unresolved_items),
            verdict=verdict,
        )

    # -- get_taste_profile -------------------------------------------------
    async def get_taste_profile(self, state: AdjacentState, budget: Budget) -> TasteResult:
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
            tags_above_high=sum(1 for tag in state.taste_tags if (tag.affinity or 0) >= evidence.BAND_HIGH),
            verdict=verdict,
        )

    # -- expand_candidates ------------------------------------------------
    async def expand_candidates(self, state: AdjacentState, budget: Budget) -> ExpandResult:
        domains = tuple(DEFAULT_EXPANSION_DOMAINS)
        budget.ensure(len(domains))
        await _expand_candidates(self.client, state, budget)
        # A domain whose call raised is absent from expansion_call_ids: the step
        # records the reason as a finding and carries on, so the agent can tell
        # "some domains degraded" apart from "every call failed".
        failed = tuple(domain for domain in domains if domain not in state.expansion_call_ids)
        return ExpandResult(
            tool="expand_candidates",
            action="expand",
            detail=(
                f"{sum(len(v) for v in state.candidates_by_domain.values())} candidate(s) across "
                f"{len(state.candidates_by_domain)}/{len(domains)} domain(s); "
                f"{len(failed)} domain(s) failed"
            ),
            call_ids=tuple(state.expansion_call_ids.values()),
            candidates=sum(len(v) for v in state.candidates_by_domain.values()),
            domains=domains,
            failed_domains=failed,
            per_domain={d: len(v) for d, v in state.candidates_by_domain.items()},
        )

    # -- rank_cohorts ------------------------------------------------------
    async def rank_cohorts(self, state: AdjacentState, budget: Budget) -> RankResult:
        if not state.cohorts:
            # Construction is part of this action: the ranker receives candidate
            # cohorts, never a pre-scored pool.
            state.cohorts = build_candidate_cohorts(
                state.candidates_by_domain, source_call_ids=state.expansion_call_ids
            )
        contexts = len({cohort.domain for cohort in state.cohorts})
        budget.ensure(contexts)
        await _rank(self.client, state, budget)
        ranking = state.ranking
        return RankResult(
            tool="rank_cohorts",
            action="rank",
            detail=(
                f"ONE logical operation over {len(state.cohorts)} candidate cohort(s) in "
                f"{len(ranking.contexts) if ranking else 0} scoring context(s); "
                f"{len(state.ranked)} cleared the gate, {len(state.rejected)} rejected"
            ),
            call_ids=tuple(ranking.scoring_call_ids) if ranking else (),
            operation_call_id=ranking.operation_call_id if ranking else None,
            contexts=len(ranking.contexts) if ranking else 0,
            cohorts_ranked=len(state.ranked),
            cohorts_rejected=len(state.rejected),
            entities_scored=ranking.scored_entity_count if ranking else 0,
        )


# ---------------------------------------------------------------------------
# The Milestone-1 steps (unchanged), driven by the tools above
# ---------------------------------------------------------------------------


async def _resolve_programme(client: Any, fixture: Any, run: AdjacentState, budget: Budget) -> None:
    """Resolve the fixture's programme through /entities.

    A 404 is a data outcome — "this title is not in Qloo" — not an outage, and it
    must never be papered over by a guess.
    """
    if not run.programme:
        # Direct callers (and the Milestone-1 test) hand over an empty state, so the
        # step seeds itself from the fixture. A run driven by the orchestrator has
        # already seeded the state from the real input at INIT.
        run.programme = programme_items(fixture.programme)

    imdb_ids = [p.imdb_id for p in run.programme if p.imdb_id]
    declared_ids = [p.declared_entity_id for p in run.programme if p.declared_entity_id]
    looked_up: list[ScoredEntity] = []

    if imdb_ids and budget.take():
        try:
            response = await client.entities(
                external_ids={"imdb": imdb_ids}, tool="resolve_entities:external.imdb"
            )
        except NotFoundError as exc:
            run.resolution_call_ids.append(exc.call_id or "unrecorded")
            run.findings.append(
                Finding(
                    code="unresolved_external_ids",
                    message=(
                        f"no programme title matched external.imdb lookup ({len(imdb_ids)} id(s) "
                        "supplied): these titles are not in the taste graph as far as this "
                        "evidence goes"
                    ),
                    stats={"imdb_ids": imdb_ids},
                )
            )
        else:
            run.resolution_call_ids.append(response.call_id)
            looked_up.extend(response.results)

    if declared_ids and budget.take():
        try:
            response = await client.entities(entity_ids=declared_ids, tool="resolve_entities:by_id")
        except NotFoundError as exc:
            run.resolution_call_ids.append(exc.call_id or "unrecorded")
            run.findings.append(
                Finding(
                    code="unresolved_entity_ids",
                    message=(
                        f"none of the {len(declared_ids)} supplied entity ids are present in the "
                        "fixture/lookup"
                    ),
                    stats={"entity_ids": declared_ids},
                )
            )
        else:
            run.resolution_call_ids.append(response.call_id)
            looked_up.extend(response.results)

    if not run.resolution_call_ids:
        run.findings.append(
            Finding(
                code="resolution_skipped",
                message="the programme input carried no entity ids and no external ids",
            )
        )
        run.resolution_verdict = evidence.evaluate_programme_resolution(0)
        run.findings.append(
            Finding(
                code=run.resolution_verdict.reason_code,
                message=run.resolution_verdict.message,
                stats=dict(run.resolution_verdict.stats),
            )
        )
        return

    returned = {e.entity_id: e for e in looked_up}
    for item in run.programme:
        # Only an explicit declared id can resolve here. Titles are never
        # fuzzy-matched against a search result in this milestone.
        entity = returned.get(item.declared_entity_id or "")
        if entity is None:
            continue
        item.resolved_entity_id = entity.entity_id
        item.resolved_name = entity.name
        item.entity_type = entity.type
        item.subtype = entity.subtype
        item.popularity = entity.popularity
        item.source_call_id = run.resolution_call_ids[-1]

    run.resolution_verdict = evidence.evaluate_programme_resolution(len(run.resolved_items))
    if run.resolution_verdict.insufficient:
        run.findings.append(
            Finding(
                code=run.resolution_verdict.reason_code,
                message=run.resolution_verdict.message,
                stats=dict(run.resolution_verdict.stats),
            )
        )


async def _taste_profile(client: Any, run: AdjacentState, budget: Budget) -> None:
    ids = run.resolved_ids
    if not ids:
        run.taste_verdict = evidence.evaluate_tags([])
        run.findings.append(
            Finding(
                code="taste_skipped",
                message="no resolved entities, so no taste profile could be requested",
            )
        )
        return
    if not budget.take():
        run.findings.append(Finding(code="budget_exhausted", message="no budget for the taste call"))
        return
    response = await client.insights(
        filter_type="urn:tag",
        signal_interests_entities=ids,
        take=50,
        tool="taste_profile",
    )
    run.taste_call_id = response.call_id
    run.taste_tags = list(response.results)
    run.taste_verdict = evidence.evaluate_tags(response.results)
    if run.taste_verdict.insufficient:
        run.findings.append(
            Finding(
                code=run.taste_verdict.reason_code,
                message=run.taste_verdict.message,
                stats=dict(run.taste_verdict.stats),
            )
        )


async def _expand_candidates(client: Any, run: AdjacentState, budget: Budget, *, domains: tuple[str, ...] | None = None) -> None:
    """One adjacency call per domain. A failure degrades that domain, never the run."""
    ids = run.resolved_ids
    if not ids:
        return
    target_domains = domains or DEFAULT_EXPANSION_DOMAINS
    for domain in target_domains:
        if not budget.take():
            run.findings.append(
                Finding(
                    code="budget_exhausted",
                    message=f"call budget reached before expanding domain {domain}",
                    stats={"calls_used": budget.qloo_calls_used, "limit": budget.max_qloo_calls},
                )
            )
            break
        try:
            response = await client.insights(
                filter_type=domain,
                signal_interests_entities=ids,
                filter_popularity_min=0.05,
                filter_popularity_max=0.90,
                take=50,
                tool=f"expand_adjacency:{domain}",
            )
        except QlooError as exc:
            run.findings.append(
                Finding(
                    code="expansion_failed",
                    message=f"{domain} expansion failed: {exc}",
                    stats=exc.to_dict(),
                )
            )
            continue
        run.candidates_by_domain[domain] = [e for e in response.results if e.entity_id]
        run.expansion_call_ids[domain] = response.call_id


async def _rank(client: Any, run: AdjacentState, budget: Budget) -> None:
    if not run.cohorts:
        run.findings.append(
            Finding(
                code=RejectionCode.NO_VALID_COHORT.value,
                message=(
                    "no candidate cohorts could be constructed — the expansion calls returned "
                    "nothing that can be grouped"
                ),
                stats={"candidates": sum(len(v) for v in run.candidates_by_domain.values())},
            )
        )
        return
    remaining = budget.remaining_calls
    contexts_needed = len({c.domain for c in run.cohorts})
    if contexts_needed > remaining:
        run.findings.append(
            Finding(
                code="budget_exhausted",
                message="call budget reached before every scoring context could be scored",
                stats={"needed": contexts_needed, "remaining": remaining},
            )
        )
        # Score what the budget allows; the shortfall is recorded, not hidden.
        run.cohorts = [
            c for c in run.cohorts if c.domain in sorted({x.domain for x in run.cohorts})[:remaining]
        ]
    ranker = CohortRanker(client, programme_ids=run.resolved_ids)
    run.ranking = await ranker.build_and_rank_cohorts(run.cohorts)
    budget.record_calls(len(run.ranking.contexts))
    run.ranked = list(run.ranking.ranked)
    run.rejected = list(run.ranking.rejected)
    for cohort_id in run.ranking.unscored_member_ids:
        run.findings.append(
            Finding(
                code=RejectionCode.UNSCORED_MEMBERS.value,
                message=f"{cohort_id} was not returned by its scoring context, so it was not scored",
            )
        )


async def run_fixture_async(
    fixture: str | Path = DEFAULT_FIXTURE,
    *,
    settings: Settings | None = None,
    render: bool = True,
    budget: Budget | None = None,
) -> AdjacentState:
    """Execute the pipeline against a fixture, through the agent. No API key required."""
    settings = settings or Settings.from_env()
    fixture_path = resolve_fixture_path(fixture, settings=settings)
    name = fixture_path.stem

    client = MockQlooClient(settings, fixture=name, run_id=f"m1-{name}")
    fx = client.fixture

    state = AdjacentState(
        run_id=f"m1-{name}",
        fixture_name=name,
        fixture_path=str(fixture_path),
        scenario=fx.scenario,
        fixture_notice=client.notice,
        data_status="fixture",
        description=fx.description,
        programme=programme_items(fx.programme),
        budget=budget or Budget(),
    )
    state.ledger = ProvenanceLedger(recorder=client.recorder, data_status="fixture")

    orchestrator = AgentOrchestrator(FixturePipeline(client, fx))
    state = await orchestrator.run(state)

    if render:
        state.rendered_text = render_run_text(state)
    return state


def run_fixture(
    fixture: str | Path = DEFAULT_FIXTURE,
    *,
    settings: Settings | None = None,
    render: bool = True,
    budget: Budget | None = None,
) -> AdjacentState:
    """Synchronous entry point used by the CLI and the tests."""
    return asyncio.run(run_fixture_async(fixture, settings=settings, render=render, budget=budget))


def resolve_fixture_path(value: str | Path, *, settings: Settings | None = None) -> Path:
    """Accept 'portland_strong', 'fixtures/portland_strong.json' or an absolute path.

    There is exactly one fixture system: everything resolves through
    `Settings.fixtures_dir`, which is what `load_fixture` uses too.
    """
    settings = settings or Settings.from_env()
    raw = Path(str(value))
    candidates = [raw, raw if raw.is_absolute() else Path.cwd() / raw]
    if raw.suffix == ".json":
        candidates.append(settings.fixtures_dir / raw.name)
    else:
        candidates.append(settings.fixtures_dir / f"{raw.name}.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    available = sorted(p.stem for p in settings.fixtures_dir.glob("*.json"))
    raise FileNotFoundError(
        f"fixture {value!r} not found. Looked in {settings.fixtures_dir}. Available: {available}"
    )


def gate_status(run: AdjacentState) -> dict[str, bool]:
    """The three gates, exactly as Milestone 1 reported them. One implementation,
    in `agent.tools.assess_evidence`."""
    return build_evidence_report(run).gates


# ---------------------------------------------------------------------------
# Rendering — every displayed number goes through the ledger
# ---------------------------------------------------------------------------

WIDTH = 88

SECTION_ORDER = (
    "PROGRAMME",
    "RESOLUTION",
    "TASTE PROFILE",
    "CANDIDATE COHORTS",
    "RANKED COHORTS",
    "REJECTED",
    "EVIDENCE",
    "STOP",
)


def _rule(char: str = "=") -> str:
    return char * WIDTH


def _section(title: str) -> list[str]:
    return ["", _rule("-"), title, _rule("-")]


def _runtime_label(run: AdjacentState) -> str:
    """Which implementation drove the run. Fixture today; a live runtime later."""
    scenario = run.scenario or run.fixture_name or "unknown"
    return f"{'fixture' if run.data_status == 'fixture' else 'live'}:{scenario}"


def _entity_index(run: MilestoneRun) -> dict[str, ScoredEntity]:
    return {
        entity.entity_id: entity
        for entities in run.candidates_by_domain.values()
        for entity in entities
        if entity.entity_id
    }


def _label(run: MilestoneRun, entity_id: str) -> str:
    entity = _entity_index(run).get(entity_id)
    if entity is None:
        return entity_id
    return f"{entity.name or entity_id}"


def _names(run: MilestoneRun, ids: Sequence[str]) -> str:
    return ", ".join(_label(run, entity_id) for entity_id in ids) or "—"


def render_run_text(run: MilestoneRun) -> str:
    """Human-readable milestone output. Registers every number with the ledger."""
    if run.ledger is None:  # pragma: no cover - defensive
        raise ValueError("cannot render a run without a ledger")
    led = run.ledger
    file_source = f"file:{run.fixture_name}.json"
    out: list[str] = []

    out += [
        _rule(),
        "ADJACENT — MILESTONE 1 (FIXTURE SPINE)",
        _rule(),
        f"SCENARIO      {run.scenario}",
        f"FIXTURE       {run.fixture_path}",
        f"DESCRIPTION   {run.description}",
        "",
        "!! DATA STATUS: FIXTURE — SYNTHETIC, HAND-AUTHORED, NOT MEASURED QLOO OUTPUT !!",
        f"!! {run.fixture_notice}",
        "!! This run made no live Qloo call. Every affinity below is a fixture value. !!",
    ]

    # --- PROGRAMME ---------------------------------------------------------
    out += _section("PROGRAMME")
    out.append(
        f"items: {led.fmt(len(run.programme), label='programme items', source=file_source)}"
        "   (source of the item list: the fixture file)"
    )
    for index, item in enumerate(run.programme, start=1):
        year = led.fmt(item.year, label=f"programme[{index}].year", source=file_source)
        mark = "[resolved]" if item.resolved else "[not in Qloo]"
        target = item.resolved_entity_id or "excluded from every signal below"
        out.append(f"  {index:>2}. {item.title} ({year})  {mark}   imdb={item.imdb_id or '—'}   → {target}")

    # --- RESOLUTION --------------------------------------------------------
    out += _section("RESOLUTION")
    out.append(f"endpoint {EP_ENTITIES} · calls: {', '.join(run.resolution_call_ids) or 'none'}")
    if run.resolution_call_ids:
        res_call = run.resolution_call_ids[0]
        out.append(
            f"  resolved "
            f"{led.fmt(len(run.resolved_items), call_id=res_call, label='resolved count')}"
            f" / {led.fmt(len(run.programme), label='programme items', source=file_source)}"
            f" · unresolved "
            f"{led.fmt(len(run.unresolved_items), label='unresolved count', source=file_source)}"
        )
    else:
        out.append("  no resolution call was made")
    if run.unresolved_items:
        out.append(
            "  unresolved titles (shown, never guessed): "
            + ", ".join(item.title for item in run.unresolved_items)
        )
    if run.resolution_verdict:
        verdict = run.resolution_verdict
        out.append(
            f"  evidence: {verdict.reason_code} · sufficient={verdict.sufficient}"
            + (f" · {verdict.message}" if verdict.insufficient else "")
        )

    # --- TASTE PROFILE -----------------------------------------------------
    out += _section("TASTE PROFILE")
    if not run.taste_call_id:
        out.append("  no taste profile was requested (see EVIDENCE → findings)")
    else:
        out.append(
            f"endpoint {EP_INSIGHTS} · filter.type=urn:tag · "
            f"signal.interests.entities=<{len(run.resolved_ids)} resolved id(s)>"
        )
        out.append(f"  call: {run.taste_call_id}")
        above = sum(1 for t in run.taste_tags if (t.affinity or 0) >= evidence.BAND_HIGH)
        out.append(
            f"  scored tags: "
            f"{led.fmt(len(run.taste_tags), call_id=run.taste_call_id, label='tag count')}"
            f" · at/above High (0.6): "
            f"{led.fmt(above, call_id=run.taste_call_id, label='tags above high')}"
        )
        for tag in run.taste_tags:
            affinity = led.fmt(tag.affinity, call_id=run.taste_call_id, label=f"tag[{tag.tag_id}].affinity")
            popularity = led.fmt(
                tag.popularity, call_id=run.taste_call_id, label=f"tag[{tag.tag_id}].popularity"
            )
            out.append(
                f"  {affinity}  {tag.band.value:<10} {tag.name or tag.tag_id!s:<30}"
                f" pop={popularity}  {tag.tag_id}"
            )
        if run.taste_verdict:
            out.append(
                f"  evidence: {run.taste_verdict.reason_code} · sufficient={run.taste_verdict.sufficient}"
            )

    # --- CANDIDATE COHORTS (construction only) ----------------------------
    out += _section("CANDIDATE COHORTS (construction — scores are not shown at this stage)")
    out.append("All scoring happens once, in the RANKED COHORTS operation below. Showing scores here")
    out.append("as well would invite comparing numbers produced by different calls.")
    for domain in sorted(run.candidates_by_domain):
        call_id = run.expansion_call_ids.get(domain)
        out.append(
            f"  expanded {domain}: "
            f"{led.fmt(len(run.candidates_by_domain[domain]), call_id=call_id, label=f'candidates[{domain}]')}"
            f" candidate(s)  [call {call_id}]"
        )
    out.append("")
    out.append(
        f"cohorts constructed: "
        f"{led.fmt(len(run.cohorts), label='cohorts constructed', source='run:construction')}"
        f" across {len(run.domains_represented)} domain(s): {', '.join(run.domains_represented)}"
    )
    for index, cohort in enumerate(run.cohorts, start=1):
        membership_call = run.expansion_call_ids.get(cohort.domain)
        out.append("")
        out.append(
            f"  {index:>2}. {cohort.cohort_id}   kind={cohort.kind}   members="
            f"{led.fmt(cohort.member_count, call_id=membership_call, label=f'{cohort.cohort_id}.members')}"
        )
        out.append(f"      why grouped: {cohort.construction_reason}")
        out.append(f"      members: {_names(run, cohort.member_ids)}")
        out.append(
            f"      evidence rule: {cohort.construction_evidence.get('rule')} · call {membership_call}"
        )

    # --- RANKED COHORTS ----------------------------------------------------
    out += _section("RANKED COHORTS (one logical operation)")
    if run.ranking is None:
        out.append("  no ranking operation was performed (see EVIDENCE → findings)")
    else:
        operation_rows = run.trace_by_tool("build_and_rank_cohorts")
        op_call = run.ranking.operation_call_id
        out.append(
            f"operation: {op_call}   logical operations of this kind recorded: "
            f"{led.fmt(len(operation_rows), label='build_and_rank_cohorts rows', source='run:trace')}"
            f"  ({'PASS' if len(operation_rows) == 1 else 'FAIL'} — exactly 1 expected)"
        )
        out.append(
            f"scoring contexts: "
            f"{led.fmt(len(run.ranking.contexts), label='scoring contexts', source='run:ranking')}"
            f" · scoring calls: "
            f"{led.fmt(len(run.ranking.scoring_call_ids), label='scoring calls', source='run:ranking')}"
            f" · cohorts scored: "
            f"{led.fmt(len(run.cohorts), label='cohorts scored', source='run:ranking')}"
            f" · entities scored: "
            f"{led.fmt(run.ranking.scored_entity_count, label='entities scored', source='run:ranking')}"
        )
        out.append("rule: one scoring call per CONTEXT (entity type), never one per cohort. Numbers are")
        out.append("      comparable only inside their own context; cross-context order uses strength,")
        out.append("      novelty and member counts — never raw affinity.")
        if run.ranking.cross_context_tiebreak_used:
            out.append("  !! cross_context_tiebreak_used = True — two cohorts in different normalisation")
            out.append("     contexts tied on every safe key. Reported, not silently broken.")
        scored_ids = set(run.ranking.scoring_call_ids)
        for cohort in run.ranked:
            score = cohort.score
            call_id = score.call_id if score else None
            in_context = call_id in scored_ids
            out.append("")
            out.append(
                f"  #{cohort.rank}  {cohort.cohort_id}   "
                f"[{cohort.verdict.reason_code if cohort.verdict else '?'}]   "
                f"context={cohort.context_id}"
            )
            out.append(
                f"      mean affinity "
                f"{led.fmt(score.mean_affinity if score else None, call_id=call_id, label=f'{cohort.cohort_id}.mean_affinity')}"
                f" · novelty proxy "
                f"{led.fmt(score.novelty_proxy if score else None, call_id=call_id, label=f'{cohort.cohort_id}.novelty_proxy')}"
                f" · max "
                f"{led.fmt(score.max_affinity if score else None, call_id=call_id, label=f'{cohort.cohort_id}.max_affinity')}"
                f"   [call {call_id}{'' if in_context else ' — NOT a scoring call'}]"
            )
            out.append(f"      ordered here because: {_ordering_reason(cohort)}")
            for member in cohort.members:
                out.append(f"      {_member_line(led, cohort, member, '        ')}")
            if cohort.excluded_members:
                out.append(
                    "      flagged (still shown, never hidden): "
                    + "; ".join(f"{e.name or e.entity_id} = {e.code.value}" for e in cohort.excluded_members)
                )

    # --- REJECTED ----------------------------------------------------------
    out += _section("REJECTED")
    if not run.rejected:
        out.append("  none — every constructed candidate cohort cleared the evidence gate.")
    for cohort in run.rejected:
        rejection = cohort.rejection
        score = cohort.score
        call_id = score.call_id if score else None
        out.append(
            f"  {cohort.cohort_id}   reason={rejection.code.value if rejection else '?'}"
            f"   (evidence gate verdict: {rejection.gate_reason_code if rejection else '?'})"
        )
        out.append(f"      {rejection.detail if rejection else ''}")
        out.append(
            f"      members="
            f"{led.fmt(cohort.member_count, call_id=call_id, label=f'{cohort.cohort_id}.member_count')}"
            f" · clearing Medium (>=0.5)="
            f"{led.fmt(rejection.qualifying_members if rejection else None, call_id=call_id, label=f'{cohort.cohort_id}.qualifying')}"
            f"   [call {call_id}]"
        )
        for member in cohort.members:
            out.append(f"      {_member_line(led, cohort, member, '        ')}")
        if cohort.excluded_members:
            out.append(
                "      flagged (still shown, never hidden): "
                + "; ".join(f"{e.name or e.entity_id} = {e.code.value}" for e in cohort.excluded_members)
            )

    out += _render_orchestration(run, led)

    # --- EVIDENCE ----------------------------------------------------------
    out += _section("EVIDENCE (Qloo trace)")
    errors = sum(1 for row in run.trace_rows if row.get("error"))
    out.append(
        f"client calls made: "
        f"{led.fmt(run.calls_made, label='client calls', source='run:trace')}"
        f" (budget {MAX_PIPELINE_CALLS}) · trace rows: "
        f"{led.fmt(len(run.trace_rows), label='trace rows', source='run:trace')}"
        " (incl. 1 logical-operation row)"
        f" · rows with an error: "
        f"{led.fmt(errors, label='trace errors', source='run:trace')}"
    )
    for row in run.trace_rows:
        marker = "!" if row.get("error") else " "
        out.append(
            f"  {marker}{row['call_id']}  {row['tool']:<34} {row['endpoint']:<14}"
            f" status={row['status']} n={row['result_count']} src={row['source']}"
            f" data={row['data_status']}"
        )
        if row["tool"] == "build_and_rank_cohorts":
            for note in row.get("notes", []):
                out.append(f"       note: {note}")
    out.append("")
    out.append("findings (machine-readable codes produced by deterministic code, never by a model):")
    if not run.findings:
        out.append("  none")
    for finding in run.findings:
        out.append(f"  [{finding.code}] {finding.message}")
    out.append("")
    out.append("fixture simulation limits — what this replay does NOT prove:")
    for note in FIXTURE_SIMULATION_LIMITS:
        out.append(f"  · {note}")

    # --- STOP --------------------------------------------------------------
    out += _section("STOP")
    out.append(f"stop_reason = {run.stop_reason}")
    out.append(f"message     = {run.stop_message}")
    audit = led.audit()
    out.append("")
    out.append(
        f"PROVENANCE  numbers displayed: "
        f"{led.fmt(audit['numbers_displayed'], label='numbers displayed', source='run:ledger')}"
        f" · backed by a Qloo-call trace row: "
        f"{led.fmt(audit['qloo_call_backed'], label='qloo_call_backed', source='run:ledger')}"
        f" · fixture-file/input-derived: "
        f"{led.fmt(audit['other_backed'], label='other_backed', source='run:ledger')}"
        f" · unverified: "
        f"{led.fmt(len(audit['unverified']), label='unverified numbers', source='run:ledger')}"
    )
    problems = led.problems()
    if problems:
        out.append("  !! provenance problems:")
        out.extend(f"    - {problem}" for problem in problems)
    if run.stop_reason == STOP_INSUFFICIENCY:
        out.append("")
        out.append("  Adjacent is reporting NO recommendation. Nothing in this output should be acted on")
        out.append("  as an audience hypothesis.")
    out.append("")
    out.append(_rule())
    out.append("REMINDER: every affinity above is FIXTURE DATA until docs/API_NOTES.md records a live probe.")
    out.append(_rule())
    return "\n".join(out)


def _member_line(led: ProvenanceLedger, cohort: CandidateCohort, member: Any, indent: str) -> str:
    affinity = led.fmt(
        member.affinity, call_id=member.call_id, label=f"{cohort.cohort_id}/{member.entity_id}.affinity"
    )
    popularity = led.fmt(
        member.popularity,
        call_id=member.call_id,
        label=f"{cohort.cohort_id}/{member.entity_id}.popularity",
    )
    subtype = member.scored.subtype or "—"
    flags = []
    if member.is_marginal:
        flags.append("marginal (<0.6)")
    if any(m.entity_id == member.entity_id for m in cohort.qualifying_members):
        flags.append("counts toward the gate (>=0.5)")
    else:
        flags.append("below the gate (<0.5)")
    return (
        f"{affinity}  {member.band:<10} {member.name or member.entity_id!s:<30}"
        f" pop={popularity}  subtype={subtype:<12} {' '.join(flags)}"
    )


def _ordering_reason(cohort: CandidateCohort) -> str:
    score = cohort.score
    return (
        f"strength={cohort.verdict.reason_code if cohort.verdict else '?'} → "
        f"novelty={score.novelty_proxy if score else None} → "
        f"members clearing Medium={len(cohort.qualifying_members)}"
        "  (mean affinity is only ever a within-context tiebreaker)"
    )


def _render_orchestration(run: MilestoneRun, led: ProvenanceLedger) -> list[str]:
    """The ORCHESTRATION section, as a list of lines. Exactly what
    `render_agent_trace` prints, so the two can never drift."""
    out: list[str] = []
    # --- ORCHESTRATION -----------------------------------------------------
    out += _section("ORCHESTRATION (agent trace — separate from the Qloo trace below)")
    run_source = "run:orchestration"
    out.append(
        f"run {run.run_id} · runtime={_runtime_label(run)} · "
        f"phase={run.phase.value} · status={run.status.value}"
    )
    out.append(
        f"budget  steps "
        f"{led.fmt(run.budget.steps_used, label='steps used', source=run_source)}"
        f"/{led.fmt(run.budget.max_steps, label='max steps', source=run_source)}"
        f" · qloo calls "
        f"{led.fmt(run.budget.qloo_calls_used, label='calls used', source=run_source)}"
        f"/{led.fmt(run.budget.max_qloo_calls, label='max calls', source=run_source)}"
        f" · elapsed "
        f"{led.fmt(run.budget.elapsed_s(), decimals=3, label='elapsed seconds', source=run_source)}s"
        f"/{led.fmt(run.budget.max_wall_clock_s, label='max wall clock', source=run_source)}s"
        f" · transitions "
        f"{led.fmt(len(run.transitions), label='transition count', source=run_source)}"
    )
    out.append("  #    from     → to       action               reason")
    for transition in run.transitions:
        out.append(transition.line())
    out.append("")
    out.append("cycle: PLAN → SELECT → ACT → EVALUATE → STOP. Every line above was written by")
    out.append("deterministic code, not by a model; no state followed STOP, and no tool ran twice.")
    if run.evidence_report is not None:
        out.append("")
        out.append(f"evidence report: {run.evidence_report.summary()}")
        out.append(
            f"  ready={run.evidence_report.ready} · progress_possible="
            f"{run.evidence_report.progress_possible} · surviving cohorts="
            f"{led.fmt(run.evidence_report.surviving_cohorts, label='surviving cohorts', source=run_source)}"
            f" · rejected cohorts="
            f"{led.fmt(run.evidence_report.rejected_cohorts, label='rejected cohorts', source=run_source)}"
        )
    return out


def render_agent_trace(run: MilestoneRun) -> str:
    """Only the agent's state transitions — the `--show-agent-trace` view."""
    if run.ledger is None:  # pragma: no cover - defensive
        raise ValueError("cannot render a run without a ledger")
    return "\n".join(_render_orchestration(run, run.ledger))


def render_run_json(run: MilestoneRun) -> str:
    return run.to_json()


__all__ = [
    "FIXTURE_SIMULATION_LIMITS",
    "MAX_PIPELINE_CALLS",
    "STOP_COMPLETE",
    "STOP_ERROR",
    "STOP_INSUFFICIENCY",
    "MilestoneRun",
    "ProgrammeItem",
    "gate_status",
    "render_run_json",
    "render_run_text",
    "resolve_fixture_path",
    "run_fixture",
    "run_fixture_async",
]
