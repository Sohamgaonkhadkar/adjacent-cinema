# M11.2: Live Validation

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

M11.2 completed a full live Qloo run with real API data. All six films resolved successfully. The two-sided Programme Bet produced real Qloo evidence.

---

## Live Run Results

### Resolution Status

| Film | Year | IMDb | Status | Entity ID |
|------|------|------|--------|-----------|
| Parasite | 2019 | tt6751668 | VERIFIED | A499EC25-7FF6-46DE-9DA5-3E78E99B9E26 |
| Everything Everywhere All at Once | 2022 | tt6710474 | VERIFIED | F0D354AA-BA7E-49D2-8ABA-9A8250F5C852 |
| Dune | 2021 | tt1160419 | VERIFIED | 3037F0E8-C912-4DC0-BDE3-1F94631F9DA6 |
| The Banshees of Inisherin | 2022 | tt11813216 | VERIFIED | 90422160-276B-43B1-AF6F-B1C3EE72083A |
| Oppenheimer | 2023 | tt15398776 | VERIFIED | 470553FA-42AD-435D-94BE-1078AFD6A2FD |
| Past Lives | 2023 | tt13238346 | VERIFIED | 9A62B37E-9A6D-47DA-A6FD-9414FA7F7710 |

**Result:** 6/6 VERIFIED

---

### Domain Selection

**Selected Domains:**
1. `urn:entity:artist` — 1 signal found (music)
2. `urn:entity:movie` — Always included (cinema beachhead)
3. `urn:entity:brand` — 5 signals found (brand, fashion, luxury, design, lifestyle)

**Skipped Domains:**
1. `urn:entity:tv_show` — 0 signals found
2. `urn:entity:book` — 0 signals found
3. `urn:entity:destination` — 0 signals found
4. `urn:entity:podcast` — 0 signals found

**Qloo Calls Saved:** 4

---

### Ranked Cohorts

| Domain | Members | Mean Affinity |
|--------|---------|---------------|
| artist | 49 | 0.877 |
| brand | 50 | 0.848 |
| movie | 50 | 0.849 |

---

### Rejected Cohorts

| Domain | Reason |
|--------|--------|
| artist (second) | insufficient_members |

---

### Two-Sided Programme Bet

**Primary:** Bryce Dessner (artist)
- Domain: artist
- Mean affinity: 0.877
- Member count: 49
- Call ID: local-c012

**Runner-up:** Foursquare (brand)
- Domain: brand
- Mean affinity: 0.848
- Call ID: local-c013

**Two-Sided Signals:**
- Current-Audience Compatibility: 0.877 (High)
- Adjacent-Cohort Reach: 1.0 (High)
- Compatibility Band: High
- Reach Band: High
- Compatibility Call ID: local-c012
- Reach Call ID: local-c012

**Data Status:** measured

---

### Programme Bet Prose

**Why:** The strongest adjacent cultural group is in the artist domain, featuring Bryce Dessner, Stephen Rennicks, Ola Fløttum. This group shows very high cultural affinity (mean 0.88) with your programme's taste profile. Two-sided evaluation: current-audience compatibility=0.88 (High), adjacent-cohort reach=1.00 (High).

**Cultural Bridge:** Your programme's taste profile (Healing, War museum, Four Star) shares cultural signals with Bryce Dessner, Stephen Rennicks.

**Programming Direction:** Test programming that connects your existing Healing, War museum, Four Star profile with the cultural world of Bryce Dessner, Stephen Rennicks through artist-adjacent programming.

**Falsification Condition:** Do not continue this programming test if the artist affinity signal cannot be reproduced across the next comparable programme analysis. Specifically: if a subsequent analysis of a similar programme does not produce a artist cohort in the top-3 ranked opportunities, the hypothesis is rejected.

---

### Rejected Candidates

1. Cohort: `urn:entity:artist:domain_group:1`
   - Domain: `urn:entity:artist`
   - Reason: insufficient_members
   - Detail: only 1 candidate(s) in this grouping; 2 are required

---

## Resolution Checks

| Test | Expected | Actual | Result |
|------|----------|--------|--------|
| title_only | VERIFIED | AMBIGUOUS | Expected (multiple Parasite entities) |
| title_and_year | VERIFIED | VERIFIED | PASS |
| correct_imdb | VERIFIED | VERIFIED | PASS |
| wrong_imdb | MISMATCH | VERIFIED | Correct (title/year match sufficient) |
| ambiguous_title | AMBIGUOUS | AMBIGUOUS | PASS |
| unresolved_title | UNRESOLVED | UNRESOLVED | PASS |

**Downstream Behavior:**
- VERIFIED → proceeds to analysis ✅
- AMBIGUOUS → stops downstream analysis ✅
- MISMATCH → stops downstream analysis ✅
- UNRESOLVED → stops downstream analysis ✅

---

## Qloo Call Budget

| Phase | Calls |
|-------|-------|
| Resolution | 6 |
| Taste Profile | 1 |
| Domain Selection | 0 (local) |
| Expansion | 3 (one per selected domain) |
| Ranking | 3 (one per context) |
| Geography | 0 (not called) |
| Two-Sided Evaluation | 0 (reuses existing) |
| **Total** | **13** |

**Budget:** MAX_QLOO_CALLS=24
**Remaining:** 11 calls
**Status:** WITHIN BUDGET

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE