"""FilmSponsor campaign repository.

Persists the sponsorship-campaign journey for Creator Mode:

    campaign intake → live brand discovery (evidence + limits)
                   → creator-editable sponsorship drafts (versioned)
                   → official-source review of commercial claims
                   → approval → export (approved content only)
                   → manual outreach + actual outcome recording

Design rules (mirroring ``experiment_repository`` conventions):
* SQLite in the same workspace database file as experiments (one store per
  workspace); schema created idempotently on open; no ORM.
* Every write carries a client-supplied ``request_id`` with a UNIQUE
  constraint, so retries never create duplicate rows.
* Records are never updated in place and never deleted; a correction inserts
  a new row with ``supersedes_id`` pointing at the record it replaces.
  The single exception is draft approval: a draft VERSION is immutable once
  APPROVED; editing after approval creates a new version.
* A saved draft snapshot is exactly what the creator wrote. Discovery
  evidence referenced by a draft is never rewritten underneath it.
* NULL means unavailable. An observed zero is stored as 0, never as NULL.
* Nothing in this module fabricates brands, affinity values, programmes, or
  outcomes. It stores what the creator recorded and what a live discovery
  returned.
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

#: Source-review verdicts. The product records the CREATOR's verification of
#: a commercial claim against an official source; it never asserts the claim.
VALID_REVIEW_STATUSES = {"SUPPORTED_BY_OFFICIAL_SOURCE", "CONTRADICTED", "UNVERIFIED"}

#: Outreach contact states and measurement semantics (zero vs missing).
VALID_CONTACT_STATUSES = {"CONTACTED", "RESPONDED", "PASSED", "DECLINED", "COLLABORATED"}
VALID_MEASUREMENT_STATUS = {"OBSERVED", "PARTIAL", "MISSING", "UNAVAILABLE", "FAILED"}

VALID_DRAFT_STATUSES = {"DRAFT", "APPROVED"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS filmsponsor_campaigns (
    campaign_id     TEXT PRIMARY KEY,
    request_id      TEXT NOT NULL UNIQUE,
    created_at      TEXT NOT NULL,
    film_title      TEXT NOT NULL,
    film_year       INTEGER,
    imdb_id         TEXT,
    themes          TEXT NOT NULL DEFAULT '[]',
    goals           TEXT NOT NULL DEFAULT '',
    provenance      TEXT NOT NULL DEFAULT '{}',
    guest_owner_id  TEXT
);

CREATE TABLE IF NOT EXISTS filmsponsor_discoveries (
    discovery_id    TEXT PRIMARY KEY,
    request_id      TEXT NOT NULL UNIQUE,
    campaign_id     TEXT NOT NULL REFERENCES filmsponsor_campaigns(campaign_id),
    created_at      TEXT NOT NULL,
    data_status     TEXT NOT NULL,
    report          TEXT NOT NULL DEFAULT '{}',
    supersedes_id   TEXT
);

CREATE TABLE IF NOT EXISTS filmsponsor_drafts (
    draft_id        TEXT PRIMARY KEY,
    request_id      TEXT NOT NULL UNIQUE,
    campaign_id     TEXT NOT NULL REFERENCES filmsponsor_campaigns(campaign_id),
    created_at      TEXT NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    brand_name      TEXT NOT NULL,
    pitch           TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'DRAFT',
    approved_at     TEXT,
    supersedes_id   TEXT
);

CREATE TABLE IF NOT EXISTS filmsponsor_source_reviews (
    review_id           TEXT PRIMARY KEY,
    request_id          TEXT NOT NULL UNIQUE,
    campaign_id         TEXT NOT NULL REFERENCES filmsponsor_campaigns(campaign_id),
    draft_id            TEXT NOT NULL REFERENCES filmsponsor_drafts(draft_id),
    created_at          TEXT NOT NULL,
    source_url          TEXT NOT NULL DEFAULT '',
    claim_checked       TEXT NOT NULL DEFAULT '',
    verification_status TEXT NOT NULL,
    notes               TEXT,
    supersedes_id       TEXT
);

CREATE TABLE IF NOT EXISTS filmsponsor_outreach (
    outreach_id         TEXT PRIMARY KEY,
    request_id          TEXT NOT NULL UNIQUE,
    campaign_id         TEXT NOT NULL REFERENCES filmsponsor_campaigns(campaign_id),
    draft_id            TEXT,
    created_at          TEXT NOT NULL,
    observed_on         TEXT,
    contact_status      TEXT NOT NULL,
    measurement_status  TEXT NOT NULL,
    metrics             TEXT NOT NULL DEFAULT '{}',
    outcome             TEXT,
    notes               TEXT,
    evidence_ref        TEXT,
    supersedes_id       TEXT
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _synchronized(method):
    """Serialise repository access through the instance lock (reentrant)."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            try:
                return method(self, *args, **kwargs)
            except sqlite3.Error:
                # A failed SQLite trigger/constraint must not leave a write
                # transaction open and lock other workers' session checks.
                self._conn.rollback()
                raise

    return wrapper


