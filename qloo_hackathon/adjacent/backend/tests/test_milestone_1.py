"""Milestone 1 acceptance: the fixture spine, end to end.

The fixture files are NOT modified to make anything here pass. Where a fixture
declares its own expectations (`expectations` in the JSON), this file checks the
pipeline against those declarations too, so the claims come from the evidence
rather than from the test author.

Scenario 1 — `portland_strong`: resolution succeeds, ≥3 cohorts across ≥3 domains
survive, at least one candidate cohort is rejected for weak evidence, and the run
ends `complete`.

Scenario 2 — `insufficient_evidence`: too little resolves, no cohort clears the
gate, and the run ends `insufficiency` with the product's exact refusal sentence
and no recommendation of any kind.
"""

from __future__ import annotations

import json

import pytest
from app.cli import EXIT_CANNOT_RUN, EXIT_OK, main
from app.domain.reasons import RejectionCode
from app.evidence import MSG_NO_ADJACENT_AUDIENCE
from app.runner import STOP_COMPLETE, STOP_INSUFFICIENCY, run_fixture

STRONG = "portland_strong"
SPARSE = "insufficient_evidence"


@pytest.fixture(scope="module")
def strong_run():
    return run_fixture(STRONG)


@pytest.fixture(scope="module")
def sparse_run():
    return run_fixture(SPARSE)


# 1 --------------------------------------------------------------------------
def test_candidate_cohorts_are_constructed_with_evidence_for_the_grouping(strong_run):
    """≥3 cohorts, ≥2 domains-spanning members each... constructed from the returned
    candidates, each carrying the rule and the call that justify it."""
    assert len(strong_run.cohorts) >= 3, "the strong scenario must produce ≥3 candidate cohorts"

    multi_member = [c for c in strong_run.cohorts if c.member_count >= 2]
    assert len(multi_member) >= 3

    known_ids = {
        entity.entity_id for entities in strong_run.candidates_by_domain.values() for entity in entities
    }
    for cohort in strong_run.cohorts:
        evidence = cohort.construction_evidence
        assert evidence["rule"] in {
            "shared_tag_component",
            "shared_subtype_group",
            "domain_grouping_fallback",
        }
        # "Why were these grouped?" must be answerable from the record alone.
        assert cohort.construction_reason
        assert evidence["call_id"] in strong_run.expansion_call_ids.values()
        assert cohort.source_call_ids == [evidence["call_id"]]
        assert set(cohort.member_ids) <= known_ids, "a cohort contains ids Qloo never returned"
        assert evidence["member_count"] == cohort.member_count

    # The tag rule must fire where the response actually returned shared tags, and
    # never be asserted where it did not.
    tag_clusters = [c for c in strong_run.cohorts if c.kind == "tag_cluster"]
    assert tag_clusters, "the strong fixture returns shared tags on artists, so tag_cluster is expected"
    for cohort in tag_clusters:
        assert cohort.construction_evidence["shared_tags"], "a tag cluster must name its shared tags"


# 2 --------------------------------------------------------------------------
def test_surviving_cohorts_span_at_least_three_entity_domains(strong_run):
    domains = {cohort.domain for cohort in strong_run.ranked}
    assert len(domains) >= 3, f"only {sorted(domains)} survived"
    assert len(strong_run.domains_represented) >= 3
    # Every cohort belongs to exactly one domain, and that domain is a Qloo entity type.
    for cohort in strong_run.cohorts:
        assert cohort.domain.startswith("urn:entity:")


# 3 --------------------------------------------------------------------------
def test_ranking_is_one_logical_operation_in_the_trace(strong_run):
    rows = strong_run.trace_by_tool("build_and_rank_cohorts")
    assert len(rows) == 1
    operation = rows[0]
    assert operation["call_id"] == strong_run.ranking.operation_call_id
    assert len(strong_run.ranking.contexts) == len(strong_run.ranking.scoring_call_ids)
    assert strong_run.ranking.scored_entity_count > 0


