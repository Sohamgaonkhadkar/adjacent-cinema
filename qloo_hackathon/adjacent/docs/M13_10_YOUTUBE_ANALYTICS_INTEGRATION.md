# M13.10 — YouTube Analytics Integration: Contract, Design, Boundaries

Access date for all sources: **2026-10-11** (fetched this session). Sections separate
[OFFICIAL] (from the cited source), [DESIGN] (our decision, reversible), and
[ASSUMPTION] (unverified, stated openly).

---

## 1. Authentication & authorization contract

- **[OFFICIAL]** `youtubeAnalytics.reports.query` requires **both**
  `https://www.googleapis.com/auth/youtube.readonly` **and**
  `https://www.googleapis.com/auth/yt-analytics.readonly`. The reference carries an
  explicit note: "API requests to this method now require access to the
  youtube.readonly scope." Integrations holding only the analytics scope receive
  403 insufficientPermissions.
  Sources: https://developers.google.com/youtube/analytics/reference/reports/query ·
  https://developers.google.com/youtube/reporting/guides/authorization/installed-apps
  (scope table) · corroborated by
  https://www.rapidevelopers.com/api-automations/how-to-automate-youtube-analytics-reports-using-the-api
  (2026-05-22).
- **[OFFICIAL]** Authorization is OAuth 2.0 (authorization-code flow). Service accounts
  are NOT supported for YouTube APIs (they return NoLinkedYouTubeAccount); the channel
  owner must authorize. (Same sources as above.)
- **[OFFICIAL]** Refresh tokens require `access_type=offline` on the authorization
  request. Refresh tokens stop working when: the user revokes access; the token is unused
  for six months; the OAuth client is in "Testing" publishing status (7-day expiry for
  External apps); or per-client token limits are exceeded (`invalid_grant`).
  Source: https://developers.google.com/identity/protocols/oauth2 (refresh-token
  expiration section).
- **[DESIGN]** We request exactly the two read-only scopes — no write scope, no
  `yt-analytics-monetary.readonly` — and always send `access_type=offline` +
  `prompt=consent`. `invalid_grant` on refresh deletes the stored credential and asks the
  creator to reconnect (never retried silently).

## 2. Quotas (YouTube Data API v3)

- **[OFFICIAL]** Default project allocation: **100 `search.list` calls/day**, 100
  `videos.insert` calls/day, and **10,000 units/day combined for all other endpoints**;
  resets midnight Pacific Time. Unit costs: `channels.list` = 1, `playlistItems.list` = 1,
  `videos.list` = 1, `search.list` = 1 per call (separate 100/day bucket).
  Source: https://developers.google.com/youtube/v3/determine_quota_cost (page states
  "Last updated 2026-10-08 UTC").
- **[DESIGN]** We never call `search.list`. Upload listing uses
  `channels.list(mine=true)` → uploads playlist → `playlistItems.list` (bounded to 2
  pages / 100 videos), so a full video-list view costs ~3 units. Analytics queries cost
  against the 10,000-unit pool; a quota error (403 quotaExceeded) surfaces as HTTP 429 and
  records **no** observation.

## 3. Eligible metrics for the first release

- **[OFFICIAL]** The targeted-query API supports `views`, `estimatedMinutesWatched`,
  `averageViewDuration` with `dimensions=video` and `filters=video==<id>` per video over a
  `[startDate, endDate]` range.
  Source: https://developers.google.com/youtube/analytics/reference/reports/query ·
  https://developers.google.com/youtube/analytics/metrics
- **[OFFICIAL]** Audience-retention data exists as a channel report keyed by the
  `elapsedVideoTimeRatio` dimension (metrics: `audienceWatchRatio`,
  `relativeRetentionPerformance`, `startedWatching`, `stoppedWatching`,
  `totalSegmentImpressions`) with a required `video` filter.
  Source: https://developers.google.com/youtube/analytics/channel_reports
- **[DESIGN]** First release fetches ONLY the three core metrics per video per period —
  the smallest set that can evaluate a positioning Test Card. Retention curves are
  deliberately deferred (per-segment data exceeds the minimal useful set and carries
  availability lag). Public video statistics (Data API `statistics`) are NOT treated as
  channel analytics; we do not use them.
- **[DESIGN]** Grain discipline: every fetch is per-video for an explicit period. Channel
  totals are never fetched and never presented as a film's performance.

## 4. Data handling & retention (Developer Policies)

Source: https://developers.google.com/youtube/terms/developer-policies (page dated
2026-06-24).

- **[OFFICIAL]** Authorized analytics data may be retained while authorization is
  re-verified **at least every 30 days**; other Authorized Data must be deleted or
  refreshed after 30 calendar days. Non-authorized data (e.g. public statistics) may be
  stored at most 30 days.
- **[OFFICIAL]** After consent revocation, all Authorized Data accessed under that consent
  must be deleted as soon as possible and within **7 calendar days**; on account-deletion
  requests, within 7 days; when tokens can no longer be refreshed, within 30 days.
- **[OFFICIAL]** Clients must never collect or store users' YouTube login credentials;
  authorization tokens may be stored as long as necessary, consistent with the consent.
- **[DESIGN]** Implementation:
  - `POST /youtube/disconnect` deletes stored tokens **and** all YouTube-sourced
    observation rows in the same request (the 7-day obligation is met synchronously).
    A tombstone NOTE (containing no API data) is appended so the experiment ledger stays
    honest about what was removed and why. Manual observations and all evaluations are
    kept — they are the creator's own records, not YouTube API data.
  - `GET /youtube/status` reports `days_since_connection` and
    `reauthorization_recommended` at ≥30 days (re-verification obligation).
  - No YouTube data is cached beyond the recorded observations; there is no background
    storage, no aggregation across channels, no resale — one workspace, one connection.
  - Tokens live in a gitignored SQLite file (`data/runtime/youtube_auth.db`), are never
    returned by any endpoint, and never appear in logs, SSE events, or traces (verified by
    a dedicated leakage test).

## 5. OAuth security posture

- **[DESIGN]** CSRF: every authorization start issues a 32-byte URL-safe `state`,
  persisted server-side with a 10-minute expiry and **consumed exactly once**; callbacks
  with unknown/expired/replayed state are rejected 400. State survives a server restart
  mid-flow (persisted, not in-memory).
- **[DESIGN]** Single-connection boundary: Adjacent has no user model (verified: no auth
  layer anywhere in `backend/app`). This integration therefore stores at most ONE channel
  authorization per workspace and says so in every status response
  (`single_connection_posture: true`). **Deployment prerequisite:** do not expose this
  backend publicly as a multi-user service; add a real ownership boundary first.
- **[DESIGN]** The redirect URI defaults to `http://localhost:3000/api/youtube/callback`
  (through the frontend proxy, keeping the whole consent flow on the browser-facing
  origin). Whatever is configured must EXACTLY match the Google Cloud console entry.
- **[DESIGN]** Owner-supplied configuration (documented in `.env.example`, never
  hardcoded): `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REDIRECT_URI`.
  Without them the integration reports `mode: "not_configured"` and `/youtube/authorize`
  returns 503 — an honest disconnected state, not a broken promise.

## 6. Mock/live boundary

- **[DESIGN]** `ADJACENT_YT_MOCK=1` (opt-in) exercises the FULL flow — authorize redirect,
  callback, state validation, video listing, metrics, observation recording — against a
  deterministic `MockYouTubeProvider`. Every artefact is labelled: status
  `mock_data: true`, responses `data_status: "mock"`, observations
  `source: "mock_youtube_analytics"`, limitations prefixed "MOCK DATA".
- **[DESIGN]** A failed live call NEVER falls back to the mock. Provider errors are typed
  (`quota_exceeded`, `token_invalid`, `video_not_found`, `upstream_unavailable`) and
  surface as honest HTTP failures; failures create no observations.

## 7. Unresolved assumptions / known gaps

1. **[ASSUMPTION]** The `reports.query` parameter shapes and error reasons were verified
   against official docs and corroborating 2026 sources, but **no live authenticated call
   was executed this session** (no OAuth client credentials exist for this project, and no
   live acceptance was attempted). Live acceptance is explicitly BLOCKED pending owner
   credentials.
2. **[ASSUMPTION]** Empty report rows are treated as ambiguous (recorded PARTIAL, never as
   zero). Whether YouTube returns zero-valued rows vs. no rows for a zero-view period was
   not verifiable offline; the code handles both distinctly.
3. **[ASSUMPTION]** Shorts behave like regular videos for these three metrics at the
   `dimensions=video` grain per the metrics documentation; no Shorts-specific metric
   handling was added.
4. Analytics data typically lags ~48–72h; we enforce `end_date ≤ today` but cannot
   verify per-period data completeness from the API.
