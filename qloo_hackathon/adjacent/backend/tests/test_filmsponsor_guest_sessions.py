"""Adversarial tests for opt-in FilmSponsor guest-workspace isolation.

No network calls or Qloo credentials. Sessions use independent HttpOnly-cookie
clients and the same SQLite file; tests cover both route and repository checks.
"""

from __future__ import annotations

import sqlite3
from http.cookies import SimpleCookie
from pathlib import Path

import pytest
from app.api import filmsponsor_routes
from app.domain.filmsponsor_guest_sessions import (
    SESSION_COOKIE,
    GuestSessionCapacity,
    GuestSessionStore,
)
from app.main import app
from fastapi.testclient import TestClient

ORIGIN = "https://judge.example.test"


@pytest.fixture()
def guest_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ADJACENT_FILMSPONSOR_GUEST_DEMO", "1")
    monkeypatch.setenv("ADJACENT_FILMSPONSOR_GUEST_ORIGINS", ORIGIN)
    monkeypatch.setenv("ADJACENT_FILMSPONSOR_GUEST_COOKIE_SECURE", "1")
    monkeypatch.delenv("QLOO_API_KEY", raising=False)
    filmsponsor_routes.reset_filmsponsor_for_tests(tmp_path / "guest.db")
    from app import public_demo

    public_demo._PUBLIC_REQUEST_LIMITER.reset()
    yield tmp_path / "guest.db"
    filmsponsor_routes.reset_filmsponsor_for_tests()
    monkeypatch.delenv("ADJACENT_FILMSPONSOR_GUEST_DEMO", raising=False)
    monkeypatch.delenv("ADJACENT_FILMSPONSOR_GUEST_ORIGINS", raising=False)
    monkeypatch.delenv("ADJACENT_FILMSPONSOR_GUEST_COOKIE_SECURE", raising=False)


def _client() -> TestClient:
    return TestClient(app)


def _headers(csrf: str | None = None, *, origin: str | None = ORIGIN) -> dict[str, str]:
    result: dict[str, str] = {}
    if origin is not None:
        result["Origin"] = origin
    if csrf is not None:
        result["X-FilmSponsor-CSRF"] = csrf
    return result


def _new_session(client: TestClient) -> tuple[str, str]:
    response = client.post("/filmsponsor/guest-session", json={}, headers=_headers())
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "csrf_token" in payload and "expires_at" in payload
    assert "session_id" not in payload and "session_token" not in payload
    cookies = {}
    for item in response.headers.get_list("set-cookie"):
        parsed = SimpleCookie()
        parsed.load(item)
        cookies.update(parsed)
    morsel = cookies[SESSION_COOKIE]
    csrf_morsel = cookies["adjacent_filmsponsor_csrf"]
    assert morsel["httponly"] and morsel["secure"] and morsel["samesite"].lower() == "strict"
    assert morsel["path"] == "/api/filmsponsor"
    assert not csrf_morsel["httponly"] and csrf_morsel["secure"] and csrf_morsel["samesite"].lower() == "strict"
    token = morsel.value
    # Direct ASGI tests do not traverse the Next.js /api rewrite, so explicitly
    # scope this test cookie to the backend route; production browser scope is
    # asserted above and exercised separately through Next's proxy.
    client.cookies.set(SESSION_COOKIE, token, path="/")
    client.cookies.set("adjacent_filmsponsor_csrf", csrf_morsel.value, path="/")
    assert payload["csrf_token"] == csrf_morsel.value
    return token, payload["csrf_token"]


def _create(client: TestClient, csrf: str, request_id: str = "guest-campaign-0001") -> dict:
    response = client.post(
        "/filmsponsor/campaigns",
        json={"request_id": request_id, "film_title": "Synthetic judge input"},
        headers=_headers(csrf),
    )
    assert response.status_code == 201, response.text
    return response.json()["campaign"]


def _sid(token: str) -> str:
    session = filmsponsor_routes.get_guest_store().authenticate(token, None, write=False)
    return session.session_id


class TestGuestSessionIsolation:
    def test_new_guest_session_cookie_create_and_retrieve_own_campaign(self, guest_env):
        with _client() as guest:
            _token, csrf = _new_session(guest)
            campaign = _create(guest, csrf)
            fetched = guest.get(
                f"/filmsponsor/campaigns/{campaign['campaign_id']}", headers=_headers()
            )
            assert fetched.status_code == 200
            assert fetched.json()["campaign"]["film_title"] == "Synthetic judge input"
            assert guest.get("/filmsponsor/campaigns", headers=_headers()).json()["campaigns"][0]["campaign_id"] == campaign["campaign_id"]

    def test_second_session_cannot_list_read_or_mutate_first_session_tree(self, guest_env):
        with _client() as alice, _client() as bob:
            _token_a, csrf_a = _new_session(alice)
            _token_b, csrf_b = _new_session(bob)
            campaign = _create(alice, csrf_a)
            cid = campaign["campaign_id"]
            draft_resp = alice.post(
                f"/filmsponsor/campaigns/{cid}/drafts",
                json={"request_id": "guest-draft-0001", "brand_name": "User-entered text"},
                headers=_headers(csrf_a),
            )
            assert draft_resp.status_code == 201
            draft_id = draft_resp.json()["draft"]["draft_id"]

            assert bob.get("/filmsponsor/campaigns", headers=_headers()).json() == {"campaigns": []}
            assert bob.get(f"/filmsponsor/campaigns/{cid}", headers=_headers()).status_code == 404
            assert bob.get(f"/filmsponsor/campaigns/{cid}/export", headers=_headers()).status_code == 404
            mutations = [
                (f"/filmsponsor/campaigns/{cid}/discover", {"request_id": "guest-disc-0001"}),
                (f"/filmsponsor/campaigns/{cid}/drafts", {"request_id": "guest-draft-0002", "brand_name": "X"}),
                (f"/filmsponsor/campaigns/{cid}/drafts/{draft_id}/source-reviews", {"request_id": "guest-review-01", "verification_status": "UNVERIFIED"}),
                (f"/filmsponsor/campaigns/{cid}/drafts/{draft_id}/approve", {}),
                (f"/filmsponsor/campaigns/{cid}/outreach", {"request_id": "guest-outreach-01", "contact_status": "CONTACTED", "measurement_status": "OBSERVED"}),
            ]
            for path, payload in mutations:
                denied = bob.post(path, json=payload, headers=_headers(csrf_b))
                assert denied.status_code == 404, (path, denied.status_code, denied.text)

            # Interleaving other-session writes cannot change Alice's records.
            # The same caller request_id is scoped to a different server owner;
            # it must not replay or disclose Alice's globally-unique legacy row.
            own_b = _create(bob, csrf_b, "guest-campaign-0001")
            assert own_b["campaign_id"] != cid
            assert alice.get("/filmsponsor/campaigns", headers=_headers()).json()["campaigns"][0]["campaign_id"] == cid
            assert alice.get(f"/filmsponsor/campaigns/{cid}", headers=_headers()).json()["drafts"][0]["draft_id"] == draft_id

    def test_repository_enforces_parent_and_child_ownership(self, guest_env):
        with _client() as alice, _client() as bob:
            ta, ca = _new_session(alice)
            tb, _cb = _new_session(bob)
            campaign = _create(alice, ca)
            cid = campaign["campaign_id"]
            draft = alice.post(
                f"/filmsponsor/campaigns/{cid}/drafts",
                json={"request_id": "repo-draft-0001", "brand_name": "Private"},
                headers=_headers(ca),
            ).json()["draft"]
            owner_a, owner_b = _sid(ta), _sid(tb)
            repo = filmsponsor_routes.get_repo()
            legacy = repo.create_campaign(request_id="legacy-unowned-0001", film_title="Legacy private row")
            alice_list = alice.get("/filmsponsor/campaigns", headers=_headers()).json()["campaigns"]
            assert all(item["campaign_id"] != legacy["campaign_id"] for item in alice_list)
            assert alice.get(f"/filmsponsor/campaigns/{legacy['campaign_id']}", headers=_headers()).status_code == 404
            assert repo.get_campaign(cid, owner_b) is None
            assert repo.list_campaigns(owner_b) == []
            assert repo.get_draft(draft["draft_id"], owner_b) is None
            assert repo.list_drafts(cid, owner_b) == []
            assert repo.list_discoveries(cid, owner_b) == []
            assert repo.list_source_reviews(cid, owner_b) == []
            assert repo.list_outreach(cid, owner_b) == []
            with pytest.raises(KeyError):
                repo.save_discovery(request_id="repo-forged-disc", campaign_id=cid, data_status="measured", report={}, owner_id=owner_b)
            with pytest.raises(KeyError):
                repo.save_draft(request_id="repo-forged-0001", campaign_id=cid, brand_name="x", owner_id=owner_b)
            with pytest.raises(KeyError):
                repo.add_source_review(request_id="repo-forged-rev", campaign_id=cid, draft_id=draft["draft_id"], verification_status="UNVERIFIED", owner_id=owner_b)
            with pytest.raises(KeyError):
                repo.add_outreach(request_id="repo-forged-out", campaign_id=cid, contact_status="CONTACTED", measurement_status="OBSERVED", owner_id=owner_b)
            with pytest.raises(KeyError):
                repo.approve_draft(draft["draft_id"], owner_b)
            with pytest.raises(KeyError):
                repo.export_package(cid, owner_b)
            assert repo.get_campaign(cid, owner_a) is not None

    def test_missing_invalid_expired_and_revoked_sessions_fail_closed(self, guest_env):
        with _client() as client:
            assert client.get("/filmsponsor/campaigns", headers=_headers()).status_code == 401
            client.cookies.set(SESSION_COOKIE, "not-a-valid-secret", path="/")
            assert client.get("/filmsponsor/campaigns", headers=_headers()).status_code == 401
            client.cookies.set(SESSION_COOKIE, "x" * 200, path="/")
            assert client.get("/filmsponsor/campaigns", headers=_headers()).status_code == 401
            client.cookies.clear()
            token, csrf = _new_session(client)
            campaign = _create(client, csrf)
            session_id = _sid(token)
            store = filmsponsor_routes.get_guest_store()
            store._conn.execute(
                "UPDATE filmsponsor_guest_sessions SET expires_at='2000-01-01T00:00:00+00:00' WHERE session_id=?",
                (session_id,),
            )
            store._conn.commit()
            expired = client.get("/filmsponsor/campaigns", headers=_headers())
            assert expired.status_code == 401
            assert filmsponsor_routes.get_repo().get_campaign(campaign["campaign_id"]) is None

        with _client() as revoked, _client() as copied:
            token, csrf = _new_session(revoked)
            campaign = _create(revoked, csrf)
            session_id = _sid(token)
            copied.cookies.set(SESSION_COOKIE, token, path="/")
            deleted = revoked.delete("/filmsponsor/guest-session", headers=_headers(csrf))
            assert deleted.status_code == 200
            assert revoked.get("/filmsponsor/campaigns", headers=_headers()).status_code == 401
            assert copied.get("/filmsponsor/campaigns", headers=_headers()).status_code == 401
            repo = filmsponsor_routes.get_repo()
            assert repo.get_campaign(campaign["campaign_id"]) is None
            with pytest.raises(sqlite3.IntegrityError, match="guest session is no longer active"):
                repo.create_campaign(request_id="after-revoke-0001", film_title="must not persist", owner_id=session_id)

    def test_missing_csrf_wrong_origin_and_missing_origin_reject_writes(self, guest_env):
        with _client() as guest:
            _token, csrf = _new_session(guest)
            endpoint = "/filmsponsor/campaigns"
            payload = {"request_id": "csrf-write-0001", "film_title": "Must not store"}
            assert guest.post(endpoint, json=payload, headers=_headers()).status_code == 403
            assert guest.post(endpoint, json=payload, headers=_headers("wrong-csrf")).status_code == 403
            assert guest.post(endpoint, json=payload, headers=_headers(csrf, origin=None)).status_code == 403
            assert guest.post(endpoint, json=payload, headers=_headers(csrf, origin="https://attacker.example")).status_code == 403
            cross_site = {**_headers(csrf), "Sec-Fetch-Site": "cross-site"}
            assert guest.post(endpoint, json=payload, headers=cross_site).status_code == 403
            assert guest.get(endpoint, headers=_headers()).json() == {"campaigns": []}

    def test_storage_limits_and_cleanup_are_enforced(self, guest_env, monkeypatch):
        with _client() as guest:
            token, csrf = _new_session(guest)
            first_campaign = _create(guest, csrf, "guest-cap-campaign-00")
            owner_id = _sid(token)
            repo = filmsponsor_routes.get_repo()
            for i in range(50):
                repo.save_draft(
                    request_id=f"guest-draft-cap-{i:03d}",
                    campaign_id=first_campaign["campaign_id"],
                    brand_name="bounded",
                    owner_id=owner_id,
                )
            with pytest.raises(sqlite3.IntegrityError, match="guest draft storage limit"):
                repo.save_draft(
                    request_id="guest-draft-cap-overflow",
                    campaign_id=first_campaign["campaign_id"],
                    brand_name="overflow",
                    owner_id=owner_id,
                )
            for i in range(1, 10):
                assert _create(guest, csrf, f"guest-cap-campaign-{i:02d}")
            eleventh = guest.post(
                "/filmsponsor/campaigns",
                json={"request_id": "guest-cap-campaign-10", "film_title": "Over cap"},
                headers=_headers(csrf),
            )
            assert eleventh.status_code == 429
            session_id = _sid(token)
            store = filmsponsor_routes.get_guest_store()
            store._conn.execute(
                "UPDATE filmsponsor_guest_sessions SET expires_at='2000-01-01T00:00:00+00:00' WHERE session_id=?",
                (session_id,),
            )
            store._conn.commit()
            assert store.cleanup() == 1
            assert guest.get("/filmsponsor/campaigns", headers=_headers()).status_code == 401
            assert filmsponsor_routes.get_repo().list_campaigns(session_id) == []

    def test_parallel_page_bootstrap_reuses_same_session_and_csrf(self, guest_env):
        with _client() as guest:
            token, csrf = _new_session(guest)
            again = guest.post("/filmsponsor/guest-session", json={}, headers=_headers())
            assert again.status_code == 200
            assert again.json()["csrf_token"] == csrf
            parsed = SimpleCookie()
            for item in again.headers.get_list("set-cookie"):
                parsed.load(item)
            assert parsed[SESSION_COOKIE].value == token
            assert parsed["adjacent_filmsponsor_csrf"].value == csrf

    def test_session_ownership_survives_store_reopen(self, guest_env):
        with _client() as client:
            token, csrf = _new_session(client)
            campaign = _create(client, csrf)
            session_id = _sid(token)
        filmsponsor_routes._guest_store.close()
        filmsponsor_routes._guest_store = GuestSessionStore(guest_env)
        resumed = filmsponsor_routes.get_guest_store().authenticate(token, None, write=False)
        assert resumed.session_id == session_id
        assert filmsponsor_routes.get_repo().get_campaign(campaign["campaign_id"], resumed.session_id) is not None

    def test_global_active_session_cap_and_rate_limit_are_bounded(self, guest_env, monkeypatch):
        import app.domain.filmsponsor_guest_sessions as guest_module

        monkeypatch.setattr(guest_module, "MAX_ACTIVE_SESSIONS", 1)
        store = GuestSessionStore(guest_env)
        _token, session, created = store.issue_or_rotate(None)
        assert created is True
        with pytest.raises(GuestSessionCapacity):
            store.issue_or_rotate(None)
        store.revoke(session.session_id)
        store.close()

        monkeypatch.setattr(guest_module, "MAX_REQUESTS_PER_MINUTE", 1)
        with _client() as guest:
            token, _csrf = _new_session(guest)
            # Reset the row added through the route store so the first GET is allowed.
            sid = _sid(token)
            store = filmsponsor_routes.get_guest_store()
            store._conn.execute("UPDATE filmsponsor_guest_sessions SET rate_count=0 WHERE session_id=?", (sid,))
            store._conn.commit()
            assert guest.get("/filmsponsor/campaigns", headers=_headers()).status_code == 200
            assert guest.get("/filmsponsor/campaigns", headers=_headers()).status_code == 429

    def test_unavailable_qloo_never_stores_discovery_and_unrelated_public_guard_stays(self, guest_env):
        with _client() as guest:
            _token, csrf = _new_session(guest)
            campaign = _create(guest, csrf)
            response = guest.post(
                f"/filmsponsor/campaigns/{campaign['campaign_id']}/discover",
                json={"request_id": "guest-no-key-0001"},
                headers=_headers(csrf),
            )
            assert response.status_code == 503
            assert "Nothing was substituted" in response.json()["detail"]
            assert guest.get(f"/filmsponsor/campaigns/{campaign['campaign_id']}", headers=_headers()).json()["discoveries"] == []
            assert guest.post("/experiments", json={}, headers=_headers(csrf)).status_code == 403
            # Explicitly labelled Creator fixture demo remains available; no
            # guest session cookie is shared with other route families.
            demo = guest.post("/creator/run/demo", json={}, headers=_headers())
            assert demo.status_code == 200, demo.text

    def test_guest_flag_alone_or_missing_origins_does_not_open_surface(self, guest_env, monkeypatch):
        monkeypatch.delenv("ADJACENT_FILMSPONSOR_GUEST_ORIGINS")
        with _client() as client:
            denied = client.post("/filmsponsor/guest-session", json={}, headers=_headers())
            assert denied.status_code == 403
            assert client.post("/filmsponsor/campaigns", json={"request_id": "blocked-guest-01", "film_title": "x"}).status_code == 403


