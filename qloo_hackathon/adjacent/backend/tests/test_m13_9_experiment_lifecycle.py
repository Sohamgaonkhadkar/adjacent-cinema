"""M13.9 experiment lifecycle regressions.

Save → observe → evaluate → history, with the properties the milestone
requires: idempotent retries, partial observations, observed-zero vs missing,
append-only evaluations that supersede rather than rewrite, persistence across
repository re-open, and no unprotected side effects on the cinema surface.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.api import creator_routes
from app.domain.experiment_repository import ExperimentRepository
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Point the experiment repository at a throwaway database."""
    creator_routes.reset_repo_for_tests(tmp_path / "experiments.db")
    yield TestClient(app)
    creator_routes.reset_repo_for_tests(None)


def _save(client: TestClient, request_id: str = "req-00000001", run_id: str = "run-a") -> dict:
    response = client.post("/experiments", json={
        "request_id": request_id,
        "film_title": "Neon Harbour",
        "hypothesis": "An audience aligned with the artist world is reachable with artist framing.",
        "success_criteria": "Responses reference the artist framing; reach beats own baseline.",
        "observation_window": "First two weeks after release.",
        "action_plan": "Position title/description toward the artist world and test.",
        "data_status": "fixture",
        "source_run_id": run_id,
        "source_bet": {"primary": {"cohort_id": "music_artists", "mean_affinity": 0.71}},
        "provenance": {"primary_call_id": "call-1", "data_status": "fixture"},
    })
    assert response.status_code == 201
    return response.json()


class TestSaveExperiment:
    def test_save_and_retrieve_with_snapshot(self, client: TestClient) -> None:
        saved = _save(client)
        assert saved["duplicate"] is False
        exp = saved["experiment"]

        fetched = client.get(f"/experiments/{exp['experiment_id']}").json()
        assert fetched["experiment"]["hypothesis"] == exp["hypothesis"]
        # The decision snapshot travels with the experiment.
        assert fetched["experiment"]["source_bet"]["primary"]["cohort_id"] == "music_artists"
        assert fetched["experiment"]["provenance"]["primary_call_id"] == "call-1"
        assert fetched["observations"] == []
        assert fetched["evaluations"] == []

    def test_retry_same_request_id_returns_original(self, client: TestClient) -> None:
        first = _save(client)
        again = client.post("/experiments", json={
            "request_id": "req-00000001",
            "film_title": "Neon Harbour",
            "hypothesis": "A DIFFERENT hypothesis must not create a second decision.",
        })
        assert again.status_code == 201
        body = again.json()
        assert body["duplicate"] is True
        assert body["experiment"]["experiment_id"] == first["experiment"]["experiment_id"]
        assert body["experiment"]["hypothesis"] == first["experiment"]["hypothesis"]

    def test_second_save_for_same_run_is_deduplicated(self, client: TestClient) -> None:
        first = _save(client, request_id="req-aaaaaaaa")
        second = _save(client, request_id="req-bbbbbbbb", run_id="run-a")
        assert second["duplicate"] is True
        assert second["experiment"]["experiment_id"] == first["experiment"]["experiment_id"]
        assert len(client.get("/experiments").json()["experiments"]) == 1


