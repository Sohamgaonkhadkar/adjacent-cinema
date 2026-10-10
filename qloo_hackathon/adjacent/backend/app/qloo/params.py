"""Strict parameter allowlist for the Qloo API.

Why this module exists
----------------------
Qloo **silently ignores** parameters it does not recognise. An empty result set
therefore cannot be distinguished from a typo. That makes "I assumed this
parameter worked" the single most dangerous failure mode in this project, so we
refuse to send anything we cannot point at documentation for.

Rules:
  * unknown parameter                        -> UnverifiedParameterError
  * documented for a different endpoint      -> UnverifiedParameterError
  * explicitly marked UNVERIFIED             -> UnverifiedParameterError
       (unless the caller passes allow_unverified=True, which only the probe
        script does while resolving an open question)
  * marked DEPRECATED                        -> DeprecatedParameterError
  * documented params combined invalidly     -> InvalidCombinationError
  * filter.type not a documented value       -> InvalidFilterTypeError

Every spec below records where it was verified. Anything without a source is
marked UNVERIFIED and listed as an open question in docs/API_NOTES.md.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .errors import (
    DeprecatedParameterError,
    InvalidCombinationError,
    InvalidFilterTypeError,
    InvalidValueError,
    ParamError,
    UnverifiedParameterError,
)

# ---------------------------------------------------------------------------
# Endpoints we claim to know.
# ---------------------------------------------------------------------------

EP_SEARCH = "/search"
EP_ENTITIES = "/entities"
EP_INSIGHTS = "/v2/insights"
EP_TAGS = "/v2/tags"
EP_AUDIENCES = "/v2/audiences"
EP_TRENDING = "/v2/trending"
EP_COMPARE = "/v2/analysis/compare"

KNOWN_ENDPOINTS: frozenset[str] = frozenset(
    {EP_SEARCH, EP_ENTITIES, EP_INSIGHTS, EP_TAGS, EP_AUDIENCES, EP_TRENDING, EP_COMPARE}
)

# ---------------------------------------------------------------------------
# filter.type values.
# ---------------------------------------------------------------------------

#: First-class entity types. `filter.results.entities` and `filter.popularity.*`
#: are documented for these (Entity Type Parameter Guide).
ENTITY_FILTER_TYPES: frozenset[str] = frozenset(
    {
        "urn:entity:artist",
        "urn:entity:book",
        "urn:entity:brand",
        "urn:entity:movie",
        "urn:entity:person",
        "urn:entity:place",
        "urn:entity:podcast",
        "urn:entity:tv_show",
        "urn:entity:video_game",
    }
)

#: Non-entity result shapes.
SPECIAL_FILTER_TYPES: frozenset[str] = frozenset({"urn:tag", "urn:demographics", "urn:heatmap"})

ALL_FILTER_TYPES: frozenset[str] = ENTITY_FILTER_TYPES | SPECIAL_FILTER_TYPES

#: Documented as deprecated — "should not be used for new integrations".
DEPRECATED_FILTER_TYPES: frozenset[str] = frozenset({"urn:entity:audience"})

#: Verified by the probe at runtime. Not used for validation, only reporting.
CRITICAL_FILTER_TYPE = "urn:entity:movie"

#: `/entities` external ID families (22) — verified on /reference/get-entities.
EXTERNAL_ID_FAMILIES: tuple[str, ...] = (
    "facebook",
    "goodreads",
    "goodreads_author",
    "igdb",
    "imdb",
    "instagram",
    "isbn10",
    "isbn13",
    "itunes",
    "lastfm",
    "library_of_congress",
    "metacritic",
    "michelin",
    "musicbrainz",
    "rottentomatoes",
    "soundcloud",
    "spotify",
    "tablet",
    "twitch",
    "twitter",
    "wikidata",
    "resy",
)

#: Extra `filter.type` values used by `/v2/trending` and `/v2/analysis/compare`.
NON_INSIGHTS_FILTER_TYPES: frozenset[str] = ENTITY_FILTER_TYPES | frozenset({"urn:entity:locality"})


class ParamKind(StrEnum):
    STR = "str"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    CSV = "csv"  # sequence -> comma-joined string
    ISO_DATE = "iso_date"


class ParamStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class ParamSpec:
    name: str  # wire name, e.g. "filter.type"
    kind: ParamKind
    endpoints: frozenset[str]  # where it may be sent
    required_on: frozenset[str] = frozenset()  # where it must be sent
    status: ParamStatus = ParamStatus.VERIFIED
    summary: str = ""
    source: str = ""
    open_question: str = ""
    #: Endpoints where this parameter is accepted but NOT verified. Verification is
    #: per-endpoint: `filter.parents.types` is documented for /v2/audiences (audience
    #: categories) while its behaviour on /v2/insights is unverified.
    unverified_on: frozenset[str] = frozenset()

    def status_for(self, endpoint: str) -> ParamStatus:
        if self.unverified_on and endpoint in self.unverified_on:
            return ParamStatus.UNVERIFIED
        return self.status

    def is_unverified_anywhere(self) -> bool:
        return self.status is ParamStatus.UNVERIFIED or bool(self.unverified_on)

    @property
    def kwarg(self) -> str:
        """Python-friendly keyword name: `filter.type` -> `filter_type`."""
        return self.name.replace(".", "_").replace("-", "_")


# ---------------------------------------------------------------------------
# The registry.
# ---------------------------------------------------------------------------

_INSIGHTS = frozenset({EP_INSIGHTS})
_TAGS = frozenset({EP_TAGS})
_AUDIENCES = frozenset({EP_AUDIENCES})

_SPECS: tuple[ParamSpec, ...] = (
    # ---------------------------- /search --------------------------------
    ParamSpec(
        "query",
        ParamKind.STR,
        frozenset({EP_SEARCH}),
        frozenset({EP_SEARCH}),
        summary="Free-text search string",
        source="docs.qloo.com/reference/get-search",
    ),
    ParamSpec(
        "types",
        ParamKind.CSV,
        frozenset({EP_SEARCH}),
        summary="Restrict results to entity types",
        source="docs.qloo.com/reference/get-search",
    ),
    ParamSpec(
        "take",
        ParamKind.INT,
        frozenset({EP_SEARCH, EP_INSIGHTS, EP_TAGS, EP_AUDIENCES, EP_TRENDING, EP_COMPARE}),
        summary="Max results (docs: <=50)",
        source="docs.qloo.com/reference/parameter-overview",
    ),
    ParamSpec(
        "page",
        ParamKind.INT,
        frozenset({EP_SEARCH, EP_INSIGHTS, EP_TAGS, EP_AUDIENCES, EP_TRENDING, EP_COMPARE}),
        summary="Page number (docs: 1..100)",
        source="docs.qloo.com/reference/parameter-overview",
    ),
    ParamSpec(
        "offset",
        ParamKind.INT,
        frozenset({EP_COMPARE}),
        summary="Offset for compare pagination",
        source="docs.qloo.com/reference/analysis-compare",
    ),
    ParamSpec(
        "feature.typo_tolerance",
        ParamKind.BOOL,
        frozenset({EP_SEARCH, EP_TAGS}),
        summary="Tolerate typos in the query string",
        source="docs.qloo.com/reference/get-search",
    ),
    # --------------------------- /entities -------------------------------
    ParamSpec(
        "entity_ids",
        ParamKind.CSV,
        frozenset({EP_ENTITIES}),
        summary="Batch lookup by Qloo UUID",
        source="docs.qloo.com/reference/get-entities",
    ),
    # NOTE: take/page are deliberately NOT registered for /entities. The docs we
    # read do not show pagination for it, so we do not send it. Verify before adding.
    # `external.<family>.ids` specs are generated from EXTERNAL_ID_FAMILIES.
    # 404 is a data outcome here (entity not in Qloo), never retried.
    # --------------------------- /v2/insights ----------------------------
    ParamSpec(
        "filter.type",
        ParamKind.STR,
        frozenset({EP_INSIGHTS, EP_TRENDING, EP_COMPARE}),
        frozenset({EP_INSIGHTS, EP_TRENDING, EP_COMPARE}),
        summary="What kind of result is requested",
        source="docs.qloo.com/reference/available-parameters-by-entity-type",
    ),
    ParamSpec(
        "filter.subtype",
        ParamKind.CSV,
        frozenset({EP_INSIGHTS, EP_COMPARE}),
        summary="Narrow within a type, e.g. urn:tag:genre",
        source="docs.qloo.com/reference/analysis-compare",
    ),
    ParamSpec(
        "signal.interests.entities",
        ParamKind.CSV,
        _INSIGHTS | frozenset({EP_TRENDING, EP_COMPARE}),
        summary="Seed entity ids (the taste vector)",
        source="docs.qloo.com/reference/insights-api-deep-dive",
    ),
    ParamSpec(
        "signal.interests.tags",
        ParamKind.CSV,
        _INSIGHTS,
        summary="Seed tag ids",
        source="docs.qloo.com/reference/insights-api-deep-dive",
    ),
    ParamSpec(
        "signal.demographics.audiences",
        ParamKind.CSV,
        _INSIGHTS,
        summary="Qloo audience ids as a signal",
        source="docs.qloo.com/reference/demographics-use-case",
    ),
    ParamSpec(
        "signal.demographics.age",
        ParamKind.CSV,
        _INSIGHTS,
        summary="Age buckets as a signal",
        source="docs.qloo.com/reference/demographics-use-case",
    ),
    ParamSpec(
        "signal.demographics.gender",
        ParamKind.CSV,
        _INSIGHTS,
        summary="Gender as a signal",
        source="docs.qloo.com/reference/demographics-use-case",
    ),
    ParamSpec(
        "filter.results.entities",
        ParamKind.CSV,
        _INSIGHTS,
        summary="Score exactly these entities inside one normalisation",
        source="docs.qloo.com/reference/available-parameters-by-entity-type",
        open_question="Does it return ALL supplied ids scored, or only the top `take`? (probe D)",
    ),
    ParamSpec(
        "filter.exclude.entities",
        ParamKind.CSV,
        _INSIGHTS,
        summary="Exclude entities from results",
        source="docs.qloo.com/reference/insights-api-deep-dive",
    ),
    ParamSpec(
        "filter.popularity.min",
        ParamKind.FLOAT,
        _INSIGHTS | _TAGS | _AUDIENCES,
        summary="Popularity percentile floor, 0..1",
        source="docs.qloo.com/reference/parameter-overview",
    ),
    ParamSpec(
        "filter.popularity.max",
        ParamKind.FLOAT,
        _INSIGHTS | _TAGS | _AUDIENCES,
        summary="Popularity percentile ceiling, 0..1",
        source="docs.qloo.com/reference/parameter-overview",
    ),
    ParamSpec(
        "filter.location.query",
        ParamKind.STR,
        _INSIGHTS | frozenset({EP_COMPARE}),
        summary="Free-text locality ('Portland, Oregon'); fuzzy-matched",
        source="docs.qloo.com/reference/heatmaps-use-case",
    ),
    ParamSpec(
        "filter.location.radius",
        ParamKind.FLOAT,
        _INSIGHTS,
        summary="Radius in MILES; 0 disables default boundary padding",
        source="docs.qloo.com/reference/heatmaps-use-case",
    ),
    ParamSpec(
        "output.heatmap.boundary",
        ParamKind.STR,
        _INSIGHTS,
        summary="Boundary scheme, e.g. urn:geohash",
        source="docs.qloo.com/reference/heatmaps-use-case",
    ),
    ParamSpec(
        "feature.explainability",
        ParamKind.BOOL,
        _INSIGHTS,
        summary="Per-recommendation attribution of input entities",
        source="docs.qloo.com/reference/insights-api-deep-dive",
        open_question="Is it exposed on the hackathon key, and how large is the payload at take=50? (probe F)",
    ),
    ParamSpec(
        "diversify.by",
        ParamKind.STR,
        _INSIGHTS,
        summary="Spread results across a tag family; docs show ONE value",
        source="docs.qloo.com/reference/insights-api-deep-dive",
    ),
    ParamSpec(
        "backfill.cross_domain.take",
        ParamKind.INT,
        _INSIGHTS,
        summary="<=20 cross-domain filler results appended BELOW primary results",
        source="docs.qloo.com/reference/insights-api-deep-dive",
    ),
    ParamSpec(
        "backfill.content_based.take",
        ParamKind.INT,
        _INSIGHTS,
        summary="<=10 content-similarity filler results appended BELOW primary results",
        source="docs.qloo.com/reference/insights-api-deep-dive",
    ),
    # --- explicitly NOT verified; must be opted into, never assumed --------
    ParamSpec(
        "filter.parents.types",
        ParamKind.CSV,
        _INSIGHTS | _TAGS | _AUDIENCES,
        summary="Parent type scoping. On /v2/audiences this takes AUDIENCE CATEGORY urns.",
        source="docs.qloo.com/reference/get-audiences (audience categories)",
        unverified_on=_INSIGHTS | _TAGS,
        open_question="For filter.type=urn:tag on /v2/insights, does filter.parents.types accept "
        "urn:entity:movie,urn:entity:tv_show, or only urn:audience:* "
        "categories? Passing the wrong family returns an EMPTY set, "
        "not an error, so this must be tested before it is relied on. (probe B2)",
    ),
    ParamSpec(
        "filter.tags",
        ParamKind.CSV,
        _INSIGHTS | _TAGS,
        status=ParamStatus.UNVERIFIED,
        summary="Appears in our project spec; not located in the current docs.",
        source="",
        open_question="Does `filter.tags` exist? The documented tag scoping params "
        "are `filter.tag.types` (/v2/tags) and `filter.parents.types`. "
        "(probe G2)",
    ),
    ParamSpec(
        "filter.tag.types",
        ParamKind.CSV,
        _TAGS,
        summary="Restrict tag results to subtypes, e.g. urn:tag:genre",
        source="docs.qloo.com/reference/search-tags",
    ),
    ParamSpec(
        "signal.location.query",
        ParamKind.STR,
        _INSIGHTS,
        status=ParamStatus.UNVERIFIED,
        summary="Locality bias on a non-heatmap query; unclear whether it changes results.",
        source="",
        open_question="Does signal.location.query actually alter entity results for "
        "urn:entity:artist, or is it a no-op that gets silently dropped? "
        "(probe C2)",
    ),
    ParamSpec(
        "feature.semantic_search",
        ParamKind.BOOL,
        _TAGS,
        status=ParamStatus.UNVERIFIED,
        summary="Semantic tag search — documented as BETA, may change.",
        source="docs.qloo.com/reference/search-tags (beta)",
        open_question="Is the beta `feature.semantic_search` enabled on the hackathon key?",
    ),
    # ---------------------------- /v2/tags -------------------------------
    ParamSpec(
        "filter.query",
        ParamKind.STR,
        _TAGS | _AUDIENCES,
        summary="Free-text query for tag/audience lookup",
        source="docs.qloo.com/reference/search-tags",
    ),
    ParamSpec(
        "filter.results.tags",
        ParamKind.CSV,
        _TAGS,
        summary="Grade these specific tags against the query",
        source="docs.qloo.com/reference/search-tags",
    ),
    # -------------------------- /v2/audiences ----------------------------
    ParamSpec(
        "filter.audience.types",
        ParamKind.CSV,
        _AUDIENCES,
        summary="Restrict audience results by type",
        source="docs.qloo.com/reference/get-audiences",
    ),
    ParamSpec(
        "filter.results.audiences",
        ParamKind.CSV,
        _AUDIENCES,
        summary="Grade these specific audiences",
        source="docs.qloo.com/reference/get-audiences",
    ),
    # --------------------------- /v2/trending ----------------------------
    ParamSpec(
        "filter.start_date",
        ParamKind.ISO_DATE,
        frozenset({EP_TRENDING}),
        frozenset({EP_TRENDING}),
        summary="REQUIRED. ISO date.",
        source="docs.qloo.com/reference/get-trending",
    ),
    ParamSpec(
        "filter.end_date",
        ParamKind.ISO_DATE,
        frozenset({EP_TRENDING}),
        frozenset({EP_TRENDING}),
        summary="REQUIRED. ISO date.",
        source="docs.qloo.com/reference/get-trending",
    ),
    # ---------------------- /v2/analysis/compare -------------------------
    ParamSpec(
        "a.signal.interests.entities",
        ParamKind.CSV,
        frozenset({EP_COMPARE}),
        frozenset({EP_COMPARE}),
        summary="REQUIRED. Group A entities.",
        source="docs.qloo.com/reference/analysis-compare",
    ),
    ParamSpec(
        "b.signal.interests.entities",
        ParamKind.CSV,
        frozenset({EP_COMPARE}),
        frozenset({EP_COMPARE}),
        summary="REQUIRED. Group B entities.",
        source="docs.qloo.com/reference/analysis-compare",
    ),
    ParamSpec(
        "model",
        ParamKind.STR,
        frozenset({EP_COMPARE}),
        summary="descriptive | predictive",
        source="docs.qloo.com/reference/analysis-compare",
    ),
)

#: `external.<family>.ids` for every documented external ID family.
_EXTERNAL_SPECS: tuple[ParamSpec, ...] = tuple(
    ParamSpec(
        f"external.{family}.ids",
        ParamKind.CSV,
        frozenset({EP_ENTITIES}),
        summary=f"Look up entities by their {family} id",
        source="docs.qloo.com/reference/get-entities",
    )
    for family in EXTERNAL_ID_FAMILIES
)

REGISTRY: dict[str, ParamSpec] = {spec.name: spec for spec in (*_SPECS, *_EXTERNAL_SPECS)}
KWARG_TO_WIRE: dict[str, str] = {spec.kwarg: spec.name for spec in REGISTRY.values()}

#: Largest documented `take`. Exceeding it is a client-side bug, not a Qloo decision.
MAX_TAKE = 50
MIN_PAGE, MAX_PAGE = 1, 100

#: filter.type values for which each cross-cutting param is documented.
_RESULTS_ENTITIES_TYPES = ENTITY_FILTER_TYPES
_DEMOGRAPHIC_SIGNAL_TYPES = ENTITY_FILTER_TYPES | {"urn:heatmap"}
_POPULARITY_TYPES = ENTITY_FILTER_TYPES
_LOCATION_TYPES = ENTITY_FILTER_TYPES | {"urn:heatmap"}
_DIVERSIFY_TYPES = ENTITY_FILTER_TYPES
_BACKFILL_TYPES = ENTITY_FILTER_TYPES


@dataclass
class BuiltParams:
    """Result of validation: wire parameters plus everything we learned."""

    endpoint: str
    params: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    unverified_used: list[str] = field(default_factory=list)
    dropped_empty: list[str] = field(default_factory=list)
    filter_type: str | None = None

    def as_query(self) -> dict[str, str]:
        """Flatten to the string mapping httpx will encode."""
        out: dict[str, str] = {}
        for key, value in self.params.items():
            if isinstance(value, bool):
                out[key] = "true" if value else "false"
            elif isinstance(value, (list, tuple)):
                out[key] = ",".join(str(v) for v in value)
            else:
                out[key] = str(value)
        return out


def _coerce(spec: ParamSpec, value: Any) -> Any:
    kind = spec.kind
    if kind is ParamKind.BOOL:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
            return value.strip().lower() == "true"
        raise InvalidValueError(f"{spec.name} must be a boolean, got {value!r}", parameter=spec.name)
    if kind is ParamKind.INT:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise InvalidValueError(
                f"{spec.name} must be an integer, got {value!r}", parameter=spec.name
            ) from exc
    if kind is ParamKind.FLOAT:
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise InvalidValueError(
                f"{spec.name} must be a number, got {value!r}", parameter=spec.name
            ) from exc
    if kind is ParamKind.ISO_DATE:
        if isinstance(value, _dt.date):
            return value.isoformat()
        text = str(value)
        try:
            _dt.date.fromisoformat(text)
        except ValueError as exc:
            raise InvalidValueError(
                f"{spec.name} must be an ISO date (YYYY-MM-DD), got {text!r}", parameter=spec.name
            ) from exc
        return text
    if kind is ParamKind.CSV:
        if isinstance(value, str):
            return value
        if isinstance(value, Iterable) and not isinstance(value, (bytes, Mapping)):
            return [str(v).strip() for v in value if str(v).strip()]
        raise InvalidValueError(
            f"{spec.name} must be a sequence of strings, got {value!r}", parameter=spec.name
        )
    # ParamKind.STR — a single value only. A multi-valued sequence is a caller bug,
    # not something to flatten silently.
    if isinstance(value, (list, tuple)):
        cleaned = [str(v) for v in value if str(v).strip()]
        if len(cleaned) == 1:
            return cleaned[0]
        raise InvalidValueError(
            f"{spec.name} accepts a single value (got {len(cleaned)}). "
            "The official docs document one value for this parameter.",
            parameter=spec.name,
        )
    return str(value)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, bytes)) and value.strip() == "":
        return True
    return isinstance(value, Sequence) and not isinstance(value, str) and len(value) == 0


def filter_type_of(params: Mapping[str, Any]) -> str | None:
    value = params.get("filter.type")
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else None
    return str(value) if value not in (None, "") else None


def validate_filter_type(filter_type: str, *, endpoint: str) -> None:
    if filter_type in DEPRECATED_FILTER_TYPES:
        raise DeprecatedParameterError(
            f"filter.type={filter_type} is documented as DEPRECATED "
            "('should not be used for new integrations'). Use /v2/audiences with "
            "signal.demographics.audiences instead.",
            parameter="filter.type",
            endpoint=endpoint,
        )
    allowed = NON_INSIGHTS_FILTER_TYPES if endpoint in {EP_TRENDING, EP_COMPARE} else ALL_FILTER_TYPES
    if filter_type not in allowed:
        raise InvalidFilterTypeError(
            f"filter.type={filter_type!r} is not a documented value for {endpoint}. "
            f"Allowed: {', '.join(sorted(allowed))}",
            parameter="filter.type",
            endpoint=endpoint,
        )


def validate_combination(
    endpoint: str,
    params: Mapping[str, Any],
    *,
    warnings: list[str] | None = None,
) -> str | None:
    """Cross-parameter rules. Returns the filter.type it validated, if any."""
    warns = warnings if warnings is not None else []
    filter_type = filter_type_of(params)
    if filter_type is not None:
        validate_filter_type(filter_type, endpoint=endpoint)

    def requires(condition: bool, message: str, param: str) -> None:
        if not condition:
            raise InvalidCombinationError(message, parameter=param, endpoint=endpoint)

    if "filter.results.entities" in params:
        requires(
            filter_type in _RESULTS_ENTITIES_TYPES,
            "filter.results.entities only scores ENTITY types "
            f"(got filter.type={filter_type!r}). It is NOT documented for urn:tag, "
            "urn:demographics or urn:heatmap.",
            "filter.results.entities",
        )

    for demo_param in (
        "signal.demographics.audiences",
        "signal.demographics.age",
        "signal.demographics.gender",
    ):
        if demo_param in params:
            requires(
                filter_type in _DEMOGRAPHIC_SIGNAL_TYPES,
                f"{demo_param} is documented for entity types and heatmaps, not for "
                f"filter.type={filter_type!r}.",
                demo_param,
            )

    if "signal.demographics.audiences" in params:
        warns.append(
            "Multiple signal.demographics.audiences values are MERGED into one combined "
            "profile by Qloo — they do not produce per-audience result sets."
        )

    for pop_param in ("filter.popularity.min", "filter.popularity.max"):
        if pop_param in params:
            requires(
                filter_type in _POPULARITY_TYPES,
                f"{pop_param} is not documented for filter.type={filter_type!r}.",
                pop_param,
            )
            value = params[pop_param]
            if not isinstance(value, (int, float)) or not (0.0 <= float(value) <= 1.0):
                raise InvalidValueError(
                    f"{pop_param} must be between 0 and 1 (a percentile), got {value!r}",
                    parameter=pop_param,
                )

    if (
        "filter.popularity.min" in params
        and "filter.popularity.max" in params
        and float(params["filter.popularity.min"]) > float(params["filter.popularity.max"])
    ):
        raise InvalidCombinationError(
            "filter.popularity.min must be <= filter.popularity.max "
            f"(got {params['filter.popularity.min']} > {params['filter.popularity.max']})",
            parameter="filter.popularity.min",
        )

    if "filter.location.query" in params:
        requires(
            filter_type in _LOCATION_TYPES,
            f"filter.location.query is documented for entity types and heatmaps, not "
            f"filter.type={filter_type!r}.",
            "filter.location.query",
        )
    if filter_type == "urn:heatmap":
        requires(
            "filter.location.query" in params,
            "filter.type=urn:heatmap requires filter.location.query — the heatmap is "
            "always scoped to a locality.",
            "filter.location.query",
        )
        heatmap_signals = {
            "signal.interests.entities",
            "signal.interests.tags",
            "signal.demographics.audiences",
        }
        requires(
            any(p in params for p in heatmap_signals),
            "filter.type=urn:heatmap requires at least one signal "
            "(signal.interests.entities, signal.interests.tags or "
            "signal.demographics.audiences) — a heatmap with no signal has no meaning.",
            "signal.interests.entities",
        )
        warns.append(
            "Heatmap cells are MODEL ESTIMATES of taste concentration, not counts of "
            "people, and not attendance."
        )

    for heatmap_param in ("output.heatmap.boundary", "filter.location.radius"):
        if heatmap_param in params:
            requires(
                filter_type == "urn:heatmap",
                f"{heatmap_param} is only meaningful with filter.type=urn:heatmap.",
                heatmap_param,
            )

    if "diversify.by" in params:
        requires(
            filter_type in _DIVERSIFY_TYPES,
            f"diversify.by is not documented for filter.type={filter_type!r}.",
            "diversify.by",
        )
        value = params["diversify.by"]
        if isinstance(value, (list, tuple)) and len(value) > 1:
            raise InvalidValueError(
                f"diversify.by accepts a SINGLE value per the official docs (got {len(value)}).",
                parameter="diversify.by",
            )

    for backfill_param in ("backfill.cross_domain.take", "backfill.content_based.take"):
        if backfill_param in params:
            requires(
                filter_type in _BACKFILL_TYPES,
                f"{backfill_param} is not documented for filter.type={filter_type!r}.",
                backfill_param,
            )
            caps = {  # documented maxima
                "backfill.cross_domain.take": 20,
                "backfill.content_based.take": 10,
            }[backfill_param]
            if int(params[backfill_param]) > caps:
                raise InvalidValueError(
                    f"{backfill_param} is documented with a maximum of {caps}.",
                    parameter=backfill_param,
                )
            if int(params[backfill_param]) > 0:
                warns.append(
                    f"{backfill_param} appends CONTENT-SIMILARITY FILLER below primary "
                    "results. Backfill must be detected and labelled, never presented as "
                    "affinity evidence."
                )

    if filter_type == "urn:tag":
        requires(
            "signal.interests.entities" in params,
            "filter.type=urn:tag is used here to characterise a programme, which requires "
            "signal.interests.entities as the taste vector.",
            "signal.interests.entities",
        )

    if filter_type == "urn:demographics":
        requires(
            "signal.interests.entities" in params,
            "filter.type=urn:demographics requires a signal to describe. Adjacent uses "
            "signal.interests.entities (the programme).",
            "signal.interests.entities",
        )

    if "take" in params:
        take = int(params["take"])
        if take < 1 or take > MAX_TAKE:
            raise InvalidValueError(
                f"take must be between 1 and {MAX_TAKE} (documented maximum), got {take}",
                parameter="take",
            )
    if "page" in params:
        page = int(params["page"])
        if page < MIN_PAGE or page > MAX_PAGE:
            raise InvalidValueError(
                f"page must be between {MIN_PAGE} and {MAX_PAGE}, got {page}",
                parameter="page",
            )

    if endpoint == EP_TRENDING:
        for required in ("filter.type", "filter.start_date", "filter.end_date"):
            requires(
                required in params,
                f"{required} is REQUIRED by /v2/trending (it is not a no-argument 'what is hot' endpoint).",
                required,
            )

    if endpoint == EP_COMPARE:
        for required in ("a.signal.interests.entities", "b.signal.interests.entities", "filter.type"):
            requires(
                required in params,
                f"{required} is REQUIRED by {EP_COMPARE}.",
                required,
            )

    if endpoint == EP_SEARCH and "query" not in params:
        requires(False, "query is REQUIRED by /search.", "query")

    return filter_type


def build_params(
    endpoint: str,
    values: Mapping[str, Any] | None = None,
    *,
    allow_unverified: bool = False,
    check_required: bool = True,
    **kwargs: Any,
) -> BuiltParams:
    """Validate and normalise parameters for one Qloo endpoint.

    Keys may be wire names ("filter.type") or python kwargs ("filter_type").
    Raises a `ParamError` subclass for anything we cannot justify.
    """
    if endpoint not in KNOWN_ENDPOINTS:
        raise ParamError(f"Unknown Qloo endpoint {endpoint!r}", endpoint=endpoint)

    merged: dict[str, Any] = dict(values or {})
    merged.update(kwargs)

    built = BuiltParams(endpoint=endpoint)
    wire_values: dict[str, Any] = {}

    for key, raw_value in merged.items():
        wire = KWARG_TO_WIRE.get(key, key)
        spec = REGISTRY.get(wire)
        if spec is None:
            raise UnverifiedParameterError(
                f"{wire!r} is not in the verified parameter allowlist for {endpoint}. "
                "Qloo silently ignores unknown parameters, so this would have produced a "
                "silently wrong (empty) result. Add it to app/qloo/params.py only with a "
                "documentation source.",
                parameter=wire,
                endpoint=endpoint,
            )
        if endpoint not in spec.endpoints:
            raise UnverifiedParameterError(
                f"{wire!r} is documented for {sorted(spec.endpoints)} but not for {endpoint}.",
                parameter=wire,
                endpoint=endpoint,
            )
        # An omitted parameter is not "sent", so its verification status is
        # irrelevant — drop it before the status gate. (Anything actually being
        # sent must clear the gate below.)
        if _is_empty(raw_value):
            built.dropped_empty.append(wire)
            continue
        effective_status = spec.status_for(endpoint)
        if effective_status is ParamStatus.DEPRECATED:
            raise DeprecatedParameterError(
                f"{wire!r} is deprecated for {endpoint}.", parameter=wire, endpoint=endpoint
            )
        if effective_status is ParamStatus.UNVERIFIED and not allow_unverified:
            raise UnverifiedParameterError(
                f"{wire!r} is UNVERIFIED for {endpoint}. "
                f"Open question: {spec.open_question or 'unresolved'} "
                "Pass allow_unverified=True only from the probe script while resolving this.",
                parameter=wire,
                endpoint=endpoint,
            )
        if effective_status is ParamStatus.UNVERIFIED:
            built.unverified_used.append(wire)
            built.warnings.append(f"UNVERIFIED parameter sent to {endpoint}: {wire}")
        wire_values[wire] = _coerce(spec, raw_value)

    if check_required:
        missing = sorted(
            name
            for name, spec in REGISTRY.items()
            if endpoint in spec.required_on and name not in wire_values
        )
        if missing:
            raise InvalidCombinationError(
                f"{endpoint} requires: {', '.join(missing)}",
                parameter=missing[0],
                endpoint=endpoint,
            )

    built.filter_type = validate_combination(endpoint, wire_values, warnings=built.warnings)
    built.params = wire_values
    return built


def registry_summary() -> list[dict[str, Any]]:
    """Machine-readable registry, used by /debug/params and by API_NOTES.md."""
    rows = []
    for spec in sorted(REGISTRY.values(), key=lambda s: (s.status.value, s.name)):
        rows.append(
            {
                "param": spec.name,
                "kind": spec.kind.value,
                "endpoints": sorted(spec.endpoints),
                "required_on": sorted(spec.required_on),
                "status": spec.status.value,
                "unverified_on": sorted(spec.unverified_on),
                "status_per_endpoint": {
                    endpoint: spec.status_for(endpoint).value for endpoint in sorted(spec.endpoints)
                },
                "summary": spec.summary,
                "source": spec.source or None,
                "open_question": spec.open_question or None,
            }
        )
    return rows


def unverified_params() -> list[ParamSpec]:
    """Every parameter that is unverified for at least one endpoint it accepts."""
    return [s for s in REGISTRY.values() if s.is_unverified_anywhere()]


def unverified_endpoints(spec: ParamSpec) -> list[str]:
    """Which of this parameter's endpoints are unverified."""
    return sorted(e for e in spec.endpoints if spec.status_for(e) is ParamStatus.UNVERIFIED)