# 4 --------------------------------------------------------------------------
def test_at_least_one_cohort_is_rejected_for_weak_evidence(strong_run):
    assert strong_run.rejected, "the strong fixture contains a candidate that cannot clear the gate"
    gate_weak = [c for c in strong_run.rejected if c.rejection.gate_reason_code == "weak_evidence"]
    assert gate_weak, "expected at least one rejection whose evidence-gate verdict is weak_evidence"

    for cohort in strong_run.rejected:
        rejection = cohort.rejection
        # Machine-readable, produced by deterministic code, with a human detail line.
        assert rejection.code in set(RejectionCode)
        assert rejection.detail
        assert rejection.member_count == cohort.member_count
        assert rejection.code.value in strong_run.rendered_text


# 5 --------------------------------------------------------------------------
def test_strong_scenario_completes(strong_run):
    assert strong_run.stop_reason == STOP_COMPLETE
    assert len(strong_run.ranked) >= 3
    assert len(strong_run.ranked) >= len(strong_run.rejected)
    # Ranking is dense and ordered 1..n with no gaps.
    assert [c.rank for c in strong_run.ranked] == list(range(1, len(strong_run.ranked) + 1))
    # The refusal sentence must NOT appear when the run succeeds.
    assert MSG_NO_ADJACENT_AUDIENCE not in strong_run.rendered_text


def test_strong_run_satisfies_the_fixtures_own_declared_expectations(strong_run):
    """The fixture file states what it is for. Check against that, not just against
    our own thresholds."""
    with open(strong_run.fixture_path, encoding="utf-8") as handle:
        expectations = json.load(handle)["expectations"]

    assert len(strong_run.resolved_items) == expectations["resolved_entity_count"]
    surviving_domains = {c.domain for c in strong_run.ranked}
    assert len(surviving_domains) >= expectations["min_cross_domain_count"]
    assert len(strong_run.ranked) >= expectations["min_cohorts_meeting_evidence"]

    rejected_names = {(m.name or m.entity_id) for cohort in strong_run.rejected for m in cohort.members}
    for name in expectations["weak_candidate_names"]:
        # A "weak candidate" is either in a rejected cohort or flagged as marginal.
        in_rejected = name in rejected_names
        marginal = any(
            (m.name or "") == name and m.is_marginal for cohort in strong_run.cohorts for m in cohort.members
        )
        assert in_rejected or marginal, f"{name} was declared weak but was neither rejected nor flagged"

    # Every over-popular candidate must be flagged, not hidden.
    flagged = {
        e.name
        for cohort in strong_run.cohorts
        for e in cohort.excluded_members
        if e.code.value == "oversaturated"
    }
    for name in expectations["over_popular_candidate_names"]:
        assert name in flagged, f"{name} is over-popular and must be flagged, not silently used"


# 6 --------------------------------------------------------------------------
def test_sparse_scenario_ends_in_insufficiency_with_zero_surviving_cohorts(sparse_run):
    assert sparse_run.stop_reason == STOP_INSUFFICIENCY
    assert sparse_run.ranked == []
    assert not any(cohort.verdict and cohort.verdict.sufficient for cohort in sparse_run.cohorts), (
        "no cohort may clear the gate in the sparse scenario"
    )
    # The insufficiencies are reported, not glossed over.
    codes = {finding.code for finding in sparse_run.findings}
    assert "insufficient_resolved_titles" in codes
    assert "insufficient_cohorts" in codes


# 7 --------------------------------------------------------------------------
def test_sparse_scenario_message_is_exactly_the_product_sentence(sparse_run):
    assert sparse_run.stop_message == (
        "I do not have enough Qloo evidence to name an adjacent audience for this programme."
    )
    assert MSG_NO_ADJACENT_AUDIENCE in sparse_run.rendered_text
    # No fabricated recommendation may appear anywhere in the output.
    assert "RECOMMEND" not in sparse_run.rendered_text.upper().replace("NO RECOMMENDATION", "")
    for cohort in sparse_run.cohorts:
        assert cohort.rejected, "every constructed cohort must be explicitly rejected"


