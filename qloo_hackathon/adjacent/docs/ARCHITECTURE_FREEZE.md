# Adjacent — Architecture Freeze

> **Historical design snapshot:** 6 October 2026.
> **Status:** historical baseline; its deployment, rate-limit, and implementation claims are superseded by [`FINALIZATION_STATUS.md`](FINALIZATION_STATUS.md) and the live contract in [`FRONTEND_CONTRACT.md`](FRONTEND_CONTRACT.md), updated 16 October 2026.
> **Authority:** use this document for the original architecture rationale, not as evidence of current deployment or runtime behavior. Creator Mode is now the primary demo surface; Cinema Mode remains preserved.

---

## A. Product Boundary

**Adjacent** is a programme-level audience-development tool for independent/arthouse cinemas. It discovers culturally aligned audience hypotheses *outside* the existing audience, using Qloo as the sole cultural evidence source.

**What it produces:**
1. Taste DNA — tag affinities characterising the programme's cultural profile
2. Ranked adjacent cohorts — cross-domain entities ranked by affinity in a single normalisation context
3. Geographic heatmap — where the programme's audience concentrates (London, New York, Portland)
4. Programme Bet — a testable programming hypothesis with a falsification condition
5. Evidence Panel — full provenance for every rendered number
6. Test Card — printable one-pager with the bet and evidence

**What it does NOT produce:**
- Individual audience profiling or PII
- Attendance or conversion claims
- Invented Qloo scores or fabricated data
- Recommendations based on anything other than Qloo evidence

---

## B. System Context Diagram

```
┌─────────────────────────────────────────────────┐
│  Cinema Programmer (user)                       │
│  - Pastes programme (titles + IMDb IDs)         │
│  - Selects city                                 │
│  - Reviews outputs 1–6                          │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  Next.js UI (Vercel)                             │
│  - Intake form                                   │
│  - Live SSE trace                                │
│  - Output cards (Taste DNA, cohorts, map, bet)   │
│  - Evidence panel                                │
└──────────────────────┬───────────────────────────┘
                       │ JSON + SSE
                       ▼
┌──────────────────────────────────────────────────┐
│  FastAPI Backend (Fly.io)                        │
│  - Explicit agent orchestrator                   │
│  - Typed tools                                   │
│  - Trusted entity resolver                       │
│  - Deterministic domain engine                   │
│  - Evidence + provenance                         │
└──────────────────────┬───────────────────────────┘
                       │ X-Api-Key (GET only)
                       ▼
┌──────────────────────────────────────────────────┐
│  Qloo Hackathon API                              │
│  https://hackathon.api.qloo.com                  │
│  /search /entities /v2/insights /v2/tags         │
│  /v2/audiences /v2/analysis/compare /v2/trending │
└──────────────────────────────────────────────────┘
```

---

## C. Container-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  FastAPI (backend/app/)                                      │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ API      │  │ Agent    │  │ Domain   │  │ Qloo     │   │
│  │ Routes   │→ │ Orch.    │→ │ Engine   │→ │ Client   │   │
│  │ /health  │  │ FSM      │  │ scoring  │  │ models   │   │
│  │ /run     │  │ budget   │  │ cohorts  │  │ params   │   │
│  │ /demo    │  │ tools    │  │ evidence │  │ trace    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │Resolution│  │ LLM      │  │ DB       │                  │
│  │ /search  │  │ extract  │  │ runs     │                  │
│  │ VERIFIED │  │ narrate  │  │ cache    │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

---

## D. Backend Module Boundaries

| Module | Path | Responsibility | External Dependencies |
|---|---|---|---|
| API | `app/main.py`, `app/api/` | HTTP routes, CORS, request validation | FastAPI |
| Agent | `app/agent/` | Orchestrator, budget, state machine, stop conditions | None |
| Tools | `app/agent/tools.py` | Typed tool interface, PipelineRuntime protocol | None |
| Domain | `app/domain/` | Scoring, cohorts, evidence, ledger, rejection reasons | None |
| Qloo | `app/qloo/` | HTTP client, params allowlist, models, trace, mock | httpx |
| Resolution | `app/resolution/` | Entity resolver, match contract | None |
| Runner | `app/runner.py`, `app/live_runner.py` | Pipeline implementations (mock + live) | Agent, Domain, Qloo |
| Evidence | `app/evidence.py` | Evidence gate functions | None |
| Config | `app/config.py` | Settings from env, mode detection | None |
| LLM | `app/llm/` (future) | Text extraction, prose narration | Hosted LLM |
| DB | `app/db/` (future) | Runs table, cache, saved runs | psycopg, PostgreSQL |

**Key boundary rules:**
1. No `httpx` import outside `qloo/client.py`
2. No domain logic in the agent orchestrator
3. No direct Qloo calls from domain code
4. Tools are the only bridge between agent and implementation
5. Resolution produces `ResolvedEntity` — downstream code never re-resolves

---

## E. Agent State Machine

