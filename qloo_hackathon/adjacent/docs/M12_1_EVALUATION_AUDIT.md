# M12.1: Evaluation Audit

**Date:** 2026-10-07
**Status:** COMPLETE

---

## Problems Fixed

### 1. Baseline Rebuilt

**Before:** Hand-written title keyword classifier
**After:** Real metadata/content baseline using genre, country, decade, style similarity

**Baseline fields used:**
- genre (Jaccard overlap)
- country (exact match)
- decade (exact match)
- style (exact match)

**Baseline does NOT use:** Qloo, taste tags, affinity scores, or any Qloo-derived data.

### 2. Novelty Metric Replaced

**Before:** Word-level text Jaccard on generated prose (INVALID: 0.997)
**After:** Structural metrics:
- Jaccard@K (candidate overlap)
- Cross-domain unique discovery
- Non-overlapping opportunities
- Domain expansion
- Insufficiency rate

### 3. "Materially Different" Redefined

**Before:** "Qloo has a non-film domain" (built into product design)
**After:** Measured by Jaccard@K and cross-domain count

---

## Programme Context Audit

### VERIFIED_PROGRAMME (3 contexts)

| Venue | Source | Verification |
|-------|--------|--------------|
| Prince Charles Cinema | Scraped from live website 2026-10-07 | ✅ VERIFIED |
| ICA | From ICA website film listings | ✅ VERIFIED |
| ArtHouse Crouch End | From ArtHouse website | ✅ VERIFIED |

### PARTIAL_PROGRAMME_EVIDENCE (2 contexts)

| Venue | Source | Issue |
|-------|--------|-------|
| The Garden Cinema | Website but some retrospective titles | Partial |
| Genesis Cinema | Search results, not confirmed current | Partial |

### UNVERIFIED (5 contexts)

| Venue | Source | Issue |
|-------|--------|-------|
| Curzon Soho | Plausible but not scraped | Unverified |
| Picturehouse Central | Not scraped, chain venue | Unverified |
| BFI Southbank | Not scraped, national institution | Unverified |
| Phoenix Cinema Leicester | Not scraped | Unverified |
| Tyneside Cinema | Not scraped | Unverified |

---

## Venue Type Corrections

- **BFI Southbank:** National institution, NOT independent cinema
- **Picturehouse Central:** Chain venue (Cineworld-owned), NOT independent
- **Curzon Soho:** Chain venue, NOT independent
- **Prince Charles Cinema:** Independent repertory cinema ✅
- **ICA:** Institutional arts venue (supports independent film)
- **ArtHouse Crouch End:** Community arts venue ✅

---

## Invalid Results Superseded

The M12 result "average novelty = 0.997" is **INVALID** and **SUPERSEDED** by M12.1.

**Reason:** Used word-level text Jaccard on generated prose, which is not a meaningful information-gain metric.

**Historical report preserved at:** `docs/M12_FINAL_REPORT.md`

---

**Report Generated:** 2026-10-07
**Status:** COMPLETE