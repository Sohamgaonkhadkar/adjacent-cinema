"""FilmSponsor brand discovery — evidence-backed, never fabricated.

Runs the bounded FilmSponsor discovery stages over an injected Qloo client and
the production ``EntityResolver``:

    1. film identity resolution (VERIFIED usable; AMBIGUOUS/MISMATCH/UNRESOLVED
       are preserved and reported — never promoted, never reselected)
    2. theme canonicalisation via GET /v2/tags (exact-tag match only)
    3. brand discovery from resolver-verified film entities
       (GET /v2/insights filter.type=urn:entity:brand)
    4. brand discovery from canonical theme tags
    5. optional combined exploratory query — only when the two separate
       queries produced sufficiently distinct typed-brand sets

Rules preserved from the live gate (``scripts/filmsponsor_live_gate.py``):
* Only entities with explicit brand-type evidence are presented as brands.
* Affinity values from separately seeded queries are never compared; the
  combined stage records ID/shape comparison only.
* A valid affinity of 0 is kept as 0; a missing affinity stays None.
* Errors are projected to safe fields (type/kind/status/endpoint/call_id);
  raw provider payloads are never stored in the report.
* Cultural affinity is not sponsorship likelihood. The report always carries
  its interpretation limits.

This module performs live calls only through the injected client. Without a
configured key the API layer refuses before reaching here — nothing in this
product fabricates brands or affinity values for display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MOVIE_ENTITY_TYPE = "urn:entity:movie"
BRAND_ENTITY_TYPE = "urn:entity:brand"

#: Budget for one discovery request (mirrors the gate's bounded posture).
MAX_LOGICAL_GETS = 12
TAG_TAKE = 5
BRAND_TAKE = 10
MAX_FILMS = 5
MAX_THEMES = 5

INTERPRETATION_LIMITS = [
    "Cultural affinity is not sponsorship likelihood, eligibility, budget, availability, or ROI.",
    "Brand candidates are for human relevance review only; no outreach or contact discovery is performed.",
    "Affinity values are per-query normalised; values from different queries are not comparable.",
    "Only entities with explicit brand-type evidence are presented as brands.",
]


@dataclass
class DiscoveryBudget:
    """Counts logical GETs and refuses work it cannot afford."""

    max_logical_gets: int = MAX_LOGICAL_GETS
    logical_gets: int = 0
    halted: bool = False
    halt_reason: dict[str, Any] | None = None

    def charge(self) -> bool:
        if self.halted:
            return False
        if self.logical_gets >= self.max_logical_gets:
            self.halted = True
            self.halt_reason = {
                "error_type": "BudgetExhausted",
                "kind": "budget_exhausted",
                "message": "Discovery stopped at the bounded live-call budget.",
            }
            return False
        self.logical_gets += 1
        return True


def safe_error(exc: Exception) -> dict[str, Any]:
    """Project an exception to safe fields; never emit message/payload text."""
    return {
        "error_type": type(exc).__name__,
        "kind": getattr(exc, "kind", None),
        "status": getattr(exc, "status", None),
        "endpoint": getattr(exc, "endpoint", None),
        "call_id": getattr(exc, "call_id", None),
    }


def _is_fatal(error: dict[str, Any] | None) -> bool:
    """A 404 is a documented data outcome; anything else halts the stage chain."""
    return error is not None and error.get("status") != 404


def _entity_types(entity: Any) -> set[str]:
    raw = getattr(entity, "raw", None)
    raw = raw if isinstance(raw, dict) else {}
    values: set[str] = set()
    for value in (
        getattr(entity, "type", None),
        getattr(entity, "subtype", None),
        raw.get("type"),
        raw.get("subtype"),
    ):
        if isinstance(value, str) and value:
            values.add(value)
    raw_types = raw.get("types")
    if isinstance(raw_types, str):
        values.add(raw_types)
    elif isinstance(raw_types, list):
        values.update(str(v) for v in raw_types if v)
    return values


def _is_typed_brand(entity: Any) -> bool:
    return BRAND_ENTITY_TYPE in _entity_types(entity)


def _affinity(entity: Any) -> float | None:
    """Preserve a valid 0.0; keep missing affinity as None (zero ≠ missing)."""
    value = getattr(entity, "affinity", None)
    return float(value) if isinstance(value, (int, float)) else None


def _brand_observation(entity: Any, *, source: str, call_id: str | None) -> dict[str, Any]:
    return {
        "entity_id": getattr(entity, "entity_id", None),
        "name": getattr(entity, "name", None),
        "popularity": getattr(entity, "popularity", None),
        "type_evidence": sorted(t for t in _entity_types(entity) if t.startswith("urn:entity:")),
        "observation": {
            "source": source,
            "affinity": _affinity(entity),
            "band": getattr(getattr(entity, "band", None), "value", getattr(entity, "band", None)),
            "call_id": call_id,
        },
    }


def _split_brand_results(
    response: Any, *, source: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Typed brands vs everything else — non-brand types are reported, not hidden."""
    brands: list[dict[str, Any]] = []
    others: list[dict[str, Any]] = []
    call_id = getattr(response, "call_id", None)
    for entity in getattr(response, "results", []) or []:
        if _is_typed_brand(entity):
            brands.append(_brand_observation(entity, source=source, call_id=call_id))
        else:
            others.append(
                {
                    "entity_id": getattr(entity, "entity_id", None),
                    "name": getattr(entity, "name", None),
                    "reason_code": "not_brand_typed",
                    "type_evidence": sorted(
                        t for t in _entity_types(entity) if t.startswith("urn:entity:")
                    ),
                    "call_ids": [call_id] if call_id else [],
                }
            )
    return brands, others


def _merge_brand_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per candidate entity; each query contributes its own observation.

    Observations keep their own source, affinity and call_id — values from
    separately seeded queries are never merged or compared.
    """
    by_id: dict[Any, dict[str, Any]] = {}
    for row in rows:
        key = row.get("entity_id") or ("name", row.get("name"))
        entry = by_id.setdefault(
            key,
            {
                "entity_id": row.get("entity_id"),
                "name": row.get("name"),
                "popularity": row.get("popularity"),
                "type_evidence": row.get("type_evidence", []),
                "observations": [],
            },
        )
        entry["observations"].append(row["observation"])
    return list(by_id.values())


def _merge_other_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[Any, dict[str, Any]] = {}
    for row in rows:
        key = (row.get("entity_id"), row.get("reason_code"))
        entry = by_key.setdefault(key, {k: v for k, v in row.items() if k != "call_ids"})
        entry.setdefault("call_ids", [])
        for call_id in row.get("call_ids", []):
            if call_id and call_id not in entry["call_ids"]:
                entry["call_ids"].append(call_id)
    return list(by_key.values())


def _resolution_record(result: Any) -> dict[str, Any]:
    """Project a ResolvedEntity to safe fields (no raw payloads, no notes text
    beyond the resolver's own verification notes)."""
    status = getattr(getattr(result, "match_status", None), "value", None) or str(
        getattr(result, "match_status", "UNRESOLVED")
    )
    method = getattr(getattr(result, "match_method", None), "value", None)
    candidate = None
    if getattr(result, "qloo_entity_id", None):
        candidate = {
            "entity_id": result.qloo_entity_id,
            "name": getattr(result, "qloo_name", None),
            "year": getattr(result, "qloo_year", None),
            "type": getattr(result, "qloo_entity_type", None),
        }
    return {
        "input_title": getattr(result, "input_title", None),
        "input_year": getattr(result, "input_year", None),
        "input_external_id": getattr(result, "input_external_id", None),
        "match_status": status,
        "match_method": method,
        "usable": bool(getattr(result, "resolved", False)),
        "candidate": candidate,
        "verification_notes": list(getattr(result, "verification_notes", []) or []),
        "call_id": getattr(result, "call_id", None),
        "related_call_ids": list(getattr(result, "related_call_ids", []) or []),
    }


@dataclass
class FilmInput:
    title: str
    year: int | None = None
    imdb_id: str | None = None


@dataclass
class DiscoveryOutcome:
    report: dict[str, Any]
    data_status: str = "measured"
    call_ids: list[str] = field(default_factory=list)


async def discover_brand_evidence(
    *,
    client: Any,
    resolver: Any,
    films: list[FilmInput],
    themes: list[str],
    budget: DiscoveryBudget | None = None,
) -> DiscoveryOutcome:
    """Run the bounded discovery chain. Raises nothing for data outcomes —
    provider failures are recorded as safe errors and halt the chain.
    """
    budget = budget or DiscoveryBudget()
    report: dict[str, Any] = {
        "data_status": "measured",
        "source": "qloo",
        "films": [],
        "theme_canonicalization": [],
        "stages": {},
        "brands": [],
        "non_brand_results": [],
        "interpretation_limits": list(INTERPRETATION_LIMITS),
        "call_ids": [],
    }

    async def call(awaitable: Any) -> tuple[Any | None, dict[str, Any] | None]:
        if not budget.charge():
            return None, budget.halt_reason
        try:
            response = await awaitable
        except Exception as exc:  # projected to safe fields below
            error = safe_error(exc)
            if _is_fatal(error):
                budget.halted = True
                budget.halt_reason = error
            return None, error
        call_id = getattr(response, "call_id", None)
        if call_id and call_id not in report["call_ids"]:
            report["call_ids"].append(call_id)
        return response, None

    # ---- Stage 1: film identity resolution -------------------------------
    for film in films[:MAX_FILMS]:
        if budget.halted:
            break
        if not budget.charge():
            break
        try:
            result = await resolver.resolve_item(
                film.title,
                film.year,
                film.imdb_id,
                "imdb" if film.imdb_id else None,
            )
        except Exception as exc:  # projected to safe fields below
            error = safe_error(exc)
            if _is_fatal(error):
                budget.halted = True
                budget.halt_reason = error
            report["films"].append(
                {
                    "input_title": film.title,
                    "input_year": film.year,
                    "match_status": "UNRESOLVED",
                    "usable": False,
                    "candidate": None,
                    "error": error,
                }
            )
            continue
        record = _resolution_record(result)
        for ref in [record["call_id"], *record["related_call_ids"]]:
            if ref and ref not in report["call_ids"]:
                report["call_ids"].append(ref)
        report["films"].append(record)

    verified = [f for f in report["films"] if f.get("usable") and f.get("candidate")]
    report["stages"]["film_resolution"] = {
        "verified_count": len(verified),
        "input_count": len(films[:MAX_FILMS]),
        "rule": (
            "Only resolver-VERIFIED films seed brand signals; AMBIGUOUS, MISMATCH "
            "and UNRESOLVED inputs are preserved as reported, never promoted."
        ),
    }

    # ---- Stage 2: theme canonicalisation ---------------------------------
    canonical_tags: dict[str, str] = {}
    for theme in themes[:MAX_THEMES]:
        if budget.halted:
            break
        response, error = await call(
            client.tags(filter_query=theme, take=TAG_TAKE, tool="filmsponsor:tag_search")
        )
        record: dict[str, Any] = {"theme": theme, "canonical_tag": None, "error": error}
        if response is not None:
            exact = [
                tag
                for tag in (getattr(response, "results", []) or [])
                if getattr(tag, "name", None)
                and tag.name.strip().lower() == theme.strip().lower()
            ]
            if exact:
                tag = exact[0]
                record["canonical_tag"] = {"tag_id": tag.tag_id, "name": tag.name}
                canonical_tags[theme] = tag.tag_id
            record["returned_count"] = len(getattr(response, "results", []) or [])
        report["theme_canonicalization"].append(record)

    report["stages"]["theme_canonicalization"] = {
        "exact_unique_tags": len(canonical_tags),
        "rule": "GET /v2/tags with documented filter.query and take only; exact-tag matches are canonical.",
    }

    # ---- Stage 3: brands from verified film entities ----------------------
    entity_ids = [f["candidate"]["entity_id"] for f in verified if f["candidate"].get("entity_id")]
    tag_ids = list(dict.fromkeys(canonical_tags.values()))
    entity_brand_ids: set[str] = set()
    tag_brand_ids: set[str] = set()

    if budget.halted:
        report["stages"]["brand_from_verified_films"] = {"status": "HALTED", "reason": budget.halt_reason}
    elif not entity_ids:
        report["stages"]["brand_from_verified_films"] = {
            "status": "EMPTY",
            "reason": "No resolver-verified film entities; no brand signal was requested.",
        }
    else:
        response, error = await call(
            client.insights(
                filter_type=BRAND_ENTITY_TYPE,
                signal_interests_entities=entity_ids,
                take=BRAND_TAKE,
                tool="filmsponsor:brand_from_films",
            )
        )
        brands, others = (
            _split_brand_results(response, source="brand_from_films")
            if response is not None
            else ([], [])
        )
        report["brands"].extend(brands)
        report["non_brand_results"].extend(others)
        entity_brand_ids = {b["entity_id"] for b in brands if b.get("entity_id")}
        report["stages"]["brand_from_verified_films"] = {
            "status": "COMPLETE" if error is None else "HALTED",
            "seed_entity_ids": entity_ids,
            "brand_count": len(brands),
            "non_brand_count": len(others),
            "error": error,
        }
        if error is not None and _is_fatal(error):
            budget.halted = True
            budget.halt_reason = error

    # ---- Stage 4: brands from canonical theme tags ------------------------
    if budget.halted:
        report["stages"]["brand_from_canonical_tags"] = {"status": "HALTED", "reason": budget.halt_reason}
    elif not tag_ids:
        report["stages"]["brand_from_canonical_tags"] = {
            "status": "EMPTY",
            "reason": "No exact canonical tags; no tag-seeded brand signal was requested.",
        }
    else:
        response, error = await call(
            client.insights(
                filter_type=BRAND_ENTITY_TYPE,
                signal_interests_tags=tag_ids,
                take=BRAND_TAKE,
                tool="filmsponsor:brand_from_tags",
            )
        )
        brands, others = (
            _split_brand_results(response, source="brand_from_tags")
            if response is not None
            else ([], [])
        )
        report["brands"].extend(brands)
        report["non_brand_results"].extend(others)
        tag_brand_ids = {b["entity_id"] for b in brands if b.get("entity_id")}
        report["stages"]["brand_from_canonical_tags"] = {
            "status": "COMPLETE" if error is None else "HALTED",
            "seed_tag_ids": tag_ids,
            "brand_count": len(brands),
            "non_brand_count": len(others),
            "error": error,
        }
        if error is not None and _is_fatal(error):
            budget.halted = True
            budget.halt_reason = error

    # ---- Stage 5: combined exploratory query (ID/shape comparison only) ---
    if budget.halted:
        report["stages"]["combined_brand_query"] = {"status": "HALTED", "reason": budget.halt_reason}
    elif entity_brand_ids and tag_brand_ids and len(entity_brand_ids ^ tag_brand_ids) >= 2:
        response, error = await call(
            client.insights(
                filter_type=BRAND_ENTITY_TYPE,
                signal_interests_entities=entity_ids,
                signal_interests_tags=tag_ids,
                take=BRAND_TAKE,
                tool="filmsponsor:brand_combined_exploratory",
            )
        )
        brands, others = (
            _split_brand_results(response, source="brand_combined_exploratory")
            if response is not None
            else ([], [])
        )
        report["brands"].extend(brands)
        report["non_brand_results"].extend(others)
        report["stages"]["combined_brand_query"] = {
            "status": "COMPLETE" if error is None else "HALTED",
            "brand_count": len(brands),
            "comparison_rule": (
                "Compare candidate IDs and response shape only; affinity values "
                "from separately seeded queries are not comparable."
            ),
            "error": error,
        }
    else:
        report["stages"]["combined_brand_query"] = {
            "status": "SKIPPED",
            "reason": (
                "Separate queries did not produce sufficiently distinct typed-brand "
                "candidate sets; no extra request justified."
            ),
        }

    # Merge to one row per candidate (per-entity observations keep provenance)
    # and one row per non-brand result; true duplicates collapse.
    report["brands"] = _merge_brand_rows(report["brands"])
    report["non_brand_results"] = _merge_other_rows(report["non_brand_results"])

    report["logical_gets"] = budget.logical_gets
    if budget.halted and budget.halt_reason is not None:
        report["halt_reason"] = budget.halt_reason
    report["empty"] = not report["brands"] and not report["non_brand_results"]
    return DiscoveryOutcome(report=report, data_status="measured", call_ids=list(report["call_ids"]))
