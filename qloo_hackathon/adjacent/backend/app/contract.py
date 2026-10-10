"""The product result contract — the typed payload every consumer reads.

Why this module exists: the agent's `AdjacentState` is an *internal* working record.
It carries helpers, mutable lists and a live client reference; it is the wrong thing
to freeze as an API for a frontend, a CLI export or a future test harness. This
module is the frozen, serialisable view of a completed run.

Design rules, in order of importance:

1. **Nothing here is invented.** Every field is derived from an artefact the
   pipeline already produces (a resolved entity, a tag affinity, a cohort, a
   trace row, a verdict). If the pipeline does not produce it, it is not here.
2. **Every number keeps its `call_id`.** Provenance is not a rendering concern;
   it travels in the payload, so a consumer that displays a score can point at the
   Qloo response behind it without a second lookup.
3. **Absent is explicit.** Features that are not built yet (geography, the
   programme hypothesis) are `None` *and* named in `not_yet_available`, so a
   consumer can never mistake "not built yet" for "no evidence found" — those are
   different states and the product's whole honesty story depends on keeping them
   apart.
4. **The stop reason is the canonical one.** `StopReason` is imported from
   `app.agent.stop`, not redeclared: a second vocabulary would eventually disagree
   with the first.

Names deliberately mirror the domain layer where the concept is the same
(`CandidateCohort`, `RankingResult`). They are view models: `domain.cohorts.CandidateCohort`
is the in-process object, `contract.CandidateCohort` is its wire form.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .agent.state import AdjacentState
from .agent.stop import StopReason

#: Bumped when a consumer would have to change to read the payload. A frontend can
#: then refuse a payload it does not understand instead of half-rendering it.
SCHEMA_VERSION = "1.0.0"

#: Features the product specifies but this milestone does not implement. Named
#: explicitly so their absence in the payload is never read as an evidence outcome.
NOT_YET_AVAILABLE: tuple[str, ...] = ("geography", "programme_hypothesis")


class ContractModel(BaseModel):
    """Base for every contract model: strict about unknown fields, JSON-ready."""

    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------------------
# Provenance-carrying primitives
# ---------------------------------------------------------------------------


class Verdict(ContractModel):
    """An `app.evidence` verdict, as the gate produced it. Codes are never rewritten."""

    sufficient: bool
    reason_code: str
    message: str = ""
    stats: dict[str, Any] = Field(default_factory=dict)


class EvidenceRef(ContractModel):
    """A number and the Qloo call that produced it."""

    call_id: str
    endpoint: str | None = None
    data_status: Literal["measured", "fixture"]


# ---------------------------------------------------------------------------
# 1. Programme profile
# ---------------------------------------------------------------------------


class ProgrammeItemView(ContractModel):
    """One supplied programme item and what resolution did with it."""

    title: str
    year: int | None = None
    imdb_id: str | None = None
    declared_entity_id: str | None = None
    resolved: bool
    resolved_entity_id: str | None = None
    resolved_name: str | None = None
    entity_type: str | None = None
    subtype: str | None = None
    popularity: float | None = None
    source_call_id: str | None = None


class TasteSignal(ContractModel):
    """One tag Qloo scored for the programme, with its band and its call."""

    tag_id: str
    name: str | None = None
    affinity: float | None = None
    band: str
    popularity: float | None = None
    call_id: str


class ProgrammeProfile(ContractModel):
    """Section 1 + 2 of the product result: what was programmed, and what it tastes like."""

    items: list[ProgrammeItemView] = Field(default_factory=list)
    resolved_count: int = 0
    unresolved_count: int = 0
    resolution_verdict: Verdict | None = None
    taste_profile: list[TasteSignal] = Field(default_factory=list)
    taste_verdict: Verdict | None = None
    taste_call_id: str | None = None
    expansion: dict[str, int] = Field(default_factory=dict)  # domain → candidate count
    expansion_call_ids: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 3. Candidate cohorts + 4. ranking/evidence + 5. rejections
# ---------------------------------------------------------------------------


class CohortMemberView(ContractModel):
    entity_id: str
    name: str | None = None
    subtype: str | None = None
    affinity: float | None = None
    band: str
    popularity: float | None = None
    is_marginal: bool = False
    call_id: str


class ExcludedMemberView(ContractModel):
    """An entity that must not be used as a signature, and why. Flagged, never hidden."""

    entity_id: str
    name: str | None = None
    reason_code: str
    affinity: float | None = None


class ScoreView(ContractModel):
    """A cohort's numbers, all from ONE scoring context."""

    context_id: str
    call_id: str
    mean_affinity: float | None = None
    max_affinity: float | None = None
    min_affinity: float | None = None
    median_popularity: float | None = None
    novelty_proxy: float | None = None
    qualifying_members: int = 0
    total_members: int = 0
    partial: bool = False


