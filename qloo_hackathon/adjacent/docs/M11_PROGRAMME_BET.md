# M11: Programme Bet Implementation

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

This report documents the upgrade of Programme Bet to a genuine two-sided decision layer.

**Key Change:** Programme Bet now evaluates both (A) cultural compatibility with existing programme AND (B) evidence of reaching the adjacent cohort.

---

## Previous Behavior

**Programme Bet was a prose wrapper:**
- Extracted top-ranked cohort
- Generated prose about the cohort
- No actual two-sided scoring
- No compatibility/reach evaluation
- No rejected candidates

**Problem:** Not a genuine decision layer. Just wrapped the top-ranked cohort in prose.

---

## New Behavior

**Two-sided scoring evaluates:**

### A. Current-Audience Compatibility
- Does the candidate remain culturally compatible with the existing programme?
- Uses Qloo insights to measure affinity between candidate and existing programme
- Reports compatibility score and Qloo band

### B. Adjacent-Cohort Reach
- Does the candidate have evidence of reaching the selected adjacent cohort?
- Uses Qloo insights to measure affinity between candidate and target cohort
- Reports reach score and Qloo band

### Rejected Candidates
- Documents why candidates were rejected
- Provides deterministic reasons
- Preserves evidence/call IDs

---

## Two-Sided Signals

| Signal | Description | Source |
|--------|-------------|--------|
| `current_audience_compatibility` | Affinity with existing programme | Qloo insights |
| `adjacent_cohort_reach` | Affinity with target cohort | Qloo insights |
| `compatibility_band` | Qloo band for compatibility | Qloo bands |
| `reach_band` | Qloo band for reach | Qloo bands |

---

## Example Output

For a programme with taste profile "Silent film, Slapstick, Physical comedy":

**Primary Recommendation:**
- Domain: `urn:entity:artist`
- Cohort: Classic Hollywood composers
- Mean Affinity: 0.72
- Current-Audience Compatibility: 0.65 (Medium)
- Adjacent-Cohort Reach: 0.78 (High)

**Runner-Up:**
- Domain: `urn:entity:movie`
- Cohort: Silent film directors
- Mean Affinity: 0.68

**Rejected Candidates:**
- `urn:entity:brand:tag_cluster:1` — Reason: `weak_evidence` (only 1 member above Medium)
- `urn:entity:book:domain_group:2` — Reason: `weak_evidence` (no members above Medium)

---

## Programme Bet Output

```json
{
  "primary": {
    "domain": "artist",
    "cohort_name": "Classic Hollywood composers",
    "mean_affinity": 0.72,
    "member_count": 5,
    "call_id": "abc123"
  },
  "runner_up": {
    "domain": "movie",
    "cohort_name": "Silent film directors",
    "mean_affinity": 0.68,
    "call_id": "def456"
  },
  "two_sided_signals": {
    "current_audience_compatibility": 0.65,
    "adjacent_cohort_reach": 0.78,
    "compatibility_band": "Medium",
    "reach_band": "High",
    "compatibility_call_id": "ghi789",
    "reach_call_id": "jkl012"
  },
  "why": "The strongest adjacent cultural group is in the artist domain...",
  "cultural_bridge": "Your programme's taste profile (Silent film, Slapstick)...",
  "geographic_signal": "Cultural affinity concentrates in London...",
  "programming_direction": "Test programming that connects your existing...",
  "falsification_condition": "Do not continue this programming test if...",
  "rejected_candidates": [
    {
      "cohort_id": "urn:entity:brand:tag_cluster:1",
      "domain": "urn:entity:brand",
      "reason": "weak_evidence",
      "detail": "1 of 3 members clear the Medium band (needs 2)"
    }
  ],
  "geography_call_id": "mno345",
  "data_status": "measured"
}
```

---

## Key Rules

1. **No attendance lift** — Do not invent attendance lift, conversion probability, revenue, or predicted ticket sales
2. **No predictions** — The final wording must remain a hypothesis to test, not a prediction
3. **Both sides required** — Both compatibility AND reach must clear Medium for a valid bet
4. **Evidence-based** — All scores come from measured Qloo evidence
5. **Deterministic** — Same inputs → same outputs every time

---

## Implementation

**File:** `backend/app/domain/programme_bet.py`

**Key Changes:**
- Added `current_audience_compatibility` field
- Added `adjacent_cohort_reach` field
- Added `compatibility_band` field
- Added `reach_band` field
- Added `rejected_candidates` field
- Added `compatibility_call_id` field
- Added `reach_call_id` field
- Updated `to_dict()` to include two-sided signals

---

## Benefits

1. **Genuine decision layer** — Not just a prose wrapper
2. **Two-sided evaluation** — Both compatibility AND reach
3. **Evidence-based** — All scores from measured Qloo evidence
4. **Auditable** — Every decision has explicit reasons
5. **Hypothesis, not prediction** — Remains a testable hypothesis

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE