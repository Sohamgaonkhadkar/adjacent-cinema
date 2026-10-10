"""Single-normalisation discipline.

Qloo affinity is normalised **per query**, so two affinity numbers produced by two
different queries are not comparable. The product decision that follows — rank every
candidate inside ONE scoring context, record ONE logical operation, never call the
scorer once per cohort — is only worth anything if it is enforced by tests.

These tests assert the discipline on the real fixture run, and one of them builds a
synthetic tie to prove the cross-context guard actually fires rather than being a
decorative flag.
"""

from __future__ import annotations

import asyncio

import pytest
from app.domain.cohorts import CandidateCohort
from app.domain.scoring import CohortRanker
from app.qloo.mock import MockQlooClient
from app.qloo.models import EntityAffinityResponse, ScoredEntity
from app.runner import run_fixture

STRONG = "portland_strong"


@pytest.fixture(scope="module")
def strong_run():
    return run_fixture(STRONG)


# -- the operation itself ----------------------------------------------------


def test_ranking_is_recorded_as_exactly_one_logical_operation(strong_run):
    rows = strong_run.trace_by_tool("build_and_rank_cohorts")
    assert len(rows) == 1, (
        "the ranking must appear in the trace as exactly one logical operation; "
        f"found {len(rows)}: {[r['call_id'] for r in rows]}"
    )
    assert rows[0]["source"] == "mock"
    assert rows[0]["data_status"] == "fixture"
    # The operation's own notes must state the discipline, not just imply it.
    notes = " ".join(rows[0]["notes"])
    assert "never one per cohort" in notes


def test_never_one_scoring_call_per_cohort(strong_run):
    ranking = strong_run.ranking
    contexts = len(ranking.contexts)
    cohorts = len(strong_run.cohorts)
    assert cohorts > contexts, (
        "the fixture has more cohorts than entity types, so a correct run MUST score "
        "several cohorts from one call — otherwise this test proves nothing"
    )
    assert len(ranking.scoring_call_ids) == contexts
    assert len(set(ranking.scoring_call_ids)) == contexts, "a scoring context was called twice"


def test_every_cohort_is_scored_from_its_domain_scoring_call(strong_run):
    calls_by_domain = {context.domain: context.call_id for context in strong_run.ranking.contexts}
    for cohort in strong_run.cohorts:
        assert cohort.context_id == f"ctx:{cohort.domain}"
        assert cohort.score is not None, f"{cohort.cohort_id} was never scored"
        assert cohort.score.call_id == calls_by_domain[cohort.domain]
        for member in cohort.members:
            # Same call for every member: one normalisation, one comparison basis.
            assert member.call_id == cohort.score.call_id


def test_scoring_call_asks_for_the_whole_domain_cohort_set_at_once(strong_run):
    """The call that scores a cohort must request *every* cohort's members in that
    domain — that is what `filter.results.entities` is for."""
    requested_by_domain: dict[str, set[str]] = {}
    for context in strong_run.ranking.contexts:
        row = next(r for r in strong_run.trace_rows if r["call_id"] == context.call_id)
        requested = row["params"].get("filter.results.entities")
        assert requested, "a scoring call must pin the candidate set with filter.results.entities"
        requested_by_domain[context.domain] = set(requested)

    for cohort in strong_run.cohorts:
        assert set(cohort.member_ids) <= requested_by_domain[cohort.domain], (
            f"{cohort.cohort_id} was scored by a call that did not even ask for its members"
        )


def test_no_trace_row_is_named_after_a_single_cohort(strong_run):
    for row in strong_run.trace_rows:
        assert row["tool"] not in {"rank_cohort_A", "rank_cohort_B", "rank_cohort_C"}
        assert row["tool"] == "build_and_rank_cohorts" or not row["tool"].startswith("rank_")


def test_affinity_used_for_ordering_never_crosses_contexts(strong_run):
    """Mean affinity is the LAST ordering key and must never decide between
    different normalisations. The flag records any attempt."""
    assert strong_run.ranking.cross_context_tiebreak_used is False
    for entry in strong_run.ranking.ordering:
        assert entry["reasoning"].endswith("within-context tiebreaker only")


# -- the guard itself --------------------------------------------------------


class _FixedClient:
    """A client that returns a fixed affinity per entity, one call per context."""

    def __init__(self, affinities: dict[str, float], popularities: dict[str, float]) -> None:
        self.recorder = MockQlooClient().recorder
        self._affinities = affinities
        self._popularities = popularities
        self.calls: list[dict[str, object]] = []

    async def insights(self, **kwargs: object) -> EntityAffinityResponse:
        self.calls.append(kwargs)
        domain = str(kwargs["filter_type"])
        results = [
            ScoredEntity(
                entity_id=entity_id,
                name=entity_id,
                type=domain,
                affinity=affinity,
                popularity=self._popularities.get(entity_id),
            )
            for entity_id, affinity in self._affinities.items()
            if entity_id.startswith(domain)
        ]
        return EntityAffinityResponse(
            call_id=f"fixed-{domain}",
            source="mock",
            data_status="fixture",
            endpoint="/v2/insights",
            results=results,
        )


def _cohort(cohort_id: str, domain: str, member_ids: list[str]) -> CandidateCohort:
    return CandidateCohort(
        cohort_id=cohort_id,
        domain=domain,
        kind="subtype_group",
        member_ids=member_ids,
        construction_reason="test fixture",
    )


def test_identical_safe_keys_across_contexts_raise_the_tiebreak_flag():
    """Two cohorts in different contexts with identical band strength, identical
    novelty and identical member counts: the ordering would need raw affinity to
    separate them, so the flag must be raised instead of silently comparing."""
    artists = "urn:entity:artist"
    books = "urn:entity:book"
    cohorts = [
        _cohort("a", artists, [f"{artists}-1", f"{artists}-2"]),
        _cohort("b", books, [f"{books}-1", f"{books}-2"]),
    ]
    client = _FixedClient(
        affinities={
            f"{artists}-1": 0.90,
            f"{artists}-2": 0.70,
            f"{books}-1": 0.55,
            f"{books}-2": 0.60,
        },
        popularities=dict.fromkeys([f"{artists}-1", f"{artists}-2", f"{books}-1", f"{books}-2"], 0.5),
    )
    result = asyncio.run(CohortRanker(client, programme_ids=["programme-1"]).build_and_rank_cohorts(cohorts))

    assert len(result.contexts) == 2
    assert len(result.scoring_call_ids) == 2
    assert result.ranked, "both cohorts clear the evidence gate in this construct"
    assert result.cross_context_tiebreak_used is True, (
        "identical safe keys in different normalisations must raise the flag rather "
        "than be separated by raw affinity"
    )
    # The cohorts are still ordered deterministically (by cohort_id), and each keeps
    # a reference to its own context so no consumer can mistake the basis.
    assert {c.context_id for c in result.ranked} == {f"ctx:{artists}", f"ctx:{books}"}
