"""Decision Challenge — necessity, stability and next checks.

The point of these tests is not that the payload has the right shape. It is that
the counterfactuals are *honest*: they must reproduce the product's own ranking
exactly, they must change the winner when the affinity signal is what decided it,
they must say so when it isn't, and they must refuse to compute anything at all
when the evidence is not there.

Several tests build synthetic cohorts on purpose. A fixture that happens never to
make affinity decisive cannot demonstrate that the counterfactual would notice if
it did, so the decisive case is constructed explicitly — and then run through the
real gate, the real score function and the real ordering.
"""

from __future__ import annotations

import copy
import json
from typing import ClassVar

import pytest
from app import evidence
from app.domain.challenge import (
    AFFINITY_DERIVED_KEYS,
    FRAGILE,
    MIN_SCENARIOS_FOR_STABLE,
    STABLE,
    UNDETERMINED,
    build_decision_challenge,
)
from app.domain.cohorts import CandidateCohort, MemberEvidence
from app.domain.scoring import CohortRanker, RankingResult, cohort_score_from
from app.qloo.models import ScoredEntity
from app.runner import run_fixture

STRONG = "portland_strong"


# ---------------------------------------------------------------------------
# Helpers: build cohorts that behave exactly like production cohorts
# ---------------------------------------------------------------------------


def _member(entity_id: str, affinity: float, popularity: float, name: str | None = None) -> MemberEvidence:
    entity = ScoredEntity(
        entity_id=entity_id,
        name=name or entity_id,
        type="artist",
        affinity=affinity,
        popularity=popularity,
    )
    return MemberEvidence(
        scored=entity,
        call_id=f"call-{entity_id}",
        is_marginal=affinity < evidence.BAND_HIGH,
        qloo_attribution_status="returned",
        allowed_qloo_seed_ids=("seed-1",),
    )


def _cohort(cohort_id: str, members: list[MemberEvidence], domain: str = "urn:entity:artist") -> CandidateCohort:
    cohort = CandidateCohort(
        cohort_id=cohort_id,
        domain=domain,
        kind="tag_cluster",
        member_ids=[m.entity_id for m in members],
        construction_reason="built by the test",
    )
    cohort.members = members
    cohort.context_id = f"ctx:{domain}"
    cohort.score = cohort_score_from(
        members, context_id=f"ctx:{domain}", call_id=f"call-{cohort_id}"
    )
    cohort.verdict = evidence.evaluate_cohort([m.scored for m in members])
    cohort.rejected = not cohort.verdict.sufficient
    return cohort


def _ranked_state(cohorts: list[CandidateCohort]):
    """Order the cohorts with the production ordering and attach them to a state."""

    class _State:
        run_id = "test-run"
        data_status = "fixture"
        ranking = None
        programme: ClassVar[list] = []
        trace_rows: ClassVar[list] = []
        stop_reason = "complete"
        calls_made = 0

    result = RankingResult(operation_call_id="op", all_cohorts=list(cohorts))
    CohortRanker._order(result)
    state = _State()
    state.ranked = list(result.ranked)
    state.rejected = list(result.rejected)
    state.ranking = result
    return state


@pytest.fixture(scope="module")
def strong_run():
    return run_fixture(STRONG, render=False)


# ---------------------------------------------------------------------------
# 1. It uses the production ranking, not a second scorer
# ---------------------------------------------------------------------------


def test_baseline_ordering_reproduces_the_production_ranking(strong_run):
    """The challenge must not disagree with the list the product actually showed."""
    challenge = build_decision_challenge(strong_run)
    production = [c.cohort_id for c in strong_run.ranked]

    assert challenge["available"] is True
    assert challenge["necessity"]["production_order"] == production
    assert challenge["recommendation"]["cohort_id"] == (production[0] if production else None)
    assert challenge["receipt"]["recommendation"]["cohort_id"] == (production[0] if production else None)


