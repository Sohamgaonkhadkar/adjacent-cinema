"""Order-agreement maths for the counterfactuals — pure, deterministic, no I/O.

The Decision Challenge compares a production ranking with two counterfactual
orderings of the same candidate pool. Two numbers answer "how much did the
ordering actually move?":

* **Top-k overlap** — how many of the first *k* positions are the same grouping.
  Easy to read, blunt, and insensitive to changes below the cut.
* **Kendall's tau-b** — a rank correlation over every grouping present in both
  orders, with the tie correction. It moves when positions swap anywhere in the
  list, so it catches reshuffling that top-k overlap would miss.

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


def kendall_tau_b(left: Sequence[str], right: Sequence[str]) -> dict[str, Any]:
    """Kendall's tau-b between two orderings, over the ids they share.

    tau-b is used rather than tau-a because cohorts can tie: the counterfactual
    orderings are sorted on discrete keys, and two groupings can sit at the same
    novelty or popularity. Ties are counted as ties, not as agreement.
    """
    left_rank = _ranks(left)
    right_rank = _ranks(right)
    common = [cid for cid in left if cid in right_rank]

    result: dict[str, Any] = {
        "method": "kendall_tau_b",
        "value": None,
        "n": len(common),
        "concordant": 0,
        "discordant": 0,
        "ties_left": 0,
        "ties_right": 0,
        "meaning": AGREEMENT_MEANING,
    }
    if len(common) < 2:
        return result

    concordant = discordant = ties_left = ties_right = 0
    for a, b in itertools.combinations(common, 2):
        dl = left_rank[a] - left_rank[b]
        dr = right_rank[a] - right_rank[b]
        if dl == 0 and dr == 0:  # pragma: no cover - one id cannot hold two ranks
            continue
        if dl == 0:
            ties_left += 1
        elif dr == 0:
            ties_right += 1
        elif (dl > 0) == (dr > 0):
            concordant += 1
        else:
            discordant += 1

    pairs = len(common) * (len(common) - 1) / 2
    denominator = ((pairs - ties_left) * (pairs - ties_right)) ** 0.5
    result.update(
        {
            "concordant": concordant,
            "discordant": discordant,
            "ties_left": ties_left,
            "ties_right": ties_right,
            "value": (concordant - discordant) / denominator if denominator else None,
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
