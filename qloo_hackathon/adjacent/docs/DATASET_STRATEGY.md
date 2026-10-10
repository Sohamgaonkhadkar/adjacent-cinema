# DATASET STRATEGY — Adjacent

**Last Updated:** 2026-10-06 (M9 completion)

## 1. Datasets Discovered

### Tier 1: Public/Acquirable
| Dataset | Type | Scale | Access | Status |
|---------|------|-------|--------|--------|
| Kaggle Cinema Tickets | Attendance | 142,524 rows | Free download | READY |
| UK Cinema Infrastructure | Venue aggregates | National stats | Public | READY |
| BFI Statistical Yearbook | Market benchmarks | Annual stats | Public | READY |
| Wikidata Cinema Entities | Venue metadata | Thousands | SPARQL | READY |
| OpenStreetMap Cinemas | Venue geodata | Thousands | Overpass API | READY |
| TMDb API | Film metadata | 1M+ films | Free API | READY |
| UK Census | Demographics | Postcode-level | Open Gov | READY |
| Taking Part Survey | Cultural participation | Annual survey | Open Gov | READY |

### Tier 2: Scrape-Acquirable
| Dataset | Type | Scale | Access | Status |
|---------|------|-------|--------|--------|
| UK Independent Cinema Programmes | Programme data | 50,000+ screenings target | Web scraping | TO BUILD |
| Datathistle UK Cinemas | Venue data | 800+ venues | Web scraping | TO BUILD |
| Art-house Cinema Schedules | Programme data | Varies | Web scraping | TO BUILD |

### Tier 3: Partnership Required
| Dataset | Type | Scale | Access | Status |
|---------|------|-------|--------|--------|
| Kinomatics Global Showtimes | Programme data | 330M records | Research partnership | TO NEGOTIATE |
| Audience Finder | Audience segments | 16M transactions | Sector partnership | TO EVALUATE |
| Cinema Context (NL) | Historical programme | 100K+ screenings | Open Data + SPARQL | READY |

### Tier 4: Commercial
| Dataset | Type | Scale | Access | Status |
|---------|------|-------|--------|--------|
| International Showtimes API | Current programme | 120+ countries | Commercial API | NOT PURSUING |
| Movio Data | Audience behaviour | 100M moviegoers | Proprietary | NOT ACCESSIBLE |
| Comscore Box Office | Market data | Global | Commercial | NOT PURSUING |

## 2. Datasets Selected

### For Model Training:
1. **Kaggle Cinema Tickets** (142,524 rows) — Demand forecasting benchmark
2. **Scraped UK Cinema Programmes** (to build) — Programme-level prediction
3. **TMDb + Wikidata** — Film metadata enrichment
4. **UK Census + OSM** — Geographic/catchment features

### For Qloo Feature Engineering:
5. **Qloo Insights API** — Cultural affinity, taste profiles, geographic heatmaps
6. **Scraped programme data** — Venue cultural profiles

### For Validation:
7. **BFI Statistical Yearbook** — Market-level benchmarks
8. **Kinomatics** (if accessible) — Global programme patterns

## 3. Datasets Rejected

| Dataset | Reason |
|---------|--------|
| ScrapeHero Cinema Locations | Paid; limited to single chain; we can get better data from Wikidata/OSM |
| Movio Data | Proprietary; requires Vista integration; not accessible |
| Commercial POS Data | Proprietary; GDPR issues; not accessible |
| Movie Rating Prediction datasets | Wrong problem (predicting ratings, not attendance/programming) |
| Box Office Revenue datasets | Wrong granularity (film-level, not venue-level) |

## 4. Collection Methods

### Web Scraping Pipeline:
1. **Source identification**: UK independent cinemas with public programme pages
2. **robots.txt check**: Verify scraping permitted
3. **Rate limiting**: 1-2 second delays between requests
4. **Raw HTML/JSON storage**: Cache in data/raw/
5. **Parser extraction**: Extract film, date, time, venue
6. **Deduplication**: Match films across venues using TMDb/IMDb IDs
7. **Provenance tracking**: Source URL, retrieval timestamp, parser version

### API-Based Collection:
1. **TMDb API**: Film metadata enrichment (rate-limited)
2. **Wikidata SPARQL**: Venue and film entity extraction
3. **OSM Overpass**: Venue geocoding

## 5. Source/Licensing Status

| Source | License | Commercial Use | Attribution |
|--------|---------|----------------|-------------|
| Kaggle Cinema Tickets | CC0 | Yes | No |
| BFI Statistics | Open | Yes | Citation required |
| Wikidata | CC0 | Yes | No |
| OpenStreetMap | ODbL | Yes | Attribution required |
| TMDb | Non-commercial | No | Attribution required |
| UK Census | Open Gov | Yes | Attribution required |
| Cinema Context | Open Data | Yes | Citation required |
| Kinomatics | Research | Negotiate | Citation required |

**Note**: TMDb's non-commercial license limits its use in a commercial product. For the hackathon, this is acceptable. For production, we would need to use Wikidata + IMDb datasets (non-commercial) or negotiate a commercial license.

## 6. Scale Targets