def test_sparse_scenario_keeps_unresolved_titles_visible_and_out_of_the_signals(sparse_run):
    assert len(sparse_run.unresolved_items) == 2
    for item in sparse_run.unresolved_items:
        assert item.title in sparse_run.rendered_text, "an unresolved title must stay visible"
        assert item.resolved_entity_id is None
    assert sparse_run.unresolved_items
    assert len(sparse_run.resolved_ids) == 1


# 8 --------------------------------------------------------------------------
def test_every_displayed_number_is_traceable_to_a_trace_row(strong_run):
    ledger = strong_run.ledger
    audit = ledger.audit()
    assert audit["numbers_displayed"] > 0
    assert audit["unverified"] == []
    assert ledger.problems() == []

    trace_ids = {row["call_id"] for row in strong_run.trace_rows}
    for number in ledger.numbers:
        if number.source_kind == "qloo_call":
            assert number.source in trace_ids, f"{number.label} cites a call with no trace row"

    # Anything displayed FOR a cohort must come from that cohort's single scoring
    # call — the numbers on screen are therefore all from one normalisation.
    for cohort in strong_run.cohorts:
        expected_call = cohort.score.call_id
        cohort_numbers = [n for n in ledger.numbers if n.label.startswith(f"{cohort.cohort_id}/")]
        assert cohort_numbers, f"no number for {cohort.cohort_id} went through the ledger"
        assert {n.source for n in cohort_numbers} == {expected_call}

    # Every affinity the output could show for a cohort member IS registered.
    registered = {n.label for n in ledger.numbers}
    for cohort in strong_run.cohorts:
        for member in cohort.members:
            assert f"{cohort.cohort_id}/{member.entity_id}.affinity" in registered
            assert f"{cohort.cohort_id}/{member.entity_id}.popularity" in registered


def test_no_number_is_rendered_without_a_declared_source(strong_run):
    """The ledger refuses to format a number with no source at all — that is the
    mechanism, not a convention."""
    from app.domain.ledger import ProvenanceLedger

    ledger = ProvenanceLedger(recorder=strong_run.ledger.recorder)
    with pytest.raises(ValueError):
        ledger.fmt(0.5, label="unsourced")


# 9 --------------------------------------------------------------------------
def test_every_artefact_is_marked_as_fixture(strong_run):
    assert strong_run.data_status == "fixture"
    assert strong_run.trace_rows, "a run without trace rows has no provenance"
    for row in strong_run.trace_rows:
        assert row["source"] == "mock"
        assert row["data_status"] == "fixture"
    assert "DATA STATUS: FIXTURE" in strong_run.rendered_text
    assert "NOT MEASURED QLOO OUTPUT" in strong_run.rendered_text
    # The declared simulation limits are printed with the run, not hidden in a doc.
    assert "filter.results.entities" in strong_run.rendered_text
    assert "fixture simulation limits" in strong_run.rendered_text

    payload = json.loads(strong_run.to_json())
    assert payload["data_status"] == "fixture"
    assert all(row["data_status"] == "fixture" for row in payload["trace"])
    assert payload["ledger_audit"]["unverified"] == []


# 10 -------------------------------------------------------------------------
def test_no_client_call_is_duplicated(strong_run):
    seen: set[tuple[str, str]] = set()
    for row in strong_run.trace_rows:
        fingerprint = (row["tool"], json.dumps(row["params"], sort_keys=True))
        assert fingerprint not in seen, f"duplicate call: {row['tool']} {row['params']}"
        seen.add(fingerprint)

    score_rows = [r for r in strong_run.trace_rows if r["tool"].startswith("score_context:")]
    assert len(score_rows) == len(strong_run.ranking.contexts)
    assert len({r["tool"] for r in score_rows}) == len(score_rows)

    # Call budget is respected and reported.
    assert strong_run.calls_made <= 20
    assert len(strong_run.trace_rows) == strong_run.calls_made + 1  # + the operation row