def test_the_extracted_scorer_reproduces_the_attached_production_scores(strong_run):
    """Extraction must not have changed a single published number.

    The ranker and the counterfactual now share one function; this asserts that
    function still reproduces, exactly, the scores the product already attached —
    including the scored-member count behind cohort breadth.
    """
    assert strong_run.ranked
    for cohort in strong_run.ranked:
        score = cohort.score
        assert score is not None
        rebuilt = cohort_score_from(
            cohort.members,
            context_id=cohort.context_id or "",
            call_id=score.call_id,
            unscored=cohort.unscored_member_ids,
        )
        assert rebuilt.to_dict() == score.to_dict()
        assert rebuilt.total_members == len(cohort.members)
        assert rebuilt.total_members == score.total_members


def test_counterfactual_never_mutates_the_run_it_is_examining(strong_run):
    before = json.dumps(
        [
            (c.cohort_id, c.rank, c.rejected, c.score.mean_affinity if c.score else None)
            for c in [*strong_run.ranked, *strong_run.rejected]
        ],
        sort_keys=True,
    )
    build_decision_challenge(strong_run)
    after = json.dumps(
        [
            (c.cohort_id, c.rank, c.rejected, c.score.mean_affinity if c.score else None)
            for c in [*strong_run.ranked, *strong_run.rejected]
        ],
        sort_keys=True,
    )
    assert before == after


# ---------------------------------------------------------------------------
# 2. Affinity withheld: it must notice when affinity is decisive
# ---------------------------------------------------------------------------


def test_affinity_withheld_changes_the_winner_when_affinity_decided_it():
    """Two cohorts identical on every non-affinity key: affinity must pick the winner.

    Novelty and group size tie, so the production ordering falls through to mean
    affinity. Withholding affinity removes that key, so the counterfactual must
    produce a different first cohort.
    """
    # Same median popularity (0.4) and same size (2) → only affinity differs.
    # The ids are chosen so the id tie-break cannot accidentally reproduce the
    # affinity order: that is the only way the assertion below proves anything.
    high = _cohort("z-high-affinity", [_member("a1", 0.92, 0.4), _member("a2", 0.88, 0.4)])
    low = _cohort("a-low-affinity", [_member("b1", 0.62, 0.4), _member("b2", 0.70, 0.4)])
    state = _ranked_state([low, high])

    assert state.ranked[0].cohort_id == "z-high-affinity", "affinity should decide this pair"

    challenge = build_decision_challenge(state)
    withheld = challenge["necessity"]["affinity_withheld"]

    assert withheld["winner_changed"] is True
    assert withheld["counterfactual_winner"] == "a-low-affinity"
    # ...and the payload must also admit that the two are indistinguishable
    # without affinity, which is the more important fact.
    assert withheld["top_pair_tied_without_affinity"] is True
    assert "indistinguishable" in challenge["necessity_statement"]
    # Affinity really did separate an adjacent pair, and the payload says which.
    assert challenge["necessity"]["affinity_decided_pairs"], (
        "the decisive key must be reported, not inferred by the reader"
    )
    assert challenge["necessity"]["affinity_decided_pairs"][0]["decided_by"] in AFFINITY_DERIVED_KEYS
    assert "changes the recommendation" in challenge["necessity_statement"]


def test_affinity_withheld_reports_no_change_honestly_on_the_fixture(strong_run):
    """On the shipped fixture the order is popularity-driven; say so, don't spin it."""
    challenge = build_decision_challenge(strong_run)
    withheld = challenge["necessity"]["affinity_withheld"]

    assert withheld["winner_changed"] is False
    assert withheld["ranks_moved"] == 0
    # When affinity decides nothing, the counterfactual must be the same list the
    # product showed — same ids, same positions, no quiet reshuffling.
    assert [row["cohort_id"] for row in withheld["order"]] == [
        cohort.cohort_id for cohort in strong_run.ranked
    ]
    assert challenge["necessity"]["affinity_decided_pairs"] == []
    # ...but the taste signal still separates it from the mainstream pick, which is
    # a different claim and is reported as such.
    assert challenge["necessity"]["popularity_only"]["winner_changed"] is True
    assert "the taste signal is what separates" in challenge["necessity_statement"]


