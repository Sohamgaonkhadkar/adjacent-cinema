"""M13.13 regressions: claim-level grounding, adversarial overclaiming,
abstention honesty, provider bounds, and evaluation rubric v3.

All deterministic and offline (labelled stub providers only).
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.domain.llm_provider import (
    LLMProviderConfig,
    LLMUnavailableError,
    OpenAICompatibleProvider,
    StubSynthesisProvider,
)
from app.domain.synthesis import (
    GUARANTEES,
    MAX_CLAIMS,
    deterministic_fallback,
    synthesize_investigation,
    validate_synthesis,
)

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "research" / "scripts"))

from m13_11_qloo_vs_llm import (
    BRIEFS,
    RUBRIC_VERSION,
    run_comparison,
    score_output,
)

INVESTIGATION: dict[str, Any] = {
    "investigation_id": "inv-13",
    "film": {"title": "Neon Harbour", "genre": "urban drama"},
    "questions": [{"id": "q1", "evidence_refs": ["run-c001"]}],
    "findings": [
        {"claim_type": "FACT", "statement": "Taste profile returned 12 tags.",
         "evidence_refs": ["run-c001"]},
        {"claim_type": "UNKNOWN", "statement": "Whether framing changes reach.",
         "evidence_refs": []},
    ],
    "hypotheses": {
        "primary": {
            "statement": "An audience aligned with the urn:entity:movie world is reachable.",
            "evidence_refs": ["run-c001"],
            "supporting_evidence": "Measured affinity.",
        },
        "alternatives": [
            {"statement": "Alternative world.", "evidence_refs": ["run-c002"]},
        ],
    },
    "experiment": {
        "title": "Framing test",
        "action_plan": "Post with the film-world framing.",
        "success_criteria": "Responses reference the named world.",
        "observation_window": "Four weeks.",
        "falsification": "No responses reference the framing.",
    },
    "limitations": ["Fixture demonstration data."],
    "open_questions": ["Whether framing changes reach."],
    "data_status": "fixture",
    "provenance": {"call_ids": ["run-c001", "run-c002"]},
}

ABSTAINING: dict[str, Any] = {
    **deepcopy(INVESTIGATION),
    "hypotheses": {"primary": None, "alternatives": []},
    "experiment": None,
    "findings": [
        {"claim_type": "UNKNOWN", "statement": "Nothing is supported.", "evidence_refs": []},
    ],
}


def claim(statement: str, ctype: str, refs: list[str] | None = None, **kw) -> dict:
    return {
        "statement": statement,
        "claim_type": ctype,
        "evidence_refs": refs if refs is not None else [],
        "rationale": kw.get("rationale", ""),
        "limitations": kw.get("limitations", ""),
    }


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


def payload(claims: list[dict], **overrides) -> dict:
    base = {
        "summary": "The measured evidence favours the film world (run-c001).",
        "hypothesis_restated": "An audience aligned with the film world may be reachable.",
        "rationale": "Affinity evidence supports the film world.",
        "alternatives": [],
        "next_experiment": "Test the framing and record references.",
        "caveats": ["Fixture data."],
        "claims": claims,
        "experiment_proposal": deepcopy(TEST_PROPOSAL),
    }
    base.update(overrides)
    return base


GOOD_CLAIMS = [
    claim("Taste profile returned 12 tags.", "FACT", ["run-c001"]),
    claim("The film world is the strongest target.", "INTERPRETATION", ["run-c001"]),
    claim("Reachable with naming framing.", "HYPOTHESIS", ["run-c001"]),
    claim("Whether reach changes is unresolved.", "UNKNOWN"),
]


class TestClaimLevelGrounding:
    def test_valid_structured_claims_pass(self) -> None:
        assert validate_synthesis(payload(deepcopy(GOOD_CLAIMS)), INVESTIGATION) == []

    def test_fact_without_refs_is_rejected(self) -> None:
        issues = validate_synthesis(
            payload([claim("The profile returned tags.", "FACT")]), INVESTIGATION
        )
        assert any("FACT claim without evidence refs" in i for i in issues)

    def test_fact_with_dangling_ref_is_rejected(self) -> None:
        issues = validate_synthesis(
            payload([claim("A fact.", "FACT", ["run-c999"])]), INVESTIGATION
        )
        assert any("do not exist" in i for i in issues)

    def test_unknown_claim_must_not_cite_refs(self) -> None:
        issues = validate_synthesis(
            payload([claim("Unresolved.", "UNKNOWN", ["run-c001"])]), INVESTIGATION
        )
        assert any("UNKNOWN claim must not cite" in i for i in issues)

    def test_interpretation_must_rest_on_facts_when_facts_exist(self) -> None:
        issues = validate_synthesis(
            payload([claim("The world feels right.", "INTERPRETATION")]), INVESTIGATION
        )
        assert any("INTERPRETATION claim cites nothing" in i for i in issues)

    def test_interpretation_needs_no_refs_when_no_facts_exist(self) -> None:
        thin = deepcopy(ABSTAINING)  # no FACT findings, abstained
        p = payload(
            [claim("Nothing can be interpreted yet.", "INTERPRETATION")],
            hypothesis_restated="No hypothesis was supported by the evidence.",
            experiment_proposal=deepcopy(INFO_PROPOSAL),
        )
        assert not any("INTERPRETATION" in i for i in validate_synthesis(p, thin))

    def test_invalid_claim_type_is_rejected(self) -> None:
        issues = validate_synthesis(
            payload([claim("Something.", "OPINION")]), INVESTIGATION
        )
        assert any("claim_type must be one of" in i for i in issues)

    def test_empty_claims_rejected(self) -> None:
        assert any("must not be empty" in i for i in validate_synthesis(payload([]), INVESTIGATION))

    def test_too_many_claims_rejected(self) -> None:
        claims = [claim(f"Fact {i}.", "FACT", ["run-c001"]) for i in range(MAX_CLAIMS + 1)]
        assert any("exceeds" in i for i in validate_synthesis(payload(claims), INVESTIGATION))

    def test_unsupported_urn_entity_is_rejected(self) -> None:
        issues = validate_synthesis(
            payload([claim("Fans of urn:entity:videogame overlap.", "INTERPRETATION", ["run-c001"])]),
            INVESTIGATION,
        )
        assert any("unsupported entity identifier urn:entity:videogame" in i for i in issues)

    def test_entity_present_in_investigation_is_accepted(self) -> None:
        issues = validate_synthesis(
            payload([claim("The urn:entity:movie world is strongest.", "INTERPRETATION", ["run-c001"])]),
            INVESTIGATION,
        )
        assert not any("unsupported entity" in i for i in issues)

    def test_oversized_claim_statement_rejected(self) -> None:
        issues = validate_synthesis(
            payload([claim("x" * 601, "FACT", ["run-c001"])]), INVESTIGATION
        )
        assert any("exceeds 600" in i for i in issues)


class TestInsufficiencyContradiction:
    def test_hypothesis_claim_rejected_when_investigation_abstained(self) -> None:
        p = payload(
            [claim("An audience is reachable.", "HYPOTHESIS")],
            hypothesis_restated="No hypothesis was supported by the evidence.",
            experiment_proposal=deepcopy(INFO_PROPOSAL),
        )
        issues = validate_synthesis(p, ABSTAINING)
        assert any("contradicts the investigation" in i for i in issues)

    def test_confident_restatement_rejected_when_investigation_abstained(self) -> None:
        p = payload(
            [claim("Nothing is supported yet.", "UNKNOWN")],
            hypothesis_restated="Position toward the film world and it will resonate.",
            experiment_proposal=deepcopy(INFO_PROPOSAL),
        )
        issues = validate_synthesis(p, ABSTAINING)
        assert any("restates a hypothesis" in i for i in issues)

    def test_honest_abstaining_brief_is_accepted(self) -> None:
        p = payload(
            [claim("Nothing is supported yet.", "UNKNOWN")],
            hypothesis_restated="No hypothesis was supported by the available evidence.",
            next_experiment="Collect more seed references before testing any framing.",
            experiment_proposal=deepcopy(INFO_PROPOSAL),
        )
        assert validate_synthesis(p, ABSTAINING) == []

    def test_test_proposal_rejected_when_investigation_abstained(self) -> None:
        p = payload(
            [claim("Nothing is supported yet.", "UNKNOWN")],
            hypothesis_restated="No hypothesis was supported by the available evidence.",
            experiment_proposal=deepcopy(TEST_PROPOSAL),
        )
        issues = validate_synthesis(p, ABSTAINING)
        assert any("contradicts the investigation" in i and "information_gathering" in i for i in issues)


class TestAdversarialOverclaims:
    @pytest.mark.parametrize(
        "text",
        [
            "This positioning will go viral with port-city audiences.",
            "We guarantee the film finds its audience.",
            "It will reach 500k views within a month.",
            "The data predicts strong retention.",
            "This framing causes growth in views.",
        ],
    )
    def test_overclaims_rejected_wherever_they_appear(self, text: str) -> None:
        p = payload(deepcopy(GOOD_CLAIMS))
        p["claims"][1]["rationale"] = text  # hidden inside a claim, not the summary
        issues = validate_synthesis(p, INVESTIGATION)
        assert any("forbidden claim pattern" in i for i in issues), text

    def test_v1_payload_without_claims_is_rejected_not_silently_accepted(self) -> None:
        v1 = payload(deepcopy(GOOD_CLAIMS))
        del v1["claims"]
        issues = validate_synthesis(v1, INVESTIGATION)
        assert issues == ["missing key: claims"]
        outcome = synthesize_investigation(
            deepcopy(INVESTIGATION), StubSynthesisProvider(v1)
        )
        assert outcome["metadata"]["method"] == "deterministic_fallback"

    def test_guarantees_metadata_is_honest(self) -> None:
        assert GUARANTEES["reference_integrity"].startswith("checked")
        assert GUARANTEES["semantic_support"].startswith("NOT guaranteed")
        outcome = synthesize_investigation(
            deepcopy(INVESTIGATION), StubSynthesisProvider(payload(deepcopy(GOOD_CLAIMS)))
        )
        assert outcome["metadata"]["guarantees"] == GUARANTEES


class TestFallbackStructure:
    def test_fallback_emits_structured_claims_with_correct_types(self) -> None:
        fb = deterministic_fallback(deepcopy(INVESTIGATION), "boom")
        types = {c["claim_type"] for c in fb["claims"]}
        assert "FACT" in types and "HYPOTHESIS" in types and "UNKNOWN" in types
        for c in fb["claims"]:
            if c["claim_type"] == "FACT":
                assert c["evidence_refs"]
            if c["claim_type"] == "UNKNOWN":
                assert c["evidence_refs"] == []
        # The fallback itself passes the validator (contract identical).
        check = {k: v for k, v in fb.items() if not k.startswith("_")}
        assert validate_synthesis(check, INVESTIGATION) == []

    def test_fallback_on_abstaining_investigation_passes_validator(self) -> None:
        fb = deterministic_fallback(deepcopy(ABSTAINING), "boom")
        check = {k: v for k, v in fb.items() if not k.startswith("_")}
        assert validate_synthesis(check, ABSTAINING) == []
        assert not any(c["claim_type"] == "HYPOTHESIS" for c in fb["claims"])


class TestProviderBounds:
    def test_oversized_provider_response_raises(self) -> None:
        huge = {"choices": [{"message": {"content": "x" * 150_000}}]}

        class HugeTransport(httpx.BaseTransport):
            def handle_request(self, request):
                return httpx.Response(200, json=huge)

        provider = OpenAICompatibleProvider(
            LLMProviderConfig(api_key="TEST-KEY-CANARY"), transport=HugeTransport()
        )
        with pytest.raises(LLMUnavailableError, match="char bound"):
            provider.complete("s", "u")

    def test_oversized_response_becomes_labelled_fallback(self) -> None:
        class BoomProvider:
            kind = "live_llm"
            model = "test"

            def complete(self, system: str, user: str) -> str:
                raise LLMUnavailableError("provider response exceeds 100000-char bound")

        outcome = synthesize_investigation(deepcopy(INVESTIGATION), BoomProvider())
        assert outcome["metadata"]["method"] == "deterministic_fallback"
        assert "char bound" in outcome["metadata"]["llm_error"]


class TestRubricV3:
    def test_version_and_abstention_category_exist(self) -> None:
        assert RUBRIC_VERSION == "3.0"
        thin = next(b for b in BRIEFS if b["fixture"] == "insufficient_evidence")
        comparison = run_comparison(briefs=[thin])
        run = comparison["runs"][0]
        scores = run["scores"]
        assert scores["decision_quality"]["applicable"] is False
        assert "abstention_quality" in scores["categories_applicable"]
        abst = scores["abstention_quality"]["checks"]
        assert abst["recognizes_insufficiency"]["score"] == 1
        assert abst["no_forced_hypothesis"]["score"] == 1
        assert abst["avoids_unsupported_facts"]["score"] == 1

    def test_positioning_output_is_not_abstention_scored(self) -> None:
        strong = next(b for b in BRIEFS if b["fixture"] == "portland_strong")
        comparison = run_comparison(briefs=[strong])
        scores = comparison["runs"][0]["scores"]
        assert scores["abstention_quality"] is None
        assert "decision_quality" in scores["categories_applicable"]

    def test_forced_answer_would_not_score_as_good_abstention(self) -> None:
        # A fabricated "abstention" with a complete stop and no explanation
        # must NOT be rewarded — refusal quality is evidence-conditional.
        fake = {
            "condition": "qloo_grounded",
            "positioning": None,
            "stop_reason": "complete",
            "limitations": [],
            "open_questions": [],
            "unsupported_fact_claims": 2,
            "fact_claims": 2,
        }
        scores = score_output(fake)
        abst = scores["abstention_quality"]["checks"]
        assert abst["recognizes_insufficiency"]["score"] == 0
        assert abst["explains_source"]["score"] == 0
        assert abst["avoids_unsupported_facts"]["score"] == 0
        assert abst["identifies_next_info"]["score"] == 0
        assert scores["abstention_quality"]["total"] <= 1  # only the trivial criterion

    def test_run_metadata_records_fixture_and_alignment(self) -> None:
        comparison = run_comparison(briefs=[BRIEFS[0]])
        meta = comparison["runs"][0]["run_metadata"]
        assert meta["fixture"] == "portland_strong"
        assert "NOT Qloo data" in meta["fixture_alignment"]
        assert meta["rubric_version"] == "3.0"

    def test_artefact_json_is_reproducible_and_labelled(self) -> None:
        comparison = run_comparison(briefs=[BRIEFS[0]])
        blob = json.dumps(comparison, default=str)
        assert '"rubric_version": "3.0"' in blob
        assert "abstention_quality" in comparison["rubric_anchors"]
        assert "condition_a_status" in comparison["summary"]