```
INIT → PLAN → RESOLVE → EVALUATE
                  ↓
              ANALYSE → EVALUATE
                  ↓
              EXPAND → EVALUATE
                  ↓
              RANK → EVALUATE
                  ↓
              STOP
```

**Phases:**
- INIT: validate input, seed programme items
- PLAN: decide next phase (deterministic, no LLM)
- RESOLVE: trusted entity resolution via /search
- ANALYSE: taste DNA via /v2/insights (urn:tag)
- EXPAND: cross-domain candidates via /v2/insights (urn:entity:X)
- RANK: single-context cohort ranking via filter.results.entities
- EVALUATE: evidence gate after each phase
- STOP: final decision (complete/insufficiency/budget_exhausted/error/invalid_input/timeout)

**Budget:** 14 steps, 24 Qloo calls, 90 seconds. Checked BEFORE every call.

**Future phases (not yet implemented):**
- LOCATE: geographic heatmap
- DECIDE: programme bet
- ASSEMBLE: final output rendering

---

## F. Qloo Integration Boundary

**Client:** `backend/app/qloo/client.py` — the ONLY httpx caller.

**Endpoints used:**
| Endpoint | Tool | Purpose |
|---|---|---|
| `GET /search` | resolve_programme | Entity resolution (primary) |
| `GET /entities` | resolve_programme | Entity resolution (supplementary) |
| `GET /v2/insights` | get_taste_profile | Taste DNA (urn:tag) |
| `GET /v2/insights` | expand_candidates | Cross-domain adjacency |
| `GET /v2/insights` | rank_cohorts | Single-context scoring |
| `GET /v2/insights` | (future) | Heatmap (urn:heatmap) |
| `GET /v2/audiences` | (future) | Audience catalogue |
| `GET /v2/tags` | (future) | Tag search |

**Rules:**
1. Allowlisted parameters only (`params.py`)
2. GET only (POST rejected)
3. `X-Api-Key` header (never Bearer, never query-param)
4. 404 = data outcome (not an error)
5. Every response → TraceRow
6. Rate limit: token bucket, configurable RPS
7. Retry: exponential backoff on 429/5xx, max 3 attempts
8. Backfill detection: mandatory when `backfill.*` parameters are used

**Response parsing (models.py):**
- Affinity in `entity.query.affinity` (nested, not top-level)
- Heatmap cells in `results.heatmap` (not `results.cells`)
- Coordinates in `cell.location.{latitude, longitude}`
- Locality in `query.localities.filter` (list, not dict)
- Explainability in `entity.query.explainability.signal.interests.entities[]`

---

## G. Data/Provenance Flow

```
Input Programme
  → Entity Resolution (/search, VERIFIED only)
    → Taste DNA (/v2/insights, urn:tag)
      → Cross-Domain (/v2/insights, urn:entity:X per domain)
        → Cohort Construction (domain logic)
          → Single-Context Ranking (filter.results.entities)
            → Evidence Gate (resolution + taste + cohorts)
              → Stop Decision
```

**Provenance rules:**
1. Every displayed number carries a call_id or source
2. `ProvenanceLedger` tracks every number with its backing evidence
3. Numbers without backing are flagged as "unverified"
4. Fixture data carries `data_status="fixture"`, never confused with measured data
5. The evidence panel can trace any number back to the exact Qloo response

---

## H. LLM Boundary

**Scope:** Two narrow jobs only:
1. **Extraction:** messy programme text → structured `ParsedTitle[]`
2. **Narration:** typed `ToolResult` → human-readable prose

**Hard rules:**
- LLM has NO tool access — cannot call Qloo, cannot modify state
- LLM MUST NOT produce: entity IDs, affinity values, rankings, geographic claims, evidence, cohort scores, programme decisions
- LLM output is schema-validated before use
- Empty-state guard: every narration function returns empty string if input is empty
- The LLM is a text transformer at the edges, not a decision-maker

**Implementation:** `app/llm/extract.py` and `app/llm/narrate.py` (not yet built).

---

## I. Persistence/Cache Design

**Database:** PostgreSQL 16 + psycopg (no ORM).

**Tables:**
1. `runs` — completed run records (id, slug, created_at, state JSON, outputs)
2. `qloo_cache` — response cache (key, response, created_at, ttl, endpoint_class)
3. `saved_runs` — user-saved runs for sharing

**Cache strategy:**
- Key = `sha256(method + path + sorted(params))`
- TTLs: /entities 7d, /search 24h, /v2/insights 12h, heatmap 6h, /v2/tags 7d
- Cache hits visible in the trace
- Demo fixtures pre-warmed before recording

**Not Redis:** One fewer service. Cache is inspectable in the UI.

---

## J. API/SSE Boundary

