# M13.4: Leakage Audit

**Date:** 2026-10-07

---

## LEAKAGE PREVENTION MECHANISM

### Rule

For each screening observation, only use a Qloo feature snapshot where:

```
retrieved_at <= source_timestamp
```

If the latest Qloo snapshot was retrieved AFTER the screening observation, mark as `FUTURE_FEATURE_UNAVAILABLE` and exclude from prediction analysis.

### Implementation

```python
feature = repo.get_latest_qloo_feature(film_key, before=source_timestamp)
```

The `before` parameter enforces temporal ordering.

---

## AUDIT RESULTS

| Feature Status | Screenings | % |
|---------------|-----------|---|
| AVAILABLE_AT_PREDICTION_TIME | 0 | 0.0% |
| FUTURE_FEATURE_UNAVAILABLE | 9 | 1.2% |
| NO_FEATURE | 754 | 98.8% |
| **Total** | **763** | |

---

## FUTURE FEATURE CONTAMINATION: ZERO

All 9 screenings with verified Qloo entities have `FUTURE_FEATURE_UNAVAILABLE` — their Qloo features were retrieved AFTER the screening observations.

**Zero observations use future Qloo information.**

This is the correct behavior: Qloo features retrieved today cannot be used to predict outcomes that were observed yesterday.

---

## TEMPORAL ORDERING VERIFICATION

| Check | Result |
|-------|--------|
| Observations using future features | 0 |
| Observations using prediction-time features | 0 |
| Observations with no features | 754 |
| Future feature contamination rate | 0.0% |

---

## IMPLICATIONS

1. **No leakage** — The benchmark is leakage-safe
2. **No prediction-time features yet** — Because Qloo resolution happened AFTER screening collection
3. **Future features correctly excluded** — When features are available, they are properly marked

**To get prediction-time features:** Collect Qloo features BEFORE scraping screenings, or accumulate features over time and use historical snapshots.

---

## RECOMMENDATION

For future collections:
1. Run Qloo resolution weekly (creates historical snapshots)
2. Run PCC scraping daily/weekly
3. Use Qloo snapshots from BEFORE the observation time

This will naturally create prediction-time features as the pipeline accumulates data.

---

**Status:** Leakage audit PASS. Zero future-feature contamination.