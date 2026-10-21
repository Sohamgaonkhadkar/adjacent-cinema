"""Golden-path tests for the run API surface (POST /run, GET /run/{id},
GET /run/{id}/stream, POST /run/demo, GET /health).

These tests exercise the same routes the frontend calls through the Next.js
`/api` rewrite. They never require a Qloo key:

* the live path without a key must fail LOUDLY and truthfully (never fall back
  to mock content silently);
* the fixture demo path must be labelled `fixture` in every artefact;
* the submitted programme must be stored exactly as submitted.
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest
from app.agent.stop import StopDecision, StopReason
from app.api import routes
from app.api.store import RunStatus
from app.main import app
from app.qloo.errors import UpstreamError
from app.qloo.trace import TraceRecorder
from fastapi.testclient import TestClient

TERMINAL = {"completed", "failed", "insufficient"}


def _wait_for_terminal(client: TestClient, run_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        last = client.get(f"/run/{run_id}").json()
        if last.get("status") in TERMINAL:
            return last
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} never reached a terminal state; last={last}")


CUSTOM_PROGRAMME = [
    {"title": "Chungking Express", "year": 1994, "imdb_id": "tt0109424"},
    {"title": "Cleo from 5 to 7", "year": 1962},
    {"title": "Some Unreleased Local Short"},
]


class TestLiveRunWithoutKey:
    def test_post_run_without_key_fails_honestly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No key → the run fails with an explicit configuration error.

        It must NOT silently substitute fixture/mock content for a live request.
        """
        monkeypatch.delenv("QLOO_API_KEY", raising=False)
        client = TestClient(app)
        created = client.post(
            "/run",
            json={"city": "Lisbon, Portugal", "venue_name": "Cinema Ideal", "programme": CUSTOM_PROGRAMME},
        )
        assert created.status_code == 200
        run_id = created.json()["run_id"]

        final = _wait_for_terminal(client, run_id)
        assert final["status"] == "failed"
        assert "QLOO_API_KEY not configured" in (final["error"] or "")
        # No fabricated result on failure.
        assert final["result"] is None

    def test_post_run_stores_programme_exactly_as_submitted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Whatever the programmer typed is what the backend stores — verbatim."""
        monkeypatch.delenv("QLOO_API_KEY", raising=False)
        client = TestClient(app)
        created = client.post(
            "/run",
            json={"city": "Lisbon, Portugal", "venue_name": "Cinema Ideal", "programme": CUSTOM_PROGRAMME},
        ).json()
        assert created["city"] == "Lisbon, Portugal"
        assert created["venue_name"] == "Cinema Ideal"
        # The backend normalises optional fields to None but must not alter values.
        assert created["programme"] == [
            {**item, "year": item.get("year"), "imdb_id": item.get("imdb_id")}
            for item in CUSTOM_PROGRAMME
        ]

    def test_post_run_rejects_empty_programme(self) -> None:
        client = TestClient(app)
        response = client.post("/run", json={"city": "London, UK", "programme": []})
        assert response.status_code == 422

    def test_get_unknown_run_is_404(self) -> None:
        client = TestClient(app)
        assert client.get("/run/does-not-exist").status_code == 404


def _run_with_fake_live_stop(
    monkeypatch: pytest.MonkeyPatch,
    stop: StopDecision,
) -> routes.RunRecord:
    """Exercise terminal-state serialization without constructing a live Qloo client."""
    import app.agent.orchestrator as orchestrator_module
    import app.live_runner as live_runner_module
    import app.qloo.client as qloo_client_module
    import app.resolution.resolver as resolver_module

    monkeypatch.delenv("ADJACENT_PUBLIC_DEMO", raising=False)
    monkeypatch.setenv("QLOO_API_KEY", "SYNTHETIC-TEST-KEY-NOT-A-REAL-CREDENTIAL")

    class FakeClient:
        def __init__(self, settings: object) -> None:
            del settings
            self.recorder = TraceRecorder(run_id="synthetic-run")
            trace = self.recorder.record(
                tool="resolve_programme",
                endpoint="/search",
                params={"query": "Synthetic Film"},
            )
            trace.set_error(
                UpstreamError(
                    "Qloo returned an upstream error",
                    endpoint="/search",
                    status=502,
                    detail={
                        "message": "UPSTREAM-RESPONSE-CANARY",
                        "Authorization": "Bearer HEADER-CANARY",
                    },
                    call_id="synthetic-run-c001",
                )
            )
            trace.finish()

        async def aclose(self) -> None:
            return None

    class FakeResolver:
        def __init__(self, client: object, *, delay_s: float) -> None:
            del client, delay_s

    class FakePipeline:
        def __init__(self, client: object, resolver: object, programme: object) -> None:
            del client, resolver, programme

    class FakeOrchestrator:
        def __init__(self, pipeline: object) -> None:
            del pipeline

        async def run(self, state: object) -> object:
            state.programme[0].resolved_entity_id = "synthetic-verified-id"
            state.programme[0].resolved_name = "Synthetic Film"
            state.stop = stop
            return state

    monkeypatch.setattr(qloo_client_module, "QlooClient", FakeClient)
    monkeypatch.setattr(resolver_module, "EntityResolver", FakeResolver)
    monkeypatch.setattr(live_runner_module, "LivePipeline", FakePipeline)
    monkeypatch.setattr(orchestrator_module, "AgentOrchestrator", FakeOrchestrator)

    record = routes.run_store.create(
        city="Test City",
        venue_name="Test Cinema",
        programme=[{"title": "Synthetic Film", "year": 2020, "imdb_id": None}],
    )
    asyncio.run(routes._execute_run(record))
    return record


class TestFailedRunSemantics:
    def test_failure_after_partial_pipeline_state_has_no_result_or_raw_diagnostics(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Partial measured state is retained diagnostically, never returned as a result."""
        stop = StopDecision(
            reason=StopReason.ERROR,
            message="raw upstream response must not be returned",
            detail_code="qloo_error",
            stats={
                "calls_made": 1,
                "error": {
                    "error_type": "AuthenticationError",
                    "kind": "authentication",
                    "status": 401,
                    "call_id": "synthetic-run-c001",
                    "message": "UPSTREAM-RESPONSE-CANARY",
                    "detail": "HEADER-CANARY",
                },
            },
        )
        record = _run_with_fake_live_stop(monkeypatch, stop)

        assert record.status == RunStatus.FAILED
        assert record.result is None
        assert record.state_json is None  # avoid retaining raw exception details from the state
        assert record.trace and record.trace[0]["call_id"] == "synthetic-run-c001"

        client = TestClient(app)
        response = client.get(f"/run/{record.run_id}")
        trace = client.get(f"/run/{record.run_id}/trace")
        stream = client.get(f"/run/{record.run_id}/stream")
        assert response.status_code == trace.status_code == stream.status_code == 200
        body = response.json()
        assert body["status"] == "failed"
        assert body["result"] is None
        assert body["error"].startswith("Qloo rejected the request (HTTP 401)")
        trace_json = json.dumps(trace.json())
        stream_text = stream.text
        for canary in ("UPSTREAM-RESPONSE-CANARY", "HEADER-CANARY", "SYNTHETIC-TEST-KEY"):
            assert canary not in json.dumps(body)
            assert canary not in trace_json
            assert canary not in stream_text
        assert trace.json()["trace"][0]["call_id"] == "synthetic-run-c001"
        assert trace.json()["trace"][0]["error"]["status"] == 502
        assert "Qloo rejected the request" in stream_text

    def test_insufficient_remains_distinct_and_keeps_its_partial_evidence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        record = _run_with_fake_live_stop(
            monkeypatch,
            StopDecision(
                reason=StopReason.INSUFFICIENCY,
                message="Not enough verified evidence to proceed.",
                detail_code="insufficient_cohorts",
                findings=["insufficient_cohorts"],
            ),
        )

        assert record.status == RunStatus.INSUFFICIENT
        assert record.result is not None
        assert record.result["data_status"] == "measured"
        assert record.result["evidence"]["stop_reason"] == "insufficiency"

    def test_failed_response_hides_a_preexisting_partial_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ADJACENT_PUBLIC_DEMO", raising=False)
        record = routes.run_store.create(city="Test City", programme=[])
        record.status = RunStatus.FAILED
        record.result = {"data_status": "measured", "programme": {"resolved_count": 0}}

        response = TestClient(app).get(f"/run/{record.run_id}")

        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert response.json()["result"] is None


