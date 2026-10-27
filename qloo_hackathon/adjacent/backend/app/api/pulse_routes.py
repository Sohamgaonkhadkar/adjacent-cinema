"""Audience Pulse HTTP surface: owner control, and one bounded public ballot.

Two audiences, two shapes
-------------------------
**Owner routes** live under ``/experiments/{experiment_id}/pulse``. They sit in
the same trust boundary as the rest of the experiment lifecycle: in a public
demo the existing guard blocks the whole ``/experiments`` prefix, and nothing
here loosens that.

**Participant routes** live under ``/pulse/share/{token}``. They are the only
new anonymous surface, and they are deliberately narrow:

* a 256-bit unguessable token identifies exactly one poll;
* the GET returns the ballot only — no experiment id, no hypothesis, no rule,
  and no counts while collection is open (early totals would bias later votes);
* the POST accepts one option id, requires the HttpOnly session cookie the GET
  issued, stores a *hash* of that cookie and never a network address, and is
  refused once that session has answered;
* both routes are behind an in-process sliding-window limiter, a per-poll
  ceiling of stored responses, and the poll's own collection window.

The whole share surface is off unless the operator sets
``ADJACENT_PULSE_SHARE_ENABLED=1``. That default is intentional: a public
deployment should not gain an anonymous write endpoint because it upgraded.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..domain.pulse import (
    MAX_RESPONSES_PER_POLL,
    PULSE_SCHEMA,
    PulseCapacityError,
    PulseClosedError,
    PulseValidationError,
    public_poll,
)
from ..domain.store_errors import DuplicateRequest
from ..public_demo import PublicDemoLimiter, pulse_sharing_enabled, request_rate_key
from .creator_routes import get_repo

router = APIRouter()

PULSE_COOKIE = "adjacent_pulse_session"
_COOKIE_MAX_AGE_S = 60 * 60 * 24 * 90

#: A single participant can open a poll a few times; a script cannot loop. The
#: limiter is process-local, so a multi-worker host needs edge quotas as well —
#: the same caveat the public-demo limiter already documents.
_RESPONSE_LIMITER = PublicDemoLimiter(
    client_limit=20, global_limit=600, max_active=16, window_seconds=3600.0
)
_SHARE_READ_LIMITER = PublicDemoLimiter(
    client_limit=120, global_limit=2000, max_active=64, window_seconds=60.0
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _cookie_secure() -> bool:
    import os

    raw = (os.getenv("ADJACENT_PULSE_COOKIE_SECURE") or "").strip().lower()
    if not raw:
        return True
    return raw in {"1", "true", "yes", "on"}


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        PULSE_COOKIE,
        token,
        max_age=_COOKIE_MAX_AGE_S,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        path="/",
    )


def _require_sharing() -> None:
    if not pulse_sharing_enabled():
        raise HTTPException(
            status_code=404,
            detail="Audience Pulse sharing is not enabled on this deployment.",
        )


class PulseOptionInput(BaseModel):
    label: str = Field(..., min_length=1, max_length=120)


class PulseRuleInput(BaseModel):
    kind: str = "option_share_at_least"
    option_id: str = Field(..., min_length=1, max_length=32)
    threshold: float = Field(..., gt=0.0, le=1.0)
    min_responses: int = Field(default=10, ge=5, le=MAX_RESPONSES_PER_POLL)


class CreatePulseRequest(BaseModel):
    request_id: str = Field(..., min_length=8, max_length=128)
    question: str = Field(..., min_length=1, max_length=240)
    options: list[PulseOptionInput] = Field(..., min_length=2, max_length=5)
    opens_at: str = Field(..., min_length=10, max_length=64)
    closes_at: str = Field(..., min_length=10, max_length=64)
    decision_rule: PulseRuleInput


class PulseEvaluationRequest(BaseModel):
    request_id: str = Field(..., min_length=8, max_length=128)


class PulseResponseRequest(BaseModel):
    option_id: str = Field(..., min_length=1, max_length=32)


# ---------------------------------------------------------------------------
# Owner routes — same trust boundary as /experiments
# ---------------------------------------------------------------------------


def _owner_poll(experiment_id: str, poll_id: str) -> dict[str, Any]:
    poll = get_repo().get_poll(poll_id)
    if poll is None or poll.get("experiment_id") != experiment_id:
        # A poll that belongs to another experiment is not found here, so the
        # route cannot be used to probe for poll ids across experiments.
        raise HTTPException(status_code=404, detail=f"Poll {poll_id} not found")
    return poll


def _owner_payload(poll: dict[str, Any], *, include_share_path: bool) -> dict[str, Any]:
    payload = {
        "schema": PULSE_SCHEMA,
        "poll": {key: value for key, value in poll.items() if key != "responses"},
        "responses": poll.get("responses", []),
        "evaluations": get_repo().list_poll_evaluations(poll["poll_id"]),
    }
    if include_share_path:
        payload["share_path"] = f"/pulse/{poll['share_token']}"
    return payload


@router.post("/experiments/{experiment_id}/pulse", status_code=201)
async def create_pulse(
    experiment_id: str,
    request: CreatePulseRequest,
    http_request: Request,
) -> dict[str, Any]:
    if not pulse_sharing_enabled():
        raise HTTPException(
            status_code=503,
            detail=(
                "Audience Pulse sharing is disabled on this deployment. Set "
                "ADJACENT_PULSE_SHARE_ENABLED=1 to serve the participant link; without it a "
                "poll could be created but never answered."
            ),
        )
    try:
        poll = get_repo().create_poll(
            experiment_id,
            request_id=request.request_id,
            question=request.question,
            options=[option.model_dump() for option in request.options],
            opens_at=request.opens_at,
            closes_at=request.closes_at,
            decision_rule=request.decision_rule.model_dump(),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PulseValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DuplicateRequest as dup:
        existing = get_repo().get_poll(dup.existing["poll_id"])
        if existing is None:  # pragma: no cover - defensive
            raise HTTPException(status_code=409, detail="That request was already stored.") from dup
        return {"duplicate": True, **_owner_payload(existing, include_share_path=False)}
    return {
        "duplicate": False,
        **_owner_payload(poll, include_share_path=False),
        "share_path": f"/pulse/{poll['share_token']}",
        "share_url_base": str(http_request.base_url).rstrip("/"),
    }


@router.get("/experiments/{experiment_id}/pulse")
async def list_pulses(experiment_id: str) -> dict[str, Any]:
    repo = get_repo()
    if repo.get_experiment(experiment_id) is None:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    polls = repo.list_polls(experiment_id)
    return {
        "schema": PULSE_SCHEMA,
        "sharing_enabled": pulse_sharing_enabled(),
        "polls": [
            {
                "schema": PULSE_SCHEMA,
                "poll": {key: value for key, value in poll.items() if key != "responses"},
                "share_path": f"/pulse/{poll['share_token']}",
            }
            for poll in polls
        ],
    }


@router.get("/experiments/{experiment_id}/pulse/{poll_id}")
async def get_pulse(experiment_id: str, poll_id: str) -> dict[str, Any]:
    poll = _owner_poll(experiment_id, poll_id)
    return _owner_payload(poll, include_share_path=True)


@router.post("/experiments/{experiment_id}/pulse/{poll_id}/close", status_code=200)
async def close_pulse(experiment_id: str, poll_id: str) -> dict[str, Any]:
    _owner_poll(experiment_id, poll_id)
    try:
        poll = get_repo().close_poll(poll_id)
    except KeyError as exc:  # pragma: no cover - guarded by _owner_poll
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _owner_payload(poll, include_share_path=True)


@router.post("/experiments/{experiment_id}/pulse/{poll_id}/evaluate", status_code=201)
async def evaluate_pulse(
    experiment_id: str, poll_id: str, request: PulseEvaluationRequest
) -> dict[str, Any]:
    _owner_poll(experiment_id, poll_id)
    try:
        evaluation = get_repo().add_poll_evaluation(poll_id, request_id=request.request_id)
    except KeyError as exc:  # pragma: no cover - guarded by _owner_poll
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DuplicateRequest as dup:
        existing = next(
            (
                item
                for item in get_repo().list_poll_evaluations(poll_id)
                if item["evaluation_id"] == dup.existing.get("evaluation_id")
            ),
            None,
        )
        return {"duplicate": True, "evaluation": existing}
    poll = get_repo().get_poll(poll_id)
    return {
        "duplicate": False,
        "evaluation": evaluation,
        "preview": (poll or {}).get("evaluation_preview"),
    }


# ---------------------------------------------------------------------------
# Participant routes — token only, no owner data
# ---------------------------------------------------------------------------


@router.get("/pulse/share/{share_token}")
async def read_shared_pulse(share_token: str, request: Request, response: Response) -> Any:
    _require_sharing()
    if not _guard_share_read(request):
        raise HTTPException(
            status_code=429, detail="Too many requests for this poll. Please retry later."
        )
    poll = get_repo().get_poll_by_token(share_token)
    if poll is None:
        raise HTTPException(status_code=404, detail="This poll link is not valid.")
    session = request.cookies.get(PULSE_COOKIE)
    if not session:
        session = secrets.token_urlsafe(32)
        _set_session_cookie(response, session)
    payload = public_poll(poll, now=_now())
    payload["already_responded"] = get_repo().has_responded(poll["poll_id"], session)
    response.headers["Cache-Control"] = "no-store"
    return payload


@router.post("/pulse/share/{share_token}/responses", status_code=201)
async def submit_shared_pulse_response(
    share_token: str, request: PulseResponseRequest, http_request: Request
) -> Any:
    _require_sharing()
    permit = _acquire_response_permit(http_request)
    try:
        poll = get_repo().get_poll_by_token(share_token)
        if poll is None:
            raise HTTPException(status_code=404, detail="This poll link is not valid.")

        session = http_request.cookies.get(PULSE_COOKIE)
        if not session:
            # The cookie is SameSite=Lax, so a cross-site POST arrives without
            # it. Refusing here is what keeps this endpoint from being a
            # drive-by write target.
            raise HTTPException(
                status_code=400,
                detail=(
                    "Open the poll link in this browser before answering: the session that "
                    "records your response has not been issued."
                ),
            )
        try:
            recorded = get_repo().add_poll_response(
                poll["poll_id"],
                respondent_token=session,
                option_id=request.option_id,
                now=_now(),
            )
        except PulseClosedError as closed:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "This poll is not accepting responses.",
                    "collection": closed.status,
                },
            ) from closed
        except DuplicateRequest as dup:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": (
                        "This browser has already answered this poll. One response per session "
                        "keeps the count honest."
                    ),
                    "already_responded": bool(dup.existing.get("already_responded")),
                },
            ) from dup
        except PulseCapacityError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except PulseValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="This poll link is not valid.") from exc

        return {
            "recorded": True,
            "submitted_at": recorded["submitted_at"],
            "collection": recorded["collection"],
        }
    finally:
        if permit is not None:
            permit.release()


def _acquire_response_permit(request: Request) -> Any:
    permit, retry_after = _RESPONSE_LIMITER.acquire(request_rate_key(request))
    if permit is None:
        raise HTTPException(
            status_code=429,
            detail="Too many poll responses from this connection. Please retry later.",
            headers={"Retry-After": str(retry_after)},
        )
    return permit


def _guard_share_read(request: Request) -> bool:
    """Cheap shared limiter for the public ballot read.

    The limiter is the same object the response endpoint uses, so one abusive
    key cannot read and write without limit, and no IP is written to disk.
    """
    permit, _retry_after = _SHARE_READ_LIMITER.acquire(request_rate_key(request))
    if permit is None:
        return False
    permit.release()
    return True



def reset_pulse_limits_for_tests() -> None:
    """Test hook: clear the process-local counters (never exposed over HTTP)."""
    _RESPONSE_LIMITER.reset()
    _SHARE_READ_LIMITER.reset()


__all__ = [
    "PULSE_COOKIE",
    "CreatePulseRequest",
    "PulseEvaluationRequest",
    "PulseOptionInput",
    "PulseResponseRequest",
    "PulseRuleInput",
    "close_pulse",
    "create_pulse",
    "evaluate_pulse",
    "get_pulse",
    "list_pulses",
    "read_shared_pulse",
    "reset_pulse_limits_for_tests",
    "router",
    "submit_shared_pulse_response",
]
