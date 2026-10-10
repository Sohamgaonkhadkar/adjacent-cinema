"""Prince Charles Cinema Collector — scrapes showtimes and sold_out status.

Extracts from HTML:
- Film title, year, URL
- Show date, show time → normalized to Europe/London timezone-aware ISO
- Format (35mm, 4K, 70mm, DCP, etc.)
- Sold_out / Available status
- Booking URL
- show_start_at (timezone-aware ISO timestamp)

M13.3: Live outcome collection.
M13.4: Timestamp normalization to Europe/London.
"""

from __future__ import annotations

import html as html_module
import re
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Any

SOURCE_URL = "https://princecharlescinema.com/whats-on/"
VENUE_ID = "prince_charles_cinema"
VENUE_NAME = "Prince Charles Cinema"
CITY = "London"

# Month name → number
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def _parse_show_datetime(date_str: str, time_str: str) -> str | None:
    """Parse 'Friday 9th October' + '8:20 pm' → Europe/London ISO timestamp.

    Returns ISO 8601 string with +01:00 (BST) or +00:00 (GMT) offset.
    Returns None if parsing fails.

    Assumes current year (2026) for dates without explicit year.
    BST (British Summer Time) runs last Sunday of March to last Sunday of October.
    In 2026: BST ends 25 October 2026.
    """
    # Parse date: "Friday 9th October"
    date_match = re.match(
        r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+'
        r'(\d+)(?:st|nd|rd|th)?\s+(\w+)',
        date_str, re.IGNORECASE
    )
    if not date_match:
        return None

    day = int(date_match.group(1))
    month_name = date_match.group(2).lower()
    month = _MONTHS.get(month_name)
    if not month:
        return None

    # Parse time: "8:20 pm" or "12:15 pm"
    time_match = re.match(r'(\d{1,2}):(\d{2})\s*(am|pm)', time_str.strip(), re.IGNORECASE)
    if not time_match:
        return None

    hour = int(time_match.group(1))
    minute = int(time_match.group(2))
    ampm = time_match.group(3).lower()

    if ampm == "pm" and hour != 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0

    # Use 2026 as the year (PCC listings are for current/upcoming year)
    year = 2026
    try:
        naive_dt = datetime(year, month, day, hour, minute)
    except ValueError:
        return None

    # Determine BST vs GMT
    # BST: last Sunday of March to last Sunday of October
    # In 2026: BST starts 29 March, ends 25 October
    is_bst = _is_bst(naive_dt)

    # Europe/London offset: BST = UTC+1, GMT = UTC+0
    if is_bst:
        tz_offset = timedelta(hours=1)
        tz_name = "+01:00"
    else:
        tz_offset = timedelta(hours=0)
        tz_name = "+00:00"

    dt_with_tz = naive_dt.replace(tzinfo=timezone(tz_offset))
    return dt_with_tz.isoformat()


def _is_bst(dt: datetime) -> bool:
    """Check if a datetime falls within British Summer Time (BST).

    BST starts last Sunday of March, ends last Sunday of October.
    """
    year = dt.year

    # Last Sunday of March
    march_31 = datetime(year, 3, 31)
    days_since_sunday = march_31.weekday()  # 0=Monday, 6=Sunday
    if days_since_sunday == 6:
        bst_start = march_31
    else:
        bst_start = march_31 - timedelta(days=(days_since_sunday + 1) % 7)

    # Last Sunday of October
    oct_31 = datetime(year, 10, 31)
    days_since_sunday = oct_31.weekday()
    if days_since_sunday == 6:
        bst_end = oct_31
    else:
        bst_end = oct_31 - timedelta(days=(days_since_sunday + 1) % 7)

    return bst_start <= dt < bst_end


def collect_prince_charles() -> dict[str, Any]:
    """Scrape Prince Charles Cinema showtimes."""
    source_timestamp = datetime.now(timezone.utc).isoformat()

    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "30", SOURCE_URL],
            capture_output=True, text=True, timeout=35,
        )
        if result.returncode != 0:
            return {"success": False, "screenings": [], "source_url": SOURCE_URL,
                    "source_timestamp": source_timestamp,
                    "error": f"curl failed: {result.stderr[:200]}"}

        html = result.stdout
        if not html or len(html) < 1000:
            return {"success": False, "screenings": [], "source_url": SOURCE_URL,
                    "source_timestamp": source_timestamp,
                    "error": "Response too short or empty"}

        screenings = _parse_html(html, source_timestamp)
        return {"success": True, "screenings": screenings, "source_url": SOURCE_URL,
                "source_timestamp": source_timestamp, "raw_length": len(html)}

    except Exception as e:
        return {"success": False, "screenings": [], "source_url": SOURCE_URL,
                "source_timestamp": source_timestamp, "error": str(e)[:200]}


