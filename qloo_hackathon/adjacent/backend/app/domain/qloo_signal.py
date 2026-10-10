"""Shared, deterministic quality and temporal-selection rules for Qloo features.

Entity resolution is not cultural affinity. A resolved entity or its popularity
score may be useful metadata, but only non-empty, valid tags or a finite affinity
score count as a cultural signal. This module deliberately distinguishes those
cases so a row's existence cannot inflate feature coverage.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any

CULTURAL_SIGNAL = "CULTURAL_SIGNAL"
POPULARITY_ONLY = "POPULARITY_ONLY"
IDENTITY_ONLY = "IDENTITY_ONLY"
EMPTY_SNAPSHOT = "EMPTY_SNAPSHOT"
INVALID_SIGNAL_SCHEMA = "INVALID_SIGNAL_SCHEMA"


def parse_timestamp(value: Any) -> datetime | None:
    """Parse an ISO timestamp and normalize it to UTC; invalid timestamps return None."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def finite_number(value: Any) -> bool:
    """True for finite numeric data (including zero), excluding bools and numeric strings."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse_candidate_tags(raw: Any) -> tuple[list[Any], bool]:
    """Return schema-valid non-empty tags plus whether the supplied shape is valid.

    Supported tag values are non-empty strings or objects with a non-empty
    `name`, `label`, `tag`, `id`, or `value` string. A non-empty list of empty
    dictionaries/nulls is not a usable signal.
    """
    if raw is None or raw == "":
        return [], True
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return [], False
    if not isinstance(raw, list):
        return [], False

    valid: list[Any] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            valid.append(item.strip())
        elif isinstance(item, dict) and any(
            isinstance(item.get(key), str) and item[key].strip()
            for key in ("name", "label", "tag", "id", "value")
        ):
            valid.append(item)
        elif item not in (None, "", {}, []):
            return [], False
    return valid, True


def assess_feature(feature: dict[str, Any] | None) -> dict[str, Any]:
    """Classify a stored feature row by substance rather than row existence."""
    if not feature:
        return {"status": EMPTY_SNAPSHOT, "has_cultural_signal": False,
                "has_usable_feature": False, "valid_tag_count": 0}

    tags, tags_schema_valid = parse_candidate_tags(feature.get("candidate_tags", []))
    affinity = feature.get("qloo_affinity")
    has_affinity = finite_number(affinity)
    popularity = feature.get("qloo_popularity")
    has_popularity = finite_number(popularity)
    has_entity = bool(str(feature.get("qloo_entity_id") or "").strip())

    cultural = bool(tags) or has_affinity
    if cultural:
        status = CULTURAL_SIGNAL
    elif not tags_schema_valid:
        status = INVALID_SIGNAL_SCHEMA
    elif has_popularity:
        status = POPULARITY_ONLY
    elif has_entity:
        status = IDENTITY_ONLY
    else:
        status = EMPTY_SNAPSHOT

    return {
        "status": status,
        "has_cultural_signal": cultural,
        "has_usable_feature": cultural or has_popularity,
        "valid_tag_count": len(tags),
        "tags": tags,
        "has_affinity": has_affinity,
        "has_popularity": has_popularity,
    }


def latest_feature(
    features: list[dict[str, Any]],
    *,
    before: str | None = None,
    cultural_only: bool = False,
    usable_only: bool = False,
) -> dict[str, Any] | None:
    """Select the latest valid row before a cutoff using normalized timestamps.

    Rows with invalid timestamps are excluded. Empty or metadata-only rows do not
    mask an earlier row with a usable feature when `usable_only` is requested.
    """
    cutoff = parse_timestamp(before) if before is not None else None
    eligible: list[tuple[datetime, dict[str, Any]]] = []
    for feature in features:
        timestamp = parse_timestamp(feature.get("retrieved_at"))
        if timestamp is None or (before is not None and cutoff is None):
            continue
        if cutoff is not None and timestamp > cutoff:
            continue
        assessment = assess_feature(feature)
        if cultural_only and not assessment["has_cultural_signal"]:
            continue
        if usable_only and not assessment["has_usable_feature"]:
            continue
        eligible.append((timestamp, feature))
    return max(eligible, key=lambda pair: pair[0])[1] if eligible else None


def temporal_signal_status(
    eligible_feature: dict[str, Any] | None,
    all_features: list[dict[str, Any]],
    prediction_timestamp: str,
) -> str:
    """Return a truthful signal status for a specific prediction timestamp."""
    assessment = assess_feature(eligible_feature)
    if eligible_feature is not None:
        if assessment["status"] == CULTURAL_SIGNAL:
            return "CULTURAL_SIGNAL_AVAILABLE_AT_PREDICTION_TIME"
        if assessment["status"] == POPULARITY_ONLY:
            return "POPULARITY_ONLY_AT_PREDICTION_TIME"
        if assessment["status"] == INVALID_SIGNAL_SCHEMA:
            return "INVALID_SIGNAL_SCHEMA_AT_PREDICTION_TIME"
        if assessment["status"] == IDENTITY_ONLY:
            return "IDENTITY_ONLY_AT_PREDICTION_TIME"
        return "EMPTY_SNAPSHOT_AT_PREDICTION_TIME"

    cutoff = parse_timestamp(prediction_timestamp)
    later = []
    for feature in all_features:
        timestamp = parse_timestamp(feature.get("retrieved_at"))
        if timestamp and cutoff and timestamp > cutoff:
            later.append((timestamp, feature))
    if later:
        latest_later = max(later, key=lambda pair: pair[0])[1]
        status = assess_feature(latest_later)["status"]
        if status == CULTURAL_SIGNAL:
            return "RETROSPECTIVE_CULTURAL_SIGNAL"
        if status == POPULARITY_ONLY:
            return "RETROSPECTIVE_POPULARITY_ONLY"
        if status == INVALID_SIGNAL_SCHEMA:
            return "RETROSPECTIVE_INVALID_SIGNAL_SCHEMA"
        return "RETROSPECTIVE_EMPTY_OR_IDENTITY_ONLY"

    if all_features:
        if any(assess_feature(row)["status"] == INVALID_SIGNAL_SCHEMA for row in all_features):
            return "INVALID_SIGNAL_SCHEMA_ONLY"
        if any(assess_feature(row)["status"] == EMPTY_SNAPSHOT for row in all_features):
            return "EMPTY_SNAPSHOT_ONLY"
        if any(assess_feature(row)["status"] == IDENTITY_ONLY for row in all_features):
            return "IDENTITY_ONLY"
        return "NO_ELIGIBLE_FEATURE"
    return "NO_FEATURE"
