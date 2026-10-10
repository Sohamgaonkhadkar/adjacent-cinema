"""Canonical Film Identity — deterministic canonicalization of film titles.

M13.5: Build a canonical film identity layer that normalizes representation
without inventing film identities. Every normalization is documented with a reason.

Rules:
1. HTML entity decoding (&amp; → &, &#039; → ', etc.)
2. Unicode normalization (NFKD, strip combining marks for key generation)
3. Whitespace normalization (strip, collapse)
4. Colon normalization (" :" → ":")
5. Year extraction from title ("(1974)" → year=1974, title cleaned)
6. Edition suffix removal ("(Theatrical Cut)", "[UK Version]", etc.)
7. Director prefix removal ("Ken Russell's", "Rob Zombie's", etc.)
8. Event/composite detection (double features, marathons, shorts programmes)
9. Membership screening detection

NEVER invent a film identity. Every change is documented.
"""

from __future__ import annotations

import html as html_module
import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum


class IdentityStatus(StrEnum):
    """Status of a canonical film identity."""
    VERIFIED = "VERIFIED"              # Year confirmed, identity defensible
    YEAR_MISSING = "YEAR_MISSING"      # Title defensible but year unknown
    EVENT_OR_COMPOSITE = "EVENT_OR_COMPOSITE"  # Double feature, marathon, event
    NEEDS_REVIEW = "NEEDS_REVIEW"      # Ambiguous, needs human review


# ============================================================
# NORMALIZATION RULES
# ============================================================

# HTML entities to decode
_HTML_ENTITIES = {
    "&amp;": "&",
    "&#039;": "'",
    "&apos;": "'",
    "&quot;": '"',
    "&lt;": "<",
    "&gt;": ">",
    "&#38;": "&",
    "&#x27;": "'",
}

# Edition suffixes to strip (order matters — longer patterns first)
_EDITION_SUFFIXES = [
    # Specific edition patterns
    r'\s*[-–—:]\s*The\s+Director\'?s?\s+Cut\s*$',
    r'\s*[-–—•·:]\s*Director\'?s?\s+Cut\s*$',
    r'\s*[-–—:]\s*Extended\s+Cut\s*$',
    r'\s*[-–—:]\s*Theatrical\s+Cut\s*$',
    r'\s*[-–—:]\s*Final\s+Cut\s*$',
    r'\s*[-–—:]\s*4K\s+Restoration\s*$',
    r'\s*[-–—:]\s*4K\s+Remaster\s*$',
    r'\s*[-–—:]\s*Restoration\s*$',
    r'\s*[-–—:]\s*Remastered\s*$',
    r'\s*[-–—:]\s*\d+(?:st|nd|rd|th)?\s+Anniversary\s*$',
    r'\s*[-–—]\s*\d+(?:st|nd|rd|th)?\s+Anniversary\s*$',
    r'\s*\(\s*Theatrical\s+Cut\s*\)\s*$',
    r'\s*\[\s*UK\s+Version\s*\]\s*$',
    r'\s*\[\s*US\s+Version\s*\]\s*$',
    r'\s*\[\s*Theatrical\s+Editions?\s*\]\s*$',
    r'\s*[-–—:]\s*UK\s+Version\s*$',
    r'\s*[-–—:]\s*US\s+Version\s*$',
    r'\s*\+\s*.*$',  # Everything after " + " (sequels in double features)
]

# Director prefixes to strip
_DIRECTOR_PREFIXES = [
    r"^Ken Russell'?s?\s+",
    r"^Rob Zombie'?s?\s+",
]

# Patterns that indicate events/composites (not single films)
_EVENT_PATTERNS = [
    r'\+',  # Double features with "+"
    r'\band\b.*\band\b.*\bFrankenstein\b',  # "X and Y" double features
    r'Double\s+Feature',
    r'Marathon',
    r'All-Nighter',
    r'Film\s+Quiz',
    r'Shorts\s+Programme',
    r'Solve\s+Along',
    r'Sing-A-Long',
    r'with\s+Live\s+Score',
    r'presents\s+',  # "Funeral Parade presents ..."
    r'Gd\s+Trip\s+presents',
    r'Scooby-Dooble',
    r'Tennis\s*\(with\b',
    r'Pyjama\s+Party',
]

# Year-in-title pattern: "(1974)" or "(2026)" at end or middle of title
_YEAR_IN_TITLE = re.compile(r'\s*\((\d{4})\)\s*$')

# Colon with space pattern: "X : Y" → "X: Y"
_COLON_SPACE = re.compile(r'\s+:\s+')

