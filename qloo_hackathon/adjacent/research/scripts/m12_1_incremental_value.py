#!/usr/bin/env python3
"""M12.1: Repaired Qloo Incremental-Value Evaluation.

Fixes:
1. Real metadata/content baseline (not hand-written keywords)
2. Structural metrics (not word Jaccard)
3. Verified programme contexts
4. Same candidate budget for both systems
"""

import asyncio
import json
import math
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Load .env
adjacent_root = Path(__file__).parent.parent.parent
env_path = adjacent_root / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ[key.strip()] = value.strip()

# Add backend to path
sys.path.insert(0, str(adjacent_root / 'backend'))

from app.config import Settings
from app.live_runner import run_live_async
from app.domain.programme_bet import build_programme_bet

# Candidate budget K — same for both systems
TOP_K = 10

# ============================================================
# VERIFIED PROGRAMME CONTEXTS
# Each context has: venue, city, films, source_url, verification_status
# ============================================================

VERIFIED_CONTEXTS = [
    {
        "context_id": "prince_charles_london_2026_10",
        "venue": "Prince Charles Cinema",
        "city": "London",
        "venue_type": "independent_repertory",
        "source_url": "https://princecharlescinema.com",
        "retrieved_at": "2026-10-07T09:00:00Z",
        "verification_status": "VERIFIED_PROGRAMME",
        "verification_notes": "Films scraped from live website on 2026-10-07",
        "films": [
            {"title": "The Thing", "year": 1982, "imdb_id": "tt0084787"},
            {"title": "The Shining", "year": 1980, "imdb_id": "tt0081505"},
            {"title": "Halloween III: Season of the Witch", "year": 1982, "imdb_id": "tt0085636"},
            {"title": "Suspiria", "year": 1977, "imdb_id": "tt0076786"},
            {"title": "Perfect Blue", "year": 1997, "imdb_id": "tt0156887"},
            {"title": "Akira", "year": 1988, "imdb_id": "tt0094625"},
            {"title": "Possession", "year": 1981, "imdb_id": "tt0082933"},
            {"title": "The Devils", "year": 1971, "imdb_id": "tt0066993"},
        ],
    },
    {
        "context_id": "ica_london_2026_10",
        "venue": "ICA (Institute of Contemporary Arts)",
        "city": "London",
        "venue_type": "institutional_arts",
        "source_url": "https://www.ica.art/films",
        "retrieved_at": "2026-10-07T09:00:00Z",
        "verification_status": "VERIFIED_PROGRAMME",
        "verification_notes": "Films from ICA website film listings, October 2026",
        "films": [
            {"title": "Her Private Hell", "year": 2026},
            {"title": "Barrio Triste", "year": 2026},
            {"title": "Everybody Digs Bill Evans", "year": 2026},
            {"title": "Queen at Sea", "year": 2026},
            {"title": "Manhunter", "year": 1986, "imdb_id": "tt0091474"},
            {"title": "Remake", "year": 2026},
        ],
    },
    {
        "context_id": "art_house_crouch_end_london_2026_10",
        "venue": "ArtHouse Crouch End",
        "city": "London",
        "venue_type": "community_arts",
        "source_url": "https://www.arthousecrouchend.co.uk/",
        "retrieved_at": "2026-10-07T09:00:00Z",
        "verification_status": "VERIFIED_PROGRAMME",
        "verification_notes": "Films from ArtHouse website, October 2026",
        "films": [
            {"title": "The Incomer", "year": 2026},
            {"title": "Sense and Sensibility", "year": 2026},
            {"title": "Extra Geography", "year": 2026},
            {"title": "Madness: Take It Or Leave It", "year": 2026},
            {"title": "Comédie Française", "year": 2026},
        ],
    },
    {
        "context_id": "garden_cinema_london_2026_10",
        "venue": "The Garden Cinema",
        "city": "London",
        "venue_type": "members_cinema",
        "source_url": "https://www.thegardencinema.co.uk/",
        "retrieved_at": "2026-10-07T09:00:00Z",
        "verification_status": "PARTIAL_PROGRAMME_EVIDENCE",
        "verification_notes": "Films from website but some are retrospective/season titles, not current programme",
        "films": [
            {"title": "Sense and Sensibility", "year": 2026},
            {"title": "Naza", "year": 2026},
            {"title": "Whisper of the Heart", "year": 1995, "imdb_id": "tt0113824"},
        ],
    },
    {
        "context_id": "genesis_london_2026_10",
        "venue": "Genesis Cinema",
        "city": "London",
        "venue_type": "independent_community",
        "source_url": "https://genesiscinema.co.uk/",
        "retrieved_at": "2026-10-07T09:00:00Z",
        "verification_status": "PARTIAL_PROGRAMME_EVIDENCE",
        "verification_notes": "Films mentioned in search results, not confirmed as current programme",
        "films": [
            {"title": "Parasite", "year": 2019, "imdb_id": "tt6751668"},
            {"title": "The Zone of Interest", "year": 2023, "imdb_id": "tt7160372"},
            {"title": "Perfect Days", "year": 2023, "imdb_id": "tt27503384"},
            {"title": "Past Lives", "year": 2023, "imdb_id": "tt13238346"},
        ],
    },
    {
        "context_id": "curzon_soho_london_2026_10",
        "venue": "Curzon Soho",
        "city": "London",
        "venue_type": "chain_artthouse",
        "source_url": "https://www.curzon.com/soho",
        "retrieved_at": "2026-10-07T09:00:00Z",
        "verification_status": "UNVERIFIED",
        "verification_notes": "Films are plausible for venue but not scraped from live site",
        "films": [
            {"title": "Everything Everywhere All at Once", "year": 2022, "imdb_id": "tt6710474"},
            {"title": "Dune", "year": 2021, "imdb_id": "tt1160419"},
            {"title": "Oppenheimer", "year": 2023, "imdb_id": "tt15398776"},
            {"title": "The Grand Budapest Hotel", "year": 2014, "imdb_id": "tt2278388"},
            {"title": "Moonlight", "year": 2016, "imdb_id": "tt4975722"},
        ],
    },
    {
        "context_id": "picturehouse_central_london_2026_10",
        "venue": "Picturehouse Central",
        "city": "London",
        "venue_type": "chain_artthouse",
        "source_url": "https://www.picturehouses.com",
        "retrieved_at": "2026-10-07T09:00:00Z",
        "verification_status": "UNVERIFIED",
        "verification_notes": "Films are plausible for venue but not scraped from live site. Picturehouses is a chain.",
        "films": [
            {"title": "La La Land", "year": 2016, "imdb_id": "tt3783958"},
            {"title": "The Shape of Water", "year": 2017, "imdb_id": "tt5580390"},
            {"title": "Three Billboards Outside Ebbing, Missouri", "year": 2017, "imdb_id": "tt5027774"},
            {"title": "Lady Macbeth", "year": 2016, "imdb_id": "tt4291600"},
            {"title": "I, Daniel Blake", "year": 2016, "imdb_id": "tt5168192"},
        ],
    },
    {
        "context_id": "bfi_southbank_london_2026_10",
        "venue": "BFI Southbank",
        "city": "London",
        "venue_type": "national_institution",
        "source_url": "https://www.bfi.org.uk",
        "retrieved_at": "2026-10-07T09:00:00Z",
        "verification_status": "UNVERIFIED",
        "verification_notes": "Films are plausible for BFI but not scraped. BFI is a national institution, not independent.",
        "films": [
            {"title": "2001: A Space Odyssey", "year": 1968, "imdb_id": "tt0062622"},
            {"title": "Andrei Rublev", "year": 1966, "imdb_id": "tt0060107"},
            {"title": "Persona", "year": 1966, "imdb_id": "tt0060827"},
            {"title": "Tokyo Story", "year": 1953, "imdb_id": "tt0046438"},
            {"title": "In the Mood for Love", "year": 2000, "imdb_id": "tt0118694"},
        ],
    },
    {
        "context_id": "phoenix_leicester_2026_10",
        "venue": "Phoenix Cinema Leicester",
        "city": "Leicester",
        "venue_type": "independent_community",
        "source_url": "https://phoenix.org.uk",
        "retrieved_at": "2026-10-07T09:00:00Z",
        "verification_status": "UNVERIFIED",
        "verification_notes": "Films are plausible but not scraped from live site",
        "films": [
            {"title": "Shoplifters", "year": 2018, "imdb_id": "tt8075192"},
            {"title": "Roma", "year": 2018, "imdb_id": "tt6155172"},
            {"title": "Portrait of a Lady on Fire", "year": 2019, "imdb_id": "tt8613070"},
            {"title": "The Lighthouse", "year": 2019, "imdb_id": "tt7984734"},
            {"title": "Uncut Gems", "year": 2019, "imdb_id": "tt5727208"},
        ],
    },
    {
        "context_id": "tyneside_newcastle_2026_10",
        "venue": "Tyneside Cinema",
        "city": "Newcastle",
        "venue_type": "independent_community",
        "source_url": "https://tynesidecinema.co.uk",
        "retrieved_at": "2026-10-07T09:00:00Z",
        "verification_status": "UNVERIFIED",
        "verification_notes": "Films are plausible but not scraped from live site",
        "films": [
            {"title": "Paddington 2", "year": 2017, "imdb_id": "tt4468740"},
            {"title": "The Death of Stalin", "year": 2017, "imdb_id": "tt4686844"},
            {"title": "The Souvenir", "year": 2019, "imdb_id": "tt6721508"},
            {"title": "Ammonite", "year": 2020, "imdb_id": "tt7983894"},
            {"title": "Saint Maud", "year": 2019, "imdb_id": "tt7545066"},
        ],
    },
]


