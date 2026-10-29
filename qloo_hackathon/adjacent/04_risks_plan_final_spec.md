# Adjacent — Product Definition & Execution Plan
### Parts 13–17 · Risks, build plan, pre-key work, first milestone, final spec

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

## 13.1 Current evidence gates (implementation update, 29 October 2026)

This section supersedes the original fixed three-title rule. A run's seed coverage decides whether evidence gathering can start; it does **not** by itself authorise a strong recommendation. The taste-profile and candidate-cohort gates remain mandatory.

| Condition | Current behaviour |
|---|---|
| 3 or more verified reference works | Standard seed coverage. |
| 2 verified reference works | Exploratory run, with the limited seed coverage disclosed in the Creator result. The taste-profile and candidate-cohort gates still decide whether a positioning hypothesis is supported. |
| 1 verified reference work | Exploratory only when at least 2 distinct theme inputs resolve to exact, unique Qloo tag names. |
| No verified reference works | Tag-driven exploration only when at least 3 distinct theme inputs resolve to exact, unique Qloo tag names. |
| Fewer signals than those exploratory paths require | Stop with an explanation of which verified signals are missing. No unresolved title or theme is substituted. |
| Zero tags above the Medium band (0.5) | *"Qloo found no tags with meaningful affinity for this programme. Nothing has been substituted. This programme may be too heterogeneous, or too obscure, for the taste graph to characterise."* |
| No candidate cohort clears its member-level evidence gate | Refuse to name an adjacent audience. A candidate needs at least 2 members above Medium; the stronger band additionally requires at least 1 member above High. One surviving cohort is sufficient; the system does not require two separate surviving cohorts. |
| Fewer than 10 scored heatmap cells return for a city | Withhold a density/concentration claim. Any valid scored cells the provider did return may still be shown as points; they are not interpreted as attendance, footfall, or evidence of low cultural activity. |
| A programme bet scores below Medium against either signal | Refuse the two-sided bet unless both the current-audience fit and target-cohort fit clear Medium. |
| The per-run resource budget is exhausted | Stop as budget-exhausted, distinct from insufficient evidence or provider error. Current ceilings are 14 agent steps, 24 Qloo calls, and 90 seconds per run. |

The live seed-coverage rules are implemented in `backend/app/evidence.py` and applied to verified film and exact-matched theme signals in `backend/app/live_runner.py`. Geographic display policy is split between the backend's 10-cell concentration gate and the frontend's points-versus-density view. These are product policies, not universal Qloo requirements.
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
    assert trace.calls_by_tool["build_and_rank_cohorts"] == 1  # ← criterion 4
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
