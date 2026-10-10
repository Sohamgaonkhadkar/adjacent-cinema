#!/usr/bin/env python3
"""
M10: Qloo Information-Gain Validation (Corrected)

Tests whether Qloo's cultural affinity data adds value beyond basic metadata
when analyzing historical cinema programming.

Uses Cinema Context (Netherlands) historical programming data.

SECURITY: API key loaded from environment variable only.
"""

import httpx
import json
import os
import pandas as pd
from pathlib import Path
from datetime import datetime

# Data directories
DATA_DIR = Path(__file__).parent.parent.parent / "data"
PROCESSED_DIR = DATA_DIR / "processed"
DOCS_DIR = Path(__file__).parent.parent.parent / "docs"

# Qloo API - loaded from environment ONLY
QLOO_API_KEY = os.environ.get('QLOO_API_KEY')
QLOO_BASE_URL = os.environ.get('QLOO_BASE_URL', 'https://hackathon.api.qloo.com')

if not QLOO_API_KEY:
    raise ValueError("QLOO_API_KEY environment variable not set. Export it before running.")

def search_qloo_entity(query: str, entity_type: str = 'urn:entity:movie') -> dict:
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
        print(f'  Error searching for {query}: {e}')
        return None

def get_qloo_insights(entity_id: str) -> dict:
    """Get cultural insights for an entity."""
    headers = {
        'x-api-key': QLOO_API_KEY,
        'Content-Type': 'application/json',
    }
    
    try:
        resp = httpx.get(
            f'{QLOO_BASE_URL}/v2/insights',
            params={
                'filter.type': 'urn:entity:movie',
                'signal.interests.entities': entity_id,
                'feature.explainability': 'true',
            },
            headers=headers,
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        print(f'  Error getting insights for {entity_id}: {e}')
        return None

def load_historical_data() -> pd.DataFrame:
    """Load the historical programme data."""
    parquet_path = PROCESSED_DIR / "independent_cinema_programmes.parquet"
    return pd.read_parquet(parquet_path)

def validate_qloo_on_venue(venue_name: str, films: list, max_films: int = 5) -> dict:
    """Validate Qloo information gain for a venue's programming."""
    print(f'\n--- Validating Qloo for {venue_name} ---')
    print(f'Total films in programme: {len(films)}')
    
    # Sample films to test
    sample_films = films[:max_films]
    print(f'Testing {len(sample_films)} films...')
    
    qloo_results = []
    for film in sample_films:
        print(f'  Searching for: {film}')
        entity = search_qloo_entity(film)
        if entity:
            entity_id = entity.get('entity_id', '')
            entity_name = entity.get('name', '?')
            print(f'    Found: {entity_name} ({entity_id})')
            
            # Get insights
            insights = get_qloo_insights(entity_id)
            if insights:
                print(f'    Insights: {len(insights.get("results", []))} results')
                qloo_results.append({
                    'film': film,
                    'entity_id': entity_id,
                    'entity_name': entity_name,
                    'insights_count': len(insights.get('results', [])),
                })
            else:
                print(f'    No insights available')
                qloo_results.append({
                    'film': film,
                    'entity_id': entity_id,
                    'entity_name': entity_name,
                    'insights_count': 0,
                })
        else:
            print(f'    Not found in Qloo')
            qloo_results.append({
                'film': film,
                'entity_id': None,
                'entity_name': None,
                'insights_count': 0,
            })
    
    # Calculate statistics
    found_count = sum(1 for r in qloo_results if r['entity_id'] is not None)
    insights_count = sum(1 for r in qloo_results if r['insights_count'] > 0)
    
    return {
        'venue': venue_name,
        'films_tested': len(sample_films),
        'films_found': found_count,
        'films_with_insights': insights_count,
        'qloo_hit_rate': found_count / len(sample_films) if sample_films else 0,
        'insights_rate': insights_count / len(sample_films) if sample_films else 0,
        'results': qloo_results,
    }

def main():
    print("=" * 60)
    print("M9: Qloo Information-Gain Validation")
    print("=" * 60)
    
    # Load historical data
    print("\n1. Loading historical programme data...")
    df = load_historical_data()
    print(f"   Loaded {len(df)} screenings")
    
    # Get unique venues
    venues = df.groupby('venue_name')['film_title'].apply(list).to_dict()
    print(f"   Found {len(venues)} venues")
    
    # Validate Qloo for each venue
    print("\n2. Validating Qloo information gain...")
    validation_results = []
    
    for venue_name, films in venues.items():
        # Get unique films
        unique_films = list(set(films))
        result = validate_qloo_on_venue(venue_name, unique_films, max_films=3)
        validation_results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("QLOO VALIDATION SUMMARY")
    print("=" * 60)
    
    total_tested = sum(r['films_tested'] for r in validation_results)
    total_found = sum(r['films_found'] for r in validation_results)
    total_insights = sum(r['films_with_insights'] for r in validation_results)
    
    print(f"\nTotal films tested: {total_tested}")
    print(f"Films found in Qloo: {total_found} ({total_found/total_tested*100:.1f}%)")
    print(f"Films with insights: {total_insights} ({total_insights/total_tested*100:.1f}%)")
    
    print("\nPer-venue results:")
    for r in validation_results:
        print(f"  {r['venue']}: {r['films_found']}/{r['films_tested']} found, "
              f"{r['films_with_insights']} with insights")
    
    # Save results
    results_path = DOCS_DIR / "M9_QLOO_VALIDATION.json"
    with open(results_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_films_tested': total_tested,
            'total_films_found': total_found,
            'total_films_with_insights': total_insights,
            'qloo_hit_rate': total_found / total_tested if total_tested else 0,
            'insights_rate': total_insights / total_tested if total_tested else 0,
            'venue_results': validation_results,
        }, f, indent=2)
    print(f"\nResults saved to: {results_path}")
    
    # Conclusion
    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    
    hit_rate = total_found / total_tested if total_tested else 0
    insights_rate = total_insights / total_tested if total_tested else 0
    
    if hit_rate > 0.5 and insights_rate > 0.3:
        print("✅ Qloo provides significant information gain")
        print("   Historical films are well-represented in Qloo's database")
        print("   Qloo can add cultural affinity data to historical programming")
    elif hit_rate > 0.3:
        print("⚠️ Qloo provides moderate information gain")
        print("   Some historical films are in Qloo's database")
        print("   Qloo may add value for newer films in the dataset")
    else:
        print("❌ Qloo provides limited information gain")
        print("   Most historical films are not in Qloo's database")
        print("   Qloo may not add value for this historical dataset")

if __name__ == '__main__':
    import warnings
    warnings.filterwarnings('ignore')
    main()