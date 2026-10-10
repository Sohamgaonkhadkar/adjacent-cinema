# M12.3: Evaluation Integrity Lock

**Date:** 2026-10-07
**Status:** COMPLETE

---

## Fixes Applied

### 1. Identical Film Candidate Universe ✅

**Problem:** M12.2 compared baseline candidates from a curated universe against unrestricted Qloo candidates from Qloo's entire database.

**Fix:** Built a common 53-film universe. Both systems must score only films from this universe.

**Result:** Qloo returns 0 candidates from the common universe. Qloo's film recommendations come from its own database (different films than the curated universe).

**Interpretation:** The two systems operate on fundamentally different film databases. Experiment A (film-space comparison) is not meaningful because the universes don't overlap.

### 2. Provenance Separated from Evidence ✅

**Before:** "Evidence-supported" = has Qloo call ID
**After:** Two separate fields:
- `retrieval_provenance`: Qloo call/entity/cohort exists
- `cultural_evidence`: interpretable relationship exists (affinity ≥ 0.7 AND qualifying_members ≥ 3)

### 3. Entity-Level Actionability ✅

**Before:** Domain-level scoring (e.g., "artist = ACTIONABLE")
**After:** Entity-level scoring with:
- RELEVANCE (0-2): based on entity affinity
- PROGRAMMABILITY (0-2): based on domain + qualifying members
- EVIDENCE (0-2): based on provenance + cultural evidence
- Threshold: ≥ 5 = ACTIONABLE, 3-4 = PLAUSIBLE, ≤ 2 = REJECT

---

## Independent Sanity Check

**Candidates audited:** 15
**Agreement:** 15/15 (100%)

All algorithmic classifications agreed with manual classification.

---

## Venue Labelling

| Context | Type | Classification Basis |
|---------|------|---------------------|
| Prince Cinema | INDEPENDENT | Independent repertory cinema |
| Genesis Cinema | INDEPENDENT | Independent community cinema |
| Ritzy Picturehouse | CHAIN | Part of Picturehouses chain |
| Phoenix Oxford | CHAIN | Part of Picturehouses chain |
| Duke of York's | CHAIN | Part of Picturehouses chain |

**Independent:** 2 contexts
**Chain:** 3 contexts

---

## Key Finding

**Qloo's film candidates come from a different database than the curated universe.**

This means:
- Experiment A (film-space Jaccard) cannot be computed meaningfully
- The stronger claim comes from Experiment B: Qloo can return non-film entities that a film-only system cannot represent

---

**Report Generated:** 2026-10-07
**Status:** COMPLETE