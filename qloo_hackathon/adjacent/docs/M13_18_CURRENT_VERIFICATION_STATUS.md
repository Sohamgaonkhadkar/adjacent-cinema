# M13.18 — Current Verification Status

**Checkpoint:** 24 October 2026, PR head 9fbeeba6cf3bf38044513519800cb4e46d92ffb7, CI run #225. This records observed local and CI results; it does not certify the full deployed application flow, hosted acceptance, hackathon eligibility, or a submission.

## Changes included in this working tree

- Qloo Insights scoring optionally requests `feature.explainability` only for at most 12 unique candidates and when budget permits one possible fallback. Only an explicitly identified 400/422 rejection of this parameter at `/v2/insights` can trigger one request without it. Other errors are not retried by this fallback. Both provider-call IDs remain in trace; the operation note records the rejected ID; core scoring remains tied to the successful call; affected attributions are `unsupported`.
- Attribution serialization validates finite scores in [0,1], rejects booleans/malformed values/duplicate IDs, and in production limits returned attribution IDs to verified input seeds. It does not expose raw response payloads. API status distinguishes returned, missing, unsupported and not-requested states.
- Creator and Cinema Test Cards allow review/edit of comparison protocol, primary measure, decision prompt and observation window before export. Creator stores the exact fields in the saved snapshot and top-level observation window, then reads them on reopen; legacy snapshots continue to load without inventing missing design values. Cinema edits remain explicitly observational. Observation/decision prompts do not create invented thresholds or outcomes.
- Added a current public competitor scorecard, owner/live handoff, clarified the exact “Qloo 4after” eligibility text without interpreting it, and linked current notes from the root README.

## Results observed

| Area | Command / method | Result | Limits |
|---|---|---|---|
| Frontend clean install | `npm ci --no-audit --no-fund` | **Passed**, 80 packages added | Node/npm package-install result only. |
| Frontend typecheck | `npx tsc --noEmit` | **Passed** | Static typecheck; not browser interaction. |
| Frontend production build | `npm run build` | **Passed**; `/`, `/cinema`, `/creator`, and `/creator/sponsor` prerendered | Does not prove hosted deployment or runtime API availability. |
| Frontend Node suites | `test:recovery`, `test:layout`, `test:creator-ui`, `test:entity-display` | **16 passed, 0 failed** | Node tests/static checks; `test:layout` is not an automated real-browser interaction suite. |
| Production-render smoke | `npm run test:render` after build | **1 passed** | Checks production-rendered surfaces; not click-driven browser E2E. |
| Dependency audit | `npm audit --audit-level=high` | **0 vulnerabilities** | Scope is the frontend lockfile at this checkpoint. |
| Backend Ruff | `ruff check backend` | **Passed** | Static lint across backend. |
| Targeted backend format check | Ruff format check on cohorts/scoring/new tests | **Passed** | `creator_analysis.py` and `test_m13_9_creator_mode.py` have pre-existing format differences elsewhere; no broad reformat was applied. |
| Backend full suite, compatibility scratch | Python **3.11.2**, copied scratch tree with only existing `class ToolResult[T]` syntax translated to the equivalent `Generic[T]` form; `QLOO_API_KEY` unset | **745 passed, 9 skipped, 0 failed** | Includes the new attribution contract rejection cases and no-parameter fallback assertions. This is not a native Python 3.12 run. The 9 skips are live-provider checks, not passes. Scratch copy only; the checkout's Python 3.12 syntax is unchanged. |
| Local backend native collection | Python **3.11.2** on checkout | **Blocked at collection** | Existing PEP 695 ToolResult[T] syntax in backend/app/qloo/models.py requires Python 3.12. This local limitation is superseded for backend-suite verification by the native Python 3.12 CI result below. |
| Backend native CI (offline/fixture) | GitHub Actions CI run #225, Python **3.12.15**, pytest -m not-live selection | **746 passed, 8 deselected** | Unmodified source on the supported interpreter; live-marked tests run separately. |
| Direct live Qloo contract CI | Same CI run #225, pytest -m live -rs | **8 passed, 746 deselected** | Includes test_explainability_contract against the Qloo API. This verifies the direct endpoint contract, not the application's full Creator/Cinema path. |
| Application-level live Qloo path | Not run against the deployed backend | **Pending** | No full deployed Creator/Cinema run or runtime trace has been verified. |
| Hosted production / browser E2E | Not run | **Reserved / pending** | No production setting or deployment was touched. The repository blueprint/docs were inspected read-only. |

The compatibility-scratch result (745 passed, 9 skipped) is supplemental evidence and remains a Python 3.11 scratch run. The latest PR CI run (#225) did run the unmodified backend source with Python 3.12.15: 746 non-live tests passed, and a separate live-marked step passed 8 tests including the direct Qloo explainability response contract. This proves the endpoint contract was observed in CI, but not that the deployed application completes a live Creator/Cinema run through Render.

## Known remaining gates

1. Keep the native Python 3.12 CI suite green after any further backend edit; the latest PR head has 746 non-live tests passing and 8 live-marked Qloo contract tests passing.
2. Have ChatGPT/the authorized owner verify the integrated live Qloo path and hosted production/browser acceptance. The direct Qloo contract test passed in CI, but it does not establish deployed entity resolution, scoring, attribution serialization, fallback handling, or frontend rendering.
3. Ask the hackathon organizers in writing what the literal “Qloo 4after” means if project-history eligibility depends on it. No eligibility verdict is made.
4. Before a judge-facing live demo, verify the exact current frontend/backend deployment revisions, same-origin `/api` proxy, health mode, and FilmSponsor guest origin/cookie isolation without changing production configuration.
5. Keep the public competitor scorecard as a source-grounded screening estimate, not an official leaderboard or placement claim.

## Readiness verdict

**Ready for final deployment review, but NOT READY to certify hosted judge acceptance or hackathon eligibility.** Frontend checks passed; native Python 3.12 CI passed 746 non-live tests; 8 direct live Qloo contract tests also passed, including explainability. The integrated live application path, hosted/browser acceptance, and organizer clarification remain open. No production deployment is part of this verification.
