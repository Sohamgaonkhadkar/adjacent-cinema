"""M13.9 experiment lifecycle regressions.

Save → observe → evaluate → history, with the properties the milestone
requires: idempotent retries, partial observations, observed-zero vs missing,
append-only evaluations that supersede rather than rewrite, persistence across
repository re-open, and no unprotected side effects on the cinema surface.
"""

from __future__ import annotations

import time
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


def _completed_fixture_run(client: TestClient, title: str = "Night Harbour") -> dict:
    created = client.post("/creator/run/demo", json={
        "title": title,
        "logline": "A night-shift story used only to exercise the labelled fixture contract.",
        "genre": "drama",
        "language": "English",
        "themes": [],
        "references": [],
        "release_goal": "offline contract test",
    })
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        current = client.get(f"/run/{run_id}").json()
        if current["status"] in {"completed", "failed", "insufficient"}:
            assert current["status"] == "completed", current
            return current
        time.sleep(0.01)
    pytest.fail("fixture Creator run did not reach a terminal state")


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

    def test_versioned_positioning_snapshot_round_trips_and_survives_appends(self, client: TestClient) -> None:
        final_run = _completed_fixture_run(client)
        run_id = final_run["run_id"]
        result = final_run["result"]
        source_cohort = result["cohorts"]["ranked"][0]
        source_member = source_cohort["members"][0]
        call_id = source_member["call_id"]
        selected = {
            "id": "anchor",
            "type": "ANCHOR",
            "availability": "available",
            "source_cohort_ids": [source_cohort["cohort_id"]],
            "entity_refs": [{
                "cohort_id": source_cohort["cohort_id"],
                "entity_id": source_member["entity_id"],
                "call_id": call_id,
            }],
            "evidence_refs": [{
                "kind": "source_member",
                "description": "A reference to a returned fixture member.",
                "call_ids": [call_id],
                "cohort_ids": [source_cohort["cohort_id"]],
                "entity_ids": [source_member["entity_id"]],
            }],
            "evidence_challenge": {"supporting_call_ids": [call_id], "source_inputs": []},
            "falsifiable_hypothesis": "Compare the framing using a preselected observable measure.",
            "creative_direction": "Test the source-backed cultural direction.",
            "tradeoffs": ["Fixture evidence is not live Qloo data."],
        }
        strategies = [
            selected,
            {"id": "bridge", "type": "BRIDGE", "availability": "unavailable", "unavailable_reason": "No supported shared evidence.", "source_cohort_ids": [], "entity_refs": [], "evidence_refs": []},
            {"id": "frontier", "type": "FRONTIER", "availability": "unavailable", "unavailable_reason": "No same-context alternative clears the gate.", "source_cohort_ids": [], "entity_refs": [], "evidence_refs": []},
        ]
        card = result["test_card"]
        design = {
            "comparison_protocol": card["comparison_protocol"],
            "primary_measure": card["primary_measure"],
            "decision_rule": card["decision_rule"],
            "observation_window": card["observation_window"],
        }
        snapshot = {
            "snapshot_version": "cultural-positioning-snapshot-v1",
            "calculation_version": "cultural-positioning-v1",
            "source_run_id": run_id,
            "original_data_status": "fixture",
            "selected_strategy_id": "anchor",
            "selected_strategy": selected,
            "strategies": strategies,
            "policy": {"formula_version": "weighted-ordinal-preference-v1", "values": {"fit": 50, "exploration": 25, "breadth": 25}},
            "original_test_card": card,
            "experiment_design": design,
        }
        payload = {
            "request_id": "positioning-snapshot-1",
            "film_title": result["film"]["title"],
            "hypothesis": selected["falsifiable_hypothesis"],
            "action_plan": selected["creative_direction"],
            "observation_window": design["observation_window"],
            "data_status": "fixture",
            "source_run_id": run_id,
            "source_bet": {"primary": result["programme_bet"]["primary"], "cultural_multiverse_snapshot": snapshot},
        }

        invalid_run = {**payload, "source_bet": {**payload["source_bet"], "cultural_multiverse_snapshot": {**snapshot, "source_run_id": "another-run"}}}
        assert client.post("/experiments", json={**invalid_run, "request_id": "positioning-bad-run"}).status_code == 422
        bad_reference = {**selected, "entity_refs": [{**selected["entity_refs"][0], "call_id": "fabricated-call"}]}
        bad_snapshot = {**snapshot, "selected_strategy": bad_reference, "strategies": [bad_reference, *strategies[1:]]}
        bad_payload = {**payload, "request_id": "positioning-bad-call", "source_bet": {**payload["source_bet"], "cultural_multiverse_snapshot": bad_snapshot}}
        assert client.post("/experiments", json=bad_payload).status_code == 422

        response = client.post("/experiments", json=payload)
        assert response.status_code == 201, response.text
        experiment = response.json()["experiment"]
        assert experiment["source_run_id"] == run_id
        assert experiment["film_title"] == result["film"]["title"]
        assert experiment["source_bet"]["cultural_multiverse_snapshot"] == snapshot
        experiment_id = experiment["experiment_id"]

        observation = client.post(f"/experiments/{experiment_id}/observations", json={
            "request_id": "positioning-observation-1",
            "kind": "NOTE",
            "measurement_status": "UNAVAILABLE",
            "limitations": "No external result was collected.",
        })
        evaluation = client.post(f"/experiments/{experiment_id}/evaluations", json={
            "request_id": "positioning-evaluation-1",
            "outcome": "INCONCLUSIVE",
            "rationale": "A saved plan is not evidence that its test ran.",
        })
        assert observation.status_code == 201
        assert evaluation.status_code == 201
        reopened = client.get(f"/experiments/{experiment_id}").json()
        assert reopened["experiment"]["source_bet"]["cultural_multiverse_snapshot"] == snapshot
        assert len(reopened["observations"]) == 1
        assert reopened["evaluations"][0]["outcome"] == "INCONCLUSIVE"

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

    def test_observation_correction_must_target_a_current_local_record(
        self, client: TestClient
    ) -> None:
        first_id = _save(client, request_id="req-obscorr-1", run_id="run-obscorr-1")[
            "experiment"
        ]["experiment_id"]
        second_id = _save(client, request_id="req-obscorr-2", run_id="run-obscorr-2")[
            "experiment"
        ]["experiment_id"]
        original = client.post(f"/experiments/{first_id}/observations", json={
            "request_id": "obs-obscorr-1",
            "kind": "ANALYTICS",
            "measurement_status": "OBSERVED",
            "metrics": {"views": 0},
        }).json()["observation"]
        correction = client.post(f"/experiments/{first_id}/observations", json={
            "request_id": "obs-obscorr-2",
            "kind": "ANALYTICS",
            "measurement_status": "PARTIAL",
            "metrics": {"views": 0},
            "supersedes_id": original["observation_id"],
        })
        foreign = client.post(f"/experiments/{second_id}/observations", json={
            "request_id": "obs-obscorr-3",
            "kind": "ANALYTICS",
            "measurement_status": "PARTIAL",
            "supersedes_id": original["observation_id"],
        })
        stale = client.post(f"/experiments/{first_id}/observations", json={
            "request_id": "obs-obscorr-4",
            "kind": "ANALYTICS",
            "measurement_status": "PARTIAL",
            "supersedes_id": original["observation_id"],
        })

        assert correction.status_code == 201
        assert correction.json()["observation"]["supersedes_id"] == original["observation_id"]
        assert foreign.status_code == stale.status_code == 422
        history = client.get(f"/experiments/{first_id}").json()["observations"]
        assert len(history) == 2
        assert history[0]["metrics"]["views"] == 0

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
    def test_evaluate_and_repeatedly_supersede_keeps_history_and_current_outcome(
        self, client: TestClient
    ) -> None:
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
        third = client.post(f"/experiments/{eid}/evaluations", json={
            "request_id": "eval-00000003",
            "outcome": "CONTRADICTED",
            "rationale": "The later release window did not reproduce the framing response.",
        }).json()["evaluation"]

        assert second["supersedes_id"] == first["evaluation_id"]
        assert third["supersedes_id"] == second["evaluation_id"]
        history = client.get(f"/experiments/{eid}").json()["evaluations"]
        assert len(history) == 3  # append-only: every earlier evaluation survives
        assert [item["outcome"] for item in history] == [
            "INCONCLUSIVE", "SUPPORTED", "CONTRADICTED"
        ]

        listed = client.get("/experiments").json()["experiments"]
        experiment = next(item for item in listed if item["experiment_id"] == eid)
        assert experiment["latest_evaluation"] == "CONTRADICTED"

    def test_evaluation_rejects_observations_outside_its_experiment(
        self, client: TestClient
    ) -> None:
        first_id = _save(client, request_id="req-evidence-1", run_id="run-evidence-1")[
            "experiment"
        ]["experiment_id"]
        second_id = _save(client, request_id="req-evidence-2", run_id="run-evidence-2")[
            "experiment"
        ]["experiment_id"]
        observation = client.post(f"/experiments/{first_id}/observations", json={
            "request_id": "obs-evidence-1",
            "kind": "ANALYTICS",
            "measurement_status": "OBSERVED",
            "metrics": {"views": 0},
        }).json()["observation"]

        foreign = client.post(f"/experiments/{second_id}/evaluations", json={
            "request_id": "eval-foreign-observation",
            "outcome": "SUPPORTED",
            "rationale": "This must not cite another experiment's observation.",
            "observation_ids": [observation["observation_id"]],
        })
        missing = client.post(f"/experiments/{second_id}/evaluations", json={
            "request_id": "eval-missing-observation",
            "outcome": "SUPPORTED",
            "rationale": "This must not cite a nonexistent observation.",
            "observation_ids": ["missing-observation-id"],
        })

        assert foreign.status_code == 422
        assert missing.status_code == 422
        assert client.get(f"/experiments/{second_id}").json()["evaluations"] == []

    def test_evaluation_correction_must_target_a_current_local_record(
        self, client: TestClient
    ) -> None:
        eid = _save(client, request_id="req-correction-1", run_id="run-correction-1")[
            "experiment"
        ]["experiment_id"]
        other_id = _save(client, request_id="req-correction-2", run_id="run-correction-2")[
            "experiment"
        ]["experiment_id"]
        first = client.post(f"/experiments/{eid}/evaluations", json={
            "request_id": "eval-correction-1",
            "outcome": "INCONCLUSIVE",
            "rationale": "Initial evidence is incomplete.",
        }).json()["evaluation"]
        second = client.post(f"/experiments/{eid}/evaluations", json={
            "request_id": "eval-correction-2",
            "outcome": "SUPPORTED",
            "rationale": "A later observation supports the hypothesis.",
        }).json()["evaluation"]
        foreign = client.post(f"/experiments/{other_id}/evaluations", json={
            "request_id": "eval-correction-3",
            "outcome": "CONTRADICTED",
            "rationale": "Separate experiment.",
        }).json()["evaluation"]

        stale = client.post(f"/experiments/{eid}/evaluations", json={
            "request_id": "eval-correction-stale",
            "outcome": "CONTRADICTED",
            "rationale": "Cannot branch from an already superseded evaluation.",
            "supersedes_id": first["evaluation_id"],
        })
        foreign_parent = client.post(f"/experiments/{eid}/evaluations", json={
            "request_id": "eval-correction-foreign",
            "outcome": "CONTRADICTED",
            "rationale": "Cannot supersede a different experiment's evaluation.",
            "supersedes_id": foreign["evaluation_id"],
        })
        unknown_parent = client.post(f"/experiments/{eid}/evaluations", json={
            "request_id": "eval-correction-unknown",
            "outcome": "CONTRADICTED",
            "rationale": "Cannot supersede a missing evaluation.",
            "supersedes_id": "missing-evaluation-id",
        })

        assert stale.status_code == foreign_parent.status_code == unknown_parent.status_code == 422
        history = client.get(f"/experiments/{eid}").json()["evaluations"]
        assert [item["evaluation_id"] for item in history] == [
            first["evaluation_id"], second["evaluation_id"]
        ]

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
