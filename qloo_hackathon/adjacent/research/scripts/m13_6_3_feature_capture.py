#!/usr/bin/env python3
"""M13.6.3: Pre-prediction Qloo feature capture.

Retrieves genuine Qloo features for films with upcoming prediction timestamps,
persisting them with actual retrieval timestamps so they can be used when
predictions freeze.

Usage:
    python -m research.scripts.m13_6_3_feature_capture [--dry-run] [--env-file .env]

Key rules:
- Features are retrieved NOW, with the actual retrieval timestamp.
- A feature is eligible for a prediction only if retrieved_at <= prediction_timestamp.
- Planned predictions never expose feature values as frozen.
- Idempotent: re-running with the same input creates no duplicate snapshots.
- Missing/failed retrievals are recorded explicitly.
- Uses a single async context for all API calls (avoids event-loop lifecycle bugs).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))


def load_env(env_file: str = ".env") -> None:
    """Load .env file into os.environ."""
    env_path = ROOT / env_file
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


def get_upcoming_films_needing_features(conn: sqlite3.Connection) -> list[dict]:
    """Find PLANNED films without a non-empty feature snapshot.

    Empty snapshots (no usable cultural signal) do NOT prevent re-collection.
    Only films with a substantive feature snapshot are considered covered.
    """
    rows = conn.execute(
        """SELECT DISTINCT p.film_key, p.observation_id, p.prediction_timestamp,
                  p.show_start_at, p.prediction_horizon_hours
           FROM prediction_snapshot p
           WHERE p.prediction_state = 'PLANNED'
           AND NOT EXISTS (
             SELECT 1 FROM qloo_feature_snapshot q
             WHERE q.film_key = p.film_key
             AND q.candidate_tags IS NOT NULL
             AND q.candidate_tags != '[]'
           )
           ORDER BY p.prediction_timestamp ASC"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_film_resolution(conn: sqlite3.Connection, film_key: str) -> dict | None:
    """Get existing film resolution for entity lookup."""
    row = conn.execute(
        "SELECT * FROM film_resolution WHERE film_key = ?",
        (film_key,),
    ).fetchone()
    return dict(row) if row else None


def feature_already_exists(conn: sqlite3.Connection, film_key: str) -> bool:
    """Check if a non-empty feature snapshot already exists for this film key.

    Empty snapshots (no tags) do NOT block re-collection, because an empty
    API response may change on a subsequent query. Only snapshots with actual
    Qloo signal prevent re-collection.
    """
    count = conn.execute(
        """SELECT COUNT(*) FROM qloo_feature_snapshot
        WHERE film_key = ?
        AND candidate_tags IS NOT NULL
        AND candidate_tags != '[]'""",
        (film_key,),
    ).fetchone()[0]
    return count > 0


def persist_feature_snapshot(
    conn: sqlite3.Connection,
    film_key: str,
    entity_id: str | None,
    popularity: float | None,
    affinity: float | None,
    band: str | None,
    domain: str | None,
    tags: list[dict] | None,
    call_id: str | None,
    provenance: str,
    retrieved_at: str,
) -> str:
    """Persist a Qloo feature snapshot. Returns feature_id."""
    feature_id = hashlib.sha256(
        f"{film_key}|{entity_id}|{retrieved_at}".encode()
    ).hexdigest()[:16]

    # Check idempotency
    existing = conn.execute(
        "SELECT feature_id FROM qloo_feature_snapshot WHERE feature_id = ?",
        (feature_id,),
    ).fetchone()
    if existing:
        return existing[0]

    conn.execute(
        """INSERT INTO qloo_feature_snapshot
        (feature_id, film_key, qloo_entity_id, retrieved_at, qloo_affinity,
         qloo_popularity, qloo_band, qloo_domain, candidate_tags, qloo_call_id, provenance)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            feature_id, film_key, entity_id, retrieved_at, affinity,
            popularity, band, domain,
            json.dumps(tags) if tags else "[]",
            call_id, provenance,
        ),
    )
    return feature_id


async def _capture_one(client, entity_id: str) -> tuple[list[dict], str | None]:
    """Call Qloo insights for one entity. Returns (tags, call_id)."""
    result = await client.insights(
        filter_type="urn:tag",
        signal_interests_entities=[entity_id],
        take=20,
        tool="feature_capture",
    )
    tags = []
    call_id = getattr(result, "call_id", None)
    if hasattr(result, "results") and result.results:
        for t in result.results[:20]:
            tags.append({
                "tag_id": getattr(t, "tag_id", None),
                "name": getattr(t, "name", None),
                "affinity": getattr(t, "affinity", None),
                "band": getattr(t, "band", None),
                "popularity": getattr(t, "popularity", None),
            })
    return tags, call_id


async def capture_batch(
    conn: sqlite3.Connection,
    films: list[dict],
    client,
    dry_run: bool = False,
) -> dict:
    """Capture Qloo features for a batch of films in a single async context.

    Returns a results dict with counts and details.
    """
    results = {
        "total_films": len(films),
        "captured": 0,
        "exists": 0,
        "no_resolution": 0,
        "errors": 0,
        "dry_run": dry_run,
        "details": [],
    }

    for i, film in enumerate(films):
        film_key = film["film_key"]

        # Idempotency check
        if feature_already_exists(conn, film_key):
            results["details"].append({"status": "EXISTS", "film_key": film_key})
            results["exists"] += 1
            continue

        # Resolution check
        resolution = get_film_resolution(conn, film_key)
        if not resolution or not resolution.get("qloo_entity_id"):
            results["details"].append({"status": "NO_RESOLUTION", "film_key": film_key})
            results["no_resolution"] += 1
            continue

        entity_id = resolution["qloo_entity_id"]

        if dry_run:
            results["details"].append({
                "status": "DRY_RUN",
                "film_key": film_key,
                "entity_id": entity_id,
                "would_retrieve": True,
            })
            continue

        # Actual API call
        retrieved_at = datetime.now(timezone.utc).isoformat()
        try:
            tags, call_id = await _capture_one(client, entity_id)

            popularity = resolution.get("qloo_popularity")
            affinity = tags[0]["affinity"] if tags else None
            band = str(tags[0]["band"]) if tags and tags[0].get("band") is not None else None

            feature_id = persist_feature_snapshot(
                conn=conn,
                film_key=film_key,
                entity_id=entity_id,
                popularity=popularity,
                affinity=affinity,
                band=band,
                domain="film",
                tags=tags,
                call_id=call_id,
                provenance=f"feature_capture|{retrieved_at}|{call_id}",
                retrieved_at=retrieved_at,
            )
            conn.commit()

            results["details"].append({
                "status": "CAPTURED",
                "film_key": film_key,
                "entity_id": entity_id,
                "feature_id": feature_id,
                "call_id": call_id,
                "retrieved_at": retrieved_at,
                "tag_count": len(tags),
            })
            results["captured"] += 1

        except Exception as e:
            results["details"].append({
                "status": "ERROR",
                "film_key": film_key,
                "entity_id": entity_id,
                "error": str(e)[:200],
            })
            results["errors"] += 1

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{len(films)} films processed")

    results["status"] = "COMPLETE"
    return results


def run_capture(env_file: str = ".env", dry_run: bool = False, limit: int = 0) -> dict:
    """Run the pre-prediction feature capture. Manages async context for the full batch."""
    load_env(env_file)

    from backend.app.config import Settings

    settings = Settings.from_env()

    if not settings.has_api_key:
        return {
            "status": "NO_API_KEY",
            "message": "QLOO_API_KEY not configured. Cannot retrieve features.",
            "dry_run": dry_run,
        }

    from backend.app.qloo.client import QlooClient

    conn = sqlite3.connect(str(ROOT / "data" / "processed" / "outcome_ledger.db"))
    conn.row_factory = sqlite3.Row

    # Find films needing features (sync, before async context)
    films = get_upcoming_films_needing_features(conn)
    if limit > 0:
        films = films[:limit]

    client = QlooClient(settings)

    # Single async context for all API calls
    results = asyncio.run(capture_batch(conn, films, client, dry_run=dry_run))

    conn.close()
    return results


def main():
    parser = argparse.ArgumentParser(description="M13.6.3 Pre-prediction feature capture")
    parser.add_argument("--dry-run", action="store_true", help="Don't make API calls")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("--limit", type=int, default=0, help="Max films to process (0=all)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    results = run_capture(env_file=args.env_file, dry_run=args.dry_run, limit=args.limit)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(f"\n=== M13.6.3 Feature Capture Results ===")
        print(f"Status: {results['status']}")
        print(f"Dry run: {results.get('dry_run', False)}")
        print(f"Total films needing features: {results.get('total_films', 0)}")
        print(f"Captured: {results.get('captured', 0)}")
        print(f"Already existed: {results.get('exists', 0)}")
        print(f"No resolution: {results.get('no_resolution', 0)}")
        print(f"Errors: {results.get('errors', 0)}")

        if results.get("details"):
            print(f"\nDetails (first 10):")
            for d in results["details"][:10]:
                print(f"  {d['status']:12s} {d['film_key'][:50]}")


if __name__ == "__main__":
    main()
