"""M13.9 Creator Mode regressions.

Covers the creator analysis journey on the fixture-labelled demo path and the
honest-failure behaviour of the live path — mirroring the cinema golden-path
contract: no silent fixture substitution, truthful data_status, preserved
inputs, 422 on empty seeds, 404 on unknown runs.
"""

from __future__ import annotations

import time

import pytest
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
