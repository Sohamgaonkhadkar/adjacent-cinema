# Frontend Response Contract — Adjacent (live document)

**Updated:** 2026-10-16 (public-demo boundary and server-side proxy). This document describes the payload the
backend ACTUALLY serves, matching `_build_result()` / `_record_to_response()` in
`backend/app/api/routes.py` and the TypeScript types in
`frontend/types/adjacent.ts`. The contract is enforced by
`backend/tests/test_run_api_golden_path.py`.

> The pre-M6 draft contract that used to live here (schema_version 1.0.0 with
> `run_meta` / `candidate_cohorts` / `programme_hypothesis` envelopes) was never
> implemented in that shape and has been removed; see Git history at
> `docs/FRONTEND_CONTRACT.md` before commit 46cb73a for the historical text.

---

## 1. Routes (all reachable from the browser through the Next.js `/api` rewrite)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/run` | Start a live analysis. Body: `{city, venue_name, programme:[{title, year?, imdb_id?}]}` (≥1 film; empty programme → 422). |
| `POST` | `/api/run/demo` | Start the explicitly labelled **fixture** demo run (no key needed). No body. |
| `GET` | `/api/run/{run_id}` | Current run state + result. 404 for unknown ids. |
| `GET` | `/api/run/{run_id}/stream` | SSE. Replays all prior events to late subscribers, then streams live; terminates on `done` \| `insufficiency` \| `error`. |
| `GET` | `/api/run/{run_id}/trace` | `{run_id, trace:[...]}` provenance rows. |
| `GET` | `/api/health` | `{status, qloo_configured, mode: "live"\|"mock", ...}` — never contains the key. |

## 2. RunResponse (`POST /run`, `GET /run/{id}`)

```jsonc
{
  "run_id": "uuid",
  "status": "pending|running|completed|failed|insufficient",
  "created_at": 1760000000.0,
  "city": "as submitted",
  "venue_name": "as submitted",
  "programme": [ { "title": "...", "year": 1994, "imdb_id": "tt…|null" } ],  // verbatim, optional fields normalised to null
  "current_phase": "",
  "stop_reason": "complete|insufficiency|error|budget_exhausted|invalid_input|timeout|null",
  "stop_message": "...|null",
  "error": "...|null",
  "result": AdjacentRunResult | null,   // null until the pipeline produced one
  "trace": [ ... ]
}
```

## 3. AdjacentRunResult (`result`)

Built by `_build_result()`; TypeScript mirror: `AdjacentRunResult` in
`frontend/types/adjacent.ts`.

