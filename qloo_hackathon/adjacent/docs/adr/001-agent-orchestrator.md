# ADR-001: Custom Async Orchestrator vs LangGraph

## Status

FROZEN

## Date

4 October 2026 (research) / 6 October 2026 (freeze)

## Decision

Use a custom async state machine (~421 lines) instead of LangGraph or any other agent framework.

## Rationale

1. **Judging criterion.** The hackathon evaluates "Does the code reflect genuine effort… and avoid wrappers and shortcuts?" An explicit state machine reads as engineering; a framework reads as scaffolding.
2. **Traceability.** Every transition is recorded with from/to/action/reason. LangGraph's internal state transitions would be opaque.
3. **Simplicity.** The graph is linear: RESOLVE → ANALYSE → EXPAND → RANK, with one loop (widen+retry) and one human-in-the-loop point (disambiguation). LangGraph's value is complex branching and persistence — we don't need either.
4. **No hidden control flow.** The orchestrator knows nothing about Qloo, domain logic, or scoring. It selects tools by name, executes one bounded action, and reads a typed result.

## Alternative Considered

LangGraph. Also considered Prefect, Airflow, and custom coroutine chains.

## Why Rejected

- LangGraph: adds a dependency, obscures the trace, makes agent decisions less legible
- Prefect/Airflow: designed for batch workflows, not interactive agent loops
- Coroutine chains: less structured than a state machine, harder to audit

## Consequence

- The orchestrator is ~421 lines of readable Python
- Adding a new phase requires adding a Phase enum value, a tool, and a plan transition
- No framework upgrades or compatibility concerns

## Trigger to Revisit

If the agent graph becomes significantly more complex (e.g., parallel tool execution, conditional branching based on intermediate results), LangGraph might become justified. Current graph does not warrant it.