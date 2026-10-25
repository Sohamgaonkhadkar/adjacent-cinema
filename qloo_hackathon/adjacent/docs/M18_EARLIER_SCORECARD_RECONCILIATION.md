# M18 — Reconciling the four earlier-scored competitors (and two corrections to my own M17)

**Date:** 25 October 2026
**Question asked:** the earlier scorecard (`M13_16`) put COMMON GROUND and MOSAIC at **8.8**, Clash Control
and Taste-Matched Trailer at **8.3**. `M17` (written yesterday) put the same four at 8.1, 7.4, 7.4 and 6.9.
Which is right, and how does Adjacent compare to them head-to-head?

**Answer:** COMMON GROUND's 8.8 was broadly right — I under-scored it. MOSAIC's 8.8 was inflated. Clash Control's
8.3 was right and my 7.4 was clearly wrong. Taste-Matched Trailer's 8.3 was inflated; 7.5 is the honest number.
Adjacent stays at 8.0 and therefore sits **below all three that survive at the top** — 3rd among film projects,
**7th of 12** across the comparable shortlist. Details, arithmetic and the two places where I was wrong are below.

---

## 1. Why the two scorecards disagreed

`M13_16` was **README-and-file-tree level**; it says so: *"No competitor repository was cloned, built, tested, or
run."* `M17` had cloned sources, but for these four I still leaned on tree metrics and my own grep counts, and the
grep counts were wrong in ways that mattered (see §2).

This round I cloned all four fresh and **ran every suite that can run in this sandbox**. Three of the four turned
out to be substantially better engineered than their file-tree appearance suggested, because their test counts are
test *cases* inside few files, not test *files*.

| Project | `M13_16` mean | `M17` mean | **This review** | Direction |
|---|---:|---:|---:|---|
| COMMON GROUND | 8.8 | 8.1 | **8.5** | both neighbours wrong; 8.8 near the truth |
| MOSAIC | 8.8 | 7.4 | **7.9** | `M13_16` inflated, `M17` too harsh |
| Clash Control | 8.3 | 7.4 | **8.5** | `M13_16` near the truth, `M17` clearly wrong |
| Taste-Matched Trailer | 8.3 | 6.9 | **7.5** | `M13_16` inflated |
| **Adjacent** | 7.1 | 8.0 | **8.0** | unchanged from `M17` |

`M13_16`'s Adjacent score of 7.1 is not comparable to the 8.0: the 7.1 was written before CI went green on the
port and before the 737-test backend / 8-node-suite frontend state existed. Do not read the two Adjacent numbers
as a decline.

## 2. What I actually executed (T0 evidence)

| Project | Command | Result |
|---|---|---|
| **COMMON GROUND** | `npm ci && npm test` (vitest) | **29 files, 186 tests, 0 failures**, 10.7 s |
| **MOSAIC** | `npm test` (node `--test`, project has **zero dependencies**) | **127 tests, 0 failures**, 2.0 s |
| **Clash Control (web)** | `npm ci && npm test` (vitest) | **88 files, 2,307 passed, 16 skipped**, 67 s |
| **Clash Control (backend)** | — | **not run**: `requires-python = ">=3.12"`; sandbox has 3.11 and no `uv`. Counted instead: **545** `def test_` functions in 33 files, plus 28 Playwright e2e specs. |
| **Taste-Matched Trailer** | `python3 -m unittest discover` | **6 tests, OK** |
| | `node --test tests/test_editorial_workbench.mjs` | **4 tests pass** |
| | `node --test runtime/test_recorded_cache.mjs` | **fails on a clean clone** — hardcodes `/home/user/Library/Application Support/Agentique/...`, a path on the author's own Mac, to a private recording that is deliberately not committed. Not a logic bug; a portability defect that means this one test proves nothing to anyone but the author. |
| **Adjacent** | — | **not run here**: backend needs Python 3.12 (PEP 695 `class ToolResult[T]` at `app/qloo/models.py:239`). Evidence remains its CI workflow (ruff, pytest `not live`, pytest `live`, `qloo_probe.py`, 8 node suites, Next build, `render.yaml` parse, two Docker builds) and 737 test functions. |

