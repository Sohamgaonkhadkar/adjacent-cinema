"""M13.12 regressions: Role-B synthesis layer.

The synthesis layer is OPTIONAL and bounded: schema-constrained output,
deterministic post-validation, evidence-ref resolution, forbidden-claim
guard, and an explicitly labelled deterministic fallback. Every failure path
must stay honest — a failed model call never masquerades as model output,
and a missing provider is BLOCKED, never silently stubbed.

All tests run offline against the labelled StubSynthesisProvider.
"""

from __future__ import annotations

import time
from copy import deepcopy
from typing import Any

import pytest
from app.api.creator_routes import reset_synthesis_for_tests
from app.domain.llm_provider import (
    LLMProviderConfig,
    LLMUnavailableError,
    OpenAICompatibleProvider,
    StubSynthesisProvider,
)
from app.domain.synthesis import (
    SYNTHESIS_KEYS,
    build_user_prompt,
    collect_evidence_refs,
    deterministic_fallback,
    synthesize_investigation,
    validate_synthesis,
)
from app.main import app
from fastapi.testclient import TestClient

TERMINAL = {"completed", "failed", "insufficient"}

INVESTIGATION: dict[str, Any] = {
    "investigation_id": "inv-test",
    "film": {"title": "Neon Harbour"},
    "seeds": ["Neon Harbour"],
    "questions": [{"id": "q1", "evidence_refs": ["run-c001"]}],
    "findings": [
        {"claim_type": "FACT", "statement": "Taste profile returned 12 tags.",
         "evidence_refs": ["run-c001"]},
        {"claim_type": "UNKNOWN", "statement": "Whether framing changes reach.",
         "evidence_refs": []},
    ],
    "hypotheses": {
        "primary": {
            "statement": "An audience aligned with the film world is reachable.",
            "evidence_refs": ["run-c001"],
            "supporting_evidence": "Measured affinity across expanded candidates.",
            "falsification": "No responses reference the framing.",
        },
        "alternatives": [
            {"statement": "Alternative: the music world.", "evidence_refs": ["run-c002"]},
        ],
    },
    "experiment": {"success_criteria": "Responses reference the named world."},
    "limitations": ["Fixture demonstration data."],
    "open_questions": ["Whether framing changes reach."],
    "data_status": "fixture",
    "provenance": {"call_ids": ["run-c001", "run-c002"]},
}

VALID_PAYLOAD = {
    "summary": "The investigation's strongest measured world is film (run-c001).",
    "hypothesis_restated": "An audience aligned with the film world may be reachable.",
    "rationale": "Affinity evidence (run-c001) supports the film world; similarity, not demand.",
    "alternatives": ["The music world is a grounded runner-up."],
    "next_experiment": "Post with the film-world framing and record references.",
    "caveats": ["Fixture demonstration data."],
    "experiment_proposal": {
        "kind": "test",
        "hypothesis": "An audience aligned with the film world is reachable.",
        "action_plan": "Post with the film-world framing.",
        "success_criteria": "Responses reference the named world.",
        "observation_window": "Four weeks after posting.",
        "falsification": "No responses reference the framing.",
        "relevant_metrics": ["responses referencing the named cultural world"],
        "assumptions": [],
        "limitations": "",
    },
    "claims": [
        {
            "statement": "The taste profile returned 12 interest tags.",
            "claim_type": "FACT",
            "evidence_refs": ["run-c001"],
            "rationale": "Directly recorded by the pipeline call.",
            "limitations": "",
        },
        {
            "statement": "The film world is the most defensible positioning target.",
            "claim_type": "INTERPRETATION",
            "evidence_refs": ["run-c001", "run-c002"],
            "rationale": "Rests on the measured affinity facts.",
            "limitations": "Affinity is similarity, not demand.",
        },
        {
            "statement": "An audience aligned with the film world is reachable with framing that names it.",
            "claim_type": "HYPOTHESIS",
            "evidence_refs": ["run-c001"],
            "rationale": "Proposed positioning decision to test.",
            "limitations": "Not yet established.",
        },
        {
            "statement": "Whether the framing changes reach is unresolved.",
            "claim_type": "UNKNOWN",
            "evidence_refs": [],
            "rationale": "",
            "limitations": "Requires the creator's own post-release observations.",
        },
    ],
}


def valid_stub(real_refs: list[str] | None = None) -> StubSynthesisProvider:
    """Route-test payload. FACT/INTERPRETATION claims cite the DEMO run's
    real refs when given; without refs only ref-free claim types are used
    (fabricated ids would rightly fail the dangling-ref guard)."""
    payload = deepcopy(VALID_PAYLOAD)
    payload["summary"] = "The investigation's strongest measured world is film."
    payload["rationale"] = "Affinity evidence supports the film world; similarity, not demand."
    if real_refs:
        first = real_refs[0]
        payload["claims"][0]["evidence_refs"] = [first]
        payload["claims"][1]["evidence_refs"] = list(real_refs[:2])
        payload["claims"][2]["evidence_refs"] = [first]
    else:
        payload["claims"] = [
            c for c in payload["claims"] if c["claim_type"] in ("HYPOTHESIS", "UNKNOWN")
        ]
        for c in payload["claims"]:
            c["evidence_refs"] = []
    return StubSynthesisProvider(payload)


@pytest.fixture(autouse=True)
def _clear_override():
    yield
    reset_synthesis_for_tests(None)


class TestSynthesisValidation:
    def test_valid_output_passes_and_is_labelled_with_provider_kind(self) -> None:
        # INVESTIGATION's real refs are run-c001/run-c002, so the full
        # ref-citing payload is valid here.
        outcome = synthesize_investigation(
            deepcopy(INVESTIGATION), StubSynthesisProvider(deepcopy(VALID_PAYLOAD))
        )
        assert outcome["metadata"]["method"] == "stub"
        assert outcome["metadata"]["validation"] == "passed"
        assert outcome["synthesis"]["summary"] == VALID_PAYLOAD["summary"]

    def test_malformed_json_falls_back_with_error_recorded(self) -> None:
        outcome = synthesize_investigation(
            deepcopy(INVESTIGATION), StubSynthesisProvider("not json at all")
        )
        assert outcome["metadata"]["method"] == "deterministic_fallback"
        assert "malformed JSON" in (outcome["metadata"]["llm_error"] or "")
        assert "_fallback_error" in outcome["synthesis"]

    def test_missing_schema_key_is_rejected(self) -> None:
        payload = deepcopy(VALID_PAYLOAD)
        del payload["caveats"]
        outcome = synthesize_investigation(deepcopy(INVESTIGATION), StubSynthesisProvider(payload))
        assert outcome["metadata"]["method"] == "deterministic_fallback"
        assert "missing key" in outcome["metadata"]["validation"]

    def test_fabricated_evidence_ref_is_rejected(self) -> None:
        payload = deepcopy(VALID_PAYLOAD)
        payload["rationale"] += " Also supported by run-c999."
        outcome = synthesize_investigation(deepcopy(INVESTIGATION), StubSynthesisProvider(payload))
        assert outcome["metadata"]["method"] == "deterministic_fallback"
        assert "do not exist" in outcome["metadata"]["validation"]
        assert "run-c999" in outcome["metadata"]["validation"]

    def test_real_evidence_ref_is_accepted(self) -> None:
        payload = deepcopy(VALID_PAYLOAD)
        payload["rationale"] += " Cross-checked against run-c002."
        outcome = synthesize_investigation(deepcopy(INVESTIGATION), StubSynthesisProvider(payload))
        assert outcome["metadata"]["validation"] == "passed"

    @pytest.mark.parametrize(
        "text, label",
        [
            ("This will go viral.", "virality"),
            ("We guarantee resonance.", "guarantee"),
            ("It will reach 100k views.", "viewership prediction"),
            ("This causes growth in views.", "causal"),
        ],
    )
    def test_forbidden_claims_are_rejected(self, text: str, label: str) -> None:
        payload = deepcopy(VALID_PAYLOAD)
        payload["summary"] = text
        outcome = synthesize_investigation(deepcopy(INVESTIGATION), StubSynthesisProvider(payload))
        assert outcome["metadata"]["method"] == "deterministic_fallback", label
        assert "forbidden claim pattern" in outcome["metadata"]["validation"]

    def test_oversized_fields_and_lists_are_rejected(self) -> None:
        payload = deepcopy(VALID_PAYLOAD)
        payload["summary"] = "x" * 2001
        payload["caveats"] = ["c"] * 9
        issues = validate_synthesis(payload, INVESTIGATION)
        assert any("exceeds 2000" in i for i in issues)
        assert any("exceeds 8 entries" in i for i in issues)

    def test_provider_failure_yields_labelled_fallback_not_silence(self) -> None:
        outcome = synthesize_investigation(
            deepcopy(INVESTIGATION),
            StubSynthesisProvider(LLMUnavailableError("simulated timeout")),
        )
        assert outcome["metadata"]["method"] == "deterministic_fallback"
        assert "simulated timeout" in outcome["metadata"]["llm_error"]

    def test_fallback_never_fabricates_when_evidence_is_insufficient(self) -> None:
        thin = deepcopy(INVESTIGATION)
        thin["hypotheses"] = {"primary": None, "alternatives": []}
        thin["findings"] = [
            {"claim_type": "UNKNOWN", "statement": "Nothing is supported.", "evidence_refs": []}
        ]
        fallback = deterministic_fallback(thin, "boom")
        assert fallback["hypothesis_restated"] == "No hypothesis was supported by the evidence."
        assert "no factual findings" in fallback["summary"]
        assert fallback["_fallback_error"] == "boom"

    def test_fallback_uses_only_factual_findings_for_the_summary(self) -> None:
        fallback = deterministic_fallback(deepcopy(INVESTIGATION), "boom")
        assert "Taste profile returned 12 tags." in fallback["summary"]
        assert "Whether framing changes reach." not in fallback["summary"]

    def test_prompt_contains_investigation_and_no_credentials(self) -> None:
        prompt = build_user_prompt(INVESTIGATION)
        assert "Neon Harbour" in prompt and "run-c001" in prompt
        lowered = prompt.lower()
        assert "api_key" not in lowered and "authorization" not in lowered


class TestProviderConfig:
    def test_missing_credentials_raise_blocked_error_mentioning_env_var(self, monkeypatch) -> None:
        monkeypatch.delenv("ADJACENT_LLM_API_KEY", raising=False)
        config = LLMProviderConfig.from_env()
        assert not config.configured
        with pytest.raises(LLMUnavailableError) as exc:
            OpenAICompatibleProvider(config)
        assert "ADJACENT_LLM_API_KEY" in str(exc.value)

    def test_redacted_view_never_contains_the_key(self) -> None:
        config = LLMProviderConfig(api_key="SECRET-VALUE", model="m")
        view = config.redacted()
        assert view["api_key_present"] is True
        assert "SECRET-VALUE" not in str(view)


class TestSynthesisRoutes:
    def _demo_run_id(self, client: TestClient, with_refs: bool = False):
        run_id = client.post("/creator/run/demo").json()["run_id"]
        deadline = time.time() + 30.0
        while time.time() < deadline:
            record = client.get(f"/run/{run_id}").json()
            if record.get("status") in TERMINAL:
                if with_refs:
                    refs = record["result"]["investigation"]["provenance"]["call_ids"]
                    return run_id, refs
                return run_id
            time.sleep(0.05)
        raise AssertionError("demo run never terminal")

    def test_status_is_honestly_blocked_without_provider(self, client_env_cleared) -> None:
        client = TestClient(app)
        status = client.get("/creator/synthesis-status").json()
        assert status["available"] is False
        assert "ADJACENT_LLM_API_KEY" in status["blocked_reason"]

    def test_synthesize_404_for_unknown_run(self) -> None:
        client = TestClient(app)
        response = client.post("/creator/synthesize", json={"run_id": "no-such-run"})
        assert response.status_code == 404

    def test_synthesize_503_when_provider_unconfigured(self, monkeypatch) -> None:
        monkeypatch.delenv("ADJACENT_LLM_API_KEY", raising=False)
        client = TestClient(app)
        run_id = self._demo_run_id(client)
        response = client.post("/creator/synthesize", json={"run_id": run_id})
        assert response.status_code == 503
        assert "ADJACENT_LLM_API_KEY" in response.json()["detail"]

    def test_synthesize_with_stub_provider_is_labelled_stub(self) -> None:
        client = TestClient(app)
        run_id, refs = self._demo_run_id(client, with_refs=True)
        reset_synthesis_for_tests(valid_stub(refs))
        response = client.post("/creator/synthesize", json={"run_id": run_id})
        assert response.status_code == 200
        body = response.json()
        assert body["run_id"] == run_id
        assert body["metadata"]["method"] == "stub"
        assert body["metadata"]["model"] == "deterministic-test-stub"
        assert set(body["synthesis"].keys()) == set(SYNTHESIS_KEYS)
        assert body["metadata"]["evidence_refs_available"]
        # M13.13: claim-level structure survives the route, refs resolve.
        claims = body["synthesis"]["claims"]
        assert claims and all(c["claim_type"] in {"FACT", "INTERPRETATION", "HYPOTHESIS", "UNKNOWN"} for c in claims)
        known = set(body["metadata"]["evidence_refs_available"])
        for claim in claims:
            assert all(r in known for r in claim["evidence_refs"])
        assert body["metadata"]["guarantees"]["semantic_support"].startswith("NOT guaranteed")

    def test_synthesize_reports_fallback_when_model_output_invalid(self) -> None:
        client = TestClient(app)
        run_id = self._demo_run_id(client)
        reset_synthesis_for_tests(StubSynthesisProvider({"summary": "incomplete"}))
        response = client.post("/creator/synthesize", json={"run_id": run_id})
        assert response.status_code == 200
        body = response.json()
        assert body["metadata"]["method"] == "deterministic_fallback"
        assert body["metadata"]["llm_error"] == "output rejected by validation"

    def test_status_reflects_injected_override(self) -> None:
        reset_synthesis_for_tests(valid_stub())
        status = TestClient(app).get("/creator/synthesis-status").json()
        assert status["available"] is True
        assert status["provider"] == "stub"


@pytest.fixture
def client_env_cleared(monkeypatch):
    for name in ("ADJACENT_LLM_API_KEY", "ADJACENT_LLM_BASE_URL", "ADJACENT_LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    return TestClient(app)


def test_collect_evidence_refs_covers_all_sections() -> None:
    refs = collect_evidence_refs(INVESTIGATION)
    assert refs == {"run-c001", "run-c002"}
