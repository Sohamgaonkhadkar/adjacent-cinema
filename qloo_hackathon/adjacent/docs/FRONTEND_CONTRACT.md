# Frontend Response Contract — Adjacent

> **Status note (2026-10-10).** This document is the historical M6-era contract.
> The LIVE payload served by `POST /run` / `GET /run/{id}` is built by
> `_build_result()` in `backend/app/api/routes.py` (programme / taste_dna /
> cohorts / geography / programme_bet / test_card / evidence / city /
> data_status) and is typed for the frontend in `frontend/types/adjacent.ts`.
> The golden-path contract is enforced by `backend/tests/test_run_api_golden_path.py`.


> **Schema version:** 1.0.0
>
> This document defines the shape of the JSON payload the backend will serve to
> the frontend.  It is a *view* of `AdjacentState`, not a re-declaration of its
> vocabulary.

---

## 1. Top-level shape

```jsonc
{
  "schema_version": "1.0.0",
  "run_meta":     { /* RunMeta — provenance envelope */ },
  "programme":    { /* ProgrammeProfile — the input programme */ },
  "taste_profile": { /* TasteDNA — tag affinities from Qloo */ },
  "candidate_cohorts": [ /* CandidateCohort[] — ranked adjacent-entity groups */ ],
  "geography":    { /* GeographicEvidence — heatmap/rings (NOT YET IMPLEMENTED) */ },
  "programme_hypothesis": { /* ProgrammeHypothesis — bet + test card (NOT YET IMPLEMENTED) */ },
  "verdict":      "complete" | "insufficiency" | "error" | "budget_exhausted" | "invalid_input" | "timeout",
  "provenance":   { /* ProvenanceAudit — call counts by source */ }
}
```

## 2. RunMeta

| Field | Type | Description |
|---|---|---|
| `mode` | `"live" \| "mock"` | `"mock"` when data_status is fixture |
| `fixture` | `string?` | Fixture name if mock mode |
| `started_at` | `ISO-8601` | Run start time |
| `completed_at` | `ISO-8601` | Run end time |
| `stop_reason` | `string` | Why the agent stopped |
| `budget` | `{max_steps, max_calls, max_seconds}` | Budget limits |

## 3. ProgrammeProfile

| Field | Type | Description |
|---|---|---|
| `items` | `ProgrammeItemView[]` | Resolved programme items |

Each `ProgrammeItemView`:

| Field | Type | Description |
|---|---|---|
| `title` | `string` | Original title |
| `year` | `int?` | Release/production year |
| `imdb_id` | `string?` | IMDb ID if available |
| `entity_id` | `string?` | Qloo UUID (null if unresolved) |
| `entity_type` | `string?` | Qloo entity type URN |
| `resolved_name` | `string?` | Qloo's canonical name |
| `popularity` | `float?` | Qloo popularity score |
| `source` | `"live_qloo" \| "fixture" \| "unresolved"` | Resolution source |

## 4. TasteDNA

| Field | Type | Description |
|---|---|---|
| `tags` | `TasteSignal[]` | Scored tags from Qloo |
| `total_tags` | `int` | Tags returned |
| `scored_tags` | `int` | Tags with affinity |

Each `TasteSignal`:

| Field | Type | Description |
|---|---|---|
| `tag_id` | `string` | Qloo tag URN |
| `name` | `string?` | Human-readable name |
| `subtype` | `string?` | Tag subtype URN |
| `affinity` | `float` | 0–1 affinity score |
| `band` | `"very_high" \| "high" \| "medium" \| "low"` | Official affinity band |
| `popularity` | `float?` | Tag popularity |
| `source` | `"live_qloo" \| "fixture"` | Data source |

## 5. CandidateCohort

| Field | Type | Description |
|---|---|---|
| `domain` | `string` | Qloo filter.type URN |
| `members` | `CohortMemberView[]` | Scored cohort members |
| `member_count` | `int` | Total members returned |
| `query_affinity_range` | `{min, max}` | Affinity range in this cohort |

Each `CohortMemberView`:

| Field | Type | Description |
|---|---|---|
| `entity_id` | `string` | Qloo UUID |
| `name` | `string?` | Entity name |
| `affinity` | `float` | 0–1 affinity score |
| `band` | `string` | Official affinity band |
| `popularity` | `float?` | Entity popularity |
| `explainability` | `object?` | Per-signal attribution (when available) |
| `source` | `"live_qloo" \| "fixture"` | Data source |

### Explainability structure (LIVE QLOO OBSERVATION)

When `feature.explainability=true` is passed, each entity result includes:

```json
{
  "explainability": {
    "signal.interests.entities": [
      {"entity_id": "<input-uuid>", "attribution": 0.2718},
      {"entity_id": "<input-uuid>", "attribution": 0.2700}
    ]
  }
}
```

Attribution scores sum approximately to the entity's overall affinity.
Tags do NOT receive explainability data.

## 6. GeographicEvidence (NOT YET IMPLEMENTED)

Status: `not_implemented`.

Live Qloo heatmap data IS available:

| City | Cell count | Avg affinity |
|---|---|---|
| London, UK | 207 | 0.500 |
| New York, NY | 203 | 0.500 |
| Portland, Oregon | 19 | 0.500 |

Cell structure (from live Qloo):
```json
{
  "location": {"latitude": 51.55, "longitude": -0.126, "geohash": "gcpvm0"},
  "query": {"affinity": 1.0, "affinity_rank": 0.991, "popularity": 0.0}
}
```

## 7. ProgrammeHypothesis (NOT YET IMPLEMENTED)

Status: `not_implemented`.

## 8. ProvenanceAudit

| Field | Type | Description |
|---|---|---|
| `qloo_calls` | `int` | Real Qloo API calls |
| `fixture_calls` | `int` | Fixture/mock calls |
| `mock_calls` | `int` | Mock client calls |
| `error_calls` | `int` | Failed calls |
| `total_trace_rows` | `int` | Total trace entries |

---

## Example JSON

> **⚠️ MOCK DATA — NOT LIVE QLOO DATA**
>
> This example uses the real Qloo response structure observed in live testing
> (6 October 2026). The numbers are **synthetic placeholders**, NOT measured
> Qloo values. Do not treat any number here as a verified Qloo result.

```json
{
  "_label": "MOCK DATA — NOT LIVE QLOO DATA",
  "schema_version": "1.0.0",
  "run_meta": {
    "mode": "mock",
    "fixture": "portland_strong",
    "started_at": "2026-10-06T00:00:00Z",
    "completed_at": "2026-10-06T00:00:05Z",
    "stop_reason": "complete",
    "budget": {"max_steps": 14, "max_calls": 24, "max_seconds": 90}
  },
  "programme": {
    "items": [
      {
        "title": "Perfect Days",
        "year": 2023,
        "imdb_id": "tt7594358",
        "entity_id": "3ECAC26F-AC87-4E09-8A54-4B138B8596C6",
        "entity_type": "urn:entity:movie",
        "resolved_name": "Perfect Days",
        "popularity": 0.99,
        "source": "fixture"
      }
    ]
  },
  "taste_profile": {
    "tags": [
      {
        "tag_id": "urn:tag:cultural_relevance:qloo:sustainability",
        "name": "Sustainability",
        "subtype": "urn:tag:cultural_relevance:qloo",
        "affinity": 0.9998,
        "band": "very_high",
        "popularity": 0.995,
        "source": "fixture"
      }
    ],
    "total_tags": 50,
    "scored_tags": 50
  },
  "candidate_cohorts": [
    {
      "domain": "urn:entity:artist",
      "members": [
        {
          "entity_id": "FA295951-408A-4CAE-A399-776AB308D5FD",
          "name": "Nico",
          "affinity": 0.9373,
          "band": "very_high",
          "popularity": 0.994,
          "source": "fixture"
        }
      ],
      "member_count": 12,
      "query_affinity_range": {"min": 0.92, "max": 0.94}
    }
  ],
  "geography": {
    "status": "not_implemented",
    "_note": "Heatmap data available from Qloo but not yet wired into the product."
  },
  "programme_hypothesis": {
    "status": "not_implemented"
  },
  "verdict": "complete",
  "provenance": {
    "qloo_calls": 0,
    "fixture_calls": 13,
    "mock_calls": 0,
    "error_calls": 0,
    "total_trace_rows": 13
  }
}
```

---

## Key structural findings from live Qloo (6 October 2026)

These are **LIVE QLOO OBSERVATIONS**, not documentation assumptions:

1. **Affinity lives in `entity.query.affinity`**, not at the entity top level.
2. **Tag affinity lives in `tag.query.affinity`**, same nested pattern.
3. **Heatmap cells** are under `results.heatmap` (not `results.cells`).
4. **Heatmap coordinates** are nested: `cell.location.latitude`, `cell.location.longitude`.
5. **Heatmap locality** (`query.localities.filter`) is a **list** of locality objects, not a dict.
6. **filter.results.entities** works: all N supplied candidates returned and scored in one query. Verdict: **SAFE**.
7. **Explainability** works for entities: `entity.query.explainability.signal.interests.entities[]` with per-entity attribution scores.
8. **Explainability** does NOT work for tags (empty object returned).
9. **Entity resolution** via `/entities` returns a flat list under `results` (not `results.entities`).
10. **`filter.tags`** parameter is not supported on `/v2/tags` (silently ignored or returns error).