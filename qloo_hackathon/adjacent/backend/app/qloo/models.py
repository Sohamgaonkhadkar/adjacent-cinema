"""Typed response models for the three Qloo shapes Adjacent consumes first.

Scope discipline: this models ONLY what the MVP reads. We do not model the whole
Qloo API. Anything else is preserved verbatim in `raw` so the evidence panel can
still show it.

Provenance rules enforced here:
  * every model carries `source` ("qloo" | "mock") and `data_status`
    ("measured" | "fixture"), so fixture data can never be mistaken for
    measured production data in a log, a payload or a UI;
  * every scored item keeps its `raw` payload, so any number rendered later can
    be traced to the exact response body that produced it.

Shape tolerance: Qloo nests results under `results.entities`, `results.tags`,
`results.cells`, etc. The parsers accept either that nested shape or a flat
`results` list, and record which one was observed (`observed_shape`) so the
probe can report real structure rather than our assumption of it.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

SourceKind = Literal["qloo", "mock"]
DataStatus = Literal["measured", "fixture"]

#: Official affinity bands (docs.qloo.com/docs/interpreting-affinity-scores).
BAND_VERY_HIGH_MIN = 0.8
BAND_HIGH_MIN = 0.6
BAND_MEDIUM = 0.5


class Band(StrEnum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNSCORED = "unscored"


BAND_LABELS: dict[Band, str] = {
    Band.VERY_HIGH: "Very High",
    Band.HIGH: "High",
    Band.MEDIUM: "Medium",
    Band.LOW: "Low",
    Band.UNSCORED: "Unscored",
}


def band_for(score: float | None) -> Band:
    """Map a measured affinity to its official band. No invented thresholds."""
    if score is None:
        return Band.UNSCORED
    if score > BAND_VERY_HIGH_MIN:
        return Band.VERY_HIGH
    if BAND_HIGH_MIN <= score <= BAND_VERY_HIGH_MIN:
        return Band.HIGH
    if score == BAND_MEDIUM:
        return Band.MEDIUM
    return Band.LOW


def clears_medium(score: float | None) -> bool:
    """True when a score reaches the Medium band (>= 0.5)."""
    return score is not None and score >= BAND_MEDIUM


class _Base(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class TagRef(_Base):
    tag_id: str
    name: str | None = None
    subtype: str | None = None


class ScoredTag(_Base):
    tag_id: str
    name: str | None = None
    subtype: str | None = None
    affinity: float | None = None
    popularity: float | None = None
    parent_type: str | None = None
    raw: dict[str, Any] | None = None

    @property
    def band(self) -> Band:
        return band_for(self.affinity)


class ScoredEntity(_Base):
    entity_id: str
    name: str | None = None
    type: str | None = None
    subtype: str | None = None
    affinity: float | None = None
    popularity: float | None = None
    tags: list[TagRef] = Field(default_factory=list)
    location: dict[str, Any] | None = None
    raw: dict[str, Any] | None = None

    @property
    def band(self) -> Band:
        return band_for(self.affinity)


class HeatmapCell(_Base):
    lat: float | None = None
    lng: float | None = None
    geohash: str | None = None
    affinity: float | None = None
    affinity_rank: int | None = None
    popularity: float | None = None
    raw: dict[str, Any] | None = None

    @property
    def band(self) -> Band:
        return band_for(self.affinity)


class _ResponseBase(_Base):
    """Common provenance envelope for every parsed response."""

    call_id: str
    source: SourceKind
    data_status: DataStatus
    endpoint: str | None = None
    query: dict[str, Any] | None = None
    observed_shape: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @property
    def is_fixture(self) -> bool:
        return self.data_status == "fixture"


class TagAffinityResponse(_ResponseBase):
    results: list[ScoredTag] = Field(default_factory=list)

    @property
    def scored(self) -> list[ScoredTag]:
        return [t for t in self.results if t.affinity is not None]


class EntityAffinityResponse(_ResponseBase):
    results: list[ScoredEntity] = Field(default_factory=list)

    @property
    def scored(self) -> list[ScoredEntity]:
        return [e for e in self.results if e.affinity is not None]


class HeatmapResponse(_ResponseBase):
    results: list[HeatmapCell] = Field(default_factory=list)
    #: Qloo returns `query.localities.filter` as a *list* of locality objects,
    #: not a single dict.  Accept both for forward-compatibility.
    locality: dict[str, Any] | list[Any] | None = None
    boundary: str | None = None

    @property
    def cells(self) -> list[HeatmapCell]:
        return self.results


class EntitiesResponse(_ResponseBase):
    results: list[ScoredEntity] = Field(default_factory=list)
    requested_entity_ids: list[str] = Field(default_factory=list)
    requested_external: dict[str, list[str]] = Field(default_factory=dict)

    @property
    def missing(self) -> list[str]:
        """Requested UUIDs that Qloo did not return.

        For `/entities` a 404 is a data outcome ("not in Qloo"), never a crash.
        """
        found = {e.entity_id for e in self.results}
        return [i for i in self.requested_entity_ids if i not in found]


class SearchResponse(_ResponseBase):
    results: list[ScoredEntity] = Field(default_factory=list)


class TagSearchResponse(_ResponseBase):
    results: list[ScoredTag] = Field(default_factory=list)


class RawResponse(_ResponseBase):
    """For endpoints not yet modelled in detail (audiences, trending, compare)."""

    data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Trace + tool envelope
# ---------------------------------------------------------------------------

CacheStatus = Literal["hit", "miss", "bypass"]


class TraceRow(_Base):
    """One Qloo call, or one mock call. Powers the Evidence Panel."""

    call_id: str
    seq: int = 0
    tool: str
    endpoint: str
    method: str = "GET"
    params: dict[str, Any] = Field(default_factory=dict)  # ALWAYS redacted
    started_at: str
    duration_ms: int = 0
    status: int | None = None
    result_count: int | None = None
    cache: CacheStatus = "bypass"
    source: SourceKind = "qloo"
    data_status: DataStatus = "measured"
    attempt: int = 1
    backfill_detected: bool = False
    error: dict[str, Any] | None = None
    notes: list[str] = Field(default_factory=list)

    def assert_no_secret(self, secret: str | None) -> None:
        """Defensive check used by tests: no key material may appear anywhere."""
        if not secret:
            return
        blob = self.model_dump_json()
        if secret in blob:
            raise AssertionError("API key found in trace row — redaction failed")


T = TypeVar("T", bound=BaseModel)


class ToolResult[T](_Base):
    """What every agent tool returns: data + provenance, never bare data."""

    tool: str
    ok: bool
    source: SourceKind
    data_status: DataStatus
    call_ids: list[str] = Field(default_factory=list)
    data: T | None = None
    error: dict[str, Any] | None = None
    insufficient: bool = False
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsers (shape-tolerant, and explicit about what they saw)
# ---------------------------------------------------------------------------


def _results_container(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return (container, observed_keys).

    Qloo returns `results` either as an object keyed by result kind
    (`{"entities": [...]}`) or, for some endpoints, as a list. We accept both and
    report which we saw, rather than assuming.
    """
    results = payload.get("results")
    if isinstance(results, dict):
        return results, sorted(results.keys())
    if isinstance(results, list):
        return {"_list": results}, ["_list"]
    return {}, []


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _parse_tags(raw_tags: Any) -> list[TagRef]:
    """Tag lists arrive either as URN strings or as objects."""
    out: list[TagRef] = []
    if not isinstance(raw_tags, Sequence) or isinstance(raw_tags, (str, bytes)):
        return out
    for item in raw_tags:
        if isinstance(item, str):
            parts = item.split(":")
            subtype = parts[2] if len(parts) > 2 and parts[1] == "tag" else None
            out.append(TagRef(tag_id=item, name=None, subtype=subtype))
        elif isinstance(item, dict):
            tag_id = item.get("tag_id") or item.get("id") or item.get("urn") or ""
            if not tag_id:
                continue
            out.append(
                TagRef(
                    tag_id=str(tag_id),
                    name=item.get("name"),
                    subtype=item.get("subtype") or item.get("type"),
                )
            )
    return out


