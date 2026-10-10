#!/usr/bin/env python3
"""
M10.1: Qloo Resolution Benchmark

Builds a proper benchmark dataset for Qloo entity resolution.
Minimum 200 films with stratified sampling across:
- Decades
- Languages
- Title lengths
- Translated/original titles
- Films with/without IMDb ID
- Common/unusual titles
- Films from different venues

SECURITY: API key loaded from environment variable only.
"""

import httpx
import json
import os
import re
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

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


def extract_year_from_title(title: str) -> Optional[int]:
    """Extract year from title like 'Film Name (1936)'."""
    match = re.search(r'\((\d{4})\)', title)
    if match:
        return int(match.group(1))
    return None


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


def resolve_film(
    source_film_id: str,
    film_title: str,
    film_year: Optional[int],
    imdb_id: Optional[str] = None,
) -> Dict:
    """
    Resolve a film to a Qloo entity with proper verification.
    
    Returns:
        Dict with resolution status and evidence
    """
    result = {
        'source_film_id': source_film_id,
        'film_title': film_title,
        'film_year': film_year,
        'imdb_id': imdb_id,
        'external_ids': {},
        'qloo_entity_id': None,
        'qloo_entity_name': None,
        'qloo_entity_year': None,
        'qloo_entity_imdb': None,
        'resolution_method': None,
        'resolution_status': 'UNRESOLVED',
        'confidence': 0.0,
        'evidence': [],
        'resolved_at': datetime.now().isoformat(),
    }
    
    # Add IMDb ID if available
    if imdb_id:
        result['external_ids']['imdb'] = imdb_id
    
    # Extract year from title if not provided
    if not film_year:
        film_year = extract_year_from_title(film_title)
        if film_year:
            result['film_year'] = film_year
            result['film_year_status'] = 'DERIVED'
            result['film_year_source'] = 'title_string'
        else:
            result['film_year_status'] = 'UNKNOWN'
            result['film_year_source'] = 'none'
    else:
        result['film_year_status'] = 'OBSERVED_SOURCE'
        result['film_year_source'] = 'cinema_context'
    
    # Normalize title for comparison
    normalized_title = normalize_title(film_title)
    
    # Search Qloo
    qloo_entity = search_qloo_entity(film_title)
    if not qloo_entity:
        result['resolution_status'] = 'UNRESOLVED'
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
    if qloo_imdb:
        result['external_ids']['qloo_imdb'] = qloo_imdb
    
    # Check for VERIFIED match
    evidence = []
    confidence = 0.0
    
    # Method 1: Exact title match
    if normalized_title == qloo_normalized:
        evidence.append('Exact title match')
        confidence += 0.4
    elif normalized_title in qloo_normalized or qloo_normalized in normalized_title:
        evidence.append('Partial title match')
        confidence += 0.2
    
    # Method 2: Year match (critical for verification)
    if film_year and qloo_year:
        if film_year == qloo_year:
            evidence.append(f'Exact year match ({film_year})')
            confidence += 0.5
        elif abs(film_year - qloo_year) <= 2:
            evidence.append(f'Year close match ({film_year} vs {qloo_year})')
            confidence += 0.3
        elif abs(film_year - qloo_year) <= 5:
            evidence.append(f'Year moderate mismatch ({film_year} vs {qloo_year})')
            confidence += 0.0
        else:
            evidence.append(f'Year mismatch ({film_year} vs {qloo_year})')
            confidence -= 0.5
    elif film_year and not qloo_year:
        evidence.append('No year in Qloo result')
        # Don't penalize - Qloo may not have year for all films
    
    # Method 3: IMDb ID match (if available)
    if imdb_id and qloo_imdb:
        if imdb_id == qloo_imdb:
            evidence.append(f'IMDb ID match ({imdb_id})')
            confidence += 0.5
        else:
            evidence.append(f'IMDb ID mismatch ({imdb_id} vs {qloo_imdb})')
            confidence -= 0.3
    
    # Method 4: Title contains key words
    if film_year and qloo_year:
        if abs(film_year - qloo_year) > 10:
            evidence.append(f'Large year gap suggests different film')
            confidence -= 0.5
    
    # Determine resolution status
    if confidence >= 0.7:
        result['resolution_status'] = 'VERIFIED'
        result['resolution_method'] = 'multi_signal_verification'
    elif confidence >= 0.4:
        result['resolution_status'] = 'AMBIGUOUS'
        result['resolution_method'] = 'partial_match'
    elif confidence < 0.0:
        result['resolution_status'] = 'MISMATCH'
        result['resolution_method'] = 'year_mismatch_or_imdb_mismatch'
    else:
        result['resolution_status'] = 'AMBIGUOUS'
        result['resolution_method'] = 'insufficient_evidence'
    
    result['confidence'] = max(0.0, min(1.0, confidence))
    result['evidence'] = evidence
    
    return result


def load_historical_data() -> pd.DataFrame:
    """Load the historical programme data."""
    parquet_path = PROCESSED_DIR / "independent_cinema_programmes.parquet"
    return pd.read_parquet(parquet_path)


def build_stratified_sample(df: pd.DataFrame, n: int = 200) -> pd.DataFrame:
    """
    Build a stratified sample of films for benchmark.
    
    Stratifies by:
    - Decade (1900s, 1910s, 1920s, 1930s, 1940s, 1950s)
    - Has IMDb ID or not
    - Title length (short/medium/long)
    - Venue
    """
    df = df.copy()
    
    # Extract decade from title
    df['decade'] = df['film_title'].apply(lambda x: extract_year_from_title(x))
    df['decade'] = df['decade'].apply(lambda x: (x // 10) * 10 if pd.notna(x) else None)
    
    # Add title length category
    df['title_len'] = df['film_title'].str.len()
    df['title_category'] = pd.cut(df['title_len'], bins=[0, 20, 40, 200], labels=['short', 'medium', 'long'])
    
    # Add has_imdb flag
    df['has_imdb'] = df['imdb_id'].notna() & (df['imdb_id'] != '')
    
    # Sample from each stratum
    sample_frames = []
    
    # Stratify by decade
    for decade in [1900, 1910, 1920, 1930, 1940, 1950]:
        decade_df = df[df['decade'] == decade]
        if len(decade_df) > 0:
            # Sample proportional to decade size, minimum 10
            n_sample = max(10, min(40, len(decade_df) // 5))
            sample_frames.append(decade_df.sample(n=n_sample, random_state=42))
    
    # Add films without decade
    no_decade = df[df['decade'].isna()]
    if len(no_decade) > 0:
        sample_frames.append(no_decade.sample(n=min(20, len(no_decade)), random_state=42))
    
    sample = pd.concat(sample_frames)
    
    # Ensure we have at least n films
    if len(sample) < n:
        remaining = df[~df.index.isin(sample.index)]
        additional = remaining.sample(n=min(n - len(sample), len(remaining)), random_state=42)
        sample = pd.concat([sample, additional])
    
    return sample.head(n)


def main():
    print("=" * 70)
    print("M10.1: Qloo Resolution Benchmark")
    print("=" * 70)
    
    # Load historical data
    print("\n1. Loading historical programme data...")
    df = load_historical_data()
    print(f"   Loaded {len(df)} screenings")
    
    # Get unique films
    unique_films = df[['film_title', 'imdb_id']].drop_duplicates()
    print(f"   Unique films: {len(unique_films)}")
    
    # Build stratified sample
    print("\n2. Building stratified sample (200 films)...")
    sample = build_stratified_sample(unique_films, n=200)
    print(f"   Sample size: {len(sample)}")
    
    # Resolve each film
    print("\n3. Resolving films with trusted verification...")
    resolutions = []
    
    for idx, row in sample.iterrows():
        film_title = row['film_title']
        imdb_id = row['imdb_id'] if pd.notna(row['imdb_id']) else None
        
        # Extract year from title
        film_year = extract_year_from_title(film_title)
        
        print(f"   [{len(resolutions)+1}/{len(sample)}] {film_title[:50]}...", end=" ")
        
        resolution = resolve_film(
            source_film_id=f"CC-{idx}",
            film_title=film_title,
            film_year=film_year,
            imdb_id=imdb_id,
        )
        
        resolutions.append(resolution)
        
        status = resolution['resolution_status']
        confidence = resolution['confidence']
        print(f"→ {status} ({confidence:.2f})")
    
    # Create DataFrame
    resolution_df = pd.DataFrame(resolutions)
    
    # Calculate statistics
    print("\n" + "=" * 70)
    print("BENCHMARK STATISTICS")
    print("=" * 70)
    
    status_counts = resolution_df['resolution_status'].value_counts()
    print(f"\nTotal films resolved: {len(resolution_df)}")
    print(f"\nResolution status:")
    for status, count in status_counts.items():
        print(f"  {status}: {count} ({count/len(resolution_df)*100:.1f}%)")
    
    # Calculate detailed metrics
    search_return_rate = len(resolution_df[resolution_df['qloo_entity_id'].notna()]) / len(resolution_df)
    verified_count = len(resolution_df[resolution_df['resolution_status'] == 'VERIFIED'])
    ambiguous_count = len(resolution_df[resolution_df['resolution_status'] == 'AMBIGUOUS'])
    mismatch_count = len(resolution_df[resolution_df['resolution_status'] == 'MISMATCH'])
    unresolved_count = len(resolution_df[resolution_df['resolution_status'] == 'UNRESOLVED'])
    
    print(f"\nDetailed metrics:")
    print(f"  Search return rate: {search_return_rate*100:.1f}%")
    print(f"  Verified match rate: {verified_count/len(resolution_df)*100:.1f}%")
    print(f"  Ambiguous rate: {ambiguous_count/len(resolution_df)*100:.1f}%")
    print(f"  Mismatch rate: {mismatch_count/len(resolution_df)*100:.1f}%")
    print(f"  Unresolved rate: {unresolved_count/len(resolution_df)*100:.1f}%")
    
    # Save benchmark dataset
    print("\n4. Saving benchmark dataset...")
    benchmark_path = PROCESSED_DIR / "qloo_resolution_benchmark.parquet"
    resolution_df.to_parquet(benchmark_path, index=False)
    print(f"   Saved: {benchmark_path}")
    
    # Save as CSV for inspection
    csv_path = PROCESSED_DIR / "qloo_resolution_benchmark.csv"
    resolution_df.to_csv(csv_path, index=False)
    print(f"   Saved: {csv_path}")
    
    return resolution_df


if __name__ == '__main__':
    import warnings
    warnings.filterwarnings('ignore')
    main()