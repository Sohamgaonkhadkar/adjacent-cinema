"""Anonymous public-demo safety regressions.

These tests use only synthetic keys and fixture-backed runs. They do not call
Qloo, YouTube, or an LLM provider.
"""

from __future__ import annotations

import json
import time

import pytest
from app import public_demo
from app.agent.state import AdjacentState
from app.agent.stop import StopDecision, StopReason
from app.api import routes as run_routes
from app.api.routes import run_store
from app.api.store import RunEvent, RunStatus, RunStore
from app.main import app
from app.public_demo import PublicDemoLimiter, safe_run_error, sanitize_public_stop
from fastapi.testclient import TestClient


def _wait(client: TestClient, run_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/run/{run_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"completed", "failed", "insufficient"}:
            return body
        time.sleep(0.05)
    raise AssertionError("fixture run did not reach a terminal status")


class TestPublicDemoBoundary:
    def test_health_hides_provider_hosts_and_key_fingerprint(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        monkeypatch.setenv("ADJACENT_PUBLIC_LIVE", "1")
        monkeypatch.setenv("QLOO_API_KEY", "SYNTHETIC-KEY-CANARY")

        response = TestClient(app).get("/health")
        body = response.json()
        dumped = json.dumps(body)

        assert response.status_code == 200
        assert body["mode"] == "public_demo"
        assert body["public_demo"] is True
        assert body["live_creator_available"] is True
        assert "key_fingerprint" not in body
        assert "qloo_base_url" not in body
        assert "SYNTHETIC-KEY-CANARY" not in dumped

    def test_shared_storage_oauth_synthesis_and_debug_are_not_public(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        monkeypatch.delenv("ADJACENT_PUBLIC_LIVE", raising=False)
        monkeypatch.delenv("QLOO_API_KEY", raising=False)
        client = TestClient(app)

        assert client.get("/experiments").status_code == 403
        assert client.get("/experiments/private-id").status_code == 403
        assert client.post("/experiments", json={}).status_code == 403
        assert client.post("/experiments/private-id/observations", json={}).status_code == 403
        assert client.post("/experiments/private-id/evaluations", json={}).status_code == 403
        assert client.post(
            "/experiments/private-id/observations/from-youtube", json={}
        ).status_code == 403
        assert client.get("/youtube/videos").status_code == 403
        assert client.get("/youtube/authorize").status_code == 403
        assert client.post("/youtube/disconnect").status_code == 403
        assert client.post("/creator/synthesize", json={}).status_code == 403
        assert client.get("/debug/config").status_code == 404
        assert client.get("/debug/mock/run").status_code == 404
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404

        youtube = client.get("/youtube/status").json()
        assert youtube["connected"] is False
        assert youtube["connection"] is None
        assert youtube["configured"] is False
        assert "token" not in json.dumps(youtube).lower()

        synthesis = client.get("/creator/synthesis-status").json()
        assert synthesis["available"] is False
        assert "disabled" in synthesis["blocked_reason"].lower()

    def test_public_live_cinema_requires_explicit_opt_in_and_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        monkeypatch.delenv("ADJACENT_PUBLIC_LIVE", raising=False)
        monkeypatch.delenv("QLOO_API_KEY", raising=False)
        client = TestClient(app)
        body = {
            "city": "London",
            "venue_name": "Prince Charles Cinema",
            "programme": [{"title": "Perfect Days", "year": 2023}],
        }

        disabled = client.post("/run", json=body)
        assert disabled.status_code == 403
        assert "disabled" in disabled.json()["detail"].lower()

        monkeypatch.setenv("ADJACENT_PUBLIC_LIVE", "1")
        unconfigured = client.post("/run", json=body)
        assert unconfigured.status_code == 503
        assert "not configured" in unconfigured.json()["detail"].lower()

        # A synthetic key plus a stubbed runner proves the route is reachable
        # without making a real Qloo request during tests.
        monkeypatch.setenv("QLOO_API_KEY", "SYNTHETIC-KEY-CANARY")

        async def fake_execute_run(record) -> None:
            record.status = RunStatus.FAILED
            record.error = "synthetic test failure"
            record.stop_message = record.error

        monkeypatch.setattr(run_routes, "_execute_run", fake_execute_run)
        started = client.post("/run", json=body)
        assert started.status_code == 200
        final = _wait(client, started.json()["run_id"])
        assert final["status"] == "failed"
        assert final["error"] == "synthetic test failure"

    def test_public_live_creator_requires_explicit_opt_in_and_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        monkeypatch.delenv("ADJACENT_PUBLIC_LIVE", raising=False)
        monkeypatch.delenv("QLOO_API_KEY", raising=False)
        client = TestClient(app)
        body = {"title": "Neon Harbour", "themes": ["night workers"]}

        disabled = client.post("/creator/run", json=body)
        assert disabled.status_code == 403
        assert "disabled" in disabled.json()["detail"].lower()

        monkeypatch.setenv("ADJACENT_PUBLIC_LIVE", "1")
        unconfigured = client.post("/creator/run", json=body)
        assert unconfigured.status_code == 503
        assert "not configured" in unconfigured.json()["detail"].lower()

    def test_public_live_creator_inputs_are_bounded(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        monkeypatch.setenv("ADJACENT_PUBLIC_LIVE", "1")
        monkeypatch.setenv("QLOO_API_KEY", "SYNTHETIC-KEY-CANARY")
        client = TestClient(app)

        too_long = client.post(
            "/creator/run",
            json={"title": "x" * 161, "themes": ["night workers"]},
        )
        too_many_themes = client.post(
            "/creator/run",
            json={"title": "Bounded", "themes": [f"theme-{i}" for i in range(6)]},
        )
        too_many_references = client.post(
            "/creator/run",
            json={
                "title": "Bounded",
                "references": [{"title": f"Film {i}", "year": 2000} for i in range(6)],
            },
        )
        too_large = client.post(
            "/creator/run",
            content=b"x" * 16_385,
            headers={"content-type": "application/json"},
        )

        assert too_long.status_code == 422
        assert too_many_themes.status_code == 422
        assert too_many_references.status_code == 422
        assert too_large.status_code == 413

    def test_malformed_creator_json_returns_validation_error_without_running(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        monkeypatch.setenv("ADJACENT_PUBLIC_LIVE", "1")
        monkeypatch.setenv("QLOO_API_KEY", "SYNTHETIC-KEY-CANARY")

        response = TestClient(app).post(
            "/creator/run",
            content=b"{",
            headers={"content-type": "application/json"},
        )

        assert response.status_code == 422
        assert "QLOO_API_KEY" not in response.text

    def test_public_fixture_run_is_available_and_remains_labelled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        monkeypatch.delenv("ADJACENT_PUBLIC_LIVE", raising=False)
        monkeypatch.delenv("QLOO_API_KEY", raising=False)
        client = TestClient(app)

        created = client.post("/creator/run/demo")
        assert created.status_code == 200
        final = _wait(client, created.json()["run_id"])
        assert final["status"] == "completed"
        assert final["result"]["mode"] == "creator"
        assert final["result"]["data_status"] == "fixture"
        assert final["result"]["test_card"]["data_status"] == "fixture"

    def test_fixture_body_limit_applies_before_run_creation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        client = TestClient(app)
        response = client.post("/run/demo", content=b"x" * 1025)
        assert response.status_code == 413

    def test_public_demo_does_not_expose_cors_wildcard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        response = TestClient(app).get(
            "/health", headers={"Origin": "https://untrusted.example"}
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") != "*"

    def test_exact_origin_preflight_reaches_cors_middleware(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        response = TestClient(app).options(
            "/creator/run",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    def test_public_failure_messages_redact_exception_details(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        failure = "UPSTREAM-DETAIL-CANARY"

        message = safe_run_error(RuntimeError(failure))

        assert message == "The analysis could not complete in this public demo. Please try again."
        assert failure not in message

    def test_public_run_responses_trace_and_sse_hide_error_details(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        private_detail = "PRIVATE-TRACE-DETAIL-CANARY"
        synthetic_key = "SYNTHETIC-KEY-CANARY"
        state = AdjacentState()
        state.stop = StopDecision(
            reason=StopReason.ERROR,
            message=private_detail,
            detail_code="RuntimeError",
            stats={"calls_made": 3, "error": {"message": private_detail}},
        )
        sanitize_public_stop(state)
        assert state.stop is not None
        assert state.stop.message.startswith("The analysis could not complete")
        assert state.stop.detail_code == "provider_failure"
        assert state.stop.stats == {"calls_made": 3}

        record = run_store.create(city="", programme=[])
        record.status = RunStatus.FAILED
        record.stop_reason = "error"
        record.stop_message = private_detail
        record.error = f"{private_detail} {synthetic_key}"
        record.result = {
            "evidence": {"stop_reason": "error", "stop_message": private_detail}
        }
        record.trace = [{
            "call_id": "run-c001",
            "error": {
                "error_type": "RuntimeError",
                "kind": "upstream",
                "message": private_detail,
                "detail": synthetic_key,
                "status": 502,
            },
        }]
        record.emit(RunEvent("error", {
            "stop_reason": "error",
            "stop_message": private_detail,
            "message": f"{private_detail} {synthetic_key}",
        }))
        client = TestClient(app)

        response = client.get(f"/run/{record.run_id}")
        trace = client.get(f"/run/{record.run_id}/trace")
        stream = client.get(f"/run/{record.run_id}/stream")

        assert response.status_code == trace.status_code == stream.status_code == 200
        response_text = json.dumps(response.json())
        trace_text = json.dumps(trace.json())
        for canary in (private_detail, synthetic_key):
            assert canary not in response_text
            assert canary not in trace_text
            assert canary not in stream.text
        assert response.json()["stop_message"].startswith("The analysis could not complete")
        assert trace.json()["trace"][0]["error"]["message"].startswith(
            "The upstream provider call could not be completed"
        )
        assert "The analysis could not complete" in stream.text


class TestPublicDemoLimiter:
    def test_public_fixture_run_endpoint_uses_its_own_process_local_quota(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        monkeypatch.delenv("ADJACENT_PUBLIC_LIVE", raising=False)
        monkeypatch.delenv("QLOO_API_KEY", raising=False)
        limiter = PublicDemoLimiter(
            client_limit=1,
            global_limit=1,
            max_active=4,
            window_seconds=60,
        )
        monkeypatch.setattr(public_demo, "_PUBLIC_FIXTURE_LIMITER", limiter)
        client = TestClient(app)

        first = client.post("/creator/run/demo")
        assert first.status_code == 200
        _wait(client, first.json()["run_id"])
        second = client.post("/creator/run/demo")

        assert second.status_code == 429
        assert second.headers["retry-after"] == "60"

    def test_public_http_requests_have_a_separate_rate_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        limiter = PublicDemoLimiter(
            client_limit=1,
            global_limit=2,
            max_active=1,
            window_seconds=60,
        )
        monkeypatch.setattr(public_demo, "_PUBLIC_REQUEST_LIMITER", limiter)
        client = TestClient(app)

        first = client.get("/health")
        second = client.get("/health")

        assert first.status_code == 200
        assert second.status_code == 429
        assert second.headers["retry-after"] == "60"

    def test_public_reads_expire_completed_run_records(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        expired = run_store.create(city="", programme=[])
        expired.status = RunStatus.COMPLETED
        expired.created_at = time.time() - 6 * 60 * 60 - 1

        response = TestClient(app).get(f"/run/{expired.run_id}")

        assert response.status_code == 404
        assert run_store.get(expired.run_id) is None

    def test_cache_reserves_a_slot_before_each_new_public_run(self) -> None:
        store = RunStore()
        for _ in range(100):
            completed = store.create(city="", programme=[])
            completed.status = RunStatus.COMPLETED

        store.prune_completed(max_records=99, max_age_s=6 * 60 * 60)
        store.create(city="", programme=[])

        assert len(store.list_runs()) == 100

    def test_volatile_run_cache_prunes_expired_records_but_keeps_active_runs(self) -> None:
        store = RunStore()
        expired = store.create(city="", programme=[])
        expired.created_at = time.time() - 60
        expired.status = RunStatus.COMPLETED
        active = store.create(city="", programme=[])
        active.status = RunStatus.RUNNING

        removed = store.prune_completed(max_records=1, max_age_s=10)

        assert removed == 1
        assert store.get(expired.run_id) is None
        assert store.get(active.run_id) is not None

    def test_client_global_and_concurrency_limits_are_enforced(self) -> None:
        now = [100.0]
        limiter = PublicDemoLimiter(
            client_limit=1,
            global_limit=2,
            max_active=1,
            window_seconds=10,
            clock=lambda: now[0],
        )

        first, _ = limiter.acquire("client-a")
        assert first is not None
        busy, retry_after = limiter.acquire("client-b")
        assert busy is None
        assert retry_after > 0  # in-flight cap
        first.release()

        rate_limited, retry_after = limiter.acquire("client-a")
        assert rate_limited is None
        assert retry_after == 10

        second, _ = limiter.acquire("client-b")
        assert second is not None
        second.release()
        global_limited, retry_after = limiter.acquire("client-c")
        assert global_limited is None
        assert retry_after == 10

        now[0] = 111.0
        after_window, _ = limiter.acquire("client-a")
        assert after_window is not None
        after_window.release()

    def test_release_is_idempotent(self) -> None:
        limiter = PublicDemoLimiter(
            client_limit=2, global_limit=2, max_active=1, window_seconds=10
        )
        permit, _ = limiter.acquire("client")
        assert permit is not None
        permit.release()
        permit.release()
        next_permit, _ = limiter.acquire("client")
        assert next_permit is not None
        next_permit.release()
