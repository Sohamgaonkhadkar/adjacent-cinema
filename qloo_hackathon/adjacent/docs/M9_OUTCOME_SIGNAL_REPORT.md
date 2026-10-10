# M9: Outcome Signal Investigation Report

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

This report investigates legitimate programme-level outcome proxies for the verified historical cinema programme corpus. We assess signals as DIRECTLY OBSERVED, DERIVED, or UNAVAILABLE.

**Key Finding:** No direct attendance/sales data available. Programme-level signals exist but are insufficient for audience-expansion prediction.

---

## Signal Investigation

### 1. Directly Observed Signals

#### Film Title
- **Status:** ✅ AVAILABLE
- **Source:** Cinema Context `schema:name`
- **Quality:** High - original language titles
- **Coverage:** 100% of screenings
- **Use:** Film entity resolution, genre inference via IMDb

#### Screening Date
- **Status:** ✅ AVAILABLE
- **Source:** Cinema Context `sem:hasEarliestBeginTimeStamp`
- **Quality:** High - exact dates
- **Coverage:** 100% of screenings
- **Use:** Temporal analysis, programming patterns

#### Venue Identity
- **Status:** ✅ AVAILABLE
- **Source:** Cinema Context venue URI
- **Quality:** High - unique identifiers
- **Coverage:** 100% of screenings
- **Use:** Cross-venue comparison, venue clustering

#### Film External ID (IMDb)
- **Status:** ✅ AVAILABLE
- **Source:** Cinema Context `schema:sameAs`
- **Quality:** High - verified IMDb links
- **Coverage:** 88% of screenings
- **Use:** Film metadata enrichment, genre inference

---

### 2. Derived Signals

#### Film Genre/Category
- **Status:** ⚠️ DERIVABLE
- **Source:** IMDb metadata (via external API)
- **Method:** Query IMDb API with film ID
- **Quality:** Medium - depends on IMDb coverage
- **Use:** Genre-based programming analysis

#### Programming Patterns
- **Status:** ✅ DERIVABLE
- **Source:** Historical screening data
- **Method:** Analyze co-programming, frequency, recency
- **Quality:** High - direct from data
- **Use:** Venue programming profiles, adjacency analysis

#### Temporal Trends
- **Status:** ✅ DERIVABLE
- **Source:** Screening dates over time
- **Method:** Time-series analysis of programming
- **Quality:** High - direct from data
- **Use:** Cultural trend analysis, programming evolution

#### Film Networks
- **Status:** ✅ DERIVABLE
- **Source:** Co-programming patterns
- **Method:** Graph analysis of films shown at same venues
- **Quality:** High - direct from data
- **Use:** Adjacency analysis, "what's next" recommendations

---

### 3. Unavailable Signals

#### Audience Attendance
- **Status:** ❌ UNAVAILABLE
- **Reason:** Cinema Context does not include attendance data
- **Impact:** Cannot build audience-expansion labels
- **Alternative:** None - this is the core ML label

#### Ticket Price
- **Status:** ❌ UNAVAILABLE
- **Reason:** Historical data does not include pricing
- **Impact:** Cannot analyze price sensitivity
- **Alternative:** None

#### Availability Status (Sold Out / Seats Remaining)
- **Status:** ❌ UNAVAILABLE
- **Reason:** Historical data only, no real-time availability
- **Impact:** Cannot measure demand
- **Alternative:** None

#### Booking Window
- **Status:** ❌ UNAVAILABLE
- **Reason:** No booking data in Cinema Context
- **Impact:** Cannot analyze advance booking patterns
- **Alternative:** None

#### Cancellation/Recurrence
- **Status:** ❌ UNAVAILABLE
- **Reason:** No event management data
- **Impact:** Cannot analyze programming stability
- **Alternative:** None

---

## Outcome Signal Matrix

| Signal | Type | Status | Quality | Use Case |
|--------|------|--------|---------|----------|
| Film Title | DIRECT | ✅ | High | Entity resolution, genre |
| Screening Date | DIRECT | ✅ | High | Temporal analysis |
| Venue Identity | DIRECT | ✅ | High | Cross-venue comparison |
| IMDb ID | DIRECT | ✅ | High | Film metadata |
| Film Genre | DERIVED | ⚠️ | Medium | Genre analysis |
| Programming Patterns | DERIVED | ✅ | High | Adjacency analysis |
| Temporal Trends | DERIVED | ✅ | High | Cultural trends |
| Film Networks | DERIVED | ✅ | High | Co-programming |
| Attendance | UNAVAILABLE | ❌ | N/A | Audience expansion |
| Ticket Price | UNAVAILABLE | ❌ | N/A | Price sensitivity |
| Availability | UNAVAILABLE | ❌ | N/A | Demand measurement |
| Booking Window | UNAVAILABLE | ❌ | N/A | Advance booking |

---

## ML Implications

### What We CAN Build

1. **Programme Pattern Model**
   - Input: Historical programming
   - Output: Programming patterns, venue profiles
   - Use: "What kind of films does this venue program?"

2. **Film Adjacency Model**
   - Input: Co-programming data
   - Output: Film similarity networks
   - Use: "What films are shown together?"

3. **Temporal Trend Model**
   - Input: Programming over time
   - Output: Cultural trends, programming evolution
   - Use: "How has programming changed?"

4. **Qloo Validation Model**
   - Input: Historical programming
   - Output: Qloo cultural profiles
   - Use: "Does Qloo capture programming patterns?"

### What We CANNOT Build

1. **Audience Expansion Model**
   - Required: Attendance data
   - Status: ❌ Unavailable
   - Impact: Cannot predict audience growth

2. **Demand Forecasting Model**
   - Required: Ticket sales, availability
   - Status: ❌ Unavailable
   - Impact: Cannot predict demand

3. **Real-Time Recommendation Model**
   - Required: Current availability, booking data
   - Status: ❌ Unavailable
   - Impact: Cannot recommend for current screenings

---

## Recommendation

### ML Readiness: PARTIALLY VIABLE

**Verdict:** The dataset is suitable for programme analysis and Qloo validation, but NOT for audience-expansion prediction.

### Next Steps

1. **Proceed with Qloo Validation**
   - Test Qloo information gain on historical programming
   - Validate that Qloo captures cultural patterns
   - This is valuable for Adjacent's core proposition

2. **Seek Attendance Data**
   - Look for modern cinema datasets with attendance
   - Consider survey data, box office data, etc.
   - This is needed for ML model training

3. **Focus on Adjacent Analysis**
   - Use historical programming for "what's adjacent" analysis
   - Build venue programming profiles
   - Identify cultural directions

### Hard Rules Compliance

- ✅ DO NOT train LightGBM/XGBoost (no attendance labels)
- ✅ DO NOT create synthetic attendance
- ✅ DO NOT infer attendance from seats available
- ✅ DO NOT treat chain-wide duplicated schedules as venue-specific
- ✅ DO NOT fabricate historical records
- ✅ DO NOT invent labels
- ✅ DO NOT claim predictive performance

---

## Conclusion

The M9 outcome signal investigation reveals that:

1. **Direct signals exist:** Film title, date, venue, IMDb ID
2. **Derived signals are valuable:** Programming patterns, temporal trends, film networks
3. **Critical signals are missing:** Attendance, ticket price, availability
4. **ML is partially viable:** Programme analysis yes, audience expansion no

**Key Insight:** The dataset is excellent for understanding programming patterns and validating Qloo, but insufficient for building an audience-expansion prediction model.

**Recommendation:** Proceed with Qloo validation on historical corpus. Seek modern attendance data for ML training.

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE