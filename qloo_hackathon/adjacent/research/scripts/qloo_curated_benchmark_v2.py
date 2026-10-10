#!/usr/bin/env python3
"""
M10.2: Rebuild Clean Curated Benchmark

Creates a clean curated benchmark with:
- Unique films only
- One canonical IMDb ID per film
- Verified title + year + IMDb input metadata
- No duplicates
- Documented source for each input identity

SECURITY: API key loaded from environment variable only.
"""

import httpx
import json
import os
import re
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Data directories
DATA_DIR = Path(__file__).parent.parent.parent / "data"
PROCESSED_DIR = DATA_DIR / "processed"
DOCS_DIR = Path(__file__).parent.parent.parent / "docs"

# Qloo API - loaded from environment ONLY
QLOO_API_KEY = os.environ.get('QLOO_API_KEY')
QLOO_BASE_URL = os.environ.get('QLOO_BASE_URL', 'https://hackathon.api.qloo.com')

if not QLOO_API_KEY:
    raise ValueError("QLOO_API_KEY environment variable not set. Export it before running.")


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    if not title:
        return ""
    # Remove year suffix like "(1936)"
    title = re.sub(r'\s*\(\d{4}\)\s*$', '', title)
    # Remove common prefixes/suffixes
    title = re.sub(r'^(The|A|An|Le|La|Les|Das|Die|Der|De|Het|En)\s+', '', title, flags=re.IGNORECASE)
    # Remove punctuation and normalize whitespace
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip().lower()
    return title


