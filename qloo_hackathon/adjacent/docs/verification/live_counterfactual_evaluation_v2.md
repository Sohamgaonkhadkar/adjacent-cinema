# Live Qloo Counterfactual Evaluation

- Generated: **2026-10-29T12:08:37.623994+00:00**
- Schema: **adjacent.live-counterfactual-evaluation/2**
- Programmes attempted: **9**
- Programmes evaluable: **8**
- Failed / not evaluable: **1**
- Affinity-withheld runs that changed the winner: **0 / 8**
- Popularity-only runs that changed the winner: **8 / 8**
- Affinity-withheld runs that left the winner unchanged: **8 / 8**
- Mean top-5 overlap (affinity withheld / popularity only): **1.000 / 0.950**
- Mean Kendall tau-b (affinity withheld / popularity only): **1.000 / -1.000**
- Programmes with at least one cohort suppressed by the affinity gate: **0 / 8**
- Cohorts suppressed by the affinity gate across all programmes: **0**
- Programmes where affinity decided at least one adjacent ranking pair: **0 / 8**

## Per-programme results

| Programme | Status | Resolved | App trace rows | Production winner | Winner without affinity | Changed? | Popularity-only winner | Changed? | Affinity-decided pairs | Stability | Top-5 kept (withheld) | tau-b (withheld) |
|---|---|---:|---:|---|---|---|---|---|---:|---|---:|---:|
| international-stories | evaluable | 4/4 | 22 | book · Dear America: Notes of an Undocumented Citizen | book · Dear America: Notes of an Undocumented Citizen | False | movie · The Great Beauty | True | 0/5 | stable | 5/5 | 1.00 |
| psychological-tension | evaluable | 4/4 | 17 | artist · Kirin J Callinan | artist · Kirin J Callinan | False | movie · Lover | True | 0/2 | stable | 3/3 | 1.00 |
| auteur-cross-cultural | evaluable | 3/4 | 17 | artist · Alan Sparhawk | artist · Alan Sparhawk | False | movie · This Is Not a Burial, It's a Resurrection | True | 0/2 | stable | 3/3 | 1.00 |
| documentary-essay | evaluable | 3/4 | 16 | book · VALIS | book · VALIS | False | movie · The White Diamond | True | 0/2 | stable | 3/3 | 1.00 |
| horror-folk | evaluable | 3/4 | 17 | artist · Violet Town | artist · Violet Town | False | movie · Baskin | True | 0/2 | stable | 3/3 | 1.00 |
| animation-family | evaluable | 4/4 | 21 | artist · Loomer | artist · Loomer | False | brand · Harry's | True | 0/5 | stable | 5/5 | 1.00 |
| romance-classic | evaluable | 4/4 | 17 | artist · Sian Alice Group | artist · Sian Alice Group | False | movie · Spring in a Small Town | True | 0/2 | fragile | 3/3 | 1.00 |
| music-cult | evaluable | 3/4 | 20 | book · Jailbird | book · Jailbird | False | artist · The Fire Engines | True | 0/4 | stable | 5/5 | 1.00 |
| regional-language | not_evaluable | 0/4 | 8 | — | — | — | — | — | — | — | — | — |

## Affinity-gate and winner-signal audit

The gate audit is separate from the order-only counterfactual: it records structurally large groupings that did not clear the production evidence gate. It holds the returned candidate pool fixed and does not simulate fresh Qloo retrieval. Winner affinity is shown only alongside its own entity-type context; raw affinity values are not comparable across domains or runs.

| Programme | Gate-suppressed groupings | Winning context | Winner mean affinity (context-local) | Qualifying / scored members | Winner explainability status |
|---|---:|---|---:|---:|---|
| international-stories | 0 | urn:entity:book | 0.850929 | 12/12 | not_requested_limit |
| psychological-tension | 0 | urn:entity:artist | 0.86601 | 49/49 | not_requested_limit |
| auteur-cross-cultural | 0 | urn:entity:artist | 0.886144 | 50/50 | not_requested_limit |
| documentary-essay | 0 | urn:entity:book | 0.828588 | 17/17 | not_requested_limit |
| horror-folk | 0 | urn:entity:artist | 0.877328 | 50/50 | not_requested_limit |
| animation-family | 0 | urn:entity:artist | 0.842112 | 50/50 | not_requested_limit |
| romance-classic | 0 | urn:entity:artist | 0.880998 | 50/50 | not_requested_limit |
| music-cult | 0 | urn:entity:book | 0.84337 | 19/19 | not_requested_limit |
| regional-language | 0 | — | — | — | — |

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

**documentary-essay**

| Context | Requested candidates | Returned candidates | Explainability status |
|---|---:|---:|---|
| urn:entity:book | 50 | 50 | not_requested_limit |
| urn:entity:movie | 50 | 50 | not_requested_limit |

**horror-folk**

| Context | Requested candidates | Returned candidates | Explainability status |
|---|---:|---:|---|
| urn:entity:artist | 50 | 50 | not_requested_limit |
| urn:entity:brand | 50 | 50 | not_requested_limit |
| urn:entity:movie | 50 | 50 | not_requested_limit |