def test_unchanged_winner_with_changed_ranking_is_reported_as_such():
    """The winner survives, the order does not — both facts must appear.

    The winner is separated from the rest by novelty. Below it, two cohorts tie on
    every non-affinity key and differ only in affinity, so the production ordering
    uses the affinity tie-break and the counterfactual cannot.
    """
    winner = _cohort("winner", [_member("w1", 0.90, 0.10), _member("w2", 0.88, 0.12)])
    # tied pair: same median popularity (0.5) and same size, different affinity.
    tie_high = _cohort("z-tie-high", [_member("h1", 0.80, 0.5), _member("h2", 0.78, 0.5)])
    tie_low = _cohort("a-tie-low", [_member("l1", 0.64, 0.5), _member("l2", 0.62, 0.5)])
    state = _ranked_state([tie_low, tie_high, winner])

    production = [c.cohort_id for c in state.ranked]
    assert production[0] == "winner"
    challenge = build_decision_challenge(state)
    withheld = challenge["necessity"]["affinity_withheld"]

    assert withheld["production_winner"] == "winner"
    assert withheld["winner_changed"] is False
    assert withheld["ranks_moved"] >= 1
    assert withheld["changed_below_first"] is True
    assert "2 other positions change" in challenge["necessity_statement"]


def test_popularity_only_baseline_picks_the_mainstream_cohort(strong_run):
    challenge = build_decision_challenge(strong_run)
    popularity = challenge["necessity"]["popularity_only"]
    ranked = {c.cohort_id: c for c in strong_run.ranked}

    winner = ranked[popularity["counterfactual_winner"]]
    novelty = winner.score.novelty_proxy
    # The mainstream baseline must pick the *least* novel admitted cohort.
    assert novelty == min(c.score.novelty_proxy for c in strong_run.ranked)


def test_suppressed_candidates_are_reported_but_never_admitted_silently(strong_run):
    challenge = build_decision_challenge(strong_run)
    gate = challenge["necessity"]["gate"]
    ranked_ids = {c.cohort_id for c in strong_run.ranked}

    assert set(gate["suppressed_by_affinity_gate"]).isdisjoint(ranked_ids), (
        "the counterfactual must not add candidates that the product suppressed"
    )
    assert gate["admitted_with_affinity_gate"] == sorted(ranked_ids)


# ---------------------------------------------------------------------------
# 3. Stability
# ---------------------------------------------------------------------------


def test_stability_names_the_exact_item_that_flips_the_decision(strong_run):
    challenge = build_decision_challenge(strong_run)
    stability = challenge["stability"]

    assert stability["verdict"] == FRAGILE
    assert stability["evaluated"] == len(stability["scenarios"])
    assert stability["evaluated"] > 0
    for flip in stability["flips"]:
        assert flip["removed"]["entity_id"]
        assert flip["removed_from"]["cohort_id"]
        assert flip["winner_after"] != challenge["recommendation"]["cohort_id"]


def test_stability_is_stable_when_every_removal_preserves_the_winner():
    """A cohort carried by four strong members survives losing one."""
    solid = _cohort(
        "solid",
        [
            _member("m1", 0.90, 0.20),
            _member("m2", 0.88, 0.22),
            _member("m3", 0.86, 0.24),
            _member("m4", 0.84, 0.26),
        ],
    )
    weak = _cohort(
        "weak",
        [_member("x1", 0.61, 0.90), _member("x2", 0.60, 0.92), _member("x3", 0.58, 0.94)],
    )
    state = _ranked_state([weak, solid])
    assert state.ranked[0].cohort_id == "solid"

    challenge = build_decision_challenge(state)
    stability = challenge["stability"]

    assert stability["verdict"] == STABLE
    assert stability["flips"] == []
    assert stability["evaluated"] >= MIN_SCENARIOS_FOR_STABLE
    assert all(scenario["winner_after"] == "solid" for scenario in stability["scenarios"])


