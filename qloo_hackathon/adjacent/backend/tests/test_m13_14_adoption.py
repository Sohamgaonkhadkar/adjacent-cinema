"""M13.14 regressions: structured experiment proposals, explicit adoption,
and immutable synthesis snapshots in saved-decision provenance.

Layer guarantees under test:
- Layer A (investigation) is never mutated by synthesis or adoption.
- Layer B (Decision Brief) proposes; invalid proposals cannot masquerade as
  valid experiments; fallback proposals are consistent with abstention.
- Layer C (saved decision) keeps the model's ORIGINAL proposal distinct from
  the creator's saved (possibly edited) fields, survives replay unchanged,
  and stores only sanitised, ref-verified snapshot data.
"""

from __future__ import annotations

import json
import time
from copy import deepcopy
from typing import Any

from app.domain.llm_provider import StubSynthesisProvider
from app.domain.synthesis import (
    deterministic_fallback,
    synthesize_investigation,
    validate_synthesis,
)
from app.main import app
from fastapi.testclient import TestClient

TERMINAL = {"completed", "failed", "insufficient"}

TEST_PROPOSAL = {
    "kind": "test",
    "hypothesis": "An audience aligned with the film world is reachable.",
    "action_plan": "Post with the film-world framing.",
    "success_criteria": "Responses reference the named world.",
    "observation_window": "Four weeks.",
    "falsification": "No responses reference the framing.",
    "relevant_metrics": ["responses referencing the named world"],
    "assumptions": [],
    "limitations": "",
}

INFO_PROPOSAL = {
    "kind": "information_gathering",
    "hypothesis": "",
    "action_plan": "Collect more resolvable seed references and re-run.",
    "success_criteria": "",
    "observation_window": "",
    "falsification": "",
    "relevant_metrics": ["resolved seed count"],
    "assumptions": [],
    "limitations": "No supported hypothesis yet.",
}

GOOD_CLAIMS = [
    {"statement": "Taste profile returned tags.", "claim_type": "FACT",
     "evidence_refs": ["run-c001"], "rationale": "", "limitations": ""},
    {"statement": "Whether reach changes is unresolved.", "claim_type": "UNKNOWN",
     "evidence_refs": [], "rationale": "", "limitations": ""},
]

INVESTIGATION: dict[str, Any] = {
    "investigation_id": "inv-14",
    "film": {"title": "T"},
    "questions": [{"id": "q1", "evidence_refs": ["run-c001"]}],
    "findings": [
        {"claim_type": "FACT", "statement": "Taste profile returned tags.",
         "evidence_refs": ["run-c001"]},
    ],
    "hypotheses": {
        "primary": {"statement": "Reachable with framing.", "evidence_refs": ["run-c001"],
                    "supporting_evidence": "affinity", "assumptions": ["seeds represent the film"]},
        "alternatives": [],
    },
    "experiment": {
        "title": "Framing test",
        "action_plan": "Post with the film-world framing.",
        "success_criteria": "Responses reference the named world.",
        "observation_window": "Four weeks.",
        "falsification": "No responses reference the framing.",
    },
    "limitations": ["Fixture data."],
    "open_questions": ["Whether reach changes."],
    "data_status": "fixture",
    "provenance": {"call_ids": ["run-c001"]},
}

ABSTAINING: dict[str, Any] = {
    **deepcopy(INVESTIGATION),
    "hypotheses": {"primary": None, "alternatives": []},
    "experiment": None,
    "findings": [],
}


def payload(proposal: dict, claims: list[dict] | None = None, **overrides) -> dict:
    base = {
        "summary": "Evidence favours the film world.",
        "hypothesis_restated": "Reachable with framing.",
        "rationale": "Affinity evidence.",
        "alternatives": [],
        "next_experiment": "Test the framing.",
        "caveats": ["Fixture data."],
        "claims": deepcopy(GOOD_CLAIMS if claims is None else claims),
        "experiment_proposal": deepcopy(proposal),
    }
    base.update(overrides)
    return base


class TestProposalValidation:
    def test_valid_test_proposal_accepted(self) -> None:
        assert validate_synthesis(payload(TEST_PROPOSAL), INVESTIGATION) == []

    def test_test_proposal_missing_field_rejected(self) -> None:
        broken = deepcopy(TEST_PROPOSAL)
        broken["success_criteria"] = "   "
        issues = validate_synthesis(payload(broken), INVESTIGATION)
        assert any("success_criteria" in i for i in issues)

    def test_empty_relevant_metrics_rejected(self) -> None:
        broken = deepcopy(TEST_PROPOSAL)
        broken["relevant_metrics"] = []
        assert any("relevant_metrics" in i for i in validate_synthesis(payload(broken), INVESTIGATION))

    def test_oversized_metrics_list_rejected(self) -> None:
        broken = deepcopy(TEST_PROPOSAL)
        broken["relevant_metrics"] = [f"m{i}" for i in range(9)]
        assert any("exceeds 8" in i for i in validate_synthesis(payload(broken), INVESTIGATION))

    def test_invalid_kind_rejected(self) -> None:
        broken = deepcopy(TEST_PROPOSAL)
        broken["kind"] = "guaranteed_winner"
        assert any("kind must be one of" in i for i in validate_synthesis(payload(broken), INVESTIGATION))

    def test_test_proposal_rejected_when_investigation_abstained(self) -> None:
        p = payload(
            TEST_PROPOSAL,
            hypothesis_restated="No hypothesis was supported by the evidence.",
        )
        issues = validate_synthesis(p, ABSTAINING)
        assert any("'test' contradicts the investigation" in i for i in issues)

    def test_information_gathering_accepted_when_abstained(self) -> None:
        p = payload(
            INFO_PROPOSAL,
            claims=[{"statement": "Nothing supported.", "claim_type": "UNKNOWN",
                     "evidence_refs": [], "rationale": "", "limitations": ""}],
            hypothesis_restated="No hypothesis was supported by the evidence.",
        )
        assert validate_synthesis(p, ABSTAINING) == []

    def test_information_gathering_needs_an_action(self) -> None:
        broken = deepcopy(INFO_PROPOSAL)
        broken["action_plan"] = ""
        assert any("what information to collect" in i for i in validate_synthesis(payload(broken), ABSTAINING))

    def test_v2_0_payload_without_proposal_is_rejected_not_adopted(self) -> None:
        v20 = payload(TEST_PROPOSAL)
        del v20["experiment_proposal"]
        assert validate_synthesis(v20, INVESTIGATION) == ["missing key: experiment_proposal"]
        outcome = synthesize_investigation(deepcopy(INVESTIGATION), StubSynthesisProvider(v20))
        assert outcome["metadata"]["method"] == "deterministic_fallback"


class TestFallbackProposals:
    def test_fallback_test_proposal_mirrors_the_investigation_experiment(self) -> None:
        fb = deterministic_fallback(deepcopy(INVESTIGATION), "boom")
        prop = fb["experiment_proposal"]
        assert prop["kind"] == "test"
        assert prop["action_plan"] == INVESTIGATION["experiment"]["action_plan"]
        assert prop["success_criteria"] == INVESTIGATION["experiment"]["success_criteria"]
        assert prop["falsification"] == INVESTIGATION["experiment"]["falsification"]
        assert prop["relevant_metrics"]
        check = {k: v for k, v in fb.items() if not k.startswith("_")}
        assert validate_synthesis(check, INVESTIGATION) == []

    def test_fallback_abstains_honestly_when_investigation_abstained(self) -> None:
        fb = deterministic_fallback(deepcopy(ABSTAINING), "boom")
        prop = fb["experiment_proposal"]
        assert prop["kind"] == "information_gathering"
        assert prop["hypothesis"] == ""  # no confident positioning invented
        assert "not a positioning experiment" in prop["limitations"] or \
               "information-gathering" in prop["limitations"]
        check = {k: v for k, v in fb.items() if not k.startswith("_")}
        assert validate_synthesis(check, ABSTAINING) == []


# ---------------------------------------------------------------------------
# Layer C: adoption through the real API
# ---------------------------------------------------------------------------


def _demo(client: TestClient) -> tuple[str, dict]:
    run_id = client.post("/creator/run/demo").json()["run_id"]
    deadline = time.time() + 30.0
    while time.time() < deadline:
        record = client.get(f"/run/{run_id}").json()
        if record.get("status") in TERMINAL:
            return run_id, record
        time.sleep(0.05)
    raise AssertionError("demo run never terminal")


def _prov(experiment: dict) -> dict:
    raw = experiment.get("provenance")
    return json.loads(raw) if isinstance(raw, str) else (raw or {})


def _save_body(run_id: str, refs: list[str], inv_id: str, **overrides) -> dict:
    body = {
        "request_id": f"m1314-{run_id}",
        "film_title": "Demo Film",
        "hypothesis": "CREATOR-EDITED hypothesis wording.",
        "success_criteria": "Responses reference the named world.",
        "observation_window": "Four weeks.",
        "action_plan": "Post with the film-world framing.",
        "data_status": "fixture",
        "source_run_id": run_id,
        "synthesis_snapshot": {
            "investigation_id": inv_id,
            "source_run_id": run_id,
            "schema_version": "2.1",
            "method": "stub",
            "provider_kind": "stub",
            "model": "deterministic-test-stub",
            "validation": "passed",
            "summary": "Evidence favours the film world.",
            "hypothesis_restated": "Reachable with framing.",
            "claims": [
                {"statement": "Taste profile returned tags.", "claim_type": "FACT",
                 "evidence_refs": [refs[0]], "rationale": "", "limitations": ""},
                {"statement": "Dangling claim.", "claim_type": "FACT",
                 "evidence_refs": ["ghost-c999"], "rationale": "", "limitations": ""},
            ],
            "caveats": ["Fixture data."],
            "limitations": ["Fixture data."],
            "evidence_refs": [refs[0], "ghost-c998"],
            "data_status": "fixture",
            "experiment_proposal": deepcopy(TEST_PROPOSAL),
            # must be stripped by the allowlist:
            "api_key": "SECRET-CANARY-1234567890",
            "internal_dump": {"anything": "dropped"},
        },
        "adopted_proposal": {
            **deepcopy(TEST_PROPOSAL),
            "hypothesis": "An audience aligned with the film world is reachable.",
        },
    }
    body.update(overrides)
    return body


class TestAdoptionPersistence:
    def test_snapshot_saved_sanitised_and_ref_verified(self) -> None:
        client = TestClient(app)
        run_id, record = _demo(client)
        refs = record["result"]["investigation"]["provenance"]["call_ids"]
        resp = client.post("/experiments", json=_save_body(run_id, refs, "inv-14"))
        assert resp.status_code == 201
        prov = _prov(resp.json()["experiment"])
        snap = prov["synthesis_snapshot"]
        # sanitised: allowlist only, no credential-shaped keys anywhere
        assert "api_key" not in snap and "internal_dump" not in snap
        assert "SECRET-CANARY" not in json.dumps(prov)
        # refs verified against the source run's recorded trace
        assert snap["evidence_ref_status"] == "verified against source run trace"
        assert snap["evidence_refs"] == [refs[0]]
        assert set(snap["unresolved_evidence_refs"]) == {"ghost-c998", "ghost-c999"}
        assert snap["claims"][0]["evidence_refs"] == [refs[0]]
        assert snap["claims"][1]["evidence_refs"] == []
        # fixture provenance survives
        assert snap["data_status"] == "fixture"

    def test_creator_edits_are_attributable(self) -> None:
        client = TestClient(app)
        run_id, record = _demo(client)
        refs = record["result"]["investigation"]["provenance"]["call_ids"]
        resp = client.post("/experiments", json=_save_body(run_id, refs, "inv-14"))
        prov = _prov(resp.json()["experiment"])
        # saved hypothesis differs from the model's original proposal
        assert prov["creator_edits"] == ["hypothesis"]
        assert prov["adopted_proposal"]["hypothesis"].startswith("An audience aligned")
        assert prov["adoption"] == {"origin": "model_proposal", "method": "stub"}

    def test_replay_is_idempotent_and_snapshot_immutable(self) -> None:
        client = TestClient(app)
        run_id, record = _demo(client)
        refs = record["result"]["investigation"]["provenance"]["call_ids"]
        body = _save_body(run_id, refs, "inv-14")
        first = client.post("/experiments", json=body).json()["experiment"]
        # replay with a DIFFERENT (would-be-edited) snapshot must not mutate
        body2 = deepcopy(body)
        body2["request_id"] = f"m1314-{run_id}-retry"
        body2["synthesis_snapshot"]["summary"] = "TAMPERED"
        second = client.post("/experiments", json=body2).json()
        assert second["duplicate"] is True
        assert second["experiment"]["experiment_id"] == first["experiment_id"]
        assert _prov(second["experiment"])["synthesis_snapshot"]["summary"] != "TAMPERED"

    def test_investigation_unchanged_by_adoption(self) -> None:
        client = TestClient(app)
        run_id, record = _demo(client)
        before = record["result"]["investigation"]
        refs = before["provenance"]["call_ids"]
        client.post("/experiments", json=_save_body(run_id, refs, "inv-14"))
        after = client.get(f"/run/{run_id}").json()["result"]["investigation"]
        assert after == before  # Layer A is immutable

    def test_snapshot_without_source_run_is_marked_unverified(self) -> None:
        client = TestClient(app)
        body = _save_body("no-run", ["run-c001"], "inv-14")
        body["request_id"] = "m1314-unverified-1"
        body["source_run_id"] = None
        resp = client.post("/experiments", json=body)
        assert resp.status_code == 201
        snap = _prov(resp.json()["experiment"])["synthesis_snapshot"]
        assert snap["evidence_ref_status"].startswith("unverified")
        # without a source run nothing can be verified — refs are kept but
        # the whole snapshot is explicitly labelled unverified
        assert snap["evidence_refs"] == ["run-c001", "ghost-c998"]
        assert "unresolved_evidence_refs" not in snap

    def test_information_gathering_adoption_is_honest(self) -> None:
        client = TestClient(app)
        run_id, record = _demo(client)
        refs = record["result"]["investigation"]["provenance"]["call_ids"]
        body = _save_body(run_id, refs, "inv-14")
        body["request_id"] = f"m1314-ig-{run_id}"
        body["source_run_id"] = None  # avoid per-run dedupe with the other saves
        body["hypothesis"] = "No supported hypothesis yet — information-gathering step."
        body["action_plan"] = INFO_PROPOSAL["action_plan"]
        body["success_criteria"] = ""
        body["observation_window"] = ""
        body["synthesis_snapshot"]["experiment_proposal"] = deepcopy(INFO_PROPOSAL)
        body["adopted_proposal"] = deepcopy(INFO_PROPOSAL)
        resp = client.post("/experiments", json=body)
        assert resp.status_code == 201
        exp = resp.json()["experiment"]
        assert "information-gathering" in exp["hypothesis"]
        prov = _prov(exp)
        assert prov["synthesis_snapshot"]["experiment_proposal"]["kind"] == "information_gathering"
        assert prov["adopted_proposal"]["kind"] == "information_gathering"
        # only the hypothesis text differs (repository requires non-empty) —
        # and that difference is attributed to the creator, not the model.
        assert prov["creator_edits"] == ["hypothesis"]
