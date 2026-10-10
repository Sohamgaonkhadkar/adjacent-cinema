# M13.4: Final Report — Temporal Qloo Join & Leakage-Safe Proxy Benchmark

**Date:** 2026-10-07
**Commit:** Pending
**Status:** COMPLETE

---

## EXECUTIVE SUMMARY

M13.4 corrected critical label semantics bugs, normalized timestamps, modeled observation horizon, attempted Qloo resolution for all 337 unique films, built a leakage-safe analytical benchmark, and ran comprehensive audits.

**Key findings:**
1. Label semantics corrected: sold_out=False → DESCRIPTIVE_ONLY (not STRONG_PROXY)
2. Timestamps normalized to Europe/London with BST/GMT detection
3. Lead time modeled: 0-24h, 1-3d, 4-7d, 8-14d, 15-30d, 30d+
4. Qloo resolution: 3 VERIFIED / 337 unique films (0.9%)
5. Prediction-time leakage: ZERO contamination
6. 339 tests passing

---

## 10 QUESTIONS ANSWERED

### 1. How many of 337 films resolve?

| Status | Count | % |
|--------|-------|---|
| VERIFIED | 3 | 0.9% |
| AMBIGUOUS | 221 | 65.6% |
| MISMATCH | 112 | 33.2% |
| UNRESOLVED | 1 | 0.3% |

**Why so few VERIFIED:** PCC doesn't provide film years. The resolver correctly returns AMBIGUOUS when title matches but year is unverifiable.

### 2. How many screenings obtain a verified Qloo entity?

9 / 763 (1.2%)

### 3. How many have prediction-time Qloo features?

0 / 763 (0.0%)

**Why:** Qloo resolution happened AFTER screening collection. Features are marked FUTURE_FEATURE_UNAVAILABLE.

### 4. How many observations are future-feature contaminated?

**Zero.** All 9 observations with Qloo features correctly exclude them because features were retrieved after observation time.

### 5. What is the actual lead-time distribution?

| Bucket | Screenings | % |
|--------|-----------|---|
| 0-24h | 9 | 1.2% |
| 1-3d | 17 | 2.2% |
| 4-7d | 35 | 4.6% |
| 8-14d | 55 | 7.2% |
| 15-30d | 155 | 20.3% |
| 30d+ | 492 | 64.5% |

**Observation:** Most screenings are 30+ days away. Closest screenings (1-3d) have highest sold_out rate (17.6%).

### 6. How many state transitions exist?

1 / 763 screenings transitioned from AVAILABLE → SOLD_OUT.

### 7. What is the sold_out observation rate?

24 / 763 (3.1%)

### 8. What percentage of available states are correctly treated as descriptive?

**100%.** All available states (739) have model_target=NULL (not 0) and label_quality=DESCRIPTIVE_ONLY (not STRONG_PROXY).

### 9. Is the benchmark leakage-safe?

**Yes.** Zero observations use future Qloo information. The leakage prevention mechanism works correctly.

### 10. Can Qloo + proxy evaluation now begin?

**Not yet.** Three blockers:
1. Only 3 VERIFIED entities (need film years)
2. Zero prediction-time features (need temporal accumulation)
3. Only 1 state transition (need more data)

---

## DELIVERABLES

| File | Description |
|------|-------------|
| `backend/app/domain/outcome_repository.py` | M13.4 repository with temporal fields, corrected labels |
| `backend/app/collectors/prince_charles.py` | M13.4 collector with timezone normalization |
| `research/scripts/m13_4_collect.py` | Full M13.4 pipeline script |
| `backend/tests/test_m13_4_temporal_qloo.py` | 53 tests for M13.4 |
| `data/processed/m13_4_qloo_proxy_benchmark.json` | Analytical benchmark |
| `data/processed/m13_4_audit.json` | Resolution + bias audit |
| `docs/M13_4_TEMPORAL_QLOO_LOCK.md` | Temporal Qloo lock report |
| `docs/M13_4_DATASET_REPORT.md` | Dataset report |
| `docs/M13_4_LEAKAGE_AUDIT.md` | Leakage audit |

---

## GATE VALIDATION (13 items)

| # | Gate | Status |
|---|------|--------|
| 1 | Label semantics corrected | ✅ |
| 2 | Show timestamps normalized | ✅ |
| 3 | Observation lead time modeled | ✅ |
| 4 | 337 unique films through resolver | ✅ |
| 5 | Qloo feature snapshots exist | ✅ |
| 6 | Prediction-time leakage blocked | ✅ |
| 7 | Analytical benchmark exists | ✅ |
| 8 | Film-level and screening-level coverage reported | ✅ |
| 9 | State transitions preserved | ✅ |
| 10 | AVAILABLE not treated as negative outcome | ✅ |
| 11 | Provenance complete | ✅ |
| 12 | Full tests pass | ✅ (339) |
| 13 | No ML training | ✅ |

**13/13 gates passed.**

---

## WHAT M13.4 CORRECTED

| Issue | M13.3 | M13.4 |
|-------|-------|-------|
| sold_out=False label | STRONG_PROXY | DESCRIPTIVE_ONLY |
| AVAILABLE model_target | 0 | NULL |
| Date format | Free-text | ISO 8601 with timezone |
| Lead time | Not modeled | Bucketed |
| Resolution scope | Per observation | Per unique film |
| Prediction-time check | None | enforced |
| Feature timestamps | Optional | Required |

---

## NEXT STEPS

1. **Get film years** — Scrape PCC detail pages or use external source
2. **Re-resolve with years** — Should dramatically increase VERIFIED rate
3. **Collect weekly** — Accumulate temporal data
4. **Then** evaluate Qloo signal

---

**ML readiness: NOT_ML_READY** — Insufficient verified entities and temporal data.

**M13.5 = Multi-Venue Outcome Expansion + Initial Descriptive Qloo Signal Test** (after M13.4 stable).