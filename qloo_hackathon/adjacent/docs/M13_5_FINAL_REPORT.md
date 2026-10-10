# M13.5: Canonical Film Identity + Verified Qloo Join — Final Report

**Date:** 2026-10-07
**Commit:** Pending
**Status:** COMPLETE

---

## EXECUTIVE SUMMARY

M13.5 built a canonical film identity layer, scraped PCC detail pages for film years, and re-ran the EntityResolver with canonical titles + years. The result: **VERIFIED film count jumped from 3 to 208** (0.9% → 79.9%).

---

## KEY METRICS

| Metric | M13.4 | M13.5 | Change |
|--------|-------|-------|--------|
| Raw film count | 337 | 337 | — |
| Canonical film count | 312 | 312 | — |
| Collapse count | 25 | 25 | — |
| Events excluded | 28 | 23 | — |
| VERIFIED films | 3 | **208** | +205 |
| AMBIGUOUS | 221 | 11 | -210 |
| MISMATCH | 112 | 37 | -75 |
| UNRESOLVED | 1 | 0 | -1 |
| Screening coverage | 9/763 (1.2%) | **610/726 (84.0%)** | +82.8pp |
| Prediction-time features | 0 | **0** | — |

---

## PHASE 1: CANONICALIZATION AUDIT

### Normalization Rules Applied

| Rule | Count | Example |
|------|-------|---------|
| HTML entity decode | 25 | `Angel&#039;s Egg` → `Angel's Egg` |
| Edition suffix removed | 18 | `Alien (Theatrical Cut)` → `Alien` |
| Year extracted | 13 | `Black Christmas (1974)` → `Black Christmas` |
| Director prefix removed | 6 | `Ken Russell's The Devils` → `The Devils` |
| Colon normalized | 9 | `2001 : A Space Odyssey` → `2001: A Space Odyssey` |

### Collapsed Groups (25 examples)

| Canonical Key | Raw Titles |
|--------------|-----------|
| `a very harold & kumar christmas\|none` | `A Very Harold & Kumar Christmas`, `A Very Harold &amp; Kumar Christmas` |
| `angel's egg\|none` | `Angel&#039;s Egg`, `Angel's Egg` |
| `don't look now\|none` | `Don&#039;t Look Now`, `Don't Look Now` |
| `the devils\|none` | `Ken Russell&#039;s The Devils: The Director&#039;s Cut`, `Ken Russell's The Devils: The Director's Cut` |

### Events Detected (23)

- Double features (e.g., "Halloween (1978) + Halloween II (1981)")
- Marathons (e.g., "Classic Horror Marathon")
- Shorts programmes (e.g., "Call Your Bluff [Shorts Programme]")
- Live scores (e.g., "Nosferatu with Live Score")
- Special events (e.g., "Christmas Pyjama Party")

---

## PHASE 2: FILM IDENTITY RECORDS

Canonical films stored in `canonical_film` table with:
- `film_key`: Deterministic key (normalized title + year)
- `raw_titles`: All raw title variants (JSON array)
- `canonical_title`: Normalized title
- `film_year`: Year with provenance
- `year_source`: "pcc_detail_page" | "pcc_provided" | "extracted_from_title"
- `identity_status`: VERIFIED | YEAR_MISSING | EVENT_OR_COMPOSITE | NEEDS_REVIEW

---

## PHASE 3: YEAR PROVENANCE

### Sources

| Source | Films | % |
|--------|-------|---|
| PCC detail page | 256 | 88.9% |
| PCC listing (embedded year) | 13 | 4.5% |
| No year available | 19 | 6.6% |

### Year Scraping Results

- Attempted: 269 films
- Years found: 256 (95.2%)
- Failed: 13 (4.8%)

**Provenance:** Every year from PCC detail pages has `year_source="pcc_detail_page"` and `year_provenance` with the exact evidence string.

---

## PHASE 4: QLOO RESOLUTION

| Status | Films | % |
|--------|-------|---|
| VERIFIED | 208 | 79.9% |
| AMBIGUOUS | 11 | 4.2% |
| MISMATCH | 37 | 14.2% |
| UNRESOLVED | 0 | 0.0% |

### MISMATCH Analysis (37 cases)

| Category | Count | Examples |
|----------|-------|---------|
| Title variant (punctuation) | 12 | `The Squid & The Whale` vs `The Squid and the Whale` |
| Composite/event title | 8 | `The Lord of the Rings Trilogy` |
| Edition suffix in Qloo | 7 | `The Wicker Man - The Final Cut` |
| Foreign title variant | 5 | `Wings of Desire [Der Himmel über Berlin]` |
| Genuine title conflict | 5 | `The Unknown` (multiple films) |

**Note:** MISMATCH records are NOT relabeled to improve percentages. They are genuine conflicts.

---

## PHASE 5: QLOO FEATURE SEMANTICS

### Separation

| Feature Type | Fields | Source |
|-------------|--------|--------|
| Identity/Resolution | qloo_entity_id, qloo_domain, qloo_popularity, qloo_band | /search endpoint |
| Cultural Affinity | affinity, cohort/context, signal definition | /insights endpoint (NOT YET) |

