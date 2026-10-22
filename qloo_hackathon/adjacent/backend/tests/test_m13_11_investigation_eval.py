"""M13.11 regressions: cultural investigation layer + Qloo-vs-LLM harness.

Covers: investigation structure and honesty (FACT vs INTERPRETATION, evidence
refs, insufficiency paths, fixture labelling), the API wiring for creator
runs, cinema non-regression, and the evaluation harness mechanics (grounded
condition, blocked Condition A, stub labelling, rubric behaviour).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.main import app
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "research" / "scripts"))

from m13_11_qloo_vs_llm import (
    BRIEFS,
    RUBRIC_VERSION,
    LLMUnavailableError,
    OpenAICompatibleLLM,
    ScriptedStubLLM,
    run_comparison,
    run_grounded_condition,
    run_llm_condition,
    score_output,
)

TERMINAL = {"completed", "failed", "insufficient"}


def _wait(client: TestClient, run_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        last = client.get(f"/run/{run_id}").json()
        if last.get("status") in TERMINAL:
            return last
        time.sleep(0.05)
    raise AssertionError(f"run never terminal; last={last}")


class TestInvestigationViaAPI:
    def test_creator_demo_result_carries_structured_investigation(self) -> None:
        client = TestClient(app)
        run_id = client.post("/creator/run/demo").json()["run_id"]
        final = _wait(client, run_id)
        assert final["status"] == "completed"
        inv = final["result"]["investigation"]

        # Questions map to real tools with real statuses and evidence refs.
        assert len(inv["questions"]) >= 3
        # M13.12: q0 (context framing) may precede the tool questions — look up
        # by tool rather than by position.
        q1 = next(q for q in inv["questions"] if q["tool"] == "get_taste_profile")
        assert q1["status"] == "answered"
        assert q1["evidence_refs"]  # cites the call that actually ran

        # Hypothesis chain present and evidence-linked.
        primary = inv["hypotheses"]["primary"]
        assert primary is not None
        assert primary["evidence_refs"]
        assert primary["falsification"]
        assert inv["experiment"]["success_criteria"]

        # Provenance: every cited call id exists in the run's trace.
        trace_calls = {
            row.get("call_id") for row in final.get("trace") or [] if row.get("call_id")
        }
        for ref in inv["provenance"]["call_ids"]:
            assert ref in trace_calls, f"evidence ref {ref} not in run trace"

        # Fixture labelling + affinity guard are mandatory.
        assert inv["data_status"] == "fixture"
        assert any("FIXTURE" in lim for lim in inv["limitations"])
        assert any("not evidence that any audience will watch" in lim for lim in inv["limitations"])

    def test_sse_emits_investigation_event(self) -> None:
        client = TestClient(app)
        run_id = client.post("/creator/run/demo").json()["run_id"]
        _wait(client, run_id)
        with client.stream("GET", f"/run/{run_id}/stream") as response:
            body = "".join(chunk for chunk in response.iter_text())
        assert "event: investigation" in body

    def test_cinema_run_has_no_investigation_key(self) -> None:
        client = TestClient(app)
        run_id = client.post("/run/demo").json()["run_id"]
        final = _wait(client, run_id)
        assert final["status"] == "completed"
        assert "investigation" not in final["result"]


class TestInvestigationHonesty:
    def test_fact_and_interpretation_are_separated(self) -> None:
        grounded = run_grounded_condition(BRIEFS[0])
        assert grounded["positioning"] is not None
        assert grounded["generator"]["kind"] == "rule_based_grounded"
        # Every grounded output must acknowledge the affinity guard.
        assert any("not evidence" in lim for lim in grounded["limitations"])

    def test_insufficient_brief_produces_no_hypothesis(self) -> None:
        thin_ice = next(b for b in BRIEFS if b["fixture"] == "insufficient_evidence")
        grounded = run_grounded_condition(thin_ice)
        assert grounded["stop_reason"] != "complete"
        assert grounded["positioning"] is None  # honest absence, not fabrication

    def test_empty_state_yields_insufficient_statuses(self) -> None:
        from app.domain.cultural_investigation import build_investigation

        empty_state = SimpleNamespace(
            taste_tags=[], resolved_items=[], unresolved_items=[],
            expansion_call_ids={}, candidates_by_domain={}, ranked=[], rejected=[],
            taste_call_id=None, calls_made=0,
        )
        inv = build_investigation(
            empty_state,
            film={"title": "Untitled"}, seeds=[],
            bet=None, test_card=None, geography=None, city=None,
            data_status="measured",
        )
        assert inv["hypotheses"]["primary"] is None
        assert inv["experiment"] is None
        assert all(q["status"] in ("insufficient", "unavailable") for q in inv["questions"])
        assert any("unsupported" in lim or "No taste-profile" in lim for lim in inv["limitations"])


class TestEvaluationHarness:
    def test_grounded_condition_scores_and_traceability(self) -> None:
        comparison = run_comparison(briefs=[BRIEFS[0]])
        grounded_runs = [r for r in comparison["runs"] if r["output"]["condition"] == "qloo_grounded"]
        assert len(grounded_runs) == 1
        scores = grounded_runs[0]["scores"]
        assert scores["rubric_version"] == RUBRIC_VERSION == "3.0"
        assert set(scores["categories_applicable"]) == {"decision_quality", "evidence_grounding"}
        dq = scores["decision_quality"]["checks"]
        assert dq["schema_valid"]["score"] == 1
        assert dq["falsifiable"]["score"] == 1
        assert dq["uncertainty_handled"]["score"] == 1
        grounding = scores["evidence_grounding"]["checks"]
        assert grounding["evidence_refs_present"]["score"] == 1
        assert grounding["refs_resolve"]["score"] == 1

    def test_condition_a_blocked_without_llm(self, monkeypatch) -> None:
        monkeypatch.delenv("ADJACENT_LLM_API_KEY", raising=False)
        with pytest.raises(LLMUnavailableError):
            OpenAICompatibleLLM()
        comparison = run_comparison(briefs=[BRIEFS[0]], llm_generator=None)
        assert comparison["summary"]["condition_a_status"] == "blocked"
        assert "ADJACENT_LLM_API_KEY" in (comparison["summary"]["condition_a_error"] or "")
        # No silently-stubbed Condition A rows exist.
        assert all(r["output"]["condition"] == "qloo_grounded" for r in comparison["runs"])

    def test_stub_condition_is_labelled_and_scores_lower(self) -> None:
        comparison = run_comparison(briefs=[BRIEFS[0]], llm_generator=ScriptedStubLLM())
        stub_runs = [r for r in comparison["runs"] if r["output"]["condition"] == "llm_only"]
        assert len(stub_runs) == 1
        assert stub_runs[0]["output"]["generator"]["kind"] == "llm_stub"
        stub_scores = stub_runs[0]["scores"]
        # Rubric v2: grounding is NOT APPLICABLE to the baseline — never a zero.
        assert stub_scores["evidence_grounding"] is None
        assert stub_scores["categories_applicable"] == ["decision_quality"]
        assert comparison["summary"]["llm_only"]["evidence_grounding"]["applicable"] is False
        grounded = next(r for r in comparison["runs"] if r["output"]["condition"] == "qloo_grounded")
        assert (
            grounded["scores"]["decision_quality"]["total"]
            > stub_scores["decision_quality"]["total"]
        )

    def test_llm_condition_output_shape(self) -> None:
        out = run_llm_condition(BRIEFS[1], ScriptedStubLLM())
        assert out["evidence_refs"] == []
        assert out["positioning"]["hypothesis"]
        scores = score_output({**out, "_available_refs": [], "_genre": BRIEFS[1]["genre"]})
        assert scores["decision_quality"]["max"] == 5
        assert scores["evidence_grounding"] is None

    def test_all_briefs_run_without_crash(self) -> None:
        comparison = run_comparison()
        grounded = [r for r in comparison["runs"] if r["output"]["condition"] == "qloo_grounded"]
        assert len(grounded) == len(BRIEFS)
        assert all(r.get("scores") for r in grounded)
        assert all(r["run_metadata"]["rubric_version"] == "3.0" for r in grounded)
        assert comparison["methodology"].startswith("Offline harness, rubric v3.")
