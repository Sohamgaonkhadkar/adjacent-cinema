# M11.2: Programme Bet Runtime Implementation

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

M11.2 completed the two-sided Programme Bet with real Qloo evidence.

**Key Change:** Programme Bet now receives measured Qloo evidence for both compatibility and reach.

---

## How Two-Sided Evidence Works

### A. Current-Audience Compatibility

**Source:** `mean_affinity` from ranked cohort's Qloo scoring call

**What it measures:** How strongly the candidate cohort's members are culturally adjacent to the existing programme

**Calculation:** Mean affinity of qualifying members (members above Medium band 0.5)

**Evidence:** Backed by Qloo `/v2/insights` scoring call

**Band thresholds:**
- High: ≥ 0.6
- Medium: ≥ 0.5
- Low: < 0.5

### B. Adjacent-Cohort Reach

**Source:** `qualifying_members / total_members` ratio

**What it measures:** What fraction of the cohort's members reach the target audience

**Calculation:** Count of members above Medium band / total members

**Evidence:** Backed by same Qloo `/v2/insights` scoring call

**Band thresholds:**
- High: ≥ 0.5 (50%+ members clear Medium)
- Medium: ≥ 0.3 (30%+ members clear Medium)
- Low: < 0.3

---

## Architecture Consistency

### No New Qloo Endpoints

Both signals come from existing Qloo evidence:
- Compatibility: `mean_affinity` from `CohortScore`
- Reach: `qualifying_members` count from `CandidateCohort`

### No New Qloo Calls

The two-sided evaluation uses the same scoring calls already made for cohort ranking. No additional Qloo API calls required.

### Budget Respect

The two-sided evaluation adds zero additional Qloo calls. It reuses existing scoring evidence.

---

## Runtime Integration

### Updated `routes.py`

```python
# Build two-sided evidence from ranked cohorts
compatibility_scores = {}
reach_scores = {}
compatibility_bands = {}
reach_bands = {}
compatibility_call_ids = {}
reach_call_ids = {}

for cohort in state.ranked:
    cid = cohort.cohort_id
    score = cohort.score

    # A. Compatibility: mean_affinity from Qloo scoring
    if score and score.mean_affinity is not None:
        compatibility_scores[cid] = score.mean_affinity
        compatibility_bands[cid] = (
            "High" if score.mean_affinity >= 0.6
            else "Medium" if score.mean_affinity >= 0.5
            else "Low"
        )
        compatibility_call_ids[cid] = score.call_id or ""

    # B. Reach: qualifying members ratio
    total = len(cohort.members) if cohort.members else 0
    qualifying = len(cohort.qualifying_members) if cohort.members else 0
    if total > 0:
        reach_ratio = qualifying / total
        reach_scores[cid] = reach_ratio
        reach_bands[cid] = (
            "High" if reach_ratio >= 0.5
            else "Medium" if reach_ratio >= 0.3
            else "Low"
        )
        reach_call_ids[cid] = score.call_id if score and score.call_id else ""

programme_bet = build_programme_bet(
    ...
    compatibility_scores=compatibility_scores,
    reach_scores=reach_scores,
    compatibility_bands=compatibility_bands,
    reach_bands=reach_bands,
    compatibility_call_ids=compatibility_call_ids,
    reach_call_ids=reach_call_ids,
    rejected_cohorts=state.rejected,
)
```

---

## Programme Bet Output

```json
{
  "primary": {
    "domain": "movie",
    "cohort_name": "Classic Hollywood",
    "mean_affinity": 0.72,
    "member_count": 5,
    "call_id": "abc123"
  },
  "two_sided_signals": {
    "current_audience_compatibility": 0.72,
    "adjacent_cohort_reach": 0.6,
    "compatibility_band": "High",
    "reach_band": "High",
    "compatibility_call_id": "abc123",
    "reach_call_id": "abc123"
  },
  "rejected_candidates": [
    {
      "cohort_id": "urn:entity:book:domain_group:1",
      "domain": "urn:entity:book",
      "reason": "weak_evidence",
      "detail": "Only 1 member above Medium"
    }
  ],
  "why": "...",
  "falsification_condition": "..."
}
```

---

## Tests

**Status:** ✅ 9 tests pass

**Tests:**
1. Basic Programme Bet creation
2. Two-sided evidence populated
3. Two-sided signals None when no evidence
4. Rejected candidates included
5. Geography signal included
6. Falsification condition included
7. to_dict() includes two-sided signals
8. No cohorts returns None
9. Deterministic behavior

---

## Frontend Display

**Status:** ✅ UPDATED

The ProgrammeBet component now displays:
- Primary recommendation
- Two-sided evaluation (compatibility + reach)
- Band badges (High/Medium/Low)
- Runner-up
- Rejected candidates
- Falsification condition

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE