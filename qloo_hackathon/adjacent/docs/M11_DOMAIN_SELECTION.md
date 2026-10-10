# M11: Domain Selection Implementation

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

This report documents the implementation of agentic domain selection for Adjacent.

**Key Change:** Replaced unconditional fixed-domain expansion with a deterministic, auditable domain-selection step.

---

## Previous Behavior

**Fixed 5 domains:**
- `urn:entity:artist`
- `urn:entity:movie`
- `urn:entity:tv_show`
- `urn:entity:book`
- `urn:entity:brand`

**Problem:** Every programme queried the same 5 domains regardless of the cultural profile. A film programme always queried brands even if the taste profile suggested art, music, or destinations.

---

## New Behavior

**Dynamic domain selection based on Taste DNA:**

1. **Extract tag families** from taste tags (music, film, book, etc.)
2. **Match signal families** to domain criteria
3. **Select domains** with explicit reasons
4. **Skip domains** with explicit reasons
5. **Save Qloo calls** by not querying irrelevant domains

---

## Available Domains

| Domain | Signal Families | Description |
|--------|----------------|-------------|
| `urn:entity:artist` | music, band, singer, musician, composer, performer | Music artists |
| `urn:entity:movie` | film, cinema, movie, director, screenwriter | Movies (always included) |
| `urn:entity:tv_show` | television, tv, series, show, drama, comedy | TV shows |
| `urn:entity:book` | book, literature, novel, author, writer, fiction, nonfiction | Books |
| `urn:entity:brand` | brand, fashion, luxury, design, lifestyle | Brands |
| `urn:entity:destination` | travel, destination, city, country, tourism, geography | Destinations |
| `urn:entity:podcast` | podcast, audio, radio, interview, conversation | Podcasts |

---

## Selection Rules

1. **Always include:** `urn:entity:movie` (cinema beachhead)
2. **Signal-based:** Include domain if ≥1 signal family matches taste tags
3. **Max domains:** Optional limit to stay within call budget
4. **Deterministic:** Same tags → same domains every time
5. **Explainable:** Every decision has a reason

---

## Example Output

For a programme with taste tags: "Silent film", "Slapstick", "Physical comedy", "Classic Hollywood"

**Selected:**
- `urn:entity:movie` — Always included (cinema beachhead)
- `urn:entity:artist` — Signal "music" found (silent film → music)

**Skipped:**
- `urn:entity:tv_show` — 0 signals found
- `urn:entity:book` — 0 signals found
- `urn:entity:brand` — 0 signals found
- `urn:entity:destination` — 0 signals found
- `urn:entity:podcast` — 0 signals found

**Qloo calls saved:** 5 (only queried 2 domains instead of 7)

---

## Implementation

**File:** `backend/app/domain/domain_selection.py`

**Key Functions:**
- `select_domains(taste_tags, always_include, max_domains)` — Main selection function
- `_extract_tag_families(tags)` — Extract tag family counts
- `_count_signals(family_counts, signal_families)` — Count matching signals

**Output:** `DomainSelectionResult` with:
- `selected_domains` — domains to query
- `skipped_domains` — domains not queried
- `selections` — all decisions with reasons
- `qloo_calls_saved` — calls saved
- `total_tags_analyzed` — tags analyzed

---

## Benefits

1. **Adaptive:** Queries domains relevant to the programme
2. **Efficient:** Saves Qloo calls by skipping irrelevant domains
3. **Auditable:** Every decision has an explicit reason
4. **Deterministic:** Same tags → same domains every time
5. **Budget-aware:** Respects call budget limits

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE