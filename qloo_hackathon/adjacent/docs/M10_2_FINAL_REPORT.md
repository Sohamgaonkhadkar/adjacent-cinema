# M10.2: Final Report — Benchmark Integrity + Trusted Qloo Resolution Audit

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

M10.2 audited and rebuilt the Qloo benchmark for scientific trustworthiness.

**Key Findings:**

1. **Modern benchmark input is clean** — 91 unique films, no duplicates
2. **Every benchmark film is uniquely identified** — One IMDb ID per film
3. **Qloo resolver is deterministic and evidence-based** — IMDb ID matching as primary method
4. **Corrected verified match rate:** 93.4% (85/91 films)
5. **Benchmark is representative enough for information-gain experiment** — With documented limitations
6. **What remains biased:** Popularity, genre, language, year distribution
7. **M11 is now justified** — Can proceed with information-gain test

---

## Answers to Required Questions

### 1. Is the modern benchmark input clean?

**Answer:** ✅ YES

**Evidence:**
- Removed 3 duplicate films
- Verified 91 unique films with unique IMDb IDs
- All metadata from IMDb (verified source)
- No incorrect title/year/IMDb combinations

### 2. Is every benchmark film uniquely identified?

**Answer:** ✅ YES

**Evidence:**
- 91 unique films
- 91 unique IMDb IDs
- One canonical IMDb ID per film
- No duplicates

### 3. Is the Qloo resolver deterministic and evidence-based?

**Answer:** ✅ YES

**Evidence:**
- Resolver uses IMDb ID matching as primary method
- Same IMDb → VERIFIED
- Different IMDb → MISMATCH
- Every resolution has explicit evidence
- No weighted confidence scores as sole authority

### 4. What is the corrected verified match rate?

**Answer:** 93.4% (85/91 films)

**Evidence:**
- 85 films verified via IMDb ID match
- 6 films mismatched (IMDb ID mismatch)
- 0 films ambiguous
- 0 films unresolved

**Comparison with M10.1:**
- M10.1: 92.6% (88/95 films) — CURATED_PRELIMINARY_BENCHMARK
- M10.2: 93.4% (85/91 films) — Clean curated benchmark

**Change:** +0.8% (after removing duplicates and fixing resolver)

### 5. Is the corrected benchmark representative enough for the information-gain experiment?

**Answer:** ⚠️ PARTIALLY

**Strengths:**
- Clean input (no duplicates)
- Verified metadata (IMDb)
- Transparent methodology
- Explicit evidence for each resolution

**Weaknesses:**
- Curated list (not random sample)
- Popularity bias (famous films)
- Genre imbalance (drama overrepresented)
- Language imbalance (English overrepresented)
- Small sample size (91 films)

**Recommendation:** Proceed with M11, but document limitations.

### 6. What remains biased?

**Answer:**

| Bias | Severity | Impact |
|------|----------|--------|
| Curated-list bias | HIGH | May not represent less famous films |
| Popularity bias | HIGH | Qloo may have better coverage of famous films |
| Genre imbalance | MODERATE | Drama overrepresented |
| Geographic/language imbalance | HIGH | English overrepresented |
| Year distribution bias | MODERATE | Recent films overrepresented |
| Benchmark size | MODERATE | 91 films may not be representative |
| Source-selection bias | MODERATE | Researcher-selected films |
| Resolver bias | LOW | IMDb ID matching only |

### 7. Is M11 now justified?

**Answer:** ✅ YES

**Reasoning:**
- Benchmark is clean and trustworthy
- Resolver is deterministic and evidence-based
- Verified match rate is 93.4%
- Limitations are documented
- Can proceed with information-gain test

**Caution:** Results may not generalize to less famous films.

---

## Deliverables

### Created

| File | Description |
|------|-------------|
| `data/processed/qloo_modern_curated_benchmark_v2.parquet` | Clean curated benchmark |
| `data/processed/qloo_resolution_audit_v2.parquet` | Resolution audit with evidence |
| `docs/M10_2_INPUT_AUDIT.md` | Input audit report |
| `docs/M10_2_CURATED_BENCHMARK.md` | Curated benchmark report |
| `docs/M10_2_BIAS_AND_LIMITATIONS.md` | Bias and limitations report |
| `docs/M10_2_FINAL_REPORT.md` | This report |
| `research/scripts/qloo_curated_benchmark_v2.py` | Curated benchmark script |

### Updated

| File | Description |
|------|-------------|
| `docs/M10_1_QLOO_BENCHMARK.md` | Classified as CURATED_PRELIMINARY_BENCHMARK |
| `docs/M10_1_FINAL_REPORT.md` | Updated with M10.2 findings |

---

## Key Findings

### 1. Benchmark Integrity

- ✅ Input is clean (91 unique films, no duplicates)
- ✅ Every film is uniquely identified (one IMDb ID per film)
- ✅ Resolver is deterministic and evidence-based
- ✅ Every resolution has explicit evidence

### 2. Corrected Verified Match Rate

- **M10.1:** 92.6% (88/95 films) — CURATED_PRELIMINARY_BENCHMARK
- **M10.2:** 93.4% (85/91 films) — Clean curated benchmark
- **Change:** +0.8% (after removing duplicates and fixing resolver)

### 3. Mismatched Films

6 films had IMDb ID mismatches:
1. The Boy and the Heron (2023)
2. March of the Penguins (2005)
3. My Octopus Teacher (2020)
4. The Witch (2015)
5. The Whale (2022)
6. The Holdovers (2023)

**Interpretation:** Qloo returned a different film for these 6 titles.

### 4. Bias and Limitations

- **Popularity bias:** HIGH — Famous films overrepresented
- **Genre imbalance:** MODERATE — Drama overrepresented
- **Language imbalance:** HIGH — English overrepresented
- **Year distribution bias:** MODERATE — Recent films overrepresented
- **Benchmark size:** MODERATE — 91 films may not be representative

### 5. Confidence Assessment

**Confidence in 93.4% figure:** MODERATE

**Reasoning:** The benchmark is well-constructed but biased toward famous, English-language, recent films.

---

## Recommendations

### For M11 (Information Gain Test)

1. **Use the curated benchmark** — 93.4% verified match rate
2. **Document limitations** — Benchmark is biased toward famous films
3. **Test with caution** — Results may not generalize

### For Future Benchmarks

1. **Random sample** — Use a random sample from a film database
2. **Balance genres** — Include all genres equally
3. **Balance geography** — Include non-English films
4. **Balance years** — Include films from all decades
5. **Increase size** — 200+ films minimum

### For Generalization

1. **Do NOT claim "Qloo coverage"** — Use "verified match rate on benchmark"
2. **Document biases** — Make biases explicit
3. **Test generalization** — Run additional benchmarks with different samples

---

## Conclusion

M10.2 successfully audited and rebuilt the Qloo benchmark for scientific trustworthiness.

**Key Findings:**

1. **Benchmark is clean** — 91 unique films, no duplicates
2. **Resolver is deterministic** — IMDb ID matching as primary method
3. **Corrected verified match rate:** 93.4% (85/91 films)
4. **Benchmark is biased** — Famous, English-language, recent films
5. **M11 is justified** — Can proceed with information-gain test

**Defensible Statement:** "Qloo verified 85/91 films in this curated benchmark."

**Do NOT Claim:** "Qloo has 93.4% modern-film coverage."

**Next Milestone:** M11 — Qloo Information Gain Test on Modern Programming

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE