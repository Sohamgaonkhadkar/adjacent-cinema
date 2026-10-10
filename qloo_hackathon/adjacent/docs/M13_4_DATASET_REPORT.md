# M13.4: Dataset Report

**Date:** 2026-10-07

---

## DATASET OVERVIEW

| Metric | Value |
|--------|-------|
| Version | M13.4 |
| Collection date | 2026-10-07 |
| Venue | Prince Charles Cinema |
| Total screenings | 763 |
| Unique films | 337 |
| Sold out | 24 (3.1%) |
| Available | 739 (96.9%) |
| Unknown | 0 |

---

## SCHEMA

Each analytical row contains:

| Field | Type | Description |
|-------|------|-------------|
| observation_id | string | Deterministic screening ID |
| venue_id | string | "prince_charles_cinema" |
| film_title | string | Film title from PCC |
| film_year | int\|null | Year (usually null from PCC) |
| show_start_at | string | ISO 8601 with timezone (Europe/London) |
| observation_timestamp | string | ISO 8601 UTC |
| lead_time_hours | float\|null | Hours between observation and show |
| lead_time_bucket | string | "0-24h", "1-3d", "4-7d", "8-14d", "15-30d", "30d+" |
| sold_out_observed | int\|null | 1=sold out, 0=available, null=unknown |
| model_target | int\|null | 1=SOLD_OUT, null=AVAILABLE (NOT 0) |
| qloo_entity_id | string\|null | Qloo entity ID (if resolved) |
| qloo_affinity | float\|null | Qloo affinity (if available) |
| qloo_popularity | float\|null | Qloo popularity score |
| qloo_band | string\|null | Popularity band |
| qloo_domain | string\|null | "film" |
| qloo_feature_timestamp | string\|null | When Qloo feature was retrieved |
| qloo_feature_status | string | "AVAILABLE_AT_PREDICTION_TIME" \| "FUTURE_FEATURE_UNAVAILABLE" \| "NO_FEATURE" |
| format | string | "35mm", "4K", "70mm", etc. |
| booking_url | string\|null | PCC booking URL |
| source_url | string | PCC whats-on URL |
| source_timestamp | string | When data was scraped |
| resolution_status | string | "VERIFIED" \| "AMBIGUOUS" \| "MISMATCH" \| "UNRESOLVED" \| "NO_RESOLUTION" |
| provenance | string | Resolution provenance |

---

## MODEL TARGET SEMANTICS

| sold_out_observed | model_target | Meaning |
|-------------------|-------------|---------|
| 1 (SOLD_OUT) | 1 | Venue reported no tickets remaining |
| 0 (AVAILABLE) | NULL | Tickets were available at observation time |
| NULL (UNKNOWN) | NULL | State unknown |

**CRITICAL:** AVAILABLE is NOT encoded as 0. "Tickets available" does not imply low demand.

---

## QLOO FEATURE STATUS

| Status | Meaning |
|--------|---------|
| AVAILABLE_AT_PREDICTION_TIME | Qloo feature retrieved before observation — safe to use |
| FUTURE_FEATURE_UNAVAILABLE | Qloo feature retrieved after observation — excluded |
| NO_FEATURE | No Qloo feature exists for this film |

---

## DATA QUALITY

| Check | Result |
|-------|--------|
| Missing dates | 0 |
| Missing titles | 0 |
| Duplicate screenings | 0 (deterministic key) |
| Unknown states | 0 |
| Suspicious sold_out rate | No (3.1% — reasonable) |

---

## COVERAGE

| Metric | Count | Rate |
|--------|-------|------|
| Total screenings | 763 | |
| With verified Qloo entity | 9 | 1.2% |
| With prediction-time feature | 0 | 0.0% |
| With future feature | 9 | 1.2% |

---

## FILES

| File | Description |
|------|-------------|
| `data/processed/outcome_ledger.db` | SQLite database |
| `data/processed/m13_4_qloo_proxy_benchmark.json` | Analytical benchmark |
| `data/processed/m13_4_audit.json` | Resolution + bias audit |

---

**Status:** Dataset complete. Ready for temporal accumulation.