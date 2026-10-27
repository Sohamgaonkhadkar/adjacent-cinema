"""SQLite storage for Audience Pulse, mixed into ``ExperimentRepository``.

Why a mixin on the existing repository rather than a second database
---------------------------------------------------------------------
The experiment lifecycle already owns a SQLite file, a re-entrant lock and an
append-only convention. A poll is *part of* a saved experiment, and the whole
point of the feature is that the poll cannot be separated from the hypothesis it
was written against. Sharing the connection, the lock and the file keeps that
link structural instead of hopeful, and it means one backup covers both.

What the schema guarantees
--------------------------
* ``pulse_polls.experiment_id`` is a real foreign key to ``experiments``.
* The definition columns are frozen by a trigger the moment ``frozen_at`` is
  set (on the first stored response). No code path — including a future bug or a
  manual SQL statement — can rewrite the question, options, rule, hypothesis or
  window after voting begins.
* ``UNIQUE(poll_id, respondent_key)`` makes a replay physically impossible.
* Evaluations are append-only, with ``supersedes_id`` recording corrections.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from .pulse import (
    MAX_POLLS_PER_EXPERIMENT,
    MAX_RESPONSES_PER_POLL,
    OUTCOMES,
    PulseCapacityError,
    PulseClosedError,
    PulseValidationError,
    collection_status,
    evaluate,
    normalise_definition,
    tabulate,
)
from .store_errors import DuplicateRequest

PULSE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pulse_polls (
    poll_id           TEXT PRIMARY KEY,
    experiment_id     TEXT NOT NULL REFERENCES experiments(experiment_id),
    request_id        TEXT NOT NULL UNIQUE,
    created_at        TEXT NOT NULL,
    share_token       TEXT NOT NULL UNIQUE,
    question          TEXT NOT NULL,
    options           TEXT NOT NULL,
    hypothesis        TEXT NOT NULL,
    experiment_snapshot TEXT NOT NULL DEFAULT '{}',
    decision_rule     TEXT NOT NULL,
    opens_at          TEXT NOT NULL,
    closes_at         TEXT NOT NULL,
    closed_at         TEXT,
    frozen_at         TEXT
);

CREATE TABLE IF NOT EXISTS pulse_responses (
    response_id      TEXT PRIMARY KEY,
    poll_id          TEXT NOT NULL REFERENCES pulse_polls(poll_id),
    respondent_key   TEXT NOT NULL,
    option_id        TEXT NOT NULL,
    submitted_at     TEXT NOT NULL,
    UNIQUE (poll_id, respondent_key)
);

CREATE TABLE IF NOT EXISTS pulse_evaluations (
    evaluation_id     TEXT PRIMARY KEY,
    poll_id           TEXT NOT NULL REFERENCES pulse_polls(poll_id),
    request_id        TEXT NOT NULL UNIQUE,
    created_at        TEXT NOT NULL,
    outcome           TEXT NOT NULL,
    rationale         TEXT NOT NULL,
    rule_applied      TEXT NOT NULL,
    counts            TEXT NOT NULL,
    sample_size       INTEGER NOT NULL,
    collection_status TEXT NOT NULL,
    limitations       TEXT NOT NULL DEFAULT '[]',
    supersedes_id     TEXT
);

CREATE TRIGGER IF NOT EXISTS pulse_polls_definition_frozen
BEFORE UPDATE ON pulse_polls
WHEN OLD.frozen_at IS NOT NULL
 AND (
   NEW.question IS NOT OLD.question
   OR NEW.options IS NOT OLD.options
   OR NEW.decision_rule IS NOT OLD.decision_rule
   OR NEW.hypothesis IS NOT OLD.hypothesis
   OR NEW.opens_at IS NOT OLD.opens_at
   OR NEW.closes_at IS NOT OLD.closes_at
   OR NEW.experiment_id IS NOT OLD.experiment_id
   OR NEW.experiment_snapshot IS NOT OLD.experiment_snapshot
 )
BEGIN
    SELECT RAISE(ABORT, 'poll definition is frozen once voting begins');
END;
"""

_LOCKED_FIELDS = (
    "question",
    "options",
    "decision_rule",
    "hypothesis",
    "opens_at",
    "closes_at",
    "experiment_id",
)


def respondent_key(raw_token: str) -> str:
    """Hash a browser-issued token; the raw value is never stored."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


class PulseStoreMixin:
    """Poll storage methods. Requires ``self._conn`` and ``self._lock``."""

    def migrate_pulse_schema(self) -> None:
        """Add columns that later versions introduced to an existing database."""
        columns = {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(pulse_evaluations)").fetchall()
        }
        if columns and "limitations" not in columns:
            self._conn.execute(
                "ALTER TABLE pulse_evaluations ADD COLUMN limitations TEXT NOT NULL DEFAULT '[]'"
            )
            self._conn.commit()

    # -- creation ----------------------------------------------------------
    def create_poll(
        self,
        experiment_id: str,
        *,
        request_id: str,
        question: Any,
        options: Any,
        opens_at: Any,
        closes_at: Any,
        decision_rule: Any,
        now: str | None = None,
    ) -> dict[str, Any]:
        moment = now or _iso(datetime.now(UTC))
        with self._lock:
            experiment = self.get_experiment(experiment_id)
            if experiment is None:
                raise KeyError(f"experiment {experiment_id} not found")

            existing = self._conn.execute(
                "SELECT poll_id FROM pulse_polls WHERE request_id = ?", (request_id,)
            ).fetchone()
            if existing:
                raise DuplicateRequest({"poll_id": existing["poll_id"]})

            definition = normalise_definition(
                question=question,
                options=options,
                opens_at=opens_at,
                closes_at=closes_at,
                decision_rule=decision_rule,
                now=moment,
            )

            polls = self._poll_rows(experiment_id)
            if len(polls) >= MAX_POLLS_PER_EXPERIMENT:
                raise PulseValidationError(
                    f"this experiment already has {MAX_POLLS_PER_EXPERIMENT} polls; that is the "
                    "bound for one saved decision"
                )
            for row in polls:
                poll = self._poll_from_row(row)
                if collection_status(poll, now=moment)["accepting_responses"]:
                    raise PulseValidationError(
                        "this experiment already has a poll accepting responses; close it before "
                        "opening another so each collection window stays interpretable"
                    )

            poll_id = str(uuid.uuid4())
            self._conn.execute(
                """INSERT INTO pulse_polls (poll_id, experiment_id, request_id, created_at,
                   share_token, question, options, hypothesis, experiment_snapshot,
                   decision_rule, opens_at, closes_at, closed_at, frozen_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    poll_id,
                    experiment_id,
                    request_id,
                    moment,
                    secrets.token_urlsafe(32),
                    definition["question"],
                    json.dumps(definition["options"]),
                    experiment["hypothesis"],
                    json.dumps(_experiment_snapshot(experiment)),
                    json.dumps(definition["decision_rule"]),
                    definition["opens_at"],
                    definition["closes_at"],
                    None,
                    None,
                ),
            )
            self._conn.commit()
            return self.get_poll(poll_id, now=moment)

    # -- reads -------------------------------------------------------------
    def list_polls(self, experiment_id: str, *, now: str | None = None) -> list[dict[str, Any]]:
        moment = now or _iso(datetime.now(UTC))
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM pulse_polls WHERE experiment_id = ? ORDER BY created_at",
                (experiment_id,),
            ).fetchall()
            return [self._poll_dict(row["poll_id"], now=moment) for row in rows]

    def get_poll(self, poll_id: str, *, now: str | None = None) -> dict[str, Any] | None:
        moment = now or _iso(datetime.now(UTC))
        with self._lock:
            row = self._conn.execute(
                "SELECT poll_id FROM pulse_polls WHERE poll_id = ?", (poll_id,)
            ).fetchone()
            return self._poll_dict(row["poll_id"], now=moment) if row else None

    def get_poll_by_token(
        self, share_token: str, *, now: str | None = None
    ) -> dict[str, Any] | None:
        moment = now or _iso(datetime.now(UTC))
        if not isinstance(share_token, str) or not share_token:
            return None
        with self._lock:
            row = self._conn.execute(
                "SELECT poll_id FROM pulse_polls WHERE share_token = ?", (share_token,)
            ).fetchone()
            return self._poll_dict(row["poll_id"], now=moment) if row else None

    def has_responded(self, poll_id: str, raw_token: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM pulse_responses WHERE poll_id = ? AND respondent_key = ?",
                (poll_id, respondent_key(raw_token)),
            ).fetchone()
            return row is not None

    # -- responses ---------------------------------------------------------
    def add_poll_response(
        self,
        poll_id: str,
        *,
        respondent_token: str,
        option_id: Any,
        now: str | None = None,
    ) -> dict[str, Any]:
        moment = now or _iso(datetime.now(UTC))
        if not isinstance(respondent_token, str) or len(respondent_token) < 16:
            raise PulseValidationError("a poll response needs the browsing session that opened it")

        with self._lock:
            poll = self.get_poll(poll_id, now=moment)
            if poll is None:
                raise KeyError(f"poll {poll_id} not found")

            status = poll["collection"]
            if not status["accepting_responses"]:
                raise PulseClosedError(status)

            valid_ids = {option["option_id"] for option in poll["options"]}
            if option_id not in valid_ids:
                raise PulseValidationError("that option is not on this poll")

            total = self._conn.execute(
                "SELECT COUNT(*) FROM pulse_responses WHERE poll_id = ?", (poll_id,)
            ).fetchone()[0]
            if total >= MAX_RESPONSES_PER_POLL:
                raise PulseCapacityError(
                    f"this poll already stores {MAX_RESPONSES_PER_POLL} responses, its ceiling"
                )

            key = respondent_key(respondent_token)
            duplicate = self._conn.execute(
                "SELECT response_id FROM pulse_responses WHERE poll_id = ? AND respondent_key = ?",
                (poll_id, key),
            ).fetchone()
            if duplicate:
                raise DuplicateRequest({"already_responded": True})

            # Freeze the definition at the first stored response. The trigger
            # makes this permanent; the condition keeps it idempotent.
            self._conn.execute(
                "UPDATE pulse_polls SET frozen_at = ? WHERE poll_id = ? AND frozen_at IS NULL",
                (moment, poll_id),
            )
            response_id = str(uuid.uuid4())
            try:
                self._conn.execute(
                    """INSERT INTO pulse_responses (response_id, poll_id, respondent_key,
                       option_id, submitted_at) VALUES (?,?,?,?,?)""",
                    (response_id, poll_id, key, option_id, moment),
                )
            except sqlite3.IntegrityError as exc:  # the UNIQUE constraint, raced
                self._conn.rollback()
                raise DuplicateRequest({"already_responded": True}) from exc
            self._conn.commit()

            return {
                "recorded": True,
                "response_id": response_id,
                "submitted_at": moment,
                "collection": collection_status({**poll, "responses": []}, now=moment),
            }

    # -- owner actions -----------------------------------------------------
    def close_poll(self, poll_id: str, *, now: str | None = None) -> dict[str, Any]:
        moment = now or _iso(datetime.now(UTC))
        with self._lock:
            poll = self.get_poll(poll_id, now=moment)
            if poll is None:
                raise KeyError(f"poll {poll_id} not found")
            if poll.get("closed_at") is None:
                self._conn.execute(
                    "UPDATE pulse_polls SET closed_at = ? WHERE poll_id = ?", (moment, poll_id)
                )
                self._conn.commit()
            return self.get_poll(poll_id, now=moment)

    def add_poll_evaluation(
        self,
        poll_id: str,
        *,
        request_id: str,
        now: str | None = None,
    ) -> dict[str, Any]:
        """Apply the frozen rule to the stored responses and append the result."""
        moment = now or _iso(datetime.now(UTC))
        with self._lock:
            poll = self.get_poll(poll_id, now=moment)
            if poll is None:
                raise KeyError(f"poll {poll_id} not found")

            existing = self._conn.execute(
                "SELECT evaluation_id FROM pulse_evaluations WHERE request_id = ?", (request_id,)
            ).fetchone()
            if existing:
                raise DuplicateRequest(
                    {"evaluation_id": existing["evaluation_id"], "already_evaluated": True}
                )

            result = evaluate(poll, poll["responses"], now=moment)
            if result["outcome"] not in OUTCOMES:  # pragma: no cover - defensive
                raise PulseValidationError("evaluation produced an unknown outcome")

            prior = self._conn.execute(
                """SELECT evaluation_id FROM pulse_evaluations
                   WHERE poll_id = ? ORDER BY created_at DESC LIMIT 1""",
                (poll_id,),
            ).fetchone()

            evaluation_id = str(uuid.uuid4())
            self._conn.execute(
                """INSERT INTO pulse_evaluations (evaluation_id, poll_id, request_id, created_at,
                   outcome, rationale, rule_applied, counts, sample_size, collection_status,
                   limitations, supersedes_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    evaluation_id,
                    poll_id,
                    request_id,
                    moment,
                    result["outcome"],
                    result["rationale"],
                    json.dumps({**result["rule"], "statement": result["rule_statement"]}),
                    json.dumps(
                        {
                            "total": result["counts"]["total"],
                            "options": result["counts"]["options"],
                            "unrecognised": result["counts"]["unrecognised"],
                        }
                    ),
                    result["sample_size"],
                    result["collection"]["status"],
                    json.dumps(result["limitations"]),
                    prior["evaluation_id"] if prior else None,
                ),
            )
            self._conn.commit()
            return self._poll_evaluation_dict(evaluation_id)

    def list_poll_evaluations(self, poll_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT evaluation_id FROM pulse_evaluations WHERE poll_id = ? ORDER BY created_at",
                (poll_id,),
            ).fetchall()
            return [self._poll_evaluation_dict(row["evaluation_id"]) for row in rows]

    # -- internals ---------------------------------------------------------
    def _poll_rows(self, experiment_id: str) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM pulse_polls WHERE experiment_id = ? ORDER BY created_at",
            (experiment_id,),
        ).fetchall()

    def _poll_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "poll_id": row["poll_id"],
            "experiment_id": row["experiment_id"],
            "created_at": row["created_at"],
            "share_token": row["share_token"],
            "question": row["question"],
            "options": json.loads(row["options"]),
            "hypothesis": row["hypothesis"],
            "experiment_snapshot": json.loads(row["experiment_snapshot"]),
            "decision_rule": json.loads(row["decision_rule"]),
            "opens_at": row["opens_at"],
            "closes_at": row["closes_at"],
            "closed_at": row["closed_at"],
            "frozen_at": row["frozen_at"],
        }

    def _poll_dict(self, poll_id: str, *, now: str) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT * FROM pulse_polls WHERE poll_id = ?", (poll_id,)
        ).fetchone()
        poll = self._poll_from_row(row)
        responses = [
            dict(response)
            for response in self._conn.execute(
                "SELECT response_id, option_id, submitted_at FROM pulse_responses "
                "WHERE poll_id = ? ORDER BY submitted_at",
                (poll_id,),
            ).fetchall()
        ]
        # Respondent keys are never returned: the payload needs counts, not the
        # identity of who answered.
        counts = tabulate(poll, responses)
        poll["responses"] = responses
        poll["counts"] = counts
        poll["response_count"] = counts["total"]
        poll["collection"] = collection_status(poll, now=now)
        poll["definition_frozen"] = poll["frozen_at"] is not None
        latest = self._conn.execute(
            """SELECT evaluation_id FROM pulse_evaluations
               WHERE poll_id = ? ORDER BY created_at DESC LIMIT 1""",
            (poll_id,),
        ).fetchone()
        poll["latest_evaluation"] = (
            self._poll_evaluation_dict(latest["evaluation_id"]) if latest else None
        )
        poll["evaluation_preview"] = evaluate(poll, responses, now=now)
        return poll

    def _poll_evaluation_dict(self, evaluation_id: str) -> dict[str, Any]:
        """Poll evaluations share no id space with experiment evaluations."""
        row = self._conn.execute(
            "SELECT * FROM pulse_evaluations WHERE evaluation_id = ?", (evaluation_id,)
        ).fetchone()
        return {
            "evaluation_id": row["evaluation_id"],
            "poll_id": row["poll_id"],
            "created_at": row["created_at"],
            "outcome": row["outcome"],
            "rationale": row["rationale"],
            "rule_applied": json.loads(row["rule_applied"]),
            "counts": json.loads(row["counts"]),
            "sample_size": row["sample_size"],
            "collection_status": row["collection_status"],
            "limitations": json.loads(row["limitations"]),
            "supersedes_id": row["supersedes_id"],
        }


def _experiment_snapshot(experiment: dict[str, Any]) -> dict[str, Any]:
    """The parts of the saved experiment a poll is judged against, frozen."""
    return {
        "experiment_id": experiment.get("experiment_id"),
        "film_title": experiment.get("film_title"),
        "hypothesis": experiment.get("hypothesis"),
        "success_criteria": experiment.get("success_criteria"),
        "observation_window": experiment.get("observation_window"),
        "data_status": experiment.get("data_status"),
        "source_run_id": experiment.get("source_run_id"),
        "created_at": experiment.get("created_at"),
    }


__all__ = ["PULSE_SCHEMA_SQL", "PulseStoreMixin", "respondent_key"]