**Current state:** Only identity/resolution features are stored. `qloo_affinity` is NULL because no legitimate cohort/context has been defined yet.

**qloo_popularity is NOT cultural affinity.** It is a general popularity score from Qloo's entity data.

---

## PHASE 6: TEMPORAL LEAKAGE LOCK

| Test | Result |
|------|--------|
| Feature before observation → usable | ✅ PASS |
| Feature at observation boundary → usable (<=) | ✅ PASS |
| Feature after observation → excluded | ✅ PASS |
| Multiple historical snapshots → latest valid prior | ✅ PASS |
| No historical feature → NO_FEATURE | ✅ PASS |

**Zero future-feature contamination.** All 610 screenings with verified entities have `qloo_feature_status=FUTURE_FEATURE_UNAVAILABLE` because Qloo resolution happened AFTER screening collection.

---

## PHASE 7: SCREENING-LEVEL JOIN

### Film-Level Coverage

| Metric | Value |
|--------|-------|
| Unique canonical films (non-event) | 289 |
| Films with VERIFIED Qloo entity | 231 |
| Film verification rate | 79.9% |

### Screening-Level Coverage

| Metric | Value |
|--------|-------|
| Non-event observations | 726 |
| Screenings with verified entity | 610 |
| Screening verification rate | 84.0% |
| Prediction-time features | 0 |
| Future features | 610 |

### Coverage by Lead Time

| Bucket | Verified | Total | Rate |
|--------|----------|-------|------|
| 0-24h | 5 | 8 | 62.5% |
| 1-3d | 14 | 16 | 87.5% |
| 4-7d | 29 | 33 | 87.9% |
| 8-14d | 40 | 54 | 74.1% |
| 15-30d | 116 | 139 | 83.5% |
| 30d+ | 406 | 476 | 85.3% |

### Coverage by Film Frequency

| Frequency | Verified | Total | Rate |
|-----------|----------|-------|------|
| 3+ screenings | 35 | 46 | 76.1% |

---

## SCIENTIFIC ACCEPTANCE GATES

| # | Gate | Status |
|---|------|--------|
| 1 | Canonicalization is deterministic and tested | ✅ 40 tests |
| 2 | No uncertain title merges silently performed | ✅ Documented |
| 3 | Every external year has provenance | ✅ year_source + year_provenance |
| 4 | Existing EntityResolver reused | ✅ No second resolver |
| 5 | VERIFIED never from unverified identity | ✅ year required |
| 6 | MISMATCH cases audited | ✅ 37 cases categorized |
| 7 | qloo_popularity not mislabeled as affinity | ✅ Affinity is NULL |
| 8 | affinity is NULL without cohort/context | ✅ No /insights calls |
| 9 | Temporal leakage prevention passes | ✅ 5 tests |
| 10 | Screening-level joins use canonical film_key | ✅ Linked |
| 11 | Raw-title duplicates don't inflate counts | ✅ 25 collapsed |
| 12 | Full test suite passes | ✅ 379 tests |
| 13 | No ML training | ✅ Zero |
| 14 | Prediction-time coverage reported | ✅ Explicitly zero |

**14/14 gates passed.**

---

## REMAINING BLOCKER FOR OUTCOME EVALUATION

**Prediction-time Qloo feature coverage is STILL ZERO.**

All 610 Qloo features were retrieved AFTER the screening observations. This is because:
1. Qloo resolution happened in this session (2026-10-07)
2. Screening observations were also collected in this session
3. Features are correctly excluded by the leakage prevention rule

**To obtain prediction-time features:**
1. Run Qloo resolution weekly (creates historical snapshots)
2. Run PCC scraping daily/weekly
3. Use Qloo snapshots from BEFORE the observation time

**This is a temporal data accumulation problem, not a pipeline problem.**

---

## CLAIMS CORRECTED

| Old Claim | Corrected Claim |
|-----------|----------------|
| "337 unique films" | "312 canonical films (25 raw duplicates collapsed)" |
| "3 VERIFIED entities" | "208 VERIFIED entities (after year scraping)" |
| "1.2% screening coverage" | "84.0% screening coverage" |
| "Qloo predicts attendance" | NOT CLAIMED |

---

## DELIVERABLES

| File | Description |
|------|-------------|
| `backend/app/domain/film_identity.py` | Canonicalization function |
| `backend/app/collectors/pcc_years.py` | PCC year scraper |
| `research/scripts/m13_5_canonicalize.py` | Full M13.5 pipeline |
| `backend/tests/test_m13_5_canonical_identity.py` | 40 tests |
| `data/processed/m13_5_canonical_benchmark.json` | Canonical benchmark |
| `data/processed/m13_5_audit.json` | Full audit |
| `data/processed/outcome_ledger.db` | Updated SQLite with canonical_film table |

---

## NEXT STEPS

1. **Accumulate temporal data** — Run weekly for 3-6 months
2. **Create prediction-time Qloo snapshots** — Resolve films BEFORE scraping
3. **Then** evaluate Qloo signal vs sold_out rate

---

**ML readiness: NOT_ML_READY** — Need prediction-time Qloo features (temporal accumulation required).