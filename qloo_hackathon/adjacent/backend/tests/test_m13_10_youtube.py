"""M13.10 YouTube integration regressions (deterministic, offline).

All external YouTube/Google interactions are mocked (httpx.MockTransport or
the labelled MockYouTubeProvider). Nothing here demonstrates live API
acceptance — it demonstrates the integration BOUNDARY: OAuth state/CSRF,
honest disconnected states, typed failure propagation, provenance capture,
zero-vs-missing semantics, idempotency, policy deletion, and the guarantee
that tokens never surface in responses.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from app.api import creator_routes, youtube_routes
from app.domain.youtube_auth import TokenStore, YouTubeSettings
from app.domain.youtube_provider import (
    EMPTY_REPORT_NOTE,
    QuotaExceeded,
    TokenInvalid,
    YouTubeProvider,
)
from app.main import app
from fastapi.testclient import TestClient

MOCK_TOKEN = "TEST-ACCESS-TOKEN-CANARY"  # synthetic canary, not credential-shaped
MOCK_REFRESH = "TEST-REFRESH-TOKEN-CANARY"  # synthetic canary, not credential-shaped


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    creator_routes.reset_repo_for_tests(tmp_path / "experiments.db")
    youtube_routes.reset_youtube_for_tests(tmp_path / "youtube_auth.db")
    monkeypatch.delenv("ADJACENT_YT_MOCK", raising=False)
    monkeypatch.delenv("YOUTUBE_CLIENT_ID", raising=False)
    monkeypatch.delenv("YOUTUBE_CLIENT_SECRET", raising=False)
    yield TestClient(app)
    creator_routes.reset_repo_for_tests(None)
    youtube_routes.reset_youtube_for_tests(None)


def _make_experiment(client: TestClient) -> str:
    response = client.post("/experiments", json={
        "request_id": "req-yt-000001",
        "film_title": "Neon Harbour",
        "hypothesis": "Artist-world audience is reachable with artist framing.",
        "success_criteria": "Responses reference the framing; reach beats baseline.",
        "observation_window": "Two weeks after release.",
        "data_status": "fixture",
        "source_run_id": "run-yt-0001",
    })
    assert response.status_code == 201
    return response.json()["experiment"]["experiment_id"]


def _connect_mock(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the real authorize→callback path in the labelled mock mode."""
    monkeypatch.setenv("ADJACENT_YT_MOCK", "1")
    first = client.get("/youtube/authorize", follow_redirects=False)
    assert first.status_code == 302
    callback_url = first.headers["location"]
    assert callback_url.startswith("/youtube/callback?")
    second = client.get(callback_url, follow_redirects=False)
    assert second.status_code == 302
    assert second.headers["location"] == "/creator?yt=connected"


# ---------------------------------------------------------------------------
# Status + configuration honesty
# ---------------------------------------------------------------------------


class TestStatus:
    def test_not_configured_is_honest(self, client: TestClient) -> None:
        body = client.get("/youtube/status").json()
        assert body["mode"] == "not_configured"
        assert body["configured"] is False
        assert body["connected"] is False
        assert body["connection"] is None
        assert body["single_connection_posture"] is True
        assert "youtube.readonly" in body["requested_scopes"][0]
        assert "yt-analytics.readonly" in body["requested_scopes"][1]

    def test_authorize_without_credentials_503(self, client: TestClient) -> None:
        response = client.get("/youtube/authorize")
        assert response.status_code == 503
        assert "YOUTUBE_CLIENT_ID" in response.json()["detail"]


