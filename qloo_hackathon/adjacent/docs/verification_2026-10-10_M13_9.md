# M13.9 Verification Report — exact counts

Date: 2026-10-10. Environment: sandbox without native Python 3.12 (source downloads
blocked this session); backend suite executed on **Python 3.11 against a labelled scratch
desugar copy** of the tree (single transform: `class ToolResult[T](_Base)` →
`Generic[T]` form in `app/qloo/models.py`; production code untouched and remains
3.12-syntax). Frontend checks ran on the production tree.

## Static checks (production tree)

| Check | Command | Result |
|---|---|---|
| Ruff 0.17.0 | `ruff check .` (from `qloo_hackathon/adjacent/`) | **All checks passed** (2 F541 in new code auto-fixed during the session) |
| TypeScript | `npx tsc --noEmit` (frontend, after `npm ci`) | **0 errors** |
| Next build | `npm run build` | **Clean; routes `/`, `/_not-found`, `/creator` (all static)** |

## Backend test suite (scratch 3.11 copy)

`python -m pytest -m "not live"` → **479 passed, 1 skipped, 7 deselected** (was 463p/1s/7d
at M13.7 baseline — **+16 new M13.9 regressions, zero cinema regressions**).

New tests:
- `test_m13_9_creator_mode.py` (6): demo completion with fixture labels + `mode:"creator"`
  + film context; bet↔cohort↔test-card invariant; success-criteria contract (includes
  "predicts no view counts"); exclusions surfaced; SSE event stream; live-run-without-key
  honest failure (`result: null`, no fabricated payload); 422 on empty seeds; 422 on
  missing title; 404 on unknown run.
- `test_m13_9_experiment_lifecycle.py` (10): save + snapshot retrieval; retry returns
  original (duplicate flag); second save for same run deduplicated; observed-zero kept as
  data vs UNAVAILABLE with empty metrics; observation retry idempotent; invalid
  measurement_status → 422; observation on unknown experiment → 404; evaluation supersede
  keeps append-only history; invalid outcome → 422; history survives repository reopen.

**Defect found and fixed by these tests:** `ExperimentRepository` opened SQLite with
default `check_same_thread`, which raised `ProgrammingError` under FastAPI's
cross-thread request handling (10 failures on first run). Fixed with
`check_same_thread=False` + reentrant lock serialising all repository access; full suite
green after the fix.

## End-to-end verification (live servers, this session)

Backend: uvicorn from the scratch 3.11 copy on :8000 (labelled — not the 3.12 production
runtime); frontend: production `next start` build on :3000 proxying `/api` → :8000.
All requests went through the Next proxy, i.e. the browser-facing path.

| # | Check | Result |
|---|---|---|
| 1 | `POST /api/creator/run` without QLOO_API_KEY | `failed`, error "QLOO_API_KEY not configured", `result: null` — no fixture substitution |
| 2 | `POST /api/creator/run/demo` | `completed`, `mode:"creator"`, film context present, `data_status:"fixture"` on result/bet/card; bet.primary.cohort_id == ranked[0].cohort_id; card.provenance.primary_cohort_id == bet cohort |
| 3 | `POST /api/experiments` + retry (new request_id, same run) | Saved; retry → `duplicate:true`, same experiment_id, one row in list |
| 4 | Observations | observed-zero stored as `{"views": 0}`; UNAVAILABLE stored with empty metrics + limitation text |
| 5 | Evaluations | INCONCLUSIVE then CONTRADICTED → `supersedes_id` set; history `["INCONCLUSIVE","CONTRADICTED"]` both retained |
| 6 | Validation live | 7-char request_id → **422 string_too_short** (min_length=8) — surfaced during E2E, product behaving as designed |
| 7 | Cinema regression `POST /api/run/demo` | `completed`; **no `mode` field leaked**; city "Portland, Oregon"; bet + test card present |
| 8 | SSR `GET /creator` | HTTP 200; page renders hero ("Position your film in its cultural context") |

## Invariants preserved

- Fixture vs live never conflated: demo/fixture paths labelled at result, bet, and card
  level; live failure never falls back to fixtures (check 1).
- bet ↔ cohort ↔ test-card provenance link holds in creator mode (check 2, mirrors the
  M13.7 cinema invariant).
- Exclusions visible: ranked cohorts carry `qualifying_count` + `excluded_members`.
- No predicted views/retention/revenue anywhere in generated artefacts; success criteria
  are observable statements (card text asserts "predicts no view counts").
- Model readiness untouched: no new label sources; `NOT_READY` stands.
- No secrets: QLOO_API_KEY not read, logged, or required; `.gitignore` covers
  `data/processed/experiments.db`.

## Not verified (honest gaps)

- **No native 3.12 run** this session (source downloads blocked); the single desugared
  line is the only 3.11/3.12 divergence in the executed copy.
- **No live Qloo API call** (sandbox egress blocks `hackathon.api.qloo.com`; key handling
  untouched per session constraints). The live creator path is exercised only up to its
  honest-failure branch.
- **No browser screenshots** (no browser in sandbox); SSR + API checks stand in.
- GitHub Actions CI was not run (remote GitHub operations are unavailable in this
  session); CI status for this work is unknown, not green.