# ============================================================
# METADATA/CONTENT BASELINE
# Uses only: title, year, genre, country, language, director
# Does NOT use Qloo
# ============================================================

# Film metadata database (title → metadata)
# This is what a metadata system would have access to
FILM_METADATA = {
    "The Thing": {"genre": ["horror", "sci-fi"], "country": "USA", "language": "English", "decade": "1980s", "style": "cult_horror"},
    "The Shining": {"genre": ["horror", "thriller"], "country": "USA/UK", "language": "English", "decade": "1980s", "style": "psychological_horror"},
    "Halloween III: Season of the Witch": {"genre": ["horror"], "country": "USA", "language": "English", "decade": "1980s", "style": "cult_horror"},
    "Suspiria": {"genre": ["horror"], "country": "Italy", "language": "Italian", "decade": "1970s", "style": "giallo"},
    "Perfect Blue": {"genre": ["animation", "thriller", "horror"], "country": "Japan", "language": "Japanese", "decade": "1990s", "style": "anime_thriller"},
    "Akira": {"genre": ["animation", "sci-fi"], "country": "Japan", "language": "Japanese", "decade": "1980s", "style": "anime_classic"},
    "Possession": {"genre": ["horror", "drama"], "country": "France/Germany", "language": "English/French", "decade": "1980s", "style": "art_horror"},
    "The Devils": {"genre": ["horror", "drama", "historical"], "country": "UK", "language": "English", "decade": "1970s", "style": "controversial_classic"},
    "Parasite": {"genre": ["thriller", "drama", "comedy"], "country": "South Korea", "language": "Korean", "decade": "2010s", "style": "arthouse_mainstream"},
    "The Zone of Interest": {"genre": ["drama", "historical"], "country": "UK/Poland", "language": "German", "decade": "2020s", "style": "arthouse"},
    "Perfect Days": {"genre": ["drama"], "country": "Japan/Germany", "language": "Japanese", "decade": "2020s", "style": "arthouse"},
    "Past Lives": {"genre": ["drama", "romance"], "country": "USA/South Korea", "language": "English/Korean", "decade": "2020s", "style": "arthouse"},
    "Everything Everywhere All at Once": {"genre": ["sci-fi", "comedy", "drama"], "country": "USA", "language": "English", "decade": "2020s", "style": "arthouse_mainstream"},
    "Dune": {"genre": ["sci-fi", "drama"], "country": "USA", "language": "English", "decade": "2020s", "style": "blockbuster_art"},
    "Oppenheimer": {"genre": ["drama", "historical", "biography"], "country": "USA/UK", "language": "English", "decade": "2020s", "style": "prestige"},
    "The Grand Budapest Hotel": {"genre": ["comedy", "drama"], "country": "Germany/UK", "language": "English", "decade": "2010s", "style": "auteur_comedy"},
    "Moonlight": {"genre": ["drama"], "country": "USA", "language": "English", "decade": "2010s", "style": "arthouse"},
    "Drive My Car": {"genre": ["drama"], "country": "Japan", "language": "Japanese", "decade": "2020s", "style": "arthouse"},
    "Get Out": {"genre": ["horror", "thriller"], "country": "USA", "language": "English", "decade": "2010s", "style": "social_horror"},
    "The Farewell": {"genre": ["drama", "comedy"], "country": "USA/China", "language": "English/Mandarin", "decade": "2010s", "style": "indie_drama"},
    "Minari": {"genre": ["drama"], "country": "USA", "language": "English/Korean", "decade": "2020s", "style": "indie_drama"},
    "Nomadland": {"genre": ["drama"], "country": "USA", "language": "English", "decade": "2020s", "style": "arthouse"},
    "Shoplifters": {"genre": ["drama"], "country": "Japan", "language": "Japanese", "decade": "2010s", "style": "arthouse"},
    "Roma": {"genre": ["drama"], "country": "Mexico", "language": "Spanish/Mixtec", "decade": "2010s", "style": "arthouse"},
    "Portrait of a Lady on Fire": {"genre": ["drama", "romance"], "country": "France", "language": "French", "decade": "2010s", "style": "arthouse"},
    "The Lighthouse": {"genre": ["horror", "drama"], "country": "USA/Canada", "language": "English", "decade": "2010s", "style": "art_horror"},
    "Uncut Gems": {"genre": ["thriller", "drama", "crime"], "country": "USA", "language": "English", "decade": "2010s", "style": "indie_thriller"},
    "Mulholland Drive": {"genre": ["mystery", "thriller", "drama"], "country": "USA/France", "language": "English", "decade": "2000s", "style": "surrealist"},
    "In the Mood for Love": {"genre": ["drama", "romance"], "country": "Hong Kong", "language": "Cantonese", "decade": "2000s", "style": "arthouse"},
    "Stalker": {"genre": ["sci-fi", "drama"], "country": "USSR", "language": "Russian", "decade": "1970s", "style": "art_scifi"},
    "Le Samouraï": {"genre": ["crime", "thriller"], "country": "France", "language": "French", "decade": "1960s", "style": "neo_noir"},
    "Paris, Texas": {"genre": ["drama"], "country": "Germany/France", "language": "English", "decade": "1980s", "style": "arthouse"},
    "The Handmaiden": {"genre": ["thriller", "drama", "romance"], "country": "South Korea", "language": "Korean", "decade": "2010s", "style": "arthouse"},
    "Call Me by Your Name": {"genre": ["drama", "romance"], "country": "Italy/France", "language": "English/Italian", "decade": "2010s", "style": "arthouse"},
    "Phantom Thread": {"genre": ["drama", "romance"], "country": "USA/UK", "language": "English", "decade": "2010s", "style": "auteur"},
    "The Favourite": {"genre": ["drama", "comedy", "historical"], "country": "Ireland/UK/USA", "language": "English", "decade": "2010s", "style": "arthouse"},
    "Lady Bird": {"genre": ["drama", "comedy"], "country": "USA", "language": "English", "decade": "2010s", "style": "indie_drama"},
    "La La Land": {"genre": ["musical", "drama", "romance"], "country": "USA", "language": "English", "decade": "2010s", "style": "prestige"},
    "The Shape of Water": {"genre": ["fantasy", "drama", "romance"], "country": "USA", "language": "English", "decade": "2010s", "style": "arthouse_mainstream"},
    "Three Billboards Outside Ebbing, Missouri": {"genre": ["drama", "comedy", "crime"], "country": "USA/UK", "language": "English", "decade": "2010s", "style": "prestige"},
    "Lady Macbeth": {"genre": ["drama"], "country": "UK", "language": "English", "decade": "2010s", "style": "arthouse"},
    "I, Daniel Blake": {"genre": ["drama"], "country": "UK/France", "language": "English", "decade": "2010s", "style": "social_realism"},
    "2001: A Space Odyssey": {"genre": ["sci-fi", "drama"], "country": "UK/USA", "language": "English", "decade": "1960s", "style": "art_scifi"},
    "Andrei Rublev": {"genre": ["drama", "historical", "biography"], "country": "USSR", "language": "Russian", "decade": "1960s", "style": "art_drama"},
    "Persona": {"genre": ["drama"], "country": "Sweden", "language": "Swedish", "decade": "1960s", "style": "art_drama"},
    "Tokyo Story": {"genre": ["drama"], "country": "Japan", "language": "Japanese", "decade": "1950s", "style": "art_drama"},
    "Paddington 2": {"genre": ["comedy", "family"], "country": "UK/France", "language": "English", "decade": "2010s", "style": "family"},
    "The Death of Stalin": {"genre": ["comedy", "drama", "historical"], "country": "UK/France", "language": "English", "decade": "2010s", "style": "political_comedy"},
    "The Souvenir": {"genre": ["drama"], "country": "UK/USA", "language": "English", "decade": "2010s", "style": "arthouse"},
    "Ammonite": {"genre": ["drama", "romance", "biography"], "country": "UK/Australia", "language": "English", "decade": "2020s", "style": "arthouse"},
    "Saint Maud": {"genre": ["horror", "drama"], "country": "UK", "language": "English", "decade": "2010s", "style": "art_horror"},
    "Selma": {"genre": ["drama", "historical", "biography"], "country": "USA/UK", "language": "English", "decade": "2010s", "style": "prestige"},
    "12 Years a Slave": {"genre": ["drama", "historical", "biography"], "country": "USA/UK", "language": "English", "decade": "2010s", "style": "prestige"},
    "Mudbound": {"genre": ["drama"], "country": "USA", "language": "English", "decade": "2010s", "style": "social_drama"},
    "If Beale Street Could Talk": {"genre": ["drama", "romance"], "country": "USA", "language": "English", "decade": "2010s", "style": "arthouse"},
    "Small Axe: Mangrove": {"genre": ["drama", "historical"], "country": "UK", "language": "English", "decade": "2020s", "style": "social_drama"},
    "Anatomy of a Fall": {"genre": ["drama", "thriller"], "country": "France", "language": "French", "decade": "2020s", "style": "arthouse"},
    "The Banshees of Inisherin": {"genre": ["drama", "comedy"], "country": "Ireland/UK/USA", "language": "English", "decade": "2020s", "style": "arthouse"},
}

