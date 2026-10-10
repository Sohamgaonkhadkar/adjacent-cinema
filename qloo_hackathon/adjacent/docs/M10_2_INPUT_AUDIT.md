# M10.2: Input Audit — Modern Benchmark

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

This report audits the M10.1 modern benchmark input for data quality issues.

**Key Finding:** The benchmark has3 duplicate films that must be removed.

---

## Audit Results

### 1. Duplicate Check

**Result:** ❌ FAIL —3 duplicate films found

| Film | Occurrences | IMDb ID |
|------|-------------|---------|
| The Grand Budapest Hotel | 2 | tt2278388 |
| The Banshees of Inisherin | 2 | tt11813216 |
| The Power of the Dog | 2 | tt10293406 |

**Impact:** 3 duplicate records inflate the benchmark count.

### 2. IMDb ID Duplicate Check

**Result:** ❌ FAIL —4 duplicate IMDb IDs found

| IMDb ID | Occurrences | Film |
|---------|-------------|------|
| tt2278388 | 2 | The Grand Budapest Hotel |
| tt4925292 | 2 | Lady Bird |
| tt10293406 | 2 | The Power of the Dog |
| tt11813216 | 2 | The Banshees of Inisherin |

**Note:** Lady Bird (tt4925292) appears to have a duplicate IMDb ID but different title. Need to verify.

### 3. Year Distribution

**Result:** ✅ PASS — Reasonable distribution across years

| Year | Films |
|------|-------|
| 2001 | 2 |
| 2002 | 2 |
| 2003 | 2 |
| 2004 | 1 |
| 2005 | 1 |
| 2006 | 3 |
| 2007 | 2 |
| 2008 | 4 |
| 2009 | 2 |
| 2010 | 5 |
| 2011 | 5 |
| 2012 | 1 |
| 2013 | 6 |
| 2014 | 9 |
| 2015 | 8 |
| 2016 | 4 |
| 2017 | 6 |
| 2018 | 6 |
| 2019 | 6 |
| 2020 | 6 |
| 2021 | 3 |
| 2022 | 6 |
| 2023 | 5 |

**Observation:** 2014 has the most films (9). Distribution is skewed toward recent years.

### 4. Title-Year Consistency

**Result:** ✅ PASS — No films with inconsistent years

### 5. Resolution Status

**Result:** ✅ PASS — All films have resolution status

| Status | Count | Percentage |
|--------|-------|------------|
| VERIFIED | 88 | 92.6% |
| AMBIGUOUS | 7 | 7.4% |

---

## Bias Analysis

### 1. Popularity Bias

**Result:** ⚠️ HIGH BIAS

The benchmark is heavily biased toward globally famous films:
- The Dark Knight
- Inception
- Parasite
- Oppenheimer
- Barbie

**Impact:** Qloo may have better coverage of famous films. Results may not generalize to less famous films.

### 2. Genre Imbalance

**Result:** ⚠️ MODERATE BIAS

| Genre | Films | Percentage |
|-------|-------|------------|
| Drama | ~40 | ~42% |
| Comedy | ~10 | ~11% |
| Sci-Fi | ~5 | ~5% |
| Horror | ~8 | ~8% |
| Animation | ~10 | ~11% |
| Documentary | ~7 | ~7% |
| Other | ~15 | ~16% |

**Observation:** Drama is overrepresented. Horror and Sci-Fi are underrepresented.

### 3. Geographic/Language Imbalance

**Result:** ⚠️ HIGH BIAS

| Language | Films | Percentage |
|----------|-------|------------|
| English | ~75 | ~79% |
| French | ~5 | ~5% |
| Korean | ~3 | ~3% |
| Spanish | ~3 | ~3% |
| Japanese | ~3 | ~3% |
| German | ~2 | ~2% |
| Other | ~4 | ~4% |

**Observation:** English-language films are heavily overrepresented.

### 4. Title-Language Bias

**Result:** ⚠️ HIGH BIAS

Most films have English titles. Non-English titles are underrepresented.

**Impact:** Qloo may have better coverage of English-title films.

### 5. Year Distribution Bias

**Result:** ⚠️ MODERATE BIAS

Most films are from 2010-2023. Earlier decades (2000-2009) are underrepresented.

**Impact:** Qloo may have better coverage of recent films.

---

## Recommendations

### For Curated Benchmark v2

1. **Remove duplicates** —3 duplicate films
2. **Verify IMDb IDs** — Check tt4925292 (Lady Bird)
3. **Balance genres** — Add more horror, sci-fi, documentary
4. **Balance geography** — Add more non-English films
5. **Balance years** — Add more films from 2000-2009
6. **Document source** — Record where each film metadata came from

### For Bias Report

1. **Document all biases** — popularity, genre, geography, language, year
2. **Quantify confidence** — How much confidence in 92.6%?
3. **Recommend corrections** — How to reduce bias?

---

## Conclusion

**Input Quality:** ❌ NOT CLEAN

**Issues Found:**
- 3 duplicate films
- 4 duplicate IMDb IDs
- High popularity bias
- High genre imbalance
- High geographic/language imbalance

**Recommendation:** Rebuild curated benchmark with duplicates removed and bias documented.

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE