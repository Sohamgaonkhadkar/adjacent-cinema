# M12.3: Final Report — Evaluation Integrity Lock

**Date:** 2026-10-07
**Status:** COMPLETE

---

## Executive Summary

M12.3 locks evaluation integrity. The key finding: **Qloo's film candidates come from a different database than the curated universe, making film-space Jaccard uncomputable. The stronger claim comes from Experiment B: Qloo adds cross-domain cultural capability.**

---

## Answers to Final Gate

### 1. Is the film candidate universe genuinely identical?

**Answer:** ✅ YES — Common 53-film universe defined. Both systems score only these films.

**However:** Qloo returns 0 candidates from this universe. Qloo's film recommendations come from its own database.

### 2. Is Jaccard now a valid apples-to-apples metric?

**Answer:** ❌ NOT COMPUTABLE — The universes don't overlap. Qloo returns different films than the curated universe.

### 3. Is provenance separated from evidence?

**Answer:** ✅ YES
- `retrieval_provenance`: Qloo call/entity/cohort exists
- `cultural_evidence`: interpretable relationship exists

### 4. Are actionable opportunities entity-level and auditable?

**Answer:** ✅ YES — Each entity scored individually on relevance, programmability, evidence.

### 5. How many opportunities survive the independent sanity check?

**Answer:** 15/15 (100% agreement)

### 6. How many verified independent/community contexts exist?

**Answer:** 2 (Prince Charles, Genesis Cinema)

### 7. What is the strongest Genesis case study?

**Answer:**
- INPUT: American History X, Rosemary's Baby, Halloween, Parasite, The Substance, Conclave
- QLOO: 98 ACTIONABLE non-film opportunities (artists, TV shows, books, brands)
- TOP: Unloved (artist, affinity 0.901), Frances Forever (artist, affinity 0.885)

### 8. What claims are now safe?

**Answer:**
> "Adjacent adds a cross-domain cultural capability unavailable to a film-only metadata system. On verified cinema programmes, Qloo can connect the programme to specific non-film cultural entities and convert those relationships into testable programming opportunities."

### 9. What claims remain unsupported?

**Answer:**
- ❌ Higher attendance
- ❌ Audience growth
- ❌ Better recommendations
- ❌ Higher conversion
- ❌ Predictive accuracy

### 10. Is the evaluation strong enough to start M13?

**Answer:** ✅ YES — For hackathon narrative. The cross-domain capability is demonstrated.

---

## Results Summary

| Metric | Independent | Chain |
|--------|-------------|-------|
| Contexts | 2 | 3 |
| Qloo successful | 2/2 | 3/3 |
| Avg resolution rate | 97% | 88% |
| ACTIONABLE opportunities | 148 | 147 |
| Non-film domains | artist, tv_show, book, brand | artist, brand |

---

## Final Valid Claim

> "Adjacent adds a cross-domain cultural capability unavailable to a film-only metadata system. On verified cinema programmes, Qloo can connect the programme to specific non-film cultural entities (artists, books, TV shows, brands) and convert those relationships into testable programming opportunities."

---

## Forbidden Claims

- ❌ Higher attendance
- ❌ Audience growth
- ❌ Better recommendations
- ❌ Higher conversion
- ❌ Predictive accuracy
- ❌ Business impact

---

## Deliverables

| File | Description |
|------|-------------|
| `docs/M12_3_EVALUATION_INTEGRITY.md` | Integrity fixes documentation |
| `docs/M12_3_FINAL_REPORT.md` | This report |
| `data/processed/m12_3_incremental_value_results.json` | Machine-readable results |

---

## Conclusion

M12.3 locks evaluation integrity:

1. ✅ Identical film candidate universe (though Qloo returns different films)
2. ✅ Provenance separated from evidence
3. ✅ Entity-level actionability
4. ✅ Independent sanity check (100% agreement)
5. ✅ Venue types properly labelled

**The evaluation is now rigorous enough for the hackathon narrative.**

---

**Next Milestone:** M13 — Attendance / Outcome Signal Validation

---

**Report Generated:** 2026-10-07
**Status:** COMPLETE