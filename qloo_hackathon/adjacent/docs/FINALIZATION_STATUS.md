# Finalization status — 19 October 2026

> **Historical document.** Everything below describes a 19 October 2026
> working branch (`arena/277f0f76-adjacent-cinema`) and PR #3, which did not
> reach `main` in that form. It is retained for reproduction history only. The
> code that shipped is `main` at `db9a59c`; current numbers, limits and owner
> actions are in [the post-merge verification record](verification_2026-10-28_post_merge.md).
> Do not read the branch names, commit SHAs or test counts below as current.

## Executive summary

Creator Mode is documented and remains the primary demo path; Cinema Mode is preserved. This sprint adds a narrow, opt-in public-demo boundary, tighter request/input limits, entity-mismatch regressions, more complete resolution-call provenance, a same-origin frontend API proxy, and refreshed operator/judge documentation. The anonymous demo is fixture-first; public live Creator requests require two owner-controlled opt-ins.

**Historical note (19 October 2026):** the original sandbox session used labelled fixtures and did not verify hosted deployment or a live Qloo request. That status was superseded by production checks on 26–27 October 2026: Vercel/Render are deployed, sampled Creator/Cinema requests returned measured Qloo traces, and a separate three-programme live counterfactual evaluation completed. See the current [developer verification status](M13_18_CURRENT_VERIFICATION_STATUS.md), [live-Qloo evaluation](verification/live_counterfactual_evaluation.md), and [current checklist](NEXT_LIVE_CHECKLIST.md). Do not treat the older sandbox results below as current hosted evidence.

## Repository, branch, PR, and CI

