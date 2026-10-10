"""Prospective Outcome Ledger — future-proof outcome logging.

Whenever Adjacent generates a Programme Bet, store the recommendation
and leave space for actual outcomes to be recorded later.

No synthetic labels. No inferred attendance. NULL = unavailable.

M13.2: Created for prospective outcome collection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class OutcomeRecord:
    """One recommendation + eventual outcome."""

    # Identity
    recommendation_id: str
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    # Venue context
    venue: str = ""
    city: str = ""
    venue_type: str = ""  # INDEPENDENT, CHAIN, etc.
    capacity: int | None = None

    # Programme context
    programme_context_id: str = ""
    programme_films: list[str] = field(default_factory=list)

    # Recommendation (Layer A: cultural evidence)
    candidate_entity: str = ""
    candidate_domain: str = ""
    qloo_affinity: float | None = None
    qloo_popularity: float | None = None
    qloo_evidence_score: float | None = None
    qloo_entity_id: str | None = None
    recommendation_rank: int | None = None

    # Recommendation (Layer B: experiment)
    experiment_format: str = ""
    experiment_date: str | None = None

    # Outcome (filled later — NULL until observed)
    actual_event_id: str | None = None
    tickets_sold: int | None = None
    occupancy: float | None = None
    sold_out: bool | None = None
    new_to_venue_visitors: int | None = None
    revenue: float | None = None

    # Provenance
    source: str = "adjacent_prospective"
    measurement_timestamp: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "created_at": self.created_at,
            "venue": self.venue,
            "city": self.city,
            "venue_type": self.venue_type,
            "capacity": self.capacity,
            "programme_context_id": self.programme_context_id,
            "programme_films": self.programme_films,
            "candidate_entity": self.candidate_entity,
            "candidate_domain": self.candidate_domain,
            "qloo_affinity": self.qloo_affinity,
            "qloo_popularity": self.qloo_popularity,
            "qloo_evidence_score": self.qloo_evidence_score,
            "qloo_entity_id": self.qloo_entity_id,
            "recommendation_rank": self.recommendation_rank,
            "experiment_format": self.experiment_format,
            "experiment_date": self.experiment_date,
            "actual_event_id": self.actual_event_id,
            "tickets_sold": self.tickets_sold,
            "occupancy": self.occupancy,
            "sold_out": self.sold_out,
            "new_to_venue_visitors": self.new_to_venue_visitors,
            "revenue": self.revenue,
            "source": self.source,
            "measurement_timestamp": self.measurement_timestamp,
            "notes": self.notes,
        }

    def record_outcome(
        self,
        *,
        actual_event_id: str | None = None,
        tickets_sold: int | None = None,
        occupancy: float | None = None,
        sold_out: bool | None = None,
        new_to_venue_visitors: int | None = None,
        revenue: float | None = None,
        measurement_timestamp: str | None = None,
        notes: str = "",
    ) -> None:
        """Record actual outcome after event occurs."""
        if actual_event_id is not None:
            self.actual_event_id = actual_event_id
        if tickets_sold is not None:
            self.tickets_sold = tickets_sold
        if occupancy is not None:
            self.occupancy = occupancy
        if sold_out is not None:
            self.sold_out = sold_out
        if new_to_venue_visitors is not None:
            self.new_to_venue_visitors = new_to_venue_visitors
        if revenue is not None:
            self.revenue = revenue
        if measurement_timestamp is not None:
            self.measurement_timestamp = measurement_timestamp
        if notes:
            self.notes = notes

    @property
    def has_outcome(self) -> bool:
        """Whether any outcome has been recorded."""
        return any([
            self.tickets_sold is not None,
            self.occupancy is not None,
            self.sold_out is not None,
            self.new_to_venue_visitors is not None,
            self.revenue is not None,
        ])

    @property
    def outcome_type(self) -> str:
        """Classification of outcome quality."""
        if self.tickets_sold is not None:
            return "DIRECT_OUTCOME"
        if self.occupancy is not None:
            return "DIRECT_OUTCOME"
        if self.sold_out is not None:
            return "STRONG_PROXY"
        if self.new_to_venue_visitors is not None:
            return "DIRECT_OUTCOME"
        if self.revenue is not None:
            return "DIRECT_OUTCOME"
        return "NO_OUTCOME"
