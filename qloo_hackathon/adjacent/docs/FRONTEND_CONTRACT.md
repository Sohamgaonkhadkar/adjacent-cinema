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
    "ranked": [ { "cohort_id", "domain": "urn:entity:…", "rank": 1, "member_count": int,
                  "verdict": "strong|…|null",
                  "score": { "mean_affinity", "max_affinity", "novelty_proxy" } | null,
                  "members": [ { "entity_id", "name", "affinity", "band", "popularity" } ] } ],
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
  "evidence": { "qloo_calls", "trace_rows", "stop_reason", "stop_message" },
  "city": "..."
}
```

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
- Experiment list/detail and all experiment writes return 403. YouTube authorization/data/write routes are blocked; the status route returns an explicit disconnected/disabled state. Synthesis execution, debug routes, `/docs`, `/redoc`, and `/openapi.json` are blocked. Public health omits provider hosts, key fingerprints, and detailed parameter metadata. Public run responses, SSE errors, and trace rows replace raw exception/upstream details with safe failure text while keeping status and call references.
- CORS never uses `*`; direct browser origins must be explicitly configured with `ADJACENT_CORS_ORIGINS`. The supported frontend path is same-origin `/api` with a server-side Next.js rewrite to `ADJACENT_API_ORIGIN`.

The rate limits are process-local. Add an edge/API-gateway quota and a shared limiter before scaling across workers or replicas. No hosted deployment is verified; see [`FINALIZATION_STATUS.md`](FINALIZATION_STATUS.md).
