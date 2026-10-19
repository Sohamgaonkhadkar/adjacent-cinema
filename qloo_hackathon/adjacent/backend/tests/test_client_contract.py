"""Qloo client contract: auth, classification, tracing and redaction.

Every test here runs WITHOUT a real API key. The live client is exercised
against `httpx.MockTransport`, which is why the transport is injectable.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest
from app.config import Settings
from app.main import app
from app.qloo import (
    AuthenticationError,
    MockQlooClient,
    NotFoundError,
    QlooClient,
    QlooClientProtocol,
    QlooError,
    QlooTimeoutError,
    RateLimitError,
    TraceRecorder,
    UnverifiedParameterError,
    UpstreamError,
)
from app.qloo.client import _RATE_LIMITER_REGISTRY
from app.qloo.errors import InvalidCombinationError, MissingApiKeyError
from app.qloo.models import EntityAffinityResponse, TagAffinityResponse
from app.qloo.trace import REDACTED, redact, redact_params
from fastapi.testclient import TestClient

#: Deliberately non-real. Tests must never need a working key.
FAKE_KEY = "test-key-not-real-0000"

SUCCESS_TAGS = {
    "results": {
        "tags": [
            {
                "tag_id": "urn:tag:keyword:media:slow_cinema",
                "name": "Slow Cinema",
                "subtype": "urn:tag:keyword",
                "affinity": 0.84,
                "properties": {"popularity": 0.31},
            },
            {
                "tag_id": "urn:tag:genre:movie:crime_noir",
                "name": "Crime Noir",
                "subtype": "urn:tag:genre",
                "affinity": 0.44,
                "properties": {"popularity": 0.41},
            },
        ]
    },
    "query": {"tags": {"filter": {"types": ["urn:tag"]}}},
}
SUCCESS_ARTISTS = {
    "results": {
        "entities": [
            {
                "entity_id": "22222222-2222-4222-8222-000000000001",
                "name": "Example Ambient Artist",
                "type": "urn:entity:artist",
                "subtype": "musician",
                "affinity": 0.79,
                "properties": {"popularity": 0.24, "tags": ["urn:tag:genre:music:ambient"]},
            },
        ]
    },
    "query": {"entities": {"filter": {"types": ["urn:entity:artist"]}}},
}


def client_with(handler: Any, settings: Settings) -> QlooClient:
    return QlooClient(settings, transport=httpx.MockTransport(handler), run_id="contract")


def settings_with(**overrides: Any) -> Settings:
    base = {
        "qloo_api_key": FAKE_KEY,
        "rate_limit_rps": 0.0,
        "max_retries": 0,
        "retry_backoff_base_s": 0.0,
    }
    base.update(overrides)
    return Settings.from_env(**base)


def respond(status: int, payload: Any = None, headers: dict[str, str] | None = None) -> Any:
    body = payload if payload is not None else {"error": f"status {status}"}

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body, headers=headers or {})

    return handler


# --- construction -----------------------------------------------------------


def test_live_client_refuses_to_construct_without_a_key(no_key_settings: Settings) -> None:
    with pytest.raises(MissingApiKeyError):
        QlooClient(no_key_settings)


def test_mock_client_needs_no_key(no_key_settings: Settings) -> None:
    client = MockQlooClient(no_key_settings)
    assert client.fixture.scenario
    asyncio.run(client.aclose())


def test_live_clients_share_a_strictest_per_key_process_rate_limit() -> None:
    key = "synthetic-rate-limit-test-key-not-real"
    fast = QlooClient(Settings.from_env(
        qloo_api_key=key,
        qloo_base_url="https://hackathon.api.qloo.com",
        rate_limit_rps=20.0,
    ))
    slow = QlooClient(Settings.from_env(
        qloo_api_key=key,
        qloo_base_url="https://hackathon.api.qloo.com",
        rate_limit_rps=2.0,
    ))
    other_key = QlooClient(Settings.from_env(
        qloo_api_key=f"{key}-other",
        qloo_base_url="https://hackathon.api.qloo.com",
        rate_limit_rps=20.0,
    ))
    other_host = QlooClient(Settings.from_env(
        qloo_api_key=key,
        qloo_base_url="https://other-qloo.invalid",
        rate_limit_rps=20.0,
    ))

    assert fast._limiter is slow._limiter
    assert slow._limiter._interval == pytest.approx(0.5)
    assert fast._limiter is not other_key._limiter
    assert fast._limiter is not other_host._limiter
    # The registry stores only a digest, never the configured credential.
    assert key not in repr(_RATE_LIMITER_REGISTRY)


def test_real_and_mock_clients_share_the_same_interface(no_key_settings: Settings) -> None:
    live = QlooClient(settings_with(), transport=httpx.MockTransport(respond(200, SUCCESS_TAGS)))
    mock = MockQlooClient(no_key_settings)
    assert isinstance(live, QlooClientProtocol)
    assert isinstance(mock, QlooClientProtocol)
    for name in ("search", "insights", "entities", "tags", "audiences", "trending", "compare", "aclose"):
        assert callable(getattr(live, name)) and callable(getattr(mock, name))
    asyncio.run(live.aclose())


# --- 7/8. status classification --------------------------------------------


@pytest.mark.parametrize("status", [401, 403])
def test_auth_failures_become_authentication_error(status: int) -> None:
    client = client_with(respond(status), settings_with())
    with pytest.raises(AuthenticationError) as excinfo:
        asyncio.run(client.insights(filter_type="urn:tag", signal_interests_entities=["a"]))
    assert excinfo.value.status == status
    assert "hackathon.api.qloo.com" in str(excinfo.value)
    assert excinfo.value.to_dict()["kind"] == "authentication"


def test_404_becomes_not_found_error_and_is_not_retried() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(404, json={"error": "not found"})

    client = client_with(handler, settings_with(max_retries=3))
    with pytest.raises(NotFoundError):
        asyncio.run(client.entities(entity_ids=["nope"]))
    assert len(calls) == 1, "a 404 is a data outcome and must never be retried"


def test_429_becomes_rate_limit_error_with_retry_after() -> None:
    client = client_with(respond(429, headers={"Retry-After": "2"}), settings_with())
    with pytest.raises(RateLimitError) as excinfo:
        asyncio.run(client.insights(filter_type="urn:tag", signal_interests_entities=["a"]))
    assert excinfo.value.retry_after_s == 2.0
    assert excinfo.value.retryable is True


def test_rate_limit_is_retried_then_succeeds() -> None:
    state = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(429, json={"error": "slow down"})
        return httpx.Response(200, json=SUCCESS_TAGS)

    client = client_with(handler, settings_with(max_retries=1))
    response = asyncio.run(
        client.insights(filter_type="urn:tag", signal_interests_entities=["a"], tool="taste_dna")
    )
    assert isinstance(response, TagAffinityResponse)
    assert state["n"] == 2
    assert client.recorder.rows[-1].attempt == 2


def test_server_error_becomes_upstream_error() -> None:
    client = client_with(respond(503), settings_with())
    with pytest.raises(UpstreamError):
        asyncio.run(client.insights(filter_type="urn:tag", signal_interests_entities=["a"]))


def test_timeout_becomes_qloo_timeout_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("simulated timeout", request=request)

    client = client_with(handler, settings_with())
    with pytest.raises(QlooTimeoutError):
        asyncio.run(client.insights(filter_type="urn:tag", signal_interests_entities=["a"]))


def test_other_4xx_is_a_classified_qloo_error() -> None:
    client = client_with(respond(400), settings_with())
    with pytest.raises(QlooError) as excinfo:
        asyncio.run(client.insights(filter_type="urn:tag", signal_interests_entities=["a"]))
    assert excinfo.value.status == 400
    assert excinfo.value.retryable is False


# --- request shape ----------------------------------------------------------


def test_request_is_get_with_header_auth_and_no_key_in_the_query() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["query"] = request.url.query.decode()
        seen["api_key_header"] = request.headers.get("X-Api-Key")
        seen["auth_header"] = request.headers.get("Authorization")
        return httpx.Response(200, json=SUCCESS_TAGS)

    client = client_with(handler, settings_with())
    asyncio.run(client.insights(filter_type="urn:tag", signal_interests_entities=["a", "b"], take=50))
    assert seen["method"] == "GET"
    assert seen["api_key_header"] == FAKE_KEY
    assert seen["auth_header"] is None, "auth must not use Bearer tokens"
    assert FAKE_KEY not in seen["query"]
    assert seen["api_key_header"] not in seen["url"]
    assert "filter.type=urn%3Atag" in seen["query"] or "filter.type=urn:tag" in seen["query"]


def test_search_sends_documented_movie_types_filter_in_outgoing_request() -> None:
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["types"] = request.url.params.get("types")
        seen["query"] = request.url.params.get("query")
        seen["take"] = request.url.params.get("take")
        return httpx.Response(200, json={"results": {"entities": []}})

    client = client_with(handler, settings_with())
    asyncio.run(
        client.search(
            query="Perfect Days",
            types=["urn:entity:movie"],
            take=5,
            tool="resolve:search",
        )
    )

    assert seen == {"types": "urn:entity:movie", "query": "Perfect Days", "take": "5"}


# --- 9. tracing -------------------------------------------------------------


def test_trace_row_is_created_for_every_call() -> None:
    client = client_with(respond(200, SUCCESS_TAGS), settings_with())
    asyncio.run(client.insights(filter_type="urn:tag", signal_interests_entities=["a"], tool="taste_dna"))
    rows = client.recorder.rows
    assert len(rows) == 1
    row = rows[0]
    assert row.tool == "taste_dna"
    assert row.endpoint == "/v2/insights"
    assert row.status == 200
    assert row.result_count == 2
    assert row.duration_ms >= 0
    assert row.source == "qloo"
    assert row.data_status == "measured"
    assert row.call_id
    assert row.started_at


def test_trace_row_is_created_for_failed_calls_too() -> None:
    client = client_with(respond(500), settings_with())
    with pytest.raises(UpstreamError):
        asyncio.run(client.insights(filter_type="urn:tag", signal_interests_entities=["a"]))
    row = client.recorder.rows[-1]
    assert row.status == 500
    assert row.error and row.error["kind"] == "upstream"


# --- 6. the API key never reaches a trace -----------------------------------


def test_api_key_never_appears_in_trace() -> None:
    client = client_with(respond(200, SUCCESS_TAGS), settings_with())
    asyncio.run(client.insights(filter_type="urn:tag", signal_interests_entities=["a"]))
    blob = client.recorder.to_json()
    assert FAKE_KEY not in blob
    client.recorder.rows[-1].assert_no_secret(FAKE_KEY)  # would raise on contamination


def test_redaction_removes_sensitive_keys_and_literal_secret_values() -> None:
    params = {"filter.type": "urn:tag", "api_key": FAKE_KEY, "note": f"key is {FAKE_KEY}"}
    redacted = redact_params(params, secret=FAKE_KEY)
    assert redacted["filter.type"] == "urn:tag"
    assert redacted["api_key"] == REDACTED
    assert FAKE_KEY not in json.dumps(redacted)
    assert REDACTED in json.dumps(redacted)


def test_redaction_handles_nested_structures() -> None:
    payload = {
        "headers": {"X-Api-Key": FAKE_KEY, "Accept": "application/json"},
        "list": [{"authorization": FAKE_KEY}],
    }
    out = redact(payload, secret=FAKE_KEY)
    blob = json.dumps(out)
    assert FAKE_KEY not in blob
    assert out["headers"]["Accept"] == "application/json"


def test_trace_recorder_can_be_shared_across_clients(no_key_settings: Settings) -> None:
    recorder = TraceRecorder(run_id="shared", secret=None)
    live = QlooClient(
        settings_with(), transport=httpx.MockTransport(respond(200, SUCCESS_TAGS)), recorder=recorder
    )
    mock = MockQlooClient(no_key_settings, recorder=recorder)
    asyncio.run(live.insights(filter_type="urn:tag", signal_interests_entities=["a"]))
    asyncio.run(mock.insights(filter_type="urn:tag", signal_interests_entities=["a"]))
    assert [r.source for r in recorder.rows] == ["qloo", "mock"]
    assert [r.seq for r in recorder.rows] == [1, 2]
    asyncio.run(live.aclose())


# --- parser dispatch --------------------------------------------------------


def test_insights_parser_dispatch_follows_filter_type() -> None:
    client = client_with(respond(200, SUCCESS_ARTISTS), settings_with())
    response = asyncio.run(client.insights(filter_type="urn:entity:artist", signal_interests_entities=["a"]))
    assert isinstance(response, EntityAffinityResponse)
    assert response.results[0].name == "Example Ambient Artist"
    assert response.results[0].popularity == 0.24
    assert response.results[0].tags and response.results[0].tags[0].tag_id.startswith("urn:tag:")


# --- strictness on the live client too --------------------------------------


def test_live_client_rejects_unsupported_kwargs() -> None:
    client = client_with(respond(200, SUCCESS_TAGS), settings_with())
    with pytest.raises(UnverifiedParameterError):
        asyncio.run(
            client.insights(filter_type="urn:tag", signal_interests_entities=["a"], made_up_parameter="x")
        )


def test_live_client_rejects_unverified_parameter_without_opt_in() -> None:
    client = client_with(respond(200, SUCCESS_TAGS), settings_with())
    with pytest.raises(UnverifiedParameterError):
        asyncio.run(
            client.insights(
                filter_type="urn:tag",
                signal_interests_entities=["a"],
                filter_parents_types=["urn:entity:movie"],
            )
        )


def test_entities_requires_an_id_argument() -> None:
    client = client_with(respond(200, SUCCESS_ARTISTS), settings_with())
    with pytest.raises(InvalidCombinationError):
        asyncio.run(client.entities())


# --- app surface ------------------------------------------------------------


def test_health_endpoint_reports_mock_mode_without_a_key() -> None:
    client = TestClient(app)
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["service"] == "adjacent-backend"
    assert isinstance(body["qloo_configured"], bool)
    # mock_mode is True only when no key is set; when a key is present, mode is "live".
    import os
    has_key = bool((os.environ.get("QLOO_API_KEY") or "").strip())
    assert body["mock_mode"] is (not has_key)
    assert body["param_registry_size"] > 30
    assert body["unverified_param_count"] >= 4
    assert body["evidence_thresholds"]["min_cohort_members"] >= 2


def test_health_endpoint_never_leaks_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QLOO_API_KEY", FAKE_KEY)
    client = TestClient(app)
    body = client.get("/health")
    assert FAKE_KEY not in body.text
    assert body.json()["qloo_configured"] is True


def test_debug_params_exposes_the_unverified_list() -> None:
    client = TestClient(app)
    body = client.get("/debug/params").json()
    names = {row["param"] for row in body["registry"]}
    assert {"filter.type", "filter.results.entities", "signal.interests.entities"} <= names
    unverified = {row["param"] for row in body["unverified"]}
    assert {"filter.parents.types", "filter.tags"} <= unverified
    assert all(row["open_question"] for row in body["unverified"])


def test_debug_mock_run_executes_end_to_end_without_a_key() -> None:
    client = TestClient(app)
    body = client.get("/debug/mock/run", params={"fixture": "portland_strong"}).json()
    assert body["data_status"] == "fixture"
    assert "SYNTHETIC FIXTURE DATA" in body["fixture_notice"]
    assert body["programme_entity_ids_supplied"] == 8
    assert body["taste_dna"]["count"] >= 6
    assert body["adjacency"]["count"] >= 3
    assert body["geography"]["cells"] >= 10
    assert body["trace"], "trace rows must be returned"
    assert body["errors"] == []
    # the strongest cohort clears evidence; nothing here is invented
    assert body["adjacency"]["evidence"]["sufficient"] is True


def test_debug_mock_run_reports_insufficiency_without_inventing() -> None:
    client = TestClient(app)
    body = client.get("/debug/mock/run", params={"fixture": "insufficient_evidence"}).json()
    assert body["adjacency"]["evidence"]["sufficient"] is False
    assert body["taste_dna"]["evidence"]["sufficient"] is False
    assert body["geography"]["evidence"]["sufficient"] is False
    assert body["geography"]["evidence"]["reason_code"] == "insufficient_heatmap_cells"
    assert body["errors"] == []


def test_unknown_fixture_returns_404() -> None:
    client = TestClient(app)
    assert client.get("/debug/mock/run", params={"fixture": "nope"}).status_code == 404


def test_param_check_endpoint_reports_validation_without_calling_qloo() -> None:
    client = TestClient(app)
    ok = client.get(
        "/debug/params/check", params={"endpoint": "/v2/insights", "filter_type": "urn:entity:movie"}
    ).json()
    assert ok["ok"] is True
    # urn:tag without a signal is an invalid combination and must be reported as such
    needs_signal = client.get(
        "/debug/params/check", params={"endpoint": "/v2/insights", "filter_type": "urn:tag"}
    ).json()
    assert needs_signal["ok"] is False
    assert needs_signal["error"]["kind"] == "invalid_combination"
    bad = client.get(
        "/debug/params/check", params={"endpoint": "/v2/insights", "filter_type": "urn:entity:audience"}
    ).json()
    assert bad["ok"] is False
    assert bad["error"]["kind"] == "deprecated_parameter"