```jsonc
{
  "data_status": "measured" | "fixture",        // provenance of the WHOLE result
  "programme": {
    "items": [ { "title", "year", "imdb_id", "resolved": bool,
                 "qloo_entity_id": str|null, "qloo_name": str|null } ],
    "resolved_count": int, "total_count": int
  },
  "taste_dna": {
    "tags": [ { "tag_id", "name", "affinity": float, "band": "High|Medium|Low", "popularity": float|null } ],
    "tag_count": int
  },
  "cohorts": {
    "ranked": [ { "cohort_id", "domain": "urn:entity:…", "context_id", "rank": 1, "member_count": int,
                  "verdict": "strong|…|null",
                  "score": { "call_id", "context_id", "mean_affinity", "max_affinity", "novelty_proxy" } | null,
                  "members": [ { "entity_id", "name", "affinity", "band", "popularity", "call_id",
                                 "qloo_attributions": [{"entity_id", "score"}],
                                 "qloo_attribution_status": "returned|missing|unsupported|not_requested_limit|not_requested_budget" } ] } ],
    "rejected": [ { "cohort_id", "domain", "rejection_reason", "rejection_detail" } ]
  },
  "geography": {                                // present only when the heatmap step ran
    "city", "city_display", "total_cells",
    "highest_affinity_cells": [ { "latitude", "longitude", "geohash", "affinity", "affinity_rank", "popularity" } ],
    "call_id", "data_status", "source", "sufficient": bool, "note"
  },
  "programme_bet": {                            // present only when a bet cleared the evidence gate
    "primary": { "domain", "cohort_name", "member_count", "mean_affinity",
                 "cohort_id",                        // M13.7: links the bet to its ranked cohort
                 "call_id" },
    "runner_up": {...} | null,
    "two_sided_signals": { "programme_adjacency", "adjacency_band", "adjacency_call_id",
                           "cohort_breadth", "breadth_band", "breadth_call_id", "methodology_note" },
    "why", "cultural_bridge", "geographic_signal", "programming_direction",
    "falsification_condition", "rejected_candidates": [...],
    "geography_call_id", "data_status"
  },
  "test_card": {
    "title", "programme_context",
    "audience_hypothesis",                      // ← the hypothesis field (fixed mapping)
    "cultural_bridge", "geographic_signal", "programming_direction",
    "primary_evidence", "runner_up", "falsification_condition",
    "success_criteria",                              // M13.7: observable, never predicts numbers
    "observation_window",                            // M13.7: bounded, practical
    "provenance": { "primary_call_id", "runner_up_call_id", "geography_call_id",
                    "primary_cohort_id",             // M13.7: card ↔ bet ↔ cohort chain
                    "data_status" },
    "data_status"
  },
  "evidence": { "qloo_calls", "trace_rows", "stop_reason", "stop_message",
                "bounded_attribution" },          // winner-only explainability follow-up
  // Present whenever a comparison was attempted — including its refusals.
  "pairwise": {
    "status": "measured | not_applicable | unavailable_budget | unsupported_response_shape | not_modelled_in_fixture | failed",
    "available", "reason", "metric": { "key", "value", "direction" } | null,
    "cohorts": { "a", "b" }, "call_id", "observed_keys", "call_attempted",
    "error_type", "error_kind", "error_status", "limits"
  },
  "city": "..."
}
```

### Attribution and comparison surfaces (added 2026-10-27)

* `cohorts.ranked[].members[].qloo_attribution_origin` is `"scoring"`,
  `"bounded"` or `null`. `"bounded"` means the per-seed attribution came from
  one extra call covering the winning cohort's top 12 members; the affinity and
  popularity on that member still come from the original scoring call.
  `qloo_attribution_status` gains the value `"returned_bounded"`.
* `evidence.bounded_attribution` reports that follow-up call for the run:
  `status` is `returned | missing | failed | unavailable_budget | not_needed`,
  with `members_updated` and the `call_id`.
* `pairwise.metric` is currently always `null` for provider responses,
  because the public Compare reference documents request parameters but not the
  response payload fields. This build does **not** infer a metric, meaning or
  direction from plausible-looking names. The result is
  `unsupported_response_shape` with `observed_keys` (top-level key names only)
  and the originating `call_id`. Treat `metric: null` as "no verified value",
  never as zero. Only change this contract after recording an official response
  schema or a verifiable provider sample.
* `call_attempted` is `false` for every refusal (`not_applicable`,
  `unavailable_budget`) and for a parameter error that never left the process,
  and `true` once a request was sent — including a failed one. The run's call
  count is charged on `call_attempted`, so a timeout is visible in the budget
  rather than disappearing from it.
* A failed comparison carries `error_kind` (`timeout`, `authentication`,
  `upstream`, `rate_limited`, `transport`, `invalid_response`, `param_error`, …)
  and `error_status`, never the exception text: response bodies are not echoed
  into a run payload.
* `challenge.pairwise` repeats the comparison object and
  `challenge.receipt.{pairwise,attribution}` carry the compact forms for export.

### Invariants the UI relies on

1. `data_status` is truthful at every level: a fixture run is `fixture` in the
   result, the bet, the test card and the geography; only real Qloo responses
   produce `measured`.
2. A failed run has `result: null` — no fabricated payload is ever substituted.
3. `insufficiency` is a first-class outcome (`status: "insufficient"`,
   `stop_reason: "insufficiency"`), distinct from `failed`.
4. Unresolved films appear in `programme.items` with `resolved: false` and are
   excluded from evidence — never guessed.
5. Affinity values are Qloo cultural-similarity scores (0–1). They are never
   audience sizes, attendance forecasts or conversion probabilities.
6. The decision chain is explicit: `cohorts.ranked[0].cohort_id` =
   `programme_bet.primary.cohort_id` = `test_card.provenance.primary_cohort_id`
   — the Bet and Test Card always follow from the same ranked cohort.
7. Excluded cohort members are surfaced with reason codes, never hidden;
   success criteria are observations, never predictions.

## 4. SSE events (`GET /run/{id}/stream`)

`trace` (phase/message progress) · `resolution` · `taste_dna` · `cohort` (one
per ranked cohort) · `heatmap` · `bet` · `test_card` · terminal `done` |
`insufficiency` | `error`. Late subscribers receive the full replay first.

## 5. Creator Mode additions (M13.9)

Creator runs reuse the entire RunResponse/SSE contract above. Two extra routes start a
run; the same `GET /api/run/{id}`, `/stream`, `/trace` endpoints watch it.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/creator/run` | Live creator run. Body: `{title, logline?, genre?, language?, release_goal?, city?, references?:[{title, year?}], themes?:[string]}` — needs ≥1 reference or theme (else 422). Without `QLOO_API_KEY` the run FAILS honestly (`status:"failed"`, `result:null`); it never falls back to fixtures. |
| `POST` | `/api/creator/run/demo` | Explicitly labelled fixture demo (no key, no body). |

`result` for creator runs = the full `AdjacentRunResult` plus:

```jsonc
{
  "mode": "creator",                       // absent on cinema runs
  "film": { "title", "logline", "genre", "language", "release_goal" },
  "city": { "name": "…", "analysed": true } | { "analysed": false, "message": "…" }
}
```

`programme_bet` and `test_card` carry the same shapes and the same invariant
(`bet.primary.cohort_id == cohorts.ranked[0].cohort_id ==
test_card.provenance.primary_cohort_id`). `data_status` is `"fixture"` on demo runs and
`"measured"` on successful live-Qloo runs; a failed live run has no result. Creator
success criteria never predict views/retention/revenue.

### Positioning Arena (derived from an existing completed Creator response)

Positioning Arena adds no provider route and makes no new Qloo request. The Creator browser derives ANCHOR, BRIDGE, and FRONTIER candidates from `result.cohorts.ranked`, verified `programme.items`, and the run's `trace` call IDs. It refuses candidates without a strong/moderate verdict, at least two trace-linked members at or above Qloo's Medium band, finite source scores, and a matching data status. BRIDGE requires a Qloo-returned shared tag or validated attribution to the same verified source entity across distinct domains; otherwise it abstains. FRONTIER requires a different eligible cohort in the anchor's same scoring context with a higher, non-missing `novelty_proxy`.

The existing `novelty_proxy` is `1 - median_popularity` from the source cohort. It is an exploratory proxy only. Fit and novelty What-If priorities use ordinal positions only inside each source scoring context; BRIDGE's cross-context fit/novelty dimensions are explicitly unavailable. Breadth counts distinct returned entity domains. The weighted ordinal preference index is an operator preference aid, not a calibrated score or behaviour prediction. Every strategy retains measured/fixture status and source call/cohort/entity IDs.

When the creator saves the selected strategy, it is added as `source_bet.cultural_multiverse_snapshot` inside the existing experiment JSON snapshot, alongside the original Test Card, alternatives, selection, policy/formula version, limitations, and exact edited experiment design. No SQLite migration or parallel experiment store is introduced. Older records without this optional key continue to load; observations/evaluations remain append-only. The browser-side strategy contract is in `frontend/lib/positioningArena.ts` and its matching TypeScript types/components/tests.

## 6. Experiment lifecycle routes (M13.9)

All writes take `request_id` (min 8 chars) and are idempotent: a retry returns the
original record with `duplicate: true`. Persistence: SQLite, survives restarts.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/experiments` | Save a Test Card as a planned experiment. Snapshot fields (`film_context`, `source_bet`, `provenance`, `data_status`, `source_run_id`) are frozen at save time — later evidence never rewrites them. One saved decision per `source_run_id` (second save → `duplicate:true` + original). |
| `GET` | `/api/experiments` | `{experiments:[…]}` newest first. |
| `GET` | `/api/experiments/{id}` | `{experiment, observations, evaluations}` — full append-only history; 404 unknown id. |
| `POST` | `/api/experiments/{id}/observations` | Append observation. `measurement_status` ∈ `OBSERVED\|PARTIAL\|MISSING\|UNAVAILABLE\|FAILED`; `kind` ∈ `ANALYTICS\|SCREENING\|FEEDBACK\|COMMUNITY\|NOTE`. **Zero is data** (`metrics:{"views":0}`); missing data stays out of `metrics` entirely. `interpretation` and `limitations` are stored separately from measurements. |
| `POST` | `/api/experiments/{id}/evaluations` | `outcome` ∈ `SUPPORTED\|CONTRADICTED\|INCONCLUSIVE` + `rationale` (required). New evaluation sets `supersedes_id` to the previous one; **history is never rewritten** — `evaluations[-1]` is current. |

Frontend: `frontend/app/creator/page.tsx` (linked from the cinema home nav as
"Creator Mode"); client functions in `frontend/lib/api.ts`
(`createCreatorRun`, `createCreatorDemoRun`, `saveExperiment`, `listExperiments`,
`getExperiment`, `addObservation`, `addEvaluation`).

## 6b. Audience Pulse routes (pre-registered poll)

Opt-in per deployment: participant links are served only when the backend sets
`ADJACENT_PULSE_SHARE_ENABLED=1`. Creation returns 503 with that variable named
otherwise, so a poll cannot exist without a link that can collect.

**Owner routes** (same trust boundary as `/experiments`; blocked wholesale in
public-demo mode because they sit under the same prefix):

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/experiments/{id}/pulse` | Create a poll. Body: `request_id`, `question` (≤240), `options[{label}]` (2–5, unique), `opens_at`/`closes_at` (ISO-8601 **with offset**, 1 h–90 d, closes in the future), `decision_rule{kind:"option_share_at_least", option_id, threshold (0–1], min_responses ≥5}`. 201 `{duplicate, poll, responses, evaluations, share_path}`; 422 with the reason; 404 unknown experiment. |
| `GET` | `/api/experiments/{id}/pulse` | `{schema, sharing_enabled, polls:[{poll, share_path}]}`. |
| `GET` | `/api/experiments/{id}/pulse/{poll_id}` | `{poll, responses, evaluations}` — owner view. A poll belonging to another experiment is 404. |
| `POST` | `/api/experiments/{id}/pulse/{poll_id}/close` | Sets `closed_at`; the definition is untouched. |
| `POST` | `/api/experiments/{id}/pulse/{poll_id}/evaluate` | Applies the frozen rule to the stored responses and appends an evaluation (`request_id`-idempotent). `outcome` ∈ `SUPPORTED\|CONTRADICTED\|INCONCLUSIVE`. |

**Participant routes** (token only, no owner data):

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/pulse/share/{token}` | `{schema, question, options, opens_at, closes_at, collection, limitations, already_responded}`. No experiment id, hypothesis, rule or counts while collection is open. Sets `adjacent_pulse_session` (`HttpOnly; SameSite=Lax`; `Secure` unless `ADJACENT_PULSE_COOKIE_SECURE=0`). |
| `POST` | `/api/pulse/share/{token}/responses` | Body `{option_id}`. 201 `{recorded, submitted_at, collection}`; 400 without the session cookie; 409 already answered / not accepting; 422 unknown option; 429 per-poll ceiling or rate limit. |

Stored per poll: question, options, the experiment's hypothesis and snapshot, the
decision rule, the window, `closed_at`, and `frozen_at` (set by the first stored
response). A SQLite trigger rejects any later change to the question, options,
rule, hypothesis, window or experiment link once `frozen_at` is set. Responses
store a SHA-256 digest of the browser's session cookie — never the raw cookie
and never a network address. Limits: 3 polls per experiment, 1 accepting
responses at a time, 5,000 stored responses per poll, 20 response POSTs per
client key per hour (process-local).