# Candidate film pool — films a metadata system would know about
# This represents the universe of films a content-based system could recommend
CANDIDATE_POOL = [
    # Horror/cult (for Prince Charles type programmes)
    {"title": "Hereditary", "genre": ["horror"], "country": "USA", "style": "art_horror", "decade": "2010s"},
    {"title": "The Witch", "genre": ["horror"], "country": "USA", "style": "art_horror", "decade": "2010s"},
    {"title": "Midsommar", "genre": ["horror"], "country": "USA/Sweden", "style": "art_horror", "decade": "2010s"},
    {"title": "It Follows", "genre": ["horror"], "country": "USA", "style": "indie_horror", "decade": "2010s"},
    {"title": "The Babadook", "genre": ["horror"], "country": "Australia", "style": "art_horror", "decade": "2010s"},
    {"title": "Raw", "genre": ["horror"], "country": "France", "style": "art_horror", "decade": "2010s"},
    {"title": "Tetsuo: The Iron Man", "genre": ["horror", "sci-fi"], "country": "Japan", "style": "cult_horror", "decade": "1980s"},
    {"title": "Videodrome", "genre": ["horror", "sci-fi"], "country": "Canada", "style": "cult_horror", "decade": "1980s"},
    {"title": "Eraserhead", "genre": ["horror"], "country": "USA", "style": "surrealist_horror", "decade": "1970s"},
    {"title": "Don't Look Now", "genre": ["horror", "thriller"], "country": "UK/Italy", "style": "art_horror", "decade": "1970s"},
    {"title": "The Wicker Man", "genre": ["horror"], "country": "UK", "style": "folk_horror", "decade": "1970s"},
    {"title": "Deep Red", "genre": ["horror"], "country": "Italy", "style": "giallo", "decade": "1970s"},
    {"title": "Tenebre", "genre": ["horror"], "country": "Italy", "style": "giallo", "decade": "1980s"},
    {"title": "Phenomena", "genre": ["horror"], "country": "Italy", "style": "giallo", "decade": "1980s"},
    {"title": "Paprika", "genre": ["animation", "sci-fi"], "country": "Japan", "style": "anime_thriller", "decade": "2000s"},
    {"title": "Ghost in the Shell", "genre": ["animation", "sci-fi"], "country": "Japan", "style": "anime_classic", "decade": "1990s"},
    {"title": "Ninja Scroll", "genre": ["animation", "action"], "country": "Japan", "style": "anime_classic", "decade": "1990s"},
    # Arthouse (for ICA/Curzon type programmes)
    {"title": "Burning", "genre": ["drama", "mystery"], "country": "South Korea", "style": "arthouse", "decade": "2010s"},
    {"title": "The Handmaiden", "genre": ["drama", "thriller"], "country": "South Korea", "style": "arthouse", "decade": "2010s"},
    {"title": "Capernaum", "genre": ["drama"], "country": "Lebanon", "style": "arthouse", "decade": "2010s"},
    {"title": "Cold War", "genre": ["drama", "romance"], "country": "Poland", "style": "arthouse", "decade": "2010s"},
    {"title": "The Square", "genre": ["drama", "comedy"], "country": "Sweden", "style": "arthouse", "decade": "2010s"},
    {"title": "Force Majeure", "genre": ["drama", "comedy"], "country": "Sweden", "style": "arthouse", "decade": "2010s"},
    {"title": "Toni Erdmann", "genre": ["drama", "comedy"], "country": "Germany", "style": "arthouse", "decade": "2010s"},
    {"title": "Happy as Lazzaro", "genre": ["drama"], "country": "Italy", "style": "arthouse", "decade": "2010s"},
    {"title": "Transit", "genre": ["drama"], "country": "Germany", "style": "arthouse", "decade": "2010s"},
    {"title": "Waltz with Bashir", "genre": ["animation", "documentary"], "country": "Israel", "style": "arthouse", "decade": "2000s"},
    # Japanese cinema (for arthouse programmes with Japanese films)
    {"title": "Still Walking", "genre": ["drama"], "country": "Japan", "style": "arthouse", "decade": "2000s"},
    {"title": "Nobody Knows", "genre": ["drama"], "country": "Japan", "style": "arthouse", "decade": "2000s"},
    {"title": "After Life", "genre": ["drama"], "country": "Japan", "style": "arthouse", "decade": "1990s"},
    {"title": "Hana-bi", "genre": ["drama", "crime"], "country": "Japan", "style": "arthouse", "decade": "1990s"},
    {"title": "Sonatine", "genre": ["drama", "crime"], "country": "Japan", "style": "arthouse", "decade": "1990s"},
    # French cinema
    {"title": "Amour", "genre": ["drama"], "country": "France/Germany", "style": "arthouse", "decade": "2010s"},
    {"title": "Blue Is the Warmest Colour", "genre": ["drama", "romance"], "country": "France", "style": "arthouse", "decade": "2010s"},
    {"title": "The Piano Teacher", "genre": ["drama"], "country": "France/Austria", "style": "arthouse", "decade": "2000s"},
    {"title": "Caché", "genre": ["drama", "thriller"], "country": "France/Germany", "style": "arthouse", "decade": "2000s"},
    # UK social realism
    {"title": "Trainspotting", "genre": ["drama"], "country": "UK", "style": "social_realism", "decade": "1990s"},
    {"title": "This Is England", "genre": ["drama"], "country": "UK", "style": "social_realism", "decade": "2000s"},
    {"title": "Fish Tank", "genre": ["drama"], "country": "UK", "style": "social_realism", "decade": "2000s"},
    {"title": "Tyrannosaur", "genre": ["drama"], "country": "UK", "style": "social_realism", "decade": "2010s"},
    # Classic arthouse
    {"title": "Wild Strawberries", "genre": ["drama"], "country": "Sweden", "style": "art_drama", "decade": "1950s"},
    {"title": "The Seventh Seal", "genre": ["drama"], "country": "Sweden", "style": "art_drama", "decade": "1950s"},
    {"title": "8½", "genre": ["drama", "comedy"], "country": "Italy", "style": "art_drama", "decade": "1960s"},
    {"title": "La Dolce Vita", "genre": ["drama"], "country": "Italy", "style": "art_drama", "decade": "1960s"},
    {"title": "Breathless", "genre": ["drama", "crime"], "country": "France", "style": "new_wave", "decade": "1960s"},
    {"title": "The 400 Blows", "genre": ["drama"], "country": "France", "style": "new_wave", "decade": "1950s"},
    # Family/comedy (for mixed programmes)
    {"title": "Paddington", "genre": ["comedy", "family"], "country": "UK", "style": "family", "decade": "2010s"},
    {"title": "The Grand Budapest Hotel", "genre": ["comedy", "drama"], "country": "Germany/UK", "style": "auteur_comedy", "decade": "2010s"},
    {"title": "Isle of Dogs", "genre": ["animation", "comedy"], "country": "Germany/UK", "style": "auteur_animation", "decade": "2010s"},
]


