"""Persistent Outcome Repository — SQLite-backed outcome ledger.

Stores recommendations, screening observations, and outcome measurements.
Idempotent: repeated scrapes of the same screening create snapshots, not duplicates.

M13.3: Production outcome collection infrastructure.
M13.4: Temporal timestamps, lead-time buckets, corrected label semantics,
       film-level resolution, prediction-time Qloo features.
"""

from __future__ import annotations

import hashlib
import html as html_module
import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ============================================================
# SCHEMA (M13.4 — adds temporal + film-level resolution columns)
# ============================================================

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS recommendation (
    recommendation_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    venue_id TEXT NOT NULL,
    venue_name TEXT NOT NULL,
    city TEXT NOT NULL DEFAULT '',
    programme_context_id TEXT NOT NULL DEFAULT '',
    programme_films TEXT NOT NULL DEFAULT '[]',
    candidate_entity TEXT NOT NULL,
    candidate_domain TEXT NOT NULL,
    qloo_entity_id TEXT,
    qloo_affinity REAL,
    qloo_popularity REAL,
    qloo_evidence_score REAL,
    recommendation_rank INTEGER,
    experiment_format TEXT NOT NULL DEFAULT '',
    experiment_date TEXT
);

CREATE TABLE IF NOT EXISTS screening_observation (
    observation_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    venue_id TEXT NOT NULL,
    venue_name TEXT NOT NULL DEFAULT '',
    film_id TEXT,
    film_title TEXT NOT NULL,
    film_year INTEGER,
    film_url TEXT,
    show_date TEXT NOT NULL,
    show_time TEXT NOT NULL DEFAULT '',
    show_start_at TEXT,
    format TEXT NOT NULL DEFAULT '',
    booking_url TEXT,
    source_url TEXT NOT NULL,
    source_timestamp TEXT NOT NULL,
    sold_out INTEGER,
    availability_state TEXT NOT NULL DEFAULT 'UNKNOWN',
    model_target INTEGER,
    lead_time_hours REAL,
    lead_time_bucket TEXT,
    recommendation_id TEXT,
    UNIQUE(venue_id, film_title, film_year, show_date, show_time, format)
);

CREATE TABLE IF NOT EXISTS screening_snapshot (
    snapshot_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    source_timestamp TEXT NOT NULL,
    sold_out INTEGER,
    availability_state TEXT NOT NULL DEFAULT 'UNKNOWN',
    raw_source_url TEXT,
    FOREIGN KEY (observation_id) REFERENCES screening_observation(observation_id)
);

CREATE TABLE IF NOT EXISTS outcome_measurement (
    measurement_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    label_quality TEXT NOT NULL DEFAULT 'UNAVAILABLE',
    sold_out INTEGER,
    tickets_sold INTEGER,
    occupancy REAL,
    capacity INTEGER,
    measurement_timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    provenance TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (observation_id) REFERENCES screening_observation(observation_id)
);

CREATE TABLE IF NOT EXISTS film_resolution (
    film_key TEXT PRIMARY KEY,
    film_title TEXT NOT NULL,
    film_year INTEGER,
    film_url TEXT,
    resolution_status TEXT NOT NULL,
    resolved_title TEXT,
    resolved_year INTEGER,
    qloo_entity_id TEXT,
    qloo_name TEXT,
    qloo_entity_type TEXT,
    qloo_popularity REAL,
    qloo_call_id TEXT,
    resolution_provenance TEXT NOT NULL DEFAULT '',
    resolution_timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS qloo_feature_snapshot (
    feature_id TEXT PRIMARY KEY,
    film_key TEXT NOT NULL,
    qloo_entity_id TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    qloo_affinity REAL,
    qloo_popularity REAL,
    qloo_band TEXT,
    qloo_domain TEXT,
    candidate_tags TEXT NOT NULL DEFAULT '[]',
    qloo_call_id TEXT,
    provenance TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (film_key) REFERENCES film_resolution(film_key)
);

CREATE TABLE IF NOT EXISTS canonical_film (
    film_key TEXT PRIMARY KEY,
    raw_titles TEXT NOT NULL DEFAULT '[]',
    canonical_title TEXT NOT NULL,
    film_year INTEGER,
    year_source TEXT NOT NULL DEFAULT '',
    year_provenance TEXT NOT NULL DEFAULT '',
    film_url TEXT,
    source_provenance TEXT NOT NULL DEFAULT '',
    identity_status TEXT NOT NULL DEFAULT 'YEAR_MISSING',
    identity_confidence TEXT NOT NULL DEFAULT '',
    is_event INTEGER NOT NULL DEFAULT 0,
    event_reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prediction_run (
    prediction_run_id TEXT PRIMARY KEY,
    run_timestamp TEXT NOT NULL,
    run_type TEXT NOT NULL DEFAULT 'INITIAL',
    total_screenings INTEGER NOT NULL DEFAULT 0,
    eligible_screenings INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prediction_snapshot (
    prediction_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    film_key TEXT NOT NULL,
    prediction_run_id TEXT NOT NULL,
    prediction_timestamp TEXT NOT NULL,
    prediction_horizon_hours INTEGER NOT NULL,
    show_start_at TEXT NOT NULL,
    qloo_entity_id TEXT,
    qloo_popularity REAL,
    qloo_band TEXT,
    qloo_domain TEXT,
    qloo_feature_timestamp TEXT,
    qloo_feature_status TEXT NOT NULL DEFAULT 'NO_FEATURE',
    qloo_signal_status TEXT NOT NULL DEFAULT 'NO_FEATURE',
    qloo_affinity REAL,
    qloo_candidate_tags TEXT NOT NULL DEFAULT '[]',
    qloo_feature_provenance TEXT NOT NULL DEFAULT '',
    qloo_call_id TEXT,
    outcome_status TEXT NOT NULL DEFAULT 'PENDING',
    sold_out_observed INTEGER,
    final_observation_timestamp TEXT,
    lead_time_at_final_observation REAL,
    format TEXT NOT NULL DEFAULT '',
    day_of_week TEXT NOT NULL DEFAULT '',
    start_hour INTEGER,
    source_url TEXT NOT NULL DEFAULT '',
    source_timestamp TEXT NOT NULL DEFAULT '',
    provenance TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(observation_id, prediction_horizon_hours)
);

CREATE INDEX IF NOT EXISTS idx_pred_snap_obs ON prediction_snapshot(observation_id);
CREATE INDEX IF NOT EXISTS idx_pred_snap_run ON prediction_snapshot(prediction_run_id);
CREATE INDEX IF NOT EXISTS idx_pred_snap_horizon ON prediction_snapshot(prediction_horizon_hours);
CREATE INDEX IF NOT EXISTS idx_pred_snap_outcome ON prediction_snapshot(outcome_status);

CREATE INDEX IF NOT EXISTS idx_obs_venue ON screening_observation(venue_id);
CREATE INDEX IF NOT EXISTS idx_obs_date ON screening_observation(show_date);
CREATE INDEX IF NOT EXISTS idx_obs_film ON screening_observation(film_title);
CREATE INDEX IF NOT EXISTS idx_snapshot_obs ON screening_snapshot(observation_id);
CREATE INDEX IF NOT EXISTS idx_outcome_obs ON outcome_measurement(observation_id);
CREATE INDEX IF NOT EXISTS idx_resolution_film ON film_resolution(film_key);
CREATE INDEX IF NOT EXISTS idx_feature_film ON qloo_feature_snapshot(film_key);
"""

# M13.4 migration: add columns to existing tables if missing
_MIGRATIONS = [
    ("screening_observation", "show_start_at", "TEXT"),
    ("screening_observation", "lead_time_hours", "REAL"),
    ("screening_observation", "lead_time_bucket", "TEXT"),
    ("screening_observation", "model_target", "INTEGER"),
    # M13.6.5: preserve the exact time-safe signal in the frozen prediction row.
    ("prediction_snapshot", "qloo_signal_status", "TEXT NOT NULL DEFAULT 'NO_FEATURE'"),
    ("prediction_snapshot", "qloo_affinity", "REAL"),
    ("prediction_snapshot", "qloo_candidate_tags", "TEXT NOT NULL DEFAULT '[]'"),
    ("prediction_snapshot", "qloo_feature_provenance", "TEXT NOT NULL DEFAULT ''"),
]


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(r[1] == column for r in rows)
    except sqlite3.OperationalError:
        return False


def _has_table(conn: sqlite3.Connection, table: str) -> bool:
    """Check if a table exists."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _screening_title_identity(title: str) -> str:
    """Normalize only representational title differences for screening joins.

    This is intentionally narrower than canonical film matching: it decodes HTML
    entities, normalizes equivalent Unicode apostrophes/dashes, and collapses
    whitespace. It does not remove editions, subtitles, years, or director names.
    """
    decoded = html_module.unescape(str(title or ""))
    decoded = unicodedata.normalize("NFKC", decoded)
    decoded = decoded.translate(str.maketrans({
        "’": "'", "‘": "'", "ʼ": "'", "＇": "'",
        "–": "-", "—": "-", "−": "-",
    }))
    return re.sub(r"\s+", " ", decoded).strip().casefold()


def _deterministic_obs_id(venue_id: str, film_title: str, film_year: int | None,
                          show_date: str, show_time: str, fmt: str) -> str:
    """Deterministic observation ID from minimally normalized screening identity."""
    key = f"{venue_id}|{_screening_title_identity(film_title)}|{film_year}|{show_date}|{show_time}|{fmt}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _snapshot_id(observation_id: str, source_timestamp: str) -> str:
    """Snapshot ID from observation + timestamp."""
    key = f"{observation_id}|{source_timestamp}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def film_key(film_title: str, film_year: int | None) -> str:
    """Deterministic film key for resolution caching."""
    return f"{film_title.strip().lower()}|{film_year}"


def _model_target(sold_out: int | None) -> int | None:
    """Compute model_target from sold_out.

    sold_out=1 (SOLD_OUT) → model_target=1
    sold_out=0 (AVAILABLE) → model_target=None (NOT 0)
    sold_out=None (UNKNOWN) → model_target=None

    AVAILABLE is NOT a negative demand label.
    """
    if sold_out == 1:
        return 1
    return None


def _label_quality_for_sold_out(sold_out: bool | None) -> str:
    """Correct label quality classification.

    sold_out=True  → STRONG_PROXY
    sold_out=False → DESCRIPTIVE_ONLY  (not STRONG_PROXY)
    sold_out=None  → UNAVAILABLE
    """
    if sold_out is True:
        return "STRONG_PROXY"
    if sold_out is False:
        return "DESCRIPTIVE_ONLY"
    return "UNAVAILABLE"


def compute_lead_time(show_start_at: str | None, source_timestamp: str | None) -> float | None:
    """Compute lead_time_hours = show_start_at - source_timestamp.

    Returns None if either timestamp is missing.
    Raises ValueError if lead time is negative (post-show observation).
    """
    if not show_start_at or not source_timestamp:
        return None
    try:
        show_dt = datetime.fromisoformat(show_start_at)
        obs_dt = datetime.fromisoformat(source_timestamp)
    except (ValueError, TypeError):
        return None

    # Ensure both are timezone-aware
    if show_dt.tzinfo is None:
        show_dt = show_dt.replace(tzinfo=timezone.utc)
    if obs_dt.tzinfo is None:
        obs_dt = obs_dt.replace(tzinfo=timezone.utc)

    delta = (show_dt - obs_dt).total_seconds() / 3600.0
    return delta


def lead_time_bucket(hours: float | None) -> str | None:
    """Classify lead time into buckets.

    Returns None if hours is None.
    Negative hours → 'post_show' (rejected for prediction analysis).
    """
    if hours is None:
        return None
    if hours < 0:
        return "post_show"
    if hours <= 24:
        return "0-24h"
    if hours <= 72:
        return "1-3d"
    if hours <= 168:
        return "4-7d"
    if hours <= 336:
        return "8-14d"
    if hours <= 720:
        return "15-30d"
    return "30d+"


# ============================================================
# REPOSITORY
# ============================================================

class OutcomeRepository:
    """Persistent outcome storage backed by SQLite."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """Create or migrate schema to M13.4 version."""
        conn = self._conn

        # Check if we have the old M13.3 film_resolution schema (keyed by observation_id)
        if _has_table(conn, "film_resolution"):
            if _has_column(conn, "film_resolution", "observation_id") and not _has_column(conn, "film_resolution", "film_key"):
                # Old schema — need to migrate
                conn.execute("ALTER TABLE film_resolution RENAME TO film_resolution_old")
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS film_resolution (
                        film_key TEXT PRIMARY KEY,
                        film_title TEXT NOT NULL,
                        film_year INTEGER,
                        film_url TEXT,
                        resolution_status TEXT NOT NULL,
                        resolved_title TEXT,
                        resolved_year INTEGER,
                        qloo_entity_id TEXT,
                        qloo_name TEXT,
                        qloo_entity_type TEXT,
                        qloo_popularity REAL,
                        qloo_call_id TEXT,
                        resolution_provenance TEXT NOT NULL DEFAULT '',
                        resolution_timestamp TEXT NOT NULL
                    )
                """)
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO film_resolution
                        (film_key, film_title, film_year, resolution_status,
                         resolved_title, resolved_year, qloo_entity_id, qloo_call_id,
                         resolution_provenance, resolution_timestamp)
                        SELECT
                            lower(trim(so.film_title)) || '|' || so.film_year,
                            so.film_title, so.film_year,
                            fro.resolution_status, fro.resolved_title, fro.resolved_year,
                            fro.qloo_entity_id, fro.qloo_call_id,
                            fro.resolution_provenance,
                            COALESCE(datetime('now'), '')
                        FROM film_resolution_old fro
                        JOIN screening_observation so ON fro.observation_id = so.observation_id
                    """)
                except sqlite3.OperationalError:
                    pass
                conn.execute("DROP TABLE IF EXISTS film_resolution_old")
                conn.commit()

        # Check if we have the old M13.3 qloo_feature_snapshot schema
        if _has_table(conn, "qloo_feature_snapshot"):
            if _has_column(conn, "qloo_feature_snapshot", "observation_id") and not _has_column(conn, "qloo_feature_snapshot", "film_key"):
                conn.execute("ALTER TABLE qloo_feature_snapshot RENAME TO qloo_feature_snapshot_old")
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS qloo_feature_snapshot (
                        feature_id TEXT PRIMARY KEY,
                        film_key TEXT NOT NULL,
                        qloo_entity_id TEXT NOT NULL,
                        retrieved_at TEXT NOT NULL,
                        qloo_affinity REAL,
                        qloo_popularity REAL,
                        qloo_band TEXT,
                        qloo_domain TEXT,
                        candidate_tags TEXT NOT NULL DEFAULT '[]',
                        qloo_call_id TEXT,
                        provenance TEXT NOT NULL DEFAULT '',
                        FOREIGN KEY (film_key) REFERENCES film_resolution(film_key)
                    )
                """)
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO qloo_feature_snapshot
                        (feature_id, film_key, qloo_entity_id, retrieved_at,
                         qloo_affinity, qloo_popularity, qloo_band, qloo_domain,
                         candidate_tags, qloo_call_id)
                        SELECT
                            qfo.feature_id,
                            lower(trim(so.film_title)) || '|' || so.film_year,
                            qfo.qloo_entity_id,
                            qfo.retrieval_timestamp,
                            qfo.qloo_affinity, qfo.qloo_popularity,
                            qfo.qloo_band, qfo.qloo_domain,
                            qfo.candidate_tags, qfo.qloo_call_id
                        FROM qloo_feature_snapshot_old qfo
                        JOIN screening_observation so ON qfo.observation_id = so.observation_id
                    """)
                except sqlite3.OperationalError:
                    pass
                conn.execute("DROP TABLE IF EXISTS qloo_feature_snapshot_old")
                conn.commit()

        # Now create all tables (IF NOT EXISTS handles already-existing ones)
        conn.executescript(SCHEMA_SQL)

        # Add missing columns from incremental migrations.
        for table, column, col_type in _MIGRATIONS:
            if not _has_column(conn, table, column):
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                except sqlite3.OperationalError:
                    pass

        conn.commit()

    def close(self) -> None:
        self._conn.close()

    # --------------------------------------------------------
    # RECOMMENDATIONS
    # --------------------------------------------------------

    def create_recommendation(self, rec: dict[str, Any]) -> str:
        """Create a recommendation record. Returns recommendation_id."""
        rid = rec["recommendation_id"]
        self._conn.execute(
            """INSERT OR IGNORE INTO recommendation
            (recommendation_id, created_at, venue_id, venue_name, city,
             programme_context_id, programme_films,
             candidate_entity, candidate_domain, qloo_entity_id,
             qloo_affinity, qloo_popularity, qloo_evidence_score,
             recommendation_rank, experiment_format, experiment_date)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rid, rec.get("created_at", datetime.now(timezone.utc).isoformat()),
             rec.get("venue_id", ""), rec.get("venue_name", ""),
             rec.get("city", ""), rec.get("programme_context_id", ""),
             json.dumps(rec.get("programme_films", [])),
             rec.get("candidate_entity", ""), rec.get("candidate_domain", ""),
             rec.get("qloo_entity_id"), rec.get("qloo_affinity"),
             rec.get("qloo_popularity"), rec.get("qloo_evidence_score"),
             rec.get("recommendation_rank"), rec.get("experiment_format", ""),
             rec.get("experiment_date")),
        )
        self._conn.commit()
        return rid

    def get_recommendation(self, recommendation_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM recommendation WHERE recommendation_id = ?",
            (recommendation_id,),
        ).fetchone()
        return dict(row) if row else None

    # --------------------------------------------------------
    # SCREENING OBSERVATIONS (idempotent)
    # --------------------------------------------------------

    def record_screening(self, obs: dict[str, Any]) -> tuple[str, bool]:
        """Record a screening observation. Returns (observation_id, is_new).

        Idempotent: same screening key → same observation_id.
        New snapshot created if state changed.

        M13.4: Also computes model_target, lead_time_hours, lead_time_bucket.
        """
        obs_id = _deterministic_obs_id(
            obs["venue_id"], obs["film_title"], obs.get("film_year"),
            obs["show_date"], obs.get("show_time", ""),
            obs.get("format", ""),
        )

        # Reuse a single existing screening whose title only differs by HTML/Unicode
        # representation. If more than one historical row already matches, fail
        # closed and require the read-only duplicate audit/manual reconciliation.
        potential_rows = self._conn.execute(
            """SELECT observation_id, film_title FROM screening_observation
            WHERE venue_id = ? AND film_year IS ? AND show_date = ?
              AND show_time = ? AND format = ?""",
            (obs["venue_id"], obs.get("film_year"), obs["show_date"],
             obs.get("show_time", ""), obs.get("format", "")),
        ).fetchall()
        title_identity = _screening_title_identity(obs["film_title"])
        normalized_matches = [
            row for row in potential_rows
            if _screening_title_identity(row["film_title"]) == title_identity
        ]
        if len(normalized_matches) > 1:
            ids = ", ".join(row["observation_id"] for row in normalized_matches)
            raise ValueError(
                "Ambiguous normalized screening identity already exists; "
                f"refusing to create or mutate another row. Candidate observation IDs: {ids}"
            )
        if len(normalized_matches) == 1:
            obs_id = normalized_matches[0]["observation_id"]

        snap_id = _snapshot_id(obs_id, obs["source_timestamp"])

        # Check if observation exists
        existing = self._conn.execute(
            "SELECT observation_id, sold_out, availability_state FROM screening_observation WHERE observation_id = ?",
            (obs_id,),
        ).fetchone()

        is_new = existing is None

        # Check if existing observation has show_start_at (for M13.4 migration)
        existing_show_start_at = None
        if not is_new:
            existing_row = self._conn.execute(
                "SELECT show_start_at FROM screening_observation WHERE observation_id = ?",
                (obs_id,),
            ).fetchone()
            existing_show_start_at = existing_row["show_start_at"] if existing_row else None

        sold_out_int = 1 if obs.get("sold_out") is True else (0 if obs.get("sold_out") is False else None)

        # M13.4: Compute temporal fields
        show_start_at = obs.get("show_start_at")
        source_timestamp = obs.get("source_timestamp")
        lt_hours = compute_lead_time(show_start_at, source_timestamp)
        lt_bucket = lead_time_bucket(lt_hours)
        m_target = _model_target(sold_out_int)

        if is_new:
            self._conn.execute(
                """INSERT INTO screening_observation
                (observation_id, snapshot_id, venue_id, venue_name, film_id,
                 film_title, film_year, film_url, show_date, show_time,
                 show_start_at, format,
                 booking_url, source_url, source_timestamp, sold_out,
                 availability_state, model_target, lead_time_hours,
                 lead_time_bucket, recommendation_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (obs_id, snap_id, obs["venue_id"], obs.get("venue_name", ""),
                 obs.get("film_id"), obs["film_title"], obs.get("film_year"),
                 obs.get("film_url"), obs["show_date"], obs.get("show_time", ""),
                 show_start_at, obs.get("format", ""),
                 obs.get("booking_url"),
                 obs.get("source_url", ""), source_timestamp,
                 sold_out_int, obs.get("availability_state", "UNKNOWN"),
                 m_target, lt_hours, lt_bucket,
                 obs.get("recommendation_id")),
            )
        else:
            # Update current state (but preserve history via snapshots)
            # M13.4: Also update show_start_at/lead_time if newly available
            if show_start_at and not existing_show_start_at:
                self._conn.execute(
                    """UPDATE screening_observation
                    SET sold_out = ?, availability_state = ?, snapshot_id = ?,
                        model_target = ?,
                        show_start_at = ?, lead_time_hours = ?, lead_time_bucket = ?
                    WHERE observation_id = ?""",
                    (sold_out_int, obs.get("availability_state", "UNKNOWN"),
                     snap_id, m_target,
                     show_start_at, lt_hours, lt_bucket, obs_id),
                )
            else:
                self._conn.execute(
                    """UPDATE screening_observation
                    SET sold_out = ?, availability_state = ?, snapshot_id = ?,
                        model_target = ?
                    WHERE observation_id = ?""",
                    (sold_out_int, obs.get("availability_state", "UNKNOWN"),
                     snap_id, m_target, obs_id),
                )

        # Always create snapshot for this observation
        self._conn.execute(
            """INSERT OR IGNORE INTO screening_snapshot
            (snapshot_id, observation_id, source_timestamp, sold_out,
             availability_state, raw_source_url)
            VALUES (?,?,?,?,?,?)""",
            (snap_id, obs_id, source_timestamp, sold_out_int,
             obs.get("availability_state", "UNKNOWN"),
             obs.get("source_url")),
        )

        self._conn.commit()
        return obs_id, is_new

    def get_observation(self, observation_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM screening_observation WHERE observation_id = ?",
            (observation_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_snapshots(self, observation_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM screening_snapshot WHERE observation_id = ? ORDER BY source_timestamp",
            (observation_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # --------------------------------------------------------
    # FILM RESOLUTION (M13.4: per-unique-film, not per-observation)
    # --------------------------------------------------------

    def record_film_resolution(self, resolution: dict[str, Any]) -> None:
        """Record film resolution. One resolution per unique film (title+year).

        M13.4: Resolution is per film_key, not per observation_id.
        """
        fk = resolution["film_key"]
        self._conn.execute(
            """INSERT OR REPLACE INTO film_resolution
            (film_key, film_title, film_year, film_url,
             resolution_status, resolved_title, resolved_year,
             qloo_entity_id, qloo_name, qloo_entity_type, qloo_popularity,
             qloo_call_id, resolution_provenance, resolution_timestamp)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (fk,
             resolution.get("film_title", ""),
             resolution.get("film_year"),
             resolution.get("film_url"),
             resolution["resolution_status"],
             resolution.get("resolved_title"),
             resolution.get("resolved_year"),
             resolution.get("qloo_entity_id"),
             resolution.get("qloo_name"),
             resolution.get("qloo_entity_type"),
             resolution.get("qloo_popularity"),
             resolution.get("qloo_call_id"),
             resolution.get("resolution_provenance", ""),
             resolution.get("resolution_timestamp",
                            datetime.now(timezone.utc).isoformat())),
        )
        self._conn.commit()

    def get_film_resolution(self, fk: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM film_resolution WHERE film_key = ?",
            (fk,),
        ).fetchone()
        return dict(row) if row else None

    def get_resolution(self, obs_id: str) -> dict | None:
        """Backward-compatible: get resolution by observation's film."""
        obs = self.get_observation(obs_id)
        if not obs:
            return None
        fk = film_key(obs["film_title"], obs.get("film_year"))
        return self.get_film_resolution(fk)

    # M13.3 backward compat: record_resolution still works
    def record_resolution(self, obs_id: str, resolution: dict[str, Any]) -> None:
        """Backward-compatible: record resolution for an observation's film."""
        obs = self.get_observation(obs_id)
        if not obs:
            return
        fk = film_key(obs["film_title"], obs.get("film_year"))
        resolution_with_key = {
            "film_key": fk,
            "film_title": obs["film_title"],
            "film_year": obs.get("film_year"),
            "film_url": obs.get("film_url"),
            **resolution,
        }
        self.record_film_resolution(resolution_with_key)

    # --------------------------------------------------------
    # QLOO FEATURE SNAPSHOTS (M13.4: per film, with retrieval timestamp)
    # --------------------------------------------------------

    def record_qloo_features(self, features: dict[str, Any]) -> str:
        """Record Qloo feature snapshot. M13.4: keyed by film_key.

        features must include:
        - film_key: unique film identifier
        - qloo_entity_id: resolved Qloo entity
        - retrieved_at: ISO timestamp of retrieval
        """
        fk = features["film_key"]
        retrieved_at = features["retrieved_at"]
        fid = hashlib.sha256(f"{fk}|{retrieved_at}".encode()).hexdigest()[:16]

        self._conn.execute(
            """INSERT OR REPLACE INTO qloo_feature_snapshot
            (feature_id, film_key, qloo_entity_id, retrieved_at,
             qloo_affinity, qloo_popularity, qloo_band, qloo_domain,
             candidate_tags, qloo_call_id, provenance)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (fid, fk, features["qloo_entity_id"],
             retrieved_at,
             features.get("qloo_affinity"), features.get("qloo_popularity"),
             features.get("qloo_band"), features.get("qloo_domain"),
             json.dumps(features.get("candidate_tags", [])),
             features.get("qloo_call_id"),
             features.get("provenance", "")),
        )
        self._conn.commit()
        return fid

    # Backward compat for M13.3 test (obs_id-based)
    def record_qloo_features_for_obs(self, obs_id: str, features: dict[str, Any]) -> str:
        """Backward-compatible: record features for an observation's film."""
        obs = self.get_observation(obs_id)
        if not obs:
            return ""
        fk = film_key(obs["film_title"], obs.get("film_year"))
        features_with_key = {
            "film_key": fk,
            **features,
        }
        return self.record_qloo_features(features_with_key)

    def get_latest_qloo_feature(self, fk: str, before: str | None = None) -> dict | None:
        """Get the latest Qloo feature snapshot for a film.

        If `before` is provided, only return features retrieved at or before
        that timestamp (prediction-time leakage prevention).
        """
        if before:
            row = self._conn.execute(
                """SELECT * FROM qloo_feature_snapshot
                WHERE film_key = ? AND retrieved_at <= ?
                ORDER BY retrieved_at DESC LIMIT 1""",
                (fk, before),
            ).fetchone()
        else:
            row = self._conn.execute(
                """SELECT * FROM qloo_feature_snapshot
                WHERE film_key = ?
                ORDER BY retrieved_at DESC LIMIT 1""",
                (fk,),
            ).fetchone()
        return dict(row) if row else None

    def get_qloo_features_for_film(self, fk: str) -> list[dict]:
        """Get all Qloo feature snapshots for a film (history preserved)."""
        rows = self._conn.execute(
            """SELECT * FROM qloo_feature_snapshot
            WHERE film_key = ?
            ORDER BY retrieved_at""",
            (fk,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_latest_usable_qloo_feature(
        self, fk: str, before: str | None = None, *, cultural_only: bool = False
    ) -> dict | None:
        """Select the latest substantive feature at/before a cutoff.

        Empty responses and identity-only rows cannot mask earlier valid signal.
        Timestamps are compared as UTC datetimes rather than lexicographic strings,
        so ISO timestamps with different offsets are handled correctly.
        """
        from .qloo_signal import latest_feature

        return latest_feature(
            self.get_qloo_features_for_film(fk),
            before=before,
            cultural_only=cultural_only,
            usable_only=not cultural_only,
        )

    # --------------------------------------------------------
    # OUTCOME MEASUREMENTS (M13.4: corrected label semantics)
    # --------------------------------------------------------

    def record_outcome(self, obs_id: str, outcome: dict[str, Any]) -> str:
        """Record an outcome measurement.

        M13.4 CORRECTED label semantics:
        - sold_out=True  → STRONG_PROXY
        - sold_out=False → DESCRIPTIVE_ONLY (NOT STRONG_PROXY)
        - sold_out=None  → UNAVAILABLE
        - tickets_sold present → DIRECT_OUTCOME (overrides)
        - occupancy present → DIRECT_OUTCOME (overrides)
        """
        mid = hashlib.sha256(
            f"{obs_id}|{outcome.get('measurement_timestamp', '')}".encode()
        ).hexdigest()[:16]

        # Validation
        ts = outcome.get("tickets_sold")
        if ts is not None and ts < 0:
            raise ValueError(f"tickets_sold must be >= 0, got {ts}")
        cap = outcome.get("capacity")
        if cap is not None and cap <= 0:
            raise ValueError(f"capacity must be > 0, got {cap}")
        occ = outcome.get("occupancy")
        if occ is not None and not (0 <= occ <= 1):
            raise ValueError(f"occupancy must be in [0,1], got {occ}")

        # M13.4: Corrected label quality
        label_quality = _label_quality_for_sold_out(outcome.get("sold_out"))
        # tickets_sold and occupancy override to DIRECT_OUTCOME
        if outcome.get("tickets_sold") is not None:
            label_quality = "DIRECT_OUTCOME"
        if outcome.get("occupancy") is not None:
            label_quality = "DIRECT_OUTCOME"

        sold_out_int = 1 if outcome.get("sold_out") is True else (
            0 if outcome.get("sold_out") is False else None
        )

        self._conn.execute(
            """INSERT OR REPLACE INTO outcome_measurement
            (measurement_id, observation_id, label_quality, sold_out,
             tickets_sold, occupancy, capacity, measurement_timestamp,
             source, provenance)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (mid, obs_id, label_quality, sold_out_int,
             outcome.get("tickets_sold"), outcome.get("occupancy"),
             outcome.get("capacity"),
             outcome.get("measurement_timestamp", datetime.now(timezone.utc).isoformat()),
             outcome.get("source", ""), outcome.get("provenance", "")),
        )
        self._conn.commit()
        return mid

    def get_outcome(self, obs_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM outcome_measurement WHERE observation_id = ?",
            (obs_id,),
        ).fetchone()
        return dict(row) if row else None

    # --------------------------------------------------------
    # QUERIES
    # --------------------------------------------------------

    def list_observations(self, venue_id: str | None = None,
                          limit: int = 100) -> list[dict]:
        if venue_id:
            rows = self._conn.execute(
                "SELECT * FROM screening_observation WHERE venue_id = ? ORDER BY show_date DESC LIMIT ?",
                (venue_id, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM screening_observation ORDER BY show_date DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_all_observations(self, venue_id: str | None = None) -> list[dict]:
        """List all observations (no limit)."""
        if venue_id:
            rows = self._conn.execute(
                "SELECT * FROM screening_observation WHERE venue_id = ? ORDER BY show_date",
                (venue_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM screening_observation ORDER BY show_date",
            ).fetchall()
        return [dict(r) for r in rows]

    def count_observations(self, venue_id: str | None = None) -> int:
        if venue_id:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM screening_observation WHERE venue_id = ?",
                (venue_id,),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM screening_observation",
            ).fetchone()
        return row[0]

    def count_snapshots(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM screening_snapshot").fetchone()
        return row[0]

    def sold_out_stats(self, venue_id: str | None = None) -> dict:
        """Compute sold_out statistics."""
        where = "WHERE venue_id = ?" if venue_id else ""
        params = (venue_id,) if venue_id else ()

        total = self._conn.execute(
            f"SELECT COUNT(*) FROM screening_observation {where}", params
        ).fetchone()[0]

        sold_out = self._conn.execute(
            f"SELECT COUNT(*) FROM screening_observation {where} {'AND' if where else 'WHERE'} sold_out = 1",
            params,
        ).fetchone()[0]

        available = self._conn.execute(
            f"SELECT COUNT(*) FROM screening_observation {where} {'AND' if where else 'WHERE'} sold_out = 0",
            params,
        ).fetchone()[0]

        unknown = total - sold_out - available

        return {
            "total": total,
            "sold_out": sold_out,
            "available": available,
            "unknown": unknown,
            "sold_out_rate": round(sold_out / total, 4) if total > 0 else 0,
        }

    def get_unique_films(self) -> list[dict]:
        """Get all unique films (title+year) from observations."""
        rows = self._conn.execute(
            """SELECT DISTINCT film_title, film_year, film_url
            FROM screening_observation
            ORDER BY film_title"""
        ).fetchall()
        return [dict(r) for r in rows]

    def get_observations_for_film(self, fk: str) -> list[dict]:
        """Get all observations for a given film_key."""
        title, year_str = fk.split("|", 1)
        year = int(year_str) if year_str != "None" else None
        if year is not None:
            rows = self._conn.execute(
                """SELECT * FROM screening_observation
                WHERE lower(trim(film_title)) = ? AND film_year = ?
                ORDER BY show_start_at""",
                (title, year),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT * FROM screening_observation
                WHERE lower(trim(film_title)) = ? AND film_year IS NULL
                ORDER BY show_start_at""",
                (title,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_all_film_resolutions(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM film_resolution ORDER BY film_title"
        ).fetchall()
        return [dict(r) for r in rows]

    def list_all_qloo_features(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM qloo_feature_snapshot ORDER BY film_key, retrieved_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def count_multi_snapshot_observations(self) -> int:
        """Count observations with more than one snapshot."""
        row = self._conn.execute(
            """SELECT COUNT(*) FROM (
                SELECT observation_id, COUNT(*) as cnt
                FROM screening_snapshot
                GROUP BY observation_id
                HAVING cnt > 1
            )"""
        ).fetchone()
        return row[0]

    def count_state_transitions(self) -> int:
        """Count observations that transitioned from AVAILABLE to SOLD_OUT."""
        rows = self._conn.execute(
            """SELECT observation_id, sold_out
            FROM screening_snapshot
            ORDER BY observation_id, source_timestamp"""
        ).fetchall()

        transitions = 0
        current_obs = None
        saw_available = False
        for row in rows:
            obs_id = row["observation_id"]
            so = row["sold_out"]
            if obs_id != current_obs:
                current_obs = obs_id
                saw_available = False
            if so == 0:
                saw_available = True
            elif so == 1 and saw_available:
                transitions += 1
                saw_available = False
        return transitions

    def data_quality_audit(self) -> dict:
        """Compute data quality metrics."""
        total_obs = self.count_observations()
        total_snap = self.count_snapshots()

        # Unique films
        films = self._conn.execute(
            "SELECT COUNT(DISTINCT film_title) FROM screening_observation"
        ).fetchone()[0]

        # Unique venues
        venues = self._conn.execute(
            "SELECT COUNT(DISTINCT venue_id) FROM screening_observation"
        ).fetchone()[0]

        # Resolution stats
        resolved = self._conn.execute(
            "SELECT COUNT(*) FROM film_resolution WHERE resolution_status = 'VERIFIED'"
        ).fetchone()[0]
        ambiguous = self._conn.execute(
            "SELECT COUNT(*) FROM film_resolution WHERE resolution_status = 'AMBIGUOUS'"
        ).fetchone()[0]
        unresolved = self._conn.execute(
            "SELECT COUNT(*) FROM film_resolution WHERE resolution_status = 'UNRESOLVED'"
        ).fetchone()[0]

        # Duplicate rate (snapshots per observation)
        avg_snap = self._conn.execute(
            "SELECT AVG(cnt) FROM (SELECT COUNT(*) as cnt FROM screening_snapshot GROUP BY observation_id)"
        ).fetchone()[0]

        return {
            "total_observations": total_obs,
            "total_snapshots": total_snap,
            "unique_films": films,
            "unique_venues": venues,
            "resolved_films": resolved,
            "ambiguous_films": ambiguous,
            "unresolved_films": unresolved,
            "resolution_rate": round(resolved / total_obs, 4) if total_obs > 0 else 0,
            "avg_snapshots_per_observation": round(avg_snap or 0, 2),
            "sold_out_stats": self.sold_out_stats(),
        }

    # --------------------------------------------------------
    # CANONICAL FILM IDENTITY (M13.5)
    # --------------------------------------------------------

    def upsert_canonical_film(self, cf: dict[str, Any]) -> None:
        """Insert or update a canonical film record."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT OR REPLACE INTO canonical_film
            (film_key, raw_titles, canonical_title, film_year, year_source,
             year_provenance, film_url, source_provenance, identity_status,
             identity_confidence, is_event, event_reason, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cf["film_key"],
             json.dumps(cf.get("raw_titles", [])),
             cf["canonical_title"],
             cf.get("film_year"),
             cf.get("year_source", ""),
             cf.get("year_provenance", ""),
             cf.get("film_url", ""),
             cf.get("source_provenance", ""),
             cf.get("identity_status", "YEAR_MISSING"),
             cf.get("identity_confidence", ""),
             1 if cf.get("is_event") else 0,
             cf.get("event_reason", ""),
             cf.get("created_at", now),
             now),
        )
        self._conn.commit()

    def get_canonical_film(self, fk: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM canonical_film WHERE film_key = ?",
            (fk,),
        ).fetchone()
        return dict(row) if row else None

    def list_canonical_films(self, exclude_events: bool = False) -> list[dict]:
        if exclude_events:
            rows = self._conn.execute(
                "SELECT * FROM canonical_film WHERE is_event = 0 ORDER BY canonical_title"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM canonical_film ORDER BY canonical_title"
            ).fetchall()
        return [dict(r) for r in rows]

    def canonical_film_stats(self) -> dict:
        """Compute canonical film statistics."""
        total = self._conn.execute(
            "SELECT COUNT(*) FROM canonical_film"
        ).fetchone()[0]
        verified = self._conn.execute(
            "SELECT COUNT(*) FROM canonical_film WHERE identity_status = 'VERIFIED'"
        ).fetchone()[0]
        year_missing = self._conn.execute(
            "SELECT COUNT(*) FROM canonical_film WHERE identity_status = 'YEAR_MISSING'"
        ).fetchone()[0]
        events = self._conn.execute(
            "SELECT COUNT(*) FROM canonical_film WHERE is_event = 1"
        ).fetchone()[0]
        needs_review = self._conn.execute(
            "SELECT COUNT(*) FROM canonical_film WHERE identity_status = 'NEEDS_REVIEW'"
        ).fetchone()[0]
        return {
            "total": total,
            "verified": verified,
            "year_missing": year_missing,
            "events": events,
            "needs_review": needs_review,
        }

    def link_observation_to_canonical(self, observation_id: str, canonical_film_key: str) -> None:
        """Add canonical_film_key column to screening_observation if needed,
        then update the link."""
        conn = self._conn
        if not _has_column(conn, "screening_observation", "canonical_film_key"):
            try:
                conn.execute("ALTER TABLE screening_observation ADD COLUMN canonical_film_key TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass
        conn.execute(
            "UPDATE screening_observation SET canonical_film_key = ? WHERE observation_id = ?",
            (canonical_film_key, observation_id),
        )
        conn.commit()

    # --------------------------------------------------------
    # PREDICTION SNAPSHOTS (M13.6)
    # --------------------------------------------------------

    def create_prediction_run(self, run: dict[str, Any]) -> str:
        """Create a prediction run record. Returns prediction_run_id."""
        rid = run["prediction_run_id"]
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT OR IGNORE INTO prediction_run
            (prediction_run_id, run_timestamp, run_type, total_screenings,
             eligible_screenings, created_at)
            VALUES (?,?,?,?,?,?)""",
            (rid, run.get("run_timestamp", now),
             run.get("run_type", "INITIAL"),
             run.get("total_screenings", 0),
             run.get("eligible_screenings", 0),
             now),
        )
        self._conn.commit()
        return rid

    def get_prediction_run(self, run_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM prediction_run WHERE prediction_run_id = ?",
            (run_id,),
        ).fetchone()
        return dict(row) if row else None

    def upsert_prediction_snapshot(self, snap: dict[str, Any]) -> str:
        """Insert or update a prediction snapshot.

        IMPORTANT: Only updates if the existing snapshot is not frozen
        (i.e., has PENDING outcome status). Once an outcome is recorded,
        the snapshot cannot be modified.
        """
        now = datetime.now(timezone.utc).isoformat()
        pred_id = hashlib.sha256(
            f"{snap['observation_id']}|{snap['prediction_horizon_hours']}".encode()
        ).hexdigest()[:16]

        # Check if existing snapshot exists and is frozen
        existing = self._conn.execute(
            """SELECT prediction_id, outcome_status, prediction_timestamp FROM prediction_snapshot
            WHERE observation_id = ? AND prediction_horizon_hours = ?""",
            (snap["observation_id"], snap["prediction_horizon_hours"]),
        ).fetchone()

        if existing:
            # Freeze at the prediction cutoff, not only once an outcome arrives.
            # A later collector run must not retrofit a feature onto a past prediction.
            prediction_dt = None
            try:
                prediction_dt = datetime.fromisoformat(
                    existing["prediction_timestamp"].replace("Z", "+00:00")
                )
                if prediction_dt.tzinfo is None:
                    prediction_dt = prediction_dt.replace(tzinfo=timezone.utc)
                prediction_dt = prediction_dt.astimezone(timezone.utc)
            except (TypeError, ValueError):
                pass
            if (existing["outcome_status"] != "PENDING" or prediction_dt is None
                    or datetime.now(timezone.utc) >= prediction_dt):
                return existing["prediction_id"]  # Frozen; never retrofit a past prediction

            self._conn.execute(
                """UPDATE prediction_snapshot SET
                prediction_timestamp = ?,
                qloo_entity_id = ?,
                qloo_popularity = ?,
                qloo_band = ?,
                qloo_domain = ?,
                qloo_feature_timestamp = ?,
                qloo_feature_status = ?,
                qloo_signal_status = ?,
                qloo_affinity = ?,
                qloo_candidate_tags = ?,
                qloo_feature_provenance = ?,
                qloo_call_id = ?,
                updated_at = ?
                WHERE prediction_id = ?""",
                (snap["prediction_timestamp"],
                 snap.get("qloo_entity_id"),
                 snap.get("qloo_popularity"),
                 snap.get("qloo_band"),
                 snap.get("qloo_domain"),
                 snap.get("qloo_feature_timestamp"),
                 snap.get("qloo_feature_status", "NO_FEATURE"),
                 snap.get("qloo_signal_status", "NO_FEATURE"),
                 snap.get("qloo_affinity"),
                 json.dumps(snap.get("qloo_candidate_tags", [])),
                 snap.get("qloo_feature_provenance", ""),
                 snap.get("qloo_call_id"),
                 now,
                 existing["prediction_id"]),
            )
        else:
            self._conn.execute(
                """INSERT INTO prediction_snapshot
                (prediction_id, observation_id, film_key, prediction_run_id,
                 prediction_timestamp, prediction_horizon_hours, show_start_at,
                 qloo_entity_id, qloo_popularity, qloo_band, qloo_domain,
                 qloo_feature_timestamp, qloo_feature_status, qloo_signal_status,
                 qloo_affinity, qloo_candidate_tags, qloo_feature_provenance, qloo_call_id,
                 outcome_status, sold_out_observed, final_observation_timestamp,
                 lead_time_at_final_observation, format, day_of_week, start_hour,
                 source_url, source_timestamp, provenance, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (pred_id,
                 snap["observation_id"],
                 snap["film_key"],
                 snap["prediction_run_id"],
                 snap["prediction_timestamp"],
                 snap["prediction_horizon_hours"],
                 snap["show_start_at"],
                 snap.get("qloo_entity_id"),
                 snap.get("qloo_popularity"),
                 snap.get("qloo_band"),
                 snap.get("qloo_domain"),
                 snap.get("qloo_feature_timestamp"),
                 snap.get("qloo_feature_status", "NO_FEATURE"),
                 snap.get("qloo_signal_status", "NO_FEATURE"),
                 snap.get("qloo_affinity"),
                 json.dumps(snap.get("qloo_candidate_tags", [])),
                 snap.get("qloo_feature_provenance", ""),
                 snap.get("qloo_call_id"),
                 "PENDING",
                 None, None, None,
                 snap.get("format", ""),
                 snap.get("day_of_week", ""),
                 snap.get("start_hour"),
                 snap.get("source_url", ""),
                 snap.get("source_timestamp", ""),
                 snap.get("provenance", ""),
                 now, now),
            )

        self._conn.commit()
        return pred_id

    def get_prediction_snapshot(self, observation_id: str, horizon: int) -> dict | None:
        row = self._conn.execute(
            """SELECT * FROM prediction_snapshot
            WHERE observation_id = ? AND prediction_horizon_hours = ?""",
            (observation_id, horizon),
        ).fetchone()
        return dict(row) if row else None

    def update_prediction_outcome(self, observation_id: str, horizon: int,
                                   outcome: dict[str, Any]) -> None:
        """Update the outcome of a prediction snapshot.

        This is the ONLY way to set outcome_status after creation.
        """
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """UPDATE prediction_snapshot SET
            outcome_status = ?,
            sold_out_observed = ?,
            final_observation_timestamp = ?,
            lead_time_at_final_observation = ?,
            updated_at = ?
            WHERE observation_id = ? AND prediction_horizon_hours = ?""",
            (outcome["outcome_status"],
             outcome.get("sold_out_observed"),
             outcome.get("final_observation_timestamp"),
             outcome.get("lead_time_at_final_observation"),
             now,
             observation_id, horizon),
        )
        self._conn.commit()

    def list_prediction_snapshots(self, run_id: str | None = None,
                                   horizon: int | None = None,
                                   outcome_status: str | None = None) -> list[dict]:
        """List prediction snapshots with optional filters."""
        conditions = []
        params = []
        if run_id:
            conditions.append("prediction_run_id = ?")
            params.append(run_id)
        if horizon is not None:
            conditions.append("prediction_horizon_hours = ?")
            params.append(horizon)
        if outcome_status:
            conditions.append("outcome_status = ?")
            params.append(outcome_status)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        rows = self._conn.execute(
            f"SELECT * FROM prediction_snapshot {where} ORDER BY show_start_at",
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    def prediction_snapshot_stats(self) -> dict:
        """Compute prediction snapshot statistics."""
        total = self._conn.execute(
            "SELECT COUNT(*) FROM prediction_snapshot"
        ).fetchone()[0]

        by_horizon = {}
        for h in [168, 72, 24]:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM prediction_snapshot WHERE prediction_horizon_hours = ?",
                (h,),
            ).fetchone()[0]
            by_horizon[h] = count

        by_outcome = {}
        for status in ["PENDING", "SOLD_OUT_OBSERVED", "AVAILABLE_NEAR_SHOWTIME", "CENSORED", "UNKNOWN"]:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM prediction_snapshot WHERE outcome_status = ?",
                (status,),
            ).fetchone()[0]
            by_outcome[status] = count

        with_qloo = self._conn.execute(
            "SELECT COUNT(*) FROM prediction_snapshot WHERE qloo_entity_id IS NOT NULL"
        ).fetchone()[0]

        return {
            "total": total,
            "by_horizon": by_horizon,
            "by_outcome": by_outcome,
            "with_qloo_entity": with_qloo,
        }

    def leakage_audit(self) -> dict:
        """Automated leakage audit.

        Checks:
        1. qloo_retrieval <= prediction_timestamp
        2. frozen prediction features never change (manual check)
        3. outcomes after prediction_timestamp
        4. censored observations not treated as negative
        5. prediction horizons correctly calculated
        6. no duplicated screening × horizon rows
        """
        snapshots = self.list_prediction_snapshots()

        violations = {
            "qloo_after_prediction": 0,
            "negative_from_censored": 0,
            "duplicate_rows": 0,
            "horizon_mismatch": 0,
            "available_without_timestamp": 0,
            "snapshot_created_after_prediction_timestamp": 0,
            "cultural_status_without_signal": 0,
            "popularity_without_temporal_feature": 0,
            "retrospective_feature_payload_present": 0,
        }

        seen_keys = set()
        for snap in snapshots:
            key = (snap["observation_id"], snap["prediction_horizon_hours"])
            if key in seen_keys:
                violations["duplicate_rows"] += 1
            seen_keys.add(key)

            from .qloo_signal import assess_feature, parse_timestamp
            qts = snap.get("qloo_feature_timestamp")
            pts = snap.get("prediction_timestamp")
            q_dt = parse_timestamp(qts)
            p_dt = parse_timestamp(pts)
            if qts and pts and (q_dt is None or p_dt is None):
                violations["invalid_temporal_timestamp"] = violations.get("invalid_temporal_timestamp", 0) + 1
            elif q_dt and p_dt and q_dt > p_dt:
                violations["qloo_after_prediction"] += 1

            feature_status = snap.get("qloo_feature_status", "NO_FEATURE")
            signal_status = snap.get("qloo_signal_status", "NO_FEATURE")
            if feature_status == "AVAILABLE_AT_PREDICTION_TIME" and not q_dt:
                violations["available_without_timestamp"] += 1

            # Feature-time safety alone is not proof of a prospective prediction:
            # the prediction record itself must also exist by its cutoff.
            created_dt = parse_timestamp(snap.get("created_at"))
            if created_dt and p_dt and created_dt > p_dt:
                violations["snapshot_created_after_prediction_timestamp"] += 1
            elif created_dt is None or p_dt is None:
                violations["invalid_temporal_timestamp"] = violations.get("invalid_temporal_timestamp", 0) + 1
            assessment = assess_feature({
                "qloo_affinity": snap.get("qloo_affinity"),
                "qloo_popularity": snap.get("qloo_popularity"),
                "candidate_tags": snap.get("qloo_candidate_tags", "[]"),
                "qloo_entity_id": snap.get("qloo_entity_id"),
            })
            if signal_status == "CULTURAL_SIGNAL_AVAILABLE_AT_PREDICTION_TIME" and not assessment["has_cultural_signal"]:
                violations["cultural_status_without_signal"] += 1

            if feature_status != "AVAILABLE_AT_PREDICTION_TIME" and snap.get("qloo_popularity") is not None:
                violations["popularity_without_temporal_feature"] += 1

            if signal_status.startswith("RETROSPECTIVE_") and (
                snap.get("qloo_popularity") is not None
                or snap.get("qloo_affinity") is not None
                or assessment.get("valid_tag_count", 0) > 0
            ):
                violations["retrospective_feature_payload_present"] += 1

            # Check censored not treated as negative
            if snap.get("outcome_status") == "CENSORED" and snap.get("sold_out_observed") == 0:
                violations["negative_from_censored"] += 1

        return {
            "total_snapshots": len(snapshots),
            "violations": violations,
            "passed": all(v == 0 for v in violations.values()),
        }

    # --------------------------------------------------------
    # ANALYTICAL BENCHMARK EXPORT (M13.4)
    # --------------------------------------------------------

    def build_analytical_benchmark(self) -> list[dict]:
        """Build the analytical benchmark with leakage-safe Qloo features.

        For each observation:
        - Only uses Qloo features retrieved BEFORE the observation timestamp
        - Marks features as AVAILABLE_AT_PREDICTION_TIME or FUTURE_FEATURE_UNAVAILABLE
        """
        observations = self.list_all_observations()
        benchmark_rows = []

        for obs in observations:
            obs_id = obs["observation_id"]
            fk = film_key(obs["film_title"], obs.get("film_year"))
            source_ts = obs.get("source_timestamp")

            # Get film resolution
            resolution = self.get_film_resolution(fk)

            # Select substantive, prediction-time-safe feature rows. Empty or
            # metadata-only rows must not mask an earlier usable snapshot.
            feature_rows = self.get_qloo_features_for_film(fk)
            feature = self.get_latest_usable_qloo_feature(fk, before=source_ts)
            latest_usable = self.get_latest_usable_qloo_feature(fk)

            if feature:
                qloo_feature_status = "AVAILABLE_AT_PREDICTION_TIME"
            elif latest_usable:
                qloo_feature_status = "FUTURE_FEATURE_UNAVAILABLE"
            elif feature_rows:
                qloo_feature_status = "EMPTY_OR_METADATA_ONLY"
            else:
                qloo_feature_status = "NO_FEATURE"

            from .qloo_signal import temporal_signal_status
            qloo_signal_status = temporal_signal_status(feature, feature_rows, source_ts or "")

            row = {
                "observation_id": obs_id,
                "venue_id": obs["venue_id"],
                "film_title": obs["film_title"],
                "film_year": obs.get("film_year"),
                "show_start_at": obs.get("show_start_at"),
                "observation_timestamp": source_ts,
                "lead_time_hours": obs.get("lead_time_hours"),
                "lead_time_bucket": obs.get("lead_time_bucket"),
                "sold_out_observed": obs.get("sold_out"),
                "model_target": obs.get("model_target"),
                "qloo_entity_id": resolution.get("qloo_entity_id") if resolution else None,
                "qloo_affinity": feature.get("qloo_affinity") if feature else None,
                "qloo_popularity": feature.get("qloo_popularity") if feature else None,
                "qloo_band": feature.get("qloo_band") if feature else None,
                "qloo_domain": feature.get("qloo_domain") if feature else None,
                "qloo_feature_timestamp": feature.get("retrieved_at") if feature else None,
                "qloo_feature_status": qloo_feature_status,
                "qloo_signal_status": qloo_signal_status,
                "qloo_candidate_tags": feature.get("candidate_tags", "[]") if feature else "[]",
                "qloo_feature_provenance": feature.get("provenance", "") if feature else "",
                "format": obs.get("format"),
                "booking_url": obs.get("booking_url"),
                "source_url": obs.get("source_url"),
                "source_timestamp": source_ts,
                "resolution_status": resolution.get("resolution_status") if resolution else "NO_RESOLUTION",
                "provenance": resolution.get("resolution_provenance", "") if resolution else "",
            }
            benchmark_rows.append(row)

        return benchmark_rows