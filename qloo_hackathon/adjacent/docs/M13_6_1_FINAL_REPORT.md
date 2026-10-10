# M13.6.1 — Temporal Freeze + Leakage Lock Repair

**Status:** COMPLETE
**Commit:** (pending)
**Parent:** M13.6 (`9ce7264`)

---

## 1. Problem Statement

M13.6 had three temporal-design flaws that violated the prospective-evaluation contract:

### Bug 1: Premature Qloo Attachment
Future prediction rows were populated with Qloo data at creation time, not at prediction time.

**Example:** A prediction for Oct 20 (7d horizon → Oct 13 prediction timestamp) created on Oct 8 immediately received Qloo features — 5 days before the prediction timestamp arrived.

### Bug 2: Retrospective Qloo Leakage in Signal Analysis
`qloo_entity_id != NULL` was used as proof of prediction-time Qloo availability without checking whether the Qloo data was actually available at the prediction timestamp.

### Bug 3: Outcome Semantic Inconsistency
SOLD_OUT_OBSERVED only examined the final pre-show snapshot. A screening with trajectory AVAILABLE→SOLD_OUT→AVAILABLE was incorrectly classified as AVAILABLE instead of SOLD_OUT_OBSERVED.

---

## 2. Solution: Prediction Lifecycle State Machine

### States
```
PLANNED → FROZEN → OUTCOME_FINAL
                  → CENSORED
```

| State | Qloo Features | Mutability |
|-------|--------------|------------|
| PLANNED | None (cleared if provided) | Can transition to FROZEN |
| FROZEN | Frozen at prediction time | Immutable |
| OUTCOME_FINAL | Immutable | Immutable |
| CENSORED | Immutable | Immutable |

### Key Behaviors

1. **Future predictions remain PLANNED** — `upsert_prediction_snapshot()` with `prediction_timestamp > current_time` creates PLANNED with no Qloo features, regardless of what the caller passes.

2. **Freeze at prediction time** — `freeze_due_predictions(current_time)` transitions PLANNED→FROZEN for predictions whose `prediction_timestamp <= current_time` and `show_start_at > current_time`.

3. **Immutable at freeze time** — Once FROZEN, Qloo fields cannot be modified. Updates to FROZEN/OUTCOME_FINAL/CENSORED predictions are silently ignored.

4. **Trajectory-based outcome semantics** — SOLD_OUT_OBSERVED counts if sold_out was observed at ANY point after prediction (not just the final observation).

---

## 3. Database Changes

### New Columns on `prediction_snapshot`
| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `prediction_state` | TEXT | 'PLANNED' | Lifecycle state |
| `freeze_timestamp` | TEXT | NULL | ISO timestamp when frozen |
| `feature_provenance` | TEXT | '' | Source of Qloo features |

### Migration
`_migrate_prediction_snapshot()` adds columns via `ALTER TABLE ADD COLUMN` if missing. Existing rows default to PLANNED.

---

## 4. Database Repair

### Before Repair
- 2175 prediction snapshots
- 1614 with Qloo entity ID (74.2%) — all premature
- 0 with prediction_state column

### After Repair
- 2175 prediction snapshots preserved
- **2078 PLANNED** (prediction_timestamp in future)
- **91 FROZEN** (prediction_timestamp passed, show_start_at in future)
- **6 CENSORED** (past screenings with no valid freeze window)

### Qloo Coverage After Repair
| Category | Count | % |
|----------|-------|---|
| Entity linked | 73 | 3.4% |
| Prediction-time available | 6 | 0.3% |
| Retrospective only | 67 | 3.1% |
| No Qloo feature | 2102 | 96.6% |

**Key insight:** Only 6/2175 snapshots (0.3%) have prediction-time Qloo data. The remaining 67 have Qloo from resolution metadata only (retrospective). This is the honest baseline.

---

## 5. Leakage Audit V2

10 explicit checks, all must = 0:

| # | Check | Result |
|---|-------|--------|
| 1 | future_prediction_has_qloo | PASS (0) |
| 2 | qloo_attached_before_freeze | PASS (0) |
| 3 | freeze_before_prediction_timestamp | PASS (0) |
| 4 | qloo_after_freeze | PASS (0) |
| 5 | frozen_prediction_mutated | PASS (0) |
| 6 | retrospective_qloo_used_as_prediction_feature | PASS (0) |
| 7 | invalid_horizon | PASS (0) |
| 8 | duplicate_prediction_horizon | PASS (0) |
| 9 | outcome_before_prediction | PASS (0) |
| 10 | final_observation_before_prediction | PASS (0) |

