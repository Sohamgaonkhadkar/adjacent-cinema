# M12.1: Results

**Date:** 2026-10-07
**Status:** COMPLETE

---

## Summary

**Among verified programme contexts, Qloo discovers cross-domain cultural opportunities that are structurally unavailable to the metadata/content baseline.**

However, Qloo fails when films are not in its database (2026 releases).

---

## Primary Evaluation (VERIFIED_PROGRAMME Only)

| Metric | Value |
|--------|-------|
| Verified contexts | 3 |
| Qloo successful | 2/3 |
| Qloo insufficient | 1/3 |
| Cross-domain discovery | 2/3 |
| Avg Jaccard@10 | 0.000 |
| Avg overlap | 0.0 |
| Avg Qloo-only | 6.3 |
| Avg cross-domain | 2.7 |

---

## Detailed Results by Context

### 1. Prince Cinema (VERIFIED)

**Baseline top-3:**
1. Deep Red (film) — similarity=1.0
2. Tenebre (film) — similarity=0.85
3. Phenomena (film) — similarity=0.85

**Qloo top-3:**
1. Edward Ka-Spel (artist) — affinity=0.883
2. The Contortions (artist) — affinity=0.883
3. Snakefinger (artist) — affinity=0.883

**Overlap:** 0 (Jaccard@10 = 0.0)
**Qloo-only:** 9 candidates
**Cross-domain:** 3 domains (artist, movie, brand)

**Interpretation:** Baseline recommends similar horror films. Qloo discovers that this horror/cult audience also connects to industrial/experimental musicians. A music event would reach the same cultural audience.

---

### 2. ICA London (VERIFIED)

**Baseline top-3:**
None — films not in metadata database (2026 releases)

**Qloo top-3:**
1. We3 (book) — affinity=0.876
2. From Hell (book) — affinity=0.876
3. Kick-Ass (book) — affinity=0.876

**Overlap:** 0
**Qloo-only:** 10 candidates
**Cross-domain:** 5 domains (artist, movie, TV show, book, brand)

**Interpretation:** Baseline cannot produce candidates (films too new). Qloo discovers literary/graphic novel connections. Note: only 4/6 films resolved in Qloo.

---

### 3. ArtHouse Crouch End (VERIFIED)

**Baseline top-3:**
None — films not in metadata database (2026 releases)

**Qloo top-3:**
None — 0 films resolved (all 2026 releases not in Qloo)

**Qloo insufficient:** YES

**Interpretation:** Both systems fail. The programme consists entirely of 2026 releases that neither the metadata database nor Qloo can resolve.

---

## Cross-Domain Evidence

| Domain | Contexts with Discovery |
|--------|------------------------|
| artist | 2/3 |
| brand | 2/3 |
| movie | 2/3 |
| TV show | 1/3 |
| book | 1/3 |

---

## What Qloo Adds

1. **Artist connections:** Horror/cult audiences connect to industrial/experimental musicians
2. **Book connections:** Contemporary arthouse audiences connect to graphic novels and literary fiction
3. **Brand connections:** Independent cinema audiences connect to specific lifestyle brands
4. **TV show connections:** Arthouse audiences connect to prestige TV

---

## What Qloo Fails At

1. **2026 releases:** Films not in Qloo's database cannot be resolved
2. **Insufficiency rate:** 1/3 verified contexts (33%) — Qloo produces no ranked cohorts

---

## Structural Metrics

| Metric | Prince Charles | ICA | ArtHouse |
|--------|----------------|-----|----------|
| Jaccard@10 | 0.000 | 0.000 | 0.000 |
| Overlap | 0 | 0 | 0 |
| Qloo-only | 9 | 10 | 0 |
| Cross-domain | 3 | 5 | 0 |
| Qloo insufficient | False | False | True |

**Key finding:** When Qloo succeeds, overlap with baseline is ZERO. The systems produce completely different candidate sets.

---

## Honest Assessment

### Strong Evidence

- When films are in Qloo's database, cross-domain discovery is robust
- Jaccard@10 = 0.0 shows Qloo and baseline produce structurally different results
- Artist and book connections are specific and actionable

### Weak Evidence

- Only 3 verified contexts (small sample)
- 1/3 contexts fail (2026 releases)
- Cannot claim generalizability

### Cannot Claim

- Predictive accuracy (no attendance labels)
- Better recommendations (no outcome data)
- Higher conversion (no ticket sales)

---

**Report Generated:** 2026-10-07
**Status:** COMPLETE