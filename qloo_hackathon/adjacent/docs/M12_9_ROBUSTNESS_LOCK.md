# M12.9: Evidence Score Robustness Lock

**Date:** 2026-10-07
**Status:** COMPLETE

---

## SCORING POLICIES TESTED

| Policy | Formula | Note |
|--------|---------|------|
| affinity_only | `affinity` | Simplest Qloo-derived ranking |
| affinity_qualifying | `0.8*affinity + 0.2*qr` | Adds cohort quality |
| affinity_popularity | `0.8*affinity + 0.2*pop` | Adds mainstream signal |
| balanced | `0.6*affinity + 0.2*pop + 0.2*qr` | M12.8 default |

---

## RESULTS

### Genesis Cinema

| Policy | Winner | Score | Domain |
|--------|--------|-------|--------|
| affinity_only | What Remains | 0.9560 | tv_show |
| affinity_qualifying | What Remains | 0.9648 | tv_show |
| affinity_popularity | Tomorrow | 0.9373 | tv_show |
| balanced | Tomorrow | 0.9471 | tv_show |

**Sensitivity vs affinity_only:**

| Policy | Kendall τ | Top-5 | Top-10 | Winner same |
|--------|-----------|-------|--------|-------------|
| affinity_qualifying | 1.000 | 5/5 | 10/10 | YES |
| affinity_popularity | 0.633 | 0/5 | 2/10 | NO |
| balanced | 0.546 | 0/5 | 2/10 | NO |

### Prince Charles Cinema

| Policy | Winner | Score | Domain |
|--------|--------|-------|--------|
| affinity_only | What Remains | 0.9596 | tv_show |
| affinity_qualifying | What Remains | 0.9677 | tv_show |
| affinity_popularity | Devil in Ohio | 0.9403 | tv_show |
| balanced | Devil in Ohio | 0.9495 | tv_show |

**Sensitivity vs affinity_only:**

| Policy | Kendall τ | Top-5 | Top-10 | Winner same |
|--------|-----------|-------|--------|-------------|
| affinity_qualifying | 1.000 | 5/5 | 10/10 | YES |
| affinity_popularity | 0.510 | 0/5 | 3/10 | NO |
| balanced | 0.410 | 0/5 | 3/10 | NO |

---

## CRITICAL FINDINGS

### 1. qualifying_ratio has ZERO differentiating power

All top candidates have qualifying_ratio = 1.0 (50/50 or 48/48). Adding it to the score changes the magnitude but not the ranking. It is correctly classified as **cohort-level** evidence.

### 2. Affinity spread is tiny; popularity spread is large

| Context | Affinity spread (top 10) | Popularity spread (top 10) |
|---------|--------------------------|---------------------------|
| Genesis | 0.005 | 0.380 |
| Prince Charles | 0.006 | 0.521 |

Top candidates have very similar affinity (~0.951-0.956). Popularity varies much more (0.50-0.88). Therefore **popularity weight dominates the ranking sensitivity**.

### 3. Domain-level winner is robust

**All 4 policies produce tv_show winners for both contexts.** The domain-level decision is not sensitive to weight choice.

### 4. Entity-level winner is sensitive to popularity weight

Without popularity: What Remains (highest affinity, lower popularity)
With popularity: Tomorrow / Devil in Ohio (high affinity + high popularity)

This is not a bug — it's a genuine policy choice: "Do we prefer the strongest cultural signal, or the most accessible cultural signal?"

---

## EVIDENCE CLASSIFICATION (FINAL)

| Category | Fields |
|----------|--------|
| **CANDIDATE-LEVEL** | affinity, popularity, band, candidate_tags |
| **COHORT-LEVEL** | qualifying_members, total_members, qualifying_ratio, cohort_kind, shared_tags, construction_evidence |
| **DERIVED** | qloo_evidence_score, rank_correlations |
| **PRODUCT_POLICY** | scoring weights |
| **UNKNOWN** | actual attendance impact, per-film attribution, success thresholds |

---

## WINNER STABILITY

| Context | Unique winners | Domain consistent? | Robust? |
|---------|----------------|-------------------|---------|
| Genesis | 2 (What Remains, Tomorrow) | YES (both tv_show) | YES (domain-level) |
| Prince Charles | 2 (What Remains, Devil in Ohio) | YES (both tv_show) | YES (domain-level) |

---

## FINAL CLAIM (CORRECTLY PHRASED)

"Under the tested Qloo evidence-ranking policies, TV-show entities rank highest because they exhibit higher observed Qloo affinity in these programme contexts. The specific TV-show winner varies with popularity weighting, but the domain-level outcome is robust across all tested policies."

NOT: "Qloo says TV shows are the best audience opportunity."

---

## TESTS

14 tests proving:
- Same numeric evidence + different domain = identical score
- Same numeric evidence + different format = identical score
- Same numeric evidence + different cohort_kind = identical score
- Same numeric evidence + different tags = identical score
- Removing Layer-B policy fields preserves entity ordering
- No unconditional/pass-always assertions exist
- qualifying_ratio is cohort-level, not candidate-level
- Affinity-only is a valid policy
- Winner stability is measured, not assumed
- Rank correlation is computed, not hardcoded

---

**Status:** COMPLETE