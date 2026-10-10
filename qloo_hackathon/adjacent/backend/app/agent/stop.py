"""Canonical stop reasons — one definition, one vocabulary.

Milestone 1 ended a run in one of three states (`complete`, `insufficiency`,
`error`). Milestone 2 adds the two the plan promised and a wall-clock ceiling:

    complete          evidence supports the output; a cohort cleared the gate
    insufficiency     the evidence genuinely does not support an answer
    budget_exhausted  the run ran out of steps, calls or wall clock
    invalid_input     the programme cannot be worked with at all
    error             a tool or transport failure — NOT a data outcome
    timeout           the wall-clock ceiling (a detail of budget_exhausted, kept
                      separate because the plan names it separately in R8)

The distinction between `insufficiency` and `error` is the one that will matter in
the live product: "Qloo has nothing on this programme" is a finding, "Qloo returned
a 500" is a fault. They must never be reported as each other.

Every refusal sentence lives here or in `app/evidence.py`:

* the insufficiency sentences are the Milestone-1 ones, imported and copied
  nowhere — including the exact product sentence
  "I do not have enough Qloo evidence to name an adjacent audience for this programme."
* the budget sentences come from `agent/budget.py` (they are the plan's wording)
* invalid input and timeout get one sentence each, here, because no existing
  module owned them.

`decide_stop()` is the Milestone-1 terminal decision, moved into the agent instead
of being reimplemented: a run is `complete` only when every gate that ran was
satisfied, and otherwise the refusal comes from the gate closest to the decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from .. import evidence
from ..qloo.errors import QlooError
from .budget import BudgetExhausted

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .state import AdjacentState
    from .tools import EvidenceReport


class StopReason(StrEnum):
    """The canonical set. Nothing else may end a run."""

    COMPLETE = "complete"
    INSUFFICIENCY = "insufficiency"
    BUDGET_EXHAUSTED = "budget_exhausted"
    INVALID_INPUT = "invalid_input"
    ERROR = "error"
    TIMEOUT = "timeout"

    @property
    def ok(self) -> bool:
        """True only for a run that produced a usable answer."""
        return self is StopReason.COMPLETE


#: The exact sentence the product uses when it refuses. Re-exported so tests and
#: callers have one place to look, and asserted verbatim in the test suite.
MSG_NO_ADJACENT_AUDIENCE = evidence.MSG_NO_ADJACENT_AUDIENCE

#: Invalid input: the programme carries nothing that can be looked up. This is a
#: user-input problem, not an evidence problem, so it gets its own words.
MSG_INVALID_INPUT_EMPTY = (
    "No programme was supplied. Adjacent needs at least one programme item with an entity id or "
    "an external id before it can look anything up."
)
MSG_INVALID_INPUT_NO_IDS = (
    "None of the {count} programme item(s) carry an entity id or an external id, and this "
    "milestone does not guess a title match. Add an entity id (or an IMDb id) for at least one "
    "title, or run Milestone 3's search-based resolution."
)

#: Input problems, machine-readable, alongside the sentence above.
CODE_EMPTY_PROGRAMME = "empty_programme"
CODE_NO_IDENTIFIERS = "no_identifiers"


@dataclass(frozen=True)
class StopDecision:
    """Why the run ended, in a form both a human and a script can read."""

    reason: StopReason
    message: str
    detail_code: str | None = None
    findings: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.reason.ok

    @property
    def refuses_recommendation(self) -> bool:
        return self.reason is StopReason.INSUFFICIENCY

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason.value,
            "ok": self.ok,
            "message": self.message,
            "detail_code": self.detail_code,
            "findings": list(self.findings),
            "stats": self.stats,
        }


# ---------------------------------------------------------------------------
# The decisions
# ---------------------------------------------------------------------------


def decide_stop(state: AdjacentState, report: EvidenceReport) -> StopDecision:
    """The terminal decision for a run that ran its course.

    Identical in substance to Milestone 1's `_decide_stop`: `complete` requires
    every gate that ran to be satisfied; otherwise the run refuses, and the
    sentence comes from the gate closest to the decision.
    """
    if report.ready:
        survived_domains = sorted({c.domain for c in state.ranked})
        return StopDecision(
            reason=StopReason.COMPLETE,
            message=(
                f"{len(state.ranked)} cohort(s) cleared the evidence gate, covering "
                f"{len(survived_domains)} of the {len(state.domains_represented)} expanded "
                f"domain(s); {len(state.rejected)} candidate cohort(s) were rejected."
            ),
            findings=[],
            stats={
                "ranked": len(state.ranked),
                "rejected": len(state.rejected),
                "domains_survived": len(survived_domains),
                "domains_expanded": len(state.domains_represented),
            },
        )

    failing = report.failing_verdict
    return StopDecision(
        reason=StopReason.INSUFFICIENCY,
        message=failing.message if failing is not None else MSG_NO_ADJACENT_AUDIENCE,
        detail_code=failing.reason_code if failing is not None else "insufficient_cohorts",
        findings=[failing.reason_code] if failing is not None else ["insufficient_cohorts"],
        stats=dict(failing.stats) if failing is not None else {},
    )


def stop_for_insufficiency(
    verdict_message: str, reason_code: str, stats: dict[str, Any] | None = None
) -> StopDecision:
    """Early refusal, when no further evidence can be obtained at all."""
    return StopDecision(
        reason=StopReason.INSUFFICIENCY,
        message=verdict_message,
        detail_code=reason_code,
        findings=[reason_code],
        stats=dict(stats or {}),
    )


def stop_for_budget(exc: BudgetExhausted, state: AdjacentState) -> StopDecision:
    """The budget refused. Reported as its own reason, never as insufficiency."""
    return StopDecision(
        reason=StopReason.TIMEOUT if exc.detail_code == "wall_clock" else StopReason.BUDGET_EXHAUSTED,
        message=exc.message,
        detail_code=exc.detail_code,
        findings=["budget_exhausted"],
        stats={**exc.stats, **state.budget.snapshot()},
    )


def stop_for_invalid_input(code: str, message: str) -> StopDecision:
    return StopDecision(
        reason=StopReason.INVALID_INPUT,
        message=message,
        detail_code=code,
        findings=[code],
    )


def stop_for_error(exc: BaseException, state: AdjacentState) -> StopDecision:
    """A tool or transport failure. Deliberately NOT reported as insufficiency."""
    detail = (
        exc.to_dict()
        if isinstance(exc, QlooError)
        else {"error_type": type(exc).__name__, "message": str(exc)}
    )
    kind = "qloo_error" if isinstance(exc, QlooError) else detail["error_type"]
    return StopDecision(
        reason=StopReason.ERROR,
        message=f"The run could not complete: {detail['message']}",
        detail_code=kind,
        findings=["tool_failure"],
        stats={"error": detail, "calls_made": state.calls_made},
    )
