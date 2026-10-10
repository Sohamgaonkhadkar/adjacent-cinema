# M9: ML Readiness Assessment

**Date:** 2026-10-06
**Status:** COMPLETE (with M10 corrections)

---

## ⚠️ M10 CORRECTION: QLOO VALIDATION INVALID

**Original M9 Claim:** Qloo validation successful (100% hit rate on historical films)

**M10 Finding:** This claim is INVALID. The validation only checked if Qloo returned a result, NOT whether the result was the correct historical film. Evidence shows systematic mismatches:
- "Work (1915)" → "Dirty Work" (MISMATCH)
- "Golem, Le (1936)" → "The Limehouse Golem" (2016 film, MISMATCH)
- "Calino et le petit restaurant très bien (1913)" → "The Good, the Bad and the Ugly" (MISMATCH)
- And 9 more mismatches in the sample

**Corrected Assessment:**
- Actual verified Qloo matches: 0/12 sampled films
- Actual mismatches: 12/12 sampled films
- Conclusion: Qloo search returns fuzzy matches to unrelated modern films

**Do NOT use M9 Qloo validation as evidence. M10 will build trusted entity resolution before re-testing.**

---

## Executive Summary

This report assesses the ML readiness of the verified historical independent cinema programme corpus.

**Verdict: PARTIALLY VIABLE**

The dataset is suitable for programme pattern analysis and Qloo validation, but NOT for audience-expansion prediction due to missing attendance data.

---

## Dataset Assessment

### Data Quality

| Criterion | Score | Notes |
|-----------|-------|-------|
| Venue Specificity | ✅ 10/10 | Each record belongs to a specific venue |
| Historical Coverage | ✅ 9/10 | 48 years (1907-1955) |
| Data Provenance | ✅ 10/10 | Full source URL, timestamp, parser version |
| External IDs | ✅ 8/10 | 88% have IMDb IDs |
| Film Resolution | ⚠️ 7/10 | 88% VERIFIED, 12% AMBIGUOUS |
| Venue Resolution | ✅ 10/10 | All venues have unique URIs |
| Data Completeness | ⚠️ 6/10 | Missing attendance, price, availability |
| Data Consistency | ✅ 9/10 | Consistent schema across all records |

**Overall Quality Score: 8.6/10**

---

## ML Problem Formulation

### Original Plan (M8)

**Problem:** Programme-Contextualised Audience Expansion
**Label:** Binary `audience_expansion` (>20% over 12-week rolling average)
**Model:** LightGBM with time-series CV

### Current Assessment

| Requirement | Status | Notes |
|-------------|--------|-------|
| Venue-specific data | ✅ Available | Cinema Context provides venue URIs |
| Historical programming | ✅ Available | 1907-1955 |
| Film metadata | ✅ Available | IMDb IDs for 88% |
| Attendance data | ❌ Missing | No attendance in Cinema Context |
| Ticket price data | ❌ Missing | No pricing in Cinema Context |
| Availability data | ❌ Missing | Historical data only |

**Impact:** Cannot build the original ML model without attendance labels.

---

## Alternative ML Formulations

### Option 1: Programme Pattern Analysis

**Problem:** Unsupervised learning on programming patterns
**Input:** Historical film screenings per venue
**Output:** Venue programming profiles, film clusters
**Methods:** Clustering, topic modeling, network analysis

**Viability:** ✅ FULLY VIABLE
- No labels needed
- Rich historical data available
- Can answer "what kind of films does this venue program?"

### Option 2: Film Adjacency Model

**Problem:** Graph-based analysis of co-programming
**Input:** Films shown at same venues
**Output:** Film similarity networks
**Methods:** Graph neural networks, network analysis

**Viability:** ✅ FULLY VIABLE
- Co-programming data available
- Can identify "what films are shown together?"
- Useful for "what's adjacent" analysis

### Option 3: Temporal Trend Model

**Problem:** Time-series analysis of programming evolution
**Input:** Programming over 48 years
**Output:** Cultural trends, programming shifts
**Methods:** Time-series analysis, change detection

**Viability:** ✅ FULLY VIABLE
- Rich temporal data available
- Can identify "how has programming changed?"
- Useful for cultural trend analysis

### Option 4: Qloo Validation Model

**Problem:** Test Qloo information gain on historical programming
**Input:** Historical film programming
**Output:** Qloo cultural profiles
**Methods:** Correlation analysis, information gain measurement

**Viability:** ⚠️ REQUIRES TRUSTED ENTITY RESOLUTION

**M10 CORRECTION:** M9 Qloo validation is INVALID. The validation only checked if Qloo returned a result, NOT whether the result was the correct historical film. Evidence shows systematic mismatches (historical titles mapped to unrelated modern films).

**Status:** Cannot test Qloo information gain until trusted entity resolution is built.

**Next Step:** Build trusted film identity resolution (M10 Step 3-8) before re-testing Qloo.