## 3. Project by project

### 3.1 COMMON GROUND — `Dhamani-aryan/qloo-hackathon` → **8.5**

**What it is:** two groups of people with different cultural favourites → find what *both* genuinely like (not what
everyone likes), then build a 4-session programme and an organiser's delivery pack.

**What I verified in code, this round:**

- **An LLM-only baseline that runs in the product, in parallel with the real run** — `src/lib/agent/baseline.ts`,
  launched at `src/lib/agent/orchestrator.ts:319-329`, degrading to `null` with a warning if the model fails, and
  surfaced in the UI via `compareStats` (`src/lib/agent/ablation.ts`, `src/components/studio/comparison.tsx`).
  A judge sees "what the same AI said without Qloo" **on the result page**, not in a document.
- **An executed evaluation** (`docs/EVALUATION.md`): 16 cases, **live** (Qloo + LLM, no cache), 1 held out, with a
  published ablation table — 58 plan anchors backed by both groups' Qloo data vs **0** for the baseline; 148 of 188
  baseline titles merely reuse the favourites it was given; 40 of 188 named with no evidence; 257 evidence citations
  vs 0. Technical metrics too: 100 % seed resolution (136 exact / 14 flagged / 0 not found), 68 % of candidates
  rejected by the two-sided test, 2132 one-sided and 464 weak-on-both rejections, 16/16 deterministic reruns.
- **An MCP server** (Streamable HTTP, one tool `find_common_ground`) at `src/lib/server/mcp.ts` + `src/app/api/mcp/route.ts`,
  replaying or running the same agent the website runs, with 5 passing tests.
- **A recording/replay layer** (`src/lib/agent/replay.ts`) so a judge's demo doesn't depend on a live model.
- 5 Qloo endpoints actually invoked (`/search` 45 refs, `/v2/insights` 12, `/v2/analysis/compare` 7, `/entities` 5,
  `/v2/tags` 4), Redis cache, zod-validated intake, rate limiting.

**Honest weaknesses:** **no CI workflow at all** (`.github/workflows` does not exist) — so the 186 tests I just ran
are the author's local habit, not a gate. The evaluation's raw outputs are git-ignored (`eval/out/`), so the 16-case
table is author-reported and I could not reproduce it. The seeds are hypothetical. An LLM sits in the main path, so
runs are less reproducible than a deterministic engine's.

**Scoring:** Tech 8.6 · Design 9.0 · Impact 7.8 · Idea 8.7 → **8.53**

The 9.0 for Design is the one score here I have grounds for beyond code: I viewed `docs/screenshots/02-highlights.png`
— editorial serif display type, a clean three-panel "why these, not the obvious pick / what Qloo added / what the
agent did" strip, and inline epistemic caveats printed *inside* the result ("activity fit is our interpretation;
venue access is unverified"; "relative ranks within the retrieved candidates, not the percentage of people who will
like it"). It is the best-looking thing in this field.

**Why `M17` was low:** I credited the ablation as "code exists" when it is actually *executed and published*, and I
counted 38 test files instead of 186 tests. Both errors ran the same direction.

**Head-to-head vs Adjacent:**

| | COMMON GROUND | Adjacent |
|---|---|---|
| Executed with/without-Qloo evidence | **yes, 16 live cases, published** | harness exists, LLM arm `BLOCKED` |
| Baseline visible in the product | **yes** | no |
| MCP / agent-consumable surface | **yes** | no |
| CI | **none** | ruff + 2 pytest markers + live probe + 8 node suites + 2 Docker builds |
| Test cases run in this sandbox | 186 | not runnable here (737 fns in CI) |
| Qloo endpoints invoked | 5 | 5 |
| Decision lifecycle after the recommendation | no | **yes** (Test Card → observations → evaluation) |
| Honesty surface | inline caveats, strong | `data_status`, no-silent-fallback, `FEATURES_NOT_BUILDING.md`, demo gates — **broader** |
| Domain | community/event programming | pre-release film positioning |

COMMON GROUND wins on the one thing judges weight hardest (demonstrated Qloo necessity) and on design. Adjacent wins
on engineering breadth and on the lifecycle. 8.5 vs 8.0 is a fair representation.

### 3.2 MOSAIC — `Abdullah-m7/qloo-mosaic` → **7.9**

**What it is:** "common ground by design" — a cultural negotiation agent for event promoters: discover across two
audiences, rank the *same* shortlist against each group independently, then choose a three-category combination
(artist + place + film-themed experience) that **maximises the lower of the two group ranks**.

**What I verified in code, this round:**

- **127 tests, 0 failures, in 2 seconds, with zero runtime dependencies** (`package.json` has empty `deps` and
  `devDeps`; it runs on Node's built-in test runner). For 2 293 product LOC that is a remarkable test-to-code ratio.
- **Methodological care that most of the field does not show:** `docs/LIVE_ABLATION_PROTOCOL.md` compares plans using
  *within-list ordinal-rank percentiles* rather than treating scores from separate Qloo calls as comparable; it
  publishes the one-sided and average-first baselines; it stress-tests by removing each category and re-solving with
  the same verified rankings; it names abstention as a first-class outcome.
- A **pre-registered ablation, frozen 2026-10-15 "before first credentialed API test"**, with a documented amendment
  after a pilot (typed category lookups), and an explicit statement: **"Status: Not yet executed with real Qloo
  responses. No empirical claim is made."**
- Results are **encrypted** (AES-256-GCM data key, RSA-OAEP-SHA256 wrapped, public key committed) so that a private
  research artefact can exist in CI without leaking metrics — with "never discard a scenario for an unfavourable
  outcome" written into the protocol.
- CI is not decorative: `qloo-event-smoke.yml` runs `npm test` **and** `npm audit --audit-level=high` **and** a
  credentialed live smoke. `render.yaml` + `Dockerfile` + `/health`, and a `judge:release-check` script.

**Honest weaknesses:** the **narrowest Qloo usage in the field** — 2 endpoints (`/search` 10 refs, `/v2/insights` 7),
no `/analysis/compare`, no tags, no trending, no entities-by-id. The evidence that *is* committed is a **500-case
synthetic** benchmark whose own disclaimer says it is *"not Qloo-derived evidence, nor a human preference or product
impact experiment"*. So the expensive part of the argument — does this help a real organiser — is unproven, and the
demo judges can click is explicitly synthetic.

**Scoring:** Tech 8.2 · Design 7.8 · Impact 7.3 · Idea 8.3 → **7.90**

**Why `M13_16` said 8.8:** it scored 9.0 on both Tech and Idea from `engine.mjs` plus a README. The engine deserves
that; the 9.0 on Tech does not survive contact with the fact that the Qloo surface is two endpoints and the
evaluation is unexecuted. My `M17` 7.4 over-corrected in the other direction — I had recorded "23 tests" when the
suite is 127 and passes in two seconds.

**Head-to-head vs Adjacent:** MOSAIC and Adjacent are the **same failure mode** — a rigorous evaluation protocol
that has never been run — and they should be scored as such. MOSAIC is more rigorous *about the protocol* (frozen,
amended in public, encrypted so it can't be quietly reshaped) and Adjacent is more rigorous *about the system*
(self-audited its own rubric twice, in `M13_12`/`M13_13`). MOSAIC is deterministic and dependency-free; Adjacent has
5× the product and 6× the tests. Adjacent ahead, 8.0 vs 7.9 — this gap is not meaningful.

### 3.3 Clash Control — `neric-joel/qloo-agentic-hackathon` → **8.5**

**What it is:** taste data used to **schedule** rather than to recommend — for a festival head of programming, rank
set-time clashes and test a legal move, then print a brief with a sign-off block.

This is the project my `M17` got most wrong (7.4), and the correction is substantial.

**What I verified, this round:**

- **2,307 frontend tests passing** across 88 files (16 skipped), plus **545 backend test functions** in 33 files
  that I could not execute (Python ≥3.12) and **28 Playwright e2e specs** covering `honesty.spec.ts`,
  `network-safety.spec.ts`, `print.spec.ts`, `reduced-motion.spec.ts`, `keyboard.spec.ts`, `layout.spec.ts`.
  There are e2e tests asserting that the product *does not* send a network request when it says it doesn't.
- **It publishes that its own pre-registered test failed.** `src/app/method/page.tsx:315-329`: *"The test we set
  before building failed. Taste overlap put 46.8 % of complained-about clashes in the 25 % highest-ranked clashes…
  6.8 points ahead of genre tags. The bar we wrote down before building was 60 % and 10 points… Popularity did better:
  another Qloo field, it reached 57.8 %."* And the figures are asserted in tests
  (`src/lib/method-figures.test.ts:298-306`, including `expect(taste.topQuarterPct).toBeLessThan(backtest.bar.topQuarterPct)`),
  so the failure cannot quietly be edited out. Measured AUC 0.634 with a CI of 0.517–0.755, genre 0.512, random 0.5.
  I am not aware of another project in this field — or many commercial products — that ships a self-refuting headline
  metric on the main method page.
- **Per-feature live gating with real limits and an honest health endpoint.** Three Qloo/LLM-touching features, each
  off by default, each with per-visitor-hour/day and global daily caps, plus a monthly `QLOO_QUOTA_FLOOR` below which
  it stops calling Qloo; `/api/health` reports what is currently on. README states exactly which caps were live on
  which date.
- **Recorded agent runs that replay offline**, each trace labelled *"Live when recorded, 20 Oct 2026; replayed now,
  nothing fetched"*, with the exact request (`GET /v2/analysis/compare` + request id) listed per run.
- **5 Qloo endpoints, used heavily in the right places:** `/search` 199 refs, `/v2/insights` 81,
  **`/v2/analysis/compare` 62**, `/v2/tags` 12, `/v2/trending` 8.
- Public demo + a literal "Judge in 60 seconds" scripted walkthrough + `/brief` printable one-pager + `/method`.

**Honest weaknesses:** it is **music festivals, not film** — same family of decision (taste-grounded programming
under constraints), different industry, so it competes for judges rather than for Adjacent's user. Its headline
method *lost* to a simpler Qloo field. And an LLM writes the run explanations, so runs are not fully deterministic.

**Scoring:** Tech 9.0 · Design 8.8 · Impact 7.8 · Idea 8.5 → **8.53**

Impact is held at 7.8 rather than higher precisely *because* the demonstrated result is a negative one: the specific
case for the audience is strong, but "does the solution actually address it, based on what's demonstrated" has to
absorb that its chosen signal underperformed popularity on its own benchmark.

**Why `M17` was wrong:** I recorded "150 test files, largest codebase", then scored Tech 8.0 and Design 7.0. I had not
run the suite, had not read the method page, and was penalising it for being a music product. Having run 2,307 tests
and read the failed-test disclosure, 8.5 is defensible and 7.4 is not.

**Head-to-head vs Adjacent:**

| | Clash Control | Adjacent |
|---|---|---|
| Test cases executed here | **2,307 (+545 unrun backend fns)** | not runnable here |
| e2e coverage incl. honesty/network/print/reduced-motion | **28 specs** | none |
| Publishes a failed pre-registered test | **yes, on the live method page** | no |
| Executed backtest vs baselines | **yes** | harness exists, arm `BLOCKED` |
| Uses `/v2/analysis/compare` | **62 references** | **declared, never called** |
| Decision lifecycle after the recommendation | no | **yes** |
| Recorded-run replay labelled live-vs-cached | **yes** | no (trace exists, no replay surface) |
| CI breadth | browser + ci + journey gate | **wider** (2 pytest markers, live probe, 2 Docker builds) |
| Domain | music festival scheduling | film pre-release positioning |

### 3.4 Taste-Matched Trailer — `yannabadie/taste-matched-trailer` → **7.5**

**What it is:** a cultural launch director for a book — Qloo-seeded reference books → a cross-domain graph (films &
visual aesthetic, soundtrack & composers, audience personas) → four trailer shots, with an editorial workbench that
lets the author choose between two edits, produce a sound-off adaptation, and export a decision that is
cryptographically bound to its parent.

**What I verified, this round:**

- 6 Python `unittest` tests pass; 4 editorial-workbench Node tests pass. One committed test cannot run outside the
  author's machine (hardcoded macOS path to a private recording).
- **The most granular honesty record in the field.** `EVALUATION_RESULTS.json` carries per-case fields such as
  `"actual_api_verified": false`, `"correction_validation": "Offline replay of the genuine physical responses under
  2.6.2; no new API call"`, `"response_rows_retained_privately": true`, and — remarkably —
  `"operator_confirmation": "Codex selected the canonical first novel from genuine candidates; this was not a click
  or approval by Yann"`. It discloses that an AI performed a step that a reader would assume a human performed.
  There are separate `PUBLIC-BROWSER-RECEPTION`, `PHYSICAL-COVERAGE-RECEPTION` and `JURY-RELIABILITY-RECEPTION`
  artefacts and `SOURCE-PINS.json`.
- A genuine derivability property: a sound-off derivative records its exact parent hash and the correction applied,
  and the parent's verdict is not rewritten.
- 3 Qloo endpoints (`/v2/insights` 16, `/search` 10, `/entities` 3+).

**Honest weaknesses:** it is a **single-work creative artefact** — one French novel, one trailer — delivered as static
HTML plus a Python agent plus a JS workbench, not a product with an operating surface. No CI. The audience (a
self-published author making one book trailer) is the narrowest in the sample and there is no evidence anyone wants
it. Qloo usage is shallow: seed books and a graph expansion, no comparison, no tag work.

**Scoring:** Tech 7.4 · Design 8.3 · Impact 6.2 · Idea 8.0 → **7.48**

**Why `M13_16` said 8.3:** it scored 9.0 Design and 9.0 Idea from tree presence and rendered assets, while explicitly
noting *"tree presence does not prove the claimed live behavior"*. The craft is real; the 9.0s assumed a product
that isn't there. My `M17` 6.9 was too harsh on Tech and Design. 7.5 is the honest landing point.

**Head-to-head vs Adjacent:** not really the same product. Taste-Matched is a *creative director* that produces an
artefact; Adjacent is a *decision system* that produces a falsifiable bet. Taste-Matched's evidence ledger is more
meticulous per case; Adjacent has a CI gate, a lifecycle and 40× the operating surface. 8.0 vs 7.5.

## 4. Revised combined table

Equal 25 % weights on the four official criteria, 1–10, my screening estimates. Not official scores; differences
≤ 0.5 are not meaningful.

| # | Project | Tech | Design | Impact | Idea | Mean | Was (`M13_16` / `M17`) |
|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | `zicheng-yu/clearrun` | 9.0 | 8.5 | 8.5 | 9.0 | **8.75** | — / 8.75 |
| 2 | `neric-joel/Clash Control` | 9.0 | 8.8 | 7.8 | 8.5 | **8.5** | 8.3 / 7.4 |
| 2 | `Dhamani-aryan/COMMON GROUND` | 8.6 | 9.0 | 7.8 | 8.7 | **8.5** | 8.8 / 8.1 |
| 2 | `longtt-marketing/taste-brief` *(not film)* | 9.0 | 8.0 | 8.5 | 8.5 | **8.5** | — / 8.5 |
| 5 | `shro-2002/territory` | 8.5 | 7.5 | 9.0 | 8.5 | **8.4** | — / 8.4 |
| 6 | `louji2308/Zorq` *(not film)* | 8.5 | 8.0 | 8.0 | 8.0 | **8.1** | — / 8.1 |
| **7** | **Adjacent (this repo)** | **8.5** | **7.5** | **8.0** | **8.0** | **8.0** | 7.1 / 8.0 |
| 8 | `Abdullah-m7/MOSAIC` | 8.2 | 7.8 | 7.3 | 8.3 | **7.9** | 8.8 / 7.4 |
| 9 | `msimakhov-star/will-it-land` | 7.5 | 8.0 | 7.0 | 8.5 | **7.75** | — / 7.75 |
| 10 | `G-Hostin/quiet-week` | 7.5 | 7.5 | 7.5 | 8.0 | **7.6** | — / 7.6 |
| 11 | `yannabadie/Taste-Matched Trailer` | 7.4 | 8.3 | 6.2 | 8.0 | **7.5** | 8.3 / 6.9 |
| 12 | `kevin9327/HyperCueStudio` | 6.0 | 7.5 | 7.0 | 7.5 | **7.0** | — / 7.0 |

**Film/cinema cluster:** clearrun 8.75 → territory 8.4 → **Adjacent 8.0** → will-it-land 7.75 → Taste-Matched 7.5 →
HyperCue 7.0. Adjacent is **3rd of 6**, unchanged from `M17`.
**Whole comparable shortlist:** Adjacent is **7th of 12**, down from the 4th–6th I reported yesterday.

## 5. Two corrections to my own `M17`

Both go against Adjacent. Stating them because the earlier document is in this repository and would otherwise
mislead.

### 5.1 Adjacent does not have the broadest Qloo surface — it has 5 of the 8 families it declares

`M17` claimed *"8 endpoint families — the broadest of any clone"*. That counted the declarations in
`app/qloo/params.py`, not calls. Of the seven `EP_*` constants:

| Endpoint | Declared | Called from `client.py` |
|---|---|---|
| `/search` | yes | **yes** |
| `/entities` | yes | **yes** |
| `/v2/insights` (incl. `filter.type=urn:heatmap`) | yes | **yes** |
| `/v2/tags` | yes | **yes** |
| `/v2/audiences` | yes | **yes** |
| `/v2/trending` | yes | **no** — spec only |
| `/v2/analysis/compare` | yes | **no** — spec only |

So Adjacent invokes **5** endpoints, exactly like COMMON GROUND and Clash Control, and it is the only one of the
three that leaves **`/v2/analysis/compare` unused** — the endpoint that returns symmetric pairwise affinity, which is
what all three competitors use to justify "these two entities belong together". Clash Control references it 62 times.
`app/agent/tools.py:24` even says *"Later milestones add tools (heatmap, programme bet, audiences, trends)"*, i.e. the
gap was known.

Corrected claim: **Adjacent's Qloo breadth is mid-field, tied at 5 endpoints, with a documented registry that makes
the two unbuilt ones cheap to add.**

### 5.2 Adjacent is not #1 on engineering proof

`M17` said *"Adjacent #1, narrowly over territory."* With execution evidence, that is wrong on test depth:

| Repo | Tests executed in this sandbox | Backend tests | e2e |
|---|---|---|---|
| Clash Control | **2,307 passing** (web) | 545 fns (unrun here) | **28 Playwright specs** |
| Adjacent (CI) | not runnable here | 737 fns | none |
| COMMON GROUND | 186 passing | — | none |
| MOSAIC | 127 passing | — | none |

Adjacent still has the **widest CI pipeline** in the field (ruff, two pytest markers, a live Qloo probe script, 8
frontend suites, Next build, `render.yaml` parse, two Docker builds) and the most test *functions*. It does not have
the most executed test *cases*, and it has **no browser tests at all** — Clash Control has 28, including ones that
assert the app makes no network request when it claims not to.

Corrected claim: **Adjacent has the broadest CI pipeline and the most offline test functions; Clash Control has the
deepest executed suite and the only meaningful e2e/honesty-browser layer.**

## 6. So what does this change about Adjacent's position?

Nothing structural, and that is worth saying plainly. Adjacent's three genuine deficits are the same three `M17`
named, and the four projects examined here sharpened rather than changed them:

1. **Executed proof of Qloo necessity.** COMMON GROUND publishes a 16-case live ablation with an LLM-only baseline
   visible in the product. Clash Control publishes a backtest *that failed its own bar*. territory publishes E6.
   clearrun ships backtests. Adjacent has a harness whose comparison arm says `BLOCKED`.
2. **A judge-operable product.** COMMON GROUND, Clash Control and Taste-Matched all publish a demo URL; Clash Control
   publishes a 60-second scripted path and 28 e2e specs. Adjacent has the public-demo guards built and no deployment.
3. **A machine-consumable surface.** COMMON GROUND ships an MCP server. Adjacent ships none.

And one new, cheap, concrete finding: **the two Qloo endpoints Adjacent already documents but never calls are the
two its closest rivals lean on.** `/v2/analysis/compare` is specified in `params.py` with its own `ParamSpec` entries
— wiring it into cohort ranking is a contained change, not a rewrite, and it would give Adjacent the pairwise
affinity story that COMMON GROUND, Clash Control and clearrun all tell.

### Ranked next actions, re-cut with this evidence

| # | Action | Why now | Cost |
|---|---|---|---|
| 1 | Deploy the public demo + 60-second judge path + 4–5 screenshots in the README | 3 of the 4 re-examined projects have this; Adjacent has none, and Design is its lowest verified score | guards already built; deployment only |
| 2 | Run `M13_11` Condition A with a real LLM key and publish the table — or, if no key, add a Qloo-off arm that runs offline today | every project that beat Adjacent has an executed counterfactual | harness written |
| 3 | Wire `/v2/analysis/compare` into cohort ranking | spec'd already; the one endpoint all three rivals use and Adjacent doesn't | contained |
| 4 | `bias.content_based` for unreleased films | still unclaimed by anyone except clearrun; uniquely valuable for a *pre-release* product | small |
| 5 | One-tool MCP server (`find_adjacent_cohorts`, `read_run`) | closes the surface COMMON GROUND already has | small |

## 7. Reproducing this review

```bash
mkdir -p /tmp/comp && cd /tmp/comp
for r in Dhamani-aryan/qloo-hackathon Abdullah-m7/qloo-mosaic \
         neric-joel/qloo-agentic-hackathon yannabadie/taste-matched-trailer; do
  git clone --depth 1 https://github.com/$r.git $(echo $r | tr '/' '_')
done

cd Dhamani-aryan_qloo-hackathon      && npm ci && npm test   # 186 passed
cd ../Abdullah-m7_qloo-mosaic        && npm test             # 127 passed (no install needed)
cd ../neric-joel_qloo-agentic-hackathon/web && npm ci && npm test   # 2307 passed, 16 skipped
cd ../../yannabadie_taste-matched-trailer && python3 -m unittest discover -s . -p "test_*.py"  # 6 OK
# known-failing on a clean clone (author's local path):
node --test runtime/test_recorded_cache.mjs
```

**Limitations.** Every score here is a screening estimate from cloned source plus, where stated, an executed test
run. No hosted demo of any competitor was opened — outbound access to their deploy domains fails in this sandbox, so
"has a live demo" always means "publishes a URL". No competitor's *evaluation* was reproduced: COMMON GROUND's raw
`eval/out/` is git-ignored, MOSAIC's ablation results are encrypted by design, Clash Control's backtest figures come
from its own committed data module, and Taste-Matched's reception artefacts are the author's own records. Adjacent's
Design score remains the least verified number in the table: this repository commits no screenshots and I have no
browser here.
