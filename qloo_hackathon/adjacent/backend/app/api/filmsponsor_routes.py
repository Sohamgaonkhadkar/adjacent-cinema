"""FilmSponsor campaign routes (Creator Mode).

Campaign intake → live brand discovery → creator-editable sponsorship drafts
→ official-source review → approval → export → manual outreach/outcome
recording. Mirrors the creator/experiment conventions: bounded request models,
``request_id`` idempotency, append-only storage, and honest failures.

Live brand discovery requires the backend ``QLOO_API_KEY``. Without it the
route fails with 503 — it never substitutes fixture brands. There is no
fabricated demo of live brands, affinity values, sponsorship programmes, or
outcomes anywhere in this surface.

Authorisation note: like ``/creator`` and ``/run``, this API is a local,
single-user tool with no auth model in the application today. In
``ADJACENT_PUBLIC_DEMO`` mode the public guard blocks all FilmSponsor routes
(shared campaign storage is not exposed anonymously).
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..domain.brand_discovery import (
    BRAND_ENTITY_TYPE,
    INTERPRETATION_LIMITS,
    MAX_THEMES,
    FilmInput,
    discover_brand_evidence,
)
from ..domain.filmsponsor_guest_sessions import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    GuestSession,
    GuestSessionCapacity,
    GuestSessionError,
    GuestSessionRateLimited,
    GuestSessionStore,
    allowed_origins,
    guest_demo_enabled,
    hash_request_id,
    secure_cookie_enabled,
)
from ..domain.filmsponsor_repository import DuplicateRequest, FilmSponsorRepository
from .creator_routes import EXPERIMENTS_DB_PATH

router = APIRouter()

_repo: FilmSponsorRepository | None = None
_guest_store: GuestSessionStore | None = None
_store_init_lock = threading.RLock()


def get_repo() -> FilmSponsorRepository:
    global _repo
    with _store_init_lock:
        if _repo is None:
            _repo = FilmSponsorRepository(EXPERIMENTS_DB_PATH)
        return _repo


def get_guest_store() -> GuestSessionStore:
    global _guest_store
    with _store_init_lock:
        # Ensure ownership-column migrations exist before expiry cleanup can query them.
        get_repo()
        if _guest_store is None:
            _guest_store = GuestSessionStore(EXPERIMENTS_DB_PATH)
        return _guest_store


def reset_filmsponsor_for_tests(db_path: str | Path | None = None) -> None:
    """Test hook: point both FilmSponsor stores at an isolated database."""
    global _repo, _guest_store
    if _repo is not None:
        _repo.close()
        _repo = None
    if _guest_store is not None:
        _guest_store.close()
        _guest_store = None
    if db_path is not None:
        _repo = FilmSponsorRepository(db_path)
        _guest_store = GuestSessionStore(db_path)


def _check_guest_origin(request: Request, *, required: bool) -> None:
    origin = request.headers.get("origin")
    origins = allowed_origins()
    fetch_site = request.headers.get("sec-fetch-site", "").lower()
    if fetch_site == "cross-site" or (required and not origin) or (origin is not None and origin not in origins):
        raise HTTPException(status_code=403, detail="Guest-demo origin is not allowed.")


def require_guest_session(
    request: Request,
    cookie_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_token: str | None = Header(default=None, alias="X-FilmSponsor-CSRF"),
) -> GuestSession | None:
    if not guest_demo_enabled():
        return None
    _check_guest_origin(request, required=request.method not in {"GET", "HEAD"})
    try:
        return get_guest_store().authenticate(
            cookie_token, csrf_token, write=request.method not in {"GET", "HEAD"}
        )
    except GuestSessionRateLimited as exc:
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "60"}) from exc
    except GuestSessionError as exc:
        code = 403 if "CSRF" in str(exc) else 401
        raise HTTPException(status_code=code, detail=str(exc)) from exc


def _owner(session: GuestSession | None) -> str | None:
    return session.session_id if guest_demo_enabled() and session is not None else None


def _request_id(session: GuestSession | None, value: str) -> str:
    return hash_request_id(session.session_id, value) if _owner(session) else value


def _storage_limit_error(exc: sqlite3.IntegrityError, owner_id: str | None, detail: str) -> HTTPException:
    if owner_id is not None and not get_guest_store().is_active(owner_id):
        return HTTPException(status_code=401, detail="Guest session is no longer active. Start a new workspace.")
    return HTTPException(status_code=429, detail=detail)


# ---------------------------------------------------------------------------
# Isolated anonymous guest session lifecycle
# ---------------------------------------------------------------------------


@router.post("/filmsponsor/guest-session")
async def initialize_guest_session(
    request: Request,
    response: Response,
    cookie_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
) -> dict[str, str]:
    if not guest_demo_enabled():
        raise HTTPException(status_code=404, detail="Guest FilmSponsor mode is not enabled.")
    _check_guest_origin(request, required=True)
    try:
        token, session, _created = get_guest_store().issue_or_rotate(cookie_token, csrf_cookie)
    except GuestSessionCapacity as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    max_age = max(1, int((datetime.fromisoformat(session.expires_at) - datetime.now(UTC)).total_seconds()))
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=secure_cookie_enabled(),
        samesite="strict",
        path="/api/filmsponsor",
    )
    # A same-site CSRF cookie lets parallel browser tabs reuse the same
    # synchronizer token. The DB stores only its digest; JS receives the token
    # in this response, and the cookie is never accepted as the header itself.
    response.set_cookie(
        key=CSRF_COOKIE,
        value=session.csrf_token,
        max_age=max_age,
        httponly=False,
        secure=secure_cookie_enabled(),
        samesite="strict",
        path="/api/filmsponsor",
    )
    return {"csrf_token": session.csrf_token, "expires_at": session.expires_at}


@router.delete("/filmsponsor/guest-session")
async def revoke_guest_session(
    response: Response,
    session: GuestSession | None = Depends(require_guest_session),
) -> dict[str, bool]:
    if not guest_demo_enabled() or session is None:
        raise HTTPException(status_code=404, detail="Guest FilmSponsor mode is not enabled.")
    get_guest_store().revoke(session.session_id)
    response.delete_cookie(SESSION_COOKIE, path="/api/filmsponsor", secure=secure_cookie_enabled(), httponly=True, samesite="strict")
    response.delete_cookie(CSRF_COOKIE, path="/api/filmsponsor", secure=secure_cookie_enabled(), httponly=False, samesite="strict")
    return {"revoked": True}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class CreateCampaignRequest(BaseModel):
    request_id: str = Field(..., min_length=8, max_length=120)
    film_title: str = Field(..., min_length=1, max_length=200)
    film_year: int | None = Field(default=None, ge=1888, le=2100)
    imdb_id: str | None = Field(default=None, max_length=20)
    themes: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(
        default_factory=list, max_length=MAX_THEMES
    )
    goals: str = Field(default="", max_length=1000)
    provenance: dict[str, Any] = Field(default_factory=dict, max_length=32)


class DiscoverRequest(BaseModel):
    request_id: str = Field(..., min_length=8, max_length=120)


class SaveDraftRequest(BaseModel):
    request_id: str = Field(..., min_length=8, max_length=120)
    brand_name: str = Field(..., min_length=1, max_length=200)
    pitch: str = Field(default="", max_length=4000)
    supersedes_id: str | None = Field(default=None, max_length=64)


class SourceReviewRequest(BaseModel):
    request_id: str = Field(..., min_length=8, max_length=120)
    source_url: str = Field(default="", max_length=2000)
    claim_checked: str = Field(default="", max_length=1000)
    verification_status: str = Field(..., max_length=40)
    notes: str | None = Field(default=None, max_length=2000)
    supersedes_id: str | None = Field(default=None, max_length=64)


class OutreachRequest(BaseModel):
    request_id: str = Field(..., min_length=8, max_length=120)
    contact_status: str = Field(..., max_length=32)
    measurement_status: str = Field(..., max_length=16)
    draft_id: str | None = Field(default=None, max_length=64)
    observed_on: str | None = Field(default=None, max_length=32)
    metrics: dict[str, Any] = Field(default_factory=dict, max_length=32)
    outcome: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    evidence_ref: str | None = Field(default=None, max_length=2000)
    supersedes_id: str | None = Field(default=None, max_length=64)


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------


@router.post("/filmsponsor/campaigns", status_code=201)
async def create_campaign(
    request: CreateCampaignRequest,
    session: GuestSession | None = Depends(require_guest_session),
) -> dict[str, Any]:
    owner_id = _owner(session)
    try:
        campaign = get_repo().create_campaign(
            film_title=request.film_title.strip(),
            film_year=request.film_year,
            imdb_id=(request.imdb_id or "").strip() or None,
            themes=[t.strip() for t in request.themes if t.strip()],
            goals=request.goals.strip(),
            provenance=request.provenance,
            owner_id=owner_id,
            request_id=_request_id(session, request.request_id),
        )
    except DuplicateRequest as exc:
        return {"duplicate": True, "campaign": exc.existing}
    except OverflowError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise _storage_limit_error(exc, owner_id, "Guest campaign storage limit reached.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Request could not be replayed for this session.") from exc
    return {"duplicate": False, "campaign": campaign}


@router.get("/filmsponsor/campaigns")
async def list_campaigns(
    session: GuestSession | None = Depends(require_guest_session),
) -> dict[str, Any]:
    return {"campaigns": get_repo().list_campaigns(_owner(session))}


@router.get("/filmsponsor/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    session: GuestSession | None = Depends(require_guest_session),
) -> dict[str, Any]:
    repo = get_repo()
    owner_id = _owner(session)
    campaign = repo.get_campaign(campaign_id, owner_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {
        "campaign": campaign,
        "discoveries": repo.list_discoveries(campaign_id, owner_id),
        "drafts": repo.list_drafts(campaign_id, owner_id),
        "source_reviews": repo.list_source_reviews(campaign_id, owner_id),
        "outreach": repo.list_outreach(campaign_id, owner_id),
    }


# ---------------------------------------------------------------------------
# Brand discovery (live only — never fabricated)
# ---------------------------------------------------------------------------


@router.post("/filmsponsor/campaigns/{campaign_id}/discover")
async def discover_campaign(
    campaign_id: str,
    request: DiscoverRequest,
    session: GuestSession | None = Depends(require_guest_session),
) -> dict[str, Any]:
    from ..config import Settings
    from ..qloo.client import QlooClient
    from ..resolution.resolver import EntityResolver

    repo = get_repo()
    owner_id = _owner(session)
    campaign = repo.get_campaign(campaign_id, owner_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    request_id = _request_id(session, request.request_id)
    existing = _find_discovery_by_request(repo, campaign_id, request_id, owner_id)
    if existing is not None:
        return {"duplicate": True, "discovery": existing}

    settings = Settings.from_env()
    if not settings.has_api_key:
        # Honest unavailable-service state. No fixture brands are substituted.
        raise HTTPException(
            status_code=503,
            detail=(
                "Live Qloo is not configured for this backend, so brand discovery "
                "is unavailable. Nothing was substituted."
            ),
        )

    films = [
        FilmInput(title=campaign["film_title"], year=campaign["film_year"], imdb_id=campaign["imdb_id"])
    ]
    themes = list(campaign["themes"])[:MAX_THEMES]

    async with QlooClient(settings) as client:
        resolver = EntityResolver(client, delay_s=0.0)
        outcome = await discover_brand_evidence(
            client=client, resolver=resolver, films=films, themes=themes
        )

    report = outcome.report
    if report.get("halt_reason") is not None and not report.get("call_ids"):
        # Provider failure before any successful call: sanitized 502, nothing stored.
        raise HTTPException(
            status_code=502,
            detail="Live brand discovery could not complete. No results were stored.",
        )

    try:
        discovery = repo.save_discovery(
            request_id=request_id,
            campaign_id=campaign_id,
            data_status=outcome.data_status,
            report=_sanitized_report(report),
            owner_id=owner_id,
        )
    except DuplicateRequest as exc:
        return {"duplicate": True, "discovery": repo.get_discovery(exc.existing["discovery_id"], owner_id)}
    except sqlite3.IntegrityError as exc:
        raise _storage_limit_error(exc, owner_id, "Guest discovery storage limit reached.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    return {"duplicate": False, "discovery": discovery}


def _find_discovery_by_request(
    repo: FilmSponsorRepository, campaign_id: str, request_id: str, owner_id: str | None = None
) -> dict[str, Any] | None:
    for record in repo.list_discoveries(campaign_id, owner_id):
        if record["request_id"] == request_id:
            return record
    return None


def _sanitized_report(report: dict[str, Any]) -> dict[str, Any]:
    """Drop nothing but keep the report JSON-safe and bounded."""
    out = dict(report)
    out["interpretation_limits"] = list(INTERPRETATION_LIMITS)
    out["brand_domain"] = BRAND_ENTITY_TYPE
    return out


# ---------------------------------------------------------------------------
# Drafts, source review, approval
# ---------------------------------------------------------------------------


@router.post("/filmsponsor/campaigns/{campaign_id}/drafts", status_code=201)
async def save_draft(
    campaign_id: str,
    request: SaveDraftRequest,
    session: GuestSession | None = Depends(require_guest_session),
) -> dict[str, Any]:
    repo = get_repo()
    owner_id = _owner(session)
    if repo.get_campaign(campaign_id, owner_id) is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        draft = repo.save_draft(
            request_id=_request_id(session, request.request_id),
            campaign_id=campaign_id,
            brand_name=request.brand_name.strip(),
            pitch=request.pitch.strip(),
            supersedes_id=request.supersedes_id,
            owner_id=owner_id,
        )
    except DuplicateRequest as exc:
        return {"duplicate": True, "draft": repo.get_draft(exc.existing["draft_id"], owner_id)}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise _storage_limit_error(exc, owner_id, "Guest draft storage limit reached.") from exc
    return {"duplicate": False, "draft": draft}


@router.post(
    "/filmsponsor/campaigns/{campaign_id}/drafts/{draft_id}/source-reviews",
    status_code=201,
)
async def add_source_review(
    campaign_id: str,
    draft_id: str,
    request: SourceReviewRequest,
    session: GuestSession | None = Depends(require_guest_session),
) -> dict[str, Any]:
    repo = get_repo()
    owner_id = _owner(session)
    try:
        review = repo.add_source_review(
            request_id=_request_id(session, request.request_id),
            campaign_id=campaign_id,
            draft_id=draft_id,
            source_url=request.source_url.strip(),
            claim_checked=request.claim_checked.strip(),
            verification_status=request.verification_status.strip().upper(),
            notes=request.notes,
            supersedes_id=request.supersedes_id,
            owner_id=owner_id,
        )
    except DuplicateRequest as exc:
        return {"duplicate": True, "review": repo.get_source_review(exc.existing["review_id"], owner_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise _storage_limit_error(exc, owner_id, "Guest source-review storage limit reached.") from exc
    return {"duplicate": False, "review": review}


@router.post("/filmsponsor/campaigns/{campaign_id}/drafts/{draft_id}/approve")
async def approve_draft(
    campaign_id: str,
    draft_id: str,
    session: GuestSession | None = Depends(require_guest_session),
) -> dict[str, Any]:
    repo = get_repo()
    owner_id = _owner(session)
    draft = repo.get_draft(draft_id, owner_id)
    if draft is None or draft["campaign_id"] != campaign_id:
        raise HTTPException(status_code=404, detail="Draft not found")
    try:
        approved = repo.approve_draft(draft_id, owner_id)
    except ValueError as exc:
        # Approval before a completed official-source review is refused.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"draft": approved}


# ---------------------------------------------------------------------------
# Outreach and export
# ---------------------------------------------------------------------------


@router.post("/filmsponsor/campaigns/{campaign_id}/outreach", status_code=201)
async def add_outreach(
    campaign_id: str,
    request: OutreachRequest,
    session: GuestSession | None = Depends(require_guest_session),
) -> dict[str, Any]:
    repo = get_repo()
    owner_id = _owner(session)
    if repo.get_campaign(campaign_id, owner_id) is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        record = repo.add_outreach(
            request_id=_request_id(session, request.request_id),
            campaign_id=campaign_id,
            contact_status=request.contact_status.strip().upper(),
            measurement_status=request.measurement_status.strip().upper(),
            draft_id=request.draft_id,
            observed_on=request.observed_on,
            metrics=request.metrics,
            outcome=request.outcome,
            notes=request.notes,
            evidence_ref=request.evidence_ref,
            supersedes_id=request.supersedes_id,
            owner_id=owner_id,
        )
    except DuplicateRequest as exc:
        return {"duplicate": True, "outreach": repo.get_outreach(exc.existing["outreach_id"], owner_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise _storage_limit_error(exc, owner_id, "Guest outreach storage limit reached.") from exc
    return {"duplicate": False, "outreach": record}


@router.get("/filmsponsor/campaigns/{campaign_id}/export")
async def export_campaign(
    campaign_id: str,
    session: GuestSession | None = Depends(require_guest_session),
) -> dict[str, Any]:
    """Approval-gated export: unapproved drafts are excluded with reasons."""
    repo = get_repo()
    try:
        return repo.export_package(campaign_id, _owner(session))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