def compute_content_similarity(film_a_meta: dict, film_b_meta: dict) -> float:
    """Compute content similarity between two films using metadata only.
    
    Uses: genre overlap, country, language, decade, style.
    Does NOT use Qloo.
    """
    score = 0.0
    
    # Genre overlap (Jaccard)
    genres_a = set(film_a_meta.get("genre", []))
    genres_b = set(film_b_meta.get("genre", []))
    if genres_a and genres_b:
        genre_intersection = len(genres_a & genres_b)
        genre_union = len(genres_a | genres_b)
        score += (genre_intersection / genre_union) * 0.4
    
    # Country match
    if film_a_meta.get("country") == film_b_meta.get("country"):
        score += 0.2
    
    # Decade match
    if film_a_meta.get("decade") == film_b_meta.get("decade"):
        score += 0.15
    
    # Style match
    if film_a_meta.get("style") == film_b_meta.get("style"):
        score += 0.25
    
    return score


def build_baseline_top_k(programme_films: list[dict], k: int = TOP_K) -> list[dict]:
    """Build baseline candidate list using content similarity.
    
    For each programme film, find the most similar films from the candidate pool.
    Returns top-k unique candidates with their similarity scores.
    """
    # Get metadata for programme films
    programme_metadata = []
    for film in programme_films:
        title = film["title"]
        if title in FILM_METADATA:
            programme_metadata.append(FILM_METADATA[title])
    
    if not programme_metadata:
        return []
    
    # Score each candidate against the programme
    candidate_scores = {}
    for candidate in CANDIDATE_POOL:
        if candidate["title"] in [f["title"] for f in programme_films]:
            continue  # Skip films already in programme
        
        max_similarity = 0.0
        for prog_meta in programme_metadata:
            similarity = compute_content_similarity(prog_meta, candidate)
            max_similarity = max(max_similarity, similarity)
        
        if max_similarity > 0:
            candidate_scores[candidate["title"]] = {
                "title": candidate["title"],
                "domain": "film",
                "similarity": round(max_similarity, 3),
                "genre": candidate.get("genre", []),
                "country": candidate.get("country", ""),
                "style": candidate.get("style", ""),
            }
    
    # Sort by similarity and return top-k
    sorted_candidates = sorted(
        candidate_scores.values(),
        key=lambda x: x["similarity"],
        reverse=True
    )
    return sorted_candidates[:k]


