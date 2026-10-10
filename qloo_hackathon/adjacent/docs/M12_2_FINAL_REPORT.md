# M12.2: Final Report — Apples-to-Apples Evaluation

**Date:** 2026-10-07
**Status:** COMPLETE

---

## Executive Summary

M12.2 makes the evaluation genuinely apples-to-apples. The key finding: **Qloo adds a cross-domain cultural capability that a film-metadata baseline does not provide.**

---

## Answers to Required Questions

### 1. How many genuinely verified current programme contexts?

**Answer:** 5
- Prince Charles Cinema (INDEPENDENT) — scraped from live website
- Genesis Cinema (INDEPENDENT) — scraped from live website
- Ritzy Picturehouse (CHAIN) — scraped via API
- Phoenix Picturehouse (CHAIN) — scraped via API
- Duke of York's (CHAIN) — scraped via API

### 2. What is the real metadata baseline?

**Answer:** Content similarity using genre (Jaccard, 0.5), country (exact match, 0.2), director (exact match, 0.3). No Qloo data. No hand-written style labels.

### 3. What is the common film candidate universe?

**Answer:** 42 films from public metadata database (genre, country, director).

### 4. What is the true Qloo top-K definition?

**Answer:** All candidates from ranked cohorts, sorted by affinity globally. Film-domain and non-film-domain reported separately.

### 5. What is film-space overlap?

**Answer:** Jaccard@10 = 0.000 for all contexts. Zero overlap.

### 6. How many Qloo non-film opportunities exist?

**Answer:** Average 2.6 non-film domains per context. 150-200 non-film candidates per context.

### 7. How many are evidence-supported?

**Answer:** All candidates have Qloo call IDs (provenance-backed).

### 8. How many are actionable?

**Answer:** 13 total across 5 contexts. All non-film domains scored ≥ 4/6 on actionability rubric.

### 9. What is Qloo resolution coverage?

**Answer:** 92% average (5/6 to 8/8 films resolved per context).

### 10. What are the main failure cases?

**Answer:**
- 2024/2026 releases may not be in Qloo (1-2 films per context)
- Baseline metadata coverage is 100% (all films in database)

### 11. Does Qloo demonstrably add cross-domain capability?

**Answer:** ✅ YES

Evidence:
- 5/5 contexts show non-film domains (artist, tv_show, book, brand)
- 13 actionable cross-domain opportunities
- Film-space Jaccard@10 = 0.000 (completely different recommendations)
- Average 2.6 non-film domains per context

### 12. Is the evidence strong enough to move to M13?

**Answer:** ⚠️ For hackathon: YES. For scientific publication: need more contexts.

---

## Key Results

| Metric | Value |
|--------|-------|
| Verified contexts | 5 |
| Qloo successful | 5/5 |
| Avg resolution rate | 92% |
| Film-space Jaccard@10 | 0.000 |
| Non-film domains | 2.6 avg |
| Actionable cross-domain | 13 total |
| Qloo failures | 0 |

---

## Experiment A: Film-Space

**Result:** Jaccard@10 = 0.000

Baseline and Qloo produce completely different film recommendations:
- Baseline: genre-similar films (The Thing, Get Out, Suspiria)
- Qloo: culturally adjacent films (Friendly Beast, Thinner, The Appointment)

**Do NOT interpret as "Qloo is better."** Only that the systems diverge.

---

## Experiment B: Cross-Domain

**Result:** 13 actionable opportunities across 5 contexts

| Domain | Contexts | Actionable |
|--------|----------|------------|
| artist | 5/5 | 5/5 |
| brand | 5/5 | 5/5 |
| tv_show | 2/5 | 2/5 |
| book | 1/5 | 1/5 |

---

## Valid Claim

> "Adjacent adds a cross-domain cultural capability that a film-metadata baseline does not provide. Across verified current programme contexts, Qloo surfaced evidence-backed non-film opportunities that were unavailable to the film-only baseline."

---

## Forbidden Claims

- ❌ Higher attendance
- ❌ Better recommendations
- ❌ Audience growth
- ❌ Conversion improvement
- ❌ Predictive accuracy
- ❌ Superiority of Qloo

---

## Deliverables

| File | Description |
|------|-------------|
| `docs/M12_2_CASE_STUDY.md` | Genesis Cinema case study |
| `docs/M12_2_FINAL_REPORT.md` | This report |
| `data/processed/m12_2_incremental_value_results.json` | Machine-readable results |
| `research/scripts/m12_2_incremental_value.py` | Evaluation script |

---

## Conclusion

M12.2 makes the evaluation genuinely apples-to-apples:

1. **Real programme data** from scraped sources
2. **Real metadata baseline** (genre, country, director)
3. **Proper Qloo candidate extraction** (global affinity ranking)
4. **Split experiments** (film-space vs cross-domain)
5. **Coverage tracking** (resolution rates)
6. **Actionability rubric** (deterministic scoring)

**The evidence supports:** Qloo adds cross-domain cultural capability unavailable from metadata.

**The evidence does NOT support:** Predictive accuracy, attendance improvement, or recommendation superiority.

---

**Next Milestone:** M13 — Attendance Signal Validation

---

**Report Generated:** 2026-10-07
**Status:** COMPLETE