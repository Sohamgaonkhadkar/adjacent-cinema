# Architecture Audit — Code vs Research

> **Date:** 6 October 2026
> **Scope:** Compare the researched architecture (01–04, README, FEATURES_NOT_BUILDING) against the actual implementation in `backend/app/`.
> **Method:** Every classification is based on reading the actual code, not inferring from documentation.

---

## Classification Key

| Status | Meaning |
|---|---|
| IMPLEMENTED | Working in code, tested, used in live demo |
| PARTIALLY IMPLEMENTED | Core exists but missing components |
| PLANNED | Designed in architecture docs, not yet built |
| CONFLICTING | Code differs from architecture in a meaningful way |
| REQUIRES CHANGE | Architecture doc is wrong or code needs fixing |

---

## A. Frontend Boundary

**Architecture says:** Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui. MapLibre GL JS for heatmap. Recharts for bars.

**Code does:** No frontend exists. FastAPI serves `/health` only.

**Classification:** PLANNED

**Intentional?** Yes — Milestone 4 explicitly deferred frontend. The live core must be trustworthy first.

**Risk:** None — frontend is cleanly separated. The API contract is defined in `docs/FRONTEND_CONTRACT.md`.

**Correction needed:** None.

---

## B. FastAPI/API Boundary

**Architecture says:** Routes: `POST /run`, `GET /run/{id}/stream` (SSE), `POST /run/{id}/disambiguate`, `GET /run/{id}`, `GET /run/{id}/trace`, `GET /demo/{slug}`, `GET /demo/{slug}/canned`, `GET /health`.

**Code does:** Only `GET /health` exists. Returns `status`, `service`, `qloo_configured`, `mock_mode`, `mode`, `qloo_trusted_base_url`, `param_registry_size`, `unverified_param_count`, `evidence_thresholds`.

**Classification:** PARTIALLY IMPLEMENTED

**Intentional?** Yes — API routes require a run-store (PostgreSQL or in-memory), which is not yet built.

**Risk:** Low — the `/health` endpoint is correct and the run API is cleanly separable.

**Correction needed:** None for now. The run API should be implemented when the frontend arrives.

---

## C. Agent Orchestrator

**Architecture says:** Custom async state machine, ~350 lines. PLAN → SELECT → ACT → EVALUATE → STOP. MAX_QLOO_CALLS=24. Typed tools. No LangGraph.

**Code does:** `backend/app/agent/orchestrator.py` — 421 lines. Exactly the described loop. Five phases: INIT, PLAN, RESOLVE, ANALYSE, EXPAND, RANK, EVALUATE, STOP. Budget enforced before calls. Every transition recorded.

**Classification:** IMPLEMENTED

**Intentional?** Yes — matches the architecture exactly.

**Risk:** None.

**Difference from architecture:** The architecture mentions 7 phases (resolve → analyse → expand → rank → locate → decide → assemble). The implementation has 5 acting phases (RESOLVE, ANALYSE, EXPAND, RANK, EVALUATE) because locate (geography), decide (programme bet), and assemble (rendering) are not yet built. This is correct — the orchestrator should grow phases as tools are added.

**Correction needed:** None.

---

## D. Tool Boundary

**Architecture says:** 14 tools (T1–T14), one file each. A tool may call Qloo; it may not call another tool.

**Code does:** 5 tools implemented as classes in `backend/app/agent/tools.py`:
- `resolve_programme` → T2 (entity resolution)
- `get_taste_profile` → T3 (taste DNA)
- `expand_candidates` → T5 (cross-domain adjacency)
- `rank_cohorts` → T6 (single-context ranking)
- `assess_evidence` → T13 (evidence gate)

Tools are not in separate files — they're in one `tools.py`. The `PipelineRuntime` protocol abstracts the implementation.

**Classification:** PARTIALLY IMPLEMENTED

**Intentional?** Yes — T1 (resolve locality), T4 (demographic skew), T7 (cohort heatmap), T8 (audience lens), T9 (candidate additions), T10 (score programme), T11 (compare seasons), T12 (trend check), T14 (trace) are all deferred.

**Risk:** Low — the tool boundary is clean. Adding tools requires only implementing `PipelineRuntime` methods and adding phase transitions.

**Difference from architecture:** Tools are in one file, not separate files. This is actually better for the current codebase size — separate files would be mostly empty.

**Correction needed:** None. When T7+ are added, they can be split into separate files.

---

## E. Qloo Client Boundary

**Architecture says:** One client, one place. No `httpx` import outside `qloo/client.py`. Allowlisted parameters only. GET only. `X-Api-Key` header. 404 ≠ error. Every response → TraceRow.

