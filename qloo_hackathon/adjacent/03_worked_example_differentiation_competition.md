# Adjacent — Product Definition & Execution Plan
### Parts 9–12 · Worked example, differentiator, proof of necessity, competition

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
