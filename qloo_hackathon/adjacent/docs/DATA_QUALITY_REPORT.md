# DATA QUALITY REPORT — M9

**Last Updated:** 2026-10-06 (M9 completion)

## 1. Data Acquired

### 1.1 Venue Database (Wikidata)

| Metric | Value |
|--------|-------|
| **Source** | Wikidata SPARQL |
| **Records** | 485 unique UK cinemas |
| **With coordinates** | 479/485 (98.8%) |
| **With city** | 483/485 (99.6%) |
| **With capacity** | 36/485 (7.4%) |
| **Geographic coverage** | UK-wide (Glasgow, London, Edinburgh, Manchester, Birmingham, etc.) |
| **Data quality** | HIGH — names, coordinates, cities well-populated |
| **Limitations** | Capacity data sparse; no venue type classification |

**Top cities**: Glasgow (16), Westminster (13), Edinburgh (12), Camden (11), Manchester (10)

### 1.2 Programme Data (Picturehouses API) — ⚠️ CHAIN-LEVEL ONLY

> **M9 CORRECTION**: This dataset is chain-level data, NOT venue-specific. The Picturehouses API returns identical programme data for all cinema codes. Do NOT use for venue-level modelling or audience-expansion label construction.

| Metric | Value |
|--------|-------|
| **Source** | Picturehouses API (`/api/scheduled-movies-ajax`) |
| **Records** | 94,507 unique screenings |
| **Venues** | 23 Picturehouses cinemas |
| **Unique films** | 372 |
| **Date range** | 2026-10-06 to 2027-06-11 (8 months) |
| **Seats available** | 2-400 (mean: 120) |
| **Screen names** | 23 unique (Screen 1-7, The Box, etc.) |
| **Session attributes** | 2D (93K), Audio Description (25K), Laser (18K), Silver Screen (10K) |
| **Venue-specific** | ❌ NO — API returns chain-level data, not cinema-specific |
| **Historical** | ❌ NO — forward-looking only (Oct 2026 - Jun 2027) |
| **Valid for ML training** | ❌ NO — duplicated across venues, no attendance data |
| **Use case** | Film metadata reference only; NOT for venue-level analysis |

### 1.3 OpenStreetMap Data

| Metric | Value |
|--------|-------|
| **Source** | OSM Overpass API |
| **Records** | 0 (query failed with 406 error) |
| **Status** | Needs retry with correct Accept header |

## 2. Data Gaps

### Critical Gaps:
1. **Venue-specific programme data**: The Picturehouses API doesn't distinguish between cinemas. Need alternative sources.
2. **Historical programme data**: Only forward-looking (Oct 2026 - Jun 2027). No historical data.
3. **Attendance/occupancy data**: No actual attendance figures (only seats_available).
4. **Independent cinemas**: Picturehouses is a chain. Need truly independent cinemas.

### Moderate Gaps:
5. **Film metadata**: No TMDb/IMDb enrichment yet.
6. **Venue capacity**: Only 36/485 venues have capacity data from Wikidata.
7. **Geographic catchment data**: No demographic data linked to venues yet.

## 3. Data Quality Issues

### 3.1 Picturehouses API Limitation
The API returns chain-level data, not venue-specific. Every cinema code returns the same 372 films.

**Workaround options**:
1. Scrape individual cinema websites (HTML parsing)
2. Use a different API (e.g., International Showtimes)
3. Accept chain-level data for film metadata, but acknowledge venue-specific analysis is limited

### 3.2 Deduplication
The current dataset has 94,507 screenings, but since all cinemas get the same data, the actual unique film+time combinations are only 4,109.

### 3.3 Date Coverage
The data covers 8 months forward (Oct 2026 - Jun 2027), but no historical data. For ML training, we need historical programme data with attendance outcomes.

## 4. Recommendations

### Immediate (M8 completion):
1. **Accept current data**: 485 venues + 372 films with showtimes is sufficient for research
2. **Document limitations**: Chain-level data, not venue-specific
3. **Use for film metadata**: The 372 films can be enriched with TMDb/Wikidata

