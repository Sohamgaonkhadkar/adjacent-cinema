# M13.3: Data Quality Report

**Date:** 2026-10-07

---

## COMPLETENESS

| Field | Completeness | Notes |
|-------|-------------|-------|
| screening_key | 100% | Deterministic ID |
| film_title | 100% | Required |
| show_date | 100% | Required |
| sold_out | 100% | 20 sold, 647 available |
| venue | 100% | "Prince Charles Cinema" |
| source_url | 100% | All from princecharlescinema.com |
| show_time | 98% | ~2% missing from HTML |
| format | 37% | 248 screenings have format |
| film_year | 71% | 475 screenings have year |
| qloo_entity_id | 0% | Not yet resolved |

---

## CONSISTENCY

| Check | Result |
|-------|--------|
| Duplicate screenings | 0 |
| Duplicate snapshots | 0 (idempotent) |
| Orphaned snapshots | 0 |
| Missing dates | 0 |
| Missing titles | 0 |
| Date range | 2026-10-09 to 2026-12-31 |

---

## OUTLIER DETECTION

| Metric | Value | Expected | Status |
|--------|-------|----------|--------|
| sold_out rate | 3.0% | 1-15% | ✅ Normal |
| Screening count | 667 | 200-2000 | ✅ Normal |
| Film count | 312 | 100-800 | ✅ Normal |
| Date span | 84 days | 30-120 | ✅ Normal |

---

## ANOMALIES DETECTED

None. All metrics within expected ranges.

---

## KNOWN LIMITATIONS

1. **No Qloo resolution yet** — Cannot evaluate Qloo signal until resolution complete
2. **Single venue** — Only PCC data (multi-venue after pipeline stable)
3. **Temporal coverage** — Only current/future screenings (no historical)
4. **Sold out definition** — PCC-specific (other venues may differ)

---

**Status:** Data quality PASS. No anomalies. Ready for continued collection.