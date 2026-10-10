# M13.2: Final Report — Real-World Outcome Bridge & Validation Benchmark

**Date:** 2026-10-07
**Status:** COMPLETE

---

## FINAL REPORT — 16 QUESTIONS

**1. Did any Kaggle identifier mapping exist?**
No. Exhaustive search of Kaggle discussions (5 threads), notebooks (20), GitHub repos (5+), and creator profile found no mapping. The dataset is from an Iranian/Turkish cinema chain with intentionally anonymized codes.

**2. What percentage of film IDs were recovered?**
0%. film_code → film_title: UNRESOLVED.

**3. What percentage of cinema IDs were recovered?**
0%. cinema_code → venue_name: UNRESOLVED.

**4. What percentage of screenings became joinable?**
0%. No mapping exists.

**5. What percentage resolved to Qloo?**
0%. Cannot join without film identity.

**6. If Kaggle remains blocked, what real proxy was obtained?**
Prince Charles Cinema website shows real sold_out flags for current screenings. Film title, year, format, showtime, and sold_out status are publicly accessible. This is a STRONG PROXY but requires scraper development.

**7. How many direct outcome observations exist?**
0. No dataset currently provides joinable screening-level attendance.

**8. How many strong-proxy observations exist?**
0. Prince Charles sold_out data is available but not yet scraped.

**9. How many weak-proxy observations exist?**
0.

**10. Does Qloo add measurable value?**
UNKNOWN. Cannot measure without outcome data. This is the central unanswered question.

**11. Does the current deterministic ranker beat affinity-only?**
UNKNOWN. Cannot measure without outcome data. The ranker was tested for policy invariance (M12.9) but not for outcome prediction.

**12. Is exact entity selection robust?**
PARTIALLY. Domain-level: YES (tv_show wins across all policies). Entity-level: SENSITIVE to popularity weight (M12.9).

**13. Is ML actually justified?**
NOT YET. Zero outcome observations. ML readiness = NOT_ML_READY.

**14. If ML is justified, what exact model and target?**
IF data becomes available: LightGBM Ranker. Target: sold_out (binary) or occupancy_rate. Evaluated against 5 baselines with venue/time-grouped metrics.

**15. If ML is NOT justified, why?**
No publicly available dataset has BOTH real screening-level attendance AND joinable identifiers to Qloo entities. The Kaggle dataset is the best outcome source but its identifiers are permanently anonymized.

**16. What data must we collect prospectively?**
1. Adjacent recommendations → outcome_ledger (schema created)
2. Prince Charles Cinema sold_out scraping (weekly)
3. Film title → Qloo entity resolution (via Adjacent resolver)
4. After 3-6 months: evaluate Qloo signal vs sold_out

---

## DELIVERABLES CREATED

| File | Description |
|------|-------------|
| `docs/M13_2_IDENTIFIER_RECOVERY.md` | Kaggle identifier recovery attempt + UK proxy analysis |
| `docs/M13_2_OUTCOME_BRIDGE.md` | Join feasibility + bridge status |
| `docs/M13_2_VALIDATION_DESIGN.md` | Evaluation architecture + metrics |
| `docs/M13_2_MODEL_DECISION.md` | ML readiness + ranker evaluation |
| `research/scripts/m13_2_validation.py` | Evaluation pipeline design |
| `backend/app/domain/outcome_ledger.py` | Prospective outcome logging schema |
| `data/processed/m13_2_validation_design.json` | Machine-readable validation design |

---

## ML READINESS: NOT_ML_READY

**Reason:** Zero outcome observations. The Kaggle dataset (best source) has permanently anonymized identifiers. No other public dataset provides screening-level attendance with joinable identifiers.

---

## RECOMMENDED PATH FORWARD

1. **Now:** Deploy prospective outcome logging in Adjacent
2. **1-2 days:** Build Prince Charles Cinema showtime scraper
3. **3-6 months:** Collect weekly sold_out snapshots
4. **After collection:** Evaluate Qloo signal vs sold_out rate
5. **If justified:** Train LightGBM Ranker

---

## STRICT CLAIM COMPLIANCE

**Valid claims (current):**
- "Qloo provides cultural adjacency signals."
- "Under tested policies, Qloo affinity ranks TV-show entities highest."
- "The decision layer is deterministic and policy-invariant."

**NOT claimed:**
- ❌ "Qloo increases attendance"
- ❌ "Adjacent predicts attendance"
- ❌ "Qloo is more accurate"
- ❌ "Our model predicts demand"

---

**Status:** COMPLETE