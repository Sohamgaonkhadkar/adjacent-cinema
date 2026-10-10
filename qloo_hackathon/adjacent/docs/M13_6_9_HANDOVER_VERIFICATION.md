# M13.6.9 — Arena Handover Audit, Integration and Verification

**Date:** 2026-10-10
**Repository:** `Sohamgaonkhadkar/adjacent-cinema`
**Branch:** `arena/6462c00a-adjacent-cinema`
**Base HEAD at handover:** `ee7363e` ("Initial commit" — the only commit in the connected repository)

This document separates **reproduced facts** (verified in this session against the
connected Git repository and the running application) from **historical claims**
(previous milestone transcripts that could not be confirmed from Git).

---

## 1. Git state at handover (reproduced)

* Remote: `https://github.com/Sohamgaonkhadkar/adjacent-cinema.git`.
* The connected history contains **one squashed commit** (`ee7363e Initial commit`).
* The commits quoted in the previous transcript — `c22c9b6` (M13.6.7), `507af2b`
  and `8a31178` (M13.6.8) — **do not exist in this repository** (`git cat-file -t`
  returns "Not a valid object name" for each). All M13.6.7/M13.6.8 claims were
  therefore treated as unverified and re-checked against the code itself.
* Google Drive was not accessed at any point; the in-repo reference frontend at
  `correct_frontend_source/Qloo/` and the task file in `uploads/` were the only
  external-workspace materials used.

## 2. What the code actually contained at handover (reproduced)

Verified as **present** (matching M13.6.8 claims):

* Frontend API base defaults to `/api` and `createRun` posts to `${API_BASE}/run`
  (`frontend/lib/api.ts`); `next.config.ts` rewrites `/api/:path*` → `localhost:8000`.
* Backend result payload propagates `data_status` (`_build_result` in
  `backend/app/api/routes.py`).
* Collector re-collection after empty snapshots
  (`research/scripts/m13_6_3_feature_capture.py` — empty snapshots do not block
  re-collection) and the M13.6.4 regression tests
  (`backend/tests/test_m13_6_4_signal_integrity.py`).
* Test Card contract uses `audience_hypothesis` (`backend/app/domain/test_card.py`).
* Mobile hamburger + dropdown navigation (page.tsx header + `globals.css` media query).
* Signal-integrity domain layer intact: `qloo_signal.py` classification
  (CULTURAL_SIGNAL / POPULARITY_ONLY / IDENTITY_ONLY / EMPTY_SNAPSHOT /
  INVALID_SIGNAL_SCHEMA), UTC-normalized timestamps, cutoff-safe
  `latest_feature`, `freeze_due_predictions` and `build_analytical_benchmark`
  both selecting via `get_latest_usable_qloo_feature(..., cultural_only=True)`.

Verified as **NOT done** (the three unfinished M13.6.8 items — all confirmed in code):

1. `frontend/components/IntakeForm.tsx` existed but was **not imported anywhere**;
   `app/page.tsx` hardcoded `city: "London, UK"`, `venue_name: "Prince Charles
   Cinema"` and five sample films in `handleAnalyse`, and the hero said
   "A DEMO FOR Prince Charles Cinema" regardless of user input.
2. The OPPORTUNITY section still rendered **fabricated static bars**
   (92/80/72/63/57 % "expressed", 86/78/69/62/55 % "adjacent").
3. No browser-based verification evidence existed in the repository.

Additional claim from the transcript that did **not** match the code:
"ranked cohorts added to the Cultural Field display" — the page displayed taste
tags but **no ranked cohorts at all**. Now implemented.

## 3. Root causes found and fixed in this session