class RejectionView(ContractModel):
    """The machine-readable reason a cohort was refused."""

    reason_code: str
    detail: str
    gate_reason_code: str | None = None
    gate_message: str = ""
    member_count: int = 0
    qualifying_members: int = 0
    stats: dict[str, Any] = Field(default_factory=dict)


class CohortEvidence(ContractModel):
    """The evidence attached to a cohort: gate verdict, scores, rejection."""

    verdict: Verdict | None = None
    score: ScoreView | None = None
    rejection: RejectionView | None = None


class CandidateCohort(ContractModel):
    """A candidate cohort, its construction record, its members and its evidence."""

    cohort_id: str
    domain: str
    kind: str
    member_count: int = 0
    construction_reason: str = ""
    construction_evidence: dict[str, Any] = Field(default_factory=dict)
    source_call_ids: list[str] = Field(default_factory=list)
    context_id: str | None = None
    members: list[CohortMemberView] = Field(default_factory=list)
    excluded_members: list[ExcludedMemberView] = Field(default_factory=list)
    unscored_member_ids: list[str] = Field(default_factory=list)
    evidence: CohortEvidence = Field(default_factory=CohortEvidence)
    rank: int | None = None
    #: True when the cohort is in the rejected list rather than the ranked list.
    rejected: bool = False


class ScoringContextView(ContractModel):
    """One entity type, scored in one call. The unit of comparability."""

    context_id: str
    domain: str
    call_id: str
    requested: int = 0
    returned: int = 0
    data_status: Literal["measured", "fixture"]


class RankingResult(ContractModel):
    """The single `build_and_rank_cohorts` operation, as a consumer sees it.

    Cohorts themselves live at the top level; this carries the operation's identity,
    the contexts it used and the ordering it produced, so a consumer can verify that
    scores were never compared across normalisations.
    """

    operation_call_id: str | None = None
    scoring_call_ids: list[str] = Field(default_factory=list)
    contexts: list[ScoringContextView] = Field(default_factory=list)
    scored_entity_count: int = 0
    cross_context_tiebreak_used: bool = False
    ranked_cohort_ids: list[str] = Field(default_factory=list)
    rejected_cohort_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 6. Geography (future stage — modelled, never populated yet)
# ---------------------------------------------------------------------------


class HeatmapCellView(ContractModel):
    """One heatmap cell, with the call that produced it."""

    lat: float | None = None
    lng: float | None = None
    geohash: str | None = None
    affinity: float | None = None
    band: str | None = None
    popularity: float | None = None
    call_id: str


class GeographicEvidence(ContractModel):
    """RESERVED: the geography stage is not implemented.

    The shape is declared because the product specification fixes it (locality
    echo, scored cells, an evidence gate that can refuse to draw a map). It is
    never constructed in this milestone, and no live heatmap behaviour has been
    observed — so nothing here may be presented as validated.
    """

    status: Literal["not_implemented"] = "not_implemented"
    city_query: str | None = None
    locality_echo: str | None = None
    cells: list[HeatmapCellView] = Field(default_factory=list)
    verdict: Verdict | None = None


# ---------------------------------------------------------------------------
# 7. Programme hypothesis (future stage — modelled, never populated yet)
# ---------------------------------------------------------------------------


class ProgrammeHypothesis(ContractModel):
    """RESERVED: the programme bet / test card stage is not implemented.

    Declared because the specification fixes what the decision must contain: one
    recommended cohort, the runner-up it beat, the metric a venue would measure and
    the condition that would falsify it. No recommendation is generated in this
    milestone.
    """

    status: Literal["not_implemented"] = "not_implemented"
    primary_cohort_id: str | None = None
    runner_up_cohort_id: str | None = None
    metric_name: str | None = None
    falsification_condition: str | None = None


# ---------------------------------------------------------------------------
# 8. Provenance
# ---------------------------------------------------------------------------


