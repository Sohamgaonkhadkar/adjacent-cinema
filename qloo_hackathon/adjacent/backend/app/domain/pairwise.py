"""Pairwise cohort comparison over Qloo's ``/v2/analysis/compare``.

Why this exists
---------------
The Decision Challenge can already say *"these two cohorts are within noise of
each other"* from a run's own numbers. It cannot say whether the two groupings
share an audience — that is a question about two groups, and Qloo has an
endpoint for exactly that. This module makes **one** bounded call to it, for the
top two ranked cohorts, and nothing else.

What it refuses to do
---------------------
* **It does not guess the response schema.** Qloo's public compare reference
  documents request parameters, not the response payload contract. Until an
  official response schema or a verified provider sample is recorded, every
  provider response is reported as `unsupported_response_shape` with the
  observed key **names** and no metric value. A familiar-looking field name is
  not proof of its semantics or direction.
* **It does not describe an unverified number as a probability, lift or
  forecast.** This build surfaces no compare metric until the response schema is
  verified, so it emits no numerical interpretation sentence for this endpoint.
* **It does not compare across entity types.** ``filter.type`` is a required
  parameter, and two cohorts from different types cannot be compared in one
  call. That case is reported as ``not_applicable`` with the reason, never
  approximated by comparing a movie with an artist.

The call is budgeted by the caller and costs at most one Qloo call. Every
outcome — including refusal and failure — is a value, never an exception that
could take down a completed run.
"""

from __future__ import annotations

from typing import Any

from ..qloo.models import RawResponse

SCHEMA = "adjacent.pairwise-comparison/1"

#: Failure kinds raised before any request leaves the process. A comparison that
#: fails this way has spent no provider call and must not be charged to the run.
LOCAL_ONLY_FAILURES: frozenset[str] = frozenset(
    {
        "param_error",
        "unverified_parameter",
        "deprecated_parameter",
        "invalid_combination",
        "invalid_filter_type",
        "invalid_value",
    }
)

#: Group size accepted by the compare call for one cohort. Kept small on purpose:
#: the comparison is about a handful of named entities, not a bulk scan.
MAX_GROUP_MEMBERS = 10

PUBLIC_LIMITS: tuple[str, ...] = (
    "A pairwise comparison describes the two groups you supplied. It is not a forecast of "
    "attendance, revenue, audience size or campaign performance.",
    "The comparison holds the retrieved candidates fixed; it does not re-query Qloo for new ones.",
    "Comparisons are only meaningful within one entity type and one location scope, which is why "
    "the call is skipped when the two cohorts are not the same type.",
)


def _domain_name(domain: str) -> str:
    """``urn:entity:book`` → ``book``. Reader-facing text never carries a urn."""
    return (domain or "unknown").replace("urn:entity:", "").replace("urn:", "") or "unknown"


