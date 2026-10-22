"""M13.9 Creator Mode regressions.

Covers the creator analysis journey on the fixture-labelled demo path and the
honest-failure behaviour of the live path — mirroring the cinema golden-path
contract: no silent fixture substitution, truthful data_status, preserved
inputs, 422 on empty seeds, 404 on unknown runs.
"""

from __future__ import annotations

import logging
import time
from types import SimpleNamespace

import pytest
from app.api import creator_routes
from app.api.routes import RunStatus, run_store
from app.main import app
from fastapi.testclient import TestClient

TERMINAL = {"completed", "failed", "insufficient"}


def _wait(client: TestClient, run_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        last = client.get(f"/run/{run_id}").json()
        if last.get("status") in TERMINAL:
            return last
        time.sleep(0.05)
    raise AssertionError(f"creator run never terminal; last={last}")


class TestCreatorFixtureDemo:
    def test_demo_completes_with_fixture_labels_and_creator_artefacts(self) -> None:
        client = TestClient(app)
        created = client.post("/creator/run/demo")
        assert created.status_code == 200
        final = _wait(client, created.json()["run_id"])

        assert final["status"] == "completed"
        result = final["result"]
        assert result["mode"] == "creator"
        assert result["film"]["title"]  # demo film context present
        assert result["data_status"] == "fixture"

        bet = result["programme_bet"]
        card = result["test_card"]
        assert bet["data_status"] == "fixture"
        assert card["data_status"] == "fixture"

        # Decision chain: bet ← ranked cohort ← card (same invariants as cinema)
        assert bet["primary"]["cohort_id"] == result["cohorts"]["ranked"][0]["cohort_id"]
        assert card["provenance"]["primary_cohort_id"] == bet["primary"]["cohort_id"]

        # Actionability contract
        assert card["success_criteria"]
        assert card["observation_window"]
        assert "predicts no view counts" in card["success_criteria"]

        # Exclusions surfaced (annotations, never deletions)
        for cohort in result["cohorts"]["ranked"]:
            assert "qualifying_count" in cohort
            assert isinstance(cohort["excluded_members"], list)

    def test_demo_sse_streams_creator_events(self) -> None:
        client = TestClient(app)
        run_id = client.post("/creator/run/demo").json()["run_id"]
        _wait(client, run_id)
        with client.stream("GET", f"/run/{run_id}/stream") as response:
            body = "".join(chunk for chunk in response.iter_text())
        for expected in ("event: resolution", "event: bet", "event: test_card", "event: done"):
            assert expected in body


class TestCreatorExperimentJourney:
    def test_fixture_evidence_to_planned_experiment_observation_and_evaluation(
        self, tmp_path
    ) -> None:
        """Exercise the real Creator response without inventing an outcome."""
        creator_routes.reset_repo_for_tests(tmp_path / "creator-journey.db")
        try:
            client = TestClient(app)
            created = client.post("/creator/run/demo")
            assert created.status_code == 200
            run_id = created.json()["run_id"]
            final = _wait(client, run_id)
            assert final["status"] == "completed"

            result = final["result"]
            card = result["test_card"]
            assert result["data_status"] == "fixture"
            assert card["data_status"] == "fixture"
            assert card["audience_hypothesis"]

            saved = client.post("/experiments", json={
                "request_id": f"journey-save-{run_id}",
                "film_title": result["film"]["title"],
                "hypothesis": card["audience_hypothesis"],
                "success_criteria": card["success_criteria"],
                "observation_window": card["observation_window"],
                "action_plan": card["programming_direction"],
                "data_status": card["data_status"],
                "source_run_id": run_id,
                "source_bet": result["programme_bet"],
                "provenance": card["provenance"],
                "film_context": result["film"],
            })
            assert saved.status_code == 201
            experiment = saved.json()["experiment"]
            assert experiment["status"] == "PLANNED"
            assert experiment["source_run_id"] == run_id
            assert experiment["data_status"] == "fixture"

            observed = client.post(
                f"/experiments/{experiment['experiment_id']}/observations",
                json={
                    "request_id": f"journey-observation-{run_id}",
                    "kind": "NOTE",
                    "measurement_status": "UNAVAILABLE",
                    "limitations": (
                        "Workflow verification only; no external creator outcome was collected."
                    ),
                },
            )
            assert observed.status_code == 201
            observation = observed.json()["observation"]
            assert observation["measurement_status"] == "UNAVAILABLE"
            assert observation["metrics"] == {}

            evaluated = client.post(
                f"/experiments/{experiment['experiment_id']}/evaluations",
                json={
                    "request_id": f"journey-evaluation-{run_id}",
                    "outcome": "INCONCLUSIVE",
                    "rationale": (
                        "The fixture demonstrates the workflow; no external outcome was measured."
                    ),
                    "unknowns": "Actual creator/audience response remains unknown.",
                },
            )
            assert evaluated.status_code == 201
            detail = client.get(f"/experiments/{experiment['experiment_id']}").json()
            assert len(detail["observations"]) == 1
            assert len(detail["evaluations"]) == 1
            assert detail["evaluations"][0]["outcome"] == "INCONCLUSIVE"
        finally:
            creator_routes.reset_repo_for_tests(None)


class TestCreatorLiveRunHonesty:
    def test_live_run_without_key_fails_honestly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("QLOO_API_KEY", raising=False)
        client = TestClient(app)
        created = client.post("/creator/run", json={
            "title": "Neon Harbour",
            "themes": ["isolation", "night workers"],
            "references": [{"title": "Chungking Express", "year": 1994}],
        })
        assert created.status_code == 200
        final = _wait(client, created.json()["run_id"])
        assert final["status"] == "failed"
        assert "QLOO_API_KEY not configured" in (final["error"] or "")
        assert final["result"] is None  # never a fabricated payload

    def test_empty_seeds_rejected_422(self) -> None:
        client = TestClient(app)
        response = client.post("/creator/run", json={"title": "Untitled"})
        assert response.status_code == 422
        assert "reference work or theme" in str(response.json())

    def test_title_required(self) -> None:
        client = TestClient(app)
        response = client.post("/creator/run", json={"themes": ["isolation"]})
        assert response.status_code == 422

    def test_unknown_run_404(self) -> None:
        client = TestClient(app)
        assert client.get("/run/does-not-exist").status_code == 404

    def test_creator_postprocessing_failure_retains_sanitized_trace_and_stack_frames(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A top-level TypeError must not erase the API trace or leak its text."""
        monkeypatch.delenv("ADJACENT_PUBLIC_DEMO", raising=False)
        caplog.set_level(logging.ERROR, logger=creator_routes.__name__)
        record = run_store.create(city="Portland, Oregon", programme=[])
        record.result = {"data_status": "measured", "partial": "must be suppressed"}
        record.state_json = '{"partial": true}'
        state = SimpleNamespace(
            phase=SimpleNamespace(value="DECIDE"),
            trace_rows=[{
                "call_id": "synthetic-c001",
                "tool": "rank_cohorts",
                "endpoint": "/v2/insights",
                "error": {
                    "error_type": "TypeError",
                    "message": "SENSITIVE-CANARY",
                    "detail": {"response": "SENSITIVE-CANARY"},
                },
            }],
        )
        try:
            raise TypeError("SENSITIVE-CANARY")
        except TypeError as exc:
            creator_routes._record_creator_failure(record, state, exc)

        assert record.status.value == "failed"
        assert record.stop_reason == "error"
        assert record.result is None
        assert record.state_json is None
        assert record.current_phase == "DECIDE"
        assert record.trace[0]["call_id"] == "synthetic-c001"
        assert record.trace[0]["error"]["error_type"] == "TypeError"
        assert "SENSITIVE-CANARY" not in str(record.trace)
        assert "SENSITIVE-CANARY" not in caplog.text
        assert "TypeError" in caplog.text
        assert "test_creator_postprocessing_failure" in caplog.text

        response = TestClient(app).get(f"/run/{record.run_id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "failed"
        assert payload["result"] is None
        assert payload["trace"][0]["call_id"] == "synthetic-c001"
        assert "SENSITIVE-CANARY" not in response.text

    def test_failed_run_with_stale_investigation_cannot_be_synthesized(self) -> None:
        record = run_store.create(city="", programme=[])
        record.status = RunStatus.FAILED
        record.result = {"investigation": {"investigation_id": "stale"}}
        response = TestClient(app).post(
            "/creator/synthesize",
            json={"run_id": record.run_id},
        )
        assert response.status_code == 409
        assert "failed runs cannot be synthesized" in response.json()["detail"].lower()

    def test_nonexception_orchestrator_failure_discards_partial_creator_result(self) -> None:
        record = run_store.create(city="", programme=[])
        record.result = {"data_status": "measured", "partial": "must not escape"}
        record.state_json = '{"partial": true}'
        state = SimpleNamespace(
            stop_reason="error",
            phase=SimpleNamespace(value="RANK"),
            trace_rows=[{"tool": "rank_cohorts", "call_id": "safe-c001"}],
        )

        creator_routes._record_creator_stopped(record, state)

        assert record.status.value == "failed"
        assert record.result is None
        assert record.state_json is None
        assert record.stop_reason == "error"
        assert record.current_phase == "RANK"
        response = TestClient(app).get(f"/run/{record.run_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert response.json()["result"] is None
