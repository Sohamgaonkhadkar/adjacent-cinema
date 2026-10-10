# M13.2: Outcome Bridge

**Date:** 2026-10-07
**Status:** COMPLETE

---

## BRIDGE STATUS

### Path 1: Kaggle → Qloo (BLOCKED)

```
Kaggle film_code → ??? → film title → Qloo entity → cultural evidence
```

**Status:** BLOCKED. No identifier mapping exists.

### Path 2: UK Proxy → Qloo (FEASIBLE)

```
Prince Charles showtime → film title → EntityResolver → Qloo entity → cultural evidence
                                                      → sold_out proxy
```

**Status:** FEASIBLE. Requires scraper + resolver pipeline.

### Path 3: Prospective Logging (READY TO BUILD)

```
Adjacent Programme Bet → recommendation logged → venue runs event → outcome recorded
```

**Status:** Schema designed. Not yet implemented in production.

---

## DIRECT OUTCOME OBSERVATIONS

| Count | Source | Status |
|-------|--------|--------|
| 0 | Kaggle (blocked) | UNJOINABLE |
| 0 | UK proxy (not yet scraped) | NOT_YET_IMPLEMENTED |
| 0 | Prospective (not yet collected) | NOT_YET_IMPLEMENTED |

**Total direct outcome observations: 0**

---

## STRONG PROXY OBSERVATIONS

| Count | Source | Status |
|-------|--------|--------|
| 0 | Prince Charles sold_out | NOT_YET_SCRAPED |
| 0 | Apify UK scraper | NOT_YET_SCRAPED |

**Total strong proxy observations: 0**

---

## WEAK PROXY OBSERVATIONS

| Count | Source | Status |
|-------|--------|--------|
| 0 | Social media engagement | NOT_COLLECTED |
| 0 | Reviews | NOT_COLLECTED |

**Total weak proxy observations: 0**

---

## WHAT EXISTS TODAY

1. Prince Charles Cinema website shows real sold_out flags for current/future screenings
2. Adjacent can resolve film titles to Qloo entities
3. Adjacent can compute cultural evidence scores
4. The join path is architecturally feasible

**Missing:** A scraper to collect the data over time.

---

## QLOO VALUE TEST DESIGN

### Central Question
Does Qloo add predictive information beyond normal film metadata and historical venue behavior?

### Experimental Design (when data exists)

**Baseline 0:** Historical venue popularity (how often does this venue sell out?)
**Baseline 1:** Film metadata only (genre, year, rating, director popularity)
**Baseline 2:** Qloo affinity only
**Baseline 3:** Current Adjacent deterministic ranker
**Baseline 4:** Qloo + metadata

**Target:** sold_out (binary) or occupancy_rate (if capacity known)

**Evaluation:** Venue/time-grouped PR AUC, ROC AUC

**Valid results:**
- Qloo adds value → keep Qloo features
- Qloo adds no measurable value → Qloo is discovery-only
- Qloo helps discovery but not outcomes → honest limitation
- Insufficient evidence → collect more data

**ALL FOUR ARE ACCEPTABLE.**

---

## LEAKAGE CONTROLS

| Risk | Mitigation |
|------|-----------|
| Same film across train/test | Temporal split — train on earlier dates, test on later |
| Same venue across splits | Venue-grouped evaluation |
| Future Qloo information | Use only Qloo data available at prediction time |
| Future popularity | Use only popularity at screening time |
| Programme context leakage | Each screening scored independently |

---

**Status:** COMPLETE