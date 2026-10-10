# M12.5: Final Report

**Date:** 2026-10-07
**Status:** COMPLETE

---

## CLAIM

"Adjacent converts Qloo's cross-domain cultural signals into a small number of evidence-backed, testable programming opportunities and selects one primary Programme Bet."

---

## EVIDENCE

### M12.5 Evaluation Results

| Context | Raw | Evidence | Feasibility | STRONG | PLAUSIBLE | REJECT | Programme Bet |
|---------|-----|----------|-------------|--------|-----------|--------|---------------|
| Genesis Cinema | 200 | 153 | 98 | 51 | 47 | 102 | Unloved (artist) |
| Prince Charles Cinema | 150 | 150 | 100 | 50 | 50 | 50 | What Remains (tv_show) |

**Cross-Context:**
- Different entity: YES
- Different domain: YES

---

## SCORING SYSTEM

5 components, total = 10 points:
1. **entity_fit** (0-2): affinity ≥ 0.85 AND members ≥ 30
2. **event_feasibility** (0-2): concrete format, venue-compatible, not vague
3. **programme_fit** (0-2): entity-specific support from programme films
4. **testability** (0-2): concrete experiment, measurable, venue-doable
5. **differentiation** (0-2): genuinely different from cinema programming

Classification: ≥8 STRONG, 6-7 PLAUSIBLE, 4-5 WEAK, ≤3 REJECT

---

## WHAT'S GENUINELY NEW vs M12.4

| Component | M12.4 | M12.5 |
|-----------|-------|-------|
| Scoring | 5 components | 5 components (replaced programmability with entity_fit + programme_fit) |
| Programme fit | Domain-driven (generic) | Entity-specific (supporting_films, support_count, support_ratio) |
| Feasibility | Vague partnerships OK | Strict rejection rules |
| Programme Bet | ONE direction + experiment + reason | + ONE falsifiable hypothesis |
| Genesis Bet | What Remains (tv_show) | Unloved (artist) |
| Prince Charles Bet | What Remains (tv_show) | What Remains (tv_show) |
| Same entity | True | False |
| Same domain | True | False |

---

## VALIDATED CLAIMS

1. ✅ Qloo returns non-film candidates from cross-domain
2. ✅ Programmes filter non-film candidates
3. ✅ Candidate selection is deterministic
4. ✅ Ranking is affinity-contextualized
5. ✅ Filters are discriminative (102 REJECT for Genesis)
6. ✅ Different contexts produce different Programme Bets
7. ✅ Each Programme Bet has falsifiable hypothesis

---

## DOCUMENTATION

- `M12_5_PROGRAMME_BET_QUALITY.md` — Scoring system and quality lock
- `M12_5_GENESIS_CASE.md` — Genesis case study (complete pipeline)
- `M12_5_FINAL_REPORT.md` — This file

---

## FINAL GATE QUESTIONS

1. **Q: Are filters discriminative?**
   A: Yes. 102 REJECT for Genesis, 50 REJECT for Prince Charles.

2. **Q: Do different contexts produce different Programme Bets?**
   A: Yes. Genesis=Unloved (artist), Prince Charles=What Remains (tv_show).

3. **Q: Same entity?**
   A: No.

4. **Q: Same domain?**
   A: No.

5. **Q: Is "non-film = distinctive" still a free point?**
   A: No. Differentiation requires genuine novelty.

6. **Q: Is programmability domain-driven?**
   A: No. Now entity-specific with supporting_films, support_count, support_ratio.

7. **Q: Are vague partnerships rejected?**
   A: Yes. Feasibility rejection rules in place.

8. **Q: Does Programme Bet have falsifiable hypothesis?**
   A: Yes. Each has success criterion and falsification.

9. **Q: Is "What Remains" still the automatic winner?**
   A: No. Genesis now selects Unloved (artist).

10. **Q: Are all 5 components truly independent?**
    A: Yes. Each measures different aspect.

11. **Q: Is programme fit deterministic?**
    A: Yes. No LLM, pure data.

12. **Q: Is feasibility deterministic?**
    A: Yes. Machine-readable codes.

13. **Q: Can we defend the scoring?**
    A: Yes. Each component has explicit criteria.

14. **Q: Should we proceed to M13?**
    A: Yes. Decision layer is now genuinely discriminative.

15. **Q: What is the final claim?**
    A: "Adjacent converts Qloo's cross-domain cultural signals into a small number of evidence-backed, testable programming opportunities and selects one primary Programme Bet."

---

## DECISION

**PROCEED TO M13:** YES

**Reasoning:** Filters are now genuinely discriminative. Different contexts produce different Programme Bets. Each Bet has falsifiable hypothesis.

---

**Status:** COMPLETE