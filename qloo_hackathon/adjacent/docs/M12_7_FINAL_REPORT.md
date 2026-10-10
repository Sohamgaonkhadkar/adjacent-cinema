# M12.7: Final Report

**Date:** 2026-10-07
**Status:** COMPLETE

---

## FINAL GATE QUESTIONS

**1. Is any hand-coded domain preference still in the score?**
No. DOMAIN_THEMATIC_VECTORS deleted. Differentiation takes event_format as input, not domain.

**2. Is any hand-coded genre/theme mapping still in the primary score?**
No. FILM_GENRE_PROXIES and GENRE_TO_THEME deleted from the primary scoring path.

**3. Is programme-fit based on real evidence?**
Yes. Uses cohort_kind (Qloo construction), shared_tags (Qloo construction_evidence), and candidate_tags (MemberEvidence.tags).

**4. Is per-film attribution genuinely available?**
No. Qloo's cohort structure does not provide per-output attribution to individual programme films.

**5. If unavailable, is that limitation explicitly reported?**
Yes. `per_film_attribution = NOT_AVAILABLE`. Documented in M12_7_EVIDENCE_LOCK.md and M12_7_SCORING_AUDIT.md.

**6. Does programme_fit reuse entity_fit inputs?**
No. programme_fit uses cohort_kind, shared_tags, candidate_tags. entity_fit uses affinity, qualifying_members, total_members. No shared inputs.

**7. Is differentiation independent of domain identity?**
Yes. `score_differentiation(event_format)` takes only the format string. Domain name is not a parameter. Format assignment is domain-based (feasibility rules), but the SCORE is format-based.

**8. Do Genesis and Prince Charles still produce defensible bets?**
Yes. Genesis: Unloved (artist). Prince Charles: The Contortions (artist). Both backed by real Qloo tag evidence (tag_cluster, 5 shared tags).

**9. What are the final top 5 candidates?**

Genesis:
1. Unloved (artist) — score=10
2. Frances Forever (artist) — score=9
3. Ashton Irwin (artist) — score=9
4. Starcrawler (artist) — score=9
5. The Daughters of Eve (artist) — score=9

Prince Charles:
1. The Contortions (artist) — score=9
2. Edward Ka-Spel (artist) — score=9
3. Dalis Car (artist) — score=9
4. These Immortal Souls (artist) — score=9
5. Snakefinger (artist) — score=9

**10. What is the strongest Programme Bet?**
Genesis: Unloved (artist), affinity=0.901, event format: Live music performance/DJ set + film screening.

**11. Which components actually changed the decision?**
Genesis: no single component changes the bet (Unloved has 10, others 9).
Prince Charles: testability and differentiation each change the bet by 50 ranks when removed.

**12. Is scoring now free of obvious hand-crafted domain bias?**
Yes. No FILM_GENRE_PROXIES, GENRE_TO_THEME, or DOMAIN_THEMATIC_VECTORS. No hardcoded domain differentiation scores. programme_fit uses real Qloo evidence only.

**13. Is the decision layer genuinely defensible?**
Yes. Each component uses different, verifiable evidence. programme_fit = NOT_AVAILABLE when real evidence is absent. Per-film attribution = NOT_AVAILABLE (documented). Differentiation is format-based (documented). No arbitrary business thresholds.

**14. Proceed to M13?**
**YES.** The decision layer is free of hand-crafted bias, uses real Qloo evidence, and explicitly reports limitations.

---

## DECISION

**NEXT MILESTONE = M13 — OUTCOME / ATTENDANCE SIGNAL VALIDATION**

**Reasoning:** Scoring is now free of hand-coded domain preferences. programme_fit uses real Qloo evidence. Differentiation is format-driven. All limitations explicitly documented.

---

**Status:** COMPLETE