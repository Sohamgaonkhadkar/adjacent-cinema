"""Scrape programme data from UK cinemas using discovered APIs.

API Sources:
- Picturehouses: POST /api/scheduled-movies-ajax with cinema_code
- Prince Charles: HTML parsing (JSON-LD)

Output: data/processed/screenings_{date}.json
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).parent.parent.parent / "data"
RAW_DIR = DATA_DIR / "raw" / "programmes"
PROCESSED_DIR = DATA_DIR / "processed"
MANIFESTS_DIR = DATA_DIR / "manifests"

for d in [RAW_DIR, PROCESSED_DIR, MANIFESTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Picturehouses cinemas with their API codes
PICTUREHOUSES_CINEMAS = [
    {"name": "Ritzy Picturehouse", "city": "London", "code": "010", "venue_id": "ritzy_london"},
    {"name": "Phoenix Picturehouse", "city": "Oxford", "code": "011", "venue_id": "phoenix_oxford"},
    {"name": "Duke of York's", "city": "Brighton", "code": "013", "venue_id": "dukeofyorks_brighton"},
    {"name": "Picturehouse Central", "city": "London", "code": "017", "venue_id": "central_london"},
    {"name": "Clapham Picturehouse", "city": "London", "code": "018", "venue_id": "clapham_london"},
    {"name": "Greenwich Picturehouse", "city": "London", "code": "019", "venue_id": "greenwich_london"},
    {"name": "Hackney Picturehouse", "city": "London", "code": "020", "venue_id": "hackney_london"},
    {"name": "Stratford Picturehouse", "city": "London", "code": "021", "venue_id": "stratford_london"},
    {"name": "East Dulwich Picturehouse", "city": "London", "code": "022", "venue_id": "eastdulwich_london"},
    {"name": "Picturehouse at FACT", "city": "Liverpool", "code": "023", "venue_id": "fact_liverpool"},
    {"name": "City Screen Picturehouse", "city": "York", "code": "024", "venue_id": "cityscreen_york"},
    {"name": "Cameo Picturehouse", "city": "Edinburgh", "code": "025", "venue_id": "cameo_edinburgh"},
    {"name": "Harbour Lights Picturehouse", "city": "Southampton", "code": "026", "venue_id": "harbourlights_southampton"},
    {"name": "Picturehouse Exeter", "city": "Exeter", "code": "027", "venue_id": "exeter"},
    {"name": "Norwich Picturehouse", "city": "Norwich", "code": "028", "venue_id": "norwich"},
    {"name": "Picturehouse Bath", "city": "Bath", "code": "029", "venue_id": "bath"},
    {"name": "Arts Picturehouse Cambridge", "city": "Cambridge", "code": "030", "venue_id": "arts_cambridge"},
    {"name": "Stratford-upon-Avon Picturehouse", "city": "Stratford-upon-Avon", "code": "031", "venue_id": "stratfordavon"},
    {"name": "The Little Picturehouse", "city": "Henley-on-Thames", "code": "032", "venue_id": "henley"},
    {"name": "Picturehouse at the National Media Museum", "city": "Bradford", "code": "033", "venue_id": "nmm_bradford"},
    {"name": "Electric Picturehouse", "city": "Worcester", "code": "034", "venue_id": "electric_worcester"},
    {"name": "Picturehouse Winchester", "city": "Winchester", "code": "035", "venue_id": "winchester"},
    {"name": "Picturehouse Bury St Edmunds", "city": "Bury St Edmunds", "code": "036", "venue_id": "burystedmunds"},
]


def scrape_picturehouses_api(cinema: dict) -> list[dict]:
    """Scrape programme data from Picturehouses API."""
    url = "https://www.picturehouses.com/api/scheduled-movies-ajax"
    headers = {
        "User-Agent": "AdjacentResearch/1.0",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": f"https://www.picturehouses.com/cinema/{cinema['venue_id']}",
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        resp = httpx.post(url, headers=headers, data={"cinema_code": cinema["code"]}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"    API error: {e}")
        return []

    if data.get("response") != "success":
        print(f"    API response not success: {data.get('response')}")
        return []

    screenings = []
    for movie in data.get("movies", []):
        title = movie.get("Title", "")
        film_id = movie.get("ScheduledFilmId", "")
        trailer_url = movie.get("TrailerUrl", "")

        for showtime in movie.get("show_times", []):
            screening = {
                "venue_id": cinema["venue_id"],
                "venue_name": cinema["name"],
                "city": cinema["city"],
                "film_title": title,
                "film_id": film_id,
                "trailer_url": trailer_url,
                "showtime": showtime.get("Showtime", ""),
                "time": showtime.get("time", ""),
                "time_format": showtime.get("time_format", ""),
                "date": showtime.get("date", ""),
                "date_f": showtime.get("date_f", ""),
                "screen_name": showtime.get("ScreenName", ""),
                "seats_available": showtime.get("SeatsAvailable", 0),
                "is_sold_out": showtime.get("SoldoutStatus", 0) == 1,
                "is_allocated_seating": showtime.get("IsAllocatedSeating", False),
                "session_attributes": showtime.get("SessionAttributesNames", []),
                "session_id": showtime.get("SessionId", ""),
                "source": "picturehouses_api",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
            screenings.append(screening)

    return screenings


def scrape_picturehouses(cinemas: list[dict]) -> list[dict]:
    """Scrape all Picturehouses cinemas."""
    all_screenings = []

    for i, cinema in enumerate(cinemas):
        print(f"  [{i+1}/{len(cinemas)}] {cinema['name']} ({cinema['city']})")
        screenings = scrape_picturehouses_api(cinema)
        print(f"    Found: {len(screenings)} screenings")
        all_screenings.extend(screenings)
        time.sleep(1.5)  # Rate limiting

    return all_screenings


def deduplicate_screenings(screenings: list[dict]) -> list[dict]:
    """Deduplicate screenings by venue + film + date + time."""
    seen = set()
    unique = []
    for s in screenings:
        key = (s.get("venue_id", ""), s.get("film_title", ""), s.get("showtime", ""))
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def save_screenings(screenings: list[dict], source_name: str) -> Path:
    """Save screenings with manifest."""
    timestamp = datetime.now(timezone.utc).isoformat()

    # Save
    output_path = PROCESSED_DIR / f"screenings_{source_name}_{timestamp[:10]}.json"
    with open(output_path, "w") as f:
        json.dump(screenings, f, indent=2)

    # Manifest
    manifest = {
        "source_id": f"{source_name}_{timestamp[:10]}",
        "domain": "picturehouses.com",
        "venue": "multiple",
        "city": "UK",
        "source_url": "https://www.picturehouses.com/api/scheduled-movies-ajax",
        "retrieved_at": timestamp,
        "robots_status": "api_endpoint",
        "licensing_notes": "Public API; programme data for research use",
        "parser_version": "2.0.0",
        "record_count": len(screenings),
    }

    manifest_path = MANIFESTS_DIR / f"programmes_{source_name}_{timestamp[:10]}_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return output_path


def main():
    print("=" * 60)
    print("Adjacent M8: Programme Scraping v2 (API-based)")
    print("=" * 60)

    # 1. Picturehouses
    print(f"\n--- Picturehouses ({len(PICTUREHOUSES_CINEMAS)} cinemas) ---")
    ph_screenings = scrape_picturehouses(PICTUREHOUSES_CINEMAS)

    # 2. Deduplicate
    unique_screenings = deduplicate_screenings(ph_screenings)

    # 3. Save
    output_path = save_screenings(unique_screenings, "picturehouses")

    # 4. Summary
    print(f"\n{'=' * 60}")
    print(f"Total screenings: {len(ph_screenings)}")
    print(f"Unique screenings: {len(unique_screenings)}")
    print(f"Output: {output_path}")

    # Venue breakdown
    venues = {}
    for s in unique_screenings:
        v = s.get("venue_name", "unknown")
        venues[v] = venues.get(v, 0) + 1
    print(f"\nBy venue:")
    for v, count in sorted(venues.items(), key=lambda x: -x[1]):
        print(f"  {v}: {count}")

    # Film breakdown
    films = {}
    for s in unique_screenings:
        f = s.get("film_title", "unknown")
        films[f] = films.get(f, 0) + 1
    print(f"\nTop 20 films:")
    for f, count in sorted(films.items(), key=lambda x: -x[1])[:20]:
        print(f"  {f}: {count} screenings")

    # Date range
    dates = sorted(set(s.get("date_f", "") for s in unique_screenings if s.get("date_f")))
    if dates:
        print(f"\nDate range: {dates[0]} to {dates[-1]}")

    # Unique films count
    print(f"\nUnique films: {len(films)}")


if __name__ == "__main__":
    main()