class TestFixtureDemoRun:
    def test_demo_run_completes_and_is_labelled_fixture(self) -> None:
        """The demo route must produce a complete journey, labelled fixture everywhere."""
        client = TestClient(app)
        created = client.post("/run/demo")
        assert created.status_code == 200
        run_id = created.json()["run_id"]

        final = _wait_for_terminal(client, run_id)
        assert final["status"] == "completed", final.get("error")
        result = final["result"]
        assert result is not None

        # Truthful labelling at every level
        assert result["data_status"] == "fixture"
        assert result["programme_bet"]["data_status"] == "fixture"
        assert result["test_card"]["data_status"] == "fixture"
        assert result["geography"]["data_status"] == "fixture"

        # The journey artefacts exist and are internally consistent
        programme = result["programme"]
        assert programme["total_count"] >= 3
        assert programme["resolved_count"] == programme["total_count"]
        assert any(item["title"] == "Perfect Days" for item in programme["items"])
        # Fixture identity rows are not live resolver verification evidence.
        assert all(item["resolution_evidence"] is None for item in programme["items"])

        assert result["taste_dna"]["tag_count"] > 0
        assert len(result["cohorts"]["ranked"]) >= 1
        top = result["cohorts"]["ranked"][0]
        assert top["rank"] == 1
        assert top["score"]["mean_affinity"] is not None
        assert len(top["members"]) >= 1

        bet = result["programme_bet"]
        assert bet["primary"]["cohort_name"]
        assert bet["falsification_condition"]

        card = result["test_card"]
        # The Test Card contract the frontend renders — audience_hypothesis included.
        assert card["audience_hypothesis"]
        assert card["title"]
        assert card["provenance"]["data_status"] == "fixture"

        geo = result["geography"]
        assert geo["total_cells"] > 0
        assert geo["call_id"]

        evidence = result["evidence"]
        assert evidence["stop_reason"] == "complete"
        assert evidence["qloo_calls"] > 0

    def test_demo_run_sse_stream_replays_history_and_terminates(self) -> None:
        """A late SSE subscriber still receives every event, ending in `done`."""
        client = TestClient(app)
        run_id = client.post("/run/demo").json()["run_id"]
        final = _wait_for_terminal(client, run_id)
        assert final["status"] == "completed"

        events: list[str] = []
        with client.stream("GET", f"/run/{run_id}/stream") as response:
            assert response.status_code == 200
            for line in response.iter_lines():
                if line.startswith("event:"):
                    events.append(line.split(":", 1)[1].strip())
                if events and events[-1] in ("done", "insufficiency", "error"):
                    break

        assert events[-1] == "done"
        # Replay contains the journey events, in a sensible order
        assert "trace" in events
        assert "resolution" in events
        assert "cohort" in events
        assert "bet" in events
        assert "test_card" in events

    def test_demo_run_trace_rows_have_provenance(self) -> None:
        client = TestClient(app)
        run_id = client.post("/run/demo").json()["run_id"]
        final = _wait_for_terminal(client, run_id)
        assert final["status"] == "completed"
        trace = client.get(f"/run/{run_id}/trace").json()["trace"]
        assert len(trace) > 0
        for row in trace:
            assert "call_id" in row


class TestHealth:
    def test_health_reports_mock_mode_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("QLOO_API_KEY", raising=False)
        body = TestClient(app).get("/health").json()
        assert body["status"] == "ok"
        assert body["qloo_configured"] is False
        assert body["mode"] == "mock"
