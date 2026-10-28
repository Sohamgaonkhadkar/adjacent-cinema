# Post-merge verification record — 28 October 2026

Scope: the code as merged into `main` at **`db9a59c`** ("Merge PR #21: evidence-first
Qloo improvements"). Everything below was executed in a sandbox checkout of that
commit. Nothing was run against the hosted Vercel deployment, the Render API, or
the live Qloo provider — the sandbox has no provider key and no outbound network
beyond GitHub and package registries.

## What is in this merge

| Area | Where | State |
|---|---|---|
| Audience Pulse (pre-registered poll on a saved experiment) | `backend/app/domain/pulse.py`, `pulse_repository.py`, `api/pulse_routes.py`, `frontend/lib/pulse.ts`, `components/nf/AudiencePulse.tsx`, `app/pulse/[token]/page.tsx` | Implemented, tested offline, opt-in per deployment |
| `/v2/analysis/compare` reader | `backend/app/domain/pairwise.py`, `comparables.py` | Wired, deliberately refuses every provider response value |
| Kendall tau-b / top-k overlap agreement | `backend/app/domain/agreement.py` | Reviewed; strict-order formula documented and tested |
| Qloo Impact Lab + "Why this result?" | `backend/app/domain/challenge.py`, `frontend/lib/challengeView.ts` | Implemented, tested offline |
| Comparables Audit | `backend/app/domain/comparables.py`, `components/nf/ComparablesAudit.tsx` | Implemented, tested offline |
| MCP server (three read-only tools) | `backend/app/mcp_server.py`, `docs/MCP_SERVER.md` | Implemented, stdio only, tested over the SDK's in-memory transport |

## Results observed in this sandbox

Backend, from the project directory (`pytest -m "not live"`):

```
927 passed, 1 skipped, 8 deselected
```

The 8 deselected tests are the live-provider tests. The 1 skip is
`test_live_contract.py:64`, skipped because `QLOO_API_KEY` is not available; the
MCP client test ran, because the `mcp` extra is installed here. A skip is not a
pass.

`ruff check .` (0.17.0, the CI pin) → `All checks passed!`

Targeted suites:

| File | Tests |
|---|---:|
| `backend/tests/test_audience_pulse.py` | 51 |
| `backend/tests/test_pairwise_comparison.py` | 24 |
| `backend/tests/test_impact_lab.py` | 11 |
| `backend/tests/test_comparables_audit.py` | 12 |
| `backend/tests/test_bounded_attribution.py` | 7 |
| `backend/tests/test_mcp_server.py` | 39 |

Frontend, from `frontend/`:

```
npx tsc --noEmit   → clean
npm run build      → succeeds; routes /, /cinema, /creator, /creator/sponsor,
                     ƒ /pulse/[token], ƒ Proxy (Middleware)
```

| Suite | Tests |
|---|---:|
| `test:recovery` | 3 |
| `test:layout` | 4 |
| `test:creator-ui` | 8 |
| `test:positioning` | 10 |
| `test:entity-display` | 3 |
| `test:contract` | 11 |
| `test:challenge` | 31 |
| `test:comparables` | 8 |
| `test:explainability` | 8 |
| `test:pulse` | 35 |
| `test:proxy` | 3 |
| `test:render` (after build) | 1 |

124 suite tests + 1 render test, 0 failures.

### Environment note (do not misread as a code result)

The sandbox interpreter is **Python 3.11.2**; the project requires 3.12 and
`backend/app/qloo/models.py` uses PEP 695 `class ToolResult[T]`. The suite was run
on a scratch copy with that one class translated to `class ToolResult(_Base,
Generic[T])` and nothing else changed. CI runs the unmodified source on 3.12.
Treat the 3.12 CI result as the authoritative one.

## The compare reader: what it does now

`read_metric()` returns `None` for **every** provider payload. Qloo's public
Analysis Compare reference documents request parameters but not response fields,
and no verified response sample exists in this repository. So:

* the call is still made (one per completed run, budgeted) and its `call_id` is
  recorded;
* the response is reported as `unsupported_response_shape` with the observed
  **key names only** — never values;
* no metric, direction, probability or interpretation sentence is produced;
* the Comparables Audit reports `no_readable_field` for the same reason, and a
  compare failure is reported as a failure class (`timeout`, `authentication`,
  `upstream`, …), never as evidence that two groups are unrelated.

A test (`test_plausible_metric_keys_are_all_refused_until_schema_is_verified`)
pins this: `overlap`, `similarity`, `correlation`, `affinity`, `distance`,
`difference` and `divergence` are all refused today. Changing that requires an
official response schema or a recorded provider sample, and the contract docs say
so.

## What this record does not establish

- **No live Qloo call was made.** No live compare response has ever been observed
  here; `model="descriptive"` acceptance and the real payload shape are
  unverified.
- **No hosted deployment was exercised.** Route availability on
  `adjacent-cinema.vercel.app` / `adjacent-cinema.onrender.com` is reported
  from earlier owner-run checks, not re-measured by this sandbox.
- **Audience Pulse has not been exercised end to end in a browser** against a
  live backend. Its routes, validation, dedupe, freezing and evaluation are
  covered by tests, including a legacy-database migration test, but no
  participant flow was walked through in a real browser.
- **No MCP client host was connected.** The server was driven over the SDK's
  in-memory transport only.
- **The `/2` nine-programme evaluation report does not exist.** The published
  `docs/verification/live_counterfactual_evaluation.{md,json}` remain the
  schema `/1` three-programme files, produced by a real run on 26 October 2026.
  Generating `/2` needs an authorised live key; it was not generated here and
  the `/1` files were not regenerated.

## Outstanding owner actions

1. **Rotate `QLOO_API_KEY`** in the Render secret store *and* in
   `.github/workflows/ci.yml`'s secret. Not done, not claimed.
2. **Generate the `/2` report** with an authorised key, running every
   prespecified programme (`PROGRAMMES` has 9 entries; `--limit` defaults to 3):
   `python research/scripts/live_counterfactual_evaluation.py --output-dir docs/verification --limit 9`
   This overwrites `live_counterfactual_evaluation.{md,json}` in place, so copy
   the `/1` files first if the published three-programme record must be kept.
3. **Browser checks** from `docs/NEXT_LIVE_CHECKLIST.md`: FilmSponsor guest
   Origin/cookie/CSRF flow, session isolation and expiry.
4. **Deployment flags**: confirm `ADJACENT_PULSE_SHARE_ENABLED` and the
   public-demo flags on Render match what the demo narrative claims. Poll
   creation requires the owner-mode experiment routes, which the public demo
   closes by design.
