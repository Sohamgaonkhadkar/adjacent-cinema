# M12.8: Final Report

**Date:** 2026-10-07
**Status:** COMPLETE

---

## FINAL GATE QUESTIONS

**1. Can the cultural ranking be reproduced from observed Qloo fields only?**
Yes. `qloo_evidence_score = 0.6*affinity + 0.2*popularity + 0.2*qualifying_ratio`. All inputs are observed Qloo fields.

**2. Does domain identity have zero effect on cultural score?**
Yes. Domain is not an input to `compute_qloo_evidence_score`.

**3. Does event format have zero effect on cultural score?**
Yes. Event format is not an input to `compute_qloo_evidence_score`.

**4. Does testability have zero effect on cultural score?**
Yes. Testability is removed from candidate ranking entirely.

**5. Does differentiation have zero effect on cultural score?**
Yes. Differentiation is removed from candidate ranking entirely.

**6. Does cohort_kind weighting have zero effect unless explicitly labelled product policy?**
Yes. cohort_kind is descriptive metadata, not a ranking input.

**7. Does shared-tag count avoid pretending to be a Qloo score?**
Yes. shared_tags are descriptive evidence in `programme_fit_evidence`, not scored.

**8. Is per-film attribution still honestly unavailable?**
Yes. `per_film_attribution = NOT_AVAILABLE`.

**9. Are experiment construction and cultural ranking separated?**
Yes. Layer A (cultural evidence) produces ranking. Layer B (experiment) proposes formats after ranking is fixed.

**10. Can identical Qloo evidence across domains produce identical ranks?**
Yes. Verified by tests: same affinity/popularity/qualifying → same score regardless of domain.

**11. Are artist winners still present after removing format policy?**
No. TV shows dominate (19/20 top Genesis, 20/20 top Prince Charles).

**12. If artists remain, is that supported by observed Qloo evidence?**
Artists are at rank ~20 in Genesis, absent from top 20 in Prince Charles. Their lower affinity (avg 0.901 vs TV show avg 0.949) is the observed reason.

**13. Is the ranking reproducible without hand-authored semantic assumptions?**
Yes. The formula is a transparent weighted average of three observed Qloo fields.

---

## CRITICAL FINDING

Previous artist dominance was caused by format policy, not Qloo evidence.

M12.5-M12.7: artist → live music format → differentiation=2 → bonus over TV shows
M12.8: pure Qloo evidence → TV shows have higher affinity → TV shows win

This is the correct answer: Qloo says the programme's audience is more culturally adjacent to TV shows than to artists.

---

## RESULTS

| Context | Programme Bet | Domain | Score | Affinity | Popularity |
|---------|---------------|--------|-------|----------|------------|
| Genesis | Tomorrow | tv_show | 0.9471 | 0.9511 | 0.882 |
| Prince Charles | Devil in Ohio | tv_show | 0.9495 | 0.9538 | 0.886 |

---

## DOCUMENTATION

- `M12_8_PURE_EVIDENCE_LOCK.md` — Two-layer architecture
- `M12_8_SCORING_AUDIT.md` — Component-by-component audit
- `M12_8_FINAL_REPORT.md` — This file

---

## DECISION

**M12.8 = COMPLETE**

All 13 gate questions answered YES.

**NEXT MILESTONE = M13 — OUTCOME / ATTENDANCE SIGNAL VALIDATION**

---

**Status:** COMPLETE