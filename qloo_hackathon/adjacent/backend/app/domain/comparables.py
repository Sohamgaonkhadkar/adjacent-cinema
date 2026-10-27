"""Comparables audit: do the reference films actually share an audience?

Why this exists
---------------
A filmmaker assembles a reference list on the assumption that those films belong
together. That assumption is a *claim about two groups of people*, and Qloo has
an endpoint for exactly that shape of question. This module makes one bounded
``/v2/analysis/compare`` call per reference pair — at most three pairs — and
reports what the provider returned for each.

What it refuses to do
---------------------
* **It does not score the pair itself.** Qloo's compare response is not modelled
  in this repository, so a payload is read strictly (see ``pairwise.read_metric``):
  a recognised numeric field is reported by its exact key, and anything else is
  reported as ``no_readable_field`` with the observed key names and no number.
* **It does not treat a missing answer as a refutation.** "Qloo returned no field
  this build can read" is not "these two films are unrelated". Every state that
  carries no measurement says so in its own words, and the limitation travels
  with the payload.
* **It cannot break the Creator run.** The audit runs after the ranking has
  completed, its own failures are values, and an exhausted budget is reported per
  pair rather than raised. The Creator result is unaffected either way.

Only reference films that passed entity resolution are compared. Unresolved
references are listed, never guessed at.
"""

from __future__ import annotations

import itertools
from typing import Any

from ..qloo.models import RawResponse
from .pairwise import observed_keys, read_metric

SCHEMA = "adjacent.comparables-audit/1"

#: At most this many reference pairs are compared in one run. Three calls keep
#: the audit bounded and leave the run's remaining budget for scoring.
MAX_PAIRS = 3

PUBLIC_LIMITS: tuple[str, ...] = (
    "Each row is one Qloo comparison of two reference films. It describes those two "
    "groups as supplied; it is not a forecast of attendance, revenue or campaign performance.",
    "A pair with no readable value is unevaluated, not refuted: the absence of a Qloo "
    "field is not evidence that the two references are unrelated.",
    "The audit never changes the programme, the cohorts or the ranking. It only reports.",
)


def _film(item: Any) -> dict[str, Any]:
    """One resolved reference, reduced to what the audit needs to be auditable."""
    return {
        "title": getattr(item, "title", "") or "(untitled)",
        "year": getattr(item, "year", None),
        "entity_id": getattr(item, "resolved_entity_id", None),
        "resolved_name": getattr(item, "resolved_name", None),
        "entity_type": getattr(item, "entity_type", None) or "urn:entity:movie",
        "resolution_call_id": getattr(item, "source_call_id", None),
    }


def _unresolved(state: Any) -> list[dict[str, Any]]:
    return [
        {"title": getattr(item, "title", "") or "(untitled)", "year": getattr(item, "year", None)}
        for item in getattr(state, "unresolved_items", []) or []
    ]


def _base(*, data_status: str) -> dict[str, Any]:
    return {"schema": SCHEMA, "data_status": data_status, "limits": list(PUBLIC_LIMITS)}


def _row(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    status: str,
    reason: str,
    metric: dict[str, Any] | None = None,
    call_id: str | None = None,
    seen_keys: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "metric": metric,
        "call_id": call_id,
        "observed_keys": seen_keys or [],
        "a": left,
        "b": right,
    }


def _sentence(left: dict[str, Any], right: dict[str, Any], metric: dict[str, Any]) -> str:
    """One deterministic sentence, only when a value was actually returned."""
    key = metric.get("key")
    value = metric.get("value")
    direction = metric.get("direction")
    if not key or not isinstance(value, (int, float)):
        return ""
    if direction == "higher_is_closer":
        tail = "higher means the two reference groups overlap more"
    elif direction == "lower_is_closer":
        tail = "lower means the two reference groups overlap more"
    else:
        tail = "this build does not interpret the direction of that field"
    return (
        f"Qloo reported {key} = {value:.3f} between {left['title']} and {right['title']} "
        f"({tail})."
    )


async def compare_entity_groups(
    client: Any,
    group_a: list[str],
    group_b: list[str],
    *,
    filter_type: str,
    data_status: str,
    tool: str = "compare_entity_groups",
) -> dict[str, Any]:
    """One compare call for two groups of entity ids, read strictly.

    Shared by the Creator audit and the MCP tool so both report the same states
    from the same reader. Returns a value for every outcome; never raises.
    """
    try:
        response = await client.compare(
            a_signal_interests_entities=list(group_a),
            b_signal_interests_entities=list(group_b),
            filter_type=filter_type,
            model="descriptive",
            take=len(group_b) or 1,
            tool=tool,
        )
    except Exception as exc:
        # Optional evidence: report the failure, never raise it.
        return {
            "status": "failed",
            "reason": (
                "The comparison call did not complete. This is an upstream failure, not "
                "evidence about the two groups."
            ),
            "metric": None,
            "call_id": None,
            "observed_keys": [type(exc).__name__],
        }

    payload = response.data if isinstance(response, RawResponse) else {}
    payload = payload if isinstance(payload, dict) else {}
    metric = read_metric(payload)
    if metric is not None:
        return {
            "status": "measured",
            "reason": "The provider returned a numeric field this build recognises.",
            "metric": metric,
            "call_id": response.call_id,
            "observed_keys": [],
        }
    if data_status == "fixture":
        return {
            "status": "not_modelled_in_fixture",
            "reason": (
                "The labelled fixture run does not model this comparison response, so the "
                "call is traced but no value is shown."
            ),
            "metric": None,
            "call_id": response.call_id,
            "observed_keys": observed_keys(payload),
        }
    return {
        "status": "no_readable_field",
        "reason": (
            "The provider answered, but the response carried no numeric field this build is "
            "willing to interpret. The pair is unevaluated — not refuted."
        ),
        "metric": None,
        "call_id": response.call_id,
        "observed_keys": observed_keys(payload),
    }


