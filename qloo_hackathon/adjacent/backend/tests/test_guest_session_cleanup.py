"""Focused tests for expired guest-session data retention and cleanup.

Covers:
 - Expired sessions are deleted along with all child campaign data.
 - Active (non-expired) sessions and their data are never touched.
 - Unrelated (ownerless / other-owner) campaign data is preserved.
 - Cleanup is idempotent: running it twice changes nothing the second time.
 - The CLI ``cleanup-guest-sessions`` command exercises the same path.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from app.api import filmsponsor_routes
from app.domain.filmsponsor_guest_sessions import GuestSessionStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _populate_campaign_tree(repo, session_id: str, tag: str) -> dict:
    """Create a full campaign tree (campaign → discovery → draft → review → outreach)."""
    campaign = repo.create_campaign(
        request_id=f"{tag}-campaign",
        film_title=f"Film {tag}",
        owner_id=session_id,
    )
    cid = campaign["campaign_id"]
    draft = repo.save_draft(
        request_id=f"{tag}-draft",
        campaign_id=cid,
        brand_name=f"Brand {tag}",
        owner_id=session_id,
    )
    repo.add_source_review(
        request_id=f"{tag}-review",
        campaign_id=cid,
        draft_id=draft["draft_id"],
        verification_status="UNVERIFIED",
        owner_id=session_id,
    )
    repo.add_outreach(
        request_id=f"{tag}-outreach",
        campaign_id=cid,
        contact_status="CONTACTED",
        measurement_status="OBSERVED",
        owner_id=session_id,
    )
    return campaign


def _expire_session(store: GuestSessionStore, session_id: str) -> None:
    """Force a session to be expired (in the past)."""
    store._conn.execute(
        "UPDATE filmsponsor_guest_sessions SET expires_at=? WHERE session_id=?",
        ("2000-01-01T00:00:00+00:00", session_id),
    )
    store._conn.commit()


def _count_rows(conn: sqlite3.Connection, table: str, where: str = "", params: tuple = ()) -> int:
    sql = f"SELECT COUNT(*) FROM {table}"
    if where:
        sql += f" WHERE {where}"
    return conn.execute(sql, params).fetchone()[0]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_env(tmp_path: Path):
    """Set up an isolated database shared by a repo and a guest-session store."""
    db = tmp_path / "retention_test.db"
    filmsponsor_routes.reset_filmsponsor_for_tests(db)
    store = GuestSessionStore(db)
    repo = filmsponsor_routes.get_repo()
    yield db, store, repo
    store.close()
    filmsponsor_routes.reset_filmsponsor_for_tests()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExpiredSessionCleanup:
    """Expired sessions and their campaign trees are fully deleted."""

    def test_expired_session_and_children_are_deleted(self, db_env):
        _db, store, repo = db_env
        _token, session, _ = store.issue_or_rotate(None)
        _populate_campaign_tree(repo, session.session_id, "expired")
        _expire_session(store, session.session_id)

        removed = store.cleanup()

        assert removed == 1
        # Session row gone
        assert _count_rows(store._conn, "filmsponsor_guest_sessions", "session_id=?", (session.session_id,)) == 0
        # All campaign data gone
        for table in ("filmsponsor_campaigns", "filmsponsor_drafts", "filmsponsor_source_reviews", "filmsponsor_outreach"):
            assert _count_rows(repo._conn, table) == 0, f"{table} still has rows"

    def test_multiple_expired_sessions_cleaned_in_one_pass(self, db_env):
        _db, store, repo = db_env
        sessions = []
        for i in range(3):
            _token, session, _ = store.issue_or_rotate(None)
            _populate_campaign_tree(repo, session.session_id, f"multi-{i}")
            sessions.append(session.session_id)

        # Expire all sessions after creation so the opportunistic cleanup
        # inside issue_or_rotate does not remove them one at a time.
        for sid in sessions:
            _expire_session(store, sid)

        removed = store.cleanup()

        assert removed == 3
        for sid in sessions:
            assert _count_rows(store._conn, "filmsponsor_guest_sessions", "session_id=?", (sid,)) == 0
        assert _count_rows(repo._conn, "filmsponsor_campaigns") == 0


class TestActiveSessionPreservation:
    """Active (non-expired) sessions must never be touched by cleanup."""

    def test_active_session_survives_cleanup(self, db_env):
        _db, store, repo = db_env
        _token, session, _ = store.issue_or_rotate(None)
        campaign = _populate_campaign_tree(repo, session.session_id, "active")

        removed = store.cleanup()

        assert removed == 0
        assert _count_rows(store._conn, "filmsponsor_guest_sessions", "session_id=?", (session.session_id,)) == 1
        assert repo.get_campaign(campaign["campaign_id"], session.session_id) is not None

    def test_only_expired_session_removed_while_active_kept(self, db_env):
        _db, store, repo = db_env
        # Active session
        _tok_a, active, _ = store.issue_or_rotate(None)
        active_campaign = _populate_campaign_tree(repo, active.session_id, "kept")
        # Expired session
        _tok_b, expired, _ = store.issue_or_rotate(None)
        _populate_campaign_tree(repo, expired.session_id, "gone")
        _expire_session(store, expired.session_id)

        removed = store.cleanup()

        assert removed == 1
        # Active is intact
        assert _count_rows(store._conn, "filmsponsor_guest_sessions", "session_id=?", (active.session_id,)) == 1
        assert repo.get_campaign(active_campaign["campaign_id"], active.session_id) is not None
        # Expired is gone
        assert _count_rows(store._conn, "filmsponsor_guest_sessions", "session_id=?", (expired.session_id,)) == 0
        assert repo.list_campaigns(expired.session_id) == []


class TestUnrelatedDataPreservation:
    """Ownerless and other-owner campaign data must survive cleanup."""

    def test_ownerless_campaigns_preserved(self, db_env):
        _db, store, repo = db_env
        # Legacy campaign with no guest owner
        legacy = repo.create_campaign(request_id="legacy-001", film_title="Legacy Film")
        # Expired guest session
        _token, session, _ = store.issue_or_rotate(None)
        _populate_campaign_tree(repo, session.session_id, "doomed")
        _expire_session(store, session.session_id)

        store.cleanup()

        # Legacy campaign untouched
        assert repo.get_campaign(legacy["campaign_id"]) is not None
        # Guest data gone
        assert repo.list_campaigns(session.session_id) == []

    def test_other_owner_campaigns_preserved(self, db_env):
        _db, store, repo = db_env
        # Owner A: will expire
        _tok_a, owner_a, _ = store.issue_or_rotate(None)
        _populate_campaign_tree(repo, owner_a.session_id, "owner-a")
        _expire_session(store, owner_a.session_id)
        # Owner B: stays active
        _tok_b, owner_b, _ = store.issue_or_rotate(None)
        owner_b_campaign = _populate_campaign_tree(repo, owner_b.session_id, "owner-b")

        store.cleanup()

        assert repo.get_campaign(owner_b_campaign["campaign_id"], owner_b.session_id) is not None
        assert len(repo.list_campaigns(owner_b.session_id)) == 1
        assert repo.list_campaigns(owner_a.session_id) == []


class TestIdempotentCleanup:
    """Running cleanup repeatedly must be safe and produce no side effects."""

    def test_repeated_cleanup_returns_zero_on_second_run(self, db_env):
        _db, store, repo = db_env
        _token, session, _ = store.issue_or_rotate(None)
        _populate_campaign_tree(repo, session.session_id, "once")
        _expire_session(store, session.session_id)

        first = store.cleanup()
        second = store.cleanup()
        third = store.cleanup()

        assert first == 1
        assert second == 0
        assert third == 0

    def test_cleanup_on_empty_database(self, db_env):
        _db, store, _repo = db_env
        assert store.cleanup() == 0


class TestCleanupCLI:
    """The CLI ``cleanup-guest-sessions`` command exercises the store cleanup."""

    def test_cli_cleanup_with_expired_sessions(self, db_env, capsys):
        db, store, repo = db_env
        _token, session, _ = store.issue_or_rotate(None)
        _populate_campaign_tree(repo, session.session_id, "cli-test")
        _expire_session(store, session.session_id)

        from app.cli import main as cli_main

        exit_code = cli_main(["cleanup-guest-sessions", "--db", str(db)])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Cleaned 1 expired guest session(s)" in captured.out

    def test_cli_cleanup_quiet_skips_zero(self, db_env, capsys):
        db, _store, _repo = db_env

        from app.cli import main as cli_main

        exit_code = cli_main(["cleanup-guest-sessions", "--db", str(db), "--quiet"])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_cli_cleanup_nonexistent_db_exits_cleanly(self, tmp_path, capsys):
        from app.cli import main as cli_main

        exit_code = cli_main(["cleanup-guest-sessions", "--db", str(tmp_path / "no-such.db")])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "does not exist yet" in captured.err
