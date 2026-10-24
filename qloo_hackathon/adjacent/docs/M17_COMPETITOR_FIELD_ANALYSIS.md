# M17 — Competitor field analysis (270-repository census) and where Adjacent ranks

**Research snapshot:** 25 October 2026
**Scope:** every public GitHub repository returned by the search `qloo hackathon` (270 repos), funnelled to the
12 that are genuinely comparable to Adjacent Cinema, compared against this repository.
**Supersedes as a sample:** `M13_16_FRESH_HACKATHON_COMPETITOR_SCORECARD.md` (10 repos, README-level review).
That document's rubric quotes are still the source for the official judging criteria; its means should no longer be
read as a field ranking.

---

## 0. Verdict in one paragraph

In the film/cinema cluster, **Adjacent ranks 3rd of 7**, behind `zicheng-yu/clearrun` and `shro-2002/territory`.
Across the whole comparable shortlist it lands **around 4th–6th of 12**, in the same 8.0 band as
`Dhamani-aryan/COMMON GROUND` and `louji2308/Zorq`. The gap to the top two is **not product depth** — Adjacent has
more product surface, far more tests and broader Qloo endpoint coverage than either. The gap is **published
evidence and judge-facing packaging**: the leaders ship a *completed* head-to-head that shows why Qloo is necessary
(territory's E6 ablation, clearrun's backtests), and they ship a public demo URL. Adjacent has the ablation harness
but its comparison arm has never run, and it has no deployed demo.

---

## 1. What I actually verified (read this before trusting any number below)

| Tier | Meaning | Applies to |
|---|---|---|
| **T0 — executed here** | I cloned the repo, ran its own test command in this sandbox, and saw the result. | `territory`: `npm ci && npm test` → **8 files, 80 tests passed**. `clearrun`: `npm ci && npm test` → **11 files, 71 tests passed**. |
| **T1 — source read** | I read the cited source files; the claim is supported by code I can see. | All 12 finalists' architecture claims, Qloo parameter usage, baselines/ablations, persistence, CI workflow contents. |
| **T2 — author-reported** | Only the README/artefact says it; I could not run it. | Every hosted demo, every live-Qloo statement, any performance number not backed by a committed artefact. |

**Not verified, by anyone's standard:**

- **No competitor hosted demo was operated.** Outbound HTTP from this sandbox to their deploy domains returns
  connection failure (`curl` → `000`), e.g. `territory-qloo.netlify.app`, `clearrun.zichengyu.com`. So "has a live
  demo" below always means *"README publishes a URL"*, not *"I saw it work"*.
- **I did not run Adjacent's own backend suite in this sandbox.** The suite is Python 3.12+ (PEP 695 generic class
  syntax in `backend/app/qloo/models.py:239`) and this sandbox has 3.11 only. Adjacent's test evidence here is its
  CI workflow (ruff, pytest `not live`, pytest `live`, `scripts/qloo_probe.py`, 8 frontend node suites, Next build,
  render.yaml parse, both Docker image builds) plus the 737 test functions counted in `backend/tests`.
- **Design is the weakest-verified aspect.** I can judge rival UI only from screenshots they committed (I viewed
  clearrun's backtest screen and COMMON GROUND's bridge screen). **Adjacent commits no screenshots and I have no
  browser in this sandbox**, so Adjacent's Design score is inferred from code and tests, not from pixels. It carries
  the widest error bar of any number in this document.
- Stars are noise in this cohort (the whole corpus peaks at 12★, this event at 4★). Popularity is not used anywhere.

---

## 2. The field, measured

### 2.1 Funnel

- **270** repos match `qloo hackathon` (spans the 2026 event and the 2025 Qloo LLM Hackathon). 233 carry a licence.
- Most of the remainder are gift / travel / city-translation / senior-dining / gaming taste apps. They are not
  competitors for the same judge attention span as a film product, and most are 1–3 kLOC.
- **12** were cloned and analysed with one identical script (`/tmp/analyse.sh`): 11 rivals + this repository.

### 2.2 Verified structural metrics

Product LOC excludes `test|spec|e2e|fixture|mock` paths; test LOC is the complement. Same script, same exclusions,
all 12 repos. This table is deliberately *not* a quality ranking — see §3 for why volume misleads.

