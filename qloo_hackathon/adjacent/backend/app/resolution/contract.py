"""Resolution contract — typed models for entity resolution results.

Every resolved entity carries its match status, method, and evidence.
No numerical confidence is invented — Qloo does not provide one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MatchStatus(StrEnum):
    """Categorical verification status for a resolved entity."""

    VERIFIED = "VERIFIED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"
    MISMATCH = "MISMATCH"


class MatchMethod(StrEnum):
    """How the resolution was performed."""

    SEARCH = "search"
    SEARCH_WITH_YEAR = "search_with_year"
    EXTERNAL_ID = "external_id"


@dataclass(frozen=True)
class ResolvedEntity:
    """The output of a single resolution attempt.

    Every field is populated from actual Qloo response data.
    No field is invented or guessed.
    """

    # --- Input ---
    input_title: str
    input_year: int | None = None
    input_external_id: str | None = None
    input_external_family: str | None = None  # e.g. "imdb"

    # --- Qloo result ---
    qloo_entity_id: str | None = None
    qloo_name: str | None = None
    qloo_entity_type: str | None = None
    qloo_year: int | None = None
    qloo_disambiguation: str | None = None
    qloo_popularity: float | None = None

    # --- Verification ---
    match_status: MatchStatus = MatchStatus.UNRESOLVED
    match_method: MatchMethod | None = None
    verification_notes: list[str] = field(default_factory=list)

    # --- Evidence ---
    call_id: str | None = None
    related_call_ids: list[str] = field(default_factory=list)
    search_query: str | None = None
    raw_result: dict[str, Any] | None = None

    @property
    def resolved(self) -> bool:
        """True only when the entity is VERIFIED — safe to use in analysis."""
        return self.match_status == MatchStatus.VERIFIED

    @property
    def usable(self) -> bool:
        """True for VERIFIED entities.  AMBIGUOUS/MISMATCH/UNRESOLVED are not usable."""
        return self.match_status == MatchStatus.VERIFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_title": self.input_title,
            "input_year": self.input_year,
            "input_external_id": self.input_external_id,
            "input_external_family": self.input_external_family,
            "qloo_entity_id": self.qloo_entity_id,
            "qloo_name": self.qloo_name,
            "qloo_entity_type": self.qloo_entity_type,
            "qloo_year": self.qloo_year,
            "qloo_disambiguation": self.qloo_disambiguation,
            "qloo_popularity": self.qloo_popularity,
            "match_status": self.match_status.value,
            "match_method": self.match_method.value if self.match_method else None,
            "verification_notes": self.verification_notes,
            "call_id": self.call_id,
            "related_call_ids": self.related_call_ids,
        }
