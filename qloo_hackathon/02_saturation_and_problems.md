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
