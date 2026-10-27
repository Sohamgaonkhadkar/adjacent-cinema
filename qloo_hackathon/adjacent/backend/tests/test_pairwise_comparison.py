"""`/v2/analysis/compare` is read strictly, and never takes down a run.

The compare response is not modelled in this repository, so the whole point of
these tests is that an unfamiliar payload produces **no number** and that every
refusal is a value rather than an exception.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest
from app.domain.pairwise import (
    MAX_GROUP_MEMBERS,
    SCHEMA,
    build_pairwise_comparison,
    comparison_targets,
    interpret,
)
from app.qloo.errors import (
    InvalidFilterTypeError,
    InvalidValueError,
    ParamError,
    QlooTimeoutError,
)
from app.qloo.models import RawResponse


@dataclass
class _Member:
    entity_id: str
    name: str
    affinity: float | None
    is_marginal: bool = False


@dataclass
class _Cohort:
    cohort_id: str
    domain: str
    kind: str = "tag_cluster"
    members: list[_Member] = field(default_factory=list)


@dataclass
class _Ranking:
    ranked: list[_Cohort]


@dataclass
class _CompareClient:
    """Records the request and answers with a supplied payload."""

    payload: dict[str, Any] | None = None
    error: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def compare(self, **kwargs: Any) -> RawResponse:
        self.calls.append(dict(kwargs))
        if self.error is not None:
            raise self.error
        return RawResponse(
            call_id="compare-call-1",
            source="qloo",
            data_status="measured",
            endpoint="/v2/analysis/compare",
            data=self.payload or {},
        )


def _artist(cohort_id: str, names: dict[str, float]) -> _Cohort:
    return _Cohort(
        cohort_id=cohort_id,
        domain="urn:entity:artist",
        members=[
            _Member(entity_id=f"urn:entity:artist:{slug}", name=name, affinity=affinity)
            for slug, (name, affinity) in names.items()
        ],
    )


def _two_artists() -> _Ranking:
    return _Ranking(
        ranked=[
            _artist("winner", {"eno": ("Brian Eno", 0.81), "bud": ("Harold Budd", 0.74)}),
            _artist("runner-up", {"gud": ("Hildur Gudnadottir", 0.79), "joh": ("Johann Johannsson", 0.71)}),
        ]
    )


def _run(
    ranking: _Ranking,
    *,
    payload: dict[str, Any] | None = None,
    budget: int = 3,
    data_status: str = "measured",
    error: Exception | None = None,
) -> tuple[dict, _CompareClient]:
    client = _CompareClient(payload=payload, error=error)
    result = asyncio.run(
        build_pairwise_comparison(
            client,
            ranking,
            data_status=data_status,
            budget_remaining=budget,
        )
    )
    return result, client


def test_measured_overlap_is_reported_by_its_exact_key_and_costs_one_call() -> None:
    result, client = _run(_two_artists(), payload={"overlap": 0.63})

    assert result["schema"] == SCHEMA
    assert result["status"] == "measured"
    assert result["available"] is True
    assert result["metric"] == {
        "key": "overlap",
        "value": 0.63,
        "direction": "higher_is_closer",
        "source": "provider_reported",
    }
    assert result["call_id"] == "compare-call-1"

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["filter_type"] == "urn:entity:artist"
    assert call["model"] == "descriptive"
    assert call["take"] == MAX_GROUP_MEMBERS
    assert call["a_signal_interests_entities"] == [
        "urn:entity:artist:eno",
        "urn:entity:artist:bud",
    ]
    assert call["b_signal_interests_entities"] == [
        "urn:entity:artist:gud",
        "urn:entity:artist:joh",
    ]


def test_the_request_carries_only_documented_parameters() -> None:
    """Freeze the request shape: no location, page or offset is invented."""
    _, client = _run(_two_artists(), payload={"overlap": 0.63})

    assert set(client.calls[0]) == {
        "a_signal_interests_entities",
        "b_signal_interests_entities",
        "filter_type",
        "model",
        "take",
        "tool",
    }
    assert "filter_location_query" not in client.calls[0]
    assert "page" not in client.calls[0]
    assert "offset" not in client.calls[0]


def test_cohort_labels_are_reader_facing_and_carry_no_identifier() -> None:
    result, _ = _run(_two_artists(), payload={"overlap": 0.63})

    for side in ("a", "b"):
        group = result["cohorts"][side]
        assert "urn:" not in group["label"]
        assert group["rank"] in (1, 2)
        assert group["domain"] == "urn:entity:artist"
    assert result["cohorts"]["a"]["label"] == "artist · Brian Eno"
    assert result["cohorts"]["b"]["label"] == "artist · Hildur Gudnadottir"


def test_nested_metric_inside_results_is_read_with_its_direction() -> None:
    result, _ = _run(_two_artists(), payload={"results": {"distance": 0.12}})

    assert result["status"] == "measured"
    assert result["metric"]["key"] == "distance"
    assert result["metric"]["direction"] == "lower_is_closer"


def test_unrecognised_shape_is_refused_with_key_names_only() -> None:
    payload = {"lift": 3.2, "private_note": "provider payload must not escape"}
    result, _ = _run(_two_artists(), payload=payload)

    assert result["status"] == "unsupported_response_shape"
    assert result["available"] is False
    assert result["metric"] is None
    assert result["call_id"] == "compare-call-1"
    assert "lift" in result["observed_keys"]
    assert "private_note" in result["observed_keys"]
    # Values are never echoed — only key names.
    assert "3.2" not in str(result)
    assert "must not escape" not in str(result)


def test_non_finite_and_non_numeric_metric_values_are_not_read() -> None:
    for bad in (True, "0.6", float("nan"), float("inf"), None):
        result, _ = _run(_two_artists(), payload={"overlap": bad})
        assert result["status"] == "unsupported_response_shape", bad
        assert result["metric"] is None


def test_fixture_run_does_not_present_an_unmodelled_comparison_as_measured() -> None:
    result, client = _run(_two_artists(), payload={"results": []}, data_status="fixture")

    assert len(client.calls) == 1
    assert result["status"] == "not_modelled_in_fixture"
    assert result["available"] is False
    assert result["metric"] is None


def test_different_entity_types_are_not_applicable_and_never_called() -> None:
    ranking = _Ranking(
        ranked=[
            _artist("winner", {"eno": ("Brian Eno", 0.81)}),
            _Cohort(
                cohort_id="books",
                domain="urn:entity:book",
                members=[_Member(entity_id="urn:entity:book:one", name="A Book", affinity=0.7)],
            ),
        ]
    )
    result, client = _run(ranking, payload={"overlap": 0.5})

    assert result["status"] == "not_applicable"
    assert result["available"] is False
    assert client.calls == []
    assert "book" in result["reason"]
    assert "urn:entity:" not in result["reason"]


def test_winner_is_compared_with_the_best_same_type_cohort_and_ranks_are_reported() -> None:
    ranking = _Ranking(
        ranked=[
            _artist("winner", {"eno": ("Brian Eno", 0.81)}),
            _Cohort(
                cohort_id="books",
                domain="urn:entity:book",
                members=[_Member(entity_id="urn:entity:book:one", name="A Book", affinity=0.76)],
            ),
            _artist("third", {"gud": ("Hildur Gudnadottir", 0.72)}),
        ]
    )
    targets = comparison_targets(ranking)
    assert targets is not None
    assert targets[1].cohort_id == "third"

    result, client = _run(ranking, payload={"overlap": 0.41})
    assert result["status"] == "measured"
    assert result["cohorts"]["a"]["rank"] == 1
    assert result["cohorts"]["b"]["rank"] == 3
    # The book cohort is never sent to a comparison scoped to one type.
    sent = client.calls[0]["a_signal_interests_entities"] + client.calls[0]["b_signal_interests_entities"]
    assert "urn:entity:book:one" not in sent


def test_single_cohort_is_not_applicable() -> None:
    result, client = _run(_Ranking(ranked=[_artist("only", {"eno": ("Brian Eno", 0.8)})]))
    assert result["status"] == "not_applicable"
    assert client.calls == []


def test_cohort_without_scored_members_is_not_applicable() -> None:
    ranking = _Ranking(
        ranked=[
            _artist("winner", {"eno": ("Brian Eno", 0.8)}),
            _artist("unscored", {"x": ("Unscored", None)}),  # type: ignore[arg-type]
        ]
    )
    result, client = _run(ranking)
    assert result["status"] == "not_applicable"
    assert client.calls == []


def test_budget_refusal_makes_no_call() -> None:
    result, client = _run(_two_artists(), budget=0)
    assert result["status"] == "unavailable_budget"
    assert result["available"] is False
    assert result["call_attempted"] is False
    assert client.calls == []


def test_provider_failure_is_recorded_and_never_raised() -> None:
    result, client = _run(_two_artists(), error=RuntimeError("provider exploded"))

    assert len(client.calls) == 1
    assert result["status"] == "failed"
    assert result["available"] is False
    assert result["error_type"] == "RuntimeError"
    assert result["metric"] is None
    assert "provider exploded" not in str(result)
    # The groups are still described, so the reader sees what *would* have
    # been compared.
    assert result["cohorts"]["a"]["label"] == "artist · Brian Eno"


def test_provider_timeout_reports_its_kind_and_counts_as_an_attempt() -> None:
    """A timeout must be diagnosable — and must not look like a refusal."""
    result, client = _run(_two_artists(), error=QlooTimeoutError("upstream stalled"))

    assert len(client.calls) == 1
    assert result["status"] == "failed"
    assert result["error_kind"] == "timeout"
    assert result["error_status"] is None
    assert result["call_attempted"] is True
    assert result["metric"] is None
    assert "stalled" not in str(result)


@pytest.mark.parametrize(
    "error",
    [
        ParamError("filter.type must be a urn"),
        InvalidFilterTypeError("filter.type is not an entity type"),
        InvalidValueError("take must be positive"),
    ],
)
def test_a_parameter_error_is_not_counted_as_a_spent_provider_call(error: Exception) -> None:
    """Nothing left the process, so the budget must not be charged for it."""
    result, client = _run(_two_artists(), error=error)

    assert len(client.calls) == 1  # the client was asked...
    assert result["status"] == "failed"
    assert result["call_attempted"] is False
    assert "filter.type" not in result["reason"]


def test_refusals_state_that_no_call_was_attempted() -> None:
    result, client = _run(_two_artists(), budget=0)
    assert result["status"] == "unavailable_budget"
    assert result["call_attempted"] is False
    assert client.calls == []


def test_groups_are_truncated_to_the_documented_size() -> None:
    names = {f"a{i:02d}": (f"Artist {i}", 0.9 - i / 100) for i in range(14)}
    ranking = _Ranking(
        ranked=[
            _artist("winner", names),
            _artist("runner-up", {"gud": ("Hildur Gudnadottir", 0.5)}),
        ]
    )
    result, client = _run(ranking, payload={"overlap": 0.5})

    group_a = result["cohorts"]["a"]
    assert group_a["member_count"] == 14
    assert len(group_a["entity_ids"]) == MAX_GROUP_MEMBERS
    assert group_a["truncated"] is True
    assert len(client.calls[0]["a_signal_interests_entities"]) == MAX_GROUP_MEMBERS


def test_interpret_is_silent_unless_a_metric_was_established() -> None:
    assert interpret(None) == ""
    assert interpret({"available": False, "metric": None}) == ""
    assert interpret({"available": True, "metric": {"key": "overlap", "value": None}}) == ""

    sentence = interpret(
        {
            "available": True,
            "metric": {"key": "overlap", "value": 0.63, "direction": "higher_is_closer"},
            "cohorts": {"a": {"label": "artist · Brian Eno"}, "b": {"label": "artist · Hildur"}},
        }
    )
    assert "0.630" in sentence
    assert "higher means the two groups overlap more" in sentence
    assert "probability" not in sentence.lower()


def test_unknown_direction_does_not_claim_an_interpretation() -> None:
    sentence = interpret(
        {
            "available": True,
            "metric": {"key": "overlap", "value": 0.4, "direction": "unknown"},
            "cohorts": {"a": {"label": "A"}, "b": {"label": "B"}},
        }
    )
    assert "does not interpret that field" in sentence


# ---------------------------------------------------------------------------
# API surface: the comparison and the bounded attribution must reach the client
# ---------------------------------------------------------------------------


def _fixture_run_result() -> dict[str, Any]:
    import time

    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    run_id = client.post("/run/demo").json()["run_id"]
    deadline = time.time() + 30
    final: dict[str, Any] = {}
    while time.time() < deadline:
        final = client.get(f"/run/{run_id}").json()
        if final.get("status") in {"completed", "failed", "insufficient"}:
            break
        time.sleep(0.05)
    assert final.get("status") == "completed", final
    return final["result"]


def test_fixture_run_publishes_the_comparison_as_explicitly_unmodelled() -> None:
    result = _fixture_run_result()

    pairwise = result["pairwise"]
    assert pairwise["status"] == "not_modelled_in_fixture"
    assert pairwise["available"] is False
    assert pairwise["metric"] is None
    assert pairwise["call_id"], "the call is still recorded and traceable"
    # The two groups are named, same entity type, and carry their real ranks.
    assert pairwise["cohorts"]["a"]["domain"] == pairwise["cohorts"]["b"]["domain"]
    assert pairwise["cohorts"]["a"]["rank"] == 1
    assert pairwise["cohorts"]["b"]["rank"] >= 2
    assert "urn:" not in pairwise["cohorts"]["a"]["label"]

    # The challenge reads the same object, and the receipt carries its status.
    assert result["challenge"]["pairwise"]["status"] == "not_modelled_in_fixture"
    assert result["challenge"]["receipt"]["pairwise"]["status"] == "not_modelled_in_fixture"


def test_fixture_run_reports_where_attribution_came_from() -> None:
    result = _fixture_run_result()

    bounded = result["evidence"]["bounded_attribution"]
    assert bounded["status"] == "not_needed"
    assert bounded["qloo_calls_made"] == 0

    attribution = result["challenge"]["receipt"]["attribution"]
    assert attribution["bounded_status"] == "not_needed"
    assert attribution["bounded_call_id"] is None

    members = [m for cohort in result["cohorts"]["ranked"] for m in cohort["members"]]
    assert members
    for member in members:
        # The field is always present, even when it is null — a client must not
        # have to distinguish "absent" from "no attribution".
        assert "qloo_attribution_origin" in member
        assert member["qloo_attribution_origin"] is None


# ---------------------------------------------------------------------------
# Reader-facing sentence: the challenge must name the pair it actually compared
# ---------------------------------------------------------------------------


def test_challenge_cites_the_measured_comparison_with_both_ranks() -> None:
    from app.domain.challenge import _pairwise_action

    pairwise = {
        "status": "measured",
        "call_id": "compare-call-1",
        "metric": {"key": "overlap", "value": 0.6314, "direction": "higher_is_closer"},
        "cohorts": {
            "a": {"label": "artist · Brian Eno", "rank": 1},
            "b": {"label": "artist · Hildur Gudnadottir", "rank": 3},
        },
    }
    sentence = _pairwise_action(pairwise)

    assert "overlap = 0.631" in sentence
    assert "artist · Brian Eno (rank 1)" in sentence
    # The compared cohort is the highest-ranked one of the same type, which is
    # not always the runner-up — the sentence says so rather than implying it.
    assert "rank 3" in sentence
    assert "compare-call-1" in sentence
    assert "urn:" not in sentence
    assert "will sell tickets" in sentence


def test_challenge_reports_a_refusal_instead_of_a_number() -> None:
    from app.domain.challenge import _pairwise_action

    for status in (
        "not_applicable",
        "unavailable_budget",
        "unsupported_response_shape",
        "not_modelled_in_fixture",
        "failed",
    ):
        sentence = _pairwise_action(
            {
                "status": status,
                "call_id": None,
                "metric": None,
                "cohorts": None,
                "reason": "A reason the reader can act on.",
            }
        )
        assert status in sentence
        assert "A reason the reader can act on." in sentence
        assert "urn:" not in sentence
        assert "(s)" not in sentence

    # No comparison at all is a distinct, honest state.
    assert "No pairwise comparison was attempted" in _pairwise_action(None)