Frontend: `frontend/components/nf/AudiencePulse.tsx` (inside the Creator research
log detail), `frontend/app/pulse/[token]/page.tsx` (participant ballot),
view model in `frontend/lib/pulse.ts`, client calls in `frontend/lib/api.ts`.

## 7. YouTube Analytics integration (M13.10)

Optional, creator-authorized, single-connection. Tokens NEVER appear in any response.
Full contract + policy notes: `docs/M13_10_YOUTUBE_ANALYTICS_INTEGRATION.md`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/youtube/status` | `{mode: "mock"\|"live"\|"not_configured", mock_data, configured, redirect_uri, requested_scopes, single_connection_posture, connection: {channel_title, connected_at, days_since_connection, reauthorization_recommended} \| null, connected}` |
| `GET` | `/api/youtube/authorize?via=proxy` | 302 into the consent flow (503 when unconfigured). `via=proxy` keeps the mock-mode callback routable behind the `/api` rewrite. |
| `GET` | `/api/youtube/callback` | OAuth callback. Invalid/expired/replayed `state` → 400 (CSRF). Denied consent → 302 `/creator?yt=denied`. Failure → 302 `/creator?yt=error&reason=…`. Success → 302 `/creator?yt=connected`. |
| `POST` | `/api/youtube/disconnect` | Revokes upstream (best effort), deletes credentials AND YouTube-sourced observations (Developer-Policies deletion), leaves tombstone NOTEs. `{revoked_upstream, credentials_deleted, youtube_observations_deleted, experiments_tombstoned}` |
| `GET` | `/api/youtube/videos` | Connected channel's uploads (≤100, no search.list). 409 when not connected. |
| `GET` | `/api/youtube/metrics?video_id&start_date&end_date` | Per-video preview `{data_status, period, metrics{views, estimated_minutes_watched, average_view_duration_seconds}, limitations, retrieved_at}`. Stores nothing. 422 future/inverted periods. |
| `POST` | `/api/experiments/{id}/observations/from-youtube` | Fetch + append observation. `request_id`-idempotent. Rows present → `OBSERVED` (zeros kept as data); empty rows → `PARTIAL` with ambiguity note (NEVER fabricated zeros); provider errors → 4xx/5xx and NO observation. `source: "youtube_analytics_api"` or `"mock_youtube_analytics"`; `evidence_ref` JSON carries provider, data_status, video_id, period, retrieved_at, row_count. |

Error codes on the analytics paths: 409 `not connected` · 401 `token invalid/revoked`
(reconnect required) · 429 `quota_exceeded` · 404 `video_not_found` · 502
`upstream_unavailable`. Live failures never fall back to mock data.

Frontend: `YouTubePanel` + `DecisionSummary` inside the Creator page's experiment
detail; client functions in `frontend/lib/api.ts` (`youtubeStatus`,
`beginYouTubeAuthorization`, `youtubeVideos`, `youtubeMetrics`,
`recordYouTubeObservation`, `disconnectYouTube`).

## 8. Public-demo mode (16 October 2026)

Enable with `ADJACENT_PUBLIC_DEMO=1` in the backend environment. This is an anonymous-demo allowlist, **not authentication**.

- Allowed requests: `GET /health`, `GET /youtube/status` (sanitized as unavailable), `GET /creator/synthesis-status` (disabled), `POST /run/demo`, `POST /creator/run/demo`, and reads for the UUID returned by those runs (`GET /run/{id}`, `/stream`, `/trace`).
- `POST /creator/run` is denied unless the owner explicitly sets `ADJACENT_PUBLIC_LIVE=1` **and** configures the server-side `QLOO_API_KEY`. `POST /run` remains blocked in public-demo mode.
- Public Creator inputs are bounded: body ≤16 KiB; title ≤160 chars; logline ≤2,000; genre ≤120; language ≤80; at most 5 themes of ≤120 chars and 5 references of ≤160 chars; optional city ≤120. The live agent's per-run call/time budget remains in force.
- All public HTTP traffic is capped at 120 requests per API-observed peer IP/minute, 2,400/process/minute, and 64 in-flight requests (including open SSE streams). Run creation has separate quotas: live Creator 2/API-observed peer IP/hour and 12/process/hour, at most 2 in flight; fixtures 12/API-observed peer IP/hour and 60/process/hour, at most 4 in flight. Behind the same-origin proxy, multiple users may share one API peer-IP bucket. Fixture request bodies are capped at 1 KiB; live Creator bodies at 16 KiB. Public run results are in-memory and capped at 100 completed records per process; completed results older than 6 hours are pruned during create/read requests.
- Experiment list/detail and all experiment writes return 403. YouTube authorization/data/write routes are blocked; the status route returns an explicit disconnected/disabled state. Synthesis execution, debug routes, `/docs`, `/redoc`, and `/openapi.json` are blocked. FilmSponsor routes also return 403 unless the separate isolated guest configuration below is fully enabled. Public health omits provider hosts, key fingerprints, and detailed parameter metadata. Public run responses, SSE errors, and trace rows replace raw exception/upstream details with safe failure text while keeping status and call references.
- CORS never uses `*`; direct browser origins must be explicitly configured with `ADJACENT_CORS_ORIGINS`. The supported frontend path is same-origin `/api` with a server-side Next.js rewrite to `ADJACENT_API_ORIGIN`.

### Isolated FilmSponsor guest mode (separately opt-in)

This remains **off by default** and activates only when `ADJACENT_PUBLIC_DEMO=1`, `ADJACENT_FILMSPONSOR_GUEST_DEMO=1`, and at least one exact origin is configured in `ADJACENT_FILMSPONSOR_GUEST_ORIGINS`. Wildcards and non-local HTTP origins are rejected. `ADJACENT_FILMSPONSOR_GUEST_COOKIE_SECURE` defaults to `1`; use `0` only for local HTTP localhost testing. Without all these conditions, the public guard keeps the prior FilmSponsor 403 behavior.

`POST /filmsponsor/guest-session` issues or resumes a server-owned workspace. It requires an allowed `Origin`, returns a CSRF token in JSON, sets a random bearer cookie (`HttpOnly; SameSite=Strict; Secure` in production; `Path=/api/filmsponsor`; eight-hour max age), and sets a matching same-site CSRF helper cookie so separate tabs reuse the same token. The raw bearer and CSRF tokens are not stored: only SHA-256 digests are persisted in the same SQLite file. All guest FilmSponsor API calls require the bearer cookie; POST/DELETE calls additionally require `X-FilmSponsor-CSRF` and an exact allowed `Origin`. `DELETE /filmsponsor/guest-session` revokes the session and deletes its campaigns/children. Expired sessions are rejected and their records are removed during session activity/cleanup.

Campaign rows carry an internal server-created session owner association. Every campaign read/write and every child path (discovery, draft, review, approval, outreach, export) is owner-filtered; legacy rows with no guest owner are not visible to guests. Request IDs are hashed with the internal owner scope before persistence to prevent global unique-key replay leaks. Limits: 500 active sessions, 8-hour lifetime, 120 API requests/minute/session, 10 campaigns/session, 2,000 guest campaigns total; global caps of 1,000 discoveries and 5,000 each of drafts, reviews, and outreach; per-campaign caps of 10 discoveries, 50 drafts, 100 reviews, and 100 outreach records; discovery report ≤128 KiB; request bodies ≤16 KiB. Never place SQLite WAL on a network filesystem or use separate database copies; deploy on one backend host with durable local storage and add an edge quota. This opt-in does not enable experiment, Creator, Cinema, YouTube, synthesis, or debug writes.

The existing request limiter is process-local; add an edge/API-gateway quota before public exposure or scaling replicas. No hosted deployment is verified; see [`FINALIZATION_STATUS.md`](FINALIZATION_STATUS.md).

## 9. FilmSponsor campaign routes (Creator Mode)

Campaign intake → live brand discovery → creator-editable sponsorship drafts →
official-source review → approval → export → manual outreach/outcome
recording. All writes take `request_id` (min 8 chars) and are idempotent: a
retry returns the original record with `duplicate: true` (same convention as
the experiment routes). Persistence: the same SQLite workspace store as
experiments (`ADJACENT_EXPERIMENTS_DB`), append-only; draft **edits create a
new version** via `supersedes_id`, and an APPROVED version is immutable.

Guest mode is a separate opt-in under §8. In that mode the frontend first calls
`POST /api/filmsponsor/guest-session` with same-origin `Origin`; the Next.js
rewrite forwards it to the backend, which sets an HttpOnly cookie and returns a
CSRF token kept only in page memory. The cookie is scoped to `/api/filmsponsor`.
Every subsequent write sends `X-FilmSponsor-CSRF`; all operations use the
server-issued session owner. Missing/expired/revoked credentials return 401;
CSRF/Origin failures return 403. `DELETE /api/filmsponsor/guest-session`
revokes the current session and removes its campaign tree. Ordinary public mode
without this explicit configuration continues to return 403 for the surface.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/filmsponsor/campaigns` | Intake. Body: `{request_id, film_title, film_year?, imdb_id?, themes?[≤5], goals?}`. |
| `GET` | `/api/filmsponsor/campaigns` | `{campaigns:[…]}` with discovery/draft/outreach counts. |
| `GET` | `/api/filmsponsor/campaigns/{id}` | `{campaign, discoveries, drafts, source_reviews, outreach}`; 404 unknown id. |
| `POST` | `/api/filmsponsor/campaigns/{id}/discover` | **Live-only** Qloo brand discovery (film identity resolution → theme canonicalisation → typed-brand queries). Without `QLOO_API_KEY` → **503** ("Nothing was substituted") and nothing is stored; provider failure before any successful call → **502**, also nothing stored. Otherwise stores a `data_status:"measured"` snapshot report: per-film `match_status` (AMBIGUOUS/MISMATCH/UNRESOLVED preserved, never promoted), brand candidates with per-query `{source, affinity, band, call_id}` observations, non-brand results kept visible with reason codes, `interpretation_limits`, and `call_ids`. |
| `POST` | `/api/filmsponsor/campaigns/{id}/drafts` | Creator-written draft version: `{request_id, brand_name, pitch?, supersedes_id?}`. Never auto-generated text. |
| `POST` | `/api/filmsponsor/campaigns/{id}/drafts/{draft_id}/source-reviews` | Creator's official-source review of a commercial claim: `verification_status` ∈ `SUPPORTED_BY_OFFICIAL_SOURCE\|CONTRADICTED\|UNVERIFIED`. The product records the review; it never asserts the claim. |
| `POST` | `/api/filmsponsor/campaigns/{id}/drafts/{draft_id}/approve` | Sets the immutable version to `APPROVED` (idempotent). **409** when no completed source review exists — approval before official-source review is refused. |
| `POST` | `/api/filmsponsor/campaigns/{id}/outreach` | Manual outreach outcome: `contact_status` ∈ `CONTACTED\|RESPONDED\|PASSED\|DECLINED\|COLLABORATED`, `measurement_status` ∈ `OBSERVED\|PARTIAL\|MISSING\|UNAVAILABLE\|FAILED`. Observed zeros go in `metrics` as `0`; missing values stay out entirely. Corrections use `supersedes_id`. |
| `GET` | `/api/filmsponsor/campaigns/{id}/export` | Approval-gated export: `approved_drafts` (with their source reviews) only; unapproved drafts appear in `excluded_drafts` with `reason:"not_approved"`; carries `interpretation_limits`. |

Frontend: `frontend/app/creator/sponsor/page.tsx` (linked from the Creator
header as "Sponsor workflow"); types in `frontend/types/adjacent.ts`
(`Sponsor*`); client functions in `frontend/lib/api.ts`
(`createSponsorCampaign`, `listSponsorCampaigns`, `getSponsorCampaign`,
`runSponsorDiscovery`, `saveSponsorDraft`, `addSponsorSourceReview`,
`approveSponsorDraft`, `addSponsorOutreach`, `exportSponsorCampaign`).

Public-demo mode blocks the entire surface (403) — shared campaign storage is
not exposed anonymously. Tests: `backend/tests/test_filmsponsor_campaigns.py`.