# -- the CLI contract --------------------------------------------------------


def test_cli_runs_the_strong_scenario_and_exits_zero(capsys):
    code = main(["run", "--fixture", "fixtures/portland_strong.json", "--mock", "--quiet-summary"])
    assert code == EXIT_OK
    out = capsys.readouterr().out
    assert "stop_reason = complete" in out


def test_cli_runs_the_sparse_scenario_and_refuses_without_failing(capsys):
    code = main(["run", "--fixture", "fixtures/insufficient_evidence.json", "--mock", "--quiet-summary"])
    assert code == EXIT_OK
    captured = capsys.readouterr()
    assert "stop_reason = insufficiency" in captured.out
    assert MSG_NO_ADJACENT_AUDIENCE in captured.out
    assert "insufficiency" in captured.err  # script-visible, not silent


def test_cli_refuses_a_live_run_in_milestone_one(capsys):
    code = main(["run", "--fixture", "portland_strong"])
    assert code == EXIT_CANNOT_RUN
    assert "--mock" in capsys.readouterr().err


# -- resolution edge cases (no new fixture files) ----------------------------


class _StubFixture:
    """Minimal stand-in for a loaded Fixture: only `programme` is used here."""

    def __init__(self, programme: list[dict]) -> None:
        self.programme = programme


class _PartialResolutionClient:
    """`external.<family>.ids` 404s; explicit ids resolve. Mirrors the live API's
    404-is-a-data-outcome behaviour without inventing a fixture scenario."""

    def __init__(self) -> None:
        from app.qloo.trace import TraceRecorder

        self.recorder = TraceRecorder(run_id="stub")
        self.calls: list[str] = []

    async def entities(self, *, external_ids=None, entity_ids=None, tool="resolve_entities"):
        from app.qloo.errors import NotFoundError
        from app.qloo.models import EntitiesResponse, ScoredEntity

        with self.recorder.record(
            tool=tool, endpoint="/entities", source="mock", data_status="fixture"
        ) as call:
            self.calls.append(tool)
            if external_ids is not None:
                call.set_result(status=404, result_count=0)
                raise NotFoundError(
                    "None of the supplied ids are present (live API returns 404 here).",
                    endpoint="/entities",
                    call_id=call.call_id,
                )
            call.set_result(status=200, result_count=1)
            return EntitiesResponse(
                call_id=call.call_id,
                source="mock",
                data_status="fixture",
                endpoint="/entities",
                results=[
                    ScoredEntity(
                        entity_id="id-1",
                        name="Resolved Title",
                        type="urn:entity:movie",
                        subtype="feature",
                        popularity=0.4,
                    )
                ],
            )


def test_a_404_while_resolving_is_recorded_as_a_data_outcome_not_an_outage():
    import asyncio

    from app.runner import _Budget, _resolve_programme

    fixture = _StubFixture(
        [
            {"title": "Findable", "year": 2024, "imdb_id": "tt1", "entity_id": "id-1"},
            {"title": "Unfindable", "year": 2024, "imdb_id": "tt2", "entity_id": "id-2"},
        ]
    )
    run = run_minimal_run()
    client = _PartialResolutionClient()

    asyncio.run(_resolve_programme(client, fixture, run, _Budget()))

    codes = {finding.code for finding in run.findings}
    assert "unresolved_external_ids" in codes, "a 404 must be recorded as a finding"
    assert len(run.resolution_call_ids) == 2  # the 404 call is still traced
    assert run.resolved_ids == ["id-1"], "only the genuinely returned entity may resolve"
    assert [item.title for item in run.unresolved_items] == ["Unfindable"]
    assert run.resolution_verdict is not None
    assert run.resolution_verdict.insufficient, "1 resolved title is below the evidence threshold"


def run_minimal_run():
    from app.runner import MilestoneRun

    return MilestoneRun(
        fixture_name="stub",
        fixture_path="stub.json",
        scenario="stub",
        fixture_notice="stub",
        data_status="fixture",
        description="stub",
    )
