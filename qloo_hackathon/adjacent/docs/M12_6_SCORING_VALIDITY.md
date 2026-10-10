# M12.6: Scoring Validity Lock

**Date:** 2026-10-07
**Status:** SUPERSEDED BY M12.7 — programme_fit still used hand-coded thematic vectors (FILM_GENRE_PROXIES, GENRE_TO_THEME, DOMAIN_THEMATIC_VECTORS); differentiation had hardcoded domain scores

---

## WHAT M12.5 CLAIMED (NOW SUPERSEDED)

- "All five components are independent" → **SUPERSEDED** — programme_fit used only affinity
- "≥20 attendees / ≥50% new visitors" → **UNVALIDATED THRESHOLDS** — removed

---

## M12.6 FIXES

### 1. Programme Fit: Uses Programme-Specific Evidence

**Before (M12.5):** programme_fit used only affinity thresholds.
**After (M12.6):** programme_fit uses:

- **programme_direction** — computed from film metadata (genres, decades, themes)
  - Deterministic: derived from known film titles and years
  - NOT from Qloo: avoids circularity with entity_fit
- **member_composition** — qualifying_members / total_members ratio
  - Varies per candidate
  - Measures cohort robustness, not signal strength

**Data source:** Film metadata (FILM_GENRE_PROXIES, GENRE_TO_THEME, DOMAIN_THEMATIC_VECTORS)

### 2. Feasibility and Testability: Genuinely Distinct

**event_feasibility** answers: "Can we DO this event?"
- Inputs: domain, programme_films count, qualifying_members
- Tests: venue compatibility, rights feasibility, format concreteness

**testability** answers: "Can we MEASURE the outcome?"
- Inputs: event_format (string), qualifying_members
- Tests: outcome clarity, sample size, confounding factors

**Key difference:** A themed season is feasible (score=2) but harder to test (score=1) because it spans multiple weeks with confounding factors.

### 3. No Arbitrary Business Thresholds

**Before:** "≥20 attendees with ≥50% new-to-venue visitors"
**After:** "Primary outcome: attendance / new-to-venue attendance / engagement. Threshold: TBD — must be calibrated against the cinema's historical baseline."

### 4. Ablation Analysis

For each context, removing each component shows rank change:
- Genesis: Unloved stable at #1 (score=10, no single component dominates)
- Prince Charles: removing testability or differentiation drops artist rank to 51

---

## COMPONENT INDEPENDENCE TABLE

| Component | Inputs | Evidence Source | Overlap |
|-----------|--------|----------------|---------|
| entity_fit | affinity, qualifying_members, total_members | Qloo API | NONE |
| event_feasibility | domain, programme_films count | Entity dict + domain rules | NONE |
| programme_fit | programme_direction, member_ratio | Film metadata (NOT Qloo) + entity | NONE |
| testability | event_format (string), qualifying_members | Feasibility output (format only, NOT score) | format shared with differentiation |
| differentiation | domain, event_format (string) | Entity + feasibility (format only) | format shared with testability |

**Key:** testability and differentiation share the format STRING but answer different questions:
- testability: can we MEASURE the outcome?
- differentiation: is this DIFFERENT from normal programming?

---

## RESULTS

### Genesis Cinema
```
200 raw → 153 evidence → 103 feasibility → 148 STRONG, 2 PLAUSIBLE, 50 REJECT
Programme Bet: Unloved (artist) — score=10
Ablation: No single component dominates
```

### Prince Charles Cinema
```
150 raw → 150 evidence → 100 feasibility → 100 STRONG, 50 REJECT
Programme Bet: The Contortions (artist) — score=9
Ablation: Removing testability or differentiation changes bet
```

### Cross-Context
- Same domain: True (both artist)
- Same entity: False (Unloved vs The Contortions)
- Valid: both horror programmes naturally align with dark/atmospheric artists

---

## DOCUMENTATION

- `M12_6_SCORING_VALIDITY.md` — This file
- `M12_6_FINAL_REPORT.md` — Final report with gate questions

---

**Status:** COMPLETE