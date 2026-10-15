# M13.13 — API Contract (delta over `M13_12_API_CONTRACT.md`)

All changes additive except the synthesis schema bump, which is a
deliberate, documented rejection of v1 payloads (they produce the labelled
fallback, never a silent pass). The investigation contract from M13.12 is
unchanged.

## Synthesis schema 2.0

`POST /creator/synthesize` 200 response:

```
{run_id,
 synthesis: {summary, hypothesis_restated, rationale, alternatives[],
             next_experiment, caveats[],
             claims: [{statement,
                       claim_type: FACT|INTERPRETATION|HYPOTHESIS|UNKNOWN,
                       evidence_refs[],   // resolve against metadata refs
                       rationale, limitations}]
             [, _fallback_error]},
 metadata: {schema_version: "2.0", provider_kind, model,
            method: "live_llm"|"stub"|"deterministic_fallback",
            validation: "passed"|"failed: …"|"not applicable …",
            llm_error?,
            evidence_refs_available[],       // the resolution set
            guarantees: {reference_integrity: "checked …",
                         semantic_support:   "NOT guaranteed …"}}}
```

Frontend state mapping (already implemented in the creator page's Decision
Brief panel):

| metadata.method | UI state |
|---|---|
| `live_llm` | LIVE MODEL SYNTHESIS |
| `stub` | STUB PROVIDER — NOT A REAL MODEL RESULT (test-only injection) |
| `deterministic_fallback` | DETERMINISTIC FALLBACK — shows `llm_error` reason |
| (503 / status.available=false) | blocked — honest `blocked_reason`, investigation unaffected |

Rules the contract guarantees: v1 payloads (no `claims`) rejected; FACT
claims always carry resolving refs; UNKNOWN claims never carry refs; no
HYPOTHESIS claims when the investigation abstained; fallback output has the
same shape and passes the same validator.

`GET /creator/synthesis-status` — unchanged shape
(`{available, provider, model, blocked_reason?}`), never exposes secrets.

## Evaluation artefacts (rubric 3.0)

`rubric_version: "3.0"`; per-run `run_metadata` adds `fixture` and
`fixture_alignment`; scores carry `decision_quality` (may be
`{applicable: false, reason}`), `evidence_grounding`,
`abstention_quality`, `categories_applicable`; summary reports per-category
means with `n` and applicability. Human-rating template unchanged.

## Experiment lifecycle — unchanged semantics, verified end-to-end

`investigation_summary` + `evidence_refs` merge into provenance; refs
validated against the source run's recorded trace; unresolvable ids listed
in `provenance.unresolved_evidence_refs`; zero≠missing, idempotency,
supersession, observation statuses preserved. **Separation rule:** a
synthesis is a rendering of the investigation; it never rewrites the saved
investigation, experiment, or evaluation history.

## Data the future frontend can rely on

Investigation (q0–q6 with statuses + resolvable refs, typed findings,
primary/alternative hypotheses with assumptions + distinguishing evidence,
limitations, open questions), synthesis (claim-level refs, method,
validation, guarantees), experiment history. Missing states are explicit
(`primary: null`, `experiment: null`, `available: false`,
`applicable: false`) — never filled with placeholder data. No tokens,
internal objects, or raw Qloo payloads are exposed.
