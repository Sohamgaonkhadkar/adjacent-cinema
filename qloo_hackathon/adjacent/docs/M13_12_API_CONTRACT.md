# M13.12 — API Contract (for the future frontend workstream)

All M13.12 changes are **additive**: no field was removed or retyped. The
frontend redesign is a separate workstream; nothing here assumes it.

## Investigation response (`result.investigation` on a completed creator run)

```
investigation_id   string (uuid)                      NEW in M13.12
film               {title, logline?, genre?, language?, release_goal?}
seeds              string[]
questions[]        {id, question, tool, operation, status,
                    evidence_refs[], summary}
                   ids: q0 (context framing, only when context beyond title,
                   tool "context_framing", no API call), q1–q4 (tools),
                   q5/q6 adaptive follow-ups (only when the evidence raises
                   them: near-tie gap <0.03; qualifying breadth <30%)
                   status: answered | insufficient | unavailable
findings[]         {kind, claim_type, statement, evidence_refs[]}
                   claim_type: FACT | INTERPRETATION | HYPOTHESIS | UNKNOWN
                   (UNKNOWN findings restate open_questions and cite nothing)
hypotheses         {primary: {statement, cohort_id, world, evidence_refs[],
                              supporting_evidence, falsification,
                              assumptions[], distinguishing_evidence} | null,
                   alternatives[]: {statement, cohort_id, world,
                              evidence_refs[]},
                   rejected_worlds[]: {cohort_id, world, reason}}
experiment         {title, action_plan, success_criteria,
                    observation_window, falsification} | null
limitations        string[]   (includes fixture labelling + affinity guard)
open_questions     string[]
data_status        "measured" | "fixture"
provenance         {call_ids[], qloo_calls_used, run_data_status}
```

**Evidence contract:** every `evidence_refs`/`call_ids` entry is a stable,
opaque call id recorded by the run (UUID or `{run_id}-cNNN`). Before the
investigation is emitted, `verify_evidence_refs` drops any ref that does not
resolve to a recorded call and appends a limitation saying so — clients can
trust that displayed refs are real. No credentials appear anywhere in the
investigation, trace, or SSE events.

## Synthesis (optional, provider-gated)

```
GET  /creator/synthesis-status
  → {available: bool, provider, model, blocked_reason?}   (never secrets)

POST /creator/synthesize   {run_id}
  404 unknown run · 409 run has no investigation
  503 provider not configured (detail names ADJACENT_LLM_API_KEY) — honest
      BLOCKED, never a silent stub
  200 → {run_id,
         synthesis: {summary, hypothesis_restated, rationale,
                     alternatives[], next_experiment, caveats[]
                     [, _fallback_error]},
         metadata: {schema_version, provider_kind, model,
                    evidence_refs_available[],
                    method: "live_llm" | "stub" | "deterministic_fallback",
                    validation: "passed" | "failed: …" | "not applicable …",
                    llm_error?}}
```

`method` is always present and unambiguous; a failed model call can never be
mistaken for a successful one.

## Experiment lifecycle (additive fields on POST /experiments)

```
investigation_summary?  {investigation_id, data_status,
                         primary_hypothesis, limitations[], open_questions[]}
evidence_refs?          string[]
```

Both are merged into the stored `provenance` JSON (no repository schema
change). When `source_run_id` is supplied, refs that do not resolve to the
run's recorded calls are dropped and listed under
`provenance.unresolved_evidence_refs` — nothing dangling is ever stored as
proof. Existing semantics preserved: zero ≠ missing in observations,
idempotent request_id, evaluations supersede with history, variant_label +
window preserved (correlation ≠ causation).

## Evaluation contract (harness artefacts)

`rubric_version: "2.0"`; categories `decision_quality` (both conditions) and
`evidence_grounding` (grounded only, else `applicable: false`); per-run
metadata (condition, provider_kind, model, fixture/live, refs available);
`condition_a_status: ran | blocked`; stub runs labelled `llm_stub`. Real vs
fixture vs blocked vs partial is explicit in every artefact.

## Contract tests

- Investigation/evidence: `backend/tests/test_m13_12_agent_intelligence.py`
- Synthesis + routes: `backend/tests/test_m13_12_synthesis.py`
- Harness/rubric: `backend/tests/test_m13_11_investigation_eval.py`
- Lifecycle regressions: `backend/tests/test_m13_9_experiment_lifecycle.py`
