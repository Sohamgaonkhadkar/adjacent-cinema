"""Qloo recommendation attribution is preserved only when it validates."""

from __future__ import annotations

import pytest
from app.contract import QlooAttributionView
from app.contract import _member as _contract_member
from app.domain.cohorts import MemberEvidence
from app.qloo.models import ScoredEntity
from pydantic import ValidationError


def _member(raw: dict) -> MemberEvidence:
    return MemberEvidence(
        scored=ScoredEntity(
            entity_id="candidate-1",
            name="Candidate",
            affinity=0.72,
            raw=raw,
        ),
        call_id="qloo-score-1",
        is_marginal=False,
        allowed_qloo_seed_ids=("seed-1", "seed-2"),
    )


def test_valid_qloo_seed_attributions_are_exported_without_raw_response() -> None:
    member = _member(
        {
            "query": {
                "affinity": 0.72,
                "explainability": {
                    "signal.interests.entities": [
                        {"entity_id": "seed-1", "score": 0.41},
                        {"entity_id": "seed-2", "score": 0.31},
                    ]
                },
            },
            "private_provider_payload": "must not escape",
        }
    )

    payload = member.to_dict()
    assert payload["qloo_attributions"] == [
        {"entity_id": "seed-1", "score": 0.41},
        {"entity_id": "seed-2", "score": 0.31},
    ]
    assert payload["qloo_attribution_status"] == "returned"
    assert "raw" not in payload
    assert "private_provider_payload" not in str(payload)

    api_member = _contract_member(
        _member(
            {
                "query": {
                    "explainability": {
                        "signal.interests.entities": [
                            {"entity_id": "seed-1", "score": 0.41},
                        ]
                    }
                },
            }
        )
    ).model_dump()
    assert api_member["qloo_attributions"] == [{"entity_id": "seed-1", "score": 0.41}]
    assert api_member["qloo_attribution_status"] == "returned"
    assert api_member["call_id"] == "qloo-score-1"


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -0.01, 1.01])
def test_api_attribution_contract_rejects_nonfinite_or_out_of_range_scores(score: float) -> None:
    with pytest.raises(ValidationError):
        QlooAttributionView(entity_id="seed-1", score=score)


def test_api_attribution_contract_rejects_blank_ids() -> None:
    with pytest.raises(ValidationError):
        QlooAttributionView(entity_id=" ", score=0.5)


def test_missing_or_invalid_qloo_attribution_is_not_inferred() -> None:
    member = _member(
        {
            "query": {
                "explainability": {
                    "signal.interests.entities": [
                        {"entity_id": "", "score": 0.4},
                        {"entity_id": "seed-nan", "score": float("nan")},
                        {"entity_id": "seed-over", "score": 1.01},
                        {"entity_id": "seed-huge", "score": 10**1000},
                        {"entity_id": "seed-text", "score": "0.4"},
                        {"entity_id": "seed-bool", "score": True},
                        {"entity_id": "not-an-input-seed", "score": 0.9},
                        {"entity_id": "seed-duplicate", "score": 0.2},
                        {"entity_id": "seed-duplicate", "score": 0.3},
                        "malformed",
                    ]
                }
            }
        }
    )
    payload = member.to_dict()
    assert payload["qloo_attributions"] == []
    assert payload["qloo_attribution_status"] == "missing"
    assert _member({"query": {}}).to_dict()["qloo_attributions"] == []
