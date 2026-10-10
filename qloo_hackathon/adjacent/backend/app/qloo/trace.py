"""Call tracing / provenance.

Every Qloo call — real or mocked — is wrapped by `TraceRecorder.record(...)`.
The resulting `TraceRow`s are the ONLY source of the Evidence Panel. The LLM is
never asked to describe provenance; it is rendered from these rows.

Hard guarantee: `params` stored in a trace row are redacted. The API key is
removed by name AND by value, so an unusual parameter name cannot leak it.
"""

from __future__ import annotations

import datetime as _dt
import json
from collections.abc import Mapping
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any

from .errors import QlooError
from .models import CacheStatus, DataStatus, SourceKind, TraceRow

REDACTED = "***REDACTED***"

#: Parameter/header names whose values must never be persisted in a trace.
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "api_key",
        "apikey",
        "api-key",
        "x-api-key",
        "x_api_key",
        "authorization",
        "auth",
        "token",
        "access_token",
        "secret",
        "password",
        "key",
    }
)

_MAX_DEPTH = 6


def is_sensitive_key(key: str) -> bool:
    return key.strip().lower().replace("-", "_") in {k.replace("-", "_") for k in SENSITIVE_KEYS}


def redact(value: Any, *, secret: str | None = None, depth: int = 0) -> Any:
    """Recursively redact sensitive keys and any literal occurrence of `secret`."""
    if depth > _MAX_DEPTH:
        return "<max-depth>"
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if is_sensitive_key(key):
                out[key] = REDACTED
            else:
                out[key] = redact(raw_value, secret=secret, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple, set)):
        return [redact(v, secret=secret, depth=depth + 1) for v in value]
    if isinstance(value, str):
        if secret and secret and secret in value:
            return value.replace(secret, REDACTED)
        return value
    return value


def redact_params(params: Mapping[str, Any], *, secret: str | None = None) -> dict[str, Any]:
    return redact(dict(params), secret=secret)  # type: ignore[return-value]


def _now() -> _dt.datetime:
    return _dt.datetime.now(tz=_dt.UTC)


class TraceCall(AbstractContextManager["TraceCall"]):
    """One traced call. Use as a context manager; never instantiate directly."""

    def __init__(
        self,
        *,
        recorder: TraceRecorder,
        call_id: str,
        tool: str,
        endpoint: str,
        params: Mapping[str, Any],
        method: str,
        source: SourceKind,
        data_status: DataStatus,
    ) -> None:
        self._recorder = recorder
        self.call_id = call_id
        self.tool = tool
        self.endpoint = endpoint
        self.method = method
        self.source = source
        self.data_status = data_status
        self.params: dict[str, Any] = redact_params(params, secret=recorder.secret)
        self.started_at = _now()
        self.status: int | None = None
        self.result_count: int | None = None
        self.cache: CacheStatus = "bypass"
        self.attempt: int = 1
        self.backfill_detected: bool = False
        self.error: dict[str, Any] | None = None
        self.notes: list[str] = []
        self._finished = False
        self.row: TraceRow | None = None

    # -- fluent setters ----------------------------------------------------
    def set_result(self, *, status: int | None, result_count: int | None = None) -> TraceCall:
        self.status = status
        self.result_count = result_count
        return self

    def set_cache(self, status: CacheStatus) -> TraceCall:
        self.cache = status
        return self

    def set_attempt(self, attempt: int) -> TraceCall:
        self.attempt = attempt
        return self

    def set_backfill(self, detected: bool, note: str | None = None) -> TraceCall:
        self.backfill_detected = detected
        if note:
            self.notes.append(note)
        return self

    def add_note(self, note: str) -> TraceCall:
        self.notes.append(note)
        return self

    def set_error(self, error: BaseException) -> TraceCall:
        if isinstance(error, QlooError):
            self.error = error.to_dict()
            self.status = self.status if self.status is not None else error.status
        else:
            self.error = {"error_type": type(error).__name__, "message": str(error)}
        return self

    # -- context manager ---------------------------------------------------
    def __enter__(self) -> TraceCall:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if exc is not None and self.error is None:
            self.set_error(exc)
        self.finish()
        return False  # never swallow

    def finish(self) -> TraceRow:
        if self._finished and self.row is not None:
            return self.row
        duration_ms = int((_now() - self.started_at).total_seconds() * 1000)
        row = TraceRow(
            call_id=self.call_id,
            seq=self._recorder.next_seq(),
            tool=self.tool,
            endpoint=self.endpoint,
            method=self.method,
            params=self.params,
            started_at=self.started_at.isoformat(),
            duration_ms=duration_ms,
            status=self.status,
            result_count=self.result_count,
            cache=self.cache,
            source=self.source,
            data_status=self.data_status,
            attempt=self.attempt,
            backfill_detected=self.backfill_detected,
            error=self.error,
            notes=self.notes,
        )
        if self._recorder.secret:
            row.assert_no_secret(self._recorder.secret)  # defensive, fails loudly
        self._finished = True
        self.row = row
        self._recorder.append(row)
        return row


class TraceRecorder:
    """Collects trace rows for one run."""

    def __init__(self, *, run_id: str = "local", secret: str | None = None) -> None:
        self.run_id = run_id
        self.secret = secret
        self.rows: list[TraceRow] = []
        self._seq = 0
        self._call_counter = 0

    def next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def append(self, row: TraceRow) -> None:
        self.rows.append(row)

    def record(
        self,
        *,
        tool: str,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
        source: SourceKind = "qloo",
        data_status: DataStatus = "measured",
        method: str = "GET",
    ) -> TraceCall:
        self._call_counter += 1
        call_id = f"{self.run_id}-c{self._call_counter:03d}"
        return TraceCall(
            recorder=self,
            call_id=call_id,
            tool=tool,
            endpoint=endpoint,
            params=dict(params or {}),
            method=method,
            source=source,
            data_status=data_status,
        )

    # -- outputs -----------------------------------------------------------
    @property
    def call_count(self) -> int:
        return len(self.rows)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.rows if r.error)

    def as_dicts(self) -> list[dict[str, Any]]:
        return [r.model_dump() for r in self.rows]

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.as_dicts(), indent=indent, default=str)
