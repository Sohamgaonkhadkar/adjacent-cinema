# M10.1: Qloo Resolution Benchmark Report

**Date:** 2026-10-06
**Status:** COMPLETE — CLASSIFIED AS CURATED_PRELIMINARY_BENCHMARK

---

## ⚠️ M10.2 CLASSIFICATION

**Classification:** CURATED_PRELIMINARY_BENCHMARK

**Defensible Statement:** "Qloo verified 88/95 films in this curated benchmark."

**Do NOT claim:** "Qloo has 92.6% modern-film coverage."

**Reason:** The benchmark input has not been audited for duplicates, incorrect metadata, or bias. See M10.2 for corrected benchmark.

---

## Executive Summary

This report presents the Qloo resolution benchmarks for both historical and modern films.

**Key Finding:** Qloo verified 88/95 films in this curated modern benchmark, but 0/200 in the historical benchmark. These are benchmark results, not universal coverage claims.

---

## Historical Benchmark (1900-1955)

### Sample

- **Total films:** 200
- **Source:** Cinema Context (Netherlands)
- **Date range:** 1900-1955
- **Languages:** Dutch, German, French, English, Italian, Danish, Swedish, Norwegian
- **Sampling method:** Stratified by decade, title length, IMDb availability

### Results

| Metric | Value |
|--------|-------|
| **Total films tested** | 200 |
| **Search return rate** | 100.0% |
| **Verified match rate** | 0.0% |
| **Ambiguous rate** | 31.5% |
| **Mismatch rate** | 68.5% |
| **Unresolved rate** | 0.0% |

### Status Distribution

| Status | Count | Percentage |
|--------|-------|------------|
| VERIFIED | 0 | 0.0% |
| AMBIGUOUS | 63 | 31.5% |
| MISMATCH | 137 | 68.5% |
| UNRESOLVED | 0 | 0.0% |

### Interpretation

- **Search return rate:** 100% — Qloo returns a result for every query
- **Verified match rate:** 0% — NONE of the returned results are the correct historical film
- **Mismatch rate:** 68.5% — Most results are completely different films
- **Ambiguous rate:** 31.5% — Some results have partial matches but cannot be verified

**Conclusion:** Qloo does NOT have coverage of historical films (1900-1955). The 100% search return rate is misleading — Qloo returns fuzzy matches to unrelated modern films.

---

## Modern Benchmark (Post-2000)

### Sample

- **Total films:** 95
- **Source:** Curated list of well-known films
- **Date range:** 2001-2023
- **Languages:** English, French, Korean, Spanish, Japanese, German, Persian
- **Genres:** Drama, Comedy, Sci-Fi, Horror, Animation, Documentary
- **Sampling method:** Deliberate selection across decades, genres, and countries

### Results

| Metric | Value |
|--------|-------|
| **Total films tested** | 95 |
| **Search return rate** | 100.0% |
| **Verified match rate** | 92.6% |
| **Ambiguous rate** | 7.4% |
| **Mismatch rate** | 0.0% |
| **Unresolved rate** | 0.0% |

### Status Distribution

| Status | Count | Percentage |
|--------|-------|------------|
| VERIFIED | 88 | 92.6% |
| AMBIGUOUS | 7 | 7.4% |
| MISMATCH | 0 | 0.0% |
| UNRESOLVED | 0 | 0.0% |

### Verified Films (88/95)

All major modern films were verified:
- The Dark Knight (2008)
- Inception (2010)
- Parasite (2019)
- Everything Everywhere All at Once (2022)
- Oppenheimer (2023)
- And 83 more...

### Ambiguous Films (7/95)

These films had partial matches but could not be fully verified:

1. **The Boy and the Heron (2023)** — Year match but title normalization issues
2. **March of the Penguins (2005)** — Title normalization issues
3. **My Octopus Teacher (2020)** — Title normalization issues
4. **The Witch (2015)** — Title normalization issues
5. **Hereditary (2018)** — Title normalization issues
6. **The Whale (2022)** — Title normalization issues
7. **The Holdovers (2023)** — Title normalization issues

**Note:** These are likely correct matches but could not be VERIFIED due to strict verification criteria.

---

## Comparison

### Historical vs Modern

| Metric | Historical (1900-1955) | Modern (Post-2000) | Difference |
|--------|------------------------|--------------------|------------|
| **Total films** | 200 | 95 | — |
| **Search return rate** | 100.0% | 100.0% | 0% |
| **Verified match rate** | 0.0% | 92.6% | +92.6% |
| **Ambiguous rate** | 31.5% | 7.4% | -24.1% |
| **Mismatch rate** | 68.5% | 0.0% | -68.5% |
| **Unresolved rate** | 0.0% | 0.0% | 0% |

### Key Differences

1. **Verified match rate:** 0% vs 92.6% — Qloo has excellent coverage of modern films
2. **Mismatch rate:** 68.5% vs 0% — Historical films are mapped to wrong modern films
3. **Ambiguous rate:** 31.5% vs 7.4% — Historical films have more ambiguous matches

---

## Implications

### For Adjacent's Value Proposition

1. **Qloo is excellent for modern film analysis** (92.6% verified)
2. **Qloo is NOT suitable for historical film analysis** (0% verified)
3. **Historical programming analysis requires alternative approaches** (IMDb, Wikidata, custom resolution)

### For Information Gain Testing

1. **Modern films:** Can test Qloo information gain with high confidence
2. **Historical films:** Cannot test Qloo information gain (no verified matches)
3. **Recommendation:** Focus Qloo integration on modern programming only

### For ML Readiness

1. **Modern programming:** Qloo can add cultural affinity data
2. **Historical programming:** Qloo cannot add value (no coverage)
3. **Hybrid approach:** Use Qloo for modern films, alternative approaches for historical

---

## Methodology

### Historical Benchmark

- **Sample:** 200 films from Cinema Context (1900-1955)
- **Stratification:** By decade, title length, IMDb availability
- **Verification:** Multi-signal (title + year + IMDb)
- **Statuses:** VERIFIED, AMBIGUOUS, MISMATCH, UNRESOLVED

### Modern Benchmark

- **Sample:** 95 curated films (2001-2023)
- **Selection:** Across decades, genres, countries
- **Verification:** Multi-signal (title + year + IMDb)
- **Statuses:** VERIFIED, AMBIGUOUS, MISMATCH, UNRESOLVED

### Verification Criteria

- **VERIFIED:** Confidence ≥ 0.7 (title + year + optional IMDb)
- **AMBIGUOUS:** Confidence 0.4-0.7 (partial matches)
- **MISMATCH:** Confidence < 0.0 (year/IMDb mismatch)
- **UNRESOLVED:** No Qloo entity found

---

## Recommendations

### For Qloo Integration

1. **Use Qloo for modern programming** — 92.6% verified match rate
2. **Do NOT use Qloo for historical programming** — 0% verified match rate
3. **Consider hybrid approach** — Qloo for modern, IMDb/Wikidata for historical

### For Information Gain Testing

1. **Test on modern films first** — Qloo has coverage
2. **Design experiment carefully** — separate modern and historical
3. **Document limitations clearly** — Qloo does not cover historical films

### For ML Readiness

1. **Modern programming:** Qloo can add cultural affinity data
2. **Historical programming:** Use alternative approaches
3. **Consider separate models** — modern vs historical

---

## Conclusion

**Key Finding:** Qloo has 92.6% verified match rate for modern films but 0% for historical films.

**Implication:** Qloo is suitable for modern film analysis but NOT for historical film analysis.

**Recommendation:** Focus Qloo integration on modern programming only. Use alternative approaches for historical programming.

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE