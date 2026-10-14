"""YouTube OAuth authorization + token storage (M13.10).

Design posture (documented in docs/M13_10_YOUTUBE_ANALYTICS_INTEGRATION.md):

* Adjacent has NO application-level user model — it is a local single-user
  tool. This integration is therefore EXPLICITLY single-connection: one
  Google account may be connected to the workspace at a time, and the token
  store keeps exactly one credential row. It must not be deployed as a public
  multi-user service without adding an ownership boundary first.
* Least privilege: only ``youtube.readonly`` + ``yt-analytics.readonly``.
  Per the official Analytics API reference (accessed 2026-10-11),
  ``reports.query`` now REQUIRES ``youtube.readonly`` in addition to the
  analytics scope. No write scopes, no monetary scopes.
* Tokens live in a SQLite file that is gitignored and NEVER appears in API
  responses, logs, SSE events, or traces. ``TokenStore`` has no repr that
  leaks values; callers receive plain dicts and must not serialise them.
* OAuth state is persisted with an expiry and consumed exactly once (CSRF
  protection that survives a server restart mid-flow).
* Developer Policies obligations implemented here: on disconnect/revocation
  the stored credentials are deleted immediately (data deletion obligations
  for stored analytics data are handled at the API layer).
"""

from __future__ import annotations

import os
import secrets
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

#: Least-privilege scopes. Both are required for youtubeAnalytics.reports.query
#: (official reference note, accessed 2026-10-11). Never add write/monetary
#: scopes without a documented need.
SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
)

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"

#: Developer Policies §III.E.4.b: analytics data may be kept only while
#: authorization is re-verified at least every 30 days.
REAUTHORIZATION_DAYS = 30

