# MODEL RESEARCH — Adjacent

**Last Updated:** 2026-10-06 (M9 completion)

## 1. Candidate ML Problem Formulations

### Problem A: Venue Demand Forecasting
**Given**: venue + film/programme + temporal + geographic context
**Predict**: expected audience/occupancy

- **Measurable**: Yes (tickets sold / capacity)
- **Labelable**: Yes (from historical data)
- **Data-supported**: Partially (Kaggle benchmark has 142K rows; need venue-specific data)
- **Relevant**: Yes (every cinema needs demand forecasting)
- **Defensible**: Moderate (many existing solutions; Cinema Intelligence does this)
- **Useful**: Yes (staffing, scheduling, pricing)
- **Compatible with Qloo**: Weakly (Qloo provides cultural features, but demand forecasting doesn't need them)
- **Verdict**: Viable but NOT differentiated

### Problem B: Programme Performance Prediction
**Given**: film/programme and venue context
**Predict**: whether it will overperform the venue's normal baseline

- **Measurable**: Yes (attendance vs. venue average)
- **Labelable**: Yes (binary: overperformed or not)
- **Data-supported**: Partially (need historical programme data per venue)
- **Relevant**: Yes (helps programmers choose films)
- **Defensible**: Moderate (similar to demand forecasting)
- **Useful**: Yes (film selection)
- **Compatible with Qloo**: Moderate (cultural affinity could predict overperformance)
- **Verdict**: Viable, better Qloo fit than A

### Problem C: Audience Expansion Prediction
**Given**: existing programme + venue history + cultural profile + geographic context
**Predict**: which culturally adjacent audience/programming direction is most promising for TESTING

- **Measurable**: Yes (did attendance exceed baseline by >20%?)
- **Labelable**: Weakly (requires historical experimentation data)
- **Data-supported**: Weakly (no existing dataset has this)
- **Relevant**: HIGH (this is the core problem independent cinemas face)
- **Defensible**: HIGH (no existing tool does this)
- **Useful**: HIGH (directly addresses the "what should I try?" question)
- **Compatible with Qloo**: STRONG (Qloo provides the cultural adjacency data)
- **Verdict**: BEST FIT for Adjacent, but hardest data problem

### Problem D: Programme Adjacency Discovery
**Given**: cultural signals from programme history
**Predict**: which combinations of cultural signals repeatedly produce successful audience expansion

- **Measurable**: Yes (co-occurrence of successful programming directions)
- **Labelable**: Requires large-scale programme history
- **Data-supported**: Weakly (need Kinomatics-scale data)
- **Relevant**: High (systematic learning across venues)
- **Defensible**: High (novel approach)
- **Useful**: High (generalizable insights)
- **Compatible with Qloo**: Strong
- **Verdict**: Ambitious; requires more data than we have

### Problem E: Counterfactual/Experimental Question
**Given**: venue's historical programme
**Predict**: what type of new programming intervention appears promising relative to baseline

- **Measurable**: Yes (comparative to venue's own baseline)
- **Labelable**: Requires experimental data
- **Data-supported**: Weakly
- **Relevant**: HIGH (the actual decision problem)
- **Defensible**: HIGH (causal reasoning)
- **Useful**: HIGH (directly actionable)
- **Compatible with Qloo**: Strong
- **Verdict**: Most aligned with Adjacent's mission, but requires careful causal framing

## 2. Recommended Problem: Programme-Contextualised Audience Expansion

### Definition
Given a venue's programme history and cultural profile (from Qloo), predict which culturally adjacent programming directions would expand the audience beyond the venue's current baseline.

### Why This Problem?
1. **No existing tool solves it** — Movio/Cinema Intelligence focus on existing audiences
2. **Qloo is essential** — cross-domain cultural affinity is the key differentiator
3. **Independent cinemas need it** — they're losing audiences and don't know what to try
4. **Testable** — each prediction is a falsifiable hypothesis

### Target Label Construction

**Unit of prediction**: venue-programme_period-week

**Primary label**: `audience_expansion`
- Binary: Did attendance in this programme period exceed the venue's 12-week rolling average by >20%?
- Construction: `current_week_attendance / rolling_12w_average > 1.2`

**Secondary label**: `expansion_magnitude`
- Continuous: `current_week_attendance / rolling_12w_average`
- Capped at 3.0 to avoid outlier dominance

**Tertiary label**: `new_audience_ratio`
- Proportion of attendees who hadn't attended in the previous 8 weeks
- Requires individual ticket data (only available from POS integration)

### Feature Engineering

#### Venue Features (from programme history)
- `venue_cultural_profile`: Qloo taste tags from last 6 months of programming
- `venue_domain_distribution`: Proportion of programming in each cultural domain
- `venue_novelty_score`: How different is current programming from venue's history
- `venue_geographic_catchment`: Qloo heatmap of cultural affinity around venue

#### Film/Programme Features (from TMDb + Wikidata)
- `film_cultural_tags`: Qloo taste tags for the film
- `film_cultural_distance`: Distance from venue's cultural profile
- `film_cross_domain_affinity`: Qloo affinity scores across domains
- `film_geographic_affinity`: Qloo geographic affinity heatmap

#### Context Features
- `day_of_week`: Calendar features
- `season`: Quarter/month
- `local_events`: Nearby cultural events (if available)
- `weather`: Historical weather (if available)

#### Qloo Features (THE DIFFERENTIATOR)
- `qloo_taste_tags`: Cultural tags from programme history
- `qloo_adjacent_entities`: Entities in adjacent cultural domains
- `qloo_geographic_concentration`: Where culturally aligned audiences live
- `qloo_cross_domain_affinity`: Affinity across film, music, books, art, dining
- `qloo_cultural_bridge`: Connecting tags between venue profile and potential new audiences

### Prediction Horizon
- **Short-term**: 1 week ahead (which films to book next week)
- **Medium-term**: 1 month ahead (what programming direction to explore)
- **Long-term**: 3 months ahead (what season themes to develop)

### Training Data

**Primary source**: Scraped UK cinema programmes + Qloo enrichment
- Target: 50,000+ screening records from 50+ venues
- Time: 6-12 months of history
- Labels: Constructed from attendance patterns

**Secondary source**: Kaggle Cinema Tickets (benchmark)
- 142,524 rows of film-cinema-date sales
- Labels: tickets_sold, occupancy_rate
- Use: Feature engineering patterns, baseline models

**Tertiary source**: Kinomatics (if accessible)
- 330M global screening records
- Use: Programme diversity analysis, cross-cultural patterns

### Validation Strategy

**DO NOT use random train/test splits** — temporal leakage risk.

**Preferred approach**:
1. **Time-based split**: Train on months 1-9, validate on month 10-11, test on month 12
2. **Venue-holdout**: Train on 80% of venues, test on 20%
3. **Film-holdout**: Train on known films, test on new releases
4. **Cold-start test**: How well does the model work for venues with <3 months of data?

### Evaluation Metrics

**Primary**: 
- **Precision@k**: Of the top-k recommended programming directions, how many actually expanded the audience?
- **Recall@k**: Of all successful expansions, how many did we recommend?

**Secondary**:
- **Calibration**: Are predicted probabilities accurate?
- **Coverage**: What proportion of venues receive useful recommendations?
- **Novelty**: Are recommendations non-obvious (not just "show popular films")?

**Baselines**:
1. **Popularity baseline**: Recommend the most popular films globally
2. **Venue-history baseline**: Recommend films similar to what the venue has shown
3. **Content-only model**: Use only film metadata (no Qloo)
4. **Qloo-only model**: Use only Qloo cultural features
5. **Combined model**: Film metadata + Qloo

### Ablation Study Design

**MODEL A**: Real-world data only (programme history + film metadata + calendar)
**MODEL B**: Qloo cultural features only (taste tags, adjacent entities, geographic heatmaps)
**MODEL C**: Real-world + Qloo (full Adjacent model)
**MODEL D**: Generic movie/content model baseline (TMDb genres + ratings)

**Goal**: Prove that Qloo contributes actual predictive value beyond what's available from public data alone.

**Success criterion**: MODEL C significantly outperforms MODEL A on precision@k.

## 3. Model Families

### Strong Baselines (Start Here)

#### LightGBM / XGBoost
- **Why**: Handles mixed feature types; fast training; interpretable; works well with tabular data
- **When**: With 50,000+ rows; good for initial benchmarking
- **Risk**: May overfit with small venue-specific datasets

#### Logistic Regression (Regularised)
- **Why**: Interpretable; good baseline; fast
- **When**: For binary classification (audience expansion yes/no)
- **Risk**: May miss non-linear relationships

### Advanced Models (If Data Supports)

#### Learning-to-Rank (LambdaMART, XGBoost Ranker)
- **Why**: We want to RANK programming directions, not just predict binary outcomes
- **When**: When we have enough venue-programme pairs
- **Risk**: Needs more data than classification

#### Causal Uplift Models (S-learner, T-learner, X-learner)
- **Why**: We want to know the CAUSAL effect of programming changes, not just correlation
- **When**: When we have enough experimental data (programming changes + outcomes)
- **Risk**: Requires careful causal framing; hard to validate

#### Two-Tower / Retrieval Systems
- **Why**: Retrieve relevant programming directions from a large candidate set
- **When**: When we have thousands of potential programming directions
- **Risk**: Complex; needs lots of data

### Models to AVOID

#### Deep Neural Networks
- **Why avoid**: Dataset too small (50K rows); interpretability critical; overkill
- **Exception**: Only if we get Kinomatics-scale data (330M rows)

#### Collaborative Filtering (Pure)
- **Why avoid**: Cold-start problem (new venues, new films); doesn't use cultural features
- **Exception**: Could complement content-based approach

## 4. Offline Evaluation Strategy

### Time-Based Splits
```
Train:  Jan-Sep 2024
Valid:  Oct-Nov 2024  
Test:   Dec 2024
```

### Venue-Holdout
```
Train:  80% of venues (randomly selected)
Test:   20% of venues
```

### Film-Holdout
```
Train:  All films released before Oct 2024
Test:   Films released Oct-Dec 2024
```

### Cold-Start Test
```
Train:  Venues with >6 months of data
Test:   Venues with <3 months of data
```

### Evaluation Protocol
1. For each test venue-week, generate ranked list of programming directions
2. Evaluate precision@1, @3, @5, @10
3. Compare against baselines
4. Statistical significance testing (paired t-test or Wilcoxon)

## 5. Qloo Feature Strategy

### Qloo-Derived Features

From programme history:
- `qloo_taste_profile`: Top-20 taste tags with affinities
- `qloo_domain_distribution`: Affinity across film, music, books, art, dining
- `qloo_geographic_heatmap`: Affinity concentration around venue

For candidate films:
- `qloo_film_tags`: Taste tags for the candidate film
- `qloo_film_affinity`: Affinity score relative to venue profile
- `qloo_cross_domain_bridges`: Connecting tags between venue and film audiences

For geographic analysis:
- `qloo_catchment_affinity`: Cultural affinity in venue's catchment area
- `qloo_underserved_areas`: Geographic areas with high cultural affinity but low current attendance

### Ablation Features

**Without Qloo** (Model A):
- Film genre, runtime, year, country (from TMDb)
- Venue type, city, screens (from scraping)
- Calendar features (day, month, season)
- Historical attendance patterns (from scraping)

**With Qloo** (Model C):
- All of Model A features PLUS
- Qloo taste tags, cultural affinity, geographic heatmaps
- Cross-domain affinity scores
- Cultural bridge indicators

**Qloo-only** (Model B):
- Only Qloo-derived features
- No historical attendance data
- No film metadata beyond what Qloo provides

## 6. Benchmark Strategy

### Internal Benchmarks
1. **Popularity baseline**: Always recommend the most popular films
2. **Venue-history baseline**: Recommend films similar to venue's recent programming
3. **Random baseline**: Random programming recommendations

### External Benchmarks
4. **Kaggle cinema forecasting**: Compare our demand forecasting component against published results
5. **Eliashberg scheduling**: Compare our schedule optimization against their published results

### Domain Benchmarks
6. **Content-only model**: Film metadata without Qloo
7. **Qloo-only model**: Qloo features without historical data

## 7. Architecture Research Draft

### Data Ingestion
- Web scraping pipeline (cinema programmes)
- API clients (TMDb, Wikidata, OSM, Qloo)
- Data validation and deduplication

### Data Lake
- Raw scraped HTML/JSON (data/raw/)
- Processed structured data (data/processed/)
- Source manifests (data/manifests/)

### Canonical Schema
- Venue, Film, Screening, Programme, Geography, Source
- Stable internal IDs; provenance at row level

### Feature Layer
- Venue cultural profile (from programme history)
- Film metadata features (from TMDb/Wikidata)
- Geographic features (from Census/OSM)
- Calendar/temporal features

### Qloo Feature Layer
- Taste tag extraction
- Cultural affinity scoring
- Geographic heatmap generation
- Cross-domain adjacency discovery

### Training Pipeline
- Data loading and feature engineering
- Model training (LightGBM baseline)
- Hyperparameter tuning (time-based CV)
- Model evaluation (precision@k, calibration)

### Model Registry
- Versioned models per venue-type
- A/B testing framework
- Performance monitoring

### Inference Service
- Input: venue programme history + candidate films
- Output: ranked programming directions with evidence
- Explanation: which Qloo features drove the ranking

### Agent/Orchestrator
- Current M7 pipeline (RESOLVE → ANALYSE → EXPAND → RANK → LOCATE → DECIDE)
- Enhanced with ML model predictions
- Falsification conditions from model uncertainty

### Decision Engine
- Combine Qloo cultural intelligence with ML predictions
- Generate testable hypotheses
- Provide evidence and provenance

### Frontend
- Current M7 interface (Programme → Taste DNA → Audience → Geography → Bet → Test Card)
- Enhanced with ML confidence scores
- Historical prediction accuracy tracking

---

## 7. M10 Update: ML Readiness Assessment (Corrected)

### ⚠️ M10 CORRECTIONS

**M9 Claim:** Qloo validation successful (100% hit rate on historical films)

**M10 Finding:** This claim is INVALID. The validation only checked if Qloo returned a result, NOT whether the result was the correct historical film.

**Actual Qloo Coverage (M10):**
- VERIFIED: 2% (2/100 films)
- AMBIGUOUS: 34% (34/100 films)
- MISMATCH: 64% (64/100 films)

**Conclusion:** Qloo has very limited coverage of historical films (1907-1955). Do NOT use M9 Qloo validation as evidence.

### Dataset Status

| Dataset | Status | Records | Venue-Specific | Historical |
|---------|--------|---------|----------------|------------|
| Cinema Context (NL) | ✅ ACQUIRED | 20,628 | ✅ Yes | ✅ 1907-1955 |
| Picturehouses (UK) | ⚠️ CHAIN-LEVEL | 94,507 | ❌ No | ❌ Forward-looking |
| Film Qloo Resolution | ✅ CREATED | 100 | N/A | N/A |

### ML Viability

| Problem Formulation | Status | Notes |
|---------------------|--------|-------|
| Venue Demand Forecasting | ❌ NOT VIABLE | No attendance data |
| Programme Performance Prediction | ❌ NOT VIABLE | No attendance data |
| Audience Expansion Prediction | ❌ NOT VIABLE | No attendance labels |
| Programme Adjacency Discovery | ✅ VIABLE | Unsupervised on historical data |
| Qloo Information-Gain Validation | ⚠️ LIMITED | Qloo has 2% coverage of historical films |

### Recommendation

**Verdict: PARTIALLY VIABLE**

1. **Qloo Validation:** Limited — Qloo has very low coverage of historical films
2. **Programme Pattern Analysis:** Fully viable — clustering, network analysis (no Qloo needed)
3. **Audience Expansion Model:** Not viable — no attendance data
4. **Next Steps:** Test Qloo on modern films, consider alternative approaches for historical data