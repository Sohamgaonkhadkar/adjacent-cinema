"""Typed budget guards for one agent run.

The numbers here are the plan's, not ours: `04_risks_plan_final_spec.md` §R8 fixes
`MAX_STEPS = 14`, `MAX_QLOO_CALLS = 24` and a 90-second wall-clock ceiling for a
whole run, because "the agent loops or stalls" is a scored risk. This module makes
those ceilings executable.

Two different kinds of refusal live here, and the difference matters:

* `take(n)` — used by the deterministic step helpers. Returns `False` when it
  cannot grant the calls, and the caller degrades and records a finding. This is
  Milestone 1's behaviour and it is unchanged.
* `ensure(n)` / `take_step()` — used by the orchestrator before it lets a tool
  run. These **raise** `BudgetExhausted` so the run stops with a machine-readable
  reason (`budget_exhausted`) instead of quietly producing a half-answer. A tool
  that cannot afford its work must not be started at all.

`Budget` is a dataclass with an injectable clock, so the wall-clock guard is
testable without sleeping.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..qloo.errors import AdjacentError

#: Ceilings from the plan (04_risks_plan_final_spec.md, risk R8).
DEFAULT_MAX_STEPS = 14
DEFAULT_MAX_QLOO_CALLS = 24
DEFAULT_MAX_WALL_CLOCK_S = 90.0

#: Machine-readable stop/finding code for every budget refusal.
CODE_BUDGET_EXHAUSTED = "budget_exhausted"

#: Which ceiling was hit. Travels with the decision so the two are never confused.
REASON_STEP_LIMIT = "step_limit"
REASON_CALL_LIMIT = "call_limit"
REASON_WALL_CLOCK = "wall_clock"

#: The wording the plan already uses for the call-budget case (Part 13, R7/R8).
MSG_CALL_BUDGET = (
    "This run used its full API budget before completing the ranking. "
    "Outputs shown are partial. Re-run to complete."
)
MSG_STEP_BUDGET = "This run hit its step ceiling (the agent may not take more than {max_steps} steps)."
MSG_WALL_CLOCK = "This run hit its wall-clock ceiling and stopped with the evidence it had gathered."


class BudgetExhausted(AdjacentError):
    """A tool asked for a resource the budget cannot grant.

    Carries the machine-readable code (`budget_exhausted`) plus the specific
    ceiling, so a budget stop is never confused with a Qloo failure or with
    insufficient evidence.
    """

    code = CODE_BUDGET_EXHAUSTED

    def __init__(self, detail_code: str, message: str, *, stats: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.detail_code = detail_code
        self.message = message
        self.stats = dict(stats or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": type(self).__name__,
            "code": self.code,
            "detail_code": self.detail_code,
            "message": self.message,
            "stats": self.stats,
        }


@dataclass(frozen=True)
class BudgetVerdict:
    """The budget's answer to "may I do one more thing?" — never raises."""

    allowed: bool
    detail_code: str | None
    message: str
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "code": None if self.allowed else CODE_BUDGET_EXHAUSTED,
            "detail_code": self.detail_code,
            "message": self.message,
            "stats": self.stats,
        }


@dataclass
class Budget:
    """Steps, Qloo calls and wall clock for exactly one run."""

    max_steps: int = DEFAULT_MAX_STEPS
    max_qloo_calls: int = DEFAULT_MAX_QLOO_CALLS
    max_wall_clock_s: float = DEFAULT_MAX_WALL_CLOCK_S
    steps_used: int = 0
    qloo_calls_used: int = 0
    clock: Callable[[], float] = time.monotonic
    started_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.started_at:
            self.started_at = self.clock()

    # -- read-only views ---------------------------------------------------
    @property
    def remaining_steps(self) -> int:
        return max(0, self.max_steps - self.steps_used)

    @property
    def remaining_calls(self) -> int:
        return max(0, self.max_qloo_calls - self.qloo_calls_used)

    def elapsed_s(self) -> float:
        return round(self.clock() - self.started_at, 6)

    def check(self) -> BudgetVerdict:
        """Is the budget still usable? Machine-readable, side-effect free."""
        elapsed = self.elapsed_s()
        stats = {
            "steps_used": self.steps_used,
            "max_steps": self.max_steps,
            "qloo_calls_used": self.qloo_calls_used,
            "max_qloo_calls": self.max_qloo_calls,
            "elapsed_s": elapsed,
            "max_wall_clock_s": self.max_wall_clock_s,
        }
        if elapsed >= self.max_wall_clock_s:
            return BudgetVerdict(False, REASON_WALL_CLOCK, MSG_WALL_CLOCK, stats)
        if self.steps_used >= self.max_steps:
            return BudgetVerdict(
                False,
                REASON_STEP_LIMIT,
                MSG_STEP_BUDGET.format(max_steps=self.max_steps),
                stats,
            )
        if self.qloo_calls_used >= self.max_qloo_calls:
            return BudgetVerdict(False, REASON_CALL_LIMIT, MSG_CALL_BUDGET, stats)
        return BudgetVerdict(True, None, "", stats)

    def snapshot(self) -> dict[str, Any]:
        return {
            "max_steps": self.max_steps,
            "steps_used": self.steps_used,
            "remaining_steps": self.remaining_steps,
            "max_qloo_calls": self.max_qloo_calls,
            "qloo_calls_used": self.qloo_calls_used,
            "remaining_calls": self.remaining_calls,
            "max_wall_clock_s": self.max_wall_clock_s,
            "elapsed_s": self.elapsed_s(),
            "exhausted": not self.check().allowed,
            "detail_code": self.check().detail_code,
        }

    # -- guards the orchestrator uses (raise) -------------------------------
    def take_step(self) -> int:
        """Claim one step for a bounded action. Raises when the ceiling is hit."""
        verdict = self.check()
        if not verdict.allowed:
            raise BudgetExhausted(
                verdict.detail_code or REASON_STEP_LIMIT, verdict.message, stats=verdict.stats
            )
        self.steps_used += 1
        return self.steps_used

    def take_step_quiet(self) -> int:
        """Count a step with no right to refuse it.

        Used by the terminal STOP phase: a run must always be able to stop, even
        after the step ceiling is reached, or the budget guard would itself be the
        reason a run never terminates.
        """
        self.steps_used += 1
        return self.steps_used

    def ensure(self, calls: int) -> None:
        """Refuse to start work that would need `calls` further Qloo calls."""
        if calls <= 0:
            return
        if self.remaining_calls < calls:
            verdict = self.check()
            detail = (
                verdict.detail_code
                if not verdict.allowed and verdict.detail_code == REASON_WALL_CLOCK
                else REASON_CALL_LIMIT
            )
            stats = {
                **verdict.stats,
                "calls_needed": calls,
                "calls_remaining": self.remaining_calls,
            }
            raise BudgetExhausted(detail, MSG_CALL_BUDGET, stats=stats)

    # -- the Milestone-1 helper contract (returns a bool) -------------------
    def take(self, n: int = 1) -> bool:
        """Reserve `n` calls up-front, or return False without reserving.

        Kept because the deterministic step helpers (`_taste_profile`,
        `_expand_candidates`, ...) degrade and record a finding instead of
        raising. The orchestrator never relies on this path: it calls `ensure`
        before the tool starts.
        """
        if self.remaining_calls < n:
            return False
        self.qloo_calls_used += n
        return True

    def record_calls(self, n: int) -> None:
        """Account for calls a tool made internally (e.g. the cohort ranker)."""
        self.qloo_calls_used += max(0, n)