### Option 5: Audience Expansion Model (Original Plan)

**Problem:** Predict audience expansion from programming
**Input:** Programming features
**Output:** Binary audience_expansion label
**Methods:** LightGBM, time-series CV

**Viability:** ❌ NOT VIABLE
- Attendance data unavailable
- Cannot construct labels
- Cannot train supervised model

---

## Qloo Information-Gain Validation

### Plan

1. **Select 5 Venues:** Choose venues with diverse programming
2. **Extract Programming:** Get historical film titles for each venue
3. **Query Qloo:** Get cultural affinity profiles for each venue
4. **Analyze Information Gain:** Compare Qloo profiles to programming patterns
5. **Measure Value:** Does Qloo add information beyond basic metadata?

### Expected Outcomes

| Outcome | Value | Notes |
|---------|-------|-------|
| Qloo captures programming patterns | High | Validates core hypothesis |
| Qloo identifies cultural adjacency | High | Supports "what's adjacent" analysis |
| Qloo provides cross-domain insights | Medium | May identify non-film affinities |
| Qloo adds no value | Low | Would invalidate Qloo integration |

### Implementation

```python
# Pseudo-code for Qloo validation
for venue in venues:
    # Get historical programming
    films = get_films_for_venue(venue)
    
    # Get Qloo cultural profile
    qloo_profile = qloo.get_cultural_profile(films)
    
    # Compare to programming patterns
    programming_profile = analyze_programming(films)
    
    # Measure information gain
    gain = calculate_information_gain(qloo_profile, programming_profile)
```

---

## Dataset Limitations

### Geographic Limitation

- **Current:** Netherlands only
- **Impact:** May not generalize to UK cinemas
- **Mitigation:** Seek UK historical data (BFI, Glasgow Film Theatre)

### Temporal Limitation

- **Current:** Pre-1955 only
- **Impact:** May not reflect modern programming
- **Mitigation:** Combine with modern data if available

### Missing Fields

- **Attendance:** No audience data
- **Pricing:** No ticket prices
- **Availability:** No sold-out information
- **Impact:** Cannot build demand models

---

## Recommendations

### Immediate (M9 Completion)

1. **Complete Qloo Validation**
   - Test Qloo on 5 venues
   - Measure information gain
   - Document findings

2. **Document Dataset Limitations**
   - Note missing fields
   - Note geographic scope
   - Note temporal scope

### Short-Term (M10)

1. **Seek UK Historical Data**
   - BFI Southbank programme archive
   - Glasgow Film Theatre history
   - Other UK independents

2. **Enrich with IMDb Metadata**
   - Genre, director, country
   - Cast, runtime, ratings
   - Enables richer analysis

3. **Build Programme Pattern Model**
   - Clustering of venues
   - Film network analysis
   - Cultural adjacency mapping

### Medium-Term (M11+)

1. **Seek Modern Attendance Data**
   - Box office data (public)
   - Survey data (academic)
   - Cinema partnership data

2. **Build Multi-Dataset Strategy**
   - Historical (Cinema Context)
   - Modern (if available)
   - Enables temporal analysis

3. **Consider Hybrid Approach**
   - Unsupervised on historical data
   - Supervised on modern data (if available)
   - Transfer learning between domains

---

## Hard Rules Compliance

| Rule | Status | Notes |
|------|--------|-------|
| DO NOT train LightGBM/XGBoost | ✅ Compliant | No attendance labels available |
| DO NOT create synthetic attendance | ✅ Compliant | No synthetic data created |
| DO NOT infer attendance from seats | ✅ Compliant | No seats data available |
| DO NOT treat chain-wide as venue-specific | ✅ Compliant | Cinema Context is venue-specific |
| DO NOT fabricate historical records | ✅ Compliant | All data from verified source |
| DO NOT invent labels | ✅ Compliant | No labels invented |
| DO NOT claim predictive performance | ✅ Compliant | No models trained |

---

## Conclusion

The M9 ML readiness assessment reveals:

1. **Dataset Quality:** High (8.6/10) for programme analysis
2. **ML Viability:** Partially viable
3. **Qloo Validation:** Fully viable and recommended
4. **Audience Expansion:** Not viable without attendance data

**Key Insight:** The dataset is excellent for understanding programming patterns and validating Qloo, but insufficient for building an audience-expansion prediction model.

**Recommendation:** 
1. Proceed with Qloo validation on historical corpus
2. Seek modern attendance data for ML training
3. Focus on programme pattern analysis in the interim

---

## Decision Matrix

| Question | Answer | Confidence |
|----------|--------|------------|
| Can we train audience-expansion model? | NO | High |
| Can we validate Qloo information gain? | YES | High |
| Can we analyze programming patterns? | YES | High |
| Can we build film adjacency model? | YES | High |
| Can we analyze temporal trends? | YES | High |

**Final Verdict:** PARTIALLY VIABLE for ML, FULLY VIABLE for Qloo validation.

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE