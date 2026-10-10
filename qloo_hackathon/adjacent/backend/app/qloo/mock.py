"""Fixture-backed Qloo client.

Same interface as `QlooClient` (see `QlooClientProtocol`), so the entire agent
can be written, tested and demonstrated before an API key exists.

Honesty rules:
  * every response this client returns carries `source="mock"` and
    `data_status="fixture"`;
  * fixture files declare, in-band, that they are synthetic;
  * if a request has no matching fixture branch, the client returns an EMPTY
    documented-shape response plus a note — it never invents entities, scores,
    places or tags to fill a gap;
  * a `/entities` lookup that matches nothing raises `NotFoundError`, mirroring
    the live API's 404 semantics, so callers handle it now rather than on day 20.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import Settings
from . import params as P
from .errors import InvalidCombinationError, NotFoundError, UnverifiedParameterError
from .models import (
    DataStatus,
    EntitiesResponse,
    EntityAffinityResponse,
    HeatmapResponse,
    RawResponse,
    SearchResponse,
    TagAffinityResponse,
    TagSearchResponse,
    parse_entities,
    parse_entity_affinity,
    parse_heatmap,
    parse_raw,
    parse_search,
    parse_tag_affinity,
    parse_tag_search,
)
from .trace import TraceRecorder

FIXTURE_NOTICE = (
    "SYNTHETIC FIXTURE DATA — hand-authored to match documented Qloo response shapes. "
    "NOT measured Qloo output and must never be presented as such."
)

DEFAULT_FIXTURE = "portland_strong"


@dataclass
class Fixture:
    """A loaded scenario fixture."""

    name: str
    path: Path
    data: dict[str, Any]

    @property
    def scenario(self) -> str:
        return str(self.data.get("scenario", self.name))

    @property
    def description(self) -> str:
        return str(self.data.get("description", ""))

    @property
    def programme(self) -> list[dict[str, Any]]:
        return list(self.data.get("programme", []))

    @property
    def entity_ids(self) -> list[str]:
        return [str(p["entity_id"]) for p in self.programme if p.get("entity_id")]

    @property
    def expectations(self) -> dict[str, Any]:
        return dict(self.data.get("expectations", {}))

    @property
    def responses(self) -> dict[str, Any]:
        return dict(self.data.get("responses", {}))

    @property
    def city_query(self) -> str | None:
        city = self.data.get("city")
        return city.get("query") if isinstance(city, dict) else None


def load_fixture(name: str = DEFAULT_FIXTURE, *, fixtures_dir: Path | None = None) -> Fixture:
    directory = fixtures_dir or Settings.from_env().fixtures_dir
    path = directory / f"{name}.json"
    if not path.exists():
        available = sorted(p.stem for p in directory.glob("*.json")) if directory.exists() else []
        raise FileNotFoundError(f"Fixture {name!r} not found at {path}. Available: {available}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Fixture {path} must contain a JSON object")
    return Fixture(name=name, path=path, data=data)


def _empty_payload(reason: str) -> dict[str, Any]:
    return {"results": {}, "_fixture_note": reason}


class MockQlooClient:
    """Fixture-backed implementation of the Qloo client interface."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        fixture: str = DEFAULT_FIXTURE,
        recorder: TraceRecorder | None = None,
        run_id: str = "local",
        simulate_latency_ms: int = 0,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.fixture = load_fixture(fixture, fixtures_dir=self.settings.fixtures_dir)
        self.recorder = recorder or TraceRecorder(run_id=run_id, secret=self.settings.qloo_api_key)
        self.simulate_latency_ms = simulate_latency_ms
        self._logged_notice = False

    # -- plumbing ----------------------------------------------------------
    @property
    def notice(self) -> str:
        return FIXTURE_NOTICE

    async def aclose(self) -> None:
        return None

    async def __aenter__(self) -> MockQlooClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def _sleep(self) -> None:
        if self.simulate_latency_ms > 0:
            import asyncio

            await asyncio.sleep(self.simulate_latency_ms / 1000)

    def _branch(self, *keys: str) -> dict[str, Any] | None:
        node: Any = self.fixture.responses
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return None
            node = node[key]
        return node if isinstance(node, dict) else None

    def _resolve(self, *keys: str) -> tuple[dict[str, Any], str | None]:
        """Return (payload, note). A missing branch yields an empty, noted payload."""
        node = self._branch(*keys)
        if node is None:
            reason = (
                f"no fixture branch for {'/'.join(keys)} in scenario "
                f"'{self.fixture.scenario}'; returning an empty result set rather than "
                "inventing data"
            )
            return _empty_payload(reason), reason
        return node, None

    @staticmethod
    def _restrict_to(payload: dict[str, Any], entity_ids: Sequence[str]) -> dict[str, Any]:
        """Used when `filter.results.entities` is supplied, to mirror scoring a fixed set."""
        wanted = {str(i) for i in entity_ids}
        results = payload.get("results")
        if not isinstance(results, dict):
            return payload
        entities = results.get("entities")
        if not isinstance(entities, list):
            return payload
        kept = [
            e
            for e in entities
            if isinstance(e, dict) and str(e.get("entity_id") or e.get("id") or "") in wanted
        ]
        cloned = dict(payload)
        cloned["results"] = {**results, "entities": kept}
        return cloned

    @staticmethod
    def _key(**flags: Any) -> str:
        parts = [k for k, v in flags.items() if v]
        return "|".join(parts)

    # -- endpoints ---------------------------------------------------------
    async def search(
        self,
        *,
        query: str,
        types: Sequence[str] | None = None,
        take: int | None = None,
        page: int | None = None,
        feature_typo_tolerance: bool | None = None,
        allow_unverified: bool = False,
        tool: str = "search",
        **unsupported: Any,
    ) -> SearchResponse:
        self._reject_unsupported(unsupported, P.EP_SEARCH)
        built = P.build_params(
            P.EP_SEARCH,
            {
                "query": query,
                "types": types,
                "take": take,
                "page": page,
                "feature.typo_tolerance": feature_typo_tolerance,
            },
            allow_unverified=allow_unverified,
        )
        await self._sleep()
        with self.recorder.record(
            tool=tool, endpoint=P.EP_SEARCH, params=built.params, source="mock", data_status="fixture"
        ) as call:
            payload, note = self._resolve("search", "default")
            if note:
                call.add_note(note)
            call.add_note(FIXTURE_NOTICE)
            results = payload.get("results", {})
            count = len(results.get("entities", [])) if isinstance(results, dict) else 0
            call.set_result(status=200, result_count=count)
            return parse_search(
                payload,
                call_id=call.call_id,
                source="mock",
                data_status="fixture",
                endpoint=P.EP_SEARCH,
            )

    async def insights(
        self,
        *,
        filter_type: str,
        filter_subtype: Sequence[str] | None = None,
        signal_interests_entities: Sequence[str] | None = None,
        signal_interests_tags: Sequence[str] | None = None,
        signal_demographics_audiences: Sequence[str] | None = None,
        signal_demographics_age: Sequence[str] | None = None,
        signal_demographics_gender: Sequence[str] | None = None,
        filter_results_entities: Sequence[str] | None = None,
        filter_exclude_entities: Sequence[str] | None = None,
        filter_popularity_min: float | None = None,
        filter_popularity_max: float | None = None,
        filter_location_query: str | None = None,
        filter_location_radius: float | None = None,
        output_heatmap_boundary: str | None = None,
        feature_explainability: bool | None = None,
        diversify_by: str | None = None,
        backfill_cross_domain_take: int | None = None,
        backfill_content_based_take: int | None = None,
        filter_parents_types: Sequence[str] | None = None,
        filter_tags: Sequence[str] | None = None,
        signal_location_query: str | None = None,
        take: int | None = None,
        page: int | None = None,
        allow_unverified: bool = False,
        tool: str = "insights",
        **unsupported: Any,
    ) -> TagAffinityResponse | EntityAffinityResponse | HeatmapResponse | RawResponse:
        self._reject_unsupported(unsupported, P.EP_INSIGHTS)
        built = P.build_params(
            P.EP_INSIGHTS,
            {
                "filter.type": filter_type,
                "filter.subtype": filter_subtype,
                "signal.interests.entities": signal_interests_entities,
                "signal.interests.tags": signal_interests_tags,
                "signal.demographics.audiences": signal_demographics_audiences,
                "signal.demographics.age": signal_demographics_age,
                "signal.demographics.gender": signal_demographics_gender,
                "filter.results.entities": filter_results_entities,
                "filter.exclude.entities": filter_exclude_entities,
                "filter.popularity.min": filter_popularity_min,
                "filter.popularity.max": filter_popularity_max,
                "filter.location.query": filter_location_query,
                "filter.location.radius": filter_location_radius,
                "output.heatmap.boundary": output_heatmap_boundary,
                "feature.explainability": feature_explainability,
                "diversify.by": diversify_by,
                "backfill.cross_domain.take": backfill_cross_domain_take,
                "backfill.content_based.take": backfill_content_based_take,
                "filter.parents.types": filter_parents_types,
                "filter.tags": filter_tags,
                "signal.location.query": signal_location_query,
                "take": take,
                "page": page,
            },
            allow_unverified=allow_unverified,
        )
        ft = built.filter_type or filter_type
        variant = "results" if filter_results_entities is not None else "default"
        await self._sleep()
        with self.recorder.record(
            tool=tool, endpoint=P.EP_INSIGHTS, params=built.params, source="mock", data_status="fixture"
        ) as call:
            for warning in built.warnings:
                call.add_note(warning)
            call.add_note(FIXTURE_NOTICE)
            payload, note = self._resolve("insights", ft, variant)
            if note and variant != "default":
                payload, note = self._resolve("insights", ft, "default")
                if note:
                    call.add_note(f"no '{variant}' branch; falling back to default branch")
            if note:
                call.add_note(note)
            if filter_results_entities:
                supplied = [str(i) for i in filter_results_entities]
                payload = self._restrict_to(payload, supplied)
                returned = len(payload.get("results", {}).get("entities", []))  # type: ignore[union-attr]
                call.add_note(
                    f"filter.results.entities: supplied={len(supplied)} returned={returned} "
                    "(fixture behaviour — the live behaviour is probe D)"
                )
            common = {
                "call_id": call.call_id,
                "source": "mock",
                "data_status": "fixture",
                "endpoint": P.EP_INSIGHTS,
            }
            if ft == "urn:heatmap":
                response = parse_heatmap(payload, **common)  # type: ignore[arg-type]
                call.set_result(status=200, result_count=len(response.results))
                return response
            if ft == "urn:tag":
                tag_response = parse_tag_affinity(payload, **common)  # type: ignore[arg-type]
                call.set_result(status=200, result_count=len(tag_response.results))
                return tag_response
            if ft in P.ENTITY_FILTER_TYPES:
                entity_response = parse_entity_affinity(
                    payload,
                    **common,
                    extra_notes=built.warnings,  # type: ignore[arg-type]
                )
                call.set_result(
                    status=200,
                    result_count=len(entity_response.results),
                )
                self._flag_backfill(call, entity_response.results, built)
                return entity_response
            raw = parse_raw(payload, **common)  # type: ignore[arg-type]
            call.set_result(status=200, result_count=0)
            return raw

    @staticmethod
    def _flag_backfill(call: Any, results: Sequence[Any], built: P.BuiltParams) -> None:
        """Backfill entries are appended below primary results; label them, never hide them."""
        requested = 0
        if built.params.get("backfill.cross_domain.take"):
            requested += int(built.params["backfill.cross_domain.take"])
        if built.params.get("backfill.content_based.take"):
            requested += int(built.params["backfill.content_based.take"])
        if requested and len(results) >= requested:
            call.set_backfill(
                True,
                f"last {requested} result(s) are content-similarity backfill, NOT affinity evidence",
            )

    async def entities(
        self,
        *,
        entity_ids: Sequence[str] | None = None,
        external_ids: Mapping[str, Sequence[str]] | None = None,
        allow_unverified: bool = False,
        tool: str = "resolve_entities",
        **unsupported: Any,
    ) -> EntitiesResponse:
        """Same contract as QlooClient.entities, including: no unverified take/page."""
        self._reject_unsupported(unsupported, P.EP_ENTITIES)
        if not entity_ids and not external_ids:
            raise InvalidCombinationError(
                "/entities requires either entity_ids or at least one external.<family>.ids parameter.",
                endpoint=P.EP_ENTITIES,
            )
        values: dict[str, Any] = {"entity_ids": entity_ids}
        requested_external: dict[str, list[str]] = {}
        for family, ids in (external_ids or {}).items():
            key = family if family.startswith("external.") else f"external.{family}.ids"
            if key not in P.REGISTRY:
                raise UnverifiedParameterError(
                    f"'{family}' is not a documented external ID family for /entities.",
                    parameter=key,
                    endpoint=P.EP_ENTITIES,
                )
            values[key] = ids
            requested_external[family] = list(ids)
        built = P.build_params(P.EP_ENTITIES, values, allow_unverified=allow_unverified)
        await self._sleep()
        with self.recorder.record(
            tool=tool, endpoint=P.EP_ENTITIES, params=built.params, source="mock", data_status="fixture"
        ) as call:
            call.add_note(FIXTURE_NOTICE)
            if external_ids:
                family = next(iter(external_ids))
                payload, note = self._resolve("entities", "external", family)
            else:
                payload, note = self._resolve("entities", "by_id")
            if note:
                call.add_note(note)
            if entity_ids:
                payload = self._restrict_to(payload, entity_ids)
            results = payload.get("results", {})
            count = len(results.get("entities", [])) if isinstance(results, dict) else 0
            if count == 0:
                # Mirror the live API: 404 means "not in Qloo", a data outcome.
                call.set_result(status=404, result_count=0)
                raise NotFoundError(
                    "None of the supplied ids are present in the fixture (the live API returns "
                    "404 in this situation). Treat as 'not in Qloo', not as an outage.",
                    endpoint=P.EP_ENTITIES,
                    call_id=call.call_id,
                )
            call.set_result(status=200, result_count=count)
            return parse_entities(
                payload,
                call_id=call.call_id,
                source="mock",
                data_status="fixture",
                endpoint=P.EP_ENTITIES,
                requested_entity_ids=list(entity_ids or []),
                requested_external=requested_external,
            )

    async def tags(
        self,
        *,
        filter_query: str | None = None,
        filter_tag_types: Sequence[str] | None = None,
        filter_results_tags: Sequence[str] | None = None,
        filter_popularity_min: float | None = None,
        filter_popularity_max: float | None = None,
        filter_parents_types: Sequence[str] | None = None,
        feature_typo_tolerance: bool | None = None,
        feature_semantic_search: bool | None = None,
        take: int | None = None,
        page: int | None = None,
        allow_unverified: bool = False,
        tool: str = "tags",
        **unsupported: Any,
    ) -> TagSearchResponse:
        self._reject_unsupported(unsupported, P.EP_TAGS)
        built = P.build_params(
            P.EP_TAGS,
            {
                "filter.query": filter_query,
                "filter.tag.types": filter_tag_types,
                "filter.results.tags": filter_results_tags,
                "filter.popularity.min": filter_popularity_min,
                "filter.popularity.max": filter_popularity_max,
                "filter.parents.types": filter_parents_types,
                "feature.typo_tolerance": feature_typo_tolerance,
                "feature.semantic_search": feature_semantic_search,
                "take": take,
                "page": page,
            },
            allow_unverified=allow_unverified,
        )
        await self._sleep()
        with self.recorder.record(
            tool=tool, endpoint=P.EP_TAGS, params=built.params, source="mock", data_status="fixture"
        ) as call:
            call.add_note(FIXTURE_NOTICE)
            payload, note = self._resolve("tags", "default")
            if note:
                call.add_note(note)
            results = payload.get("results", {})
            count = len(results.get("tags", [])) if isinstance(results, dict) else 0
            call.set_result(status=200, result_count=count)
            return parse_tag_search(
                payload,
                call_id=call.call_id,
                source="mock",
                data_status="fixture",
                endpoint=P.EP_TAGS,
            )

    async def _raw_endpoint(
        self,
        endpoint: str,
        *,
        tool: str,
        values: Mapping[str, Any],
        branch: str,
        allow_unverified: bool = False,
    ) -> RawResponse:
        built = P.build_params(endpoint, values, allow_unverified=allow_unverified)
        await self._sleep()
        with self.recorder.record(
            tool=tool, endpoint=endpoint, params=built.params, source="mock", data_status="fixture"
        ) as call:
            call.add_note(FIXTURE_NOTICE)
            call.add_note(
                f"{endpoint} is not modelled in detail on Day 1; raw payload preserved for provenance."
            )
            payload, note = self._resolve(branch, "default")
            if note:
                call.add_note(note)
            call.set_result(status=200, result_count=0)
            return parse_raw(
                payload,
                call_id=call.call_id,
                source="mock",
                data_status="fixture",
                endpoint=endpoint,
            )

    async def audiences(
        self,
        *,
        filter_query: str | None = None,
        filter_audience_types: Sequence[str] | None = None,
        filter_results_audiences: Sequence[str] | None = None,
        filter_parents_types: Sequence[str] | None = None,
        filter_popularity_min: float | None = None,
        filter_popularity_max: float | None = None,
        take: int | None = None,
        page: int | None = None,
        allow_unverified: bool = False,
        tool: str = "audiences",
        **unsupported: Any,
    ) -> RawResponse:
        self._reject_unsupported(unsupported, P.EP_AUDIENCES)
        return await self._raw_endpoint(
            P.EP_AUDIENCES,
            tool=tool,
            values={
                "filter.query": filter_query,
                "filter.audience.types": filter_audience_types,
                "filter.results.audiences": filter_results_audiences,
                "filter.parents.types": filter_parents_types,
                "filter.popularity.min": filter_popularity_min,
                "filter.popularity.max": filter_popularity_max,
                "take": take,
                "page": page,
            },
            branch="audiences",
            allow_unverified=allow_unverified,
        )

    async def trending(
        self,
        *,
        filter_type: str,
        filter_start_date: str,
        filter_end_date: str,
        signal_interests_entities: Sequence[str] | None = None,
        take: int | None = None,
        page: int | None = None,
        allow_unverified: bool = False,
        tool: str = "trending",
        **unsupported: Any,
    ) -> RawResponse:
        self._reject_unsupported(unsupported, P.EP_TRENDING)
        return await self._raw_endpoint(
            P.EP_TRENDING,
            tool=tool,
            values={
                "filter.type": filter_type,
                "filter.start_date": filter_start_date,
                "filter.end_date": filter_end_date,
                "signal.interests.entities": signal_interests_entities,
                "take": take,
                "page": page,
            },
            branch="trending",
            allow_unverified=allow_unverified,
        )

    async def compare(
        self,
        *,
        a_signal_interests_entities: Sequence[str],
        b_signal_interests_entities: Sequence[str],
        filter_type: str,
        filter_subtype: str | None = None,
        model: str | None = None,
        filter_location_query: str | None = None,
        take: int | None = None,
        page: int | None = None,
        offset: int | None = None,
        allow_unverified: bool = False,
        tool: str = "compare",
        **unsupported: Any,
    ) -> RawResponse:
        self._reject_unsupported(unsupported, P.EP_COMPARE)
        return await self._raw_endpoint(
            P.EP_COMPARE,
            tool=tool,
            values={
                "a.signal.interests.entities": a_signal_interests_entities,
                "b.signal.interests.entities": b_signal_interests_entities,
                "filter.type": filter_type,
                "filter.subtype": filter_subtype,
                "model": model,
                "filter.location.query": filter_location_query,
                "take": take,
                "page": page,
                "offset": offset,
            },
            branch="compare",
            allow_unverified=allow_unverified,
        )

    @staticmethod
    def _reject_unsupported(unsupported: Mapping[str, Any], endpoint: str) -> None:
        if unsupported:
            names = ", ".join(sorted(unsupported))
            raise UnverifiedParameterError(
                f"Unsupported/unknown argument(s) for {endpoint}: {names}.",
                endpoint=endpoint,
            )


def data_status_of(client: Any) -> DataStatus:
    return "fixture" if isinstance(client, MockQlooClient) else "measured"
