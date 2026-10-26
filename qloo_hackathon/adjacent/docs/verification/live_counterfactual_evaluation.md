# Live Qloo Counterfactual Evaluation

- Generated: **2026-10-26T19:08:21.988024+00:00**
- Schema: `adjacent.live-counterfactual-evaluation/1`
- Programmes attempted: **3**
- Programmes evaluable: **3**
- Failed / not evaluable: **0**
- Affinity-withheld runs that changed the winner: **0 / 3**
- Popularity-only runs that changed the winner: **3 / 3**

## Per-programme results

| Programme | Status | Resolved | App trace rows | Production winner | Winner without affinity | Changed? | Popularity-only winner | Changed? | Affinity-decided pairs | Stability |
|---|---|---:|---:|---|---|---|---|---|---:|---|
| international-stories | evaluable | 4/4 | 20 | book · Dear America: Notes of an Undocumented Citizen | book · Dear America: Notes of an Undocumented Citizen | false | movie · The Great Beauty | true | 0/5 | stable |
| psychological-tension | evaluable | 4/4 | 16 | artist · Kirin J Callinan | artist · Kirin J Callinan | false | movie · Lover | true | 0/2 | stable |
| auteur-cross-cultural | evaluable | 3/4 | 16 | artist · Alan Sparhawk | artist · Alan Sparhawk | false | movie · This Is Not a Burial, It's a Resurrection | true | 0/2 | stable |

The third programme left **Taipei Story unresolved**. It remains visible as an unresolved input and was not silently replaced with fixture data.

## What these results mean

Across these three measured runs, withholding affinity-derived ordering signals did not change the winner, and no adjacent pair in the returned ranking was separated first by an affinity-derived ordering key. The popularity-only baseline selected a different winner in all three runs.

This is useful diagnostic evidence, but **it does not demonstrate that affinity is the deciding factor in the current ranking**. It shows that the current ranking differs from the popularity-only baseline while the more specific affinity-withheld test did not change the winner in these samples. Further evaluation should investigate how the admission gate, evidence-strength ordering, novelty, and affinity interact. The ranking must not be changed just to force a favourable counterfactual.

## Application trace IDs (scoped to each run)

Trace IDs are application-generated, repeat from `local-c001` across separate runs, and are **not Qloo-issued request IDs**.

### international-stories

Status: `evaluable`; data status: `measured`; application trace rows: **20**.

`local-c001`, `local-c002`, `local-c003`, `local-c004`, `local-c005`, `local-c006`, `local-c007`, `local-c008`, `local-c009`, `local-c010`, `local-c011`, `local-c012`, `local-c013`, `local-c014`, `local-c015`, `local-c016`, `local-c017`, `local-c018`, `local-c019`, `local-c020`

### psychological-tension

Status: `evaluable`; data status: `measured`; application trace rows: **16**.

`local-c001`, `local-c002`, `local-c003`, `local-c004`, `local-c005`, `local-c006`, `local-c007`, `local-c008`, `local-c009`, `local-c010`, `local-c011`, `local-c012`, `local-c013`, `local-c014`, `local-c015`, `local-c016`

### auteur-cross-cultural

Status: `evaluable`; data status: `measured`; application trace rows: **16**.

`local-c001`, `local-c002`, `local-c003`, `local-c004`, `local-c005`, `local-c006`, `local-c007`, `local-c008`, `local-c009`, `local-c010`, `local-c011`, `local-c012`, `local-c013`, `local-c014`, `local-c015`, `local-c016`

## Method and limits

- The evaluator used the existing live pipeline and Decision Challenge over each run's cached candidate pool; counterfactual calculation made zero additional Qloo calls.
- The counterfactual holds the retrieved and admitted candidate pool fixed. It tests ranking sensitivity, not what a fresh Qloo query would retrieve.
- A changed winner is not proof that Qloo is correct or that a recommendation will succeed.
- Popularity-only uses the same candidates and returned popularity fields; it is not external ground truth or a business baseline.
- No attendance, audience size, conversion, revenue, causal effect, or ROI is measured.
- All runs, including unresolved inputs, are retained. Fixture data is never substituted into a live report.
