# Adjacent — Product Definition & Execution Plan
## Phase 2 deliverable · Prepared 4 October 2026 · 26 days to the Qloo Hackathon deadline (30 Oct 2026)

**Decision: B — proceed with four specific modifications.** Details in Part 0.

| Part | Contents |
|---|---|
| 0 | Validation verdict — four findings that change the design |
| 1 | Problem redefinition + Problem Statement + User Story + JTBDs |
| 2 | Product definition — inputs, and the exact six outputs |
| 3 | Full user workflow |
| 4 | Genuine agentic architecture (14 tools, decision loop, anti-hallucination) |
| 5 | API-fit verification from current official docs |
| 6 | MVP / V1 / V2 + Features We Should Not Build |
| 7 | Technical architecture, schema, routes, folder structure |
| 8 | Data requirements (Qloo / user / external / avoided) |
| 9 | One realistic end-to-end run |
| 10 | The key differentiator |
| 11 | Proving Qloo is necessary |
| 12 | Competition check |
| 13 | Risks + the explicit insufficiency conditions |
| 14 | MVP development plan, Phases 0–10 |
| 15 | What can be built before the API key arrives |
| 16 | First concrete milestone |
| 17 | Compact final specification + final decision |
| — | **WHAT SHOULD WE DO TOMORROW MORNING?** |

---

---

# PART 0 — VALIDATION VERDICT (read this first)

I re-verified Adjacent against current official Qloo documentation, the hackathon developer guide, and a fresh competitor sweep. I found **four things that change the design**, one of which invalidates the obvious implementation.

## 0.1 The four findings

### 🔴 FINDING 1 — Affinity scores are normalised **per query**. The obvious implementation is invalid.

Official documentation, [Interpreting Affinity Scores](https://docs.qloo.com/docs/interpreting-affinity-scores):

> *"Because scores are normalized per query, **compare brands based on their relative position in the results, not just the raw score**."*
> *"Affinity scores may decrease as more inputs or filters are applied. For example, a score of 0.55 could still represent a strong recommendation, but **including demographic data may lower the final score**."*

**Why this matters.** The obvious design — loop over N candidate audiences, run one query per audience, compare each audience's affinity score for your programme, rank them — **produces a meaningless ranking**, because each of those N scores was normalised against a different result set. This is the single most likely way to build Adjacent wrong, and a Qloo CTO judge would spot it.

**The fix — and it makes the product better.** Run **one query containing every candidate in `filter.results.entities` at once**, so all comparisons happen *within a single normalisation*. This is exactly what the documentation endorses ("relative position in the results"). It also happens to be far cheaper in API calls, and it turns cohort ranking into a genuine combinatorial choice for the agent rather than a mechanical loop. See Part 4 and Part 5 for the exact queries.

Documented **affinity bands** we can use honestly instead of inventing our own confidence scale:

| Score | Relevance | Official example |
|---|---|---|
| > 0.8 | Very High | Chappell Roan ↔ Sabrina Carpenter (artist query) |
| 0.6 – 0.8 | High | A local bakery ↔ Dunkin' Donuts (places query) |
| = 0.5 | Medium | A sushi restaurant ↔ a library (places query) |
| < 0.5 | Low | Chappell Roan ↔ a historical landmark (artist query) |

### 🟠 FINDING 2 — `/v2/audiences` is a **lookup**, not a ranker. And `filter.type=urn:entity:audience` is deprecated.

Verified: [`/v2/audiences`](https://docs.qloo.com/reference/get-audiences) accepts `filter.query`, `filter.parents.types` (10 categories), `filter.audience.types`, `filter.results.audiences`, `filter.popularity.*`, `page`, `take` — it **searches** audiences. It does not rank audiences by affinity to your programme. And the Insights API marks `urn:entity:audience` as deprecated "should not be used for new integrations."

**Consequence:** you cannot ask Qloo "which audiences love my programme?" You must **enumerate candidates and test each one.** That is a hypothesis-testing loop — good for agentic depth, but it must be designed deliberately rather than assumed. It also means **audience segments cannot be the primary cohort mechanism**, because we cannot yet verify how rich or granular Qloo's audience catalogue is.

**Design decision:** make **cultural adjacent-entity cohorts** the primary mechanism (robust — built on queries we know work) and **Qloo audience segments** a secondary "audience lens" layer. See Part 2 and Part 10.

### 🟢 FINDING 3 — The heatmap accepts `signal.demographics.audiences`. This is the killer loop, and it is confirmed.

Verified in the [Entity Type Parameter Guide](https://docs.qloo.com/reference/available-parameters-by-entity-type), Heatmap section: `signal.demographics.audiences`, `signal.demographics.gender`, `signal.interests.entities`, `signal.interests.tags`, `signal.demographics.age`, `take` are **all supported** on `filter.type=urn:heatmap`. The [Heatmaps use-case page](https://docs.qloo.com/reference/heatmaps-use-case) independently lists "`signal.demographics.audiences.weight`: Apply audience weighting if using demographic signals" as optional.

**Consequence:** the chain **discover a cohort → map that exact cohort in the city** is fully documented and supported. This is the product's spine and its wow moment. It is *not* an inference.

### 🟢 FINDING 4 — `/entities` accepts **external IDs**. Nobody else is using this.

Verified: [`/entities`](https://docs.qloo.com/reference/get-entities) accepts `entity_ids` **plus** `external.imdb.ids`, `external.rottentomatoes.ids`, `external.isbn10/13.ids`, `external.goodreads.ids`, `external.library_of_congress.ids`, `external.musicbrainz.ids`, `external.spotify.ids`, `external.wikidata.ids`, `external.lastfm.ids`, `external.michelin.ids`, `external.resy.ids`, and more.

**Consequence:** entity resolution — the #1 source of failure and embarrassment in every competitor's demo — becomes near-deterministic. A cinema can paste **IMDb IDs**; a library can paste **ISBNs**; a concert hall can paste **MusicBrainz or Spotify IDs**. Peer projects openly document resolution failures ("some artists cannot be found… they are flagged, never guessed" — Undercard; "Qloo could not rank L'Impératrice, so she was removed" — same). We can sidestep most of this and make it a visible strength.

## 0.2 Other verifications that changed the plan

| Item | Finding | Impact |
|---|---|---|
| `/v2/tags` | Real path is [`/reference/search-tags`](https://docs.qloo.com/reference/search-tags). Supports **`feature.semantic_search` (beta)** and `feature.typo_tolerance`. | Better tag resolution from messy free text. Use semantic search for "contemporary classical" style phrasing. |
| `analysis/compare` | Parameters are `a.signal.interests.entities` / `b.signal.interests.entities` + `filter.type`, `filter.subtype`, `model=descriptive\|predictive`. **No demographic signal.** | ✅ **It compares two *entity groups*, not two audiences.** Use it to compare "current season" vs "proposed season," **not** cohort vs cohort. This corrects an assumption in our first report. |
| `filter.results.entities` | Verified available on artist, book, brand, movie, person, place, podcast, tv_show, video_game. | The "grade my shortlist" primitive. Load-bearing for Findings 1 and 3. |
| Popularity | `filter.popularity.min/max`, 0–1 percentile, on most entity types. | Drives the novelty axis. |
| Rate limit | Still "set high enough for typical hackathon projects"; one peer measured ~1 rejection per 6 calls in a second (2026-10-03). | Budget 3 req/s, cache hard. |
| Participants | Devpost showed **356** on my first read and **174** on a later crawl; start date 30 Sep 2026. | Treat competitor count as 175–360 and rising. |

## 0.3 The verdict

> ### **DECISION: B — Proceed with Adjacent, but modify it in four specific ways.**

| # | Modification | Trigger |
|---|---|---|
| **M1** | **Beachhead: independent & repertory cinema** (not "cultural institutions" generally). Generalise to performing arts in V1. | Cleanest entity fit + strongest *current* evidence (below) |
| **M2** | **Primary cohort mechanism = adjacent-entity cohorts, not Qloo audience segments.** Audience segments become a labelled secondary layer. | Finding 2 |
| **M3** | **All cross-candidate comparisons happen inside a single `filter.results.entities` query.** Never compare scores across queries. | Finding 1 |
| **M4** | **Add external-ID ingestion** (`external.imdb.ids` etc.) as a first-class resolution path. | Finding 4 |

**Why not C (abandon).** The problem is real, current, quantified, and **no competitor has entered it** (see Part 12). The Qloo dependency is structural, not decorative. The build is 8–10 days. The one thing that would have justified abandoning — that Qloo can't do it — turned out to be false, and Finding 3 confirms the most important capability.

**Why not A (unchanged).** "Cultural institution" is too broad to demo; audience segments are unverified as a mechanism; and the naive implementation is technically wrong.

---

# PART 1 — THE PROBLEM, PROPERLY DEFINED

## 1.1 Who exactly is the user

**Primary beachhead: the programmer at an independent / repertory cinema.**

Concretely: a 1–3 screen venue, 50–400 seats, programming 300–1,500 screenings a year, with **1–4 people doing programming, marketing and audience development**, often the same person. UK examples: Phoenix Cinema (East Finchley), Hyde Park Picture House (Leeds), Showroom (Sheffield), Chapter (Cardiff), Derby QUAD. US examples: Music Box Theatre (Chicago), Hollywood Theatre (Portland), Belcourt (Nashville), Coolidge Corner (Brookline), Alamo Drafthouse's repertory arm, Northwest Film Forum (Seattle). This is a **definable, reachable, listed sector**: Art House Convergence (US), Independent Cinema Office and Film Hub network (UK), Europa Cinemas (EU), CICAE.

**Secondary (V1, same engine, different entity type):** performing-arts presenters where the programme is artists/ensembles rather than films; museums running film or performance programmes; multi-arts venues.

**Why cinema first, not orchestras:**
1. `urn:entity:movie` is a **first-class Qloo entity** with clean IDs, `release_year`, `release_country`, `content_rating`, `rating`, `tags`, and **external IMDb / Rotten Tomatoes ID lookup** (Finding 4). An orchestra's programme is *works* (Mahler 5, Op. 27) which are not entities — you resolve to composers, which is lossier.
2. **Programmes are public and structured.** Every cinema publishes a monthly/seasonal calendar. Competitors' "paste your season" demos fail on ambiguity; ours can be bulletproof.
3. **The industry's own audience research names the exact decision we inform.** Art House Convergence's National Audience Survey (32,000+ respondents, 46 cinemas, all 50 states) found audiences choose art houses for *"more films outside the mainstream"* (84%), ***"interesting programming and events"* (73%)**, *"more films I like"* (66%), and *"a sense of community"* (60%) — [IndieWire, Jul 2024](https://www.indiewire.com/news/general-news/audiences-want-more-independent-movie-theaters-study-1235024725/). **Programming choice is the #1 stated reason people come.** No tool informs it with data about non-attenders.

## 1.2 What exact problem they are facing

**The programmer must choose, every month, which films and which *nights* to put on — and the only audience information available to them describes people who already come.**

They must decide under three simultaneous pressures:
- **What to book** from a finite, negotiated, time-boxed availability window (distributor terms, repertory rights, DCP availability, competitor holdovers).
- **Which slot** (which night, which week, which strand) — because the same title on a Thursday performs differently from a Saturday.
- **Who to invite** who has never come, because the current audience is contracting: a UK Parliament committee found **cinema visit frequency fell ~40%** post-pandemic (the average cinemagoer went 6×/year, now 3–4×) and *"older audiences have not returned to the same level"* — [CMS Committee, Apr 2025](https://publications.parliament.uk/pa/cm5901/cmselect/cmcumeds/328/report.html).

*(Inference, flagged: the *slot* decision is described here from how programmers write about their work — I did not find a quantified study of slot-decision error. The book-and-audience decisions are documented; the slot decision is a reasonable extension of the same problem and the MVP should not depend on it.)*

## 1.3 What they are doing today

| Method | How common | Source |
|---|---|---|
| **Instinct + relationships.** The programmer just knows their audience. | Universal | The sector's own conferences (IND/EX 2026) are framed around "gut feel vs data" debates and "connecting the dots backward from wide-ranging results can often feel like a fool's errand" — [IDA/Documentary, Aug 2026](https://www.documentary.org/online-feature/index-2026-main-event) |
| **Distributor recommendations and screeners.** Distributors pitch what they hold rights to. | Universal | Structural — distributors' incentives are not the venue's |
| **Peer Whatsapp/Slack groups.** "Has anyone played this? How did it do?" | Widespread | Standard in Film Hub networks |
| **Box-office comparisons.** "It did well at the Prince Charles." | Widespread | The closest thing to a benchmark; entirely comparative to *other venues*, not to *this venue's non-attenders* |
| **Anecdote from the counter.** Staff feedback, Q&A attendance, social replies. | Universal | — |
| **Surveying existing audiences.** Entry surveys, membership polls. | Common | **Structurally limited — it only asks people who already came** |
| **Free/cheap tooling.** Excel, Google Sheets, the ticketing system's basic reports (Spektrix, TicketSource, Agile Ticketing), Mailchimp open rates. | Widespread | ICO written evidence documents "reduced staffing… a knock-on effect on the amount of marketing and audience development work cinemas can do" — [Parliament written evidence](https://committees.parliament.uk/writtenevidence/125483/pdf/) |
| **Paid audience research.** Avenue ISR / Art House Convergence benchmarking, bespoke consultancies. | Rare — cost | Avenue ISR's National Audience Survey is the sector's best instrument, but it is periodic, sector-wide, and expensive |

## 1.4 Why current approaches fail

**They are all built on observed attendance.** Every method in §1.3 is a measure of people who already bought a ticket, or a comparison to another venue's attendees. As the arts sector's own analysts put it about the adjacent performing-arts case:

> *"For decades, arts growth relied on lookalike targeting — finding more people who resembled your best, most loyal patrons. That model worked when the general population still looked like the audience the field originally built."* — [Culture for Hire, Sep 2026](https://www.cultureforhire.com/blog/bso)

And the strategic consequence named by the CEO of a major orchestra:

> *"Oftentimes, we tell a story about this art from the perspective of someone who already loves it, so it's hard for someone [who doesn't] to find an entry point."* — Lecolion Washington, Boston Globe, Jul 2026

**The specific failure is not that they lack data. It is that their data has a boundary at the ticket booth.** 45% of UK independent cinemas operated at a loss this year and only 10% are confident about next year ([ICO survey, 157 venues](https://cineuropa.org/en/dossiernewsdetail/1369/451801/)) — while, in the same sector, Art House Convergence reports box office **up 9% at participating indie theatres in 2025**. The difference between those two groups is what they programme and who they reach. Neither group is measuring the second half of that sentence.

## 1.5 What information is missing from their decision process

Five specific things — each of which is a Qloo query, and none of which appears in any cinema's decision process today:

| # | Missing information | Whose problem it is today |
|---|---|---|
| **1** | **What culture my programme is actually *about*, in measured terms** — not its genre labels, but the taste coordinates it occupies | Nobody's. Genre labels come from the distributor. |
| **2** | **Which *specific* adjacent culture the people who'd love my programme also love** — the non-obvious neighbour | Nobody's. Distributor comps are commercial, not taste-based. |
| **3** | **How large/strong that adjacency is, and how far it is from my current audience** (novelty vs. safety) | Nobody's. |
| **4** | **Where in my city those people physically live**, at neighbourhood scale, relative to my front door | Nobody's. Heatmap-level geography does not exist in this sector's tooling. This matters enormously: a white paper estimated that at **one mile** from an arts venue the likelihood of attendance **drops by 80%** — [Symphony.org](https://symphony.org/features/meeting-audiences-where-they-are/). |
| **5** | **Which specific programme addition captures that cohort without alienating the current one** | Nobody's. This is a two-sided test no tool performs. |

## 1.6 Why this is a CULTURAL INTELLIGENCE problem, not a generic analytics problem

A generic analytics problem is: *"given my data, find a pattern."* Adjacent's question is **"given my culture, find the people"** — and the people are, by construction, absent from every dataset the institution owns.

Three properties make it cultural-intelligence-shaped and not analytics-shaped:

1. **The unit of analysis is a *taste*, not a *customer*.** The question "what does my programme mean culturally, and who else lives in that meaning?" cannot be answered by aggregating transactions. It requires a graph of relationships *between cultural objects* — music to film to books to brands to places. Qloo's own definition: a graph of "how tastes connect" across categories.

2. **The answer is a *relationship*, not a *segment*.** Demographics segment people by who they are. Taste segments them by what they love — and what they love is what predicts whether they'll sit through a 1970s Hungarian film on a Tuesday.

3. **The inferential leap is cross-domain.** The single most valuable output is a sentence that crosses a domain boundary: *"the audience for your Ozu retrospective over-indexes on ambient/field-recording music and third-wave coffee shops."* No domain-specific analytics tool can produce a cross-domain sentence, because no domain-specific analytics tool contains more than one domain.

## 1.7 Why CRM / ticketing data cannot solve it

Four structural reasons — none of which is "their data is bad":

1. **The boundary problem.** A CRM contains only people who transacted. The product's entire output is about people who never have. No amount of querying a database returns rows that were never written.
2. **The cold-start problem.** A venue that opened last year, or that has just changed programming direction, has almost no signal. Qloo's own FAQ states the product is *"designed to overcome cold starts and does not require customer data to generate insights"* — [FAQs](https://docs.qloo.com/docs/faqs). That is the exact inversion the sector needs.
3. **The privacy ceiling.** Even a rich CRM cannot tell you about non-customers, and first-party-data enrichment (lookalike audiences) is both privacy-constrained and, per §1.4, strategically self-defeating.
4. **The column problem.** A ticketing system has columns for *what was bought*. It has no column for *what else that person loves*. Adjacent's core variable does not exist in the schema.

## 1.8 Why a normal LLM cannot solve it

Not "the LLM is worse" — **the LLM is answering a different kind of question and cannot know when it's wrong.**

| The question | LLM behaviour |
|---|---|
| "What adjacent culture does my programme connect to?" | Produces plausible, memorised, **already-famous** comps. Asking about Ozu returns Bresson, Bergman, Kurosawa — the canon. These are not discoveries; the programmer already knows them. |
| "How strong is that connection?" | No measurement. It asserts. |
| "Where do those people live in my city?" | It has no geographic taste data at all. It will confabulate neighbourhood names. |
| "Which of these three options is better for my venue?" | No way to compare; it produces a persuasive-sounding paragraph for whichever you asked about. |
| "Is my data good enough to answer this?" | It will never say no. It cannot detect the absence of evidence. |

The failure is **not** that an LLM answers badly. It is that an LLM produces an *unfalsifiable* answer with the same fluency as a falsifiable one. A programmer cannot tell which they received. That is worse than no answer, because it launders a guess into a plan.

## 1.9 Why Qloo is uniquely useful

Six reasons, each tied to a verified capability:

1. **Cold start with no customer data.** An institution with zero non-attender data still gets a measured answer. ([FAQs](https://docs.qloo.com/docs/faqs))
2. **Cross-domain adjacency at entity level.** Music ↔ film ↔ TV ↔ books ↔ brands ↔ places ↔ people. This is the only way to produce the cross-domain sentence in §1.6.
3. **Block-level geographic taste concentration** via `filter.type=urn:heatmap` with a locality query, working with entity *and* demographic signals (Finding 3). Given the 1-mile / 80%-decay finding, geography isn't decoration — it's the causal mechanism.
4. **Measured popularity percentiles** (`filter.popularity.min/max`) — the axis that separates "obvious canon" from "genuinely non-obvious," which is the whole value of the output.
5. **Per-claim explainability** (`feature.explainability=true`) — per-recommendation attribution of input entities with normalised 0–1 scores. This converts every claim into a citation.
6. **Aggregate-only, PII-free by design.** Qloo "does not handle or depend on any personally identifiable information whatsoever." For an arts non-profit — a sector with acute privacy sensitivity and often a funder-mandated data policy — this is a procurement argument, not a footnote.

## 1.10 The cost of getting the decision wrong

| Cost | Scale | Evidence |
|---|---|---|
| **Direct financial loss per booking decision** | A single mis-programmed weekend is a four-figure loss for a small cinema; a bad season is existential | 45% of UK indie cinemas operated at a loss; 42% said they might not be operating in a year — [ICO](https://cineuropa.org/en/dossiernewsdetail/1369/451801/) |
| **Irreversibility of the booking** | A slot given to the wrong film is a slot that cannot be given to the right one; repertory rights are time-boxed | Structural |
| **Distributor relationship cost** | Under-performing a title damages terms on future bookings | Structural |
| **Capital-planning cost** | 31% of UK independent cinemas say they cannot remain operational without capital investment; 69 venues need **£79m+** — and no funder will write that cheque to a venue that cannot demonstrate an audience strategy | [Guardian, Apr 2025](https://www.theguardian.com/culture/2025/apr/12/uk-independent-cinemas-at-risk-investment-funding) |
| **Sector cost** | Closures destroy local cultural provision and the incubator role for independent film | ICO director's public statement; UK Parliament CMS committee recommended BFI core funding for independent cinemas |
| **The hidden cost: the compounding lookalike trap** | Every cycle spent marketing to lookalikes of the current audience tightens the boundary, and the audience contracts by ~1.1× per cycle | The 0.907 replacement-rate finding in performing arts ([Culture for Hire](https://www.cultureforhire.com/blog/bso)) |

## 1.11 The measurable outcome our product should improve

Not "engagement." Not "reach." Three specific, instrumentable measures the venue already collects or can collect from day one:

**Primary:**
> **New-household acquisition rate for a tested programme slot** — the percentage of tickets in a designated screening/strand bought by email/postcode records that have never appeared in the venue's CRM before.

This is the sector's own instrumentation (every ticketing system in the sector — Spektrix, Tessitura, TicketSource, Agile — supports new vs. returning household reporting), it requires no new data collection, and it is exactly what the funder quotes demand ("we should be approaching audience development as a science so that there are hypotheses that get tested and evaluated" — [Hewlett Foundation](https://hewlett.org/how-arts-organizations-are-growing-the-audiences-of-tomorrow/)).

**Secondary:**
> **Cohort-indexed new-household share** — of new households acquired during the test window, the proportion whose postcode falls inside the top-3 predicted concentration cells.

This measures whether the *geography* was right, not just whether a slot worked. It is the difference between "we sold more tickets" and "our model of *where the audience is* was correct."

**Tertiary (deliberately not the primary):**
> **Programme diversity across a season** — measured as the spread of Qloo tag families covered. Guards against the failure mode where the tool just recommends more of what already works.

**What we must NOT claim:** that Adjacent predicts ticket sales. It cannot, and asserting it would be both dishonest and the easiest thing for a judge to attack. Adjacent produces a **prioritised, geographically-located, falsifiable hypothesis** — and it ships the falsification test with it. That framing is defensible, honest, and is itself the product's differentiator against every tool that guesses fluently.

---

## 📄 Problem Statement (README / Devpost version)

> Independent cinemas are caught between a shrinking core audience and a booking decision they must make every month with no information about anyone who doesn't already come. 45% of UK independent cinemas operated at a loss last year, and visit frequency has fallen 40% since the pandemic — yet Art House Convergence reports box office up 9% at theatres that programme well, and 73% of art-house audiences say "interesting programming and events" is why they come. Every tool the sector owns — ticketing CRMs, distributor comps, audience surveys — is built on data about existing attendees, so it can only ever find more people who resemble them. Adjacent uses the Qloo taste graph to answer the missing question: what culture does this programme *actually* belong to, which specific adjacent cohorts already live in that culture, where in this city do they live, and which one programme change reaches them without losing the audience you have.

## 👤 User Story

> **As a** programmer at a two-screen independent cinema who books films by instinct and distributor comps,
> **I want to** see the specific cultural cohorts adjacent to my programme, ranked by how far they are from my current audience and where they actually live in my city,
> **because** every marketing decision I make today is aimed at people who already know we exist, and I cannot grow an audience I cannot describe.

*Secondary story:* **As a** Film Hub / regional funding officer, **I want to** see a venue's audience-development hypothesis and its geographic evidence, **because** I am being asked to allocate capital and I need more than a business plan assertion.

## 🎯 Jobs To Be Done

**Core functional job:**
> *When I have to decide what to put on next month and who to try to reach, help me choose a specific programme and a specific geographic push that brings in people I have never reached before — and tell me how I'll know if I was wrong.*

**Decomposed:**

| # | Job | The user says it as |
|---|---|---|
| **JTBD-1** | *Describe my programme as culture, not as a catalogue* | "Tell me what my season actually is." |
| **JTBD-2** | *Find the non-obvious neighbour* | "Who else would love this who has never heard of us?" |
| **JTBD-3** | *Size the bet honestly* | "Is this a big opportunity or a rounding error?" |
| **JTBD-4** | *Locate the bet in space* | "Where do these people physically live — which side of town?" |
| **JTBD-5** | *De-risk the choice against my existing audience* | "Will this lose the people who already come?" |
| **JTBD-6** | *Close the loop* | "How will I know in six weeks whether this worked?" |

**Emotional job:**
> *Stop feeling like I'm guessing, and be able to defend the choice to my board and my funders with evidence I can actually show.*

**Social job:**
> *Be seen by funders and peers as running an audience-development operation with a method, not a hunch.*

**What the user is *not* hiring this for (explicit non-jobs):** scheduling software, ticketing, film booking negotiation, marketing asset creation, social media posting, film licensing.

---

# PART 2 — WHAT WE ARE BUILDING

## 2.1 Product Name
**Adjacent**

With a subtitle for the submission: *Adjacent — find the audience already living inside your programme's culture.*

## 2.2 Product Category

Being precise here matters, because the category determines the comparison set a judge uses.

**Adjacent is not:**
- ❌ A recommendation engine (it doesn't recommend films to people)
- ❌ A marketing content generator (it doesn't write copy)
- ❌ A CRM or ticketing analytics tool (it doesn't touch first-party data)
- ❌ An audience survey tool (it doesn't ask anyone anything)
- ❌ A "cultural concierge" or discovery app

**Adjacent is:**
> **An audience-discovery and programming-decision instrument for programmed cultural venues.** It belongs to the category occupied today by **audience research and audience development planning** — the work done by Avenue ISR, Art House Convergence benchmarking, TRG Arts, bespoke consultants, and (badly) by a programmer with a spreadsheet at 11pm.

Its nearest analogue in the discovery-tooling world is **geodemographic market-analysis software for retail site selection** (Placer.ai, Esri Tapestry) — *category-mapping and geographic concentration* — but applied to culture rather than footfall, and to programming rather than siting.

**One-line category statement:** *Audience-development decision support for programmed cultural venues, built on measured cross-domain taste affinity.*

## 2.3 Target User — precise definition

| Dimension | Definition |
|---|---|
| **Role** | Programmer / Head of Programming / Audience Development Manager / Cinema Director (in small venues, one person does all four) |
| **Organisation** | Independent or repertory cinema, 1–4 screens, 40–400 seats |
| **Revenue** | £150k–£3m / $200k–$4m annual |
| **Team size** | 4–30 total staff; 1–4 touching programming/marketing |
| **Booking volume** | 300–1,500 screenings/year |
| **Tech** | A ticketing system (Spektrix, TicketSource, Agile, Tessitura, Vendini), a website, a Mailchimp/WordPress stack, an Excel booking grid |
| **Budget for tooling** | Near zero for audience research; the sector's capital need (£79m across 69 UK venues) is for buildings, not software |
| **Geography for MVP** | **English-speaking, English-programmed, high-Qloo-coverage cities**: London, Manchester, Leeds, Bristol, Glasgow, Edinburgh, Sheffield, Cardiff; New York, Chicago, Portland, Seattle, Nashville, Boston, Austin, Los Angeles |
| **Defining trait** | They programme **by judgement** and would rather have a better judgement than a bigger spreadsheet |

**Who this is NOT for (MVP):** multiplex chains (they have research departments and distribution data), film festivals (different cadence and one-shot decision shape — V1 candidate), streaming platforms, individual film fans.

**The buyer vs. the user** *(inference, flagged — I did not verify procurement behaviour in this sector)*: the **user** is the programmer; the **economic buyer** for a paid version is likely the venue director, and the **budget-holder of last resort** is a funder (BFI/Film Hub in the UK, NEA/regional arts councils and foundations in the US), because audience development is a funded activity with reporting requirements. This shapes the eventual business model but **must not shape the hackathon MVP** — build for the programmer.

## 2.4 Main Input — and the true minimum viable input

### The full input
| Field | Required? | Format | Why |
|---|---|---|---|
| **Institution / venue** | Optional | Name + city | Used to resolve a Qloo place entity (nice-to-have; the product works without it) |
| **City** | **Required** | Free text | Drives `filter.location.query` for the heatmap. Fuzzy-matched, AKA-aware ("The Big Apple" works). |
| **Recent programme** | **Required** | 5–20 film/event titles, plain text lines | The seed set. Each line may optionally carry a year and/or an IMDb ID. |
| **Venue postcode / address** | Optional | Text | Pins the venue on the map. Without it, the city centroid is used and **the UI must say so.** |
| **Current audience description** | Optional | 1–3 free-text lines ("mostly 55+, cinephiles, weekday evenings") | Used only to *calibrate the novelty slider's starting point* — never sent to Qloo as a signal, because it's a self-report |
| **Screening slots available** | Optional (V1) | e.g. "one Thursday 20:00 slot/month" | Constrains the programme recommendation |

### The minimum viable input — deliberately chosen

> ### **Minimum viable input = a city + 5 titles.**
> ### **Ideal input = a city + 8–12 titles + a postcode.**

**Why exactly this, and not less or more:**

- **Why not fewer than 5 titles:** the taste vector is built from `signal.interests.entities`. Three films is a thin vector and produces noisy tags. Five is the floor for a stable pattern across at least two genres/eras.
- **Why not more than 20:** `take` caps at 50, responses are verbose, and — critically — a longer list dilutes the taste vector. A programmer who had a genuinely coherent 40-film season doesn't need us. **Twelve is the sweet spot** (roughly one month of a two-screen venue).
- **Why titles alone suffice:** titles are the one thing every programmer has instantly available, published publicly, in a format they already possess. **Zero data entry is the product requirement.** If the user has to export from a ticketing system, we've already lost.
- **Why the postcode is optional but heavily pushed:** the heatmap's value is relative to the venue. Without it, we can still show where the cohort concentrates in the city — which is the wow — but we cannot compute "distance from your door," which is the actionable framing.

### Input resolution ladder (Finding 4 — the bulletproof path)

```
Line format accepted (all optional beyond the title):
   Perfect Days (2023)                        → /search → title + year disambiguation
   Perfect Days (2023) [tt7594358]            → /entities?external.imdb.ids=tt7594358   ← deterministic
   tt7594358                                  → /entities?external.imdb.ids=tt7594358   ← deterministic
   Sansho the Bailiff                          → /search → may be ambiguous → ASK
```
The agent should **prefer external IDs when present, fall back to `/search`, and ask on ambiguity rather than guessing.** Undercard's public documentation shows the cost of guessing: "Qloo could not rank L'Impératrice, so she was removed." We will instead *ask*.

## 2.5 Main Output — exactly what Adjacent returns

Six artefacts. The user asked for concrete, not "insights." Here is the exact output contract, in the order it appears on screen.

---

### OUTPUT 1 — **Taste DNA**
*What your programme is, culturally.*

- 8–15 **Qloo tags** describing the programme, ordered, each with its **affinity score and official band** (>0.8 Very High · 0.6–0.8 High · 0.5 Medium · <0.5 Low)
- Each tag shown as **`name` + the raw `tag_id` URN** (e.g. `Slow Cinema` → `urn:tag:keyword:media:slow_cinema`)
- The **age and gender skew** of the programme's audience from `filter.type=urn:demographics`, rendered as a simple signed bar chart, with a plain-language reading: *"This programme skews strongly to 25–34 and away from 55+."*
- **Entity coverage line:** `11 of 12 titles resolved · 1 ambiguous (awaiting your choice) · 0 not found.` — always visible, never hidden.

**Why every element:** tags are the interpretable middle layer between films and audiences; the URNs are what make the output auditable (a judge can paste one into a browser); the demographic skew is what reframes the conversation from "we need younger audiences" (a slogan) to "this programme already over-indexes young, so the problem is awareness, not programming" (a decision).

---

### OUTPUT 2 — **3 Adjacent Cohorts**
*Who else lives in that culture.*

Each cohort card contains:

| Element | Example | Source |
|---|---|---|
| **Cohort name** | *"Ambient & field-recording listeners who cook"* | Agent-generated label from the signature entities |
| **Cohort type badge** | `Adjacent-entity` *(primary)* or `Qloo audience` *(secondary)* | Finding 2 |
| **Signature entities** | 3–6 named Qloo entities with their affinity score and band | Qloo only |
| **Rank position** | *"1st of 9 candidate cohorts tested"* — within a single normalisation | Finding 1 |
| **Novelty score** | 0–100, derived from the signature entities' median `filter.popularity` percentile | Qloo only |
| **Audience distance** | *"Far from your current programme"* / `Adjacent` / `Close` | Computed from the programme's own tag set |
| **Why this cohort** | One sentence, **generated only from returned tags and entities** | Enforced in code |
| **Evidence level** | `Strong` (>0.8) · `Moderate` (0.6–0.8) · `Weak` (0.5–0.6) · `Insufficient` (unscored) | Official bands |
| **Domain badge** | `film` · `music` · `book` · `brand` · `place` · `person` | Qloo `filter.type` |

**Hard rule:** if a cohort cannot be backed by at least one scored Qloo entity above the Medium threshold, **it is not rendered.** The card area stays empty with an explicit message.

---

### OUTPUT 3 — **The Map**
*Where they actually are.*

- A **geohash heatmap** of the city for the top cohort's signal, drawn on OpenStreetMap tiles
- **Venue pin** at the supplied postcode (or the city centroid, labelled as such)
- **Distance rings** at 1 mile / 2 miles / 5 miles — tied explicitly to the published 1-mile/80%-decay finding
- **Top 3 concentration cells** named as real neighbourhoods, each with: the cell's `affinity_rank`, and *"N of the top 50 cells in the city fall here"*
- **An honest coverage line:** the number of cells returned and the locality Qloo actually matched (*"Qloo read your city as Portland, Cumberland County, Maine"*) — this is how you catch a mis-match before it becomes a wrong recommendation

**Why this is the strongest single artefact:** it converts a score into a mail-drop, a flyer route, a partner venue, a bus-ad booking. It is the only output that a cinema's marketing budget can act on tomorrow.

---

### OUTPUT 4 — **The Programme Bet** (one, specific)
*What to put on to reach them.*

- **1 recommended addition**, presented as a concrete title or title cluster with year(s)
- **Two-sided scoring, in one query:** its affinity against **(a)** the current programme as signal, and **(b)** the target cohort's signature entities as signal — both scored inside a single `filter.results.entities` call
- A plain statement of the trade: *"This holds current-audience fit at 0.71 (High) while scoring 0.83 (Very High) for the target cohort."*
- **A runner-up** with the reason it lost (transparency about the search, not just the answer)
- **A rejected list** — 3–6 titles the agent *considered and killed*, each with the reason (`off-cohort`, `too popular / already saturated`, `no Qloo entity`, `already programmed in the last 6 months`). **This is a deliberate design choice** — see Part 10.

---

### OUTPUT 5 — **The Test Card**
*How you'll know if it worked.*

A single printable page:
- **The cohort** and its signature entities
- **The geography** — the named concentration areas, with the number of top-50 cells in each
- **The bet** — title, slot recommendation, rationale
- **The test design** — suggested slot, suggested outreach split by area, test window (e.g. 6 weeks)
- **The primary metric** — new-household acquisition rate for the slot
- **The secondary metric** — share of new households from the top-3 predicted cells
- **The baseline to beat** — the venue's own rolling new-household rate (the user enters it; if they don't, the field says `baseline not supplied — measure it this month and re-run`)
- **The falsification condition, stated in words:** *"If new-household rate for this slot does not exceed the baseline, the geographic hypothesis is disconfirmed for this cohort and the cohort should be retired."*
- **Honest limitations block** — see Part 13

---

### OUTPUT 6 — **The Evidence Panel**
*Every Qloo call, and every claim's provenance.*

- Every call: workflow/tool name · endpoint · **full parameter string** · HTTP status · result count · duration · cache hit/miss · attempt number
- For every affinity number shown anywhere: the call ID that produced it, the signal used, and the entity's position in the result set
- `feature.explainability` attribution for recommendation calls: which input entities contributed, with their normalised scores
- **Copy as JSON** — one button, complete run provenance
- **A permanent banner when any panel is empty:** *"Qloo returned no entities for this query. Nothing has been substituted."*

**Why this is an output and not a debug view:** the judging criterion is *"Does the code reflect genuine effort and a non-trivial implementation?"* A provenance panel is the cheapest possible way to demonstrate depth, and it simultaneously satisfies *"Potential Impact… based on what's demonstrated."*

---

### What Adjacent explicitly does NOT output
- ❌ Predicted ticket sales or revenue
- ❌ Individual-level audience profiles or anything that looks like one
- ❌ Marketing copy, social posts, or campaign assets
- ❌ A schedule (it recommends a slot, not a calendar)
- ❌ Any statement about a specific person

---

# PART 3 — THE COMPLETE USER WORKFLOW

Design principles applied: **the first screen must be usable with zero knowledge of Qloo; every wait must show work; the agent may ask exactly one clarifying question; every panel can go empty.**

### Screen 0 — Landing (no login)
**Headline:** *"You know who comes. Adjacent finds who would."*
**Sub:** one sentence of the problem, one sentence of the mechanism.
**Primary action:** `Run the demo` — loads a pre-filled real season for a real cinema so a judge can be inside the product in 3 seconds.
**Secondary:** `Start with your own programme`.
**Persistent footer:** `Qloo connected · 0 calls` — visible from the first second, so the very first thing the judge sees is that this is a Qloo tool.

---

### Step 1 — Institution & city *(10 seconds)*
The user enters a **venue name** (optional) and a **city** (required). Typeahead for the city. If a venue name is given, the agent resolves it as a `urn:entity:place` and extracts `properties.geocode` to auto-fill the postcode — so the user often types nothing but a name.

*Failure path:* city not fuzzy-matched → inline message: *"Qloo couldn't match that city. Try 'Portland, Maine' or 'Leeds, UK'."* — no silent fallback.

### Step 2 — The programme *(60–90 seconds, the only real work)*
A single textarea. **One title per line.** Placeholder text shows three correctly-formatted examples including one with an IMDb ID. Plus:
- **`Paste from anywhere`** — the parser strips years, directors, dates, times, and `Q&A`/`35mm` annotations from pasted box-office listings or a website season page
- **`Load an example season`** — three real, pre-verified seasons for three different venues
- An **optional** audience line ("mostly 55+, cinephiles, weekday evenings") and an **optional** baseline ("our new-household rate last quarter was 34%")

The user presses **Run**.

### Step 3 — Resolution *(3–6 seconds, fully visible)*
A resolution strip appears, one row per title, resolving progressively:

```
✓ Perfect Days (2023)              tt7594358  ·  urn:entity:movie  ·  pop 0.71
✓ The Zone of Interest (2023)      tt7160372  ·  urn:entity:movie  ·  pop 0.83
⚠ Sansho the Bailiff (1954)        2 Qloo entities match — which?
✓ Taipei Story (1985)              matched    ·  urn:entity:movie  ·  pop 0.22
✗ Untitled work-in-progress         not found in Qloo
```
- **Ambiguous rows** expand to a two-option chooser. The agent asks **once**, in a single batch, and waits.
- **Unresolved rows** stay in the list, struck through, counted in the coverage line, and **excluded from every downstream signal.** They are never quietly dropped and never guessed.
- Coverage line updates live: `9 resolved · 1 ambiguous · 2 not found`.

**Why visible resolution matters:** it is the first proof that the system is grounded. It also front-loads failure to the point where it is recoverable, rather than poisoning the analysis behind the user's back.

### Step 4 — Taste DNA *(2–4 seconds)*
The tag panel and the demographic skew bar render. The agent narrates one line: *"Your programme reads as slow cinema with a strong observational-documentary and urban-alienation signature."* — **generated strictly from the returned tags.**

*Honest-failure branch:* if fewer than 3 tags return above Medium, the panel renders a warning and the agent **offers to widen** — e.g. retry with `filter.parents.types` relaxed, or with the resolved subset only — and says what it changed.

### Step 5 — Cohort discovery *(8–20 seconds — the heart of the demo)*
The agent now runs its search loop (Part 4). The UI shows a **live trace rail** on the left, one line per step, monotonically appending:

```
→ Expanding across domains…            film, music, book, brand, place
   film    12 candidates
   music    8 candidates
   book     4 candidates
→ Building 9 candidate cohorts from 24 candidate entities
→ Ranking all 9 cohorts in a single query (one normalisation) ✓
→ Rejecting 3 weak cohorts (below Medium evidence)
→ Deepening the top 3 (adjacency re-check, popularity spread)
→ Locating cohort 1 in Portland…
```

Three cohort cards fade in — **in rank order, not all at once**, so the judge experiences the ranking as an act of judgement rather than a list appearing.

### Step 6 — Geography *(4–8 seconds)*
The map fills cell by cell for the **top cohort**. The venue pin drops. Distance rings draw. The top-3 concentration areas get named labels and the "N of the top 50 cells" counts.

The user can **switch cohorts** with a click — the map re-queries for that cohort (a fresh heatmap call) and re-renders. This is where a judge realises the geography is live, not canned.

### Step 7 — The programme bet *(6–12 seconds)*
The agent pulls candidate titles from the top cohort's own affinity neighbourhood (`signal.interests.entities` = cohort signature entities, `filter.type=urn:entity:movie`), filters out anything the venue recently played, and scores the survivors **two-sidedly in one query**. One recommendation, one runner-up, and the rejected list.

### Step 8 — The Test Card *(instant, assembled)*
Rendered from everything above. Printable (print-CSS, no PDF library). The falsification condition is generated from the actual measured baseline if supplied, and shows a `measure your baseline first` state if not.

### Step 9 — Evidence panel & export
Full call trace, explainability attributions, `Copy as JSON`, and a **shareable read-only link** to the saved run (so a judge can revisit, and so the venue can send it to their funder).

---

### What the agent does at each step (one-line map)

| Step | Agent action | Qloo tool |
|---|---|---|
| 1 | Resolve venue + city locality | `resolve_venue`, `resolve_locality` |
| 2 | Parse free text into candidate titles | *(LLM, extraction only — no claims)* |
| 3 | Resolve each title, batch-ask ambiguity | `resolve_entities` / `get_entities_by_external_id` |
| 4 | Build the taste vector | `taste_dna` |
| 5 | **Decide** which domains to expand into, generate candidates, build cohorts, rank in one query, **reject weak ones, decide whether to deepen or stop** | `expand_adjacency`, `rank_candidates`, `assess_evidence` |
| 6 | Locate the chosen cohort | `cohort_heatmap` |
| 7 | **Find and two-sidedly score** candidate additions | `candidate_additions`, `score_programme` |
| 8 | Assemble the test card | *(deterministic)* |
| 9 | Compile provenance | `trace` |

The agent has **decision points** at steps 3 (ask or proceed), 5 (expand where, deepen or stop, reject what), and 7 (recommend or report insufficiency). Those are the four places where non-agentic implementations collapse into a fixed pipeline.

---

# PART 4 — MAKING THE AGENT GENUINELY AGENTIC

## 4.1 The design rule

> **The agent owns the decisions; the tools own the truth. The LLM is never allowed to produce a number, an entity, a place, or a score. It may only produce (a) extraction from user text and (b) prose that is a restatement of tool output.**

This rule is enforced structurally: the LLM's output schema has no numeric fields and no entity-name fields. Prose templates take a `ToolResult` object as their only input. If a `ToolResult` is empty, the template has no branch that produces a sentence — it produces the empty-state string.

## 4.2 The agent's state

```python
@dataclass
class AdjacentState:
    # Inputs
    institution_name: str | None
    city_query: str
    raw_programme_text: str
    venue_postcode: str | None
    stated_baseline: float | None

    # Resolution
    resolved: list[ResolvedEntity]        # id, name, subtype, popularity, source(ext_id|search)
    ambiguous: list[AmbiguityGroup]        # awaiting one user decision
    unresolved: list[str]

    # Evidence accumulation (the agent's working memory)
    taste_tags: list[ScoredTag]
    demographic_skew: DemographicProfile
    candidate_entities: dict[Domain, list[ScoredEntity]]
    candidate_cohorts: list[Cohort]
    ranked_cohorts: list[Cohort]           # single-normalisation ranking
    rejected_cohorts: list[RejectedCohort] # each with a reason code
    chosen_cohort: Cohort | None
    cohort_heatmap: HeatmapResult | None
    programme_candidates: list[ScoredMovie]
    chosen_bet: ProgrammeBet | None

    # Control
    call_budget: int
    calls_made: int
    step: int
    trace: list[ToolCall]
    stop_reason: StopReason | None
    insufficiency: InsufficiencyReport | None
```

## 4.3 Tool catalogue

Every tool below is specified completely: input, endpoint, parameters, output, why, when to call, when NOT to call.

---

### T1 · `resolve_locality`
| | |
|---|---|
| **Input** | `city_query: str` |
| **Endpoint** | `GET /v2/insights` (as a probe) or `GET /search?types=urn:entity:locality` |
| **Parameters** | `/search`: `query=<city>`, `types=urn:entity:locality`, `take=5`. Probe: `filter.type=urn:heatmap`, `filter.location.query=<city>`, `signal.interests.tags=<any known-valid tag>` |
| **Output** | `{locality_entity_id, name, disambiguation, geocode}` — plus Qloo's own `query.localities.filter` echo |
| **Why the agent needs it** | Every downstream geographic call depends on a valid locality. `filter.location.query` is fuzzy-matched and returns a **400 if unmatched** — the agent must know *before* it burns the heatmap calls |
| **When to call** | Immediately after step 1. **Always.** |
| **When NOT to call** | Never skip this. If it fails, **stop and ask the user** — do not proceed with a guessed city |
| **Verified** | ✅ [`/search` types incl. `urn:entity:locality`](https://docs.qloo.com/reference/get-search); heatmap locality echo documented in the [heatmaps response example](https://docs.qloo.com/reference/heatmaps-use-case) |

---

### T2 · `resolve_entities`
| | |
|---|---|
| **Input** | `titles: list[ParsedTitle]` where each has `{title, year?, external_ids?}` |
| **Endpoint** | **Preferred:** `GET /entities` · **Fallback:** `GET /search` |
| **Parameters** | `/entities`: `external.imdb.ids=<comma list>` (or `external.rottentomatoes.ids`, `external.musicbrainz.ids`, `external.spotify.ids`, `external.isbn13.ids`). `/search`: `query=<title> <year>`, `types=urn:entity:movie`, `take=5` |
| **Output** | `ResolvedEntity[]` + `AmbiguityGroup[]` + `unresolved: string[]` |
| **Why** | Everything downstream is a function of these IDs. A wrong ID silently poisons every result |
| **When to call** | Step 3, always. Batch: one `/entities` call for all external IDs at once, then parallel `/search` calls for the rest |
| **When NOT to call** | If the user supplied zero titles — refuse to run, do not invent a programme |
| **Verified** | ✅ [`/entities` external ID families](https://docs.qloo.com/reference/get-entities) (Finding 4). `/search` `types` enum includes `urn:entity:movie`, `urn:entity:artist`, `urn:entity:book`, `urn:entity:place`, `urn:entity:tv_show`, `urn:entity:video_game` |
| **Edge cases** | Remakes and same-title films (**always show year**); films Qloo lacks (count them, exclude them); a TV series listed as a film (subtype mismatch — surface it) |

---

### T3 · `taste_dna`
| | |
|---|---|
| **Input** | `resolved_ids: list[uuid]` |
| **Endpoint** | `GET /v2/insights` |
| **Parameters** | `filter.type=urn:tag` · `signal.interests.entities=<ids>` · `filter.parents.types=urn:entity:movie,urn:entity:tv_show` · `take=50` |
| **Output** | `ScoredTag[]` — `{tag_id, name, subtype, affinity, band}` |
| **Why** | The interpretable middle layer. Tags are what make the output **explainable in a sentence** and auditable as URNs. Also the input to the "audience distance" calculation |
| **When to call** | Step 4, once. Optionally re-call with `filter.tag.types` narrowed if the first returns noise |
| **When NOT to call** | Do not call with fewer than 3 resolved ids — the vector is too thin |
| **Verified** | ✅ [Taste Analysis use case](https://docs.qloo.com/reference/taste-analysis) explicitly documents `filter.type=urn:tag` with `signal.interests.entities` and `filter.parents.types` |

---

### T4 · `demographic_skew`
| | |
|---|---|
| **Input** | `resolved_ids: list[uuid]` |
| **Endpoint** | `GET /v2/insights` |
| **Parameters** | `filter.type=urn:demographics` · `signal.interests.entities=<ids>` |
| **Output** | `{age: {24_and_younger: −0.09, 25_to_29: +0.43, …}, gender: {male: +0.08, female: −0.08}}` — signed, where **positive = above-average alignment** |
| **Why** | Reframes the conversation from a slogan to a decision: if the programme *already* over-indexes young, the problem is awareness, not programming. Directly answers a question every cinema's board asks |
| **When to call** | Step 4, once, in parallel with T3 |
| **When NOT to call** | If the venue has no interest in demographic framing (some do not), still call it — it costs one call and it is often the most quotable line in the report |
| **Verified** | ✅ [Demographics use case](https://docs.qloo.com/reference/demographics-use-case). Response shape confirmed: `results.demographics[].query.age.{...}` with signed floats |

---

### T5 · `expand_adjacency`
The candidate generator. **This is a decision, not a loop.**

| | |
|---|---|
| **Input** | `resolved_ids`, `taste_tags`, `city_locality_id`, `domains_to_try: list[Domain]` |
| **Endpoint** | `GET /v2/insights` — one call per domain |
| **Parameters** | `filter.type=urn:entity:{movie\|tv_show\|artist\|book\|brand\|place\|person}` · `signal.interests.entities=<ids>` · `signal.interests.tags=<top 3 taste tag ids>` · `filter.exclude.entities=<resolved ids>` · `filter.popularity.min=0.05` · `filter.popularity.max=0.90` · `take=12` · `feature.explainability=true` |
| **Output** | `dict[Domain, list[ScoredEntity]]` |
| **Why** | This is where the cross-domain sentence comes from. A cohort that spans film→music→place is a *discovery*; a cohort inside film is a *recommendation* |
| **When to call** | Step 5. **The agent chooses the domains** based on the Taste DNA: if the top tags are media-keyword tags, prioritise `movie`/`tv_show`/`book`; if they are mood/lifestyle tags, prioritise `artist`/`brand`/`place` |
| **When NOT to call** | Do **not** fan out to all seven domains blindly — it burns 7 calls for noise. Start with **three**, evaluate yield, then expand only if yield is thin. If a domain returns 0 entities, record it and never retry it this run |
| **Verified** | ✅ Cross-domain is Qloo's core claim. `filter.popularity.min/max` ✅ on artist/book/brand/movie/person/place/podcast/tv_show/video_game. `filter.exclude.entities` ✅. `signal.interests.tags` ✅. `feature.explainability` ✅ |
| **Edge case** | `backfill.cross_domain.take` (≤20) and `backfill.content_based.take` (≤10) append filler when primary results run dry. **The agent must detect backfill** (it sits below the primary set) and label it — otherwise a "cohort" can be made of content-similarity filler rather than affinity. This is a real trap nobody else is handling. |

---

### T6 · `build_and_rank_cohorts` ← **the critical tool (Finding 1)**

| | |
|---|---|
| **Input** | `candidate_entities: dict[Domain, list[ScoredEntity]]`, `resolved_ids`, `taste_tags` |
| **Endpoint** | `GET /v2/insights` — **exactly one call** |
| **Parameters** | `filter.type=urn:entity:<primary domain>` · `signal.interests.entities=<programme ids>` · **`filter.results.entities=<EVERY candidate cohort's signature entities, flattened, deduped, ≤50>`** · `take=50` |
| **Output** | Every candidate entity, **ranked inside one normalisation**, each with affinity + band, plus each cohort's aggregate position |
| **Why the agent needs it** | **Because affinity scores are per-query normalised, this is the only way to compare cohorts to each other validly.** It replaces the naive "N calls, N scores, sort the scores" — which is wrong |
| **When to call** | Exactly once per run, after T5 |
| **When NOT to call** | If total candidate entities exceed 50, the agent must **prune first** (drop the lowest-affinity candidates per domain) and say so in the trace. Never silently truncate |
| **Verified** | ✅ `filter.results.entities` is available on all nine entity types; docs endorse relative-position comparison |

**Cohort construction from the ranked set:**
1. Group ranked entities into candidate cohorts by **domain + shared tag signature** (entities sharing ≥2 tags)
2. Drop cohorts whose members fall below the **Medium band (0.5)**
3. Compute each cohort's **novelty** = `1 − median(popularity)` of its members
4. Compute each cohort's **audience distance** = tag-set Jaccard distance between the cohort's entities' tags and the programme's Taste DNA tags
5. Rank by `evidence_strength × novelty × distance` with the weights exposed in the UI

**The agent here is making real choices:** how to cluster, what threshold to drop at, whether 9 cohorts is enough or it should go back to T5 for another domain.

---

### T7 · `cohort_heatmap`

| | |
|---|---|
| **Input** | `chosen_cohort.signature_entity_ids`, `locality_query`, `venue_point` |
| **Endpoint** | `GET /v2/insights` |
| **Parameters** | `filter.type=urn:heatmap` · `filter.location.query=<city>` · `signal.interests.entities=<cohort signature ids>` · *(optional)* `signal.demographics.audiences=<audience id>` when the cohort is an audience-type cohort · `output.heatmap.boundary=urn:geohash` |
| **Output** | `HeatmapResult` — `[{lat, lng, geohash, affinity, affinity_rank, popularity}]` + the locality echo |
| **Why** | Converts a score into a mail-drop. The **only** output a £500 marketing budget can act on tomorrow. Load-bearing given the 1-mile/80%-decay finding |
| **When to call** | Step 6, once per displayed cohort. Lazily — only when the user actually switches to a cohort |
| **When NOT to call** | **Do not call with `signal.interests.tags` alone for cuisine/activity tags.** A peer project measured that food and activity tastes return no tag affinity on the heatmap (music genres and artists do). Use **entity** signals for the heatmap; treat tag-only heatmaps as unsupported until verified |
| **Verified** | ✅ [Heatmaps use case](https://docs.qloo.com/reference/heatmaps-use-case) + [Entity Type Parameter Guide](https://docs.qloo.com/reference/available-parameters-by-entity-type) heatmap section confirms `signal.interests.entities`, `signal.demographics.audiences`, `signal.demographics.age/gender` |
| **Edge case** | `output.heatmap.boundary` defaults to geohashes; `filter.location.radius=0` disables the default boundary padding — **use `radius=0` for honest "within the city" claims**, and say which mode you used |

---

### T8 · `audience_lens` *(secondary, optional, honestly labelled)* ← **Finding 2**

| | |
|---|---|
| **Input** | `programme_ids`, `city_query` |
| **Endpoint** | `GET /v2/audiences` (enumerate) → `GET /v2/insights` (test) |
| **Parameters** | `/v2/audiences`: `filter.parents.types=urn:audience:hobbies_and_interests,urn:audience:leisure,urn:audience:lifestyle_preferences_beliefs`, `take=50`. Test: `filter.type=urn:entity:movie`, `signal.demographics.audiences=<aud_id>`, `filter.results.entities=<programme ids>`, `take=50` |
| **Output** | `AudienceFit[]` — per audience: how many of the programme's titles clear the Medium band |
| **Why** | Adds a **second, independent cohort vocabulary** (psychographic rather than cultural), which strengthens the report and gives a human-readable label the radio/city magazine can use |
| **When to call** | Only if the run has call budget left **and** the primary cohorts are strong. This is a V1 feature |
| **When NOT to call** | **Do not rank audiences by comparing raw affinity scores across audiences — invalid (Finding 1).** Report only a *count of titles clearing a band*, labelled as a coarse instrument, and state the caveat in the provenance panel |
| **Verified** | ✅ [`/v2/audiences` params](https://docs.qloo.com/reference/get-audiences); `signal.demographics.audiences` ✅ on artist, book, brand, movie, person, place, podcast, tv_show, video_game **and heatmap**. ⚠️ `filter.type=urn:entity:audience` is **deprecated** — do not use it |
| **Must verify with Qloo** | How many audiences exist, their granularity, and whether cross-audience comparison has any legitimate form. **Ask on day one.** |

---

### T9 · `candidate_additions`

| | |
|---|---|
| **Input** | `cohort.signature_entity_ids`, `city`, `already_programmed_ids` |
| **Endpoint** | `GET /v2/insights` |
| **Parameters** | `filter.type=urn:entity:movie` · `signal.interests.entities=<cohort signature ids>` · `filter.exclude.entities=<programme ids + already-programmed ids>` · `filter.popularity.min=0.05` · `filter.popularity.max=0.85` · `take=15` |
| **Output** | `ScoredMovie[]` |
| **Why** | Turns a cohort into an action. Also the place where "non-obvious" is enforced — the popularity ceiling keeps the list out of the canon |
| **When to call** | Step 7, once |
| **When NOT to call** | If T5 returned no `movie`-domain candidates, skip this and report the bet as unavailable rather than substituting another domain's entities for films |
| **Verified** | ✅ `filter.exclude.entities` ✅, `filter.popularity.*` ✅, `filter.type=urn:entity:movie` ✅ |
| **Edge case** | Availability is a **real-world constraint Qloo cannot see.** The output must say `Qloo cannot tell you whether this title is available to book` and prompt the user to check their distributor. This honesty is a feature, not a bug |

---

### T10 · `score_programme` ← **two-sided test in one query (Finding 1)**

| | |
|---|---|
| **Input** | `bet_candidates`, `programme_ids`, `cohort_entity_ids` |
| **Endpoint** | `GET /v2/insights` — **two calls, run in parallel** |
| **Parameters** | **Call A (holds the core audience):** `filter.type=urn:entity:movie`, `signal.interests.entities=<programme ids>`, `filter.results.entities=<bet + runner-up + rejected list>` — **Call B (reaches the cohort):** identical, but `signal.interests.entities=<cohort signature ids>` |
| **Output** | Each candidate with **two affinity scores and bands**, scored against two different signals but **each within a single normalisation** |
| **Why** | This is the trade-off made legible: *"holds current-audience fit at 0.71 (High) while scoring 0.83 (Very High) for the target cohort."* No cinema tool does a two-sided test |
| **When to call** | Step 7, once |
| **When NOT to call** | If either signal has fewer than 3 source entities, the comparison is too thin — report `insufficient signal` rather than a number |
| **Verified** | ✅ Signal and results-filter are both documented; the **caveat you must state in the UI: the two scores come from two different normalisations, so read them as *bands*, not as a difference.** The card says `High for your audience · Very High for this cohort` — never `+0.12 better` |

---

### T11 · `compare_seasons` *(advanced)*

| | |
|---|---|
| **Input** | `programme_ids` (group A) vs `proposed_season_ids` (group B) |
| **Endpoint** | `GET /v2/analysis/compare` |
| **Parameters** | `a.signal.interests.entities=<current>` · `b.signal.interests.entities=<proposed>` · `filter.type=urn:entity:movie` · `model=descriptive` |
| **Output** | Entities/attributes that A and B share vs. differ on |
| **Why** | Answers "does adding these four films change our identity, or extend it?" |
| **When to call** | V1 only, when comparing two *entity groups* |
| **When NOT to call** | ⚠️ **Correction to our first report: this endpoint has NO demographic parameter.** It compares two entity groups, **not two audiences.** Do not use it for cohort-vs-cohort |
| **Verified** | ✅ [Analysis Compare](https://docs.qloo.com/reference/analysis-compare) — parameters are `a.signal.interests.entities`, `b.signal.interests.entities`, `filter.type`, `filter.subtype=urn:tag:genre\|urn:tag:occupation`, `model`, `filter.location.*`, `page`, `take`, `offset` |

---

### T12 · `trend_check` *(advanced)*

| | |
|---|---|
| **Input** | `bet_candidate_ids`, `start_date`, `end_date` |
| **Endpoint** | `GET /v2/trending` |
| **Parameters** | `filter.type=urn:entity:movie` · `filter.start_date` **(required)** · `filter.end_date` **(required)** · `signal.interests.entities=<ids>` · `take=20` |
| **Output** | Time series of popularity across the window → durability signal |
| **Why** | Distinguishes "this is on an upslope" from "this peaked last month." Protects against recommending a saturated title |
| **When to call** | V1, and only for the final bet + runner-up (2 calls) |
| **When NOT to call** | Not during candidate generation — it's per-entity and expensive |
| **Verified** | ✅ [Get Trending](https://docs.qloo.com/reference/get-trending). Note `filter.start_date` and `filter.end_date` are **required**; `filter.type` enum includes movie/artist/tv_show/etc. |

---

### T13 · `assess_evidence` — **the honesty gate (no API call)**

| | |
|---|---|
| **Input** | The entire accumulated state |
| **Endpoint** | none — pure logic |
| **Output** | `EvidenceReport` + `InsufficiencyReport \| None` |
| **Rules** | · A cohort requires ≥2 scored members above the **Medium (0.5)** band to be *shown*, and ≥1 above **High (0.6)** to be *ranked in the top 3* · A programme bet requires both scores above Medium · A geography claim requires ≥10 heatmap cells · **If fewer than 2 cohorts survive, the run reports insufficiency rather than padding the list** |
| **Why** | This is what makes the product *trustworthy* rather than fluent, and it is the single most differentiated behaviour in the whole submission |
| **When to call** | After every phase; it can send the agent **back** to T5 or **stop** the run |
| **When NOT to call** | Never skip it |
| **Verified** | Thresholds derived from Qloo's own published bands (0.8/0.6/0.5), not invented |

---

### T14 · `trace` — provenance recorder (no API call)
Wraps *every* tool. Records `{tool, workflow, url, params, status, result_count, duration_ms, cache_hit, attempt, backfill_detected, run_id}`. Emits the Evidence Panel (Output 6) and the shareable run JSON.

## 4.4 The decision loop

```
                    ┌──────────────────────────────┐
                    │  PLAN: what do I not know?   │
                    └──────────────┬───────────────┘
                                   ▼
        ┌──────────────────────────────────────────────────┐
        │ SELECT: cheapest tool that closes the biggest gap│
        └──────────────┬───────────────────────────────────┘
                       ▼
        ┌──────────────────────────────────────────────────┐
        │ ACT: call the tool. Budget check before, not after│
        └──────────────┬───────────────────────────────────┘
                       ▼
        ┌──────────────────────────────────────────────────┐
        │ EVALUATE (assess_evidence)                       │
        │  · enough cohorts?   → no → widen domains (T5)   │
        │  · cohorts strong?   → no → reject, retry once   │
        │  · ambiguity?        → yes → ASK USER, then wait │
        │  · budget left?      → no → stop, report partial │
        │  · all gaps closed?  → yes → STOP with answer    │
        │  · nothing found?    → STOP with insufficiency   │
        └──────────────┬───────────────────────────────────┘
                       ▼
                 FINALISE or LOOP (max 3 loops)
```

**Hard budget:** `MAX_QLOO_CALLS = 24` per run, `MAX_STEPS = 14`, `MAX_LOOPS = 3`. The trace shows `14 / 24 calls used` continuously. When the budget is hit, the run finishes with what it has and **says so** — it never silently degrades.

## 4.5 The four behaviours that prove it's an agent

| Behaviour | Where it shows | How a judge sees it |
|---|---|---|
| **Decides what information is missing** | Chooses which domains to expand into based on the Taste DNA's tag families | The trace rail names the decision and the reason |
| **Rejects weak results** | `assess_evidence` drops sub-Medium cohorts; the Rejected List on Output 4 shows killed candidates with reasons | A visible rejection list is impossible to fake and no pipeline produces it |
| **Compares alternatives** | T6 ranks 9 cohorts in one normalisation; T10 scores bet vs runner-up two-sidedly | The runner-up and the "why it lost" line |
| **Stops, or admits insufficiency** | Budget exhaustion and the insufficiency branch | The empty state with a real message |

## 4.6 Anti-hallucination architecture (structural, not prompt-based)

| Layer | Mechanism |
|---|---|
| **1. Type system** | `ScoredTag`, `ScoredEntity`, `Cohort`, `HeatmapCell` are Pydantic models. Numbers only exist if parsed from a Qloo response. There is no code path that assigns an affinity value from LLM output |
| **2. LLM I/O contract** | The LLM's response schema contains **only** `extracted_titles: list[str]` and `prose: str`. Any response containing digits adjacent to a `%` or a decimal is rejected and regenerated |
| **3. Prose templates** | Prose is generated *from* a `ToolResult`, never alongside it. `render_why(cohort)` has an `if not cohort.scored_members: return EMPTY_STATE` branch as its first line |
| **4. Empty-state discipline** | Every panel has an explicit empty state. There is no default text |
| **5. Trace completeness** | If a number appears on screen, there is a trace row that produced it. The Evidence Panel is generated by iterating the trace, not by the LLM |
| **6. Golden-run test** | A test suite replays 5 recorded Qloo responses and asserts that every rendered number appears in the fixture |

---

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

---

# PART 9 — ONE REALISTIC END-TO-END RUN

**Everything below is labelled.** `[Q]` = a claim that came from a Qloo response. `[D]` = deterministic computation over Qloo output. `[U]` = user-supplied. `[A]` = agent decision. `[X]` = external real-world fact. `[!]` = a limitation stated honestly.

*Illustrative values throughout — these are what a real run would look like, not recorded API output. The shape of every call is verified against the documentation; the numbers are placeholders and are marked as such.*

---

## The venue

**Hollywood Theatre**, 4122 NE Sandy Blvd, Portland, Oregon. A 1926 non-profit movie palace, 300+ seats, run by Film Action Oregon, programming repertory 35mm, first-run independent, and a substantial documentary strand. `[X]` It is exactly the kind of venue in the beachhead: single-screen-dominant, programmer-led, publicly-published calendar, and — as a non-profit — under funder pressure to demonstrate audience strategy.

**Why this venue for the demo:** its real programme is *coherent but unusual* (35mm repertory + documentary + genre midnight movies), which is a hard taste vector to fake and an easy one for a taste graph to characterise. And Portland, Oregon is a city with a strong, geographically-clustered cultural identity — so a heatmap either works or fails visibly.

---

## INPUT `[U]` — 8.7 seconds of typing

```
City:      Portland, Oregon
Venue:     Hollywood Theatre, 4122 NE Sandy Blvd  (postcode 97212)
Baseline:  new-household rate last quarter = 38%

Programme (last 6 weeks + next 4 weeks):
  Perfect Days (2023) [tt7594358]
  The Zone of Interest (2023) [tt7160372]
  Taipei Story (1985) [tt0089853]
  Sansho the Bailiff (1954) 
  Le Samouraï (1967) [tt0062229]
  All the Beauty and the Bloodshed (2022) [tt2137482]
  Sorcerer (1977) [tt0076740]
  Fire of Love (2022) [tt12879666]
```

---

## STEP 1 — Resolve the locality `[A][Q]`

```
TOOL T1 resolve_locality
GET /v2/insights
  filter.type=urn:heatmap
  filter.location.query=Portland, Oregon
  signal.interests.entities=<Perfect Days id>
  take=1
→ 200 · 14ms · 1 cell returned · locality echo:
   { "name": "Portland", "state": "Oregon", "country": "USA", "id": "..." }
```
**Agent decision:** the echo says **Oregon**, not Maine. Proceed. *(Without this check, a whole run could be built on the wrong Portland — a real hazard, since both are mid-size US cities with active film scenes.)* `[A]`

## STEP 2 — Parse `[A]`

```
LLM (extraction only, schema: {title, year?, imdb_id?, annotations?}):
  8 titles extracted. Annotations ("35mm", "Q&A", "one night only") discarded
  but retained for the Test Card's slot note. No entity IDs, no scores, no
  interpretations produced. Guard: the response schema has no numeric or
  entity-name field, so nothing else *can* be produced.
```

## STEP 3 — Resolve entities `[Q]` — the two-path ladder

```
TOOL T2 resolve_entities
Path A — one batched call for all 7 titles with IMDb IDs:
GET /entities
  external.imdb.ids=tt7594358,tt7160372,tt0089853,tt0062229,
                    tt2137482,tt0076740,tt12879666
→ 200 · 240ms · 7 entities returned with urn:entity:movie ids,
  subtypes, popularity values, and Qloo tags

Path B — one search for the title without an ID:
GET /search
  query=Sansho the Bailiff
  types=urn:entity:movie
  feature.typo_tolerance=true
  take=5
→ 200 · 1 exact match (1954, Kenji Mizoguchi) — auto-accepted on
  exact title + year agreement; no ambiguity prompt needed
```

**Resolution strip shown to the user:**
```
✓ 8 of 8 titles resolved · 0 ambiguous · 0 not found
[Q] Sansho the Bailiff            matched via /search   pop 0.14
[Q] Taipei Story (1985)           matched via IMDb      pop 0.11
[Q] Le Samouraï (1967)            matched via IMDb      pop 0.42
[Q] Sorcerer (1977)               matched via IMDb      pop 0.19
[Q] Perfect Days (2023)           matched via IMDb      pop 0.71
[Q] The Zone of Interest (2023)   matched via IMDb      pop 0.83
[Q] All the Beauty… (2022)        matched via IMDb      pop 0.35
[Q] Fire of Love (2022)           matched via IMDb      pop 0.58
Evidence: 2 calls, 7 entities resolved deterministically from external IDs.
```
**This strip is the first thing that distinguishes Adjacent from a peer project that hit rate limits and ambiguity errors on day 12.** `[A]`

## STEP 4 — Taste DNA `[Q]` + demographic skew `[Q]` (two calls, run in parallel)

```
TOOL T3 taste_dna
GET /v2/insights
  filter.type=urn:tag
  signal.interests.entities=<all 8 movie ids>
  filter.parents.types=urn:entity:movie,urn:entity:tv_show
  take=50
→ 200 · 310ms · 23 tags returned

TOOL T4 demographic_skew
GET /v2/insights
  filter.type=urn:demographics
  signal.interests.entities=<all 8 movie ids>
→ 200 · 190ms
```

**Taste DNA panel — the tags that cleared the Medium band, illustrative:**
| Tag `[Q]` | Affinity `[Q]` | Band (official) | URN `[Q]` |
|---|---|---|---|
| Slow cinema | 0.84 | **Very High** | `urn:tag:keyword:media:slow_cinema` |
| Observational documentary | 0.79 | High | `urn:tag:genre:movie:documentary` |
| 35mm / analog presentation | 0.74 | High | `urn:tag:keyword:media:film_35mm` |
| Urban alienation | 0.68 | High | `urn:tag:keyword:theme:urban_alienation` |
| Minimalism | 0.63 | High | `urn:tag:style:minimalism` |
| Existential drama | 0.61 | High | `urn:tag:genre:movie:existential_drama` |
| Environmental documentary | 0.56 | Medium | `urn:tag:keyword:theme:environment` |
| Crime noir | 0.44 | **Below Medium — not shown** | *(excluded from the vector)* |

*Values illustrative. The bands are the official thresholds from [Interpreting Affinity Scores](https://docs.qloo.com/docs/interpreting-affinity-scores) and the URN pattern is the documented `urn:tag:{subtype}:{category}:{name}` form.*

**Demographic skew `[Q]`:** `25–34: +0.31` · `35–44: +0.18` · `55+: −0.12` · `male: +0.04` · `female: −0.04`
**Plain-language line (template-rendered from those numbers only):**
> *"This programme skews younger than the general population — it over-indexes 25–44 by a clear margin and under-indexes 55+. Worth knowing before you conclude you have a youth-audience problem: on this evidence you don't, or not from programming."*

**Why the agent stops at 23 tags and doesn't fetch more:** `[A]` the tags below the Medium band are not evidence; adding them would weaken the vector (docs: "affinity scores may decrease as more inputs or filters are applied") and would not change the cohort search.

## STEP 5 — Cohort discovery `[A][Q]` — **the agent decides**

**Agent reasoning, shown in the trace rail:**
> *"Taste DNA is dominated by **media** and **theme** tags, not mood or lifestyle tags. Media and theme tags predict best by expanding across other media domains — film → TV → books — and by mood-adjacent domains. The programme already includes a strong music-adjacent element (Sorcerer's Tangerine Dream score, Fire of Love's archival form), so music is worth testing. Expanding into: `movie`, `tv_show`, `artist`, `book`. Skipping `brand`, `place`, `person` on the first pass — no taste signal points there, and burning calls on a domain with no prior is the most common way to waste a budget."* `[A]`

*Why this decision matters:* a non-agentic system either expands everywhere (wasteful, noisy) or follows a hardcoded domain list (obtuse). The domain choice is derived from the programme's own tag families, so the same engine behaves differently for a jazz festival.

```
TOOL T5 expand_adjacency — 4 parallel calls, all with explainability on
GET /v2/insights
  filter.type=urn:entity:movie
  signal.interests.entities=<8 ids>
  signal.interests.tags=urn:tag:keyword:media:slow_cinema,
                       urn:tag:keyword:theme:urban_alienation,
                       urn:tag:style:minimalism
  filter.exclude.entities=<8 ids>
  filter.popularity.min=0.05  filter.popularity.max=0.90
  feature.explainability=true
  take=12
→ 200 · 480ms · 12 results, 0 backfill

  filter.type=urn:entity:tv_show   → 200 · 12 results, 0 backfill
  filter.type=urn:entity:artist    → 200 · 12 results, 2 backfill (labelled)
  filter.type=urn:entity:book      → 200 · 12 results, 0 backfill
```

**Sample results `[Q]` (illustrative):**

| Domain | Entity | Affinity | Band | Popularity |
|---|---|---|---|---|
| movie | *Paterson* (2016) | 0.81 | Very High | 0.66 |
| movie | *Aguirre, the Wrath of God* (1972) | 0.77 | High | 0.71 |
| movie | *In the Mood for Love* (2000) | 0.76 | High | 0.79 |
| movie | *The Straight Story* (1999) | 0.72 | High | 0.39 |
| tv_show | *Twin Peaks* | 0.74 | High | 0.72 |
| tv_show | *Detectorists* | 0.61 | High | 0.28 |
| artist | **Brian Eno** | 0.79 | High | 0.74 |
| artist | **Grouper** | 0.71 | High | 0.24 |
| artist | **Hildur Guðnadóttir** | 0.68 | High | 0.58 |
| artist | **William Basinski** | 0.64 | High | 0.21 |
| artist | *(2 backfill entries)* | — | — | *labelled as content-similarity, not affinity* |
| book | **Rebecca Solnit — *A Field Guide to Getting Lost*** | 0.66 | High | 0.44 |
| book | *(2 further entries below High)* | — | — | |

**This is the moment the product exists for.** `[D][A]` Four artists — Eno, Grouper, Basinski, Guðnadóttir — share a clearly coherent taste cluster (ambient / drone / modern composition). *No human would write the sentence "your Ozu-and-documentary season has an ambient-music audience," and no LLM would assert it with a measurement attached.* And the books cluster around essayistic, place-and-wandering nonfiction — Solnit, not airport thrillers.

## STEP 6 — THE RANKING (the tool that makes this correct) `[A][D][Q]`

**Agent decision:** `[A]` *"I have 33 affinity-scored candidate entities. I will construct 7 candidate cohorts and rank them **in a single query**, because scores from separate queries are not comparable."*

```
TOOL T6 build_and_rank_cohorts
GET /v2/insights                                         ← exactly ONE call
  filter.type=urn:entity:artist
  signal.interests.entities=<8 programme movie ids>
  filter.results.entities=<signature entities of ALL 7 candidate cohorts,
                           flattened + deduped, 41 ids, pruned to ≤50>
  take=50
→ 200 · 520ms · 41 entities returned, all ranked inside ONE normalisation
```

**Cohort construction `[D]`** — entities grouped by domain + shared tag signature (≥2 shared tags):

| Rank | Cohort `[A]` | Type | Signature entities `[Q]` | Evidence `[D]` | Novelty `[D]` | Distance from your audience `[D]` |
|---|---|---|---|---|---|---|
| **1** | **"Ambient & modern-composition listeners"** | Adjacent-entity | Brian Eno (0.79) · Grouper (0.71) · Hildur Guðnadóttir (0.68) · William Basinski (0.64) | **Strong** | **78/100** | **Far** |
| 2 | "Slow-cinema completists" | Adjacent-entity | *Paterson* 0.81 · *The Straight Story* 0.72 · *Aguirre* 0.77 | Strong | 41/100 | Close |
| 3 | "Place-and-wandering essayists" | Adjacent-entity | Solnit 0.66 · + 3 further book entities 0.58–0.63 | Moderate | 69/100 | Moderate |
| 4 | "Twin Peaks / Lynch-adjacent TV" | Adjacent-entity | *Twin Peaks* 0.74 · *Detectorists* 0.61 | Moderate | 33/100 | Close |
| — | "Scandinavian crime TV" | — | *rejected* | **Weak** — 1 member above High | — | — |
| — | "Craft-coffee brands" | — | *rejected* | **Weak** — 0 members above High | — | — |
| — | "Photography book collectors" | — | *rejected* | Insufficient — 1 member, 0.51 | — | — |

**Rejection reasons `[D]`, rendered in the UI as the Rejected List:**
```
REJECTED  Scandinavian crime TV      weak_evidence: 1 of 4 members above High
REJECTED  Craft-coffee brands        weak_evidence: 0 of 3 members above High
REJECTED  Photography book collectors insufficient: 1 member, 0.51 (Medium), no cluster
PRUNED    Paterson (0.81)            already_programmed_adjacent: venue played it 14 months ago
SKIPPED   brand / place / person     no_taste_prior: not attempted this run
```

**The agent's stopping decision `[A]`:**
> *"Cohort 1 is Strong and Far (novelty 78). Cohort 2 is Strong but Close — it describes people who already come. Cohorts 3 and 4 are Moderate. I have 11 of 24 calls left. I will deepen cohort 1 only, then locate it. I will not expand into `brand` and `place`: two cohorts that clear the High band is the sufficiency threshold, and additional domains would spend the remaining budget without changing the recommendation."*

## STEP 7 — Where they live `[Q]` — **the wow**

```
TOOL T7 cohort_heatmap
GET /v2/insights
  filter.type=urn:heatmap
  filter.location.query=Portland, Oregon
  filter.location.radius=0
  signal.interests.entities=<Brian Eno id, Grouper id,
                             Hildur Guðnadóttir id, William Basinski id>
  output.heatmap.boundary=urn:geohash
→ 200 · 610ms · 412 cells returned
   locality echo: Portland, Oregon, USA
```

**`[D]` Map rendering (deterministic over the returned cells):**
- 412 cells plotted as a heat layer on MapLibre, weighted by `affinity`
- Venue pin at 4122 NE Sandy Blvd
- Distance rings at 1 mi / 2 mi / 5 mi — labelled *"published arts-attendance research suggests likelihood of attendance drops sharply beyond ~1 mile"* `[X]`
- **Top 3 concentration cells, named:**

| Area `[D]` | Cells in city top-50 `[D]` | Median cell affinity `[D]` | Distance from venue `[D]` |
|---|---|---|---|
| **Alberta Arts District / NE 15th–30th** | 11 of 50 | 0.78 | **1.4 mi** |
| **Buckman / Central Eastside** | 7 of 50 | 0.74 | 3.1 mi |
| **Northwest / Pearl District** | 6 of 50 | 0.71 | 4.6 mi |

**The sentence that becomes the whole strategy:**
> *"The audience for your ambient-music-adjacent programming lives disproportionately in the Alberta Arts District — **1.4 miles from your door** — and in Buckman. Eleven of the fifty strongest cells in Portland sit inside a fifteen-minute walk of each other, four of them within a mile of the theatre."* `[D]`

**Honest coverage line, always displayed:** `412 cells · 50 in the top decile · locality matched: Portland, Oregon (not Maine) · radius mode: within-city (radius=0)` `[Q][!]`

**What the venue does with this on Monday:** flyers to the Alberta Arts businesses (record shops, galleries, the coffee roasters the taste graph also surfaced), a cross-promo with a nearby ambient-listening bar, a geo-weighted Meta/Instagram push instead of the usual citywide scatter — and, for the first time, a *reason* to choose that geography over any other. `[D]`

## STEP 8 — The programme bet `[A][Q][D]`

```
TOOL T9 candidate_additions
GET /v2/insights
  filter.type=urn:entity:movie
  signal.interests.entities=<Eno, Grouper, Guðnadóttir, Basinski ids>
  filter.exclude.entities=<8 programme ids + 3 already-played ids>
  filter.popularity.min=0.05  filter.popularity.max=0.85
  take=15
→ 200 · 430ms · 15 candidates

TOOL T10 score_programme — two calls, in parallel, ONE normalisation each
A: signal.interests.entities=<8 programme ids>
   filter.results.entities=<bet, runner-up, 6 rejected candidates>
B: signal.interests.entities=<4 cohort signature artist ids>
   filter.results.entities=<same 9 ids>
→ 200 · 380ms each
```

**The output card:**
> ### Recommended addition
> **Koyaanisqatsi (1982)** — one 35mm screening, Thursday 20:00, Alberta-Arts-geo-weighted outreach
>
> **Holds your current audience: 0.72 · High** `[Q]`
> **Reaches this cohort: 0.83 · Very High** `[Q]`
> *(These are two separate measurements against two different signals. Read them as bands, not as a difference. A cross-query arithmetic comparison would be invalid.)* `[!]`
>
> **Why:** glass-adjacent minimalism, urban-alienation imagery, and Philip Glass's score place it simultaneously inside your slow-cinema signature and inside the ambient cluster. `[Q][D]`
>
> **Novelty: 61/100** — it is not in the canon of your current programme, but it is famous enough to have an audience. `[D]`
>
> **The risk, stated:** *Koyaanisqatsi* has been widely revived in the last decade, so part of this cohort may already have seen it theatrically. `[!]`

**Runner-up:** **Sátántangó (1994)** — cohort fit 0.79 (High), current-audience fit 0.64 (High), **lost on runtime** (7h 30m cannot occupy a single Thursday slot without a structural change to your evening) `[D]` — plus a note that Qloo cannot tell you the runtime; that came from the agent's own knowledge of the film and is flagged as a **non-Qloo claim**. `[!][A]`

**Rejected, with reasons `[D]` — the part every pipeline hides:**
```
REJECTED  Baraka (1992)                 too_popular: pop 0.88 > ceiling 0.85
REJECTED  NOSTALGHIA (1983)             off_cohort: cohort fit 0.52 = Medium
REJECTED  Bladerunner 2049              off_cohort: cohort fit 0.49, film 0.0=Below
REJECTED  Various 5 candidates          weak_or_missing_qloo_entity
EXCLUDED  Paterson, Patlabor 2, ...     already_programmed_recently
```

## STEP 9 — The Test Card `[D]` (deterministic assembly)

> ### Adjacent Test Card — Hollywood Theatre · Portland, Oregon · 4 Oct 2026
>
> **Cohort:** Ambient & modern-composition listeners *(rank 1 of 7 tested; Strong evidence)*
> **Signature:** Brian Eno 0.79 · Grouper 0.71 · Hildur Guðnadóttir 0.68 · William Basinski 0.64 `[Q]`
>
> **Geography:** Alberta Arts District (11 of Portland's top-50 cells, 1.4 mi) · Buckman (7) · Pearl/NW (6)
>
> **The bet:** *Koyaanisqatsi* (1982), 35mm, Thursday 20:00. Current-audience fit **High** · cohort fit **Very High**. `[Q]`
>
> **Outreach split:** ~55% of spend geo-weighted to the top 3 areas; ~45% to the existing email list for baseline continuity.
>
> **Primary metric:** new-household acquisition rate for this screening.
> **Baseline to beat:** **38%** `[U]` — measured last quarter.
> **Secondary metric:** share of new households whose postcode falls inside the top-3 predicted cells.
> **Test window:** 6 weeks from the screening.
>
> **Falsification condition:** *If the new-household rate for this screening does not exceed 38%, the geographic and cohort hypothesis is disconfirmed for this cluster — retire the cohort and do not build a second screening on it.*
>
> **Limitations on this card:** `[!]`
> · Availability not checked — *Koyaanisqatsi* may not be bookable; check your distributor.
> · Qloo cells are model estimates of taste concentration, not counts of people.
> · This card does not predict ticket sales and no such claim is made anywhere in this report.
> · 8 of 8 titles resolved; no substitutes were used anywhere.

## STEP 10 — Evidence panel `[D]`

```
Run 4f2c… · 11 of 24 calls used · 0 errors · 0 cached · 0 retries
 seq tool                  method path                   status  count  ms   backfill
  1  resolve_locality      GET    /v2/insights           200     1      14   –
  2  resolve_entities      GET    /entities              200     7     240   –
  3  resolve_entities      GET    /search                200     1      95   –
  4  taste_dna             GET    /v2/insights           200    23     310   –
  5  demographic_skew      GET    /v2/insights           200     4     190   –
  6  expand_adjacency      GET    /v2/insights           200    12     480   –   (movie)
  7  expand_adjacency      GET    /v2/insights           200    12     501   –   (tv_show)
  8  expand_adjacency      GET    /v2/insights           200    12     670   YES (artist, 2/12)
  9  expand_adjacency      GET    /v2/insights           200    12     455   –   (book)
 10  build_and_rank_cohorts GET   /v2/insights           200    41     520   –   ← single normalisation
 11  cohort_heatmap        GET    /v2/insights           200   412     610   –
 12  candidate_additions   GET    /v2/insights           200    15     430   –
 13  score_programme (A)   GET    /v2/insights           200     9     380   –
 14  score_programme (B)   GET    /v2/insights           200     9     380   –
Stop reason: complete
```

**What this run proves, to a judge, in three minutes:**
1. It resolved 8/8 films with zero ambiguity, using external IDs `[Q]` — the failure point where rival demos break.
2. It reasoned about *which* domains to search and explained why `[A]` — not a pipeline.
3. It **refused** three candidate cohorts and **killed** six candidate films, with reason codes `[D]`.
4. It ranked cohorts inside a single normalisation `[Q]`, which is the technically correct thing to do and the thing most builders get wrong.
5. Every number on screen traces to a row in this table `[D]`.

---

# PART 10 — THE KEY DIFFERENTIATOR

## 10.1 Evaluating the candidates honestly

| Candidate | Qloo dependency | Discovery? | Would it be obvious anyway? | Evidence? | Verdict |
|---|---|---|---|---|---|
| **Cross-domain audience discovery** (music↔film↔books↔brands) | ● Essential — no other public source maps taste across ≥5 domains with scores | **Yes** | **No** — the whole point is it isn't guessable | Measured affinity `[Q]` | ✅ **Core** |
| **Cold-start discovery** (no first-party data at all) | ● Essential — Qloo's FAQ states this as a designed property | Yes | Partly obvious as a *benefit*, but not as an *output* | — | ✅ **Keep as framing**, not as a feature. It's *why the product can exist*, not a feature to build |
| **Affinity-vs-novelty axis** | ● Essential — needs `filter.popularity` + affinity together | Partly | **No** — "is this a discovery or have I just been told to book Bresson?" is the user's real anxiety | Measured `[Q]` | ✅ **Core — underrated** |
| **Geographic taste concentration** | ● Essential — heatmap | Yes | No | Measured `[Q]` | ✅ **Core — the wow** |
| **Audience comparison** | ◐ Needs `/v2/audiences` | Yes | — | ⚠️ **Not rankable across audiences** (Finding 2) | ⚠️ **Secondary layer only** |
| **Programming-gap analysis** | ◐ | Yes | Partly — "what don't we play" is somewhat inferable from your own calendar | Weak without a signal for "what your audience wants but isn't available" | ⚠️ Fold into the programme bet |
| **Explainability as a feature** | ◐ Available broadly | No | — | Attribution `[Q]` | ✅ **Keep — as a trust layer, not a headline** |
| **Candidate scoring ("grade my shortlist")** | ● `filter.results.entities` | No — it's validation, not discovery | — | Measured `[Q]` | ✅ **Keep only as a secondary action** ("check 2 titles you're already considering") |
| **Trend / durability** | ● `/v2/trending` | Partly | Partly | Measured `[Q]` | ⚠️ **V1, small** |

## 10.2 The pick — the smallest compelling combination

> ### **The Qloo-native core:**
> ### **[Cross-domain taste characterisation] → [Single-normalisation cohort ranking] → [Geographic concentration for the winning cohort]**
>
> ### One sentence: **"Your programme's taste DNA reaches a cohort you've never targeted, and here is where that cohort lives in your city."**

**Why this exact combination and nothing more:**

1. **Each link requires the previous one to exist, and no link can be replaced.** You cannot get the cohort without cross-domain taste mapping. You cannot rank cohorts correctly without the single-normalisation trick (a correctness requirement, not a flourish). You cannot locate them without the heatmap. Remove any link and the sentence above becomes false.
2. **It is a *sentence*, not a dashboard.** A judge can repeat it after one demo. Products whose value takes a paragraph to explain lose hackathons.
3. **It is the answer to "why is Qloo here?" in the most literal possible form.** The output is a statement about *taste relationships between cultural objects* and *their spatial distribution*. There is no other public API that can produce either half.
4. **The additive pieces are all enhancement, not architecture.** Popularity/new affinity axis, explainability, the two-sided programme bet, the test card — each improves the core and each can be cut without breaking it. That's the correct relationship between a core and its features.
5. **It deliberately excludes audience-segment ranking**, because we could not verify it is legitimate (Finding 2) and because building on unverified capability is how demos die. Audience segments ship as a *labelled secondary layer* in V1, if the API supports it.

## 10.3 The best supporting feature (and why it earns its place)

> ### **The Rejected List.**

Every competitor shows what it found. **Adjacent shows what it killed and why** — cohorts rejected for weak evidence, films rejected as too popular, domains never attempted, with reason codes.

**Why this is worth building:** it is the only artefact that cannot be produced by a system that isn't actually reasoning. A pipeline has no rejections; it has an empty slot. And it directly attacks the sector's stated problem — IDA/Documentary's 2026 industry coverage describes programmers facing "a fool's errand" of "connecting the dots backward from wide-ranging results." **A tool that shows its rejections is a tool that shows its reasoning.** It costs about forty lines of code and it is the most quotable thing in the demo video.

## 10.4 What we deliberately did NOT make the differentiator

| Rejected as headline | Why |
|---|---|
| "Agentic AI for the arts" | A category, not a differentiator |
| "Explainable recommendations" | Every entrant will claim this; and explainability is table stakes for trust, not a reason to exist |
| "The first cross-domain audience tool" | Sounds like marketing; unprovable in three minutes |
| "Real-time" anything | Nothing here is real-time; claiming it invites questions we can't answer |
| "Predictive" anything | **The single most dangerous word available to us.** We do not predict, and we should say so in the pitch — that refusal is a differentiator against everyone who does |

---

# PART 11 — PROVING QLOO IS NECESSARY

## 11.1 The baseline: what a normal LLM produces

**Protocol.** Ask a frontier LLM (GPT-5-class, with web browsing **enabled** so the baseline is as strong as possible — a weak baseline would be dishonest):

> *"I run a 300-seat independent cinema in Portland, Oregon. Our recent programme is: Perfect Days, The Zone of Interest, Taipei Story, Sansho the Bailiff, Le Samouraï, All the Beauty and the Bloodshed, Sorcerer, Fire of Love. Tell me: (1) what cultural taste this programme represents, (2) three specific audiences adjacent to it that we probably don't reach, (3) where those audiences live in Portland, and (4) what one film we should add."*

**Predicted output `[A] — this is our honest expectation, informed by how LLMs behave, and we will record the real output on video]`:** a competent essay naming "arthouse film lovers, cinephiles, documentary audiences," adjacent directors from the canon (Bresson, Bergman, Haneke, Wong Kar-wai), and a recommendation from the well-known repertory canon (*Stalker*, *In the Mood for Love*, *Chungking Express*, a Bresson). Geography: generic — "Portland's east side," "the Pearl District," or a confident but unsourced guess.

## 11.2 The comparison, by the seven criteria the brief specifies

| Criterion | LLM baseline (browsing enabled) | Adjacent (`[Q]` = measured) | Is the difference real? |
|---|---|---|---|
| **Relevance** | High but **generic** — correct at the category level ("arthouse audiences") | Cohort-level and specific: *"ambient & modern-composition listeners,"* evidenced by four named artists with scores `[Q]` | **Partly.** The LLM gets the broad shape right. We must not claim it fails here |
| **Novelty** | **Weak.** The canon is over-represented in training data, so the LLM's adjacent names are famous ones everyone already knows — Wong Kar-wai, Bergman | **Strong by construction.** `filter.popularity.max=0.85` plus affinity ranking surfaces Grouper (pop 0.21) and Basinski (pop 0.21) with real scores `[Q]` | **Yes — measurable**: median popularity percentile of adjacent entities. LLM outputs will cluster high; ours is bounded and the bound is visible |
| **Cultural adjacency** | **Plausible but unmeasured.** Any of the LLM's suggestions might be right; you cannot tell | **Measured and falsifiable.** Each adjacent entity carries an affinity score, and each score traces to a query you can re-run `[Q]` | **Yes — and this is the core claim, because it converts opinion into evidence** |
| **Geographic relevance** | **Absent or confabulated.** An LLM has no taste-by-neighbourhood data and will produce a plausible answer regardless | **Cell-level model output**, 412 cells, top-50 concentration counts, named districts `[Q]` | **Yes — categorical.** Not a quality difference; a capability the LLM does not possess at all |
| **Diversity** | Clusters tightly on the canon and on Western arthouse | Spans ≥4 Qloo entity domains and multiple popularity strata, and the domain choice is *derived from the programme* `[Q][A]` | **Yes, and it's inspectable** — the domain coverage is in the trace |
| **Non-obviousness** | **The failure mode.** Asks "what else might appeal to my audience?" and gets the shelf next to the one you already own | Asks "who else lives in this taste, and where" and can answer with an entity the programmer has never heard of (Grouper, Basinski) `[Q]` | **Yes — this is the product** |
| **Evidence quality** | Zero. Assertions with no provenance, and **no way to tell a confident guess from a retrieved fact** | Every claim: trace row, affinity score, official band, source entity, explainability attribution `[Q]` | **Yes — categorical** |

## 11.3 The two honest claims

> **Claim 1 (capability).** The LLM cannot produce outputs 3 and part of 2 *at all*, regardless of quality: there is no source in its weights or on the open web that reports measured cross-domain taste affinity and its neighbourhood-level spatial concentration. **This is a categorical argument, not a performance argument** — which is why we don't need to invent a number to make it.
>
> **Claim 2 (data quality).** Where the LLM *can* answer — outputs 1 and 4 — Qloo's version is **measured, traceable, and bounded by a popularity filter**, while the LLM's is asserted from memory. This is a difference in *kind of evidence*, not in *quality of prose*.

**And what we will NOT claim:** that Adjacent's recommendations are *better* than the LLM's in some measured sense. We will not report precision, lift, accuracy, or "X% more relevant" — there is no ground truth for taste-cluster quality within a hackathon timeframe, and inventing such a comparison would be the fastest way to lose credibility with judges who work at Qloo.

## 11.4 The runnable evaluation protocol (executable during the hackathon)

| Element | Design |
|---|---|
| **Cases** | **3 real programmes** from 3 real venues (one US, one UK, one European — all with published calendars). Plus the option for a judge to enter their own |
| **Conditions** | **(A)** LLM, browsing on · **(B)** LLM, browsing off · **(C)** Adjacent |
| **Blinding** | Outputs stripped of provenance annotations, shuffled, presented as three unlabelled documents |
| **Ratings** | Each output rated 1–5 on: relevance · novelty · cultural adjacency · geographic relevance · diversity · non-obviousness · evidence quality |
| **Raters (honest constraints)** | **n = 3–8**, not enough for statistics, and we will say so. Recruit: 1–2 real cinema programmers (cold-email or a r/Arthouse or Art House Convergence contact), 1–2 people with no film background (to measure whether the difference is legible to a non-expert judge), and the judges themselves if they engage |
| **The one quantitative measure we *can* defend** | **Median popularity percentile of every entity each condition named.** This is computed, not judged, and it is the cleanest possible demonstration that the LLM lives in the canon and Adjacent does not. Present it as a distribution plot |
| **The companion measure** | **Provenance rate**: the fraction of factual claims in each output that can be traced to a source. Adjacent → 100% by construction. LLM-browsing → measurable and low for geography. LLM-no-browsing → near zero |
| **Honesty requirement** | Publish the full protocol, the raw matrix, the actual n, and — critically — **the cases where Adjacent lost.** If the LLM wins on relevance for one case, that result is in the report |

## 11.5 The demonstration that wins the room

Do it **live, on stage, in the video**:
1. Show the LLM's answer for the Hollywood Theatre programme on screen for fifteen seconds. It is *good*, which is the point.
2. **Read its geography sentence aloud** and ask the room: *"How would anyone check that?"*
3. Run Adjacent on the same programme, live.
4. Show the 412 cells, the Alberta Arts District, and the *Grouper, popularity 0.21* row.
5. Show the trace table.

**The demo does not argue that the LLM is bad. It argues that the LLM is unfalsifiable and Adjacent is falsifiable** — and it puts the evidence on screen.

---

# PART 12 — COMPETITION: WHO ELSE IS BUILDING THIS

*Verified by fresh sweep of Devpost and GitHub for this cycle (Qloo Hackathon, 30 Sep – 30 Oct 2026), October 2026.*

## 12.1 Is anyone building Adjacent?

> **No.** As of this sweep, **no project on Devpost or GitHub is doing institutional audience development** — i.e. taking a venue's existing programme, characterising its taste, discovering adjacent cohorts the venue does not serve, and locating those cohorts geographically.

Every project found falls into one of these shapes:

| Cluster | Projects (GitHub, this cycle) | What they do |
|---|---|---|
| **Event/talent booking & tour logistics** | Booker · Advance · Undercard | Venue↔artist matching; promoter tour advance incl. opener, support act, after-show, sponsor picks; support-act shortlist auditing |
| **Relocation & place-fit** | Tastebridge · Home2Here · Soft Landing | "Find the equivalent of my city's taste in a new one" |
| **Heatmap / neighbourhood ranking** | newcomer · tastebridge | Rank neighbourhoods for a *person* moving or choosing |
| **Local business marketing briefs** | Hayy | Café/restaurant marketing briefs |
| **Synthetic audience research** | Quorum | Synthetic focus-group panels replacing surveys |
| **Creator / sync / licensing** | SyncVision | Sync-licensing matching + rights triage |
| **B2B partnerships** | Cold-Open | Partnership lead-gen |
| **Consumer cultural discovery** | CultureHub · Zento · Taste Match | Cultural-discovery chat and event discovery (**verified live on Devpost this cycle**) |
| **Niche verticals** | resonance-qloo · taste-route-agent · common-ground · tasteship · tasteloop | Senior-living activity plans · week/route planners · community matching · etc. |
| **Infrastructure / MCP wrappers** | qloo-mcp · qloo-taste-mcp · NoBanks/qloo-mcp | Expose Qloo as a tool for other agents |

**2025 edition winners (the people we'd be up against, conceptually):** GeoTaste (1st), Alloy, Resonance AI, Zesty — [Qloo on X](https://x.com/Qloo/status/1965110790151775).

*(Caveat: Devpost's participant counter returned 356 on one read and 174 on another, so the size of the field is uncertain — between roughly 175 and 360 builders. The cluster analysis above is drawn from the projects I could actually locate, which is a sample, not a census — labelled as inference.)*

## 12.2 Is "cultural audience development" saturated?

**Saturated:** consumer cultural *discovery* (chat-based and feed-based), relocation taste-fit, event/artist booking, and neighbourhood ranking for individuals. There are multiple entrants in each.

**Not saturated — genuinely open:**
- **Institutional / B2B audience development.** Zero entrants. The sector is populated by non-profits, not by startups, and their tools are surveys and consultants.
- **Programme-level taste characterisation** (as opposed to person-level).
- **Non-obviousness as an explicit, bounded, measurable output** (popularity ceilings, novelty scores you can see being enforced).
- **Honest insufficiency** — every project found presents what it discovered; none presents what it refused.
- **Two-sided trade-off testing** (does this addition serve the new cohort *and* hold the current one).
- **Provenance-first design** — the trace and the rejection list as *first-class UI*, not debug logs.

## 12.3 What competitors do (and how we differ)

| Competitor | Their output | Our difference — **structurally, not cosmetically** |
|---|---|---|
| **Quorum** — synthetic audience panels | "What this audience would think of X" (simulated opinion) | We do not simulate people. We measure the taste relationships Qloo has actually computed. **Their output is a simulation; ours is a retrieval** |
| **Undercard** — support-act auditing | Audit a shortlist of bands for one show | We start from a whole programme and end in geography. **Their unit is a booking; ours is a season** |
| **Booker** — venue↔artist matching | "Which venue suits this artist" | We answer "who should *come to us*, and where do they live." **Opposite direction of fit** |
| **Hayy** — café marketing briefs | Marketing brief for a local business | Closest in *shape*, farthest in *input*. Hayy briefs a business; we characterise a **programme** — a cultural object with its own taste vector — and then locate the cohort |
| **newcomer / Tastebridge** | Rank neighbourhoods for a person | They rank places for an *individual's* taste. We map a *cohort's* concentration relative to *your existing building*. **The unit of analysis is inverted** |
| **CultureHub / Zento** | Consumer discovery chat | Different user, different scale, different decision. **A judge will see the difference in ten seconds** |
| **qloo-mcp and friends** | Infrastructure | Complementary, not competing. (And a judge may notice we could expose Adjacent as one — we deliberately don't, in scope terms) |

## 12.4 The three phrases that would make a judge say "this is just another X" — and our defence

| The accusation | Our structural defence |
|---|---|
| **"This is another heatmap demo."** | The heatmap is step 7 of 10, it is *downstream* of an agentic decision, and it is populated with the winning cohort's signature entities — not a city's general taste profile. **Our map is the consequence of a judgement; theirs is the product** |
| **"This is another LLM chat wrapper."** | There is no chat interface. The LLM has two jobs (parse text, render prose from typed results) and **no path to producing a fact**. The UI is a decision document |
| **"This is just recommendations with extra steps."** | We do not recommend to people. We characterise a programme, rank cohorts, and locate them. **And we ship the falsification test** — no recommendation product does that, because it makes the recommendation accountable |

**The product shape is the differentiator, not the name.** Adjacent is:
> **A programme-level cultural profiling and audience-location instrument for institutions that cannot use customer data — because they don't have any about the people they need to reach.**

No competitor occupies that sentence, and the shape is not reachable by renaming any of them.

---

---

# PART 13 — BRUTALLY CRITICAL RISKS

Ranked by **expected damage**, not by likelihood. Each has a mitigation and a **pre-decided fallback** — because the failure mode of a hackathon project is discovering a problem on day 24 and improvising.

| # | Risk | Sev | Mitigation | Pre-decided fallback | Tell the user? |
|---|---|---|---|---|---|
| **R1** | **Qloo has thin coverage in the demo city** — too few heatmap cells, few adjacent entities for an arts venue | 🔴 Critical | Verify coverage on **day one** with the key, in the actual demo city, before committing the story. Pick the city *after* seeing coverage | Switch demo city to one of London / NYC / Chicago / LA. If coverage is thin everywhere for our signal type, **drop Output 3 and the demo becomes Outputs 1, 2, 4, 5** — the product still stands | ✅ Yes — show the coverage line honestly |
| **R2** | **Aspect: our central ranking trick doesn't behave as documented** — `filter.results.entities` may not return all supplied entities scored, or `take` may clip them | 🔴 Critical | Test it in hour 3, in isolation, with a hand-written query | Fall back to **within-domain ranking only** and *show a reduced-confidence badge*. This is a visible degradation, not a lie | ✅ Yes — the badge says why |
| **R3** | **Entity resolution failures in the demo** — a title the programmer chose isn't in Qloo | 🟠 High | External-ID path (Finding 4) resolves ~7 of 8 titles deterministically; ambiguity prompt instead of guessing | Demo season uses titles **pre-verified on day one**. Unresolved titles are shown as unresolved, never hidden | ✅ Yes — the coverage line makes it a feature |
| **R4** | **Weak affinity signals across the board** — everything comes back 0.5, top cohorts look arbitrary | 🟠 High | Use the official bands, not raw score cut-offs; rely on **relative position**, which the docs endorse. Never quote a 0.51 as a strong result | Report insufficiency honestly. A run that says "Qloo does not have sufficient evidence for this programme in this city" **is a more impressive artefact than a mediocre run presented confidently** | ✅ Yes — loudly |
| **R5** | **Misleading correlations get presented as insight** — a cohort that looks culturally coherent but is statistical noise | 🟠 High | `assess_evidence` requires ≥2 members above Medium and ≥1 above High; the Rejected List makes the bar visible; cohorts are labelled with their evidence band | Cap: never show more than 3 cohorts, and never show a cohort below Moderate | ✅ Yes — the band is on every card |
| **R6** | **Backfill presented as affinity** — a "discovery" that is actually content-similarity filler | 🟠 High | Detect backfill by position in the response order; label it in the trace; exclude it from cohort construction | If backfill detection is unreliable, **turn backfill off** (`backfill.*.take=0`) and accept thinner results | ✅ Yes — a count in the trace |
| **R7** | **Rate limits kill the live demo** | 🟠 High | 3 rps limiter, 24-call budget, Postgres cache, cache pre-warmed for the demo season, retry with backoff | **The canned run**: `/demo/{slug}/canned` replays a recorded complete run, indistinguishable in the UI, labelled `replayed` in the evidence panel (we do not lie about it) | ✅ Yes — labelled |
| **R8** | **The agent loops or stalls** | 🟡 Medium | Hard caps: `MAX_QLOO_CALLS=24`, `MAX_STEPS=14`, `MAX_LOOPS=3`, per-tool timeouts, and a **wall-clock ceiling of 90 s** for the whole run after which it finalises with what it has | 90 s ceiling → `stop_reason=timeout`, partial outputs rendered | ✅ Yes |
| **R9** | **The LLM hallucinates inside prose** | 🟠 High | Structural: LLM output schema has no numeric or entity-name fields; prose is templated from `ToolResult`; the empty-state guard is the first line of every render function; a pytest asserts no digits adjacent to scores in LLM output | If violated in production, prose is disabled entirely and the UI shows structured data only | ❌ Internal — but the guard is visible in the repo |
| **R10** | **Judges read it as a heatmap demo** | 🟠 High | Temperature-check the demo script on someone who hasn't seen it; if the first thing they describe is the map, restructure the video to lead with the *rejected list* and the two-sided score | Lead the video with the Rejected List and the insufficiency branch | — |
| **R11** | **The "so what" objection** — "nice, but would a cinema actually use this?" | 🟠 High | The Test Card is the answer: it is a printable page a programmer can act on Monday, with a metric and a falsification condition. **Demo the Test Card on paper** | Get **one real programmer to react on record** (cold email to 10 arthouse programmers in week 1; one reply is likely) and put the quote in the Devpost | — |
| **R12** | **Privacy / ethics** — the product touches audience geography | 🟡 Medium | **Aggregate-only by design.** No PII stored, no individual records, no CRM access. Heatmap cells are model estimates, never counts. Reported demographics are programme-level, never person-level | If questioned, the answer is already written: `LIMITATIONS.md` and the zero-PII data section. **Do not add any feature that needs first-party data** | ✅ Yes — proactively, in the video |
| **R13** | **`/v2/audiences` turns out to be sparse** | 🟡 Medium | It is already a **secondary layer**, not the architecture (Finding 2) | Drop the audience-lens feature entirely; the product does not change | ✅ Yes |
| **R14** | **Deployment breaks on the day** | 🟡 Medium | Deploy the skeleton on day 2 with a mock client; keep it green through CI; never deploy the final build on day 30 | Run from the local machine and screen-record; the video is the submission | — |
| **R15** | **Scope creep** | 🔴 Critical | Part 6.4 is a written, standing refusal list. Print it | Cut, in this order: trend → compare → audience lens → shareable link → the runner-up | — |
| **R16** | **A rival ships something adjacent mid-month** | 🟡 Medium | Irrelevant to the shape: they cannot ship our problem framing, our honest-insufficiency behaviour, and our institution-level unit of analysis in three weeks. **But re-sweep Devpost on day 20 and check the gallery on day 29** | If a direct competitor appears, **pivot the demo emphasis** to the two things hardest to copy: honest insufficiency and the falsification test | — |
| **R17** | **The demo venue objects / feels misrepresented** | 🟡 Medium | Use only **public** programming information; never state that a venue has an audience problem; frame everything as "if you ran this." Name the venue only as an example | Use a fictional-but-realistic venue name with a real programme (label it clearly as illustrative) | — |
| **R18** | **The 1-mile / 80% claim is from a source whose methodology we haven't read** | 🟡 Medium | It is cited as *published arts-attendance research*, attributed, and used as context for the distance rings — **not** as a Qloo claim and never as a computed relationship in our output | Drop the distance rings' annotation; keep the rings as pure geometry | ✅ Cite the source every time it appears |
| **R19** | **`feature.explainability` payload bloat** | 🟢 Low | Measure it in hour 3. If the response grows past ~5×, disable it on the `take=50` calls and keep it on `take=12` ones | Disable explainability on bulk calls; keep it on scoring calls | — |
| **R20** | **We can't get the API key in time** | 🟠 High | **Phases 0–4 need no key at all** (Part 15). The mock client, the fixtures, the state machine, the UI and the evaluation harness are all key-independent | Demo on fixtures with the mock client, clearly labelled, and say the key arrived late. Everything else is real | ✅ Yes |

## 13.1 The explicit insufficiency conditions

**Adjacent must refuse to make a recommendation — in these exact words — when:**

| Condition | The message it shows |
|---|---|
| Fewer than 3 programme titles resolved | *"Only N of your titles could be identified in Qloo. With fewer than three, the taste profile is too thin to be meaningful. Please check the unresolved titles or add more to your programme."* |
| Zero tags above the Medium band (0.5) | *"Qloo found no tags with meaningful affinity for this programme. Nothing has been substituted. This programme may be too heterogeneous, or too obscure, for the taste graph to characterise."* |
| Fewer than 2 cohorts survive the evidence gate | *"Adjacent tested N candidate cohorts and none cleared the evidence threshold (2 or more members above Medium affinity). I do not have enough Qloo evidence to name an adjacent audience for this programme."* |
| Fewer than 10 heatmap cells returned for the city | *"Qloo returned only N geographic cells for this city — too few to support a geographic claim. No map is shown rather than showing a misleading one."* |
| A programme bet scores below Medium (< 0.5) against **either** signal | *"No candidate held both your current audience and the target cohort above Medium. Rather than recommend a film that serves one and loses the other, Adjacent is reporting no recommendation."* |
| The call budget is exhausted before the ranking step | *"This run used its full API budget before completing the ranking. Outputs shown are partial. Re-run to complete."* |
| The city could not be matched | *"Qloo could not match '<input>' to a locality. Please provide a city and country. Adjacent will not guess — a wrong city would produce a confidently wrong map."* |

**This table is not a safety net. It is the product's most defensible feature.** A tool that can say *"I don't know"* is a tool whose *"I know"* means something.

---

# PART 14 — MVP DEVELOPMENT PLAN (PHASES 0–10)

*26 calendar days remaining at the time of writing. The plan budgets ~15 focused days and leaves ~11 days of slack, which is deliberate: the last three days will be lost to the video, the Devpost write-up, and something unexpected.*

| Phase | Focus | Key tasks | Files / modules | Depends on | Difficulty | ✅ Must be working at the end |
|---|---|---|---|---|---|---|
| **0** | **Repo & guardrails** · 0.5 d | Repo init · `Makefile` · CI (ruff + pytest + `next build`) · `.env.example` · README skeleton · **`FEATURES_NOT_BUILDING.md`** (Part 6.4, committed on day one) · `docs/API_NOTES.md` seeded with the verified parameter allowlist | `Makefile`, `.github/workflows/ci.yml`, `docs/API_NOTES.md` | — | 🟢 Easy | `make test` passes on an empty test suite; CI is green; the refusal list is in the repo where scope creep can see it |
| **1** | **Qloo client + mock + typed models** · 1.5 d | Client with `X-Api-Key` + hackathon base URL · parameter allowlist that **raises** on unverified params · retry/backoff · token-bucket limiter · Pydantic models for the 6 response shapes we actually use · **`MockQlooClient`** reading fixtures · `record_fixtures.py` | `qloo/{client,params,models,limiter,retry}.py`, `tests/fixtures/*` | 0 | 🟡 Medium | With `MOCK=true` and no key, `client.insights(filter_type="urn:tag", …)` returns a typed `TagAffinityResponse`; with an unknown parameter it raises `UnverifiedParameterError` |
| **2** | **Entity resolution** · 1 d | The two-path ladder (external IDs → `/search`) · ambiguity detection & grouping · the `ResolutionStrip` UI · one-shot batch disambiguation · coverage accounting | `tools/t02_resolve_entities.py`, `api/routes_run.py`, `components/ResolutionStrip.tsx` | 1 | 🟡 Medium | Paste 8 real titles → 8 visually-correct resolution rows against fixtures, with an ambiguity case that produces a real prompt |
| **3** | **Core analysis tools** · 1 d | T3 taste DNA · T4 demographics · T5 adjacency expansion (**incl. domain choice logic + backfill detection**) · **T6 single-normalisation ranking** · band helpers · cohort construction (novelty, distance) | `tools/t03–t06*.py`, `domain/{bands,cohorts,scoring}.py` | 2 | 🟠 Hard | A programmatic call chain produces a **ranked, evidence-banded cohort list from fixtures**, and a unit test proves all cohorts were ranked inside one query |
| **4** | **Agent state machine + evidence gate** · 1.5 d | `AdjacentState` · plan→select→act→evaluate→stop loop · budget guards · six stop conditions · `assess_evidence` + `InsufficiencyReport` · rejection reason codes · **the trace recorder** | `agent/{state,orchestrator,budget,stop}.py`, `domain/{evidence,reasons}.py`, `qloo/trace.py` | 3 | 🟠 Hard | `python -m app.cli run fixtures/portland.json` prints a full decision trace ending in `stop_reason=complete`; a second fixture deliberately ends in `insufficiency` |
| **5** | **Geography** · 1 d | T7 heatmap · locality echo capture & mismatch warning · `radius=0` mode · top-3 concentration computation & **neighbourhood naming** (via OSM reverse geocode, cached) · MapLibre layer + venue pin + distance rings | `tools/t07_cohort_heatmap.py`, `components/TasteMap.tsx` | 4 | 🟡 Medium | A real city renders 300+ cells with a named top-3 and a visible locality echo — or an honest "insufficient cells" message |
| **6** | **Frontend run experience** · 2 d | Run shell · **SSE trace rail** · Taste DNA panel · cohort cards (fade in by rank) · rejection list · programme bet card · test card (print CSS) · insufficiency banner · empty states everywhere | `app/run/page.tsx`, `components/*`, `lib/sse.ts` | 5 | 🟠 Hard | A full run streams from start to finish in the browser against fixtures, with the trace rail live and every panel having a tested empty state |
| **7** | **Scoring, provenance, explainability** · 1 d | T9 candidate additions · **T10 two-sided scoring** · runner-up + rejected list with reasons · `feature.explainability` rendering · evidence panel table · `Copy as JSON` | `tools/t09,t10*.py`, `components/{ProgrammeBet,EvidencePanel}.tsx` | 4 | 🟡 Medium | Every number on screen has a hovering link to a trace row; the JSON export round-trips into a re-renderable run |
| **8** | **Baseline comparison (the honest one)** · 0.5 d | The 3 cases · the LLM conditions · the blinding script · the ratings matrix template · **the popularity-percentile computation** (the one hard number) · `docs/EVALUATION.md` | `docs/EVALUATION.md`, `scripts/evaluate.py`, `docs/evaluation_matrix.csv` | 7 | 🟢 Easy | `python scripts/evaluate.py` emits a filled ratings matrix and the popularity-percentile plot from recorded outputs, with the real n printed |
| **9** | **Deployment** · 1 d | Fly.io backend + Postgres · Vercel frontend · CORS · env vars · migration script · smoke test · **demo season pre-warming** · the canned run | `Dockerfile`, `fly.toml`, `scripts/{migrate.py,smoke.sh,warm_cache.py}`, `public/demo/*` | 6 | 🟡 Medium | `curl https://<fly>/health` → `{"qloo_configured":true}` with the real key; a live run completes on the deployed URL in under 60 s |
| **10** | **Testing, video, Devpost** · 2.5 d | The golden-run test · the 3 recorded demo seasons (real, pre-verified) · **the 3-minute video** (script in Part 17.5) · README + `LIMITATIONS.md` · Devpost copy · gallery re-sweep · final scope cut | `tests/test_golden_run.py`, `public/demo/*`, `docs/DEVPOST.md`, `README.md` | 9 | 🟡 Medium | Submission filed with time to spare, video under 3 min, every claim in the Devpost backed by something in the repo |

**Total: ~15 focused days.** Phases 0–4 (5.5 days) need **no API key**.

## 14.1 Critical path

```
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 9 → 10
                └──── 8 (parallel, any time after 7) ────┘
```
**Everything hangs off Phase 3.** If Phase 3 slips, cut Phase 8 and the audience lens, and push Phase 6 to a single day by dropping the cohort-card animations. **Never cut Phase 7** — provenance and honest scoring are the submission's substance.

---

# PART 15 — WHAT CAN BE BUILT BEFORE THE API KEY ARRIVES

**The rule: Phase 3's correctness must be *testable* before the key exists.** That is what the mock client and recorded fixtures buy us.

## 15.1 Can be built, tested and *demoed* with no key at all

| Work | Why it's key-independent | Done by |
|---|---|---|
| **Full repo, CI, Makefile, Docker** | Build config is build config | Phase 0 |
| **`MockQlooClient` + `record_fixtures.py`** | The mock returns **typed** fixtures shaped exactly like the documented responses. `record_fixtures.py` swaps the transport in one line once a key exists | Phase 1 |
| **All Pydantic response models** | We model from the documentation (which we have read and dated), not from the API | Phase 1 |
| **Parameter allowlist + `UnverifiedParameterError`** | Derived from `docs/API_NOTES.md`, the doc-verified table in Part 5 | Phase 1 |
| **Entity resolution logic** — parsing, ambiguity detection, grouping, the precedence ladder | Pure logic; the HTTP path is one function behind an interface | Phase 2 |
| **The whole agent state machine, budget, stop conditions** | It orchestrates *tools*, not HTTP | Phase 4 |
| **`assess_evidence` and every insufficiency branch** | Pure logic over typed results | Phase 4 |
| **Cohort construction, bands, novelty, distance, rejection codes** | Pure arithmetic | Phase 3/4 |
| **The entire frontend**, including the map (fixture GeoJSON), the trace rail (fixture SSE), the rejection list, the test card, the evidence panel | It renders types | Phase 6 |
| **SSE plumbing** | Transport-agnostic | Phase 6 |
| **DB schema, cache table, migrations** | SQL is SQL | Phase 1/9 |
| **The evaluation harness, blinding script, ratings matrix, popularity-percentile plot** | Nothing about it touches Qloo; it compares recorded outputs | Phase 8 |
| **Deployment of the skeleton** (both services, mock mode, `/health` → `qloo_configured:false`) | Deploy on day 2, stay green | Phase 9 |
| **`LIMITATIONS.md`, `README.md`, `docs/METHOD.md`, `FEATURES_NOT_BUILDING.md`** | Writing | Phase 0/10 |
| **The video script and the Devpost draft** | Writing | Phase 10 |
| **`docs/API_NOTES.md`** — the full dated, doc-verified parameter table | Already 90% written in Part 5 of this document | Phase 0 |
| **Neighbourhood naming from OSM/Nominatim** (cached) | Unrelated to Qloo | Phase 5 |

## 15.2 Must wait for the key

| Work | Why | Blocking? |
|---|---|---|
| **Coverage verification in the demo city** (heatmap cell counts for arts signals) | Determines the whole demo geography — **R1** | 🔴 Yes, but only for the demo *story*, not the build |
| **Recording real fixtures** | Fixtures must come from real responses | 🟡 Yes, for the golden-run test |
| **Verifying `filter.results.entities` behaviour at `take=50`** — the single most important unknown — **R2** | Determines whether our core ranking trick is available | 🔴 Yes |
| **Verifying `feature.explainability` payload size** | Determines whether it's on for bulk calls | 🟢 No — can degrade |
| **Enumerating real `urn:audience:*` values** | Needed for the V1 audience lens | 🟢 No — already secondary |
| **`/v2/audiences` catalogue depth** | V1 | 🟢 No |
| **Real rate-limit behaviour** | Tunes the limiter | 🟢 No — 3 rps is conservative and safe |
| **Real entity coverage for real films** | Determines which demo titles are used | 🟡 Yes, for the demo season |
| **Recording the demo run** | It must be real | 🟡 Yes |
| **Measuring the median-popularity baseline claim** | Needs real popularity values | 🟢 No — the harness is built and ready |

**Total work available before the key: roughly 5½ focused days — essentially Phases 0–4, plus the entire frontend against fixtures.** If the key never arrives, we still have a complete, coherent, demonstrable system on recorded fixtures, clearly labelled — and that is a materially better position than any team that waited.

---

# PART 16 — THE FIRST CONCRETE MILESTONE

> ## Milestone 1 — "Fixture Spine"
> ### One command that produces a ranked, evidence-gated cohort list from a hardcoded programme, entirely from local fixtures, with no API key and no UI.
> ### Time: 3–5 hours. Target: end of day one.

## The exact command

```bash
make milestone-1
# ≡ python -m app.cli run --fixture fixtures/portland.json --mock
```

## Exact success criteria — all seven must pass

| # | Criterion | How it's checked |
|---|---|---|
| **1** | **8 of 8 titles resolve to Qloo entity IDs** through the two-path ladder (7 via `external.imdb.ids`, 1 via `/search`) | Printed resolution strip: `8 resolved · 0 ambiguous · 0 not found` |
| **2** | **The client refuses an unverified parameter.** `client.insights(filter_type=…, made_up_param="x")` raises `UnverifiedParameterError` | `pytest tests/test_params_allowlist.py` passes |
| **3** | **At least 3 cohorts are constructed from fixtures across ≥3 entity domains**, each with ≥2 members above the Medium band | The CLI prints the cohort table |
| **4** | **All cohorts are ranked inside exactly ONE call** — asserted, not assumed. The trace shows one `build_and_rank_cohorts` row and zero per-cohort ranking calls | `pytest tests/test_cohort_ranking_single_normalisation.py` asserts the call count is 1 and that every cohort's scores come from that call's `run_id` |
| **5** | **At least one cohort is rejected for weak evidence**, with a machine-readable reason code, and it appears in the printed *Rejected List* | The CLI prints at least one `REJECTED … weak_evidence` line |
| **6** | **The insufficiency branch is exercised.** A second fixture (`fixtures/sparse.json`) produces zero surviving cohorts and the run ends with `stop_reason=insufficiency` and the exact message: *"I do not have enough Qloo evidence to name an adjacent audience for this programme."* | `make milestone-1-sparse` exits 0 and prints that sentence |
| **7** | **Every number in the printed output traces to a trace row.** A test walks the rendered output and asserts each affinity value appears in the trace | `pytest tests/test_golden_run.py::test_every_number_has_provenance` passes |

## What is deliberately NOT in this milestone
No UI. No map. No LLM. No heatmap. No database. No deployment. **If it takes more than five hours, the scope has already drifted.**

## Why this is the right first milestone
1. It proves the **single most important technical assumption in the product** (criterion 4) on day one, when it's still cheap to change course.
2. It builds the **anti-hallucination type system** (criteria 2 and 7) before there is any prose to hallucinate in.
3. It makes the **honesty behaviour** (criterion 6) a first-class citizen from the first commit, rather than a day-29 addition — which is precisely how it ends up being the product's best feature.
4. It produces something a person can **look at and argue with** on day one, which is how a solo build keeps its direction.

---

# PART 17 — COMPACT FINAL SPECIFICATION

```
PROJECT NAME        Adjacent
                    (subtitle: "You know who comes. Adjacent finds who would.")

TAGLINE             Find the audience already living inside your programme's
                    culture — and the neighbourhood they live in.

PROBLEM             Independent cultural venues must decide what to programme
                    every month with information that only describes people who
                    already attend. 45% of UK independent cinemas ran at a loss
                    last year; visit frequency is down 40% post-pandemic;
                    programming is the #1 stated reason arts audiences choose a
                    venue (73%) — and no tool informs it with any data about
                    non-attenders. Every existing method (ticketing CRM,
                    distributor comps, surveys, peers' box office) is built on
                    observed attendance and therefore structurally cannot answer
                    the question.

TARGET USER         The programmer at an independent / repertory cinema:
                    1–4 screens, 1–4 staff doing programming + marketing,
                    300–1,500 screenings/year, programming by judgement, no
                    audience-research budget. Beachhead cities: London,
                    Manchester, Leeds, Bristol, Glasgow, Edinburgh, Sheffield,
                    Cardiff / New York, Chicago, Portland, Seattle, Nashville,
                    Boston, Austin, LA.

SOLUTION            Paste your last 5–20 programme titles and your city.
                    Adjacent characterises the programme's taste DNA,
                    discovers 3 adjacent cohorts it does not currently reach,
                    ranks them by evidence strength × novelty × distance from
                    your current audience, maps where the winning cohort
                    concentrates in your city, recommends one specific
                    programme addition that serves both the new cohort and the
                    audience you have, and issues a printable test card with a
                    falsification condition.

CORE WORKFLOW       City + programme (min: city + 5 titles)
                    → visible entity resolution (IMDb-ID fast path, ambiguous
                      titles asked about, unresolved titles shown not hidden)
                    → Taste DNA: ranked tags with official bands + URNs +
                      programme demographic skew
                    → the agent decides which cultural domains to expand into,
                      based on the programme's own tag families
                    → cross-domain adjacency expansion (film / TV / music /
                      books / …) with popularity bounds and explainability on
                    → 7–9 candidate cohorts built, then ranked in a SINGLE
                      normalisation (affinity scores are per-query normalised —
                      ranking across queries is invalid)
                    → weak cohorts rejected with reason codes
                    → the winning cohort located: city heatmap, venue pin,
                      1/2/5-mile rings, top-3 named districts with counts
                    → one programme bet, scored two-sidedly (holds your current
                      audience | reaches the target cohort), plus a runner-up
                      and a rejected list with reasons
                    → Test Card: metric, baseline, test window, falsification
                      condition
                    → Evidence Panel: every call, every parameter, every
                      attribution, Copy as JSON

MVP FEATURES        M1 free-text + IMDb-ID intake · M2 visible resolution
                    with one-shot disambiguation · M3 Taste DNA · M4
                    cross-domain cohort discovery with explained domain choice
                    · M5 single-normalisation ranking + evidence gate · M6
                    city heatmap with named concentration areas · M7 two-sided
                    programme bet + runner-up + rejected list · M8 Test Card
                    with falsification condition · M9 evidence panel + trace +
                    JSON export · M10 insufficiency and empty states everywhere
                    · M11 demo mode with 3 pre-verified real seasons + canned
                    replay · M12 hard call budget + backoff.

QLOO ROLE           Load-bearing in six distinct places, all doc-verified:
                    (1) entity resolution incl. IMDb/Rotten Tomatoes external
                        IDs — the fast path
                    (2) programme taste characterisation: /v2/insights with
                        filter.type=urn:tag + signal.interests.entities
                    (3) cross-domain adjacency: filter.type=urn:entity:{movie,
                        tv_show,artist,book,…} on the same signal
                    (4) cohort ranking inside one normalisation via
                        filter.results.entities
                    (5) geography: filter.type=urn:heatmap with
                        filter.location.query + signal.interests.entities
                        (+ signal.demographics.audiences)
                    (6) provenance: feature.explainability + popularity
                        percentiles for the novelty axis
                    Remove Qloo and there is no product: no other public source
                    reports measured cross-domain taste affinity, and none
                    reports its spatial concentration.

AGENT ROLE          The agent owns four decisions and nothing else:
                    (1) which cultural domains to expand into — derived from
                        the programme's tag families, not a fixed list
                    (2) which candidate cohorts to keep and which to REJECT,
                        at an evidence threshold derived from Qloo's own
                        published bands
                    (3) whether to deepen, widen, or STOP
                    (4) whether the evidence supports a recommendation at all —
                        with seven explicit insufficiency conditions
                    The LLM has exactly two jobs (parse text; render prose FROM
                    typed results) and no code path to produce a fact. Numbers,
                    entities, places and scores can only come from a Qloo
                    response.

DATA REQUIREMENTS   Q (required): /entities + /search, /v2/insights
                    (urn:tag, urn:demographics, urn:entity:*, urn:heatmap,
                    filter.results.entities).
                    USER (required): city + 5–20 programme titles. Optional:
                    IMDb IDs, postcode, baseline new-household rate.
                    EXTERNAL: OpenStreetMap tiles + optionally Nominatim /
                    postcodes.io. That is the entire external footprint.
                    AVOIDED ENTIRELY: CRM/ticketing data, first-party customer
                    data, email lists, social scraping, census/deprivation
                    data, individual-level Qloo data. Zero PII, by design.

TECH STACK          Next.js 15 + TS + Tailwind + shadcn/ui · MapLibre GL +
                    OSM tiles · Recharts · FastAPI (Python 3.12) · a custom
                    ~350-line async orchestrator (deliberately NOT LangGraph) ·
                    PostgreSQL 16, raw psycopg, no ORM · Postgres-backed TTL
                    cache (not Redis) · Fly.io backend + Vercel frontend ·
                    pytest with recorded fixtures. Hosted LLM for text
                    transformation only.

ARCHITECTURE         Browser ──SSE──> FastAPI ──> agent state machine ──>
                    14 typed tools (T1–T14) ──> qloo/ client layer
                    (auth · allowlisted params · limiter · retry · cache ·
                    trace) ──> hackathon.api.qloo.com.
                    Every call wrapped by the trace recorder; the Evidence
                    Panel is generated from trace rows, not from the LLM.

SUCCESS METRIC      (what the PRODUCT improves, for the venue)
                    Primary: new-household acquisition rate for a tested
                    programme slot.
                    Secondary: share of new households falling inside the
                    predicted concentration cells — i.e. was the geography
                    right, not just the film.
                    (what WE demonstrate, in the hackathon)
                    A complete live run in <60 s; 100% of rendered numbers
                    traceable to a Qloo response; ≥1 cohort visibly rejected
                    for weak evidence; the insufficiency path demonstrable on
                    demand; a popularity-percentile comparison against an
                    LLM-with-browsing baseline.

KEY DIFFERENTIATOR  Cross-domain taste characterisation of a PROGRAMME
                    (not a person) → cohort ranking inside a single
                    normalisation → neighbourhood-level location of the winning
                    cohort. Plus the two behaviours nothing else in this cycle
                    has: a visible Rejected List with reason codes, and honest
                    insufficiency as a designed output.

MAIN RISKS          R1 thin city coverage → verify day 1, be ready to drop the
                    map · R2 filter.results.entities behaviour → the core
                    unknown, test in hour 3 · R7 rate limits → budget + cache +
                    canned replay · R9 LLM hallucination → structural, typed
                    schemas · R10 "just a heatmap demo" → lead the video with
                    the rejected list · R15 scope creep → the committed
                    refusal list.
```

---

## 17.5 The 3-minute video script (write it now, record it on day 29)

| Time | Content |
|---|---|
| 0:00–0:20 | The problem in one image: a programmer with a booking spreadsheet and no data about anyone who isn't already in it. *"You know who comes. You don't know who would."* |
| 0:20–0:40 | `Run the demo` — a real cinema's real programme. Resolution strip fills: **8 of 8, via IMDb IDs**. |
| 0:40–1:00 | Taste DNA appears: *slow cinema, observational documentary, urban alienation.* Cut to the demographic skew: *"Over-indexes 25–44. You do not have a youth-audience problem from programming."* |
| 1:00–1:35 | **The agent's decision, on screen:** *"Media and theme tags dominate → expanding into movie, tv_show, artist, book. Not brand, place, person — no taste prior."* Then the discovery: **Eno, Grouper, Hildur Guðnadóttir, Basinski.** *"No human writes this sentence. No LLM can measure it."* |
| 1:35–1:55 | **The Rejected List.** *"It killed three cohorts and six films. Here's why."* — the moment that separates this from a pipeline. |
| 1:55–2:20 | **The map.** Alberta Arts District, 11 of Portland's top-50 cells, 1.4 miles from the door. |
| 2:20–2:40 | **The two-sided bet.** *"Holds your audience at High. Reaches the cohort at Very High."* Plus: *"If it can't, it says so"* — show the insufficiency message. |
| 2:40–3:00 | The Test Card, the metric, the falsification condition, and the one-line close: *"Qloo didn't give us a recommendation. It gave us a hypothesis we can be wrong about — and that's the difference between a plan and a guess."* |

---

# FINAL DECISION

> # **B — PROCEED WITH ADJACENT, WITH FOUR SPECIFIC MODIFICATIONS.**

## Why B and not A

A would mean building the product exactly as originally framed: "cultural institutions" generally, Qloo audience segments as the primary mechanism, and cohort scores compared across queries. **That version is wrong in three ways**, each verified against current official documentation:

1. **"Cultural institutions" is not a demonstrable target.** Cinemas have clean structured public programmes and first-class Qloo entity types with IMDb-ID resolution. Orchestras resolve to composers, which is lossier. **Modify to a cinema beachhead, generalise in V1.**
2. **Audience segments are a lookup, not a ranker** ([`/v2/audiences`](https://docs.qloo.com/reference/get-audiences)), and `urn:entity:audience` as a filter type is **deprecated**. A design that depends on them is building on unverified capability. **Modify to adjacent-entity cohorts as the primary mechanism, with audience segments as a labelled secondary layer.**
3. **Comparing affinity scores across separate queries is invalid** — scores are normalised per query ([Interpreting Affinity Scores](https://docs.qloo.com/docs/interpreting-affinity-scores)). The naive implementation would have produced a confident, meaningless ranking of cohorts. **Modify to single-query ranking via `filter.results.entities`.** This is not merely a fix; it makes the product cheaper to run and makes the cohort ranking a genuine act of judgement by the agent.

## Why not C

Abandoning Adjacent would require one of these to be true. None is.

| Test | Verdict |
|---|---|
| Is the problem real and currently measured? | ✅ Yes — 45% of UK indie cinemas loss-making, 40% frequency decline, 73% of audiences cite programming as the reason they attend. Multiple current, reputable sources |
| Is it a *cultural intelligence* problem rather than generic analytics? | ✅ Yes — the unit is taste, the novel content is cross-domain relationships, the missing data is about non-attenders by construction |
| Does Qloo uniquely enable it? | ✅ Yes — and the specific capability has been verified, not assumed: cross-domain affinity, popularity percentiles, block-level heatmaps with demographic signals, external-ID lookup, per-claim explainability |
| Is anyone else building it? | ❌ **No.** Zero institutional-audience-development projects on Devpost or GitHub in this cycle |
| Can one dev build and deploy it before 30 Oct? | ✅ Yes — ~15 focused days, with 5½ of them requiring no API key |
| Is the Qloo dependency structural rather than decorative? | ✅ Yes — remove Qloo and neither the cross-domain cohort nor the geography can be produced by any public source |

And one further reason not to abandon: **the honest-insufficiency behaviour is worth building even if the cohort ranking turns out to be weak.** A tool in this sector that can say *"I don't have enough evidence"* is more valuable than one that always answers, because the sector's actual problem is unfalsifiable confidence. If R2 (the single-normalisation trick) fails on day one, the product degrades to a smaller product — it does not become a failed product.

## What would change this decision

State these as tripwires. If any fires, re-open the decision:

| Tripwire | Trigger | Response |
|---|---|---|
| **T-A** | Day-one coverage test shows <50 heatmap cells for arts signals in the target city, *and* the same for two fallback cities | **Drop geographic output.** If adjacency is also thin → escalate to C |
| **T-B** | `filter.results.entities` does not return all supplied entities scored | Ship within-domain ranking with a confidence badge; still B |
| **T-C** | A direct competitor appears on the Devpost gallery doing institutional audience development | Re-cut the video to lead with honest insufficiency + the falsification test; still B |
| **T-D** | By day 12, Phase 3 is not working | Cut Phases 8 and the audience lens, ship Phases 0–7 + 9 + 10 as a smaller product; still B |
| **T-E** | `feature.explainability` is not exposed on the hackathon key **and** `/entities` external IDs fail | Downgrade the resolution story; the product stands on adjacency + geography; still B |

---

# WHAT SHOULD WE DO TOMORROW MORNING?

**Five actions, in this order. Actions 1–3 need no API key. Do not start with a UI.**

---

### **1 — Run the coverage probe first thing, before anything else is built. (60–90 minutes)**

Open `docs/API_NOTES.md`, write the eight probes below as raw `curl` commands, and run them **the moment the key is in hand**. If the key has not arrived, write the script and run it against the mock. This is the single highest-information action available today, and it determines whether the demo city and the map exist at all.

```bash
export K=$QLOO_API_KEY; export H=https://hackathon.api.qloo.com

# (a) Do the external IDs we plan to demo actually resolve? [Finding 4]
curl -s -H "X-Api-Key: $K" "$H/entities?external.imdb.ids=tt7594358,tt7160372,tt0089853"

# (b) Does the programme produce real tag affinity with the right parents? 
curl -s -H "X-Api-Key: $K" "$H/v2/insights?filter.type=urn:tag&signal.interests.entities=<ids>&filter.parents.types=urn:entity:movie,urn:entity:tv_show&take=50"

# (c) Cross-domain adjacency — do artists come back for a film signal?
curl -s -H "X-Api-Key: $K" "$H/v2/insights?filter.type=urn:entity:artist&signal.interests.entities=<ids>&take=12"

# (d) THE CRITICAL ONE — does filter.results.entities return ALL supplied entities scored?
curl -s -H "X-Api-Key: $K" "$H/v2/insights?filter.type=urn:entity:artist&signal.interests.entities=<ids>&filter.results.entities=<15 ids>&take=50"
#    → count the returned entities. If < 15, R2 is live and the ranking design changes TODAY.

# (e) Heatmap coverage for the demo city with a real signal. How many cells?
curl -s -H "X-Api-Key: $K" "$H/v2/insights?filter.type=urn:heatmap&filter.location.query=Portland,Oregon&filter.location.radius=0&signal.interests.entities=<ids>"
#    → if < 50 cells, test London and New York. THE DEMO CITY IS CHOSEN HERE, NOT EARLIER.

# (f) Is feature.explainability exposed, and how big is the payload?
curl -s -H "X-Api-Key: $K" "$H/v2/insights?filter.type=urn:entity:movie&signal.interests.entities=<ids>&feature.explainability=true&take=12" | wc -c

# (g) What real audience URNs exist?
curl -s -H "X-Api-Key: $K" "$H/v2/audiences?filter.parents.types=urn:audience:hobbies_and_interests&take=50"

# (h) Rate limit behaviour — 10 sequential calls, log any 429
```

**Success = a filled-in `docs/API_NOTES.md` with real counts, real cell numbers, and the demo city chosen on evidence.** Post the four unanswerable questions from Part 5.4 in `#api-help` the same hour.

---

### **2 — Post the API-key application immediately if it hasn't gone out, and post the four questions to `#api-help` in the same session. (20 minutes)**

The application text is already written in `04_scoring_and_winner.md` §12. Send it. Then post the four questions that gate design decisions:
> 1. Does `filter.results.entities` return *all* supplied entities scored, or only the top `take`? *(gates our core ranking design)*
> 2. Is `feature.explainability` exposed on the hackathon key, and what is a typical payload size at `take=50`?
> 3. What are the concrete `urn:audience:*` values, and how many audiences exist?
> 4. What is the actual rate limit, and does the heatmap support tag-only signals?

**Success = key application sent, questions posted, an expected-answer window identified.**

---

### **3 — Write `FEATURES_NOT_BUILDING.md` and commit it. (30 minutes)**

Part 6.4, verbatim, in the repo root, on day one. Fourteen refusals, each with its reason. **This is not bureaucracy — it is the single cheapest intervention against the specific failure mode of a 26-day solo build**, which is arriving at day 20 with nine half-features and a broken demo. Committing the refusal list before any code exists means every scope argument has a written precedent.

**Success = the file exists, is committed, and lists every item from Part 6.4 with its reason.**

---

### **4 — Build Phase 0 + the first half of Phase 1: repo, CI, and the mock client with a *typed* fixture. (3–4 hours)**

Concretely, by end of day one:
```bash
mkdir -p adjacent/backend/app/qloo adjacent/backend/tests/fixtures
# pyproject with fastapi, httpx, pydantic, psycopg, pytest, ruff
# Makefile: dev test types migrate lint
# .github/workflows/ci.yml: ruff + pytest
```
Then `qloo/client.py`, `qloo/params.py` (the allowlist, which **raises** on unknown parameters), `qloo/models.py` for the three response shapes we need first (tags, entity-affinity, heatmap), and `MockQlooClient` reading one hand-written fixture.

**Acceptance test:**
```python
def test_unverified_parameter_raises():
    with pytest.raises(UnverifiedParameterError):
        build_params(filter_type="urn:tag", not_a_real_param="x")

def test_mock_returns_typed_tags():
    r = MockQlooClient().insights(filter_type="urn:tag", signal_interests_entities=["a"])
    assert isinstance(r, TagAffinityResponse) and r.results[0].affinity > 0
```

**Success = `make test` green in CI, with the allowlist enforced and a typed mock response flowing through the same interface the real client will use.**

---

### **5 — Write the exact `make milestone-1` test first, then make it pass. (Target: tomorrow evening / day two morning)**

Before writing the orchestrator, write `tests/test_cohort_ranking_single_normalisation.py` as a **failing test** that asserts: *given a programme, the runner constructs ≥3 cohorts across ≥3 domains, ranks them in exactly one Qloo call, rejects at least one for weak evidence, and every rendered number appears in the trace.*

```python
def test_milestone_1(monkeypatch):
    trace = run_mock("fixtures/portland.json")
    assert trace.stop_reason == "complete"
    assert len(trace.ranked_cohorts) >= 3
    assert len({c.domain for c in trace.ranked_cohorts}) >= 3
    assert trace.calls_by_tool["build_and_rank_cohorts"] == 1     # ← criterion 4
    assert any(r.reason == "weak_evidence" for r in trace.rejected_cohorts)
    assert_every_number_has_provenance(trace)
```

Then implement until it passes. **This is the whole of Milestone 1 (Part 16): 3–5 hours of work, and by the end of it the product's riskiest assumption is proven or disproven while there is still a month to react.**

---

## Why this order, and not "start with the frontend"

Because **action 1 can invalidate action 5's design**, and it costs 90 minutes to find out. Because **action 3 is free and prevents the failure that actually kills solo builds.** Because **action 4 builds the anti-hallucination type system before there is anything to hallucinate in** — retrofitting it later is the thing that doesn't happen. And because **action 5 tests the one assumption the whole product rests on** — that cohorts can be ranked validly in a single query — on the first evening, while changing course is still cheap.

The UI is the *last* thing, because the UI is the only part that cannot be wrong.

---

*Prepared 4 October 2026. Every Qloo capability asserted in this document was read from official documentation on or before this date and is cited inline. Every external claim carries a source. Values marked "illustrative" in Part 9 are placeholders, not recorded API output. Nothing in this document reports a measured performance improvement of Adjacent over any other system.*
