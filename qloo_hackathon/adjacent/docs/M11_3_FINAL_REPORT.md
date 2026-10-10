# M11.3: Final Report — Decision Integrity Fix Before M12

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

M11.3 fixed two correctness issues:

1. **Wrong IMDb now produces MISMATCH** — External ID is verified via /entities endpoint
2. **Programme Bet methodology corrected** — Renamed "reach" to "cohort breadth" for scientific accuracy

---

## Answers to Required Questions

### 1. Does wrong IMDb now produce MISMATCH?

**Answer:** ✅ YES

**Evidence:** Live resolution check shows:
- wrong_imdb (tt9999999) → MISMATCH
- Notes: "external ID tt9999999 not found in Qloo — supplied ID does not match any Qloo entity"

### 2. Can unverified entities reach downstream analysis?

**Answer:** ✅ NO

**Evidence:** Resolution checks confirm:
- AMBIGUOUS → stops downstream analysis
- MISMATCH → stops downstream analysis
- UNRESOLVED → stops downstream analysis

### 3. What exactly does current-programme compatibility measure?

**Answer:** Programme adjacency — mean affinity of cohort members against programme taste profile

**Source:** Qloo `/v2/insights` scoring call — `mean_affinity` field

**Interpretation:** How culturally close the cohort is to the programme

### 4. What exactly does the second Programme Bet dimension measure?

**Answer:** Cohort breadth — fraction of cohort members above Medium affinity threshold

**Source:** Same Qloo `/v2/insights` call — `qualifying_members / total_members`

**Interpretation:** How much of the cohort clears the quality bar

### 5. Are we still making any unsupported "reach" claim?

**Answer:** ✅ NO

**Evidence:** All "reach" claims removed or replaced with "cohort breadth" (scientifically accurate)

### 6. Does the live six-film run still work?

**Answer:** ✅ YES

**Evidence:** Live run completed successfully:
- 6/6 films resolved
- 3 ranked cohorts
- Programme Bet generated with accurate labels

### 7. Is the Qloo call budget respected?

**Answer:** ✅ YES

**Evidence:** Total Qloo calls: 13 out of 24 budget

### 8. Is the system now ready for the M12 baseline/information-gain experiment?

**Answer:** ✅ YES

**Evidence:**
- Resolution: Fixed (wrong IMDb → MISMATCH)
- Programme Bet: Corrected (scientifically accurate labels)
- Tests: All pass
- Frontend: Build passes
- Live run: Works correctly

---

## Changes Made

### 1. External ID Resolution Fix

**File:** `backend/app/resolution/resolver.py`

**Change:** When external ID is supplied, verify via /entities endpoint

**Key Logic:**
- If /entities returns no results for wrong IMDb → MISMATCH
- If /entities returns same entity → VERIFIED
- If /entities returns different entity → MISMATCH

### 2. Programme Bet Methodology Fix

**File:** `backend/app/domain/programme_bet.py`

**Changes:**
- `current_audience_compatibility` → `programme_adjacency`
- `adjacent_cohort_reach` → `cohort_breadth`
- `compatibility_band` → `adjacency_band`
- `reach_band` → `breadth_band`
- Added `methodology_note` to JSON export

**Rationale:** "Reach" was misleading — it's not audience reach, it's cohort breadth

### 3. Frontend Update

**File:** `frontend/components/ProgrammeBet.tsx`

**Changes:**
- Updated labels to "Programme Adjacency" and "Cohort Breadth"
- Added descriptive subtitles
- Added methodology note display

---

## Verification

### Resolution Checks (6/6 PASS)

| Test | Expected | Actual | Result |
|------|----------|--------|--------|
| title_only | AMBIGUOUS | AMBIGUOUS | PASS |
| title_and_year | VERIFIED | VERIFIED | PASS |
| correct_imdb | VERIFIED | VERIFIED | PASS |
| wrong_imdb | MISMATCH | MISMATCH | PASS |
| ambiguous_title | AMBIGUOUS | AMBIGUOUS | PASS |
| unresolved_title | UNRESOLVED | UNRESOLVED | PASS |

### Live Run

- 6/6 films resolved
- 3 ranked cohorts
- Programme Bet generated
- Budget respected (13/24 calls)

### Tests

- Backend: 214 pass, 8 skipped, 0 failed
- Frontend: TypeScript check PASS, build PASS

---

## Deliverables

| File | Description |
|------|-------------|
| `docs/M11_3_RESOLUTION_FIX.md` | Resolution fix documentation |
| `docs/M11_3_DECISION_INTEGRITY.md` | Programme Bet methodology fix |
| `docs/M11_3_FINAL_REPORT.md` | This report |
| `docs/m11_3_live_run_result.json` | Live run results |
| `docs/m11_3_resolution_checks.json` | Resolution check results |
| `scripts/m11_3_live_run.py` | Live run script |
| `scripts/m11_3_resolution_check.py` | Resolution check script |

---

## Conclusion

M11.3 fixed two correctness issues:

1. **Wrong IMDb → MISMATCH** — External ID verified via /entities
2. **Programme Bet methodology corrected** — "Reach" replaced with "cohort breadth"

The system is now ready for M12.

---

**Next Milestone:** M12 — Qloo Incremental-Value Evaluation

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE