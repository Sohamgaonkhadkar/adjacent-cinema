"""Typed tools — the only things the orchestrator is allowed to do.

The orchestrator does not know what a Qloo client is, and it does not know whether
the implementation behind a tool is the fixture mock or the live client. It selects
a tool by name, executes exactly one bounded action, and reads a typed result.

Five tools exist, and no more:

    resolve_programme    /entities                     → ResolveResult
    get_taste_profile    /v2/insights?filter.type=urn:tag  → TasteResult
    expand_candidates    /v2/insights (one call per domain)  → ExpandResult
    rank_cohorts         the single build_and_rank_cohorts operation  → RankResult
    assess_evidence      pure logic over typed results  → EvidenceReport

The first four are *implementations supplied by a runtime* (`PipelineRuntime`), so
this module contains no HTTP, no fixtures and no ranking maths. That is what makes
the orchestrator independent of the client: `app.runner.FixturePipeline` implements
the runtime over the Milestone-1 step functions today, and a live runtime will
implement the same four methods later without touching the agent.

`assess_evidence` is pure and belongs here: it calls the same `app.evidence`
functions Milestone 1 used, so the gate has exactly one implementation.

Later milestones add tools (heatmap, programme bet, audiences, trends). None of
them is stubbed here — an unimplemented tool would be a lie about capability.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from .. import evidence
from .budget import Budget

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..evidence import EvidenceVerdict
    from .state import AdjacentState


# ---------------------------------------------------------------------------
# Typed tool results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolResult:
    """What every tool returns: a short, typed account of what it did.

    Deliberately a *summary*, not a copy of the response objects — those live in
    the state, with their `call_id`s. The orchestrator reads this to decide what
    to do next and records it in the orchestration trace.
    """

    tool: str
    action: str
    detail: str
    call_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "action": self.action,
            "detail": self.detail,
            "call_ids": list(self.call_ids),
        }


@dataclass(frozen=True)
class ResolveResult(ToolResult):
    resolved: int = 0
    unresolved: int = 0
    verdict: EvidenceVerdict | None = None


@dataclass(frozen=True)
class TasteResult(ToolResult):
    call_id: str | None = None
    tag_count: int = 0
    tags_above_high: int = 0
    verdict: EvidenceVerdict | None = None


@dataclass(frozen=True)
class ExpandResult(ToolResult):
    candidates: int = 0
    domains: tuple[str, ...] = ()
    failed_domains: tuple[str, ...] = ()
    per_domain: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class RankResult(ToolResult):
    operation_call_id: str | None = None
    contexts: int = 0
    cohorts_ranked: int = 0
    cohorts_rejected: int = 0
    entities_scored: int = 0


@dataclass(frozen=True)
class EvidenceReport:
    """The evidence gate's answer, over everything gathered so far."""

    gates: dict[str, bool] = field(default_factory=dict)
    resolution_verdict: EvidenceVerdict | None = None
    taste_verdict: EvidenceVerdict | None = None
    cohort_verdict: EvidenceVerdict | None = None
    surviving_cohorts: int = 0
    rejected_cohorts: int = 0
    resolved_ids: int = 0
    resolved_theme_tags: int = 0

    # -- readings ---------------------------------------------------------
    @property
    def ready(self) -> bool:
        """Every gate that ran was satisfied. This is `complete`."""
        return bool(self.gates) and all(self.gates.values())

    @property
    def progress_possible(self) -> bool:
        """Can any remaining tool still obtain evidence?

        With no resolved entity id, the taste, expansion and ranking tools would
        all no-op: the run can only refuse. This is what makes an early
        `insufficiency` stop honest rather than lazy.
        """
        return self.resolved_ids > 0 or self.resolved_theme_tags > 0

    @property
    def failing_verdict(self) -> EvidenceVerdict | None:
        """The gate closest to the decision: cohorts first, then resolution, then taste."""
        for verdict in (self.cohort_verdict, self.resolution_verdict, self.taste_verdict):
            if verdict is not None and not verdict.sufficient:
                return verdict
        return self.cohort_verdict

    @property
    def insufficient_gates(self) -> list[str]:
        return [name for name, ok in self.gates.items() if not ok]

    def summary(self) -> str:
        state = " ".join(f"{name}={'ok' if ok else 'FAIL'}" for name, ok in sorted(self.gates.items()))
        if self.ready:
            return f"all gates satisfied ({state})"
        failed = ", ".join(self.insufficient_gates) or "none"
        return f"gate(s) not satisfied: {failed} ({state})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "gates": self.gates,
            "ready": self.ready,
            "progress_possible": self.progress_possible,
            "surviving_cohorts": self.surviving_cohorts,
            "rejected_cohorts": self.rejected_cohorts,
            "resolved_ids": self.resolved_ids,
            "resolved_theme_tags": self.resolved_theme_tags,
            "resolution_verdict": self.resolution_verdict.as_dict() if self.resolution_verdict else None,
            "taste_verdict": self.taste_verdict.as_dict() if self.taste_verdict else None,
            "cohort_verdict": self.cohort_verdict.as_dict() if self.cohort_verdict else None,
            "summary": self.summary(),
        }