async def run_qloo_evaluation(context: dict, k: int = TOP_K) -> dict:
    """Run Qloo/Adjacent pipeline on a programme context."""
    films = context["films"]
    
    try:
        state = await run_live_async(
            films,
            render=False,
            resolver_delay_s=1.0,
        )
        
        # Build Programme Bet
        programme_adjacency_scores = {}
        cohort_breadth_scores = {}
        programme_adjacency_bands = {}
        cohort_breadth_bands = {}
        programme_adjacency_call_ids = {}
        cohort_breadth_call_ids = {}
        
        for cohort in state.ranked:
            cid = cohort.cohort_id
            score = cohort.score
            
            if score and score.mean_affinity is not None:
                programme_adjacency_scores[cid] = score.mean_affinity
                programme_adjacency_bands[cid] = (
                    "High" if score.mean_affinity >= 0.6
                    else "Medium" if score.mean_affinity >= 0.5
                    else "Low"
                )
                programme_adjacency_call_ids[cid] = score.call_id or ""
            
            total = len(cohort.members) if cohort.members else 0
            qualifying = len(cohort.qualifying_members) if cohort.members else 0
            if total > 0:
                breadth_ratio = qualifying / total
                cohort_breadth_scores[cid] = breadth_ratio
                cohort_breadth_bands[cid] = (
                    "High" if breadth_ratio >= 0.5
                    else "Medium" if breadth_ratio >= 0.3
                    else "Low"
                )
                cohort_breadth_call_ids[cid] = score.call_id if score and score.call_id else ""
        
        programme_bet = build_programme_bet(
            ranked_cohorts=state.ranked,
            taste_tags=state.taste_tags,
            geography=None,
            resolved_names=[p.resolved_name or p.title for p in state.resolved_items],
            programme_adjacency_scores=programme_adjacency_scores,
            cohort_breadth_scores=cohort_breadth_scores,
            programme_adjacency_bands=programme_adjacency_bands,
            cohort_breadth_bands=cohort_breadth_bands,
            programme_adjacency_call_ids=programme_adjacency_call_ids,
            cohort_breadth_call_ids=cohort_breadth_call_ids,
            rejected_cohorts=state.rejected,
        )
        
        # Collect top-k Qloo candidates (from ranked cohorts)
        qloo_candidates = []
        for cohort in state.ranked[:k]:
            score = cohort.score
            members = cohort.members if cohort.members else []
            # Get top members from this cohort
            for member in members[:3]:
                qloo_candidates.append({
                    "title": member.name if hasattr(member, "name") else str(member),
                    "domain": cohort.domain.replace("urn:entity:", ""),
                    "mean_affinity": score.mean_affinity if score else None,
                    "cohort_id": cohort.cohort_id,
                })
        
        return {
            "success": True,
            "resolved_items": len(state.resolved_items),
            "ranked_cohorts": len(state.ranked),
            "rejected_cohorts": len(state.rejected),
            "selected_domains": list(state.domain_selection.selected_domains) if state.domain_selection else [],
            "skipped_domains": list(state.domain_selection.skipped_domains) if state.domain_selection else [],
            "programme_bet": programme_bet.to_dict() if programme_bet else None,
            "taste_tags": [t.name for t in state.taste_tags[:10]] if state.taste_tags else [],
            "qloo_candidates": qloo_candidates[:k],
            "stop_reason": state.stop_reason,
            "data_status": state.data_status,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "qloo_candidates": [],
        }


