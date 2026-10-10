# M9: Verified Historical Independent Cinema Programme Corpus Report

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

M9 successfully built a verified historical independent cinema programme corpus using Cinema Context (University of Amsterdam) as the primary data source. The corpus contains **20,628 verified historical screenings** across **10 independent cinemas** in the Netherlands, spanning **1907-1955**.

**Key Achievement:** Genuine venue-specific historical programme data with full provenance, not chain-level duplicates.

---

## Data Source

### Cinema Context (University of Amsterdam)

- **URL:** https://data.create.humanities.uva.nl/sparql
- **License:** CC-BY 4.0
- **Coverage:** Netherlands, 1895-present
- **Records:** 100,000+ historical screenings
- **Format:** RDF/SPARQL endpoint
- **Verification:** Academic dataset, curated by film historians

### Source Validation

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Venue Identity | ✅ VERIFIED | Each venue has unique URI (e.g., `B000069`) |
| Programme Belongs to Venue | ✅ VERIFIED | SPARQL queries filter by venue URI |
| Date Belongs to Screening | ✅ VERIFIED | `sem:hasEarliestBeginTimeStamp` per programme |
| Film Belongs to Screening | ✅ VERIFIED | `schema:workPresented` links film to screening |
| Historical Records Exist | ✅ VERIFIED | Data spans 1895-1955 |
| Not Chain-Wide Feed | ✅ VERIFIED | Each venue has distinct programme schedule |

---

## Dataset Statistics

### Overview

| Metric | Value |
|--------|-------|
| Total Screenings | 20,628 |
| Unique Venues | 10 |
| Unique Films | 9,054 |
| Date Range | 1907-09-20 to 1955-06-24 |
| Screenings/Venue | 2,063 |
| Films/Venue | 905 |
| Country | Netherlands |

### Venue Breakdown

| Venue | City | Programmes | Date Range |
|-------|------|------------|------------|
| Rialto | Amsterdam | 1,741 | 1921-1955 |
| Flora | Utrecht | 1,740 | 1909-1948 |
| Olympia | Den Haag | 1,722 | 1913-1947 |
| Nöggerath | Amsterdam | 1,701 | 1907-1955 |
| Apollo | Den Haag | 1,694 | 1911-1947 |
| Rembrandt | Utrecht | 1,654 | 1913-1948 |
| Prinses Theater | Rotterdam | 1,609 | 1917-1948 |
| Thalia | Den Haag | 1,551 | 1915-1947 |
| Luxor | Leiden | 1,521 | 1918-1947 |
| Luxor | Rotterdam | 1,503 | 1917-1947 |

### Film Match Status

| Status | Count | Percentage |
|--------|-------|------------|
| VERIFIED | 18,194 | 88.2% |
| AMBIGUOUS | 2,434 | 11.8% |

---

## Data Quality

### Strengths

1. **Venue-Specific:** Each record belongs to a specific venue, not a chain
2. **Historical Depth:** Spans 48 years (1907-1955)
3. **Full Provenance:** Every record has source URL, retrieval timestamp, parser version
4. **External IDs:** 88% of films have IMDb IDs
5. **Academic Source:** Curated by film historians at University of Amsterdam
6. **SPARQL Access:** Reproducible queries, transparent data model

### Limitations

1. **Geographic Scope:** Netherlands only (not UK)
2. **Historical Period:** Pre-1955 (no modern programming data)
3. **Missing Fields:** No ticket prices, availability status, screen names
4. **Language:** Film titles in original language (Dutch, English, French, German)

### Comparison with Picturehouses Data

| Criterion | Picturehouses (M8) | Cinema Context (M9) |
|-----------|-------------------|---------------------|
| Venue-Specific | ❌ Chain-level | ✅ Venue-specific |
| Historical | ❌ Current only | ✅ 1907-1955 |
| Geographic | UK | Netherlands |
| Records | 94,507 | 20,628 |
| Unique Films | 372 | 9,054 |
| External IDs | ❌ None | ✅ IMDb |
| License | Unknown | CC-BY 4.0 |

---

## Canonical Dataset

### Location

- **Parquet:** `data/processed/independent_cinema_programmes.parquet`
- **Validation:** `data/venue_source_validation.csv`
- **Manifest:** `data/manifests/independent_cinema_programmes_2026-10-06_manifest.json`

### Schema

```
venue_id           STRING  - Cinema Context venue ID
venue_name         STRING  - Venue name
city               STRING  - City
country            STRING  - Country (Netherlands)
lat                FLOAT   - Latitude
lon                FLOAT   - Longitude
film_id            STRING  - Film identifier
film_title         STRING  - Film title
film_year          STRING  - Film year (if available)
screening_date     STRING  - Screening date (YYYY-MM-DD)
screening_time     STRING  - Screening time
screen_name        STRING  - Screen name
programme_name     STRING  - Programme name
event_type         STRING  - Event type (regular/special)
is_special_event   BOOLEAN - Special event flag
is_festival        BOOLEAN - Festival flag
ticket_price       STRING  - Ticket price
availability_status STRING - Status (historical)
source_url         STRING  - Data source URL
retrieved_at       STRING  - Retrieval timestamp
parser_version     STRING  - Parser version
data_status        STRING  - Data status (verified)
film_match_status  STRING  - Film match status
venue_match_status STRING  - Venue match status
imdb_id            STRING  - IMDb ID
source_id          STRING  - Source identifier
source_hash        STRING  - Source hash for deduplication
```

