#!/usr/bin/env python3
"""Read-only audit of Qloo signal substance, temporal safety and outcome balance.

Uses SQLite URI mode=ro and never migrates, updates, or backfills the source database.
Run from the repository root:
    python research/scripts/m13_6_5_integrity_audit.py
    python research/scripts/m13_6_5_integrity_audit.py --db path/to/outcome_ledger.db
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.domain.qloo_signal import assess_feature, parse_timestamp  # noqa: E402
from app.domain.outcome_repository import _screening_title_identity  # noqa: E402


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if not table_exists(conn, table):
        return set()
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def rows(conn: sqlite3.Connection, table: str) -> list[dict]:
    if not table_exists(conn, table):
        return []
    return [dict(row) for row in conn.execute(f'SELECT * FROM "{table}"')]


def run_audit(db_path: Path) -> dict:
    uri = db_path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        table_names = {
            row["name"] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        table_counts = {
            name: conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            for name in sorted(table_names)
        }
        feature_rows = rows(conn, "qloo_feature_snapshot")
        feature_counts = Counter(assess_feature(row)["status"] for row in feature_rows)
        predictions = rows(conn, "prediction_snapshot")
        pred_cols = columns(conn, "prediction_snapshot")
        outcomes = Counter(str(row.get("outcome_status") or "UNKNOWN") for row in predictions)
        by_horizon: dict[str, Counter] = defaultdict(Counter)
        violations = Counter()
        for pred in predictions:
            horizon = str(pred.get("prediction_horizon_hours", "UNKNOWN"))
            status = str(pred.get("qloo_feature_status") or "NO_FEATURE")
            by_horizon[horizon][status] += 1
            ts = parse_timestamp(pred.get("qloo_feature_timestamp"))
            pts = parse_timestamp(pred.get("prediction_timestamp"))
            if status == "AVAILABLE_AT_PREDICTION_TIME" and ts is None:
                violations["available_without_timestamp"] += 1
            created = parse_timestamp(pred.get("created_at"))
            if created and pts and created > pts:
                violations["snapshot_created_after_prediction_timestamp"] += 1
            if ts and pts and ts > pts:
                violations["feature_after_prediction"] += 1
            if status != "AVAILABLE_AT_PREDICTION_TIME" and pred.get("qloo_popularity") is not None:
                violations["popularity_without_temporal_feature"] += 1
            candidate_tags = pred.get("qloo_candidate_tags", "[]")
            if isinstance(candidate_tags, str):
                try:
                    parsed_tags = json.loads(candidate_tags)
                except (ValueError, TypeError):
                    parsed_tags = None
            else:
                parsed_tags = candidate_tags
            assessment = assess_feature({
                "qloo_entity_id": pred.get("qloo_entity_id"),
                "qloo_popularity": pred.get("qloo_popularity"),
                "qloo_affinity": pred.get("qloo_affinity"),
                "candidate_tags": parsed_tags,
            })
            if (pred.get("qloo_signal_status") == "CULTURAL_SIGNAL_AVAILABLE_AT_PREDICTION_TIME"
                    and not assessment["has_cultural_signal"]):
                violations["cultural_status_without_signal"] += 1
            if str(pred.get("qloo_signal_status") or "").startswith("RETROSPECTIVE_") and (
                pred.get("qloo_popularity") is not None
                or pred.get("qloo_affinity") is not None
                or assessment.get("valid_tag_count", 0) > 0
            ):
                violations["retrospective_payload_present"] += 1

        # Duplicate candidates by same practical screening dimensions and equivalent display title.
        observations = rows(conn, "screening_observation")
        groups: dict[tuple, list[dict]] = defaultdict(list)
        for obs in observations:
            key = (
                obs.get("venue_id"), obs.get("film_year"), obs.get("show_date"),
                obs.get("show_time") or "", obs.get("format") or "",
                _screening_title_identity(obs.get("film_title") or ""),
            )
            groups[key].append(obs)
        duplicate_groups = []
        for key, group in groups.items():
            if len(group) > 1:
                duplicate_groups.append({
                    "normalized_key": [str(value) if value is not None else None for value in key],
                    "observation_ids": [row.get("observation_id") for row in group],
                    "titles": [row.get("film_title") for row in group],
                })

        return {
            "audit": "M13.6.5 read-only signal integrity audit",
            "database": str(db_path.resolve()),
            "database_bytes": db_path.stat().st_size,
            "database_mutated": False,
            "tables": table_counts,
            "feature_snapshot_rows": len(feature_rows),
            "feature_snapshot_classification": dict(sorted(feature_counts.items())),
            "prediction_snapshot_rows": len(predictions),
            "prediction_schema_has_signal_fields": "qloo_signal_status" in pred_cols,
            "prediction_by_horizon_and_feature_status": {
                horizon: dict(sorted(counts.items()))
                for horizon, counts in sorted(by_horizon.items())
            },
            "prediction_outcome_status": dict(sorted(outcomes.items())),
            "prediction_integrity_violations": dict(sorted(violations.items())),
            "normalized_screening_duplicate_groups": duplicate_groups,
            "model_readiness": "NOT_READY",
            "model_readiness_reasons": [
                "This audit checks data integrity; it does not establish a sufficient, balanced, temporally joined label set.",
                "Popularity or entity identity alone is not a cultural signal and must not be used as proof of cultural adjacency.",
            ],
        }
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "data/processed/outcome_ledger.db")
    parser.add_argument("--json-out", type=Path, help="Optional report output path; the database remains read-only")
    args = parser.parse_args()
    if not args.db.exists():
        parser.error(f"Database does not exist: {args.db}")
    report = run_audit(args.db)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
