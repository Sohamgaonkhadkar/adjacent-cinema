# M13.16 — Fresh Qloo Hackathon Competitor Scorecard

**Research snapshot:** 24 October 2026
**Scope:** ten publicly accessible GitHub repositories that describe themselves as Qloo Agentic Hackathon projects, compared with Adjacent Cinema. This is a review sample, not a verified census of Devpost submissions.

## Official judging frame

The official [Qloo Agentic Hackathon page](https://qloo.devpost.com/) lists these criteria:

> **Technological Implementation** — “How thoroughly and skillfully does the project use Qloo? Does the code reflect genuine effort and a working, non-trivial implementation?”
>
> **Design** — “Does the project deliver a complete, coherent product experience, not just a technical proof of concept?”
>
> **Potential Impact** — “Does the project make a credible, specific case for solving a real problem for a real audience and does the solution actually address that problem based on what's demonstrated?”
>
> **Quality of the Idea** — “Is this a creative, non-obvious use of Qloo and does the team demonstrate genuine understanding of the problem space they're working in?”

The user requested equal weights, so this scorecard gives each criterion 25%. The official page names the criteria; this report does **not** claim that Devpost publishes equal numerical weights or that these are official judge scores.

## Method and confidence

I inspected public GitHub repository pages/READMEs and file-tree evidence for all ten projects. I also inspected selected source files for Common Ground (`src/lib/engine/score.ts`), MOSAIC (`src/engine.mjs`), Clash Control (`backend/app/qloo/overlap.py`), and Vellum (`src/app/api/curate/route.ts`). The remaining entries are primarily README/file-tree reviews. No competitor repository was cloned, built, tested, or run; no hosted demo was operated; and README performance/test/live-Qloo statements remain author-reported unless the cited source file itself supports the narrow implementation detail. The source code was not audited exhaustively.

Scores are **screening estimates from visible public evidence**, not measured product quality, popularity, placement, or a prediction of judging results. A repository, README, or screenshot cannot establish that a hosted application currently works. Score differences of a point or less should not be treated as meaningful. Confidence is medium for inspected source paths and low-to-medium for README/tree-only entries.

## Equal-weight scorecard (1–10)

| Project | Technological implementation | Design | Potential impact | Quality of idea | Mean | Evidence reviewed and comparison note |
|---|---:|---:|---:|---:|---:|---|
| **Adjacent Cinema** | 7.0 | 7.5 | 6.5 | 7.5 | **7.1** | Current checkout: typed Qloo client, resolver, bounded orchestration, traces, Creator/Cinema workflows, FilmSponsor, and experiment persistence are visible in code; frontend checks passed in this workspace. The new Python changes are linted but not pytest-verified here, and live Qloo/hosted operation is reserved to the owner. Specific filmmaker/programmer decision lifecycle is a strength; no user or outcome evidence is claimed. |
| **Clash Control — Neric Joël** | 8.0 | 9.0 | 8.0 | 8.0 | **8.3** | [Repository](https://github.com/neric-joel/qloo-agentic-hackathon): README describes a festival clash ranking/schedule workflow with a public demo and limits; inspected `overlap.py` documents rank normalization, symmetric pair scoring, and unknown/one-direction coverage. Repo tree contains extensive backend tests. The README's live/demo status and user-facing behavior were not independently operated. Strong adjacent festival-programming workflow, but not the same filmmaker pre-release positioning/experiment problem. |
| **COMMON GROUND — Dhamani-aryan** | 9.0 | 9.0 | 8.0 | 9.0 | **8.8** | [Repository](https://github.com/Dhamani-aryan/qloo-hackathon): README describes group-to-group cultural programming, Qloo resolution/discovery/separate group scoring, session plans and organizer materials. Inspected `score.ts` shows a deterministic evidence-diversity/bilateral-lift calculation and describes its output as a ranking score, not probability. The README reports automated and live-case results; those counts/results are self-reported and were not run or corroborated here. Closest overlap on cinema/community programming. |
| **MOSAIC — Abdullah-m7** | 9.0 | 9.0 | 8.0 | 9.0 | **8.8** | [Repository](https://github.com/Abdullah-m7/qloo-mosaic): README describes evidence-gated cultural negotiation for event organizers, separate group-relative ranks, trade-off baselines, veto stress tests, and abstention. Inspected `engine.mjs` implements deterministic feasible-plan ranking and explicitly labels group scores as proxies, not probabilities/attendance. README says public demos are synthetic while a separate isolated API smoke test passed; neither claim was independently tested in this review. |
| **Taste-Matched Trailer — Yannabadie** | 8.0 | 9.0 | 7.0 | 9.0 | **8.3** | [Repository](https://github.com/yannabadie/taste-matched-trailer): public repository description and tree show Qloo-linked creative briefs, editorial-workbench code, runtime/Qloo modules, test files, a license, and rendered creative assets. The creator-facing creative-output direction is compelling and adjacent to Creator Mode; no code/build/demo was run here, and tree presence does not prove the claimed live behavior. |
| **TasteMem / Taste Compass — Dev-angPatil** | 7.0 | 9.0 | 7.0 | 8.0 | **7.8** | [Repository](https://github.com/Dev-angPatil/qloo-agentic-hackathon): README describes a visual personal cultural shelf and four discovery/trip modes. The public tree includes Qloo resolve/search/recommendation routes and adversarial/integration-oriented test files. Implementation, tests, external metadata providers, and current live service were not independently exercised. Broad discovery UX is polished in concept but less focused on a single cinema decision lifecycle. |
| **VELLUM — PPurab-006** | 6.0 | 8.0 | 6.0 | 7.0 | **6.8** | [Repository](https://github.com/PPurab-006/qloo-taste-agent): README describes a cross-domain personal cultural itinerary and explainability; tree includes Qloo/client/API/test modules. Inspected `route.ts` validates a request with a schema before calling the curator and classifies Qloo errors. The README also describes a mock fallback; that behavior was not independently inspected or tested. Broad personal curation is adjacent but less tied to cinema operations. |
| **Taste Trail — aibeginnermcp** | 7.0 | 8.0 | 7.0 | 6.0 | **7.0** | [Repository](https://github.com/aibeginnermcp/taste-trail-qloo): README describes a Qloo-grounded weekend culture trail, same-origin server routes, replacement/exclusion behavior, and controlled fixture tests; it explicitly says fixture tests do not prove live Qloo availability. This is a coherent consumer itinerary rather than a cinema programming or creator experiment tool. Source implementation and test suite were not run. |
| **IRL LootDrop — vamshiivardhan** | 6.0 | 8.0 | 6.0 | 7.0 | **6.8** | [Repository](https://github.com/vamshiivardhan/qloo-H): README/tree describe a game-inspired multi-turn agent, Python/FastAPI backend, Qloo categories, and a Qloo-grounded versus “naked LLM” comparison UI. These are repository descriptions and file-tree evidence; no measured recommendation quality, live response, or deployment was verified. The cross-domain gaming-to-lifestyle concept is distinct but outside Adjacent's core user. |
| **Taste-Evolving Concierge — rajat552** | 6.0 | 8.0 | 6.0 | 7.0 | **6.8** | [Repository](https://github.com/rajat552/qloo-hackathon): README describes a persistent cultural graph, multi-step concierge, city itinerary, and Qloo integration; the public tree includes a service/API layer and screenshots. The “production”/live/API claims in the README were not verified; no tests or live service were run in this review. Persistent personal taste memory is a different, broad consumer proposition. |
| **Qloo Cultural Taste Agent — liutingqiu** | 5.0 | 7.0 | 5.0 | 7.0 | **6.0** | [Repository](https://github.com/liutingqiu/qloo-cultural-taste-agent): README describes an MCP-based cross-domain agent, workbench, and six tests; the tree includes source, generated `dist` files, and `tests/qloo.test.js`. Those test results and claims such as calibrated affinity are author-reported and were not run or validated against Qloo. The idea is broad and agent-framework oriented rather than a narrow decision workflow. |

**How to read the mean:** arithmetic mean of the four visible scores, each weighted equally. It is a compact prioritization aid, not a ranking. Rows are ordered by relevance to Adjacent's cinema/creator space, not by mean score.

## What the comparison suggests for Adjacent

1. **The closest reviewed overlaps are real.** COMMON GROUND and MOSAIC both address cultural bridges between groups in event/community settings, while Clash Control addresses festival scheduling and Taste-Matched Trailer addresses creator-facing creative work. Adjacent should not pitch itself as the only Qloo project touching film, festivals, or creator decisions.
2. **Keep the product distinction narrow and evidence-based.** Adjacent's most defensible difference in this sample is the connection from a filmmaker's comparable works and cultural evidence to a pre-release positioning decision, editable Test Card, saved experiment snapshot, and later append-only observations/evaluation. This is a description of this sample—not a claim that no other tool can do those things.
3. **The clearest technical proof is provenance and boundaries.** Demo one live, resolved Qloo path only after the owner independently verifies it: exact resolved title/year/ID, the related call trace, bounded analysis, and where attribution is returned. Clearly identify fixture output otherwise. Do not present affinity as demand, attendance, views, sponsorship likelihood, or causal lift.
4. **Impact is the largest evidence gap across Adjacent's own case.** The target problem is specific, but there are no current creator interviews, pilot, customer adoption, release outcomes, or measured impact in this review. Do not fill that gap with competitor README claims or synthetic evaluation numbers.
5. **Avoid a feature-count arms race.** Competitors publicly describe large agent/tool stacks and broad feature sets. Adjacent's credible case is narrower: verified inputs, honest evidence states, an inspectable programming/positioning choice, and a preserved experiment lifecycle—not a more autonomous agent or an unsupported performance prediction.

## Sources

Official rubric and deadline: [Qloo Agentic Hackathon — Devpost](https://qloo.devpost.com/). The page currently lists the deadline as 30 October 2026; it does not establish that any repository below is an accepted/submitted Devpost entry.

Public repository pages reviewed on 24 October 2026:

- [Neric Joël — Clash Control](https://github.com/neric-joel/qloo-agentic-hackathon)
- [Dhamani-aryan — COMMON GROUND](https://github.com/Dhamani-aryan/qloo-hackathon)
- [Abdullah-m7 — MOSAIC](https://github.com/Abdullah-m7/qloo-mosaic)
- [Yannabadie — Taste-Matched Trailer](https://github.com/yannabadie/taste-matched-trailer)
- [Dev-angPatil — TasteMem / Taste Compass](https://github.com/Dev-angPatil/qloo-agentic-hackathon)
- [PPurab-006 — VELLUM](https://github.com/PPurab-006/qloo-taste-agent)
- [aibeginnermcp — Taste Trail](https://github.com/aibeginnermcp/taste-trail-qloo)
- [vamshiivardhan — IRL LootDrop](https://github.com/vamshiivardhan/qloo-H)
- [rajat552 — Taste-Evolving Concierge](https://github.com/rajat552/qloo-hackathon)
- [liutingqiu — Qloo Cultural Taste Agent](https://github.com/liutingqiu/qloo-cultural-taste-agent)
