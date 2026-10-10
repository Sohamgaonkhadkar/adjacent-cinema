"""Structured error types for the Qloo integration layer.

Two families:

1. `QlooError` + subclasses — anything that came back from (or failed to reach)
   the Qloo API. These are always *classified*: 401/403, 404, 429, 5xx and
   timeouts are handled differently by every caller.

2. `ParamError` + subclasses — local validation failures raised *before* a
   request is ever built. These exist so that a parameter we have not verified
   against official documentation can never be silently sent to Qloo.

Nothing in this module swallows an error.
"""

from __future__ import annotations

from typing import Any


class AdjacentError(Exception):
    """Base class for every error raised by this codebase."""

    def to_dict(self) -> dict[str, Any]:
        return {"error_type": type(self).__name__, "message": str(self)}


# ---------------------------------------------------------------------------
# 1. Transport / API errors
# ---------------------------------------------------------------------------


class QlooError(AdjacentError):
    """A failed or rejected call to the Qloo API."""

    #: HTTP status that produced this error, when there was one.
    default_status: int | None = None
    #: Short machine-readable classification used by callers and the trace.
    kind: str = "qloo_error"

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        status: int | None = None,
        detail: Any = None,
        call_id: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.endpoint = endpoint
        self.status = status if status is not None else self.default_status
        self.detail = detail
        self.call_id = call_id
        self.retryable = retryable

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": type(self).__name__,
            "kind": self.kind,
            "message": str(self),
            "endpoint": self.endpoint,
            "status": self.status,
            "retryable": self.retryable,
            "call_id": self.call_id,
            "detail": self.detail,
        }


class AuthenticationError(QlooError):
    """401/403 — the key is missing, wrong, or the host is wrong.

    Almost always means: hackathon key sent to staging/production, or Bearer /
    query-param auth used instead of the `X-Api-Key` header.
    """

    default_status = 401
    kind = "authentication"

    def __init__(self, message: str = "Qloo rejected the credentials", **kw: Any) -> None:
        super().__init__(message, **kw)


class NotFoundError(QlooError):
    """404 — for `/entities` this is a *data outcome*, not a system failure.

    A 404 means "this entity is not in Qloo". It must be surfaced to the user as
    an unresolved item and never retried into a crash.
    """

    default_status = 404
    kind = "not_found"


class RateLimitError(QlooError):
    """429 — back off and retry a bounded number of times."""

    default_status = 429
    kind = "rate_limited"

    def __init__(
        self, message: str = "Qloo rate limit reached", *, retry_after_s: float | None = None, **kw: Any
    ) -> None:
        kw.setdefault("retryable", True)
        super().__init__(message, **kw)
        self.retry_after_s = retry_after_s


class UpstreamError(QlooError):
    """5xx or an unparseable successful response."""

    default_status = 500
    kind = "upstream"

    def __init__(self, message: str = "Qloo returned a server error", **kw: Any) -> None:
        kw.setdefault("retryable", True)
        super().__init__(message, **kw)


class QlooTimeoutError(QlooError):
    """Connect or read timeout."""

    default_status = None
    kind = "timeout"

    def __init__(self, message: str = "Timed out talking to Qloo", **kw: Any) -> None:
        kw.setdefault("retryable", True)
        super().__init__(message, **kw)


class TransportError(QlooError):
    """Anything else at the network layer (DNS, TLS, connection reset)."""

    default_status = None
    kind = "transport"

    def __init__(self, message: str = "Network failure talking to Qloo", **kw: Any) -> None:
        kw.setdefault("retryable", True)
        super().__init__(message, **kw)


class InvalidResponseError(QlooError):
    """The API returned 200 but the body does not match a shape we can parse."""

    default_status = 200
    kind = "invalid_response"

    def __init__(self, message: str = "Qloo response did not match an expected shape", **kw: Any) -> None:
        super().__init__(message, **kw)


class MissingApiKeyError(QlooError):
    """Raised when a live call is attempted with mock mode forced and no key."""

    default_status = None
    kind = "missing_api_key"

    def __init__(
        self, message: str = "QLOO_API_KEY is not set; live Qloo calls are unavailable", **kw: Any
    ) -> None:
        super().__init__(message, **kw)


# ---------------------------------------------------------------------------
# 2. Local parameter validation errors
# ---------------------------------------------------------------------------


class ParamError(AdjacentError):
    """Base class for anything rejected before a request is built."""

    kind = "param_error"

    def __init__(self, message: str, *, parameter: str | None = None, endpoint: str | None = None) -> None:
        super().__init__(message)
        self.parameter = parameter
        self.endpoint = endpoint

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": type(self).__name__,
            "kind": self.kind,
            "message": str(self),
            "parameter": self.parameter,
            "endpoint": self.endpoint,
        }


class UnverifiedParameterError(ParamError):
    """A parameter we cannot point at official documentation for.

    Raised for (a) unknown parameters, (b) parameters documented for a different
    endpoint, and (c) parameters we have explicitly marked UNVERIFIED — unless
    the caller passes `allow_unverified=True`, which is only ever done from the
    probe script while an open question is being resolved.
    """

    kind = "unverified_parameter"


class DeprecatedParameterError(ParamError):
    """A parameter Qloo documents as deprecated (`urn:entity:audience`)."""

    kind = "deprecated_parameter"


class InvalidCombinationError(ParamError):
    """Documented parameters combined in a way the documentation excludes."""

    kind = "invalid_combination"


class InvalidFilterTypeError(ParamError):
    """`filter.type` is not one of the documented values."""

    kind = "invalid_filter_type"


class InvalidValueError(ParamError):
    """A documented parameter given a value outside its documented domain."""

    kind = "invalid_value"
