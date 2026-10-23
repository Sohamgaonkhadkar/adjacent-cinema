"""Opt-in guardrails for an anonymous public demo.

This is intentionally not authentication. Enable ``ADJACENT_PUBLIC_DEMO=1``
only for the narrow, public-facing demo posture: bounded Creator runs, labelled
fixture runs, transient run reads, and no shared experiment, YouTube, synthesis,
or debug access. Public live Creator runs require the separate explicit
``ADJACENT_PUBLIC_LIVE=1`` opt-in plus a server-side Qloo key.

Rate limits are process-local; a multi-worker or replicated deployment must
also enforce edge-level quotas. The API key is never sent to the browser.
"""

from __future__ import annotations

import math
import os
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import replace
from typing import ClassVar
from uuid import UUID

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_TRUE = {"1", "true", "yes", "on"}


def _enabled(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in _TRUE


def public_demo_enabled() -> bool:
    """Whether anonymous public-demo restrictions are active."""
    return _enabled("ADJACENT_PUBLIC_DEMO")


def public_live_requested() -> bool:
    """Whether the owner explicitly allows bounded live Creator runs."""
    return _enabled("ADJACENT_PUBLIC_LIVE")


def qloo_key_configured() -> bool:
    """Presence check only; key material is never returned by this module."""
    return bool((os.getenv("QLOO_API_KEY") or "").strip())


def public_live_available() -> bool:
    return public_demo_enabled() and public_live_requested() and qloo_key_configured()


_PUBLIC_FAILURE_MESSAGE = "The analysis could not complete in this public demo. Please try again."
_PUBLIC_TRACE_FAILURE_MESSAGE = "The upstream provider call could not be completed."


def public_failure_message() -> str:
    """Stable, non-sensitive failure text for public run responses."""
    return _PUBLIC_FAILURE_MESSAGE


def safe_error_diagnostic(
    *,
    error_type: str | None = None,
    kind: str | None = None,
    status: int | None = None,
    call_id: str | None = None,
) -> str:
    """Build useful failure text without echoing exception or response bodies."""
    if public_demo_enabled():
        return public_failure_message()

    suffix = f" Call ID: {call_id}." if call_id else ""
    if kind == "authentication":
        status_text = f" (HTTP {status})" if status else ""
        return f"Qloo rejected the request{status_text}. Check backend key and host configuration.{suffix}"
    if kind == "rate_limited":
        return f"Qloo rate-limited this request. Retry after a short delay.{suffix}"
    if kind == "timeout":
        return f"The Qloo request timed out. Check connectivity and retry.{suffix}"
    if kind == "transport":
        return f"Could not connect to Qloo. Check backend connectivity and retry.{suffix}"
    if kind == "upstream":
        status_text = f" (HTTP {status})" if status else ""
        return f"Qloo returned an upstream error{status_text}. Retry later.{suffix}"
    if kind == "invalid_response":
        return f"Qloo returned a response the analysis could not interpret.{suffix}"
    if kind == "missing_api_key":
        return "QLOO_API_KEY is not configured for this live analysis."
    if kind == "not_found":
        return f"Qloo could not find a required entity. Check the submitted film identity.{suffix}"

    label = error_type or "pipeline error"
    return f"Analysis failed during {label}. Review the sanitized trace and retry.{suffix}"


def safe_run_error(exc: Exception) -> str:
    """Return actionable diagnostics without exposing raw exception contents."""
    if public_demo_enabled():
        return public_failure_message()

    from .qloo.errors import QlooError

    if isinstance(exc, QlooError):
        return safe_error_diagnostic(
            error_type=type(exc).__name__,
            kind=exc.kind,
            status=exc.status,
            call_id=exc.call_id,
        )
    return safe_error_diagnostic(error_type=type(exc).__name__)


def sanitize_public_stop(state: object) -> None:
    """Remove exception detail from an agent error before public serialization."""
    if not public_demo_enabled():
        return
    stop = getattr(state, "stop", None)
    if stop is None:
        return
    reason = getattr(getattr(stop, "reason", None), "value", getattr(stop, "reason", None))
    if reason != "error":
        return
    stats = getattr(stop, "stats", {})
    safe_stats = {"calls_made": stats.get("calls_made", 0)} if isinstance(stats, dict) else {}
    state.stop = replace(
        stop,
        message=public_failure_message(),
        detail_code="provider_failure",
        stats=safe_stats,
    )


def safe_public_trace(trace_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Keep call provenance but omit exception text and raw upstream response bodies."""
    safe_rows: list[dict[str, object]] = []
    safe_error_fields = ("error_type", "kind", "status", "retryable", "call_id")
    safe_message = (
        _PUBLIC_TRACE_FAILURE_MESSAGE
        if public_demo_enabled()
        else "Detailed error omitted; use the call ID and status for diagnosis."
    )
    for source in trace_rows:
        row = dict(source)
        error = row.get("error")
        if isinstance(error, dict):
            safe_error = {key: error[key] for key in safe_error_fields if key in error}
            safe_error["message"] = safe_message
            row["error"] = safe_error
        elif error:
            row["error"] = {"message": safe_message}
        safe_rows.append(row)
    return safe_rows


def safe_public_event(event: object) -> object:
    """Scrub error events at the SSE boundary, including already-stored events."""
    if not public_demo_enabled() or getattr(event, "event", None) != "error":
        return event
    data = getattr(event, "data", None)
    if not isinstance(data, dict):
        return event
    safe_data = dict(data)
    if "message" in safe_data:
        safe_data["message"] = public_failure_message()
    if "stop_message" in safe_data:
        safe_data["stop_message"] = public_failure_message()
    return replace(event, data=safe_data)


def prune_public_run_cache(*, max_records: int = 100) -> None:
    """Keep only a bounded, recent window of volatile run results in public mode."""
    if not public_demo_enabled():
        return
    # Lazy import avoids coupling the guard module to API-router construction.
    from .api.store import run_store

    run_store.prune_completed(max_records=max_records, max_age_s=6 * 60 * 60)


class _Permit:
    def __init__(self, limiter: PublicDemoLimiter) -> None:
        self._limiter = limiter
        self._released = False
        self._lock = threading.Lock()

    def release(self) -> None:
        with self._lock:
            if self._released:
                return
            self._released = True
        self._limiter._release()


class PublicDemoLimiter:
    """Sliding-window client/global quotas plus an in-flight ceiling."""

    def __init__(
        self,
        *,
        client_limit: int,
        global_limit: int,
        max_active: int,
        window_seconds: float = 3600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client_limit = client_limit
        self.global_limit = global_limit
        self.max_active = max_active
        self.window_seconds = window_seconds
        self._clock = clock
        self._client_events: dict[str, deque[float]] = {}
        self._global_events: deque[float] = deque()
        self._active = 0
        self._lock = threading.Lock()

    def acquire(self, client_key: str) -> tuple[_Permit | None, int]:
        now = self._clock()
        with self._lock:
            self._prune(now)
            if self._active >= self.max_active:
                return None, 30
            if len(self._global_events) >= self.global_limit:
                return None, self._retry_after(self._global_events, now)
            client_events = self._client_events.setdefault(client_key, deque())
            if len(client_events) >= self.client_limit:
                return None, self._retry_after(client_events, now)
            client_events.append(now)
            self._global_events.append(now)
            self._active += 1
            return _Permit(self), 0

    def _retry_after(self, events: deque[float], now: float) -> int:
        if not events:
            return 1
        return max(1, math.ceil(self.window_seconds - (now - events[0])))

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._global_events and self._global_events[0] <= cutoff:
            self._global_events.popleft()
        expired: list[str] = []
        for key, events in self._client_events.items():
            while events and events[0] <= cutoff:
                events.popleft()
            if not events:
                expired.append(key)
        for key in expired:
            del self._client_events[key]

    def _release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)

    def reset(self) -> None:
        """Clear counters for deterministic tests; not exposed over HTTP."""
        with self._lock:
            self._client_events.clear()
            self._global_events.clear()
            self._active = 0


# Live calls are much more expensive than local fixture computation. The
# per-instance limit remains in force behind a shared Next.js proxy as well.
_PUBLIC_LIVE_LIMITER = PublicDemoLimiter(
    client_limit=2, global_limit=12, max_active=2
)
_PUBLIC_FIXTURE_LIMITER = PublicDemoLimiter(
    client_limit=12, global_limit=60, max_active=4
)
_PUBLIC_REQUEST_LIMITER = PublicDemoLimiter(
    client_limit=120,
    global_limit=2400,
    max_active=64,
    window_seconds=60,
)


def acquire_public_demo_run(request: Request, *, live: bool) -> _Permit | None:
    """Acquire a public-mode run slot and fail with a bounded retry hint."""
    if not public_demo_enabled():
        return None
    limiter = _PUBLIC_LIVE_LIMITER if live else _PUBLIC_FIXTURE_LIMITER
    client_key = request.client.host if request.client else "unknown"
    permit, retry_after = limiter.acquire(client_key)
    if permit is None:
        raise HTTPException(
            status_code=429,
            detail="Public demo run capacity reached. Please retry later.",
            headers={"Retry-After": str(retry_after)},
        )
    return permit


def _is_run_read(path: str) -> bool:
    parts = path.strip("/").split("/")
    if len(parts) not in (2, 3) or parts[0] != "run":
        return False
    try:
        UUID(parts[1])
    except ValueError:
        return False
    return len(parts) == 2 or parts[2] in {"stream", "trace"}


def _guest_filmsponsor_request(method: str, path: str) -> bool:
    if not path.startswith("/filmsponsor/"):
        return False
    from .domain.filmsponsor_guest_sessions import guest_demo_enabled

    if not guest_demo_enabled():
        return False
    if path == "/filmsponsor/guest-session":
        return method in {"POST", "DELETE"}
    return method in {"GET", "POST"}


class PublicDemoGuard:
    """ASGI boundary for public-demo requests, with a small body ceiling."""

    _FIXTURE_POSTS: ClassVar[frozenset[str]] = frozenset(
        {"/run/demo", "/creator/run/demo"}
    )
    _SAFE_GETS: ClassVar[frozenset[str]] = frozenset(
        {"/health", "/youtube/status", "/creator/synthesis-status"}
    )
    _HIDDEN: ClassVar[frozenset[str]] = frozenset(
        {"/docs", "/redoc", "/openapi.json"}
    )

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not public_demo_enabled():
            await self.app(scope, receive, send)
            return

        peer = scope.get("client")
        client_key = str(peer[0]) if peer else "unknown"
        permit, retry_after = _PUBLIC_REQUEST_LIMITER.acquire(client_key)
        if permit is None:
            await JSONResponse(
                {"detail": "Public demo request capacity reached. Please retry later."},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )(scope, receive, send)
            return
        try:
            await self._handle_public(scope, receive, send)
        finally:
            permit.release()

    async def _handle_public(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = str(scope.get("path") or "/")
        method = str(scope.get("method") or "GET").upper()
        if method == "OPTIONS":
            # Let the inner CORS middleware answer preflight against its exact
            # origin allowlist; the actual request still passes this guard.
            await self.app(scope, receive, send)
            return
        if path in self._HIDDEN or path.startswith("/debug/"):
            await JSONResponse({"detail": "Not found"}, status_code=404)(scope, receive, send)
            return

        if method in {"GET", "HEAD"} and (path in self._SAFE_GETS or _is_run_read(path)):
            await self.app(scope, receive, send)
            return

        if method == "POST" and path == "/run/demo":
            body_limit = 1024
        elif method == "POST" and path == "/creator/run/demo":
            body_limit = 16_384
        elif _guest_filmsponsor_request(method, path):
            # Strictly opt-in. Route dependencies enforce the server-issued
            # session, ownership, CSRF token, and allowed Origin for every call.
            body_limit = 16_384
        elif method == "POST" and path == "/run":
            # The Cinema UI's live workflow uses POST /run. Keep it available
            # only when the operator explicitly enables public live Qloo and
            # configures a backend-only key.
            if not public_live_requested():
                await JSONResponse(
                    {"detail": "Live Cinema runs are disabled in this public demo."},
                    status_code=403,
                )(scope, receive, send)
                return
            if not qloo_key_configured():
                await JSONResponse(
                    {"detail": "Live Qloo is not configured for this public demo."},
                    status_code=503,
                )(scope, receive, send)
                return
            body_limit = 16_384
        elif method == "POST" and path == "/creator/run":
            query = bytes(scope.get("query_string") or b"")
            is_fixture_demo = b"demo=fixture" in query
            if not is_fixture_demo:
                if not public_live_requested():
                    await JSONResponse(
                        {"detail": "Live Creator runs are disabled in this public demo."},
                        status_code=403,
                    )(scope, receive, send)
                    return
                if not qloo_key_configured():
                    await JSONResponse(
                        {"detail": "Live Qloo is not configured for this public demo."},
                        status_code=503,
                    )(scope, receive, send)
                    return
            body_limit = 16_384
        else:
            await JSONResponse(
                {
                    "detail": (
                        "This public demo does not expose shared experiments, "
                        "sponsorship campaigns, YouTube, synthesis, debug, or "
                        "live Cinema writes."
                    )
                },
                status_code=403,
            )(scope, receive, send)
            return

        content_lengths = [
            value for key, value in scope.get("headers", []) if key.lower() == b"content-length"
        ]
        if len(content_lengths) > 1:
            await JSONResponse(
                {"detail": "Invalid request body metadata."}, status_code=400
            )(scope, receive, send)
            return
        if content_lengths:
            try:
                declared_length = int(content_lengths[0])
            except ValueError:
                await JSONResponse(
                    {"detail": "Invalid request body metadata."}, status_code=400
                )(scope, receive, send)
                return
            if declared_length < 0:
                await JSONResponse(
                    {"detail": "Invalid request body metadata."}, status_code=400
                )(scope, receive, send)
                return
            if declared_length > body_limit:
                await JSONResponse(
                    {"detail": "Request body exceeds the public demo limit."},
                    status_code=413,
                )(scope, receive, send)
                return

        messages: list[Message] = []
        total_bytes = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            total_bytes += len(message.get("body", b""))
            if total_bytes > body_limit:
                await JSONResponse(
                    {"detail": "Request body exceeds the public demo limit."},
                    status_code=413,
                )(scope, receive, send)
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        cursor = 0

        async def replay_body() -> Message:
            nonlocal cursor
            if cursor < len(messages):
                message = messages[cursor]
                cursor += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_body, send)
