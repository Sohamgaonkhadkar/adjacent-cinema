# M12.1: Baseline Design

**Date:** 2026-10-07
**Status:** COMPLETE

---

## Baseline Type

**Content similarity using metadata only.**

The baseline does NOT use Qloo. It uses only information available from ordinary film metadata.

---

## Fields Used

| Field | Weight | Method |
|-------|--------|--------|
| genre | 0.4 | Jaccard overlap of genre sets |
| country | 0.2 | Exact match |
| decade | 0.15 | Exact match |
| style | 0.25 | Exact match |

**Total:** 1.0

---

## How It Works

1. For each programme film, look up metadata (genre, country, decade, style)
2. For each candidate in the pool, compute similarity against each programme film
3. Take the maximum similarity score
4. Rank candidates by similarity
5. Return top-K

---

## What the Baseline Can Do

- Find films with similar genres
- Find films from the same country
- Find films from the same decade
- Find films with similar style labels

## What the Baseline Cannot Do

- Discover non-film cultural connections (books, artists, brands)
- Find cross-domain cultural adjacency
- Identify audience taste beyond film metadata
- Access Qloo's cultural graph

---

## Candidate Pool

The baseline uses a pool of ~60 candidate films spanning:
- Horror/cult (for repertory programmes)
- Arthouse (for contemporary programmes)
- Japanese cinema (for programmes with Japanese films)
- French cinema (for European arthouse)
- UK social realism (for British programmes)
- Classic arthouse (for archival programmes)
- Family/comedy (for mixed programmes)

---

## Key Property

**The baseline is genuinely independent of Qloo.**

It uses only: title, year, genre, country, language, style — fields that would be available in any film database.

---

**Report Generated:** 2026-10-07
**Status:** COMPLETE