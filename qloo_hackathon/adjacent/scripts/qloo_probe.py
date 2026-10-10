#!/usr/bin/env python3
"""Qloo API probe — Day 1 deliverable.

Runs a small, deterministic suite of probes against the live Qloo hackathon API
and writes:

    docs/api_probe_results.json   machine-readable results
    docs/API_NOTES.md             human-readable report

If `QLOO_API_KEY` is not set, the script runs the SAME suite against
`MockQlooClient` in dry-run mode and stamps every result with
"NOT YET EXECUTED AGAINST QLOO". It never fabricates live results, and it never
writes a number it did not observe.

The most important probe is D: whether `filter.results.entities` returns EVERY
supplied candidate entity, scored, in a single query. Adjacent's cohort ranking
is only valid inside a single normalisation, so this result decides which
ranking implementation is safe to build.

Usage:
    python scripts/qloo_probe.py                  # dry-run unless a key exists
    python scripts/qloo_probe.py --live           # force live (requires key)
    python scripts/qloo_probe.py --city "Leeds, UK" --city "Portland, Oregon"
    python scripts/qloo_probe.py --unverified      # also run the UNVERIFIED probes
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as _dt
import json
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "backend"))

from app.config import Settings
from app.qloo import (
    FIXTURE_NOTICE,
    MockQlooClient,
    QlooClient,
    band_for,
    unverified_params,
)
from app.qloo.errors import QlooError
from app.qloo.params import registry_summary

NOT_EXECUTED = "NOT YET EXECUTED AGAINST QLOO — results below are from the fixture-backed mock client"

#: What is actually blocked by each unresolved parameter. Written out so the open
#: questions have consequences attached rather than being a to-do list.
BLOCKED_WORK: dict[str, str] = {
    "filter.parents.types": (
        "Taste-DNA query shape (tool T3) on /v2/insights. Until resolved we do NOT send it, so "
        "tag results are unscoped. Probed by B2."
    ),
    "filter.tags": (
        "Nothing. It is not used anywhere in the design; recorded so it is never assumed to work. "
        "Probed by G2."
    ),
    "signal.location.query": (
        "Optional locality bias during candidate generation. The MVP does not require it. Probed by C2."
    ),
    "feature.semantic_search": (
        "Improved tag resolution from messy free text. Falls back to plain /v2/tags search, so "
        "nothing is blocked."
    ),
}

#: Real film identifiers, used only as probe inputs. No demo city is assumed.
PROBE_PROGRAMME = [
    {"title": "Perfect Days", "year": 2023, "imdb_id": "tt7594358"},
    {"title": "The Zone of Interest", "year": 2023, "imdb_id": "tt7160372"},
    {"title": "Taipei Story", "year": 1985, "imdb_id": "tt0089853"},
    {"title": "Sansho the Bailiff", "year": 1954, "imdb_id": "tt0047445"},
    {"title": "Le Samourai", "year": 1967, "imdb_id": "tt0062229"},
]


@dataclass
class ProbeOutcome:
    probe_id: str
    name: str
    endpoint: str
    request: str
    mode: str  # "live" | "dry-run"
    http_status: int | None = None
    result_count: int | None = None
    relevant_fields: list[str] = field(default_factory=list)
    latency_ms: int | None = None
    success: bool = False
    observed_limitation: str = ""
    verified_against_qloo: bool = False
    skipped_reason: str | None = None
    error: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProbeRunner:
    def __init__(
        self,
        *,
        client: Any,
        settings: Settings,
        cities: Sequence[str],
        mode: str,
        run_unverified: bool,
    ) -> None:
        self.client = client
        self.settings = settings
        self.cities = list(cities)
        self.mode = mode
        self.run_unverified = run_unverified
        self.outcomes: list[ProbeOutcome] = []
        self.programme_ids: list[str] = []
        self.artist_ids: list[str] = []
        self.started_at = _dt.datetime.now(tz=_dt.UTC)

    # -- helpers -----------------------------------------------------------
    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    def _fields_of_first(self, results: Sequence[Any]) -> list[str]:
        for item in results:
            raw = getattr(item, "raw", None)
            if isinstance(raw, dict):
                return sorted(raw.keys())
        return []

    def _add(self, outcome: ProbeOutcome) -> ProbeOutcome:
        outcome.verified_against_qloo = self.is_live and outcome.success
        self.outcomes.append(outcome)
        marker = "OK " if outcome.success else "-- "
        print(
            f"  {marker}[{outcome.probe_id}] {outcome.name}: "
            f"{outcome.result_count if outcome.result_count is not None else 'n/a'} "
            f"{'result(s)' if outcome.result_count is not None else ''}"
            f"{f' — {outcome.observed_limitation}' if outcome.observed_limitation else ''}"
        )
        return outcome

    def _error_outcome(
        self,
        *,
        probe_id: str,
        name: str,
        endpoint: str,
        request: str,
        exc: BaseException,
        latency_ms: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> ProbeOutcome:
        error = (
            exc.to_dict()
            if isinstance(exc, QlooError)
            else {"error_type": type(exc).__name__, "message": str(exc)}
        )
        status = error.get("status")
        limitation = {
            "authentication": "401/403 — check the key is a hackathon key and the base URL is hackathon.api.qloo.com",
            "not_found": "404 — for /entities this means 'not in Qloo' (a data outcome, not an outage)",
            "rate_limited": "429 — pacing/backoff required",
            "timeout": "timeout — check read timeout",
        }.get(str(error.get("kind")), str(error.get("message")))
        return self._add(
            ProbeOutcome(
                probe_id=probe_id,
                name=name,
                endpoint=endpoint,
                request=request,
                mode=self.mode,
                http_status=status if isinstance(status, int) else None,
                latency_ms=latency_ms,
                success=False,
                observed_limitation=limitation,
                error=error,
                extra=extra or {},
            )
        )

    async def _timed(self, coro: Any) -> tuple[Any, int]:
        start = time.perf_counter()
        result = await coro
        return result, int((time.perf_counter() - start) * 1000)

    # -- probes ------------------------------------------------------------
    async def probe_a_entity_resolution(self) -> None:
        ids = [p["imdb_id"] for p in PROBE_PROGRAMME]
        endpoint = "/entities"
        request = f"GET {endpoint}?external.imdb.ids={','.join(ids)}"
        try:
            response, ms = await self._timed(
                self.client.entities(external_ids={"imdb": ids}, tool="probe_a_resolve_entities")
            )
        except Exception as exc:
            self._error_outcome(
                probe_id="A",
                name="External ID entity resolution",
                endpoint=endpoint,
                request=request,
                exc=exc,
            )
            return
        self.programme_ids = [e.entity_id for e in response.results if e.entity_id]
        missing = [
            i
            for i in ids
            if i
            not in {
                (r.raw or {}).get("properties", {}).get("external", {}).get("imdb", {}).get("ids", [None])[0]
                for r in response.results
                if isinstance(r.raw, dict)
            }
            and len(response.results) < len(ids)
        ]
        self._add(
            ProbeOutcome(
                probe_id="A",
                name="External ID entity resolution",
                endpoint=endpoint,
                request=request,
                mode=self.mode,
                http_status=200,
                result_count=len(response.results),
                relevant_fields=self._fields_of_first(response.results),
                latency_ms=ms,
                success=bool(response.results),
                observed_limitation=(
                    f"{len(ids) - len(response.results)} of {len(ids)} IMDb ids did not resolve"
                    if len(response.results) < len(ids)
                    else ""
                ),
                extra={
                    "requested_imdb_ids": ids,
                    "resolved_entity_ids": self.programme_ids,
                    "resolved_count": len(response.results),
                    "unresolved_imdb_ids_estimate": missing,
                    "observed_shape": response.observed_shape,
                    "data_status": response.data_status,
                },
            )
        )

    async def probe_b_tag_affinity(self, *, with_parents: bool = False) -> None:
        if not self.programme_ids:
            self._add(
                ProbeOutcome(
                    probe_id="B2" if with_parents else "B",
                    name="Programme → tag affinity",
                    endpoint="/v2/insights",
                    request="(skipped)",
                    mode=self.mode,
                    skipped_reason="probe A produced no entity ids",
                )
            )
            return
        endpoint = "/v2/insights"
        params = {
            "filter.type": "urn:tag",
            "signal.interests.entities": ",".join(self.programme_ids),
            "take": "50",
        }
        probe_id, name = "B", "Programme → tag affinity (taste DNA)"
        if with_parents:
            # DELIBERATELY UNVERIFIED. See docs/API_NOTES.md open question #1.
            params["filter.parents.types"] = "urn:entity:movie,urn:entity:tv_show"
            probe_id, name = "B2", "Taste DNA with filter.parents.types (UNVERIFIED combination)"
        request = f"GET {endpoint}?" + "&".join(f"{k}={v}" for k, v in params.items())
        try:
            response, ms = await self._timed(
                self.client.insights(
                    filter_type="urn:tag",
                    signal_interests_entities=self.programme_ids,
                    filter_parents_types=(
                        ["urn:entity:movie", "urn:entity:tv_show"] if with_parents else None
                    ),
                    take=50,
                    allow_unverified=with_parents,
                    tool=f"probe_{probe_id.lower()}_taste_dna",
                )
            )
        except Exception as exc:
            self._error_outcome(probe_id=probe_id, name=name, endpoint=endpoint, request=request, exc=exc)
            return
        scored = [t for t in response.results if t.affinity is not None]
        top = sorted(scored, key=lambda t: t.affinity or 0, reverse=True)[:8]
        limitation = ""
        if with_parents and not scored:
            limitation = (
                "with filter.parents.types the query returned ZERO scored tags — the "
                "parameter may accept only audience category URNs, or may be silently ignored"
            )
        elif not scored:
            limitation = "no scored tags returned"
        self._add(
            ProbeOutcome(
                probe_id=probe_id,
                name=name,
                endpoint=endpoint,
                request=request,
                mode=self.mode,
                http_status=200,
                result_count=len(response.results),
                relevant_fields=self._fields_of_first(response.results),
                latency_ms=ms,
                success=bool(scored),
                observed_limitation=limitation,
                extra={
                    "scored_tag_count": len(scored),
                    "tags_above_medium": sum(1 for t in scored if (t.affinity or 0) >= 0.5),
                    "top_tags": [
                        {
                            "tag_id": t.tag_id,
                            "name": t.name,
                            "affinity": t.affinity,
                            "band": band_for(t.affinity).value,
                            "popularity": t.popularity,
                        }
                        for t in top
                    ],
                    "observed_shape": response.observed_shape,
                },
            )
        )

    async def probe_c_cross_domain(self, *, with_location: bool = False) -> None:
        if not self.programme_ids:
            self._add(
                ProbeOutcome(
                    probe_id="C2" if with_location else "C",
                    name="Programme → artist adjacency",
                    endpoint="/v2/insights",
                    request="(skipped)",
                    mode=self.mode,
                    skipped_reason="probe A produced no entity ids",
                )
            )
            return
        endpoint = "/v2/insights"
        city = self.cities[0] if self.cities else None
        params = {
            "filter.type": "urn:entity:artist",
            "signal.interests.entities": ",".join(self.programme_ids),
            "take": "12",
        }
        probe_id, name = "C", "Programme → artist cross-domain adjacency"
        if with_location:
            params["signal.location.query"] = str(city)
            probe_id, name = "C2", "Artist adjacency with signal.location.query (UNVERIFIED)"
        request = f"GET {endpoint}?" + "&".join(f"{k}={v}" for k, v in params.items())
        try:
            response, ms = await self._timed(
                self.client.insights(
                    filter_type="urn:entity:artist",
                    signal_interests_entities=self.programme_ids,
                    signal_location_query=city if with_location else None,
                    take=12,
                    allow_unverified=with_location,
                    tool=f"probe_{probe_id.lower()}_adjacency",
                )
            )
        except Exception as exc:
            self._error_outcome(probe_id=probe_id, name=name, endpoint=endpoint, request=request, exc=exc)
            return
        scored = [e for e in response.results if e.affinity is not None]
        ids = [e.entity_id for e in scored]
        if probe_id == "C":
            self.artist_ids = ids
        self._add(
            ProbeOutcome(
                probe_id=probe_id,
                name=name,
                endpoint=endpoint,
                request=request,
                mode=self.mode,
                http_status=200,
                result_count=len(response.results),
                relevant_fields=self._fields_of_first(response.results),
                latency_ms=ms,
                success=bool(scored),
                observed_limitation="" if scored else "no scored cross-domain entities returned",
                extra={
                    "scored_count": len(scored),
                    "returned_entity_ids": ids,
                    "top": [
                        {
                            "entity_id": e.entity_id,
                            "name": e.name,
                            "affinity": e.affinity,
                            "band": band_for(e.affinity).value,
                            "popularity": e.popularity,
                        }
                        for e in sorted(scored, key=lambda x: x.affinity or 0, reverse=True)[:6]
                    ],
                    "observed_shape": response.observed_shape,
                },
            )
        )

    async def probe_d_results_entities(self) -> None:
        """THE critical probe: does filter.results.entities return everything supplied?"""
        endpoint = "/v2/insights"
        supplied = list(self.artist_ids)
        request = (
            f"GET {endpoint}?filter.type=urn:entity:movie"
            f"&signal.interests.entities=<{len(self.programme_ids)} programme ids>"
            f"&filter.results.entities=<{len(supplied)} supplied ids>&take=50"
        )
        if not supplied:
            self._add(
                ProbeOutcome(
                    probe_id="D",
                    name="filter.results.entities completeness",
                    endpoint=endpoint,
                    request=request,
                    mode=self.mode,
                    skipped_reason="no candidate entity ids available (probe C produced none)",
                )
            )
            return
        try:
            response, ms = await self._timed(
                self.client.insights(
                    filter_type="urn:entity:artist",
                    signal_interests_entities=self.programme_ids,
                    filter_results_entities=supplied,
                    take=50,
                    tool="probe_d_results_entities",
                )
            )
        except Exception as exc:
            self._error_outcome(
                probe_id="D",
                name="filter.results.entities completeness",
                endpoint=endpoint,
                request=request,
                exc=exc,
            )
            return
        returned = [e.entity_id for e in response.results]
        returned_scored = [e.entity_id for e in response.results if e.affinity is not None]
        all_returned = set(supplied) <= set(returned)
        all_scored = set(supplied) <= set(returned_scored)
        limitation = ""
        if not all_returned:
            limitation = (
                f"ONLY {len(returned)} of {len(supplied)} supplied entities were returned — "
                "cohort ranking MUST compress cohorts into fewer, larger candidate sets "
                "(or rank within a domain and accept weaker comparability)."
            )
        self._add(
            ProbeOutcome(
                probe_id="D",
                name="filter.results.entities completeness",
                endpoint=endpoint,
                request=request,
                mode=self.mode,
                http_status=200,
                result_count=len(response.results),
                relevant_fields=self._fields_of_first(response.results),
                latency_ms=ms,
                success=True,
                observed_limitation=limitation,
                extra={
                    "supplied_count": len(supplied),
                    "returned_count": len(returned),
                    "returned_scored_count": len(returned_scored),
                    "all_supplied_returned": all_returned,
                    "all_supplied_returned_and_scored": all_scored,
                    "missing_ids": sorted(set(supplied) - set(returned)),
                    "take_used": 50,
                    "conclusion": (
                        "SAFE: rank all candidate cohorts in a single query via filter.results.entities."
                        if all_scored
                        else "NOT SAFE AS PLANNED: not every supplied entity came back scored. "
                        "See docs/API_NOTES.md — the ranking design must change."
                    ),
                    "observed_shape": response.observed_shape,
                },
            )
        )

    async def probe_e_heatmap(self) -> None:
        if not self.programme_ids:
            self._add(
                ProbeOutcome(
                    probe_id="E",
                    name="Heatmap coverage by city",
                    endpoint="/v2/insights",
                    request="(skipped)",
                    mode=self.mode,
                    skipped_reason="probe A produced no entity ids",
                )
            )
            return
        per_city: dict[str, Any] = {}
        supported: list[str] = []
        for city in self.cities:
            endpoint = "/v2/insights"
            request = (
                f"GET {endpoint}?filter.type=urn:heatmap&filter.location.query={city}"
                f"&filter.location.radius=0&signal.interests.entities=<{len(self.programme_ids)} ids>"
            )
            try:
                response, ms = await self._timed(
                    self.client.insights(
                        filter_type="urn:heatmap",
                        signal_interests_entities=self.programme_ids,
                        filter_location_query=city,
                        filter_location_radius=0,
                        output_heatmap_boundary="urn:geohash",
                        tool=f"probe_e_heatmap:{city}",
                    )
                )
            except Exception as exc:
                outcome = self._error_outcome(
                    probe_id=f"E:{city}",
                    name=f"Heatmap coverage — {city}",
                    endpoint=endpoint,
                    request=request,
                    exc=exc,
                )
                per_city[city] = {"ok": False, "error": outcome.error}
                continue
            cells = response.results
            scored = [c for c in cells if c.affinity is not None]
            top = sorted(scored, key=lambda c: c.affinity or 0, reverse=True)[:3]
            # Qloo returns `query.localities.filter` as a *list* of locality objects.
            _loc = response.locality
            if isinstance(_loc, list) and _loc and isinstance(_loc[0], dict):
                locality = _loc[0]
            elif isinstance(_loc, dict):
                locality = _loc
            else:
                locality = {}
            matched = (
                ", ".join(
                    str(v)
                    for v in (locality.get("name"), locality.get("state"), locality.get("country"))
                    if v
                )
                or "NOT MATCHED"
            )
            supports = len(cells) >= 10
            if supports:
                supported.append(city)
            per_city[city] = {
                "ok": bool(cells),
                "cell_count": len(cells),
                "scored_cell_count": len(scored),
                "locality_echo": locality,
                "locality_matched_as": matched,
                "top_cells": [
                    {
                        "lat": c.lat,
                        "lng": c.lng,
                        "geohash": c.geohash,
                        "affinity": c.affinity,
                        "affinity_rank": c.affinity_rank,
                    }
                    for c in top
                ],
                "latency_ms": ms,
                "supports_geographic_claim": supports,
            }
        self._add(
            ProbeOutcome(
                probe_id="E",
                name="Heatmap coverage by city",
                endpoint="/v2/insights",
                request="; ".join(f"filter.location.query={c}" for c in self.cities),
                mode=self.mode,
                http_status=200 if per_city else None,
                result_count=sum(v.get("cell_count", 0) for v in per_city.values() if isinstance(v, dict)),
                latency_ms=None,
                success=bool(supported),
                observed_limitation=(
                    "no candidate city produced >= 10 cells"
                    if not supported
                    else (
                        f"geography supported in: {', '.join(supported)}"
                        if self.is_live
                        else "DRY-RUN: identical fixture replayed per city — not evidence about any city"
                    )
                ),
                extra={
                    "cities_tested": self.cities,
                    "cities_supporting_geography": supported if self.is_live else [],
                    "min_cells_required": 10,
                    "per_city": per_city,
                    "result_is_meaningful": self.is_live,
                    "dry_run_caveat": (
                        None
                        if self.is_live
                        else "DRY-RUN: the mock replays ONE fixture for every city, so identical cell "
                        "counts across cities mean nothing. The demo city can only be chosen from a "
                        "live probe."
                    ),
                    "recommendation": (
                        f"Use '{supported[0]}' for the geographic demo, pending a venue in that city."
                        if (supported and self.is_live)
                        else (
                            "Run this probe with --live to choose the demo city on evidence."
                            if not self.is_live
                            else "Do NOT build the geographic output for these cities yet."
                        )
                    ),
                },
            )
        )

    async def probe_f_explainability(self) -> None:
        if not self.programme_ids:
            self._add(
                ProbeOutcome(
                    probe_id="F",
                    name="feature.explainability payload",
                    endpoint="/v2/insights",
                    request="(skipped)",
                    mode=self.mode,
                    skipped_reason="probe A produced no entity ids",
                )
            )
            return
        endpoint = "/v2/insights"
        sizes: dict[str, int] = {}
        attribution_found = False
        for flag in (False, True):
            request = (
                f"GET {endpoint}?filter.type=urn:entity:movie&signal.interests.entities=<ids>"
                f"&feature.explainability={'true' if flag else 'false'}&take=12"
            )
            try:
                response, _ms = await self._timed(
                    self.client.insights(
                        filter_type="urn:entity:movie",
                        signal_interests_entities=self.programme_ids,
                        feature_explainability=flag,
                        take=12,
                        tool=f"probe_f_explainability:{flag}",
                    )
                )
            except Exception as exc:
                self._error_outcome(
                    probe_id=f"F(ex={flag})",
                    name="feature.explainability payload",
                    endpoint=endpoint,
                    request=request,
                    exc=exc,
                )
                return
            payload_bytes = len(json.dumps([r.raw for r in response.results if r.raw], default=str))
            sizes["with" if flag else "without"] = payload_bytes
            for item in response.results:
                raw = item.raw or {}
                if any(k in raw for k in ("explainability", "explanation", "attributions", "measurements")):
                    attribution_found = True
        ratio = (sizes["with"] / sizes["without"]) if sizes.get("without") else None
        limitation = ""
        if ratio is not None and ratio > 5:
            limitation = (
                f"payload grows {ratio:.1f}x with explainability on — disable it on bulk (take=50) calls"
            )
        if not attribution_found:
            limitation = (
                limitation + " | " if limitation else ""
            ) + "no attribution field observed in the response payload"
        self._add(
            ProbeOutcome(
                probe_id="F",
                name="feature.explainability payload",
                endpoint=endpoint,
                request="feature.explainability=false vs true at take=12",
                mode=self.mode,
                http_status=200,
                result_count=None,
                latency_ms=None,
                success=True,
                observed_limitation=limitation,
                extra={
                    "payload_bytes_without": sizes.get("without"),
                    "payload_bytes_with": sizes.get("with"),
                    "size_ratio": round(ratio, 2) if ratio else None,
                    "attribution_field_observed": attribution_found,
                },
            )
        )

    async def probe_g_audiences(self) -> None:
        endpoint = "/v2/audiences"
        request = (
            "GET /v2/audiences?filter.parents.types="
            "urn:audience:hobbies_and_interests,urn:audience:leisure&take=50"
        )
        try:
            response, ms = await self._timed(
                self.client.audiences(
                    filter_parents_types=["urn:audience:hobbies_and_interests", "urn:audience:leisure"],
                    take=50,
                    tool="probe_g_audiences",
                )
            )
        except Exception as exc:
            self._error_outcome(
                probe_id="G", name="Audience catalogue", endpoint=endpoint, request=request, exc=exc
            )
            return
        payload = response.data if isinstance(response.data, dict) else {}
        audiences = []
        results = payload.get("results")
        if isinstance(results, dict):
            audiences = results.get("audiences") or []
        sample_ids = [a.get("audience_id") for a in audiences[:10] if isinstance(a, dict)]
        limitation = ""
        if not audiences:
            limitation = (
                "no audiences returned for these parent categories — the concrete "
                "urn:audience:* catalogue may be smaller, differently scoped, or gated"
            )
        self._add(
            ProbeOutcome(
                probe_id="G",
                name="Audience catalogue",
                endpoint=endpoint,
                request=request,
                mode=self.mode,
                http_status=200,
                result_count=len(audiences),
                relevant_fields=sorted(audiences[0].keys())
                if audiences and isinstance(audiences[0], dict)
                else [],
                latency_ms=ms,
                success=bool(audiences),
                observed_limitation=limitation,
                extra={"sample_audience_ids": sample_ids, "results_shape": response.observed_shape},
            )
        )

    async def probe_g2_filter_tags(self) -> None:
        """Does `filter.tags` exist? It appears in our own spec but not in the docs.

        Honesty note: Qloo SILENTLY IGNORES parameters it does not recognise, so a
        200 response does not prove the parameter is honoured. The only reliable
        signal is a 4xx.
        """
        endpoint = "/v2/tags"
        request = (
            "GET /v2/tags?filter.query=slow cinema&filter.tags=urn:tag:genre&take=5"
            "   (filter.tags is UNVERIFIED)"
        )
        try:
            response, ms = await self._timed(
                self.client.tags(
                    filter_query="slow cinema",
                    filter_tags=["urn:tag:genre"],
                    take=5,
                    allow_unverified=True,
                    tool="probe_g2_filter_tags",
                )
            )
        except Exception as exc:
            outcome = self._error_outcome(
                probe_id="G2",
                name="filter.tags existence (UNVERIFIED)",
                endpoint=endpoint,
                request=request,
                exc=exc,
            )
            outcome.extra["interpretation"] = (
                "A 4xx would indicate the parameter is rejected; any other error is inconclusive."
            )
            return
        self._add(
            ProbeOutcome(
                probe_id="G2",
                name="filter.tags existence (UNVERIFIED)",
                endpoint=endpoint,
                request=request,
                mode=self.mode,
                http_status=200,
                result_count=len(response.results),
                relevant_fields=self._fields_of_first(response.results),
                latency_ms=ms,
                success=True,
                observed_limitation=(
                    "INCONCLUSIVE by construction: Qloo silently ignores unknown parameters, so a "
                    "200 does not prove filter.tags is honoured. Only a 4xx would be conclusive."
                ),
                extra={
                    "interpretation": "Do not rely on filter.tags. It is not required by the design.",
                    "tag_results_returned": len(response.results),
                },
            )
        )

    async def probe_h_rate_limit(self) -> None:
        """Deliberately small: 10 sequential calls, counting rejections."""
        if not self.is_live:
            self._add(
                ProbeOutcome(
                    probe_id="H",
                    name="Rate limit behaviour",
                    endpoint="/search",
                    request="10 sequential GET /search?query=probe&take=1",
                    mode=self.mode,
                    skipped_reason="rate limits are not observable in dry-run mode",
                )
            )
            return
        codes: list[int | str] = []
        latencies: list[int] = []
        for i in range(10):
            try:
                start = time.perf_counter()
                await self.client.search(query=f"probe{i}", take=1, tool="probe_h_rate_limit")
                latencies.append(int((time.perf_counter() - start) * 1000))
                codes.append(200)
            except QlooError as exc:
                codes.append(exc.status or exc.kind)
        rejected = sum(1 for c in codes if c != 200)
        self._add(
            ProbeOutcome(
                probe_id="H",
                name="Rate limit behaviour",
                endpoint="/search",
                request="10 sequential GET /search?query=probeN&take=1 (no pacing)",
                mode=self.mode,
                http_status=None,
                result_count=rejected,
                latency_ms=max(latencies) if latencies else None,
                success=rejected == 0,
                observed_limitation=(
                    f"{rejected}/10 calls were rejected" if rejected else "no rejections in 10 rapid calls"
                ),
                extra={
                    "status_codes": codes,
                    "rejected_count": rejected,
                    "max_latency_ms": max(latencies) if latencies else None,
                },
            )
        )

    # -- orchestration -----------------------------------------------------
    async def run(self) -> dict[str, Any]:
        print(
            f"Running probes in {self.mode} mode"
            f"{'' if self.is_live else ' (no QLOO_API_KEY — fixture-backed mock)'}"
        )
        await self.probe_a_entity_resolution()
        await self.probe_b_tag_affinity()
        await self.probe_c_cross_domain()
        await self.probe_d_results_entities()
        await self.probe_e_heatmap()
        await self.probe_f_explainability()
        await self.probe_g_audiences()
        await self.probe_h_rate_limit()
        if self.run_unverified:
            print("Running UNVERIFIED probes (explicitly opted in):")
            await self.probe_b_tag_affinity(with_parents=True)
            await self.probe_c_cross_domain(with_location=True)
            await self.probe_g2_filter_tags()
        return self.report()

    def report(self) -> dict[str, Any]:
        trace = getattr(self.client, "recorder", None)
        return {
            "generated_at": self.started_at.isoformat(),
            "mode": self.mode,
            "verified_against_qloo": self.is_live,
            "banner": None if self.is_live else NOT_EXECUTED,
            "fixture_notice": None if self.is_live else FIXTURE_NOTICE,
            "base_url": self.settings.qloo_base_url,
            "key_fingerprint": self.settings.key_fingerprint(),
            "cities_tested": self.cities,
            "programme_inputs": PROBE_PROGRAMME,
            "probes": [o.as_dict() for o in self.outcomes],
            "trace": trace.as_dicts() if trace is not None else [],
            "call_count": len(getattr(trace, "rows", []) or []),
        }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return f"`{json.dumps(value, default=str)}`"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    live = bool(report["verified_against_qloo"])
    lines: list[str] = []
    a = lines.append
    a("# API_NOTES.md")
    a("")
    a(
        "Generated by `scripts/qloo_probe.py`. This file is the record of **what we actually "
        "observed** against the Qloo API, as opposed to what the documentation implies."
    )
    a("")
    if not live:
        a("> ## ⚠️ NOT YET EXECUTED AGAINST QLOO")
        a(">")
        a(f"> {NOT_EXECUTED}")
        a(">")
        a(f"> {report.get('fixture_notice') or ''}")
        a(">")
        a(
            "> Re-run `make probe` (or `python scripts/qloo_probe.py --live`) once `QLOO_API_KEY` "
            "is set. Every result below will then be replaced with measured output."
        )
    else:
        a("> ## ✅ EXECUTED AGAINST QLOO")
        a(f"> Base URL: `{report['base_url']}` · key fingerprint: `{report['key_fingerprint']}`")
    a("")
    a(
        f"Generated: `{report['generated_at']}` · mode: `{report['mode']}` · "
        f"Qloo calls traced: `{report['call_count']}`"
    )
    a("")

    a("## 1. Probe results")
    a("")
    for probe in report["probes"]:
        a("```")
        a("--------------------------------")
        a(f"Probe              {probe['probe_id']} — {probe['name']}")
        a(f"Endpoint           {probe['endpoint']}")
        a(f"Request            {probe['request']}")
        a(f"HTTP status        {_fmt(probe['http_status'])}")
        a(f"Result count       {_fmt(probe['result_count'])}")
        a(f"Relevant fields    {', '.join(probe['relevant_fields']) or '—'}")
        a(f"Latency            {_fmt(probe['latency_ms'])} ms")
        a(f"Success / Failure  {'SUCCESS' if probe['success'] else 'FAILURE'}")
        a(f"Verified vs Qloo   {'yes' if probe['verified_against_qloo'] else 'NO (dry-run)'}")
        a(f"Observed limitation {probe['observed_limitation'] or '—'}")
        if probe.get("skipped_reason"):
            a(f"Skipped            {probe['skipped_reason']}")
        if probe.get("error"):
            a(f"Error              {json.dumps(probe['error'], default=str)}")
        a("--------------------------------")
        a("```")
        if probe.get("extra"):
            a("")
            a(f"<details><summary>Extra detail — probe {probe['probe_id']}</summary>")
            a("")
            a("```json")
            a(json.dumps(probe["extra"], indent=2, default=str))
            a("```")
            a("")
            a("</details>")
        a("")

    a("## 2. CRITICAL RESULT — `filter.results.entities`")
    a("")
    d = next((p for p in report["probes"] if p["probe_id"] == "D"), None)
    if d and d.get("extra"):
        extra = d["extra"]
        a(f"* supplied_count: **{extra.get('supplied_count')}**")
        a(f"* returned_count: **{extra.get('returned_count')}**")
        a(f"* returned_scored_count: **{extra.get('returned_scored_count')}**")
        a(f"* all_supplied_returned: **{_fmt(extra.get('all_supplied_returned'))}**")
        a(f"* all_supplied_returned_and_scored: **{_fmt(extra.get('all_supplied_returned_and_scored'))}**")
        a("")
        a(f"**Conclusion:** {extra.get('conclusion')}")
        if not live:
            a("")
            a(
                "> This conclusion is from the fixture-backed mock and is therefore NOT evidence "
                "about the real API. It exercises the reporting path only."
            )
    else:
        a("_Probe D did not run (see skipped reason above)._")
    a("")

    a("## 3. Geographic coverage by candidate city")
    a("")
    e = next((p for p in report["probes"] if p["probe_id"] == "E"), None)
    if e and e.get("extra"):
        extra = e["extra"]
        a(f"Cities tested: {', '.join(extra.get('cities_tested', []))}")
        a("")
        a("| City | Cells | Locality matched as | Supports geographic claim |")
        a("|---|---|---|---|")
        for city, data in (extra.get("per_city") or {}).items():
            if not isinstance(data, dict):
                continue
            a(
                f"| {city} | {data.get('cell_count', '—')} | {data.get('locality_matched_as', '—')} | "
                f"{data.get('supports_geographic_claim')} |"
            )
        a("")
        if extra.get("dry_run_caveat"):
            a("")
            a(f"> ⚠️ {extra['dry_run_caveat']}")
        a("")
        a(f"**Recommendation:** {extra.get('recommendation')}")
    else:
        a("_Probe E did not run._")
    a("")

    a("## 4. Parameter verification status")
    a("")
    a(
        "Every parameter the codebase may send. `UNVERIFIED` means we cannot point at current "
        "documentation for it; the validator refuses to send it unless a caller explicitly opts in."
    )
    a("")
    a("| Parameter | Kind | Endpoints | Status | Unverified on | Source |")
    a("|---|---|---|---|---|---|")
    for row in registry_summary():
        status = row["status"].upper()
        if row["status"] == "unverified":
            status = "**UNVERIFIED**"
        elif row["status"] == "deprecated":
            status = "**DEPRECATED**"
        unverified_on = ", ".join(row.get("unverified_on") or []) or "—"
        a(
            f"| `{row['param']}` | {row['kind']} | {', '.join(row['endpoints'])} | {status} | "
            f"{unverified_on} | {row['source'] or '—'} |"
        )
    a("")

    a("## 5. Open questions (must be resolved before the dependent code is built)")
    a("")
    for i, spec in enumerate(unverified_params(), start=1):
        a(f"**Q{i}. `{spec.name}`** — {spec.summary}")
        a("")
        a(f"* Question: {spec.open_question or 'Unresolved.'}")
        a("* Blocked work: see PATTERN in section 2 and the probe outcome above.")
        a("")
    a("Ask these in the hackathon `#api-help` channel; record the answer here with a date.")
    a("")

    a("## 6. Method notes")
    a("")
    a(
        "* Auth is header-only (`X-Api-Key`). The key is never placed in a query string and is "
        "redacted from every trace row."
    )
    a(
        "* Base URL is `https://hackathon.api.qloo.com`. Staging and production both return 401 "
        "for a hackathon key, so that is not a symptom of a bad key."
    )
    a('* A `404` from `/entities` means "not in Qloo" — a data outcome, never an outage.')
    a("* Probe H is deliberately small (10 calls). Do not turn the probe into load testing.")
    a("* No number in this file is estimated, interpolated or invented.")
    a("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


EXIT_OK = 0
#: Non-zero on purpose: a caller (Makefile, CI, a human) must be able to tell that
#: the live probe did NOT run. An earlier version fell back to dry-run and exited 0,
#: which made "make probe-live succeeded" indistinguishable from "the key is missing".
EXIT_KEY_MISSING = 2


async def main_async(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    cities = args.city or list(settings.probe_cities)

    # `--live` is an explicit request for real Qloo observations. It is never
    # silently downgraded to the mock: a probe that reports mock numbers under a
    # live flag is how fabricated "validation" happens.
    if args.live and not settings.has_api_key:
        print(
            "ERROR: --live was requested but QLOO_API_KEY is not set.\n"
            "Refusing to fall back to the fixture-backed mock under a live flag: a\n"
            "mock run reported as live is exactly the failure this guard exists to\n"
            "prevent.\n\n"
            "  Set the key and re-run:  export QLOO_API_KEY=...   (or put it in .env)\n"
            "  Confirm the mode:        make probe            # dry-run, no key needed\n"
            "  Then:                    make probe-live       # real Qloo",
            file=sys.stderr,
        )
        return EXIT_KEY_MISSING

    live = bool(args.live)
    if live:
        client: Any = QlooClient(settings, run_id="probe")
        print(
            f"LIVE mode against {settings.qloo_base_url} "
            f"(key {settings.key_fingerprint()}) — every result below is a real Qloo response"
        )
        if not settings.base_url_is_hackathon_host:
            print(
                f"WARNING: QLOO_BASE_URL is {settings.qloo_base_url}, not the hackathon host; "
                "hackathon keys return 401 elsewhere.",
                file=sys.stderr,
            )
    else:
        client = MockQlooClient(settings, fixture="portland_strong", run_id="probe-dryrun")
        print("DRY-RUN mode: fixture-backed mock client (no live Qloo call will be made)")

    runner = ProbeRunner(
        client=client,
        settings=settings,
        cities=cities,
        mode="live" if live else "dry-run",
        run_unverified=args.unverified,
    )
    try:
        report = await runner.run()
    finally:
        await client.aclose()

    json_path = Path(args.out_json)
    md_path = Path(args.out_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"\nWrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"\nMode: {'LIVE (real Qloo)' if live else 'dry-run (mock)'} · wrote {json_path.name} and {md_path.name}")
    if not live:
        print("\n" + "!" * 78)
        print(NOT_EXECUTED)
        print("!" * 78)
    return EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe the Qloo API and write docs/API_NOTES.md")
    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Live mode: make real Qloo calls. REQUIRED: QLOO_API_KEY. If the key is "
            "missing this exits 2 and writes nothing — it never falls back to the mock."
        ),
    )
    parser.add_argument(
        "--city",
        action="append",
        default=None,
        help="Candidate city to test for heatmap coverage (repeatable)",
    )
    parser.add_argument(
        "--unverified",
        action="store_true",
        help=(
            "Also run the probes that use UNVERIFIED parameters. Combine with --live "
            "for real observations: `make probe-live-unverified`."
        ),
    )
    parser.add_argument("--out-json", default=str(PROJECT_DIR / "docs" / "api_probe_results.json"))
    parser.add_argument("--out-md", default=str(PROJECT_DIR / "docs" / "API_NOTES.md"))
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
