# M13.14 — Model-to-Decision Lifecycle

The three decision layers and how they connect. This is the authoritative
description of the workflow; `M13_12_MODEL_ARCHITECTURE.md` and
`M13_13_MODEL_QUALITY.md` remain valid for the agent and synthesis internals.

## The layers

| Layer | Artifact | Mutability |
|---|---|---|
| **A — Investigation** | `result.investigation` on the run record | **Immutable.** Written once by the deterministic pipeline (refs pre-verified against the run trace). Synthesis only reads it; adoption never touches it (regression-tested: run result identical before/after adoption). |
| **B — Decision Brief** | `/creator/synthesize` response (schema 2.1) | Ephemeral until adopted. Method-labelled (`live_llm` / `stub` / `deterministic_fallback`), claim-level validated. |
| **C — Saved decision** | `POST /experiments` record | Append-only history; idempotent twice over (request_id replay AND one saved decision per `source_run_id` — the second save returns the ORIGINAL, never overwrites). |

## Structured experiment proposals (schema 2.1)

`synthesis.experiment_proposal` — one vocabulary, deliberately mirroring the
existing Test Card / `SaveExperimentRequest` fields so adoption is a 1:1
mapping, not a schema translation:

```
{kind: "test" | "information_gathering",
 hypothesis, action_plan, success_criteria, observation_window,
 falsification,              // all non-empty for kind "test"
 relevant_metrics[],         // non-empty, ≤8, observable metrics/observations
 assumptions[], limitations}
```

Validation (deterministic, post-model):
- `kind: "test"` is **rejected outright** when the investigation abstained —
  a model cannot manufacture a positioning experiment the evidence does not
  support. The only honest proposal then is `information_gathering`, which
  must state what to collect and is labelled as *not* a positioning test.
- v2.0 payloads (no `experiment_proposal`) are rejected → labelled fallback.
- The deterministic fallback emits a proposal too: kind `test` mirroring the
  investigation's experiment when supported; kind `information_gathering`
  with an empty hypothesis when abstaining. The fallback passes the same
  validator (parity-tested).

**A proposal is a proposal.** Nothing in the system records a proposed
experiment as run or validated; status distinctions (proposed → adopted →
saved → observed → evaluated) live in the experiment record's real fields
(`status`, observations, evaluations).

## Adoption workflow (implemented)

1. Creator completes an investigation (Layer A) and sees the deterministic
   Test Card (existing save path unchanged).
2. Creator optionally generates a Decision Brief (Layer B) — panel shows
   method + validation + claims.
3. Panel renders the proposal, labelled **"PROPOSED EXPERIMENT (not yet
   saved)"** or **"PROPOSED NEXT STEP — INFORMATION GATHERING (no supported
   hypothesis)"**.
4. **"Use this experiment"** prepares an **editable draft** — nothing is
   persisted at this point.
5. Creator reviews/edits the four decision fields and explicitly confirms.
6. Save sends: decision fields + `investigation_summary` + `evidence_refs`
   + `synthesis_snapshot` (sanitised) + `adopted_proposal` (the model's
   ORIGINAL proposal).
7. The route stores the snapshot in provenance, verifies every snapshot ref
   against the source run's recorded trace (unresolved →
   `snapshot.unresolved_evidence_refs`, never stored as proof), and computes
   `creator_edits` — the fields where the saved value differs from the
   proposal. **The model is never credited with the creator's edits.**
8. Replay/duplicate saves return the original record; a tampered snapshot in
   a replay cannot mutate the stored one (E2E-verified).

## Snapshot contents (allowlisted — no object dumps, no credentials)

`investigation_id, source_run_id, schema_version, method, provider_kind,
model, validation, summary, hypothesis_restated, claims (trimmed to
statement/claim_type/evidence_refs/rationale/limitations, ≤12), caveats,
limitations, evidence_refs (+ `evidence_ref_status`,
`unresolved_evidence_refs`), data_status, experiment_proposal`. Keys outside
the allowlist are dropped server-side — a credential-shaped key injected by
a client is stripped (regression-tested). Without a `source_run_id` the
snapshot is kept but labelled `evidence_ref_status: "unverified — source run
not available"`.

## Decision chain for later evaluation

investigation (immutable, Layer A) → synthesis snapshot (what the model
proposed, with method + validation) → adopted proposal + creator_edits
(what the creator chose) → saved experiment (planned action/criteria/window)
→ observations (zero≠missing≠partial≠unavailable, YouTube source + period
metadata preserved) → evaluations (supersede with history, correlation ≠
causation). No component claims an outcome was caused by the creative
choice; evaluation outcomes remain SUPPORTED / CONTRADICTED / INCONCLUSIVE
over pre-registered criteria.
