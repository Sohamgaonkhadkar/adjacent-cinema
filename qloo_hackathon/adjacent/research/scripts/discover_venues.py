"""Discover UK independent cinemas from public sources.

Sources:
1. Wikidata SPARQL — cinema/theatre entities in UK
2. OpenStreetMap Overpass — cinema amenities in UK
3. Datathistle.com — UK cinema directory

Output: data/processed/venues_raw.parquet
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).parent.parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MANIFESTS_DIR = DATA_DIR / "manifests"

# Ensure directories exist
for d in [RAW_DIR, PROCESSED_DIR, MANIFESTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def discover_wikidata_cinemas(limit: int = 500) -> list[dict]:
    """Query Wikidata for UK cinema/theatre entities."""
    query = f"""
    SELECT ?cinema ?cinemaLabel ?lat ?lng ?cityLabel ?countryLabel ?inception ?capacity
    WHERE {{
      ?cinema wdt:P31/wdt:P279* wd:Q41253 ;  # instance of movie theater
              wdt:P17 wd:Q145 .               # country: United Kingdom
      OPTIONAL {{ ?cinema p:P625 ?coord . ?coord psv:P625 ?coordVal .
                 ?coordVal wikibase:geoLatitude ?lat ; wikibase:geoLongitude ?lng . }}
      OPTIONAL {{ ?cinema wdt:P131 ?city . }}
      OPTIONAL {{ ?cinema wdt:P571 ?inception . }}
      OPTIONAL {{ ?cinema wdt:P1083 ?capacity . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    LIMIT {limit}
    """

    url = "https://query.wikidata.org/sparql"
    headers = {"Accept": "application/json", "User-Agent": "AdjacentResearch/1.0"}

    print(f"Querying Wikidata for UK cinemas (limit={limit})...")
    try:
        resp = httpx.get(url, params={"query": query}, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  Wikidata query failed: {e}")
        return []

    venues = []
    for binding in data.get("results", {}).get("bindings", []):
        venue = {
            "source": "wikidata",
            "entity_id": binding.get("cinema", {}).get("value", ""),
            "name": binding.get("cinemaLabel", {}).get("value", ""),
            "latitude": float(binding["lat"]["value"]) if "lat" in binding else None,
            "longitude": float(binding["lng"]["value"]) if "lng" in binding else None,
            "city": binding.get("cityLabel", {}).get("value", ""),
            "country": "GB",
            "inception": binding.get("inception", {}).get("value", ""),
            "capacity": int(binding["capacity"]["value"]) if "capacity" in binding else None,
        }
        if venue["name"] and venue["name"] != venue["entity_id"].split("/")[-1]:
            venues.append(venue)

    print(f"  Found {len(venues)} venues from Wikidata")
    return venues


def discover_osm_cinemas() -> list[dict]:
    """Query OpenStreetMap for cinema amenities in UK."""
    query = """
    [out:json][timeout:60];
    area["ISO3166-1"="GB"]->.uk;
    (
      node["amenity"="cinema"](area.uk);
      way["amenity"="cinema"](area.uk);
      relation["amenity"="cinema"](area.uk);
    );
    out center tags;
    """

    url = "https://overpass-api.de/api/interpreter"
    headers = {"Accept": "application/json", "User-Agent": "AdjacentResearch/1.0"}
    print("Querying OpenStreetMap for UK cinemas...")

    try:
        resp = httpx.post(url, data={"data": query}, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  OSM query failed: {e}")
        return []

    venues = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        lat = element.get("lat") or element.get("center", {}).get("lat")
        lng = element.get("lon") or element.get("center", {}).get("lon")

        venue = {
            "source": "openstreetmap",
            "entity_id": f"osm_{element.get('type', 'node')}_{element.get('id', '')}",
            "name": tags.get("name", ""),
            "latitude": float(lat) if lat else None,
            "longitude": float(lng) if lng else None,
            "city": tags.get("addr:city", ""),
            "country": "GB",
            "screens": int(tags["screens"]) if "screens" in tags else None,
            "capacity": int(tags["capacity"]) if "capacity" in tags else None,
            "website": tags.get("website", ""),
        }
        if venue["name"]:
            venues.append(venue)

    print(f"  Found {len(venues)} venues from OpenStreetMap")
    return venues


def save_venues(venues: list[dict], source_name: str) -> None:
    """Save venues to raw storage with manifest."""
    timestamp = datetime.now(timezone.utc).isoformat()

    # Save raw data
    raw_path = RAW_DIR / f"venues_{source_name}_{timestamp[:10]}.json"
    with open(raw_path, "w") as f:
        json.dump(venues, f, indent=2)

    # Save manifest
    manifest = {
        "source_id": f"{source_name}_{timestamp[:10]}",
        "domain": source_name,
        "venue": "multiple",
        "city": "UK",
        "source_url": f"research/scripts/discover_venues.py ({source_name})",
        "retrieved_at": timestamp,
        "robots_status": "public_api",
        "licensing_notes": "Wikidata: CC0; OSM: ODbL",
        "parser_version": "1.0.0",
        "record_count": len(venues),
    }

    manifest_path = MANIFESTS_DIR / f"{source_name}_{timestamp[:10]}_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"  Saved {len(venues)} venues to {raw_path}")
    print(f"  Manifest: {manifest_path}")


def deduplicate_venues(all_venues: list[dict]) -> list[dict]:
    """Deduplicate venues by name + city (approximate)."""
    seen = set()
    unique = []
    for v in all_venues:
        key = (v.get("name", "").lower().strip(), v.get("city", "").lower().strip())
        if key not in seen and key[0]:
            seen.add(key)
            unique.append(v)
    return unique


def main():
    print("=" * 60)
    print("Adjacent M8: Venue Discovery")
    print("=" * 60)

    all_venues = []

    # 1. Wikidata
    wikidata_venues = discover_wikidata_cinemas(limit=500)
    all_venues.extend(wikidata_venues)
    save_venues(wikidata_venues, "wikidata")
    time.sleep(2)  # Rate limiting

    # 2. OpenStreetMap
    osm_venues = discover_osm_cinemas()
    all_venues.extend(osm_venues)
    save_venues(osm_venues, "openstreetmap")

    # 3. Deduplicate
    unique_venues = deduplicate_venues(all_venues)

    # 4. Save combined
    timestamp = datetime.now(timezone.utc).isoformat()
    combined_path = PROCESSED_DIR / f"venues_combined_{timestamp[:10]}.json"
    with open(combined_path, "w") as f:
        json.dump(unique_venues, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Total venues discovered: {len(all_venues)}")
    print(f"Unique venues after dedup: {len(unique_venues)}")
    print(f"Combined output: {combined_path}")

    # Summary
    sources = {}
    for v in unique_venues:
        src = v.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1
    print(f"\nBy source:")
    for src, count in sorted(sources.items()):
        print(f"  {src}: {count}")

    with_coords = sum(1 for v in unique_venues if v.get("latitude"))
    print(f"\nWith coordinates: {with_coords}/{len(unique_venues)}")


if __name__ == "__main__":
    main()