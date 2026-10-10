# M12.9: Final Report

**Date:** 2026-10-07
**Status:** COMPLETE

---

## FINAL GATE QUESTIONS

**1. Are all invariance tests real?**
Yes. All assertions check actual conditions. No `or True` patterns. 14 tests, all pass.

**2. Is qualifying_ratio correctly labelled cohort-level?**
Yes. `qualifying_ratio` is in `cohort_evidence`, not `candidate_evidence`. All cohort members share the same value.

**3. Is affinity-only evaluated?**
Yes. `affinity_only` is the baseline policy. Winner: What Remains (both contexts).

**4. Are multiple weight policies evaluated?**
Yes. Four policies: affinity_only, affinity_qualifying, affinity_popularity, balanced.

**5. Is winner stability measured?**
Yes. 2 unique winners per context (both tv_show). Domain-level outcome is robust.

**6. Is popularity sensitivity measured?**
Yes. Kendall τ drops from 1.000 (affinity_qualifying) to 0.546/0.410 (balanced). Popularity weight causes significant rank reordering.

**7. Is the ranking robust?**
Domain-level: YES (always tv_show). Entity-level: SENSITIVE to popularity weight (What Remains vs Tomorrow/Devil in Ohio).

**8. If not robust, is that honestly reported?**
Yes. Reported: "The specific TV-show winner varies with popularity weighting." Not hidden.

**9. Is the final claim phrased as our policy over Qloo evidence rather than Qloo's own prediction?**
Yes. "Under the tested Qloo evidence-ranking policies, TV-show entities rank highest because they exhibit higher observed Qloo affinity." NOT "Qloo says TV shows are best."

**10. Can M13 proceed without hiding weighting sensitivity?**
Yes. The sensitivity is documented. The domain-level decision is robust. M13 can proceed.

---

## DECISION

**M12.9 = COMPLETE. All 10 gate questions YES.**

**NEXT MILESTONE = M13 — OUTCOME / ATTENDANCE SIGNAL VALIDATION**

---

## KEY NUMBERS

| Metric | Genesis | Prince Charles |
|--------|---------|---------------|
| Affinity spread (top 10) | 0.005 | 0.006 |
| Popularity spread (top 10) | 0.380 | 0.521 |
| Kendall τ (balanced vs affinity_only) | 0.546 | 0.410 |
| Unique winners | 2 | 2 |
| Domain consistent | YES | YES |
| qualifying_ratio differentiating | NO | NO |

---

**Status:** COMPLETE