"""The evidence gate — "honest insufficiency" as executable code.

Adjacent must be able to say "I do not have enough Qloo evidence to make this
recommendation", and that behaviour has to exist from the first commit rather
than being bolted on at the end. This module is the small, testable core of it.

SCOPE NOTE: this is deliberately NOT the cohort-ranking engine. It contains no
clustering, no novelty scoring and no API calls. It answers one question —
"does this evidence clear a threshold we can defend?" — using the thresholds
Qloo publishes (0.8 / 0.6 / 0.5), so nothing here is invented.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .qloo.models import Band, ScoredEntity, band_for, clears_medium

# --- Thresholds (derived from Qloo's published affinity bands) --------------
#: Band boundary constants, for readability at the call sites.
BAND_HIGH = 0.6

#: A candidate cohort must have at least this many members at/above Medium.
MIN_COHORT_MEMBERS = 2
#: ...and at least this many at or above High, or it is only "Weak".
MIN_COHORT_MEMBERS_HIGH = 1
#: Below this many heatmap cells, no geographic claim may be made.
MIN_HEATMAP_CELLS = 10
#: Below this many resolved programme titles, the taste vector is too thin.
MIN_RESOLVED_TITLES = 3

# --- The exact sentences the product uses when it refuses -------------------
# These strings are part of the product, not placeholders: a run that cannot
# support a claim must say so in words a programmer can act on.

MSG_NOT_ENOUGH_RESOLVED = (
    "Only {resolved} of your titles could be identified in Qloo. With fewer than "
    f"{MIN_RESOLVED_TITLES}, the taste profile is too thin to be meaningful. Please check the "
    "unresolved titles or add more to your programme."
)
MSG_NO_TAGS = (
    "Qloo found no tags with meaningful affinity for this programme. Nothing has been "
    "substituted. This programme may be too heterogeneous, or too obscure, for the taste graph "
    "to characterise."
)
MSG_NO_ADJACENT_AUDIENCE = (
    "I do not have enough Qloo evidence to name an adjacent audience for this programme."
)
MSG_NO_GEOGRAPHY = (
    "Qloo returned only {cells} geographic cells for this city — too few to support a "
    "geographic claim. No map is shown rather than showing a misleading one."
)
MSG_CITY_NOT_MATCHED = (
    "Qloo could not match '{city}' to a locality. Please provide a city and country. Adjacent "
    "will not guess — a wrong city would produce a confidently wrong map."
)
MSG_WEAK_BET = (
    "No candidate held both your current audience and the target cohort above Medium. Rather "
    "than recommend something that serves one and loses the other, Adjacent is reporting no "
    "recommendation."
)


@dataclass(frozen=True)
class EvidenceVerdict:
    """A decision about whether evidence supports a claim."""

    sufficient: bool
    reason_code: str
    message: str
    stats: dict[str, object] = field(default_factory=dict)

    @property
    def insufficient(self) -> bool:
        return not self.sufficient

    def as_dict(self) -> dict[str, object]:
        return {
            "sufficient": self.sufficient,
            "reason_code": self.reason_code,
            "message": self.message,
            "stats": self.stats,
        }


def evaluate_programme_resolution(resolved_count: int) -> EvidenceVerdict:
    if resolved_count >= MIN_RESOLVED_TITLES:
        return EvidenceVerdict(
            True, "resolved_ok", "", {"resolved": resolved_count, "min_required": MIN_RESOLVED_TITLES}
        )
    return EvidenceVerdict(
        False,
        "insufficient_resolved_titles",
        MSG_NOT_ENOUGH_RESOLVED.format(resolved=resolved_count),
        {"resolved": resolved_count, "min_required": MIN_RESOLVED_TITLES},
    )


def evaluate_tags(scored_tags: Sequence[object]) -> EvidenceVerdict:
    """A tag must clear the Medium band to count as evidence."""
    clearing = [t for t in scored_tags if clears_medium(getattr(t, "affinity", None))]
    if clearing:
        return EvidenceVerdict(True, "tags_ok", "", {"tags_above_medium": len(clearing)})
    return EvidenceVerdict(False, "no_tags_above_medium", MSG_NO_TAGS, {"tags_above_medium": 0})


def evaluate_cohort(members: Sequence[ScoredEntity]) -> EvidenceVerdict:
    """Can this candidate cohort be shown at all, and how strong is it?"""
    above_medium = [m for m in members if clears_medium(m.affinity)]
    above_high = [m for m in members if m.affinity is not None and m.affinity >= BAND_HIGH]
    stats = {
        "members": len(members),
        "members_above_medium": len(above_medium),
        "members_above_high": len(above_high),
    }
    if len(above_high) >= MIN_COHORT_MEMBERS_HIGH and len(above_medium) >= MIN_COHORT_MEMBERS:
        return EvidenceVerdict(True, "strong", "", {**stats, "band": Band.HIGH.value})
    if len(above_medium) >= MIN_COHORT_MEMBERS:
        return EvidenceVerdict(True, "moderate", "", {**stats, "band": Band.MEDIUM.value})
    return EvidenceVerdict(
        False,
        "weak_evidence",
        (
            f"{len(above_medium)} of {len(members)} members clear the Medium band "
            f"(needs {MIN_COHORT_MEMBERS})."
        ),
        stats,
    )


def evaluate_cohort_set(
    cohorts: Sequence[Sequence[ScoredEntity]],
) -> EvidenceVerdict:
    """The gate that produces MSG_NO_ADJACENT_AUDIENCE when nothing survives."""
    survivors = [c for c in cohorts if evaluate_cohort(c).sufficient]
    if survivors:
        return EvidenceVerdict(True, "cohorts_ok", "", {"tested": len(cohorts), "surviving": len(survivors)})
    return EvidenceVerdict(
        False,
        "insufficient_cohorts",
        MSG_NO_ADJACENT_AUDIENCE,
        {"tested": len(cohorts), "surviving": 0},
    )


def evaluate_heatmap(cells: Sequence[object]) -> EvidenceVerdict:
    """No geography is shown unless there are enough cells to mean something."""
    count = len(cells)
    if count >= MIN_HEATMAP_CELLS:
        return EvidenceVerdict(True, "heatmap_ok", "", {"cells": count})
    return EvidenceVerdict(
        False,
        "insufficient_heatmap_cells",
        MSG_NO_GEOGRAPHY.format(cells=count),
        {"cells": count, "min_required": MIN_HEATMAP_CELLS},
    )


def evaluate_two_sided_bet(current_audience_fit: float | None, cohort_fit: float | None) -> EvidenceVerdict:
    """Both sides must clear Medium, or there is no programme bet worth making."""
    stats = {"current_audience_fit": current_audience_fit, "cohort_fit": cohort_fit}
    if clears_medium(current_audience_fit) and clears_medium(cohort_fit):
        bands = {
            "current_audience_band": band_for(current_audience_fit).value,
            "cohort_band": band_for(cohort_fit).value,
        }
        return EvidenceVerdict(True, "bet_ok", "", {**stats, **bands})
    return EvidenceVerdict(False, "weak_bet", MSG_WEAK_BET, stats)