---

## Outcome Signal Investigation

### Available Signals

| Signal | Type | Status | Notes |
|--------|------|--------|-------|
| Film Title | DIRECT | ✅ Available | Full title in original language |
| Screening Date | DIRECT | ✅ Available | Exact date per programme |
| Venue Identity | DIRECT | ✅ Available | Unique venue URI |
| Film External ID | DIRECT | ✅ Available | IMDb ID for 88% of films |
| Historical Programming Patterns | DERIVED | ✅ Available | Can analyze programming over time |
| Film Genre/Category | DERIVED | ⚠️ Partial | Can derive from IMDb data |
| Audience Attendance | UNAVAILABLE | ❌ Not available | No attendance data in Cinema Context |
| Ticket Price | UNAVAILABLE | ❌ Not available | No price data |
| Availability Status | UNAVAILABLE | ❌ Not available | Historical data only |

### ML Readiness Assessment

**Verdict: PARTIALLY VIABLE**

The dataset is suitable for:
- ✅ Programme pattern analysis (what films are programmed together)
- ✅ Temporal trend analysis (how programming evolves over time)
- ✅ Cross-venue comparison (programming differences between venues)
- ✅ Film network analysis (which films are co-programmed)
- ✅ Qloo information-gain validation (can test Qloo on historical programming)

The dataset is NOT suitable for:
- ❌ Audience expansion prediction (no attendance data)
- ❌ Demand forecasting (no ticket sales data)
- ❌ Real-time recommendation (historical data only)

---

## Qloo Integration Potential

### ⚠️ M9 QLOO VALIDATION: INVALID

**Status:** INVALIDATED by M10 Data Integrity Review

**Reason:** M9 validation only checked if Qloo returned a result, NOT whether the result was the correct historical film. Evidence shows systematic mismatches: historical titles mapped to unrelated modern films with similar names.

**Evidence:** See `docs/M9_QLOO_VALIDATION.json` for detailed mismatch examples.

**Corrected Assessment:**
- Original claim: 100% hit rate (27/27 films found)
- Actual verified matches: 0
- Actual mismatches: 12/12 sampled films
- Conclusion: Qloo search returns fuzzy matches to unrelated modern films

**Do NOT use M9 Qloo validation as evidence for any claims.**

### Original Assessment (Now Invalid)

The verified historical corpus can be used to validate Qloo's information gain:

1. **Historical Programme → Qloo Cultural Profile**
   - Input: Film titles from historical programme
   - Output: Qloo cultural affinity tags
   - Test: Do Qloo tags capture programming patterns?

2. **Cross-Venue Comparison**
   - Input: Programming from two different venues
   - Output: Qloo affinity profiles
   - Test: Do venues with similar programming get similar Qloo profiles?

3. **Temporal Analysis**
   - Input: Programming from different eras
   - Output: Qloo cultural trends
   - Test: Do Qloo tags reflect historical cultural shifts?

**Note:** These tests require proper entity resolution BEFORE testing Qloo information gain. M10 will build trusted entity resolution first.

---

## Recommendations

### For M10 (Next Milestone)

1. **Expand to UK Venues:** Identify UK independent cinemas with similar historical data
2. **Add IMDb Metadata:** Enrich films with genre, director, country of origin
3. **Build Programme Networks:** Analyze co-programming patterns
4. **Validate Qloo:** Test Qloo information gain on historical programming
5. **Consider Adjacent Analysis:** Use historical programming to inform "what's adjacent" analysis

### For Dataset Strategy

1. **Keep Cinema Context as Primary:** It's the only verified venue-specific historical dataset
2. **Mark Picturehouses as Reference Only:** Chain-level data, not venue-specific
3. **Seek Additional Sources:** BFI Southbank, Glasgow Film Theatre, other UK independents
4. **Build Multi-Dataset Strategy:** Combine historical (Cinema Context) with modern (if available)

---

## Conclusion

M9 successfully delivered a verified historical independent cinema programme corpus. The Cinema Context dataset provides genuine venue-specific historical programming data with full provenance, suitable for programme pattern analysis and Qloo information-gain validation.

**Key Achievement:** Moved from chain-level duplicates (Picturehouses) to venue-specific historical data (Cinema Context).

**Next Step:** Validate Qloo information gain on this verified corpus.

---

**Report Generated:** 2026-10-06
**Dataset Version:** 2026-10-06
**Status:** COMPLETE