#: OAuth states are short-lived; ten minutes covers a slow consent screen.
STATE_TTL = timedelta(minutes=10)


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class YouTubeSettings:
    """OAuth client configuration, from the environment (never hardcoded).

    The project owner supplies:
      YOUTUBE_CLIENT_ID      OAuth client id (Google Cloud Console, Web app)
      YOUTUBE_CLIENT_SECRET  OAuth client secret — never committed
      YOUTUBE_REDIRECT_URI   must EXACTLY match a console-registered redirect
                             (default: http://localhost:3000/api/youtube/callback,
                             i.e. through the frontend proxy, keeping the whole
                             consent flow on the browser-facing origin)
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
    ) -> None:
        self.client_id = (client_id or "").strip() or None
        self.client_secret = (client_secret or "").strip() or None
        self.redirect_uri = (
            redirect_uri or os.getenv("YOUTUBE_REDIRECT_URI")
            or "http://localhost:3000/api/youtube/callback"
        ).strip()

    @classmethod
    def from_env(cls) -> YouTubeSettings:
        return cls(
            client_id=os.getenv("YOUTUBE_CLIENT_ID"),
            client_secret=os.getenv("YOUTUBE_CLIENT_SECRET"),
            redirect_uri=os.getenv("YOUTUBE_REDIRECT_URI"),
        )

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def redacted(self) -> dict[str, Any]:
        """Diagnostic-safe view: NEVER contains the secret."""
        return {
            "client_id_present": bool(self.client_id),
            "client_secret_present": bool(self.client_secret),
            "redirect_uri": self.redirect_uri,
            "scopes": list(SCOPES),
        }


class InvalidStateError(Exception):
    """Unknown, expired, or already-used OAuth state (possible CSRF)."""


class TokenStore:
    """Single-connection credential + OAuth state storage (SQLite).

    One credential row maximum (single-user posture). Schema is created
    idempotently on open. Access is serialised through a reentrant lock
    because FastAPI may serve requests from different threads.
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS youtube_tokens (
        id             INTEGER PRIMARY KEY CHECK (id = 1),
        access_token   TEXT NOT NULL,
        refresh_token  TEXT,
        scope          TEXT NOT NULL DEFAULT '',
        token_type     TEXT NOT NULL DEFAULT 'Bearer',
        expires_at     TEXT,
        channel_id     TEXT,
        channel_title  TEXT,
        connected_at   TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS oauth_states (
        state       TEXT PRIMARY KEY,
        created_at  TEXT NOT NULL,
        expires_at  TEXT NOT NULL,
        used        INTEGER NOT NULL DEFAULT 0
    );
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(self._SCHEMA)
            self._conn.commit()

    def __repr__(self) -> str:  # never leak values, even accidentally
        return f"<TokenStore {self.db_path.name}>"

    def close(self) -> None:
        self._conn.close()

    # -- OAuth state (CSRF) -------------------------------------------------
    def create_state(self, ttl: timedelta = STATE_TTL) -> str:
        state = secrets.token_urlsafe(32)
        now = _now()
        with self._lock:
            self._conn.execute(
                "INSERT INTO oauth_states (state, created_at, expires_at) VALUES (?,?,?)",
                (state, _iso(now), _iso(now + ttl)),
            )
            self._conn.commit()
        return state

    def validate_and_consume_state(self, state: str | None) -> bool:
        """Return True exactly once per issued, unexpired state."""
        if not state:
            return False
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM oauth_states WHERE state = ?", (state,)
            ).fetchone()
            if row is None or row["used"]:
                return False
            if datetime.fromisoformat(row["expires_at"]) < _now():
                return False
            self._conn.execute(
                "UPDATE oauth_states SET used = 1 WHERE state = ?", (state,)
            )
            self._conn.commit()
            return True

    # -- credentials ---------------------------------------------------------
    def save_tokens(
        self,
        *,
        access_token: str,
        refresh_token: str | None,
        scope: str,
        token_type: str = "Bearer",
        expires_in: int | None = None,
        channel_id: str | None = None,
        channel_title: str | None = None,
    ) -> None:
        now = _now()
        expires_at = _iso(now + timedelta(seconds=expires_in)) if expires_in else None
        with self._lock:
            self._conn.execute(
                """INSERT INTO youtube_tokens
                   (id, access_token, refresh_token, scope, token_type,
                    expires_at, channel_id, channel_title, connected_at)
                   VALUES (1,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     access_token=excluded.access_token,
                     refresh_token=excluded.refresh_token,
                     scope=excluded.scope,
                     token_type=excluded.token_type,
                     expires_at=excluded.expires_at,
                     channel_id=COALESCE(excluded.channel_id, youtube_tokens.channel_id),
                     channel_title=COALESCE(excluded.channel_title, youtube_tokens.channel_title)
                """,
                (
                    access_token, refresh_token, scope, token_type,
                    expires_at, channel_id, channel_title, _iso(now),
                ),
            )
            self._conn.commit()

    def get_tokens(self) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM youtube_tokens WHERE id = 1"
            ).fetchone()
        if row is None:
            return None
        return {
            "access_token": row["access_token"],
            "refresh_token": row["refresh_token"],
            "scope": row["scope"],
            "token_type": row["token_type"],
            "expires_at": row["expires_at"],
            "channel_id": row["channel_id"],
            "channel_title": row["channel_title"],
            "connected_at": row["connected_at"],
        }

    def update_access_token(self, *, access_token: str, expires_in: int | None) -> None:
        expires_at = (
            _iso(_now() + timedelta(seconds=expires_in)) if expires_in else None
        )
        with self._lock:
            self._conn.execute(
                "UPDATE youtube_tokens SET access_token = ?, expires_at = ? WHERE id = 1",
                (access_token, expires_at),
            )
            self._conn.commit()

    def clear(self) -> None:
        """Delete stored credentials (disconnect / revocation)."""
        with self._lock:
            self._conn.execute("DELETE FROM youtube_tokens")
            self._conn.commit()

    def status_view(self) -> dict[str, Any] | None:
        """NON-SENSITIVE connection summary — safe for API responses."""
        row = self.get_tokens()
        if row is None:
            return None
        connected_at = datetime.fromisoformat(row["connected_at"])
        days = (_now() - connected_at).days
        return {
            "connected": True,
            "channel_id": row["channel_id"],
            "channel_title": row["channel_title"],
            "connected_at": row["connected_at"],
            "days_since_connection": days,
            "reauthorization_recommended": days >= REAUTHORIZATION_DAYS,
            # Deliberately NO tokens, no expiry internals, no scopes granted
            # beyond what we requested.
        }