class TestOAuthFlow:
    def test_callback_rejects_unknown_state(self, client: TestClient) -> None:
        response = client.get("/youtube/callback?code=abc&state=forged-state")
        assert response.status_code == 400
        assert "CSRF" in response.json()["detail"]

    def test_callback_state_single_use(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setenv("ADJACENT_YT_MOCK", "1")
        location = client.get("/youtube/authorize", follow_redirects=False).headers["location"]
        assert client.get(location, follow_redirects=False).status_code == 302
        replay = client.get(location, follow_redirects=False)  # same state again
        assert replay.status_code == 400

    def test_state_survives_restart_and_expires(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        from datetime import timedelta

        store = youtube_routes.get_store()
        state = store.create_state(ttl=timedelta(minutes=10))
        # "restart": reopen the store against the same file
        store.close()
        reopened = TokenStore(tmp_path / "youtube_auth.db")
        assert reopened.validate_and_consume_state(state) is True
        assert reopened.validate_and_consume_state(state) is False  # consumed
        expired = reopened.create_state(ttl=timedelta(seconds=-1))
        assert reopened.validate_and_consume_state(expired) is False
        reopened.close()
        youtube_routes.reset_youtube_for_tests(tmp_path / "youtube_auth.db")

    def test_denied_consent_redirects_honestly(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setenv("ADJACENT_YT_MOCK", "1")
        location = client.get("/youtube/authorize", follow_redirects=False).headers["location"]
        state = location.split("state=")[1]
        denied = client.get(
            f"/youtube/callback?error=access_denied&state={state}",
            follow_redirects=False,
        )
        assert denied.status_code == 302
        assert denied.headers["location"].startswith("/creator?yt=denied")
        assert client.get("/youtube/status").json()["connected"] is False

    def test_mock_connect_sets_connection_metadata_only(
        self, client: TestClient, monkeypatch
    ) -> None:
        _connect_mock(client, monkeypatch)
        status = client.get("/youtube/status").json()
        assert status["mode"] == "mock"
        assert status["mock_data"] is True
        assert status["connected"] is True
        assert status["connection"]["channel_title"] == "Mock Channel (demo data)"
        # Tokens must NOT appear anywhere in the response.
        dumped = json.dumps(status)
        assert "mock-access-token" not in dumped
        assert "mock-refresh-token" not in dumped


# ---------------------------------------------------------------------------
# Live provider unit behaviour (httpx.MockTransport — no network)
# ---------------------------------------------------------------------------


def _provider(handler) -> YouTubeProvider:
    return YouTubeProvider(transport=httpx.MockTransport(handler))


class TestLiveProvider:
    def test_metrics_success_mapping(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert "channel%3D%3DMINE" in str(request.url) or "channel==MINE" in str(request.url)
            return httpx.Response(200, json={
                "columnHeaders": [
                    {"name": "video"}, {"name": "views"},
                    {"name": "estimatedMinutesWatched"}, {"name": "averageViewDuration"},
                ],
                "rows": [["vid123", "42", "100.5", "143.57"]],
            })

        result = asyncio.run(_provider(handler).query_video_metrics(
            MOCK_TOKEN, "vid123", "2026-09-01", "2026-09-14"
        ))
        assert result["metrics"] == {
            "views": 42,
            "estimated_minutes_watched": 100.5,
            "average_view_duration_seconds": 143.57,
        }
        assert result["row_count"] == 1

    def test_observed_zero_vs_empty_report(self) -> None:
        def zero_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "columnHeaders": [
                    {"name": "video"}, {"name": "views"},
                    {"name": "estimatedMinutesWatched"}, {"name": "averageViewDuration"},
                ],
                "rows": [["vid", "0", "0", "0"]],
            })

        zero = asyncio.run(_provider(zero_handler).query_video_metrics(
            MOCK_TOKEN, "vid", "2026-09-01", "2026-09-14"
        ))
        assert zero["metrics"]["views"] == 0  # zero is DATA
        assert zero["row_count"] == 1

        def empty_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"columnHeaders": [], "rows": []})

        empty = asyncio.run(_provider(empty_handler).query_video_metrics(
            MOCK_TOKEN, "vid", "2026-09-01", "2026-09-14"
        ))
        assert empty["metrics"] == {}  # missing is NOT zero
        assert EMPTY_REPORT_NOTE in empty["limitations"][0]

    def test_partial_report_flags_absent_metrics(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "columnHeaders": [{"name": "video"}, {"name": "views"}],
                "rows": [["vid", "7"]],
            })

        result = asyncio.run(_provider(handler).query_video_metrics(
            MOCK_TOKEN, "vid", "2026-09-01", "2026-09-14"
        ))
        assert result["metrics"] == {"views": 7}
        assert "NOT zeros" in result["limitations"][0]

    def test_quota_and_auth_errors_are_typed(self) -> None:
        def quota(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={
                "error": {"errors": [{"reason": "quotaExceeded"}]}
            })

        with pytest.raises(QuotaExceeded):
            asyncio.run(_provider(quota).query_video_metrics(
                MOCK_TOKEN, "vid", "2026-09-01", "2026-09-14"
            ))

        def denied(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={"error": {"errors": [{"reason": "forbidden"}]}})

        with pytest.raises(TokenInvalid):
            asyncio.run(_provider(denied).query_video_metrics(
                MOCK_TOKEN, "vid", "2026-09-01", "2026-09-14"
            ))

    def test_refresh_invalid_grant_raises_token_invalid(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": "invalid_grant"})

        settings = YouTubeSettings(client_id="id", client_secret="secret")
        with pytest.raises(TokenInvalid):
            asyncio.run(_provider(handler).refresh_access_token(settings, MOCK_REFRESH))

    def test_revoke_token_best_effort(self) -> None:
        def ok(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={})

        assert asyncio.run(_provider(ok).revoke_token(MOCK_REFRESH)) is True

        def boom(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no egress")

        assert asyncio.run(_provider(boom).revoke_token(MOCK_REFRESH)) is False


# ---------------------------------------------------------------------------
# Routes: connection required, data retrieval, observation bridge
# ---------------------------------------------------------------------------


class TestDataRoutes:
    def test_videos_without_connection_409(self, client: TestClient) -> None:
        assert client.get("/youtube/videos").status_code == 409

    def test_from_youtube_without_connection_409(self, client: TestClient) -> None:
        eid = _make_experiment(client)
        response = client.post(f"/experiments/{eid}/observations/from-youtube", json={
            "request_id": "obs-yt-00001",
            "video_id": "vid", "start_date": "2026-09-01", "end_date": "2026-09-14",
        })
        assert response.status_code == 409
        assert client.get(f"/experiments/{eid}").json()["observations"] == []

    def test_mock_flow_records_provenanced_observation(
        self, client: TestClient, monkeypatch
    ) -> None:
        eid = _make_experiment(client)
        _connect_mock(client, monkeypatch)

        videos = client.get("/youtube/videos").json()
        assert videos["data_status"] == "mock"
        vid = videos["videos"][0]["video_id"]

        preview = client.get(
            f"/youtube/metrics?video_id={vid}&start_date=2026-09-01&end_date=2026-09-14"
        ).json()
        assert preview["data_status"] == "mock"
        assert preview["metrics"]["views"] == 128

        response = client.post(f"/experiments/{eid}/observations/from-youtube", json={
            "request_id": "obs-yt-00002",
            "video_id": vid,
            "start_date": "2026-09-01",
            "end_date": "2026-09-14",
            "interpretation": "Framing seemed to land with the artist community.",
        })
        assert response.status_code == 200
        observation = response.json()["observation"]
        assert observation["measurement_status"] == "OBSERVED"
        assert observation["metrics"]["views"] == 128
        assert observation["source"] == "mock_youtube_analytics"
        evidence = json.loads(observation["evidence_ref"])
        assert evidence["provider"] == "mock_youtube_analytics"
        assert evidence["data_status"] == "mock"
        assert evidence["video_id"] == vid
        assert evidence["period"] == {"start_date": "2026-09-01", "end_date": "2026-09-14"}
        assert evidence["retrieved_at"]
        # Subjective interpretation stays a separate field from measurements.
        assert observation["interpretation"].startswith("Framing seemed")

        # Idempotent retry
        again = client.post(f"/experiments/{eid}/observations/from-youtube", json={
            "request_id": "obs-yt-00002",
            "video_id": vid, "start_date": "2026-09-01", "end_date": "2026-09-14",
        })
        assert again.json()["duplicate"] is True
        assert len(client.get(f"/experiments/{eid}").json()["observations"]) == 1

    def test_empty_report_becomes_partial_not_zero(
        self, client: TestClient, monkeypatch
    ) -> None:
        from app.domain.youtube_provider import MockYouTubeProvider

        eid = _make_experiment(client)
        monkeypatch.setenv("ADJACENT_YT_MOCK", "1")
        youtube_routes.reset_youtube_for_tests(
            Path(youtube_routes.get_store().db_path),
            provider=MockYouTubeProvider(scenario="empty_report"),
        )
        response = client.post(f"/experiments/{eid}/observations/from-youtube", json={
            "request_id": "obs-yt-00003",
            "video_id": "mockVideoId001",
            "start_date": "2026-09-01", "end_date": "2026-09-14",
        })
        observation = response.json()["observation"]
        assert observation["measurement_status"] == "PARTIAL"
        assert observation["metrics"] == {}
        assert "NOT recorded as a zero" in observation["limitations"]

    def test_quota_failure_creates_no_observation(
        self, client: TestClient, monkeypatch
    ) -> None:
        from app.domain.youtube_provider import MockYouTubeProvider

        eid = _make_experiment(client)
        monkeypatch.setenv("ADJACENT_YT_MOCK", "1")
        youtube_routes.reset_youtube_for_tests(
            Path(youtube_routes.get_store().db_path),
            provider=MockYouTubeProvider(scenario="quota"),
        )
        response = client.post(f"/experiments/{eid}/observations/from-youtube", json={
            "request_id": "obs-yt-00004",
            "video_id": "mockVideoId001",
            "start_date": "2026-09-01", "end_date": "2026-09-14",
        })
        assert response.status_code == 429
        assert client.get(f"/experiments/{eid}").json()["observations"] == []

    def test_unknown_video_404(self, client: TestClient, monkeypatch) -> None:
        eid = _make_experiment(client)
        _connect_mock(client, monkeypatch)
        response = client.post(f"/experiments/{eid}/observations/from-youtube", json={
            "request_id": "obs-yt-00005",
            "video_id": "notARealVideo",
            "start_date": "2026-09-01", "end_date": "2026-09-14",
        })
        assert response.status_code == 404

    def test_period_validation(self, client: TestClient, monkeypatch) -> None:
        eid = _make_experiment(client)
        _connect_mock(client, monkeypatch)
        future = client.post(f"/experiments/{eid}/observations/from-youtube", json={
            "request_id": "obs-yt-00006",
            "video_id": "mockVideoId001",
            "start_date": "2026-09-01", "end_date": "2099-01-01",
        })
        assert future.status_code == 422
        inverted = client.post(f"/experiments/{eid}/observations/from-youtube", json={
            "request_id": "obs-yt-00007",
            "video_id": "mockVideoId001",
            "start_date": "2026-09-14", "end_date": "2026-09-01",
        })
        assert inverted.status_code == 422

    def test_unknown_experiment_404(self, client: TestClient, monkeypatch) -> None:
        _connect_mock(client, monkeypatch)
        response = client.post("/experiments/nope/observations/from-youtube", json={
            "request_id": "obs-yt-00008",
            "video_id": "mockVideoId001",
            "start_date": "2026-09-01", "end_date": "2026-09-14",
        })
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Disconnect + policy deletion
# ---------------------------------------------------------------------------


class TestDisconnect:
    def test_disconnect_deletes_credentials_and_youtube_data(
        self, client: TestClient, monkeypatch
    ) -> None:
        eid = _make_experiment(client)
        _connect_mock(client, monkeypatch)
        client.post(f"/experiments/{eid}/observations/from-youtube", json={
            "request_id": "obs-yt-00009",
            "video_id": "mockVideoId001",
            "start_date": "2026-09-01", "end_date": "2026-09-14",
        })
        # a manual observation that must survive the deletion
        client.post(f"/experiments/{eid}/observations", json={
            "request_id": "obs-manual-01", "kind": "FEEDBACK",
            "measurement_status": "OBSERVED",
            "interpretation": "A friend said the framing resonated.",
        })

        result = client.post("/youtube/disconnect").json()
        assert result["credentials_deleted"] is True
        assert result["youtube_observations_deleted"] == 1
        assert result["experiments_tombstoned"] == 1
        assert client.get("/youtube/status").json()["connected"] is False

        observations = client.get(f"/experiments/{eid}").json()["observations"]
        sources = [o["source"] for o in observations]
        assert "mock_youtube_analytics" not in sources  # deleted
        assert "policy_deletion" in sources  # tombstone
        assert any(o["kind"] == "FEEDBACK" for o in observations)  # manual kept
        tombstones = [o for o in observations if o["kind"] == "NOTE"]
        assert tombstones
        # Inspect data-bearing fields, not random IDs/timestamps whose digits can
        # coincidentally contain "128". The deleted value and video ID must not
        # survive in the tombstone's content.
        for note in tombstones:
            safe_content = {
                key: note.get(key)
                for key in (
                    "kind", "measurement_status", "metrics", "interpretation",
                    "source", "evidence_ref", "limitations",
                )
            }
            assert "128" not in json.dumps(safe_content)
            assert "mockVideoId001" not in json.dumps(safe_content)
            assert safe_content["metrics"] in (None, {})


# ---------------------------------------------------------------------------
# Token-leakage guard across the whole surface
# ---------------------------------------------------------------------------


class TestTokenLeakage:
    def test_no_tokens_in_any_response(self, client: TestClient, monkeypatch) -> None:
        secrets_seen = []
        _connect_mock(client, monkeypatch)
        eid = _make_experiment(client)
        responses = [
            client.get("/youtube/status").text,
            client.get("/youtube/videos").text,
            client.get(
                "/youtube/metrics?video_id=mockVideoId001"
                "&start_date=2026-09-01&end_date=2026-09-14"
            ).text,
            client.post(f"/experiments/{eid}/observations/from-youtube", json={
                "request_id": "obs-yt-00010",
                "video_id": "mockVideoId001",
                "start_date": "2026-09-01", "end_date": "2026-09-14",
            }).text,
            client.get(f"/experiments/{eid}").text,
            client.post("/youtube/disconnect").text,
        ]
        for body in responses:
            for needle in ("mock-access-token", "mock-refresh-token"):
                if needle in body:
                    secrets_seen.append(needle)
        assert secrets_seen == []


# ---------------------------------------------------------------------------
# Live-mode honest failure (no network in sandbox → deterministic error path)
# ---------------------------------------------------------------------------


class TestLiveModeHonesty:
    def test_live_callback_network_failure_redirects_with_reason(
        self, client: TestClient, monkeypatch
    ) -> None:
        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test-client-secret")
        status = client.get("/youtube/status").json()
        assert status["mode"] == "live"
        assert status["configured"] is True

        location = client.get("/youtube/authorize", follow_redirects=False).headers["location"]
        assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
        assert "prompt=consent" in location
        assert "access_type=offline" in location
        assert "yt-analytics.readonly" in location
        assert "youtube.readonly" in location
        # no write/monetary scopes requested
        assert "youtube.force-ssl" not in location
        assert "monetary" not in location

        # Replay the callback with a state we issued by extracting it.
        state = location.split("state=")[1]
        result = client.get(
            f"/youtube/callback?code=fake-code&state={state}",
            follow_redirects=False,
        )
        # Sandbox has no egress to Google: exchange fails → honest error redirect,
        # never a mock substitution, never a stored connection.
        assert result.status_code == 302
        assert "yt=error" in result.headers["location"]
        assert client.get("/youtube/status").json()["connected"] is False
