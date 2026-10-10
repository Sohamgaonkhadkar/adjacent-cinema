"""PCC Film Year Scraper — extracts years from Prince Charles Cinema detail pages.

The PCC detail page for each film contains structured metadata:
```
## Film Title
- YEAR
- RUNTIME mins
- COUNTRY
- (RATING)
- GENRE
```

This module fetches the detail page and extracts the year.

Provenance: princecharlescinema.com detail page (PCC's own data).
"""

from __future__ import annotations

import re
import subprocess
from typing import Any


def scrape_pcc_film_year(film_url: str) -> dict[str, Any]:
    """Scrape the year from a PCC detail page.

    Args:
        film_url: Full URL like https://princecharlescinema.com/film/XXXXX/name

    Returns:
        Dict with year, source_url, evidence, success
    """
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "15", film_url],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode != 0:
            return {"success": False, "year": None, "source_url": film_url,
                    "evidence": f"curl failed: {result.stderr[:100]}"}

        html = result.stdout
        if not html or len(html) < 500:
            return {"success": False, "year": None, "source_url": film_url,
                    "evidence": "Response too short"}

        # Extract year from structured metadata
        # Pattern: after the film title heading, look for "- YEAR" line
        # The metadata block looks like:
        #   ## Film Title
        #   - 1984
        #   - 89mins
        #   - USA
        #   - (15)
        #   - Horror

        # Method 1: Look for the metadata block after the title heading
        # Pattern: "- YYYY\n- XXmins" (year followed by runtime)
        year_pattern = re.compile(
            r'<h2[^>]*>[^<]*</h2>\s*'
            r'(?:<[^>]+>\s*)*'
            r'-\s*(\d{4})\s*\n\s*-\s*\d+\s*mins',
            re.IGNORECASE | re.DOTALL
        )
        m = year_pattern.search(html)
        if m:
            year = int(m.group(1))
            if 1888 <= year <= 2030:  # Reasonable film year range
                return {"success": True, "year": year, "source_url": film_url,
                        "evidence": f"PCC detail page: year {year} in metadata block"}

        # Method 2: Look for the text pattern in the rendered content
        # After the title heading, find "- YEAR\n" followed by "- XXmins"
        text_pattern = re.compile(
            r'##\s+[^\n]+\n\s*-\s*(\d{4})\s*\n\s*-\s*\d+\s*mins',
            re.IGNORECASE
        )
        m = text_pattern.search(html)
        if m:
            year = int(m.group(1))
            if 1888 <= year <= 2030:
                return {"success": True, "year": year, "source_url": film_url,
                        "evidence": f"PCC detail page: year {year} in text metadata"}

        # Method 3: Look for structured list items with year pattern
        # <li>YEAR</li> or similar patterns near runtime
        li_pattern = re.compile(
            r'>\s*(\d{4})\s*<.*?>\s*\d+\s*mins',
            re.IGNORECASE | re.DOTALL
        )
        m = li_pattern.search(html)
        if m:
            year = int(m.group(1))
            if 1888 <= year <= 2030:
                return {"success": True, "year": year, "source_url": film_url,
                        "evidence": f"PCC detail page: year {year} in list metadata"}

        # Method 4: Look for year in the page title or description
        # e.g., "Alien (1979) Trailer" in the YouTube embed
        title_year_pattern = re.compile(
            r'[A-Z][^()]*\((\d{4})\)\s*(?:Trailer|Official|Clip)',
            re.IGNORECASE
        )
        m = title_year_pattern.search(html)
        if m:
            year = int(m.group(1))
            if 1888 <= year <= 2030:
                return {"success": True, "year": year, "source_url": film_url,
                        "evidence": f"PCC detail page: year {year} in trailer title (lower confidence)"}

        return {"success": False, "year": None, "source_url": film_url,
                "evidence": "No year found in PCC detail page"}

    except Exception as e:
        return {"success": False, "year": None, "source_url": film_url,
                "evidence": f"Error: {str(e)[:100]}"}
