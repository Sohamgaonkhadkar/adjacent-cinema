"""Experiment lifecycle repository (M13.9).

Persists the decision-to-observation loop for Creator (and future) modes:

    Test Card → saved experiment (PLANNED)
              → observations (partial allowed; zero ≠ missing)
              → evaluations (SUPPORTED / CONTRADICTED / INCONCLUSIVE)
              → retrievable history (append-only; corrections supersede)

Design rules (mirroring outcome_ledger / outcome_repository conventions):
* SQLite, schema created idempotently on open; no ORM.
* Every write carries a client-supplied ``request_id`` with a UNIQUE
  constraint, so retries never create duplicate rows.
* Records are never updated in place and never deleted; a correction inserts
  a new row with ``supersedes_id`` pointing at the record it replaces.
* A saved experiment snapshots the Test Card / Bet evidence AS GENERATED —
  later evidence changes never rewrite the original decision.
* NULL means unavailable. An observed zero is stored as 0, never as NULL.
"""

from __future__ import annotations

import functools
import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VALID_MEASUREMENT_STATUS = {"OBSERVED", "PARTIAL", "MISSING", "UNAVAILABLE", "FAILED"}
VALID_OBSERVATION_KINDS = {"ANALYTICS", "SCREENING", "FEEDBACK", "NOTE"}
VALID_OUTCOMES = {"SUPPORTED", "CONTRADICTED", "INCONCLUSIVE"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id     TEXT PRIMARY KEY,
    request_id        TEXT NOT NULL UNIQUE,
    created_at        TEXT NOT NULL,
    film_title        TEXT NOT NULL,
    film_context      TEXT NOT NULL DEFAULT '{}',
    hypothesis        TEXT NOT NULL,
    success_criteria  TEXT NOT NULL DEFAULT '',
    observation_window TEXT NOT NULL DEFAULT '',
    action_plan       TEXT NOT NULL DEFAULT '',
    data_status       TEXT NOT NULL,
    source_run_id     TEXT,
    source_bet        TEXT NOT NULL DEFAULT '{}',
    provenance        TEXT NOT NULL DEFAULT '{}',
    status            TEXT NOT NULL DEFAULT 'PLANNED',
    dedupe_key        TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS experiment_observations (
    observation_id    TEXT PRIMARY KEY,
    request_id        TEXT NOT NULL UNIQUE,
    experiment_id     TEXT NOT NULL REFERENCES experiments(experiment_id),
    created_at        TEXT NOT NULL,
    observed_on       TEXT,
    kind              TEXT NOT NULL,
    measurement_status TEXT NOT NULL,
    metrics           TEXT NOT NULL DEFAULT '{}',
    interpretation    TEXT,
    source            TEXT,
    evidence_ref      TEXT,
    limitations       TEXT,
    supersedes_id     TEXT
);

CREATE TABLE IF NOT EXISTS experiment_evaluations (
    evaluation_id     TEXT PRIMARY KEY,
    request_id        TEXT NOT NULL UNIQUE,
    experiment_id     TEXT NOT NULL REFERENCES experiments(experiment_id),
    created_at        TEXT NOT NULL,
    outcome           TEXT NOT NULL,
    rationale         TEXT NOT NULL,
    observations_used TEXT NOT NULL DEFAULT '[]',
    unknowns          TEXT,
    supersedes_id     TEXT
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _synchronized(method):
    """Serialise repository access through the instance lock (reentrant)."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class DuplicateRequest(Exception):
    """Raised with the already-stored row when a request_id is replayed."""

    def __init__(self, existing: dict[str, Any]) -> None:
        self.existing = existing
        super().__init__("duplicate request_id")


class ExperimentRepository:
    """Append-only experiment store. Safe across process restarts."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False + an explicit lock: FastAPI may serve the
        # write endpoints from a different thread than the one that opened the
        # repository (TestClient portal, worker threads). All access is
        # serialised through self._lock, so sharing the connection is safe.
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- experiments -------------------------------------------------------
    @_synchronized
    def save_experiment(
        self,
        *,
        request_id: str,
        film_title: str,
        hypothesis: str,
        film_context: dict[str, Any] | None = None,
        success_criteria: str = "",
        observation_window: str = "",
        action_plan: str = "",
        data_status: str,
        source_run_id: str | None = None,
        source_bet: dict[str, Any] | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Save a Test Card as a planned experiment.

        Idempotent twice over: a replayed ``request_id`` and a second save for
        the same ``source_run_id`` both return the ORIGINAL record instead of
        creating a duplicate decision.
        """
        existing = self._conn.execute(
            "SELECT * FROM experiments WHERE request_id = ?", (request_id,)
        ).fetchone()
        if existing:
            raise DuplicateRequest(self._row_to_experiment(existing))
        if source_run_id:
            prior = self._conn.execute(
                "SELECT * FROM experiments WHERE dedupe_key = ?",
                (f"run:{source_run_id}",),
            ).fetchone()
            if prior:
                raise DuplicateRequest(self._row_to_experiment(prior))

        experiment_id = str(uuid.uuid4())
        self._conn.execute(
            """INSERT INTO experiments (experiment_id, request_id, created_at,
               film_title, film_context, hypothesis, success_criteria,
               observation_window, action_plan, data_status, source_run_id,
               source_bet, provenance, status, dedupe_key)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                experiment_id, request_id, _now(), film_title,
                json.dumps(film_context or {}), hypothesis, success_criteria,
                observation_window, action_plan, data_status, source_run_id,
                json.dumps(source_bet or {}), json.dumps(provenance or {}),
                "PLANNED", f"run:{source_run_id}" if source_run_id else None,
            ),
        )
        self._conn.commit()
        return self.get_experiment(experiment_id)

    @_synchronized
    def list_experiments(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM experiments ORDER BY created_at DESC"
        ).fetchall()
        out = []
        for row in rows:
            exp = self._row_to_experiment(row)
            exp["observation_count"] = self._conn.execute(
                "SELECT COUNT(*) FROM experiment_observations WHERE experiment_id=?",
                (exp["experiment_id"],),
            ).fetchone()[0]
            latest = self._conn.execute(
                """SELECT outcome FROM experiment_evaluations
                   WHERE experiment_id=? AND supersedes_id IS NULL
                   ORDER BY created_at DESC LIMIT 1""",
                (exp["experiment_id"],),
            ).fetchone()
            exp["latest_evaluation"] = latest["outcome"] if latest else None
            out.append(exp)
        return out

    @_synchronized
    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM experiments WHERE experiment_id = ?", (experiment_id,)
        ).fetchone()
        return self._row_to_experiment(row) if row else None

    # -- observations --------------------------------------------------------
    @_synchronized
    def add_observation(
        self,
        experiment_id: str,
        *,
        request_id: str,
        kind: str,
        measurement_status: str,
        observed_on: str | None = None,
        metrics: dict[str, Any] | None = None,
        interpretation: str | None = None,
        source: str | None = None,
        evidence_ref: str | None = None,
        limitations: str | None = None,
        supersedes_id: str | None = None,
    ) -> dict[str, Any]:
        if kind not in VALID_OBSERVATION_KINDS:
            raise ValueError(f"kind must be one of {sorted(VALID_OBSERVATION_KINDS)}")
        if measurement_status not in VALID_MEASUREMENT_STATUS:
            raise ValueError(
                f"measurement_status must be one of {sorted(VALID_MEASUREMENT_STATUS)}"
            )
        if self.get_experiment(experiment_id) is None:
            raise KeyError(f"experiment {experiment_id} not found")
        existing = self._conn.execute(
            "SELECT observation_id FROM experiment_observations WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if existing:
            raise DuplicateRequest({"observation_id": existing["observation_id"]})

        observation_id = str(uuid.uuid4())
        self._conn.execute(
            """INSERT INTO experiment_observations (observation_id, request_id,
               experiment_id, created_at, observed_on, kind, measurement_status,
               metrics, interpretation, source, evidence_ref, limitations,
               supersedes_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                observation_id, request_id, experiment_id, _now(), observed_on,
                kind, measurement_status, json.dumps(metrics or {}),
                interpretation, source, evidence_ref, limitations, supersedes_id,
            ),
        )
        self._conn.commit()
        return self._observation_dict(observation_id)

    @_synchronized
    def list_observations(self, experiment_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT observation_id FROM experiment_observations
               WHERE experiment_id = ? ORDER BY created_at""",
            (experiment_id,),
        ).fetchall()
        return [self._observation_dict(r["observation_id"]) for r in rows]

    @_synchronized
    def get_observation(self, observation_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT 1 FROM experiment_observations WHERE observation_id = ?",
            (observation_id,),
        ).fetchone()
        return self._observation_dict(observation_id) if row else None

    @_synchronized
    def delete_observations(self, observation_ids: list[str]) -> int:
        """HARD DELETE — the single, deliberate exception to append-only.

        Reserved for external data-protection obligations: the YouTube API
        Services Developer Policies require deletion of Authorized Data when
        a creator revokes consent / disconnects. This is a user-initiated
        legal deletion, never a silent overwrite or correction — corrections
        still go through ``supersedes_id``. Callers leave a tombstone NOTE
        (containing no API data) so the ledger stays honest about the removal.
        """
        if not observation_ids:
            return 0
        placeholders = ",".join("?" * len(observation_ids))
        with self._conn:
            cursor = self._conn.execute(
                f"DELETE FROM experiment_observations WHERE observation_id IN ({placeholders})",
                observation_ids,
            )
        return cursor.rowcount

    # -- evaluations ---------------------------------------------------------
    @_synchronized
    def add_evaluation(
        self,
        experiment_id: str,
        *,
        request_id: str,
        outcome: str,
        rationale: str,
        observation_ids: list[str] | None = None,
        unknowns: str | None = None,
        supersedes_id: str | None = None,
    ) -> dict[str, Any]:
        if outcome not in VALID_OUTCOMES:
            raise ValueError(f"outcome must be one of {sorted(VALID_OUTCOMES)}")
        if self.get_experiment(experiment_id) is None:
            raise KeyError(f"experiment {experiment_id} not found")
        existing = self._conn.execute(
            "SELECT evaluation_id FROM experiment_evaluations WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if existing:
            raise DuplicateRequest({"evaluation_id": existing["evaluation_id"]})

        # A new evaluation supersedes the previous un-superseded one, keeping it
        # in history (append-only corrections).
        if supersedes_id is None:
            prior = self._conn.execute(
                """SELECT evaluation_id FROM experiment_evaluations
                   WHERE experiment_id = ? AND supersedes_id IS NULL""",
                (experiment_id,),
            ).fetchone()
            supersedes_id = prior["evaluation_id"] if prior else None

        evaluation_id = str(uuid.uuid4())
        self._conn.execute(
            """INSERT INTO experiment_evaluations (evaluation_id, request_id,
               experiment_id, created_at, outcome, rationale, observations_used,
               unknowns, supersedes_id) VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                evaluation_id, request_id, experiment_id, _now(), outcome,
                rationale, json.dumps(observation_ids or []), unknowns,
                supersedes_id,
            ),
        )
        self._conn.commit()
        return self._evaluation_dict(evaluation_id)

    @_synchronized
    def list_evaluations(self, experiment_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT evaluation_id FROM experiment_evaluations
               WHERE experiment_id = ? ORDER BY created_at""",
            (experiment_id,),
        ).fetchall()
        return [self._evaluation_dict(r["evaluation_id"]) for r in rows]

    # -- internals -----------------------------------------------------------
    def _row_to_experiment(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "experiment_id": row["experiment_id"],
            "request_id": row["request_id"],
            "created_at": row["created_at"],
            "film_title": row["film_title"],
            "film_context": json.loads(row["film_context"]),
            "hypothesis": row["hypothesis"],
            "success_criteria": row["success_criteria"],
            "observation_window": row["observation_window"],
            "action_plan": row["action_plan"],
            "data_status": row["data_status"],
            "source_run_id": row["source_run_id"],
            "source_bet": json.loads(row["source_bet"]),
            "provenance": json.loads(row["provenance"]),
            "status": row["status"],
        }

    def _observation_dict(self, observation_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT * FROM experiment_observations WHERE observation_id = ?",
            (observation_id,),
        ).fetchone()
        return {
            "observation_id": row["observation_id"],
            "experiment_id": row["experiment_id"],
            "created_at": row["created_at"],
            "observed_on": row["observed_on"],
            "kind": row["kind"],
            "measurement_status": row["measurement_status"],
            "metrics": json.loads(row["metrics"]),
            "interpretation": row["interpretation"],
            "source": row["source"],
            "evidence_ref": row["evidence_ref"],
            "limitations": row["limitations"],
            "supersedes_id": row["supersedes_id"],
        }

    def _evaluation_dict(self, evaluation_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT * FROM experiment_evaluations WHERE evaluation_id = ?",
            (evaluation_id,),
        ).fetchone()
        return {
            "evaluation_id": row["evaluation_id"],
            "experiment_id": row["experiment_id"],
            "created_at": row["created_at"],
            "outcome": row["outcome"],
            "rationale": row["rationale"],
            "observations_used": json.loads(row["observations_used"]),
            "unknowns": row["unknowns"],
            "supersedes_id": row["supersedes_id"],
        }
