"""Regression tests for adaptive, explicitly labelled Creator evidence gates."""

from __future__ import annotations

import pytest
from app.evidence import (
    MIN_RESOLVED_TITLES,
    evaluate_programme_resolution,
)


def test_three_verified_reference_works_receive_standard_coverage() -> None:
    verdict = evaluate_programme_resolution(3, 0)

    assert verdict.sufficient is True
    assert verdict.reason_code == "resolved_ok"
    assert verdict.stats["coverage"] == "standard"
    assert verdict.stats["resolved"] == 3
    assert verdict.stats["min_required"] == MIN_RESOLVED_TITLES


def test_two_verified_reference_works_can_continue_exploratorily() -> None:
    verdict = evaluate_programme_resolution(2, 0)

    assert verdict.sufficient is True
    assert verdict.reason_code == "exploratory_resolved_ok"
    assert verdict.stats["coverage"] == "exploratory"
    assert verdict.stats["limitation"] == "limited_reference_works"
    assert "candidate-cohort gates" in verdict.message.lower()


def test_one_verified_work_requires_two_exact_theme_matches() -> None:
    enough = evaluate_programme_resolution(1, 2)
    not_enough = evaluate_programme_resolution(1, 1)

    assert enough.sufficient is True
    assert enough.reason_code == "mixed_signal_resolution"
    assert enough.stats["limitation"] == "one_reference_work"
    assert not_enough.sufficient is False
    assert not_enough.reason_code == "insufficient_resolved_titles"


def test_tag_driven_exploration_requires_three_exact_theme_matches() -> None:
    enough = evaluate_programme_resolution(0, 3)
    not_enough = evaluate_programme_resolution(0, 2)

    assert enough.sufficient is True
    assert enough.reason_code == "tag_driven_resolution"
    assert enough.stats["limitation"] == "no_verified_reference_works"
    assert not_enough.sufficient is False


def test_strong_film_coverage_does_not_require_theme_tag_matches() -> None:
    verdict = evaluate_programme_resolution(4, 0)

    assert verdict.sufficient is True
    assert verdict.reason_code == "resolved_ok"
    assert verdict.stats["coverage"] == "standard"


def test_no_usable_signals_still_stops_and_explains_the_gate() -> None:
    verdict = evaluate_programme_resolution(0, 0)

    assert verdict.sufficient is False
    assert verdict.reason_code == "insufficient_resolved_titles"
    assert "two verified works" in verdict.message
    assert "three exact-matched Qloo theme tags" in verdict.message
    assert verdict.stats["coverage"] == "insufficient"
    assert verdict.stats["matched_theme_tags"] == 0


@pytest.mark.parametrize(
    ("films", "tags"),
    [(-1, 0), (0, -1)],
)
def test_negative_signal_counts_are_rejected(films: int, tags: int) -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        evaluate_programme_resolution(films, tags)
