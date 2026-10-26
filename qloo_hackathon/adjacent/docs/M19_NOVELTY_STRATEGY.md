# M19 — How to reach the top: the one category nobody in this field occupies

**Date:** 25 October 2026
**Basis:** `M17` (270-repo census) + `M18` (executed suites, revised ranking: Adjacent 8.0, 7th of 12,
3rd of 6 film projects).
**Question:** what can Adjacent add that is genuinely *new*, so it stops being "a smaller score than clearrun" and
becomes the project a judge remembers?

---

## 1. The strategic read (why feature-adding loses)

I have now read the code of the twelve closest projects. Three of them are ahead of Adjacent and **none of them is
ahead on product surface**. clearrun is 8.6 k product LOC; territory is 4.8 k. Adjacent is 33 k with 737 tests,
two pytest markers, a live probe and two Docker builds per CI run. Adding *more product* makes that gap
**worse**, because every extra surface dilutes the one thing Adjacent is unmistakably best at.

So the trap is: "our agent is only one pass, let's make it adaptive", "they have MCP, let's have MCP", "they have 3
agents, let's have 5". Every one of those is a step into a fight the field has already decided — on size, and
against a smaller opponent with a cleaner story.

**The opening is not a feature. It is a category nobody has entered: evidential integrity for pre-release
decisions.** Every competitor answers *"what is adjacent?"* Adjacent can be the only product that answers:

> **Is the adjacency actually doing the work — and would this decision survive being wrong?**

That question is unanswerable by a bigger agent, cannot be faked, and is exactly where Adjacent's existing skills
(determinism, provenance, typed stop reasons, `data_status`, a Test Card that already carries a
`falsification_condition` and a `decision_rule`) are decisive rather than merely tidy. It also happens to convert
all three of the deficits `M17`/`M18` identified into *product surfaces* instead of documents — permanently, in every
run.

One-line pitch that this unlocks:

> *Other Qloo film projects show you an adjacency. Adjacent tells you whether the adjacency is doing the work, how
> fragile your decision is, and whether Qloo already knew how your film did.*

Nobody in this field can say that sentence today. After the four features below, only Adjacent can.

---

## 2. The four novel features

Each one: the novelty argument (what exactly no competitor does), why it is defensible, where it lands in this
codebase, effort, and the honest risk.

### N1 — Necessity Ledger: every run reports whether Qloo changed the answer

**What it is.** Each run computes a **second ranking with the Qloo-derived affinity signal withheld**, from evidence
already cached in the run (no extra API calls), and publishes the diff next to the recommendation:

> *With Qloo: cohort #1 = X. Without Qloo's affinity signal: cohort #1 = X as well.
> **Qloo did not change this decision** — the same answer is reachable from popularity and tag overlap alone.
> Ranked #2 and #3 did change.*

And when it does change the answer, it says so with the two rows side by side.

**Why this is genuinely new.** Every project in the field computes *one* aggregate ablation, in a document, some
time after the fact: territory's E6, COMMON GROUND's baseline panel, clearrun's backtests, Zorq's removal proof,
MOSAIC's frozen-but-unrun protocol. **None of them computes necessity per decision, inside the product, for the run
the judge is looking at.** And none of them is willing to print "Qloo did nothing here" — which is exactly why
printing it is credible. It also inverts the field's incentive: everyone claims Qloo changed everything; Adjacent
reports how often it changed nothing.

**Why it is defensible.** It requires a deterministic engine, cached evidence, and the discipline not to re-query.
That is Adjacent, and it is the opposite of an LLM-in-the-loop design. A rival copying it must first give up the
LLM in the product path.

**Where.** New `app/domain/necessity.py`; the ranker in `app/domain/scoring.py` already ranks from
`ScoringContext` per `filter.type`, so an "affinity-withheld" ordering is a second sort over the same
`CohortScore`s (evidence strength → popularity novelty → member count, skipping `mean_affinity`). State already
holds `candidates_by_domain`, `cohorts`, `ranking`, `ranked` — nothing new needs fetching. Surface on the contract,
`/run` response, and the Cinema result panel.

**Effort:** ~1 day including tests. **Risk:** low; fully offline-testable. **Deficit killed:** #1 (the `BLOCKED`
comparison arm).

### N2 — Stability Certificate: the flip point of your own decision

**What it is.** A leave-one-out analysis over the run's own evidence: for each of the filmmaker's comparables, and
for each member of the top cohort, remove it and re-rank from cache. The output is a certificate, not a score:

> *Top cohort: **holds** if any single comparable is dropped (3 of 3 leave-one-out rankings unchanged).
> **Flips** if "Comparable B" is dropped → cohort #2 becomes #1.
> Margin to the runner-up: 1 band (strong → moderate).*

**Why this is genuinely new.** Nothing in the field measures decision fragility. clearrun's backtests measure
*hindsight accuracy*; territory's E6 measures *rule compliance*; COMMON GROUND measures *discovery*; MOSAIC measures
*protocol compliance*. A filmmaker's real question — "if my second comp is wrong, does this whole plan change?" — is
answered by nobody. It is also the honest alternative to the forbidden thing (predicting demand): it says how
*robust* the decision is, never how many people will come.

**Why it is defensible.** It is only computable when the engine is deterministic and the evidence is retained —
i.e. it is the direct payoff of ADR-001's non-adaptive loop. The thing that makes Adjacent's agent look least
"agentic" is what makes this possible. That is a strong narrative inversion for the write-up.

**Where.** New `app/domain/stability.py`, consumed by `test_card.py` (a `stability` block beside
`falsification_condition`) and the Cinema result panel.

**Effort:** ~0.5–1 day. **Risk:** low. **Payoff:** gives judges a *number* that isn't a fake forecast, and it is
the cheapest "novel contribution" in the whole list.

### N3 — Contamination Guard: is your film already in the graph?

**What it is.** For the film being positioned, test whether Qloo's **behavioural** graph already contains it — and if
it does, declare the run *contaminated for pre-release purposes*, re-score with `bias.content_based=1`, and label
which view you are showing:

> *"Late Night Window" resolves to a Qloo entity with popularity and behavioural tags. That means part of this
> affinity reflects how the film has already landed, not pre-release cultural adjacency.
> **Pre-release view** (content-based) is shown; the behavioural view is available and labelled post-hoc.*

**Why this is genuinely new.** This is *the* correct technical criticism of every project in the field, including
this one: you cannot judge an unreleased film's cultural adjacency with a graph that already knows the release.
clearrun identified it and solves it *inside one backtest tab* for three historical films. Nobody makes it a
per-film diagnostic, nobody re-scores on demand, and nobody shows the user which view they are looking at.
For a product whose entire premise is **pre-release**, this is the difference between a demo and domain mastery.

**Why it is defensible (and the honest catch).** It depends on `bias.content_based`, which is not yet in
`app/qloo/params.py` (the registry documents `backfill.content_based.take`, a different parameter). It also behaves
unknown-ly on an unreleased entity — which is precisely why this repo's `ParamSpec` pattern with an `open_question`
and probe id is the right way to build it. **I cannot verify live behaviour without a key**, so it must ship as:
verified-offline logic, an explicit probe (`probe H`), and an unavailable state until the owner runs the probe.
That is honest and it is also *more* impressive than a claim.

**Where.** `ParamSpec` for `bias.content_based` in `app/qloo/params.py`; client method + mock in
`app/qloo/client.py` / `mock.py`; a `contamination` block on the run contract; badge in the result header.

**Effort:** ~1 day. **Risk:** medium (live semantics unverified). **Originality:** highest in the field.

### N4 — Comp Audit: prove or break the user's own assumptions

**What it is.** The filmmaker names comparable films. Adjacent checks each pair with
`/v2/analysis/compare` (`model=descriptive` and `model=predictive`) and reports which of the user's adjacencies
actually hold:

> *"Comparable A ↔ B: supported (both directions, descriptive + predictive). Comparable B ↔ C: **not supported**
> — you are reasoning from two films that share a title's audience only one way. Two of your four comparables
> carry the others."*

**Why this is genuinely new.** Every project in the field reads the user's input as given and validates its own
output. None audits the *input* with evidence. For an honesty-first product, telling the user their premise is weak
is the strongest possible demonstration of the value system — and it is unflattering in a way that cannot be faked.

**Why it is defensible.** `/v2/analysis/compare` returns symmetric pairwise support, which is exactly the right
primitive and is a *different* endpoint family from everything else Adjacent uses.

**Where.** `EP_COMPARE` is already declared with `a.signal.interests.entities`, `b.signal.interests.entities`,
`model` (`descriptive | predictive`) at `app/qloo/params.py:455-478`. Add a client method and a pre-flight step.
This also closes the `M18` §5.1 finding that compare is the endpoint all three of the closest rivals lean on and
Adjacent declares but never calls.

**Effort:** ~0.5 day + verification risk on compare semantics.

---

## 3. Ranked build order — and the one thing that must not be skipped

| # | Move | Novel? | Kills which deficit | Effort | Rank effect |
|---|---|---|---|---|---|
| **1** | **Deploy the public demo + 60-second judge path + 4–5 committed screenshots** | no — table stakes | #2 packaging | hours (guards already exist) | **largest single jump.** Design is Adjacent's lowest verified score and 8 of 11 rivals publish a URL |
| **2** | **N1 Necessity Ledger** | **yes** | #1 executed counterfactual | ~1 day | turns the `BLOCKED` arm into a per-run feature; nothing else in the field has it |
| **3** | **N2 Stability Certificate** | **yes** | #1 (second form) | ~1 day | the cheapest defensible novelty; gives a real number that isn't a forecast |
| **4** | **N3 Contamination Guard** | **yes, most** | #3 domain credibility | ~1 day | the memorable technical idea; names the flaw everyone else has |
| **5** | **N4 Comp Audit** (`/analysis/compare`) | partly | #3 endpoint gap | ~0.5 day | matches the pairwise story the leaders tell |
| 6 | Sealed receipt: SHA-256 + UTC timestamp over the canonical Test Card at save, and a "resolve" view that reports predicted-vs-realised as *within-provider agreement* | yes | lifecycle is unproven | ~0.5 day | makes the unique lifecycle auditable |
| 7 | `/v2/trending` shelf-life ("this adjacency is rising / decaying") | yes, for film | breadth claim corrected in `M18` | ~0.5 day + probe | nice-to-have; unverified params, must degrade honestly |
| 8 | One-tool MCP server (`find_adjacent_cohorts`, `read_run`) | no — parity | COMMON GROUND has it | ~0.5 day | closes a visible gap |

**If you build only two things: #1 and #2.** Deployment makes an 8.0 visible; the Necessity Ledger makes it
unignorable. #3 is the one a technical judge will remember a week later, and it is the one I would build third
because it carries live-verification risk that must be handled honestly rather than claimed.

**Sequencing note.** #2 and #3 are complements and should be described together in the submission as a single
claim: *"Adjacent reports the contribution of Qloo to each decision and the contribution of the film's own release
history to the evidence."* Two directions of contamination — one from the model, one from the data.

---

## 4. What this changes about the ranking

Rough arithmetic on the four official criteria (equal weights), from `M18`'s 8.0:

| Move | Tech | Design | Impact | Idea | Mean |
|---|---|---|---|---|---|
| today | 8.5 | 7.5 | 8.0 | 8.0 | **8.0** |
| + deploy & judge path | 8.5 | 8.8 | 8.4 | 8.0 | **8.4** |
| + N1 Necessity Ledger | 9.0 | 8.8 | 8.6 | 8.7 | **8.8** |
| + N2 Stability Certificate | 9.2 | 8.9 | 8.8 | 9.1 | **9.0** |
| + N3 Contamination Guard | 9.4 | 9.0 | 8.9 | 9.5 | **9.2** |

That would put Adjacent **first in the film cluster and first overall** in this sample, ahead of clearrun's 8.75 —
not by out-building anyone, but by being the only project whose central claim a judge cannot reduce to
"an adjacency list with a nicer UI". Treat these as directional, not promises: they assume the features land with
tests and honest unavailable states, and they assume Design is actually as good as the code implies, which I still
cannot verify without a browser.

---

## 5. The list I would refuse to build

Stated because each is a tempting way to *lose*:

- **An LLM in scoring or in ranking.** Kills the determinism that N1 and N2 depend on, and every number becomes
  unverifiable.
- **More agents / persona theatre.** clearrun's 4-tool agent and Clash Control's recorded runs already win that
  comparison; adding a fifth role adds surface, not credibility.
- **An adaptive loop as the headline.** Keep ADR-001. The one-pass loop is a *reliability argument* and, after N2,
  it is also the enabling condition for the stability analysis. If a widening step is added, it must be framed as
  a bounded re-expand with the trade-off on screen — never as "we fixed our agent".
- **Any demand, attendance, revenue or conversion number.** The field is full of these; the rubric says "based on
  what's demonstrated", and one invented forecast would undo N1–N4 at a stroke.
- **A tenth evaluation document.** Adjacent's evidence problem is not a shortage of documents (132 of them,
  twelve evaluation/benchmark ones) — it is that none of it is in the product or on the first screen.

---

## 6. The submission paragraph this writes for you

> Adjacent is a pre-release positioning tool for filmmakers that refuses to be impressive in the usual way. Every
> run reports whether Qloo's affinity data changed the recommendation at all (the Necessity Ledger), whether the
> decision survives losing any single one of the filmmaker's comparables (the Stability Certificate), and whether
> the film's own release history has already leaked into the graph that is supposed to be pre-release
> (the Contamination Guard). All three are deterministic, all three cite Qloo call ids, and all three can say
> "nothing changed here". The saved Test Card is hashed and timestamped, and later observations resolve against it
> as within-provider agreement — never as a forecast.

That is a project that cannot be beaten by making the agent bigger.

---

## 7. Immediate next step

Build **N1 + N2 together**, because they share the same substrate (`state.candidates_by_domain`, `cohorts`,
`ScoringContext`) and both are fully verifiable offline with the existing fixture provider and test suite — no Qloo
key required, no live claim made. They are the two features that convert the deficits `M17`/`M18` found into
surfaces, in ~2 days, with the repo's existing honesty contract intact.