def _parse_entity(item: dict[str, Any]) -> ScoredEntity:
    props = item.get("properties") if isinstance(item.get("properties"), dict) else {}
    popularity = _as_float(
        props.get("popularity", item.get("popularity")) if isinstance(props, dict) else item.get("popularity")
    )
    tags = _parse_tags((props or {}).get("tags") or item.get("tags") or [])
    location = None
    if isinstance(props, dict):
        geo = props.get("location") or props.get("geocode") or props.get("coordinates")
        if isinstance(geo, dict):
            location = geo
    # Live Qloo entities carry affinity inside `query.affinity`, not at top level.
    q_affinity = (
        item.get("query", {}).get("affinity")
        if isinstance(item.get("query"), dict)
        else None
    )
    return ScoredEntity(
        entity_id=str(item.get("entity_id") or item.get("id") or ""),
        name=item.get("name"),
        type=item.get("type"),
        subtype=item.get("subtype"),
        affinity=_as_float(q_affinity or item.get("affinity")),
        popularity=popularity,
        tags=tags,
        location=location,
        raw=item,
    )


def _parse_scored_tag(item: dict[str, Any]) -> ScoredTag:
    props = item.get("properties") if isinstance(item.get("properties"), dict) else {}
    # Live Qloo tags carry affinity inside `query.affinity`, not at top level.
    q_affinity = (
        item.get("query", {}).get("affinity")
        if isinstance(item.get("query"), dict)
        else None
    )
    return ScoredTag(
        tag_id=str(item.get("tag_id") or item.get("id") or item.get("urn") or ""),
        name=item.get("name"),
        subtype=item.get("subtype") or item.get("type"),
        affinity=_as_float(q_affinity or item.get("affinity")),
        popularity=_as_float((props or {}).get("popularity", item.get("popularity"))),
        parent_type=item.get("parent_type"),
        raw=item,
    )