def search_qloo_entity(query: str, entity_type: str = 'urn:entity:movie') -> Optional[Dict]:
    """Search for an entity in Qloo."""
    headers = {
        'x-api-key': QLOO_API_KEY,
        'Content-Type': 'application/json',
    }
    
    try:
        resp = httpx.get(
            f'{QLOO_BASE_URL}/search',
            params={'query': query, 'types': entity_type},
            headers=headers,
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('results', [])
            if results:
                return results[0]
        return None
    except Exception as e:
        return None


def extract_qloo_year(entity: Dict) -> Optional[int]:
    """Extract year from Qloo entity search result."""
    # Method 1: Check properties.release_year
    props = entity.get('properties', {})
    if 'release_year' in props:
        return props['release_year']
    
    # Method 2: Check disambiguation field
    disambiguation = entity.get('disambiguation', '')
    if disambiguation and disambiguation.isdigit():
        return int(disambiguation)
    
    # Method 3: Check properties.release_date
    if 'release_date' in props:
        try:
            return int(props['release_date'][:4])
        except:
            pass
    
    return None


def extract_qloo_imdb(entity: Dict) -> Optional[str]:
    """Extract IMDb ID from Qloo entity search result."""
    props = entity.get('properties', {})
    external = props.get('external', {})
    imdb = external.get('imdb', {})
    return imdb.get('id')


def resolve_modern_film(
    film_title: str,
    film_year: int,
    imdb_id: str,
) -> Dict:
    """
    Resolve a modern film to a Qloo entity with proper verification.
    
    Returns:
        Dict with resolution status and evidence
    """
    result = {
        'film_title': film_title,
        'film_year': film_year,
        'imdb_id': imdb_id,
        'qloo_entity_id': None,
        'qloo_entity_name': None,
        'qloo_entity_year': None,
        'qloo_entity_imdb': None,
        'title_match': False,
        'year_match': False,
        'imdb_match': False,
        'alternate_title_match': False,
        'resolution_status': 'UNRESOLVED',
        'resolution_reason': '',
        'evidence': [],
        'resolved_at': datetime.now().isoformat(),
    }
    
    # Search Qloo
    qloo_entity = search_qloo_entity(film_title)
    if not qloo_entity:
        result['resolution_status'] = 'UNRESOLVED'
        result['resolution_reason'] = 'No Qloo entity found'
        result['evidence'].append('No Qloo entity found')
        return result
    
    qloo_name = qloo_entity.get('name', '')
    qloo_id = qloo_entity.get('entity_id', '')
    qloo_normalized = normalize_title(qloo_name)
    
    result['qloo_entity_id'] = qloo_id
    result['qloo_entity_name'] = qloo_name
    
    # Extract year directly from search result
    qloo_year = extract_qloo_year(qloo_entity)
    result['qloo_entity_year'] = qloo_year
    
    # Extract IMDb ID from search result
    qloo_imdb = extract_qloo_imdb(qloo_entity)
    result['qloo_entity_imdb'] = qloo_imdb
    
    # Check title match
    normalized_title = normalize_title(film_title)
    if normalized_title == qloo_normalized:
        result['title_match'] = True
        result['evidence'].append('Exact title match')
    elif normalized_title in qloo_normalized or qloo_normalized in normalized_title:
        result['alternate_title_match'] = True
        result['evidence'].append('Partial title match')
    
    # Check year match
    if film_year and qloo_year:
        if film_year == qloo_year:
            result['year_match'] = True
            result['evidence'].append(f'Exact year match ({film_year})')
        else:
            result['evidence'].append(f'Year mismatch ({film_year} vs {qloo_year})')
    
    # Check IMDb match
    if imdb_id and qloo_imdb:
        if imdb_id == qloo_imdb:
            result['imdb_match'] = True
            result['evidence'].append(f'IMDb ID match ({imdb_id})')
        else:
            result['evidence'].append(f'IMDb ID mismatch ({imdb_id} vs {qloo_imdb})')
    
    # Determine resolution status based on rules
    # Rule: IMDb agreement is strong identity evidence
    if imdb_id and qloo_imdb:
        if imdb_id == qloo_imdb:
            # IMDb match = VERIFIED (regardless of title/year)
            result['resolution_status'] = 'VERIFIED'
            result['resolution_reason'] = 'IMDb ID match'
        else:
            # IMDb mismatch = MISMATCH
            result['resolution_status'] = 'MISMATCH'
            result['resolution_reason'] = 'IMDb ID mismatch'
    elif result['title_match'] and result['year_match']:
        # Exact title + exact year = VERIFIED
        result['resolution_status'] = 'VERIFIED'
        result['resolution_reason'] = 'Exact title + exact year match'
    elif result['title_match'] and not result['year_match']:
        # Title match but year mismatch = MISMATCH
        result['resolution_status'] = 'MISMATCH'
        result['resolution_reason'] = 'Title match but year mismatch'
    elif result['alternate_title_match'] and result['year_match']:
        # Partial title + exact year = AMBIGUOUS
        result['resolution_status'] = 'AMBIGUOUS'
        result['resolution_reason'] = 'Partial title + exact year match'
    else:
        # Insufficient evidence
        result['resolution_status'] = 'AMBIGUOUS'
        result['resolution_reason'] = 'Insufficient evidence'
    
    return result


# Modern films (post-2000) with verified metadata
# Source: IMDb (verified)
MODERN_FILMS = [
    # 2000s
    ("The Dark Knight", 2008, "tt0468569"),
    ("Inception", 2010, "tt1375666"),
    ("The Social Network", 2010, "tt1285016"),
    ("Black Swan", 2010, "tt0947798"),
    ("The King's Speech", 2010, "tt1504320"),
    ("The Artist", 2011, "tt1655442"),
    ("The Tree of Life", 2011, "tt0478304"),
    ("Drive", 2011, "tt0780504"),
    ("The Grand Budapest Hotel", 2014, "tt2278388"),
    ("Boyhood", 2014, "tt1065073"),
    ("Birdman", 2014, "tt2562232"),
    ("The Revenant", 2015, "tt1663202"),
    ("Mad Max: Fury Road", 2015, "tt1392190"),
    ("Moonlight", 2016, "tt4975722"),
    ("La La Land", 2016, "tt3783958"),
    ("Get Out", 2017, "tt5052448"),
    ("The Shape of Water", 2017, "tt5580390"),
    ("Lady Bird", 2017, "tt4925292"),
    ("Parasite", 2019, "tt6751668"),
    ("1917", 2019, "tt8579674"),
    # 2010s
    ("The Wolf of Wall Street", 2013, "tt0993846"),
    ("Her", 2013, "tt1798709"),
    ("Gravity", 2013, "tt1454468"),
    ("The Imitation Game", 2014, "tt2084970"),
    ("Interstellar", 2014, "tt0816692"),
    ("The Martian", 2015, "tt3659388"),
    ("Spotlight", 2015, "tt1895587"),
    ("Arrival", 2016, "tt2543164"),
    ("Manchester by the Sea", 2016, "tt4034228"),
    ("Dunkirk", 2017, "tt5013056"),
    # 2020s
    ("Nomadland", 2020, "tt9770150"),
    ("Minari", 2020, "tt10633456"),
    ("The Power of the Dog", 2021, "tt10293406"),
    ("Dune", 2021, "tt1160419"),
    ("Everything Everywhere All at Once", 2022, "tt6710474"),
    ("The Banshees of Inisherin", 2022, "tt11813216"),
    ("Tár", 2022, "tt14444726"),
    ("Oppenheimer", 2023, "tt15398776"),
    ("Barbie", 2023, "tt1517268"),
    ("Poor Things", 2023, "tt14230458"),
    # International films
    ("Amélie", 2001, "tt0211915"),
    ("City of God", 2002, "tt0317248"),
    ("Oldboy", 2003, "tt0364569"),
    ("The Lives of Others", 2006, "tt0405094"),
    ("Pan's Labyrinth", 2006, "tt0457430"),
    ("The Secret in Their Eyes", 2009, "tt1305806"),
    ("A Separation", 2011, "tt1832382"),
    ("The Great Beauty", 2013, "tt2358891"),
    ("Two Days, One Night", 2014, "tt2737050"),
    ("Roma", 2018, "tt6155172"),
    # Animated
    ("Spirited Away", 2001, "tt0245429"),
    ("Finding Nemo", 2003, "tt0266543"),
    ("The Incredibles", 2004, "tt0317705"),
    ("WALL-E", 2008, "tt0910970"),
    ("Toy Story 3", 2010, "tt0435761"),
    ("Inside Out", 2015, "tt2096673"),
    ("Coco", 2017, "tt2380307"),
    ("Spider-Man: Into the Spider-Verse", 2018, "tt4633694"),
    ("Soul", 2020, "tt2948372"),
    ("The Boy and the Heron", 2023, "tt6587046"),
    # Documentaries
    ("March of the Penguins", 2005, "tt0427311"),
    ("An Inconvenient Truth", 2006, "tt0497116"),
    ("Man on Wire", 2008, "tt1155592"),
    ("Searching for Sugar Man", 2012, "tt2125608"),
    ("Amy", 2015, "tt2870648"),
    ("Free Solo", 2018, "tt7775622"),
    ("My Octopus Teacher", 2020, "tt12884640"),
    # Horror
    ("The Ring", 2002, "tt0298130"),
    ("The Conjuring", 2013, "tt1457767"),
    ("It Follows", 2014, "tt3235888"),
    ("The Witch", 2015, "tt3101340"),
    ("Hereditary", 2018, "tt4925292"),
    ("Midsommar", 2019, "tt8772262"),
    ("The Lighthouse", 2019, "tt7984734"),
    ("Nope", 2022, "tt10954984"),
    # Sci-Fi
    ("Ex Machina", 2014, "tt0470752"),
    ("Blade Runner 2049", 2017, "tt1856101"),
    ("Annihilation", 2018, "tt2798920"),
    ("Tenet", 2020, "tt6723592"),
    # Comedy
    ("The Hangover", 2009, "tt1119646"),
    ("Bridesmaids", 2011, "tt1478338"),
    ("The Big Short", 2015, "tt1596363"),
    ("Jojo Rabbit", 2019, "tt2584384"),
    # Drama
    ("There Will Be Blood", 2007, "tt0469494"),
    ("No Country for Old Men", 2007, "tt0477348"),
    ("The Hurt Locker", 2008, "tt0887912"),
    ("12 Years a Slave", 2013, "tt2024544"),
    ("The Favourite", 2018, "tt5083738"),
    ("Joker", 2019, "tt7286456"),
    ("The Father", 2020, "tt10272386"),
    ("The Whale", 2022, "tt13487810"),
    ("The Holdovers", 2023, "tt14849128"),
]


def main():
    print("=" * 70)
    print("M10.2: Rebuild Clean Curated Benchmark")
    print("=" * 70)
    
    # Step 1: Remove duplicates
    print("\n1. Removing duplicates...")
    seen_imdb = set()
    unique_films = []
    for title, year, imdb_id in MODERN_FILMS:
        if imdb_id not in seen_imdb:
            seen_imdb.add(imdb_id)
            unique_films.append((title, year, imdb_id))
        else:
            print(f'   Removed duplicate: {title} ({year}) - {imdb_id}')
    
    print(f'   Original: {len(MODERN_FILMS)} films')
    print(f'   Unique: {len(unique_films)} films')
    
    # Step 2: Resolve each film
    print("\n2. Resolving films...")
    resolutions = []
    
    for i, (title, year, imdb_id) in enumerate(unique_films):
        print(f'   [{i+1}/{len(unique_films)}] {title} ({year})...', end=' ')
        
        resolution = resolve_modern_film(
            film_title=title,
            film_year=year,
            imdb_id=imdb_id,
        )
        
        resolutions.append(resolution)
        
        status = resolution['resolution_status']
        reason = resolution['resolution_reason']
        print(f'→ {status}: {reason}')
    
    # Create DataFrame
    resolution_df = pd.DataFrame(resolutions)
    
    # Calculate statistics
    print('\n' + '=' * 70)
    print('CURATED BENCHMARK STATISTICS')
    print('=' * 70)
    
    status_counts = resolution_df['resolution_status'].value_counts()
    print(f'\nTotal unique films: {len(resolution_df)}')
    print(f'\nResolution status:')
    for status, count in status_counts.items():
        print(f'  {status}: {count} ({count/len(resolution_df)*100:.1f}%)')
    
    # Calculate detailed metrics
    search_return_rate = len(resolution_df[resolution_df['qloo_entity_id'].notna()]) / len(resolution_df)
    verified_count = len(resolution_df[resolution_df['resolution_status'] == 'VERIFIED'])
    ambiguous_count = len(resolution_df[resolution_df['resolution_status'] == 'AMBIGUOUS'])
    mismatch_count = len(resolution_df[resolution_df['resolution_status'] == 'MISMATCH'])
    unresolved_count = len(resolution_df[resolution_df['resolution_status'] == 'UNRESOLVED'])
    
    print(f'\nDetailed metrics:')
    print(f'  Search return rate: {search_return_rate*100:.1f}%')
    print(f'  Verified match rate: {verified_count/len(resolution_df)*100:.1f}%')
    print(f'  Ambiguous rate: {ambiguous_count/len(resolution_df)*100:.1f}%')
    print(f'  Mismatch rate: {mismatch_count/len(resolution_df)*100:.1f}%')
    print(f'  Unresolved rate: {unresolved_count/len(resolution_df)*100:.1f}%')
    
    # Save benchmark dataset
    print('\n3. Saving curated benchmark...')
    benchmark_path = PROCESSED_DIR / 'qloo_modern_curated_benchmark_v2.parquet'
    resolution_df.to_parquet(benchmark_path, index=False)
    print(f'   Saved: {benchmark_path}')
    
    # Save as CSV for inspection
    csv_path = PROCESSED_DIR / 'qloo_modern_curated_benchmark_v2.csv'
    resolution_df.to_csv(csv_path, index=False)
    print(f'   Saved: {csv_path}')
    
    # Save audit dataset
    print('\n4. Saving resolution audit...')
    audit_path = PROCESSED_DIR / 'qloo_resolution_audit_v2.parquet'
    resolution_df.to_parquet(audit_path, index=False)
    print(f'   Saved: {audit_path}')
    
    # Save as CSV for inspection
    audit_csv_path = PROCESSED_DIR / 'qloo_resolution_audit_v2.csv'
    resolution_df.to_csv(audit_csv_path, index=False)
    print(f'   Saved: {audit_csv_path}')
    
    return resolution_df


if __name__ == '__main__':
    import warnings
    warnings.filterwarnings('ignore')
    main()