**Code does:** `backend/app/qloo/client.py` — the only httpx caller. Parameter allowlist in `params.py`. GET-only enforced. `X-Api-Key` header. 404 raises `NotFoundError` (data outcome). Trace rows recorded via `trace.py`. Rate limiter in `_Limiter` class (token bucket, configurable RPS). Retry with exponential backoff on 429/5xx.

**Classification:** IMPLEMENTED

**Intentional?** Yes — matches architecture exactly.

**Risk:** None.

**Verification:** Confirmed by live testing — no httpx import exists outside `qloo/client.py`.

**Correction needed:** None.

---

## F. Entity Resolution

**Architecture says:** Primary path = `/entities` with external IMDb IDs. Fallback = `/search` with title. M1: "kills ~80% of entity-resolution risk — our unfair advantage".

**Code does:** **Reversed priority.** The resolver (`resolution/resolver.py`) uses `/search` as primary with title+year verification. `/entities` with external IDs is supplementary, only used if the external ID is confirmed in the response. This was forced by live testing: `/entities` with external IDs does NOT return the external IDs in the response, making it impossible to verify which input mapped to which entity.

**Classification:** CONFLICTING (with architecture research), but the code is CORRECT.

**The conflict:** The architecture says `/entities` with external IDs is the primary path and "kills ~80% of entity-resolution risk." Live testing proved this is UNSAFE — Qloo returns entities but doesn't include the external IDs in the response, so you can't verify which IMDb ID mapped to which entity.

**Why the code is correct:** `/search` with title+year verification provides verifiable identity. The resolver marks entities as VERIFIED only when title AND year match. This is safer than the architecture's assumption.

**Risk:** The architecture's claim about external IDs being the "unfair advantage" is partially invalidated. External IDs are still useful as a supplementary signal, but cannot be the primary resolution path.

**Correction needed:** Update the architecture to reflect `/search` as primary, `/entities` as supplementary. This is a LIVE QLOO OBSERVATION that supersedes the documentation-only assumption.

---

## G. Taste DNA

**Architecture says:** Tags + bands + URNs from `/v2/insights?filter.type=urn:tag`. Scores normalised per query.

**Code does:** Exactly this. `runner.py:_taste_profile()` calls `client.insights(filter_type="urn:tag", signal_interests_entities=ids, take=50)`. Tags carry `query.affinity` (nested, discovered during live testing). Bands computed from official thresholds.

**Classification:** IMPLEMENTED

**Intentional?** Yes.

**Risk:** None.

**Note:** The architecture mentions "demographic skew bars" (T4). This is not implemented — it would require `filter.type=urn:demographics` queries.

**Correction needed:** None.

---

## H. Cross-Domain Expansion

**Architecture says:** One call per domain via `/v2/insights?filter.type=urn:entity:X`. `backfill.*` can inject content-similarity filler that must be detected and labelled.

**Code does:** `runner.py:_expand_candidates()` iterates `DEFAULT_EXPANSION_DOMAINS` (artist, book, brand, movie, tv_show). One call per domain. `filter.popularity.min=0.05, filter.popularity.max=0.90` applied.

**Classification:** PARTIALLY IMPLEMENTED

**Intentional?** Expansion works. Backfill detection is NOT implemented.

**Risk:** Medium — if Qloo returns backfill results, they would be treated as affinity results. However, live testing shows the current results are genuine affinity matches.

**Correction needed:** Add backfill detection when `backfill.cross_domain.take` is used. Not needed for MVP if we don't use backfill parameters.

---

## I. Single-Context Cohort Ranking

**Architecture says:** All cross-candidate comparisons happen inside a single `filter.results.entities` query. Never compare scores across queries.

**Code does:** `domain/scoring.py:CohortRanker` groups candidates by domain, then issues ONE `filter.results.entities` call per domain (one scoring context). Cross-context ordering uses band strength, novelty proxy, and qualifying-member count — never raw affinity.

**Classification:** IMPLEMENTED

**Intentional?** Yes — this is Finding 1 from the architecture research, correctly implemented.

**Risk:** None.

**Verification:** Live testing confirmed `filter.results.entities` returns all supplied candidates with affinity scores in one query.

**Correction needed:** None.

---

## J. Evidence/Provenance

**Architecture says:** Three layers: inline (data-call-id attributes), attribution (explainability), export (Copy as JSON). Insufficiency distinct from errors. Every rendered number carries provenance.

