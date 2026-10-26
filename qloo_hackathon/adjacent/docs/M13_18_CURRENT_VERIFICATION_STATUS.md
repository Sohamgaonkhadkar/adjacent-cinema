# M13.18 — Current Verification Status

**Historical checkpoint:** 24 October 2026, feature branch `arena/76d901e7-adjacent-cinema`, commit `259ecf0`, GitHub Actions CI run `40106948750`. This document preserves that earlier review. The more recent hosted and live-Qloo verification is summarized below; these checks establish route availability and sampled runs, not a complete browser/security acceptance or hackathon eligibility verdict.

## Changes included in this working tree

- Qloo Insights scoring optionally requests `feature.explainability` only for at most 12 unique candidates and when budget permits one possible fallback. Only an explicitly identified 400/422 rejection of this parameter at `/v2/insights` can trigger one request without it. Other errors are not retried by this fallback. Both provider-call IDs remain in trace; the operation note records the rejected ID; core scoring remains tied to the successful call; affected attributions are `unsupported`.
- Attribution serialization validates finite scores in [0,1], rejects booleans/malformed values/duplicate IDs, and in production limits returned attribution IDs to verified input seeds. It does not expose raw response payloads. API status distinguishes returned, missing, unsupported and not-requested states.
- Creator and Cinema Test Cards allow review/edit of comparison protocol, primary measure, decision prompt and observation window before export. Creator stores the exact fields in the saved snapshot and top-level observation window, then reads them on reopen; legacy snapshots continue to load without inventing missing design values. Cinema edits remain explicitly observational. Observation/decision prompts do not create invented thresholds or outcomes.
- Added a current public competitor scorecard and clarified the exact “Qloo 4after” eligibility text without interpreting it. Current operational checks are maintained in `NEXT_LIVE_CHECKLIST.md` and `DEPLOYMENT.md`.

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
| Application-level live Qloo path | Sampled production Creator/Cinema runs (27 Oct 2026) | **Partially verified** | Sampled runs completed with `data_status="measured"` and inspected Qloo trace entries returned HTTP 200. This is not exhaustive coverage of every input/error path. |
| Hosted production route smoke | Vercel/Render production (27 Oct 2026) | **Passed, scoped** | `/`, `/creator`, `/cinema`, `/creator/sponsor` and proxied `/api/health` returned HTTP 200. This is not a browser-driven click-through or security audit. |
| FilmSponsor browser security E2E | Render logs show successful session/campaign/discovery requests; earlier origin mismatches also recorded | **Partially verified / browser gate remains** | Still needs a normal browser check of exact Origin, Secure/HttpOnly/SameSite cookies, CSRF, session isolation and expiry. |
| Public LLM synthesis | `/api/creator/synthesis-status` | **Intentionally unavailable** | `available=false`; optional synthesis is disabled in public-demo mode. Core deterministic Qloo analysis remains independent. |

The compatibility-scratch result (745 passed, 9 skipped) is supplemental evidence and remains a Python 3.11 scratch run. The latest PR CI run (#225) did run the unmodified backend source with Python 3.12.15: 746 non-live tests passed, and a separate live-marked step passed 8 tests including the direct Qloo explainability response contract. This proves the endpoint contract was observed in CI, but not that the deployed application completes a live Creator/Cinema run through Render.

## Cultural Multiverse / Positioning Arena follow-up (commit `259ecf0`)

- Added a deterministic Creator-side Positioning Arena based only on one completed run's ranked cohorts, verified source inputs, and trace. ANCHOR uses the existing ranking; BRIDGE requires returned shared tags or validated attribution to the same verified source film across distinct domains; FRONTIER requires another eligible cohort in the anchor's exact source scoring context with a higher existing novelty proxy. Unsupported strategies abstain. What-If uses within-context ordinal preferences and reorders only existing candidates; it makes no Qloo request and is not an audience prediction.
- Cohort serialization now exposes `context_id`, score `call_id`/`context_id`, and bounded member attribution/status details so the browser can audit provenance. These are additive response fields; no database migration was introduced.
- Creator save stores the selection, all alternatives, original Test Card, source IDs/status, policy/formula version/order and edited protocol/measure/decision/window under `source_bet.cultural_multiverse_snapshot`. Legacy snapshot-less experiments continue to load; observations/evaluations remain append-only.
- Local frontend verification on the committed source: existing Node suites plus Positioning Arena **26 passed, 0 failed**; `npx tsc --noEmit`, production build, and production-render smoke (**1 passed**) all passed.
- Local backend verification used a temporary Python 3.11.2 scratch copy with only the existing Python 3.12 `ToolResult[T]` syntax translated to `Generic[T]`: focused creator/experiment/attribution/run API tests **50 passed**; full non-live suite **746 passed, 1 skipped, 8 deselected**; Ruff passed. Do not treat that scratch result as a native runtime check.
- GitHub Actions CI run `40106948750` for commit `259ecf0` completed successfully: Python 3.12 backend, frontend (including new strategy test/build/render steps), and container build jobs all green. The conditional live-Qloo step is reported successful; it does not establish a hosted Creator run. The detailed remote log download was unavailable at verification time, so no live-test count is recorded here.
- Hosted production was subsequently verified read-only on 27 October 2026: Vercel served the primary routes with HTTP 200, `/api/health` reported the expected public-demo flags, and sampled Creator/Cinema runs completed with measured Qloo traces. This supersedes the older blocked-hosted wording in the historical notes below. Full browser-driven FilmSponsor Origin/cookie/CSRF/isolation testing is still pending.

## Known remaining gates

1. Keep the native Python 3.12 CI suite green after further backend edits. As of 27 October 2026, the post-merge CI run for commit `4346a5c` passed backend, frontend, and container-build jobs; see [run #40394494087](https://github.com/Sohamgaonkhadkar/adjacent-cinema/actions/runs/40394494087).
2. Finish a normal-browser FilmSponsor guest acceptance check: exact frontend Origin, Secure/HttpOnly/SameSite cookies, CSRF header, second-session isolation, revocation and expiry. Do not loosen production security settings to make the test pass.
3. Privately verify trusted-proxy/shared-secret alignment and external rate-limit/monitoring posture before increasing anonymous live usage. Do not expose or change secret values without an explicit, authorized operator action.
4. Ask hackathon organizers in writing what the literal “Qloo 4after” phrase means if project-history eligibility depends on it. No eligibility verdict is made from the available wording.
5. Keep the public competitor scorecard as a source-grounded screening estimate, not an official leaderboard or placement claim.
6. Optional per-seed explainability was not requested in 11/11 scoring contexts in the current live evaluation because each contained 50 IDs, above the 12-ID bound. If per-seed attribution is important to the judging story, evaluate a bounded run with at most 12 unique candidates per scoring context; report missing/unsupported attribution honestly.

## Readiness verdict

**The current code is deployed and CI-green; full browser/security acceptance and hackathon eligibility are not certified.** The current production route smoke passed and sampled Creator/Cinema runs returned measured Qloo evidence. Remaining work is narrowed to the FilmSponsor browser security contract, private proxy/secret alignment review, optional bounded per-seed attribution analysis, and written organizer clarification of “Qloo 4after.”
