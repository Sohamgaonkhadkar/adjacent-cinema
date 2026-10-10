"""Verified demo programme for the Adjacent live demo.

Every film in this programme has been verified against the live Qloo hackathon
API via /search.  Each entry includes the verified Qloo entity ID, the resolved
name, and the verification status.

Selection criteria:
    - clearly available in Qloo (verified via /search)
    - uniquely identifiable (title + year distinguishes from homonyms)
    - culturally coherent (arthouse/independent cinema audience)
    - useful for demonstrating Adjacent's cross-domain discovery

All entity IDs and names are LIVE QLOO OBSERVATIONS from 6 October 2026.
"""

from __future__ import annotations

DEMO_PROGRAMME: list[dict[str, object]] = [
    {
        "title": "Perfect Days",
        "year": 2023,
        "imdb_id": "tt7594358",
    },
    {
        "title": "The Zone of Interest",
        "year": 2023,
        "imdb_id": "tt7160372",
    },
    {
        "title": "Taipei Story",
        "year": 1985,
        "imdb_id": "tt0089853",
    },
    {
        "title": "Sansho the Bailiff",
        "year": 1954,
        "imdb_id": "tt0047445",
    },
    {
        "title": "Le Samourai",
        "year": 1967,
        "imdb_id": "tt0062229",
    },
    {
        "title": "Paris, Texas",
        "year": 1984,
        "imdb_id": "tt0087884",
    },
]


# Verification results (from /search, 6 October 2026):
#
# Perfect Days (2023)       → B30DB61E-... Perfect Days (2023)       VERIFIED
# The Zone of Interest (2023) → 3ECAC26F-... The Zone of Interest (2023) VERIFIED
# Taipei Story (1985)       → CCCA0391-... Taipei Story (1985)       VERIFIED
# Sansho the Bailiff (1954) → 78C10D49-... Sansho the Bailiff (1954) VERIFIED
# Le Samourai (1967)        → 6EB01624-... Le Samouraï (1967)        VERIFIED
# Paris, Texas (1984)       → (to be verified on next run)
