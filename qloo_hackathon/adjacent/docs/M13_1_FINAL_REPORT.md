# M13.1: Final Report — Real Outcome Dataset & Model-Readiness Lock

**Date:** 2026-10-07

---

## FINAL REPORT — 12 QUESTIONS

**1. What real outcome datasets exist?**
- Kaggle Cinema Tickets: 142,524 screening-level observations, tickets_sold + occupancy, 2018, anonymized
- Poland show-level: 179,103 shows, attendance per show, 2016-2018, PROPRIETARY (unavailable)
- Apify UK Showtimes Scraper: sold_out flag, UK venues, ongoing scraping required

**2. Which are actually usable?**
Kaggle is the only accessible dataset with real attendance. But its anonymized identifiers prevent joining to Qloo.

**3. Which one is best?**
Kaggle Cinema Tickets — screening-level, real attendance, occupancy, capacity. Fatal flaw: anonymized codes.

**4. How many real labelled observations can be obtained?**
0 (zero) that can be joined to Qloo entities. 142,524 exist in Kaggle but cannot be connected.

**5. What is the exact target?**
Primary: `tickets_sold` (integer count). Secondary: `occu_perc` (occupancy rate, 0-1).

**6. Can outcomes be joined to Qloo?**
NO. Kaggle uses anonymized film_codes and cinema_codes with no mapping to real titles or identifiers.

**7. What is the join success rate?**
0%. No mapping exists from Kaggle codes to film titles, IMDB IDs, or Qloo entity IDs.

**8. Is leakage avoidable?**
If data were joinable: YES — temporal split (train on months 1-6, test on months 7-8).

**9. Is the current ranker testable?**
NOT against real outcomes. The ranker is tested for policy invariance (M12.9) but not for outcome prediction.

**10. Is supervised ML justified?**
NOT YET. No joinable outcome data exists.

**11. What should the next model be?**
IF data becomes available: LightGBM Ranker with Qloo + programme + venue + temporal features. Evaluated against affinity-only baseline and current deterministic ranker.

**12. What would make us reject the ML approach?**
- No accessible dataset with joinable outcome labels
- Learned model doesn't beat affinity-only baseline
- Venue features dominate Qloo features

---

## MOST IMPORTANT RESEARCH ANSWER

**D. There is currently insufficient real data to validate whether Qloo affinity predicts attendance.**

"Under the tested Qloo evidence-ranking policies, TV-show entities rank highest because they exhibit higher observed Qloo affinity in these programme contexts. Whether this cultural signal predicts actual cinema attendance cannot be determined from publicly available data."

---

## DOCUMENTATION

- `M13_1_DATA_AUDIT.md` — Full dataset audit (10 sources)
- `M13_1_DATASET_MATRIX.md` — Comparison matrix
- `M13_1_LABEL_SCHEMA.md` — Canonical outcome schema
- `M13_1_MODEL_READINESS.md` — Readiness gates and architecture
- `data/processed/m13_1_outcome_benchmark.json` — Machine-readable benchmark (empty — no joinable data)

---

## ML READINESS: NOT_ML_READY

The system is architecturally ready. The missing piece is data access.

---

**Status:** COMPLETE