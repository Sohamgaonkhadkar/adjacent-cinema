"""YouTube Analytics retrieval provider (M13.10).

Narrow first-release metric set (deliberate — see
docs/M13_10_YOUTUBE_ANALYTICS_INTEGRATION.md):

    views                      video view count for the period
    estimatedMinutesWatched    estimated watch time in minutes
    averageViewDuration        computed average view duration in seconds

Grain: one aggregated row per video for the requested [start, end] period
(dimensions=video, filters=video==<id>). This is PER-VIDEO performance of the
authorized channel — never channel totals, never a prediction, and cultural
affinity is never derived from it.

Audience-retention curves (elapsedVideoTimeRatio reports) are documented as a
later step, not fetched here: per-segment data exceeds the smallest useful set
and carries availability lag.

Failure honesty: transport/API errors raise typed exceptions; empty report
rows are NOT an error — they are returned with an explicit ambiguity note
(no activity vs. processing delay), and the API layer decides how to label the
observation. The Mock provider is never a fallback for live failures; it is
only reachable when the deployment opts in (ADJACENT_YT_MOCK=1) and every
value it returns is labelled mock.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

import httpx

from .youtube_auth import REVOKE_URL, TOKEN_URL, YouTubeSettings

ANALYTICS_QUERY_URL = "https://youtubeanalytics.googleapis.com/v2/reports"
DATA_API_URL = "https://www.googleapis.com/youtube/v3"

#: The narrow first-release metric set, in query order.
METRICS: tuple[str, ...] = ("views", "estimatedMinutesWatched", "averageViewDuration")

EMPTY_REPORT_NOTE = (
    "YouTube returned no rows for this video and period. This is ambiguous: "
    "it may mean no views occurred, or that analytics processing has not "
    "finished. It is NOT recorded as a zero."
)


class YouTubeProviderError(Exception):
    """Typed, honest failure. ``code`` is stable for clients; message is human."""

    def __init__(self, code: str, message: str, status_code: int | None = None) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"{code}: {message}")


class NotConnected(YouTubeProviderError):
    def __init__(self, message: str = "no authorized YouTube connection") -> None:
        super().__init__("not_connected", message)


class TokenInvalid(YouTubeProviderError):
    """Access token rejected AND refresh unavailable/failed → re-authorize."""

    def __init__(self, message: str = "authorization expired or revoked") -> None:
        super().__init__("token_invalid", message, status_code=401)


class QuotaExceeded(YouTubeProviderError):
    def __init__(self) -> None:
        super().__init__(
            "quota_exceeded",
            "YouTube API daily quota exhausted (resets midnight Pacific Time).",
            status_code=429,
        )


class VideoNotFound(YouTubeProviderError):
    def __init__(self, video_id: str) -> None:
        super().__init__(
            "video_not_found",
            f"video {video_id!r} is not accessible for the authorized channel "
            "(deleted, private to another channel, or invalid id).",
            status_code=404,
        )


class UpstreamUnavailable(YouTubeProviderError):
    def __init__(self, detail: str) -> None:
        super().__init__("upstream_unavailable", detail, status_code=502)


class YouTubeProvider:
    """Live provider over httpx. ``transport`` is injectable for tests."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        kwargs: dict[str, Any] = {"timeout": 10.0}
        if self._transport is not None:
            kwargs["transport"] = self._transport
        return httpx.AsyncClient(**kwargs)

    # -- token operations ---------------------------------------------------
    async def refresh_access_token(
        self, settings: YouTubeSettings, refresh_token: str
    ) -> dict[str, Any]:
        async with self._client() as client:
            response = await client.post(
                TOKEN_URL,
                data={
                    "client_id": settings.client_id,
                    "client_secret": settings.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        if response.status_code != 200:
            # invalid_grant: revoked / expired (e.g. Testing-mode 7-day limit,
            # 6-month inactivity). Callers must clear the stored credential.
            raise TokenInvalid()
        return response.json()

    async def revoke_token(self, token: str) -> bool:
        """Best-effort revocation at Google. Returns success."""
        try:
            async with self._client() as client:
                response = await client.post(REVOKE_URL, data={"token": token})
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    # -- channel + video listing (Data API; channels/playlistItems/videos = 1 unit each)
    async def get_channel(self, access_token: str) -> dict[str, Any] | None:
        async with self._client() as client:
            response = await client.get(
                f"{DATA_API_URL}/channels",
                params={"part": "snippet,contentDetails", "mine": "true"},
                headers=self._auth(access_token),
            )
        if response.status_code == 401:
            raise TokenInvalid()
        if response.status_code != 200:
            raise UpstreamUnavailable(f"channels.list HTTP {response.status_code}")
        items = response.json().get("items") or []
        if not items:
            return None
        return {
            "channel_id": items[0].get("id"),
            "channel_title": (items[0].get("snippet") or {}).get("title"),
            "uploads_playlist_id": (
                ((items[0].get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads")
            ),
        }

    async def list_uploads(self, access_token: str, max_pages: int = 2) -> list[dict[str, Any]]:
        """Channel uploads via uploads playlist (quota-cheap; no search.list)."""
        channel = await self.get_channel(access_token)
        if channel is None or not channel.get("uploads_playlist_id"):
            return []
        video_ids: list[str] = []
        page_token: str | None = None
        for _ in range(max_pages):  # bounded: ≤100 videos per connection view
            async with self._client() as client:
                response = await client.get(
                    f"{DATA_API_URL}/playlistItems",
                    params={
                        "part": "contentDetails",
                        "playlistId": channel["uploads_playlist_id"],
                        "maxResults": 50,
                        **({"pageToken": page_token} if page_token else {}),
                    },
                    headers=self._auth(access_token),
                )
            if response.status_code == 401:
                raise TokenInvalid()
            if response.status_code != 200:
                raise UpstreamUnavailable(f"playlistItems.list HTTP {response.status_code}")
            body = response.json()
            for item in body.get("items") or []:
                vid = (item.get("contentDetails") or {}).get("videoId")
                if vid:
                    video_ids.append(vid)
            page_token = body.get("nextPageToken")
            if not page_token:
                break
        if not video_ids:
            return []
        async with self._client() as client:
            response = await client.get(
                f"{DATA_API_URL}/videos",
                params={
                    "part": "snippet",
                    "id": ",".join(video_ids[:50]),
                },
                headers=self._auth(access_token),
            )
        if response.status_code != 200:
            raise UpstreamUnavailable(f"videos.list HTTP {response.status_code}")
        out = []
        for item in response.json().get("items") or []:
            snippet = item.get("snippet") or {}
            out.append(
                {
                    "video_id": item.get("id"),
                    "title": snippet.get("title"),
                    "published_at": snippet.get("publishedAt"),
                }
            )
        return out

    # -- analytics query ------------------------------------------------------
    async def query_video_metrics(
        self, access_token: str, video_id: str, start_date: str, end_date: str
    ) -> dict[str, Any]:
        """Aggregated metrics for ONE video over [start_date, end_date].

        Returns {"metrics": {...}, "row_count": n, "limitations": [...]}.
        Only metrics actually present in the response are included; a missing
        metric is omitted, never defaulted to zero.
        """
        params = {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": ",".join(METRICS),
            "dimensions": "video",
            "filters": f"video=={video_id}",
        }
        async with self._client() as client:
            response = await client.get(
                ANALYTICS_QUERY_URL, params=params, headers=self._auth(access_token)
            )
        if response.status_code == 401:
            raise TokenInvalid()
        if response.status_code == 403:
            errors = (response.json().get("error") or {}) if response.content else {}
            reasons = [e.get("reason") for e in errors.get("errors") or []]
            if "quotaExceeded" in reasons or "dailyLimitExceeded" in reasons:
                raise QuotaExceeded()
            raise TokenInvalid(
                "insufficient permissions — the grant may lack the required scopes"
            )
        if response.status_code == 400:
            raise VideoNotFound(video_id)
        if response.status_code == 404:
            raise VideoNotFound(video_id)
        if response.status_code != 200:
            raise UpstreamUnavailable(f"reports.query HTTP {response.status_code}")

        body = response.json()
        headers = [h.get("name") for h in body.get("columnHeaders") or []]
        rows = body.get("rows") or []
        limitations: list[str] = []
        if not rows:
            return {"metrics": {}, "row_count": 0, "limitations": [EMPTY_REPORT_NOTE]}
        row = rows[0]
        metrics: dict[str, Any] = {}
        for name, value in zip(headers, row, strict=False):
            if name == "video":
                continue
            if name == "views":
                metrics["views"] = int(value)
            elif name == "estimatedMinutesWatched":
                metrics["estimated_minutes_watched"] = float(value)
            elif name == "averageViewDuration":
                metrics["average_view_duration_seconds"] = float(value)
        missing = [m for m in METRICS if m not in headers]
        if missing:
            limitations.append(
                "YouTube response omitted metrics: " + ", ".join(missing)
                + " (partial report — absent values are NOT zeros)."
            )
        return {"metrics": metrics, "row_count": len(rows), "limitations": limitations}

    @staticmethod
    def _auth(access_token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {access_token}"}


def retrieved_now() -> str:
    return datetime.now(UTC).isoformat()


class MockYouTubeProvider:
    """Deterministic offline provider. EVERY value is labelled mock.

    Used by tests and by the opt-in ADJACENT_YT_MOCK=1 demo mode. It is never
    consulted when a live call fails, and its output can never be recorded as
    a genuine YouTube observation (evidence_ref.provider == "mock").
    """

    data_status = "mock"

    MOCK_VIDEOS: ClassVar[list[dict[str, str]]] = [
        {
            "video_id": "mockVideoId001",
            "title": "Mock Short — 'Neon Harbour' (demo data, not a real upload)",
            "published_at": "2026-09-01T00:00:00Z",
        },
        {
            "video_id": "mockVideoId002",
            "title": "Mock Short — Festival Cut (demo data, not a real upload)",
            "published_at": "2026-08-15T00:00:00Z",
        },
    ]

    def __init__(self, *, scenario: str = "default") -> None:
        #: "default" | "zero" | "empty_report" | "quota" | "token_invalid"
        self.scenario = scenario

    async def get_channel(self, access_token: str) -> dict[str, Any] | None:
        self._maybe_fail()
        return {
            "channel_id": "MOCK_CHANNEL_ID",
            "channel_title": "Mock Channel (demo data)",
            "uploads_playlist_id": "MOCK_UPLOADS",
        }

    async def list_uploads(self, access_token: str, max_pages: int = 2) -> list[dict[str, Any]]:
        self._maybe_fail()
        return list(self.MOCK_VIDEOS)

    async def query_video_metrics(
        self, access_token: str, video_id: str, start_date: str, end_date: str
    ) -> dict[str, Any]:
        self._maybe_fail()
        if video_id not in {v["video_id"] for v in self.MOCK_VIDEOS}:
            raise VideoNotFound(video_id)
        if self.scenario == "zero":
            return {
                "metrics": {
                    "views": 0,
                    "estimated_minutes_watched": 0.0,
                    "average_view_duration_seconds": 0.0,
                },
                "row_count": 1,
                "limitations": ["Mock data — observed zeros for demonstration."],
            }
        if self.scenario == "empty_report":
            return {"metrics": {}, "row_count": 0, "limitations": [EMPTY_REPORT_NOTE]}
        return {
            "metrics": {
                "views": 128,
                "estimated_minutes_watched": 512.0,
                "average_view_duration_seconds": 240.0,
            },
            "row_count": 1,
            "limitations": ["Mock data — these numbers are not real YouTube analytics."],
        }

    def _maybe_fail(self) -> None:
        if self.scenario == "quota":
            raise QuotaExceeded()
        if self.scenario == "token_invalid":
            raise TokenInvalid()
