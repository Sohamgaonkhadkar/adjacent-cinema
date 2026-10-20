"""Persistent, bounded guest sessions for the opt-in FilmSponsor judge demo.

Only a SHA-256 digest of each bearer cookie is persisted. Ownership is keyed by
an internal server-generated session UUID stored on each campaign. SQLite is
shared with FilmSponsor and must live on a durable, single-host filesystem.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

SESSION_COOKIE = "adjacent_filmsponsor_guest"
CSRF_COOKIE = "adjacent_filmsponsor_csrf"
SESSION_TTL = timedelta(hours=8)
MAX_ACTIVE_SESSIONS = 500
MAX_REQUESTS_PER_MINUTE = 120


def _now() -> datetime:
    return datetime.now(UTC)


def _stamp(value: datetime) -> str:
    return value.isoformat()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class GuestSession:
    session_id: str
    csrf_token: str
    expires_at: str


class GuestSessionError(Exception):
    """Base class for expected guest-session denials."""


class GuestSessionCapacity(GuestSessionError):
    pass


class GuestSessionRateLimited(GuestSessionError):
    pass


class GuestSessionStore:
    """Session lifecycle store using SQLite transactions across workers.

    The DB must be a persistent local volume shared by backend workers on one
    host. SQLite WAL is not supported on arbitrary network filesystems or
    independently mounted replicas; use one backend host and an edge quota.
    """

    def __init__(self, db_path: str | Path, *, clock=None) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), timeout=5, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._clock = clock or _now
        with self._lock:
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute("PRAGMA secure_delete=ON")
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS filmsponsor_guest_sessions (
                    session_id TEXT PRIMARY KEY,
                    token_hash TEXT NOT NULL UNIQUE,
                    csrf_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT,
                    rate_window_at TEXT NOT NULL,
                    rate_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_guest_session_expiry
                    ON filmsponsor_guest_sessions(expires_at, revoked_at);
                """
            )
            self._conn.executescript(
                """
                CREATE TRIGGER IF NOT EXISTS filmsponsor_guest_campaign_session_valid
                BEFORE INSERT ON filmsponsor_campaigns
                WHEN NEW.guest_owner_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM filmsponsor_guest_sessions s
                    WHERE s.session_id=NEW.guest_owner_id AND s.revoked_at IS NULL
                      AND julianday(s.expires_at) > julianday('now')
                ) BEGIN SELECT RAISE(ABORT, 'guest session is no longer active'); END;
                CREATE TRIGGER IF NOT EXISTS filmsponsor_guest_discovery_session_valid
                BEFORE INSERT ON filmsponsor_discoveries
                WHEN (SELECT guest_owner_id FROM filmsponsor_campaigns WHERE campaign_id=NEW.campaign_id) IS NOT NULL
                 AND NOT EXISTS (
                    SELECT 1 FROM filmsponsor_campaigns c JOIN filmsponsor_guest_sessions s
                      ON s.session_id=c.guest_owner_id
                    WHERE c.campaign_id=NEW.campaign_id AND s.revoked_at IS NULL
                      AND julianday(s.expires_at) > julianday('now')
                 ) BEGIN SELECT RAISE(ABORT, 'guest session is no longer active'); END;
                CREATE TRIGGER IF NOT EXISTS filmsponsor_guest_draft_session_valid
                BEFORE INSERT ON filmsponsor_drafts
                WHEN (SELECT guest_owner_id FROM filmsponsor_campaigns WHERE campaign_id=NEW.campaign_id) IS NOT NULL
                 AND NOT EXISTS (
                    SELECT 1 FROM filmsponsor_campaigns c JOIN filmsponsor_guest_sessions s
                      ON s.session_id=c.guest_owner_id
                    WHERE c.campaign_id=NEW.campaign_id AND s.revoked_at IS NULL
                      AND julianday(s.expires_at) > julianday('now')
                 ) BEGIN SELECT RAISE(ABORT, 'guest session is no longer active'); END;
                CREATE TRIGGER IF NOT EXISTS filmsponsor_guest_review_session_valid
                BEFORE INSERT ON filmsponsor_source_reviews
                WHEN (SELECT guest_owner_id FROM filmsponsor_campaigns WHERE campaign_id=NEW.campaign_id) IS NOT NULL
                 AND NOT EXISTS (
                    SELECT 1 FROM filmsponsor_campaigns c JOIN filmsponsor_guest_sessions s
                      ON s.session_id=c.guest_owner_id
                    WHERE c.campaign_id=NEW.campaign_id AND s.revoked_at IS NULL
                      AND julianday(s.expires_at) > julianday('now')
                 ) BEGIN SELECT RAISE(ABORT, 'guest session is no longer active'); END;
                CREATE TRIGGER IF NOT EXISTS filmsponsor_guest_outreach_session_valid
                BEFORE INSERT ON filmsponsor_outreach
                WHEN (SELECT guest_owner_id FROM filmsponsor_campaigns WHERE campaign_id=NEW.campaign_id) IS NOT NULL
                 AND NOT EXISTS (
                    SELECT 1 FROM filmsponsor_campaigns c JOIN filmsponsor_guest_sessions s
                      ON s.session_id=c.guest_owner_id
                    WHERE c.campaign_id=NEW.campaign_id AND s.revoked_at IS NULL
                      AND julianday(s.expires_at) > julianday('now')
                 ) BEGIN SELECT RAISE(ABORT, 'guest session is no longer active'); END;
                """
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def issue_or_rotate(
        self, presented_token: str | None, presented_csrf: str | None = None
    ) -> tuple[str, GuestSession, bool]:
        """Issue a session or restore its CSRF synchronizer token.

        A valid bearer plus matching CSRF cookie reuses the same workspace
        across tabs/reloads. Missing or invalid credentials create a new
        isolated session here; they never authorize campaign requests.
        """
        now = self._clock()
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        token_hash = _digest(presented_token) if presented_token else None
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                self._cleanup_locked(now)
                if token_hash:
                    row = self._conn.execute(
                        "SELECT * FROM filmsponsor_guest_sessions WHERE token_hash=?",
                        (token_hash,),
                    ).fetchone()
                    if row and not row["revoked_at"] and row["expires_at"] > _stamp(now):
                        if presented_csrf and hmac.compare_digest(row["csrf_hash"], _digest(presented_csrf)):
                            csrf = presented_csrf
                        self._conn.execute(
                            "UPDATE filmsponsor_guest_sessions SET csrf_hash=?, last_seen_at=? WHERE session_id=?",
                            (_digest(csrf), _stamp(now), row["session_id"]),
                        )
                        self._conn.commit()
                        return presented_token or token, GuestSession(
                            row["session_id"], csrf, row["expires_at"]
                        ), False
                count = self._conn.execute(
                    "SELECT COUNT(*) FROM filmsponsor_guest_sessions WHERE revoked_at IS NULL AND expires_at > ?",
                    (_stamp(now),),
                ).fetchone()[0]
                if count >= MAX_ACTIVE_SESSIONS:
                    raise GuestSessionCapacity("Guest demo is at capacity; please try later.")
                session_id = str(uuid.uuid4())
                expires = now + SESSION_TTL
                self._conn.execute(
                    """INSERT INTO filmsponsor_guest_sessions
                       (session_id, token_hash, csrf_hash, created_at, last_seen_at,
                        expires_at, rate_window_at, rate_count)
                       VALUES (?,?,?,?,?,?,?,0)""",
                    (session_id, _digest(token), _digest(csrf), _stamp(now), _stamp(now),
                     _stamp(expires), _stamp(now)),
                )
                self._conn.commit()
                return token, GuestSession(session_id, csrf, _stamp(expires)), True
            except Exception:
                self._conn.rollback()
                raise

    def authenticate(self, token: str | None, csrf_token: str | None, *, write: bool) -> GuestSession:
        if not token or len(token) > 128:
            raise GuestSessionError("Guest session is missing, expired, or revoked. Start a new session.")
        now = self._clock()
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                self._cleanup_locked(now)
                row = self._conn.execute(
                    "SELECT * FROM filmsponsor_guest_sessions WHERE token_hash=?",
                    (_digest(token),),
                ).fetchone()
                if row is None or row["revoked_at"] or row["expires_at"] <= _stamp(now):
                    # Expiry cleanup must survive the authorization denial so
                    # expired session data cannot remain indefinitely.
                    self._conn.commit()
                    raise GuestSessionError(
                        "Guest session is missing, expired, or revoked. Start a new session."
                    )
                if write and (not csrf_token or not hmac.compare_digest(row["csrf_hash"], _digest(csrf_token))):
                    raise GuestSessionError("Guest-demo CSRF validation failed.")
                window = datetime.fromisoformat(row["rate_window_at"])
                count = int(row["rate_count"])
                if now - window >= timedelta(minutes=1):
                    window, count = now, 0
                if count >= MAX_REQUESTS_PER_MINUTE:
                    raise GuestSessionRateLimited("Guest session request limit reached; retry shortly.")
                self._conn.execute(
                    "UPDATE filmsponsor_guest_sessions SET last_seen_at=?, rate_window_at=?, rate_count=? WHERE session_id=?",
                    (_stamp(now), _stamp(window), count + 1, row["session_id"]),
                )
                self._conn.commit()
                return GuestSession(row["session_id"], "", row["expires_at"])
            except Exception:
                self._conn.rollback()
                raise

    def is_active(self, session_id: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM filmsponsor_guest_sessions WHERE session_id=? AND revoked_at IS NULL AND julianday(expires_at)>julianday('now')",
                (session_id,),
            ).fetchone()
            return row is not None

    def revoke(self, session_id: str) -> None:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                self._delete_campaigns_locked(session_id)
                # Removing the row is revocation: its token digest can no longer
                # authenticate, and it avoids accumulating revoked credentials.
                self._conn.execute(
                    "DELETE FROM filmsponsor_guest_sessions WHERE session_id=?",
                    (session_id,),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def cleanup(self) -> int:
        now = self._clock()
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                count = self._cleanup_locked(now)
                self._conn.commit()
                return count
            except Exception:
                self._conn.rollback()
                raise

    def _cleanup_locked(self, now: datetime) -> int:
        expired = self._conn.execute(
            "SELECT session_id FROM filmsponsor_guest_sessions WHERE expires_at<=? OR (revoked_at IS NOT NULL AND revoked_at<?)",
            (_stamp(now), _stamp(now - timedelta(days=1))),
        ).fetchall()
        for row in expired:
            self._delete_campaigns_locked(row["session_id"])
        if expired:
            self._conn.executemany(
                "DELETE FROM filmsponsor_guest_sessions WHERE session_id=?",
                [(row["session_id"],) for row in expired],
            )
        return len(expired)

    def _delete_campaigns_locked(self, session_id: str) -> None:
        campaign_ids = [r[0] for r in self._conn.execute(
            "SELECT campaign_id FROM filmsponsor_campaigns WHERE guest_owner_id=?", (session_id,)
        ).fetchall()]
        for campaign_id in campaign_ids:
            self._conn.execute("DELETE FROM filmsponsor_outreach WHERE campaign_id=?", (campaign_id,))
            self._conn.execute("DELETE FROM filmsponsor_source_reviews WHERE campaign_id=?", (campaign_id,))
            self._conn.execute("DELETE FROM filmsponsor_drafts WHERE campaign_id=?", (campaign_id,))
            self._conn.execute("DELETE FROM filmsponsor_discoveries WHERE campaign_id=?", (campaign_id,))
            self._conn.execute("DELETE FROM filmsponsor_campaigns WHERE campaign_id=?", (campaign_id,))


def hash_request_id(session_id: str, request_id: str) -> str:
    """Namespace global legacy UNIQUE request ids without exposing session ids."""
    return "guest-" + hashlib.sha256(f"{session_id}:{request_id}".encode()).hexdigest()


def allowed_origins() -> frozenset[str]:
    """Explicit frontend origins; wildcard and URL paths are never accepted."""
    import os
    from urllib.parse import urlsplit

    raw = os.getenv("ADJACENT_FILMSPONSOR_GUEST_ORIGINS", "")
    origins: set[str] = set()
    for item in raw.split(","):
        item = item.strip().rstrip("/")
        if not item or item == "*":
            continue
        parsed = urlsplit(item)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
            continue
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            continue
        origins.add(f"{parsed.scheme}://{parsed.netloc.lower()}")
    return frozenset(origins)


def guest_demo_enabled() -> bool:
    """Guest mode is strictly subordinate to the existing public-demo guard."""
    import os

    from .. import public_demo

    flag = (os.getenv("ADJACENT_FILMSPONSOR_GUEST_DEMO") or "").strip().lower()
    if flag not in {"1", "true", "yes", "on"} or not public_demo.public_demo_enabled():
        return False
    origins = allowed_origins()
    if not origins:
        return False
    secure = (os.getenv("ADJACENT_FILMSPONSOR_GUEST_COOKIE_SECURE") or "1").strip().lower()
    secure_cookie = secure not in {"0", "false", "no", "off"}
    # Insecure cookies are accepted only for explicitly configured localhost
    # development origins; production origins require Secure.
    return secure_cookie or all(
        o.startswith("http://localhost")
        or o.startswith("http://127.0.0.1")
        or o.startswith("http://[::1]")
        for o in origins
    )


def secure_cookie_enabled() -> bool:
    import os
    return (os.getenv("ADJACENT_FILMSPONSOR_GUEST_COOKIE_SECURE") or "1").strip().lower() not in {"0", "false", "no", "off"}
