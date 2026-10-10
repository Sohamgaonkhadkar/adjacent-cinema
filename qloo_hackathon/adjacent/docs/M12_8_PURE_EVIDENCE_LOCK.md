# M12.8: Pure Evidence Decision Lock

**Date:** 2026-10-07
**Status:** SUPERSEDED BY M12.9 — qualifying_ratio had zero differentiating power (all top candidates identical); popularity sensitivity was unmeasured; policy-invariance tests had `or True` bugs

---

## TWO-LAYER ARCHITECTURE

### Layer A: Cultural Evidence Ranking
Uses ONLY observed Qloo fields. IMMUNE to domain, format, policy.

**Formula:**
```
qloo_evidence_score = 0.6 * affinity + 0.2 * popularity + 0.2 * qualifying_ratio
```

**Inputs** (all observed Qloo quantities):
- `affinity`: Qloo affinity score (0-1)
- `popularity`: Qloo popularity (0-1)
- `qualifying_ratio`: qualifying_members / total_members

**Weights** are product policy (explicitly labelled). Inputs are observed.

### Layer B: Experiment Construction
Uses domain, venue, format. Does NOT change cultural ranking.

```
Cultural ranking → top candidates → then assign experiment format
```

---

## WHAT WAS REMOVED FROM RANKING

| Removed | Why |
|---------|-----|
| differentiation | Domain → format → differentiation was domain-derived |
| testability | Synthetic keyword heuristics |
| event_feasibility | Domain-driven format assignment |
| programme_fit score | Hand-coded semantic weights (tag_cluster=2, etc.) |
| shared_tag count scoring | Our interpretation, not Qloo score |
| cohort_kind weighting | Our interpretation, not Qloo score |

These remain as Layer B metadata, not ranking factors.

---

## FIELD CLASSIFICATION

| Category | Fields |
|----------|--------|
| **OBSERVED** | affinity, popularity, qualifying_members, total_members, band, tags, cohort_kind, construction_evidence |
| **DERIVED** | qloo_evidence_score, qualifying_ratio |
| **POLICY** | evidence weights, experiment format, event feasibility rules |
| **UNKNOWN** | per_film_attribution, success_thresholds |

---

## RESULTS

### Genesis Cinema

**Top 10 (Layer A):**

| Rank | Entity | Domain | Score | Affinity | Popularity |
|------|--------|--------|-------|----------|------------|
| 1 | Tomorrow | tv_show | 0.9471 | 0.9511 | 0.882 |
| 2 | Glitch | tv_show | 0.9467 | 0.9458 | 0.896 |
| 3 | Devil in Ohio | tv_show | 0.9452 | 0.9466 | 0.886 |
| 4 | Dirty John | tv_show | 0.9432 | 0.9465 | 0.877 |
| 5 | Keep Breathing | tv_show | 0.9427 | 0.9489 | 0.867 |
| 6 | Stateless | tv_show | 0.9366 | 0.9484 | 0.838 |
| 7 | Thirteen | tv_show | 0.9359 | 0.9489 | 0.833 |
| 8 | The Five | tv_show | 0.9314 | 0.9493 | 0.809 |
| 9 | Red Rose | tv_show | 0.9300 | 0.9523 | 0.793 |
| 10 | Chambers | tv_show | 0.9291 | 0.9456 | 0.809 |

**Domain distribution (top 20):** tv_show: 19, artist: 1

**Programme Bet:** Tomorrow (tv_show), score=0.9471

### Prince Charles Cinema

**Top 10 (Layer A):**

| Rank | Entity | Domain | Score | Affinity | Popularity |
|------|--------|--------|-------|----------|------------|
| 1 | Devil in Ohio | tv_show | 0.9495 | 0.9538 | 0.886 |
| 2 | Slasher | tv_show | 0.9453 | 0.9506 | 0.875 |
| 3 | Millennium | tv_show | 0.9384 | 0.9514 | 0.838 |
| 4 | Thirteen | tv_show | 0.9361 | 0.9492 | 0.833 |
| 5 | Shiki | tv_show | 0.9350 | 0.9505 | 0.824 |

**Domain distribution (top 20):** tv_show: 20

**Programme Bet:** Devil in Ohio (tv_show), score=0.9495

---

## MOST IMPORTANT ANALYSIS

**A. Are artists still dominating?**
No. TV shows dominate when using pure Qloo evidence.

**B. If yes, is that because Qloo evidence actually ranks them higher?**
N/A — artists do NOT dominate.

**C. Did previous format policy create the artist dominance?**
**YES.** In M12.5-M12.7, artists won because:
1. `artist → live music format → differentiation = 2`
2. `tv_show → season format → differentiation = 1`
This +1 differentiation advantage was enough to overcome artists' lower affinity.

**D. Which exact observed Qloo variables drive the ranking?**
Affinity (weight 0.6) is the primary driver. TV shows have higher affinity (avg 0.949) than artists (avg 0.901).

**E. Which fields are purely product policy?**
Evidence weights (0.6/0.2/0.2), experiment format, event feasibility rules.

**F. Can two domains with identical Qloo evidence receive identical ranking?**
**YES.** The formula uses only numeric Qloo fields. Domain is not an input.

**G. Is the final ranking defensible without using semantic assumptions?**
**YES.** The ranking is a transparent weighted average of observed Qloo quantities.

---

## CROSS-CONTEXT

| Context | Programme Bet | Domain | Score |
|---------|---------------|--------|-------|
| Genesis | Tomorrow | tv_show | 0.9471 |
| Prince Charles | Devil in Ohio | tv_show | 0.9495 |

Same domain: True (both tv_show). Different entity: True.

---

## TESTS

17 tests proving:
- Same Qloo evidence + different domain → same score
- Same Qloo evidence + different format → same score
- Same Qloo evidence + different cohort_kind → same score
- Different shared_tag count → does NOT change score
- Domain cannot improve rank by itself
- Format cannot improve rank by itself
- Removing all policy fields leaves ranking unchanged
- Layer A and Layer B are separated
- Evidence formula is transparent and correct

---

**Status:** COMPLETE