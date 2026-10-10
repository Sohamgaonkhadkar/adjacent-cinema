# M13.3: Live Outcome Collection Report

**Date:** 2026-10-07
**Status:** COMPLETE

---

## COLLECTION SUMMARY

| Metric | Value |
|--------|-------|
| Collection date | 2026-10-07 |
| Venue | Prince Charles Cinema |
| Source URL | https://princecharlescinema.com/whats-on/ |
| Total screenings | 667 |
| Unique films | 312 |
| Sold out | 20 (3.0%) |
| Available | 647 (97.0%) |
| Unknown | 0 |
| Snapshots | 667 |
| Duplicate rate | 0% |

---

## FIRST REAL PROXY OBSERVATIONS

This is the **first real proxy data** collected in the Adjacent project.

| Classification | Count | Definition |
|---------------|-------|-----------|
| SOLD_OUT | 20 | "Venue's public booking system reported sold out" |
| AVAILABLE | 647 | "Tickets were available at time of observation" |

**SOLD_OUT is a STRONG PROXY.** It does NOT mean "attendance was high." It means "the venue reported no tickets remaining."

---

## SOLD OUT SCREENINGS (first 10)

| Date | Time | Film | Format |
|------|------|------|--------|
| Friday 9th October | 8:20 pm | The Thing | — |
| Saturday 10th October | 12:15 pm | Psycho | — |
| Saturday 10th October | 5:45 pm | Possession | — |
| Monday 12th October | 6:00 pm | Ken Russell's The Devils | 4K |
| Saturday 31st October | 8:00 pm | Ken Russell's The Devils | 35mm |
| Sunday 1st November | 3:10 pm | Ken Russell's The Devils | 35mm |
| Monday 12th October | 6:15 pm | Invasion of the Body Snatchers | £1 MEM |
| Tuesday 27th October | 6:20 pm | The Texas Chain Saw Massacre | 35mm |
| Friday 30th October | 8:50 pm | The Texas Chain Saw Massacre | 35mm |
| Friday 16th October | 5:45 pm | Halloween (1978) + Halloween II | — |

---

## PIPELINE COMPONENTS

| Component | Status | Location |
|-----------|--------|----------|
| Outcome repository | ✅ Working | `backend/app/domain/outcome_repository.py` |
| Prince Charles collector | ✅ Working | `backend/app/collectors/prince_charles.py` |
| Collection script | ✅ Working | `research/scripts/m13_3_collect.py` |
| SQLite database | ✅ Created | `data/processed/outcome_ledger.db` |
| Benchmark JSON | ✅ Created | `data/processed/m13_3_proxy_benchmark.json` |

---

## IDEMPOTENCY VERIFIED

- Same screening scraped twice → exactly one observation
- State change (Book → Sold Out) creates new snapshot
- Previous state preserved in snapshot history

---

## DATA QUALITY

| Check | Result |
|-------|--------|
| Missing dates | 0 |
| Missing titles | 0 |
| Duplicate screenings | 0 (deterministic key) |
| Unknown states | 0 |
| Suspicious sold_out rate | No (3.0% — reasonable) |

---

## TESTS

19 tests:
- Idempotency (duplicate scrape → one observation)
- State change (Book → Sold Out → new snapshot)
- NULL preservation (NULL stays NULL)
- Recommendation persistence
- Label quality (STRONG_PROXY, DIRECT_OUTCOME)
- Duplicate protection
- Validation (negative tickets, zero capacity, out-of-range occupancy)
- Film resolution
- Data quality audit
- Deterministic IDs

---

## NEXT STEPS

1. Run collection weekly for 3-6 months
2. Add Genesis Cinema collector
3. Add ICA Cinema collector
4. After sufficient data: evaluate Qloo signal vs sold_out rate

---

**ML readiness: NOT_ML_READY** — Need 3-6 months of data for meaningful analysis.

**Status:** Pipeline operational, collecting real proxy data.