class ProvenanceAudit(ContractModel):
    """The provenance ledger's own audit: how many displayed numbers are backed."""

    numbers_displayed: int = 0
    qloo_call_backed: int = 0
    fixture_file_backed: int = 0
    run_internal: int = 0
    other_backed: int = 0
    distinct_call_ids: int = 0
    trace_rows_available: int = 0
    unverified: list[dict[str, Any]] = Field(default_factory=list)
    problems: list[str] = Field(default_factory=list)
    data_status: Literal["measured", "fixture"] = "fixture"


# ---------------------------------------------------------------------------
# 9. Agent trace + Qloo trace (separate records, deliberately)
# ---------------------------------------------------------------------------


class TransitionView(ContractModel):
    order: int
    step: int
    from_state: str
    to_state: str
    action: str
    reason: str
    at: str


class BudgetView(ContractModel):
    max_steps: int
    steps_used: int
    remaining_steps: int
    max_qloo_calls: int
    qloo_calls_used: int
    remaining_calls: int
    max_wall_clock_s: float
    elapsed_s: float
    exhausted: bool
    detail_code: str | None = None


class AgentTrace(ContractModel):
    """The orchestration record: states, transitions, budget. Not a Qloo trace."""

    run_id: str
    phase: str
    status: str
    completed_actions: list[str] = Field(default_factory=list)
    budget: BudgetView | None = None
    transitions: list[TransitionView] = Field(default_factory=list)


class QlooTraceRow(ContractModel):
    """One Qloo call, exactly as the recorder stored it (params already redacted)."""

    call_id: str
    seq: int = 0
    tool: str
    endpoint: str
    method: str = "GET"
    params: dict[str, Any] = Field(default_factory=dict)
    started_at: str
    duration_ms: int = 0
    status: int | None = None
    result_count: int | None = None
    cache: str = "bypass"
    source: str
    data_status: Literal["measured", "fixture"]
    attempt: int = 1
    backfill_detected: bool = False
    error: dict[str, Any] | None = None
    notes: list[str] = Field(default_factory=list)


class QlooTrace(ContractModel):
    rows: list[QlooTraceRow] = Field(default_factory=list)
    row_count: int = 0
    call_count: int = 0
    error_count: int = 0
    sources: list[str] = Field(default_factory=list)
    data_statuses: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 10. Stop reason
# ---------------------------------------------------------------------------


class StopSummary(ContractModel):
    """Why the run ended. `reason` uses the canonical vocabulary from agent.stop."""

    reason: StopReason
    ok: bool
    refuses_recommendation: bool
    message: str
    detail_code: str | None = None
    findings: list[str] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


class RunMeta(ContractModel):
    run_id: str
    scenario: str
    fixture_name: str = ""
    description: str = ""
    #: "mock" when the run was driven by MockQlooClient, "live" when it talked to Qloo.
    mode: Literal["live", "mock"]
    data_status: Literal["measured", "fixture"]
    schema_version: str = SCHEMA_VERSION
    generated_at_utc: str
    calls_made: int = 0
    steps_used: int = 0
    notices: list[str] = Field(default_factory=list)


class AnalysisRun(ContractModel):
    """The complete, frozen result of one analysis run."""

    meta: RunMeta
    stop: StopSummary
    programme: ProgrammeProfile
    candidate_cohorts: list[CandidateCohort] = Field(default_factory=list)
    ranking: RankingResult | None = None
    #: Future stages. `None` here means "not built yet" — see `not_yet_available`.
    geography: GeographicEvidence | None = None
    programme_hypothesis: ProgrammeHypothesis | None = None
    not_yet_available: list[str] = Field(default_factory=lambda: list(NOT_YET_AVAILABLE))
    provenance: ProvenanceAudit
    agent_trace: AgentTrace
    qloo_trace: QlooTrace


# ---------------------------------------------------------------------------
# Builder — state → contract. Pure, no I/O.
# ---------------------------------------------------------------------------


def _verdict(verdict: Any | None) -> Verdict | None:
    if verdict is None:
        return None
    return Verdict(
        sufficient=bool(verdict.sufficient),
        reason_code=str(verdict.reason_code),
        message=str(verdict.message or ""),
        stats=dict(verdict.stats or {}),
    )


def _tag(tag: Any, call_id: str) -> TasteSignal:
    return TasteSignal(
        tag_id=str(tag.tag_id),
        name=tag.name,
        affinity=tag.affinity,
        band=tag.band.value,
        popularity=tag.popularity,
        call_id=call_id,
    )


