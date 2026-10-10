# Qloo Agentic Hackathon — Deep Research, 15 Ideas, and the Winning Recommendation

_Generated 4 October 2026 · deadline 30 October 2026_

**Read this first:** Part 4, §9 is the answer. Parts 1–3 are the evidence behind it.

---

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

---

# Part 2 — Saturation Map & Real-Problem Evidence

---

## 3. Saturation analysis: what is already being built for THIS hackathon

I found **24 named projects** across the current Qloo Agentic Hackathon and its 2025 predecessor. This is the most important input to idea selection, because the judging criterion "Quality of the Idea — creative, **non-obvious** use of Qloo" is a *relative* judgement against whatever else the panel has already read.

### 3.1 Projects found — current hackathon (deadline 30 Oct 2026)

| Project | Shape | One-liner | Source |
|---|---|---|---|
| **Booker** | Room programming | "Book the acts your room's crowd already loves" — taste-matched booking for venues + touring artists, web + MCP | [GitHub](https://github.com/danielhagever/booker) |
| **Advance** | Room programming | Tour-advance agent for promoters: where to play, who opens, which room, after-show, sponsors | [GitHub](https://github.com/bisale24-ops/advance) |
| **Undercard** | Room programming | Audits a support-act shortlist against headliner fans vs. a target audience | [GitHub](https://github.com/Xio-Shark/undercard) |
| **TasteBridge** | Relocation | "Move cities, keep your taste" — taste-equivalents + neighbourhood ranking + first-week plan | [GitHub](https://github.com/teddywasserman/tastebridge) |
| **Newcomer** | Relocation | "Find the neighborhood that already likes what you like" — heatmap + MCP | [GitHub](https://github.com/danielhagever/newcomer) |
| **Soft Landing** | Relocation | Translates your taste to a new city (dna · places · barrio · culture · match lanes) | [GitHub](https://github.com/TomasArancibia1/soft-landing) |
| **Home2Here** | Relocation | Cultural bridge → personalised first-week belonging plan for a new city | [GitHub](https://github.com/rehan-ml/home2here-qloo-agent) |
| **CulturePilot** | Marketing / brand brief | Qloo cultural-intelligence studio, culture graph, opportunity scoring, provenance | [GitHub](https://github.com/ect2000/culturepilot) |
| **Hayy** | Marketing / local venue | Taste-grounded marketing agent for small cafés — menu move, playlist, collabs, social posts | [GitHub](https://github.com/FaisalMT3/hayy) |
| **TasteShip** | Marketing / product | Feature ask → same-day ship pack grounded in Qloo | [GitHub](https://github.com/Cubiczan/tasteship) |
| **Quorum** | Synthetic research | "Focus group in a box" — grounded panel reacting via real affinity fingerprints, with receipts | [GitHub](https://github.com/AkshayJohn03/Quorum) |
| **Cold-Open** | B2B partnership | Taste-matched partnership lead gen (brand collabs, artists, venues) | [GitHub](https://github.com/nicolasesanchez50/cold-open) |
| **Common Ground** | Bridging | Finds what two groups both love | [GitHub](https://github.com/AtmanSculptor/common-ground) |
| **Resonance** | Senior living | Cultural favourites → engagement plan for senior-living activity teams and families | [GitHub](https://github.com/P00NSMASHER/resonance-qloo) |
| **TasteLoop** | Week planner | Agentic week-planner; explicitly runs a **simulated generic baseline** side-by-side | [GitHub](https://github.com/knowaguy4u-cell/tasteloop) |
| **TasteRoute** | Route planner | Mood + city + anchor → three-stop route with an interpretation trace | [GitHub](https://github.com/XFFFK/taste-route-agent) |
| **Taste Match** (`qloo-mcp`) | MCP + artist audience | MCP tools + "who would love this artwork" agent; 7 parallel insight calls | [GitHub](https://github.com/NoBanks/qloo-mcp) |
| **qloo-taste-mcp** | MCP wrapper | 4 tools (search/recommend/trending/tags) + Taste Match demo | [GitHub](https://github.com/hahahahahahahahah6/qloo-taste-mcp) |
| **TasteForge** | Workflow migration | Reference implementation pinned to official harness workflows | [PR](https://github.com/williamleewilliam1-star/babydov-tasteforge-agent/pull/1) |
| **Zento** | Cultural concierge | 3-question "Taste Triangle" → cross-domain discovery, Gemini + Qloo | [Devpost](https://devpost.com/software/zento-85n0g4) |

### 3.2 Projects found — 2025 Qloo LLM Hackathon (2,896 participants)
Winners: **GeoTaste** (1st, $10k — "location into business insights", market analysis + competitive intel + interactive visualisations), **Alloy** (Cultural Due Diligence Engine for M&A), **Resonance AI** (political messaging), **Zesty** (unrecommendation engine). Honourable mentions aside, the wider gallery included: **QlooTwin** (chat with your consumer data), **CULTAURA**, **Mapetizer** ("appetizing business zones mapped by taste to location"), **PersonaMuse** (character creation), **Luna** (AI bestie), **NexPR** (PR campaign analysis), **Poshak AI** (fashion), **Vybr** (roommate matching), **Duddle** (group decision), **Taste Taylor** (fashion, multi-agent), **CultureAI**, **PersonaReads**, **Marketly**, **Cultural DNA**, **RescueEye Global**, **CultureHub**, **Appmuseme**, **QLOOTRA**, **MyNakama**, **Taste Mirror**, **TasteJourney**, **Product Discovery & Market Insights (Beacon Base)**.
Source: [2025 gallery](https://qloo-hackathon.devpost.com/project-gallery) · [winners announcement](https://x.com/Qloo/status/1965110790400151775)

### 3.3 The shapes that are already crowded — do not build these

| Shape | Occupancy | Verdict |
|---|---|---|
| **Relocation / "keep your taste in a new city"** | **4 projects** (TasteBridge, Newcomer, Soft Landing, Home2Here) | **Dead. Do not enter.** |
| **Live music booking / touring / room programming** | **3 projects** (Booker, Advance, Undercard) — Booker is unusually thorough | **Dead. Do not enter.** |
| **Marketing / brand brief / campaign generator** | **4+ across both editions** (CulturePilot, Hayy, TasteShip, NexPR, Marketly, TAVA, Resonance AI, GeoTaste) | Effectively dead. |
| **Travel itinerary** | 4+ (Appmuseme, QLOOTRA, Voya, TasteJourney, CULTURA, TasteRoute) | Dead. |
| **MCP wrapper / "give any agent taste as tools"** | 3 (qloo-mcp, qloo-taste-mcp, Booker MCP) | Dead as a standalone idea. |
| **General "cultural concierge / taste DNA"** | 10+ | Dead. |
| **Movie / book / music recommender** | 6+ | Dead. |
| **Fashion** | 3 (Poshak AI, Taste Taylor, Qloo Fashion AI) | Dead. |
| **Group decision making** | 2 (Duddle, Common Ground) | Crowded. |
| **Synthetic audience / focus group** | 1 strong entry (Quorum) | Crowded. |
| **Senior living / memory care engagement** | 1 (Resonance) | Taken. |
| **Route / outing planning** | 3 | Dead. |
| **B2B partner / lead matching** | 2 (Cold-Open, Alloy) | Crowded. |

### 3.4 What this tells us strategically
1. **The winning move is a new *shape*, not a new *domain*.** Every crowded lane above is a different domain wearing the same four shapes: *concierge*, *room programmer*, *planner*, *brief generator*.
2. **Two shapes are almost entirely unused:**
   - **Institutional audience development** — "who else would love us, and where do they live?" (distinct from *marketing to a cohort*, which is saturated)
   - **Constrained consumer decision under real constraints** (budget, geography, physical/religious/health limits) rather than open-ended discovery
3. **Nobody is using the time axis.** `/v2/trending` (date-range time series) and `bias.trends` appear in almost no submission. Nor is anyone using `filter.popularity.min/max` as a *strategy*, `diversify.by`, `filter.content_rating`, `filter.release_country`, `filter.external.exists` (Resy/Michelin/Tablet), `filter.hours`, or `heatmap.dimensions`.
4. **`feature.explainability=true` + a visible call trace is now table stakes** for the top entries. Several projects already show "how we know" panels. You need receipts *and* something more.
5. **The GeoTaste precedent matters.** The 2025 winner was a **B2B decision tool with maps and business consequences**, not a consumer app. That is the template the Qloo team rewarded.

---

## 4. Real user problems — evidence, with sources

Only domains with **documented** pain are listed. My own inference is marked *(inference)*.

### 4.1 Cultural institutions are losing their audiences faster than they can replace them
- Boston Symphony Orchestra reported **attendance down 40% over 20 years**; NEA's Survey of Public Participation in the Arts shows US adults attending live classical performances fell from **8.6% (2017) to 4.6% (2022)**. — [Boston Globe, Jul 2026](https://www.bostonglobe.com/2026/07/01/arts/boston-classical-music-attendance-decline/)
- TRG Arts, analysing transactional data from **163 arts organisations across the US and Canada (2018→2025)**: households attend **fewer** events (1.5 → 1.45 orders/yr) and organisations sell **~9% fewer tickets**, with revenue held up only by pricing. — [TRG Arts, Mar 2026](https://trgarts.com/blog/north-american-arts-audience-trends-march-2026)
- The replacement rate is below 1.0: every active symphony attendee who leaves is replaced by **0.907 of a person** — a structural, compounding decline. — [Culture for Hire, Sep 2026](https://www.cultureforhire.com/blog/bso)
- The Wallace Foundation's literature review: there is **"scant research evidence to explain why arts audiences are shrinking, how organizations can reverse this trend"**, and proposed techniques "don't point to obvious solutions." — [Wallace Foundation](https://wallacefoundation.org/report/audience-building-and-financial-health-nonprofit-performing-arts-current-literature-and)
- The industry itself names the failure: *"the historic arts audience now represents a shrinking share of the population… For decades, arts growth relied on **lookalike targeting** — finding more people who resembled your best, most loyal patrons. That model worked when the general population still looked like the audience the field originally built."* — [Culture for Hire](https://www.cultureforhire.com/blog/bso)
- **Distance is decisive:** a white paper estimated that at **one mile** from an arts organisation the likelihood of attendance **drops by 80%**. — [Symphony.org](https://symphony.org/features/meeting-audiences-where-they-are/)
- Funders are asking for it: *"We should be approaching audience development as a science so that there are hypotheses that get tested and evaluated."* — Bay Area funder, [Hewlett Foundation](https://hewlett.org/how-arts-organizations-are-growing-the-audiences-of-tomorrow/)
- Barriers reported by 18–34s: **no one to go with**, competition from other leisure (dining, rock concerts, sport), lack of awareness, travel time. — [Wallace Foundation, Building Millennial Audiences](https://wallacefoundation.org/report/building-millennial-audiences-barriers-and-opportunities-barriers-and-opportunities)

**Why this is a Qloo problem, not just a marketing problem:** the field's analytic vendors (TRG Arts, SMU DataArts, Capacity Interactive, WolfBrown) work from **your ticket data**. They are structurally incapable of describing people who have never bought a ticket. Qloo's own FAQ says *"Qloo is designed to overcome cold starts and does not require customer data."* That is the exact inversion the field has been waiting for.

### 4.2 Independent venues and promoters are dying, and booking is done on gut feel
- NIVA's *State of Live* study (TEConomy Partners, June 2025): **64% of US independent stages were not profitable in 2024**; **31% of all expenses go to artist and booking fees**; 60% of venues expect artist fees to rise further; **$153.1bn total economic output, 908,000 jobs**; 183.7m fans served. — [NIVA](https://www.nivassoc.org/stateoflive) · [Pollstar](https://news.pollstar.com/2025/06/23/nivas-state-of-live-survey-finds-independent-venues-generated-153-1b-in-total-economic-output-across-u-s-in-2024-64-stages-struggling-with-unprofitability/) · [Report PDF](https://www.digitalmusicnews.com/wp-content/uploads/2025/06/NIVA-State-of-Live-2025-Report.pdf)
- Talent buying is a spreadsheet job: *"All of our stuff is buried within Dropbox folders, Google sheets and emails but it's a mess."* — working talent buyer, [r/musicindustry AMA](https://www.reddit.com/r/musicindustry/comments/17plz6t/i_am_a_talent_buyer_for_multiple_venues_ask_me_ama/)
- Venues get **10–40 unsolicited booking emails per week**, each taking ~20 minutes to assess, mostly from acts outside their genre or price range. — [Dave Ruch survey of venues](https://daveruch.com/advice/how-to-reach-out-for-a-gig-booking/)
- Existing tools surface **lagging indicators** (where an act already played) and **vanity metrics**: *"Social media tells them what people are watching, but it doesn't prove anyone is invested."* — [ArtistRack](https://artistrack.com/what-booking-agents-look-for-indie-bands/)
- ⚠️ **This is the strongest problem/evidence pair I found — and it is already occupied by three hackathon projects.** I am flagging it as a "reject despite great evidence" case, which is itself an insight: evidence quality and contest differentiation are different axes.

### 4.3 Music sync licensing is a broken market
- Music supervisors get **hundreds of cold pitches per week and delete almost all of them**; TV supervisors may have **48 hours** to clear a track before air. — [notnoise.co](https://notnoise.co/blog/sync-licensing-guide)
- *"The sync industry has historically been a 'who-you-know' business… They go to their trusted sources."* Brands now produce **200–300 pieces of branded content per year** and manual rights clearance is buckling. — [Resident Advisor Pro, Nov 2025](https://ra.co/news/84036)
- Agencies process **500+ submissions a day**; music is disqualified for *metadata* and *process*, not taste. — [notnoise.co](https://notnoise.co/blog/sync-licensing-for-musicians) · [Chartlex](https://www.chartlex.com/blog/money/music-sync-licensing-guide-independent-artists-2026)
- **A competitor already exists but is non-Qloo:** [SyncVision](https://github.com/TheLyricalLuminary/SyncVision) does deterministic clearance triage and explicitly states it "makes no claim to editorial taste, cultural context, or legal determination." That is precisely the hole Qloo fills.

### 4.4 Consumer gifting is universally painful and universally generic
- Representative of the pattern: *"Our anniversary is coming up and I just don't know what to get him. He buys everything he wants so it makes it hard to buy something I know he will want and use."* — [r/GiftIdeas, Mar 2026](https://www.reddit.com/r/GiftIdeas/comments/1rs0s3d/gift_ideas_for_a_boyfriend_who_buys_everything_he/) *(inference: this thread shape recurs constantly; I did not run a quantitative study)*
- Standard answers are structurally generic — gift cards, food baskets, socks, "listen to them through the year and write it down." — [r/AskReddit thread](https://www.reddit.com/r/AskReddit/comments/9ey89f/whats_a_good_go_to_gift_for_someone_when_you_have/)
- **This is the least-evidenced problem in my set at a quantitative level** — it is a universally-recognised pain, not a documented industry crisis. Score it accordingly.

### 4.5 Independent retail cannot do assortment planning
- **93% of retailers report struggling with merchandise assortment planning**; 62% plan to buy analytics tooling; localisation to neighbourhood demographics/culture is named as a best practice most independents cannot execute. — [Wave Grocery](https://www.wavegrocery.com/blogpost/what-is-assortment-planning-in-retail-how-to-optimize-it) · [Optimum Retailing](https://marketing.optimumretailing.com/blog/assortment-planning-what-every-retailer-needs-to-know)
- ⚠️ Qloo's brand entities map to *brands*, not *SKUs*. A boutique needs SKU-level advice. This is a real data-model mismatch, not a footnote.

### 4.6 People in recovery are structurally excluded from social life
- Recurring, specific, and emotional: *"I'm increasingly annoyed with the fact that every single social activity geared towards adults seems to always involve alcohol."* — [r/rva](https://www.reddit.com/r/rva/comments/1cfc5jy/where_to_hang_out_and_meet_new_people_when_youre/); *"I stopped going out, or even being invited out… It's a horrible culture."* — [r/london](https://www.reddit.com/r/london/comments/1hxre9s/where_do_sober_people_go/); *"it is hard and I wish there was more out there"* — [r/Sober](https://www.reddit.com/r/Sober/comments/1cueq1l/23m_how_do_i_find_sober_social_things_to_do_with/)
- Four separate subreddits (r/Sober, r/SoberCurious, r/stopdrinking, r/AskChicago) contain the same request in different words. Demand for solutions is real (see The Phoenix, Sober Climb Club, Sauna & Sobriety, dry bars).
- ⚠️ **Critical:** Qloo has no verified "sober-friendly" or "alcohol-free" tag. Any solution must be built on entity attributes you can *verify* (place categories, hours, price level) plus an explicit honesty rule. Do **not** invent a sobriety tag.

### 4.7 Personalised activity is the evidence-backed intervention for dementia — and it's taken
- Cochrane review of personally tailored activities for people with dementia: may reduce challenging behaviour and **slightly improve quality of life**; effects on caregiver burden were **not clearly significant** (MD −0.62, 95% CI −3.08 to 1.83). Be honest: the evidence is *low-certainty*. — [PMC8094398](https://pmc.ncbi.nlm.nih.gov/articles/PMC8094398/)
- Music engagement specifically: musical memory is among the last to deteriorate; personalised playlists improve cooperation, reduce resistance to care and agitation. — [Music & Memory caregiver guide](https://musicandmemory.org/wp-content/uploads/2021/08/Guide-to-Creating-Personalized-Playlists.pdf) · [Dementia Australia](https://www.dementia.org.au/living-dementia/staying-connected/activities-people-dementia)
- Activity type tracks disease stage (music/entertainment peaks at *moderate* dementia). — [PMC5881689](https://pmc.ncbi.nlm.nih.gov/articles/PMC5881689/)
- ⚠️ **Resonance already occupies this exact space in the current hackathon.**

---

# Part 3 — 15 Project Ideas, Fully Specified

Format: each idea carries the 25 requested fields in compact form, then its 10 scores.
Weights used for the overall (see §5 for rationale): **Qloo dependency 0.18 · Real-world impact 0.16 · Novelty 0.14 · Technical feasibility 0.12 · Demo potential 0.12 · Data feasibility 0.08 · Saturation-resistance 0.06 · Agentic depth 0.06 · Judge appeal 0.05 · Product potential 0.03**

Saturation-resistance is scored **10 = uncrowded, 1 = a lane with 4+ direct competitors**.

---

## IDEA 1 — **Adjacent**
### (working subtitle: *"The people who'd already love you, and the program that brings them in."*)

**2 · One-line concept.** An audience-development agent for cultural institutions that uses the Qloo taste graph to name the specific, non-obvious cultural cohorts most likely to become their audience, show where in the city those people actually live, and propose a falsifiable program + outreach test.

**3 · Real user / problem.** A performing-arts organisation, museum, indie cinema or festival has a shrinking, ageing audience and no way to describe the people who aren't coming. Every analytic tool they own (ticketing CRM, TRG/DataArts dashboards, Meta lookalikes) is built from data about people who already bought — so it can only ever find *more people like their current audience*, which is the strategy that produced the decline.

**4 · Evidence.** BSO −40% over 20 years; NEA classical attendance 8.6%→4.6% (2017→2022); TRG Arts' 163-org dataset shows ~9% fewer tickets sold 2018→2025; symphony replacement rate 0.907; Wallace Foundation concludes the literature offers "no obvious solutions"; the field itself names "lookalike targeting" as the broken model; 80% attendance drop-off by one mile. Full sources in §4.1.

**5 · Target users.** Programming directors, executive directors, marketing/audience-development leads, and development (fundraising) leads at mid-size cultural institutions; plus the funders who require audience-development plans. Secondary: indie cinemas, comedy clubs, museums, festivals, and cultural presenters.

**6 · Exact workflow.**
1. User pastes or searches their last 1–2 seasons (5–12 works/artists/titles) and their venue address + main city.
2. Agent resolves every item to Qloo entity IDs (`describe` / `/search`), flagging anything ambiguous rather than guessing.
3. Agent derives the institution's **Taste DNA** — the tags that describe the programme (`filter.type=urn:tag`, `signal.interests.entities=<season>`), plus the programme's age/gender skew (`filter.type=urn:demographics`).
4. Agent fans out across domains (`artist`, `movie`, `book`, `brand`, `place`) to find **high-affinity, low-obviousness adjacencies**, ranked on two axes: *affinity strength* vs *distance from the current audience* (novelty).
5. Agent calls the **heatmap** for the city with the season as signal → where that taste concentrates, block by block. Cross-references against the institution's own address and (optionally) a supplied patron postcode list.
6. Agent proposes **3 candidate additions to the programme** and scores each against both audiences (`filter.results.entities` scoring in both directions) plus `analysis/compare` between the current programme and each candidate.
7. Agent outputs a **one-page testable plan**: the cohort, the zips, the programme bet, the outreach budget split, the metric, the falsification condition — and the Qloo call trace + `feature.explainability` receipts behind every claim.

**7 · What the AI agent does.** It is a **research loop with a budget**, not a single prompt: it plans which adjacencies to explore, executes bounded Qloo tool calls, evaluates coverage, decides whether to widen or deepen, resolves ambiguity by asking, and refuses to answer when the graph returns nothing (rather than reverting to LLM priors). It owns a step budget and a call budget, and it narrates each decision.

**8 · Exactly where Qloo is used.** Six distinct, documented calls: `/search` (resolve season + venue), `/v2/insights?filter.type=urn:tag&signal.interests.entities=<season>` (Taste DNA), `/v2/insights?filter.type=urn:entity:{artist|movie|book|brand|place}&signal.interests.entities=<season>` (cross-domain adjacency), `/v2/insights?filter.type=urn:heatmap&filter.location.query=<city>&signal.interests.entities=<season>` (geo concentration), `/v2/insights?filter.type=urn:demographics` (skew), `/v2/insights?filter.type=urn:entity:artist&signal.interests.entities=<season>&filter.results.entities=<candidate slate>` (grade a slate), and `/v2/analysis/compare` (current vs candidate audience). Plus `feature.explainability=true` on every recommendation call.

**9 · Why Qloo is essential.** The core question — "which specific culture cohorts, described in measured terms, over-index on what we make, and where do they live?" — is a **graph query over measured cross-domain affinity**. There is no substitute dataset. It also cannot be derived from the institution's own data, because by definition the target people have never appeared in it. Qloo's FAQ explicitly positions the product as the fix for exactly this: *"designed to overcome cold starts and does not require customer data."*

**10 · What it does that a normal LLM cannot reliably do.** An LLM, given a season of Mahler and Caroline Shaw, will produce plausible-sounding marketing advice ("target younger audiences, use social video, programme more contemporary work"). It cannot produce: *"your programme's strongest cross-domain adjacency is with people who over-index on A24 psychological horror, natural-wine bars and vinyl record stores; that cohort's affinity is X–Y; and 58% of the cells in the top decile of that heatmap sit in three zips you have never mailed."* The LLM has no measurement, no geography, and no way to be wrong. Adjacent can be wrong, and shows you how to check.

**11 · What happens if Qloo is removed.** The product collapses to a generic arts-marketing advice generator — the exact saturated category (CulturePilot, Hayy, Marketify, TAVA, NexTate). The heatmap disappears, the affinity numbers disappear, the cohort names become plausible hallucinations, and the "measure the delta" claim becomes unfalsifiable. **Nothing of value survives.**

**12 · Qloo API capabilities required.** `/search` · `/v2/insights` with `filter.type` in {artist, movie, book, brand, place, tag, heatmap, demographics} · `signal.interests.entities` and `.tags` (with weights) · `filter.location.query` + `filter.location.radius` · `filter.popularity.min/max` · `filter.tags` / `operator.filter.tags` · `filter.results.entities` · `filter.exclude.entities` · `signal.demographics.age` + `.audiences` · `feature.explainability` · `/v2/analysis/compare` · `/v2/audiences` · `diversify.by=properties.geocode.city` for multi-city output.

**13 · External APIs / data required.** **None are strictly required.** Optional: a geocoding service to convert the venue address to lat/lon (Qloo's own `/search` on the venue usually returns `properties.geocode`), and Leaflet + OpenStreetMap tiles for the heatmap (free, and Qloo itself uses OSM/ODbL data — credit it). Real public data helps credibility: Census ACS median income by zip and the NEA/TRG benchmarks for the "what good looks like" baseline.

**14 · Does real public data exist?** Yes — richly. NEA SPPA participation rates, TRG Arts benchmark aggregates (published), SMU DataArts (free org-level dashboards for many US orgs), Census ACS for zips, and every institution publishes its own season. The demo runs entirely on public inputs plus Qloo.

**15 · MVP features.**
- Paste/search a season of 5–12 works; venue address; city
- Taste DNA panel (Qloo tags + age/gender skew, with the raw tag IDs shown)
- 3 ranked adjacent cohorts across ≥3 domains, each with affinity evidence and a novelty/safety slider
- Heatmap overlay of the cohort vs. the venue, with the top under-served zips named
- 1 recommended programme addition, scored against current audience *and* target cohort
- Full Qloo call trace panel: endpoint, parameters, HTTP status, result count, duration, cache state
- Honest-failure mode: if the graph returns nothing, the panel stays empty and says so

**16 · Advanced features.**
- Multiple candidate seasons side by side (A/B) via `analysis/compare`
- "What would a generic model say?" live toggle that actually calls a frontier LLM with the same prompt, so the comparison is real rather than simulated
- Export a one-page PDF board memo with the receipts appendix
- Cohort-drift monitor via `/v2/trending` over a date range
- Multi-city / touring-presenter mode using `diversify.by=properties.geocode.city`

**17 · Technical architecture.** Next.js (or Vite React) front-end → server route handler (secrets stay server-side) → Python FastAPI agent service (LangGraph or a hand-rolled planner loop with a tool registry: `resolve`, `taste_dna`, `adjacent_cohorts`, `heatmap`, `score_slate`, `compare`) → typed Qloo client with LRU response cache (6–24h), token-bucket rate limiter (~3 calls/sec), bounded retries on 429, a hard per-analysis call budget, and a full trace recorder → Postgres (or SQLite for the MVP) for saved analyses. Hosted on Vercel/Render. Leaflet for the map. No model training anywhere.

**18 · Implementation difficulty.** **Medium.** Six tool functions, a planner, a cache, a rate limiter, and a map. The genuinely hard parts are (a) designing the "novelty vs. affinity" ranking so it produces believable cohorts rather than noise, and (b) the honesty rules (no fabricated scores, every claim carries a receipt). One developer, ~5–8 focused days.

**19 · Hackathon demo story.** "This is a 900-seat concert hall in Cincinnati. Sixty-eight percent of its subscribers are over 60. Its marketing team has four people. Watch what happens when I paste their actual last season." → Taste DNA appears → **a cohort they would never have named appears with a number** → a map shows that cohort is concentrated 1.8 miles from the hall, in three zips that appear in zero of their mailings → the agent proposes one programme addition and shows that it holds the current audience score *up* while tripling the score for the new cohort → and it writes the sentence "this is falsifiable; here's the metric and here's the falsification condition."

**20 · Competitive landscape.** TRG Arts, SMU DataArts/DataArts suite, Capacity Interactive, WolfBrown/Arts Audience Analytics, Purple Seven, Spektrix Insights, Tessitura Analytics. All are **transactional** analytics: they describe your existing buyers. None can cold-start. Adjacent sits *upstream* of them (it generates the hypothesis they then measure) rather than competing with them — which is also the go-to-market story.

**21 · Existing similar products/projects.** No direct Qloo-hackathon competitor found. Closest adjacencies in the pool are CulturePilot / Hayy / TasteShip (brand marketing) and Quorum (synthetic audience research) — all different questions. Outside the pool: [Resonance AI](https://devpost.com/software/resonance-ai-1hjbf0) (2025, political messaging) and [Alloy](https://devpost.com/software/axiom-2bn391) (2025, M&A due diligence) are the same *shape* (institutional decision under uncertainty) in unrelated domains.

**22 · What makes it different.** It is the only idea in the pool whose output is a **decision with a falsification condition**, not a recommendation, plan, or piece of content. And it is the only one where the Qloo heatmap is load-bearing rather than decorative.

**23 · Risks.** (a) Qloo's artist coverage for niche/regional ensembles may be thin; (b) heatmap may behave differently in smaller metros; (c) cohort definitions can read as sociology-flavoured astrology if the affinity deltas are small; (d) nonprofit buyers have little budget.

**24 · How judges might criticise it.** *"This is a marketing plan generator — that category is saturated."* · *"Nonprofits can't pay."* · *"You're inferring that an affinity for A24 films means someone will buy a concert ticket."* · *"Where's the proof your recommendations beat the status quo?"*

**25 · How to defend.** (a) It is not a marketing generator: it produces a *measured cohort + geography + a test*, and explicitly refuses to produce prose without a Qloo receipt — show the code path that empties the panel. (b) The buyer is not only the org: funders, arts service organisations and touring presenters buy audience data, and the same engine sells to indie cinemas, museums and festivals. (c) Adjacency is not a purchase prediction and the product must say so — Qloo's own terms describe output as "correlative inferences." Frame it as *prioritisation*, and pair it with the org's own measurement. (d) Show the pre-registered comparison against a live LLM baseline *and* cite the 1-mile distance-decay research that makes the geography meaningful rather than decorative.

**Scores.** Qloo dep **10** · Impact **9** · Novelty **9** · Tech feasibility **9** · Demo **8.5** · Data feasibility **9** · Saturation-resistance **8** · Agentic depth **9** · Judge appeal **9** · Product potential **7.5**
**Weighted overall: 8.97**

---

## IDEA 2 — **Undertow**
### (*"The culturally right song, for a scene, in 48 hours."*)

**2 · Concept.** A music-supervision agent that converts a scene brief (script excerpt, era, mood, reference tracks, target demographic) into a shortlist of real artists with measured audience affinity — biased toward *under-licensed, affordable, non-obvious* catalogue — each with a receipt and a rights-readiness checklist.

**3 · Problem.** Music supervisors and the producers who can't afford one must find, vet and clear a track in 48–72 hours, against hundreds of competing pitches and shrinking budgets. The bottleneck is *fit plus friction*: supervisors reject music for metadata and clearance reasons ("be less work"), and the market is a "who-you-know" business that systematically excludes independent catalogue.

**4 · Evidence.** RA Pro (Nov 2025): "the sync industry has historically been a 'who-you-know' business"; supervisors "don't always have time to dig for niche tunes." Supervisors receive hundreds of cold pitches weekly and delete almost all; a TV episode may have a 48-hour clearance window; agencies process 500+ submissions/day; metadata gaps are the fastest route to being skipped. Two-thirds of a $1.6bn stock-music industry exists precisely because supervisors need speed. Sources in §4.3.

**5 · Target users.** Independent music supervisors, boutique sync agencies, in-house ad-agency producers, indie film/TV producers, game audio leads, and (as a paid upsell) independent artists/labels who want to understand which briefs they're closest to.

**6 · Workflow.** Paste scene text or pick a scene archetype → choose era/decade, territory, content constraints, and a "reach vs. safety" slider → optionally name 1–3 reference tracks ("feels like early Portishead but isn't famous") → agent resolves references and the scene's adjacent film/TV entities → runs cross-domain affinity into `urn:entity:artist`, constrained by release decade proxy (`filter.tags` for genre/era) and **`filter.popularity.max`** to keep the list under-famous → scores the shortlist against `signal.demographics.age` matching the target audience → checks `trending` to flag tracks/artists already saturated → returns a ranked top 8 with affinity receipts, a "why this fits the scene" line grounded only in returned tags, and a rights-readiness checklist per candidate (with an explicit disclaimer that Qloo cannot verify ownership).

**7 · Agent.** Multi-step with a **constraint solver** at its centre: it must satisfy creative fit + popularity ceiling + demographic target + territory simultaneously, and it must ask the user to resolve ambiguity in the scene brief rather than inventing it. It also runs a self-critique pass: "does my shortlist actually satisfy the popularity ceiling I was given?"

**8 · Qloo used.** `/search` (reference tracks/artists, scene-adjacent films) · `/v2/insights?filter.type=urn:entity:artist&signal.interests.entities=<references>&signal.interests.tags=<mood/genre>&filter.popularity.min/max=<ceiling>&filter.tags=<era>` · `/v2/insights?filter.type=urn:entity:movie|tv_show` to derive the scene's cultural neighbourhood · `filter.type=urn:demographics` for audience age fit · `/v2/trending` to flag saturation · `feature.explainability` for the "why".

**9 · Why Qloo essential.** Qloo is the only dataset that can answer "which artists do the people who love *this specific constellation of films and references* also love, that are not yet famous?" — a joint query over affinity, taste similarity and popularity percentiles. Streaming APIs give popularity without affinity; LLMs give affinity without measurement or a popularity index.

**10 · vs. a normal LLM.** An LLM asked for "a track like early Portishead for a 90s Detroit night-drive scene" returns Portishead, Massive Attack, Tricky, Sneaker Pimps — i.e. the *expensive, obvious, already-licensed* answers. Undertow returns artists at the *same measured taste coordinates* with a popularity percentile low enough to be affordable, plus a numeric reason.

**11 · Without Qloo.** It becomes a mood-based Spotify-style recommender — a thing that already exists in every supervisor's DISCO/Songtradr search box. Dead on arrival.

**12 · Capabilities.** `/search` · `urn:entity:artist` + `urn:entity:movie`/`tv_show` insights · `signal.interests.entities`/`.tags` with weights · **`filter.popularity.min/max`** (the load-bearing parameter) · `filter.tags` + `operator.filter.tags` · `filter.release_year.min/max`, `filter.release_country`, `filter.content_rating` · `signal.demographics.age/gender` · `/v2/trending` · `feature.explainability`.

**13 · External APIs.** Optional: MusicBrainz / Discogs / ListenBrainz for real catalogue metadata and rights signals (composer splits rarely public). Optional LLM for scene parsing. No paid API is required for the MVP.

**14 · Real data?** Yes. Qloo supplies artists, films, TV, tags, popularity and demographics. Real scene briefs are publicly posted on sync-opportunity boards (e.g. [artistportal.studio](https://artistportal.studio/music-sync-opportunities) lists live briefs like "early 90s radio songs, no covers, Olympics film"). That gives you *real* briefs to demo against.

**15 · MVP.** Scene-brief input (text or 6 archetypes) · era + territory + popularity ceiling controls · ranked top 8 with affinity receipts · "why this fits" lines grounded only in returned tags · saturation flags · rights-readiness checklist per candidate · full Qloo trace.

**16 · Advanced.** Reference-track "sounds like but isn't" mode · a cost/obscurity frontier chart (affinity vs. popularity, showing the efficient frontier) · supervisor-side shortlist scoring ("grade my 20 candidates against this brief") · artist-side reverse mode ("which live briefs am I closest to?") · territory/original-version filtering using `filter.release_country`.

**17 · Architecture.** Same skeleton as Idea 1: React front-end → FastAPI/LangGraph agent → typed Qloo client (cache, limiter, retry, budget, trace) → Postgres. Add a small local brief-parser (rule-based + one LLM call) so the agent has structured input. Optional MusicBrainz enrichment worker.

**18 · Difficulty.** **Medium.** Slightly harder than Idea 1 because brief parsing is fuzzy and because the rights-readiness layer needs honest boundaries.

**19 · Demo story.** Paste a real three-line scene from a screenplay. Reference: "feels like early Portishead." Press go. The screen shows the agent resolving the reference, then fanning out, then *the frontier chart*: a scatter where the x-axis is Qloo popularity and the y-axis is affinity, with the user's chosen ceiling drawn as a line — and the agent has picked the six artists sitting in the top-left corner. Then the punchline: the "obvious" answers (Portishead, Massive Attack) are shown too, sitting high on popularity, labelled "what every other supervisor is pitching today."

**20 · Competitive landscape.** DISCO, Songtradr, Music Vine, Soundstripe, Artlist (stock/library), Marmoset, SyncFloor, TunedGlobal (rights-licensed curation), [SyncVision](https://github.com/TheLyricalLuminary/SyncVision) (clearance triage — explicitly not taste). Streaming DSP recommendation and "similar artist" tools (Spotify, MusicBrainz/ListenBrainz) give similarity without measured audience affinity or a popularity index for licensing leverage.

**21 · Existing similar projects.** No Qloo-hackathon entry found for sync. The non-Qloo [SyncVision](https://github.com/TheLyricalLuminary/SyncVision) is the closest product and explicitly disclaims cultural context, which is the gap Undertow fills — cite it as validation and as a boundary.

**22 · Differentiator.** The **affinity-vs-obscurity frontier**. Nobody else ranks by "measured audience fit divided by how famous you are." That is a genuinely novel framing, and it is the whole commercial thesis of the indie-sync market.

**23 · Risks.** (a) Qloo cannot verify rights, one-stop status or ownership — the most important factor in the real workflow; (b) Qloo has no BPM/mood/instrumentation attributes for tracks (it has *artists*, and tags like `urn:tag:genre:media:*`), so "sad piano under two minutes" is not answerable; (c) supervisors may see it as another pitch pipeline.

**24 · Criticisms.** *"The hard part of sync is clearance, not discovery — you solved the easy half."* · *"You're ranking artists, not tracks."* · *"Supervisors don't need another list."*

**25 · Defence.** (a) Be explicit and honest: the product's job is to **compress the search space** and then hand over a rights-readiness checklist; say so on screen. In fact, turning the limitation into a visible feature is exactly what judges rewarded in the 2025 winners. (b) Yes — and that is honest: the artefact supervisors license is the master, but the *brief* is "an artist who sounds like X"; offer a "candidate track" slot where the supervisor pastes their catalogue and the agent scores it. (c) That's the strongest objection; the counter is the frontier framing: this list is *priced to be cleared*, which is the job supervisors actually fail at.

**Scores.** Qloo dep **9** · Impact **8** · Novelty **9.5** · Feasibility **8.5** · Demo **9** · Data feasibility **7** · Saturation-resistance **9** · Agentic **8.5** · Judge appeal **9** · Product **8**
**Weighted overall: 8.71**

---

## IDEA 3 — **Greenlight**
### (*"Which catalogue titles should this service license for this market?"*)

**2 · Concept.** A content-acquisition agent for streamers, broadcasters, AVOD/FAST channels and distributors that ranks *available* catalogue titles for a target market and audience segment using measured affinity rather than acquisition-exec instinct.

**3 · Problem.** Content acquisition and commissioning is one of the largest recurring spends in media. Decisions are made by small teams reading spreadsheets of availability plus gut feel, and they systematically over-index on global hits and under-serve regional taste — which is exactly the complaint that shows up in churn data.

**4 · Evidence.** Qloo's own client roster includes **Netflix** and its FAQ lists "anonymised API Ecosystem Learning Rights (Fortune 500 Financials, JCDecaux, Michelin, Samsung, Netflix)". Independent corroboration: *"a streaming client in Asia was able to prioritise regionally-specific results over globally popular recommendations and tune the algorithm accordingly"* — [TechCrunch, 2022](https://techcrunch.com/2022/08/23/qloo-raises-cash-to-expand-its-ai-driven-recommendation-api/). IFE/hospitality content programming has the same structure and the same documented "cultural sensitivity vs. demographic diversity" tension. *(The pain is well-attested at the mature-player level; I did not find a public study quantifying mid-market acquisition waste — treat impact evidence as strong-but-inferential.)*

**5 · Target users.** Content acquisition/commissioning leads at mid-size streamers, FAST/AVOD operators, regional broadcasters, airlines' IFE content teams, hotel group entertainment teams, museums' film programmes, festival curators.

**6 · Workflow.** Pick a market (country + region) and a target segment (age, gender, audience category) → paste or search the *available* slate (or a competitor's current slate as a proxy) → agent profiles the segment's taste across domains → ranks the available titles by affinity for that market, with `filter.release_country` and `filter.release_year` constraints → clusters the slate to avoid redundancy (`diversify.by`) → checks `/v2/trending` to separate durable from momentary popularity → returns a graded acquisition slate with a per-title evidence line and an "already over-indexed globally" flag.

**7 · Agent.** A portfolio optimiser: it must produce not just a ranked list but a *balanced slate* — it runs the affinity ranking, then a diversity/clustering pass, then a cannibalisation check (which titles appeal to the same sub-segment), then writes the acquisition memo.

**8 · Qloo used.** `/search` (resolve titles) · `/v2/insights?filter.type=urn:entity:movie|tv_show&filter.results.entities=<available slate>&signal.demographics.audiences=<segment>&signal.demographics.age=<bucket>&filter.release_country=<market>&filter.release_year.min/max` · `filter.type=urn:demographics` for the slate's natural skew · `/v2/trending` for durability · `diversify.by=properties.geocode.city` for multi-territory output · `analysis/compare` to benchmark against the incumbent slate.

**9 · Why Qloo essential.** *"What does this specific market's 25–34 segment over-index on that is also available to license, and what have we already got too much of?"* requires cross-domain affinity + demographic conditioning + geographic market framing in one query. No ratings vendor (Nielsen, Parrot, PlumResearch, Antenna) answers it; they measure what was already watched, which is the incumbent-bias trap.

**10 · vs. an LLM.** An LLM recommends famous titles it has memorised. Greenlight ranks a *supplied available slate* by measured market affinity — including titles the model has never heard of.

**11 · Without Qloo.** Becomes "GPT recommends 20 films for Brazil" — useless, and demonstrably biased toward Western canon.

**12 · Capabilities.** `urn:entity:movie` + `urn:entity:tv_show` insights · `filter.results.entities` (grade my slate — essential) · `filter.release_country`, `filter.release_year.*`, `filter.content_rating`, `filter.rating.*`, `filter.popularity.*` · `signal.demographics.age/gender/audiences` with weights · `urn:entity:person` for cast/creator affinity · `/v2/trending` · `diversify.by` · `analysis/compare`.

**13 · External APIs.** Optional: a streaming-availability dataset (JustWatch) to make "available to license" real; TMDB/OMDb for artwork and metadata. Not required for the MVP if you treat the slate as user-pasted.

**14 · Real data?** Yes — user-pasted slates are real; public catalogues exist; TMDB/JustWatch are free-tier. Qloo covers the affinity and demographic layer.

**15 · MVP.** Market + segment selector · pasted slate input (CSV or search) · ranked slate with affinity evidence · over-indexed/under-served gap analysis · redundancy clustering · acquisition memo export.

**16 · Advanced.** Incumbent-slate benchmarking via `analysis/compare`; a "taste gap" heatmap per market showing where the slate under-serves; multi-territory portfolio mode; a churn-risk proxy built from segment coverage; a scenario mode ("if we could only license 10, which 10?").

**17 · Architecture.** FastAPI + LangGraph agent with slate-scoring and portfolio-optimisation tools; React front-end with a spreadsheet-like slate editor; Qloo client with trace; Postgres. Optional JustWatch/TMDB enrichment.

**18 · Difficulty.** **Medium.** The optimisation layer (clustering + cannibalisation) is the only non-trivial part.

**19 · Demo story.** Two markets, one slate. "Same 40 available titles. Left column: what a global-popularity ranking recommends. Right column: what Qloo says the 25–34 cohort in São Paulo over-indexes on." The two lists barely overlap — and the agent names the specific titles in the overlap-gap and says what they cost you in segment coverage.

**20 · Competitive landscape.** Parrot Analytics (demand measurement), Nielsen, PlumResearch, Antenna, Ampere Analysis, Luminate, Kantar. Content-aggregator marketplaces (DistroTV, Filmhub, Magnolia). All measure *observed demand* or serve licensing logistics; none model *latent cross-domain affinity by market segment*.

**21 · Existing projects.** Nothing in either Qloo hackathon. Closest in-pool: Beacon Base's "product discovery & market insights" (2025) — a different domain and a different method.

**22 · Differentiator.** Portfolio optimisation rather than ranking, and a *latent*-demand rather than *observed*-demand signal — the only kind of signal that can identify a market's unmet appetite rather than its existing habits.

**23 · Risks.** (a) Hard to demo compellingly — a spreadsheet of titles is less exciting than a map; (b) you can't validate the recommendation without real acquisition data; (c) "would work without Qloo?" — it *would*, in the sense that an LLM could rank a slate; the Qloo value depends entirely on the audience signal being credible, so the demo must prove it with receipts.

**24 · Criticisms.** *"This is just a ranking."* · *"Unfalsifiable — you can't test it."* · *"Enterprise sales, not a hackathon product."*

**25 · Defence.** (a) Show the portfolio layer and the cannibalisation analysis, not just a list. (b) Be honest and pre-register a validation design (hold out a title a platform *did* acquire and see whether Greenlight would have surfaced it — a backtest anyone can run). (c) The hackathon explicitly rewards "agent-powered app" over consumer toy; and Design criterion is about coherence, not consumer scale.

**Scores.** Qloo dep **9** · Impact **8.5** · Novelty **8.5** · Feasibility **8** · Demo **6.5** · Data **7.5** · Saturation-resistance **9.5** · Agentic **8** · Judge appeal **8.5** · Product **8**
**Weighted overall: 8.35**

---

## IDEA 4 — **Reading Room** (working title)
### (*Brand-integration matchmaking for film & TV*)

**2 · Concept.** Given a script's scene — or a commission's audience — an agent finds the brands that the *audience* would actually accept in that context, and the ones that would break it, with measured evidence.

**3 · Problem.** Branded entertainment and product placement are multi-billion-dollar markets where fit memos are written by two agencies using instinct and prior relationships. The failure mode is expensive and public: an integration that reads as cynical and damages both parties.

**4 · Evidence.** Qloo's client list includes **JCDecaux** — whose published case study is precisely "understand the cultural nuances and preferences of the consumers that pass by our placements so advertisements truly resonate" — [Qloo/JCDecaux case study](https://www.qloo.com/resources/jcdecaux-case-study). This proves the *method* is commercially deployed for media/brand fit; it does not by itself prove the film-integration pain, which is *(partly inference from industry structure)*.

**5 · Target users.** Studio branded-entertainment teams, brand-side sponsorships/partnerships leads, product-placement agencies, branded-content studios, games publishers.

**6 · Workflow.** Paste scene text + target audience (or the production's measured audience profile) → agent resolves scene-adjacent media entities → profiles the audience across brands, music, places and media → scores a supplied candidate brand list *and* generates a discovery list → outputs an ordered fit list with a "risky / on-brand / off-brand" banding, a per-brand evidence line, and a "what the audience would rather see instead" set.

**7 · Agent.** A dual-mode matcher: **grade** (score my brand list) and **discover** (find brands I haven't considered), plus a conflict pass (is this brand already saturated in this genre? is it attached to a competitor's property?).

**8 · Qloo used.** `/search` (brands + scene media) · `/v2/insights?filter.type=urn:entity:brand&signal.interests.entities=<scene media>&signal.demographics.age/gender=<audience>` · `filter.results.entities=<candidate brands>` to grade the shortlist · `/v2/insights?filter.type=urn:entity:brand&filter.popularity.min/max` to find challenger brands willing to pay more · `feature.explainability` for the memo.

**9 · Why Qloo essential.** The question is a *measured* affinity between a brand's audience and a narrative context. Only a cross-domain taste graph holds brand↔media affinity at scale, and `filter.results.entities` lets you score a studio's actual shortlist, which is the workflow artefact.

**10 · vs. LLM.** An LLM produces plausible placements ("a character drinks a Coke") using memorised cultural stereotype. Qloo produces *the specific challenger brand whose audience overlaps this scene's audience most strongly* — frequently not the one anyone would have pitched.

**11 · Without Qloo.** A creative-writing toy. Nothing survives.

**12 · Capabilities.** `urn:entity:brand` insights (with `filter.results.entities`, `filter.popularity.*`) · `urn:entity:movie`/`tv_show` signals · `signal.demographics.*` · `feature.explainability` · `analysis/compare` for A/B scene versions.

**13 · External APIs.** Optional LLM for scene parsing. Nothing else required.

**14 · Real data?** Qloo side yes. Public scripts/scene descriptions exist for well-known films; for the demo, use a real public screenplay excerpt.

**15 · MVP.** Scene input · audience selector · graded shortlist + discovery list · fit bands with evidence · export memo.

**16 · Advanced.** A/B alternative integrations via `analysis/compare`; a "brand fatigue" check against trending; sponsorship package value estimation via audience-size × affinity; genre-level brand maps.

**17 · Architecture.** Standard: React → FastAPI agent → Qloo client → Postgres.

**18 · Difficulty.** **Medium-low.**

**19 · Demo story.** Show a scene: "post-breakup night drive." Ask a frontier LLM live for five integration ideas — you get the obvious list. Then run the agent: it names three challenger brands with the affinity numbers, and flags that two of the LLM's suggestions are actively off-audience.

**20 · Competitive landscape.** Branded-entertainment agencies, Hollywood Branded, BENlabs, ProductPlacement.com, StoryFit (script analytics), Nielsen Sports/BrandImpact, YouGov brand-health, GWI. StoryFit is the closest structural analogue but does script-and-audience analysis, not cross-domain affinity.

**21 · Existing projects.** Cold-Open (B2B partnership lead gen) is the nearest Qloo-hackathon neighbour and is the same *shape* (affinity → partner list). That's a meaningful overlap: judges may see it as "Cold-Open for film." Mitigation: the dual grade/discover mode on a *narrative context* is genuinely different, but the similarity is real and this is why it is not the final recommendation.

**22 · Differentiator.** Context-conditioned brand fit (scene + audience), not company-to-company fit.

**23 · Risks.** (a) Shape-overlap with Cold-Open; (b) no public ground truth to validate against; (c) Qloo brand coverage skews global/consumer — sub-brands and B2B brands may be thin.

**24 · Criticisms.** *"Cold-Open already did this."* · *"This is subjective — how is a brand fit 'measured'?"* · *"It's an agency tool for a market you can't reach."*

**25 · Defence.** (a) Show the scene-conditioning and the grade/discover duality, and cite the difference explicitly in the write-up rather than hoping the judge notices; honestly, though, if you want this domain, accept that you're differentiating against a live competitor. (b) Ground it: every band is backed by an affinity number and the audience cohort it came from; avoid adjectives without numbers. (c) Market size is large and Qloo already sells to this buyer shape (JCDecaux).

**Scores.** Qloo dep **9** · Impact **7.5** · Novelty **7.5** · Feasibility **8.5** · Demo **8.5** · Data **7** · Saturation-resistance **6.5** · Agentic **7.5** · Judge appeal **8.5** · Product **7.5**
**Weighted overall: 8.13**

---

## IDEA 5 — **Good Neighbour**
### (*A gift that isn't a gift card: cold-start gifting from three cultural breadcrumbs.*)

**2 · Concept.** You describe someone in a sentence; the agent converts it into cultural signals, runs a cross-domain affinity expansion, applies hard constraints (budget, distance, what they already own, age-appropriateness), and returns a small set of specific, defensible gifts across *multiple domains* — including experiences, not just things.

**3 · Problem.** Gift-giving is a universal recurring decision with high emotional stakes and genuinely poor tooling. Amazon's "frequently bought together" and ChatGPT's listicle answers both produce generic, low-signal suggestions precisely when the buyer knows little about the recipient.

**4 · Evidence.** Recurring, well-formed pain in public forums: *"I just don't know what to get him. He buys everything he wants so it makes it hard"* — [r/GiftIdeas, Mar 2026](https://www.reddit.com/r/GiftIdeas/comments/1rs0s3d/gift_ideas_for_a_boyfriend_who_buys_everything_he/). The canonical advice thread's top answers are gift cards, food baskets, socks and "write things down through the year" — i.e. the market admits it has no solution — [r/AskReddit](https://www.reddit.com/r/AskReddit/comments/9ey89f/whats_a_good_go_to_gift_for_someone_when_you_have/). **Flagged: this is the weakest quantitative evidence in my set.** It is a universally recognised pain, not a documented crisis. Do not oversell it.

**5 · Target users.** Anyone buying a gift (billion-dollar market); secondarily, gifting platforms (Not Another Bill, Uncommon Goods), corporate gifting buyers, and card/hallmark-style retail.

**6 · Workflow.** Describe the person in free text ("my sister, 29, lives in Logan Square, loves Phoebe Bridgers and The Bear, cooks constantly, just moved, budget ~$75, hates clutter") → agent extracts candidate cultural signals → resolves each to Qloo entities, asking the user to disambiguate ("Phoebe Bridgers the musician, yes?") → runs cross-domain expansion into `artist`, `book`, `brand`, `place`, `movie` → applies constraints (`filter.location.query`, `filter.location.radius`, `filter.price_level.max`, `filter.tags`, `filter.exclude.entities`) → returns ~7 options spanning *at least three domains*, each with an affinity receipt and a personalisation sentence → the user marks what they'd actually give, and the agent re-ranks with `signal.interests.entities.include` on the accepted seeds.

**7 · Agent.** A constraint-problem solver with an interaction loop: parse → disambiguate → expand → constrain → rank → learn from rejections. It must handle the *negative* constraints ("hates clutter") which LLMs tend to ignore.

**8 · Qloo used.** `/search` (recipient's stated favourites) · `/v2/insights?filter.type=urn:entity:{artist|book|brand|place|movie}&signal.interests.entities=<seeds>&filter.location.query=<city>&filter.location.radius=<m>` · `filter.price_level.max` / `filter.price_range.to` (budget, place entities) · `filter.exclude.entities` (things they own / already gifted) · `signal.demographics.age` (age-appropriate) · `filter.popularity.max` (find non-obvious options rather than the top-40 answer) · `feature.explainability`.

**9 · Why Qloo essential.** **Cross-domain inference from a near-empty input is the entire product.** The interesting gift is almost never in the same category as the stated interest — it's "she loves Phoebe Bridgers and cooks, so the best thing in the graph is a natural-wine tasting at *this specific bar* two miles from her flat plus *this specific cookbook*." That jump requires measured cross-domain affinity plus geography. A search engine cannot do it; an LLM will fake it.

**10 · vs. LLM.** LLM: "a record player, a cookbook, a candle, a gift card." Good Neighbour: named entities with affinity numbers, in her city, inside her budget, excluding things she owns.

**11 · Without Qloo.** It's a prompt wrapper over a gift-idea listicle. Zero moat.

**12 · Capabilities.** Multi-domain `urn:entity:*` insights · `signal.interests.entities` (+ `.include`) · `filter.location.query` / `filter.location.radius` / `filter.geocode.*` · `filter.price_level.min/max`, `filter.price_range.from/to` · `filter.popularity.min/max` · `filter.exclude.entities` / `.query` · `filter.hours` (is it open this weekend?) · `filter.external.exists=resy|michelin` (bookable experiences) · `signal.demographics.age` · `feature.explainability`.

**13 · External APIs.** Optional and additive: a booking link (Resy/OpenTable), Eventbrite or Ticketmaster for experience availability, a shopping affiliate API for brand products. **Not required for the MVP** — the MVP can return named entities + a link-out, which is honest.

**14 · Real data?** Qloo supplies entities, geo, price level, hours, Resy/Michelin flags. Experience availability needs one more API if you want clickable booking.

**15 · MVP.** Free-text recipient description · disambiguation step · ≥3-domain gift set with receipts · budget + distance + exclusions honoured · reason sentence per gift · "not this one" feedback loop that re-ranks.

**16 · Advanced.** Team/committee gifting (bundle multiple recipients' tastes via `analysis/compare` to find a joint gift); occasion-aware mode; a "regift risk" check against trending (don't buy the thing that's about to be everywhere); a wishlist-safety mode using `filter.exclude.entities`; group-gift splitting.

**17 · Architecture.** React → FastAPI/LangGraph agent (tools: `parse_recipient`, `resolve`, `expand_cross_domain`, `apply_constraints`, `rank`, `learn`) → Qloo client with trace + cache → Postgres for saved recipients. One optional LLM call for parsing and one for the personal note.

**18 · Difficulty.** **Low-medium.** The cleanest build in this list. One person, 3–5 days.

**19 · Demo story.** Judge-facing, high relatability: "Here's my best friend. Eleven words." Paste → the agent asks one clarifying question → returns a shortlist where **the top item is not a product at all** — it's a specific bar's tasting flight two miles from her apartment, because that's where the affinity graph and the geography agree — plus a book, plus a brand, each with numbers. Then the kill shot: run the same eleven words through a frontier LLM live and put the two answers side by side.

**20 · Competitive landscape.** Amazon's recommendation engine and "Gift Finder", Etsy's gift mode, Uncommon Goods, [GiftList](https://giftlist.com), Giftful, Wrapp, Snappy (corporate). All rely on **explicit** preference capture (a quiz, a wishlist, a category filter) or purchase history — none does cold-start cross-domain inference from unstructured text. That's the gap.

**21 · Existing projects.** **None found in either Qloo hackathon.** Genuinely novel in this competition — a strong "Quality of the Idea" play.

**22 · Differentiator.** Cold-start + cross-domain + hard constraints + experiences, from unstructured input. All four together, and each one alone is already uncommon.

**23 · Risks.** (a) Qloo has no SKU-level product data, so "gift" means *named brand / book / artist merch / place-based experience*, not a specific item — a genuine ceiling; (b) consumer product with no obvious revenue model; (c) "impact" reads small; (d) taste affinity ≠ gift success (a person can love jazz and own every jazz record).

**24 · Criticisms.** *"This is just recommendations — the thing the brief says not to build."* · *"The stakes are $50."* · *"Qloo can't actually tell me what to buy at a shop."* · *"No business model."*

**25 · Defence.** (a) Not a feed — it's a constrained decision with a stated rationale and an interaction loop; and the *distinction is demonstrable in 30 seconds* by putting it beside a live LLM. (b) Counter with universality: gift spend is enormous and the failure is universal — but concede the impact score honestly rather than inflating it. (c) Concede and design around it: the agent returns *directions with named entities* and says explicitly that it isn't a shopping engine. Honesty here reads as rigour. (d) Affiliate/booking revenue on the experience path, plus B2B corporate gifting, is the story — but it's a story, not a proof.

**Scores.** Qloo dep **8.5** · Impact **7** · Novelty **9.5** · Feasibility **9.5** · Demo **9.5** · Data **7.5** · Saturation-resistance **10** · Agentic **8** · Judge appeal **8.5** · Product **6**
**Weighted overall: 8.51**

---

## IDEA 6 — **Aisle**
*(Independent-retail assortment & merchandising agent)*

**2 · Concept.** A neighbourhood shop tells the agent where it is; the agent tells it what to stock, what to put in the window, what to play, and which local partner to cross-promote with — grounded in what the people within walking distance actually love.

**3 · Problem.** Independent retailers must decide assortment with no analytics function; 93% report struggling with assortment planning, and localisation to neighbourhood culture is a best practice that only chains can afford.

**4 · Evidence.** 93% of retailers struggle with merchandise assortment planning; 62% intend to buy analytics; regional/localised assortment is repeatedly named best practice — [Wave Grocery](https://www.wavegrocery.com/blogpost/what-is-assortment-planning-in-retail-how-to-optimize-it) · [Optimum Retailing](https://marketing.optimumretailing.com/blog/assortment-planning-what-every-retailer-needs-to-know). Weakness: the evidence is largely vendor-published.

**5 · Target users.** Independent boutiques, record shops, bookshops, speciality grocers, and small multi-site groups.

**6 · Workflow.** Enter the shop's Qloo place entity + a few signals (what sells, what doesn't) → agent profiles the local taste of the walkable catchment (heatmap + place affinity) → proposes brands to add and brands to drop (brand entity affinity conditioned on location) → proposes a window/display theme, an in-store playlist direction, and 2–3 local partner businesses → a weekly one-page brief.

**7 · Agent.** A monitoring + recommendation loop: it re-runs weekly, tracks what changed (`/v2/trending`), and reports deltas rather than regenerating everything.

**8 · Qloo used.** `/search` (the shop as a place) · `/v2/insights?filter.type=urn:heatmap&filter.location.query=<area>&signal.interests.entities=<shop>` · `urn:entity:brand` insights conditioned on `signal.location` + `signal.demographics.audiences` · `urn:entity:place` for partners · `filter.price_level` and `filter.tags` for positioning.

**9 · Why Qloo essential.** "Which brands do the people within a kilometre of *this specific shop* over-index on?" is a geospatial affinity query with no substitute.

**10 · vs. LLM.** LLM says "stock local favourites and seasonal items." Aisle names brands with affinity deltas for that catchment.

**11 · Without Qloo.** Generic small-business advice — a saturated genre with free incumbents.

**12 · Capabilities.** `urn:heatmap` · `urn:entity:brand` with `signal.location`/`signal.demographics.audiences` · `urn:entity:place` · `filter.tags`, `filter.price_level.*` · `/v2/trending`.

**13 · External APIs.** Optional POS/EPOS integration (Square, Shopify POS) to make "what sells" real. Not required for MVP.

**14 · Real data?** Partially. Qloo supplies brands + geo. Whether a *brand* maps to a *stockable SKU* for an indie shop is the weak link — see risks.

**15–17 · MVP / advanced / architecture.** MVP: shop profile → catchment taste report → 8 brand suggestions with evidence → 3 partner businesses → display theme → weekly delta report. Advanced: POS-integrated assortment gap analysis, supplier link-outs, multi-site clustering. Architecture: standard React → FastAPI agent → Qloo client → Postgres.

**18 · Difficulty.** **Low-medium.**

**19 · Demo story.** Pick a real record shop in a real city. Show the catchment taste map, then the brand list — including two brands that aren't records at all, which is the interesting bit. Then a browser-before/after of the window display concept.

**20 · Competitive landscape.** Shopify/Sidekick, Faire (wholesale marketplace with recommendations), Brightpearl, Vend/Lightspeed, Joor, Trendalytics, WGSN.

**21 · Existing projects.** Hayy (taste-grounded marketing for cafés) is close and in the pool. GeoTaste (2025 winner) covered business-location decisions. **This idea sits between two occupied positions.**

**22 · Differentiator.** Catchment-level taste rather than category-level trend.

**23 · Risks.** (a) **The brand→SKU mismatch is fundamental**; Qloo knows "Le Creuset" not "this specific Dutch oven in sage"; (b) Hayy overlap; (c) indie retailers are extremely price-sensitive and low-tech.

**24 · Criticisms.** *"Hayy already does taste-grounded retail marketing."* · *"You can't tell me what to buy from a wholesaler — your brands aren't SKUs."* · *"This is consulting, not a product."*

**25 · Defence.** (a) Differentiate on *assortment vs. marketing* — Aisle changes what's on the shelf, Hayy changes what's on Instagram — but accept the overlap is real. (b) Be explicit that the output is brand/category direction, not a purchase order, and link to Faire for fulfilment. (c) Weekly automated briefs are product, not consulting — but this is the weakest part of the case.

**Scores.** Qloo dep **8** · Impact **7.5** · Novelty **7** · Feasibility **8.5** · Demo **7** · Data **6** · Saturation-resistance **6** · Agentic **7.5** · Judge appeal **7** · Product **6.5**
**Weighted overall: 7.42**

---

## IDEA 7 — **The Long Table**
*(Constrained dining: faith, allergy, health and recovery constraints + actual taste)*

**2 · Concept.** A dining agent for people whose constraints aren't negotiable — halal, kosher, gluten-free, low-FODMAP, texture/chewing limits, alcohol-free — that finds places where the constraint *and* the taste both hold, and says honestly when it can't verify a constraint.

**3 · Problem.** People with hard dietary or religious constraints report being pushed to a generic "safe" subset of restaurants, or to the same three places. Constraint filters alone produce endless-undifferentiated results; taste alone produces unsafe ones. Nobody combines them.

**4 · Evidence.** The hackathon prompt itself names the adjacent case ("age-specific needs like easy-to-chew menus, low-heat delivery, medication-aware ingredients"). Broader evidence for constraint-driven dining difficulty is abundant in allergy/coeliac and faith-community forums, but **I did not find a rigorous published quantification** — treat as medium-strength, and note that the prompt's own mention means high submission saturation.

**5 · Target users.** Coeliac and allergy households; halal and kosher diners; people managing diabetes, IBS, or dysphagia; people in recovery avoiding alcohol-led venues; travellers with constraints; and the carers who plan meals *for* them.

**6 · Workflow.** Declare constraints (hard) and tastes (soft) → agent resolves taste seeds → runs place insights with `filter.tags` intersection (taste) plus constraint tags where verifiable (cuisine, dietary, category) → applies `filter.price_level`, `filter.hours`, `filter.location.radius`, `filter.external.exists=resy|michelin` if a reservation is wanted → returns ranked venues with a **per-constraint truth table**: verified / inferred / unverified — and the agent may not claim "verified" for anything Qloo doesn't actually hold.

**7 · Agent.** A constraint-first ranker with an honesty gate: it can *downgrade* a recommendation to "unverified" rather than assert safety, and it escalates to the user when a hard constraint cannot be confirmed.

**8 · Qloo used.** `/search` (resolve cuisine/dietary tags — **must first check which dietary tags actually exist**) · `/v2/insights?filter.type=urn:entity:place&signal.interests.entities=<taste seeds>&filter.tags=<cuisine|dietary tags>&operator.filter.tags=intersection&filter.location.query=<city>&filter.price_level.min/max&filter.hours=<day>` · `filter.external.exists`/Resy filters for bookability · `feature.explainability`.

**9 · Why Qloo essential.** The taste half of the query is only answerable from the graph — without it you're back to a filter list. The Qloo value is *finding the place that satisfies BOTH*, which is a conjunction across a measured affinity space and a categorical filter space.

**10 · vs. LLM.** An LLM hallucinates restaurant attributes and will confidently invent "gluten-free options." Qloo returns real entities with real tags, and you can build a UI that shows which tags drove the match.

**11 · Without Qloo.** A Yelp/Google Places filter clone. Yelp and Google already do filters better.

**12 · Capabilities.** `urn:entity:place` insights · `filter.tags` + `operator.filter.tags=intersection` · `filter.location.query` / `.radius` / `.geohash` · `filter.price_level.*` · `filter.hours` · `filter.external.exists` + Resy/Tripadvisor ratings · `filter.popularity.*` · `feature.explainability`.

**13 · External APIs.** For safety, a **verified** dietary source is needed (allergen menus, certifying bodies). This is the hard part and it is not in Qloo.

**14 · Real data?** Mixed. Qloo gives real places; verified dietary attributes require a second source or manual curation. **This is the central feasibility risk.**

**15–17.** MVP: constraint declaration → taste profile → ranked venues with per-constraint truth table → booking link. Advanced: carer multi-profile mode; low-heat/easy-chew proxies from cuisine tags; recovery-safe venue scoring (explicitly *not* a sobriety tag); weekly "new options" digest. Architecture: standard.

**18 · Difficulty.** **Medium**, spiking to hard if you attempt real constraint verification.

**19 · Demo story.** Two people, two hard constraints, one city. Show the agent refusing to over-claim: "I can confirm this venue is tagged Italian and gluten-free-friendly by Qloo's cuisine tags; I cannot confirm a dedicated fryer — here's the phone number and here's the question to ask." **The honesty is the wow**, because every other AI in this space will just say yes.

**20 · Competitive landscape.** Yelp, Google Maps, HappyCow, Find Me Gluten Free, Fig (allergen scanning), Spokin, Zabihah, OpenTable.

**21 · Existing projects.** No direct Qloo-hackathon entry found, **but** the challenge prompt explicitly suggests the senior-dining version. Expect many.

**22 · Differentiator.** Conjunction of measured taste and hard constraints, plus an explicit verification status per constraint.

**23 · Risks.** (a) Safety — any implied medical/dietary guarantee is a liability; (b) Qloo may not have granular dietary tags; (c) saturation, given the prompt hint; (d) verification requires a data source you probably can't get in 26 days.

**24 · Criticisms.** *"Yelp does filters."* · *"You can't verify allergens — this is dangerous."* · *"The prompt already suggested this; it's not creative."*

**25 · Defence.** (a–b) Build the product **around** the verification gap: the agent's honesty gate *is* the innovation and is defensible ethically. Never claim safety. (c) Hard to counter — this is why it is not the winner. (d) Be explicit that the constraint layer is a starting filter and the *agent's* contribution is the taste conjunction plus refusal-to-over-claim.

**Scores.** Qloo dep **7** · Impact **8.5** · Novelty **6** · Feasibility **6.5** · Demo **7.5** · Data **5.5** · Saturation-resistance **4** · Agentic **7.5** · Judge appeal **7.5** · Product **7**
**Weighted overall: 7.01**

---

## IDEA 8 — **Recovery Map**
*(Non-drinking social life navigation)*

**2 · Concept.** For people in recovery or who don't drink, an agent that turns "what do I do on Friday that isn't a bar" into a *specific, verifiable* plan built from their actual tastes — with an explicit rule that it never guesses whether a venue is sober-safe.

**3 · Problem.** Social life for adults is structurally organised around alcohol. People in early recovery describe losing their social world entirely, and generic advice ("join a club") doesn't produce a plan.

**4 · Evidence.** Strong for a Reddit-scale claim: *"I'm increasingly annoyed with the fact that every single social activity geared towards adults seems to always involve alcohol"* — [r/rva](https://www.reddit.com/r/rva/comments/1cfc5jy/where_to_hang_out_and_meet_new_people_when_youre/); *"I stopped going out, or even being invited out… It's a horrible culture"* — [r/london](https://www.reddit.com/r/london/comments/1hxre9s/where_do_sober_people_go/); repeated requests in [r/Sober](https://www.reddit.com/r/Sober/comments/1cueq1l/23m_how_do_i_find_sober_social_things_to_do_with/), [r/SoberCurious](https://www.reddit.com/r/SoberCurious/comments/1n0welb/nondrinking_activities_with_friends/), [r/stopdrinking](https://www.reddit.com/r/stopdrinking/comments/1dvfuqf/anyone_know_how_to_have_fun_sober/). Existing solutions named by users: The Phoenix (sober events non-profit), Sober Climb Club, Sauna & Sobriety, dry bars, run clubs.

**5 · Target users.** People in recovery (esp. first 90 days), sober-curious adults, people who don't drink for religious or health reasons, and the peers/families supporting them. Also: treatment centres, sober-living operators, and recovery-friendly employers.

**6 · Workflow.** User names 3–5 things they've genuinely enjoyed (music, food, films, sports, places) + city + weekend availability → agent expands cross-domain into places that are *categorically* not bars (climbing gyms, cinemas, bookshops, board-game cafés, galleries, parks, sports facilities, community venues) → filters by `filter.hours` for the specific day, `filter.price_level` for affordability, `filter.location.radius` for walkability → returns a concrete two-option plan with a "why this fits you" line, plus a "questions to ask before you go" list.

**7 · Agent.** A planner with an ethical gate: a **hard exclusion list** of categories (bars, nightclubs, breweries, distilleries, liquor stores) via `filter.exclude.tags`, plus an absolute refusal to assert that any venue is alcohol-free unless the data says so. It also holds the user's own stated boundaries and never nudges.

**8 · Qloo used.** `/search` (resolve taste seeds) · `/v2/insights?filter.type=urn:entity:place&signal.interests.entities=<seeds>&filter.location.query=<city>&filter.location.radius=<walkable>&filter.exclude.tags=<bar|nightclub|brewery|…>&filter.hours=<saturday>&filter.price_level.max=<n>` · `urn:entity:brand` for parallel hobby interests · `/v2/trending` to surface what's happening locally now · `feature.explainability`.

**9 · Why Qloo essential.** "Find me something to do that matches *my* taste and isn't drinking-related" requires taste transfer across domains plus categorical exclusion plus opening-hours and walkability constraints. Only a graph with place attributes + affinity does this in one pass.

**10 · vs. LLM.** An LLM gives "join a sports league, try pottery, volunteer" — true, generic, and unusable tonight. Recovery Map gives a named climbing gym with a Saturday intro session, a bookshop event, and a walkable route.

**11 · Without Qloo.** A Meetup/Yelp filter — already free, and it doesn't know you.

**12 · Capabilities.** `urn:entity:place` insights · **`filter.exclude.tags` + `operator.filter.exclude.tags`** (the load-bearing features) · `filter.hours` · `filter.location.query`/`.radius`/`.geohash` · `filter.price_level.min/max` · `filter.tags` · `/v2/trending` · `feature.explainability`.

**13 · External APIs.** Optional: Eventbrite/Meetup for live events; a support-group directory for the "community" layer. Not required.

**14 · Real data?** Qloo yes (places + hours + categories). Whether Qloo's place tags include enough non-alcohol categories reliably is **unverified** — test early.

**15–17.** MVP: taste intake → city + day + budget → two concrete plans with exclusion guarantees → "questions to ask" → trace panel. Advanced: a 4-week ramp plan that gradually expands radius/social density; a peer-matching mode (aggregate only, no PII); a treatment-centre dashboard. Architecture: standard, with a strict no-PII posture that matches Qloo's own privacy design (a genuine selling point).

**18 · Difficulty.** **Medium-low.**

**19 · Demo story.** Emotional and immediate: "It's day nine. I live in Minneapolis. I don't know what to do on Saturday." Two named options come back — one is a bouldering gym's beginner session, one is a record store's listening night — each with the affinity reason, the walk time, and the price. Then the panel that matters: **"things this agent will not claim"** — it lists every category it excluded and every question the user should ask. Judges remember products that admit limits.

**20 · Competitive landscape.** The Phoenix (non-profit sober events), Meetup, Bumble BFF, Sober Grid, I Am Sober, Smart Recovery, Rehabs.com directories. All are either event directories or peer networks — none is a personalised taste-grounded planner.

**21 · Existing projects.** None found in either Qloo hackathon.

**22 · Differentiator.** Taste-grounded (not event-directory-grounded) + an explicit ethical exclusion architecture.

**23 · Risks.** (a) No verified sobriety attribute in Qloo — the core honesty problem; (b) sensitive population — must never collect PII, and must not be positioned as treatment; (c) commercial model unclear (non-profit/healthcare partnership likely); (d) the exclusion-tag list requires empirical validation early.

**24 · Criticisms.** *"You can't know if a venue is safe — you're enabling someone."* · *"This is a list of gyms."* · *"Where's the money?"*

**25 · Defence.** (a) Turn it into the feature: the agent's job is to remove alcohol-led categories and never to assert safety; the user makes the call with a checklist. (b) Counter with the constraint architecture: hours, walkability, budget, exclusions and taste all at once — a list cannot do that. (c) Recovery healthcare, sober-living operators and employers fund this; say so plainly and don't pretend it's consumer subscription.

**Scores.** Qloo dep **7.5** · Impact **9** · Novelty **8.5** · Feasibility **7.5** · Demo **8.5** · Data **6.5** · Saturation-resistance **9.5** · Agentic **7.5** · Judge appeal **8** · Product **6.5**
**Weighted overall: 8.06**

---

## IDEA 9 — **Sensory Passport**
*(Accessible & sensory-considered outings for disabled and neurodivergent people)*

**2 · Concept.** An agent that plans outings matching a person's taste *and* their access requirements — step-free routes, quiet hours, low-sensory sessions, companion-friendly ticketing — and says honestly which requirements it could and could not confirm.

**3 · Problem.** Disabled and neurodivergent people and their families report that venue accessibility information is unreliable and that "family-friendly" recommendations ignore sensory load. Planning an outing takes hours of phone calls.

**4 · Evidence.** There is a large body of advocacy literature on inaccessible venue information and on autism-friendly/sensory-friendly programming (museums, cinemas, theatres run these sessions precisely because demand exists). **I did not find a rigorous quantified source in this research pass — flag as weak evidence.** The counter-argument is that this domain is important enough that weak evidence may still justify it, but a hackathon judge will ask "how do you know?"

**5 · Target users.** Disabled adults, families with autistic or sensory-sensitive children, carers, and (as buyers) venues' access officers and tourism boards.

**6 · Workflow.** Declare access requirements (hard) and tastes (soft) → agent finds taste-matched venues and events → overlays what can be confirmed → outputs a plan with a journey chain and a phone-call checklist.

**7 · Agent.** A constraint planner with an honesty gate, similar to Ideas 7 and 8 but with an added routing/journey layer.

**8 · Qloo used.** `urn:entity:place` with `signal.interests.entities`, `filter.location.radius`, `filter.hours`, `filter.exclude.tags`, `filter.price_level`; `urn:entity:destination` for trip-level planning.

**9 · Why Qloo essential.** Only the *taste* half is Qloo's; the access half is not. **Qloo dependency is therefore materially weaker than in Ideas 1–5** — the taste layer would be a nice-to-have rather than the differentiator.

**10 · vs. LLM.** Same structural answer as Idea 7.

**11 · Without Qloo.** An accessibility database with a personalisation skin. Still useful! Which is exactly the problem for this competition.

**12–17.** Standard, with the addition of an access-attribute layer (open data: Wheelmap, OpenStreetMap `wheelchair=*`, venue access pages) and a journey planner.

**18 · Difficulty.** **Medium-high** — the access-attribute layer is the hard part and Qloo doesn't supply it.

**19 · Demo story.** A family with an autistic 9-year-old and a shared love of dinosaurs; the agent returns a Saturday plan with a quiet-hours slot, a step-free route, and a "confirm by phone" list.

**20 · Competitive landscape.** Wheelmap, AccessAble, Euan's Guide, Sociability, Google Maps accessibility attributes, KultureCity (sensory-inclusive certification). Strong incumbents on the access axis, none on taste.

**21 · Existing projects.** None found.

**22 · Differentiator.** Taste × access together.

**23 · Risks.** (a) Qloo doesn't hold accessibility attributes — *the single biggest weakness*; (b) requires an external dataset you'd have to integrate in 26 days; (c) evidence thin.

**24 · Criticisms.** *"Qloo is doing almost nothing here — this would work with any places API."* · *"AccessAble already exists."* · *"This fails the 'would it work without Qloo?' test."*

**25 · Defence.** Honest answer: **it partly does fail that test.** You could rescue it by making taste the *reason* it works (taste transfers across domains to find non-obvious accessible activities), but this is a rescue, not a strength. **Recommend not building this for this competition** — it's a good product with a weak Qloo case.

**Scores.** Qloo dep **4.5** · Impact **9** · Novelty **7.5** · Feasibility **6** · Demo **7.5** · Data **5** · Saturation-resistance **9** · Agentic **7** · Judge appeal **7.5** · Product **7**
**Weighted overall: 7.04** — **but it fails the hackathon's own test ("would this work the same without Qloo?"). Reject.**

---

## IDEA 10 — **Overtone**
*(Independent label release-marketing & routing agent)*

**2 · Concept.** An independent label or distributor names a release; the agent says which cities and which *adjacent* audiences to push it to, which non-obvious artists to cross-promote with, and what the campaign should say.

**3 · Problem.** Independent labels push releases with a blanket "all cities, all DSPs" approach and have no way to find the non-obvious audiences adjacent to a record.

**4 · Evidence.** Same structural market as §4.2 (independent music economics) plus the sync-market evidence in §4.3. **However:** this is very close to Taste Match (artist audience finding) and Booker/Advance (city routing) — both already in the pool.

**5–9.** Workflow: resolve the release's artist → expand to adjacent artists + cities via insights → rank cities by affinity → propose playlist/community targets and cross-promotion partners. Qloo: `urn:entity:artist` insights with `signal.location.query`, `filter.results.entities` for scoring cities, `urn:entity:place` for local scenes, `filter.popularity.min/max` for peer-level collaborators.

**10–11.** Without Qloo: a generic release checklist. Nothing survives.

**12–17.** Standard; low complexity.

**18 · Difficulty.** **Low.**

**19 · Demo story.** A real indie release; the agent shows a map of 12 cities ranked by local affinity, and finds one city nobody would have chosen where affinity is highest.

**20–22 · Competitive landscape / overlap.** Chartmetric, Viberate, Soundcharts, Spotify for Artists, Bandcamp. **In-pool overlap is severe:** Taste Match does artist→audience, Booker does act→cities, Advance does act→cities→rooms→sponsors. **This idea is essentially the union of two occupied positions. Reject for this competition.**

**Scores.** Qloo dep **8** · Impact **7** · Novelty **4.5** · Feasibility **9** · Demo **7.5** · Data **8** · Saturation-resistance **3** · Agentic **6.5** · Judge appeal **7.5** · Product **7**
**Weighted overall: 6.94** — **Reject: crowded lane.**

---

## IDEA 11 — **Field Trip**
*(Culturally-responsive reading & media curation for teachers and librarians)*

**2 · Concept.** A teacher describes a class — age, region, reading levels, languages spoken at home, what the kids actually love (music, games, shows) — and the agent proposes book and media sets that are both age-appropriate and culturally adjacent to what those students already care about, with `filter.content_rating`-style safety checks.

**3 · Problem.** Teachers and librarians choose titles with limited time and strong pressure from both directions (inclusive-curriculum mandates and book challenges). "Culturally responsive" is a requirement without a tool.

**4 · Evidence.** Substantial literature on culturally responsive pedagogy and on book-selection difficulty; also the documented surge in book challenges in US schools. **I did not verify specific statistics in this pass — treat as medium evidence with a strong normative pull.**

**5 · Target users.** K–12 teachers, school librarians, public librarians, curriculum leads, literacy non-profits.

**6 · Workflow.** Class profile → agent resolves what students love to Qloo entities → finds books with high affinity to those cultural signals (Qloo has `urn:entity:book` with `filter.publication_year.*`) → applies age/reading-level and content filters → returns 12 titles across a "safe / adjacent / stretch" gradient, each with a one-line rationale and the evidence.

**7 · Agent.** A curation planner that must balance safety, currency, and cultural adjacency, and that explains each pick in language a teacher can put in a parent letter.

**8 · Qloo used.** `urn:entity:book` insights with `signal.interests.entities=<students' media/music>` · `filter.publication_year.min/max` · `filter.tags` · `urn:entity:movie`/`tv_show` with `filter.content_rating` for media sets · `signal.demographics.age` for age skew · `feature.explainability`.

**9 · Why Qloo essential.** "Which books are culturally adjacent to what *these specific* students already love?" is a cross-domain affinity query (music/film/games → books). Genuinely Qloo-shaped and, as far as I know, nobody is doing it.

**10 · vs. LLM.** An LLM returns the canonical inclusive-reading list (which is itself a form of lookalike bias). Qloo can surface a title no one in the district has heard of that sits at the same taste coordinates.

**11 · Without Qloo.** A curated listicle. Dead.

**12–17.** Standard. Add a content-advisory layer (Common Sense Media, publisher ratings) for the safety gradient.

**18 · Difficulty.** **Low-medium.**

**19 · Demo story.** A sixth-grade class in a specific school: 34 students, 11 languages. The agent shows what those students' own cultural signals are, then a "taste-adjacent reading ladder" from safe to stretch, annotated for a parent letter.

**20 · Competitive landscape.** Common Sense Media, TeachingBooks, Follett Destiny, Mackin, NoveList, Epic!/Renaissance. All use reading level and genre metadata — **none uses measured cultural affinity**.

**21 · Existing projects.** None found in either Qloo hackathon. Genuinely open.

**22 · Differentiator.** Taste-adjacency instead of curriculum-category matching.

**23 · Risks.** (a) Politically charged domain — could attract hostile judging or undermine appeal; (b) Qloo book coverage and child-age appropriateness filtering may be thin; (c) public-sector buyers, slow sales; (d) demo risk — a list of books is not visually exciting.

**24 · Criticisms.** *"This is a list of books."* · *"You're inferring children's identities from their music — a privacy and ethics problem."* · *"This would work with a library catalogue and an LLM."*

**25 · Defence.** (a–b) The ethics objection is serious and needs a designed answer: **never infer an individual child's identity**; work at class-of-named-interests level, exactly as Qloo's aggregate-only model requires (this is actually a *good* fit with Qloo's privacy-first design — lean into it). (c) Differentiate from a library catalogue by showing the *cross-domain* jump the catalogue cannot make. (d) Accept the demo weakness; if you build this, invest in making the ladder visual.

**Scores.** Qloo dep **7.5** · Impact **8.5** · Novelty **8.5** · Feasibility **8** · Demo **6** · Data **6.5** · Saturation-resistance **9.5** · Agentic **7** · Judge appeal **7** · Product **7**
**Weighted overall: 7.53**

---

## IDEA 12 — **Foyer**
*(Membership retention & reactivation for culture clubs)*

**2 · Concept.** Museums, film clubs, sports clubs and arts organisations have lapsed members and unknown prospects; Foyer tells them which *adjacent* cultural cohorts would convert, what to offer them, and which specific lapsed segments to win back with what.

**3 · Problem.** Membership is the most profitable revenue line for cultural institutions and the hardest to grow; lapsed-member reactivation is done by mass email.

**4 · Evidence.** Same as §4.1 (TRG/BSO/NEA), plus the specific finding that households attend fewer events even as organisations reach more households — i.e. the member relationship is weakening even where reach is growing.

**5 · Target users.** Membership directors and CRM leads at museums, arts centres, sports clubs, subscription cinemas, zoos, heritage sites.

**6–9.** Workflow: define the target cohort or the lapsed segment → profile its taste → find adjacent cohorts with high affinity and no prior contact → map their geography → propose an offer and a channel → measure. Qloo: `urn:entity:artist`/`movie`/`place`/`tag` adjacency; `urn:heatmap`; `signal.demographics.audiences`; `analysis/compare` between members and prospects.

**10–11.** Without Qloo: an email-marketing template. Dead.

**12–17.** Standard.

**18 · Difficulty.** **Low-medium.**

**19 · Demo story.** "Here are the 4,000 people who have never bought a ticket but live within a mile and have a 2× taste adjacency to your programme. Here are the three zips they're in. Here's the offer."

**20–22.** Competitive landscape: Tessitura, Spektrix, AudienceView, TRG, Purple Seven, Subscribers/CI. Overlap: this is a **narrower slice of Idea 1** (same buyer, same data, smaller scope).

**23–25.** Main criticism: *"This is a feature of Idea 1, not an idea."* Correct. It's listed for completeness and to show the winner is extensible — but it should be built *as* part of Adjacent, not separately.

**Scores.** Qloo dep **9** · Impact **8** · Novelty **6** · Feasibility **9** · Demo **7** · Data **8** · Saturation-resistance **6.5** · Agentic **7** · Judge appeal **7.5** · Product **7.5**
**Weighted overall: 7.73**

---

## IDEA 13 — **Warm Front**
*(Municipal & BID cultural programming with an access-equity lens)*

**2 · Concept.** A parks department or business improvement district asks: "which free cultural programming, in which locations, reaches residents who currently have the *least* cultural access, while still being something they'd actually love?" The agent answers with a schedule, a map, and an equity metric.

**3 · Problem.** Cities and BIDs program public cultural events with almost no audience data, and cultural access is unevenly distributed geographically. Public funders increasingly require equity reporting.

**4 · Evidence.** The 1-mile 80% attendance decay finding (Symphony.org) plus the arts-participation decline (NEA) plus the documented reality that cultural institutions' audiences don't reflect their cities (Hewlett/ABAG data; SF Symphony SoundBox audience is 58% under 45 vs 23% for the main hall — proof that programming change *can* move demography). This is a decent evidence base.

**5 · Target users.** Municipal arts/culture offices, parks & recreation departments, BIDs and downtown associations, public library systems, transit-adjacent placemaking teams, and the philanthropic funders who finance them (sometimes the actual buyer).

**6 · Workflow.** The city selects N candidate locations and a budget → the agent profiles the taste of the *population within walking distance of each location* → finds programming (genres, artists, formats, food) with high affinity per location → checks that the unions of locations do not double-serve the same neighbourhood → outputs a schedule, a map, a cost envelope and an access-equity score.

**7 · Agent.** An allocation optimiser: it must maximise affinity coverage subject to budget and an equity constraint, and it must justify *why this location* rather than the obvious downtown one.

**8 · Qloo used.** `urn:heatmap` per candidate location with different taste signals · `urn:entity:artist` insights with `signal.location.query` per neighbourhood · `signal.demographics.audiences` and `.age` for population framing · `urn:entity:place` to find existing venues and partners · `diversify.by=properties.geocode.city` for cross-city programmes · `/v2/trending` for what's rising locally.

**9 · Why Qloo essential.** Neighbourhood-level taste affinity is the whole input. Census gives you income and age; it cannot tell you what the people there love.

**10 · vs. LLM.** LLM: "host a diverse lineup in accessible locations." Warm Front: "put the Friday Afrobeat night in Ward 4 because that programme's affinity there is 2.1× its citywide baseline, and Ward 4 currently has zero cultural events." 

**11 · Without Qloo.** A spreadsheet with a map. Nothing survives.

**12–17.** Standard, plus a geospatial optimiser and a simple equity metric (affinity-index × access deficit).

**18 · Difficulty.** **Medium.**

**19 · Demo story.** Pull up a real mid-size US city. Show three candidate sites. The agent proposes a schedule that puts the highest-affinity programme *in the neighbourhood with the least existing cultural provision* — and shows the number that proves it. The emotional beat: a map where the *best* answer is not downtown.

**20 · Competitive landscape.** SMU DataArts, PolicyMap, Esri community-analytics, Culture Counts, Placer.ai (footfall), and internal city GIS teams. None models *taste*; all model *demographics and footfall*.

**21 · Existing projects.** GeoTaste (2025 winner) is the nearest — business-location intelligence. Mapetizer (2025) did "business zones mapped by taste." **Two adjacent precedents, both maps, one of them a winner.**

**22 · Differentiator.** Cultural affinity as the allocation variable rather than footfall or demographics.

**23 · Risks.** (a) Slow public-sector sales; (b) equity framing can read as political to some judges; (c) hard to validate; (d) the "wow" is a map — and GeoTaste already won with a map.

**24 · Criticisms.** *"GeoTaste already did taste-based geography, and it won."* · *"Cities can't buy software."* · *"You're deciding what poor neighbourhoods should like."* — that last one is the sharpest and needs a careful answer.

**25 · Defence.** (a–b) Differentiate on the *allocation decision* (which programme where) versus GeoTaste's *location decision* (where to open) — but accept the proximity. (c) The ethics objection deserves a real answer: the agent ranks affinity among options the community already has, and the product should be explicitly advisory with community input upstream. If you can't answer this crisply, don't build it.

**Scores.** Qloo dep **9** · Impact **9** · Novelty **7.5** · Feasibility **7.5** · Demo **7.5** · Data **7.5** · Saturation-resistance **6** · Agentic **8** · Judge appeal **8** · Product **6.5**
**Weighted overall: 7.99**

---

## IDEA 14 — **Second Opinion**
*(A cultural-grounding red-team tool for other AI agents)*

**2 · Concept.** An agent that takes any other AI agent's cultural output — a campaign, a slate, a playlist, a season, a set of recommendations — and reports, with evidence, where it is likely to be *culturally wrong*, plus the corrections the taste graph supports.

**3 · Problem.** Everyone is shipping LLM products that make cultural claims with no grounding and no test. There is no way to audit one.

**4 · Evidence.** The hackathon prompt itself: "We're not looking for demos of what LLMs can already do." Plus the widely-documented phenomenon of ungrounded synthetic personas (Quorum's own framing cites NN/g's evaluation and names the criticism). Plus the observable fact that two of the three "safe" answer patterns in the current pool — TasteLoop's "simulated generic baseline" and multiple "LLM would guess" claims — are *assertions*, not measurements.

**5 · Target users.** AI product teams, agencies building with LLMs, eval/platform teams, and enterprises with brand-safety requirements. (Qloo itself is a plausible buyer.)

**6 · Workflow.** Give it a prompt + a model's output → the agent extracts every cultural claim → resolves each to Qloo entities/tags → checks affinity of each claim against a declared or inferred audience → flags unsupported claims, contradictions, and missed obvious options → proposes grounded replacements with receipts → produces a scorecard.

**7 · Agent.** A verifier: claim extraction → resolution → verification → contradiction detection → remediation. Multi-step and naturally loop-shaped.

**8 · Qloo used.** `/search` + `/v2/tags` (resolve every claim) · `/v2/insights` with `filter.results.entities` (score claimed entities against the stated audience — the core test) · `urn:demographics` · `analysis/compare` between the model's output set and Qloo's top-N · `feature.explainability`.

**9 · Why Qloo essential.** The entire product is "compare an LLM's cultural claims to measured affinity." Remove Qloo and there's no ground truth to compare to.

**10 · vs. LLM.** It *is* the meta-answer to that question: an LLM cannot audit itself; this measures the gap.

**11 · Without Qloo.** Nothing. Literally nothing.

**12–17.** Standard, plus a claim-extraction step and a scorecard renderer.

**18 · Difficulty.** **Medium.**

**19 · Demo story.** Extremely strong and judge-native: run 10 prompts through a frontier LLM live, pass the outputs through Second Opinion, and show the scorecard — **X% of cultural claims unsupported; here are the three worst; here is the grounded correction.** Then flip it: "and here is the same model with Qloo wired in."

**20 · Competitive landscape.** Evals (Braintrust, LangSmith, Patronus, Galileo, Arize), brand-safety tools, factuality checkers. None has a cultural ground truth.

**21 · Existing projects.** Nothing in the pool. Quorum's synthetic panel is adjacent but is a *generator* of cultural judgement, not an auditor of it.

**22 · Differentiator.** It makes the Qloo advantage **measurable**, which is exactly what the judging criterion "Potential Impact — does the solution actually address that problem *based on what's demonstrated*" rewards.

**23 · Risks.** (a) It's infrastructure, and the prompt wants an app; (b) two MCP-wrapper projects already exist and judges may bucket this with them; (c) a "scorecard" is a less emotionally appealing product than a consumer tool; (d) harder to explain in 30 seconds.

**24 · Criticisms.** *"This is an eval harness, not a product."* · *"MCP wrappers already exist."* · *"Nobody asked for this."*

**25 · Defence.** (a) Ship a *product* around it: a free public "is your AI culturally blind?" report card, plus the API. (b) Different from a wrapper: a wrapper gives an agent Qloo; this *measures whether the agent used it honestly*. (c) Qloo itself has a commercial interest in "grounding verification" — and Calacanis-style investors like picks-and-shovels.

**Scores.** Qloo dep **10** · Impact **8** · Novelty **9** · Feasibility **7.5** · Demo **8.5** · Data **8** · Saturation-resistance **8** · Agentic **9** · Judge appeal **8** · Product **7.5**
**Weighted overall: 8.63**

---

## IDEA 15 — **Home Ground**
*(Aging-in-place: choosing a community where a parent can keep their life)*

**2 · Concept.** A family choosing a retirement or care community for a parent describes what the parent has always loved; the agent finds communities in a given radius where that life is *still available*, with evidence about the surrounding cultural environment rather than the facility's brochure.

**3 · Problem.** The move is high-stakes, irreversible and emotionally brutal, and families choose on brochure amenities and price. Continuity of identity and interest is one of the strongest known predictors of wellbeing in later life, and it is almost never a selection criterion.

**4 · Evidence.** Rush University's longitudinal study of 1,400+ seniors found those high on a "purpose in life" scale had a **30% lower rate of cognitive decline** — [Freedom Plaza summary](https://freedomplazafl.com/blog/purposeful-memory-care-activities/). Cochrane found personally tailored activities may reduce challenging behaviour and slightly improve QoL. Musical memory is among the last to deteriorate — [Music & Memory](https://musicandmemory.org/wp-content/uploads/2021/08/Guide-to-Creating-Personalized-Playlists.pdf). **This is genuinely good evidence.**

**5 · Target users.** Adult children acting as decision-makers (the actual buyer), care navigators, senior-living operators, geriatric care managers, financial advisers serving retirees.

**6–9.** Workflow: the family lists what the parent loves (music from a specific era, a specific cuisine, a faith community, a hobby) → the agent resolves to entities → for each candidate facility location, it profiles the cultural environment within a given radius (what places, what music venues, what restaurants, what community entities exist that carry those tastes) → ranks communities by *life-continuity*, not amenities, alongside price and care level. Qloo: `urn:entity:place` with `signal.interests.entities` + `filter.location.radius` centred on each facility; `urn:entity:artist` with `filter.release_year`/era tags; `filter.tags` for cuisines and activities; `urn:heatmap` to compare neighbourhoods; `signal.demographics.age=55_and_older` for a cohort frame.

**10 · vs. LLM.** LLM: "look for communities with a good activities programme and proximity to family." Home Ground: "of these six, only two are within a 15-minute drive of a venue that programmes the music he's loved since 1968 and a restaurant serving the food he grew up with — here they are."

**11 · Without Qloo.** A facility comparison site with a lifestyle filter. Care.com/Seniorly/A Place for Mom already exist and are better funded.

**12–17.** Standard, plus a facility dataset (public care-directory data, state licensing registries) and a distance/routing layer.

**18 · Difficulty.** **Medium-high** (facility data acquisition is the bottleneck).

**19 · Demo story.** "My dad. 82. He played trumpet, he loves Miles Davis, he's eaten at the same Cantonese place for thirty years, and he goes to church." Six communities come back; two preserve his life, four don't, and the map shows why.

**20 · Competitive landscape.** A Place for Mom, Caring.com, Seniorly, Seniorly, Naborforce, CaringBridge, SCAN, Blue Zones. **All monetised by referral fees from facilities — a structural bias this product would invert.** That's a genuinely compelling positioning statement.

**21 · Existing projects.** ⚠️ **Resonance already occupies the senior-living taste space in this hackathon** (activity planning for senior-living activity teams and families). Adjacent enough that a judge may see the same domain twice.

**22 · Differentiator.** Choosing the *place* by life-continuity, not the *activity* by taste — and inverting the referral-fee incentive.

**23 · Risks.** (a) Resonance overlap; (b) facility data is hard to assemble in 26 days; (c) the domain invites medical/regulatory framing that must be avoided; (d) sensitive emotional territory to demo.

**24 · Criticisms.** *"Resonance already did senior living with Qloo."* · *"You're helping families pick a facility — that's a regulated, high-stakes decision."* · *"Where's the facility data?"*

**25 · Defence.** (a) The overlap is real. Differentiate clearly (place-selection vs. activity-planning) — but you are explaining a difference rather than owning a gap. (b) Keep it strictly informational, never recommending a facility, only describing its cultural environment. (c) Concede unless you have the data.

**Scores.** Qloo dep **8.5** · Impact **9** · Novelty **6.5** · Feasibility **6** · Demo **8** · Data **5.5** · Saturation-resistance **4.5** · Agentic **7** · Judge appeal **8.5** · Product **7**
**Weighted overall: 7.53** — **Reject: adjacent to an occupied position, with the hardest data problem in the set.**

---

# Part 4 — Scoring, Comparison, and the Final Recommendation

---

## 5. Weighted scoring model

The user asked for heavier weight on **Qloo dependency, real problem, novelty, feasibility, demo potential**. Those five carry **0.72 of the total weight**:

| Criterion | Weight | Rationale |
|---|---|---|
| Qloo dependency | **0.18** | The challenge's own pass/fail test |
| Real-world impact | **0.16** | Judging criterion 3 |
| Novelty | **0.14** | Judging criterion 4, assessed against a crowded pool |
| Technical feasibility | **0.12** | Working software is mandatory; 26 days |
| Demo potential | **0.12** | No video allowed — the judges *use* it |
| Data feasibility | 0.08 | Qloo-only where possible |
| Competition / saturation resistance | 0.06 | Relative judgement against ~24 known rivals |
| Agentic depth | 0.06 | "Agentic tool / agent-powered app" |
| Judge appeal | 0.05 | Six named judges with known interests |
| Potential to become a real product | 0.03 | Lowest — least verifiable pre-build |

## 6. Comparison table — all 15

| # | Idea | Qloo dep | Impact | Novelty | Feas | Demo | Data | Sat-resist | Agentic | Judge | Product | **Weighted** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Adjacent** — cultural-institution audience development | 10 | 9 | 9 | 9 | 8.5 | 9 | 8 | 9 | 9 | 7.5 | **8.97** |
| **2** | **Undertow** — sync-music supervision agent | 9 | 8 | 9.5 | 8.5 | 9 | 7 | 9 | 8.5 | 9 | 8 | **8.71** |
| **14** | **Second Opinion** — cultural red-team for AI agents | 10 | 8 | 9 | 7.5 | 8.5 | 8 | 8 | 9 | 8 | 7.5 | **8.63** |
| **5** | **Good Neighbour** — cold-start gifting agent | 8.5 | 7 | 9.5 | 9.5 | 9.5 | 7.5 | 10 | 8 | 8.5 | 6 | **8.51** |
| **3** | **Greenlight** — content acquisition for streamers | 9 | 8.5 | 8.5 | 8 | 6.5 | 7.5 | 9.5 | 8 | 8.5 | 8 | **8.35** |
| **4** | Reading Room — film/TV brand integration | 9 | 7.5 | 7.5 | 8.5 | 8.5 | 7 | 6.5 | 7.5 | 8.5 | 7.5 | **8.13** |
| **8** | Recovery Map — non-drinking social life | 7.5 | 9 | 8.5 | 7.5 | 8.5 | 6.5 | 9.5 | 7.5 | 8 | 6.5 | **8.06** |
| **13** | Warm Front — municipal cultural programming | 9 | 9 | 7.5 | 7.5 | 7.5 | 7.5 | 6 | 8 | 8 | 6.5 | **7.99** |
| **12** | Foyer — membership retention for culture clubs | 9 | 8 | 6 | 9 | 7 | 8 | 6.5 | 7 | 7.5 | 7.5 | **7.73** |
| **11** | Field Trip — culturally-responsive reading curation | 7.5 | 8.5 | 8.5 | 8 | 6 | 6.5 | 9.5 | 7 | 7 | 7 | **7.53** |
| **15** | Home Ground — aging-in-place community choice | 8.5 | 9 | 6.5 | 6 | 8 | 5.5 | 4.5 | 7 | 8.5 | 7 | **7.53** |
| **6** | Aisle — independent retail assortment | 8 | 7.5 | 7 | 8.5 | 7 | 6 | 6 | 7.5 | 7 | 6.5 | **7.42** |
| **9** | Sensory Passport — accessible outings | 4.5 | 9 | 7.5 | 6 | 7.5 | 5 | 9 | 7 | 7.5 | 7 | **7.04** |
| **7** | The Long Table — constrained dining | 7 | 8.5 | 6 | 6.5 | 7.5 | 5.5 | 4 | 7.5 | 7.5 | 7 | **7.01** |
| **10** | Overtone — indie label release marketing | 8 | 7 | 4.5 | 9 | 7.5 | 8 | 3 | 6.5 | 7.5 | 7 | **6.94** |

---

## 7. TOP 5

1. **Adjacent** — audience development & programming for cultural institutions (8.97)
2. **Undertow** — AI music-supervision agent for sync (8.71)
3. **Second Opinion** — cultural-grounding red team for existing AI agents (8.63)
4. **Good Neighbour** — cold-start gifting grounded in the taste graph (8.51)
5. **Greenlight** — catalogue acquisition for streamers by market (8.35)

**Notable exclusions and why**
- **A venue/talent-booking agent** had the best problem-evidence pair I found (NIVA: 64% unprofitable, 31% of costs in booking fees) — but **Booker, Advance and Undercard** already occupy it. Best problem, wrong competition.
- **Relocation** — four competitors. Dead.
- **Sensory Passport** (7.04) fails the challenge's own test: accessible-venue data is the hard part and Qloo isn't where it lives.
- **Overtone** (6.94) is the union of two occupied positions.

---

## 8. TOP 3

### 🥇 1. Adjacent — *8.97*
The only idea where **every single output line requires a Qloo call**, where the geographic heatmap is load-bearing rather than decorative, and where the target market has a documented, quantified, unresolved crisis that the incumbent analytics industry structurally cannot address because it only sees people who already bought.

### 🥈 2. Undertow — *8.71*
The strongest *commercial* thesis (an affinity-vs-obscurity frontier is a genuinely new pricing idea for the sync market) and the best "put it next to a live LLM and watch the LLM lose" demo. Held back by a real gap: Qloo cannot verify rights, which is the actual bottleneck in the workflow.

### 🥉 3. Second Opinion — *8.63*
The most intellectually elegant entry and the highest Qloo dependency in the set (10/10 — remove Qloo and the product ceases to exist). The risk is category: judges may file it under "MCP wrapper / eval harness" rather than "product," which costs it on the Design criterion.

---

## 9. 🏆 FINAL RECOMMENDATION: **Adjacent**

> **Adjacent — the audience-development agent for cultural institutions.**
> *Paste a season. Get the specific culture cohorts who'd already love you, the neighbourhoods they live in, the programme that brings them in, and the test that proves it.*

---

### 9.1 Why this problem matters
The performing-arts audience is in structural, compounding decline, and the industry knows it. Boston Symphony reported **−40% attendance over 20 years**. NEA data shows live classical attendance halving, **8.6% → 4.6%** between 2017 and 2022. TRG Arts' 163-organisation dataset shows fewer tickets sold and households attending less often even where reach is growing. The replacement rate for departing symphony attendees is **0.907**. The Wallace Foundation's literature review concluded there are "no obvious solutions."

This is not a marketing problem. It is an **information problem with a named culprit**: as the field's own analysts write, arts growth "relied on lookalike targeting — finding more people who resembled your best, most loyal patrons… That model worked when the general population still looked like the audience the field originally built." Lookalike targeting cannot find people who look unlike your current audience. Every tool the sector owns is built on ticket data, so by construction it can only describe people who already bought. **The industry's entire measurement apparatus is blind to its own solution.**

### 9.2 Why now
Three things converged in the last 12 months:
1. **The decline became undeniable and quantified** (NEA 2022 SPPA released, NIVA/State of Live, TRG's 2026 benchmarks, BSO's public admission).
2. **Funders started demanding evidence**: "We should be approaching audience development as a science so that there are hypotheses that get tested and evaluated" — a funder, in Hewlett's own write-up. (The word "hypotheses" is the product brief.)
3. **The measurement technology changed.** GIS-grade taste affinity is now available as an API. Qloo covers 50+ countries "down to hundreds of feet," its clients include Netflix, Michelin and JCDecaux, and its data is refreshed daily. Two years ago this product required a bespoke data-science engagement. Now it's a graph query.

### 9.3 Why existing solutions are insufficient
| Incumbent type | Examples | Structural failure |
|---|---|---|
| Transactional analytics | TRG Arts, SMU DataArts, Purple Seven, Tessitura Insights, Spektrix | Only see people who bought. Cold-start impossible. |
| Audience research agencies | WolfBrown, Slover Linett, AMS Planning | $20k–$100k bespoke studies, months long, non-repeatable, static once delivered. |
| Ad platforms | Meta Lookalike, Google Similar Audiences | Optimise for resemblance to the current audience — the failing strategy — and know nothing about cultural adjacency. |
| CRM/email | Tessitura, Mailchimp, WordFly | Execute a plan; do not produce one. |
| LLMs | ChatGPT / Claude | Produce plausible generic advice ("target younger audiences, program more contemporary work, use social video") with no measurement, no geography, and no way to be wrong. |

**Nobody combines (a) cold-start cross-domain affinity, (b) block-level geography, and (c) a falsifiable experiment.**

### 9.4 Why Qloo changes the product
Qloo makes four things possible that no incumbent can do:
1. **Cold start.** The FAQ's own words: *"Qloo is designed to overcome cold starts and does not require customer data."* An organisation with zero data about non-attenders can still get a measured answer. That is the entire gap.
2. **Cross-domain adjacency.** Music ↔ film ↔ books ↔ brands ↔ places ↔ people. You can discover that a chamber series' audience over-indexes on A24 horror and natural-wine bars — a fact that is *in no arts database on earth*.
3. **Block-level geography that is causally relevant.** `urn:heatmap` with a 12-character geohash and a locality query gives affinity per cell, and the literature says the marginal attendee lives under a mile away. The map is not decoration — it is the mechanism.
4. **Receipts.** `feature.explainability=true` returns per-recommendation attribution (which input entities contributed, normalised 0–1) — so every statement the agent makes can carry the exact Qloo input that produced it. That converts "AI said so" into "here is the query, the parameters, the score and the timestamp."

### 9.5 Why an agent is necessary (not a single prompt)
The output requires at minimum: resolve a season → derive programme tags → run four to six cross-domain expansions under a call budget → evaluate coverage and decide whether to widen or stop → call the heatmap for the city → intersect with geography → score three candidate programme additions in two directions → compare audiences → write a plan with a falsification condition. That is a **plan–act–evaluate loop with a budget and an honest-failure branch**, which is the definition of an agent. A single prompt cannot do it, and — importantly — a single prompt cannot *refuse* to answer when the graph returns nothing, which is a behaviour you want to be able to demonstrate.

### 9.6 Why this is better than a normal recommendation system
| Normal recommender | Adjacent |
|---|---|
| Needs interaction history | Needs one season listing |
| Optimises engagement | Optimises *new audience acquisition under a geography constraint* |
| Recommends items | Recommends **a decision with a budget, a location and a test** |
| Cannot explain | Cites the exact query, score and contributing entity |
| Fails silently | Empties the panel and says "the graph has nothing for this" |
| Individual-level inference | Aggregate-level, no PII — matching Qloo's own design constraint |

### 9.7 Why it is feasible for your skill set
Every component is already in your stack. Python + FastAPI for the agent service (you know both). A typed Qloo client with cache, token-bucket limiter, bounded retries, a call budget and a trace recorder — that is the same discipline as your revenue-recovery decision engine. LangGraph or a hand-rolled planner loop for the plan–act–evaluate cycle. React + TypeScript for the UI. PostgreSQL for saved analyses. Docker for local dev. **Zero model training. Zero proprietary data. Zero machine learning.** The only ML-adjacent judgement is the ranking function, and it is arithmetic you can tune in an afternoon. A competent solo builder ships the MVP in 5–8 focused days.

### 9.8 The MVP — exact feature list
**In scope (build these, nothing else):**
1. **Season input** — search-and-add or paste 5–12 works/artists/titles; venue name + city; auto-resolve geocode.
2. **Resolution panel** — each item resolved to a Qloo entity ID with its popularity; ambiguous items surface a chooser; unresolved items are shown as *unresolved*, never silently dropped.
3. **Taste DNA** — the tags Qloo returns for the season (`filter.type=urn:tag`), plus the age/gender skew (`urn:demographics`). Raw tag URNs visible.
4. **Adjacent cohorts** — 3 cohorts from ≥3 different domains, each with: the affinity evidence, the seed entities that drove it, and a **novelty ↔ safety slider** that re-ranks live.
5. **The map** — heatmap of the leading cohort over the city; venue pinned; the top 3 under-served zips named and highlighted; a distance-ring readout at 1 mile (tied to the published distance-decay finding).
6. **The slate bet** — one recommended programme addition, scored against the current audience *and* the target cohort, using `filter.results.entities` in both directions.
7. **The test card** — one page: cohort, zips, programme bet, budget split, metric, baseline to beat, **falsification condition**, and the dates of the measurement window.
8. **The receipts panel** — every Qloo call: workflow name, endpoint, full parameters, HTTP status, result count, duration, cache hit/miss, and the `feature.explainability` attribution for recommendation calls. Copyable as JSON.
9. **Honest-failure mode** — if a call returns an empty entity set, the dependent panels go blank with "Qloo returned no entities for this query" and the raw call is still logged. **Never** substitute model priors.
10. **Saved analyses** + shareable read-only link.

**Explicitly out of scope for the MVP:** accounts/auth beyond a magic link, payments, multi-tenancy, PDF export (make it print-CSS), multi-city mode, email integration, real patron-data import.

### 9.9 The live demo should look like
A single page, dark, quiet, no gradients:
- **Top strip:** the Qloo connection indicator (`live` / `no credential`) and a live **call counter** (e.g. `7 calls · 3.1s`). Visible honesty.
- **Left column:** the season as a list of chips; the venue; a "Run" button.
- **Centre:** the Taste DNA panel, then three cohort cards that arrive progressively as calls return — **you watch the agent think**, with each step labelled ("resolving seeds → expanding across domains → locating the cohort").
- **Right:** the map, filling in with the heatmap cells.
- **Bottom:** the test card, then the receipts table.

No animation for its own sake. The motion comes from the calls resolving.

### 9.10 The 2-minute judge experience
| Time | What happens |
|---|---|
| 0:00–0:15 | "A 900-seat hall. Its subscribers are 68% over 60. It has four people in marketing and no data on anyone who doesn't already buy. I'm going to paste its actual last season." |
| 0:15–0:35 | Paste. The agent resolves eight works. One comes back ambiguous — it asks, out loud, and the judge picks. **The agent asks one question and waits.** |
| 0:35–0:55 | Taste DNA appears. Three cohort cards materialise with affinity numbers. |
| 0:55–1:15 | "Here's the cohort they'd never have named." Move the novelty/safety slider — the ranking visibly changes, and the evidence behind each card changes with it. |
| 1:15–1:35 | The map reveals itself. The venue is a pin. The cohort is three clusters. Two of the three are in zips with **zero** appearances in the org's mail history. |
| 1:35–1:50 | The slate bet: one programme addition, scored against both audiences, with the numbers on screen. |
| 1:50–2:00 | Open the receipts table. "Every sentence you just saw is one of these rows. Here's the query, the parameter, the score, the status." |

Then, if you have 20 extra seconds: **run the same season through a frontier LLM live and put the two answers side by side.**

### 9.11 The "wow" moment — with no flashy UI
There are two, and neither needs animation:

**Wow 1 — the naming.** The moment the tool names a specific, non-obvious cultural cohort the organisation has never considered, *with a number attached*. Every arts marketer in the room has been told "you need younger, more diverse audiences." Nobody has ever been told "your programme's strongest measured overlap is with people who over-index on A24 psychological horror, vinyl record shops and natural-wine bars, at 2.1× the citywide baseline." That sentence is the product.

**Wow 2 — the geography.** The moment the map shows that this cohort lives **1.8 miles from the hall** and that the institution has never mailed two of the three zips. The distance finding is published research (80% attendance drop-off by one mile); seeing it rendered against a specific organisation is what turns an affinity score into an action.

**Why they work without flash:** both are *facts the judge could not have predicted*, evidence-backed, and instantly checkable. That is the difference between "technically functional" and "actually good" — the challenge's own words.

**The structural wow:** the honesty. When a query returns nothing, the panel stays empty and says so. Every competing submission claims its agent "would have made it up." Yours can *show* it didn't.

### 9.12 Evidence that the Qloo-powered system beats a generic LLM baseline
Do not assert this. **Measure it, in public, and put the method in the repo.**

**Design: a pre-registered A/B on 20 real institutions.**
1. Pick 20 real cultural organisations with publicly listed recent seasons (build the list *before* running anything — pre-registration).
2. For each, issue the identical prompt to a frontier LLM: *"You are an audience-development consultant. Here is [org]'s last season and city. Identify three specific audience cohorts most likely to become new audiences, tell me where in the city they live, and recommend one programme addition with evidence."*
3. Run the same input through Adjacent.
4. Score every output on four **objective, machine-checkable** criteria:
   - **Named-entity specificity** — does it name *checkable* real entities (specific artists, specific venue types, specific neighbourhoods) or categories? (Count named entities per output; LLMs mostly emit categories.)
   - **Verifiability** — what fraction of claims carry a resolvable data reference? (LLM: ~0%. Adjacent: 100% by construction, since a claim without a receipt never renders.)
   - **Overlap with the incumbent-bias baseline** — measure the semantic distance between the LLM's suggested cohort and the org's *existing* audience profile. High similarity to the current audience is the failure mode the industry named. LLMs will score badly here; Adjacent is explicitly ranked on novelty-vs-affinity.
   - **Geographic falsifiability** — does the output produce a *testable geographic claim* (a named area) or an unfalsifiable one ("expand outreach")? LLMs: almost never geographic.
5. Publish the raw table, the prompts, the scoring code, and the losses.

**Supporting evidence you can cite:**
- **Qloo's own precedent for the mechanism:** JCDecaux uses this exact capability — "understand the cultural nuances and preferences of the consumers that pass by their out-of-home media placements" — for media targeting ([Qloo case study](https://www.qloo.com/resources/jcdecaux-case-study)).
- **Qloo's measured lift in an adjacent consumer setting:** Match Group's Yuzu reported a **70% increase in Likes** after adding Qloo-powered interest signals ([PRNewswire](https://www.prnewswire.com/news-releases/qloo-brings-cultural-ai-to-blk-chispa-upward-and-yuzu-302506279.html)). It's consumer, not arts, but it's a real before/after from a named client.
- **The "why geography matters" citation:** the 1-mile / 80%-drop-off finding ([Symphony.org](https://symphony.org/features/meeting-audiences-where-they-are/)).
- **The "why the incumbent method fails" citation:** the lookalike-targeting critique ([Culture for Hire](https://www.cultureforhire.com/blog/bso)).

**And the honest limitation to state yourself, before a judge finds it:** no one can prove that affinity predicts ticket purchase from a 26-day build. So the product is explicitly designed as a **prioritisation and testing instrument**, it ships with a falsification condition on every plan, and the repo contains the measurement protocol. Voluntarily naming the boundary is worth more with this judge panel — which includes an OpenAI board member and Qloo's own CTO — than overclaiming.

---

## 10. Proposed tech stack

| Layer | Choice | Why |
|---|---|---|
| Front end | **React + TypeScript + Vite**, Tailwind, Leaflet + OpenStreetMap tiles | You know it; fast; the map must be real. Credit OSM/ODbL — Qloo's own FAQ says they use OSM data. |
| API / BFF | **Next.js route handlers** or a thin Express/Fastify server | Secrets stay server-side; no credential ever reaches the browser. |
| Agent service | **Python + FastAPI + LangGraph** (or a hand-rolled planner loop) | Your existing stack; the loop is plan→tool→evaluate→(widen \| stop). |
| Qloo access | **`@qloo/qloo-harness`** for the workflow-path (`describe`, `entity_tags`, `recommend`, `compare_audiences`, `where_popular`) **plus a typed raw-HTTP client** for parameters the harness may not expose (`feature.explainability`, `diversify.by`, `analysis/compare`, `heatmap.dimensions`) | Harness = the authorised surface and gives you workflow status/correlation IDs; raw client = the depth that wins the "Technological Implementation" criterion. **Confirm the workflow list in #api-help before committing.** |
| Resilience | LRU cache (6–24h), token-bucket limiter at ~3 req/s, bounded retry on 429, hard per-analysis call budget, full trace recorder | A peer project measured that Qloo throttles around the 6th call within a second. Respect the shared quota — and say in the README that you do. |
| Persistence | **PostgreSQL** (SQLite acceptable for MVP) | Saved analyses, share links, cached entity resolutions. |
| Deploy | **Vercel/Render front end + Render/Fly agent service** | Must be externally hosted and publicly reachable — a hard requirement. |
| LLM | Any frontier model for parsing + narrative only | **Rule: the LLM never invents a score, an entity, or a place.** All numbers come from Qloo. Enforce this in code, not in the prompt. |
| Licence | **MIT** | Must be visible in the repo's About section. |

---

## 11. Expected development time

| Phase | Days | Output |
|---|---|---|
| Keys + spike | 0.5 | API key received; hardcode-tested `/search`, `/v2/insights`, `/v2/heatmap`; **confirm artist heatmap behaviour and which dietary/venue tags exist** |
| Qloo client + trace + cache + limiter | 1 | Reusable, testable, budgeted |
| Tool layer (6 tools) | 1.5 | `resolve`, `taste_dna`, `adjacent_cohorts`, `heatmap`, `score_slate`, `compare` |
| Planner loop + honest-failure branch | 1 | Plan–act–evaluate with a step budget |
| UI shell + progressive reveal | 1.5 | The 2-minute demo path |
| Map + novelty slider | 1.5 | The two wow moments |
| Test card + receipts panel | 1 | The rigour that wins criteria 1 and 3 |
| LLM baseline harness + scoring script | 1 | The evidence |
| Deploy + README + write-up + licence | 1 | Submission-ready |
| **Total** | **~10 working days** | Leaves ~16 days of buffer for Qloo coverage surprises — which is the correct amount, because coverage surprises are the biggest risk. |

**Suggested order of cuts if you fall behind:** multi-domain cohorts → single domain; novelty slider → fixed ranking; saved analyses → stateless; the LLM baseline table → a scripted, pre-computed table committed to the repo (still real data, just not live).

---

## 12. What to write in the Qloo API-key application / project-idea field

The form: **https://forms.gle/zz12orkLHTAneLGz6** · keys arrive by email "within a few business days" · Qloo confirms you may submit **before you have a finalised idea** ("Leave the project idea field blank or describe a general direction").

You should still submit a real description — it sets expectations and may route you to help. Use this:

> **Project idea — "Adjacent"**
>
> Adjacent is an audience-development agent for cultural institutions — orchestras, museums, indie cinemas and festivals that are losing their audiences and cannot see who isn't coming.
>
> The problem is structural: every analytics tool the sector owns is built on ticket data, so it can only find more people who look like current ticket-buyers — the "lookalike targeting" model that produced the decline. Boston Symphony reported a 40% attendance fall over 20 years; NEA data shows live classical attendance halving (8.6% → 4.6%, 2017→2022); and the Wallace Foundation's literature review found "no obvious solutions."
>
> Adjacent uses the Qloo Taste AI API to fix the cold-start problem directly. An organisation pastes its last season and its venue address. The agent resolves each work to a Qloo entity, derives the programme's taste profile (`filter.type=urn:tag`), expands across domains to find adjacent cultural cohorts with measured affinity (`urn:entity:artist`, `movie`, `book`, `brand`, `place`), uses `filter.type=urn:heatmap` to show block-level where those people live relative to the venue, uses `urn:demographics` for audience skew, and scores a candidate programme addition in both directions using `filter.results.entities` and `/v2/analysis/compare`. Every claim ships with the exact Qloo call and `feature.explainability` attribution behind it, and the agent is built to fail honestly — if the graph returns no entities, the panel stays empty rather than falling back on model priors.
>
> **Qloo is not a feature here, it is the substrate.** There is no substitute dataset for "which specific culture cohorts over-index on what we make, and where do they live." Without Qloo the product collapses into generic arts-marketing advice, which is a category with many existing tools.
>
> Planned endpoints: `/search`, `/entities`, `/v2/tags`, `/v2/audiences`, `/v2/insights` (artist, movie, book, brand, place, tag, heatmap, demographics), `/v2/analysis/compare`, `/v2/trending`.
>
> **Two specific questions I'd like to confirm before building:** (1) Does `urn:heatmap` reliably return affinity for *artist* entities as the signal in mid-size US metros, and at what geographic precision does coverage degrade? (2) Which tag families exist for place dietary/venue attributes (e.g. cuisine, venue category) — I want to know the real boundary rather than assume it.

**Send that two-question block regardless of what else you write.** It signals you've done the reading, it gets you a real answer from #api-help on Discord, and it will be the difference between shipping in 10 days and shipping in 20.

---

## 13. What we still need to confirm from Qloo before writing code

**Blockers — resolve before you architect anything:**

| # | Question | Why it matters | How to test |
|---|---|---|---|
| 1 | **Does `urn:heatmap` return meaningful affinity when `signal.interests.entities` are *artists* (as opposed to tags/genres)?** A peer project measured that music/artists *do* move the heatmap while food/activity tastes do not. | The map is one of the two wow moments. If artist-driven heatmaps are thin, the wow degrades to a tag-driven map. | 3 calls: heatmap with an artist ID, with a genre tag, and with a neutral control, on a known city. |
| 2 | **What is the real geographic coverage in mid-size US metros and non-US cities?** Docs warn "may not have data for every entity or region." | Determines which demo city you choose. **Choose a major Western metro.** | Run the season through 3 candidate cities; record empty-result rates. |
| 3 | **Does `signal.location.query` genuinely influence `filter.type=urn:entity:artist` results?** One peer project used it successfully in a live run on 2026-10-03, but Artist's documented parameter table does **not** list `filter.location`. | If it works, cohort geography strengthens considerably. If not, you must lose "where do *artists* live" and keep only "where do *listeners* live" via the heatmap. Design accordingly. | A/B the same artist query with and without `signal.location.query`, compare result sets. |
| 4 | **What does `feature.explainability=true` actually return, and how large is the payload?** Docs describe per-recommendation attribution plus aggregate influence — but not size. | It is your receipts panel. Verbose responses (the docs note `akas` bloat) may need truncation on your side since fields can't be filtered. | One call; inspect the shape; write your own normaliser. |
| 5 | **Which Qloo tag families exist for place attributes** (cuisine, venue category, activity)? | Determines whether you can say anything specific about *what kind of place* a cohort frequents. | `/v2/tags?query=…` across ~20 candidate terms; record which return usable URNs. |

**Second-order — resolve in the first two days:**

| # | Question |
|---|---|
| 6 | **Rate limit shape.** Peer reports suggest ≈5 calls/second. Confirm the actual ceiling and whether it is per-key. |
| 7 | **Does the harness expose `feature.explainability`, `analysis/compare`, `diversify.by` and `heatmap.dimensions`?** If not, the raw client is mandatory — plan the harness as a *thin* convenience layer, not the foundation. |
| 8 | **Pagination and depth.** `take` is capped at 50. How deep do artist/place result sets actually go for a niche seed? |
| 9 | **Popularity percentile distribution.** Is `filter.popularity` well-calibrated enough to use as a "novelty vs. mainstream" axis? Sample 100 entities across the range and plot. |
| 10 | **`analysis/compare` semantics.** The response model (`descriptive` vs `predictive`) and how to read overlap — needed for the A/B slate scoring. |
| 11 | **Affinity-score sensitivity.** Qloo explicitly warns that 91 vs 92 is not meaningful. Establish *your own* threshold for "this difference is worth showing" and encode it. |
| 12 | **Terms constraints on the demo.** Confirm nothing about the comparison against an LLM baseline or the public publishing of Qloo-derived figures conflicts with the Hackathon API terms. |

**Also join the Qloo Hackathon Discord (discord.gg/rF9PKsD5Q7, channel `#api-help`).** Their lead technical writer monitors it. The two-question block above belongs there on day one.

---

## 14. Two honest warnings

**Warning 1 — differentiation has a half-life.** I found 24 competing projects in one research pass, and there are 356 participants with 26 days left. Several of my "unsaturated" picks (arts audience development, gifting, content acquisition) will attract copycats once submissions become visible. **Your moat is not the idea; it is the receipts, the honest-failure behaviour, the pre-registered LLM comparison, and the depth of API use** (heatmap + explainability + `analysis/compare` + `filter.results.entities` + popularity percentiles, in one coherent workflow). Those are harder to copy than a concept, and they are exactly what the "Technological Implementation" criterion measures.

**Warning 2 — do not let the report become the project.** You have 26 days and this document is ~12,000 words. The build is ~10 working days. Spend today getting the API key submitted and the five blocker questions into Discord, and start coding against a mock Qloo client tomorrow. The single biggest failure mode from here is spending week one planning.

---

### Source index
Every external claim in this document is linked inline. Primary documentation sources: [Qloo API Overview](https://docs.qloo.com/reference/api-overview) · [Insights API Deep Dive](https://docs.qloo.com/reference/insights-api-deep-dive) · [Entity Type Parameter Guide](https://docs.qloo.com/reference/available-parameters-by-entity-type) · [Hackathon Developer Guide](https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide) · [Heatmaps](https://docs.qloo.com/reference/heatmaps-use-case) · [Demographics](https://docs.qloo.com/reference/demographics-use-case) · [Taste Analysis](https://docs.qloo.com/reference/taste-analysis) · [Analysis Compare](https://docs.qloo.com/reference/analysis-compare) · [Trending](https://docs.qloo.com/reference/get-trending) · [FAQs](https://docs.qloo.com/docs/faqs) · [Qloo Terms of Use](https://www.qloo.com/legal/terms) · [Hackathon Devpost](https://qloo.devpost.com/) · [2025 gallery](https://qloo-hackathon.devpost.com/project-gallery)
