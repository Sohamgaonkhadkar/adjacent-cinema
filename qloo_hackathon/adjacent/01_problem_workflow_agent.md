# Adjacent — Product Definition & Execution Plan
### Parts 0–4 · Prepared 4 October 2026 · 26 days to deadline

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
    resolved: list[ResolvedEntity]  # id, name, subtype, popularity, source(ext_id|search)
    ambiguous: list[AmbiguityGroup]  # awaiting one user decision
    unresolved: list[str]

    # Evidence accumulation (the agent's working memory)
    taste_tags: list[ScoredTag]
    demographic_skew: DemographicProfile
    candidate_entities: dict[Domain, list[ScoredEntity]]
    candidate_cohorts: list[Cohort]
    ranked_cohorts: list[Cohort]  # single-normalisation ranking
    rejected_cohorts: list[RejectedCohort]  # each with a reason code
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
