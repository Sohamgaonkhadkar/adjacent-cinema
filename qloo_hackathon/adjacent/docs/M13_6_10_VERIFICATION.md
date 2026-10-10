# M13.6.10 Verification Record — 2026-10-10

Branch `arena/6462c00a-adjacent-cinema`, based on `46cb73a`. Everything below
was executed on 2026-10-10 in the Arena sandbox unless marked *unverified*.

## 1. Native Python 3.12 test run (no source modifications)

The sandbox ships only Python 3.11.2 and all binary-distribution channels are
blocked (uv TLS interception, GitHub release assets, apt without root). CPython
**3.12.15 was therefore compiled from source** (codeload.github.com tarball)
against a statically built SQLite 3.38.2, zlib 1.3.1 and OpenSSL 3.0.17 —
prefix `/tmp/py312`, venv `/tmp/adj312`.

Result, on the committed tree with **zero syntax transformations**:

```
/tmp/adj312/bin/python -m pytest -m "not live"
455 passed, 1 skipped, 7 deselected, 2 warnings in 5.84s
```

* `7 deselected` = the `live`-marked Qloo tests (no API key configured — see §6).
* PEP 695 generics (`class ToolResult[T]`) import natively; no compatibility
  shims remain anywhere.
* This run also validates the ruff auto-fix batch (§2) as behaviour-preserving.

## 2. Lint gate (ruff 0.17.0, pinned)

* `ruff check backend` before fixes: **332 findings**; after: **0**
  (`All checks passed!`). Two justified `# noqa: SIM102` remain in
  `outcome_repository.py` (nested migration guards read clearer unfolded).
* `pyproject.toml` now pins `required-version = "==0.17.0"` and excludes
  `research/` + `scripts/` explicitly. `ruff check .` (the CI gate) exits 0.
* Legacy debt measured and documented in `docs/LINT_DEBT.md`:
  **1,249 findings** (research 1,161 / scripts 88), deliberately untouched.
* CI reports the debt count without gating on it.

## 3. Golden path (live servers, via the Next.js `/api` proxy)

Backend: native 3.12 uvicorn on :8000. Frontend: `next start` on :3000.
Evidence files: `docs/verification_2026-10-10/m13_6_10_*`.

| Step | Result |
|---|---|
| `GET /api/health` | `qloo_configured:false, mode:"mock"`, no key material |
| `POST /api/run` (custom, no key) | `status:"failed"`, `error:"QLOO_API_KEY not configured"`, **`result:null`**, submitted programme echoed verbatim — no fabricated payload |
| `GET /api/run/{id}` | failure state retrievable after the fact |
| SSE failed run | replays `trace`, terminates `error` |
| `POST /run/demo` | `completed`, `stop_reason:"complete"`, 8/8 resolved, 6 ranked cohorts + 2 rejected, 24 geo cells, bet=Brian Eno (3 members) |
| fixture labelling | `data_status:"fixture"` on result, bet AND test card |
| SSE demo | 15 events (`trace×3, resolution, taste_dna, cohort×6, heatmap, bet, test_card, done`) |
| `GET /run/{id}/trace` | 15 provenance rows |
| empty programme | **422** with pydantic detail |
| unknown run id | **404** |

Unresolved-film and insufficiency paths on a **live** run remain unverified
until a key is configured; both are covered by the automated suite
(`test_run_api_golden_path.py`, resolution tests) against the real routes.

## 4. Fresh database audit (read-only, on a copy)

`research/scripts/m13_6_4_coverage_audit.py` re-run against a copy of
`outcome_ledger.db` → `docs/verification_2026-10-10/db_audit_m13_6_10_rerun.json`:

* 2,175 predictions: PLANNED 2,068 / FROZEN 90 / OUTCOME_FINAL 11 / CENSORED 6
* Usable temporal signal **165/2,068 = 7.98%** (identical to M13.6.9)
* 36 films with non-empty tags, 226 empty-signal films, 46 unresolved
* 11 `SOLD_OUT_OBSERVED`, 0 negative outcomes, 0 leakage violations
* **Supervised readiness stays `NOT_READY`** — no new genuine labels exist.

## 5. M13.6.9 claims re-verified (not repeated)

Source inspection confirmed: `IntakeForm` rendered by the live page with no
hardcoded percentages; `API_BASE=/api` + `/run`/`/run/demo` + proxy rewrite;
`data_status` truthful at result/bet/test-card/geography level;
`audience_hypothesis` mapping fixed; demo executor hard-codes
`data_status="fixture"`.

## 6. QLOO_API_KEY — NOT CONFIGURED (owner action required)

The key was **not present** in the sandbox environment (`env` check, no
`/run/secrets`, no `.env`). It must be supplied through Arena's runtime-secret
mechanism — never committed, pasted into source, or logged. Because the key
was previously pasted into a conversation, **rotate it** after configuring.
Once available: `pytest -m live` runs automatically in CI when
`secrets.QLOO_API_KEY` exists, and the full live workflow (smoke → frontend
analysis → truthful `data_status:"measured"`) can be re-verified.

## 7. Visual verification

*Unverified (no browser binary in sandbox).* Substitute evidence: SSR HTML of
the home page (`m13_6_10_home_ssr.html`, 22.5 KB, fixture badge present in
markup) plus the HTTP/SSE captures above. No screenshots were produced.
