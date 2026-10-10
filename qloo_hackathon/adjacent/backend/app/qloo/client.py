"""The live Qloo client — the ONLY place an HTTP request to Qloo is built.

Contract (all of it deliberate):
  * header auth only, `X-Api-Key`; the key is never placed in a query string;
  * base URL comes from configuration; defaults to the hackathon host, because
    staging and production both reject a hackathon key with 401;
  * GET only (POST-with-body is rejected by the API although POST-only params
    are documented);
  * every parameter passes through the strict allowlist in `params.py`;
  * statuses are classified — 401/403, 404, 429, 5xx and timeouts are distinct
    exception types, and 404 is a DATA OUTCOME for `/entities`, not a fault;
  * every call is traced, with redacted parameters;
  * errors are never swallowed: every failure is either retried (bounded) or
    raised.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

import httpx

from ..config import Settings
from . import params as P
from .errors import (
    AuthenticationError,
    InvalidCombinationError,
    InvalidResponseError,
    MissingApiKeyError,
    NotFoundError,
    QlooError,
    QlooTimeoutError,
    RateLimitError,
    TransportError,
    UnverifiedParameterError,
    UpstreamError,
)
from .models import (
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


def _count_results(payload: dict[str, Any]) -> int:
    """Count result items straight from the response body.

    Recorded on the trace row at call time so the Evidence Panel reports what the
    API returned, not what we hoped it returned.
    """
    results = payload.get("results")
    if isinstance(results, list):
        return len(results)
    if isinstance(results, dict):
        return sum(len(v) for v in results.values() if isinstance(v, list))
    return 0


class _RateLimiter:
    """Minimal token-bucket-ish pacer. `rps <= 0` disables pacing (tests only)."""

    def __init__(self, rps: float) -> None:
        self.enabled = rps and rps > 0
        self._interval = (1.0 / rps) if self.enabled else 0.0
        self._next_at = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        if not self.enabled:
            return
        async with self._lock:
            now = time.monotonic()
            wait = self._next_at - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = time.monotonic()
            self._next_at = max(now, self._next_at) + self._interval


@runtime_checkable
class QlooClientProtocol(Protocol):
    """The interface shared by `QlooClient` and `MockQlooClient`.

    Both implementations must satisfy this, so the agent can be developed and
    tested entirely against fixtures and then switched to live data by changing
    one constructor call.
    """

    async def search(self, **kwargs: Any) -> SearchResponse: ...
    async def insights(self, **kwargs: Any) -> Any: ...
    async def entities(self, **kwargs: Any) -> EntitiesResponse: ...
    async def tags(self, **kwargs: Any) -> TagSearchResponse: ...
    async def audiences(self, **kwargs: Any) -> RawResponse: ...
    async def trending(self, **kwargs: Any) -> RawResponse: ...
    async def compare(self, **kwargs: Any) -> RawResponse: ...
    async def aclose(self) -> None: ...


class QlooClient:
    """Live client. Constructing this without an API key raises immediately."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        recorder: TraceRecorder | None = None,
        run_id: str = "local",
        require_key: bool = True,
    ) -> None:
        self.settings = settings or Settings.from_env()
        if require_key and not self.settings.has_api_key:
            raise MissingApiKeyError(
                "QLOO_API_KEY is not set. Use MockQlooClient for fixture-backed work, "
                "or export the key before constructing QlooClient."
            )
        self.recorder = recorder or TraceRecorder(run_id=run_id, secret=self.settings.qloo_api_key)
        self._limiter = _RateLimiter(self.settings.rate_limit_rps)
        self._transport = transport
        self._http: httpx.AsyncClient | None = None

    # -- plumbing ----------------------------------------------------------
    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self.settings.qloo_base_url,
                timeout=httpx.Timeout(
                    connect=self.settings.connect_timeout_s,
                    read=self.settings.read_timeout_s,
                    write=self.settings.read_timeout_s,
                    pool=self.settings.connect_timeout_s,
                ),
                transport=self._transport,
                headers={
                    # Header auth ONLY. Never a query parameter, never Bearer.
                    "X-Api-Key": self.settings.qloo_api_key or "",
                    "Accept": "application/json",
                    "User-Agent": "adjacent-hackathon/0.1 (+https://devpost.com)",
                },
            )
        return self._http

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def __aenter__(self) -> QlooClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    def _classify(self, response: httpx.Response, endpoint: str) -> QlooError:
        status = response.status_code
        body = response.text[:1000]
        if status in (401, 403):
            return AuthenticationError(
                f"Qloo rejected the credentials (HTTP {status}). Check that the key is a "
                "hackathon key and that the base URL is https://hackathon.api.qloo.com — "
                "staging/production return 401 for hackathon keys.",
                endpoint=endpoint,
                status=status,
                detail=body,
            )
        if status == 404:
            return NotFoundError(
                f"Qloo returned 404 for {endpoint}. For /entities this means 'not in Qloo' "
                "and is a data outcome, not a system failure.",
                endpoint=endpoint,
                status=status,
                detail=body,
            )
        if status == 429:
            retry_after = response.headers.get("Retry-After")
            try:
                retry_after_s = float(retry_after) if retry_after else None
            except ValueError:
                retry_after_s = None
            return RateLimitError(
                f"Qloo rate limited the call to {endpoint}.",
                endpoint=endpoint,
                status=status,
                detail=body,
                retry_after_s=retry_after_s,
            )
        if status >= 500:
            return UpstreamError(
                f"Qloo returned HTTP {status} for {endpoint}.",
                endpoint=endpoint,
                status=status,
                detail=body,
            )
        return QlooError(
            f"Qloo returned HTTP {status} for {endpoint}.",
            endpoint=endpoint,
            status=status,
            detail=body,
            retryable=False,
        )

    def _delay(self, attempt: int, error: QlooError) -> float:
        if isinstance(error, RateLimitError) and error.retry_after_s:
            return max(0.0, error.retry_after_s)
        base = self.settings.retry_backoff_base_s * (2 ** (attempt - 1))
        return base + random.uniform(0, base / 2)

    async def _get(
        self,
        *,
        endpoint: str,
        built: P.BuiltParams,
        tool: str,
    ) -> tuple[dict[str, Any], str]:
        """Execute one validated GET, with pacing, bounded retries and tracing."""
        attempts = max(1, self.settings.max_retries + 1)
        with self.recorder.record(
            tool=tool,
            endpoint=endpoint,
            params=built.params,
            source="qloo",
            data_status="measured",
        ) as call:
            for note in built.warnings:
                call.add_note(note)
            query = built.as_query()
            last_error: QlooError | None = None

            for attempt in range(1, attempts + 1):
                call.set_attempt(attempt)
                await self._limiter.acquire()
                try:
                    response = await self.http.get(endpoint, params=query)
                except httpx.TimeoutException as exc:
                    last_error = QlooTimeoutError(
                        f"Timed out calling {endpoint} after {self.settings.read_timeout_s}s.",
                        endpoint=endpoint,
                        call_id=call.call_id,
                        detail=str(exc),
                    )
                except httpx.HTTPError as exc:
                    last_error = TransportError(
                        f"Network failure calling {endpoint}: {type(exc).__name__}",
                        endpoint=endpoint,
                        call_id=call.call_id,
                        detail=str(exc),
                    )
                else:
                    call.status = response.status_code
                    if response.status_code == 200:
                        try:
                            payload = response.json()
                        except json.JSONDecodeError as exc:
                            error = InvalidResponseError(
                                f"{endpoint} returned 200 but the body was not JSON.",
                                endpoint=endpoint,
                                call_id=call.call_id,
                                detail=response.text[:500],
                            )
                            call.set_error(error)
                            raise error from exc
                        if not isinstance(payload, dict):
                            error = InvalidResponseError(
                                f"{endpoint} returned 200 but the body was not a JSON object.",
                                endpoint=endpoint,
                                call_id=call.call_id,
                                detail=str(type(payload)),
                            )
                            call.set_error(error)
                            raise error
                        call.set_result(status=200, result_count=_count_results(payload))
                        return payload, call.call_id
                    last_error = self._classify(response, endpoint)

                call.set_result(status=call.status)
                retryable = bool(last_error and last_error.retryable)
                if not retryable or attempt >= attempts:
                    call.set_error(last_error)  # type: ignore[arg-type]
                    raise last_error  # type: ignore[misc]
                call.add_note(f"attempt {attempt} failed ({last_error.kind}); retrying after backoff")
                await asyncio.sleep(self._delay(attempt, last_error))

            # Unreachable: the loop either returns or raises.
            raise UpstreamError(f"Exhausted retries calling {endpoint}", endpoint=endpoint)

    @staticmethod
    def _reject_unsupported(unsupported: Mapping[str, Any], endpoint: str) -> None:
        if unsupported:
            names = ", ".join(sorted(unsupported))
            raise UnverifiedParameterError(
                f"Unsupported/unknown argument(s) for {endpoint}: {names}. Adjacent refuses to "
                "send parameters it cannot point at documentation for, because Qloo silently "
                "ignores unknown parameters and returns an empty result instead of an error.",
                endpoint=endpoint,
            )

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
        payload, call_id = await self._get(endpoint=P.EP_SEARCH, built=built, tool=tool)
        return parse_search(
            payload, call_id=call_id, source="qloo", data_status="measured", endpoint=P.EP_SEARCH
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
        """GET /v2/insights. The parser is chosen from the validated `filter.type`."""
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
        payload, call_id = await self._get(endpoint=P.EP_INSIGHTS, built=built, tool=tool)
        ft = built.filter_type or filter_type
        common = {"call_id": call_id, "source": "qloo", "data_status": "measured", "endpoint": P.EP_INSIGHTS}
        if ft == "urn:heatmap":
            return parse_heatmap(payload, **common)  # type: ignore[arg-type]
        if ft == "urn:tag":
            return parse_tag_affinity(payload, **common)  # type: ignore[arg-type]
        if ft in P.ENTITY_FILTER_TYPES:
            return parse_entity_affinity(payload, **common, extra_notes=built.warnings)  # type: ignore[arg-type]
        # urn:demographics, urn:entity:locality, ... not modelled on Day 1.
        return parse_raw(payload, **common)  # type: ignore[arg-type]

    async def entities(
        self,
        *,
        entity_ids: Sequence[str] | None = None,
        external_ids: Mapping[str, Sequence[str]] | None = None,
        allow_unverified: bool = False,
        tool: str = "resolve_entities",
        **unsupported: Any,
    ) -> EntitiesResponse:
        """GET /entities — batch lookup by Qloo UUID or by external ID family.

        NOTE 1: a 404 here means "none of these ids are in Qloo". Callers must
        treat it as a data outcome (an unresolved programme item), not an outage.

        NOTE 2: `take`/`page` are deliberately NOT accepted here — pagination for
        this endpoint is not in the documentation we verified, and we do not send
        unverified parameters. Verify it first if batch size becomes a problem.
        """
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
                    f"'{family}' is not a documented external ID family for /entities. "
                    f"Known families: {', '.join(P.EXTERNAL_ID_FAMILIES)}.",
                    parameter=key,
                    endpoint=P.EP_ENTITIES,
                )
            values[key] = ids
            requested_external[family] = list(ids)
        built = P.build_params(P.EP_ENTITIES, values, allow_unverified=allow_unverified)
        payload, call_id = await self._get(endpoint=P.EP_ENTITIES, built=built, tool=tool)
        return parse_entities(
            payload,
            call_id=call_id,
            source="qloo",
            data_status="measured",
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
        payload, call_id = await self._get(endpoint=P.EP_TAGS, built=built, tool=tool)
        return parse_tag_search(
            payload, call_id=call_id, source="qloo", data_status="measured", endpoint=P.EP_TAGS
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
        built = P.build_params(
            P.EP_AUDIENCES,
            {
                "filter.query": filter_query,
                "filter.audience.types": filter_audience_types,
                "filter.results.audiences": filter_results_audiences,
                "filter.parents.types": filter_parents_types,
                "filter.popularity.min": filter_popularity_min,
                "filter.popularity.max": filter_popularity_max,
                "take": take,
                "page": page,
            },
            allow_unverified=allow_unverified,
        )
        payload, call_id = await self._get(endpoint=P.EP_AUDIENCES, built=built, tool=tool)
        return parse_raw(
            payload, call_id=call_id, source="qloo", data_status="measured", endpoint=P.EP_AUDIENCES
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
        """`filter.start_date` and `filter.end_date` are REQUIRED, not optional."""
        self._reject_unsupported(unsupported, P.EP_TRENDING)
        built = P.build_params(
            P.EP_TRENDING,
            {
                "filter.type": filter_type,
                "filter.start_date": filter_start_date,
                "filter.end_date": filter_end_date,
                "signal.interests.entities": signal_interests_entities,
                "take": take,
                "page": page,
            },
            allow_unverified=allow_unverified,
        )
        payload, call_id = await self._get(endpoint=P.EP_TRENDING, built=built, tool=tool)
        return parse_raw(
            payload, call_id=call_id, source="qloo", data_status="measured", endpoint=P.EP_TRENDING
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
        """Compares two ENTITY GROUPS. There is no demographic signal here."""
        self._reject_unsupported(unsupported, P.EP_COMPARE)
        built = P.build_params(
            P.EP_COMPARE,
            {
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
            allow_unverified=allow_unverified,
        )
        payload, call_id = await self._get(endpoint=P.EP_COMPARE, built=built, tool=tool)
        return parse_raw(
            payload, call_id=call_id, source="qloo", data_status="measured", endpoint=P.EP_COMPARE
        )
