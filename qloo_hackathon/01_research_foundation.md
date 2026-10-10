# Qloo Agentic Hackathon — Research Foundation
**Prepared:** 4 October 2026 · **Deadline:** 30 October 2026, 11:45pm EDT (**26 days**) · Repo: `/qloo_hackathon/`

This file is Part 1 of the deliverable: the verified facts. Part 2 (`02_ideas_and_scoring.md`) contains the 15 ideas, scoring, and final recommendation.

---

## 1. Hackathon reality check

| Item | Fact | Source |
|---|---|---|
| Prize pool | $25,000 — 1st $15k, 2nd $6k, 3rd $4k | [Qloo Agentic Hackathon](https://qloo.devpost.com/) |
| Deadline | 30 Oct 2026, 11:45pm EDT | [Devpost](https://qloo.devpost.com/) |
| Participants at time of research | 356 (previous Qloo hackathon had **2,896**) | [Devpost](https://qloo.devpost.com/) |
| Eligibility | All countries/territories excluding standard exceptions — India is fine | [Devpost rules](https://qloo.devpost.com/rules) |
| Team size | Up to 4; solo welcome | [Previous rules](https://qloo-hackathon.devpost.com/rules) |
| Demo video | **NOT required** — "we're requiring something judges can actually use" | [Devpost](https://qloo.devpost.com/) |
| Required submission | Live hosted demo · public repo · text description · open-source licence visible in repo About | [Devpost](https://qloo.devpost.com/) |

### Judging criteria (weight these in design decisions)
1. **Technological Implementation** — "How thoroughly and skillfully does the project use Qloo? Does the code reflect genuine effort and a working, non-trivial implementation?"
2. **Design** — "a complete, coherent product experience, not just a technical proof of concept"
3. **Potential Impact** — "a credible, specific case for solving a real problem for a real audience… *based on what's demonstrated*"
4. **Quality of the Idea** — "a creative, **non-obvious** use of Qloo… genuine understanding of the problem space"

### The judges (this matters a lot)
| Judge | Role | What likely moves them |
|---|---|---|
| Michael Abrams | EVP Strategic Initiatives, **Live Nation** | Rooms, audiences, touring, live programming |
| Cedric the Entertainer | Actor / producer / host | Entertainment, storytelling, format |
| Todd Boehly | CEO, Eldridge Industries (Dodgers, Chelsea, media) | Media businesses, big-market outcomes |
| Nicole Seligman | Member, OpenAI Board | Responsible AI, real human benefit |
| Mike Diolosa | **CTO, Qloo** | Depth of API use; non-obvious graph exploitation |
| Jason Calacanis | Investor | Market size, clear ROI, a real company |

**Implication:** two of six judges are entertainment-industry operators. Entertainment/culture *business* decisions have the highest judge-fluency per unit of explanation. Non-US, abstract, or purely academic framings are penalised.

### The three directions Qloo itself suggested in the prompt
- Electricians' customers choosing **lighting styles** per room
- **Meals and dining for seniors** with health/chewing/heat constraints
- **Rare-disease journeys** — information + community + next steps

> **Strategic warning:** these three are printed in the challenge text, so they will be the three most-crowded lanes in the submission pool. Building one of them well is fine; building one of them *because it was suggested* is the fastest route to looking derivative.

---

## 2. Qloo API capability map — verified against official documentation

> Rule applied throughout: **every capability below is cited from `docs.qloo.com` or Qloo's own site.** Anything I could not verify is flagged as an open question in §9 of Part 2.

### 2.1 Access, base URL, auth
| Item | Verified behaviour | Source |
|---|---|---|
| Hackathon base URL | `https://hackathon.api.qloo.com` — **keys from the hackathon work nowhere else** | [Hackathon Dev Guide](https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide) |
| Auth header | `X-Api-Key: <key>` — **not** Authorization/Bearer, **not** query param | same |
| Wrong base URL = `401` | Most common error. Staging/production URLs always 401 with a hackathon key | same |
| Method | `/v2/insights` is **GET**; params in query string. POST with JSON body → 404 | same |
| Key issuance | Google Form → email, "typically a few business days" — **form can be submitted before you have an idea** | same |
| Rate limits | "Rate limits are in place but set high enough to support typical hackathon projects." One measured datapoint from a peer project: *"Qloo rejects the sixth call within about a second"* (i.e. roughly ≤5 calls/sec, measured 2026-10-03) | [Dev guide](https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide) · [Booker repo](https://github.com/danielhagever/booker) |
| Batching | No field filtering — "The API returns the full response… no supported way to suppress specific fields." Responses are verbose (`akas`, etc.) — expect large payloads | Dev guide FAQ |
| `take` | Max **50** per request; use `page` for pagination | [Deep Dive](https://docs.qloo.com/reference/insights-api-deep-dive) |

### 2.2 Entity types (`filter.type`) — what you can actually get back
**Supported on `/v2/insights`:** `urn:entity:artist`, `urn:entity:book`, `urn:entity:brand`, `urn:entity:destination`, `urn:entity:movie`, `urn:entity:person`, `urn:entity:place`, `urn:entity:podcast`, `urn:entity:tv_show`, `urn:entity:video_game`, plus `urn:heatmap`, `urn:demographics`, `urn:tag`.

**Deprecated / careful:** `urn:entity:audience` (deprecated for new integrations); `actor` / `author` / `director` → use `urn:entity:person`. `/search` accepts **legacy-only** types `urn:entity:actor`, `urn:entity:album`, `urn:entity:author`, `urn:entity:director`, `urn:entity:locality` that `/v2/insights` will reject.

**Common mistakes Qloo explicitly calls out:** use `urn:entity:artist` not `urn:entity:music`; use `urn:entity:place` or `urn:entity:brand` not `urn:entity:food_and_drink`.
Source: [Hackathon Dev Guide](https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide), [Entity Type Parameter Guide](https://docs.qloo.com/reference/available-parameters-by-entity-type)

### 2.3 Endpoints
| Endpoint | Purpose | Notes |
|---|---|---|
| `GET /v2/insights` | **The workhorse.** Recommendations, taste analysis, demographics, heatmaps, tag/filter search all run through this one route | `filter.type` always required |
| `GET /search` | Name → Qloo entity IDs. Own `types`, `filter.location`, `filter.radius` (miles), `filter.exists`, `filter.tags`, `filter.rating`, `filter.popularity`, `sort_by` | [Docs](https://docs.qloo.com/reference/get-search) |
| `GET /entities` | Fetch entities by ID | [API overview](https://docs.qloo.com/reference/api-overview) |
| `GET /v2/tags` | Search the tag taxonomy — **no static tag list exists**, you must search | Dev guide FAQ |
| `GET /v2/audiences` + audience types | Audience segments; 10 parent categories | [API overview](https://docs.qloo.com/reference/api-overview) |
| `GET /v2/trending` | **Time series of popularity over a date range** — `filter.start_date`, `filter.end_date`, `signal.interests.entities` | [Docs](https://docs.qloo.com/reference/get-trending) |
| `GET /v2/analysis/compare` | Compare group A vs group B tastes — `a.signal.interests.entities`, `b.signal.interests.entities`, `model=descriptive\|predictive`, `filter.subtype=urn:tag:genre\|urn:tag:occupation` | [Docs](https://docs.qloo.com/reference/analysis-compare) |
| ❌ `/recommendations`, `/recs` | **Legacy — not supported for the hackathon** | Dev guide |

### 2.4 The parameters that actually matter (and which ones nobody else is using)

**Signals (what shapes the affinity score):**
- `signal.interests.entities` / `.tags` — entity or tag seeds, each with optional `.weight`
- `signal.interests.entities.include` — force specific entities into the affinity calc even if the core logic wouldn't infer them
- `signal.demographics.age` (8 buckets incl. `55_and_older`) / `.gender` / `.audiences` — **each with its own `.weight`**
- `signal.location` / `signal.location.query` — a locality name, WKT point/polygon, or Qloo locality UUID, with `.radius`
- `operator.signal.interests.tags` — `union` (max-affinity tag wins) vs `intersection` (tags merged)

**Filters (what you're allowed to return):**
- `filter.location.query` (fuzzy name, supports AKAs like "The Big Apple"), `filter.location` (lat/lon, WKT, or UUID), `filter.location.geohash` (**12-char precision — block level**), `filter.exclude.location.*`, `filter.location.radius` (≤800,000 m; `0` = strict boundary, default pads by min(10% of diameter, 2,414 m))
- `filter.geocode.name` / `.admin1_region` / `.admin2_region` / `.country_code`; `filter.location.metro`
- `filter.popularity.min` / `.max` (**0–1 percentile**) — the single most under-used parameter in the field
- `filter.tags`, `filter.exclude.tags`, `filter.results.tags`, `filter.results.entities` + `.query` (score *your own* shortlist — a "grade my list" mode)
- `filter.hours` (day of week a POI is open), `filter.price_level.min/max` (1–4), `filter.price_range.from/to` (hotels), `filter.hotel_class.min/max`, `filter.rating.min/max`, `filter.popularity.*`
- `filter.external.exists` — `resy | michelin | tablet`; plus granular Resy (rating, rating count, party size) and Tripadvisor (rating, rating count) filters — **place entities only**
- `filter.references_brand` — narrow place results to specific brand entity IDs (e.g. only Walmart stores)
- `filter.content_rating` (G→NC-17, TV-G→TV-MA), `filter.release_year.min/max`, `filter.release_country`, `filter.publication_year.*`, `filter.finale_year.*`, `filter.latest_known_year.*`, `filter.date_of_birth.*`
- `filter.parents.types` — restrict to audience categories or entity categories
- `bias.trends` (`off`→`very_high`), `bias.content_based` (0–1), `bias.quality` (**places only**)
- `diversify.by=properties.geocode.city | .metro | subtype` + `diversify.take` — cap results per city/metro. **Almost nobody uses this.** Essential for any multi-city output.
- `sort_by = affinity | distance | rating | quality`
- `feature.explainability=true` — **returns per-recommendation attribution showing which input entities contributed, normalised 0–1, plus aggregate influence across top-3/5/10/all.** This is your "receipts" feature and it is free.
- `backfill.cross_domain.take` (≤20) and `backfill.content_based.take` (≤10) — what gets appended when primary results run dry
- `output.heatmap.boundary` (geohash | city | neighbourhood) + `heatmap.dimensions = quality | popularity | hotel_class | price_level` (adds `<dim>_affinity_rank` and `<dim>_affinity` columns)

**Special `filter.type` modes on the same endpoint:**
- `urn:heatmap` → grid of `{lat, lon, geohash}` each with `affinity`, `affinity_rank`, `popularity`. Requires a location + at least one signal. Works with **artist entities** as the signal (music genres and artists move the heatmap) — but a peer project measured that **food and activity tastes do *not* produce heatmap tag affinity**, so places/cuisines cannot drive a heatmap.
- `urn:demographics` → age + gender affinity (`+` above average, `−` below) for an entity or tag.
- `urn:tag` → the tags that describe the taste of an entity set, an audience, or a location. ("Taste Analysis", formerly "Taste AI".)

Sources: [Insights Deep Dive](https://docs.qloo.com/reference/insights-api-deep-dive) · [Entity Type Parameter Guide](https://docs.qloo.com/reference/available-parameters-by-entity-type) · [Heatmaps](https://docs.qloo.com/reference/heatmaps-use-case) · [Demographics](https://docs.qloo.com/reference/demographics-use-case) · [Taste Analysis](https://docs.qloo.com/reference/taste-analysis)

**Parameters by entity type — the traps:**
- **Artist has NO `filter.location`.** You cannot ask "recommend artists for Austin" directly. You *can* pass `signal.location.query` (verified in a peer project's live run) and `filter.popularity.min/max`, `filter.tags`, `filter.parents.types`, `signal.demographics.*`.
- **Place** is the richest type (≈45 parameters, incl. hours, price, external ratings, brand refs, `sort_by`, `bias.quality`).
- **Destination requires `signal.interests.entities`** — you cannot pull destinations with no signal.
- **Movie / TV** are the only types with `filter.content_rating` and `filter.release_country`.
- **Tag** type only accepts `diversify.by`, `diversify.take`, `offset`, `take` — nothing else.
- Parameters invalid for a `filter.type` are **silently ignored, not rejected.** Empty 200 responses are almost always this, not a data gap. Check the parameter guide before assuming missing data.

### 2.5 Data, privacy and coverage facts
| Fact | Source |
|---|---|
| ~250M+ entities cited in the hackathon brief; Qloo marketing elsewhere says **575M+** across 50+ countries, "detail down to hundreds of feet" | [Qloo](https://www.qloo.com/) · [Qloo cultural AI page](https://leon-blog-post-2-8--qloocom.netlify.app/) |
| **No PII at all.** "Qloo does not handle or depend on any personally identifiable information whatsoever" | [FAQs](https://docs.qloo.com/docs/faqs) |
| **"Qloo is designed to overcome cold starts and does not require customer data to generate insights."** — *This is the single most important line in the entire documentation for our purposes.* | [FAQs](https://docs.qloo.com/docs/faqs) |
| Data sources: TasteDive cross-domain panel, third-party, proprietary entity DB, and anonymised API-ecosystem learning rights from Fortune-500 financials, **JCDecaux, Michelin, Samsung, Netflix** | [FAQs](https://docs.qloo.com/docs/faqs) |
| Updated daily/weekly/monthly depending on category | [FAQs](https://docs.qloo.com/docs/faqs) |
| Named Qloo clients: **Netflix, Starbucks, JCDecaux, Michelin**; historically BMW, Tablet Hotels, IAC, Equinox, Penguin Random House, Campbell's, Samsung, Swarovski, PepsiCo; Match Group (BLK, Chispa, Upward, Yuzu) with a claimed **+70% Likes** lift on Yuzu | [PRNewswire](https://www.prnewswire.com/news-releases/qloo-brings-cultural-ai-to-blk-chispa-upward-and-yuzu-302506279.html) · [Qloo](https://www.qloo.com/) |
| Affinity scores: 0–100; **differences of 91 vs 92 are not usually meaningful** — Qloo says so explicitly. Do not build a pitch on tiny score deltas. | [FAQs](https://docs.qloo.com/docs/faqs) |
| Terms define "End Vertex" = a collection of input signals; **Qloo Output = "correlative inferences"** — group-level, not individual predictions. Frame claims accordingly. | [Terms](https://www.qloo.com/legal/terms) |
| **Coverage caveat:** "The hackathon environment may not have data for every entity or region." Peer projects independently measured missing artists and missing regions. Demo in **major Western metros**. | [Dev guide](https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide) · [Undercard repo](https://github.com/Xio-Shark/undercard) |

### 2.6 The official hackathon harness — you should use this
Multiple submitted projects route all calls through **`@qloo/qloo-harness` (npm, v0.1.26+)**, described by its users as "the authorised surface from the hackathon kit." It exposes `qloo setup --qloo`, `qloo setup --status`, and `qloo exec` against **named workflows**:

| Workflow | Apparent role |
|---|---|
| `describe` | Resolve a typed name to a Qloo entity (+ disambiguation) |
| `entity_tags` | Tags / cultural concepts for an entity |
| `find_tags` | Tag search |
| `recommend` | Cross-category affinity recommendations |
| `compare_audiences` | Group vs candidate audience tag overlap |
| `where_popular` | Geographic popularity/affinity (heatmap) |

Sources: [Cold-Open](https://github.com/nicolasesanchez50/cold-open) · [Soft Landing](https://github.com/TomasArancibia1/soft-landing) · [Undercard](https://github.com/Xio-Shark/undercard) · [TasteForge PR](https://github.com/williamleewilliam1-star/babydov-tasteforge-agent/pull/1)

> **Recommendation:** use the harness for the *demo path* (it is what Qloo's own kit surfaces, and it preserves workflow status, correlation IDs, duration, warnings and provenance), **and** keep a typed raw-HTTP client for parameters the workflow layer may not expose (`feature.explainability`, `diversify.by`, `analysis/compare`, `heatmap.dimensions`). Confirm the workflow list with the #api-help Discord channel before you commit.
