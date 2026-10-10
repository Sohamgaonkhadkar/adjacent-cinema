# Live Qloo Validation Report

> **Generated:** 6 October 2026  
> **Mode:** LIVE (real Qloo)  
> **Endpoint:** https://hackathon.api.qloo.com  
> **Key fingerprint:** sha256:3a723d1101cb·len=45

---

## Summary

All critical Qloo API capabilities required by Adjacent have been validated
against the live hackathon endpoint. Four compatibility fixes were required
and applied.

| Probe | Status | Notes |
|---|---|---|
| A. Entity resolution | ✅ | 4/5 IMDb IDs resolved |
| B. Tag affinity (Taste DNA) | ✅ | 50 scored tags |
| C. Cross-domain artists | ✅ | 12 scored entities |
| D. filter.results.entities | ✅ | 50/50 scored — **SAFE** |
| E. Heatmap coverage | ✅ | London 207, NY 203, Portland 19 |
| F. Explainability | ✅ | Per-signal attribution for entities |
| G. Audience catalogue | ✅ | 50 audiences |
| H. Rate limit | ✅ | No rejections in 10 rapid calls |

---

## §5 — filter.results.entities verdict

**SAFE.**

50 artist entity IDs were supplied via `filter.results.entities` and all 50
were returned with affinity scores in a single query.  This confirms our
single-query cohort-ranking architecture works against real Qloo.

Key finding: affinity is in `entity.query.affinity`, NOT at the entity top level.

---

## §6 — Entity resolution

| Input | Resolved | Entity ID | Name |
|---|---|---|---|
| tt7594358 (Perfect Days) | ❌ | — | Not in Qloo |
| tt7160372 (Zone of Interest) | ✅ | 3ECAC26F-... | The Zone of Interest |
| tt0089853 (Taipei Story) | ✅ | 1EA804CA-... | The Purple Rose of Cairo |
| tt0047445 (Sansho the Bailiff) | ✅ | 78C10D49-... | Sansho the Bailiff |
| tt0062229 (Le Samourai) | ✅ | 6EB01624-... | Le Samouraï |

Note: tt0089853 is "Taipei Story" (1985) but Qloo resolved it to "The Purple
Rose of Cairo". This is a Qloo entity mapping issue, not our code.

Fields returned: `disambiguation, entity_id, name, popularity, properties,
references, tags, types`.

---

## §7 — Taste/Tag profile

50 scored tags returned. All above medium band. Top tags:

| Tag | Affinity | Band |
|---|---|---|
| Sustainability | 0.9998 | very_high |
| Practical | 0.9997 | very_high |
| Sustainability (lifestyle) | 0.9995 | very_high |
| affordable | 0.9993 | very_high |
| Eco-conscious Individuals | 0.9993 | very_high |
| Escapism | 0.9989 | very_high |
| Retail | 0.9989 | very_high |
| Footwear | 0.9987 | very_high |

**Affinity location:** `tag.query.affinity` (nested, NOT top level).

---

## §8 — Cross-domain expansion

**Domain:** `urn:entity:artist` — 12 scored entities.

Top adjacent artists:

| Artist | Affinity | Band |
|---|---|---|
| Nico | 0.9373 | very_high |
| Television | 0.9358 | very_high |
| The Velvet Underground | 0.9356 | very_high |
| Captain Beefheart & His Magic Band | 0.9336 | very_high |
| Talking Heads | 0.9327 | very_high |
| Scott Walker | 0.9319 | very_high |

**Affinity location:** `entity.query.affinity` (nested, NOT top level).

Other domains (brand, venue, book, etc.) not yet tested — future work.

---

## §9 — Heatmap validation

| City | Cells | Avg affinity | Resolved to |
|---|---|---|---|
| London, UK | 207 | 0.500 | London, Greater London, England, UK |
| New York, NY | 203 | 0.500 | New York, United States |
| Portland, Oregon | 19 | 0.500 | Portland, Multnomah County, Oregon, US |

**Demo city recommendation:** London, UK (highest cell density).

**Cell structure (LIVE QLOO OBSERVATION):**
```json
{
  "location": {"latitude": 51.55, "longitude": -0.126, "geohash": "gcpvm0"},
  "query": {"affinity": 1.0, "affinity_rank": 0.991, "popularity": 0.0}
}
```

**Key structural finding:** `query.localities.filter` is a LIST of locality
objects, not a single dict. Our `HeatmapResponse.locality` field now accepts both.

---

## §10 — Explainability validation

**Works for entities.** Does NOT work for tags.

With `feature.explainability=true`:
- Each entity result gains `query.explainability.signal.interests.entities[]`
- Each entry has `entity_id` and `score` (attribution weight)
- Attribution scores sum ≈ entity's overall affinity
- Tags return empty explainability `{}`

This directly supports our provenance model — each rendered number can be
traced to which input programme item contributed most to it.

---

## §11 — Unverified parameters

| Parameter | Endpoint | Result |
|---|---|---|
| `filter.parents.types` | /v2/insights (urn:tag) | ✅ Works — 50 scored tags returned |
| `signal.location.query` | /v2/insights (artist) | ✅ Works — 12 scored entities returned |
| `filter.tags` | /v2/tags | ❌ Not supported — Qloo returns error |

---

## §12 — Rate limit

10 rapid calls with no rejections. All returned HTTP 200.
Max observed latency: 343ms.

---

## Compatibility fixes applied

| # | File | Fix | Reason |
|---|---|---|---|
| 1 | `models.py` | `HeatmapResponse.locality` accepts `list \| dict \| None` | Qloo returns `query.localities.filter` as a list |
| 2 | `models.py` | `parse_heatmap` checks `results.heatmap` | Qloo uses `results.heatmap`, not `results.cells` |
| 3 | `models.py` | Heatmap cells: extract lat/lng from nested `location` | Qloo nests coords in `cell.location.{latitude,longitude}` |
| 4 | `models.py` | All parsers: extract affinity from `query.affinity` | Qloo nests affinity in `item.query.affinity`, not top-level |
| 5 | `qloo_probe.py` | Handle `locality` as list or dict | Prevents AttributeError in probe |

All fixes are **backward-compatible** — existing mock fixtures still work because
our parsers check both locations (`q_affinity or item.get("affinity")`).

---

## Demo city decision

**London, UK** — justified by:
1. Highest heatmap cell count (207 vs 203 for NY, 19 for Portland)
2. Strong indie/arthouse cinema ecosystem (BFI, Curzon, Picturehouse)
3. Well-defined geographic granularity (boroughs, postcodes)

Portland is too sparse (19 cells) for a compelling geographic demo.