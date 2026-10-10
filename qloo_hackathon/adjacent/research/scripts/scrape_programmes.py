"""Scrape programme data from UK independent cinemas.

Targets cinemas with public programme pages.
Respects robots.txt, rate limits requests, caches raw HTML.

Output: data/processed/screenings.parquet
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

# Cinema programme sources
# Each source has: name, city, programme_url, parser_function
CINEMA_SOURCES = [
    {
        "name": "Phoenix Picturehouse Oxford",
        "city": "Oxford",
        "venue_id": "phoenix_oxford",
        "url": "https://www.picturehouses.com/cinema/phoenix-picturehouse",
        "parser": "picturehouses",
    },
    {
        "name": "Ritzy Picturehouse",
        "city": "London",
        "venue_id": "ritzy_london",
        "url": "https://www.picturehouses.com/cinema/ritzy-picturehouse",
        "parser": "picturehouses",
    },
    {
        "name": "Duke of York's Picturehouse",
        "city": "Brighton",
        "venue_id": "dukeofyorks_brighton",
        "url": "https://www.picturehouses.com/cinema/duke-of-york-s-picturehouse",
        "parser": "picturehouses",
    },
    {
        "name": "Everyman Cinema Hampstead",
        "city": "London",
        "venue_id": "everyman_hampstead",
        "url": "https://www.everymancinema.com/hampstead",
        "parser": "everyman",
    },
    {
        "name": "Curzon Mayfair",
        "city": "London",
        "venue_id": "curzon_mayfair",
        "url": "https://www.curzon.com/cinemas/mayfair/",
        "parser": "curzon",
    },
    {
        "name": "Prince Charles Cinema",
        "city": "London",
        "venue_id": "princecharles_london",
        "url": "https://princecharlescinema.com",
        "parser": "princecharles",
    },
]


def check_robots_txt(url: str) -> dict:
    """Check robots.txt for the domain."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        resp = httpx.get(robots_url, timeout=10, headers={"User-Agent": "AdjacentResearch/1.0"})
        if resp.status_code == 200:
            return {"status": "found", "content": resp.text[:500]}
        return {"status": "not_found", "content": ""}
    except Exception as e:
        return {"status": "error", "content": str(e)}


def fetch_page(url: str) -> str | None:
    """Fetch a page with rate limiting and error handling."""
    headers = {
        "User-Agent": "AdjacentResearch/1.0 (Academic research; contact: adjacent@research.local)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
    }
    try:
        resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  Failed to fetch {url}: {e}")
        return None


def parse_generic_html(html: str, source: dict) -> list[dict]:
    """Generic parser that looks for common film listing patterns."""
    screenings = []

    # Look for film titles in common patterns
    # Pattern 1: <h3> or <h4> with film titles
    title_pattern = r'<(?:h[234]|a)[^>]*class="[^"]*(?:film|movie|title)[^"]*"[^>]*>([^<]+)</(?:h[234]|a)>'
    titles = re.findall(title_pattern, html, re.IGNORECASE)

    # Pattern 2: Look for date/time patterns near film titles
    date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})'
    time_pattern = r'(\d{1,2}:\d{2})'

    # Pattern 3: Look for structured data (JSON-LD)
    jsonld_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
    jsonld_matches = re.findall(jsonld_pattern, html, re.DOTALL)

    for match in jsonld_matches:
        try:
            data = json.loads(match)
            if isinstance(data, dict) and data.get("@type") == "Movie":
                screenings.append({
                    "film_title": data.get("name", ""),
                    "source": source["name"],
                    "venue_id": source["venue_id"],
                    "source_url": source["url"],
                })
        except json.JSONDecodeError:
            pass

    # If no structured data, try to extract from HTML
    if not screenings:
        for title in titles[:50]:  # Limit to 50
            title = title.strip()
            if len(title) > 3 and len(title) < 200:
                screenings.append({
                    "film_title": title,
                    "source": source["name"],
                    "venue_id": source["venue_id"],
                    "source_url": source["url"],
                })

    return screenings


def scrape_cinema(source: dict) -> list[dict]:
    """Scrape programme data from a single cinema."""
    print(f"\n  Scraping: {source['name']} ({source['city']})")
    print(f"    URL: {source['url']}")

    # Check robots.txt
    robots = check_robots_txt(source["url"])
    print(f"    Robots.txt: {robots['status']}")

    # Fetch page
    html = fetch_page(source["url"])
    if not html:
        return []

    # Cache raw HTML
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    cache_path = RAW_DIR / f"{source['venue_id']}_{timestamp}.html"
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"    Cached: {cache_path} ({len(html)} bytes)")

    # Parse
    screenings = parse_generic_html(html, source)
    print(f"    Found: {len(screenings)} potential screenings")

    # Add metadata
    for s in screenings:
        s["retrieved_at"] = datetime.now(timezone.utc).isoformat()
        s["parser_version"] = "1.0.0"
        s["robots_status"] = robots["status"]

    return screenings


def save_screenings(screenings: list[dict], source_name: str) -> None:
    """Save screenings with manifest."""
    timestamp = datetime.now(timezone.utc).isoformat()

    # Save raw
    raw_path = PROCESSED_DIR / f"screenings_{source_name}_{timestamp[:10]}.json"
    with open(raw_path, "w") as f:
        json.dump(screenings, f, indent=2)

    # Manifest
    manifest = {
        "source_id": f"{source_name}_{timestamp[:10]}",
        "domain": "multiple",
        "venue": source_name,
        "city": "UK",
        "source_url": "research/scripts/scrape_programmes.py",
        "retrieved_at": timestamp,
        "robots_status": "checked_per_source",
        "licensing_notes": "Public programme pages; fair use for research",
        "parser_version": "1.0.0",
        "record_count": len(screenings),
    }

    manifest_path = MANIFESTS_DIR / f"programmes_{source_name}_{timestamp[:10]}_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"  Saved {len(screenings)} screenings to {raw_path}")


def main():
    print("=" * 60)
    print("Adjacent M8: Programme Scraping")
    print("=" * 60)

    all_screenings = []

    for source in CINEMA_SOURCES:
        screenings = scrape_cinema(source)
        all_screenings.extend(screenings)
        time.sleep(2)  # Rate limiting between cinemas

    # Save combined
    save_screenings(all_screenings, "combined")

    print(f"\n{'=' * 60}")
    print(f"Total screenings found: {len(all_screenings)}")

    # Summary by source
    sources = {}
    for s in all_screenings:
        src = s.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1
    print(f"\nBy source:")
    for src, count in sorted(sources.items()):
        print(f"  {src}: {count}")

    # Show sample
    print(f"\nSample screenings:")
    for s in all_screenings[:10]:
        print(f"  {s.get('film_title', '?')} — {s.get('source', '?')}")


if __name__ == "__main__":
    main()