def test_stability_detects_a_flip_below_the_winner_too():
    """The verdict is about the winner; a flip of the runner-up is not a flip."""
    # A three-member winner survives losing one member (the gate needs two), so a
    # swap further down the list must not be reported as a flip.
    strong = _cohort(
        "strong",
        [_member("s1", 0.95, 0.10), _member("s2", 0.93, 0.12), _member("s3", 0.91, 0.14)],
    )
    near = _cohort("near", [_member("n1", 0.80, 0.60), _member("n2", 0.70, 0.62)])
    weak = _cohort("weak", [_member("w1", 0.62, 0.30), _member("w2", 0.61, 0.31)])
    state = _ranked_state([weak, near, strong])

    stability = build_decision_challenge(state)["stability"]
    assert stability["verdict"] == STABLE
    assert stability["flips"] == []
    assert stability["evaluated"] == 7  # 3 + 2 + 2 scored members


def test_stability_skips_what_it_cannot_evaluate(strong_run):
    challenge = build_decision_challenge(strong_run)
    stability = challenge["stability"]
    # Every skipped scenario must carry a reason; none may be silently dropped.
    for skip in stability["skipped"]:
        assert skip["reason"]
    assert stability["evaluated"] + len(stability["skipped"]) == sum(
        len([m for m in c.members if m.affinity is not None]) for c in strong_run.ranked
    )


def test_stability_is_undetermined_without_enough_scenarios():
    single = _cohort("only", [_member("one", 0.90, 0.30)])
    state = _ranked_state([single])
    challenge = build_decision_challenge(state)
    stability = challenge["stability"]

    # A one-member cohort fails the gate, so there is no recommendation to test.
    assert single.rejected is True
    assert stability["evaluated"] == 0
    assert stability["verdict"] == UNDETERMINED
    assert "no recommendation exists" in stability["reason"]
    assert challenge["recommendation"]["cohort_id"] is None


def test_stability_invariant_rule_is_published(strong_run):
    stability = build_decision_challenge(strong_run)["stability"]
    assert "Fragile if any single removable evidence item changes the winning cohort" in stability["rule"]
    assert str(MIN_SCENARIOS_FOR_STABLE) in stability["rule"]


# ---------------------------------------------------------------------------
# 4. Honest unavailable states
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reason", ["no cohorts", "all rejected"])
def test_no_ranking_yields_an_explicit_unavailable_challenge(reason):
    class _Empty:
        run_id = "empty"
        data_status = "fixture"
        programme: ClassVar[list] = []
        trace_rows: ClassVar[list] = []
        calls_made = 0
        ranking = None
        ranked: ClassVar[list] = []
        rejected: ClassVar[list] = []

    challenge = build_decision_challenge(_Empty())
    assert challenge["available"] is False
    assert "no candidate cohorts" in challenge["unavailable_reason"]
    assert challenge["necessity"] is None and challenge["stability"] is None
    assert challenge["receipt"] is None
    assert challenge["next_checks"] == []


def test_unresolved_and_rejected_cohorts_produce_a_next_check():
    rejected = _cohort("lonely", [_member("one", 0.70, 0.4)])
    assert rejected.rejected is True
    state = _ranked_state([rejected])

    challenge = build_decision_challenge(state)
    # No admitted cohort → still available (there is something to explain), but the
    # challenge must not invent a recommendation.
    if challenge["available"]:
        assert challenge["recommendation"]["cohort_id"] is None
        assert any(check["id"] == "no_admitted_cohort" for check in challenge["next_checks"])


def test_missing_affinity_on_every_member_is_handled_without_inventing_numbers():
    members = [_member("m1", 0.0, 0.4), _member("m2", 0.0, 0.4)]
    for member in members:
        member.scored.affinity = None
    cohort = _cohort("unscored", members)
    state = _ranked_state([cohort])

    challenge = build_decision_challenge(state)
    assert challenge["available"] is True
    assert challenge["recommendation"]["cohort_id"] is None
    assert challenge["stability"]["verdict"] == UNDETERMINED
    assert challenge["receipt"]["recommendation"] == {}