class TestObservations:
    def test_partial_observation_and_zero_vs_missing(self, client: TestClient) -> None:
        exp = _save(client)["experiment"]
        eid = exp["experiment_id"]

        # An observed zero is data; missing stays out of metrics entirely.
        observed_zero = client.post(f"/experiments/{eid}/observations", json={
            "request_id": "obs-zero-0001",
            "kind": "ANALYTICS",
            "measurement_status": "OBSERVED",
            "observed_on": "2026-10-10",
            "metrics": {"views": 0},
        })
        assert observed_zero.status_code == 201
        assert observed_zero.json()["observation"]["metrics"]["views"] == 0

        missing = client.post(f"/experiments/{eid}/observations", json={
            "request_id": "obs-miss-0001",
            "kind": "ANALYTICS",
            "measurement_status": "UNAVAILABLE",
            "limitations": "Analytics access not granted.",
        })
        assert missing.status_code == 201
        body = missing.json()["observation"]
        assert body["metrics"] == {}
        assert body["measurement_status"] == "UNAVAILABLE"

        listed = client.get(f"/experiments/{eid}").json()["observations"]
        assert len(listed) == 2

    def test_observation_retry_is_idempotent(self, client: TestClient) -> None:
        eid = _save(client)["experiment"]["experiment_id"]
        payload = {
            "request_id": "obs-retry-001",
            "kind": "FEEDBACK",
            "measurement_status": "PARTIAL",
            "interpretation": "Three comments referenced the artist framing.",
        }
        first = client.post(f"/experiments/{eid}/observations", json=payload)
        again = client.post(f"/experiments/{eid}/observations", json=payload)
        assert first.status_code == again.status_code == 201
        assert again.json()["duplicate"] is True
        assert len(client.get(f"/experiments/{eid}").json()["observations"]) == 1

    def test_invalid_status_rejected(self, client: TestClient) -> None:
        eid = _save(client)["experiment"]["experiment_id"]
        response = client.post(f"/experiments/{eid}/observations", json={
            "request_id": "obs-bad-00001",
            "kind": "ANALYTICS",
            "measurement_status": "GUESSED",
        })
        assert response.status_code == 422

    def test_observation_on_unknown_experiment_404(self, client: TestClient) -> None:
        response = client.post("/experiments/nope/observations", json={
            "request_id": "obs-404-0001",
            "kind": "NOTE",
            "measurement_status": "OBSERVED",
        })
        assert response.status_code == 404


class TestEvaluations:
    def test_evaluate_and_supersede_keeps_history(self, client: TestClient) -> None:
        eid = _save(client)["experiment"]["experiment_id"]
        first = client.post(f"/experiments/{eid}/evaluations", json={
            "request_id": "eval-00000001",
            "outcome": "INCONCLUSIVE",
            "rationale": "Only one week of data; nothing conclusive yet.",
        }).json()["evaluation"]

        second = client.post(f"/experiments/{eid}/evaluations", json={
            "request_id": "eval-00000002",
            "outcome": "SUPPORTED",
            "rationale": "Two weeks in, responses repeatedly referenced the artist framing.",
            "unknowns": "Retention never observed — analytics not connected.",
        }).json()["evaluation"]

        assert second["supersedes_id"] == first["evaluation_id"]
        history = client.get(f"/experiments/{eid}").json()["evaluations"]
        assert len(history) == 2  # append-only: the first evaluation survives
        assert history[0]["outcome"] == "INCONCLUSIVE"
        assert history[1]["outcome"] == "SUPPORTED"

    def test_invalid_outcome_rejected(self, client: TestClient) -> None:
        eid = _save(client)["experiment"]["experiment_id"]
        response = client.post(f"/experiments/{eid}/evaluations", json={
            "request_id": "eval-bad-0001",
            "outcome": "MAYBE",
            "rationale": "x",
        })
        assert response.status_code == 422


class TestPersistence:
    def test_history_survives_repository_reopen(self, client: TestClient, tmp_path: Path) -> None:
        eid = _save(client)["experiment"]["experiment_id"]
        client.post(f"/experiments/{eid}/observations", json={
            "request_id": "obs-persist-1", "kind": "SCREENING",
            "measurement_status": "OBSERVED", "metrics": {"tickets_sold": 42},
        })
        client.post(f"/experiments/{eid}/evaluations", json={
            "request_id": "eval-persist", "outcome": "CONTRADICTED",
            "rationale": "No response to the framing at all.",
        })

        # Simulate an application restart against the same database file.
        repo = ExperimentRepository(tmp_path / "experiments.db")
        exp = repo.get_experiment(eid)
        assert exp is not None
        assert len(repo.list_observations(eid)) == 1
        evaluations = repo.list_evaluations(eid)
        assert evaluations[0]["outcome"] == "CONTRADICTED"
        repo.close()
