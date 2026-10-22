"""The explicit agent orchestrator: PLAN → SELECT → ACT → EVALUATE → STOP.

No agent framework, no LLM, no hidden control flow. One loop, five named steps,
every transition recorded, and every resource spent through `Budget`:

    PLAN      decide which phase should run next (or that the run should stop)
    SELECT    pick the tool that implements that phase
    ACT       execute exactly one bounded action
    EVALUATE  read the typed result and apply the evidence gate (assess_evidence)
    STOP      produce a typed stop decision and finish

The plan is a fixed table over the acting phases, not a search: the value of the
state machine here is *auditability and refusal*, not cleverness. What the loop may
decide at EVALUATE is:

    continue                    the run can still obtain evidence
    stop / insufficiency        nothing further can be obtained (no resolved ids)
    stop / budget_exhausted     a ceiling was hit — never reported as insufficiency
    stop / error                a tool or transport failed — never reported as insufficiency
    stop / invalid_input        the programme carries nothing that can be looked up

`complete` vs `insufficiency` for a run that gathered everything it could is decided
in STOP by `stop.decide_stop` — the Milestone-1 terminal decision, moved rather than
reimplemented.

The orchestrator knows nothing about Qloo: it holds five tools and a runtime name.
"""

from __future__ import annotations

import logging
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..qloo.errors import QlooError
from .budget import BudgetExhausted
from .state import ACT_PHASES, AdjacentState, Finding, Phase, RunStatus
from .stop import (
    CODE_EMPTY_PROGRAMME,
    CODE_NO_IDENTIFIERS,
    MSG_INVALID_INPUT_EMPTY,
    MSG_INVALID_INPUT_NO_IDS,
    StopDecision,
    decide_stop,
    stop_for_budget,
    stop_for_error,
    stop_for_insufficiency,
    stop_for_invalid_input,
)
from .tools import EvidenceReport, PipelineRuntime, Tool, build_evidence_report, default_tools

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Callable

#: Phase → tool name. One tool per acting phase; nothing else may run.
PHASE_TOOL: dict[Phase, str] = {
    Phase.RESOLVE: "resolve_programme",
    Phase.ANALYSE: "get_taste_profile",
    Phase.EXPAND: "expand_candidates",
    Phase.RANK: "rank_cohorts",
}

#: Tool name → the action label recorded in `state.completed`.
ACTION_LABEL: dict[str, str] = {
    "resolve_programme": "resolve",
    "get_taste_profile": "analyse",
    "expand_candidates": "expand",
    "rank_cohorts": "rank",
}

#: A defensive loop cap. The plan is finite and `completed` only grows, so this
#: should never fire — it exists so a future planning bug cannot spin the loop.
MAX_ITERATIONS = 24

logger = logging.getLogger(__name__)


class OrchestratorFinished(RuntimeError):
    """Raised when a state is asked to execute after the run has stopped."""