**Code does:** `domain/ledger.py:ProvenanceLedger` tracks every displayed number with a call_id or source. `evidence.py` implements three gates (resolution, taste_profile, candidate_cohorts). Insufficiency is distinct from errors (budget_exhausted, error are never reported as insufficiency). Explainability data is available from Qloo but not yet connected to the provenance system.

**Classification:** PARTIALLY IMPLEMENTED

**Intentional?** The core provenance is implemented. Explainability attribution is captured in the resolver but not yet wired into the rendering.

**Risk:** Low — the foundation is solid. Connecting explainability to provenance is a matter of plumbing.

**Correction needed:** Connect `entity.query.explainability.signal.interests.entities[]` to the provenance system when building the UI.

---

## K. Geographic/Heatmap Layer

**Architecture says:** City heatmap with venue pin, distance rings, named concentration areas. MapLibre GL JS. `filter.type=urn:heatmap`.

**Code does:** Heatmap data is validated against live Qloo (London 207 cells, NY 203, Portland 19). The `parse_heatmap` function in `models.py` correctly handles the live response structure. But NO product layer exists — no venue pin, no distance rings, no named areas, no MapLibre.

**Classification:** PARTIALLY IMPLEMENTED (data layer only)

**Intentional?** Yes — geography was explicitly deferred until the live core is trustworthy.

**Risk:** Low — the data is available and the parser is correct.

**Correction needed:** Build the product layer (T7) when the frontend arrives.

---

## L. Programme Bet Decision Layer

**Architecture says:** Two-sided programme bet + runner-up + rejected list. Test Card with falsification condition.

**Code does:** Not implemented. The ranking system produces ranked cohorts with scores, but no "programme bet" decision is made.

**Classification:** PLANNED

**Intentional?** Yes — deferred until after live core validation.

**Risk:** Low — the ranking data is available to feed into a bet.

**Correction needed:** None for now.

---

## M. LLM Boundary

**Architecture says:** Hosted LLM for two narrow jobs: (a) parsing messy programme text, (b) rendering prose from ToolResult. LLM has no tool access. LLM MUST NOT produce Qloo entity IDs, affinity values, rankings, geographic claims, evidence, cohort scores, or programme decisions.

**Code does:** No LLM integration exists. The CLI accepts structured JSON input (title, year, imdb_id), not free text.

**Classification:** PLANNED

**Intentional?** Yes — LLM was explicitly deferred.

**Risk:** None — the architecture is designed for LLM-at-edges. Adding LLM extraction requires only one new module (`llm/extract.py`) and the intake API route.

**Correction needed:** None.

---

## N. PostgreSQL Persistence

**Architecture says:** PostgreSQL 16 + psycopg (no ORM). Tables: runs, qloo_cache, saved_runs.

**Code does:** No database. All state is in-memory during a run.

**Classification:** PLANNED

**Intentional?** Yes — persistence was deferred.

**Risk:** Low — the state model (`AdjacentState`) is already serialisable (has `to_json()`).

**Correction needed:** None.

---

## O. PostgreSQL-Backed Cache

**Architecture says:** Postgres table with TTL. Key = sha256(method + path + sorted(params)). TTLs: /entities 7d, /search 24h, /v2/insights 12h, heatmap 6h, /v2/tags 7d.

**Code does:** No cache. Every call goes to the live API.

**Classification:** PLANNED

**Intentional?** Yes — cache was deferred.

**Risk:** Low — the cache key format is defined, and the trace system already records cache status (always "bypass" currently).

**Correction needed:** None.

---

## P. SSE/Live Trace

**Architecture says:** `GET /run/{id}/stream` — SSE with event types: trace, resolution, taste_dna, cohort, heatmap, bet, test_card, insufficiency, done.

**Code does:** No SSE. The CLI renders the full output after the run completes.

**Classification:** PLANNED

**Intentional?** Yes — SSE requires a run-store and frontend.

**Risk:** Low — the orchestrator already records every transition, making SSE emission straightforward.

**Correction needed:** None.

---

## Q. Retry/Rate-Limit/Budget Handling

**Architecture says:** Token bucket at 3 rps. Burst cap 5. 429: honour Retry-After, else exponential backoff 1s/2s/4s + jitter, max 3 attempts. MAX_QLOO_CALLS=24, checked BEFORE every call.

**Code does:** `_Limiter` class (token bucket, configurable RPS). Retry in `_get()` with exponential backoff on 429/5xx. Budget enforced via `budget.ensure()` before calls. Budget: 14 steps, 24 calls, 90s.

**Classification:** IMPLEMENTED

**Intentional?** Yes.

**Risk:** None.

