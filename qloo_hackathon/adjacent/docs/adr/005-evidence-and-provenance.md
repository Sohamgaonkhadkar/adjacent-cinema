# ADR-005: Evidence and Provenance

## Status

FROZEN

## Date

4 October 2026

## Decision

Every displayed number carries a call_id or source. Three layers:
1. **Inline** — every rendered number has a data-call-id attribute
2. **Attribution** — `feature.explainability=true` provides per-signal attribution
3. **Export** — `Copy as JSON` emits the full run with all trace rows

## Rationale

1. **Trust.** The product's value proposition is "data-informed audience hypotheses." If any number is unverifiable, the whole product is untrustworthy.
2. **Honesty differentiator.** Competitors present numbers without provenance. Adjacent shows exactly where each number came from.
3. **Insufficiency is a feature.** When evidence is insufficient, Adjacent says so rather than guessing.

## Implementation

- `domain/ledger.py:ProvenanceLedger` — tracks every displayed number
- `evidence.py` — three gates (resolution, taste_profile, candidate_cohorts)
- `qloo/trace.py` — TraceRow for every Qloo call
- `domain/reasons.py` — machine-readable rejection codes

## Rules

1. No number is displayed without a backing source
2. Fixture data carries `data_status="fixture"`, never confused with measured data
3. Numbers without backing are flagged as "unverified" in the provenance audit
4. Insufficiency is distinct from operational errors (budget_exhausted, error)
5. A failed tool produces an empty state, not a guess

## Alternative Considered

- Trust LLM-generated numbers — rejected: unauditable
- Show numbers without provenance — rejected: violates trust requirement
- Only show provenance on request — rejected: provenance must be default

## Consequence

- The provenance ledger adds ~100 lines of code
- Every rendering function must register its numbers with the ledger
- The evidence panel is generated from trace rows and ledger data

## Trigger to Revisit

Never. Provenance is a core architectural invariant.