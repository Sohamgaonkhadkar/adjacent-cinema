#!/usr/bin/env python3
"""Bounded, read-only live Qloo acceptance gate for FilmSponsor.

Separate from the broad historical qloo_probe.py: at most 12 logical GETs,
no retries, paced at 1 request/second, no file writes, no raw-body output, and
only the existing QlooClient/strict parameter allowlist. Fails closed without
QLOO_API_KEY. Run from qloo_hackathon/adjacent with Python 3.12+.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import sys
import unicodedata
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
MOVIE_TYPE = "urn:entity:movie"
BRAND_TYPE = "urn:entity:brand"
SEARCH_TAKE = 5
TAG_TAKE = 5
BRAND_TAKE = 10
MIN_VERIFIED_FILMS = 2
MIN_CANONICAL_TAGS = 2
MAX_LOGICAL_GETS = 12

# Three input rows from data/processed/qloo_modern_benchmark.csv. Historical
# Qloo IDs/statuses are not treated as current truth; all mappings are rechecked.
# Each theme query defines an explicit, justified media taxonomy tag type:
# - superhero: urn:tag:subgenre:qloo (subgenre within narrative film/fiction)
# - science fiction: urn:tag:genre:media (primary media genre)
# - psychological thriller: urn:tag:genre:media (compound media genre)
FILMS: tuple[dict[str, Any], ...] = (
    {
        "title": "The Dark Knight",
        "year": 2008,
        "imdb_id": "tt0468569",
        "theme": "superhero",
        "tag_type": "urn:tag:subgenre:qloo",
    },
    {
        "title": "Inception",
        "year": 2010,
        "imdb_id": "tt1375666",
        "theme": "science fiction",
        "tag_type": "urn:tag:genre:media",
    },
    {
        "title": "Black Swan",
        "year": 2010,
        "imdb_id": "tt0947798",
        "theme": "psychological thriller",
        "tag_type": "urn:tag:genre:media",
    },
)


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False))


def _blocked(reason: str) -> int:
    _emit(
        {
            "overall_verdict": "BLOCKED",
            "mode": "blocked",
            "source": "none",
            "data_status": "not_run",
            "reason": reason,
            "live_requests": 0,
            "max_logical_gets": MAX_LOGICAL_GETS,
            "credential_value_emitted": False,
            "raw_responses_saved": False,
        }
    )
    return 2


def _raw(entity: Any) -> dict[str, Any]:
    value = getattr(entity, "raw", None)
    return value if isinstance(value, dict) else {}


def _types(entity: Any) -> set[str]:
    """Read explicit type fields for typed brand-result presentation only."""
    raw = _raw(entity)
    values = {
        value
        for value in (
            getattr(entity, "type", None),
            getattr(entity, "subtype", None),
            raw.get("type"),
            raw.get("subtype"),
        )
        if isinstance(value, str) and value
    }
    raw_types = raw.get("types")
    if isinstance(raw_types, str):
        values.add(raw_types)
    elif isinstance(raw_types, list):
        values.update(str(value) for value in raw_types if value)
    return values


def _safe_error(exc: Exception) -> dict[str, Any]:
    # Never emit exception text, raw response detail, or request headers.
    return {
        "error_type": type(exc).__name__,
        "kind": getattr(exc, "kind", None),
        "status": getattr(exc, "status", None),
        "endpoint": getattr(exc, "endpoint", None),
        "call_id": getattr(exc, "call_id", None),
    }


def _is_fatal(error: dict[str, Any] | None) -> bool:
    # /entities 404 is a documented unresolved-data outcome. Any other error
    # stops further calls to avoid amplifying auth, rate-limit, or service issues.
    return error is not None and error.get("status") != 404


def _film_resolution_record(film: dict[str, Any], result: Any) -> dict[str, Any]:
    """Project only safe resolver fields; never serialize raw payloads or notes."""
    status_value = getattr(getattr(result, "match_status", None), "value", "UNRESOLVED")
    method_value = getattr(getattr(result, "match_method", None), "value", None)
    verified = bool(getattr(result, "resolved", False))
    entity_id = getattr(result, "qloo_entity_id", None)
    candidate = (
        {
            "entity_id": entity_id,
            "name": getattr(result, "qloo_name", None),
            "year": getattr(result, "qloo_year", None),
            "type": getattr(result, "qloo_entity_type", None),
        }
        if entity_id
        else None
    )
    call_ids: list[str] = []
    for call_id in [getattr(result, "call_id", None), *getattr(result, "related_call_ids", [])]:
        if call_id and call_id not in call_ids:
            call_ids.append(call_id)
    has_external_id = bool(film.get("imdb_id"))
    return {
        "title": film["title"],
        "year": film.get("year"),
        "imdb_id": film.get("imdb_id"),
        "resolution": {
            "status": status_value,
            "method": method_value,
            "external_id_corroborated": (verified and method_value == "external_id")
            if has_external_id
            else None,
            "candidate": candidate,
            "call_ids": call_ids,
        },
        "verdict": "PASS" if verified else status_value,
    }


async def _resolve_film(resolver: Any, film: dict[str, Any]) -> dict[str, Any]:
    """Use the production resolver as the sole authority for film identity."""
    result = await resolver.resolve_item(
        film["title"],
        year=film.get("year"),
        external_id=film.get("imdb_id"),
        external_family="imdb" if film.get("imdb_id") else None,
    )
    return _film_resolution_record(film, result)


class _GateStopped(RuntimeError):
    """Internal sentinel raised when the read-only gate must issue no more GETs."""


class _BudgetedQlooClient:
    """Expose only bounded GET operations to the resolver and gate stages."""

    def __init__(self, client: Any) -> None:
        self._client = client
        self.logical_gets = 0
        self.halted = False
        self.halt_reason: dict[str, Any] | None = None

    async def _call(self, method: str, **kwargs: Any) -> Any:
        if self.halted:
            raise _GateStopped("Gate is halted; no further request is allowed.")
        if self.logical_gets >= MAX_LOGICAL_GETS:
            self.halted = True
            self.halt_reason = {
                "error_type": "LogicalGetBudgetExceeded",
                "kind": "request_budget",
                "status": None,
                "endpoint": None,
                "call_id": None,
            }
            raise _GateStopped("Logical GET budget exhausted.")

        self.logical_gets += 1
        try:
            return await getattr(self._client, method)(**kwargs)
        except Exception as exc:
            error = _safe_error(exc)
            if _is_fatal(error):
                self.halted = True
                self.halt_reason = error
            raise

    async def search(self, **kwargs: Any) -> Any:
        return await self._call("search", **kwargs)

    async def entities(self, **kwargs: Any) -> Any:
        return await self._call("entities", **kwargs)

    async def tags(self, **kwargs: Any) -> Any:
        return await self._call("tags", **kwargs)

    async def insights(self, **kwargs: Any) -> Any:
        return await self._call("insights", **kwargs)


def _trace_rows(recorder: Any) -> list[dict[str, Any]]:
    rows = []
    for row in recorder.rows:
        error = row.error if isinstance(row.error, dict) else None
        # TraceRecorder redacts parameters. Do not include error message/detail.
        rows.append(
            {
                "call_id": row.call_id,
                "method": row.method,
                "endpoint": row.endpoint,
                "params": row.params,
                "status": row.status,
                "result_count": row.result_count,
                "latency_ms": row.duration_ms,
                "attempt": row.attempt,
                "error_type": error.get("error_type") if error else None,
            }
        )
    return rows


def _tag_record(response: Any, error: dict[str, Any] | None, film: dict[str, Any]) -> dict[str, Any]:
    results = list(getattr(response, "results", []) or []) if response is not None else []
    query = film["theme"]
    intended_subtype = film.get("tag_type")
    normal_query = " ".join(unicodedata.normalize("NFKC", query).casefold().split())
    exact: dict[str, Any] = {}
    for tag in results:
        name = getattr(tag, "name", None)
        tag_id = getattr(tag, "tag_id", None)
        tag_subtype = getattr(tag, "subtype", None) or getattr(tag, "type", None)
        if not tag_subtype and isinstance(getattr(tag, "raw", None), dict):
            tag_subtype = tag.raw.get("subtype") or tag.raw.get("type")

        name_match = (
            isinstance(name, str)
            and " ".join(unicodedata.normalize("NFKC", name).casefold().split()) == normal_query
        )
        subtype_match = True
        if intended_subtype:
            subtype_match = bool(
                tag_subtype
                and (
                    tag_subtype == intended_subtype
                    or tag_subtype == intended_subtype.removeprefix("urn:tag:")
                    or str(tag_id).startswith(f"{intended_subtype}:")
                )
            )

        if name_match and subtype_match and tag_id:
            exact[str(tag_id)] = tag
    if error:
        verdict = "NO_EXACT_CANONICAL_MATCH" if error.get("status") == 404 else "ERROR"
    elif len(exact) == 1:
        verdict = "VERIFIED"
    elif len(exact) > 1:
        verdict = "AMBIGUOUS"
    else:
        verdict = "NO_EXACT_CANONICAL_MATCH"
    canonical = next(iter(exact.items()), None) if len(exact) == 1 else None
    return {
        "film_title": film["title"],
        "query": query,
        "intended_subtype": intended_subtype,
        "verdict": verdict,
        "call_id": getattr(response, "call_id", None) or (error or {}).get("call_id"),
        "observed_shape": list(getattr(response, "observed_shape", []) or []),
        "result_count": len(results) if response is not None else None,
        "canonical_tag": (
            {
                "tag_id": canonical[0],
                "name": getattr(canonical[1], "name", None),
                "subtype": getattr(canonical[1], "subtype", None),
            }
            if canonical
            else None
        ),
        "candidate_examples": [
            {
                "tag_id": getattr(tag, "tag_id", None),
                "name": getattr(tag, "name", None),
                "subtype": getattr(tag, "subtype", None),
            }
            for tag in results[:3]
        ],
        "error": error,
    }


def _brand_ids(response: Any) -> set[str]:
    return {
        str(entity.entity_id)
        for entity in getattr(response, "results", [])
        if getattr(entity, "entity_id", None) and BRAND_TYPE in _types(entity)
    }


def _finite_affinity(entity: Any) -> float | None:
    try:
        score = float(entity.affinity)
    except (AttributeError, TypeError, ValueError):
        return None
    return score if math.isfinite(score) else None


def _brand_record(response: Any, error: dict[str, Any] | None, signal_count: int) -> dict[str, Any]:
    if error:
        return {
            "verdict": "FAIL" if error.get("status") == 404 else "BLOCKED",
            "error": error,
        }
    if response is None:
        return {"verdict": "BLOCKED", "reason": "No response object."}
    results = list(getattr(response, "results", []) or [])
    typed = [entity for entity in results if BRAND_TYPE in _types(entity)]
    scored = [entity for entity in typed if _finite_affinity(entity) is not None]
    scored.sort(key=lambda entity: _finite_affinity(entity) or 0.0, reverse=True)
    examples = [
        {
            "entity_id": entity.entity_id,
            "name": entity.name,
            "cultural_affinity": _finite_affinity(entity),
            "types": sorted(_types(entity)),
        }
        for entity in scored[:3]
        if getattr(entity, "entity_id", None) and getattr(entity, "name", None)
    ]
    correct_shape = type(response).__name__ == "EntityAffinityResponse"
    return {
        "verdict": "PASS" if correct_shape and examples else "FAIL",
        "call_id": getattr(response, "call_id", None),
        "observed_shape": list(getattr(response, "observed_shape", []) or []),
        "result_count": len(results),
        "typed_brand_count": len(typed),
        "affinity_scored_brand_count": len(scored),
        "signal_count": signal_count,
        "examples": examples,
        "output_type": type(response).__name__,
        "affinity_semantics": "cultural affinity only",
    }


async def _run_gate(
    *,
    settings: Any,
    client_class: Any,
    recorder_class: Any,
    resolver_class: Any,
    default_base_url: str,
) -> dict[str, Any]:
    if settings.qloo_base_url != default_base_url or not settings.base_url_is_hackathon_host:
        return {
            "overall_verdict": "BLOCKED",
            "mode": "blocked",
            "source": "none",
            "data_status": "not_run",
            "reason": "QLOO_BASE_URL is not the approved hackathon host; no request was made.",
            "live_requests": 0,
            "max_logical_gets": MAX_LOGICAL_GETS,
            "credential_value_emitted": False,
            "raw_responses_saved": False,
        }
    if settings.max_retries != 0 or not 0 < settings.rate_limit_rps <= 1.0:
        return {
            "overall_verdict": "BLOCKED",
            "mode": "blocked",
            "source": "none",
            "data_status": "not_run",
            "reason": "Live gate requires zero retries and a rate limit no faster than one request per second.",
            "live_requests": 0,
            "max_logical_gets": MAX_LOGICAL_GETS,
            "credential_value_emitted": False,
            "raw_responses_saved": False,
        }

    recorder = recorder_class(run_id="filmsponsor-gate", secret=settings.qloo_api_key)
    report: dict[str, Any] = {
        "overall_verdict": "BLOCKED",
        "mode": "live",
        "source": "qloo",
        "data_status": "measured",
        "implementation_review": {
            "resolver": "app.resolution.resolver.EntityResolver.resolve_item",
            "movie_type_filter": MOVIE_TYPE,
            "external_id_corroboration": "delegated to the production resolver",
            "ambiguity_policy": "preserve the resolver status; the gate does not reselect a candidate",
        },
        "run": {
            "mode": "live",
            "source": "qloo",
            "data_status": "measured",
            "base_url": default_base_url,
            "max_retries": settings.max_retries,
            "rate_limit_rps": settings.rate_limit_rps,
            "max_logical_gets": MAX_LOGICAL_GETS,
            "input_source": "data/processed/qloo_modern_benchmark.csv",
            "theme_queries_note": "Fixed validation prompts, not ground-truth film metadata.",
            "credential_value_emitted": False,
            "raw_responses_saved": False,
        },
        "films": [],
        "stages": {},
        "interpretation_limits": [
            "Cultural affinity is not sponsorship likelihood, eligibility, budget, availability, or ROI.",
            "Brand examples are for human relevance review only; no outreach or contact discovery is performed.",
        ],
    }
    halted = False
    halt_reason: dict[str, Any] | None = None

    async with client_class(settings, recorder=recorder) as qloo_client:
        client = _BudgetedQlooClient(qloo_client)
        resolver = resolver_class(client, delay_s=0.0)

        async def call(awaitable: Any) -> tuple[Any | None, dict[str, Any] | None]:
            nonlocal halted, halt_reason
            try:
                return await awaitable, None
            except Exception as exc:
                error = _safe_error(exc)
                if client.halted:
                    halted = True
                    halt_reason = client.halt_reason
                elif _is_fatal(error):
                    halted = True
                    halt_reason = error
                return None, error

        for film in FILMS:
            if halted:
                break
            record = await _resolve_film(resolver, film)
            if client.halted:
                record["verdict"] = "BLOCKED"
                halted = True
                halt_reason = client.halt_reason
            report["films"].append(record)

        verified_films = [film for film in report["films"] if film["verdict"] == "PASS"]
        complete_film_set = len(report["films"]) == len(FILMS)
        report["stages"]["film_resolution"] = {
            "verdict": "BLOCKED"
            if halted
            else "PASS"
            if complete_film_set and len(verified_films) == len(FILMS)
            else "FAIL",
            "verified_count": len(verified_films),
            "expected_count": len(FILMS),
            "rule": "Every input must be VERIFIED by the production EntityResolver; other resolver statuses are not promoted.",
        }

        canonical: dict[str, dict[str, Any]] = {}
        tag_records: list[dict[str, Any]] = []
        for film in FILMS:
            if halted:
                break
            tag_type = film.get("tag_type")
            response, error = await call(
                client.tags(
                    filter_query=film["theme"],
                    filter_tag_types=[tag_type] if tag_type else None,
                    take=TAG_TAKE,
                    tool="filmsponsor_gate:tag_search",
                )
            )
            record = _tag_record(response, error, film)
            tag_records.append(record)
            tag = record.get("canonical_tag")
            if tag:
                canonical[film["theme"]] = tag
        report["theme_canonicalization"] = tag_records
        tag_verdict = (
            "BLOCKED"
            if halted or len(tag_records) < len(FILMS)
            else "PASS"
            if len(canonical) >= MIN_CANONICAL_TAGS
            else "FAIL"
        )
        report["stages"]["theme_canonicalization"] = {
            "verdict": tag_verdict,
            "exact_unique_tags": len(canonical),
            "expected_minimum": MIN_CANONICAL_TAGS,
            "contract": "GET /v2/tags using documented filter.query, filter.tag.types, and take only",
        }

        entity_brand = None
        tag_brand = None
        entity_ids = [
            film["resolution"]["candidate"]["entity_id"]
            for film in verified_films
            if film["resolution"]["candidate"] and film["resolution"]["candidate"]["entity_id"]
        ]
        tag_ids = list(dict.fromkeys(tag["tag_id"] for tag in canonical.values()))

        if halted or len(entity_ids) < MIN_VERIFIED_FILMS:
            report["stages"]["brand_from_verified_films"] = {
                "verdict": "BLOCKED",
                "reason": "Stopped on an upstream error or fewer than two resolver-verified film entities.",
            }
        else:
            entity_brand, error = await call(
                client.insights(
                    filter_type=BRAND_TYPE,
                    signal_interests_entities=entity_ids,
                    take=BRAND_TAKE,
                    tool="filmsponsor_gate:brand_from_films",
                )
            )
            report["stages"]["brand_from_verified_films"] = _brand_record(
                entity_brand, error, len(entity_ids)
            )

        if halted or len(tag_ids) < MIN_CANONICAL_TAGS:
            report["stages"]["brand_from_canonical_tags"] = {
                "verdict": "BLOCKED",
                "reason": "Stopped on an upstream error or fewer than two exact canonical tags.",
            }
        else:
            tag_brand, error = await call(
                client.insights(
                    filter_type=BRAND_TYPE,
                    signal_interests_tags=tag_ids,
                    take=BRAND_TAKE,
                    tool="filmsponsor_gate:brand_from_tags",
                )
            )
            report["stages"]["brand_from_canonical_tags"] = _brand_record(tag_brand, error, len(tag_ids))

        entity_brand_ids = _brand_ids(entity_brand)
        tag_brand_ids = _brand_ids(tag_brand)
        if halted:
            report["stages"]["combined_brand_query"] = {
                "verdict": "BLOCKED",
                "reason": "Stopped after an upstream/auth/rate-limit error.",
            }
        elif entity_brand_ids and tag_brand_ids and len(entity_brand_ids ^ tag_brand_ids) >= 2:
            combined, error = await call(
                client.insights(
                    filter_type=BRAND_TYPE,
                    signal_interests_entities=entity_ids,
                    signal_interests_tags=tag_ids,
                    take=BRAND_TAKE,
                    tool="filmsponsor_gate:brand_combined_exploratory",
                )
            )
            report["stages"]["combined_brand_query"] = _brand_record(
                combined, error, len(entity_ids) + len(tag_ids)
            )
            report["stages"]["combined_brand_query"]["comparison_rule"] = (
                "Compare IDs and response shape only; do not compare affinity values across separately seeded queries."
            )
        else:
            report["stages"]["combined_brand_query"] = {
                "verdict": "SKIPPED",
                "reason": "Separate queries did not provide sufficiently distinct typed-brand candidate sets; no extra request justified.",
            }

        report["run"]["logical_gets"] = client.logical_gets
        report["live_requests"] = client.logical_gets
        report["request_log"] = _trace_rows(recorder)
        if halt_reason:
            report["halt_reason"] = halt_reason

    required = [
        report["stages"]["film_resolution"]["verdict"],
        report["stages"]["theme_canonicalization"]["verdict"],
        report["stages"]["brand_from_verified_films"]["verdict"],
        report["stages"]["brand_from_canonical_tags"]["verdict"],
    ]
    combined_verdict = report["stages"]["combined_brand_query"]["verdict"]
    if "FAIL" in required or combined_verdict == "FAIL":
        report["overall_verdict"] = "FAIL"
    elif "BLOCKED" in required or combined_verdict == "BLOCKED":
        report["overall_verdict"] = "BLOCKED"
    else:
        report["overall_verdict"] = "PASS"
    return report


def main() -> int:
    if not (os.environ.get("QLOO_API_KEY") or "").strip():
        return _blocked("QLOO_API_KEY is unavailable to this process; no request was made.")
    if sys.version_info < (3, 12):  # noqa: UP036 — runtime guard for local/copy invocations
        return _blocked("The project requires Python 3.12 or later; no request was made.")

    sys.path.insert(0, str(PROJECT_DIR / "backend"))
    from app.config import DEFAULT_BASE_URL, Settings
    from app.qloo.client import QlooClient
    from app.qloo.trace import TraceRecorder
    from app.resolution.resolver import EntityResolver

    # Bound this validation run: no retries and at most one Qloo call/second.
    read_timeout_s = float(os.environ.get("QLOO_READ_TIMEOUT_S") or 15.0)
    settings = Settings.from_env(max_retries=0, rate_limit_rps=1.0, read_timeout_s=read_timeout_s)
    try:
        report = asyncio.run(
            _run_gate(
                settings=settings,
                client_class=QlooClient,
                recorder_class=TraceRecorder,
                resolver_class=EntityResolver,
                default_base_url=DEFAULT_BASE_URL,
            )
        )
    except Exception as exc:
        # Suppress exception text, which could include upstream response detail.
        _emit(
            {
                "overall_verdict": "BLOCKED",
                "mode": "live",
                "source": "qloo",
                "data_status": "unknown",
                "reason": "Unexpected internal failure; details suppressed and no raw response saved.",
                "error_type": type(exc).__name__,
                "live_requests": "unknown",
                "max_logical_gets": MAX_LOGICAL_GETS,
                "credential_value_emitted": False,
                "raw_responses_saved": False,
            }
        )
        return 2
    _emit(report)
    return 0 if report["overall_verdict"] == "PASS" else 1 if report["overall_verdict"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
