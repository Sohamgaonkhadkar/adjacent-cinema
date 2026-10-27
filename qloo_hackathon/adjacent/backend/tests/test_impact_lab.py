"""The Qloo Impact Lab: three conditions over one fixed candidate pool.

The point of these tests is that the counterfactual outputs are *computed* from
a run's own numbers, are comparable across conditions, and never claim more than
an ordering change.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from app.domain.agreement import (
    AGREEMENT_MEANING,
    TOP_K,
    describe_agreement,
    kendall_tau_b,
    top_k_overlap,
)
from app.domain.challenge import build_decision_challenge
from app.runner import run_fixture_async

# ---------------------------------------------------------------------------
# Order-agreement maths
# ---------------------------------------------------------------------------


def test_top_k_overlap_counts_shared_positions_and_handles_short_lists() -> None:
    left = ["a", "b", "c", "d", "e", "f"]
    assert top_k_overlap(left, left)["shared"] == TOP_K
    assert top_k_overlap(left, left)["fraction"] == 1.0

    rotated = ["b", "c", "d", "e", "f", "a"]
    overlap = top_k_overlap(left, rotated)
    assert overlap["shared"] == 4  # b, c, d, e remain in the top five
    assert overlap["of"] == 5
    assert overlap["shared_ids"] == ["b", "c", "d", "e"]

    short = top_k_overlap(["a", "b"], ["b", "a"])
    assert short["of"] == 2
    assert short["shared"] == 2


def test_kendall_tau_b_is_exact_for_known_orderings() -> None:
    assert kendall_tau_b(["a", "b", "c"], ["a", "b", "c"])["value"] == pytest.approx(1.0)
    assert kendall_tau_b(["a", "b", "c"], ["c", "b", "a"])["value"] == pytest.approx(-1.0)

    rotated = kendall_tau_b(["a", "b", "c"], ["b", "c", "a"])
    # one concordant pair (b,c), two discordant (a,b) and (a,c)
    assert rotated["value"] == pytest.approx(-1 / 3)
    assert rotated["concordant"] == 1
    assert rotated["discordant"] == 2
    assert rotated["n"] == 3


def test_kendall_tau_b_is_undefined_rather_than_zero_when_it_cannot_be_computed() -> None:
    for left, right in (([], []), (["a"], ["a"]), (["a", "b"], ["c", "d"])):
        result = kendall_tau_b(left, right)
        assert result["value"] is None
        assert result["method"] == "kendall_tau_b"
        assert result["meaning"] == AGREEMENT_MEANING


def test_agreement_sentence_distinguishes_unchanged_from_moved() -> None:
    same = describe_agreement(top_k_overlap(["a"], ["a"]), kendall_tau_b(["a", "b"], ["a", "b"]))
    assert "unchanged" in same

    moved = describe_agreement(
        top_k_overlap(["a", "b", "c", "d"], ["b", "c", "d", "a"]),
        kendall_tau_b(["a", "b", "c", "d"], ["b", "c", "d", "a"]),
    )
    assert "of the top" in moved
    assert "tau-b" in moved
    assert "probability" not in moved.lower()
    assert "confidence" not in moved.lower()

    assert describe_agreement({"of": 0, "shared": 0}, {"value": None}) == ""


# ---------------------------------------------------------------------------
# The challenge payload: three conditions, one pool
# ---------------------------------------------------------------------------


def _challenge() -> dict:
    state = asyncio.run(run_fixture_async("portland_strong", render=False))
    return build_decision_challenge(state)


def test_challenge_reports_the_three_conditions_over_the_same_pool() -> None:
    challenge = _challenge()
    conditions = challenge["necessity"]["conditions"]

    assert set(conditions) == {"full_analysis", "affinity_withheld", "popularity_only"}
    full = conditions["full_analysis"]
    assert full["winner"] == challenge["recommendation"]["cohort_id"]
    # The full analysis compared with itself cannot have moved.
    assert full["top_overlap"]["fraction"] == 1.0
    assert full["rank_correlation"]["value"] == pytest.approx(1.0)

    for name in ("affinity_withheld", "popularity_only"):
        condition = conditions[name]
        assert condition["definition"]
        assert 0 <= condition["top_overlap"]["shared"] <= condition["top_overlap"]["of"]
        value = condition["rank_correlation"]["value"]
        assert value is None or -1.0 <= value <= 1.0

    # Comparing an ordering with itself is not a finding: every condition makes
    # zero Qloo calls, and the pool is the same list in every condition.
    assert all(condition["qloo_calls_made"] == 0 for condition in conditions.values())


def test_condition_numbers_match_the_counterfactual_they_summarise() -> None:
    challenge = _challenge()
    necessity = challenge["necessity"]
    withheld = necessity["affinity_withheld"]

    assert necessity["conditions"]["affinity_withheld"]["top_overlap"] == withheld["top_overlap"]
    assert (
        necessity["conditions"]["affinity_withheld"]["rank_correlation"]
        == withheld["rank_correlation"]
    )
    assert withheld["agreement_statement"]
    # The sentence names no cohort identifier at all.
    assert "urn:" not in withheld["agreement_statement"]


def test_receipt_carries_the_condition_summaries() -> None:
    receipt = _challenge()["receipt"]
    conditions = receipt["conditions"]

    assert set(conditions) == {"affinity_withheld", "popularity_only"}
    for condition in conditions.values():
        assert "winner_changed" in condition
        assert "top_overlap" in condition
        assert "rank_correlation" in condition


def test_no_banned_certainty_language_reaches_the_payload() -> None:
    payload = json.dumps(_challenge(), sort_keys=True).lower()
    for banned in ("confidence interval", "probability", "reliability %", "p-value", "likelihood of"):
        assert banned not in payload, banned


def test_the_lab_spends_no_qloo_calls() -> None:
    state = asyncio.run(run_fixture_async("portland_strong", render=False))
    calls_before = state.calls_made
    challenge = build_decision_challenge(state)
    assert state.calls_made == calls_before
    assert challenge["counts"]["qloo_calls_made"] == 0