def _member(member: Any) -> CohortMemberView:
    return CohortMemberView(
        entity_id=member.entity_id,
        name=member.name,
        subtype=member.scored.subtype,
        affinity=member.affinity,
        band=member.band,
        popularity=member.popularity,
        is_marginal=bool(member.is_marginal),
        call_id=member.call_id,
    )


def _score(score: Any | None) -> ScoreView | None:
    if score is None:
        return None
    return ScoreView(
        context_id=score.context_id,
        call_id=score.call_id,
        mean_affinity=score.mean_affinity,
        max_affinity=score.max_affinity,
        min_affinity=score.min_affinity,
        median_popularity=score.median_popularity,
        novelty_proxy=score.novelty_proxy,
        qualifying_members=score.qualifying_members,
        total_members=score.total_members,
        partial=bool(score.partial),
    )


def _rejection(rejection: Any | None) -> RejectionView | None:
    if rejection is None:
        return None
    return RejectionView(
        reason_code=rejection.code.value,
        detail=rejection.detail,
        gate_reason_code=rejection.gate_reason_code,
        gate_message=rejection.gate_message or "",
        member_count=rejection.member_count,
        qualifying_members=rejection.qualifying_members,
        stats=dict(rejection.stats or {}),
    )


def _cohort(cohort: Any) -> CandidateCohort:
    return CandidateCohort(
        cohort_id=cohort.cohort_id,
        domain=cohort.domain,
        kind=cohort.kind,
        member_count=cohort.member_count,
        construction_reason=cohort.construction_reason,
        construction_evidence=dict(cohort.construction_evidence or {}),
        source_call_ids=list(cohort.source_call_ids),
        context_id=cohort.context_id,
        members=[_member(m) for m in cohort.members],
        excluded_members=[
            ExcludedMemberView(
                entity_id=e.entity_id,
                name=e.name,
                reason_code=e.code.value,
                affinity=e.affinity,
            )
            for e in cohort.excluded_members
        ],
        unscored_member_ids=list(cohort.unscored_member_ids),
        evidence=CohortEvidence(
            verdict=_verdict(cohort.verdict),
            score=_score(cohort.score),
            rejection=_rejection(cohort.rejection),
        ),
        rank=cohort.rank,
        rejected=bool(cohort.rejected),
    )