def read_metric(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return no metric until Qloo documents this endpoint response schema.

    The public Analysis Compare reference documents the required request
    parameters but does not specify response fields. Plausible-looking keys
    such as "overlap" or "distance" are not a verified contract, and their
    meaning/direction cannot be safely inferred from their names. Keep the
    response available for diagnostics through observed_keys, but do not
    interpret any numeric value until an official response contract or a
    verified provider sample is recorded.
    """
    return None

def observed_keys(payload: dict[str, Any]) -> list[str]:
    """Top-level key names only — never their values, which may be provider data."""
    return sorted(str(key) for key in payload)[:24]


def _base(*, data_status: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "data_status": data_status,
        "limits": list(PUBLIC_LIMITS),
    }


def _refusal(reason_code: str, reason: str, *, data_status: str) -> dict[str, Any]:
    return {
        **_base(data_status=data_status),
        "available": False,
        "status": reason_code,
        "reason": reason,
        "metric": None,
        "cohorts": None,
        "call_id": None,
        "observed_keys": [],
        "call_attempted": False,
    }


def comparison_targets(ranking: Any) -> tuple[Any, Any] | None:
    """The winning cohort and the best *same-type* cohort beside it.

    Comparing the winner with the cohort directly below it is only possible when
    both are the same entity type, which is often not the case — a programme can
    rank an artist first and a book second. Rather than refuse in that case, the
    comparison pairs the winner with the highest-ranked cohort that shares its
    type and reports which position that cohort holds, so the reader always
    knows exactly which two groups were compared.
    """
    ranked = list(getattr(ranking, "ranked", None) or [])
    if len(ranked) < 2:
        return None
    winner = ranked[0]
    for other in ranked[1:]:
        if getattr(other, "domain", None) == getattr(winner, "domain", None):
            return winner, other
    return None


def _rank_of(ranking: Any, cohort: Any) -> int | None:
    for position, candidate in enumerate(getattr(ranking, "ranked", None) or [], start=1):
        if candidate is cohort:
            return position
    return None


def _label_for(cohort: Any) -> str:
    """``artist · Brian Eno`` — the same shape the rest of the product uses."""
    domain = _domain_name(getattr(cohort, "domain", ""))
    members = getattr(cohort, "members", None) or []
    top = next((m.name for m in members if getattr(m, "name", None)), None)
    kind = getattr(cohort, "kind", "") or ""
    return f"{domain} · {top or kind or 'unnamed grouping'}"


def _group(cohort: Any) -> dict[str, Any]:
    members = [m for m in (getattr(cohort, "members", None) or []) if m.affinity is not None]
    members.sort(key=lambda m: (-(m.affinity or 0.0), m.entity_id))
    chosen = members[:MAX_GROUP_MEMBERS]
    return {
        "cohort_id": getattr(cohort, "cohort_id", ""),
        "domain": getattr(cohort, "domain", ""),
        "rank": None,
        "member_count": len(members),
        "entity_ids": [m.entity_id for m in chosen],
        "member_names": [m.name for m in chosen if m.name],
        "truncated": len(members) > len(chosen),
    }


async def build_pairwise_comparison(
    client: Any,
    ranking: Any,
    *,
    data_status: str,
    budget_remaining: int,
    label_for: Any = None,
) -> dict[str, Any]:
    """Compare the top two ranked cohorts, or explain honestly why not.

    Never raises: a provider error becomes a ``failed`` record so a completed
    analysis keeps its result.
    """
    targets = comparison_targets(ranking)
    if targets is None:
        ranked = list(getattr(ranking, "ranked", None) or [])
        if len(ranked) < 2:
            reason = "A comparison needs two ranked cohorts and this run produced fewer than two."
        else:
            winner_type = _domain_name(getattr(ranked[0], "domain", ""))
            others: list[str] = []
            for cohort in ranked[1:]:
                name = _domain_name(getattr(cohort, "domain", ""))
                if name != winner_type and name not in others:
                    others.append(name)
            reason = (
                f"The winner is a grouping of {winner_type} entities and every other ranked "
                f"cohort is a different type ({', '.join(others) or 'none named'}); a comparison "
                "is only defined within one type."
            )
        return _refusal("not_applicable", reason, data_status=data_status)

    ranked = list(getattr(ranking, "ranked", None) or [])
    winner, other = targets
    domain_a = getattr(winner, "domain", "") or ""

    group_a = _group(winner)
    group_b = _group(other)
    group_a["rank"] = _rank_of(ranking, winner)
    group_b["rank"] = _rank_of(ranking, other)
    if not group_a["entity_ids"] or not group_b["entity_ids"]:
        return _refusal(
            "not_applicable",
            "One of the top two cohorts has no scored members, so there is nothing to compare.",
            data_status=data_status,
        )
    if budget_remaining < 1:
        return _refusal(
            "unavailable_budget",
            "The run's call budget was needed for scoring, so no comparison call was made.",
            data_status=data_status,
        )

    if label_for is None:
        cohorts = {
            "a": {**group_a, "label": _label_for(winner), "cohort_id": group_a["cohort_id"]},
            "b": {**group_b, "label": _label_for(other), "cohort_id": group_b["cohort_id"]},
        }
    else:  # explicit resolver (tests and callers that already hold a label map)
        cohorts = {
            "a": {**group_a, "label": label_for(group_a["cohort_id"])},
            "b": {**group_b, "label": label_for(group_b["cohort_id"])},
        }

    try:
        response = await client.compare(
            a_signal_interests_entities=group_a["entity_ids"],
            b_signal_interests_entities=group_b["entity_ids"],
            filter_type=domain_a,
            # `descriptive` describes the two groups as supplied. `predictive`
            # would imply an outcome claim this product does not make.
            model="descriptive",
            take=MAX_GROUP_MEMBERS,
            tool="compare_cohorts",
        )
    # A comparison is optional evidence: any failure is reported, never raised.
    except Exception as exc:
        # Report the failure's classification (timeout, authentication, upstream,
        # …) and its HTTP status, but never the exception text: it can carry
        # response bodies. A parameter error never reached the provider, so the
        # call is not counted as spent.
        kind = getattr(exc, "kind", None)
        status = getattr(exc, "status", None)
        return {
            **_base(data_status=data_status),
            "available": False,
            "status": "failed",
            "reason": (
                "The comparison call did not complete. The recommendation above is unaffected; "
                "no comparison is shown rather than an estimated one."
            ),
            "error_type": type(exc).__name__,
            "error_kind": kind if isinstance(kind, str) else None,
            "error_status": status if isinstance(status, int) else None,
            "call_attempted": kind not in LOCAL_ONLY_FAILURES,
            "metric": None,
            "cohorts": cohorts,
            "call_id": getattr(exc, "call_id", None),
            "observed_keys": [],
        }

    payload = response.data if isinstance(response, RawResponse) else {}
    payload = payload if isinstance(payload, dict) else {}
    metric = read_metric(payload)
    if metric is None and data_status == "fixture":
        return {
            **_base(data_status=data_status),
            "available": False,
            "status": "not_modelled_in_fixture",
            "reason": (
                "The labelled fixture run does not model this comparison response. The call is "
                "made and traced, but no value is shown; only a measured run can report one."
            ),
            "metric": None,
            "cohorts": cohorts,
            "call_id": response.call_id,
            "observed_keys": observed_keys(payload),
            "call_attempted": True,
        }
    if metric is None:
        return {
            **_base(data_status=data_status),
            "available": False,
            "status": "unsupported_response_shape",
            "reason": (
                "The provider answered, but its response carried no numeric field this product is "
                "willing to interpret. The call is recorded; no comparison value is shown."
            ),
            "metric": None,
            "cohorts": cohorts,
            "call_id": response.call_id,
            "observed_keys": observed_keys(payload),
            "call_attempted": True,
        }

    return {
        **_base(data_status=data_status),
        "available": True,
        "status": "measured",
        "reason": "",
        "metric": metric,
        "cohorts": cohorts,
        "call_id": response.call_id,
        "observed_keys": [],
        "call_attempted": True,
    }


def interpret(comparison: dict[str, Any] | None) -> str:
    """Do not interpret Compare response fields until Qloo's schema is verified.

    The public endpoint reference documents request parameters but not the
    response payload. Even a numeric-looking field with a plausible name must
    not be converted into a claim about overlap or similarity.
    """
    return ""
