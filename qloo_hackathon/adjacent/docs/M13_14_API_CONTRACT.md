# M13.14 — API Contract (delta over `M13_13_API_CONTRACT.md`)

All changes additive. Investigation contract, synthesis status/route shapes,
observation/evaluation contracts unchanged.

## Synthesis schema 2.1

`POST /creator/synthesize` 200 → `synthesis` gains one required key:

```
experiment_proposal: {
  kind: "test" | "information_gathering",
  hypothesis: string,          // non-empty for kind "test"; empty for i-g
  action_plan: string,         // concrete action / what to collect
  success_criteria: string,    // non-empty for kind "test"
  observation_window: string,  // non-empty for kind "test"
  falsification: string,       // non-empty for kind "test"
  relevant_metrics: string[],  // 1–8 observable metrics/observations
  assumptions: string[],       // ≤6
  limitations: string
}
```

Guarantees: `kind:"test"` cannot survive validation when the investigation
abstained; schema-2.0 payloads are rejected (labelled
`deterministic_fallback`, never a silent pass); fallback proposals are
validator-valid and abstention-consistent. `metadata` shape unchanged
(method / validation / guarantees / llm_error).

## POST /experiments — additive request fields

```
synthesis_snapshot?: object   // sanitised server-side to an allowlist:
  // investigation_id, source_run_id, schema_version, method, provider_kind,
  // model, validation, summary, hypothesis_restated, claims[≤12, trimmed],
  // caveats, limitations, evidence_refs, data_status, experiment_proposal
  // server adds: evidence_ref_status, unresolved_evidence_refs?
adopted_proposal?: object     // the model's ORIGINAL proposal (proposal keys)
```

Stored in `provenance` (existing JSON column — no DB schema change):

```
provenance.synthesis_snapshot     // immutable once saved; replays return the
                                  // original record, never a mutated snapshot
provenance.adopted_proposal       // original proposal, distinct from saved fields
provenance.creator_edits          // ["hypothesis", ...] fields where the saved
                                  // value differs from the proposal — edits are
                                  // attributed to the creator, not the model
provenance.adoption               // {origin: "model_proposal", method}
```

Reference-integrity rules for snapshots: with `source_run_id`, every
snapshot/claim evidence ref is verified against the run's recorded trace;
unresolvable refs move to `snapshot.unresolved_evidence_refs` and are never
stored as proof. Without it, `evidence_ref_status` says `"unverified —
source run not available"`. Keys outside the allowlist (e.g. anything
credential-shaped) are dropped server-side.

Preserved semantics: `request_id` idempotency AND one saved decision per
`source_run_id` (dedupe returns the original record with
`duplicate: true`); zero≠missing observations; supersession history; no
experiment is ever marked run/validated by adoption.

## Frontend types (frontend/lib/api.ts, types/adjacent.ts)

`SynthesisExperimentProposal`, `SynthesisBrief.experiment_proposal`,
`InvestigationData.investigation_id` (backend already sent it). The Decision
Brief panel implements the draft/adopt/confirm flow; draft state is
client-side only until the creator confirms.