| # | Defect (reproduced) | Fix |
|---|---|---|
| 1 | `IntakeForm.tsx` disconnected; hardcoded London/PCC submission | Real intake integrated into `app/page.tsx` (section 02): venue, city, multiple removable film rows with optional year/IMDb ID, explicit "Load sample programme" demo action, inline validation, duplicate-submit guard, entries preserved after errors, re-run support. The submitted values are exactly what is POSTed (verified through the proxy). |
| 2 | Fabricated territory percentages | Removed. Section 04 now derives both columns from the current backend result: top-5 taste tags (Qloo affinity 0–1) vs top-5 ranked cohorts (mean member affinity), with an explicit disclaimer that affinity is not audience size/attendance/conversion, plus honest empty and insufficiency states. No illustrative numbers remain in the results path. |
| 3 | `build_programme_bet` hardcoded `data_status="measured"` | Added a `data_status` parameter; the run's real status (`state.data_status`) is passed through, so fixture bets can never be badged "MEASURED QLOO". `build_test_card` inherits it. |
| 4 | `build_geography_result` hardcoded `data_status="measured"` | Now derived from the Qloo response's own `data_status` (validated against the known vocabulary). |
| 5 | No keyless, explicitly labelled demo path through the product API | New `POST /run/demo` runs the fixture spine + geography/bet/test-card through the same code path as `/run`, labelled `fixture` at every level. The frontend exposes it only as an explicit, labelled button. Live failure never falls back to it. |
| 6 | CI workflow pointed at `working-directory: adjacent` (nonexistent in this repo layout) | Corrected to `qloo_hackathon/adjacent`. |
| 7 | Frontend contract drift: `AdjacentRunResult` lacked `data_status`; `GeographyData.cells` typed required although the backend sends only `highest_affinity_cells`; bet/test-card nullability wrong | `frontend/types/adjacent.ts` aligned with the actual payload; `as any` casts removed from the page (typed end-to-end). |
| 8 | Unused fabricated payload `DEMO_RESULT` (~150 lines of invented "live-looking" result data) and `PRINCE_CHARLES_CINEMA` sat in `lib/api.ts` | Removed, so fabricated results cannot leak into the UI. The kept `DEMO_PROGRAMME` is input-only and explicitly labelled. |

## 4. Verification evidence (all reproduced on 2026-10-10)

### Backend tests
* Full suite (`pytest -m "not live"`): **455 passed, 1 skipped, 7 deselected**.
  The 8 skipped/deselected tests are the live-network tests requiring
  `QLOO_API_KEY` (`test_live_contract.py`, `test_resolution.py`) — no key exists
  in this workspace (verified: no `.env` anywhere; `.env` is gitignored and none
  is tracked).
* Interpreter caveat: the sandbox only provides Python 3.11 while the project
  requires ≥3.12 (`class ToolResult[T]` PEP 695 syntax in
  `backend/app/qloo/models.py`). Python 3.12 binaries are not downloadable here
  (GitHub release-asset hosts are blocked). The suite was therefore executed on
  an unmodified copy of the tree in `/tmp/adj-py311` with a **single,
  semantically identical desugar** of that one class
  (`class ToolResult(_Base, Generic[T])`, the PEP 695 equivalent); `diff`
  confirms no other difference. The committed source keeps the original 3.12
  syntax.
* New tests added: `backend/tests/test_run_api_golden_path.py` (8 tests) —
  honest no-key failure, verbatim programme echo, 422 on empty programme, 404,
  fixture demo completeness + fixture labelling at every level, SSE replay +
  terminal `done`, trace provenance, health mode.

### Lint
* `ruff check` on all files changed in this session: **clean** (0 findings, ruff 0.9.10 and 0.17.0).
* Repo-wide, the tree has **pre-existing lint debt** (≈1.5k findings under any
  ruff ≥0.9 — mostly `W293`/`F541`/`UP017` in research scripts; ~90 in
  `backend/app`). This predates this session and was not mass-fixed here to
  avoid churning research code.

### Frontend
* `npm ci` + `next build` (Next.js 16.3.8, Turbopack): **compiled successfully,
  TypeScript check passed**, static pages generated.

### Golden path through the Next.js proxy (browser-equivalent origin)
* `GET /api/health` → 200 `{"status":"ok","qloo_configured":false,"mode":"mock"}`.
* `POST /api/run` with a custom payload (Lisbon / Cinema Ideal / 3 custom titles)
  → 200, values echoed verbatim; run then fails with
  `"QLOO_API_KEY not configured"` and `result: null` — no silent mock fallback.
* `GET /api/run/{id}/stream` for that run → `trace` then terminal `error` event.
* `POST /api/run/demo` → completed: 8/8 resolved, 8 taste tags, 6 ranked cohorts
  (2 rejected), 24 geography cells, Programme Bet + Test Card with
  `audience_hypothesis`, **every artefact `data_status: "fixture"`**, 13 mock
  Qloo calls in evidence.
* SSE for the demo run → 15 replayed events (`trace`×3, `resolution`,
  `taste_dna`, `cohort`×6, `heatmap`, `bet`, `test_card`) ending in `done`.
* `GET /` → HTTP 200; the served HTML contains the integrated intake form
  ("intake-card", "Load sample programme", "Analyse programme with Qloo").
* Captured evidence files: `docs/verification_2026-10-10/` (SSR HTML, SSE
  capture, demo result JSON, error-path notes).

### Browser screenshots — blocked, stated plainly
No browser binary (chromium/firefox/playwright/puppeteer cache) exists in this
sandbox and their download hosts are not reachable, so pixel screenshots could
not be captured. The equivalent evidence provided instead: served SSR HTML,
full HTTP/SSE transcripts through the proxy, and the live preview URL, which
renders the same production bundle (`next start`) verified above.

## 5. Fresh database audit (read-only copy of the tracked ledger)

Run on 2026-10-10 against `data/processed/outcome_ledger.db` (copy audited; the
tracked file was not modified):

* 763 observations · 4,667 snapshots · 337 unique films · 1 venue ·
  resolution 231/763 observations (30.3%) · sold-out rate 27/763 (3.54%).
* Predictions: 2,175 snapshots — PLANNED 2,068 / FROZEN 90 / OUTCOME_FINAL 11 /
  CENSORED 6. Outcomes: 2,158 PENDING, 11 `SOLD_OUT_OBSERVED`,
  **0 `AVAILABLE_NEAR_SHOWTIME`**.
* M13.6.4 coverage audit reproduced exactly: 308 planned films, 46 unresolved,
  36 with non-empty tags, 226 empty-snapshot films, **165/2,068 (7.98%)**
  usable temporal signal, 0 outcome-linked predictions with prediction-time
  signal.
* `leakage_audit_v2`: **passed** — all 10 violation classes 0.

**Model readiness decision: `NOT_READY` (unchanged, now re-verified).** There
are still no negative outcome labels and no outcome-linked prediction with
prediction-time cultural signal; training or lift claims remain unsupported.

## 6. Secrets and workspace hygiene

* No `.env` in the working tree; `.env`/`.env.*` gitignored; only
  `.env.example` (placeholders) tracked. Tracked-file secret scan: no key-shaped
  strings found (scan patterns: `QLOO_API_KEY=`, `api[_-]?key`, `sk-`, `Bearer `,
  AKIA/PEM markers).
* Research datasets preserved; workspace kept under the 120 MB budget
  (measured in the final report — build artefacts `node_modules/`, `.next/`,
  `__pycache__` excluded/gitignored).

## 7. Remaining limitations (specific reasons)

1. **Live-Qloo end-to-end run not executed** — no `QLOO_API_KEY` in this
   workspace and the Qloo host is not reachable from this sandbox. The
   no-key failure path and the labelled fixture path were verified instead.
2. **Pixel screenshots not captured** — no browser binary available (see §4).
3. **Backend tests ran on 3.11 with a one-line desugared copy** — the sandbox
   cannot obtain a 3.12 interpreter; the committed code is unmodified 3.12.
4. **Repo-wide ruff debt remains** (pre-existing; §4).
5. The five `correct_frontend_source/Qloo` reference tree and `uploads/` task
   file are historical inputs; they are intentionally left untouched.