def parse_tag_affinity(
    payload: dict[str, Any],
    *,
    call_id: str,
    source: SourceKind,
    data_status: DataStatus,
    endpoint: str,
) -> TagAffinityResponse:
    container, observed = _results_container(payload)
    items = container.get("tags") or container.get("_list") or []
    return TagAffinityResponse(
        results=[_parse_scored_tag(i) for i in items if isinstance(i, dict)],
        call_id=call_id,
        source=source,
        data_status=data_status,
        endpoint=endpoint,
        query=payload.get("query") if isinstance(payload.get("query"), dict) else None,
        observed_shape=observed,
    )


def parse_entity_affinity(
    payload: dict[str, Any],
    *,
    call_id: str,
    source: SourceKind,
    data_status: DataStatus,
    endpoint: str,
    extra_notes: Sequence[str] = (),
) -> EntityAffinityResponse:
    container, observed = _results_container(payload)
    items = container.get("entities") or container.get("_list") or []
    return EntityAffinityResponse(
        results=[_parse_entity(i) for i in items if isinstance(i, dict)],
        call_id=call_id,
        source=source,
        data_status=data_status,
        endpoint=endpoint,
        query=payload.get("query") if isinstance(payload.get("query"), dict) else None,
        observed_shape=observed,
        notes=list(extra_notes),
    )


