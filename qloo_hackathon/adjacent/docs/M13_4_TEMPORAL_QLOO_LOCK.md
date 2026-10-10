# M13.4: Temporal Qloo Lock Report

**Date:** 2026-10-07
**Status:** COMPLETE

---

## LABEL SEMANTICS — CORRECTED

| sold_out | Old (M13.3) | New (M13.4) | Correct? |
|----------|-------------|-------------|----------|
| True | STRONG_PROXY | STRONG_PROXY | ✅ |
| False | STRONG_PROXY | **DESCRIPTIVE_ONLY** | ✅ Fixed |
| None | UNAVAILABLE | UNAVAILABLE | ✅ |
| tickets_sold present | DIRECT_OUTCOME | DIRECT_OUTCOME | ✅ |

**M13.3 bug:** `sold_out=False` was classified as `STRONG_PROXY`. This is incorrect — "tickets available at observation time" is not a strong demand signal.

**M13.4 fix:** `sold_out=False` → `DESCRIPTIVE_ONLY`. Only `sold_out=True` → `STRONG_PROXY`.

---

## MODEL TARGET — CORRECTED

| sold_out | model_target |
|----------|-------------|
| True (1) | 1 |
| False (0) | **NULL** (not 0) |
| None | NULL |

**Key correction:** AVAILABLE is NOT encoded as 0. "Tickets available" does not imply low demand. Only SOLD_OUT gets model_target=1.

---

## TEMPORAL NORMALIZATION

| Field | Format | Example |
|-------|--------|---------|
| show_start_at | ISO 8601 with timezone | `2026-10-09T20:20:00+01:00` |
| source_timestamp | ISO 8601 UTC | `2026-10-07T21:44:36Z` |
| lead_time_hours | Float (hours) | `52.3` |
| lead_time_bucket | Categorical | `15-30d` |

**Timezone:** Europe/London (BST=+01:00, GMT=+00:00)

**BST detection:** Automatic based on date (last Sunday of March to last Sunday of October).

---

## LEAD TIME DISTRIBUTION

| Bucket | Screenings | Sold Out | Rate |
|--------|-----------|----------|------|
| 0-24h | 9 | 0 | 0.0% |
| 1-3d | 17 | 3 | 17.6% |
| 4-7d | 35 | 3 | 8.6% |
| 8-14d | 55 | 3 | 5.5% |
| 15-30d | 155 | 13 | 8.4% |
| 30d+ | 492 | 2 | 0.4% |

**Observation:** 1-3d bucket has highest sold_out rate (17.6%). This is expected — screenings close to showtime have had more time to sell out.

---

## QLOO RESOLUTION RESULTS

| Status | Films | % |
|--------|-------|---|
| VERIFIED | 3 | 0.9% |
| AMBIGUOUS | 221 | 65.6% |
| MISMATCH | 112 | 33.2% |
| UNRESOLVED | 1 | 0.3% |
| **Total** | **337** | |

**Why so few VERIFIED?** PCC doesn't provide film years in their listings. The resolver correctly returns AMBIGUOUS when title matches but year is unverifiable.

**VERIFIED films** (where year was provided by PCC):
- The Mummy (1999)
- 2 others with explicit years

**AMBIGUOUS ≠ wrong.** Most AMBIGUOUS matches are likely correct (e.g., "Casablanca", "Blue Velvet"), but without year verification, we cannot confirm.

---

## PREDICTION-TIME LEAKAGE PREVENTION

| Feature Status | Screenings |
|---------------|-----------|
| AVAILABLE_AT_PREDICTION_TIME | 0 |
| FUTURE_FEATURE_UNAVAILABLE | 9 |
| NO_FEATURE | 754 |

**All 9 screenings with verified Qloo entities have FUTURE_FEATURE_UNAVAILABLE** — the Qloo features were retrieved AFTER the screening observations, so they are correctly excluded from prediction analysis.

This is the leakage prevention working as designed.

---

## SCREENING-LEVEL COVERAGE

| Metric | Count | Rate |
|--------|-------|------|
| Total screenings | 763 | |
| With verified Qloo entity | 9 | 1.2% |
| With prediction-time feature | 0 | 0.0% |
| With future feature | 9 | 1.2% |

**Honest assessment:** Current Qloo coverage is 1.2% of screenings. This is insufficient for meaningful signal evaluation.

---

## BIAS/COVERAGE AUDIT

### By Month
| Month | Screenings | Sold Out | Rate |
|-------|-----------|----------|------|
| Oct 2026 | 211 | 20 | 9.5% |
| Nov 2026 | 282 | 3 | 1.1% |
| Dec 2026 | 270 | 1 | 0.4% |

**Note:** October has highest sold_out rate because screenings are closest to observation time.

### By Format
| Format | Screenings | Sold Out | Rate |
|--------|-----------|----------|------|
| none | 350 | 11 | 3.1% |
| 35mm | 187 | 7 | 3.7% |
| 4K | 105 | 2 | 1.9% |
| 1-MEM | 11 | 3 | 27.3% |

**Note:** 1-MEM (membership screenings) have highest sold_out rate (27.3%). This suggests membership screenings have higher demand.

---

## STATE TRANSITIONS

| Metric | Count |
|--------|-------|
| Multi-snapshot observations | 763 |
| AVAILABLE → SOLD_OUT transitions | 1 |

**Note:** Only 1 state transition observed. Most screenings have consistent availability across snapshots.

---

## CLAIMS CORRECTED

| Old Claim | Corrected Claim |
|-----------|----------------|
| "667 outcome labels" | "763 screening availability observations" |
| "20 high-attendance screenings" | "24 screenings were reported sold out by the venue" |
| "647 low-demand screenings" | "739 screenings were observed with tickets available at the snapshot time" |
| "Qloo has been validated against outcomes" | NOT YET — insufficient prediction-time features |

---

## GATE VALIDATION

| # | Gate | Status |
|---|------|--------|
| 1 | Label semantics corrected | ✅ |
| 2 | Show timestamps normalized | ✅ |
| 3 | Observation lead time modeled | ✅ |
| 4 | 337 unique films through resolver | ✅ |
| 5 | Qloo feature snapshots exist | ✅ (popularity from resolution) |
| 6 | Prediction-time leakage blocked | ✅ |
| 7 | Analytical benchmark exists | ✅ |
| 8 | Film-level and screening-level coverage reported | ✅ |
| 9 | State transitions preserved | ✅ |
| 10 | AVAILABLE not treated as negative outcome | ✅ |
| 11 | Provenance complete | ✅ |
| 12 | Full tests pass | ✅ (339) |
| 13 | No ML training | ✅ |

---

## NEXT STEPS

1. **Get film years** — Either from PCC detail pages or external sources (IMDB, TMDb)
2. **Re-resolve with years** — Should dramatically increase VERIFIED rate
3. **Collect temporal data** — Run weekly for 3-6 months
4. **Then** evaluate Qloo signal vs sold_out rate

---

**Status:** Pipeline complete. Label semantics corrected. Timestamps normalized. Leakage blocked. Qloo resolution attempted with honest results. ML readiness: NOT_ML_READY (insufficient verified entities and temporal data).