# ---------------------------------------------------------------------------
# The runtime the executable tools delegate to
# ---------------------------------------------------------------------------


class PipelineRuntime(Protocol):
    """The four deterministic operations, implemented outside the agent package.

    Implementations must mutate the state with their artefacts and return a typed
    summary. The agent never inspects a client, an endpoint or a fixture.
    """

    @property
    def name(self) -> str:
        """Short description of the implementation, for the trace (e.g. 'mock:portland_strong')."""
        ...

    @property
    def data_status(self) -> str:
        """'fixture' or 'measured' — travels into the orchestration trace."""
        ...

    async def resolve_programme(self, state: AdjacentState, budget: Budget) -> ResolveResult: ...

    async def get_taste_profile(self, state: AdjacentState, budget: Budget) -> TasteResult: ...

    async def expand_candidates(self, state: AdjacentState, budget: Budget) -> ExpandResult: ...

    async def rank_cohorts(self, state: AdjacentState, budget: Budget) -> RankResult: ...


# ---------------------------------------------------------------------------
# assess_evidence — pure, and the only tool the agent owns end to end
# ---------------------------------------------------------------------------


def build_evidence_report(state: AdjacentState) -> EvidenceReport:
    """Reuse the Milestone-1 gate functions over whatever exists so far.

    The three gate names are unchanged from Milestone 1 (`resolution`,
    `taste_profile`, `candidate_cohorts`) so the rendered `gate_status` block and
    every existing consumer keep their exact shape.
    """
    cohort_verdict = evidence.evaluate_cohort_set(
        [[member.scored for member in cohort.members] for cohort in state.cohorts]
    )
    gates = {
        "resolution": bool(state.resolution_verdict and state.resolution_verdict.sufficient),
        "taste_profile": bool(state.taste_verdict and state.taste_verdict.sufficient),
        "candidate_cohorts": bool(cohort_verdict.sufficient),
    }
    return EvidenceReport(
        gates=gates,
        resolution_verdict=state.resolution_verdict,
        taste_verdict=state.taste_verdict,
        cohort_verdict=cohort_verdict,
        surviving_cohorts=len(state.ranked),
        rejected_cohorts=len(state.rejected),
        resolved_ids=len(state.resolved_ids),
        resolved_theme_tags=len(state.theme_tag_ids),
    )


class AssessEvidenceTool:
    """The EVALUATE phase's tool. No I/O, no budget, deterministic."""

    name = "assess_evidence"
    description = "Apply the evidence gate to everything gathered so far and report it."

    def __init__(self, runtime: PipelineRuntime | None = None) -> None:
        self.runtime = runtime

    async def execute(self, state: AdjacentState, budget: Budget) -> EvidenceReport:
        report = build_evidence_report(state)
        state.evidence_report = report
        return report


# ---------------------------------------------------------------------------
# The five tools
# ---------------------------------------------------------------------------


class ResolveProgrammeTool:
    name = "resolve_programme"
    description = "Resolve the programme's titles to Qloo entity ids via /entities."

    def __init__(self, runtime: PipelineRuntime) -> None:
        self.runtime = runtime

    async def execute(self, state: AdjacentState, budget: Budget) -> ResolveResult:
        return await self.runtime.resolve_programme(state, budget)


class TasteProfileTool:
    name = "get_taste_profile"
    description = "Characterise the programme's taste with tags scored from one context."

    def __init__(self, runtime: PipelineRuntime) -> None:
        self.runtime = runtime

    async def execute(self, state: AdjacentState, budget: Budget) -> TasteResult:
        return await self.runtime.get_taste_profile(state, budget)


class ExpandCandidatesTool:
    name = "expand_candidates"
    description = "Ask Qloo for adjacent entities per domain, one call per domain."

    def __init__(self, runtime: PipelineRuntime) -> None:
        self.runtime = runtime

    async def execute(self, state: AdjacentState, budget: Budget) -> ExpandResult:
        return await self.runtime.expand_candidates(state, budget)


class RankCohortsTool:
    name = "rank_cohorts"
    description = "Construct candidate cohorts and rank them in one normalisation context per entity type."

    def __init__(self, runtime: PipelineRuntime) -> None:
        self.runtime = runtime

    async def execute(self, state: AdjacentState, budget: Budget) -> RankResult:
        return await self.runtime.rank_cohorts(state, budget)


class Tool:
    """The minimal contract every tool satisfies."""

    name: str
    description: str

    async def execute(self, state: AdjacentState, budget: Budget) -> ToolResult:
        raise NotImplementedError


def default_tools(runtime: PipelineRuntime) -> dict[str, Any]:
    """The tool set for this milestone: four runtime-backed, one pure."""
    tools: Sequence[Any] = (
        ResolveProgrammeTool(runtime),
        TasteProfileTool(runtime),
        ExpandCandidatesTool(runtime),
        RankCohortsTool(runtime),
        AssessEvidenceTool(runtime),
    )
    return {tool.name: tool for tool in tools}
