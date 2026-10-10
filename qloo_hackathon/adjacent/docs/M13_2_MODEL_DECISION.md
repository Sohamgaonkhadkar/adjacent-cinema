# M13.2: Model Decision

**Date:** 2026-10-07
**Status:** COMPLETE

---

## ML READINESS CLASSIFICATION

### **NOT_ML_READY**

| Gate | Required | Status |
|------|----------|--------|
| Real outcome labels | Yes | ❌ 0 observations |
| Stable identifiers | Yes | ❌ Kaggle blocked |
| Reproducible entity resolution | Yes | ✅ Adjacent resolver works |
| Enough observations | Yes | ❌ 0 |
| Meaningful target variance | Yes | ❌ No target data |
| No synthetic labels | Yes | ✅ |
| Temporal split possible | Yes | ✅ (when data exists) |
| Venue leakage controlled | Yes | ✅ (design exists) |
| Qloo features available | Yes | ✅ |
| Baseline measurable | Yes | ❌ No data to measure against |

---

## CURRENT RANKER EVALUATION

### Strengths
- Deterministic and reproducible
- Transparent formula with documented weights
- Policy-invariance tested (M12.9)
- Domain-level winner robust across 4 policies
- No synthetic labels
- No hand-coded domain preferences (M12.8)

### Documented Weaknesses

| Weakness | Severity | Quantified? |
|----------|----------|-------------|
| Arbitrary weighting (0.6/0.2/0.2) | Medium | ✅ M12.9 sensitivity analysis |
| No outcome validation | **High** | ✅ M13.1 — no joinable data |
| Popularity sensitivity | Medium | ✅ M12.9 — τ drops from 1.0 to 0.55 |
| qualifying_ratio = zero discriminating | Low | ✅ M12.9 — all top candidates identical |
| Entity-level winner not robust | Medium | ✅ M12.9 — 2 winners across policies |
| Unknown if Qloo predicts attendance | **High** | ✅ M13.1 — D. insufficient data |

### Current Ranker Claim

"Under the tested Qloo evidence-ranking policies, TV-show entities rank highest because they exhibit higher observed Qloo affinity in these programme contexts."

**NOT:** "Qloo predicts attendance" or "Adjacent selects the best programming."

---

## IF ML BECOMES JUSTIFIED

### Recommended Architecture

**LightGBM Ranker** (learning-to-rank)

**Feature groups:**

| Group | Features | Source |
|-------|----------|--------|
| Qloo | affinity, popularity, domain, cohort_kind, shared_tag_count, candidate_tag_count | Qloo API |
| Programme | film count, genre composition, decade spread, programme theme | Adjacent |
| Venue | capacity, city, venue_type, historical sold_out rate | Venue data |
| Temporal | day_of_week, month, season, weeks_since_release | Computed |

**Target:** sold_out (binary) or occupancy_rate (continuous)

**Evaluation:** Venue/time-grouped NDCG@K, PR AUC

**Keep ML only if it materially improves held-out performance over:**
1. Venue history baseline
2. Affinity-only baseline
3. Current deterministic ranker

---

## WHAT WOULD MAKE US REJECT ML

1. No accessible dataset with real outcome labels + joinable identifiers
2. Learned model does not beat affinity-only baseline
3. Venue features dominate Qloo features (Qloo adds no value)
4. Outcome variance is too low
5. Sample size is insufficient for meaningful evaluation

---

## NEXT STEPS

| Priority | Action | Timeline |
|----------|--------|----------|
| 1 | Build prospective outcome logging schema | Now |
| 2 | Build Prince Charles scraper for sold_out | 1-2 days |
| 3 | Collect 3-6 months of weekly data | 3-6 months |
| 4 | Evaluate Qloo signal vs sold_out | After collection |
| 5 | If justified: train LightGBM Ranker | After evaluation |

---

**Status:** COMPLETE