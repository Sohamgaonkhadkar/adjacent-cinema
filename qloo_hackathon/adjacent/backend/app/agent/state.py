"""The agent's typed state — everything that must survive between states.

`AdjacentState` is the **single** record of a run. It carries the Milestone-1
artefacts (programme, resolution, taste profile, candidates, cohorts, ranking,
findings, Qloo trace) and the control state the agent adds (phase, status, budget,
orchestration transitions, evidence report, stop decision).

Why one object and not two: a separate "agent state" mirroring the run artefacts
would give us two records of the same facts to keep in sync — exactly the failure
the provenance ledger exists to prevent. The state does not copy Qloo response
objects either; it holds the parsed results and the `call_id` that produced them.

Field groups, in order:

* **input** — what the venue supplied, plus the fixture identity it came from
* **artefacts** — filled in by the tools, state by state
* **control** — phase, status, budget, transitions, evidence report, stop decision

The Milestone-1 name for this object (`MilestoneRun`) is kept as an alias in
`app.runner`, which is where the rendering and the CLI meet it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from .budget import Budget

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..domain.cohorts import CandidateCohort
    from ..domain.ledger import ProvenanceLedger
    from ..domain.scoring import RankingResult
    from ..evidence import EvidenceVerdict
    from ..qloo.models import ScoredEntity
    from .stop import StopDecision
    from .tools import EvidenceReport


# ---------------------------------------------------------------------------
# Phases and transitions
# ---------------------------------------------------------------------------


class Phase(StrEnum):
    """The agent's states, in the order the plan can reach them.

    INIT → PLAN are always traversed. RESOLVE / ANALYSE / EXPAND / RANK are the
    acting phases; EVALUATE follows each of them; STOP is the only terminal
    phase other than ERROR. The orchestrator never jumps from INIT to output.
    """

    INIT = "INIT"
    PLAN = "PLAN"
    RESOLVE = "RESOLVE"
    ANALYSE = "ANALYSE"
    EXPAND = "EXPAND"
    RANK = "RANK"
    EVALUATE = "EVALUATE"
    STOP = "STOP"
    ERROR = "ERROR"


class RunStatus(StrEnum):
    RUNNING = "running"
    FINISHED = "finished"


#: The acting phases, in plan order. Each maps to exactly one tool.
ACT_PHASES: tuple[Phase, ...] = (Phase.RESOLVE, Phase.ANALYSE, Phase.EXPAND, Phase.RANK)


@dataclass(frozen=True)
class Transition:
    """One state transition. The orchestration trace is a list of these."""

    order: int
    step: int
    from_state: str
    to_state: str
    action: str
    reason: str
    at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "step": self.step,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "action": self.action,
            "reason": self.reason,
            "at": self.at,
        }

    def line(self) -> str:
        """One readable transition row. `step` (the agent step count when the
        transition was recorded) stays in the JSON export; the printed number is
        the transition order, which is what a reader follows."""
        return f"  {self.order:>3}  {self.from_state:<8} → {self.to_state:<8} {self.action:<20} {self.reason}"


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


# ---------------------------------------------------------------------------
# Run artefacts
# ---------------------------------------------------------------------------


@dataclass
class ProgrammeItem:
    """One programme item: what the venue supplied, and what Qloo returned for it."""

    title: str
    year: int | None
    imdb_id: str | None
    declared_entity_id: str | None
    resolved_entity_id: str | None = None
    resolved_name: str | None = None
    entity_type: str | None = None
    subtype: str | None = None
    popularity: float | None = None
    source_call_id: str | None = None
    # Sanitized identity-verification details returned by EntityResolver.
    # This deliberately excludes the raw Qloo response body.
    resolution_evidence: dict[str, Any] | None = None

    @property
    def resolved(self) -> bool:
        return self.resolved_entity_id is not None

    @property
    def identifiers(self) -> list[str]:
        return [value for value in (self.declared_entity_id, self.imdb_id) if value]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "year": self.year,
            "imdb_id": self.imdb_id,
            "declared_entity_id": self.declared_entity_id,
            "resolved_entity_id": self.resolved_entity_id,
            "resolved_name": self.resolved_name,
            "entity_type": self.entity_type,
            "subtype": self.subtype,
            "popularity": self.popularity,
            "resolved": self.resolved,
            "source_call_id": self.source_call_id,
            "resolution_evidence": self.resolution_evidence,
        }


@dataclass
class Finding:
    """An insufficiency or an operational note, with its machine-readable code."""

    code: str
    message: str
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "stats": self.stats}


@dataclass
class AdjacentState:
    """The state of one run: input, artefacts, and agent control state."""

    # -- identity / input ------------------------------------------------
    run_id: str = "local"
    fixture_name: str = ""
    fixture_path: str = ""
    scenario: str = ""
    fixture_notice: str = ""
    description: str = ""
    data_status: str = "fixture"
    programme: list[ProgrammeItem] = field(default_factory=list)
    # Creator theme strings are resolved as Qloo tag inputs, never as film titles.
    theme_queries: list[str] = field(default_factory=list)
    theme_resolution: list[dict[str, Any]] = field(default_factory=list)
    theme_tag_ids: list[str] = field(default_factory=list)

    # -- artefacts (filled by the tools) ---------------------------------
    resolution_call_ids: list[str] = field(default_factory=list)
    resolution_verdict: EvidenceVerdict | None = None
    taste_tags: list[Any] = field(default_factory=list)
    taste_call_id: str | None = None
    taste_verdict: EvidenceVerdict | None = None
    candidates_by_domain: dict[str, list[ScoredEntity]] = field(default_factory=dict)
    expansion_call_ids: dict[str, str] = field(default_factory=dict)
    domain_selection: Any | None = None  # M11: DomainSelectionResult
    cohorts: list[CandidateCohort] = field(default_factory=list)
    ranking: RankingResult | None = None
    ranked: list[CandidateCohort] = field(default_factory=list)
    rejected: list[CandidateCohort] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    ledger: ProvenanceLedger | None = None

    # -- agent control state ---------------------------------------------
    phase: Phase = Phase.INIT
    status: RunStatus = RunStatus.RUNNING
    budget: Budget = field(default_factory=Budget)
    transitions: list[Transition] = field(default_factory=list)
    completed: set[str] = field(default_factory=set)
    evidence_report: EvidenceReport | None = None
    stop: StopDecision | None = None
    rendered_text: str = ""

    # -- derived views ----------------------------------------------------
    @property
    def resolved_items(self) -> list[ProgrammeItem]:
        return [p for p in self.programme if p.resolved]

    @property
    def unresolved_items(self) -> list[ProgrammeItem]:
        return [p for p in self.programme if not p.resolved]

    @property
    def resolved_ids(self) -> list[str]:
        return [p.resolved_entity_id for p in self.programme if p.resolved_entity_id]

    @property
    def has_seed_signals(self) -> bool:
        """Whether a verified film entity or exact Qloo tag has been resolved."""
        return bool(self.resolved_ids or self.theme_tag_ids)

    @property
    def domains_represented(self) -> list[str]:
        return sorted({c.domain for c in self.cohorts})

    @property
    def calls_made(self) -> int:
        """Qloo calls made in this run — read from the budget, never tracked twice."""
        return self.budget.qloo_calls_used

    @property
    def steps_used(self) -> int:
        return self.budget.steps_used

    @property
    def stop_reason(self) -> str:
        """The canonical stop reason. `error` until a decision is made."""
        return self.stop.reason.value if self.stop is not None else "error"

    @property
    def stop_message(self) -> str:
        return self.stop.message if self.stop is not None else ""

    @property
    def finished(self) -> bool:
        return self.status is RunStatus.FINISHED

    def budget_report(self) -> dict[str, Any]:
        """The budget state *with* the phase it was spent in.

        The phase lives here, not inside `Budget`: putting a copy in both places
        would create two answers to "where is this run?", which is the class of bug
        the provenance ledger exists to prevent.
        """
        return {
            "phase": self.phase.value,
            "status": self.status.value,
            **self.budget.snapshot(),
        }

    @property
    def trace_rows(self) -> list[dict[str, Any]]:
        """The Qloo trace, in start order. The orchestration trace is separate."""
        if self.ledger is None:
            return []
        rows = sorted(self.ledger.recorder.rows, key=lambda row: (row.started_at, row.seq))
        return [row.model_dump() for row in rows]

    def trace_by_tool(self, tool: str) -> list[dict[str, Any]]:
        return [r for r in self.trace_rows if r["tool"] == tool]

    def record_transition(
        self,
        *,
        from_state: Phase,
        to_state: Phase,
        action: str,
        reason: str,
        at: str | None = None,
    ) -> Transition:
        transition = Transition(
            order=len(self.transitions) + 1,
            step=self.budget.steps_used,
            from_state=from_state.value,
            to_state=to_state.value,
            action=action,
            reason=reason,
            at=at or utc_now_iso(),
        )
        self.transitions.append(transition)
        return transition

    # -- serialisation ----------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture": self.fixture_name,
            "fixture_path": self.fixture_path,
            "scenario": self.scenario,
            "description": self.description,
            "data_status": self.data_status,
            "fixture_notice": self.fixture_notice,
            "stop_reason": self.stop_reason,
            "stop_message": self.stop_message,
            "calls_made": self.calls_made,
            "programme": [p.to_dict() for p in self.programme],
            "theme_inputs": {
                "queries": list(self.theme_queries),
                "resolved": list(self.theme_resolution),
                "tag_ids": list(self.theme_tag_ids),
            },
            "resolution": {
                "resolved": len(self.resolved_items),
                "unresolved": len(self.unresolved_items),
                "call_ids": self.resolution_call_ids,
                "verdict": self.resolution_verdict.as_dict() if self.resolution_verdict else None,
            },
            "taste_profile": {
                "call_id": self.taste_call_id,
                "tags": [
                    {
                        "tag_id": t.tag_id,
                        "name": t.name,
                        "affinity": t.affinity,
                        "band": t.band.value,
                        "popularity": t.popularity,
                    }
                    for t in self.taste_tags
                ],
                "verdict": self.taste_verdict.as_dict() if self.taste_verdict else None,
            },
            "expansion": {
                domain: {"count": len(entities), "call_id": self.expansion_call_ids.get(domain)}
                for domain, entities in self.candidates_by_domain.items()
            },
            "candidate_cohorts": [c.to_dict() for c in self.cohorts],
            "ranking_operation": {
                "operation_call_id": self.ranking.operation_call_id if self.ranking else None,
                "scoring_call_ids": self.ranking.scoring_call_ids if self.ranking else [],
                "contexts": [c.to_dict() for c in self.ranking.contexts] if self.ranking else [],
                "cross_context_tiebreak_used": (
                    self.ranking.cross_context_tiebreak_used if self.ranking else None
                ),
                "unscored_member_ids": self.ranking.unscored_member_ids if self.ranking else [],
                "ordering": self.ranking.ordering if self.ranking else [],
            },
            "ranked_cohorts": [c.to_dict() for c in self.ranked],
            "rejected": [c.rejection.to_dict() for c in self.rejected if c.rejection],
            "gate_status": self.evidence_report.gates if self.evidence_report else {},
            "findings": [f.to_dict() for f in self.findings],
            "ledger_audit": self.ledger.audit() if self.ledger else None,
            "stop": self.stop.to_dict() if self.stop else None,
            "orchestration": {
                "run_id": self.run_id,
                "phase": self.phase.value,
                "status": self.status.value,
                "completed_actions": sorted(self.completed),
                "budget": self.budget_report(),
                "transitions": [t.to_dict() for t in self.transitions],
            },
            "trace": self.trace_rows,
        }

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2, default=str)