# Multiple spaces
_MULTI_SPACE = re.compile(r'\s{2,}')


@dataclass
class NormalizationResult:
    """Result of canonicalizing a film title."""
    raw_title: str
    normalized_title: str
    canonical_title: str
    canonicalization_reasons: list[str] = field(default_factory=list)
    extracted_year: int | None = None
    year_source: str = ""
    identity_status: IdentityStatus = IdentityStatus.YEAR_MISSING
    is_event: bool = False
    event_reason: str = ""


def _decode_html_entities(title: str) -> tuple[str, bool]:
    """Decode HTML entities. Returns (decoded_title, changed)."""
    decoded = html_module.unescape(title)
    # Also handle any remaining numeric entities
    for entity, replacement in _HTML_ENTITIES.items():
        decoded = decoded.replace(entity, replacement)
    return decoded, decoded != title


def _normalize_whitespace(title: str) -> tuple[str, bool]:
    """Normalize whitespace: strip, collapse multiple spaces."""
    normalized = _MULTI_SPACE.sub(' ', title.strip())
    return normalized, normalized != title


def _normalize_colons(title: str) -> tuple[str, bool]:
    """Normalize colons: 'X : Y' → 'X: Y'."""
    normalized = _COLON_SPACE.sub(': ', title)
    return normalized, normalized != title


def _extract_year_from_title(title: str) -> tuple[str, int | None, bool]:
    """Extract year from title like 'Film (1974)'.

    Returns (cleaned_title, year, changed).
    Does NOT extract years that are part of the film title itself
    (e.g., "2001: A Space Odyssey").
    """
    m = _YEAR_IN_TITLE.search(title)
    if m:
        year = int(m.group(1))
        cleaned = title[:m.start()].strip()
        # Don't extract year if it's clearly part of the title
        # (e.g., "2001" at the start of "2001: A Space Odyssey")
        if cleaned and not cleaned[0].isdigit():
            return cleaned, year, True
    return title, None, False


def _strip_edition_suffixes(title: str) -> tuple[str, list[str]]:
    """Strip edition/director's cut/anniversary suffixes.

    Returns (cleaned_title, list_of_reasons).
    """
    reasons = []
    cleaned = title
    for pattern in _EDITION_SUFFIXES:
        new_cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE).strip()
        if new_cleaned != cleaned:
            reasons.append(f"edition_suffix_removed:{pattern[:40]}")
            cleaned = new_cleaned
    return cleaned, reasons


def _strip_director_prefix(title: str) -> tuple[str, list[str]]:
    """Strip director prefixes like "Ken Russell's".

    Returns (cleaned_title, list_of_reasons).
    """
    reasons = []
    cleaned = title
    for pattern in _DIRECTOR_PREFIXES:
        new_cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE).strip()
        if new_cleaned != cleaned:
            reasons.append(f"director_prefix_removed:{pattern[:30]}")
            cleaned = new_cleaned
    return cleaned, reasons


def _is_event_or_composite(title: str) -> tuple[bool, str]:
    """Check if title indicates an event, double feature, or composite.

    Returns (is_event, reason).
    """
    for pattern in _EVENT_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return True, f"event_pattern:{pattern[:40]}"
    return False, ""


def canonicalize_film(raw_title: str, raw_year: int | None = None,
                      film_url: str | None = None) -> NormalizationResult:
    """Canonicalize a film title.

    This function normalizes representation only. It NEVER invents a film identity.

    Args:
        raw_title: The original title from PCC
        raw_year: Year if provided by PCC (usually None)
        film_url: PCC film URL for provenance

    Returns:
        NormalizationResult with raw, normalized, and canonical titles
    """
    reasons = []
    title = raw_title

    # Step 1: HTML entity decoding
    title, html_changed = _decode_html_entities(title)
    if html_changed:
        reasons.append("html_entity_decode")

    # Step 2: Whitespace normalization
    title, ws_changed = _normalize_whitespace(title)
    if ws_changed:
        reasons.append("whitespace_normalize")

    # Step 3: Colon normalization
    title, colon_changed = _normalize_colons(title)
    if colon_changed:
        reasons.append("colon_normalize")

    normalized_title = title  # After basic normalization

    # Step 4: Check for event/composite BEFORE stripping suffixes
    is_event, event_reason = _is_event_or_composite(title)

    # Step 5: Strip director prefixes FIRST (before year extraction)
    title, dir_reasons = _strip_director_prefix(title)
    reasons.extend(dir_reasons)

    # Step 6: Strip edition suffixes (before year extraction)
    title, ed_reasons = _strip_edition_suffixes(title)
    reasons.extend(ed_reasons)

    # Step 7: Extract year from title (now after suffix/prefix removal)
    title, extracted_year, year_changed = _extract_year_from_title(title)
    if year_changed:
        reasons.append(f"year_extracted:{extracted_year}")

    # Use provided year if available, otherwise extracted
    year = raw_year if raw_year is not None else extracted_year
    year_source = "pcc_provided" if raw_year is not None else (
        "extracted_from_title" if extracted_year else ""
    )

    # Step 8: Final whitespace normalization
    title, _ = _normalize_whitespace(title)

    canonical_title = title

    # Determine identity status
    if is_event:
        status = IdentityStatus.EVENT_OR_COMPOSITE
    elif year is not None:
        status = IdentityStatus.VERIFIED  # Year available, identity defensible
    else:
        status = IdentityStatus.YEAR_MISSING

    # Special case: empty title after normalization
    if not canonical_title:
        status = IdentityStatus.NEEDS_REVIEW

    return NormalizationResult(
        raw_title=raw_title,
        normalized_title=normalized_title,
        canonical_title=canonical_title,
        canonicalization_reasons=reasons,
        extracted_year=year,
        year_source=year_source,
        identity_status=status,
        is_event=is_event,
        event_reason=event_reason,
    )


