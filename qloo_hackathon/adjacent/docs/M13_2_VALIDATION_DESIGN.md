# M13.2: Validation Design

**Date:** 2026-10-07
**Status:** COMPLETE

---

## VALIDATION ARCHITECTURE

### When Data Becomes Available

```
┌─────────────────────────────────────────────────────────┐
│  PROSPECTIVE COLLECTION                                  │
│  Adjacent generates Programme Bet                        │
│  → recommendation_id, venue, candidate, qloo_evidence   │
│  → logged to outcome_ledger                              │
│                                                          │
│  Venue runs the event                                    │
│  → actual_outcome recorded (attendance, sold_out, etc.)  │
│                                                          │
│  After sufficient observations:                          │
│  → evaluate Qloo signal vs outcome                       │
└─────────────────────────────────────────────────────────┘
```

### UK Proxy Collection (Alternative)

```
┌─────────────────────────────────────────────────────────┐
│  WEEKLY SCRAPE                                           │
│  Prince Charles Cinema showtimes                         │
│  → film, showtime, format, sold_out                      │
│                                                          │
│  Resolve film → Qloo entity                              │
│  → affinity, popularity, domain, cohort evidence         │
│                                                          │
│  Store: film + qloo_evidence + sold_out + venue_context  │
│                                                          │
│  After 3-6 months:                                       │
│  → test Qloo affinity vs sold_out rate                   │
└─────────────────────────────────────────────────────────┘
```

---

## EVALUATION METRICS

### For sold_out (binary classification)

| Metric | Why |
|--------|-----|
| PR AUC | Imbalanced classes (most screenings not sold out) |
| ROC AUC | Overall discriminative ability |
| F1 | Balance of precision and recall |
| Precision @ high recall | Business value: identify likely sell-outs |

### For occupancy_rate (regression)

| Metric | Why |
|--------|-----|
| MAE | Interpretable average error |
| RMSE | Penalizes large errors |
| R² | Variance explained |

### For ranking (if comparing candidates)

| Metric | Why |
|--------|-----|
| NDCG@K | Ranking quality at top positions |
| Kendall τ | Rank correlation with outcomes |
| Hit@K | Is the actual winner in top K? |

---

## BASELINE COMPARISONS

| Baseline | Features | Purpose |
|----------|----------|---------|
| B0: Venue history | Historical sold_out rate at venue | Minimum bar |
| B1: Film metadata | Genre, year, rating, director | Non-Qloo baseline |
| B2: Qloo affinity only | affinity | Qloo-only signal |
| B3: Current ranker | affinity + popularity + qr | Current production |
| B4: Qloo + metadata | All Qloo + film features | Best available |

**ML model (if justified) must beat B0 and B2 to be worth keeping.**

---

## TEMPORAL SPLIT DESIGN

```
Training:    weeks 1 to N-8
Validation:  weeks N-7 to N-4
Test:        weeks N-3 to N
```

**No future information leaks.** Each split uses only data available at prediction time.

---

## VENUE-GROUPED EVALUATION

To control for venue-level effects:
1. Train on all venues
2. Evaluate per-venue
3. Report macro-averaged metrics across venues
4. Report per-venue breakdown

---

**Status:** COMPLETE