"""YouTube authorization + analytics routes (M13.10).

Posture (see docs/M13_10_YOUTUBE_ANALYTICS_INTEGRATION.md):

* SINGLE-CONNECTION, opt-in. Adjacent has no user model; this surface stores
  at most one creator authorization for the local workspace. It is not safe
  to expose as a public multi-user service.
* Tokens never appear in responses, logs, SSE events, or traces. Only
  non-sensitive connection metadata (channel title, connected_at) is exposed.
* Live failures are NEVER substituted with mock data. The mock provider is
  reachable only via the explicit ADJACENT_YT_MOCK=1 opt-in, and everything it
  produces is labelled ``data_status="mock"`` end to end.
* Developer Policies: disconnect deletes stored credentials immediately and
  deletes YouTube-sourced observation data within the same request (the 7-day
  obligation is satisfied synchronously), leaving non-API-data tombstones so
  the experiment history stays honest about what was removed.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from ..domain.experiment_repository import DuplicateRequest
from ..domain.youtube_auth import (
    AUTHORIZE_URL,
    SCOPES,
    TokenStore,
    YouTubeSettings,
)
from ..domain.youtube_provider import (
    METRICS,
    MockYouTubeProvider,
    QuotaExceeded,
    TokenInvalid,
    UpstreamUnavailable,
    VideoNotFound,
    YouTubeProvider,
    YouTubeProviderError,
    retrieved_now,
)
from ..public_demo import public_demo_enabled
from .creator_routes import get_repo

router = APIRouter()

#: Credential storage — runtime data, NEVER committed (see .gitignore).
_DEFAULT_TOKEN_DB = (
    Path(__file__).resolve().parents[3] / "data" / "runtime" / "youtube_auth.db"
)
TOKEN_DB_PATH = Path(os.environ.get("ADJACENT_YT_TOKEN_DB", str(_DEFAULT_TOKEN_DB)))

_store: TokenStore | None = None
_provider_override: Any = None  # tests inject deterministic providers


def get_store() -> TokenStore:
    global _store
    if _store is None:
        _store = TokenStore(TOKEN_DB_PATH)
    return _store


def reset_youtube_for_tests(
    db_path: str | Path | None = None, provider: Any = None
) -> None:
    """Test hook: fresh token store + injectable provider."""
    global _store, _provider_override
    if _store is not None:
        _store.close()
    _store = TokenStore(db_path) if db_path else None
    _provider_override = provider


def get_settings() -> YouTubeSettings:
    return YouTubeSettings.from_env()


def get_mode() -> str:
    """'mock' | 'live' | 'not_configured' — never ambiguous, never silent."""
    if os.environ.get("ADJACENT_YT_MOCK", "").strip().lower() in {"1", "true", "yes", "on"}:
        return "mock"
    return "live" if get_settings().configured else "not_configured"


def get_provider() -> Any:
    if _provider_override is not None:
        return _provider_override
    if get_mode() == "mock":
        return MockYouTubeProvider()
    return YouTubeProvider()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class FromYouTubeObservationRequest(BaseModel):
    request_id: str = Field(..., min_length=8, max_length=120)
    video_id: str = Field(..., min_length=1, max_length=64)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    interpretation: str | None = Field(default=None, max_length=2000)
    #: M13.11: optional experiment-variant label (e.g. "title A"). Recorded in
    #: provenance only — a variant label never implies causal attribution.
    variant_label: str | None = Field(default=None, max_length=120)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_period(start_date: str, end_date: str) -> None:
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid date: {exc}") from exc
    if start > end:
        raise HTTPException(status_code=422, detail="start_date is after end_date")
    if end > datetime.now(UTC).date():
        # Analytics lags real time; a future end date can never have data.
        raise HTTPException(
            status_code=422,
            detail="end_date is in the future — analytics are retrospective",
        )


async def _authorized_call(coro_factory: Any) -> Any:
    """Run a provider call with the stored credential, refreshing once if needed.

    On unrecoverable auth failure the stored credential is deleted and an
    honest 401 is raised — the creator must re-authorize. No mock fallback.
    """
    store = get_store()
    row = store.get_tokens()
    if row is None and get_mode() != "mock":
        raise HTTPException(
            status_code=409,
            detail="no YouTube connection — authorize first (POST /youtube/authorize)",
        )
    token = row["access_token"] if row else "mock-access-token"
    try:
        return await coro_factory(token)
    except TokenInvalid:
        if get_mode() == "mock" or row is None or not row.get("refresh_token"):
            store.clear()
            raise HTTPException(
                status_code=401,
                detail="YouTube authorization expired or was revoked — reconnect required",
            ) from None
        settings = get_settings()
        try:
            fresh = await YouTubeProvider().refresh_access_token(
                settings, row["refresh_token"]
            )
        except (TokenInvalid, UpstreamUnavailable, httpx.HTTPError):
            store.clear()
            raise HTTPException(
                status_code=401,
                detail="YouTube authorization expired or was revoked — reconnect required",
            ) from None
        store.update_access_token(
            access_token=fresh["access_token"], expires_in=fresh.get("expires_in")
        )
        try:
            return await coro_factory(fresh["access_token"])
        except TokenInvalid:
            store.clear()
            raise HTTPException(
                status_code=401,
                detail="YouTube authorization rejected after refresh — reconnect required",
            ) from None
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=exc.message) from None
    except VideoNotFound as exc:
        raise HTTPException(status_code=404, detail=exc.message) from None
    except UpstreamUnavailable as exc:
        raise HTTPException(status_code=502, detail=exc.message) from None


# ---------------------------------------------------------------------------
# Routes: authorization
# ---------------------------------------------------------------------------


@router.get("/youtube/status")
def youtube_status() -> dict[str, Any]:
    """Honest connection state. NEVER contains tokens or secrets."""
    if public_demo_enabled():
        return {
            "mode": "not_configured",
            "mock_data": False,
            "configured": False,
            "redirect_uri": None,
            "requested_scopes": list(SCOPES),
            "single_connection_posture": True,
            "connection": None,
            "connected": False,
            "disabled_reason": "YouTube access is disabled in public demo mode.",
        }
    mode = get_mode()
    settings = get_settings()
    connection = get_store().status_view()
    return {
        "mode": mode,  # "mock" | "live" | "not_configured"
        "mock_data": mode == "mock",
        "configured": settings.configured,
        "redirect_uri": settings.redirect_uri,
        "requested_scopes": list(SCOPES),
        "single_connection_posture": True,
        "connection": connection,  # None when not connected
        "connected": connection is not None,
    }


@router.get("/youtube/authorize")
def youtube_authorize(via: str | None = Query(default=None)) -> Any:
    """Start the consent flow.

    ``via=proxy`` is set by the frontend when the request arrives through the
    Next.js /api rewrite, so the mock-mode callback redirect stays routable
    from the browser's origin. The live flow's callback destination is the
    console-registered YOUTUBE_REDIRECT_URI instead.
    """
    mode = get_mode()
    prefix = "/api" if via == "proxy" else ""
    if mode == "not_configured":
        raise HTTPException(
            status_code=503,
            detail=(
                "YouTube OAuth is not configured. The project owner must set "
                "YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and "
                "YOUTUBE_REDIRECT_URI (see docs/M13_10_YOUTUBE_ANALYTICS_INTEGRATION.md)."
            ),
        )
    state = get_store().create_state()
    if mode == "mock":
        # Exercise the real callback path with a mock grant — labelled, opt-in.
        return RedirectResponse(
            f"{prefix}/youtube/callback?code=mock-auth-code&state={state}",
            status_code=302,
        )
    settings = get_settings()
    params = urlencode(
        {
            "client_id": settings.client_id,
            "redirect_uri": settings.redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",  # required to receive a refresh token
            "prompt": "consent",  # explicit creator consent every time
            "state": state,
        }
    )
    return RedirectResponse(f"{AUTHORIZE_URL}?{params}", status_code=302)


@router.get("/youtube/callback")
async def youtube_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> Any:
    store = get_store()
    if not store.validate_and_consume_state(state):
        # Unknown / expired / replayed state: possible CSRF. Do NOT proceed.
        raise HTTPException(
            status_code=400, detail="invalid or expired OAuth state (possible CSRF)"
        )
    if error:
        # Creator denied consent (or Google reported an error) — honest state.
        return RedirectResponse(f"/creator?yt=denied&error={error}", status_code=302)
    if not code:
        raise HTTPException(status_code=400, detail="missing authorization code")

    mode = get_mode()
    if mode == "mock":
        token_body = {
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
            "scope": " ".join(SCOPES),
            "token_type": "Bearer",
            "expires_in": 3599,
        }
        provider = get_provider()
    else:
        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.client_id,
                        "client_secret": settings.client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": settings.redirect_uri,
                    },
                )
        except httpx.HTTPError:
            # Transport failure during code exchange — honest error redirect,
            # never a mock substitution, never a stored connection.
            return RedirectResponse(
                "/creator?yt=error&reason=network", status_code=302
            )
        if response.status_code != 200:
            return RedirectResponse(
                "/creator?yt=error&reason=exchange_failed", status_code=302
            )
        token_body = response.json()
        if "access_token" not in token_body:
            return RedirectResponse(
                "/creator?yt=error&reason=malformed_token_response", status_code=302
            )
        provider = get_provider()

    channel: dict[str, Any] | None = None
    try:
        channel = await provider.get_channel(token_body["access_token"])
    except YouTubeProviderError:
        channel = None  # connection still saved; status shows missing channel

    store.save_tokens(
        access_token=token_body["access_token"],
        refresh_token=token_body.get("refresh_token"),
        scope=token_body.get("scope", ""),
        token_type=token_body.get("token_type", "Bearer"),
        expires_in=token_body.get("expires_in"),
        channel_id=(channel or {}).get("channel_id"),
        channel_title=(channel or {}).get("channel_title"),
    )
    return RedirectResponse("/creator?yt=connected", status_code=302)


@router.post("/youtube/disconnect")
async def youtube_disconnect() -> dict[str, Any]:
    """Revoke (best effort) + delete credentials + delete YouTube-sourced data.

    Developer Policies require deletion of Authorized Data after revocation of
    consent; we do it synchronously. The experiment history keeps a tombstone
    NOTE (which contains no API data) so the ledger stays honest.
    """
    store = get_store()
    row = store.get_tokens()
    revoked = False
    if row is not None:
        if get_mode() == "live":
            try:
                revoked = await YouTubeProvider().revoke_token(row["access_token"])
                if row.get("refresh_token"):
                    await YouTubeProvider().revoke_token(row["refresh_token"])
            except Exception:  # revocation is best-effort; local deletion is not
                revoked = False
        else:
            revoked = True  # nothing real to revoke in mock mode
    store.clear()

    repo = get_repo()
    deleted = 0
    tombstoned = 0
    for exp in repo.list_experiments():
        eid = exp["experiment_id"]
        yt_obs = [
            o for o in repo.list_observations(eid)
            if o["source"] in ("youtube_analytics_api", "mock_youtube_analytics")
        ]
        if not yt_obs:
            continue
        repo.delete_observations([o["observation_id"] for o in yt_obs])
        deleted += len(yt_obs)
        repo.add_observation(
            eid,
            request_id=f"yt-tombstone-{eid}-{len(yt_obs)}",
            kind="NOTE",
            measurement_status="MISSING",
            interpretation=(
                f"{len(yt_obs)} YouTube-sourced observation(s) were deleted when "
                "the creator disconnected, per YouTube API Services Developer "
                "Policies (deletion on revocation of consent). No API data is "
                "retained in this record."
            ),
            source="policy_deletion",
        )
        tombstoned += 1
    return {
        "revoked_upstream": revoked,
        "credentials_deleted": True,
        "youtube_observations_deleted": deleted,
        "experiments_tombstoned": tombstoned,
    }


# ---------------------------------------------------------------------------
# Routes: data
# ---------------------------------------------------------------------------


@router.get("/youtube/videos")
async def youtube_videos() -> dict[str, Any]:
    """Uploads of the connected channel (bounded, quota-cheap listing)."""
    provider = get_provider()
    videos = await _authorized_call(provider.list_uploads)
    return {
        "data_status": "mock" if get_mode() == "mock" else "live",
        "videos": videos,
        "note": "Listing is bounded to the first 100 uploads by design (quota).",
    }


@router.get("/youtube/metrics")
async def youtube_metrics(
    video_id: str = Query(..., min_length=1, max_length=64),
    start_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict[str, Any]:
    """Preview a period's metrics for one video. Does NOT store anything."""
    _valid_period(start_date, end_date)
    provider = get_provider()
    result = await _authorized_call(
        lambda token: provider.query_video_metrics(token, video_id, start_date, end_date)
    )
    return {
        "data_status": "mock" if get_mode() == "mock" else "live",
        "video_id": video_id,
        "period": {"start_date": start_date, "end_date": end_date},
        "metrics_queried": list(METRICS),
        "row_count": result["row_count"],
        "metrics": result["metrics"],
        "limitations": result["limitations"],
        "retrieved_at": retrieved_now(),
    }