def canonical_film_key(canonical_title: str, year: int | None) -> str:
    """Deterministic film key for canonical films.

    Uses normalized title + year. Case-insensitive.
    """
    # Normalize for key generation: lowercase, strip accents, collapse spaces
    title_key = canonical_title.strip().lower()
    # NFKD normalize and strip combining characters for key stability
    title_key = unicodedata.normalize('NFKD', title_key)
    title_key = ''.join(c for c in title_key if not unicodedata.combining(c))
    title_key = _MULTI_SPACE.sub(' ', title_key).strip()

    year_str = str(year) if year else "none"
    return f"{title_key}|{year_str}"


def audit_canonicalization(films: list[dict]) -> dict:
    """Audit the canonicalization of a list of films.

    Args:
        films: List of dicts with 'film_title', 'film_year', 'film_url'

    Returns:
        Audit report with statistics and examples
    """
    results = []
    for film in films:
        result = canonicalize_film(
            raw_title=film["film_title"],
            raw_year=film.get("film_year"),
            film_url=film.get("film_url"),
        )
        results.append(result)

    # Statistics
    total_raw = len(results)
    unique_raw = len({r.raw_title for r in results})
    unique_normalized = len({r.normalized_title for r in results})
    unique_canonical = len({
        canonical_film_key(r.canonical_title, r.extracted_year)
        for r in results
    })

    # Count by reason
    reason_counts = {}
    for r in results:
        for reason in r.canonicalization_reasons:
            # Get the reason type (before the colon)
            reason_type = reason.split(":")[0]
            reason_counts[reason_type] = reason_counts.get(reason_type, 0) + 1

    # Count by status
    status_counts = {}
    for r in results:
        status_counts[r.identity_status.value] = status_counts.get(r.identity_status.value, 0) + 1

    # Count events
    events = [r for r in results if r.is_event]
    event_examples = [(r.raw_title, r.event_reason) for r in events[:10]]

    # Collapsed groups (multiple raw titles → same canonical key)
    canonical_groups: dict[str, list[str]] = {}
    for r in results:
        key = canonical_film_key(r.canonical_title, r.extracted_year)
        if key not in canonical_groups:
            canonical_groups[key] = []
        canonical_groups[key].append(r.raw_title)

    collapsed_groups = {k: v for k, v in canonical_groups.items() if len(v) > 1}

    # Examples for each normalization rule
    rule_examples: dict[str, list[tuple[str, str]]] = {}
    for r in results:
        for reason in r.canonicalization_reasons:
            reason_type = reason.split(":")[0]
            if reason_type not in rule_examples:
                rule_examples[reason_type] = []
            if len(rule_examples[reason_type]) < 3:
                rule_examples[reason_type].append((r.raw_title, r.canonical_title))

    return {
        "total_raw_entries": total_raw,
        "unique_raw_titles": unique_raw,
        "unique_normalized_titles": unique_normalized,
        "unique_canonical_films": unique_canonical,
        "collapse_count": unique_raw - unique_canonical,
        "reason_counts": reason_counts,
        "status_counts": status_counts,
        "event_count": len(events),
        "event_examples": event_examples,
        "collapsed_groups_count": len(collapsed_groups),
        "collapsed_groups": dict(list(collapsed_groups.items())[:20]),
        "rule_examples": rule_examples,
        "results": results,
    }
