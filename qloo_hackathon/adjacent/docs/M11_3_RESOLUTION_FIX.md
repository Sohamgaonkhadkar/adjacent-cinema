# M11.3: Resolution Fix

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Issue

Wrong IMDb ID could still result in VERIFIED when title/year match.

**Example:** Parasite (2019) with wrong IMDb ID tt9999999 was VERIFIED.

---

## Fix

Updated `EntityResolver.resolve_item()` to verify external IDs via /entities endpoint.

### New Logic

1. Search by title/year → find candidate entity
2. If external ID supplied, also query /entities with external ID
3. Compare results:
   - Same entity → VERIFIED
   - Different entity → MISMATCH
   - External ID not found → MISMATCH (supplied ID doesn't exist in Qloo)
   - External ID query fails → VERIFIED (title/year match sufficient)

### Key Change

When external ID is supplied AND /entities returns no results (UNRESOLVED), the resolution now returns MISMATCH instead of VERIFIED.

**Rationale:** If a user supplies an IMDb ID that doesn't exist in Qloo, it's a data quality issue that should stop downstream analysis.

---

## Verification

### Test Results (Live Qloo)

| Test | Expected | Actual | Result |
|------|----------|--------|--------|
| title_only | AMBIGUOUS | AMBIGUOUS | PASS |
| title_and_year | VERIFIED | VERIFIED | PASS |
| correct_imdb | VERIFIED | VERIFIED | PASS |
| wrong_imdb | MISMATCH | MISMATCH | PASS |
| ambiguous_title | AMBIGUOUS | AMBIGUOUS | PASS |
| unresolved_title | UNRESOLVED | UNRESOLVED | PASS |

**Total:** 6/6 passed

---

## Downstream Behavior

| Status | Behavior |
|--------|----------|
| VERIFIED | Proceeds to analysis |
| AMBIGUOUS | Stops downstream analysis |
| MISMATCH | Stops downstream analysis |
| UNRESOLVED | Stops downstream analysis |

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE