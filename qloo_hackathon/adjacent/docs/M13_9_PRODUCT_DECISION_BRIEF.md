# M13.9 — Product Decision Brief: Creator Intelligence

Date: 2026-10-10 · Companion to `M13_9_CREATOR_INTELLIGENCE_RESEARCH.md` (citations live
there). This records the decision, the rejected alternatives, and the assumptions.

## Decision

**Segment: independent filmmakers and YouTube narrative-short creators (merged).**
We treat "indie filmmaker" and "YouTube short-film creator" as one segment because the
research shows their distribution paths converge: festival-accepted shorts end up on
YouTube/Vimeo, and the release playbook is the same (exposure > revenue; positioning and
packaging are the lever; "launch, engage, recalibrate — keep tabs on who's connecting").

**Product shape: an analysis → positioning hypothesis → saved experiment → observation →
evaluation loop, with provenance on every claim.**

## Why this beats the reviewed alternatives (differentiation)

| Tool | What it does | What it cannot do (verified absence in reviewed material) |
|---|---|---|
| vidIQ | YouTube SEO, AI credits, keyword/channel tooling | Cultural positioning of a *concept*; hypothesis lifecycle |
| TubeBuddy | Packaging A/B tests (Legend tier), bulk tools | Pre-release positioning hypotheses; evidence trails |
| Viewstats | Outlier detection, thumbnail history | Cross-domain cultural context; decision provenance |
| **Adjacent Creator Mode** | Cultural affinity cohorts → falsifiable Positioning Bet → Test Card → saved experiment with append-only observations and evaluations | — |

Two claims we deliberately do **not** make: (1) that cultural affinity predicts view
counts, retention, or revenue — affinity is a positioning hypothesis to be tested, never
a forecast; (2) that any market-size number justifies this segment — no reliable figure
was found, so none is asserted.

## Rejected alternatives

1. **Generic content recommender** — commoditised; no differentiation; violates the
   product's honesty invariants (would need fabricated engagement claims).
2. **YouTube SEO/packaging tool** — a direct fight with three funded incumbents on their
   home turf, with no use of the Qloo cross-domain asset.
3. **Letterboxd/TMDB-powered film graph** — Letterboxd API is private-beta (access not
   guaranteed); TMDB commercial use requires a signed agreement. Building on either would
   be a dependency risk with legal exposure.
4. **YouTube Analytics ingestion now** — feasible only via per-creator OAuth
   (`youtube.readonly` + `yt-analytics.readonly`; no service accounts; 10k quota/day).
   Deferred to a later milestone behind explicit opt-in; manual observation capture
   covers the MVP without credentials. (Boundary documented, not silently skipped.)
5. **OTT/studio enterprise UI now** — premature; documented as roadmap (below).

## Assumptions (stated, testable, not facts)

- A1: Short-film creators will state their references/themes honestly enough for the
  analysis to be useful. (The fixture demo makes the mechanic learnable.)
- A2: Creators will return to record observations. Mitigation: low-friction capture forms;
  partial/missing states are first-class so returning with incomplete data still works.
- A3: Qloo's cross-domain affinity is meaningfully different from YouTube-native signals.
  This is the core bet; it is *not* proven here — the experiment lifecycle exists
  precisely to accumulate the evidence that would prove or refute it.

## Model-readiness boundary (unchanged, deliberate)

Qualitative observations and experiment outcomes are **not** ML training labels. The
supervised readiness gate stays `NOT_READY` (M13.7: 2068 DB rows / 7.98% of 26,177
records) until real, consented, labelled data exists. The experiment ledger is evidence
infrastructure, not a label factory.

## OTT / Studio roadmap (documentation only — no enterprise UI built)

Positioning shift: the same engine, one tier up the value chain.
1. **Now (M13.9):** creator self-serve; local experiment ledger; fixture + live Qloo paths.
2. **Next:** per-creator OAuth YouTube Analytics ingestion (owner-authorized, read-only,
   least-privilege; explicit consent; no shared credentials) to replace manual observation
   capture; experiment cohorts for A/B packaging framed as hypotheses, not guarantees.
3. **Later (OTT/studio):** catalogue-level positioning analysis (a slate of titles vs.
   audience worlds), multi-stakeholder review workflows, and licensing-grade provenance
   exports. Requires: real licensed data agreements (TMDB-style written terms),
   authenticated Qloo usage, and an access-control layer the current open-local
   deployment does not have. None of this is claimed as built.

## What shipped this milestone

- `POST /creator/run` (live Qloo path, honest failure without a key) and
  `POST /creator/run/demo` (labelled fixture) — reuse the cinema pipeline, add `mode:
  "creator"`, `film` context, Positioning Bet, and Test Card.
- Experiment lifecycle: `POST/GET /experiments`, observations (OBSERVED/PARTIAL/MISSING/
  UNAVAILABLE/FAILED; zero ≠ missing; interpretation separate from metrics), evaluations
  (SUPPORTED/CONTRADICTED/INCONCLUSIVE) that supersede prior evaluations with full
  history, request-id idempotency everywhere, one saved decision per source run,
  snapshot-at-save provenance that later evidence cannot rewrite, persistence across
  restarts (SQLite at `data/processed/experiments.db`, gitignored).
- `/creator` frontend page (intake → analysis → bet → test card → save → observe →
  evaluate), linked from the cinema home nav. Cinema Mode is untouched and regression-tested.