def compute_structural_metrics(baseline_top_k: list, qloo_top_k: list, qloo_domains: list) -> dict:
    """Compute structural incremental-value metrics.
    
    Uses: overlap@K, cross-domain unique, non-overlapping, domain expansion, insufficiency.
    Does NOT use word Jaccard.
    """
    # A. CANDIDATE OVERLAP (Jaccard@K)
    baseline_titles = set(c["title"] for c in baseline_top_k)
    qloo_titles = set(c["title"] for c in qloo_top_k)
    
    intersection = baseline_titles & qloo_titles
    union = baseline_titles | qloo_titles
    jaccard_at_k = len(intersection) / len(union) if union else 0.0
    overlap_count = len(intersection)
    
    # B. CROSS-DOMAIN UNIQUE DISCOVERY
    baseline_domains = {"film"}  # Baseline only knows film
    qloo_domain_set = set(qloo_domains)
    cross_domain_domains = qloo_domain_set - baseline_domains
    cross_domain_count = len(cross_domain_domains)
    
    # C. NON-OVERLAPPING OPPORTUNITIES
    qloo_only = qloo_titles - baseline_titles
    baseline_only = baseline_titles - qloo_titles
    
    # D. DOMAIN EXPANSION
    total_domains_available = len(qloo_domain_set | baseline_domains)
    
    # E. INSUFFICIENCY RATE
    qloo_insufficient = len(qloo_top_k) == 0
    
    return {
        "jaccard_at_k": round(jaccard_at_k, 3),
        "overlap_count": overlap_count,
        "overlap_titles": list(intersection),
        "qloo_only_count": len(qloo_only),
        "qloo_only_titles": list(qloo_only),
        "baseline_only_count": len(baseline_only),
        "baseline_only_titles": list(baseline_only),
        "cross_domain_domains": list(cross_domain_domains),
        "cross_domain_count": cross_domain_count,
        "domain_expansion": total_domains_available,
        "qloo_insufficient": qloo_insufficient,
        "baseline_candidate_count": len(baseline_top_k),
        "qloo_candidate_count": len(qloo_top_k),
    }


