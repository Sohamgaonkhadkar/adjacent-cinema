# M21 — Where Adjacent ranks now, and the plan to reach #1

**Date:** 25 October 2026
**Supersedes the Adjacent row only:** `M18` §4. Rival scores are carried forward unchanged.
**Deadline recorded in `M13_16`:** 30 October 2026 — five days from this note. Verify before planning against it.

This note is my own screening estimate on the four official criteria at equal 25 % weights. **No judge has scored
Adjacent.** It updates one row because the deployment and live-provider evidence changed since `M18`, and it spends
the rest of the page on what would actually close the gap.

---

## 1. What changed since `M18` (all of it verified by execution, not by reading a report)

| Change | Evidence | Criterion it moves |
|---|---|---|
| A judge can now open the Nightfall UI and run it | Feature Preview serves the ported `cinema` route with the **Challenge** chapter and the relaxed IMDb copy; `/api/health` returns 200 through the same-origin rewrite | Design, Impact |
| The live path is proven end to end against the real provider | Preview API smoke: Cinema `POST /run` title/year-only → `completed`, all 5 items `VERIFIED`, `data_status=measured`, 18 Qloo calls, 7 ranked cohorts, challenge available; Creator → 22 calls; FilmSponsor discovery → measured | Tech, Impact |
| The Decision Challenge ships | `result["challenge"]` on every completed run — necessity counterfactual, leave-one-item-out stability, next checks, receipt | Idea |
| CI is green *including* the live-Qloo step | run `40181936875` / `40182168893`; backend step 8 "Live-Qloo tests" = `success`, not skipped | Tech |
| 783 backend tests, 7 frontend suites, ruff clean | re-run locally on `12bd2a7` | Tech |

What did **not** change: no committed screenshots, no browser pixel review, no executed *ablation* (a counterfactual
over a live run published as a table), `/v2/analysis/compare` still unwired, production still serving the pre-port UI.

---

## 2. Re-scored table

| # | Project | Tech | Design | Impact | Idea | Mean | Δ vs `M18` |
|---|---|---:|---:|---:|---:|---:|---|
| 1 | `zicheng-yu/clearrun` | 9.0 | 8.5 | 8.5 | 9.0 | **8.75** | — |
| 2 | `neric-joel/Clash Control` | 9.0 | 8.8 | 7.8 | 8.5 | **8.53** | — |
| 3 | `Dhamani-aryan/COMMON GROUND` | 8.6 | 9.0 | 7.8 | 8.7 | **8.53** | — |
| 4 | `longtt-marketing/taste-brief` *(not film)* | 9.0 | 8.0 | 8.5 | 8.5 | **8.50** | — |
| 5 | `shro-2002/territory` | 8.5 | 7.5 | 9.0 | 8.5 | **8.38** | — |
| **6** | **Adjacent** | **8.7** | **8.0** | **8.2** | **8.3** | **8.30** | **+0.30** |
| 7 | `louji2308/Zorq` *(not film)* | 8.5 | 8.0 | 8.0 | 8.0 | 8.13 | — |
| 8 | `Abdullah-m7/MOSAIC` | 8.2 | 7.8 | 7.3 | 8.3 | 7.90 | — |
| 9 | `msimakhov-star/will-it-land` | 7.5 | 8.0 | 7.0 | 8.5 | 7.75 | — |
| 10 | `G-Hostin/quiet-week` | 7.5 | 7.5 | 7.5 | 8.0 | 7.63 | — |
| 11 | `yannabadie/Taste-Matched Trailer` | 7.4 | 8.3 | 6.2 | 8.0 | 7.48 | — |
| 12 | `kevin9327/HyperCueStudio` | 6.0 | 7.5 | 7.0 | 7.5 | 7.00 | — |

**Position: 6th of 12** (was 7th). **Film/cinema cluster: 3rd of 6** — clearrun 8.75, territory 8.38, **Adjacent 8.30**,
will-it-land 7.75, Taste-Matched 7.48, HyperCue 7.00.

Why each Adjacent number moved, and what still caps it:

- **Tech 8.5 → 8.7.** The live pipeline is now observed working against the provider with verified identity
  resolution — that is worth more than any amount of readable code. Capped by: 5 of the 8 Qloo families the
  repository declares are actually called, `compare` is unwired, no ablation artefact.
- **Design 7.5 → 8.0.** The ported UI is reachable and operable by a stranger. **Capped hard by the absence of any
  visual evidence** — no screenshots in the repo, no browser check of the MapLibre canvas, no 60-second path.
  This is still the least-verified number in the table and carries the widest error bar.
- **Impact 8.0 → 8.2.** A judge can now get a real Qloo-backed answer in one sitting, in three workflows. Capped
  by: no quantified case study with an actual venue.
- **Idea 8.0 → 8.3.** The Decision Challenge is a genuinely distinctive idea — a recommendation that argues with
  itself. Capped by: the counterfactual is demonstrated on a fixture run where affinity-withheld changes nothing,
  so the most interesting claim ("here is what Qloo bought us") has not yet been *shown* on live data.

### The number that should drive the plan

The gap to #1 is **0.45**. My mean absolute error against the four judge scores I have (COMMON GROUND +0.3,
Clash Control −0.2, MOSAIC +0.9, Taste-Matched +0.8) is **0.55**, and my estimates run **0.45 low** on average.
So the gap to first place is **smaller than my own measurement error**. Bias-corrected, Adjacent is 8.30 + 0.45 =
**8.75**, level with clearrun.

Two readings, both true:

1. Adjacent is already **within noise of #1** on product and evidence; the remaining distance is not depth.
2. Because the distance is inside the noise, the plan must not be "write more code". It must be **remove the two
   things that still cause me to withhold points** (no visual proof; no executed counterfactual) and **eliminate
   the ways a judge could see a failure instead of the product**.

---

## 3. The point model

Every ++ on a criterion is worth a quarter of it in the mean, so a +0.8 on Design is worth +0.20 overall — more than
a +0.2 on all four criteria combined. Ranked by points per day of work:

| # | Move | Criterion | Ceiling if it lands | Δ mean | Effort | Who |
|---|---|---|---:|---:|---|---|
| P0 | **Remove the ways a judge sees a broken app** (production still on old UI; XFF quota bypass; cold-start 504; key rotation) | protects Design + Impact | avoids −0.5 to −1.5 | **insurance** | 3 h | me + owner |
| P1 | **Design proof pack**: 6–8 real screenshots (desktop + mobile), 60-second scripted judge path in README | Design 8.0 → 8.7 | 8.7 | **+0.18** | 4–6 h | owner captures, I write |
| P2 | **Publish a live necessity ablation**: run the counterfactual over 6–10 real programmes, table of production vs affinity-withheld vs popularity-only vs LLM-only | Idea 8.3 → 8.9, Impact 8.2 → 8.4 | 8.9 | **+0.20** | 1.5 d | me builds, owner supplies key |
| P3 | **Wire `/v2/analysis/compare` into ranking** (client method already exists at `app/qloo/client.py:617`; nothing calls it) and surface the pairwise result in the Challenge chapter | Tech 8.7 → 9.0, Idea → 9.1 | 9.0 | **+0.10** | 1 d | me |
| P4 | **One real venue case study**: 2–3 programmers, publish what the engine recommended and whether they agreed | Impact 8.4 → 9.0 | 9.0 | **+0.15** | 1 d | owner (relationships) |
| P5 | **MCP server** with `find_adjacent_cohorts` + `read_run` | Tech +0.1, Impact +0.1 | — | +0.05 | 1 d | me |
| P6 | Gap-closing copy: replace the inaccurate "no verified client implementation" claim once P3 lands; keep `docs/FRAMING.md` consistent | accuracy | — | 0 | 1 h | me |

Projected if P0–P4 all land: **Tech 9.0 · Design 8.7 · Impact 9.0 · Idea 9.1 → 8.95**, which is first in this table
with a margin (0.20) that is still smaller than my error bar — so the honest claim is "top two", not "won".

**Do not do**: an LLM in scoring or labels; an autonomous agent swarm; a fabricated ablation; a second scorer; an
invented ROI/attendance figure in the case study. Each of those would raise a number by making it false, and the
whole pitch is that Adjacent's numbers are not false.

---

## 4. Five-day schedule (25–30 October)

| Day | Work | Done when |
|---|---|---|
| **D0 — today** | P0: confirm which branch the **production** Vercel project deploys and fix it, or point the Devpost entry at a stable non-hashed domain. Rotate the Qloo key in Qloo, update the Render backend secret **and** the GitHub Actions secret (`ci.yml:16`). Decide the XFF trust model. | Production domain shows the new UI, or the submission URL is deliberate and opens without a login wall |
| **D1** | P3: add `compare` to the domain layer with mock-backed tests; surface the pairwise affinity row in the Decision Challenge; keep it honest when the provider is unavailable | tests green offline; feature reports "unavailable" without a key |
| **D2** | P2 part 1: build the ablation runner + table generator, offline-tested against the mock provider so the harness cannot invent numbers | a dry run on fixtures produces a table that is labelled fixture |
| **D3** | P2 part 2: owner runs the ablation live over the chosen programmes; I commit the resulting table **with its real call IDs** and its limits | every row traces to a `call_id`; failures stay visible as failures |
| **D4** | P1: owner captures screenshots; I write the 60-second judge path and wire both into `README.md`. P4 interviews if a programmer is available | a stranger can follow the README from cold to a live run |
| **D5** | Freeze. Full regression, CI, route checks, final verification pass in the PR. No new features. Submit. | CI green on the submitted SHA |

**If only one day remains**, do P1 — and only P1. Design is the lowest verified criterion, screenshot evidence is
what the two projects that beat Adjacent on Design actually ship, and it is the one item that cannot be argued into
existence by writing more code.

---

## 5. Verification gate per move

A move counts as done only when all of these are true; anything less stays in the "unverified" section of the PR.

- **P0**: the reporter URL a judge will use serves the ported UI and returns 200 on `/api/health` from a clean
  private window; the rotated key is confirmed by a live run *and* by CI's live step.
- **P1**: screenshots are committed, show the real deployed app, and are dated; the judge path names exact clicks
  and the expected labelled fixture/live state at each step.
- **P2**: the table states `data_status=measured` only where true, carries per-row provider call IDs, includes
  rows where the counterfactual changed nothing, and states the limits (affinity is a taste signal, not attendance).
- **P3**: the wiring is covered offline; with no key the UI says the comparison is unavailable rather than silently
  omitting it; the shipped copy matches what the code does.
- **P4**: the case study quotes the recommendation verbatim, withholds anything the venue did not agree to publish,
  and reports disagreement as well as agreement.

---

## 6. Honest summary

Adjacent's product depth, evidence discipline and test surface are top-three in this field. Its position is now
**6th of 12 overall and 3rd of 6 in film**, with a **0.45 gap to first that is smaller than my own 0.55 measurement
error**. It is not far from the top: it is *unproven* to the top, in two specific places — nobody has seen it, and
nobody has seen Qloo proved necessary on live data. Those two artefacts are the plan.