| Repo | Domain | Product LOC | Test LOC | Test files | CI | Persistence | LLM in path |
|---|---|---|---|---|---|---|---|
| **Adjacent (this repo)** | pre-release cultural positioning for film | **33 047** (21 871 backend + 11 176 frontend) | 16 003 | 42 backend + 7 frontend suites, **737 test fns** | ruff + pytest ×2 + probe + 8 node suites + build + 2 Docker builds | SQLite | optional, **synthesis only** |
| `neric-joel/qloo-agentic-hackathon` (Clash Control) | festival clash scheduling | 60 732 | 65 796 | 150 | browser + ci, "journey gate" | Redis + localStorage | Anthropic, in path |
| `louji2308/Zorq` | cultural composition for physical places | 24 533 | 19 726 | 92 | ci + healthz | — | DeepSeek, in path |
| `Dhamani-aryan/qloo-hackathon` (COMMON GROUND) | two-group cultural bridge for community programming | 12 558 | 3 549 | 38 | none | Redis | OpenAI, in path + baseline |
| `zicheng-yu/clearrun` | film release-week choice | 8 570 | 2 083 | 71 (T0 pass) | typecheck + test | SQLite | Claude Haiku, tool-calling |
| `yannabadie/taste-matched-trailer` | book-trailer cultural direction | 8 184 | 1 214 | 9 | none | — | Claude, in path |
| `shro-2002/territory` | indie film distribution war room | 4 825 | 1 069 | 80 (T0 pass) + Playwright | lint + typecheck + test + build + e2e | Redis | **none** |
| `G-Hostin/quiet-week` | indie game launch timing | 5 058 | 561 | 9 | none | — | Gemini, in path |
| `longtt-marketing/taste-brief` | podcast ad buying for brands | 3 772 | 1 214 | 15 + benchmark suite | review workflow | — | Anthropic, in path |
| `msimakhov-star/will-it-land` | "spellcheck for cultural references" in scripts | 4 088 | 652 | 24 + eval + kill-test | pages | SQLite | Gemini + Claude |
| `Abdullah-m7/qloo-mosaic` (MOSAIC) | cultural negotiation for promoters | 2 293 | 1 657 | 23 | smoke + benchmark | — | none |
| `kevin9327/HyperCueStudio` | greenlight / sync / touring "courtroom" | 2 924 | 151 | 1 | pages | — | Gemini, in path |

### 2.3 Qloo surface used

Endpoint families hit, by repo (all /12):

- **Adjacent (8):** `/v2/insights` ×23, `/search` ×23, `/entities` ×25, `/v2/tags` ×6, `/v2/audiences` ×5,
  `/v2/trending` ×4, `/v2/analysis/compare` ×3, `/heatmaps` ×3 — with a declarative `ParamSpec` registry
  (`backend/app/qloo/params.py`, 930 lines) that marks each parameter verified/unverified and carries an
  `open_question` probe id for the ones that are not.
- `neric-joel` (2, very broad usage): `/search` ×160, insights ×87.
- `kevin9327` (2): `/search` ×24 + insights ×23, plus the `@qloo/qloo-harness` npm package.
- `clearrun` (2, cleverest): `/search` for title resolution, `/v2/insights?bias.content_based=1` so **unreleased
  films score from content rather than from a behavioural graph that already knows how the release went**, plus a
  Wikidata → Qloo `/entities` join for the release calendar.
- `territory`, `quiet-week`, `will-it-land`, `taste-brief`, `Zorq`, `MOSAIC`, `COMMON GROUND`: 1–3 families each.

Adjacent's breadth is real, but breadth is the weakest kind of advantage: it is easy to copy and hard for a judge to
see without reading the parameter registry.

---

## 3. Aspect-by-aspect

Eight aspects, each: what the best rival actually does (with the file that proves it), what Adjacent does, verdict.
A "rival" here means a repo where I read the code (T1), not one whose README I trusted.

### A1 — Qloo depth and correctness

**Field best — `clearrun`.** `src/worker/qloo.ts:173-186` refuses to score an unreleased film from the behavioural
graph and passes `bias.content_based=1` instead; `src/engine/backtest/run.ts` explains that "pre" means content-based
scores because *"today's graph already knows how the release went, so it can't stand in for what was knowable at the
time"*. That is the single sharpest piece of Qloo reasoning in the whole field: it is the *leakage* problem, named
and solved.