def parse_heatmap(
    payload: dict[str, Any],
    *,
    call_id: str,
    source: SourceKind,
    data_status: DataStatus,
    endpoint: str,
) -> HeatmapResponse:
    container, observed = _results_container(payload)
    items = (
        container.get("heatmap")
        or container.get("cells")
        or container.get("geohashes")
        or container.get("_list")
        or []
    )
    query = payload.get("query") if isinstance(payload.get("query"), dict) else None
    locality = None
    if isinstance(query, dict):
        locs = query.get("localities") or query.get("location")
        if isinstance(locs, dict):
            locality = locs.get("filter") or locs
        elif isinstance(locs, list) and locs and isinstance(locs[0], dict):
            locality = locs[0]
    cells = []
    for item in items:
        if not isinstance(item, dict):
            continue
        # Lat/lng live inside a nested `location` object in live responses.
        loc = item.get("location") if isinstance(item.get("location"), dict) else {}
        # Affinity lives inside `item.query.affinity` in live responses.
        q_affinity = (
            item.get("query", {}).get("affinity")
            if isinstance(item.get("query"), dict)
            else None
        )
        cells.append(
            HeatmapCell(
                lat=_as_float(
                    loc.get("latitude", item.get("lat", item.get("latitude")))
                ),
                lng=_as_float(
                    loc.get("longitude", item.get("lng", item.get("lon", item.get("longitude"))))
                ),
                geohash=loc.get("geohash") or item.get("geohash"),
                affinity=_as_float(q_affinity or item.get("affinity")),
                affinity_rank=item.get("affinity_rank")
                if isinstance(item.get("affinity_rank"), int)
                else (item.get("query", {}).get("affinity_rank") if isinstance(item.get("query"), dict) and isinstance(item.get("query", {}).get("affinity_rank"), int) else None),
                popularity=_as_float(
                    item.get("query", {}).get("popularity")
                    if isinstance(item.get("query"), dict)
                    else item.get("popularity")
                ),
                raw=item,
            )
        )
    return HeatmapResponse(
        results=cells,
        locality=locality,
        boundary=(
            query.get("boundary")
            if isinstance(query, dict) and isinstance(query.get("boundary"), str)
            else None
        ),
        call_id=call_id,
        source=source,
        data_status=data_status,
        endpoint=endpoint,
        query=query,
        observed_shape=observed,
        notes=[
            "Heatmap cells are model estimates of taste concentration, not counts of people and not attendance."
        ],
    )


def parse_entities(
    payload: dict[str, Any],
    *,
    call_id: str,
    source: SourceKind,
    data_status: DataStatus,
    endpoint: str,
    requested_entity_ids: Sequence[str] = (),
    requested_external: dict[str, list[str]] | None = None,
) -> EntitiesResponse:
    container, observed = _results_container(payload)
    items = container.get("entities") or container.get("_list") or []
    return EntitiesResponse(
        results=[_parse_entity(i) for i in items if isinstance(i, dict)],
        requested_entity_ids=list(requested_entity_ids),
        requested_external=dict(requested_external or {}),
        call_id=call_id,
        source=source,
        data_status=data_status,
        endpoint=endpoint,
        observed_shape=observed,
    )


def parse_search(
    payload: dict[str, Any],
    *,
    call_id: str,
    source: SourceKind,
    data_status: DataStatus,
    endpoint: str,
) -> SearchResponse:
    container, observed = _results_container(payload)
    items = container.get("entities") or container.get("_list") or []
    return SearchResponse(
        results=[_parse_entity(i) for i in items if isinstance(i, dict)],
        call_id=call_id,
        source=source,
        data_status=data_status,
        endpoint=endpoint,
        observed_shape=observed,
    )


def parse_tag_search(
    payload: dict[str, Any],
    *,
    call_id: str,
    source: SourceKind,
    data_status: DataStatus,
    endpoint: str,
) -> TagSearchResponse:
    container, observed = _results_container(payload)
    items = container.get("tags") or container.get("_list") or []
    return TagSearchResponse(
        results=[_parse_scored_tag(i) for i in items if isinstance(i, dict)],
        call_id=call_id,
        source=source,
        data_status=data_status,
        endpoint=endpoint,
        observed_shape=observed,
    )


def parse_raw(
    payload: dict[str, Any],
    *,
    call_id: str,
    source: SourceKind,
    data_status: DataStatus,
    endpoint: str,
) -> RawResponse:
    container, observed = _results_container(payload)
    return RawResponse(
        data=payload,
        call_id=call_id,
        source=source,
        data_status=data_status,
        endpoint=endpoint,
        query=payload.get("query") if isinstance(payload.get("query"), dict) else None,
        observed_shape=observed or sorted(container.keys()),
    )
