"""The optional explainability field must not take down core cohort scoring."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from app.config import Settings
from app.domain.cohorts import CandidateCohort
from app.domain.scoring import CohortRanker
from app.qloo.client import QlooClient
from app.qloo.errors import QlooError
from app.qloo.mock import MockQlooClient
from app.qloo.models import EntityAffinityResponse, ScoredEntity


class _RejectExplainabilityOnce:
    def __init__(self, error: QlooError) -> None:
        self.recorder = MockQlooClient().recorder
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def insights(self, **kwargs: object) -> EntityAffinityResponse:
        self.calls.append(dict(kwargs))
        if kwargs.get("feature_explainability") is True:
            raise self.error
        return EntityAffinityResponse(
            call_id="successful-fallback-call",
            source="qloo",
            data_status="measured",
            endpoint="/v2/insights",
            results=[
                ScoredEntity(
                    entity_id="urn:entity:artist:one",
                    name="One",
                    type="urn:entity:artist",
                    affinity=0.75,
                    popularity=0.4,
                ),
                ScoredEntity(
                    entity_id="urn:entity:artist:two",
                    name="Two",
                    type="urn:entity:artist",
                    affinity=0.70,
                    popularity=0.5,
                ),
            ],
        )


def _cohort() -> CandidateCohort:
    return CandidateCohort(
        cohort_id="artists",
        domain="urn:entity:artist",
        kind="test",
        member_ids=["urn:entity:artist:one", "urn:entity:artist:two"],
        construction_reason="test fixture",
    )


def _rejection(*, status: int = 422, endpoint: str = "/v2/insights", detail: object = None) -> QlooError:
    return QlooError(
        "Qloo rejected request",
        status=status,
        endpoint=endpoint,
        detail=detail
        if detail is not None
        else {
            "parameter": "feature.explainability",
            "message": "unsupported parameter",
        },
    )


def test_explicit_field_validation_rejection_is_eligible_for_one_fallback() -> None:
    error = _rejection(
        detail={
            "parameter": "feature.explainability",
            "message": "feature.explainability must be a boolean",
        }
    )
    client = _RejectExplainabilityOnce(error)
    result = asyncio.run(
        CohortRanker(client, programme_ids=["reference-1"]).build_and_rank_cohorts([_cohort()])
    )

    assert [call.get("feature_explainability") for call in client.calls] == [True, None]
    assert result.contexts[0].explainability_status == "unsupported"


def test_explicit_optional_parameter_rejection_retries_once_and_keeps_scoring() -> None:
    client = _RejectExplainabilityOnce(_rejection())
    result = asyncio.run(
        CohortRanker(client, programme_ids=["reference-1"]).build_and_rank_cohorts([_cohort()])
    )

    assert [call.get("feature_explainability") for call in client.calls] == [True, None]
    assert result.qloo_calls_made == 2
    assert result.scoring_call_ids == ["successful-fallback-call"]
    assert result.contexts[0].explainability_status == "unsupported"
    assert all(member.qloo_attribution_status == "unsupported" for member in result.ranked[0].members)
    assert all(member.call_id == "successful-fallback-call" for member in result.ranked[0].members)
    operation = next(row for row in client.recorder.rows if row.tool == "build_and_rank_cohorts")
    assert any("retried once without it" in note for note in operation.notes)


@pytest.mark.parametrize(
    "error",
    [
        _rejection(status=401),
        _rejection(status=429),
        _rejection(detail={"parameter": "filter.type", "message": "unsupported value"}),
        _rejection(detail={"parameter": "feature.explainability", "message": "bad request"}),
        _rejection(endpoint="/v1/entities"),
        _rejection(endpoint=None),
    ],
)
def test_unrelated_or_transient_errors_are_not_retried(error: QlooError) -> None:
    client = _RejectExplainabilityOnce(error)
    with pytest.raises(QlooError):
        asyncio.run(CohortRanker(client, programme_ids=["reference-1"]).build_and_rank_cohorts([_cohort()]))
    assert len(client.calls) == 1


def test_http_validation_fallback_keeps_both_request_attempts_traceable() -> None:
    observed_queries: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        query = dict(request.url.params)
        observed_queries.append(query)
        if query.get("feature.explainability") == "true":
            return httpx.Response(
                422,
                json={
                    "errors": [
                        {
                            "field": "feature.explainability",
                            "message": "unsupported parameter",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "results": {
                    "entities": [
                        {
                            "entity_id": "urn:entity:artist:one",
                            "name": "One",
                            "type": "urn:entity:artist",
                            "query": {"affinity": 0.75},
                            "properties": {"popularity": 0.4},
                        },
                        {
                            "entity_id": "urn:entity:artist:two",
                            "name": "Two",
                            "type": "urn:entity:artist",
                            "query": {"affinity": 0.70},
                            "properties": {"popularity": 0.5},
                        },
                    ]
                }
            },
        )

    settings = Settings.from_env(
        qloo_api_key="unit-test",
        rate_limit_rps=0.0,
        max_retries=0,
        retry_backoff_base_s=0.0,
    )
    client = QlooClient(
        settings,
        transport=httpx.MockTransport(handler),
        run_id="fallback-test",
    )

    async def run() -> tuple[object, list[object]]:
        try:
            ranking = await CohortRanker(client, programme_ids=["reference-1"]).build_and_rank_cohorts(
                [_cohort()]
            )
            return ranking, list(client.recorder.rows)
        finally:
            await client.aclose()

    ranking, rows = asyncio.run(run())
    assert len(observed_queries) == 2
    assert observed_queries[0]["feature.explainability"] == "true"
    assert "feature.explainability" not in observed_queries[1]
    failed = next(row for row in rows if row.status == 422)
    succeeded = next(row for row in rows if row.status == 200)
    assert failed.error["call_id"] == failed.call_id
    assert succeeded.call_id == ranking.scoring_call_ids[0]
    operation = next(row for row in rows if row.tool == "build_and_rank_cohorts")
    assert any(failed.call_id in note and "retried once" in note for note in operation.notes)


def test_budget_without_retry_capacity_omits_optional_parameter() -> None:
    client = _RejectExplainabilityOnce(_rejection())
    result = asyncio.run(
        CohortRanker(
            client,
            programme_ids=["reference-1"],
            max_explainability_fallbacks=0,
        ).build_and_rank_cohorts([_cohort()])
    )

    assert len(client.calls) == 1
    assert "feature_explainability" not in client.calls[0]
    assert result.contexts[0].explainability_status == "not_requested_budget"
    assert result.qloo_calls_made == 1
