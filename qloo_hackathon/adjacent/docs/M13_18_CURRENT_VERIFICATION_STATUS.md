# M13.18 — Current Verification Status

**Checkpoint:** 24 October 2026, current working branch. This records observed local results and their limits; it does not certify live Qloo, a hosted deployment, hackathon eligibility, or a submission.

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
| Backend native collection | Python **3.11.2** on checkout | **Blocked at collection** | Existing PEP 695 `class ToolResult[T]` in `backend/app/qloo/models.py` requires Python 3.12. No Python 3.12 interpreter is installed. |
| Live Qloo | Not run | **Reserved / pending** | No live provider claim; owner/ChatGPT handoff is in `M13_17_OWNER_DEMO_AND_LIVE_HANDOFF.md`. |
| Hosted production / browser E2E | Not run | **Reserved / pending** | No production setting or deployment was touched. The repository blueprint/docs were inspected read-only. |

The backend scratch result includes the new fallback/attribution tests and the existing full backend test tree. It is useful regression evidence, but does not replace the requested native Python 3.12 run. Python 3.12 installation through the earlier `uv` route was blocked by certificate/connectivity to the standalone runtime download. Do not report this as “Python 3.12 tests passed.”

## Known remaining gates

1. Run the unmodified backend suite under Python 3.12 in a supported CI/local environment; confirm that the nine live-provider skips remain understood.
2. Have ChatGPT/the authorized owner conduct the live Qloo test and hosted production/browser acceptance in the separate handoff. Do not make or imply this happened in this checkpoint.
3. Ask the hackathon organizers in writing what the literal “Qloo 4after” means if project-history eligibility depends on it. No eligibility verdict is made.
4. Before a judge-facing live demo, verify the exact current frontend/backend deployment revisions, same-origin `/api` proxy, health mode, and FilmSponsor guest origin/cookie isolation without changing production configuration.
5. Keep the public competitor scorecard as a source-grounded screening estimate, not an official leaderboard or placement claim.

## Readiness verdict

**NOT READY to certify live/hosted judge acceptance or hackathon eligibility.** The local frontend/build and offline backend evidence are strong enough for a clearly labelled fixture walkthrough, while native Python 3.12 backend execution, live Qloo, hosted/browser acceptance, and organizer clarification remain open. Publishing this review branch/PR is separate from production; no deployment or production change is part of this verification.
