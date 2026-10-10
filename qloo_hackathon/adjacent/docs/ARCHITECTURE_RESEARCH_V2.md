# ARCHITECTURE RESEARCH V2 — Adjacent

## Derived From Real Research

This architecture is derived from:
- 8 commercial product analyses
- 5 open-source repository analyses
- 6 academic papers
- 10+ dataset discoveries
- Competitive gap analysis
- Model research

## Core Insight

**Adjacent's unique value is cross-domain cultural intelligence for independent cinema audience development.**

No existing product combines:
1. Venue programme history (what they've shown)
2. Qloo cultural affinity (who would be interested)
3. Geographic cultural concentration (where they live)
4. Testable hypothesis generation (what to try)

## Architecture Components

### 1. Data Ingestion Layer

#### 1.1 Programme Scraper
- **Purpose**: Collect public programme data from independent cinemas
- **Sources**: Cinema websites (datathistle.com, individual venue sites)
- **Method**: Respectful scraping (robots.txt, rate limiting, caching)
- **Output**: Raw HTML/JSON → parsed programme records
- **Scale target**: 50+ venues, 20,000+ screenings

#### 1.2 Film Metadata Enricher
- **Purpose**: Enrich scraped films with metadata
- **Sources**: TMDb API, Wikidata SPARQL
- **Method**: Entity resolution (title + year + director matching)
- **Output**: Enriched film records with genres, country, language, keywords
- **Scale**: Thousands of unique films

#### 1.3 Venue Geocoder
- **Purpose**: Geocode venue addresses
- **Sources**: OpenStreetMap Nominatim, Wikidata
- **Method**: Address → lat/lng geocoding
- **Output**: Venue records with coordinates
- **Scale**: 100+ venues

#### 1.4 Qloo Feature Extractor
- **Purpose**: Extract cultural features from programme history
- **Source**: Qloo Insights API
- **Method**: 
  - Submit programme films as signal entities
  - Extract taste tags, cultural affinity scores
  - Generate geographic heatmaps
  - Discover cross-domain adjacent entities
- **Output**: Venue cultural profile, geographic affinity data

### 2. Data Lake

#### 2.1 Raw Storage
```
data/raw/
├── scrapes/
│   ├── {venue_id}/{date}/raw.html
│   └── {venue_id}/{date}/parsed.json
├── api_responses/
│   ├── tmdb/{film_id}.json
│   ├── wikidata/{entity_id}.json
│   └── qloo/{call_id}.json
└── manifests/
    └── {date}_manifest.json
```

#### 2.2 Processed Storage
```
data/processed/
├── venues.parquet
├── films.parquet
├── screenings.parquet
├── programmes.parquet
├── geography.parquet
└── qloo_features.parquet
```

#### 2.3 Source Manifests
Every data collection run produces a manifest:
```json
{
  "source_id": "datathistle_20261006",
  "domain": "datathistle.com",
  "venue": "Ritzy Picturehouse",
  "city": "London",
  "source_url": "https://film.datathistle.com/cinemas/...",
  "retrieved_at": "2026-10-06T14:30:00Z",
  "robots_status": "allowed",
  "licensing_notes": "Public website, fair use for research",
  "parser_version": "1.0.0",
  "record_count": 247
}
```

### 3. Canonical Schema

#### Venue
```sql
venue_id        VARCHAR PRIMARY KEY  -- stable internal ID
name            VARCHAR NOT NULL
address         VARCHAR
city            VARCHAR NOT NULL
country         VARCHAR NOT NULL DEFAULT 'GB'
latitude        FLOAT
longitude       FLOAT
screens         INT
capacity        INT
venue_type      VARCHAR  -- independent, chain, arthouse, multiplex
website         VARCHAR
source_url      VARCHAR
retrieved_at    TIMESTAMP
```

#### Film
```sql
film_id         VARCHAR PRIMARY KEY  -- stable internal ID
title           VARCHAR NOT NULL
year            INT
director        VARCHAR
country         VARCHAR
language        VARCHAR
genres          VARCHAR[]  -- array of genre strings
runtime_minutes INT
tmdb_id         VARCHAR
imdb_id         VARCHAR
keywords        VARCHAR[]
```

#### Screening
```sql
screening_id    VARCHAR PRIMARY KEY
venue_id        VARCHAR REFERENCES Venue(film_id)
film_id         VARCHAR REFERENCES Film(film_id)
screening_date  DATE NOT NULL
screening_time  TIME
screen_name     VARCHAR
programme_name  VARCHAR
is_special_event BOOLEAN DEFAULT FALSE
is_festival     BOOLEAN DEFAULT FALSE
source_url      VARCHAR
retrieved_at    TIMESTAMP
```

#### QlooFeature
```sql
feature_id      VARCHAR PRIMARY KEY
venue_id        VARCHAR REFERENCES Venue(venue_id)
feature_type    VARCHAR  -- taste_tag, adjacent_entity, heatmap_cell
feature_key     VARCHAR  -- tag_id, entity_id, geohash
feature_value   FLOAT
affinity        FLOAT
call_id         VARCHAR  -- Qloo API call ID for provenance
created_at      TIMESTAMP
```

### 4. Feature Layer

#### 4.1 Venue Cultural Profile
Computed from programme history + Qloo:
```python
venue_profile = {
    "taste_tags": [(tag_id, name, affinity, popularity), ...],
    "domain_distribution": {"film": 0.85, "music": 0.05, ...},
    "geographic_heatmap": [(lat, lng, affinity), ...],
    "cultural_novelty": float,  # how different from venue's history
}
```

#### 4.2 Film Features
From TMDb/Wikidata + Qloo:
```python
film_features = {
    "genre_vector": [0.3, 0.1, 0.0, ...],
    "country": "JP",
    "runtime": 120,
    "qloo_tags": [(tag_id, name, affinity), ...],
    "qloo_cultural_distance": float,  # distance from venue profile
    "qloo_cross_domain_affinity": {"music": 0.4, "books": 0.6, ...},
}
```

#### 4.3 Geographic Features
From Census/OSM + Qloo:
```python
geo_features = {
    "catchment_population": int,
    "age_distribution": {"18-24": 0.15, "25-34": 0.25, ...},
    "income_bands": {"low": 0.2, "medium": 0.5, "high": 0.3},
    "qloo_cultural_affinity": float,  # Qloo affinity in catchment
    "nearby_cultural_venues": int,  # galleries, bookshops, music venues
}
```

### 5. Qloo Feature Layer

#### 5.1 Programme → Qloo
```
Programme History → Qloo /v2/insights (signal.interests.entities)
  → Taste Tags (top 50 with affinities)
  → Cultural Domain Distribution
  → Geographic Heatmap (affinity cells around venue)
```

#### 5.2 Venue → Qloo
```
Venue Location → Qloo /v2/insights (signal.location)
  → Geographic Cultural Affinity
  → Nearby Cultural Entities
  → Catchment Cultural Profile
```

#### 5.3 Cross-Domain Discovery
```
Venue Profile → Qloo /v2/insights (filter.type=urn:entity:music, urn:entity:book, ...)
  → Adjacent Entities in Other Domains
  → Cross-Domain Affinity Scores
  → Cultural Bridge Tags
```

### 6. Training Pipeline

#### 6.1 Label Construction
```python
def construct_label(venue_id, week_start):
    """Binary: did attendance exceed venue's 12-week average by >20%?"""
    current = get_attendance(venue_id, week_start)
    baseline = get_rolling_average(venue_id, week_start, window=12)
    return 1 if current / baseline > 1.2 else 0
```

#### 6.2 Feature Matrix
```
X = [venue_cultural_profile, film_features, geo_features, calendar_features, qloo_features]
y = audience_expansion (binary)
```

#### 6.3 Model Training
```python
# Baseline: LightGBM
model = lgb.LGBMClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
)

# Time-based CV
tscv = TimeSeriesSplit(n_splits=5)
for train_idx, val_idx in tscv.split(X):
    model.fit(X[train_idx], y[train_idx])
    predictions = model.predict_proba(X[val_idx])
```

#### 6.4 Hyperparameter Tuning
```python
# Optuna-based tuning with time-series CV
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=100)
```

### 7. Offline Evaluation

#### 7.1 Metrics
```python
# Primary: Precision@k
def precision_at_k(y_true, y_scores, k=5):
    top_k = np.argsort(y_scores)[-k:]
    return np.mean(y_true[top_k])

# Secondary: Calibration
def calibration_error(y_true, y_probs, n_bins=10):
    # Expected calibration error
    ...

# Coverage
def coverage(y_venues, y_recs):
    # Proportion of venues receiving useful recommendations
    ...
```

#### 7.2 Baselines
1. Popularity baseline (most popular films globally)
2. Venue-history baseline (similar to recent programming)
3. Content-only model (film metadata, no Qloo)
4. Qloo-only model (Qloo features, no historical data)
5. Combined model (full Adjacent)

#### 7.3 Ablation Study
```python
# Model A: Real-world data only
features_A = [venue_history, film_metadata, calendar]

# Model B: Qloo only
features_B = [qloo_taste_tags, qloo_affinity, qloo_geographic]

# Model C: Combined
features_C = features_A + features_B

# Model D: Content baseline
features_D = [film_genre, film_country, film_runtime]
```

### 8. Model Registry

#### 8.1 Versioning
```
models/
├── v1.0.0/
│   ├── lightgbm_baseline.pkl
│   ├── feature_config.json
│   ├── evaluation_metrics.json
│   └── training_data_hash.txt
└── latest -> v1.0.0/
```

#### 8.2 A/B Testing Framework
- Deploy model versions side-by-side
- Track prediction accuracy over time
- Automated rollback on performance degradation

### 9. Inference Service

#### 9.1 Input
```python
{
    "venue_id": "ritzy_london",
    "programme_history": [...],  # last 6 months
    "candidate_films": [...],  # films available for booking
    "city": "London",
    "prediction_horizon": "1_week"
}
```

#### 9.2 Output
```python
{
    "ranked_directions": [
        {
            "direction": "Documentary programming with Q&A events",
            "confidence": 0.72,
            "evidence": {
                "qloo_cultural_bridge": ["contemplative cinema", "social documentary"],
                "geographic_concentration": "Brixton, Camberwell",
                "adjacent_audiences": ["documentary film festival attendees", "independent bookshop visitors"],
            },
            "falsification": "If a documentary season does not exceed baseline by >15% in 4 weeks, hypothesis is rejected.",
        },
        ...
    ],
    "venue_cultural_profile": {...},
    "geographic_heatmap": {...},
}
```

### 10. Agent/Orchestrator

#### 10.1 Current Pipeline (M7)
```
INIT → PLAN → RESOLVE → EVALUATE
              ↓ ANALYSE → EVALUATE
              ↓ EXPAND → EVALUATE ↓
          RANK → EVALUATE
              ↓ LOCATE → EVALUATE
              ↓ DECIDE → EVALUATE
              ↓ STOP
```

#### 10.2 Enhanced Pipeline (ML Integration)
```
INIT → PLAN → RESOLVE → EVALUATE
              ↓ ANALYSE → EVALUATE
              ↓ EXPAND → EVALUATE ↓
          RANK → EVALUATE
              ↓ ML_PREDICT → EVALUATE  ← NEW: ML model prediction
              ↓ LOCATE → EVALUATE
              ↓ DECIDE → EVALUATE
              ↓ STOP
```

### 11. Decision Engine

#### 11.1 Hypothesis Generation
```python
def generate_hypothesis(venue_profile, ml_prediction, qloo_evidence):
    """Combine ML prediction with Qloo evidence to generate testable hypothesis."""
    direction = ml_prediction.top_direction
    confidence = ml_prediction.confidence
    cultural_bridge = qloo_evidence.bridge_tags
    geographic = qloo_evidence.geographic_concentration
    
    hypothesis = {
        "direction": direction,
        "confidence": confidence,
        "cultural_bridge": cultural_bridge,
        "geographic_signal": geographic,
        "falsification": f"If {direction} does not exceed baseline by >15% in 4 weeks, hypothesis is rejected.",
    }
    return hypothesis
```

### 12. Evidence/Provenance

Every prediction carries:
- Qloo call IDs (which API calls produced the cultural features)
- Training data hash (which data trained the model)
- Model version (which model made the prediction)
- Feature values (what inputs drove the prediction)
- Confidence intervals (how certain is the prediction)

### 13. Frontend

#### Current (M7):
```
Programme Profile → Taste DNA → Audience Opportunities → Geography → Programme Bet → Test Card
```

#### Enhanced (ML):
```
Programme Profile → Taste DNA → Audience Opportunities → Geography → 
ML Predictions → Programme Bet → Test Card → Historical Accuracy
```

New components:
- **ML Confidence**: Visual confidence indicator for predictions
- **Historical Accuracy**: Track how past predictions performed
- **A/B Comparison**: Compare ML vs. deterministic predictions
- **Feature Importance**: Which Qloo features drove the prediction

## Architecture Decisions

### Frozen from M5:
1. Cinema beachhead
2. Adjacent-entity cohorts
3. External-ID ingestion
4. Affinity normalised per query
5. Deterministic Programme Bet (current)
6. SSE streaming pipeline
7. In-memory run store
8. No PostgreSQL (yet)
9. No Redis (yet)
10. No LLM (yet)

### New for M8+:
11. **ML model integration** — LightGBM baseline for audience expansion prediction
12. **Feature store** — Qloo-derived features cached and versioned
13. **Training pipeline** — Time-series CV, hyperparameter tuning
14. **Model registry** — Versioned models with evaluation metrics
15. **Ablation framework** — Compare Qloo vs. non-Qloo models
16. **Data acquisition pipeline** — Scraping + API enrichment
17. **Canonical schema** — Venue, Film, Screening, QlooFeature

### NOT Adding Yet:
- PostgreSQL (evaluate after data scale justifies it)
- Redis (evaluate after inference latency requires it)
- LLM (evaluate after deterministic approach proves insufficient)
- Deep learning (dataset too small)
- Real-time training (batch is sufficient)

## Data Flow

```
[Cinema Websites] → [Scraper] → [Raw HTML/JSON]
                                    ↓
                              [Parser] → [Structured Data]
                                    ↓
[TMDb/Wikidata] → [Enricher] → [Enriched Films]
                                    ↓
[Qloo API] → [Feature Extractor] → [Qloo Features]
                                    ↓
                              [Feature Store]
                                    ↓
                              [Training Pipeline]
                                    ↓
                              [Model Registry]
                                    ↓
[New Programme] → [Inference Service] → [Ranked Directions]
                                    ↓
                              [Decision Engine]
                                    ↓
                              [Test Card / Hypothesis]
```

## Implementation Priority

### Phase 1: Data Foundation (M8 — current)
1. Build scraping pipeline for UK independent cinemas
2. Acquire 20,000+ screening records
3. Enrich with TMDb/Wikidata metadata
4. Extract Qloo features for venue profiles
5. Define canonical schema

### Phase 2: Model Development (M9)
1. Construct labels from attendance patterns
2. Train LightGBM baseline
3. Run ablation study (with/without Qloo)
4. Validate on held-out venues

### Phase 3: Integration (M10)
1. Integrate ML predictions into pipeline
2. Add ML confidence to Test Card
3. Build historical accuracy tracking
4. A/B test deterministic vs. ML predictions

### Phase 4: Production (M11+)
1. Deploy inference service
2. Add PostgreSQL for data persistence
3. Add Redis for feature caching
4. Scale to 100+ venues