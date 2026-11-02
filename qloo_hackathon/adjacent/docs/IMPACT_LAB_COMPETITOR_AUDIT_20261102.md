# Adjacent Cinema — evidence-first competitive audit (2 November 2026)

**Scope.** Reviewed the main branch at `224d2212c2c416d26e5499558a49f3571a545acb`, the Decision Challenge ranking implementation, the 29 October nine-programme live report, the Impact Lab UI/receipt, frontend and backend regression tests, and selected public source files from the named competitor repositories. This is **not** a complete security audit, real-user study, browser walkthrough, or re-execution of live Qloo calls. Competitor README results are author-reported unless supported by inspected code. No official placement is inferred.

## Ten prioritized evidence gaps and product risks

| Priority | Finding | Evidence / verification status | Action |
| --- | --- | --- | --- |
| P0 | Qloo affinity does not distinguish the observed winners or rankings | The preserved 29 October report records 0/8 changed winners, mean tau-b 1.000 for affinity withholding, and 0 affinity-decided adjacent pairs. | Report this as a negative result and investigate genuinely different inputs under pre-registered protocols. |
| P0 | Popularity-sort differences were overstated as affinity effects | `backend/app/domain/challenge.py::_necessity_statement` and the frontend view previously credited the taste signal when only the popularity comparator changed. | **Fixed in this branch:** explicitly distinguish popularity from affinity. |
| P0 | Neither reported condition isolates Qloo versus no Qloo | `_necessity` keeps Qloo-discovered admitted candidates; both comparisons use provider-origin fields, including popularity. | **Clarified in API limits and UI.** An independent, feasibility-matched, non-Qloo discovery/control arm remains future work. |
| P1 | Decision changes are difficult to inspect candidate by candidate | Existing UI exposed winner, top-five overlap and tau-b, but not the actual candidate order despite the backend carrying all three. | **Fixed in this branch:** position-by-position top-five table, rendered only when all three orders describe exactly the same unique candidate pool. |
| P1 | Ranking counterfactual omits retrieval effects | The admitted cohort pool is frozen. Withholding Qloo signals cannot establish how an independent candidate discovery stage would behave. | Preserve this useful diagnostic, but label its scope and build a separate retrieval-level comparison later. |
| P1 | Affinity gate supplied no observed differentiating signal | Published nine-programme report shows 0 gate-suppressed cohorts across evaluable scenarios. | Investigate the gate's informativeness and data distribution, never adjust thresholds to manufacture winner flips. |
| P1 | No independent proof of programming success | Existing Test Cards are experimental plans; neither Qloo affinity nor popularity establishes attendance, conversion or filmmaker outcomes. | Run operator-owned prospectively registered tests with accessible outcome denominators before making impact claims. |
| P1 | Coverage failure is visible but unresolved | Regional-language scenario was not evaluable: 0/4 film seeds resolved. | Audit entity resolution and language coverage; maintain refusal rather than silently replacing films. |
| P2 | Scoring-context explainability is often omitted | Published report records `not_requested_limit` for scoring contexts whose candidate batches have 50 entities; optional bounded attribution is a separate pathway. | Improve selective inspectability and label provider attribution as descriptive, never causal. |
| P2 | Hosted workflow verification is still a separate gate | Source, prior CI and static review cannot confirm live Creator, Cinema and FilmSponsor journeys in the deployed browser or backend wake-up behavior at the time of judging. | Perform an independent first-time-user walkthrough, then record date, inputs, data provenance and failures. |

## Competitor practices inspected in source (not copied wholesale)

- **Local Edition**: `src/components/edition/evidence-drawer.tsx` co-locates an item, evidence IDs, Qloo context and guardrail results. Its `src/server/agent/guard.ts` distinguishes `unchecked` from `passed`, preventing automatic approval on guardrail outage. Relevant lesson: provenance and refusal belong beside each decision.
- **AYTO**: `src/pipeline/evidence.js` records stage-attributed Qloo calls with timings and provenance and streams each stage to the client. Relevant lesson: a reviewer should see what was requested, returned and used, not just a final prose insight.
- **Counterset**: `app/evidence.py` checks missing/duplicate/unrequested Qloo entities and refuses incomplete rows; `app/solver.py` separates explicit constraints from solver decisions. Relevant lesson: use precise validity checks and independent operational checks without turning Cinema Mode into a scheduling tool.
- **Read the Room**: its public implementation and README describe reference replacement with re-scoring and visible before/after evidence. Its reported outcomes have not been independently re-run for this audit. Relevant lesson: a change should be directly legible on the work being edited.
- **Cultural Fusion Lab**: `src/lib/agent/ablation/ablation.ts` reuses collected evidence in alternating control/evidence generations; its author openly reports `not_demonstrated` outcomes. Relevant lesson: only credit evidence when a defined operational decision changes, and accept negative outcomes.

## Design reasoning for this change

This branch does **not** change scoring weights, Qloo requests, deterministic state transitions, gated candidate sets or the product's final recommendation. Doing so in response to 0/8 sensitivity would contaminate the evaluation. Instead it changes:

1. Attribution wording to avoid crediting affinity for differences caused by a popularity-only sort.
2. Impact Lab view model: explicit run-level inference, fixed-pool scope, and strict same-pool rank order comparison.
3. User interface: visible comparison of the top five ranked candidates and a statement of what the comparison can *not* establish.
4. Decision receipt/Test Card export: the limitation travels with exported claims.
5. Backend/frontend regression tests guarding these statements and rejecting mismatched pools.

## Required next experiment — pre-register, do not cherry-pick

Test film positioning and cinema programming as **separate tasks**. For each fixed brief and programme, hold constraints and input context constant across conditions. Record: source-specific candidate coverage; identity of returned candidates; evidence eligibility; winner; complete ranking; top-k overlap; Kendall tau-b; tie / absence conditions; differences in operator actions; run seed and provider trace IDs. Classify each run as `detected`, `not_detected`, or `not_evaluable`, with explicit criteria defined before collection.

For the *independent non-Qloo* condition, acquire candidates through a separate documented discovery mechanism and evaluate only comparable decision criteria. It is not fair to rename the same Qloo candidate set as a no-Qloo baseline. Report coverage differences separately from ranking differences, avoid cross-context affinity comparisons, and independently validate candidate identity. Do **not** use simulated Qloo values as live evidence.

A different recommendation alone is not proof that it is better. The next external validation should have blinded programmer/editor preference or a venue-managed prospective measure with dates, denominators, constraints and a no-leakage protocol. `indeterminate` and `not_detected` outcomes remain first-class findings.

## Competitive assessment and five priorities

Relative to the specifically inspected peers, Adjacent's differentiator remains its joined **Creator → Cinema → FilmSponsor → Test Card** decision loop. This implementation patch increases the *honesty and inspectability* of Impact Lab; it **does not justify increasing any competition score**, claiming a top placement, or predicting judges' preferences. Existing dated scorecards are subjective and cover different shortlists.

Next steps ranked by actual decision value:

1. **Independent, pre-registered Qloo versus non-Qloo comparison** with legitimate candidate discovery for each arm.
2. **Record real operator decisions and feedback** on a narrow cinema/filmmaker use case, not invented commercial uplift.
3. **Fix coverage and explainability gaps**, especially non-English film resolution and selective evidence visibility.
4. **Make brand/programme/creator decision evidence inspectable and approvable end-to-end**, preserving provenance in every exported artifact.
5. **Validate full production journeys and cold-start behavior** with observable first-run failure states before submission.

## Limitations of this audit

Source inspection alone does not verify competitor demos, a clean local install, current deployment availability, or live Qloo authorization. The historical 29 October evaluation has **not been rerun** in this branch. Regression tests validate implementation behavior, not Qloo's commercial value. Any workflow not inspected end to end remains unverified rather than assumed broken or complete.
