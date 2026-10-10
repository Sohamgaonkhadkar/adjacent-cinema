# M11.3: Decision Integrity

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Issue

Programme Bet "compatibility" and "reach" were both derived from the same Qloo scoring call, but labeled as independent measures.

---

## Fix

Renamed fields to accurately describe what they measure:

### Before (M11.2)
- `current_audience_compatibility` — "how strongly the candidate fits the existing programme"
- `adjacent_cohort_reach` — "how strongly the candidate connects to the target cohort"

**Problem:** Both derived from `mean_affinity` and `qualifying_members` from the same Qloo call. "Reach" was misleading — it's not audience reach, it's cohort breadth.

### After (M11.3)
- `programme_adjacency` — "mean affinity of cohort members against programme taste profile"
- `cohort_breadth` — "fraction of cohort members above Medium affinity threshold"

**Key Change:** Methodology note now explains both dimensions use the same Qloo call but measure different aspects:
- Adjacency measures STRENGTH of the signal
- Breadth measures COVERAGE of the signal

---

## What Each Dimension Measures

### Programme Adjacency (Dimension A)

**Definition:** Mean affinity of cohort members against programme taste profile

**Source:** Qloo `/v2/insights` scoring call — `mean_affinity` field

**Interpretation:** How culturally close the cohort is to the programme

**Band thresholds:**
- High: ≥ 0.6
- Medium: ≥ 0.5
- Low: < 0.5

### Cohort Breadth (Dimension B)

**Definition:** Fraction of cohort members above Medium affinity threshold

**Source:** Same Qloo `/v2/insights` call — `qualifying_members / total_members`

**Interpretation:** How much of the cohort clears the quality bar

**Band thresholds:**
- High: ≥ 0.5 (50%+ members clear Medium)
- Medium: ≥ 0.3 (30%+ members clear Medium)
- Low: < 0.3

---

## Methodology Note

Both dimensions use the SAME Qloo scoring call but measure different aspects:
- Programme adjacency measures STRENGTH of the cultural signal
- Cohort breadth measures COVERAGE of the cultural signal

This is scientifically defensible because:
1. Strength and coverage are genuinely distinct concepts
2. Both come from measured Qloo evidence
3. Neither claims to be an independent audience reach measurement
4. The methodology is transparent about what each number represents

---

## Changes Made

### ProgrammeBet Model
- `current_audience_compatibility` → `programme_adjacency`
- `adjacent_cohort_reach` → `cohort_breadth`
- `compatibility_band` → `adjacency_band`
- `reach_band` → `breadth_band`
- `compatibility_call_id` → `adjacency_call_id`
- `reach_call_id` → `breadth_call_id`
- Added `methodology_note` to `two_sided_signals`

### JSON Export
- Updated field names
- Added methodology note explaining what each dimension measures

### Frontend
- Updated labels to "Programme Adjacency" and "Cohort Breadth"
- Added descriptive subtitles
- Added methodology note display

### Documentation
- Removed "reach" claims that implied independent audience measurement
- Replaced with scientifically accurate descriptions

---

## Verification

### Live Run Results

**Programme Bet:**
- Primary: Bryce Dessner (artist)
- Programme adjacency: 0.877 (High)
- Cohort breadth: 1.0 (High)
- Adjacency call ID: local-c018
- Breadth call ID: local-c018

**Key Observation:** Both call IDs are the same (`local-c018`), confirming both dimensions use the same Qloo call.

---

## Conclusion

The Programme Bet now has scientifically accurate labels that describe what each dimension actually measures. No unsupported "reach" claims remain.

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE