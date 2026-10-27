"""Bounded explainability: attribution for the winner without re-scoring the run.

A scoring context with more than 12 entities cannot request
``feature.explainability``, which is why live runs used to carry no per-seed
attribution at all. These tests pin the follow-up call: it happens once, only
for the winner, only when the budget allows it, never changes an affinity, and
never invents a contribution it did not receive.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from app.domain.cohorts import CandidateCohort
from app.domain.scoring import CohortRanker
from app.qloo.errors import QlooError
from app.qloo.mock import MockQlooClient
from app.qloo.models import EntityAffinityResponse, ScoredEntity

SEEDS = ["seed-film-1", "seed-film-2"]


def _explainability_block() -> dict[str, Any]:
    return {
        "query": {
            "explainability": {
                "signal.interests.entities": [
                    {"entity_id": "seed-film-1", "score": 0.44},
                    {"entity_id": "seed-film-2", "score": 0.21},
                ]
            }
        }
    }


class _BudgetedClient:
    """Scores 20 entities in one context; optionally answers explainability."""

    tool = "mock"

    def __init__(self, *, explainability: Any = None, fail_with: Exception | None = None) -> None:
        self.explainability = explainability
        self.fail_with = fail_with
        self.calls: list[dict[str, Any]] = []
        # The ranker writes its logical-operation row through this recorder, so
        # reuse the real one instead of faking a trace.
        self.recorder = MockQlooClient().recorder

    async def insights(self, **kwargs: Any) -> EntityAffinityResponse:
        self.calls.append(dict(kwargs))
        if kwargs.get("feature_explainability"):
            if self.fail_with is not None:
                raise self.fail_with
            return EntityAffinityResponse(
                call_id="bounded-call-1",
                source="qloo",
                data_status="measured",
                endpoint="/v2/insights",
                results=[
                    ScoredEntity(
                        entity_id=f"urn:entity:artist:{i:02d}",
                        name=f"Artist {i:02d}",
                        type="urn:entity:artist",
                        affinity=0.9 - i / 100,
                        popularity=0.5,
                        raw=(
                            self.explainability
                            if self.explainability is not None
                            else _explainability_block()
                        ),
                    )
                    for i in range(3)
                ],
            )
        return EntityAffinityResponse(
            call_id="scoring-call-1",
            source="qloo",
            data_status="measured",
            endpoint="/v2/insights",
            results=[
                ScoredEntity(
                    entity_id=f"urn:entity:artist:{i:02d}",
                    name=f"Artist {i:02d}",
                    type="urn:entity:artist",
                    affinity=0.9 - i / 100,
                    popularity=0.5,
                    raw={"query": {"affinity": 0.9 - i / 100}},
                )
                for i in range(20)
            ],
        )


def _cohort(
    member_count: int = 20, cohort_id: str = "artists", domain: str = "urn:entity:artist"
) -> CandidateCohort:
    return CandidateCohort(
        cohort_id=cohort_id,
        domain=domain,
        kind="tag_cluster",
        member_ids=[f"urn:entity:artist:{i:02d}" for i in range(member_count)],
        construction_reason="test fixture",
    )


def _rank(client: _BudgetedClient, *, budget: int = 1, cohorts: list[CandidateCohort] | None = None):
    ranker = CohortRanker(
        client,
        programme_ids=SEEDS,
        bounded_attribution_budget=budget,
    )
    return asyncio.run(ranker.build_and_rank_cohorts(cohorts or [_cohort()]))


def test_context_above_the_field_limit_still_gets_attribution_from_one_extra_call() -> None:
    client = _BudgetedClient()
    result = _rank(client)

    # 20 candidates > the 12-entity explainability limit, so inline attribution
    # was correctly not requested…
    assert result.contexts[0].explainability_status == "not_requested_limit"
    # One scoring call with no explainability field, then one bounded call.
    assert [call.get("feature_explainability") for call in client.calls] == [None, True]

    # …and exactly one bounded follow-up answered for the winner.
    bounded = result.bounded_attribution
    assert bounded["status"] == "returned"
    assert bounded["call_id"] == "bounded-call-1"
    assert bounded["domain"] == "urn:entity:artist"
    assert bounded["members_updated"] == 3
    assert result.qloo_calls_made == 2
    assert result.scoring_call_ids == ["scoring-call-1", "bounded-call-1"]

    winner = result.ranked[0]
    attributed = [m for m in winner.members if m.qloo_attributions()]
    assert attributed, "winner should carry per-seed attribution"
    assert all(m.qloo_attribution_status == "returned_bounded" for m in attributed)
    assert all(m.attribution_origin == "bounded" for m in attributed)
    assert attributed[0].qloo_attributions()[0]["entity_id"] == "seed-film-1"


def test_bounded_call_keeps_the_affinity_scores_it_was_ranked_on() -> None:
    client = _BudgetedClient()
    result = _rank(client)

    # The follow-up returns 0.9/0.89/0.88 for three members; the members keep
    # the values from the scoring call, unchanged.
    before = {m.entity_id: m.affinity for m in result.ranked[0].members}
    assert before["urn:entity:artist:00"] == pytest.approx(0.90)
    assert before["urn:entity:artist:05"] == pytest.approx(0.85)
    # Only the top-12-by-affinity members are in the bounded request (the last
    # call; the first was scoring).
    bounded_call = client.calls[-1]
    assert len(bounded_call["filter_results_entities"]) == 12
    assert bounded_call["filter_type"] == "urn:entity:artist"
    assert bounded_call["signal_interests_entities"] == SEEDS


def test_no_budget_means_no_call_and_an_explicit_refusal() -> None:
    client = _BudgetedClient()
    result = _rank(client, budget=0)

    assert [call.get("feature_explainability") for call in client.calls] == [None]
    bounded = result.bounded_attribution
    assert bounded["status"] == "unavailable_budget"
    assert bounded["qloo_calls_made"] == 0
    assert result.qloo_calls_made == 1
    assert all(m.qloo_attribution_status == "not_requested_limit" for m in result.ranked[0].members)
    assert all(m.attribution_origin is None for m in result.ranked[0].members)


def test_inline_attribution_is_not_requested_twice() -> None:
    """Three candidates fit under the limit, so the context asks inline."""

    class _Small(_BudgetedClient):
        async def insights(self, **kwargs: Any) -> EntityAffinityResponse:
            self.calls.append(dict(kwargs))
            return EntityAffinityResponse(
                call_id="small-call",
                source="qloo",
                data_status="measured",
                endpoint="/v2/insights",
                results=[
                    ScoredEntity(
                        entity_id=f"urn:entity:artist:{i:02d}",
                        name=f"Artist {i:02d}",
                        type="urn:entity:artist",
                        affinity=0.8 - i / 100,
                        popularity=0.4,
                        raw=_explainability_block(),
                    )
                    for i in range(3)
                ],
            )

    client = _Small()
    result = _rank(client, cohorts=[_cohort(member_count=3)])

    assert [call.get("feature_explainability") for call in client.calls] == [True]
    assert result.bounded_attribution["status"] == "not_needed"
    assert result.bounded_attribution["qloo_calls_made"] == 0
    assert result.qloo_calls_made == 1
    assert all(m.attribution_origin == "scoring" for m in result.ranked[0].members)


def test_provider_failure_degrades_to_failed_and_keeps_the_ranking() -> None:
    client = _BudgetedClient(fail_with=QlooError("upstream unavailable", status=503))
    result = _rank(client)

    bounded = result.bounded_attribution
    assert bounded["status"] == "failed"
    assert bounded["error_type"] == "QlooError"
    assert bounded["members_updated"] == 0
    # The ranking itself is untouched.
    assert result.ranked
    assert result.ranked[0].score is not None
    assert result.ranked[0].score.mean_affinity is not None
    assert all(m.qloo_attribution_status == "not_requested_limit" for m in result.ranked[0].members)


def test_provider_answer_without_a_valid_block_reports_missing_and_infers_nothing() -> None:
    client = _BudgetedClient(explainability={"query": {"affinity": 0.8}})
    result = _rank(client)

    bounded = result.bounded_attribution
    assert bounded["status"] == "missing"
    assert bounded["members_updated"] == 0
    assert bounded["call_id"] == "bounded-call-1"
    guard = "nothing is inferred"
    assert guard in bounded["reason"]
    assert all(m.qloo_attributions() == [] for m in result.ranked[0].members)
    assert all(m.attribution_origin is None for m in result.ranked[0].members)


def test_attribution_naming_an_unknown_seed_is_discarded() -> None:
    client = _BudgetedClient(
        explainability={
            "query": {
                "explainability": {"signal.interests.entities": [{"entity_id": "not-a-seed", "score": 0.5}]}
            }
        }
    )
    result = _rank(client)

    assert result.bounded_attribution["status"] == "missing"
    assert result.bounded_attribution["members_updated"] == 0
    assert all(m.qloo_attributions() == [] for m in result.ranked[0].members)
