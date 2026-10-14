# M13.12 — Model Architecture

Status: implemented offline-testable; live provider BLOCKED in this environment
(`ADJACENT_LLM_API_KEY` not configured). No custom-trained predictive model
exists in this project and none is claimed.

## Role separation

| Role | What it does | Implementation | Model involved? |
|------|--------------|----------------|-----------------|
| **A — tool agent** | PLAN → SELECT → ACT → EVALUATE → STOP over Qloo tools | `backend/app/agent/` (orchestrator, tools, state, budget, stop) | **No** — deterministic |
| **B — synthesis** | Renders a completed investigation into a creator-facing brief | `backend/app/domain/synthesis.py` over `llm_provider.py` | Optional, bounded |
| **C — evaluation** | Scores condition outputs against a versioned rubric | `research/scripts/m13_11_qloo_vs_llm.py` (rubric v2) | **No** — deterministic checks; LLM evaluator ≠ human evaluation |

The decision engine is deterministic. Role B never re-executes tools, never
sees credentials, and cannot change what the agent decided — it can only
render it, and its output is post-validated.

## Provider abstraction (`backend/app/domain/llm_provider.py`)

- `LLMProviderConfig.from_env()` reads `ADJACENT_LLM_API_KEY` /
  `ADJACENT_LLM_BASE_URL` (default `https://api.openai.com/v1`) /
  `ADJACENT_LLM_MODEL` (default `gpt-4o-mini`). Keys are never hardcoded,
  never logged; `redacted()` is the only diagnostic view.
- `OpenAICompatibleProvider` — minimal chat-completions client; transport
  injectable for tests; every failure raises `LLMUnavailableError` (message
  names the env var so the state is actionable).
- `StubSynthesisProvider` — deterministic offline stub, `kind="stub"`,
  labelled in every artefact and response. Never used as an implicit
  fallback.
- One implementation, two consumers: the evaluation harness (Condition A
  baseline) and Role-B synthesis.

## Why a bounded LLM synthesis layer is justified

Creators need the investigation in prose. A schema-constrained renderer over
*real* evidence improves the product without letting a model touch the
decision. Constraints:

1. **Fixed schema** — exactly `SYNTHESIS_KEYS` (summary, hypothesis_restated,
   rationale, alternatives, next_experiment, caveats). Missing/extra-typed
   keys → rejected.
2. **Deterministic post-validation** (`validate_synthesis`) — schema, size
   bounds (2000 chars/field, ≤5 alternatives, ≤8 caveats), evidence-ref
   resolution (any ref-shaped token — UUID or `…-cNNN` recorder ids — not in
   the investigation's real ref set is treated as fabrication), and a
   forbidden-claims guard (virality, guarantees, viewership predictions,
   causal claims). Validation is code, not prompt trust.
3. **Honest failure** — any provider error or validation failure returns
   `method: "deterministic_fallback"` with `llm_error` recorded; the fallback
   is generated from the investigation itself (facts only in the summary,
   "No hypothesis was supported by the evidence." when there is none). A
   failed model call never masquerades as a model result.
4. **No silent stub** — no provider configured → route reports 503 BLOCKED
   naming `ADJACENT_LLM_API_KEY`; `/creator/synthesis-status` exposes the
   same state.

Known limitation (documented, not hidden): the forbidden-claims guard is a
pattern list, not a proof; entity fabrication is guarded via evidence-ref
resolution, not full entity extraction.

## Investigation upgrades (Role A, still deterministic)

- `investigation_id` (uuid) on every investigation.
- `q0` context-framing question — only when the creator supplied context
  beyond a title; makes no API call and says so; names missing context as a
  weakness.
- Adaptive follow-ups raised by the evidence itself: `q5` (top-2 mean-affinity
  gap < 0.03 → tie cannot be broken by affinity; creator framing test must),
  `q6` (qualifying/total < 0.3 → position is narrower than it looks).
- Unified claim types on findings: `FACT | INTERPRETATION | HYPOTHESIS |
  UNKNOWN` (open questions surface as UNKNOWN findings citing nothing).
- Primary hypothesis carries `assumptions` and `distinguishing_evidence`
  (names the runner-up world when one exists).
- `verify_evidence_refs()` strips any evidence ref that does not resolve to a
  recorded call (route builds the known set from `state.trace_rows`), records
  the removal as a limitation, and returns the dropped ids.
- Insufficient evidence → no hypothesis, no experiment, explicit
  insufficiency. Never a forced recommendation.

## Testing without a provider

`backend/tests/test_m13_12_synthesis.py` covers: valid stub output, malformed
JSON, missing schema keys, fabricated refs, real refs accepted, forbidden
claims (4 patterns), oversized fields/lists, provider exception → labelled
fallback, fallback truthfulness on insufficient evidence, prompt contains no
credentials, blocked status/routes. `reset_synthesis_for_tests()` is the only
injection point and is test-only.