**Difference:** The architecture says "burst cap 5" — the implementation uses a simple token bucket without explicit burst cap. This is acceptable for the hackathon.

**Correction needed:** None.

---

## R. Observability

**Architecture says:** Structured JSON logs to stdout + a `runs` table + on-screen trace rail.

**Code does:** Trace rows recorded per call. `AdjacentState.transitions` records every orchestrator transition. `ProvenanceLedger` tracks every displayed number. No structured logging to stdout (no `logging` module usage). No `runs` table.

**Classification:** PARTIALLY IMPLEMENTED

**Intentional?** Core tracing is implemented. Structured logging and persistence are deferred.

**Risk:** Low — the trace data is available; emitting it as structured logs is trivial.

**Correction needed:** Add structured JSON logging when the deployment phase begins.

---

## S. Deployment Topology

**Architecture says:** Frontend on Vercel, Backend on Fly.io (single small machine, always-on), Database on Fly Postgres or Neon.

**Code does:** No deployment. Runs locally via `make demo-live`.

**Classification:** PLANNED

**Intentional?** Yes — deployment is a Phase-9 task.

**Risk:** None.

**Correction needed:** None.

---

## T. Failure/Degradation Semantics

**Architecture says:** AuthError → fail loudly. NotFound → data outcome. RateLimited → backoff then partial. Timeout → retry once, then degrade that tool only. UpstreamError → retry, then degrade. UnverifiedParameter → bug. Nothing is ever substituted.

**Code does:** `qloo/errors.py` defines error classes. `runner.py` catches `NotFoundError` (data outcome), `QlooError` (degrades that domain/tool). `BudgetExhausted` stops the run. UnverifiedParameter raises before the request. No silent substitution.

**Classification:** IMPLEMENTED

**Intentional?** Yes — matches architecture exactly.

**Risk:** None.

**Correction needed:** None.

---

## Summary Table

| Component | Architecture | Code | Status |
|---|---|---|---|
| A. Frontend | Next.js + MapLibre | Not built | PLANNED |
| B. API boundary | 8 routes | /health only | PARTIALLY IMPLEMENTED |
| C. Agent orchestrator | Custom async FSM | Custom async FSM | IMPLEMENTED |
| D. Tool boundary | 14 tools | 5 tools | PARTIALLY IMPLEMENTED |
| E. Qloo client | One client, allowlisted | One client, allowlisted | IMPLEMENTED |
| F. Entity resolution | /entities primary | /search primary | CONFLICTING (code is correct) |
| G. Taste DNA | Tags + bands | Tags + bands | IMPLEMENTED |
| H. Cross-domain | One call/domain | One call/domain | PARTIALLY IMPLEMENTED |
| I. Cohort ranking | Single-context | Single-context | IMPLEMENTED |
| J. Evidence/provenance | Three layers | Core layer | PARTIALLY IMPLEMENTED |
| K. Geography | Heatmap + MapLibre | Data validated | PARTIALLY IMPLEMENTED |
| L. Programme Bet | Two-sided bet | Not built | PLANNED |
| M. LLM | At edges only | Not built | PLANNED |
| N. PostgreSQL | 4 tables | Not built | PLANNED |
| O. Cache | Postgres TTL | Not built | PLANNED |
| P. SSE | Live trace | Not built | PLANNED |
| Q. Retry/budget | Token bucket + backoff | Token bucket + backoff | IMPLEMENTED |
| R. Observability | JSON logs + trace | Trace only | PARTIALLY IMPLEMENTED |
| S. Deployment | Vercel + Fly.io | Local only | PLANNED |
| T. Failure semantics | Error taxonomy | Error taxonomy | IMPLEMENTED |

---

## Critical Finding: Entity Resolution Conflict

The architecture research claimed `/entities` with external IMDb IDs "kills ~80% of entity-resolution risk" and should be the primary resolution path. **Live testing proved this is unsafe.**

**Evidence:** When `/entities` is called with `external.imdb.ids`, the returned entities do NOT include the external IDs in their `external` field. This makes it impossible to verify which input IMDb ID mapped to which returned entity. In our test, "Taipei Story" (tt0089853) may have mapped to "The Purple Rose of Cairo" — a wrong film.

**Resolution:** The implementation correctly uses `/search` with title+year verification as the primary path. This is a LIVE QLOO OBSERVATION that supersedes the documentation-only assumption. The architecture must be updated.

**Impact on other claims:** The architecture's claim that external IDs are Adjacent's "unfair advantage" is partially invalidated. External IDs are still useful as a supplementary verification signal, but the primary resolution path must be `/search` with title+year matching.