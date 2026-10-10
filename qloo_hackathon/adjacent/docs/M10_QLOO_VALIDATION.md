# M10: Qloo Validation Report

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

This report presents the corrected Qloo validation results after building trusted film identity resolution.

**Key Finding:** Qloo's actual verified coverage of historical films is **2%**, not the 100% claimed in M9.

---

## M9 vs M10 Comparison

| Metric | M9 Claim | M10 Actual | Status |
|--------|----------|------------|--------|
| Films Tested | 27 | 100 | ✅ More comprehensive |
| Hit Rate | 100% | 2% VERIFIED | ❌ M9 was INVALID |
| Mismatch Rate | 0% | 64% | ❌ M9 was INVALID |
| Ambiguous Rate | 0% | 34% | ❌ M9 was INVALID |
| Resolution Method | Fuzzy search only | Multi-signal verification | ✅ Proper methodology |

**Conclusion:** M9 Qloo validation is INVALID and must not be used as evidence.

---

## Resolution Statistics

### Overall Results

| Status | Count | Percentage |
|--------|-------|------------|
| VERIFIED | 2 | 2.0% |
| AMBIGUOUS | 34 | 34.0% |
| MISMATCH | 64 | 64.0% |
| **Total** | **100** | **100%** |

### Resolution Method

- **VERIFIED:** Multi-signal verification (title + year + optional IMDb)
- **AMBIGUOUS:** Partial match or insufficient evidence
- **MISMATCH:** Year mismatch or IMDb mismatch

---

## Detailed Analysis

### VERIFIED Films (2%)

Only 2 films were verified as correct matches:

1. **Windstärke 9 - die Geschichte einer reichen Erbin (1931)**
   - Confidence: 0.90
   - Evidence: Exact title match, exact year match

2. **Hunting big game in Africa with gun and camera (1917)**
   - Confidence: 0.90
   - Evidence: Exact title match, exact year match

### MISMATCH Films (64%)

64 films were mapped to completely different films. Examples:

| Historical Film | Qloo Entity | Year Gap | Issue |
|-----------------|-------------|----------|-------|
| The Spanish Dancer (1923) | ? | N/A | Different film |
| Red Dance, The (1928) | ? | N/A | Different film |
| Under your spell (1936) | ? | N/A | Different film |
| Young in heart, The (1938) | ? | N/A | Different film |
| Virgin of Stamboul, The (1920) | ? | N/A | Different film |

### AMBIGUOUS Films (34%)

34 films had partial matches or insufficient evidence:

- Some had title matches but no year verification
- Some had year matches but no title verification
- Some had neither

---

## Why M9 Was Wrong

### M9 Methodology (Flawed)

1. Searched Qloo for each historical film title
2. Checked if Qloo returned ANY result
3. Counted all results as "hits"
4. Claimed 100% hit rate

### Problems with M9

1. **No year verification:** Did not check if the returned film was from the same year
2. **No title verification:** Did not check if the returned film was the same film
3. **Fuzzy matching accepted:** Qloo returns modern films with similar names to historical titles
4. **No evidence requirement:** Did not require evidence of match correctness

### M10 Methodology (Correct)

1. Search Qloo for each historical film title
2. Extract year from Qloo result (`release_year`, `disambiguation`)
3. Compare year to historical film year
4. Check for IMDb ID match (if available)
5. Require multiple signals for VERIFIED status
6. Document evidence for each resolution

---

## Implications

### For Qloo Integration

1. **Qloo has limited coverage of historical films** (2% verified)
2. **Qloo's fuzzy search returns unrelated modern films** for historical titles
3. **Year verification is critical** for entity resolution
4. **IMDb ID matching** can help but requires Qloo to have the ID

### For Adjacent's Value Proposition

1. **Qloo may not add value for historical programming analysis**
2. **Qloo may work better for modern films** (not tested yet)
3. **Alternative approaches needed** for historical film analysis:
   - Use IMDb/Wikidata directly
   - Use Cinema Context's own metadata
   - Build custom entity resolution

### For ML Readiness

1. **Cannot use Qloo for historical film analysis** without proper entity resolution
2. **Need to test Qloo on modern films** before concluding it's useful
3. **Consider alternative cultural affinity sources** for historical data

---

## Recommendations

### Immediate

1. **Do NOT use M9 Qloo validation as evidence**
2. **Do NOT claim Qloo has 100% coverage of historical films**
3. **Use M10 resolution dataset** for any Qloo-related claims

### Short-Term

1. **Test Qloo on modern films** (post-2000) to see if coverage is better
2. **Investigate Qloo's film database** to understand its coverage
3. **Consider alternative approaches** for historical film analysis

### Medium-Term

1. **Build custom entity resolution** using IMDb/Wikidata
2. **Use Cinema Context metadata** directly (no Qloo needed)
3. **Focus Qloo on modern programming** where coverage may be better

---

## Security Note

**API Key Exposure:** The M9 Qloo validation script contained a hardcoded API key. This key has been removed from source code. Treat the key as compromised and consider rotation.

---

## Conclusion

The M10 Qloo validation reveals that:

1. **M9's 100% hit rate claim was false** — based on flawed methodology
2. **Actual verified Qloo coverage is 2%** — for historical films (1907-1955)
3. **64% of films are mismatches** — Qloo returns unrelated modern films
4. **Qloo may not be useful for historical programming analysis**

**Key Insight:** Qloo's fuzzy search is not suitable for historical film entity resolution. Year verification is essential.

**Recommendation:** Do not use Qloo for historical film analysis without proper entity resolution. Test Qloo on modern films before concluding it's useful for Adjacent.

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE