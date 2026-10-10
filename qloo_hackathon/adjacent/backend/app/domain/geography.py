"""Geography tool — heatmap analysis for audience concentration.

Calls Qloo's /v2/insights with filter.type=urn:heatmap to discover where
the programme's cultural affinity concentrates geographically.

Reuses the existing live parser (models.parse_heatmap) and Qloo client.
No invented geographic values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HeatmapCellResult:
    """A single heatmap cell with its affinity data."""

    latitude: float
    longitude: float
    geohash: str | None
    affinity: float
    affinity_rank: float | None
    popularity: float | None
    call_id: str | None


@dataclass(frozen=True)
class GeographyResult:
    """The complete geography analysis for a programme in a city."""

    city: str
    city_display: str
    cells: list[HeatmapCellResult] = field(default_factory=list)
    total_cells: int = 0
    highest_affinity_cells: list[HeatmapCellResult] = field(default_factory=list)
    call_id: str | None = None
    data_status: str = "measured"
    source: str = "qloo"
    sufficient: bool = False
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "city": self.city,
            "city_display": self.city_display,
            "total_cells": self.total_cells,
            "highest_affinity_cells": [
                {
                    "latitude": c.latitude,
                    "longitude": c.longitude,
                    "geohash": c.geohash,
                    "affinity": c.affinity,
                    "affinity_rank": c.affinity_rank,
                    "popularity": c.popularity,
                }
                for c in self.highest_affinity_cells
            ],
            "call_id": self.call_id,
            "data_status": self.data_status,
            "source": self.source,
            "sufficient": self.sufficient,
            "note": self.note,
        }


def build_geography_result(
    city: str,
    response: Any,
    call_id: str | None = None,
) -> GeographyResult:
    """Build a GeographyResult from a parsed HeatmapResponse.

    Args:
        city: The city query string (e.g. "London, UK")
        response: A HeatmapResponse from the Qloo client
        call_id: The Qloo call ID for provenance
    """
    cells_raw = response.results if hasattr(response, "results") else []
    cells = []
    for c in cells_raw:
        if c.lat is not None and c.lng is not None:
            cells.append(
                HeatmapCellResult(
                    latitude=c.lat,
                    longitude=c.lng,
                    geohash=c.geohash,
                    affinity=c.affinity or 0.0,
                    affinity_rank=c.affinity_rank,
                    popularity=c.popularity,
                    call_id=call_id,
                )
            )

    # Sort by affinity descending, take top cells
    scored = sorted(cells, key=lambda c: c.affinity, reverse=True)
    top = scored[:10] if scored else []

    # Determine city display name from locality
    locality = response.locality if hasattr(response, "locality") else None
    city_display = city
    if isinstance(locality, list) and locality and isinstance(locality[0], dict):
        city_display = locality[0].get("disambiguation") or locality[0].get("name") or city
    elif isinstance(locality, dict):
        city_display = locality.get("disambiguation") or locality.get("name") or city

    sufficient = len(cells) >= 10

    return GeographyResult(
        city=city,
        city_display=city_display,
        cells=cells,
        total_cells=len(cells),
        highest_affinity_cells=top,
        call_id=call_id or (response.call_id if hasattr(response, "call_id") else None),
        data_status="measured",
        source="qloo",
        sufficient=sufficient,
        note="" if sufficient else f"Only {len(cells)} cells returned (need ≥10 for geographic claims)",
    )
