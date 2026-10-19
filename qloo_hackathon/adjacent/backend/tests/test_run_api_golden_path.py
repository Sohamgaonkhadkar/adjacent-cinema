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

import time

import pytest
from app.main import app
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
