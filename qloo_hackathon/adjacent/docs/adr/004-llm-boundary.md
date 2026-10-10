# ADR-004: LLM Boundary — At Edges Only

## Status

FROZEN

## Date

4 October 2026

## Decision

LLM is used for two narrow jobs only:
1. **Extraction:** messy programme text → structured `ParsedTitle[]`
2. **Narration:** typed `ToolResult` → human-readable prose

The LLM has NO tool access and MUST NOT produce any numeric claim.

## Rationale

1. **Auditability.** Every number in the output comes from a Qloo response with a call_id. LLM-generated numbers would be unverifiable.
2. **Hallucination prevention.** The LLM cannot invent entity IDs, affinity values, rankings, or geographic claims because it has no route to producing them.
3. **Judging criterion.** "Does the code reflect genuine effort?" A system where the LLM makes decisions reads as a wrapper around an API. A system where deterministic code makes decisions and the LLM only formats text reads as engineering.

## Hard Rules

- LLM has NO tool access (cannot call Qloo, cannot modify state)
- LLM MUST NOT produce: entity IDs, affinity values, rankings, geographic claims, evidence, cohort scores, programme decisions
- LLM output is schema-validated before use
- Empty-state guard: every narration function returns empty string if input is empty

## Alternative Considered

- LLM-controlled agent (LLM decides which tool to call) — rejected: unauditable, hallucination risk
- No LLM at all — rejected: messy text extraction is a real user need
- LLM for scoring/ranking — rejected: violates provenance requirement

## Consequence

- Two new modules: `llm/extract.py` and `llm/narrate.py`
- LLM API key stored as `LLM_API_KEY` env var
- LLM calls are NOT counted in the Qloo budget (separate concern)

## Trigger to Revisit

Never. The LLM boundary is a core architectural invariant.