def test_guest_session_store_expiry_removes_all_children(tmp_path: Path):
    db = tmp_path / "cleanup.db"
    filmsponsor_routes.reset_filmsponsor_for_tests(db)
    store = GuestSessionStore(db)
    _token, session, _ = store.issue_or_rotate(None)
    repo = filmsponsor_routes.get_repo()
    campaign = repo.create_campaign(request_id="cleanup-request", film_title="Temporary", owner_id=session.session_id)
    draft = repo.save_draft(request_id="cleanup-draft", campaign_id=campaign["campaign_id"], brand_name="Draft", owner_id=session.session_id)
    repo.add_source_review(request_id="cleanup-review", campaign_id=campaign["campaign_id"], draft_id=draft["draft_id"], verification_status="UNVERIFIED", owner_id=session.session_id)
    repo.add_outreach(request_id="cleanup-outreach", campaign_id=campaign["campaign_id"], contact_status="CONTACTED", measurement_status="OBSERVED", owner_id=session.session_id)
    store._conn.execute("UPDATE filmsponsor_guest_sessions SET expires_at='2000-01-01T00:00:00+00:00' WHERE session_id=?", (session.session_id,))
    store._conn.commit()
    assert store.cleanup() == 1
    for table in ("filmsponsor_campaigns", "filmsponsor_drafts", "filmsponsor_source_reviews", "filmsponsor_outreach"):
        assert repo._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    store.close()
    filmsponsor_routes.reset_filmsponsor_for_tests()
