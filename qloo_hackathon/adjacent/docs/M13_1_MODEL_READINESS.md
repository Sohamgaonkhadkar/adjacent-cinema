# M13.1: Model Readiness Assessment

**Date:** 2026-10-07

---

## READINESS GATES

| Gate | Required | Status | Evidence |
|------|----------|--------|---------|
| Real outcome labels | Yes | **PARTIAL** | Kaggle has tickets_sold but anonymized |
| Stable event identifiers | Yes | **FAIL** | Kaggle uses film_code, cinema_code (not resolvable) |
| Reproducible entity resolution | Yes | **FAIL** | Cannot map film_code → Qloo entity |
| Enough observations | Yes | **PASS** | 142,524 rows |
| Outcome variation | Yes | **PASS** | Occupancy 0%–100% |
| No synthetic labels | Yes | **PASS** | Kaggle data is real |
| No target leakage | Yes | **POSSIBLE** | Temporal split feasible |
| Temporal train/test split | Yes | **PASS** | 8 months of data |
| Venue-level leakage control | Yes | **UNKNOWN** | Anonymized venues |

---

## CLASSIFICATION

### **NOT_ML_READY**

The only publicly available dataset with real screening-level attendance (Kaggle Cinema Tickets) uses anonymized identifiers that prevent joining to Qloo entities. The fundamental pipeline:

```
Qloo cultural signal → Adjacent ranking → ??? → actual attendance
```

has a broken link at `???`. We cannot measure whether Qloo signals predict attendance because we cannot connect them.

---

## WHAT WOULD CHANGE THIS

| Scenario | Effort | Readiness impact |
|----------|--------|-----------------|
| Kaggle publishes film title mapping | External | ML_READY |
| Access to Poland dataset | Partnership | ML_READY |
| UK cinema chain data partnership | Business development | ML_READY |
| Apify sold_out scraping | Engineering (1-2 days) | ML_PARTIALLY_READY (weak proxy) |
| Cinema Context + outcome data | External | ML_READY (if outcome added) |

---

## CURRENT RANKER EVALUATION

The current deterministic ranker (M12.8/M12.9) has these documented weaknesses:

| Weakness | Severity | Status |
|----------|----------|--------|
| Arbitrary weighting (0.6/0.2/0.2) | Medium | Measured in M12.9 |
| No outcome validation | High | Cannot fix without data |
| Popularity sensitivity | Medium | Documented in M12.9 |
| qualifying_ratio = zero differentiating power | Low | Documented, component is inert |
| Cohort-level signals masquerading as candidate evidence | Low | Correctly labelled in M12.9 |

**The ranker is not "wrong" — it is unvalidated.** It makes reasonable policy choices but cannot prove they predict attendance.

---

## RECOMMENDED MODEL ARCHITECTURE (IF DATA BECOMES AVAILABLE)

**Preferred:** Learning-to-rank (LightGBM Ranker / XGBoost ranking)

**Feature groups:**
- Qloo: affinity, popularity, domain, candidate tags, cohort evidence
- Programme: composition, film metadata, historical patterns
- Venue: city, capacity, characteristics, historical performance
- Temporal: day, month, season, release age

**Evaluation:** Venue/time-grouped NDCG@K, Kendall τ

**Baseline comparison:**
1. Metadata-only baseline
2. Affinity-only baseline
3. Current deterministic ranker
4. Learned model

**Keep learned model only if it materially improves held-out performance over the deterministic ranker.**

---

## WHAT WOULD MAKE US REJECT ML

1. No accessible dataset with real outcome labels + joinable identifiers
2. Learned model does not outperform affinity-only baseline
3. Venue-level features dominate Qloo features (Qloo adds no value)
4. Outcome variance is too low (all screenings sell similar tickets)

---

## FINAL RESEARCH ANSWER

**D. There is currently insufficient real data to validate whether Qloo affinity predicts attendance.**

This is a genuine limitation. The Adjacent system identifies cultural opportunities using Qloo evidence. Whether those opportunities translate to cinema attendance requires empirical outcome data that is not publicly available at the required granularity (screening-level + venue-level + joinable identifiers).

The system is architecturally ready for outcome validation. The missing piece is data access.

---

**Status:** COMPLETE