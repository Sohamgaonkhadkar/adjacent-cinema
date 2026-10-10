# Frontend Response Contract — Adjacent (live document)

**Updated:** 2026-10-10 (M13.6.10). This document now describes the payload the
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
    "primary": { "domain", "cohort_name", "member_count", "mean_affinity", "call_id" },
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
    "provenance": { "primary_call_id", "runner_up_call_id", "geography_call_id", "data_status" },
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

## 4. SSE events (`GET /run/{id}/stream`)

`trace` (phase/message progress) · `resolution` · `taste_dna` · `cohort` (one
per ranked cohort) · `heatmap` · `bet` · `test_card` · terminal `done` |
`insufficiency` | `error`. Late subscribers receive the full replay first.