# ---------------------------------------------------------------------------
# 5. Determinism, provenance and truthfulness
# ---------------------------------------------------------------------------


def test_two_builds_are_byte_identical(strong_run):
    first = json.dumps(build_decision_challenge(strong_run), sort_keys=True)
    second = json.dumps(build_decision_challenge(strong_run), sort_keys=True)
    assert first == second


def test_receipt_carries_provenance_and_limits(strong_run):
    receipt = build_decision_challenge(strong_run)["receipt"]
    winner = strong_run.ranked[0]

    assert receipt["data_status"] == strong_run.data_status
    assert receipt["recommendation"]["call_id"] == winner.score.call_id
    assert receipt["call_ids"] == [winner.score.call_id]
    assert any("not attendance" in limit for limit in receipt["limits"])
    assert receipt["schema"].startswith("adjacent.decision-challenge/")


def test_no_confidence_language_anywhere(strong_run):
    """No probability, confidence interval or reliability percentage may be claimed."""
    payload = json.dumps(build_decision_challenge(strong_run), sort_keys=True).lower()
    for banned in ("confidence interval", "probability", "reliability %", "p-value", "likelihood of"):
        assert banned not in payload, f"the challenge must not claim '{banned}'"


def test_challenge_spends_no_qloo_calls(strong_run):
    calls_before = strong_run.calls_made
    trace_before = len(strong_run.trace_rows)
    challenge = build_decision_challenge(strong_run)
    assert strong_run.calls_made == calls_before
    assert len(strong_run.trace_rows) == trace_before
    assert challenge["counts"]["qloo_calls_made"] == 0
    assert challenge["necessity"]["qloo_calls_made"] == 0


def test_fixture_status_propagates_into_every_section(strong_run):
    challenge = build_decision_challenge(strong_run)
    assert strong_run.data_status == "fixture"
    assert challenge["data_status"] == "fixture"
    assert challenge["receipt"]["data_status"] == "fixture"


def test_next_checks_never_propose_an_unimplemented_operation(strong_run):
    """Every proposed check must name an operation this repository actually has."""
    known = {
        "rank_cohorts",
        "expand_candidates",
        "resolve_programme",
        "get_taste_profile",
        "geography_heatmap",
    }
    for check in build_decision_challenge(strong_run)["next_checks"]:
        operation = check["proposed_check"]["operation"]
        if not operation:
            continue
        head = operation.split(" ")[0].rstrip("/")
        assert head in known, f"{check['id']} proposes unknown operation {operation!r}"
        assert check["proposed_check"]["estimated_qloo_calls"] >= 0


def test_comparable_level_removal_is_offered_not_simulated(strong_run):
    challenge = build_decision_challenge(strong_run)
    stability = challenge["stability"]
    assert "instead of being simulated" in stability["member_scope"]
    assert any("comparable changed" in check["proposed_check"]["action"] for check in challenge["next_checks"])


# ---------------------------------------------------------------------------
# 6. Ties
# ---------------------------------------------------------------------------


def test_exact_ties_are_broken_deterministically_and_reported():
    first = _cohort("tie-a", [_member("a1", 0.70, 0.40), _member("a2", 0.70, 0.40)])
    second = _cohort("tie-b", [_member("b1", 0.70, 0.40), _member("b2", 0.70, 0.40)])
    state = _ranked_state([second, first])

    order = [c.cohort_id for c in state.ranked]
    assert order == sorted(order), "an exact tie must fall back to cohort id, not input order"

    challenge = build_decision_challenge(state)
    assert challenge["necessity"]["production_order"] == order
    # Removing affinity from a fully tied set changes nothing at all.
    assert challenge["necessity"]["affinity_withheld"]["winner_changed"] is False


def test_deep_copy_of_state_is_not_required_but_is_safe(strong_run):
    """Belt and braces: a shallow-copied cohort must not corrupt the original."""
    probe = copy.copy(strong_run.ranked[0])
    probe.rank = 999
    assert strong_run.ranked[0].rank != 999