class DuplicateRequest(Exception):
    """Raised with the already-stored row when a request_id is replayed."""

    def __init__(self, existing: dict[str, Any]):
        self.existing = existing
        super().__init__("duplicate request_id")


class FilmSponsorRepository:
    """Append-only campaign store. Safe across process restarts."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute("PRAGMA secure_delete=ON")
            self._conn.executescript(_SCHEMA)
            columns = {row["name"] for row in self._conn.execute("PRAGMA table_info(filmsponsor_campaigns)")}
            if "guest_owner_id" not in columns:
                try:
                    self._conn.execute("ALTER TABLE filmsponsor_campaigns ADD COLUMN guest_owner_id TEXT")
                except sqlite3.OperationalError as exc:
                    # Another worker may have completed the idempotent migration
                    # after this connection inspected the older schema.
                    if "duplicate column name" not in str(exc).lower():
                        raise
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_filmsponsor_campaign_owner "
                "ON filmsponsor_campaigns(guest_owner_id, created_at)"
            )
            self._conn.executescript(
                """
                CREATE TRIGGER IF NOT EXISTS filmsponsor_guest_campaign_cap
                BEFORE INSERT ON filmsponsor_campaigns
                WHEN NEW.guest_owner_id IS NOT NULL AND (
                    (SELECT COUNT(*) FROM filmsponsor_campaigns WHERE guest_owner_id=NEW.guest_owner_id) >= 10 OR
                    (SELECT COUNT(*) FROM filmsponsor_campaigns WHERE guest_owner_id IS NOT NULL) >= 2000
                ) BEGIN SELECT RAISE(ABORT, 'guest campaign storage limit reached'); END;
                CREATE TRIGGER IF NOT EXISTS filmsponsor_guest_discovery_cap
                BEFORE INSERT ON filmsponsor_discoveries
                WHEN (SELECT guest_owner_id FROM filmsponsor_campaigns WHERE campaign_id=NEW.campaign_id) IS NOT NULL
                 AND ((SELECT COUNT(*) FROM filmsponsor_discoveries WHERE campaign_id=NEW.campaign_id) >= 10 OR
                      (SELECT COUNT(*) FROM filmsponsor_discoveries d JOIN filmsponsor_campaigns c USING(campaign_id) WHERE c.guest_owner_id IS NOT NULL) >= 1000)
                BEGIN SELECT RAISE(ABORT, 'guest discovery storage limit reached'); END;
                CREATE TRIGGER IF NOT EXISTS filmsponsor_guest_draft_cap
                BEFORE INSERT ON filmsponsor_drafts
                WHEN (SELECT guest_owner_id FROM filmsponsor_campaigns WHERE campaign_id=NEW.campaign_id) IS NOT NULL
                 AND ((SELECT COUNT(*) FROM filmsponsor_drafts WHERE campaign_id=NEW.campaign_id) >= 50 OR
                      (SELECT COUNT(*) FROM filmsponsor_drafts d JOIN filmsponsor_campaigns c USING(campaign_id) WHERE c.guest_owner_id IS NOT NULL) >= 5000)
                BEGIN SELECT RAISE(ABORT, 'guest draft storage limit reached'); END;
                CREATE TRIGGER IF NOT EXISTS filmsponsor_guest_review_cap
                BEFORE INSERT ON filmsponsor_source_reviews
                WHEN (SELECT guest_owner_id FROM filmsponsor_campaigns WHERE campaign_id=NEW.campaign_id) IS NOT NULL
                 AND ((SELECT COUNT(*) FROM filmsponsor_source_reviews WHERE campaign_id=NEW.campaign_id) >= 100 OR
                      (SELECT COUNT(*) FROM filmsponsor_source_reviews r JOIN filmsponsor_campaigns c USING(campaign_id) WHERE c.guest_owner_id IS NOT NULL) >= 5000)
                BEGIN SELECT RAISE(ABORT, 'guest review storage limit reached'); END;
                CREATE TRIGGER IF NOT EXISTS filmsponsor_guest_outreach_cap
                BEFORE INSERT ON filmsponsor_outreach
                WHEN (SELECT guest_owner_id FROM filmsponsor_campaigns WHERE campaign_id=NEW.campaign_id) IS NOT NULL
                 AND ((SELECT COUNT(*) FROM filmsponsor_outreach WHERE campaign_id=NEW.campaign_id) >= 100 OR
                      (SELECT COUNT(*) FROM filmsponsor_outreach o JOIN filmsponsor_campaigns c USING(campaign_id) WHERE c.guest_owner_id IS NOT NULL) >= 5000)
                BEGIN SELECT RAISE(ABORT, 'guest outreach storage limit reached'); END;
                """
            )
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- campaigns ---------------------------------------------------------

    @_synchronized
    def create_campaign(
        self,
        *,
        request_id: str,
        film_title: str,
        film_year: int | None = None,
        imdb_id: str | None = None,
        themes: list[str] | None = None,
        goals: str = "",
        provenance: dict[str, Any] | None = None,
        owner_id: str | None = None,
    ) -> dict[str, Any]:
        existing = self._conn.execute(
            "SELECT * FROM filmsponsor_campaigns WHERE request_id = ?", (request_id,)
        ).fetchone()
        if existing:
            # Never disclose another session's existing row on request-id collision.
            if owner_id is not None and existing["guest_owner_id"] != owner_id:
                raise ValueError("request_id collision")
            raise DuplicateRequest(self._row_to_campaign(existing))
        if owner_id is not None:
            owned_count = self._conn.execute(
                "SELECT COUNT(*) FROM filmsponsor_campaigns WHERE guest_owner_id=?", (owner_id,)
            ).fetchone()[0]
            total_guest = self._conn.execute(
                "SELECT COUNT(*) FROM filmsponsor_campaigns WHERE guest_owner_id IS NOT NULL"
            ).fetchone()[0]
            if owned_count >= 10 or total_guest >= 2000:
                raise OverflowError("Guest campaign storage limit reached.")
        campaign_id = str(uuid.uuid4())
        self._conn.execute(
            """INSERT INTO filmsponsor_campaigns
               (campaign_id, request_id, created_at, film_title, film_year,
                imdb_id, themes, goals, provenance, guest_owner_id)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                campaign_id,
                request_id,
                _now(),
                film_title,
                film_year,
                imdb_id,
                json.dumps([t for t in (themes or []) if t]),
                goals,
                json.dumps(provenance or {}),
                owner_id,
            ),
        )
        self._conn.commit()
        return self.get_campaign(campaign_id)  # type: ignore[return-value]

    @_synchronized
    def get_campaign(self, campaign_id: str, owner_id: str | None = None) -> dict[str, Any] | None:
        if owner_id is None:
            row = self._conn.execute(
                "SELECT * FROM filmsponsor_campaigns WHERE campaign_id = ?", (campaign_id,)
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM filmsponsor_campaigns WHERE campaign_id = ? AND guest_owner_id = ?",
                (campaign_id, owner_id),
            ).fetchone()
        return self._row_to_campaign(row) if row else None

    @_synchronized
    def list_campaigns(self, owner_id: str | None = None) -> list[dict[str, Any]]:
        if owner_id is None:
            rows = self._conn.execute(
                "SELECT * FROM filmsponsor_campaigns ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM filmsponsor_campaigns WHERE guest_owner_id=? ORDER BY created_at DESC",
                (owner_id,),
            ).fetchall()
        out = []
        for row in rows:
            campaign = self._row_to_campaign(row)
            campaign_id = campaign["campaign_id"]
            campaign["discovery_count"] = self._conn.execute(
                "SELECT COUNT(*) FROM filmsponsor_discoveries WHERE campaign_id=?",
                (campaign_id,),
            ).fetchone()[0]
            campaign["draft_count"] = self._conn.execute(
                "SELECT COUNT(*) FROM filmsponsor_drafts WHERE campaign_id=?",
                (campaign_id,),
            ).fetchone()[0]
            campaign["outreach_count"] = self._conn.execute(
                "SELECT COUNT(*) FROM filmsponsor_outreach WHERE campaign_id=?",
                (campaign_id,),
            ).fetchone()[0]
            out.append(campaign)
        return out

    # -- discoveries --------------------------------------------------------

    @_synchronized
    def save_discovery(
        self,
        *,
        request_id: str,
        campaign_id: str,
        data_status: str,
        report: dict[str, Any],
        supersedes_id: str | None = None,
        owner_id: str | None = None,
    ) -> dict[str, Any]:
        if self.get_campaign(campaign_id, owner_id) is None:
            raise KeyError(f"campaign {campaign_id} not found")
        existing = self._conn.execute(
            "SELECT discovery_id FROM filmsponsor_discoveries WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if existing:
            raise DuplicateRequest({"discovery_id": existing["discovery_id"]})
        if supersedes_id is not None:
            self._validate_supersedes_target(
                table="filmsponsor_discoveries",
                id_column="discovery_id",
                target_id=supersedes_id,
                campaign_id=campaign_id,
                record_kind="discovery",
            )
        report_json = json.dumps(report)
        if owner_id is not None and len(report_json.encode("utf-8")) > 131_072:
            raise ValueError("guest discovery report exceeds the 128 KiB limit")
        discovery_id = str(uuid.uuid4())
        self._conn.execute(
            """INSERT INTO filmsponsor_discoveries
               (discovery_id, request_id, campaign_id, created_at, data_status,
                report, supersedes_id) VALUES (?,?,?,?,?,?,?)""",
            (discovery_id, request_id, campaign_id, _now(), data_status,
             report_json, supersedes_id),
        )
        self._conn.commit()
        return self.get_discovery(discovery_id)  # type: ignore[return-value]

    @_synchronized
    def get_discovery(self, discovery_id: str, owner_id: str | None = None) -> dict[str, Any] | None:
        if owner_id is None:
            row = self._conn.execute(
                "SELECT * FROM filmsponsor_discoveries WHERE discovery_id = ?", (discovery_id,)
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT d.* FROM filmsponsor_discoveries d JOIN filmsponsor_campaigns c USING(campaign_id) "
                "WHERE d.discovery_id=? AND c.guest_owner_id=?", (discovery_id, owner_id)
            ).fetchone()
        return self._row_to_discovery(row) if row else None

    @_synchronized
    def list_discoveries(self, campaign_id: str, owner_id: str | None = None) -> list[dict[str, Any]]:
        if self.get_campaign(campaign_id, owner_id) is None:
            return []
        rows = self._conn.execute(
            "SELECT discovery_id FROM filmsponsor_discoveries WHERE campaign_id = ? ORDER BY created_at",
            (campaign_id,),
        ).fetchall()
        return [self._row_to_discovery(self._one("filmsponsor_discoveries", "discovery_id", r["discovery_id"])) for r in rows]

    # -- drafts -------------------------------------------------------------

    @_synchronized
    def save_draft(
        self,
        *,
        request_id: str,
        campaign_id: str,
        brand_name: str,
        pitch: str = "",
        supersedes_id: str | None = None,
        owner_id: str | None = None,
    ) -> dict[str, Any]:
        if self.get_campaign(campaign_id, owner_id) is None:
            raise KeyError(f"campaign {campaign_id} not found")
        existing = self._conn.execute(
            "SELECT draft_id FROM filmsponsor_drafts WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if existing:
            raise DuplicateRequest({"draft_id": existing["draft_id"]})
        version = 1
        if supersedes_id is not None:
            target = self._validate_supersedes_target(
                table="filmsponsor_drafts",
                id_column="draft_id",
                target_id=supersedes_id,
                campaign_id=campaign_id,
                record_kind="draft",
            )
            version = int(target["version"]) + 1
        draft_id = str(uuid.uuid4())
        self._conn.execute(
            """INSERT INTO filmsponsor_drafts
               (draft_id, request_id, campaign_id, created_at, version,
                brand_name, pitch, status, approved_at, supersedes_id)
               VALUES (?,?,?,?,?,?,?,'DRAFT',NULL,?)""",
            (draft_id, request_id, campaign_id, _now(), version,
             brand_name, pitch, supersedes_id),
        )
        self._conn.commit()
        return self.get_draft(draft_id)  # type: ignore[return-value]

    @_synchronized
    def get_draft(self, draft_id: str, owner_id: str | None = None) -> dict[str, Any] | None:
        if owner_id is None:
            row = self._conn.execute(
                "SELECT * FROM filmsponsor_drafts WHERE draft_id = ?", (draft_id,)
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT d.* FROM filmsponsor_drafts d JOIN filmsponsor_campaigns c USING(campaign_id) "
                "WHERE d.draft_id=? AND c.guest_owner_id=?", (draft_id, owner_id)
            ).fetchone()
        return self._row_to_draft(row) if row else None

    @_synchronized
    def list_drafts(self, campaign_id: str, owner_id: str | None = None) -> list[dict[str, Any]]:
        if self.get_campaign(campaign_id, owner_id) is None:
            return []
        rows = self._conn.execute(
            "SELECT * FROM filmsponsor_drafts WHERE campaign_id = ? "
            "ORDER BY created_at, version",
            (campaign_id,),
        ).fetchall()
        return [self._row_to_draft(r) for r in rows]

    @_synchronized
    def approve_draft(self, draft_id: str, owner_id: str | None = None) -> dict[str, Any]:
        """Mark a draft version APPROVED. Requires a completed source review.

        Approval is recorded on the immutable draft version. Editing after
        approval creates a new (DRAFT) version via ``save_draft``.
        """
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            if owner_id is not None:
                active = self._conn.execute(
                    "SELECT 1 FROM filmsponsor_guest_sessions WHERE session_id=? AND revoked_at IS NULL AND julianday(expires_at)>julianday('now')",
                    (owner_id,),
                ).fetchone()
                if active is None:
                    raise KeyError("guest session is no longer active")
            draft = self.get_draft(draft_id, owner_id)
            if draft is None:
                raise KeyError(f"draft {draft_id} not found")
            if draft["status"] == "APPROVED":
                self._conn.commit()
                return draft
            review = self._current_review_for(draft_id)
            if review is None:
                raise ValueError(
                    "a source review must be recorded before approval "
                    "(official-source review is required)"
                )
            self._conn.execute(
                "UPDATE filmsponsor_drafts SET status='APPROVED', approved_at=? WHERE draft_id=?",
                (_now(), draft_id),
            )
            self._conn.commit()
            return self.get_draft(draft_id, owner_id)  # type: ignore[return-value]
        except Exception:
            self._conn.rollback()
            raise

    # -- source reviews ------------------------------------------------------

    @_synchronized
    def add_source_review(
        self,
        *,
        request_id: str,
        campaign_id: str,
        draft_id: str,
        source_url: str = "",
        claim_checked: str = "",
        verification_status: str,
        notes: str | None = None,
        supersedes_id: str | None = None,
        owner_id: str | None = None,
    ) -> dict[str, Any]:
        if verification_status not in VALID_REVIEW_STATUSES:
            raise ValueError(
                f"verification_status must be one of {sorted(VALID_REVIEW_STATUSES)}"
            )
        if self.get_campaign(campaign_id, owner_id) is None:
            raise KeyError(f"campaign {campaign_id} not found")
        draft = self.get_draft(draft_id, owner_id)
        if draft is None or draft["campaign_id"] != campaign_id:
            raise KeyError(f"draft {draft_id} not found in campaign {campaign_id}")
        existing = self._conn.execute(
            "SELECT review_id FROM filmsponsor_source_reviews WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if existing:
            raise DuplicateRequest({"review_id": existing["review_id"]})
        if supersedes_id is not None:
            self._validate_supersedes_target(
                table="filmsponsor_source_reviews",
                id_column="review_id",
                target_id=supersedes_id,
                campaign_id=campaign_id,
                record_kind="source review",
            )
        review_id = str(uuid.uuid4())
        self._conn.execute(
            """INSERT INTO filmsponsor_source_reviews
               (review_id, request_id, campaign_id, draft_id, created_at,
                source_url, claim_checked, verification_status, notes, supersedes_id)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (review_id, request_id, campaign_id, draft_id, _now(),
             source_url, claim_checked, verification_status, notes, supersedes_id),
        )
        self._conn.commit()
        return self.get_source_review(review_id)  # type: ignore[return-value]

    @_synchronized
    def get_source_review(self, review_id: str, owner_id: str | None = None) -> dict[str, Any] | None:
        if owner_id is None:
            row = self._one("filmsponsor_source_reviews", "review_id", review_id)
        else:
            row = self._conn.execute(
                "SELECT r.* FROM filmsponsor_source_reviews r JOIN filmsponsor_campaigns c USING(campaign_id) "
                "WHERE r.review_id=? AND c.guest_owner_id=?", (review_id, owner_id)
            ).fetchone()
        return self._row_to_source_review(row) if row else None

    @_synchronized
    def list_source_reviews(self, campaign_id: str, owner_id: str | None = None) -> list[dict[str, Any]]:
        if self.get_campaign(campaign_id, owner_id) is None:
            return []
        rows = self._conn.execute(
            "SELECT * FROM filmsponsor_source_reviews WHERE campaign_id = ? "
            "ORDER BY created_at",
            (campaign_id,),
        ).fetchall()
        return [self._row_to_source_review(r) for r in rows]

    def _current_review_for(self, draft_id: str) -> dict[str, Any] | None:
        """Newest non-superseded review for this draft (supersede-corrected)."""
        row = self._conn.execute(
            """SELECT r.review_id FROM filmsponsor_source_reviews AS r
               WHERE r.draft_id = ?
                 AND NOT EXISTS (
                     SELECT 1 FROM filmsponsor_source_reviews AS correction
                     WHERE correction.supersedes_id = r.review_id
                 )
               ORDER BY r.created_at DESC, r.review_id DESC LIMIT 1""",
            (draft_id,),
        ).fetchone()
        return self.get_source_review(row["review_id"]) if row else None

    # -- outreach ------------------------------------------------------------

    @_synchronized
    def add_outreach(
        self,
        *,
        request_id: str,
        campaign_id: str,
        contact_status: str,
        measurement_status: str,
        draft_id: str | None = None,
        observed_on: str | None = None,
        metrics: dict[str, Any] | None = None,
        outcome: str | None = None,
        notes: str | None = None,
        evidence_ref: str | None = None,
        supersedes_id: str | None = None,
        owner_id: str | None = None,
    ) -> dict[str, Any]:
        if contact_status not in VALID_CONTACT_STATUSES:
            raise ValueError(
                f"contact_status must be one of {sorted(VALID_CONTACT_STATUSES)}"
            )
        if measurement_status not in VALID_MEASUREMENT_STATUS:
            raise ValueError(
                f"measurement_status must be one of {sorted(VALID_MEASUREMENT_STATUS)}"
            )
        if self.get_campaign(campaign_id, owner_id) is None:
            raise KeyError(f"campaign {campaign_id} not found")
        if draft_id is not None:
            draft = self.get_draft(draft_id, owner_id)
            if draft is None or draft["campaign_id"] != campaign_id:
                raise KeyError(f"draft {draft_id} not found in campaign {campaign_id}")
        existing = self._conn.execute(
            "SELECT outreach_id FROM filmsponsor_outreach WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if existing:
            raise DuplicateRequest({"outreach_id": existing["outreach_id"]})
        if supersedes_id is not None:
            self._validate_supersedes_target(
                table="filmsponsor_outreach",
                id_column="outreach_id",
                target_id=supersedes_id,
                campaign_id=campaign_id,
                record_kind="outreach record",
            )
        outreach_id = str(uuid.uuid4())
        self._conn.execute(
            """INSERT INTO filmsponsor_outreach
               (outreach_id, request_id, campaign_id, draft_id, created_at,
                observed_on, contact_status, measurement_status, metrics,
                outcome, notes, evidence_ref, supersedes_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (outreach_id, request_id, campaign_id, draft_id, _now(),
             observed_on, contact_status, measurement_status,
             json.dumps(metrics or {}), outcome, notes, evidence_ref, supersedes_id),
        )
        self._conn.commit()
        return self.get_outreach(outreach_id)  # type: ignore[return-value]

    @_synchronized
    def get_outreach(self, outreach_id: str, owner_id: str | None = None) -> dict[str, Any] | None:
        if owner_id is None:
            row = self._one("filmsponsor_outreach", "outreach_id", outreach_id)
        else:
            row = self._conn.execute(
                "SELECT o.* FROM filmsponsor_outreach o JOIN filmsponsor_campaigns c USING(campaign_id) "
                "WHERE o.outreach_id=? AND c.guest_owner_id=?", (outreach_id, owner_id)
            ).fetchone()
        return self._row_to_outreach(row) if row else None

    @_synchronized
    def list_outreach(self, campaign_id: str, owner_id: str | None = None) -> list[dict[str, Any]]:
        if self.get_campaign(campaign_id, owner_id) is None:
            return []
        rows = self._conn.execute(
            "SELECT outreach_id FROM filmsponsor_outreach WHERE campaign_id = ? "
            "ORDER BY created_at",
            (campaign_id,),
        ).fetchall()
        return [self._row_to_outreach(self._one("filmsponsor_outreach", "outreach_id", r["outreach_id"])) for r in rows]

    # -- export ------------------------------------------------------------

    @_synchronized
    def export_package(self, campaign_id: str, owner_id: str | None = None) -> dict[str, Any]:
        """Export approved content only; unapproved drafts are excluded with reasons.

        The export records source reviews and outreach OUTCOMES as the creator
        recorded them. It contains no invented brands, affinity values,
        programmes, or outcomes.
        """
        campaign = self.get_campaign(campaign_id, owner_id)
        if campaign is None:
            raise KeyError(f"campaign {campaign_id} not found")
        drafts = [d for d in self.list_drafts(campaign_id, owner_id) if d["supersedes_id"] is None]
        approved = [d for d in drafts if d["status"] == "APPROVED"]
        excluded = [
            {
                "draft_id": d["draft_id"],
                "brand_name": d["brand_name"],
                "reason": "not_approved",
            }
            for d in drafts
            if d["status"] != "APPROVED"
        ]
        reviews = self.list_source_reviews(campaign_id, owner_id)
        outreach = [
            o for o in self.list_outreach(campaign_id, owner_id) if o["supersedes_id"] is None
        ]
        return {
            "campaign": campaign,
            "export_ready": bool(approved),
            "approved_drafts": [
                {
                    **d,
                    "source_reviews": [
                        r for r in reviews if r["draft_id"] == d["draft_id"] and r["supersedes_id"] is None
                    ],
                }
                for d in approved
            ],
            "excluded_drafts": excluded,
            "outreach_records": outreach,
            "interpretation_limits": [
                "Cultural affinity is not sponsorship likelihood, eligibility, budget, availability, or ROI.",
                "Source reviews record the creator's own check of an official source; this export does not verify the claim itself.",
                "Outreach outcomes are what the creator recorded; unrecorded outcomes are absent, not zero.",
            ],
        }

    # -- helpers ---------------------------------------------------------------

    def _one(self, table: str, id_column: str, value: str) -> sqlite3.Row | None:
        return self._conn.execute(
            f"SELECT * FROM {table} WHERE {id_column} = ?", (value,)
        ).fetchone()

    def _validate_supersedes_target(
        self,
        *,
        table: str,
        id_column: str,
        target_id: str,
        campaign_id: str,
        record_kind: str,
    ) -> sqlite3.Row:
        target = self._conn.execute(
            f"SELECT * FROM {table} WHERE {id_column} = ?", (target_id,)
        ).fetchone()
        if target is None:
            raise ValueError(f"supersedes_id does not identify an existing {record_kind}")
        if target["campaign_id"] != campaign_id:
            raise ValueError(f"supersedes_id must refer to a {record_kind} in this campaign")
        already_superseded = self._conn.execute(
            f"SELECT 1 FROM {table} WHERE supersedes_id = ? LIMIT 1", (target_id,)
        ).fetchone()
        if already_superseded:
            raise ValueError(f"the {record_kind} has already been superseded")
        return target

    @staticmethod
    def _row_to_campaign(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "campaign_id": row["campaign_id"],
            "request_id": row["request_id"],
            "created_at": row["created_at"],
            "film_title": row["film_title"],
            "film_year": row["film_year"],
            "imdb_id": row["imdb_id"],
            "themes": json.loads(row["themes"]),
            "goals": row["goals"],
            "provenance": json.loads(row["provenance"]),
        }

    @staticmethod
    def _row_to_discovery(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "discovery_id": row["discovery_id"],
            "request_id": row["request_id"],
            "campaign_id": row["campaign_id"],
            "created_at": row["created_at"],
            "data_status": row["data_status"],
            "report": json.loads(row["report"]),
            "supersedes_id": row["supersedes_id"],
        }

    @staticmethod
    def _row_to_draft(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "draft_id": row["draft_id"],
            "request_id": row["request_id"],
            "campaign_id": row["campaign_id"],
            "created_at": row["created_at"],
            "version": row["version"],
            "brand_name": row["brand_name"],
            "pitch": row["pitch"],
            "status": row["status"],
            "approved_at": row["approved_at"],
            "supersedes_id": row["supersedes_id"],
        }

    @staticmethod
    def _row_to_source_review(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "review_id": row["review_id"],
            "request_id": row["request_id"],
            "campaign_id": row["campaign_id"],
            "draft_id": row["draft_id"],
            "created_at": row["created_at"],
            "source_url": row["source_url"],
            "claim_checked": row["claim_checked"],
            "verification_status": row["verification_status"],
            "notes": row["notes"],
            "supersedes_id": row["supersedes_id"],
        }

    @staticmethod
    def _row_to_outreach(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "outreach_id": row["outreach_id"],
            "request_id": row["request_id"],
            "campaign_id": row["campaign_id"],
            "draft_id": row["draft_id"],
            "created_at": row["created_at"],
            "observed_on": row["observed_on"],
            "contact_status": row["contact_status"],
            "measurement_status": row["measurement_status"],
            "metrics": json.loads(row["metrics"]),
            "outcome": row["outcome"],
            "notes": row["notes"],
            "evidence_ref": row["evidence_ref"],
            "supersedes_id": row["supersedes_id"],
        }
