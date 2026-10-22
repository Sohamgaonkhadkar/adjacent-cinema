"""M13.9 Creator Mode regressions.

Covers the creator analysis journey on the fixture-labelled demo path and the
honest-failure behaviour of the live path — mirroring the cinema golden-path
contract: no silent fixture substitution, truthful data_status, preserved
inputs, 422 on empty seeds, 404 on unknown runs.
"""

from __future__ import annotations

import asyncio
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

        # These are the backend payloads required by Creator steps 02–04.
        # They must be present on a successful fixture run even though the
        # optional language-model synthesis may be blocked in public-demo mode.
        investigation = result["investigation"]
        assert investigation["data_status"] == "fixture"
        assert investigation["questions"]
        assert "hypotheses" in investigation
        assert result["cohorts"]["ranked"]

        synthesis_status = client.get("/creator/synthesis-status")
        assert synthesis_status.status_code == 200
        assert synthesis_status.json()["available"] is False
        assert synthesis_status.json().get("blocked_reason")

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
            assert cohort["kind"]
            assert cohort["construction_reason"]

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

    def test_fixture_postprocessing_exception_preserves_safe_trace_and_closes_client(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        from app.qloo import mock as mock_module

        closed: list[bool] = []
        original_client = mock_module.MockQlooClient

        class TrackingMockClient(original_client):
            async def aclose(self) -> None:
                closed.append(True)
                await super().aclose()

        async def fail_after_orchestration(*_args, **_kwargs):
            raise TypeError("SENSITIVE-FIXTURE-CANARY")

        monkeypatch.setattr(mock_module, "MockQlooClient", TrackingMockClient)
        monkeypatch.setattr(creator_routes, "_post_pipeline_creator", fail_after_orchestration)
        caplog.set_level(logging.ERROR, logger=creator_routes.__name__)

        record = run_store.create(city="", programme=[])
        asyncio.run(creator_routes._execute_creator_demo_run(record))

        assert record.status.value == "failed"
        assert record.result is None
        assert record.state_json is None
        assert record.trace  # state existed and its safe trace was retained
        assert record.current_phase
        assert len([event for event in record.events if event.event == "error"]) == 1
        assert closed == [True]
        assert "SENSITIVE-FIXTURE-CANARY" not in caplog.text
        response = TestClient(app).get(f"/run/{record.run_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert response.json()["result"] is None


    def test_fixture_executor_failure_after_state_creation_clears_partial_result_and_closes_client(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        from app import runner
        from app.agent.budget import Budget
        from app.agent.state import AdjacentState, ProgrammeItem
        from app.config import Settings
        from app.domain.ledger import ProvenanceLedger
        from app.qloo import mock as mock_module

        record = run_store.create(city="", venue_name="Creator fixture failure", programme=[])
        record.result = {"data_status": "fixture", "partial": "must be cleared"}
        record.state_json = '{"partial": true}'
        monkeypatch.delenv("ADJACENT_PUBLIC_DEMO", raising=False)

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                self.notice = "fixture"
                self.fixture = SimpleNamespace(
                    programme=[{"title": "Synthetic Seed", "year": 2000, "imdb_id": None}],
                    scenario="synthetic",
                    description="safe synthetic fixture",
                )
                self.recorder = SimpleNamespace(rows=[])
                self.closed = False

            async def aclose(self):
                self.closed = True

        fake_client = FakeClient()
        monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: SimpleNamespace()))
        monkeypatch.setattr(mock_module, "MockQlooClient", lambda *_args, **_kwargs: fake_client)
        monkeypatch.setattr(runner, "resolve_fixture_path", lambda *_args, **_kwargs: SimpleNamespace(stem="synthetic"))
        monkeypatch.setattr(runner, "programme_items", lambda _programme: [])
        # The real state shape passes through orchestration and public-stop
        # sanitization, then post-processing fails after state/trace exist.
        state = AdjacentState(
            run_id=record.run_id,
            fixture_name="synthetic",
            fixture_path="synthetic.json",
            scenario="synthetic",
            fixture_notice="fixture",
            data_status="fixture",
            description="safe synthetic fixture",
            programme=[ProgrammeItem(
                title="Synthetic Seed", year=2000, imdb_id=None, declared_entity_id=None
            )],
            budget=Budget(),
        )
        state.ledger = ProvenanceLedger(recorder=SimpleNamespace(rows=[]), data_status="fixture")
        state.stop = SimpleNamespace(
            reason=SimpleNamespace(value="complete"),
            message="synthetic complete",
            detail_code=None,
            stats={},
        )
        state.status = SimpleNamespace(value="finished")
        # Add one deterministic safe trace row to the actual recorder shape.
        state.ledger.recorder.rows.append(SimpleNamespace(
            started_at="2026-01-01T00:00:00+00:00",
            seq=1,
            model_dump=lambda: {"call_id": "fixture-call-safe", "tool": "fixture_test"},
        ))
        class FakeOrchestrator:
            def __init__(self, *_args, **_kwargs):
                pass
            async def run(self, _state):
                return state

        monkeypatch.setattr("app.agent.orchestrator.AgentOrchestrator", FakeOrchestrator)
        async def fail_post(*_args, **_kwargs):
            raise TypeError("SENSITIVE-FIXTURE-CANARY")
        monkeypatch.setattr(creator_routes, "_post_pipeline_creator", fail_post)
        caplog.set_level(logging.ERROR, logger=creator_routes.__name__)

        asyncio.run(creator_routes._execute_creator_demo_run(record))

        assert record.status.value == "failed"
        assert record.result is None
        assert record.state_json is None
        assert record.current_phase == "INIT"  # executor phase reflects actual pre-pipeline setup; trace remains available
        assert record.trace[0]["call_id"] == "fixture-call-safe"
        assert "SENSITIVE-FIXTURE-CANARY" not in caplog.text
        assert fake_client.closed is True
        assert len([event for event in record.events if event.event == "error"]) == 1
        response = TestClient(app).get(f"/run/{record.run_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert response.json()["result"] is None

class TestCreatorLiveRunHonesty:
    def test_unexpected_setup_exception_finishes_run_without_leaking_message(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        from app.config import Settings

        def fail_from_env(_cls):
            raise TypeError("SENSITIVE-SETUP-CANARY")

        monkeypatch.setattr(Settings, "from_env", classmethod(fail_from_env))
        caplog.set_level(logging.ERROR, logger=creator_routes.__name__)

        request = creator_routes.CreatorRunRequest(
            title="Synthetic setup failure",
            references=[creator_routes.ReferenceInput(title="Synthetic seed", year=2000)],
        )
        record = run_store.create(
            city="",
            venue_name="Creator: Synthetic setup failure",
            programme=request.seeds(),
        )
        asyncio.run(creator_routes._execute_creator_run(record, request))

        assert record.status.value == "failed"
        assert record.result is None
        assert record.state_json is None
        assert record.current_phase == "INIT"
        assert record.stop_reason == "error"
        assert "error_type=TypeError" in caplog.text
        assert "_execute_creator_run" in caplog.text
        assert "SENSITIVE-SETUP-CANARY" not in caplog.text
        assert "SENSITIVE-SETUP-CANARY" not in (record.error or "")
        assert len([event for event in record.events if event.event == "error"]) == 1

        response = TestClient(app).get(f"/run/{record.run_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert response.json()["result"] is None
        assert "SENSITIVE-SETUP-CANARY" not in response.text

    def test_orchestrator_tool_typeerror_logs_safe_frames_through_creator_executor(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        from app.config import Settings
        from app.qloo import client as qloo_client_module
        from app.qloo.trace import TraceRecorder
        from app.resolution import resolver as resolver_module

        class FakeQlooClient:
            def __init__(self, _settings):
                self.recorder = TraceRecorder(run_id="synthetic-live-run")
                self.closed = False

            async def aclose(self):
                self.closed = True

        class FailingResolver:
            async def resolve_programme(self, _programme):
                raise TypeError("SENSITIVE-TOOL-CANARY and fake provider payload")

        monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: SimpleNamespace(has_api_key=True)))
        monkeypatch.setattr(qloo_client_module, "QlooClient", FakeQlooClient)
        monkeypatch.setattr(resolver_module, "EntityResolver", lambda *_args, **_kwargs: FailingResolver())
        caplog.set_level(logging.ERROR, logger=creator_routes.__name__)

        request = creator_routes.CreatorRunRequest(
            title="Synthetic test",
            references=[creator_routes.ReferenceInput(title="Synthetic seed", year=2000)],
        )
        record = run_store.create(
            city="",
            venue_name="Creator: Synthetic test",
            programme=request.seeds(),
        )
        asyncio.run(creator_routes._execute_creator_run(record, request))

        assert record.status.value == "failed"
        assert record.result is None
        assert "error_type=TypeError" in caplog.text
        assert "resolve_programme" in caplog.text
        assert "orchestrator.py" in caplog.text
        assert "SENSITIVE-TOOL-CANARY" not in caplog.text
        assert "fake provider payload" not in caplog.text
        assert "SENSITIVE-TOOL-CANARY" not in (record.error or "")

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


class TestCreatorThemeInputs:
    def test_themes_are_not_converted_into_film_reference_seeds(self) -> None:
        request = creator_routes.CreatorRunRequest(
            title="Test Film",
            themes=["isolation", "night workers"],
            references=[
                creator_routes.ReferenceInput(title="Nightcrawler", year=2014),
                creator_routes.ReferenceInput(title="After Hours", year=1985),
            ],
        )

        assert request.seeds() == [
            {"title": "Nightcrawler", "year": 2014, "imdb_id": None},
            {"title": "After Hours", "year": 1985, "imdb_id": None},
        ]

    def test_only_unique_exact_theme_tags_enter_taste_and_expansion_signals(self) -> None:
        from app.agent.budget import Budget
        from app.agent.state import AdjacentState
        from app.live_runner import LivePipeline
        from app.runner import _expand_candidates, _taste_profile

        class FakeClient:
            def __init__(self):
                self.recorder = SimpleNamespace(rows=[])
                self.tag_queries = []
                self.insight_calls = []

            async def tags(self, *, filter_query, **_kwargs):
                self.tag_queries.append(filter_query)
                self.recorder.rows.append(object())
                if filter_query == "Thriller":
                    results = [
                        SimpleNamespace(tag_id="qloo-thriller", name="Thriller"),
                        SimpleNamespace(tag_id="qloo-thriller-films", name="Thriller Films"),
                    ]
                else:
                    # A close-looking result is not accepted as an exact tag match.
                    results = [SimpleNamespace(tag_id="qloo-night-worker", name="Night Worker")]
                return SimpleNamespace(
                    call_id=f"theme-call-{len(self.tag_queries)}",
                    results=results,
                )

            async def insights(self, **kwargs):
                self.insight_calls.append(kwargs)
                if kwargs["filter_type"] == "urn:tag":
                    results = [SimpleNamespace(
                        tag_id="qloo-profile-tag",
                        name="Urban isolation",
                        affinity=0.72,
                        band="high",
                    )]
                    return SimpleNamespace(call_id="taste-call", results=results)
                return SimpleNamespace(call_id="expand-call", results=[])

        class EmptyResolver:
            async def resolve_programme(self, programme):
                assert programme == []
                return []

        client = FakeClient()
        state = AdjacentState(
            run_id="theme-signal-test",
            data_status="measured",
            theme_queries=["Thriller", "Night workers"],
            programme=[],
            budget=Budget(),
        )
        pipeline = LivePipeline(client, EmptyResolver(), [])
        asyncio.run(pipeline.resolve_programme(state, state.budget))

        assert state.theme_tag_ids == ["qloo-thriller"]
        assert [row["status"] for row in state.theme_resolution] == ["matched", "unresolved"]
        assert state.resolution_verdict is not None and state.resolution_verdict.sufficient

        asyncio.run(_taste_profile(client, state, state.budget))
        assert client.insight_calls[0]["signal_interests_entities"] is None
        assert client.insight_calls[0]["signal_interests_tags"] == ["qloo-thriller"]

        asyncio.run(_expand_candidates(
            client, state, state.budget, domains=("urn:entity:movie",)
        ))
        assert client.insight_calls[1]["signal_interests_entities"] is None
        assert client.insight_calls[1]["signal_interests_tags"] == ["qloo-thriller"]
