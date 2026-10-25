# ADR-007: Decision Challenge recomputes from the run's own cached evidence

## Status

ACCEPTED (implementation shipped on the feature branch, not merged to `main`)

## Date

25 October 2026

## Context

The product recommends a programme cohort from Qloo cultural-affinity evidence.
A recommendation a reader cannot interrogate is only marginally better than a
ranking they cannot see, so the run result now carries an optional
`result["challenge"]` section answering three questions:

1. **Necessity** — would this recommendation survive without the affinity
   signal at all?
2. **Stability** — does it survive losing one of its own evidence items?
3. **Next checks** — which specific evidence gaps are worth closing first?

The tempting implementation is a separate "challenge service" with its own
scoring, its own gate and its own ordering. That would have been faster to write
and would have produced a second source of truth that can disagree with the
recommendation it is describing — the exact failure mode this feature exists to
expose.

## Decision

`backend/app/domain/challenge.py` is a pure function over the finished run's
state (`build_decision_challenge(state) -> dict`), and it recomputes everything
with the **production** arithmetic:

- Cohort scores come from `app.domain.scoring.cohort_score_from` — the same
  function `CohortRanker` now calls, extracted for exactly this reason.
- Re-gating after a synthetic removal calls `app.evidence.evaluate_cohort`.
- Re-ordering calls `CohortRanker._order`, so ties break the same way the
  recommendation's ties broke.

Constraints, each enforced by a test:

- **No I/O, no Qloo calls, no LLM.** `qloo_calls_made` is asserted to be `0`.
  A challenge can never spend quota or turn a fixture run into a partly-live one.
- **Deterministic.** Two calls on the same state are byte-identical; no clocks,
  randomness or hash-order dependence.
- **No invented numbers.** There is no probability, confidence interval,
  likelihood or percentage anywhere in the payload or the frontend view
  (`frontend/lib/challengeView.ts`). Stability is a rule outcome printed next to
  the rule, and the frontend bans those words in the exported receipt.
- **A counterfactual is a diagnostic, not a claim.** "Affinity withheld changes
  nothing" is reported as unchanged; it is not reported as proof that the
  affinity evidence was uninformative. `limits` says this in the payload, in the
  section, and in the export.
- **Honest degradation.** `routes._build_challenge` wraps the call: if it raises,
  the run keeps its cohorts, test card and evidence, and the challenge degrades
  to `available: false` with an explicit reason and every computed section set to
  `null`. No partial invention. Covered by
  `tests/test_decision_challenge.py::test_a_broken_challenge_degrades_to_an_unavailable_record`
  and `::test_a_broken_challenge_does_not_invalidate_the_run`.

The affinity gate is deliberately **not** folded into the counterfactual pool.
The withheld-affinity counterfactual removes affinity-derived *ordering* keys; it
does not re-run admission, because doing so would change two things at once and
make the result unattributable. Admission effects are reported separately in
`challenge.gate` (`suppressed_by_affinity_gate`,
`admitted_without_structural_support`) instead of being smuggled into the
necessity delta.

## Deliberately not built

- **Contamination Guard (live).** The guard's job is to catch a run whose
  evidence was influenced by information the recommender should not have seen.
  The only honest version needs a real audience-outcome history to compare
  against, and this repository has no verified live outcome stream. Shipping it
  against fixture data would have produced a confident-looking check that cannot
  fail — worse than no check. Deferred until an outcome ledger has real
  observations.
- **`/v2/analysis/compare`.** Comparing two runs is attractive, but every
  comparison field would need a baseline the run does not currently carry
  (same city, same programme, same evidence window). Rather than accept
  incomparable inputs and present a difference as meaningful, the endpoint is
  deferred; the Decision Challenge answers the sharper question ("would this
  recommendation survive without this evidence?") from one run's own data.

## Consequences

- The challenge costs no provider calls, so it is safe to compute on every
  completed run, including the public fixture demo.
- Any future change to scoring, gating or ordering automatically changes the
  counterfactual too, because there is only one implementation. A test asserts
  the withheld-affinity order matches the production order when affinity is not
  decisive.
- The payload is additive and versioned (`schema:
  "adjacent.decision-challenge/1"`); older clients ignore it, and a failed
  computation cannot break a run.
