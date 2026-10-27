# Pairwise comparison + bounded attribution — implementation record (27 Oct 2026)

Two capabilities were missing from the shipped product, and this change adds them
without touching the ranking arithmetic, the evidence gate, or the fixture path.

1. **Bounded per-seed attribution.** Every real run scored ~50 candidates per
   entity type. Above 12 candidates the optional `feature.explainability` field
   cannot be requested (documented limit), so `explainability_status` was
   `not_requested_limit` for every scoring context and **no live run could answer
   "which of my films drove this pick?"**. One extra call now covers the winning
   cohort's top 12 members.
2. **`/v2/analysis/compare` is wired.** The Decision Challenge could say two
   cohorts are within noise; it could not say whether they overlap. One bounded
   call compares the winner with the best **same-type** cohort, and every refusal
   (different types, no budget, unrecognised payload, provider failure) is
   reported as a value rather than an exception.

## What was executed (all offline, in this checkout)

Backend, `python -m pytest -m "not live"`:

```
809 passed, 1 skipped, 8 deselected
```

(baseline before this change: 783 passed, 1 skipped, 8 deselected — the 26 new
tests are `backend/tests/test_pairwise_comparison.py` and
`backend/tests/test_bounded_attribution.py`)

`python -m ruff check .` → `All checks passed!` (ruff 0.17.0, the version CI pins).

Frontend, `npm ci` then every documented suite plus `tsc` and a production build:

```
test:recovery 3 · test:layout 4 · test:creator-ui 8 · test:positioning 10
test:entity-display 3 · test:contract 11 · test:proxy 3 · test:challenge 22
test:render 1 (after npm run build)          → 65 passing, 0 failing
npx tsc --noEmit                             → clean
npm run build                                → 7/7 static pages, ƒ Proxy (Middleware)
```

The `test:challenge` suite grew from 16 to 22 tests (comparison row for a
measured payload, refusals, fixture "not modelled", failure tone, unknown
direction, absent payload).

CI: added an offline step
`python research/scripts/live_counterfactual_evaluation.py --self-test`
(exit 0 locally) so the verification-report renderer cannot regress unnoticed.

## Verified offline by test

* Attribution returns for a 20-candidate context through exactly one follow-up
  call; affinity/popularity stay those of the scoring call; a frozen
  `MemberEvidence` is replaced rather than mutated.
* No budget → `unavailable_budget` and **no** call. Inline attribution already
  requested → `not_needed` and **no** second call.
* Provider failure → `failed` + `error_type`, ranking untouched.
* A provider answer with no valid explainability block, or one naming an unknown
  seed → `missing`, `members_updated: 0`, and nothing inferred.
* Pairwise: recognised metric read by exact key with its direction; unrecognised
  payload → `unsupported_response_shape` with key **names** only (no values);
  non-finite / boolean / string values rejected; cross-type pair → `not_applicable`
  with no call; winner compared with the best same-type cohort and both ranks
  reported; groups truncated to 10 with `truncated: true`; budget refusal with no
  call; provider exception → `failed` with no exception escaping.
* The challenge's reader-facing sentence cites a measured comparison with both
  cohort ranks (so a rank-3 comparison is never described as the runner-up),
  and reports each refusal status verbatim.
* Fixture demo run (through `POST /run/demo`): `pairwise.status ==
  "not_modelled_in_fixture"` with a real `call_id`, `evidence.bounded_attribution`
  present, `challenge.pairwise` identical, and `qloo_attribution_origin` present
  on every member.

## Live CI evidence — what it does and does not prove

CI run **40553055265** (branch `arena/5e39c010-adjacent-cinema`) is green, and the
`Live-Qloo tests (only when QLOO_API_KEY secret is configured)` step ran and
passed. On that run the live Creator test asserted, against a real Qloo run:

* a ranked run reports a `pairwise` object whose `status` is one of the five
  documented values, that it carries `limits`, that an unmeasured comparison has
  `metric: null` and a reason, and that any claimed `call_id` appears in the
  run's own trace;
* `evidence.bounded_attribution` is present with a documented status, and a
  `returned` status comes with a traceable call id and `members_updated >= 1`;
* every ranked member carries `qloo_attribution_origin` in `{null, "scoring",
  "bounded"}`.

That is real plumbing evidence: the two new calls are made inside a live run, the
run still completes, and their outcomes are reported truthfully. It is **not**
evidence of *which* outcome occurred: the job logs are not retrievable from this
environment, so whether that run measured a comparison, refused one, or was
recorded as insufficient (in which case no comparison is claimed) is unknown
here. No live `compare` value has been observed, and none is claimed.

## NOT verified here — do not read this as working against Qloo

* **The compare response schema.** It is not modelled in this repository
  (`docs/API_NOTES.md` records request parameters only). The reader accepts seven
  field names and reports everything else as unreadable. What Qloo actually
  returns for this endpoint has **not** been observed.
* **`model="descriptive"`.** `model` is a verified parameter for the endpoint,
  but its accepted values were never probed. The live call has not been made.
* **Live bounded explainability.** The mock fixture carries no `explainability`
  block, so offline runs exercise only the `missing` / `not_needed` /
  `unavailable_budget` / `failed` branches. `returned` is covered by tests with a
  hand-built payload, not by a live response.
* **Budget behaviour against real latency/quotas.** The reservation rule is
  arithmetic (`>= 2` spare calls), not measured under a live quota.

Until a live run happens, a reader sees `metric: null` with an explicit reason.
That is the intended state: no number is better than an invented one.