**animation-family**

| Context | Requested candidates | Returned candidates | Explainability status |
|---|---:|---:|---|
| urn:entity:artist | 50 | 50 | not_requested_limit |
| urn:entity:book | 50 | 50 | not_requested_limit |
| urn:entity:brand | 50 | 50 | not_requested_limit |
| urn:entity:movie | 50 | 50 | not_requested_limit |
| urn:entity:tv_show | 50 | 50 | not_requested_limit |

**romance-classic**

| Context | Requested candidates | Returned candidates | Explainability status |
|---|---:|---:|---|
| urn:entity:artist | 50 | 50 | not_requested_limit |
| urn:entity:brand | 50 | 50 | not_requested_limit |
| urn:entity:movie | 50 | 50 | not_requested_limit |

**music-cult**

| Context | Requested candidates | Returned candidates | Explainability status |
|---|---:|---:|---|
| urn:entity:artist | 50 | 50 | not_requested_limit |
| urn:entity:book | 50 | 50 | not_requested_limit |
| urn:entity:brand | 50 | 50 | not_requested_limit |
| urn:entity:movie | 50 | 50 | not_requested_limit |

**regional-language**

No scoring-context record was available.

## Application trace IDs (scoped to each run)

### international-stories

Status: **evaluable**; data status: **measured**.

Run-scoped application trace IDs: local-c001, local-c002, local-c003, local-c004, local-c005, local-c006, local-c007, local-c008, local-c009, local-c010, local-c011, local-c012, local-c013, local-c014, local-c015, local-c016, local-c017, local-c018, local-c019, local-c020, local-c021, local-c022

### psychological-tension

Status: **evaluable**; data status: **measured**.

Run-scoped application trace IDs: local-c001, local-c002, local-c003, local-c004, local-c005, local-c006, local-c007, local-c008, local-c009, local-c010, local-c011, local-c012, local-c013, local-c014, local-c015, local-c016, local-c017

### auteur-cross-cultural

Status: **evaluable**; data status: **measured**.

Run-scoped application trace IDs: local-c001, local-c002, local-c003, local-c004, local-c005, local-c006, local-c007, local-c008, local-c009, local-c010, local-c011, local-c012, local-c013, local-c014, local-c015, local-c016, local-c017

### documentary-essay

Status: **evaluable**; data status: **measured**.

Run-scoped application trace IDs: local-c001, local-c002, local-c003, local-c004, local-c005, local-c006, local-c007, local-c008, local-c009, local-c010, local-c011, local-c012, local-c013, local-c014, local-c015, local-c016

### horror-folk

Status: **evaluable**; data status: **measured**.

Run-scoped application trace IDs: local-c001, local-c002, local-c003, local-c004, local-c005, local-c006, local-c007, local-c008, local-c009, local-c010, local-c011, local-c012, local-c013, local-c014, local-c015, local-c016, local-c017

### animation-family

Status: **evaluable**; data status: **measured**.

Run-scoped application trace IDs: local-c001, local-c002, local-c003, local-c004, local-c005, local-c006, local-c007, local-c008, local-c009, local-c010, local-c011, local-c012, local-c013, local-c014, local-c015, local-c016, local-c017, local-c018, local-c019, local-c020, local-c021

### romance-classic

Status: **evaluable**; data status: **measured**.

Run-scoped application trace IDs: local-c001, local-c002, local-c003, local-c004, local-c005, local-c006, local-c007, local-c008, local-c009, local-c010, local-c011, local-c012, local-c013, local-c014, local-c015, local-c016, local-c017

### music-cult

Status: **evaluable**; data status: **measured**.

Run-scoped application trace IDs: local-c001, local-c002, local-c003, local-c004, local-c005, local-c006, local-c007, local-c008, local-c009, local-c010, local-c011, local-c012, local-c013, local-c014, local-c015, local-c016, local-c017, local-c018, local-c019, local-c020

### regional-language

Status: **not_evaluable**; data status: **measured**.

Run-scoped application trace IDs: local-c001, local-c002, local-c003, local-c004, local-c005, local-c006, local-c007, local-c008

Reason: This run produced no candidate cohorts, so there is no recommendation to challenge. Nothing has been inferred in place of the missing evidence.

## Interpretation and limits

- The counterfactual holds the retrieved and admitted candidate pool fixed; it tests ranking sensitivity, not what a fresh Qloo query would retrieve.
- A changed winner is not proof that Qloo is correct or that the recommendation will succeed.
- An unchanged winner is still reported and is not presented as evidence of Qloo necessity.
- Popularity-only uses the same candidates and returned popularity fields; it is not an external ground-truth or business baseline.
- No attendance, audience size, conversion, revenue, causal effect, or ROI is measured.
- All runs, including failures and insufficient-evidence results, remain in the report. Fixture data is never substituted into a live report.

A result with no winner change is retained as-is; it is not described as evidence that Qloo was necessary. These runs describe ranking sensitivity for the selected programmes, not downstream success.