**Routes:**
| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Liveness + config |
| POST | `/run` | Create a run from intake payload |
| GET | `/run/{id}/stream` | SSE — trace events + artefacts |
| POST | `/run/{id}/disambiguate` | Submit ambiguity answers |
| GET | `/run/{id}` | Full run JSON |
| GET | `/run/{id}/trace` | Trace rows |
| GET | `/demo/{slug}` | Pre-verified fixture season |
| GET | `/demo/{slug}/canned` | Recorded complete run |

**SSE event types:** trace, resolution, taste_dna, cohort, heatmap, bet, test_card, insufficiency, done.

---

## K. Failure/Retry/Degradation Model

| Situation | Behaviour |
|---|---|
| AuthError (401) | Fail loudly, never degrade silently |
| NotFound (404) | Data outcome — entity not in Qloo |
| RateLimited (429) | Exponential backoff + jitter, max 3 attempts |
| Timeout | Retry once, then degrade that tool only |
| UpstreamError (5xx) | Retry, then degrade |
| UnverifiedParameter | Bug — fail in dev, log in prod |
| Budget exhausted | Stop run, report partial results |
| Tool failure | Produce `Unavailable` result, dependent outputs show empty state |

**Never substitute.** A failed tool produces an empty state, not a guess.

---

## L. Security/Secrets Model

| Item | Rule |
|---|---|
| Key storage | `QLOO_API_KEY` env var only. `.env` gitignored |
| Proxy | Browser never talks to Qloo — all calls through FastAPI |
| Logs | Key redacted in every log line |
| Traces | `Settings.redacted()` prints `***set***`, never the key |
| Fingerprint | `sha256:<first-12-hex>·len=<n>` — sufficient for identity |
| Public runs | Share only outputs, never raw params |
| User data | No email, no name, no individual record |
| Rate limit | Per-IP cap of 10 runs/hour on public deployment |
| Prompt injection | LLM has no tool access — injection cannot produce a Qloo claim |

---

## M. Deployment Topology

| Component | Host | Notes |
|---|---|---|
| Frontend | Vercel | Next.js App Router, edge functions |
| Backend | Fly.io | Single small machine, always-on (no cold starts for SSE) |
| Database | Fly Postgres or Neon | Free tier sufficient |
| Domain | adjacent.<tld> | Optional; Vercel URL fine for Devpost |

---

## N. Testing Strategy

| Layer | Mechanism |
|---|---|
| Unit tests | pytest + typed assertions |
| Integration | MockQlooClient with fixture replay |
| Live validation | `make probe-live` against real Qloo |
| Architecture boundary | `test_resolution.py` (resolver safety), `test_live_contract.py` (live contracts) |
| Golden run | Every rendered number exists in a fixture |
| CI | `make ci` = ruff + pytest |

---

## O. Explicit Non-Goals

1. Individual audience profiling or PII collection
2. Attendance or conversion prediction
3. Movie/music/restaurant recommendation (generic)
4. Multiple Qloo clients or duplicate HTTP layers
5. LangGraph or other agent framework
6. LLM-controlled scoring or ranking
7. Real-time bidding or ad-tech integration
8. Multi-tenant SaaS (single-venue focus for MVP)

---

## P. Rejected Architectural Alternatives

| Alternative | Why Rejected |
|---|---|
| LangGraph | Adds dependency, obscures trace, makes agent decisions less legible. Judging criterion: "Does the code reflect genuine effort… and avoid wrappers?" |
| Redis cache | One more service to deploy. Postgres cache is inspectable. Worthwhile only past ~5 rps. |
| ORM (SQLAlchemy) | 4 tables, handful of queries. ORM is overhead; raw SQL is auditable. |
| Microservices | Single backend is simpler, faster to build, easier to demo. |
| LLM-controlled scoring | LLM must not produce numbers that affect decisions. Deterministic engine is auditable. |
| Multiple cultural evidence sources | Qloo is the hackathon requirement. No other API provides the same cultural graph. |
| Individual-level prediction | Programme-level analysis is the honest scope. Individual prediction requires data we don't have. |
| /entities with external IDs as primary resolution | LIVE TESTING proved this is unsafe — Qloo doesn't return external IDs in the response, making verification impossible. /search with title+year is the correct primary path. |

---

## Q. Conditions Under Which Architecture May Be Revisited

1. **Qloo changes their /entities response to include external IDs** → could restore external-ID-first resolution
2. **Qloo's hackathon API becomes unreliable** → need cached fallback or demo mode
3. **Rate limits become severe** → need aggressive caching or request batching
4. **The hackathon deadline moves** → may need to cut scope further
5. **A competitor discovers a Qloo capability we missed** → may need to incorporate it
6. **PostgreSQL proves unnecessary for the demo** → could defer further
7. **The LLM extraction proves unreliable** → may need to accept only structured input

**Do NOT revisit:**
- Custom orchestrator vs LangGraph (judging criterion)
- Single-context ranking (per-query normalisation makes cross-query comparison invalid)
- Qloo as sole evidence source (hackathon requirement)
- Programme-level analysis (honest scope)
- Deterministic scoring (auditability requirement)