**Adjacent.** Widest endpoint coverage, a typed client, a parameter registry that explicitly marks what is unverified
rather than guessing (`filter.tags` is flagged `UNVERIFIED` with a probe id), and normalisation-safe scoring in
`app/domain/scoring.py` using band-based strength. **But there is no `bias.content_based` support anywhere in
`app/qloo/params.py`** and no treatment of the pre-release leakage problem at all — for a product whose whole premise
is positioning a film *before* release, that is a genuine analytical hole, not a cosmetic one.

**Verdict:** Adjacent wins on breadth and on honesty about unknowns; loses on the one parameter that matters most for
its own use case.

### A2 — Agentic architecture

**Field best — `clearrun`** (real tool-calling agent over 4 tools, results re-checked against the answer, a daily
re-plan watch with a change log) and **`territory`** (deterministic planner that **re-plans under constraint shocks**
— remove a market or cut the budget 40% and it emits v2/v3 with reasons, sealed against tampering).

**Adjacent.** `backend/app/agent/orchestrator.py` is a hand-written 5-phase state machine
(`resolve → analyse → expand → rank → stop`). `plan_next()` is strictly linear and non-adaptive:
a completed phase is never revisited, which is what makes termination provable. Governance around it is stronger than
anyone else's — typed stop reasons, call budget, `request_id` dedupe, idempotent persistence.

**Verdict:** best-in-field *governance*, mid-field *agency*. Every serious rival can change its mind mid-run; Adjacent
cannot. For a hackathon called "Agentic", a loop that provably cannot adapt is the wrong thing to be proud of in
public — it should be framed as a deliberate reliability trade-off (ADR-001) and paired with at least one widening
path, or it will read as a workflow engine.

### A3 — Evidence discipline: proving Qloo is necessary

This is the aspect that separates the top of the field from the middle, and it is where Adjacent's story is most
misunderstood — including inside this repo.

**Field best — `territory`.** `docs/EVALUATION.md` + `docs/experiments/e6-live.json`: four briefs, same 9 markets,
same cost table, same two revisions, Territory vs local `qwen3:14b` with no tools. Published numbers: cost totals
correct 9/9 vs **3/12**; cold start with fictional comps — Territory **declines**, the LLM produces a confident
5-market plan in 3/3 prompts and names 0/10 real comps. A second artefact (`ablation-live.json`) runs the same planner
with Qloo off and shows it recommends the same plan for every film.

**Field best (different shape) — `taste-brief`.** Pre-registration locked and hash-verified before any held-out show
was read (`docs/podcast-check/PREREGISTRATION.md`, `LOCK.sha256`, `verify_lock.py`), then a real predictive test on
259 shows / 76 brands: Qloo AUC **0.663** vs Apple chart rank 0.528, popularity 0.517, ad volume 0.581, with sign
tests and CIs in `results.json`. Also `clearrun` (`docs/eval-baseline.md` + the backtests tab), `Zorq`
(`docs/qloo-removal-proof.md`, a Prior frozen before any data), `COMMON GROUND` (`src/lib/agent/ablation.ts` and
`baseline.ts`, run in parallel in `orchestrator.ts:321`), `MOSAIC` (`docs/LIVE_ABLATION_PROTOCOL.md` +
`evidence/synthetic_benchmark_*.json`), `will-it-land` (`eval/PREREG.md`).

**Adjacent.** More than I expected before reading it: `docs/M13_11_QLOO_VS_LLM_EVALUATION.md` is a genuine
two-condition harness (`research/scripts/m13_11_qloo_vs_llm.py`), and the repo **self-audited its own rubric twice**
(`M13_12` found that scoring `evidence_traceable` in both conditions guaranteed the baseline a zero; `M13_13` found
that abstention was being penalised) — that is better measurement hygiene than most of the field. `docs/M12_*`
adds a 10-context baseline-vs-Qloo difference study with committed artefacts. **But:** the LLM-only arm has never
run (`BLOCKED — ADJACENT_LLM_API_KEY not configured`), the grounded arm ran on **fixtures**, the briefs are 5
synthetic ones with explicitly no statistical claim, and the M12 "novelty proxy 0.997 / overlap 0.003" is an internal
difference measure with no ground truth behind it. So the harness exists, the *result* does not.

**Verdict:** strongest *process*, weakest *publication*. Adjacent would lose this aspect to territory on a judge's
30-second read even though its rubric discipline is arguably more careful — because a harness with a BLOCKED arm
reads as "not finished", and a table with nine numbers and a counterfactual reads as "proven".

### A4 — Honesty and failure handling

**Field best — `will-it-land`** (ships an explicit "not calibrated — the app says so" surface, scores stand-ins
identically to originals, keeps a rewrite only if the rooms improve) and **`quiet-week`** (a human confirms every
Qloo match before any measurement is shown; `check:live` and `check:secrets` are npm scripts, so the honesty policy is
executable). **`COMMON GROUND`** labels judgements inline on screen: "activity fit is our interpretation; venue access
is unverified".

**Adjacent.** This is Adjacent's strongest aspect and it is not close. A `data_status` contract that distinguishes
fixture from live everywhere, 1 763 honesty markers in source, 322 retry/timeout/rate-limit sites,
`public_demo.py` gates with separate `ADJACENT_PUBLIC_DEMO` / `ADJACENT_PUBLIC_LIVE` flags, a documented **no silent
fallback** rule (FilmSponsor discovery returns 503 rather than substituting), and `FEATURES_NOT_BUILDING.md` that
lists what does not work. `docs/CONFIGURATION.md` is an env matrix naming owning services with no secret values.

**Verdict:** Adjacent #1 in the field, and it is the thing most worth defending in the submission.

### A5 — Persistence and decision lifecycle

**Field best — `clearrun`** (`watches` table, daily re-check with a change log, share links) and `neric-joel`
(Redis + localStorage with quota isolation).

**Adjacent.** Saved experiment snapshot → editable Test Card → append-only observations → evaluation, with
idempotent writes and `request_id` dedupe. Nobody else in the sample closes the loop from *prediction* to *observed
outcome*; the rivals stop at the recommendation. This is the most defensible product idea in the field and it is
currently buried in a milestone doc instead of being the headline.

**Verdict:** Adjacent #1 on lifecycle, but the payoff (evaluation after the window closes) has never been shown with
real data, which mutes it.

### A6 — Engineering proof

**Adjacent.** Deeper CI than every rival I could read: ruff, pytest `not live`, pytest `live`, a live Qloo probe
script, 8 separate frontend node suites, Next build, `render.yaml` YAML parse, and **both** Docker images built per
run. 737 backend test functions; 132 docs.
**Rivals:** `territory` lint/typecheck/test/build/e2e (80 tests, verified passing here); `neric-joel` a "journey gate"
that fails on any skipped test; `clearrun` typecheck+test (71, verified); `Zorq` lint/typecheck/test; the rest either
no CI or a smoke/deploy workflow only.

**Verdict:** Adjacent #1, narrowly over territory. Note the counterweight: Adjacent's tests are 100 % offline and its
own `M13_11` shows the *comparison* is what's missing — more tests of the same code would not move a judge.

### A7 — Design and judge-facing packaging

**Field best — `COMMON GROUND`** (editorial typography, a three-panel "why this / what Qloo added / what the agent
did" strip, inline caveats) and **`clearrun`** (a percentile-slider backtests screen that makes an ablation argument
visible without reading a word of prose). Also `Zorq` (1440 **and** 360 screenshots, i.e. someone checked mobile) and
`taste-brief` (10 screenshots, including a with/without comparison).

**Adjacent.** A port of a supplied design reference: 4 routes (`/`, `/creator`, `/cinema`, `/creator/sponsor`),
21 components, 11 lib modules, layout/render/recovery/positioning/entity-display/contract node suites — so the UI is
*tested*, and honest unavailable states are exercised rather than mocked away. **But zero committed screenshots, no
`JUDGE_DEMO.md`, no 60-second path in the README, and no deployed URL.** By contrast 8 of the 11 rivals publish a
hosted URL (netlify / vercel / render / github.io / workers.dev / modal).

**Verdict:** likely competitive on craft, **last-but-one on packaging** in a judged event. This asymmetry is the
single most fixable thing on this list.

### A8 — Impact and domain understanding

**Field best — `territory`** (an indie distributor with an $80k print-and-marketing budget choosing ≤5 of 9 markets,
then absorbing real-world shocks) and **`clearrun`** (which week to open, with the pre-release-knowledge caveat
handled). Both describe a specific person with a specific recurring decision and a specific cost of being wrong.

**Adjacent.** "Pre-release cultural positioning for a filmmaker, with a Test Card and later observations" is a real
workflow and the lifecycle makes the impact *measurable later*. But the case is argued in docs, not demonstrated:
no user, no measured outcome, no retrospective. Several rivals have more modest domains with sharper evidence.

**Verdict:** top third. The argument is credible; the evidence is missing.

---

## 4. Scorecard

Official Devpost criteria (quoted in `M13_16`), **equal 25 % weights as requested**, 1–10, from the evidence above.
These are my screening estimates, not official scores, not measured product quality, and not a prediction of judging.
Differences ≤ 0.5 should not be read as meaningful.

| # | Project | Tech | Design | Impact | Idea | Mean | Evidence tier |
|---|---|---|---|---|---|---|---|
| 1 | `zicheng-yu/clearrun` | 9.0 | 8.5 | 8.5 | 9.0 | **8.75** | T0 tests + T1 code + screenshots |
| 2 | `longtt-marketing/taste-brief` *(not film)* | 9.0 | 8.0 | 8.5 | 8.5 | **8.5** | T1 code + committed results |
| 3 | `shro-2002/territory` | 8.5 | 7.5 | 9.0 | 8.5 | **8.4** | T0 tests + executed artefacts |
| 4 | **Adjacent (this repo)** | 8.5 | 7.5 | 8.0 | 8.0 | **8.0** | T1 code + own docs; **no visual check** |
| 5 | `louji2308/Zorq` *(not film)* | 8.5 | 8.0 | 8.0 | 8.0 | **8.1** | T1 code + screenshots |
| 6 | `Dhamani-aryan/COMMON GROUND` | 8.0 | 9.0 | 7.0 | 8.0 | **8.1** | T1 code + screenshots |
| 7 | `msimakhov-star/will-it-land` | 7.5 | 8.0 | 7.0 | 8.5 | **7.75** | T1 code + eval artefacts |
| 8 | `G-Hostin/quiet-week` | 7.5 | 7.5 | 7.5 | 8.0 | **7.6** | T1 code |
| 9 | `Abdullah-m7/MOSAIC` | 7.5 | 7.5 | 7.0 | 7.5 | **7.4** | T1 code + synthetic benchmark |
| 10 | `neric-joel/Clash Control` | 8.0 | 7.0 | 7.5 | 7.0 | **7.4** | T1 code (largest codebase in the field) |
| 11 | `kevin9327/HyperCueStudio` | 6.0 | 7.5 | 7.0 | 7.5 | **7.0** | T1 code: 1 test file for those claims |
| 12 | `yannabadie/taste-matched-trailer` | 7.5 | 6.5 | 6.0 | 7.5 | **6.9** | T1 code; extraordinary evidence artefacts, tiny audience |

*(Rows 4–6 are within 0.1 of each other; treat them as tied. Sorted by mean, rank column reflects rounding of
equal-weight sums before display.)*

**Sensitivity.** Adjacent's Design score is the least verified number here. At Design 8.5 it reaches 8.25 (2nd in the
film cluster); at 6.5 it drops to 7.75 (4th). Everything else about its position is stable.

### Film/cinema cluster only

| Rank | Project | Mean |
|---|---|---|
| 1 | `clearrun` | 8.75 |
| 2 | `territory` | 8.4 |
| 3 | **Adjacent** | **8.0** |
| 4 | `COMMON GROUND` (community programming, film in the mix) | 8.1 → tied with Adjacent |
| 5 | `will-it-land` | 7.75 |
| 6 | `MOSAIC` | 7.4 |
| 7 | `HyperCueStudio` | 7.0 |

---

## 5. Why the top two are ahead — and why that matters

Both leaders are **smaller** than Adjacent (8.6 k and 4.8 k product LOC vs 33 k) and use **fewer** Qloo endpoints.
They win on two artefacts Adjacent does not have:

1. **A finished counterfactual.** territory's E6 and clearrun's backtests both answer, with numbers, "what happens
   without Qloo / without tools?" Adjacent's answer to that question exists as a harness with one arm BLOCKED.
2. **A URL a judge can click.** Eight of eleven rivals ship one. In a 4-criterion rubric where "Design" means
   "a complete, coherent product experience", a judge who cannot open the product scores what they can see.

Neither gap is architectural. Both are days, not weeks, of work — which is the good news in this document.

---

## 6. Adjacent's honest weaknesses, in the order a judge would notice them

1. **No hosted demo.** The guards (`ADJACENT_PUBLIC_DEMO`, `ADJACENT_PUBLIC_LIVE`, guest-origin allowlist, bounded
   runs, fixture/live separation) are built and tested; the deployment is not done. Everything else on this list is
   less visible than this one.
2. **The headline comparison is BLOCKED.** `M13_11` says so itself. A judge who reads it sees "not finished".
3. **No pre-release leakage handling.** No `bias.content_based`; the film being positioned may already be encoded in
   Qloo's behavioural graph.
4. **Non-adaptive loop.** Strictly one pass, and the hackathon is called "Agentic".
5. **No machine-consumable surface.** No MCP server. `will-it-land`, `COMMON GROUND` and `HyperCueStudio` all expose
   one; that is a cheap, visible "agentic" signal Adjacent lacks.
6. **Evidence is invisible.** 132 docs, including twelve evaluation/benchmark documents and 10 committed result artefacts — none of it
   surfaces in the README as a table a judge will read in 30 seconds.
7. **No screenshots, no `JUDGE_DEMO.md`, no 60-second path.** All three rivals that look most "finished" have all
   three.

## 7. Strengths no rival in this sample has

- **End-to-end decision lifecycle**: prediction → Test Card → append-only observations → evaluation, with idempotent
  writes and dedupe. Every rival stops at the recommendation.
- **Honesty as an executable contract**: `data_status`, no-silent-fallback, `FEATURES_NOT_BUILDING.md`, public-demo
  gates, `CONFIGURATION.md` with owning services and no secrets.
- **Self-audited measurement**: the rubric was rewritten twice because the repo found its own scoring flaws
  (`M13_12`, `M13_13`). Nobody else in the field documents having done that.
- **CI depth**: two pytest markers, a live probe script, 8 frontend suites, two container builds per run.

## 8. The four moves that would change the ranking

Ordered by judge-impact per unit of work. None requires a rewrite.

1. **Deploy the public demo** (guards already exist) and put the URL + a 60-second walkthrough at the top of the
   README with 4–5 committed screenshots. Moves Design and the first impression; costs no product code.
2. **Finish the counterfactual, in the form judges read.** Two arms:
   (a) run `M13_11` Condition A with a real LLM key when available — the harness is written;
   (b) add an LLM-free arm that works offline today: same brief, ranking with Qloo insights disabled vs enabled,
   reporting how often the recommended cohort changes. territory's E6 is the template, and Adjacent's run/evidence
   structures already store what is needed. Publish a 6-row table in the README.
3. **Support `bias.content_based`** in `app/qloo/params.py` (one `ParamSpec` + client plumbing + mock + tests) and use
   it for unreleased films, stating the leakage reason in the UI. This is the single strongest technical argument
   available to a *pre-release* film product, and clearrun currently owns it alone.
4. **Add a one-tool MCP server** (`find_adjacent_cohorts` / `read_run`) over the existing service layer, so other
   agents can call Adjacent. Cheap, and it is the visible "agentic" credential the loop currently does not supply.

Optional fifth, if time remains: a widening step in `plan_next()` (re-expand when the cohort gate rejects everything)
— but only with the ADR-001 trade-off stated on screen, because the non-adaptivity is currently a *defensible*
argument and should not be quietly broken.

---

## 9. Reproducing this analysis

```bash
# census
gh api search/repositories -f q="qloo hackathon" -f per_page=50 -f page=1   # pages 1..6
# clones (shallow) into /tmp/comp/<owner>_<repo>/, then:
/tmp/analyse.sh          # per-repo structural metrics, same exclusions for every repo
# the two suites executed here:
cd /tmp/comp/shro-2002_territory && npm ci && npm test      # 80 passed
cd /tmp/comp/zicheng-yu_clearrun && npm ci && npm test      # 71 passed
```

**Limitations.** A GitHub search is not the Devpost submission list; some entrants may not publish a repo, and repos
may be private. Nothing here establishes that any hosted application currently works. Design scores are inferred from
committed screenshots and code for rivals, and from code alone for Adjacent. LOC and test counts measure typing, not
judgement. Scores are comparison aids within this snapshot, not measurements.