| Data Type | Target | Realistic | Source |
|-----------|--------|-----------|--------|
| Venues | 100+ | 50-100 | Scraping + Wikidata + OSM |
| Programme events | 50,000+ | 20,000-50,000 | Scraping UK cinemas |
| Historical time | 6-24 months | 3-12 months | Scraping (limited by website history) |
| Unique films | 1,000+ | 500-2,000 | Scraping + TMDb |
| Geographic entities | 10,000+ | 5,000-20,000 | Census + OSM |

## 7. Schema Design

### Venue
```
venue_id: str (stable internal ID)
name: str
address: str
city: str
country: str
latitude: float
longitude: float
screens: int | None
capacity: int | None
venue_type: str (independent/chain/arthouse/multiplex)
website: str | None
source_url: str
retrieved_at: datetime
```

### Film
```
film_id: str (stable internal ID)
title: str
year: int | None
director: str | None
country: str | None
language: str | None
genres: list[str]
runtime_minutes: int | None
tmdb_id: str | None
imdb_id: str | None
source_url: str | None
```

### Screening
```
screening_id: str (stable internal ID)
venue_id: str (FK → Venue)
film_id: str (FK → Film)
screening_date: date
screening_time: time | None
screen_name: str | None
programme_name: str | None
is_special_event: bool
is_festival: bool
source_url: str
retrieved_at: datetime
```

### Programme
```
programme_id: str (stable internal ID)
venue_id: str (FK → Venue)
programme_name: str
start_date: date
end_date: date
description: str | None
```

### Geography
```
geography_id: str (stable internal ID)
postcode: str
lsoa: str | None
msoa: str | None
latitude: float
longitude: float
population: int | None
age_distribution: dict | None
income_bands: dict | None
```

### Source
```
source_id: str (stable internal ID)
domain: str
venue: str
city: str
source_url: str
retrieved_at: datetime
robots_status: str
licensing_notes: str
parser_version: str
record_count: int
```

## 8. Labels

### Primary Label: Programme Performance
- **Unit**: venue-film-week
- **Target**: occupancy_rate (tickets_sold / capacity)
- **Construction**: From scraped programme data + Kaggle benchmark
- **Prediction horizon**: 1 week ahead
- **Leakage risks**: Future attendance data; cross-venue information
- **Cold-start**: New films, new venues

### Secondary Label: Audience Expansion
- **Unit**: venue-programme-period
- **Target**: binary (did attendance exceed venue baseline by >20%?)
- **Construction**: From historical programme data
- **Prediction horizon**: Programme period
- **Leakage risks**: Post-hoc programme classification
- **Cold-start**: New programming directions

## 9. Provenance

Every data row must carry:
- `source_url`: Where the data came from
- `retrieved_at`: When it was collected
- `parser_version`: Which parser extracted it
- `data_status`: "measured" | "estimated" | "synthetic"

## 10. Expected Limitations

1. **Historical depth**: Most cinema websites only show current/near-future programmes
2. **Attendance data**: Not publicly available at screening level (only Kaggle benchmark)
3. **Venue coverage**: UK-focused initially; independent cinemas may not have public programmes
4. **Film matching**: Need robust entity resolution across venues
5. **Seasonal bias**: Scraping now captures current season, not full year
6. **Selection bias**: Only cinemas with public websites; may skew towards larger/better-funded venues

## 11. Model-Training Role

| Dataset | Role |
|---------|------|
| Kaggle Cinema Tickets | Demand forecasting benchmark; feature engineering patterns |
| Scraped UK Programmes | Primary training data for programme-level prediction |
| TMDb/Wikidata | Film metadata features |
| Census/OSM | Geographic/catchment features |
| Qloo API | Cultural affinity features (our differentiator) |
| BFI Statistics | Market-level validation benchmarks |

---

## 12. M9 Update: Verified Historical Programme Corpus

### Datasets Acquired (M9)

| Dataset | Status | Records | Notes |
|---------|--------|---------|-------|
| Wikidata Venues | ✅ ACQUIRED | 485 | UK cinemas with coordinates |
| Picturehouses Programme | ⚠️ CHAIN-LEVEL | 94,507 | Not venue-specific |
| Cinema Context (NL) | ✅ ACQUIRED | 20,628 | Venue-specific, historical |

### M9 Deliverables

- `data/processed/independent_cinema_programmes.parquet` — Canonical dataset
- `data/venue_source_validation.csv` — Venue source validation
- `data/manifests/independent_cinema_programmes_2026-10-06_manifest.json` — Data manifest
- `docs/M9_PROGRAMME_CORPUS_REPORT.md` — Programme corpus report
- `docs/M9_OUTCOME_SIGNAL_REPORT.md` — Outcome signal investigation
- `docs/M9_ML_READINESS.md` — ML readiness assessment

### Key Findings (M9)

1. **Cinema Context is the best verified historical dataset** — venue-specific, 48 years, CC-BY 4.0
2. **Picturehouses data is chain-level only** — not valid for venue-level modelling
3. **No attendance data available** — cannot build audience-expansion model
4. **Qloo validation is viable** — can test information gain on historical programming

### Next Steps (M10)

1. Validate Qloo information gain on Cinema Context corpus
2. Seek UK historical data (BFI, Glasgow Film Theatre)
3. Enrich films with IMDb metadata
4. Build programme pattern model (clustering, network analysis)