**Overall: PASS**

---

## 6. Horizon Mapping

| Horizon | Days | Meaning |
|---------|------|---------|
| 168h | 7d | One week before show |
| 72h | 3d | Three days before show |
| 24h | 1d | One day before show |

---

## 7. Tests

### M13.6.1 Tests (13 new)
- `test_future_prediction_is_planned` — PLANNED predictions have no Qloo
- `test_no_qloo_features_for_planned` — Qloo data stripped from PLANNED
- `test_freeze_at_prediction_time` — PLANNED→FROZEN at correct time
- `test_frozen_cannot_be_modified` — Immutable after FROZEN
- `test_sold_out_ever_observed` — Trajectory semantics
- `test_available_near_showtime` — Available outcome
- `test_censored_no_final_observation` — CENSORED handling
- `test_oct8_oct20_scenario` — Exact regression test with fake clock
- `test_audit_passes_clean` — Audit V2 clean data
- `test_audit_fails_on_premature_qloo` — Audit V2 catches violations
- `test_run_created` — Prediction run management
- `test_idempotent_snapshots` — No duplicate snapshots
- `test_freezes_due_only` — Selective freeze by horizon

### M13.6 Tests (17 updated)
All updated to use M13.6.1 lifecycle:
- Future predictions → PLANNED (not FROZEN)
- Qloo features → attached at freeze time only
- Stats → use new key names (by_state, qloo_entity_linked, etc.)

### Full Suite
**405 passed, 4 skipped, 0 failures**

---

## 8. Files Changed

| File | Change |
|------|--------|
| `backend/app/domain/outcome_repository.py` | Added prediction lifecycle states, freeze_due_predictions(), repair_premature_predictions(), leakage_audit_v2(), updated upsert_prediction_snapshot() |
| `research/scripts/m13_6_prospective.py` | Updated step2 to create PLANNED snapshots without Qloo, added freeze call |
| `backend/tests/test_m13_6_prospective.py` | Updated 5 tests for M13.6.1 lifecycle |
| `backend/tests/test_m13_6_1_freeze.py` | New: 13 tests for freeze lifecycle |
| `data/processed/outcome_ledger.db` | Repaired 1614 premature predictions, 91 frozen |

---

## 9. Acceptance Gates (15/15)

| # | Gate | Status |
|---|------|--------|
| 1 | PLANNED state for future predictions | ✅ 2078 PLANNED |
| 2 | No Qloo features on PLANNED | ✅ 0 violations |
| 3 | freeze_due_predictions() activates at/after prediction time | ✅ 91 frozen |
| 4 | Immutability at freeze time | ✅ Tested |
| 5 | No retrospective Qloo in signal analysis | ✅ feature_status explicit |
| 6 | Database repaired | ✅ 1614 repaired |
| 7 | Trajectory-based outcome semantics | ✅ Tested |
| 8 | Horizon correction (168/72/24) | ✅ Validated |
| 9 | Leakage Audit V2 (10 checks) | ✅ All = 0 |
| 10 | Fake-clock regression test | ✅ test_oct8_oct20_scenario |
| 11 | Live validation | ✅ 91 frozen, 73 linked |
| 12 | All M13.6 tests pass | ✅ 17 passed |
| 13 | All M13.6.1 tests pass | ✅ 13 passed |
| 14 | Full suite passes | ✅ 405 passed |
| 15 | Report states all counts | ✅ This report |

---

## 10. Remaining Blockers

1. **0 completed outcomes** — All 91 FROZEN predictions still PENDING. Need screening outcomes (sold_out observations over time) to compute actual outcome labels.

2. **Low prediction-time Qloo coverage** — Only 6/91 frozen predictions (6.6%) have Qloo data from before their prediction timestamp. The other 67 use resolution metadata only (retrospective). This means most predictions cannot test Qloo signal even when outcomes arrive.

3. **No outcome evaluation** — Cannot assess whether Qloo predicts sold_out without completed outcomes. This is the M13.7 evaluation gate, not a bug.

---

## 11. What M13.6.1 Does NOT Claim

- Does NOT claim Qloo predicts attendance
- Does NOT claim 0.3% Qloo coverage is sufficient for signal testing
- Does NOT relabel historical observations
- Does NOT treat previously retrieved Qloo features as prediction-time data
- Does NOT start M13.7 (outcome evaluation)