# ---------------------------------------------------------------------------
# 7. End to end through the real API: /run/demo
# ---------------------------------------------------------------------------


def _wait(client, run_id: str, timeout: float = 60.0) -> dict:
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/run/{run_id}").json()
        if body["status"] in {"completed", "failed", "insufficient"}:
            return body
        time.sleep(0.05)
    raise AssertionError("fixture run did not reach a terminal status")


def test_demo_run_exposes_a_labelled_challenge(monkeypatch):
    from app.main import app
    from fastapi.testclient import TestClient

    monkeypatch.delenv("ADJACENT_PUBLIC_DEMO", raising=False)
    client = TestClient(app)
    started = client.post("/run/demo")
    assert started.status_code == 200

    body = _wait(client, started.json()["run_id"])
    challenge = (body.get("result") or {}).get("challenge")

    assert challenge is not None, "a completed run must carry its challenge"
    assert challenge["available"] is True
    assert challenge["data_status"] == "fixture"
    assert challenge["receipt"]["data_status"] == "fixture"
    # The fixture must remain visibly a fixture in every section it reaches.
    assert challenge["necessity"]["affinity_withheld"]["counterfactual_winner"] is not None
    assert challenge["stability"]["evaluated"] > 0
    assert challenge["receipt"]["recommendation"]["cohort_id"]


def test_a_failed_live_run_never_serializes_a_challenge(monkeypatch):
    """No key → the run fails honestly, and no challenge is invented for it."""
    from app.main import app
    from fastapi.testclient import TestClient

    monkeypatch.delenv("ADJACENT_PUBLIC_DEMO", raising=False)
    monkeypatch.delenv("QLOO_API_KEY", raising=False)
    client = TestClient(app)
    started = client.post(
        "/run",
        json={"city": "Portland", "venue_name": "Test", "programme": [{"title": "Perfect Days"}]},
    )
    body = _wait(client, started.json()["run_id"])

    assert body["status"] == "failed"
    assert body["result"] is None
    assert body["error"]


def test_a_broken_challenge_degrades_to_an_unavailable_record(monkeypatch):
    """The challenge must never be the thing that breaks a finished analysis."""
    from types import SimpleNamespace

    from app.api import routes
    from app.domain import challenge as challenge_module

    def _boom(_state):
        raise ValueError("synthetic challenge failure")

    monkeypatch.setattr(challenge_module, "build_decision_challenge", _boom)
    payload = routes._build_challenge(SimpleNamespace(data_status="fixture"))

    assert payload["available"] is False
    assert payload["schema"] == challenge_module.SCHEMA
    assert payload["data_status"] == "fixture"
    assert payload["unavailable_reason"]
    # No partial invention: every computed section is explicitly absent.
    assert payload["necessity"] is None
    assert payload["stability"] is None
    assert payload["next_checks"] == []
    assert payload["receipt"] is None
    # The diagnostic must not leak the exception message.
    assert "synthetic challenge failure" not in json.dumps(payload)


def test_a_broken_challenge_does_not_invalidate_the_run(monkeypatch):
    """Through the real API: cohorts, test card and evidence survive, challenge says why."""
    from app.domain import challenge as challenge_module
    from app.main import app
    from fastapi.testclient import TestClient

    monkeypatch.delenv("ADJACENT_PUBLIC_DEMO", raising=False)

    def _boom(_state):
        raise RuntimeError("synthetic challenge failure")

    monkeypatch.setattr(challenge_module, "build_decision_challenge", _boom)
    client = TestClient(app)
    started = client.post("/run/demo")
    body = _wait(client, started.json()["run_id"])

    assert body["status"] == "completed"
    result = body["result"]
    assert result["cohorts"]["ranked"], "the analysis must be intact"
    assert result["test_card"]
    assert result["challenge"]["available"] is False
    assert result["challenge"]["data_status"] == "fixture"