- Fixed working branch: `arena/277f0f76-adjacent-cinema`. The local branch was safely fast-forwarded from `68c138eb5fc96fea9dee0c7e72ba6d0d79bb0c17` to PR head `9e216d08df2c156a269d2b68e91ea181f31e2d8c`, preserving changes with a patch/archive and stash; the fuller Creator/EvidenceTrace versions were retained. Release commit `485e06a1a1b4bfba06dcb87f6f141be11f319150` was pushed normally to the same branch. The worktree is clean; no reset, rebase, force-push, or branch switch occurred.
- Existing PR: [#3 — Finalize creator evidence and experiment journey](https://github.com/Sohamgaonkhadkar/adjacent-cinema/pull/3), open and mergeable against `m13-work` (not `main`). `m13-work` is an ancestor of the feature branch. The default `main` still points at `68c138e` and does not contain the release changes. The preserved Creator frontend work is part of the PR branch.
- **Final release CI passed on `485e06a`:** push run [39213549744](https://github.com/Sohamgaonkhadkar/adjacent-cinema/actions/runs/39213549744) and PR run [39213554235](https://github.com/Sohamgaonkhadkar/adjacent-cinema/actions/runs/39213554235) both passed backend and frontend jobs. Backend used the workflow's native Python 3.12 setup; Ruff, the full fixture suite, and dry-run probe passed. The conditional Live-Qloo step was **skipped**, not passed. Frontend dependency install and production build passed. This validates the pushed release code.
- GitHub reported zero deployment records, no environments, and no listed release. No deployment URL, deployment manifest, or deployed commit was verified. Repository and root `LICENSE` metadata both report MIT.

## Local verification performed

| Check | Result | Scope / caveat |
|---|---|---|
| Ruff | **Passed** (`All checks passed!`) | Ruff 0.17.0 on a scratch copy of the current project. |
| Backend full suite | **631 passed, 8 skipped, 0 failed, 2 warnings** | Local interpreter is Python 3.11.2; the synchronized scratch copy uses one compatibility-only translation of `class ToolResult[T]` to `ToolResult(_Base, Generic[T])` in `app/qloo/models.py`. The checkout itself keeps the native Python 3.12 syntax. The eight skips are live-Qloo tests, not passes. Warnings: existing `TestCard` collection warning and Starlette/httpx deprecation from the installed latest packages. Separate CI on release commit `485e06a` passed using the workflow's unmodified Python 3.12 environment. |
| Resolver/public-demo regressions | **26 passed** | Includes Taipei Story/Purple Rose, explicit/conflicting IMDb ID, title/year and endpoint disagreement, Perfect Days unresolved, public route/body/rate/cache bounds, route-integrated process-local fixture quota, malformed requests, and canary redaction through run, trace, and SSE. |
| Experiment/idempotency/data semantics | **70 passed** | Lifecycle, adoption/provenance, outcome-ledger, and YouTube contracts; covers planned vs executed, immutable snapshots, retry/idempotency, append-only evaluation history, and zero vs missing/empty data. |
| Geography/affinity semantics | **21 passed** | Preserves numeric zero separately from absent affinity through Qloo entity/tag/heatmap parsing, API payloads, map ranking, and Cinema rendering; unscored cells are not ranked or displayed as zero. |
| Loading/failure/mock/Creator journey | **6 passed** | API-level SSE terminal flow, fixture Creator-to-PLANNED experiment journey, UNAVAILABLE observation with no fabricated metrics, INCONCLUSIVE evaluation, no-key live failure, agent insufficiency vs tool failure, and mock-mode health. |
| Frontend checks | **Passed** | `npm ci --no-audit --no-fund`, `npm run build`, and `npx tsc --noEmit`, Node 22.22.3 / npm 10.9.8 / Next.js 16.3.8. `/`, `/cinema`, and `/creator` prerendered. `frontend/package.json` has no lint script. No click-driven browser automation suite is configured. |
| Same-origin public preview smoke | **Passed earlier with fixtures; not running now** | Next on port 3000 proxied `/api` to the scratch API on port 8000 with public mode on, Qloo key absent, live opt-in off. All three pages returned 200; health reported fixture available/live unavailable; Creator fixture SSE returned `data_status="fixture"`; experiments and live Creator returned 403; docs/OpenAPI returned 404. Ports 3000/8000 are currently not listening. This was a sandbox preview, not hosted deployment or live-Qloo evidence. |

### Exact verification commands

Backend commands were run from `/tmp/adj-release-verify-20261019` after synchronizing the current checkout's `backend/`, `research/`, `scripts/`, and `pyproject.toml` into that scratch tree:

```bash
/tmp/adj-release-verify-venv-20261019/bin/ruff check .
env -u QLOO_API_KEY /tmp/adj-release-verify-venv-20261019/bin/python -m pytest -o addopts= -q

env -u QLOO_API_KEY /tmp/adj-release-verify-venv-20261019/bin/python -m pytest -o addopts= -q \
  backend/tests/test_m7_geography.py

env -u QLOO_API_KEY /tmp/adj-release-verify-venv-20261019/bin/python -m pytest -o addopts= -q \
  backend/tests/test_resolution.py::TestHistoricalEntityResolutionRegressions \
  backend/tests/test_public_demo.py

env -u QLOO_API_KEY /tmp/adj-release-verify-venv-20261019/bin/python -m pytest -o addopts= -q \
  backend/tests/test_m13_9_experiment_lifecycle.py \
  backend/tests/test_m13_14_adoption.py \
  backend/tests/test_m13_3_outcome_ledger.py \
  backend/tests/test_m13_10_youtube.py

env -u QLOO_API_KEY /tmp/adj-release-verify-venv-20261019/bin/python -m pytest -o addopts= -q \
  backend/tests/test_m13_9_creator_mode.py::TestCreatorFixtureDemo::test_demo_sse_streams_creator_events \
  backend/tests/test_m13_9_creator_mode.py::TestCreatorExperimentJourney::test_fixture_evidence_to_planned_experiment_observation_and_evaluation \
  backend/tests/test_m13_9_creator_mode.py::TestCreatorLiveRunHonesty::test_live_run_without_key_fails_honestly \
  backend/tests/test_agent_orchestration.py::test_insufficiency_stop_when_nothing_resolves \
  backend/tests/test_agent_orchestration.py::test_tool_failure_stops_as_error_not_insufficiency \
  backend/tests/test_client_contract.py::test_health_endpoint_reports_mock_mode_without_a_key
```

The full pytest command returned **631 passed, 8 skipped, 2 warnings**; the geography-affinity command returned **21 passed**; the resolver/public-demo command returned **26 passed**; the lifecycle/idempotency/data-semantics command returned **70 passed**; the loading/failure/mock/Creator journey command returned **6 passed**. The eight skips are the live-Qloo tests and are not counted as passes. Frontend commands, from `qloo_hackathon/adjacent/frontend`, were `npm ci --no-audit --no-fund`, `npm run build`, and `npx tsc --noEmit`.

The preview/API smoke check exercised the Next.js same-origin `/api` proxy and public allowlist with labelled fixture data. It did not exercise a live Qloo provider, persistent hosted service, or browser-driven UI automation.

## Environment constraints

- The local interpreter is Python 3.11.2; `python3.12` is absent. A temporary `uv` install was attempted, but its Python 3.12 standalone download failed at GitHub asset TLS/connection setup. No compatibility edit was made to the checkout; the local scratch copy has only the documented PEP 695 generic translation. The pushed release commit passed CI's unmodified Python 3.12 backend job.
- The checked shell has no `QLOO_API_KEY`; no live request was made. GitHub Actions secret-list access returned HTTP 403, so repository-secret presence could not be inspected. GitHub reported no deployment environments or deployments, and the repository contains no deployment manifest. No hosting access/URL is available through the checked configuration.
- Earlier startup `code 127` was because `uvicorn` was not installed/on `PATH` in the system interpreter. The earlier `code 1` `ModuleNotFoundError: app` came from launching Uvicorn outside the backend working directory; launching from `backend/` with the scratch venv worked. The earlier smoke-tested preview processes are no longer listening on 3000/8000.
- No frontend lint script is defined. The verified frontend gates were production build and `tsc --noEmit`, not ESLint.

## Changes made

- **Public boundary:** opt-in ASGI allowlist; byte ceilings; per-IP-observed and process-wide HTTP rate limits; in-flight request/SSE ceiling; separate live/fixture run quotas; temporary bounded run cache with expiry; disabled shared experiment, YouTube, synthesis, debug, and API-doc surfaces. Public run responses, SSE error events, and trace rows suppress raw exception/upstream detail while retaining safe status/call provenance. Live Creator requires `ADJACENT_PUBLIC_LIVE=1` plus backend `QLOO_API_KEY`.
- **Resolution/provenance:** title/year verification also applies to external-ID mappings; explicit conflicting IMDb IDs are `MISMATCH`; a title-search `MISMATCH` is not overridden by a separately verified external-ID result; both call references are retained.
- **Data semantics:** Qloo entity, tag, and heatmap parsing now distinguishes a valid affinity `0` from a missing affinity; geography ranking and Cinema visualization omit unscored cells rather than displaying missing data as zero.
- **Frontend:** browser client uses same-origin `/api`; Next.js has a configurable server-side rewrite via `ADJACENT_API_ORIGIN`; Creator inputs and public-mode affordances reflect server bounds and disabled shared writes; terminal SSE events close cleanly; failed partial output is explicitly labelled rather than presented as a completed result; trace links target the matching run-scoped trace row.
- **Docs/CI:** judge-facing root README; updated app/frontend guides, API contract, live checklist, deployment ADR, and historical-report warnings; CI now includes a frontend production build.

## Changed-file audit

Reviewed the exact tracked diff plus all untracked files; the release implementation spans 40 paths relative to the original local base commit (`68c138e`) and groups as follows:

- **Root/config/CI (4):** `.github/workflows/ci.yml` (frontend build job); `README.md` (new judge-facing overview); `qloo_hackathon/adjacent/.env.example` (documented opt-in settings); `qloo_hackathon/adjacent/README.md` (replaced stale milestone-era setup with current app guide).
- **Backend implementation (11):** `qloo_hackathon/adjacent/backend/app/public_demo.py` (new anonymous guard/limits/sanitizers); `backend/app/api/creator_routes.py` (bounded inputs, limiter/cache integration, sanitized failures); `backend/app/api/routes.py` (same for run APIs); `backend/app/api/store.py` (volatile run-cache pruning and accurate store docs); `backend/app/api/youtube_routes.py` (safe public disabled state); `backend/app/domain/geography.py` (zero/missing score distinction and honest ranking); `backend/app/live_runner.py` (related resolution-call IDs); `backend/app/main.py` (exact-origin CORS, guard, public health, current app description); `backend/app/qloo/models.py` (preserve numeric zero affinity); `backend/app/resolution/contract.py` (related call refs); `backend/app/resolution/resolver.py` (title/year/ID conflict policy and cross-endpoint trace refs).
- **Regression tests (4):** `backend/tests/test_m13_9_creator_mode.py` (fixture-to-planned experiment, observation, evaluation); `backend/tests/test_m7_geography.py` (zero vs missing affinity); `backend/tests/test_public_demo.py` (new boundary, limits, redaction/cache regressions); `backend/tests/test_resolution.py` (historical entity-resolution cases, including no MISMATCH override).
- **Product/deployment docs (10):** `docs/ARCHITECTURE_FREEZE.md`, `docs/FRONTEND_CONTRACT.md`, `docs/FINALIZATION_STATUS.md` (new), `docs/LIVE_DEMO_RUN.md`, `docs/LIVE_QLOO_VALIDATION.md` (fingerprint removed), `docs/M13_11_PRODUCT_ARCHITECTURE.md`, `docs/M13_14_DEPLOYMENT_READINESS.md`, `docs/M13_14_IMPLEMENTATION_AUDIT.md`, `docs/NEXT_LIVE_CHECKLIST.md`, and `docs/adr/006-deployment-topology.md` (stale deployment assertions marked historical/proposed).
- **Frontend (11):** `frontend/README.md`, `frontend/app/cinema/page.tsx` (avoid presenting missing heatmap scores as zero), `frontend/app/creator/page.tsx` (bounded intake, loading/failure/fixture states and experiment UI), `frontend/app/globals.css`, `frontend/app/page.tsx`, `frontend/components/AdjacencyGraph.tsx`, `frontend/components/EvidenceTrace.tsx` (trace display, redaction and links), `frontend/components/GeographyMap.tsx` (map only scored cells), `frontend/lib/api.ts` (same-origin client, nullable scores and terminal SSE close), `frontend/next.config.ts` (server-side proxy), and `frontend/types/adjacent.ts` (trace/health and nullable-score types).

Relative to the original base (`68c138e`), the 40 paths comprise 35 modified tracked files, one added tracked frontend file (`EvidenceTrace.tsx` from the PR head), and four untracked new root/backend/docs files. The PR head `9e216d0` already contains the other earlier frontend work; after the safe fast-forward, all of it remains preserved. No existing frontend work was discarded, no unrelated file was identified, and the root MIT `LICENSE` is unchanged. The credential-pattern scan found no matches, and `git diff --check` was clean before commit. The verified release code is committed and pushed on the fixed feature branch; the separate `/tmp/adj-release-backup-20261019/` patch/archive and Git stash preserve the pre-reconcile state.

## Security and operating limits

`ADJACENT_PUBLIC_DEMO=1` is an anonymous-demo allowlist, **not authentication**. The process-local request limits are 120 requests per API-observed peer IP/minute, 2,400 per process/minute, and 64 in-flight requests. Run limits are 2 live or 12 fixture runs per peer IP/hour, 12 live or 60 fixture runs per process/hour, and 2/4 active live/fixture runs. Fixture POST bodies are limited to 1 KiB; live Creator POST bodies to 16 KiB. Completed volatile run records are capped at 100 per process and expire after six hours when pruned.

Behind the same-origin proxy, the API may see all users as one peer IP; those users can share a bucket. These controls do not coordinate across workers/replicas and do not replace edge/API-gateway limits. Before public live use, configure a trusted edge limiter, document what run inputs are retained, and do not submit confidential or unreleased work. Shared experiments, YouTube credentials/analytics, and synthesis execution remain unavailable in public mode. Qloo credentials stay in the backend secret manager/environment; never expose them through the browser or paste them into chat.

## Remaining gates / next steps

1. **Current live Qloo path: sampled and verified.** On 26 October, the dedicated live workflow ran three programmes with measured Qloo data (3/3 evaluable). The report does not prove affinity is decisive: affinity-withheld ranking changed no winner, the popularity-only baseline changed all three, the affinity gate suppressed zero cohorts, and per-seed explainability was not requested for any of 11 scoring contexts because they each exceeded the 12-ID limit.
2. **Current deployment: live.** Vercel and Render deployments are healthy for the sampled checks. The four primary pages and proxied `/api/health` returned HTTP 200 on 27 October. This is not a full browser-driven security acceptance.
3. **Remaining hosted security gate:** run FilmSponsor guest flow in a normal browser and verify exact Origin, Secure/HttpOnly/SameSite cookies, CSRF, cross-session isolation, expiry/revocation, and privately confirm the trusted-proxy/shared-secret alignment. Never disclose or commit secret values.
4. **CI/merge status:** the current implementation is on `main`; the earlier PR #3 state below is historical and retained only as provenance. For current CI use [run #40394494087](https://github.com/Sohamgaonkhadkar/adjacent-cinema/actions/runs/40394494087).
5. **Eligibility:** the organizer interpretation of the phrase “Qloo 4after” remains unconfirmed; do not infer project eligibility without their written clarification.

## Historical evidence

`LIVE_QLOO_VALIDATION.md` is a 6 October snapshot, and `LIVE_DEMO_RUN.md` is an undated mixed-provenance artifact. Both are explicitly historical; neither is current-session acceptance. No interviews, judge feedback, user metrics, customer validation, or live deployment were conducted or inferred in this sprint.
