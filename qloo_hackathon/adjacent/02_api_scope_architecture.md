# Adjacent — Product Definition & Execution Plan
### Parts 5–8 · API fit, scope, architecture, data

---

# PART 5 — API-FIT VERIFICATION (CURRENT OFFICIAL DOCS)

**Every row below was re-read from official documentation on 4 October 2026.** "VERIFIED?" means the named parameter/endpoint was found on the official page cited. Absence of verification is marked ⚠️ and listed as a question for `#api-help`. The standing rule: **never assume a parameter works because it sounds logical.**

## 5.1 Endpoint / capability table

| FEATURE | QLOO ENDPOINT | REQUIRED PARAMS | VERIFIED? | LIMITATIONS | HOW WE USE IT |
|---|---|---|---|---|---|
| **Entity name → entity** | `GET /search` | `query` | ✅ [`/reference/get-search`](https://docs.qloo.com/reference/get-search) | Fuzzy; needs `types` or it searches everything; ambiguous on remakes | Resolution fallback when no external ID |
| **Entity ID → entity (batch)** | `GET /entities` | `entity_ids` (UUID array) **or** `external.*.ids` | ✅ [`/reference/get-entities`](https://docs.qloo.com/reference/get-entities) | Returns **404 when nothing matches**; 429 on rate limit; not under `/v2` | **Primary** resolution path via IMDb/Rotten Tomatoes IDs |
| **External-ID resolution** | `GET /entities?external.imdb.ids=` | `external.imdb.ids` (plus rottentomatoes, isbn10/13, goodreads, library_of_congress, musicbrainz, spotify, wikidata, lastfm, michelin, resy, tablet, twitch, twitter, instagram, facebook, itunes, metacritic, igdb, soundcloud) | ✅ same page | Not every entity in Qloo has an external ID; 404 must surface as "not in Qloo" | Kills ~80% of entity-resolution risk — **our unfair advantage** |
| **Taste DNA (tags)** | `GET /v2/insights` | `filter.type=urn:tag` · `signal.interests.entities` | ✅ [`/reference/taste-analysis`](https://docs.qloo.com/reference/taste-analysis) | Scores normalised per query; verbose response | Output 1 |
| **Cross-domain adjacency** | `GET /v2/insights` | `filter.type=urn:entity:X` · `signal.interests.entities` | ✅ [`/reference/insights-api-deep-dive`](https://docs.qloo.com/reference/insights-api-deep-dive) | One domain per call; `backfill.*` can inject content-similarity filler | T5, the candidate generator |
| **Cohort ranking** | `GET /v2/insights` | `filter.type=urn:entity:X` · `signal.interests.entities` · **`filter.results.entities`** | ✅ `filter.results.entities` listed for artist, book, brand, movie, person, place, podcast, tv_show, video_game | ≤50 `take`; results filtered to the supplied set | **T6 — the single-normalisation ranking (Finding 1)** |
| **Popularity filtering** | `GET /v2/insights` | `filter.popularity.min` / `.max` (0–1) | ✅ same pages | Not on every type (documented for the nine above) | The novelty axis; keeps the canon out |
| **Exclude already-played** | `GET /v2/insights` | `filter.exclude.entities` | ✅ Deep Dive parameter list | — | Prevents recommending what the venue just showed |
| **Explainability** | `GET /v2/insights?feature.explainability=true` | — | ✅ Deep Dive | **Payload size unverified** (top_brands/top_interests/measurements per recommendation) | Provenance per claim |
| **Semantic tag search** | `GET /v2/tags` | `filter.query` | ✅ [`/reference/search-tags`](https://docs.qloo.com/reference/search-tags) — `feature.semantic_search` marked **beta** | Beta; may change | Resolving loose phrases like "slow observational documentary" |
| **Tag grading** | `GET /v2/tags` | `filter.results.tags` | ✅ same page | — | Validating that a taste tag is real before we name it in prose |
| **Audience catalogue** | `GET /v2/audiences` | `filter.parents.types` (10 categories) | ✅ [`/reference/get-audiences`](https://docs.qloo.com/reference/get-audiences) | **It is a lookup, not a ranker** (Finding 2); concrete URNs not enumerated in docs | T8 enumeration |
| **Audience as signal** | `GET /v2/insights` | `signal.demographics.audiences` | ✅ Entity Type Parameter Guide + demographics use case | Multiple audiences **merge into one combined profile** | T8 testing; heats style cohorts |
| **Audience as `filter.type`** | — | — | ❌ **DEPRECATED** | "Should not be used for new integrations" | **Do not use** |
| **Demographics** | `GET /v2/insights` | `filter.type=urn:demographics` · `signal.interests.entities` | ✅ [`/reference/demographics-use-case`](https://docs.qloo.com/reference/demographics-use-case) | Signed values; "including demographic data may lower the final score" | Output 1 skew bars |
| **Heatmap (geography)** | `GET /v2/insights` | `filter.type=urn:heatmap` · `filter.location.query` | ✅ [`/reference/heatmaps-use-case`](https://docs.qloo.com/reference/heatmaps-use-case) | City-level; needs a resolved signal; `output.heatmap.boundary` default geohash | **Output 3 — the wow** |
| **Heatmap + audience** | `GET /v2/insights` | `signal.demographics.audiences` on heatmap | ✅ Parameter Guide, Heatmap section | Unverified in practice | T7 secondary path (Finding 3) |
| **Heatmap boundary control** | `GET /v2/insights` | `filter.location.radius=0` · `output.heatmap.boundary` | ✅ heatmaps page | `radius` is in **miles**, not km | Honest "within the city" claims |
| **Geography on a normal query** | `GET /v2/insights` | `filter.location.query` on artist/book/brand/movie/person/place/tv_show | ✅ Parameter Guide | ⚠️ Whether it materiality changes artist results is unverified | Optional locality-bias on candidate generation |
| **Season comparison** | `GET /v2/analysis/compare` | `a.signal.interests.entities` **and** `b.signal.interests.entities` | ✅ [`/reference/analysis-compare`](https://docs.qloo.com/reference/analysis-compare) | **No demographic signal** — compares entity groups, not audiences. Corrects our earlier report | T11 (V1) |
| **Trend / durability** | `GET /v2/trending` | `filter.type` · **`filter.start_date`** · **`filter.end_date`** | ✅ [`/reference/get-trending`](https://docs.qloo.com/reference/get-trending) | **Both dates required**; not a no-arg "what's hot" call | T12 (V1) |
| **Diversification** | `GET /v2/insights` | `diversify.by=urn:tag:genre\|urn:tag:keyword` (≤1 value) | ✅ Deep Dive | One value only (community fork documents more; docs say one) | Widen across genres when candidates cluster |
| **Backfill** | `GET /v2/insights` | `backfill.cross_domain.take` (≤20) · `backfill.content_based.take` (≤10) | ✅ Deep Dive | **Appends filler below primary results** — must be detected and labelled | Detected in T5 and flagged in the UI |
| **Pagination** | all list endpoints | `page` (1–100) · `take` (≤50) | ✅ | — | Never needed for MVP |
| **Typo tolerance** | `/search`, `/v2/tags` | `feature.typo_tolerance` | ✅ | — | Free robustness on messy pastes |
| **Auth** | all | header **`X-Api-Key`** on `https://hackathon.api.qloo.com` | ✅ developer guide | Bearer and query-param keys **fail**; staging/prod hosts **401 the hackathon key** | The one thing to get right on day one |

## 5.2 Parameters we must NOT use, and why

| Parameter | Status | Reason |
|---|---|---|
| `urn:entity:audience` as `filter.type` | **Deprecated** | Docs: should not be used for new integrations |
| `/recommendations`, `/recs` | **Unsupported** | Legacy paths; design against `/v2/insights` |
| `recos.by.*` | **Staging only** | Not available on the hackathon key |
| `filter.parents.types=<entity type>` | **Silently wrong** | Takes **audience category URNs**; passing `urn:entity:book` returns empty, not an error |
| POST with a JSON body to `/v2/insights` | **Rejected** | Despite POST-only params being documented; use GET with query params |
| Multiple `signal.demographics.audiences` expecting separate result sets | **Misuse** | They merge into one combined profile |
| Comparing affinity scores across separate queries | **Invalid** | Per-query normalisation (Finding 1) |

## 5.3 Edge cases and failure semantics

| Situation | Correct behaviour | Wrong behaviour (which peers do) |
|---|---|---|
| `/entities` returns **404** | "Not in Qloo" — count it, exclude it, show it | Crash, or silently drop the title |
| `/v2/insights` returns **200 with empty `results`** | Show the empty state; name the query that returned nothing | Treat as "no data available" for the whole city |
| **429** | Exponential backoff with jitter, 3 attempts, then surface the partial result | Retry-storm, or fail the run |
| Invalid parameter **silently ignored** | Because we cannot detect it, we **assert on verified parameter names** in test fixtures | Trust that a plausible parameter worked |
| **Backfill present** | Label it: `2 of 12 candidates are content-similarity backfill, not affinity` | Present filler as affinity — the most common quiet error in this cycle |
| Ambiguous title | Ask, once, in a batch | Guess — "…some cannot be found; they are flagged, never guessed" is one peer's honest workaround; asking is strictly better |
| City not matched | Stop and ask | Fall back to a default city |

## 5.4 Open documentation questions → post in `#api-help` on day one

1. **Concrete `urn:audience:*` values** — the docs list only 10 parent categories. How many audiences exist, and at what granularity? None are enumerated anywhere.
2. **Valid `feature.explainability` payload size** for a `take=50` movie query — does it blow up the response?
3. **Is `feature.explainability` exposed on the hackathon key** at all? Are `analysis/compare`, `diversify.by`, and `heatmap.dimensions` exposed?
4. **Rate limit** — the exact ceiling. One peer measured ~1 rejection per 6 rapid calls.
5. **`signal.location.query`** — does it actually change results for `urn:entity:artist`, or is it a no-op filter?
6. **Heatmap with tag-only signals** — a peer reports food/activity tags yield no affinity while music tags do. Is tag-only heatmap supported in principle?
7. **`take` vs `filter.results.entities` interaction** — if we send 50 result entities with `take=50`, do all 50 come back scored, or only the top subset?
8. **`filter.popularity` semantics** — is it a percentile of Qloo's user base, or of the entity type's population? This changes how we explain the novelty score to users.
9. **Coverage in mid-size metros** — how many heatmap cells are returned for a city of ~600k (e.g. Portland, Maine; Leeds, UK)? Determines whether the map is a wow or a smear.
10. **`urn:entity:movie` subtype taxonomy** — what subtypes exist? We need this to distinguish a feature from a documentary from a concert film.

---

# PART 6 — MVP, V1, V2, AND WHAT WE WILL NOT BUILD

Scoring key: **Qloo dep** = how much the feature needs Qloo (● essential / ◐ helpful / ○ none). **Demo** = importance to the 3-minute video (★★★ / ★★ / ★).

## 6.1 MVP — build this, nothing else

**Definition of MVP: a working end-to-end run for one real cinema that produces Outputs 1–6, live, on real Qloo data, in under 60 seconds.**

| # | Feature | User value | Effort | Qloo dep | Demo |
|---|---|---|---|---|---|
| **M1** | Free-text programme intake + IMDb-ID-aware parsing | Zero data entry — the reason anyone will use it at all | 0.5 d | ○ | ★ |
| **M2** | Entity resolution with **visible** success/ambiguity/failure and a one-shot disambiguation question | Trust; proves grounding; kills the #1 demo failure | 1.0 d | ● | ★★ |
| **M3** | Taste DNA — tags + bands + URNs | The interpretable middle layer | 0.5 d | ● | ★★ |
| **M4** | Cohort discovery across ≥3 domains with explained domain choice | The discovery itself | 1.0 d | ● | ★★★ |
| **M5** | Single-query cohort ranking + rejection of weak cohorts | The agentic judgement; correctness | 0.5 d | ● | ★★★ |
| **M6** | City heatmap with venue pin, distance rings, named concentration areas | The action-able artefact; the wow | 1.0 d | ● | ★★★ |
| **M7** | Two-sided programme bet + runner-up + rejected list | The decision | 0.75 d | ● | ★★★ |
| **M8** | Test Card with falsification condition | Closes the loop; the honesty differentiator | 0.5 d | ◐ | ★★ |
| **M9** | Evidence panel + full call trace + Copy as JSON | Technological-implementation evidence | 0.75 d | ◐ | ★★ |
| **M10** | Insufficiency + empty states everywhere | The most-differentiated behaviour; cheap to build | 0.5 d | ○ | ★★ |
| **M11** | Demo mode: 3 pre-verified real seasons, cached responses for the first 30 seconds | Removes all video risk | 0.5 d | ○ | ★★★ |
| **M12** | Hard call budget + stop reason + backoff | Prevents the rate-limit demo death | 0.25 d | ◐ | ★ |

**MVP total ≈ 8 days of focused work.** That is the whole scope.

## 6.2 V1 — only after the MVP is deployed and the video is recorded

| Feature | Value | Effort | Qloo dep | Notes |
|---|---|---|---|---|
| Audience-lens layer (`/v2/audiences`) | Second cohort vocabulary | 1 d | ● | ⚠️ Verify catalogue richness first |
| Season comparison (`analysis/compare`) | "Does this change who we are?" | 0.5 d | ● | Entity groups only |
| Trend durability (`/v2/trending`) | Avoid saturated titles | 0.5 d | ● | 2 calls per run |
| Shareable read-only run link | Funders, colleagues, judges | 0.5 d | ○ | Persist run JSON |
| Funding-ready PDF export | The £79m capital case | 0.75 d | ○ | Print CSS |
| Performing-arts preset (artist entity types) | Second sector, same engine | 1 d | ● | Reuses everything |
| Multi-city comparison | Touring / festival use | 0.5 d | ● | Re-run T7 per city |

## 6.3 V2 — future, and only if it's a real product

| Feature | Effort | Why it's V2 |
|---|---|---|
| Historical attendance import + observed-rate feedback loop | 3 d | Needs Spektrix/Tessitura integrations and matching; the honest version is a proper product |
| Funder/board reporting module | 2 d | Business value is real, demo value is low |
| Multi-venue / network dashboards (Film Hubs, chains) | 3 d | Enterprise shape; not a hackathon build |
| Programme simulation ("what if we swapped 3 titles?") | 2 d | Nice, but the MVP already answers the decision |
| Distributor availability integration | blocked | No public API; would need partnerships |

## 6.4 🚫 FEATURES WE SHOULD NOT BUILD (scope-creep guard)

Each of these is something that will *feel* like an obvious addition at 2am on day 12. It is not.

| ❌ Don't build | Why not |
|---|---|
| **A recommendation feed for individual film fans** | Wrong user entirely; turns Adjacent into the crowded consumer-discovery lane |
| **A chatbot interface** | Hides the agent's decisions, which are the actual product; and it's the exact "LLM wrapper" shape the brief forbids |
| **Predicted ticket sales / revenue forecasting** | Qloo cannot support it. Any number we produced would be invented. This is the single most dangerous addition |
| **Automated marketing copy generation** | Cheap LLM work that adds no Qloo value and invites the "why is Qloo here?" question |
| **Social media scheduling / campaign management** | Different product; unbuildable properly in the time |
| **A user-account system with teams and roles** | Zero demo value, days of work |
| **A mobile app** | The user is at a desk with a booking grid |
| **Deep CRM integration** | Requires partnerships, procurement, PII handling — and the product's whole point is *not* needing first-party data |
| **A venue discovery / "find your taste twin cinema" feature** | Interesting, not the problem, and increasingly crowded in this cycle |
| **Real-time collaboration / comments** | Speculative |
| **A credits/payments system** | Premature |
| **Sentiment analysis of reviews to enrich the programme vector** | Tempting (and would look clever) — but it introduces a second, unverified signal source and dilutes "Qloo is why this exists" |
| **Multi-model LLM routing / model comparison harness** | Engineering vanity; no user value |
| **A public API for Adjacent** | Premature |
| **Voice input** | No |
| **Any feature whose output is a paragraph rather than a decision** | This is the category error that kills the product's credibility |

---

# PART 7 — TECHNICAL ARCHITECTURE

## 7.1 Recommended stack — with two changes from our earlier proposal

| Layer | Recommended | Why (and what changed) |
|---|---|---|
| Frontend | **Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui** | Streaming the agent trace needs server-sent events; App Router route handlers give us SSE in the same deploy as the UI |
| Map | **MapLibre GL JS + OpenStreetMap raster tiles** | **Changed from Mapbox/Google** — zero API key, zero billing, works offline in a demo, and we only need to draw a polygon heat layer over one city |
| Charts | **Recharts** (only bars and one line) | Tiny surface area; we do not need a charting framework |
| Backend | **FastAPI (Python 3.12)** | Async parallel Qloo calls; Pydantic models are also the anti-hallucination type system |
| Agent | **Custom async orchestrator (no LangGraph)** — **changed from our earlier proposal.** A ~350-line explicit state machine with typed tools | LangGraph's value is complex branching and human-in-the-loop persistence. Our graph is: resolve → analyse → expand → rank → locate → decide → assemble, with **one** human-in-the-loop point (disambiguation) and **one** loop (widen + retry). Using a framework here adds a dependency, obscures the trace (which is our differentiator), and makes the agent's decisions *less* legible to a judge reading the code. Judging criterion #1 is **"Does the code reflect genuine effort… and avoid wrappers and shortcuts?"** An explicit state machine reads as engineering; a framework reads as scaffolding |
| LLM | **A hosted model for two narrow jobs only** (a) parsing messy programme text, (b) rendering prose from `ToolResult` objects. Model choice is deliberately swappable | The LLM has no route to producing a fact. It is a text transformer at the edges |
| DB | **PostgreSQL 16 + `psycopg` (no ORM)** | Four tables and a handful of queries. An ORM here is overhead, and raw SQL makes the caching logic auditable |
| Cache | **Postgres table with TTL (not Redis)** | **Changed** — one fewer service to deploy, and the cache is inspectable in the UI (a judge can see the cache hit/miss column). Redis becomes worthwhile only past ~5 rps |
| Deploy (backend) | **Fly.io** (single small machine, always-on) | Serverless cold starts would stall an SSE stream mid-demo; a persistent process keeps the connection and the in-flight call budget intact |
| Deploy (frontend) | **Vercel** | Zero-config Next.js; SSE proxied to the Fly backend |
| Observability | **Structured JSON logs to stdout** + a `runs` table + the on-screen trace rail | We do not need a logging platform |
| Tests | **pytest** + recorded Qloo fixtures + one golden-run assertion | Also the mechanism that makes day 1–10 work possible before the key arrives |

## 7.2 High-level architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Next.js (Vercel)                                                    │
│   /                    landing + demo entry                          │
│   /run                 intake → live trace → outputs 1–6 (SSE)       │
│   /run/[slug]          shareable read-only run                       │
│   /about               method, limitations, evaluation               │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ SSE (agent trace) + JSON (artefacts)
┌───────────────────────────▼──────────────────────────────────────────┐
│  FastAPI (Fly.io)                                                    │
│                                                                      │
│   api/          routes: /run /run/{id} /resolve /disambiguate        │
│                 /trace/{id} /health /demo/{slug}                     │
│   agent/        planner · loop · budget · stop conditions            │
│   tools/        T1–T14 (thin; each wraps exactly one Qloo call)      │
│   qloo/         client · auth · retry/backoff · rate limiter         │
│                 cache · params builder · response models · trace     │
│   domain/       scoring bands · cohort construction · distance       │
│                 novelty · evidence assessment · insufficiency        │
│   llm/          extract.py (parse) · narrate.py (templates only)     │
│   db/           schema.sql · runs · qloo_cache · saved_runs          │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ X-Api-Key  (GET only)
┌───────────────────────────▼──────────────────────────────────────────┐
│  https://hackathon.api.qloo.com                                      │
│   /search  /entities  /v2/insights  /v2/tags  /v2/audiences          │
│   /v2/analysis/compare  /v2/trending                                 │
└──────────────────────────────────────────────────────────────────────┘
```

## 7.3 Backend modules

| Module | Responsibility | Key detail |
|---|---|---|
| `qloo/client.py` | The only place an HTTP request to Qloo is constructed | Enforces `X-Api-Key`, the hackathon base URL, GET-only, a 1.5 s connect / 8 s read timeout |
| `qloo/params.py` | Builds parameter dicts from **verified allowlists** | Raises `UnverifiedParameterError` if a param isn't in the allowlist. **This is how "silently ignored parameters" stop being silent** |
| `qloo/models.py` | Pydantic models for every documented response shape | Anything unmodelled is preserved in `_raw` for the evidence panel rather than dropped |
| `qloo/limiter.py` | Token-bucket rate limiter, default 3 rps, configurable | Shared across the process via an in-memory semaphore |
| `qloo/retry.py` | 3 attempts, exponential backoff + jitter, 429/5xx only | 404 is **never** retried — it means "not in Qloo" |
| `qloo/cache.py` | Canonical key = `sha256(method + path + sorted(params))`, Postgres table, TTL by endpoint class (search 24 h, insights 12 h, heatmap 6 h, entities 7 d) | Cache hits are visible in the trace |
| `qloo/trace.py` | Context manager wrapping every call; writes a `TraceRow` | The Evidence Panel is generated from these rows and nothing else |
| `tools/*.py` | T1–T14, one file each | A tool may call Qloo; it may not call another tool |
| `domain/bands.py` | The official affinity bands as a single source of truth | `band(0.82) → "Very High"` |
| `domain/cohorts.py` | Cluster ranked entities; compute novelty + distance | All arithmetic, no LLM |
| `domain/evidence.py` | `assess_evidence`, `InsufficiencyReport` | The gate that can stop a run |
| `agent/orchestrator.py` | The state machine | ~350 lines, readable top to bottom, `MAX_QLOO_CALLS=24` |
| `llm/extract.py` | Free text → `list[ParsedTitle]` + optional metadata | Schema-constrained; no numbers, no entity IDs |
| `llm/narrate.py` | `ToolResult` → prose | First line of every function is the empty-state guard |

## 7.4 Frontend modules

| Module | Responsibility |
|---|---|
| `app/run/page.tsx` | The run shell; subscribes to the SSE trace; renders outputs in order as they land |
| `components/IntakePanel.tsx` | Venue, city, programme textarea, optional postcode + baseline, demo loader |
| `components/ResolutionStrip.tsx` | Per-title rows with status chips; inline one-shot disambiguation chooser |
| `components/TasteDna.tsx` | Tag chips with band colours, URN tooltips, demographic skew bars, coverage line |
| `components/TraceRail.tsx` | The live agent trace; call counter; every decision and its reason |
| `components/CohortCard.tsx` | One cohort: label, type badge, signature entities, rank, novelty, distance, evidence band, why, domain badge |
| `components/RejectedList.tsx` | Candidates and cohorts killed, with reason codes |
| `components/TasteMap.tsx` | MapLibre map, heat layer, venue pin, distance rings, top-3 named areas, coverage line |
| `components/ProgrammeBet.tsx` | Two-sided score card, runner-up, availability disclaimer |
| `components/TestCard.tsx` | Printable one-pager incl. the falsification condition |
| `components/EvidencePanel.tsx` | Call table, explainability attribution, Copy as JSON |
| `components/InsufficiencyBanner.tsx` | The honest failure state |
| `lib/sse.ts` · `lib/types.ts` | Typed SSE client · shared types generated from the backend Pydantic models (a single `make types` step keeps them in sync) |

## 7.5 Database schema

```sql
CREATE TABLE runs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug            TEXT UNIQUE,                    -- shareable link
  created_at      TIMESTAMPTZ DEFAULT now(),
  institution     TEXT,
  city_query      TEXT,
  locality_id     TEXT,
  locality_echo   JSONB,                          -- what Qloo actually matched
  venue_postcode  TEXT,
  programme_raw   TEXT NOT NULL,
  resolved_count  INT, ambiguous_count INT, unresolved_count INT,
  industry        TEXT NOT NULL DEFAULT 'cinema',
  stop_reason     TEXT,                           -- complete | budget | insufficiency | error
  calls_made      INT,
  state           JSONB NOT NULL,                 -- full AdjacentState snapshot
  outputs         JSONB NOT NULL                  -- the six artefacts, as rendered
);

CREATE TABLE trace_rows (
  id           BIGSERIAL PRIMARY KEY,
  run_id       UUID REFERENCES runs(id) ON DELETE CASCADE,
  seq          INT NOT NULL,
  tool         TEXT NOT NULL,
  workflow     TEXT,                              -- Qloo's own workflow id
  method       TEXT NOT NULL DEFAULT 'GET',
  path         TEXT NOT NULL,
  params       JSONB NOT NULL,
  status       INT,
  result_count INT,
  backfill_detected BOOLEAN DEFAULT FALSE,
  duration_ms  INT,
  cache_hit    BOOLEAN DEFAULT FALSE,
  attempt      INT DEFAULT 1,
  error        TEXT,
  created_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON trace_rows (run_id, seq);

CREATE TABLE qloo_cache (
  key         TEXT PRIMARY KEY,                   -- sha256(method+path+sorted(params))
  endpoint    TEXT NOT NULL,
  response    JSONB NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT now(),
  expires_at  TIMESTAMPTZ NOT NULL
);
CREATE INDEX ON qloo_cache (expires_at);

CREATE TABLE fixture_seasons (                     -- the three pre-verified demo runs
  slug         TEXT PRIMARY KEY,
  venue_name   TEXT, city TEXT, programme TEXT,
  postcode     TEXT, notes TEXT
);
```
**No user table. No PII. Ever.** That is a design constraint, not an omission.

## 7.6 API routes

| Method | Route | Purpose | Notes |
|---|---|---|---|
| `GET` | `/health` | Liveness + `qloo_configured: bool` | The frontend uses this to hide live mode when there is no key |
| `POST` | `/run` | Create a run from an intake payload | Returns `run_id`; the agent starts |
| `GET` | `/run/{id}/stream` | **SSE** — trace events, then each artefact as it completes | Event types: `trace`, `resolution`, `taste_dna`, `cohort`, `heatmap`, `bet`, `test_card`, `insufficiency`, `done` |
| `POST` | `/run/{id}/disambiguate` | Submit the one-shot ambiguity answers | Resumes the state machine |
| `GET` | `/run/{id}` | Full run JSON (`state` + `outputs`) | For the shareable page |
| `GET` | `/run/{id}/trace` | Trace rows, for the evidence panel | |
| `GET` | `/demo/{slug}` | A pre-verified fixture season | Powers `Run the demo` |
| `GET` | `/demo/{slug}/canned` | **Recorded** complete run for the fixture | Demo safety net if the network fails on stage |

## 7.7 Qloo integration layer — the rules

1. **One client, one place.** No `httpx` import outside `qloo/client.py`.
2. **Allowlisted parameters only.** Unknown parameters raise before the request.
3. **GET only.** POST-with-body is rejected by the API despite the docs.
4. **`X-Api-Key` header, `https://hackathon.api.qloo.com`.** Never Bearer, never query-param, never staging.
5. **404 ≠ error.** It is a data outcome and flows into the unresolved list.
6. **Every response → `TraceRow`.** No exceptions, including cached ones.
7. **Backfill detection is mandatory.** On any response whose primary array is exhausted, mark the tail as backfill and label it in the UI.

## 7.8 Caching, rate limits, errors

| Concern | Approach |
|---|---|
| **Caching** | Key = `sha256(method + path + sorted(params))`. TTLs: `/entities` 7 d · `/search` 24 h · `/v2/insights` 12 h · heatmap 6 h · `/v2/tags` 7 d. Hit/miss shown in the trace. Demo fixtures are pre-warmed before recording |
| **Rate limiting** | Client-side token bucket at **3 rps** (conservative; a peer measured ~1 rejection per 6 rapid calls). Burst cap 5. On 429: honour `Retry-After` if present, else exponential backoff 1 s/2 s/4 s + jitter, max 3 attempts |
| **Budget** | `MAX_QLOO_CALLS = 24` **hard**, checked *before* every call (not after). Trace shows `n/24`. On exhaustion the run finalises with `stop_reason=budget` and the UI says which outputs are partial |
| **Error taxonomy** | `AuthError` → fail loudly, never degrade silently · `NotFound` → data outcome · `RateLimited` → backoff then partial · `Timeout` → retry once, then degrade that *tool* only · `UpstreamError` → retry, then degrade · `UnverifiedParameter` → a bug, fail the run in dev, log loudly in prod |
| **Degradation** | A failed tool produces an `Unavailable` result with a reason. Dependent outputs then render their empty state. **Nothing is ever substituted** |
| **Logging** | One JSON line per call: `run_id, seq, tool, path, params, status, ms, cache, attempt, count, backfill, error`. Frontend `run_id` in every request header so a demo failure is diagnosable from the browser console |

## 7.9 Explainability & provenance

Three layers, all mandatory:
1. **Inline** — every rendered number carries a `data-call-id` attribute. The evidence panel highlights the corresponding trace row on hover.
2. **Attribution** — `feature.explainability=true` on the taste-DNS, adjacency, and scoring calls returns per-recommendation input attribution. Rendered as "this cohort is driven by: *(Perfect Days → 0.41, Taipei Story → 0.33)*".
3. **Export** — `Copy as JSON` emits the full run: inputs, every trace row, every artefact, the insufficiency report, and the stop reason. This is the artefact a judge can inspect without a demo.

## 7.10 Security & API key handling

| Item | Rule |
|---|---|
| Key storage | `QLOO_API_KEY` env var only. Never in the repo, never in the frontend bundle, never in a URL |
| Proxy | **The browser never talks to Qloo.** All calls go through FastAPI |
| Logs | The key is redacted in every log line by the client before logging |
| Public runs | Shareable runs expose only `outputs` — never raw params containing anything user-specific. (They contain only programme titles, which are public anyway) |
| User data | We store no email, no name, no individual record. The optional postcode is the venue's own published address |
| Rate-limit abuse | A simple per-IP cap of 10 runs/hour on the public deployment |
| Prompt injection | Free-text programme input is passed to the extraction LLM with a strict schema. Anything that isn't a title is discarded. **The LLM has no tool access** — it cannot call Qloo, so injection cannot produce a Qloo claim |

## 7.11 Deployment

```
Frontend   Vercel          next build → edge, env: NEXT_PUBLIC_API_URL
Backend    Fly.io          Dockerfile (python:3.12-slim), 1 machine
                           always-on, min_machines_running=1
                           env: QLOO_API_KEY, DATABASE_URL, LLM_API_KEY
Database   Fly Postgres    or Neon free tier
Domain     adjacent.<tld>  optional; the Vercel URL is fine for Devpost
Migrate    scripts/migrate.py   — runs schema.sql, idempotent
Smoke      scripts/smoke.sh     — /health + one demo run + assert 6 artefacts
```
**Deployment is a Phase-9 task, not a Phase-10 scramble.** Deploy the skeleton on day 2 with a mock client and keep it green.

## 7.12 Folder structure

```
adjacent/
├── README.md                    # problem, method, limitations, how to run
├── LIMITATIONS.md               # the honest page — judges read this
├── .env.example                 # QLOO_API_KEY=, DATABASE_URL=, LLM_API_KEY=
├── docker-compose.yml           # postgres + api for local dev
├── Makefile                     # make dev | test | types | migrate | smoke
│
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile               # fly deploy target
│   ├── app/
│   │   ├── main.py              # FastAPI app, route registration, CORS
│   │   ├── config.py            # env parsing, base URL, budget constants
│   │   ├── deps.py              # dependency wiring (client, cache, db)
│   │   │
│   │   ├── api/
│   │   │   ├── routes_run.py        # POST /run, GET /run/{id}, SSE stream
│   │   │   ├── routes_trace.py      # GET /run/{id}/trace
│   │   │   ├── routes_demo.py       # fixtures + canned runs
│   │   │   └── schemas.py           # request/response models (source of FE types)
│   │   │
│   │   ├── qloo/
│   │   │   ├── client.py            # the ONLY httpx caller
│   │   │   ├── params.py            # verified allowlists + builders
│   │   │   ├── models.py            # Pydantic response shapes
│   │   │   ├── limiter.py           # token bucket
│   │   │   ├── retry.py             # backoff policy
│   │   │   ├── cache.py             # postgres-backed TTL cache
│   │   │   └── trace.py             # context manager → TraceRow
│   │   │
│   │   ├── tools/                   # one file per tool, T1–T14
│   │   │   ├── t01_resolve_locality.py
│   │   │   ├── t02_resolve_entities.py
│   │   │   ├── t03_taste_dna.py
│   │   │   ├── t04_demographic_skew.py
│   │   │   ├── t05_expand_adjacency.py
│   │   │   ├── t06_build_and_rank_cohorts.py    # ← single normalisation
│   │   │   ├── t07_cohort_heatmap.py
│   │   │   ├── t08_audience_lens.py
│   │   │   ├── t09_candidate_additions.py
│   │   │   ├── t10_score_programme.py           # ← two-sided test
│   │   │   ├── t11_compare_seasons.py
│   │   │   ├── t12_trend_check.py
│   │   │   ├── t13_assess_evidence.py           # ← the honesty gate
│   │   │   └── t14_trace.py
│   │   │
│   │   ├── domain/
│   │   │   ├── bands.py             # official affinity bands
│   │   │   ├── cohorts.py           # clustering, novelty, distance
│   │   │   ├── scoring.py           # two-sided comparison & weighting
│   │   │   ├── evidence.py          # sufficiency rules, InsufficiencyReport
│   │   │   └── reasons.py           # rejection reason codes (enum)
│   │   │
│   │   ├── agent/
│   │   │   ├── state.py             # AdjacentState (Pydantic/dataclass)
│   │   │   ├── orchestrator.py      # the loop: plan→select→act→evaluate→stop
│   │   │   ├── budget.py            # call/step/loop counters + guards
│   │   │   └── stop.py              # the six stop conditions
│   │   │
│   │   ├── llm/
│   │   │   ├── extract.py           # messy text → ParsedTitle[]
│   │   │   ├── narrate.py           # ToolResult → prose (empty-guarded)
│   │   │   └── guards.py            # rejects numeric LLM output
│   │   │
│   │   └── db/
│   │       ├── schema.sql
│   │       ├── repo.py              # raw psycopg queries
│   │       └── seed_fixtures.py     # the 3 demo seasons
│   │
│   └── tests/
│       ├── fixtures/                # RECORDED Qloo responses (day-1 work)
│       │   ├── insights_tags_perfect_days.json
│       │   ├── insights_movie_adjacent.json
│       │   ├── insights_results_entities_ranking.json
│       │   ├── heatmap_portland_music.json
│       │   └── entities_imdb_batch.json
│       ├── test_bands.py
│       ├── test_cohort_ranking_single_normalisation.py
│       ├── test_evidence_gate.py
│       ├── test_no_numeric_llm_output.py
│       └── test_golden_run.py       # every rendered number exists in a fixture
│
├── frontend/
│   ├── package.json · next.config.ts · tailwind.config.ts
│   ├── app/
│   │   ├── page.tsx                 # landing
│   │   ├── run/page.tsx             # the run shell (SSE)
│   │   ├── run/[slug]/page.tsx      # shareable run
│   │   └── about/page.tsx           # method + limitations
│   ├── components/
│   │   ├── IntakePanel.tsx
│   │   ├── ResolutionStrip.tsx
│   │   ├── TasteDna.tsx
│   │   ├── TraceRail.tsx
│   │   ├── CohortCard.tsx
│   │   ├── RejectedList.tsx
│   │   ├── TasteMap.tsx
│   │   ├── ProgrammeBet.tsx
│   │   ├── TestCard.tsx
│   │   ├── EvidencePanel.tsx
│   │   └── InsufficiencyBanner.tsx
│   ├── lib/
│   │   ├── sse.ts                   # typed EventSource client
│   │   ├── api.ts                   # fetch wrappers
│   │   └── types.ts                 # generated from backend schemas
│   └── public/
│       └── demo/                    # pre-verified seasons + cached run JSON
│
├── scripts/
│   ├── migrate.py · smoke.sh · record_fixtures.py · warm_cache.py
│
├── docs/
│   ├── METHOD.md                    # how the agent decides + why
│   ├── API_NOTES.md                 # verified param list, dated
│   ├── EVALUATION.md                # the baseline protocol (Part 11)
│   └── DEVPOST.md                   # submission draft
│
└── .github/workflows/ci.yml         # pytest + ruff + next build
```

**Folder rationale, briefly:** `qloo/` is isolated so the client can be swapped for a mock in one line (which is precisely how Phases 0–4 work before the key arrives). `tools/` is flat and numbered so a judge reading the repo can see the agent's whole vocabulary on one screen. `domain/` holds every number-producing calculation with **no I/O** — that is what makes the maths testable. `agent/` is small on purpose. `tests/fixtures/` holds recorded real responses, which is what lets us build the whole product before the API key exists.

---

# PART 8 — DATA REQUIREMENTS

## 8.A — Data from Qloo

| Data | Endpoint | Required? | If unavailable |
|---|---|---|---|
| Entity resolution (title → ID) | `/entities`, `/search` | **Required** | Cannot run. This is the floor |
| Taste tags for the programme | `/v2/insights` (`urn:tag`) | **Required** | Degrade: cohorts still work from entities; Taste DNA panel renders its empty state |
| Demographic skew | `/v2/insights` (`urn:demographics`) | Nice-to-have | Drop the panel silently-but-labelled |
| Adjacent entities by domain | `/v2/insights` (`urn:entity:*`) | **Required** | Cannot discover cohorts. Report insufficiency |
| Single-normalisation ranking | `/v2/insights` + `filter.results.entities` | **Required** | Fall back to *within-domain* ranking only and **say the comparison is weaker** |
| Heatmap cells | `/v2/insights` (`urn:heatmap`) | **Required for Output 3** | Map shows `no coverage for this city`; the report ships without geography |
| Audience catalogue | `/v2/audiences` | Optional (V1) | Audience-lens layer off |
| Explainability attribution | `feature.explainability=true` | Nice-to-have | Evidence panel loses the attribution column |
| Season comparison | `/v2/analysis/compare` | Optional (V1) | Feature off |
| Trend series | `/v2/trending` | Optional (V1) | Feature off |

## 8.B — Data the user supplies

| Data | Required? | Why | Burden |
|---|---|---|---|
| **City** | **Required** | Every geographic claim depends on it | One field |
| **5–20 programme titles** | **Required** | The seed set | Copy-paste from a season page |
| Optional **IMDb/Rotten Tomatoes ID** per title | Optional | Deterministic resolution (Finding 4) | We auto-fill it when we can |
| **Venue postcode / address** | Optional | Distance rings and "how far are they from your door" | One field |
| Optional **baseline new-household rate** | Optional | Makes the Test Card's falsification condition quantitative | One number they already have |
| Optional **audience description** | Optional | Calibrates the novelty slider's start | One sentence |
| Optional **available slots** | Optional (V1) | Constrains the slot recommendation | Free text |

**The MVP's data requirement is: one city and a copied-and-pasted programme.** That is the product's core usability claim, and it is why cinema is the right beachhead — cinema programmes are *published, dated, titled, public documents*.

## 8.C — External public data

Evaluated honestly, including the ones we should refuse.

| Dataset | Why we'd want it | Free? | Licensing | Effort | Removable? |
|---|---|---|---|---|---|
| **OpenStreetMap tiles** | The map background | ✅ Yes, FOSS | ODbL — **attribution required** | Trivial (a raster tile URL) | ✅ Could go without a map — but the map is the wow |
| **OpenStreetMap Nominatim** (geocoding the postcode) | Turn a postcode into lat/lng | ✅ Free, **1 req/s** policy | ODbL + usage policy | Trivial | ✅ Qloo places often carry `properties.geocode`, so we often don't need it |
| **Wikidata / Wikidata SPARQL** | Rich film→director→movement structure | ✅ Yes, CC0 | CC0 | Medium | ✅ Qloo already covers most of it |
| **IMDb datasets** (`title.basics.tsv`, ~1 GB) | Title→IMDb-ID pre-resolution for offline matching | ✅ Free for non-commercial download | **Non-commercial only** — a real constraint for a future product | Medium (large file; but we'd use the API path instead) | ✅ **Not needed in the MVP** |
| **TMDb API** | Posters, release dates, external IDs | ✅ Free with attribution | Requires API key; limited commercial use | Low | ✅ **Posters are decoration.** Skip for MVP |
| **BFI / UK box office data** | Comparative performance context | ✅ Published | Public | High (PDFs, annual) | ✅ Out of scope |
| **Avenue ISR / Art House Convergence survey data** | Sector benchmarks | ❌ Not public (member/report) | Proprietary | N/A | ✅ Out of scope |
| **UK postcode → lat/lng (postcodes.io)** | Precise venue coordinates | ✅ Free, open | Open Government Licence | Trivial | ✅ Optional |
| **Census / Index of Multiple Deprivation** | Contextualise neighbourhoods | ✅ Published | OGL | Medium-high (large, geospatial joins) | ✅ **Explicitly out of scope — it invites demographic profiling and undermines the aggregate-only privacy stance** |
| **Distributor availability feeds** | Whether a title can actually be booked | ❌ No public API | N/A | Blocked | ✅ Out of scope; the Test Card says so |

### The honest conclusion on external data

> **The MVP uses exactly one external dataset: OpenStreetMap tiles (for the map background), plus optionally Nominatim/postcodes.io for the venue pin.** Everything else is either unnecessary, licensing-risky, or privacy-risky. **Qloo plus the user's own programme is sufficient** — and that is the cleanest possible statement of the product's data story, which is itself a competitive advantage over any rival that needs to assemble a data pipeline.

## 8.D — Data we can avoid entirely (and why that matters)

| Data | Why we avoid it | The strategic benefit |
|---|---|---|
| **Ticketing / CRM records** | Not needed: the whole point is finding non-attenders | No GDPR/CCPA surface, no procurement, no integration, instant onboarding |
| **First-party customer data** | Qloo needs none by design | We can promise a **zero-PII product** in writing, which no competitor in the sector's tooling can |
| **Social media scraping** | Unnecessary, and a ToS minefield | No legal exposure |
| **Email lists** | We are deliberately *not* a marketing-send tool | We don't want to be in the data-processing chain |
| **Individual-level Qloo data** | **Qloo does not provide it** — it is aggregate-only for legal reasons | We never have to ask the question |
| **Payment or identity data** | No accounts | Nothing to breach |
| **Third-party AI training data** | We use a hosted LLM for text transformation only, with no fine-tuning | No data-governance overhead |

**The line to put in the README:**

> *Adjacent stores no personal data about anyone. It does not connect to your ticketing system, your mailing list, or your CRM. It knows your programme and your city, and it asks Qloo about culture. That is the entire data footprint.*

---