async def build_comparables_audit(
    client: Any,
    state: Any,
    *,
    budget_remaining: int,
    max_pairs: int = MAX_PAIRS,
) -> dict[str, Any]:
    """Compare reference pairs, or explain honestly why a pair was not compared.

    Returns a dict and never raises. Every call is recorded in the client's trace,
    so each row's ``call_id`` is checkable against the run.
    """
    data_status = getattr(state, "data_status", "unknown") or "unknown"
    resolved = [_film(item) for item in (getattr(state, "resolved_items", None) or [])]
    unresolved = _unresolved(state)

    base = {
        **_base(data_status=data_status),
        "available": False,
        "summary": {},
        "pairs": [],
        "unresolved_references": unresolved,
        "not_evaluated": [],
        "not_evaluated_count": 0,
        "max_pairs": max_pairs,
    }

    if len(resolved) < 2:
        return {
            **base,
            "status": "insufficient_input",
            "reason": (
                "The audit needs at least two resolved reference films to compare. "
                f"This run resolved {len(resolved)}."
            ),
        }

    # Deterministic pair order: closest positions in the reference list first, so
    # three calls cover up to six different films instead of converging on the
    # first one. Ties break on the left index, then the right index.
    indexed = [
        (abs(right_index - left_index), left_index, right_index)
        for (left_index, _), (right_index, _) in itertools.combinations(
            list(enumerate(resolved)), 2
        )
    ]
    ordered_pairs = [(resolved[left], resolved[right]) for _, left, right in sorted(indexed)]
    selected = ordered_pairs[:max_pairs]
    skipped = ordered_pairs[max_pairs:]
    if skipped:
        base["not_evaluated_count"] = len(skipped)
        base["not_evaluated"] = [
            {
                "a": left["title"],
                "b": right["title"],
                "status": "not_evaluated_limit",
                "reason": (
                    f"Only {max_pairs} reference pairs are compared per run; this pair was "
                    "left out to keep the audit bounded."
                ),
            }
            for left, right in skipped[:5]
        ]

    rows: list[dict[str, Any]] = []
    upstream_failed = False
    for index, (left, right) in enumerate(selected):
        if upstream_failed:
            # One upstream failure is enough: retrying the remaining pairs would
            # spend the run's budget to reproduce the same error.
            rows.append(
                _row(
                    left,
                    right,
                    status="not_attempted_after_failure",
                    reason=(
                        "An earlier comparison call failed upstream, so this pair was not "
                        "attempted. Nothing is inferred about these two references."
                    ),
                )
            )
            continue
        if budget_remaining < 1:
            rows.append(
                _row(
                    left,
                    right,
                    status="unavailable_budget",
                    reason=(
                        "The run's call budget was needed for analysis, so this pair was not "
                        "compared. No value is inferred."
                    ),
                )
            )
            continue
        budget_remaining -= 1
        outcome = await compare_entity_groups(
            client,
            [left["entity_id"]],
            [right["entity_id"]],
            filter_type=left.get("entity_type") or "urn:entity:movie",
            data_status=data_status,
            tool=f"comparables_audit:{index + 1}",
        )
        if outcome["status"] == "failed":
            upstream_failed = True
        reason = outcome["reason"]
        if outcome["status"] == "measured" and outcome["metric"] is not None:
            reason = _sentence(left, right, outcome["metric"])
        rows.append(
            _row(
                left,
                right,
                status=outcome["status"],
                reason=reason,
                metric=outcome["metric"],
                call_id=outcome["call_id"],
                seen_keys=outcome["observed_keys"],
            )
        )

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    measured = counts.get("measured", 0)
    attempted = sum(
        counts.get(status, 0)
        for status in ("measured", "no_readable_field", "not_modelled_in_fixture", "failed")
    )

    return {
        **base,
        "available": bool(rows),
        "status": "evaluated" if attempted else "unevaluated",
        "reason": (
            f"{len(rows)} reference pair(s) attempted; {measured} returned a value this build "
            "can read."
            if attempted
            else "No reference pair was compared in this run."
        ),
        "summary": {
            "resolved_references": len(resolved),
            "unresolved_references": len(unresolved),
            "pairs_considered": len(ordered_pairs),
            "pairs_attempted": len(rows),
            "pairs_measured": measured,
            "pairs_without_readable_value": counts.get("no_readable_field", 0),
            "pairs_failed": counts.get("failed", 0),
            "pairs_not_attempted_after_failure": counts.get("not_attempted_after_failure", 0),
            "pairs_unavailable_budget": counts.get("unavailable_budget", 0),
            "pairs_not_modelled_in_fixture": counts.get("not_modelled_in_fixture", 0),
            "status_counts": counts,
        },
        "pairs": rows,
    }