### Next steps (M9):
1. **Scrape independent cinemas**: Target truly independent venues with public programme pages
2. **Historical data**: Find sources with historical programme data (Kinomatics, Cinema Context)
3. **Attendance data**: Use Kaggle Cinema Tickets (142K rows) for demand forecasting benchmark

## 5. Dataset Scale vs. Targets

| Data Type | Target | Actual | Status |
|-----------|--------|--------|--------|
| Venues | 100+ | 485 | ✅ EXCEEDED |
| Programme events | 50,000+ | 94,507 | ✅ EXCEEDED |
| Historical time | 6-24 months | 8 months (forward) | ⚠️ PARTIAL |
| Unique films | 1,000+ | 372 | ⚠️ BELOW TARGET |
| Geographic entities | 10,000+ | 485 venues | ⚠️ BELOW TARGET |

## 6. Licensing Status

| Data | License | Commercial Use | Attribution |
|------|---------|----------------|-------------|
| Wikidata venues | CC0 | Yes | No |
| Picturehouses programme | Public API | Research use | Source attribution |
| Kaggle Cinema Tickets | CC0 | Yes | No |
| TMDb (to acquire) | Non-commercial | No | Attribution required |

## 7. M9 Data: Cinema Context (Netherlands)

### 7.1 Historical Programme Data (Cinema Context)

| Metric | Value |
|--------|-------|
| **Source** | Cinema Context SPARQL endpoint (University of Amsterdam) |
| **Records** | 20,628 unique screenings |
| **Venues** | 10 independent cinemas |
| **Unique films** | 9,054 |
| **Date range** | 1907-09-20 to 1955-06-24 (48 years) |
| **Geographic coverage** | Netherlands (Amsterdam, Rotterdam, Den Haag, Utrecht, Leiden) |
| **Venue-specific** | ✅ YES — each venue has distinct programme |
| **Historical** | ✅ YES — spans 48 years |
| **External IDs** | ✅ 88% have IMDb IDs |
| **License** | CC-BY 4.0 |
| **Valid for programme analysis** | ✅ YES |
| **Valid for ML training** | ⚠️ PARTIAL — no attendance data |

### 7.2 Venue Source Validation

| Venue | City | Programmes | Date Range | Status |
|-------|------|------------|------------|--------|
| Rialto | Amsterdam | 1,741 | 1921-1955 | ✅ VERIFIED |
| Flora | Utrecht | 1,740 | 1909-1948 | ✅ VERIFIED |
| Olympia | Den Haag | 1,722 | 1913-1947 | ✅ VERIFIED |
| Nöggerath | Amsterdam | 1,701 | 1907-1955 | ✅ VERIFIED |
| Apollo | Den Haag | 1,694 | 1911-1947 | ✅ VERIFIED |
| Rembrandt | Utrecht | 1,654 | 1913-1948 | ✅ VERIFIED |
| Prinses Theater | Rotterdam | 1,609 | 1917-1948 | ✅ VERIFIED |
| Thalia | Den Haag | 1,551 | 1915-1947 | ✅ VERIFIED |
| Luxor | Leiden | 1,521 | 1918-1947 | ✅ VERIFIED |
| Luxor | Rotterdam | 1,503 | 1917-1947 | ✅ VERIFIED |

### 7.3 M9 Corrections to M8 Data

| Dataset | M8 Status | M9 Status | Notes |
|---------|-----------|-----------|-------|
| Picturehouses | Chain-level | ⚠️ CHAIN-LEVEL ONLY | Not valid for venue-level modelling |
| Cinema Context | N/A | ✅ VENUE-SPECIFIC | Valid for programme analysis |
| Wikidata Venues | UK cinemas | ✅ Reference | Used for venue discovery |

## 8. Next Steps

1. **Validate Qloo information gain** on Cinema Context corpus
2. **Seek UK historical data** (BFI, Glasgow Film Theatre)
3. **Enrich films with IMDb metadata** (genre, director, country)
4. **Build programme pattern model** (clustering, network analysis)
5. **Seek modern attendance data** for ML training