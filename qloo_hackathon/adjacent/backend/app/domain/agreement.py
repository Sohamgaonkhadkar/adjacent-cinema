"""Order-agreement maths for the counterfactuals — pure, deterministic, no I/O.

The Decision Challenge compares a production ranking with two counterfactual
orderings of the same candidate pool. Two numbers answer "how much did the
ordering actually move?":

* **Top-k overlap** — how many of the first *k* positions are the same grouping.
  Easy to read, blunt, and insensitive to changes below the cut.
* **Kendall's tau-b** — a rank correlation over every grouping present in both
  orders. It moves when positions swap anywhere in the list, so it catches
  reshuffling that top-k overlap would miss.

Both orderings are strict sequences: each grouping appears once, and each sort
key ends with the cohort id, so two cohorts never occupy the same position. The
tau-b denominator's tie terms are therefore zero by construction, and tau-b
reduces to the permutation formula ``(concordant − discordant) / pairs``. The
implementation counts ties anyway (a duplicate id would otherwise inflate the
score) and reports how many ids it dropped.

Both are reported as *agreement between two orderings computed by this
application*, never as a probability, confidence or measure of correctness.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from typing import Any

#: The top-k cut used by the product (and named as such in the UI).
TOP_K = 5

#: The reader-facing description of these numbers. Deliberately free of the words
#: the product bans everywhere else (no "probability", "confidence", "likelihood"):
#: agreement between two orderings is a description of movement, not of certainty.
AGREEMENT_MEANING = (
    "Agreement between two orderings this application computed over the same candidate "
    "pool. It describes how much the ordering moved; it says nothing about whether the "
    "recommendation is right."
)


def top_k_overlap(
    left: Sequence[str],
    right: Sequence[str],
    *,
    k: int = TOP_K,
) -> dict[str, Any]:
    """How many of the first *k* groupings the two orderings share."""
    left_top = list(left[:k])
    right_top = list(right[:k])
    right_top_set = set(right_top)
    shared = [cid for cid in left_top if cid in right_top_set]
    denominator = min(k, len(left), len(right))
    return {
        "k": k,
        "shared": len(shared),
        "of": denominator,
        "fraction": (len(shared) / denominator) if denominator else None,
        "shared_ids": shared,
    }


def _ranks(order: Sequence[str]) -> dict[str, int]:
    return {cid: index for index, cid in enumerate(order)}


def _strict(order: Sequence[str]) -> tuple[list[str], int]:
    """Remove repeated ids, keeping first position, and report how many went."""
    seen: set[str] = set()
    kept: list[str] = []
    for cohort_id in order:
        if cohort_id in seen:
            continue
        seen.add(cohort_id)
        kept.append(cohort_id)
    return kept, len(order) - len(kept)


def kendall_tau_b(left: Sequence[str], right: Sequence[str]) -> dict[str, Any]:
    """Kendall's tau-b between two orderings, over the ids they share.

    ``left`` and ``right`` are ranked sequences of cohort ids. Because both are
    strict (unique ids; the sort key ends with the cohort id), the tie terms in
    the tau-b denominator are zero and the value equals the permutation
    formula — see the module docstring. Duplicate ids are dropped from the
    front of the sequence and reported, so a malformed ordering cannot inflate
    the correlation silently.
    """
    left_ids, left_dropped = _strict(left)
    right_ids, right_dropped = _strict(right)
    left_rank = _ranks(left_ids)
    right_rank = _ranks(right_ids)
    common = [cid for cid in left_ids if cid in right_rank]

    result: dict[str, Any] = {
        "method": "kendall_tau_b",
        "value": None,
        "n": len(common),
        "pairs": 0,
        "concordant": 0,
        "discordant": 0,
        "duplicates_removed": left_dropped + right_dropped,
        "meaning": AGREEMENT_MEANING,
    }
    if len(common) < 2:
        return result

    concordant = discordant = 0
    for a, b in itertools.combinations(common, 2):
        delta_left = left_rank[a] - left_rank[b]
        delta_right = right_rank[a] - right_rank[b]
        if (delta_left > 0) == (delta_right > 0):
            concordant += 1
        else:
            discordant += 1

    pairs = len(common) * (len(common) - 1) / 2
    result.update(
        {
            "concordant": concordant,
            "discordant": discordant,
            "pairs": int(pairs),
            "value": (concordant - discordant) / pairs,
        }
    )
    return result


def describe_agreement(overlap: dict[str, Any], tau: dict[str, Any]) -> str:
    """One deterministic sentence, or ``""`` when there is nothing to say."""
    value = tau.get("value")
    of = overlap.get("of") or 0
    shared = overlap.get("shared")
    if value is None or not of:
        return ""
    if shared == of and value > 0.999:
        return (
            f"The same {of} groupings sit at the top and the full ordering is unchanged "
            f"(tau-b {value:.2f})."
        )
    direction = "moves together" if value > 0 else "moves in the opposite direction"
    if value == 0:
        direction = "is uncorrelated"
    return (
        f"{shared} of the top {of} groupings are the same, and the full ordering {direction} "
        f"(tau-b {value:.2f}, {tau.get('n', 0)} groupings compared)."
    )
