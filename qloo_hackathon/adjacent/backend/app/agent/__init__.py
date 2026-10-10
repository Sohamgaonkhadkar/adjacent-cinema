"""The Adjacent agent: an explicit, deterministic state machine.

    AgentOrchestrator   PLAN → SELECT → ACT → EVALUATE → STOP
    AdjacentState       the one record of a run (input, artefacts, control state)
    Budget              steps, Qloo calls and wall clock, with machine-readable refusals
    StopReason          the canonical vocabulary a run can end in
    Tool                the typed contract the orchestrator acts through

What this package is NOT: not LangGraph, not an LLM, not a planner that searches.
Every transition is recorded, every action is one tool execution, and every
decision that ends a run is a typed `StopDecision` produced by deterministic code.
"""

from .budget import (
    CODE_BUDGET_EXHAUSTED,
    DEFAULT_MAX_QLOO_CALLS,
    DEFAULT_MAX_STEPS,
    DEFAULT_MAX_WALL_CLOCK_S,
    Budget,
    BudgetExhausted,
    BudgetVerdict,
)
from .orchestrator import (
    AgentOrchestrator,
    Evaluation,
    OrchestratorFinished,
    OrchestratorInvalidInput,
)
from .state import ACT_PHASES, AdjacentState, Finding, Phase, ProgrammeItem, RunStatus, Transition
from .stop import MSG_NO_ADJACENT_AUDIENCE, StopDecision, StopReason
from .tools import (
    AssessEvidenceTool,
    EvidenceReport,
    ExpandCandidatesTool,
    ExpandResult,
    PipelineRuntime,
    RankCohortsTool,
    RankResult,
    ResolveProgrammeTool,
    ResolveResult,
    TasteProfileTool,
    TasteResult,
    ToolResult,
    build_evidence_report,
    default_tools,
)

__all__ = [
    "ACT_PHASES",
    "CODE_BUDGET_EXHAUSTED",
    "DEFAULT_MAX_QLOO_CALLS",
    "DEFAULT_MAX_STEPS",
    "DEFAULT_MAX_WALL_CLOCK_S",
    "MSG_NO_ADJACENT_AUDIENCE",
    "AdjacentState",
    "AgentOrchestrator",
    "AssessEvidenceTool",
    "Budget",
    "BudgetExhausted",
    "BudgetVerdict",
    "Evaluation",
    "EvidenceReport",
    "ExpandCandidatesTool",
    "ExpandResult",
    "Finding",
    "OrchestratorFinished",
    "OrchestratorInvalidInput",
    "Phase",
    "PipelineRuntime",
    "ProgrammeItem",
    "RankCohortsTool",
    "RankResult",
    "ResolveProgrammeTool",
    "ResolveResult",
    "RunStatus",
    "StopDecision",
    "StopReason",
    "TasteProfileTool",
    "TasteResult",
    "ToolResult",
    "Transition",
    "build_evidence_report",
    "default_tools",
]