def build_analysis_run(state: AdjacentState) -> AnalysisRun:
    """Freeze a completed (or refused) run into the product result contract."""
    if state.ledger is None:  # pragma: no cover - defensive
        raise ValueError("cannot build a contract from a run without a ledger")
    if state.stop is None:
        # A contract for a run that never reached STOP would have to invent a reason.
        raise ValueError("cannot build a contract before the run has stopped")

    data_status = "fixture" if state.data_status == "fixture" else "measured"
    ledger_audit = state.ledger.audit()
    qloo_rows = state.trace_rows

    programme = ProgrammeProfile(
        items=[
            ProgrammeItemView(
                title=item.title,
                year=item.year,
                imdb_id=item.imdb_id,
                declared_entity_id=item.declared_entity_id,
                resolved=item.resolved,
                resolved_entity_id=item.resolved_entity_id,
                resolved_name=item.resolved_name,
                entity_type=item.entity_type,
                subtype=item.subtype,
                popularity=item.popularity,
                source_call_id=item.source_call_id,
            )
            for item in state.programme
        ],
        resolved_count=len(state.resolved_items),
        unresolved_count=len(state.unresolved_items),
        resolution_verdict=_verdict(state.resolution_verdict),
        taste_profile=(
            [_tag(tag, state.taste_call_id) for tag in state.taste_tags]
            if state.taste_call_id
            else []
        ),
        taste_verdict=_verdict(state.taste_verdict),
        taste_call_id=state.taste_call_id,
        expansion={domain: len(entities) for domain, entities in state.candidates_by_domain.items()},
        expansion_call_ids=dict(state.expansion_call_ids),
    )

    ranking = None
    if state.ranking is not None:
        ranking = RankingResult(
            operation_call_id=state.ranking.operation_call_id or None,
            scoring_call_ids=list(state.ranking.scoring_call_ids),
            contexts=[
                ScoringContextView(
                    context_id=context.context_id,
                    domain=context.domain,
                    call_id=context.call_id,
                    requested=len(context.requested_ids),
                    returned=len(context.scored),
                    data_status=context.data_status,
                )
                for context in state.ranking.contexts
            ],
            scored_entity_count=state.ranking.scored_entity_count,
            cross_context_tiebreak_used=bool(state.ranking.cross_context_tiebreak_used),
            ranked_cohort_ids=[c.cohort_id for c in state.ranked],
            rejected_cohort_ids=[c.cohort_id for c in state.rejected],
        )

    return AnalysisRun(
        meta=RunMeta(
            run_id=state.run_id,
            scenario=state.scenario,
            fixture_name=state.fixture_name,
            description=state.description,
            mode="mock" if data_status == "fixture" else "live",
            data_status=data_status,
            generated_at_utc=datetime.now(tz=UTC).isoformat(),
            calls_made=state.calls_made,
            steps_used=state.steps_used,
            notices=[state.fixture_notice] if state.fixture_notice else [],
        ),
        stop=StopSummary(
            reason=state.stop.reason,
            ok=state.stop.ok,
            refuses_recommendation=state.stop.refuses_recommendation,
            message=state.stop.message,
            detail_code=state.stop.detail_code,
            findings=list(state.stop.findings),
            stats=dict(state.stop.stats),
        ),
        programme=programme,
        candidate_cohorts=[_cohort(c) for c in state.cohorts],
        ranking=ranking,
        geography=None,
        programme_hypothesis=None,
        not_yet_available=list(NOT_YET_AVAILABLE),
        provenance=ProvenanceAudit(
            numbers_displayed=ledger_audit["numbers_displayed"],
            qloo_call_backed=ledger_audit["qloo_call_backed"],
            fixture_file_backed=ledger_audit["fixture_file_backed"],
            run_internal=ledger_audit["run_internal"],
            other_backed=ledger_audit["other_backed"],
            distinct_call_ids=ledger_audit["distinct_call_ids"],
            trace_rows_available=ledger_audit["trace_rows_available"],
            unverified=list(ledger_audit["unverified"]),
            problems=state.ledger.problems(),
            data_status=ledger_audit["data_status"],
        ),
        agent_trace=AgentTrace(
            run_id=state.run_id,
            phase=state.phase.value,
            status=state.status.value,
            completed_actions=sorted(state.completed),
            budget=BudgetView(**state.budget_report()),
            transitions=[
                TransitionView(
                    order=t.order,
                    step=t.step,
                    from_state=t.from_state,
                    to_state=t.to_state,
                    action=t.action,
                    reason=t.reason,
                    at=t.at,
                )
                for t in state.transitions
            ],
        ),
        qloo_trace=QlooTrace(
            rows=[QlooTraceRow(**{**row, "cache": str(row.get("cache", "bypass"))}) for row in qloo_rows],
            row_count=len(qloo_rows),
            call_count=state.calls_made,
            error_count=sum(1 for row in qloo_rows if row.get("error")),
            sources=sorted({str(row["source"]) for row in qloo_rows}),
            data_statuses=sorted({str(row["data_status"]) for row in qloo_rows}),
        ),
    )


def build_analysis_run_json(state: AdjacentState, *, indent: int = 2) -> str:
    """The contract as JSON text — the exact bytes a frontend would receive."""
    return build_analysis_run(state).model_dump_json(indent=indent)


def traceable_call_ids(contract: AnalysisRun) -> set[str]:
    """Every call id the contract references, from any section.

    Used by the contract tests to prove that no affinity, popularity or tag value
    can reach a consumer without the Qloo response behind it being in the payload.
    """
    ids: set[str] = set()
    ids |= {row.call_id for row in contract.qloo_trace.rows}
    if contract.ranking is not None:
        ids |= set(contract.ranking.scoring_call_ids)
        if contract.ranking.operation_call_id:
            ids.add(contract.ranking.operation_call_id)
    return ids


__all__ = [
    "NOT_YET_AVAILABLE",
    "SCHEMA_VERSION",
    "AgentTrace",
    "AnalysisRun",
    "BudgetView",
    "CandidateCohort",
    "CohortEvidence",
    "CohortMemberView",
    "ExcludedMemberView",
    "GeographicEvidence",
    "HeatmapCellView",
    "ProgrammeHypothesis",
    "ProgrammeProfile",
    "ProvenanceAudit",
    "QlooTrace",
    "QlooTraceRow",
    "RankingResult",
    "RejectionView",
    "RunMeta",
    "ScoreView",
    "ScoringContextView",
    "StopReason",
    "StopSummary",
    "TasteSignal",
    "TransitionView",
    "Verdict",
    "build_analysis_run",
    "build_analysis_run_json",
    "traceable_call_ids",
]
