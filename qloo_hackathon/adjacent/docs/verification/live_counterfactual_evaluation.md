# Live Qloo Counterfactual Evaluation

- Generated: **2026-10-26T20:14:32.044257+00:00**
- Schema: \`adjacent.live-counterfactual-evaluation/1\`
- Programmes attempted: **3**
- Programmes evaluable: **3**
- Failed / not evaluable: **0**
- Affinity-withheld runs that changed the winner: **0 / 3**
- Popularity-only runs that changed the winner: **3 / 3**
- Programmes with at least one cohort suppressed by the affinity gate: **0 / 3**
- Cohorts suppressed by the affinity gate across all programmes: **0**
- Programmes where affinity decided at least one adjacent ranking pair: **0 / 3**

## Per-programme results

| Programme | Status | Resolved | App trace rows | Production winner | Winner without affinity | Changed? | Popularity-only winner | Changed? | Affinity-decided pairs | Stability |
|---|---|---:|---:|---|---|---|---|---|---:|---|
| international-stories | evaluable | 4/4 | 20 | book · Dear America: Notes of an Undocumented Citizen | book · Dear America: Notes of an Undocumented Citizen | False | movie · The Great Beauty | True | 0/5 | stable |
| psychological-tension | evaluable | 4/4 | 16 | artist · Kirin J Callinan | artist · Kirin J Callinan | False | movie · Lover | True | 0/2 | stable |
| auteur-cross-cultural | evaluable | 3/4 | 16 | artist · Alan Sparhawk | artist · Alan Sparhawk | False | movie · This Is Not a Burial, It's a Resurrection | True | 0/2 | stable |

## Affinity-gate and winner-signal audit

The gate audit is separate from the order-only counterfactual: it records structurally large groupings that did not clear the production evidence gate. It holds the returned candidate pool fixed and does not simulate fresh Qloo retrieval. Winner affinity is shown only alongside its own entity-type context; raw affinity values are not comparable across domains or runs.

| Programme | Gate-suppressed groupings | Winning context | Winner mean affinity (context-local) | Qualifying / scored members | Winner explainability status |
|---|---:|---|---:|---:|---|
| international-stories | 0 | urn:entity:book | 0.850929 | 12/12 | not_requested_limit |
| psychological-tension | 0 | urn:entity:artist | 0.86601 | 49/49 | not_requested_limit |
| auteur-cross-cultural | 0 | urn:entity:artist | 0.886144 | 50/50 | not_requested_limit |

### Scoring-context coverage

Per-context counts show which Qloo scoring contexts ran and whether optional provider explainability was returned/requested/omitted. Status strings come from the application trace; they are not a quality rating.

**international-stories**

| Context | Requested candidates | Returned candidates | Explainability status |
|---|---:|---:|---|
| urn:entity:artist | 50 | 50 | not_requested_limit |
| urn:entity:book | 50 | 50 | not_requested_limit |
| urn:entity:brand | 50 | 50 | not_requested_limit |
| urn:entity:movie | 50 | 50 | not_requested_limit |
| urn:entity:podcast | 50 | 50 | not_requested_limit |

**psychological-tension**

| Context | Requested candidates | Returned candidates | Explainability status |
|---|---:|---:|---|
| urn:entity:artist | 50 | 50 | not_requested_limit |
| urn:entity:brand | 50 | 50 | not_requested_limit |
| urn:entity:movie | 50 | 50 | not_requested_limit |

**auteur-cross-cultural**

| Context | Requested candidates | Returned candidates | Explainability status |
|---|---:|---:|---|
| urn:entity:artist | 50 | 50 | not_requested_limit |
| urn:entity:brand | 50 | 50 | not_requested_limit |
| urn:entity:movie | 50 | 50 | not_requested_limit |

## Application trace IDs (scoped to each run)

### international-stories

Status: **evaluable**; data status: **measured**.

Run-scoped application trace IDs: local-c001, local-c002, local-c003, local-c004, local-c005, local-c006, local-c007, local-c008, local-c009, local-c010, local-c011, local-c012, local-c013, local-c014, local-c015, local-c016, local-c017, local-c018, local-c019, local-c020

### psychological-tension

Status: **evaluable**; data status: **measured**.

Run-scoped application trace IDs: local-c001, local-c002, local-c003, local-c004, local-c005, local-c006, local-c007, local-c008, local-c009, local-c010, local-c011, local-c012, local-c013, local-c014, local-c015, local-c016

### auteur-cross-cultural

Status: **evaluable**; data status: **measured**.

Run-scoped application trace IDs: local-c001, local-c002, local-c003, local-c004, local-c005, local-c006, local-c007, local-c008, local-c009, local-c010, local-c011, local-c012, local-c013, local-c014, local-c015, local-c016

## Interpretation and limits

- The counterfactual holds the retrieved and admitted candidate pool fixed; it tests ranking sensitivity, not what a fresh Qloo query would retrieve.
- A changed winner is not proof that Qloo is correct or that the recommendation will succeed.
- An unchanged winner is still reported and is not presented as evidence of Qloo necessity.
- Popularity-only uses the same candidates and returned popularity fields; it is not an external ground-truth or business baseline.
- No attendance, audience size, conversion, revenue, causal effect, or ROI is measured.
- All runs, including failures and insufficient-evidence results, remain in the report. Fixture data is never substituted into a live report.

A result with no winner change is retained as-is; it is not described as evidence that Qloo was necessary. These runs describe ranking sensitivity for the selected programmes, not downstream success.

**Result to preserve:** the current production winner stayed the same when affinity-derived ordering keys were removed in all three samples, and no structurally sized cohort was excluded by the affinity gate in those runs. A popularity-only ordering chose a different winner in each sample. This shows a difference from that deliberately limited popularity baseline, but does not establish that affinity alone determines the recommendations.

In all **11/11** scoring contexts, per-seed explainability was \`not_requested_limit\`: each context requested 50 candidate IDs, above the 12-candidate bound. Therefore this evaluation includes Qloo's measured affinity scoring but does **not** provide per-seed attribution for these winners. One reference film, \`Taipei Story\`, remained unresolved and was not substituted with fixture data.
