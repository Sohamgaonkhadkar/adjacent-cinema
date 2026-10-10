# M11: Resolution Contract Implementation

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

This report documents the input + resolution contract for Adjacent.

**Key Change:** Formalized the input contract and implemented disambiguation path.

---

## Input Contract

### Required Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ | Film title |
| `year` | int | Optional | Film year |
| `imdb_id` | string | Optional | IMDb ID (stronger identity signal) |

### Optional Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `city` | string | Optional | City for geographic analysis |
| `cinema_name` | string | Optional | Cinema/venue name |

---

## Resolution States

### VERIFIED
- **Condition:** IMDb ID match OR (exact title + exact year)
- **Behavior:** Entity proceeds to analysis
- **Evidence:** Explicit verification notes

### AMBIGUOUS
- **Condition:** Partial title match OR year mismatch
- **Behavior:** Entity does NOT proceed to analysis
- **Evidence:** Explicit ambiguity notes
- **User Action:** Show problem visibly, provide disambiguation path

### MISMATCH
- **Condition:** IMDb ID mismatch OR (title match + year mismatch)
- **Behavior:** Entity does NOT proceed to analysis
- **Evidence:** Explicit mismatch notes
- **User Action:** Show problem visibly, provide correction path

### UNRESOLVED
- **Condition:** No Qloo entity found
- **Behavior:** Entity does NOT proceed to analysis
- **Evidence:** Explicit unresolved notes
- **User Action:** Show problem visibly, suggest adding more info

---

## Resolution Rules

### IMDb Agreement (Strong Evidence)
- Same IMDb → VERIFIED
- Different IMDb → MISMATCH

### Year Agreement
- Exact year match required for VERIFIED
- Close year NOT sufficient for VERIFIED
- Year mismatch with conflicting evidence → MISMATCH or AMBIGUOUS

### Title Agreement
- Exact normalized title required for VERIFIED
- Partial substring matches NOT enough for VERIFIED
- Alternate titles may be used only when source establishes relationship

---

## Disambiguation Path

When resolution is AMBIGUOUS or MISMATCH:

1. **Show the problem visibly** — Display the issue to the user
2. **Preserve the evidence** — Keep all verification notes
3. **Provide exactly one clear correction path** — Suggest how to fix
4. **Never silently guess** — Do not pass unverified entities downstream
5. **Never pass unverified entities into downstream Qloo analysis**

---

## Example Resolution

### Input
```json
{
  "title": "The Dark Knight",
  "year": 2008,
  "imdb_id": "tt0468569"
}
```

### Resolution
```json
{
  "input_title": "The Dark Knight",
  "input_year": 2008,
  "input_external_id": "tt0468569",
  "qloo_entity_id": "12345",
  "qloo_name": "The Dark Knight",
  "qloo_year": 2008,
  "match_status": "VERIFIED",
  "match_method": "external_id",
  "verification_notes": ["IMDb ID match"],
  "call_id": "abc123"
}
```

---

## Implementation

**Files:**
- `backend/app/resolution/contract.py` — Resolution contract models
- `backend/app/resolution/resolver.py` — Entity resolver
- `backend/app/live_runner.py` — Live pipeline with resolution

**Key Classes:**
- `MatchStatus` — VERIFIED, AMBIGUOUS, MISMATCH, UNRESOLVED
- `MatchMethod` — SEARCH, SEARCH_WITH_YEAR, EXTERNAL_ID
- `ResolvedEntity` — Resolution output with all fields

---

## Benefits

1. **Formalized contract** — Clear input/output specification
2. **Explicit states** — VERIFIED, AMBIGUOUS, MISMATCH, UNRESOLVED
3. **No silent guessing** — Never pass unverified entities downstream
4. **User-visible problems** — Show issues to user
5. **Disambiguation path** — Clear correction path

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE