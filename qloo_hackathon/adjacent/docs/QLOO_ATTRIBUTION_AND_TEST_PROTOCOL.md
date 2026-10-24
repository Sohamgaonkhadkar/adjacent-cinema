# Qloo attribution and experiment protocol

This note documents two improvements to the evidence-to-decision path. Neither turns Qloo affinity into an audience forecast, and neither claims an experiment has been executed.

## Qloo per-seed explainability

Qloo documents `feature.explainability=true` for `/v2/insights`. For entity recommendations, the response may include `query.explainability.signal.interests.entities[]`, with an input `entity_id` and normalized attribution `score` for each seed. See [Qloo's Insights API Deep Dive](https://docs.qloo.com/reference/insights-api-deep-dive#query-params-feature.explainability). The project's earlier [live validation record](LIVE_QLOO_VALIDATION.md#10-explainability-validation) reports this response shape on its Qloo hackathon key; this change does not claim a fresh live request was performed.

The implementation requests explainability only in a scoring context containing at most **12** unique candidate entities. Broad expansion remains lean; larger contexts omit the optional field entirely. A narrowly scoped fallback retries once without the optional field only when Qloo returns HTTP 400/422 and its response explicitly identifies `feature.explainability` as unsupported or invalid. Authentication, rate-limit, timeout, server, unrelated validation and transport errors are not retried by this fallback. The rejected request and successful retry have separate trace rows; the operation note records the rejected call ID and the retry omits the field entirely, and the scoring result remains associated with the successful call. Production orchestration only requests explainability when there is budget for that one possible retry; otherwise it omits the optional field and records `not_requested_budget`.

When serializing members, Adjacent extracts only IDs from the verified seed list and finite numeric scores in 0–1. It rejects malformed entries, non-input IDs, non-numeric values, booleans, out-of-range values, and all copies of a duplicate ID (case-insensitively) rather than choosing by response order. It does not serialize the provider's raw response. The Creator interface resolves attribution IDs to verified seed names when available and shows the actual scoring call ID. The API marks each member's status as `returned`, `missing`, `unsupported`, `not_requested_limit` or `not_requested_budget`; missing or partial attribution is not a zero contribution.

Attribution is an explanation supplied by Qloo about recommendation contribution. It is **not causal evidence**, a statement that a seed caused an audience response, or proof that a viewer will like or attend anything. Qloo can omit lower-impact inputs; a missing entry must not be interpreted as no contribution.

## Test Cards are test plans, not results

Both Creator and Cinema Test Cards carry three additional experiment-design fields alongside the existing observation window:

- **Comparison protocol** — Creator proposes a randomized A/B split only if the publishing platform supports comparable assignment and exposure; otherwise the comparison is labeled exploratory. Cinema proposes a venue-owned observational baseline and explicitly warns against causal attribution.
- **Primary measure** — asks the operator to choose and record one real, sourceable outcome with its denominator, dates and collection method. Views, attendance, feedback and reach are kept distinct rather than collapsed into a synthetic score.
- **Decision rule** — requires the operator to set a practically meaningful threshold and observation window *before* seeing results. Adjacent invents neither a threshold nor a sample-size guarantee. Missing or non-comparable evidence remains inconclusive.

Creator and Cinema allow the operator to review and edit the comparison, measure, decision prompt and observation window before export. Creator saves those exact design fields in the immutable experiment snapshot and displays them when reopened; legacy snapshots show an explicit “not recorded” fallback for absent design fields and retain their older top-level observation window. Cinema exports edited guidance but does not create a saved experiment. The app does not run ad experiments, collect impressions, execute film releases, or verify creator-entered observations. It only provides a more specific plan for a human to run and assess.

## Verification

Offline regression coverage checks:

- Qloo attribution extraction, duplicate/invalid-score handling, response-contract serialization and raw-response non-leakage (`backend/tests/test_qloo_attribution.py`);
- bounded explainability selection, explicit unsupported/validation fallback, non-retry error cases and mock-HTTP trace linkage (`backend/tests/test_scoring_explainability_fallback.py`, `backend/tests/test_cohort_ranking_single_normalisation.py`);
- deterministic experiment prompts and save/read persistence (`backend/tests/test_m13_7_explainability.py`, `backend/tests/test_m13_9_creator_mode.py`);
- shared Creator/Cinema edit-state and exact export section behavior plus legacy snapshot parsing (`frontend/tests/creator-failure-panels.test.mjs`).

A live Qloo response should still be verified in the deployed judge-facing environment before describing per-seed attributions as available in that demo. Fixture runs may have no attribution metadata, by design.
