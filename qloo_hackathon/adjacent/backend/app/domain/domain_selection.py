"""Agentic domain selection — deterministic, auditable, no LLM.

The agent inspects the programme's Taste DNA (tag families) and chooses
which adjacent cultural domains are worth querying.  Every selection has
an explicit reason; every skipped domain has an explicit reason.

This replaces the unconditional fixed-domain expansion with an adaptive
step that saves Qloo calls and produces better-targeted results.

Rules:
- deterministic: same tags → same domains
- explainable: every decision has a reason
- bounded by call budget
- no LLM required
- preserves single-normalisation ranking rule
- preserves all provenance
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# --- Domain definitions with selection criteria ---

@dataclass(frozen=True)
class DomainSpec:
    """A candidate domain with its selection criteria."""
    domain: str
    noun: str  # human-readable name (e.g., "artist", "movie")
    # Tag families that indicate this domain is relevant
    signal_families: tuple[str, ...]
    # Minimum number of matching tags to select this domain
    min_signal_count: int = 1
    # Description for audit
    description: str = ""


# All available domains with their signal criteria
ALL_DOMAINS: tuple[DomainSpec, ...] = (
    DomainSpec(
        domain="urn:entity:artist",
        noun="artist",
        signal_families=("music", "band", "singer", "musician", "composer", "performer"),
        description="Music artists — relevant when programme has music-related tags",
    ),
    DomainSpec(
        domain="urn:entity:movie",
        noun="movie",
        signal_families=("film", "cinema", "movie", "director", "screenwriter"),
        description="Movies — relevant when programme has film-related tags (always include for cinema beachhead)",
    ),
    DomainSpec(
        domain="urn:entity:tv_show",
        noun="tv_show",
        signal_families=("television", "tv", "series", "show", "drama", "comedy"),
        description="TV shows — relevant when programme has television-related tags",
    ),
    DomainSpec(
        domain="urn:entity:book",
        noun="book",
        signal_families=("book", "literature", "novel", "author", "writer", "fiction", "nonfiction"),
        description="Books — relevant when programme has literature-related tags",
    ),
    DomainSpec(
        domain="urn:entity:brand",
        noun="brand",
        signal_families=("brand", "fashion", "luxury", "design", "lifestyle"),
        description="Brands — relevant when programme has lifestyle/fashion-related tags",
    ),
    DomainSpec(
        domain="urn:entity:destination",
        noun="destination",
        signal_families=("travel", "destination", "city", "country", "tourism", "geography"),
        description="Destinations — relevant when programme has travel/geography-related tags",
    ),
    DomainSpec(
        domain="urn:entity:podcast",
        noun="podcast",
        signal_families=("podcast", "audio", "radio", "interview", "conversation"),
        description="Podcasts — relevant when programme has audio/media-related tags",
    ),
)


@dataclass(frozen=True)
class DomainSelection:
    """The output of domain selection — one domain with its reason."""
    domain: str
    noun: str
    selected: bool
    reason: str
    signal_count: int  # how many tags matched
    matching_tags: tuple[str, ...]  # which tags matched


@dataclass(frozen=True)
class DomainSelectionResult:
    """Complete result of domain selection."""
    selected_domains: tuple[str, ...]  # domains to query
    skipped_domains: tuple[str, ...]  # domains not queried
    selections: tuple[DomainSelection, ...]  # all decisions
    qloo_calls_saved: int  # how many calls saved by not querying all domains
    total_tags_analyzed: int
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_domains": list(self.selected_domains),
            "skipped_domains": list(self.skipped_domains),
            "selections": [
                {
                    "domain": s.domain,
                    "noun": s.noun,
                    "selected": s.selected,
                    "reason": s.reason,
                    "signal_count": s.signal_count,
                    "matching_tags": list(s.matching_tags),
                }
                for s in self.selections
            ],
            "qloo_calls_saved": self.qloo_calls_saved,
            "total_tags_analyzed": self.total_tags_analyzed,
        }


def _extract_tag_families(tags: list[Any]) -> dict[str, int]:
    """Extract tag family counts from taste tags.
    
    A tag family is derived from the tag name or tag_id:
    - "urn:tag:genre:media:comedy" → "comedy"
    - "Silent film" → "film"
    - "Music" → "music"
    """
    family_counts: dict[str, int] = {}
    
    for tag in tags:
        name = getattr(tag, "name", None) or ""
        tag_id = getattr(tag, "tag_id", None) or ""
        
        # Extract from tag_id (e.g., "urn:tag:genre:media:comedy")
        if tag_id:
            parts = tag_id.split(":")
            for part in parts:
                part_lower = part.lower().replace("_", " ")
                family_counts[part_lower] = family_counts.get(part_lower, 0) + 1
        
        # Extract from name (e.g., "Silent film")
        if name:
            words = name.lower().replace("-", " ").split()
            for word in words:
                family_counts[word] = family_counts.get(word, 0) + 1
    
    return family_counts


def _count_signals(
    family_counts: dict[str, int],
    signal_families: tuple[str, ...],
) -> tuple[int, tuple[str, ...]]:
    """Count how many signal families match the tag families."""
    matching = []
    for signal in signal_families:
        if signal.lower() in family_counts:
            matching.append(signal)
    return len(matching), tuple(matching)


def select_domains(
    taste_tags: list[Any],
    *,
    always_include: tuple[str, ...] = ("urn:entity:movie",),
    max_domains: int | None = None,
) -> DomainSelectionResult:
    """Select which domains to query based on the Taste DNA.
    
    Args:
        taste_tags: List of scored tags from Qloo insights.
        always_include: Domains to always include (e.g., movie for cinema beachhead).
        max_domains: Maximum domains to select (None = no limit).
    
    Returns:
        DomainSelectionResult with selected/skipped domains and reasons.
    """
    family_counts = _extract_tag_families(taste_tags)
    
    selections = []
    selected = []
    skipped = []
    
    for spec in ALL_DOMAINS:
        # Always include specified domains
        if spec.domain in always_include:
            selections.append(DomainSelection(
                domain=spec.domain,
                noun=spec.noun,
                selected=True,
                reason=f"Always included: {spec.description}",
                signal_count=0,
                matching_tags=(),
            ))
            selected.append(spec.domain)
            continue
        
        # Check signal families
        signal_count, matching_tags = _count_signals(family_counts, spec.signal_families)
        
        if signal_count >= spec.min_signal_count:
            reason = (
                f"Selected: {signal_count} signal(s) found "
                f"({', '.join(matching_tags)}) — {spec.description}"
            )
            selections.append(DomainSelection(
                domain=spec.domain,
                noun=spec.noun,
                selected=True,
                reason=reason,
                signal_count=signal_count,
                matching_tags=matching_tags,
            ))
            selected.append(spec.domain)
        else:
            reason = (
                f"Skipped: {signal_count} signal(s) found "
                f"(need {spec.min_signal_count}) — {spec.description}"
            )
            selections.append(DomainSelection(
                domain=spec.domain,
                noun=spec.noun,
                selected=False,
                reason=reason,
                signal_count=signal_count,
                matching_tags=matching_tags,
            ))
            skipped.append(spec.domain)
    
    # Apply max_domains limit — select by strongest signal
    if max_domains is not None and len(selected) > max_domains:
        # Keep always_include + top signal domains (sorted by signal_count desc)
        always = [d for d in selected if d in always_include]
        optional = [d for d in selected if d not in always_include]
        # Sort optional domains by signal count (strongest first)
        optional_with_signals = [
            (d, next((s.signal_count for s in selections if s.domain == d), 0))
            for d in optional
        ]
        optional_sorted = [d for d, _ in sorted(optional_with_signals, key=lambda x: -x[1])]
        selected = always + optional_sorted[:max_domains - len(always)]
        # Update skipped
        skipped = [d for d in [s.domain for s in selections] if d not in selected]
        # Update selections
        selections = tuple(
            DomainSelection(
                domain=s.domain,
                noun=s.noun,
                selected=s.domain in selected,
                reason=s.reason if s.domain in selected else f"Skipped: max_domains limit ({max_domains})",
                signal_count=s.signal_count,
                matching_tags=s.matching_tags,
            )
            for s in selections
        )
    
    total_domains = len(ALL_DOMAINS)
    calls_saved = total_domains - len(selected)
    
    return DomainSelectionResult(
        selected_domains=tuple(selected),
        skipped_domains=tuple(skipped),
        selections=tuple(selections),
        qloo_calls_saved=calls_saved,
        total_tags_analyzed=len(taste_tags),
    )