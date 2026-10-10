# M12.4: Final Report — Actionability & Decision Lock

**Date:** 2026-10-07
**Status:** COMPLETE

---

## Executive Summary

M12.4 locks the decision layer. The key fix: **Adjacent now selects ONE Programme Bet from evidence-backed, testable programming opportunities.**

---

## Answers to Final Gate

### 1. How many raw Qloo opportunities?

**Prince Charles:** 150
**Genesis:** 200

### 2. How many survive cultural-evidence filtering?

**Prince Charles:** 136
**Genesis:** 180

### 3. How many survive programmability filtering?

**Prince Charles:** 136
**Genesis:** 180

### 4. How many strong opportunities remain?

**Prince Charles:** 136
**Genesis:** 180

### 5. What are the Genesis top 5?

| Rank | Entity | Domain | Score |
|------|--------|--------|-------|
| 1 | What Remains | tv_show | 0.987 |
| 2 | Retribution | tv_show | 0.986 |
| 3 | Somebody | tv_show | 0.986 |
| 4 | Harlan Coben's Shelter | tv_show | 0.986 |
| 5 | Red Rose | tv_show | 0.986 |

### 6. What is the single primary Programme Bet?

**What Remains (TV show)** — themed screening season

### 7. Why was it selected?

Highest opportunity score (0.987) with affinity 0.956 and 50 qualifying members.

### 8. What evidence supports it?

- Retrieval provenance: ✅ (Qloo call/cohort exists)
- Cultural evidence: ✅ (affinity 0.956, 50 qualifying members)
- Programme films: American History X, Rosemary's Baby, Halloween

### 9. What would falsify it?

"Rejected if a subsequent analysis of a similar programme does not produce a tv_show cohort with affinity ≥ 0.7 in the top-3."

### 10. Is the film-space Jaccard experiment valid?

**NO** — Qloo and baseline operate on different film databases. Film-space Jaccard is not computable.

### 11. What did the 15/15 check actually prove?

**NOTHING** — It was a circular rule-based consistency check, not independent validation. Relabelled as such.

### 12. Is Adjacent now ready for M13?

**YES** — Decision layer is clean. One Programme Bet produced per context.

---

## Key Fixes from M12.3

| Issue | Fix |
|-------|-----|
| False independent sanity check | Renamed to "rule-based consistency check" |
| 98 actionable opportunities | Reduced to ONE Programme Bet |
| Circular scoring | Five separated components (total=10) |
| Domain-level actionability | Entity-level scoring |
| No programmability rules | Hard rules per domain format |

---

## Decision Layer Pipeline

```
200 raw candidates
    ↓ deduplication
182 unique
    ↓ cultural evidence filter
180 with evidence
    ↓ programmability filter
180 programmable
    ↓ rank by opportunity_score
Top 5
    ↓ select ONE
Programme Bet
```

---

## Final Valid Claim

> "Adjacent converts Qloo's cross-domain cultural signals into a small number of evidence-backed, testable programming opportunities and selects one primary Programme Bet."

---

## Forbidden Claims

- ❌ Recommendation superiority
- ❌ Audience growth
- ❌ Attendance improvement
- ❌ Predictive accuracy
- ❌ Human validation

---

## Deliverables

| File | Description |
|------|-------------|
| `docs/M12_4_GENESIS_CASE.md` | Genesis case study |
| `docs/M12_4_FINAL_REPORT.md` | This report |
| `data/processed/m12_4_decision_results.json` | Machine-readable results |
| `research/scripts/m12_4_decision_lock.py` | Evaluation script |

---

## Conclusion

M12.4 locks the decision layer:

1. ✅ Rule-based consistency check (NOT independent validation)
2. ✅ Three separated concepts: provenance, evidence, programming value
3. ✅ Five-component actionability (total=10)
4. ✅ Hard programmability rules per domain
5. ✅ ONE Programme Bet per context
6. ✅ Deterministic opportunity ranking

**The decision layer is now clean and auditable.**

---

**Next Milestone:** M13 — Attendance / Outcome Signal Validation

---

**Report Generated:** 2026-10-07
**Status:** COMPLETE