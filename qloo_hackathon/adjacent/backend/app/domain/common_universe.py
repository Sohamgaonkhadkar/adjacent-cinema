"""Independent-metadata versus live-Qloo film ranking on one frozen universe.

This is a *separate research experiment*, NOT the production cohort challenge.
It tests whether Qloo changes film ordering for metadata-selected candidates.
It never describes a ranking difference as accuracy, incremental outcome value,
attendance uplift, or evidence of a better choice.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any

from .agreement import kendall_tau_b, top_k_overlap

SCHEMA = "adjacent.common-universe/1"
REQUIRED_FILM_FIELDS = ("title", "year", "genres")
FORBIDDEN_METADATA_FIELDS = frozenset({
    "qloo_entity_id", "qloo_affinity", "qloo_popularity", "affinity",
    "popularity", "qloo_score", "qloo_rank", "recommended_by_qloo",
})


class InvalidStudy(ValueError):
    """A study cannot be run without a defensible independent comparison."""


def film_key(film: Mapping[str, Any]) -> str:
    title = film.get("title")
    year = film.get("year")
    if not isinstance(title, str) or not title.strip():
        raise InvalidStudy("Every film must have a nonempty title")
    if isinstance(year, bool) or not isinstance(year, int) or not 1888 <= year <= 2100:
        raise InvalidStudy("Every film must have a valid integer release year")
    return f"{title.strip().casefold()}|{year}"


def _catalog(films: Any, *, role: str) -> list[dict[str, Any]]:
    if not isinstance(films, list) or not films:
        raise InvalidStudy(f"{role} must be a nonempty list")
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in films:
        if not isinstance(row, dict):
            raise InvalidStudy(f"{role} entries must be objects")
        unexpected = set(row) - {"title", "year", "genres", "country", "director", "imdb_id"}
        if unexpected:
            raise InvalidStudy(f"Unexpected metadata fields in {role}: {sorted(unexpected)}")
        key = film_key(row)
        if key in seen:
            raise InvalidStudy(f"Duplicate film in {role}: {key}")
        seen.add(key)
        forbidden = FORBIDDEN_METADATA_FIELDS.intersection(row)
        if forbidden or any(str(k).startswith("qloo_") for k in row):
            raise InvalidStudy(f"{role} must be frozen without Qloo-derived fields")
        genres = row.get("genres")
        if not isinstance(genres, list) or not genres or any(
            not isinstance(g, str) or not g.strip() for g in genres
        ):
            raise InvalidStudy(f"{role} film {key} needs nonempty genre metadata")
        for field in ("country", "director", "imdb_id"):
            if field in row and row[field] is not None and not isinstance(row[field], str):
                raise InvalidStudy(f"{field} must be a string or absent")
        cleaned.append({
            "key": key,
            "title": row["title"].strip(),
            "year": row["year"],
            "genres": sorted(set(g.strip().casefold() for g in genres)),
            "country": str(row.get("country") or "").strip().casefold(),
            "director": str(row.get("director") or "").strip().casefold(),
            "imdb_id": str(row.get("imdb_id") or "").strip() or None,
        })
    return cleaned


def freeze_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate independent inputs and hash their canonical content *before* Qloo."""
    if not isinstance(manifest, dict):
        raise InvalidStudy("Manifest must be an object")
    study_id, source = manifest.get("study_id"), manifest.get("metadata_source")
    if not isinstance(study_id, str) or not study_id.strip():
        raise InvalidStudy("study_id required")
    if not isinstance(source, str) or not source.strip():
        raise InvalidStudy("metadata_source and selection provenance required")
    if "qloo" in source.casefold():
        raise InvalidStudy("Candidate discovery source cannot be Qloo")
    programme = _catalog(manifest.get("programme"), role="programme")
    candidates = _catalog(manifest.get("candidates"), role="candidates")
    if not 2 <= len(candidates) <= 50:
        raise InvalidStudy("Shared candidate universe must contain 2..50 films")
    if set(x["key"] for x in programme).intersection(x["key"] for x in candidates):
        raise InvalidStudy("Programme films cannot also be recommendations")
    if manifest.get("selection_uses_qloo") is not False:
        raise InvalidStudy("selection_uses_qloo must explicitly be false")
    frozen = {
        "schema": SCHEMA,
        "study_id": study_id,
        "metadata_source": source,
        "selection_note": str(manifest.get("selection_note") or ""),
        "programme": programme,
        "candidates": candidates,
    }
    canonical = json.dumps(frozen, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    frozen["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return frozen


def metadata_score(candidate: Mapping[str, Any], programme: list[dict[str, Any]]) -> float:
    """Metadata-only score; missing country/director never earn matching points."""
    values: list[float] = []
    for seed in programme:
        a, b = set(candidate["genres"]), set(seed["genres"])
        genre = len(a & b) / len(a | b) if (a or b) else 0.0
        country = float(bool(candidate["country"]) and candidate["country"] == seed["country"])
        director = float(bool(candidate["director"]) and candidate["director"] == seed["director"])
        values.append(0.5 * genre + 0.2 * country + 0.3 * director)
    return max(values)


def metadata_ranking(frozen: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The no-Qloo arm: rank the FULL independent candidate universe."""
    rows = [
        {"key": c["key"], "title": c["title"], "score": metadata_score(c, frozen["programme"])}
        for c in frozen["candidates"]
    ]
    return sorted(rows, key=lambda r: (-r["score"], r["key"]))


def compare_common_universe(
    frozen: Mapping[str, Any],
    *,
    scored: Mapping[str, tuple[str, float | None]] | None = None,
    call_id: str | None = None,
    data_status: str = "blocked",
    resolution: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Compare only after exact, single-context Qloo scoring of all locked films.

    scored maps locked film keys -> (Qloo entity ID, measured affinity).
    Unresolved/unscored ids remain in denominator and force 'not_evaluable'.
    Never silently intersect rankings to manufacture a complete comparison.
    """
    if frozen.get("schema") != SCHEMA or not isinstance(frozen.get("sha256"), str):
        raise InvalidStudy("Pass the result of freeze_manifest")
    unsigned = {key: value for key, value in frozen.items() if key != "sha256"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != frozen["sha256"]:
        raise InvalidStudy("Frozen catalog contents changed after hash commitment")
    candidate_keys = {x["key"] for x in frozen["candidates"]}
    rows = metadata_ranking(frozen)
    output: dict[str, Any] = {
        "schema": SCHEMA,
        "study_id": frozen["study_id"],
        "frozen_sha256": frozen["sha256"],
        "candidate_selection_source": frozen["metadata_source"],
        "conditions": {
            "metadata_only": "genre Jaccard 0.5 + country 0.2 + director 0.3; maximum across programme seeds",
            "qloo": "single scoring context, same locked film candidates; one /v2/insights call",
        },
        "metadata_order": [r["key"] for r in rows],
        "metadata_winner": rows[0]["title"],
        "candidate_count": len(rows),
        "qloo_call_id": call_id,
        "data_status": data_status,
        "qloo_resolution": dict(resolution or {}),
        "outcome_verdict": "not_established",
        "scope": (
            "This compares candidate ordering, not recommendation correctness, audience "
            "response, attendance, conversion, revenue, or Qloo incremental outcome value."
        ),
    }
    if scored is None:
        output.update(status="blocked", reason="No measured Qloo scoring supplied",
                      qloo_order=None, top_k_overlap=None, rank_correlation=None)
        return output
    if data_status != "measured" or not isinstance(call_id, str) or not call_id.strip():
        raise InvalidStudy("Measured Qloo results require a real scoring call ID")
    if set(scored) - candidate_keys:
        raise InvalidStudy("Scoring contains candidates outside the frozen universe")
    valid: dict[str, tuple[str, float]] = {}
    seen_entity_ids: set[str] = set()
    for key, pair in scored.items():
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise InvalidStudy("Each scored row must contain entity_id and affinity")
        entity_id, affinity = pair
        if not isinstance(entity_id, str) or not entity_id.strip():
            raise InvalidStudy("Missing Qloo entity id")
        norm_id = entity_id.strip().casefold()
        if norm_id in seen_entity_ids:
            raise InvalidStudy("Two independent films mapped to one Qloo entity")
        seen_entity_ids.add(norm_id)
        if affinity is None:
            continue
        if (isinstance(affinity, bool) or not isinstance(affinity, (int, float))
                or not math.isfinite(affinity) or not 0.0 <= affinity <= 1.0):
            raise InvalidStudy("Qloo affinity must be a finite score between 0 and 1")
        valid[key] = (entity_id, float(affinity))
    missing = sorted(candidate_keys - set(valid))
    output["qloo_coverage"] = {
        "scored": len(valid), "of": len(candidate_keys), "missing_keys": missing
    }
    if missing:
        output.update(status="not_evaluable", reason="Partial Qloo resolution or scoring",
                      qloo_order=None, top_k_overlap=None, rank_correlation=None)
        return output
    qloo_rows = sorted(valid, key=lambda key: (-valid[key][1], key))
    metadata_order = output["metadata_order"]
    overlap = top_k_overlap(metadata_order, qloo_rows, k=5)
    tau = kendall_tau_b(metadata_order, qloo_rows)
    output.update(
        status="evaluable",
        reason="Full same-universe, single-context ranking comparison",
        qloo_order=qloo_rows,
        qloo_winner=next(c["title"] for c in frozen["candidates"] if c["key"] == qloo_rows[0]),
        winner_changed=metadata_order[0] != qloo_rows[0],
        top_k_overlap=overlap,
        rank_correlation=tau,
    )
    return output