@router.post("/experiments/{experiment_id}/observations/from-youtube")
async def record_youtube_observation(
    experiment_id: str, request: FromYouTubeObservationRequest
) -> dict[str, Any]:
    """Fetch real (or labelled-mock) analytics and append an observation.

    Idempotent via request_id. Empty reports become PARTIAL observations with
    the ambiguity note — never fabricated zeros, never automatic negatives.
    Provider failures surface as HTTP errors and create NO observation.
    """
    _valid_period(request.start_date, request.end_date)
    repo = get_repo()
    if repo.get_experiment(experiment_id) is None:
        raise HTTPException(status_code=404, detail=f"experiment {experiment_id} not found")

    provider = get_provider()
    result = await _authorized_call(
        lambda token: provider.query_video_metrics(
            token, request.video_id, request.start_date, request.end_date
        )
    )

    mode = get_mode()
    data_status = "mock" if mode == "mock" else "live"
    source = "mock_youtube_analytics" if mode == "mock" else "youtube_analytics_api"
    evidence_ref = json.dumps(
        {
            "provider": source,
            "data_status": data_status,
            "video_id": request.video_id,
            "period": {
                "start_date": request.start_date,
                "end_date": request.end_date,
            },
            "metrics_queried": list(METRICS),
            "row_count": result["row_count"],
            "retrieved_at": retrieved_now(),
            "variant_label": request.variant_label,
        },
        sort_keys=True,
    )
    measurement_status = "OBSERVED" if result["row_count"] > 0 else "PARTIAL"
    limitations = "; ".join(result["limitations"]) if result["limitations"] else None
    if mode == "mock" and limitations:
        limitations = "MOCK DATA — not real YouTube analytics. " + limitations

    try:
        observation = repo.add_observation(
            experiment_id,
            request_id=request.request_id,
            kind="ANALYTICS",
            measurement_status=measurement_status,
            observed_on=request.end_date,
            metrics=result["metrics"],
            interpretation=request.interpretation,
            source=source,
            evidence_ref=evidence_ref,
            limitations=limitations,
        )
        return {"duplicate": False, "observation": observation}
    except DuplicateRequest as exc:
        existing = repo.get_observation(exc.existing["observation_id"])
        return {"duplicate": True, "observation": existing}
