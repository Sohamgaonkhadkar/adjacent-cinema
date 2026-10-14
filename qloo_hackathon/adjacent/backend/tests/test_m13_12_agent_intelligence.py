"""M13.12 regressions: context-aware investigation, typed claims, evidence-ref
verification, hypothesis quality, and honest insufficiency.

Everything here is deterministic — no LLM is involved in the decision engine.
"""

from __future__ import annotations

import time
from types import SimpleNamespace

from app.domain.cultural_investigation import build_investigation, verify_evidence_refs
from app.main import app
from fastapi.testclient import TestClient

TERMINAL = {"completed", "failed", "insufficient"}
CLAIM_TYPES = {"FACT", "INTERPRETATION", "HYPOTHESIS", "UNKNOWN"}


def _wait(client: TestClient, run_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        last = client.get(f"/run/{run_id}").json()
        if last.get("status") in TERMINAL:
            return last
        time.sleep(0.05)
    raise AssertionError(f"run never terminal; last={last}")


def _demo_investigation() -> tuple[dict, dict]:
    client = TestClient(app)
    run_id = client.post("/creator/run/demo").json()["run_id"]
    final = _wait(client, run_id)
    assert final["status"] == "completed"
    return final, final["result"]["investigation"]


def _cohort(domain: str, mean_affinity: float, call_id: str, members: int, qualifying: int):
    return SimpleNamespace(
        domain=domain,
        score=SimpleNamespace(mean_affinity=mean_affinity, call_id=call_id),
        members=[SimpleNamespace(name=f"{domain}-m{i}") for i in range(members)],
        qualifying_members=[
            SimpleNamespace(name=f"{domain}-q{i}") for i in range(qualifying)
        ],
        rejection=None,
    )


def _empty_state() -> SimpleNamespace:
    return SimpleNamespace(
        taste_tags=[], resolved_items=[], unresolved_items=[],
        expansion_call_ids={}, candidates_by_domain={}, ranked=[], rejected=[],
        taste_call_id=None, calls_made=0,
    )


class TestContextAwareQuestions:
    def test_q0_frames_creator_context_and_says_it_makes_no_call(self) -> None:
        _final, inv = _demo_investigation()
        q0 = inv["questions"][0]
        assert q0["id"] == "q0"
        assert q0["tool"] == "context_framing"
        assert "no API call" in q0["operation"]
        assert q0["evidence_refs"] == []  # claims no evidence it did not gather
        # The demo run supplies genre + references; q0 must name them.
        assert "genre" in q0["summary"] or "themes" in q0["summary"]

    def test_q0_absent_when_creator_supplied_only_a_title(self) -> None:
        inv = build_investigation(
            _empty_state(),
            film={"title": "Untitled"}, seeds=["solo theme"],
            bet=None, test_card=None, data_status="measured",
        )
        assert all(q["id"] != "q0" for q in inv["questions"])

    def test_q0_names_missing_context_as_a_weakness(self) -> None:
        inv = build_investigation(
            _empty_state(),
            film={"title": "T", "genre": "drama"}, seeds=["T", "ref-a"],
            bet=None, test_card=None, data_status="measured",
        )
        q0 = next(q for q in inv["questions"] if q["id"] == "q0")
        assert "Not supplied" in q0["summary"]
        assert "logline" in q0["summary"]  # logline was not provided

    def test_q5_asked_only_when_top_two_worlds_are_near_tied(self) -> None:
        state = _empty_state()
        state.ranked = [
            _cohort("urn:entity:film", 0.50, "run-c010", 6, 4),
            _cohort("urn:entity:music", 0.49, "run-c011", 6, 4),
        ]
        inv = build_investigation(
            state, film={"title": "T"}, seeds=["T"],
            bet=None, test_card=None, data_status="measured",
        )
        q5 = next(q for q in inv["questions"] if q["id"] == "q5")
        assert q5["status"] == "insufficient"  # affinity cannot break the tie
        assert "0.03" in q5["summary"]
        assert "run-c011" in q5["evidence_refs"]

    def test_q5_absent_when_gap_is_decisive(self) -> None:
        state = _empty_state()
        state.ranked = [
            _cohort("urn:entity:film", 0.62, "run-c010", 6, 4),
            _cohort("urn:entity:music", 0.40, "run-c011", 6, 4),
        ]
        inv = build_investigation(
            state, film={"title": "T"}, seeds=["T"],
            bet=None, test_card=None, data_status="measured",
        )
        assert all(q["id"] != "q5" for q in inv["questions"])

    def test_q6_flags_narrow_qualifying_breadth(self) -> None:
        state = _empty_state()
        state.ranked = [_cohort("urn:entity:film", 0.55, "run-c010", 10, 2)]
        inv = build_investigation(
            state, film={"title": "T"}, seeds=["T"],
            bet=None, test_card=None, data_status="measured",
        )
        q6 = next(q for q in inv["questions"] if q["id"] == "q6")
        assert q6["status"] == "answered"
        assert "2 of 10" in q6["summary"]

    def test_q6_absent_when_breadth_is_healthy(self) -> None:
        state = _empty_state()
        state.ranked = [_cohort("urn:entity:film", 0.55, "run-c010", 10, 7)]
        inv = build_investigation(
            state, film={"title": "T"}, seeds=["T"],
            bet=None, test_card=None, data_status="measured",
        )
        assert all(q["id"] != "q6" for q in inv["questions"])


class TestTypedClaims:
    def test_every_finding_carries_a_claim_type(self) -> None:
        _final, inv = _demo_investigation()
        assert inv["findings"], "demo investigation must produce findings"
        for finding in inv["findings"]:
            assert finding["claim_type"] in CLAIM_TYPES

    def test_open_questions_surface_as_unknown_findings(self) -> None:
        _final, inv = _demo_investigation()
        unknowns = [f for f in inv["findings"] if f["claim_type"] == "UNKNOWN"]
        assert {f["statement"] for f in unknowns} == set(inv["open_questions"])
        assert all(f["evidence_refs"] == [] for f in unknowns)  # unknowns cite nothing

    def test_no_fact_claims_without_evidence(self) -> None:
        inv = build_investigation(
            _empty_state(),
            film={"title": "T"}, seeds=["T"],
            bet=None, test_card=None, data_status="measured",
        )
        assert not [f for f in inv["findings"] if f["claim_type"] == "FACT"]
        assert inv["findings"]  # …but the unknowns are still stated honestly


class TestHypothesisQuality:
    def test_primary_hypothesis_states_assumptions_and_distinguishing_evidence(self) -> None:
        _final, inv = _demo_investigation()
        primary = inv["hypotheses"]["primary"]
        assert primary is not None
        assert primary["statement"] and primary["falsification"]
        assert primary["evidence_refs"], "primary hypothesis must cite real calls"
        assert len(primary["assumptions"]) >= 2
        alts = inv["hypotheses"]["alternatives"]
        if alts:
            # Distinguishing evidence must name the actual runner-up world.
            assert alts[0]["world"] in primary["distinguishing_evidence"]
        else:
            assert "framing" in primary["distinguishing_evidence"]
        for alt in alts:
            assert alt["statement"] and alt["world"]
        for rejected in inv["hypotheses"]["rejected_worlds"]:
            assert rejected["reason"]

    def test_insufficient_evidence_never_yields_a_forced_recommendation(self) -> None:
        inv = build_investigation(
            _empty_state(),
            film={"title": "T"}, seeds=["T"],
            bet=None, test_card=None, data_status="measured",
        )
        assert inv["hypotheses"]["primary"] is None
        assert inv["experiment"] is None
        assert any("No experiment is proposed" in oq for oq in inv["open_questions"])


class TestEvidenceRefVerification:
    def test_dangling_refs_are_removed_and_reported(self) -> None:
        inv = {
            "questions": [{"evidence_refs": ["run-c001", "ghost-c999"]}],
            "findings": [{"evidence_refs": ["ghost-c998"]}],
            "hypotheses": {
                "primary": {"evidence_refs": ["run-c002", "ghost-c997"]},
                "alternatives": [{"evidence_refs": ["ghost-c996"]}],
            },
            "provenance": {"call_ids": ["run-c001", "run-c002", "ghost-c995"]},
            "limitations": [],
        }
        cleaned, dropped = verify_evidence_refs(inv, {"run-c001", "run-c002"})
        assert cleaned["questions"][0]["evidence_refs"] == ["run-c001"]
        assert cleaned["findings"][0]["evidence_refs"] == []
        assert cleaned["hypotheses"]["primary"]["evidence_refs"] == ["run-c002"]
        assert cleaned["hypotheses"]["alternatives"][0]["evidence_refs"] == []
        assert cleaned["provenance"]["call_ids"] == ["run-c001", "run-c002"]
        # ghost-c995 sits only in provenance.call_ids (a derived list, not a
        # claim) — it is filtered out but not counted as a dropped citation.
        assert set(dropped) == {"ghost-c996", "ghost-c997", "ghost-c998", "ghost-c999"}
        assert any("could not be resolved" in lim for lim in cleaned["limitations"])

    def test_clean_investigation_is_untouched(self) -> None:
        inv = {
            "questions": [{"evidence_refs": ["run-c001"]}],
            "findings": [],
            "hypotheses": {"primary": None, "alternatives": []},
            "provenance": {"call_ids": ["run-c001"]},
            "limitations": [],
        }
        cleaned, dropped = verify_evidence_refs(inv, {"run-c001"})
        assert dropped == []
        assert cleaned["limitations"] == []

    def test_api_investigation_refs_resolve_to_recorded_calls(self) -> None:
        final, inv = _demo_investigation()
        recorded = {row.get("call_id") for row in final.get("trace", []) if row.get("call_id")}
        assert recorded, "demo run must record API calls"
        for question in inv["questions"]:
            for ref in question["evidence_refs"]:
                assert ref in recorded, f"dangling question ref {ref}"
        for ref in inv["provenance"]["call_ids"]:
            assert ref in recorded
        assert inv["investigation_id"]


class TestGeographyHonesty:
    def test_sparse_heatmap_is_insufficient_not_absence(self) -> None:
        state = _empty_state()
        geo = SimpleNamespace(sufficient=False, call_id="geo-c001", total_cells=2,
                              city_display="Kolkata")
        inv = build_investigation(
            state, film={"title": "T"}, seeds=["T"],
            bet=None, test_card=None, geography=geo, city="Kolkata",
            data_status="measured",
        )
        q4 = next(q for q in inv["questions"] if q["id"] == "q4")
        assert q4["status"] == "insufficient"
        assert "not as absence of audience" in q4["summary"]
        assert any("Kolkata" in oq for oq in inv["open_questions"])

    def test_missing_heatmap_call_is_unavailable_not_zero(self) -> None:
        state = _empty_state()
        inv = build_investigation(
            state, film={"title": "T"}, seeds=["T"],
            bet=None, test_card=None, geography=None, city="Kolkata",
            data_status="measured",
        )
        q4 = next(q for q in inv["questions"] if q["id"] == "q4")
        assert q4["status"] == "unavailable"
        assert q4["evidence_refs"] == []