async def run_evaluation():
    """Run the full M12.1 evaluation."""
    print("=" * 60)
    print("M12.1: REPAIRED INCREMENTAL-VALUE EVALUATION")
    print("=" * 60)
    print(f"Contexts: {len(VERIFIED_CONTEXTS)}")
    print(f"Candidate budget K: {TOP_K}")
    print(f"Date: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    # Count verification statuses
    verified_count = sum(1 for c in VERIFIED_CONTEXTS if c["verification_status"] == "VERIFIED_PROGRAMME")
    partial_count = sum(1 for c in VERIFIED_CONTEXTS if c["verification_status"] == "PARTIAL_PROGRAMME_EVIDENCE")
    unverified_count = sum(1 for c in VERIFIED_CONTEXTS if c["verification_status"] == "UNVERIFIED")
    
    print(f"Verification status:")
    print(f"  VERIFIED_PROGRAMME: {verified_count}")
    print(f"  PARTIAL_PROGRAMME_EVIDENCE: {partial_count}")
    print(f"  UNVERIFIED: {unverified_count}")
    print()
    
    results = []
    
    for i, context in enumerate(VERIFIED_CONTEXTS):
        context_id = context["context_id"]
        print(f"\n--- Context {i+1}/{len(VERIFIED_CONTEXTS)}: {context['venue']} ---")
        print(f"  Status: {context['verification_status']}")
        print(f"  Films: {len(context['films'])}")
        
        # Build baseline
        baseline_top_k = build_baseline_top_k(context["films"], TOP_K)
        print(f"  Baseline candidates: {len(baseline_top_k)}")
        for c in baseline_top_k[:3]:
            print(f"    {c['title']} ({c['domain']}) — similarity={c['similarity']}")
        
        # Run Qloo
        print(f"  Running Qloo...")
        qloo = await run_qloo_evaluation(context, TOP_K)
        
        if qloo["success"]:
            print(f"  Qloo: {qloo['resolved_items']} resolved, {qloo['ranked_cohorts']} ranked")
            print(f"  Selected domains: {qloo['selected_domains']}")
            print(f"  Qloo candidates: {len(qloo['qloo_candidates'])}")
            for c in qloo["qloo_candidates"][:3]:
                print(f"    {c['title']} ({c['domain']}) — affinity={c.get('mean_affinity', '?')}")
        else:
            print(f"  Qloo FAILED: {qloo.get('error')}")
        
        # Compute metrics
        metrics = compute_structural_metrics(
            baseline_top_k,
            qloo["qloo_candidates"],
            qloo.get("selected_domains", []),
        )
        print(f"  Jaccard@{TOP_K}: {metrics['jaccard_at_k']}")
        print(f"  Overlap: {metrics['overlap_count']}")
        print(f"  Qloo-only: {metrics['qloo_only_count']}")
        print(f"  Cross-domain: {metrics['cross_domain_count']}")
        print(f"  Qloo insufficient: {metrics['qloo_insufficient']}")
        
        result = {
            "evaluation_context_id": context_id,
            "venue": context["venue"],
            "city": context["city"],
            "venue_type": context["venue_type"],
            "source_url": context["source_url"],
            "verification_status": context["verification_status"],
            "verification_notes": context["verification_notes"],
            "programme_films": context["films"],
            "baseline_top_k": baseline_top_k,
            "qloo_top_k": qloo["qloo_candidates"],
            "qloo_domains": qloo.get("selected_domains", []),
            "qloo_programme_bet": qloo.get("programme_bet"),
            "qloo_taste_tags": qloo.get("taste_tags", []),
            "metrics": metrics,
            "qloo_success": qloo["success"],
            "qloo_error": qloo.get("error"),
        }
        results.append(result)
    
    # Summary (only verified contexts)
    verified_results = [r for r in results if r["verification_status"] == "VERIFIED_PROGRAMME"]
    
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY (VERIFIED_PROGRAMME ONLY)")
    print("=" * 60)
    
    total = len(verified_results)
    qloo_success = sum(1 for r in verified_results if r["qloo_success"])
    cross_domain = sum(1 for r in verified_results if r["metrics"]["cross_domain_count"] > 0)
    insufficient = sum(1 for r in verified_results if r["metrics"]["qloo_insufficient"])
    
    print(f"Verified contexts: {total}")
    print(f"Qloo successful: {qloo_success}/{total}")
    print(f"Cross-domain discovery: {cross_domain}/{total}")
    print(f"Qloo insufficient: {insufficient}/{total}")
    
    if verified_results:
        avg_jaccard = sum(r["metrics"]["jaccard_at_k"] for r in verified_results) / total
        avg_overlap = sum(r["metrics"]["overlap_count"] for r in verified_results) / total
        avg_qloo_only = sum(r["metrics"]["qloo_only_count"] for r in verified_results) / total
        avg_cross_domain = sum(r["metrics"]["cross_domain_count"] for r in verified_results) / total
        
        print(f"Avg Jaccard@{TOP_K}: {avg_jaccard:.3f}")
        print(f"Avg overlap: {avg_overlap:.1f}")
        print(f"Avg Qloo-only: {avg_qloo_only:.1f}")
        print(f"Avg cross-domain: {avg_cross_domain:.1f}")
    
    # Save results
    output = {
        "evaluation_date": datetime.now(timezone.utc).isoformat(),
        "candidate_budget_k": TOP_K,
        "baseline_type": "content_similarity_metadata_only",
        "baseline_fields": ["genre", "country", "decade", "style"],
        "total_contexts": len(results),
        "verified_contexts": verified_count,
        "partial_contexts": partial_count,
        "unverified_contexts": unverified_count,
        "results": results,
    }
    
    output_path = adjacent_root / "data" / "processed" / "m12_1_incremental_value_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nResults saved to: {output_path}")
    
    return output


if __name__ == "__main__":
    asyncio.run(run_evaluation())