def _parse_html(html: str, source_timestamp: str) -> list[dict]:
    """Parse Prince Charles Cinema HTML into screening observations.

    HTML structure per film:
    <a class="liveeventtitle" href="/film/XXXXX/film-name">Film Title</a>
    ...
    <div class="heading">Friday 9th October</div>
    <li class="35mm">
        <a class="soldfilm_book_button">   OR   <a href="..." class="film_book_button">
            <span class="hover">Sold Out</span>  OR  <span class="hover">Book</span>
            <span class="time">8:20 pm</span>
        </a>
        <div class="movietag"><span class="tag 35mm">35mm</span></div>
    </li>
    """
    screenings = []

    # Split HTML by film blocks — each film starts with a liveeventtitle link
    film_pattern = re.compile(
        r'<a\s+class="liveeventtitle"\s+href="([^"]+)"[^>]*>([^<]+)</a>',
        re.IGNORECASE
    )

    # Find all film titles and their positions
    films = []
    for m in film_pattern.finditer(html):
        film_url = m.group(1).strip()
        film_title_raw = html_module.unescape(m.group(2).strip())  # Decode HTML entities
        if film_title_raw:  # Skip empty titles
            films.append((m.start(), film_url, film_title_raw))

    for i, (pos, film_url, film_title_raw) in enumerate(films):
        # Extract year from title or nearby text
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', film_title_raw)
        film_year = int(year_match.group(1)) if year_match else None
        # Clean title (remove year if embedded)
        film_title = re.sub(r'\s*\[?\d{4}\]?\s*$', '', film_title_raw).strip()

        # Get HTML block for this film (until next film or end)
        end_pos = films[i + 1][0] if i + 1 < len(films) else len(html)
        block = html[pos:end_pos]

        # Find all showtime entries in this block
        li_pattern = re.compile(
            r'<li\s+class="([^"]*)">(.*?)</li>',
            re.DOTALL | re.IGNORECASE
        )

        # Track date from headings
        date_heading_pattern = re.compile(
            r'((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)'
            r'\s+\d+(?:st|nd|rd|th)?\s+\w+)',
            re.IGNORECASE
        )

        # Walk through the block finding dates and showtimes
        segments = re.split(r'(<div\s+class="heading">)', block)

        current_date = ""
        for seg in segments:
            # Check if this segment contains a date heading
            heading_m = date_heading_pattern.search(seg)
            if heading_m:
                current_date = heading_m.group(1).strip()

            # Find all <li> showtime entries in this segment
            for li_m in li_pattern.finditer(seg):
                li_class = li_m.group(1).strip()
                li_content = li_m.group(2)

                # Determine state
                if 'soldfilm_book_button' in li_content or 'Sold Out' in li_content:
                    availability = "SOLD_OUT"
                    sold_out = True
                elif 'film_book_button' in li_content or 'Book' in li_content:
                    availability = "AVAILABLE"
                    sold_out = False
                else:
                    availability = "UNKNOWN"
                    sold_out = None

                # Extract time
                time_m = re.search(r'<span\s+class="time">\s*([^<]+)\s*</span>', li_content)
                if not time_m:
                    continue
                show_time = time_m.group(1).strip()

                # Extract booking URL
                booking_m = re.search(r'href="(https?://[^"]*booknow[^"]*)"', li_content)
                booking_url = booking_m.group(1) if booking_m else None

                # Extract format from li class or movietag
                show_format = ""
                fmt_class = li_class.lower().strip()
                if "35mm" in fmt_class:
                    show_format = "35mm"
                elif "4k" in fmt_class:
                    show_format = "4K"
                elif "70mm" in fmt_class:
                    show_format = "70mm"
                elif "dcp" in fmt_class:
                    show_format = "DCP"
                elif "lff" in fmt_class:
                    show_format = "LFF"

                # Also check movietag spans
                tag_m = re.search(r'<span\s+class="tag\s+([^"]+)">', li_content)
                if tag_m and not show_format:
                    show_format = tag_m.group(1).strip().upper()

                if current_date and show_time:
                    # M13.4: Normalize to timezone-aware ISO timestamp
                    show_start_at = _parse_show_datetime(current_date, show_time)

                    screenings.append({
                        "venue_id": VENUE_ID,
                        "venue_name": VENUE_NAME,
                        "film_title": film_title,
                        "film_year": film_year,
                        "film_url": film_url,
                        "show_date": current_date,
                        "show_time": show_time,
                        "show_start_at": show_start_at,
                        "format": show_format,
                        "booking_url": booking_url,
                        "source_url": SOURCE_URL,
                        "source_timestamp": source_timestamp,
                        "sold_out": sold_out,
                        "availability_state": availability,
                    })

    return screenings