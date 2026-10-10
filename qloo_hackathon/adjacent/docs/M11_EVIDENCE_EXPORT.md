# M11: Evidence + Export Layer Implementation

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

This report documents the evidence + export layer for Adjacent.

**Key Change:** Every displayed quantitative claim is traceable to its source call or deterministic transformation.

---

## Evidence Components

### 1. Programme Resolution Evidence
- Resolution status for every film
- Verification notes
- Call IDs
- Data status

### 2. Taste DNA Evidence
- Tags scored from Qloo insights
- Affinity scores
- Popularity scores
- Qloo bands

### 3. Selected Expansion-Domain Reasons
- Which domains were selected
- Why each domain was selected
- Which domains were skipped
- Why each domain was skipped
- Qloo calls saved

### 4. Cohort Ranking Evidence
- Ranked cohorts with scores
- Rejected cohorts with reasons
- Context IDs
- Scoring call IDs

### 5. Geography Evidence
- Heatmap cells
- Geographic signal
- Call IDs

### 6. Programme Bet Evidence
- Primary recommendation
- Runner-up
- Rejected candidates with reasons
- Two-sided signals (compatibility + reach)
- Falsification condition

---

## Evidence Export

### JSON Export

Every run produces a complete JSON export with:

```json
{
  "run_id": "live-demo",
  "data_status": "measured",
  "programme": [...],
  "resolution": {
    "resolved": [...],
    "unresolved": [...],
    "verdict": {...},
    "call_ids": [...]
  },
  "taste_profile": {
    "tags": [...],
    "verdict": {...},
    "call_id": "..."
  },
  "domain_selection": {
    "selected_domains": [...],
    "skipped_domains": [...],
    "selections": [...],
    "qloo_calls_saved": 5
  },
  "expansion": {
    "candidates_by_domain": {...},
    "call_ids": {...}
  },
  "cohorts": {
    "constructed": [...],
    "ranked": [...],
    "rejected": [...]
  },
  "geography": {
    "cells": [...],
    "verdict": {...},
    "call_id": "..."
  },
  "programme_bet": {
    "primary": {...},
    "runner_up": {...},
    "two_sided_signals": {...},
    "rejected_candidates": [...],
    "why": "...",
    "falsification_condition": "..."
  },
  "evidence": {
    "trace_rows": [...],
    "findings": [...],
    "gates": {...}
  },
  "provenance": {
    "numbers_displayed": 42,
    "qloo_call_backed": 38,
    "other_backed": 4,
    "unverified": []
  },
  "stop": {
    "reason": "complete",
    "message": "..."
  }
}
```

---

## Traceability

Every displayed number is traceable to:

1. **Qloo call** — Backed by a Qloo API call
2. **Deterministic transformation** — Computed from Qloo data
3. **Input data** — From the programme input
4. **Fixture data** — From the fixture file (if applicable)

---

## Frontend Evidence Display

The frontend must expose:

1. **Resolution evidence** — Status, verification notes, call IDs
2. **Taste DNA evidence** — Tags, affinities, bands
3. **Domain selection reasons** — Selected/skipped with reasons
4. **Cohort ranking evidence** — Ranked/rejected with reasons
5. **Geography evidence** — Heatmap cells, signal
6. **Programme bet evidence** — Two-sided signals, rejected candidates
7. **Full trace** — All Qloo call IDs
8. **Data status** — measured/fixture
9. **Stop reason** — Why the run stopped

---

## Copy as JSON

The frontend provides a "Copy as JSON" action that exports:

1. Complete typed run result
2. Full provenance
3. All evidence
4. All call IDs
5. Data status
6. Stop reason

---

## Implementation

**Files:**
- `backend/app/evidence.py` — Evidence gate and verdicts
- `backend/app/domain/ledger.py` — Provenance ledger
- `backend/app/runner.py` — JSON export
- `frontend/components/` — Evidence display components

---

## Benefits

1. **Complete traceability** — Every number traceable to source
2. **Auditable** — Full evidence for every claim
3. **Exportable** — Copy as JSON with complete provenance
4. **Trustworthy** — No hidden transformations
5. **Reproducible** — Same inputs → same outputs

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE