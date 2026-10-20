"""Adjacent FastAPI backend.

The API serves run execution, Creator analysis, experiment lifecycle,
FilmSponsor campaigns, and an optional YouTube integration. Public-demo mode
wraps this surface in an anonymous allowlist; provider credentials remain
server-side.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import __version__, evidence
from .api.creator_routes import router as creator_router
from .api.filmsponsor_routes import router as filmsponsor_router
from .api.routes import router as run_router
from .api.youtube_routes import router as youtube_router
from .config import Settings
from .domain.filmsponsor_guest_sessions import guest_demo_enabled
from .public_demo import PublicDemoGuard, public_demo_enabled, public_live_available
from .qloo import MockQlooClient, build_params, registry_summary, unverified_params
from .qloo.errors import ParamError, QlooError
from .qloo.params import (
    ENTITY_FILTER_TYPES,
    EXTERNAL_ID_FAMILIES,
    KNOWN_ENDPOINTS,
    MAX_TAKE,
    unverified_endpoints,
)

app = FastAPI(
    title="Adjacent API",
    version=__version__,
    description=(
        "Creator-first cultural decision support with bounded typed Qloo operations, "
        "labelled fixture runs, traceable evidence, and a testable experiment lifecycle."
    ),
)

# The browser uses the same-origin Next.js /api proxy. Direct cross-origin
# callers are opt-in and must name their exact origins; never use `*`.
_configured_cors_origins = [
    origin.strip().rstrip("/")
    for origin in (os.getenv("ADJACENT_CORS_ORIGINS") or "").split(",")
    if origin.strip() and origin.strip() != "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_configured_cors_origins
    or ["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.add_middleware(PublicDemoGuard)

# Register run API routes
app.include_router(run_router)
# Creator Mode + experiment lifecycle (M13.9)
app.include_router(creator_router)
# FilmSponsor campaigns: discovery, drafts, source review, approval, outreach
app.include_router(filmsponsor_router)
# YouTube authorization + analytics bridge (M13.10)
app.include_router(youtube_router)


def get_settings() -> Settings:
    return Settings.from_env()


@app.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    if public_demo_enabled():
        # Keep the public liveness response useful without exposing provider
        # hosts, key fingerprints, parameter internals, or secret presence.
        return {
            "status": "ok",
            "service": "adjacent-backend",
            "version": __version__,
            "mode": "public_demo",
            "public_demo": True,
            "fixture_demo_available": True,
            "live_creator_available": public_live_available(),
            "filmsponsor_guest_enabled": guest_demo_enabled(),
        }
    return {
        "status": "ok",
        "service": "adjacent-backend",
        "version": __version__,
        "qloo_configured": settings.has_api_key,
        "filmsponsor_guest_enabled": guest_demo_enabled(),
        "mode": settings.mode,  # "live" | "mock" — never ambiguous
        "mock_mode": settings.mock_mode,
        "qloo_base_url": settings.qloo_base_url,
        "qloo_trusted_base_url": settings.qloo_trusted_base_url,
        "key_fingerprint": settings.key_fingerprint(),
        "param_registry_size": len(registry_summary()),
        "unverified_param_count": len(unverified_params()),
        "known_endpoints": sorted(KNOWN_ENDPOINTS),
        "max_take": MAX_TAKE,
        "evidence_thresholds": {
            "min_resolved_titles": evidence.MIN_RESOLVED_TITLES,
            "min_cohort_members": evidence.MIN_COHORT_MEMBERS,
            "min_cohort_members_high": evidence.MIN_COHORT_MEMBERS_HIGH,
            "min_heatmap_cells": evidence.MIN_HEATMAP_CELLS,
        },
    }


@app.get("/debug/config")
def debug_config() -> dict[str, Any]:
    settings = get_settings()
    return {"settings": settings.redacted(), "fixtures_dir": str(settings.fixtures_dir)}


@app.get("/debug/params")
def debug_params() -> dict[str, Any]:
    """The allowlist, including the parameters we have NOT verified."""
    return {
        "registry": registry_summary(),
        "unverified": [
            {
                "param": spec.name,
                "unverified_on": unverified_endpoints(spec),
                "summary": spec.summary,
                "open_question": spec.open_question,
            }
            for spec in unverified_params()
        ],
        "entity_filter_types": sorted(ENTITY_FILTER_TYPES),
        "external_id_families": list(EXTERNAL_ID_FAMILIES),
    }


@app.get("/debug/params/check")
def debug_params_check(
    endpoint: str = Query(..., description="e.g. /v2/insights"),
    filter_type: str | None = Query(None, description="e.g. urn:tag"),
    allow_unverified: bool = False,
) -> dict[str, Any]:
    """Dry-run the validator without sending anything. Useful while writing probes."""
    values: dict[str, Any] = {}
    if filter_type:
        values["filter.type"] = filter_type
    try:
        built = build_params(endpoint, values, allow_unverified=allow_unverified, check_required=False)
    except ParamError as exc:
        # Every local validation failure is a ParamError subclass and is reported,
        # never swallowed: the point of this route is to answer "would we send this?"
        return {"ok": False, "error": exc.to_dict()}
    return {
        "ok": True,
        "endpoint": built.endpoint,
        "filter_type": built.filter_type,
        "warnings": built.warnings,
        "unverified_used": built.unverified_used,
    }


@app.get("/debug/mock/run")
def debug_mock_run(
    fixture: str = Query("portland_strong", description="Fixture scenario name"),
    city: str | None = Query(None, description="Overrides the fixture's city query"),
) -> dict[str, Any]:
    """Execute a fixture-backed chain and return the artefacts + trace.

    This exists so the whole stack can be verified with NO API key. Everything it
    returns is marked `data_status="fixture"`.
    """
    return asyncio.run(_mock_run(fixture=fixture, city=city))


async def _mock_run(*, fixture: str, city: str | None) -> dict[str, Any]:
    settings = get_settings()
    try:
        client = MockQlooClient(settings, fixture=fixture, run_id=f"mock-{fixture}")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    fx = client.fixture
    programme_ids = fx.entity_ids
    city_query = (
        city or fx.city_query or (settings.probe_cities[0] if settings.probe_cities else "London, UK")
    )
    errors: list[dict[str, Any]] = []

    async def call(coro: Any) -> Any:
        try:
            return await coro
        except QlooError as exc:
            errors.append(exc.to_dict())
            return None
        except Exception as exc:  # pragma: no cover - defensive
            errors.append({"error_type": type(exc).__name__, "message": str(exc)})
            return None

    tags = await call(
        client.insights(
            filter_type="urn:tag",
            signal_interests_entities=programme_ids,
            take=50,
            tool="taste_dna",
        )
    )
    artists = await call(
        client.insights(
            filter_type="urn:entity:artist",
            signal_interests_entities=programme_ids,
            filter_popularity_min=0.05,
            filter_popularity_max=0.9,
            take=12,
            tool="expand_adjacency:artist",
        )
    )
    heatmap = await call(
        client.insights(
            filter_type="urn:heatmap",
            signal_interests_entities=programme_ids,
            filter_location_query=city_query,
            filter_location_radius=0,
            output_heatmap_boundary="urn:geohash",
            tool="cohort_heatmap",
        )
    )

    tag_verdict = evidence.evaluate_tags(getattr(tags, "results", []) or [])
    cohort_verdict = evidence.evaluate_cohort(getattr(artists, "results", []) or [])
    heatmap_verdict = evidence.evaluate_heatmap(getattr(heatmap, "results", []) or [])

    return {
        "fixture": fixture,
        "scenario": fx.scenario,
        "description": fx.description,
        "fixture_notice": client.notice,
        "data_status": "fixture",
        "city_query": city_query,
        "programme_entity_ids_supplied": len(programme_ids),
        "taste_dna": {
            "count": len(getattr(tags, "results", []) or []),
            "top": [
                {"tag_id": t.tag_id, "name": t.name, "affinity": t.affinity, "band": t.band.value}
                for t in (getattr(tags, "results", []) or [])[:8]
            ],
            "evidence": tag_verdict.as_dict(),
        },
        "adjacency": {
            "domain": "urn:entity:artist",
            "count": len(getattr(artists, "results", []) or []),
            "top": [
                {
                    "entity_id": e.entity_id,
                    "name": e.name,
                    "affinity": e.affinity,
                    "band": e.band.value,
                    "popularity": e.popularity,
                }
                for e in (getattr(artists, "results", []) or [])[:12]
            ],
            "evidence": cohort_verdict.as_dict(),
        },
        "geography": {
            "cells": len(getattr(heatmap, "results", []) or []),
            "locality": getattr(heatmap, "locality", None),
            "evidence": heatmap_verdict.as_dict(),
        },
        "errors": errors,
        "trace": client.recorder.as_dicts(),
    }
