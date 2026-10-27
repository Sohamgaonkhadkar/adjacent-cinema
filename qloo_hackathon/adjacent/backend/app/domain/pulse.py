"""Audience Pulse — a pre-registered poll attached to a saved experiment.

The feature answers one narrow question: *did the audience feedback the creator
collected meet the bar the creator wrote down before collection started?*

Design rules
------------
* **The rule is written first.** A poll stores its question, options, decision
  rule and the experiment's hypothesis as a frozen snapshot at creation. The
  first submitted response freezes that definition at the database level (see
  the trigger in ``pulse_repository``), so voting can never rewrite the rule it
  is being judged against.
* **Arithmetic only.** Evaluation is deterministic: counts, a share, and a
  threshold the creator chose. There is no model, no ranking and no inference.
* **Inconclusive is a real outcome.** Below the creator's own minimum sample the
  result is INCONCLUSIVE — never SUPPORTED because "most people who answered
  agreed", and never a claim about an audience the sample does not represent.
* **No probability language.** Nothing here reports significance, confidence or
  predictive validity, because a self-selected poll cannot support any of them.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

PULSE_SCHEMA = "adjacent.audience-pulse/1"

MIN_OPTIONS = 2
MAX_OPTIONS = 5
MAX_QUESTION_CHARS = 240
MAX_OPTION_CHARS = 120

MIN_WINDOW_HOURS = 1
MAX_WINDOW_DAYS = 90

#: Hard ceiling on stored responses per poll. A public link needs a bound, and
#: this one is far above any realistic test screening while still finite.
MAX_RESPONSES_PER_POLL = 5000
MAX_POLLS_PER_EXPERIMENT = 3

#: The creator picks the minimum sample; this floor stops a 2-response "result".
MIN_RULE_RESPONSES = 5

RULE_KINDS = {"option_share_at_least"}

COLLECTION_OPEN = "OPEN"
COLLECTION_SCHEDULED = "SCHEDULED"
COLLECTION_CLOSED = "CLOSED"
COLLECTION_EXPIRED = "EXPIRED"

OUTCOME_SUPPORTED = "SUPPORTED"
OUTCOME_CONTRADICTED = "CONTRADICTED"
OUTCOME_INCONCLUSIVE = "INCONCLUSIVE"
OUTCOMES = {OUTCOME_SUPPORTED, OUTCOME_CONTRADICTED, OUTCOME_INCONCLUSIVE}

SAMPLE_LIMITS: tuple[str, ...] = (
    "Respondents choose to open the link, so the sample is self-selected and its size is "
    "whatever the link attracted. Nothing here is a population estimate.",
    "One recorded response per browser session, throttled per network address; a determined "
    "participant can clear the cookie and answer again. This is a small poll, not a ballot box.",
    "A share of responses is not attendance, ticket sales, revenue or an audience prediction, "
    "and it does not measure whether a film is any good.",
    "The decision rule was written before collection and is applied mechanically, so a "
    "CONTRADICTED result is a result — not a failed test.",
)


class PulseValidationError(ValueError):
    """A definition or submission that cannot be stored as supplied."""


class PulseClosedError(RuntimeError):
    """The poll is not accepting responses (scheduled, closed or expired)."""

    def __init__(self, status: dict[str, Any]) -> None:
        self.status = status
        super().__init__(status.get("reason") or "this poll is not accepting responses")


class PulseCapacityError(RuntimeError):
    """The poll reached its stored-response ceiling."""


def _parse_timestamp(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PulseValidationError(f"{field} must be an ISO-8601 timestamp")
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise PulseValidationError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise PulseValidationError(
            f"{field} must include a timezone offset so the collection window means one thing "
            "to every reader"
        )
    return parsed.astimezone(UTC)


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


def _now(moment: str | datetime | None) -> datetime:
    if moment is None:
        return datetime.now(UTC)
    if isinstance(moment, datetime):
        return moment if moment.tzinfo else moment.replace(tzinfo=UTC)
    return _parse_timestamp(moment, field="now")


def _clean_text(value: Any, *, field: str, limit: int) -> str:
    if not isinstance(value, str):
        raise PulseValidationError(f"{field} must be text")
    text = " ".join(value.split())
    if not text:
        raise PulseValidationError(f"{field} must not be empty")
    if "\n" in value:
        raise PulseValidationError(f"{field} must be a single line")
    if len(text) > limit:
        raise PulseValidationError(f"{field} must be at most {limit} characters")
    return text


def normalise_options(raw: Any) -> list[dict[str, str]]:
    """Return ``[{"option_id": "opt-1", "label": ...}]`` or raise.

    Ids are positional and stable: they are the ballot's identity, so a label
    can be re-read by a human later without the ids drifting.
    """
    if not isinstance(raw, list):
        raise PulseValidationError("options must be a list")
    if not MIN_OPTIONS <= len(raw) <= MAX_OPTIONS:
        raise PulseValidationError(
            f"a poll needs between {MIN_OPTIONS} and {MAX_OPTIONS} options"
        )
    options: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw, start=1):
        label = item.get("label") if isinstance(item, dict) else item
        cleaned = _clean_text(label, field="option label", limit=MAX_OPTION_CHARS)
        folded = cleaned.casefold()
        if folded in seen:
            raise PulseValidationError(f"option {cleaned!r} is listed twice")
        seen.add(folded)
        options.append({"option_id": f"opt-{index}", "label": cleaned})
    return options


def normalise_rule(raw: Any, options: list[dict[str, str]]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PulseValidationError("decision_rule must be an object")
    kind = raw.get("kind", "option_share_at_least")
    if kind not in RULE_KINDS:
        raise PulseValidationError(f"decision_rule.kind must be one of {sorted(RULE_KINDS)}")

    option_id = raw.get("option_id")
    labels = {option["option_id"]: option["label"] for option in options}
    if option_id not in labels:
        raise PulseValidationError("decision_rule.option_id must name one of this poll's options")

    threshold_raw = raw.get("threshold")
    try:
        threshold = float(threshold_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise PulseValidationError("decision_rule.threshold must be a number") from exc
    if not 0.0 < threshold <= 1.0:
        raise PulseValidationError("decision_rule.threshold must be greater than 0 and at most 1")

    minimum_raw = raw.get("min_responses", MIN_RULE_RESPONSES)
    try:
        minimum = int(minimum_raw)
    except (TypeError, ValueError) as exc:
        raise PulseValidationError("decision_rule.min_responses must be an integer") from exc
    if minimum < MIN_RULE_RESPONSES:
        raise PulseValidationError(
            f"decision_rule.min_responses must be at least {MIN_RULE_RESPONSES}: a smaller "
            "sample cannot separate the option from noise, so the rule would decide nothing"
        )
    if minimum > MAX_RESPONSES_PER_POLL:
        raise PulseValidationError(
            f"decision_rule.min_responses must be at most {MAX_RESPONSES_PER_POLL}"
        )

    rule = {
        "kind": kind,
        "option_id": option_id,
        "option_label": labels[option_id],
        "threshold": threshold,
        "min_responses": minimum,
    }
    rule["statement"] = describe_rule(rule)
    return rule


def describe_rule(rule: dict[str, Any]) -> str:
    """Deterministic plain-language rendering of a stored rule."""
    label = rule.get("option_label") or rule.get("option_id") or "the chosen option"
    threshold = float(rule.get("threshold") or 0)
    minimum = int(rule.get("min_responses") or 0)
    return (
        f"SUPPORTED when {threshold:.0%} or more of valid responses choose “{label}”, "
        f"provided at least {minimum} valid responses were recorded. "
        f"CONTRADICTED when that sample exists and the share is lower. "
        f"INCONCLUSIVE while fewer than {minimum} valid responses exist, when the poll has no "
        f"responses, or when collection has not finished and the creator says so."
    )


def normalise_definition(
    *,
    question: Any,
    options: Any,
    opens_at: Any,
    closes_at: Any,
    decision_rule: Any,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    """Validate and normalise a poll definition; raise ``PulseValidationError``."""
    reference = _now(now)
    clean_question = _clean_text(question, field="question", limit=MAX_QUESTION_CHARS)
    clean_options = normalise_options(options)
    rule = normalise_rule(decision_rule, clean_options)

    opens = _parse_timestamp(opens_at, field="opens_at")
    closes = _parse_timestamp(closes_at, field="closes_at")
    if closes <= opens:
        raise PulseValidationError("closes_at must be after opens_at")
    if closes - opens < timedelta(hours=MIN_WINDOW_HOURS):
        raise PulseValidationError(
            f"the collection window must be at least {MIN_WINDOW_HOURS} hour(s)"
        )
    if closes - opens > timedelta(days=MAX_WINDOW_DAYS):
        raise PulseValidationError(
            f"the collection window must be at most {MAX_WINDOW_DAYS} days"
        )
    if closes <= reference:
        raise PulseValidationError("closes_at must still be in the future")
    if opens > reference + timedelta(days=MAX_WINDOW_DAYS):
        raise PulseValidationError(
            f"opens_at must be within {MAX_WINDOW_DAYS} days; a far-future poll is not a plan"
        )

    return {
        "question": clean_question,
        "options": clean_options,
        "opens_at": _iso(opens),
        "closes_at": _iso(closes),
        "decision_rule": rule,
    }


def collection_status(poll: dict[str, Any], *, now: str | datetime | None = None) -> dict[str, Any]:
    """Where the collection window stands, and whether a response is accepted."""
    moment = _now(now)
    opens_at = _parse_timestamp(poll.get("opens_at"), field="opens_at")
    closes_at = _parse_timestamp(poll.get("closes_at"), field="closes_at")
    closed_at = poll.get("closed_at")

    if closed_at:
        closed = _parse_timestamp(closed_at, field="closed_at")
        return {
            "status": COLLECTION_CLOSED,
            "accepting_responses": False,
            "reason": f"Collection was closed by the owner at {_iso(closed)}.",
        }
    if moment < opens_at:
        return {
            "status": COLLECTION_SCHEDULED,
            "accepting_responses": False,
            "reason": f"Collection opens at {_iso(opens_at)}.",
        }
    if moment >= closes_at:
        return {
            "status": COLLECTION_EXPIRED,
            "accepting_responses": False,
            "reason": f"The collection window ended at {_iso(closes_at)}.",
        }
    return {
        "status": COLLECTION_OPEN,
        "accepting_responses": True,
        "reason": f"Collection is open until {_iso(closes_at)}.",
    }


def tabulate(poll: dict[str, Any], responses: list[dict[str, Any]]) -> dict[str, Any]:
    """Count the stored responses against this poll's options.

    Unrecognised option ids are counted separately rather than folded into a
    real option: a stored response that cannot be matched is a data problem the
    reader has to see.
    """
    counts = {option["option_id"]: 0 for option in poll.get("options", [])}
    unrecognised = 0
    for response in responses:
        option_id = response.get("option_id")
        if option_id in counts:
            counts[option_id] += 1
        else:
            unrecognised += 1
    total = sum(counts.values())
    options = []
    for option in poll.get("options", []):
        count = counts[option["option_id"]]
        options.append(
            {
                "option_id": option["option_id"],
                "label": option["label"],
                "count": count,
                "share": (count / total) if total else None,
            }
        )
    return {
        "total": total,
        "unrecognised": unrecognised,
        "options": options,
        "by_option": counts,
    }


def evaluate(
    poll: dict[str, Any],
    responses: list[dict[str, Any]],
    *,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    """Apply the stored rule to the stored responses. Deterministic, no inference."""
    moment = _now(now)
    status = collection_status(poll, now=moment)
    counts = tabulate(poll, responses)
    rule = dict(poll.get("decision_rule") or {})
    target = rule.get("option_id")
    minimum = int(rule.get("min_responses") or MIN_RULE_RESPONSES)
    threshold = float(rule.get("threshold") or 0.0)
    target_label = rule.get("option_label") or target
    target_count = counts["by_option"].get(target, 0)
    total = counts["total"]
    share = (target_count / total) if total else None
    remaining = max(0, minimum - total)

    outstanding: list[str] = []
    if remaining:
        outstanding.append(f"{remaining} more valid response(s) to reach the pre-registered minimum of {minimum}")
    if status["accepting_responses"]:
        outstanding.append("collection is still open, so the counts are not final")

    if total == 0:
        outcome = OUTCOME_INCONCLUSIVE
        rationale = (
            "No responses were recorded, so the rule has nothing to apply. This is an absence of "
            "evidence, not a contradiction."
        )
    elif total < minimum:
        outcome = OUTCOME_INCONCLUSIVE
        rationale = (
            f"{total} valid response(s) were recorded and the pre-registered rule requires at "
            f"least {minimum} before it decides anything. The share for “{target_label}” is "
            f"{share:.0%} of the responses received so far, which is not treated as a result."
        )
    elif share is not None and share >= threshold:
        outcome = OUTCOME_SUPPORTED
        rationale = (
            f"{target_count} of {total} valid responses ({share:.0%}) chose “{target_label}”, "
            f"at or above the {threshold:.0%} bar the creator set before collection began, with "
            f"the required minimum of {minimum} responses met."
        )
    else:
        outcome = OUTCOME_CONTRADICTED
        rationale = (
            f"{target_count} of {total} valid responses ({share:.0%}) chose “{target_label}”, "
            f"below the {threshold:.0%} bar set before collection began, with the required "
            f"minimum of {minimum} responses met."
        )

    return {
        "schema": PULSE_SCHEMA,
        "poll_id": poll.get("poll_id"),
        "experiment_id": poll.get("experiment_id"),
        "evaluated_at": _iso(moment),
        "collection": status,
        "counts": counts,
        "rule": rule,
        "rule_statement": rule.get("statement") or describe_rule(rule),
        "outcome": outcome,
        "rationale": rationale,
        "sample_size": total,
        "minimum_responses": minimum,
        "threshold": threshold,
        "target_option_id": target,
        "share": share,
        "remaining_evidence": outstanding,
        "limitations": list(SAMPLE_LIMITS),
    }


def public_poll(poll: dict[str, Any], *, now: str | datetime | None = None) -> dict[str, Any]:
    """What a participant with the link may see: the ballot, and nothing else.

    Counts stay hidden while collection is open so early answers cannot nudge
    later ones. The experiment id, hypothesis and decision rule are owner data
    and are not exposed here.
    """
    status = collection_status(poll, now=now)
    payload = {
        "schema": PULSE_SCHEMA,
        "question": poll.get("question"),
        "options": [
            {"option_id": option["option_id"], "label": option["label"]}
            for option in poll.get("options", [])
        ],
        "opens_at": poll.get("opens_at"),
        "closes_at": poll.get("closes_at"),
        "collection": status,
    }
    if not status["accepting_responses"]:
        counts = tabulate(poll, poll.get("responses", []))
        payload["counts"] = {
            "total": counts["total"],
            "options": [
                {
                    "option_id": option["option_id"],
                    "label": option["label"],
                    "count": option["count"],
                    "share": option["share"],
                }
                for option in counts["options"]
            ],
        }
    payload["limitations"] = list(SAMPLE_LIMITS)
    return payload


__all__ = [
    "COLLECTION_CLOSED",
    "COLLECTION_EXPIRED",
    "COLLECTION_OPEN",
    "COLLECTION_SCHEDULED",
    "MAX_OPTIONS",
    "MAX_RESPONSES_PER_POLL",
    "MIN_OPTIONS",
    "MIN_RULE_RESPONSES",
    "OUTCOMES",
    "OUTCOME_CONTRADICTED",
    "OUTCOME_INCONCLUSIVE",
    "OUTCOME_SUPPORTED",
    "PULSE_SCHEMA",
    "SAMPLE_LIMITS",
    "PulseCapacityError",
    "PulseClosedError",
    "PulseValidationError",
    "collection_status",
    "describe_rule",
    "evaluate",
    "normalise_definition",
    "public_poll",
    "tabulate",
]