class OrchestratorInvalidInput(RuntimeError):
    """The programme cannot be worked with at all. A user problem, not evidence."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Evaluation:
    """The EVALUATE verdict for one action."""

    decision: str  # "continue" | "stop"
    reason: str
    stop: StopDecision | None = None

    @property
    def stopping(self) -> bool:
        return self.decision == "stop"


def _error_decision_with_frames(exc: Exception, state: AdjacentState) -> StopDecision:
    decision = stop_for_error(exc, state)
    error = decision.stats.get("error")
    if isinstance(error, dict):
        error["frames"] = [
            f"{Path(frame.filename).name}:{frame.name}:{frame.lineno}"
            for frame in traceback.extract_tb(exc.__traceback__)[-16:]
        ]
    # This boundary actually observes tool-level exceptions: the outer Creator
    # route receives only the terminal state, not the original exception.
    safe_error = decision.stats.get("error", {})
    safe_error = safe_error if isinstance(safe_error, dict) else {}
    frames = safe_error.get("frames", [])
    safe_frames = [frame for frame in frames if isinstance(frame, str)] if isinstance(frames, list) else []
    logger.error(
        "Orchestrator tool failure: error_type=%s call_id=%s frames=%s",
        safe_error.get("error_type") or type(exc).__name__,
        safe_error.get("call_id") or "none",
        " > ".join(safe_frames) or "<traceback unavailable>",
    )
    return decision


class AgentOrchestrator:
    """Drives one run to a terminal state. See the module docstring for the cycle."""

    def __init__(
        self,
        runtime: PipelineRuntime,
        *,
        tools: dict[str, Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
        allow_title_search: bool = False,
    ) -> None:
        self.runtime = runtime
        self.tools: dict[str, Any] = tools if tools is not None else default_tools(runtime)
        self.clock = clock
        self.allow_title_search = allow_title_search

    # -- the loop ----------------------------------------------------------
    async def run(self, state: AdjacentState) -> AdjacentState:
        """Run until a terminal state. Calling it again on a finished state is a no-op."""
        if state.finished:
            return state

        # INIT: the run begins here, and the first thing it does is plan.
        state.phase = Phase.INIT
        state.record_transition(
            from_state=Phase.INIT,
            to_state=Phase.PLAN,
            action="plan",
            reason=(
                f"input accepted: {len(state.programme)} programme item(s); "
                f"runtime={self.runtime.name} ({self.runtime.data_status}); "
                f"budget={state.budget.max_steps} steps / {state.budget.max_qloo_calls} calls"
            ),
        )
        state.phase = Phase.PLAN

        iterations = 0
        while state.status is RunStatus.RUNNING:
            iterations += 1
            if iterations > MAX_ITERATIONS:
                self.stop(
                    state,
                    stop_for_budget(
                        BudgetExhausted(
                            "iteration_limit",
                            f"The planner exceeded {MAX_ITERATIONS} iterations; stopping rather "
                            "than looping.",
                            stats={"iterations": iterations},
                        ),
                        state,
                    ),
                )
                break

            # --- PLAN ------------------------------------------------------
            problem = self.validate_input(state)
            if problem is not None:
                self.stop(state, stop_for_invalid_input(problem.code, problem.message))
                break
            next_phase, plan_reason = self.plan_next(state)

            if next_phase is Phase.STOP:
                # Nothing left to do: the terminal decision, recorded as PLAN → STOP.
                self.stop(state, decide_stop(state, self.require_report(state)))
                break

            # --- SELECT ----------------------------------------------------
            tool = self.select(next_phase)
            if tool is None:  # pragma: no cover - defensive
                self.stop(
                    state,
                    stop_for_error(
                        RuntimeError(f"no tool is registered for phase {next_phase.value}"), state
                    ),
                )
                break
            state.record_transition(
                from_state=Phase.PLAN,
                to_state=next_phase,
                action=tool.name,
                reason=plan_reason,
            )
            state.phase = next_phase

            # --- ACT -------------------------------------------------------
            try:
                result = await self.act(tool, state)

                # --- EVALUATE ----------------------------------------------
                evaluation = await self.evaluate(state, result)
            except BudgetExhausted as exc:
                self.stop(state, stop_for_budget(exc, state))
                break
            except QlooError as exc:
                self.stop(state, _error_decision_with_frames(exc, state))
                break
            except Exception as exc:
                self.stop(state, _error_decision_with_frames(exc, state))
                break

            self.record_evaluation(state, result, evaluation)
            if evaluation.stopping:
                self.stop(state, evaluation.stop or decide_stop(state, self.require_report(state)))
                break

        return state

    # -- PLAN --------------------------------------------------------------
    def validate_input(self, state: AdjacentState) -> OrchestratorInvalidInput | None:
        """Invalid input is a user problem, and stays distinct from thin evidence."""
        if not state.programme:
            return OrchestratorInvalidInput(CODE_EMPTY_PROGRAMME, MSG_INVALID_INPUT_EMPTY)
        # Creator enables title lookup explicitly; default runtimes still require
        # at least one caller-supplied identifier to preserve their input contract.
        if not any(item.identifiers for item in state.programme) and not (
            self.allow_title_search and any(item.title.strip() for item in state.programme)
        ):
            return OrchestratorInvalidInput(
                CODE_NO_IDENTIFIERS,
                MSG_INVALID_INPUT_NO_IDS.format(count=len(state.programme)),
            )
        return None

    def plan_next(self, state: AdjacentState) -> tuple[Phase, str]:
        """Choose the next phase. Deterministic, and explainable in one sentence.

        A phase that already completed is never selected again — that, plus the
        finite plan, is what makes the loop terminating by construction.
        """
        if "resolve" not in state.completed:
            return Phase.RESOLVE, (
                f"no programme entity has been resolved yet ({len(state.programme)} item(s) supplied)"
            )

        resolved = len(state.resolved_ids)
        if resolved == 0:
            return Phase.STOP, "no entity id resolved: no further tool can obtain any evidence"

        if "analyse" not in state.completed:
            return Phase.ANALYSE, f"characterise the programme's taste from {resolved} resolved id(s)"

        if "expand" not in state.completed:
            return Phase.EXPAND, f"ask Qloo for adjacent entities from {resolved} signal id(s)"

        if "rank" not in state.completed:
            return Phase.RANK, "construct candidate cohorts and rank them in one operation"

        return Phase.STOP, (
            f"plan exhausted: {len(state.ranked)} cohort(s) cleared the gate and "
            f"{len(state.rejected)} were rejected"
        )

    # -- SELECT ------------------------------------------------------------
    def select(self, phase: Phase) -> Tool | None:
        """Pick the tool that implements a phase. `None` means the phase is terminal."""
        tool_name = PHASE_TOOL.get(phase)
        if tool_name is None:
            return None
        return self.tools[tool_name]

    # -- ACT ---------------------------------------------------------------
    async def act(self, tool: Tool, state: AdjacentState) -> Any:
        """Execute exactly one bounded action, against the budget."""
        if state.status is not RunStatus.RUNNING:
            raise OrchestratorFinished("cannot execute a tool after the run has stopped")
        state.budget.take_step()
        result = await tool.execute(state, state.budget)
        state.completed.add(ACTION_LABEL.get(tool.name, tool.name))
        state.record_transition(
            from_state=state.phase,
            to_state=Phase.EVALUATE,
            action=tool.name,
            reason=result.detail,
        )
        state.phase = Phase.EVALUATE
        return result

    # -- EVALUATE ----------------------------------------------------------
    async def evaluate(self, state: AdjacentState, result: Any) -> Evaluation:
        """Read the result of the action just taken and apply the evidence gate."""
        if state.status is not RunStatus.RUNNING:
            raise OrchestratorFinished("cannot evaluate after the run has stopped")
        state.budget.take_step()
        report = await self.tools["assess_evidence"].execute(state, state.budget)

        # A technical failure the tool reported rather than raised: every attempt
        # failed, so there is nothing to reason about. This is a fault, not thin data.
        failure = tuple(getattr(result, "failed_domains", ()))
        attempted = tuple(getattr(result, "domains", ()))
        if attempted and failure and set(failure) == set(attempted):
            return Evaluation(
                decision="stop",
                reason="every expansion call failed: a tool failure, not thin evidence",
                stop=stop_for_error(
                    QlooError(
                        "every expansion call failed; the per-domain reasons are in the findings",
                        detail={"failed_domains": list(failure)},
                    ),
                    state,
                ),
            )

        # Nothing further can be obtained → an honest refusal, not a fault.
        if not report.progress_possible and not state.ranked and not report.ready:
            verdict = self.insufficiency_cause(report)
            if verdict is not None:
                # Every other unsatisfied gate is kept as a finding, so the run's
                # journal names all the reasons rather than only the first.
                for other in self.other_insufficiencies(report, verdict):
                    state.findings.append(
                        Finding(
                            code=other.reason_code,
                            message=other.message,
                            stats=dict(other.stats),
                        )
                    )
                return Evaluation(
                    decision="stop",
                    reason=(
                        "no entity resolved, so no remaining tool can obtain evidence "
                        f"({verdict.reason_code})"
                    ),
                    stop=stop_for_insufficiency(verdict.message, verdict.reason_code, dict(verdict.stats)),
                )

        # The ceilings are checked here as well, so a run stops with budget_exhausted
        # rather than discovering it half-way into the next action.
        budget_verdict = state.budget.check()
        if not budget_verdict.allowed:
            return Evaluation(
                decision="stop",
                reason=f"budget exhausted: {budget_verdict.message}",
                stop=stop_for_budget(
                    BudgetExhausted(
                        budget_verdict.detail_code or "call_limit",
                        budget_verdict.message,
                        stats=budget_verdict.stats,
                    ),
                    state,
                ),
            )

        return Evaluation(decision="continue", reason=report.summary())

    # -- PLAN helpers ------------------------------------------------------
    @staticmethod
    def insufficiency_cause(report: EvidenceReport) -> Any | None:
        """Which sentence should a run that cannot continue refuse with?

        Milestone 1's precedence (cohort → resolution → taste) still decides for a
        run that gathered everything it could. The one addition: when *nothing*
        resolved, the resolution gate is the cause, so its more specific sentence
        ("Only N of your titles could be identified...") is the one that helps.
        """
        resolution = report.resolution_verdict
        if report.resolved_ids == 0 and resolution is not None and not resolution.sufficient:
            return resolution
        verdict = report.failing_verdict
        if verdict is None or verdict.sufficient:
            return None
        return verdict

    @staticmethod
    def other_insufficiencies(report: EvidenceReport, primary: Any) -> list[Any]:
        """The remaining unsatisfied gates, in report order."""
        seen = {primary.reason_code}
        others = []
        for verdict in (report.resolution_verdict, report.taste_verdict, report.cohort_verdict):
            if verdict is None or verdict.sufficient or verdict.reason_code in seen:
                continue
            seen.add(verdict.reason_code)
            others.append(verdict)
        return others

    def record_evaluation(self, state: AdjacentState, result: Any, evaluation: Evaluation) -> None:
        state.record_transition(
            from_state=Phase.EVALUATE,
            to_state=Phase.STOP if evaluation.stopping else Phase.PLAN,
            action="assess_evidence",
            reason=evaluation.reason,
        )
        state.phase = Phase.STOP if evaluation.stopping else Phase.PLAN

    # -- STOP --------------------------------------------------------------
    def stop(
        self,
        state: AdjacentState,
        decision: StopDecision,
        *,
        note: str | None = None,
    ) -> AdjacentState:
        """Finish the run. The only way a run ends."""
        state.budget.take_step_quiet()  # stopping must never be refused by the budget
        state.stop = decision
        state.status = RunStatus.FINISHED
        failed = decision.reason.value == "error"
        state.record_transition(
            from_state=state.phase,
            to_state=Phase.ERROR if failed else Phase.STOP,
            action="stop",
            reason=note or f"{decision.reason.value}: {decision.detail_code or '-'}",
        )
        state.phase = Phase.ERROR if failed else Phase.STOP
        for code in decision.findings:
            if code and all(finding.code != code for finding in state.findings):
                state.findings.append(Finding(code=code, message=decision.message))
        return state

    # -- helpers -----------------------------------------------------------
    def require_report(self, state: AdjacentState) -> EvidenceReport:
        if state.evidence_report is None:
            state.evidence_report = build_evidence_report(state)
        return state.evidence_report


__all__ = [
    "ACTION_LABEL",
    "ACT_PHASES",
    "MAX_ITERATIONS",
    "PHASE_TOOL",
    "AgentOrchestrator",
    "Evaluation",
    "OrchestratorFinished",
    "OrchestratorInvalidInput",
]
