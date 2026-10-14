# M13.11 Verification Report — exact counts

Date: 2026-10-11. Environment: sandbox, Python 3.11 only (native 3.12 unobtainable —
source downloads blocked). Backend suite executed on the **labelled desugar scratch
copy** (single transform: `class ToolResult[T](_Base)` → `Generic[T]` form in
`app/qloo/models.py`; production sources untouched, remain 3.12-syntax). **This is NOT
a native 3.12 run.** Frontend checks ran on the production tree. GitHub remote
unreachable (TLS handshake terminated) — **no push, no CI; CI status unknown, not
green.**

## Static checks (production tree)

| Check | Command | Result |
|---|---|---|
| Ruff 0.17.0 | `ruff check backend research` | **All checks passed** (1 RUF100 found & fixed during session) |
| TypeScript | `npx tsc --noEmit` | **0 errors** |
| Next build | `npm run build` | **Clean; routes `/`, `/_not-found`, `/creator`** |

## Backend suite (scratch 3.11, `-m "not live"`)

**514 passed, 1 skipped, 7 deselected** (M13.10 baseline 503p/1s/7d → **+11 new
M13.11 tests, zero regressions** in creator/cinema/YouTube suites).

New `test_m13_11_investigation_eval.py` (11 tests): investigation via API
(questions/tools/statuses, evidence refs ⊆ run trace, fixture label + affinity guard,
hypothesis chain); SSE `investigation` event; cinema result carries NO investigation
key; grounded-condition rubric scoring; insufficient brief → no hypothesis;
empty-state → all questions insufficient/unavailable; Condition A blocked without LLM
key (never stubbed); stub condition labelled `llm_stub` and scores lower;
llm-condition output shape; all 5 briefs run.

## Evaluation harness (fixture run, labelled)

`PYTHONPATH=backend python research/scripts/m13_11_qloo_vs_llm.py` (executed from the
scratch copy): **qloo_grounded n=5, avg 5.4/6; llm_only BLOCKED
(ADJACENT_LLM_API_KEY not configured)**. Artefact committed:
`data/processed/m13_11_qloo_vs_llm_20261010_205748.json`. Fixture-based mechanics
result — NOT real-world effectiveness, NOT a comparison win.

## End-to-end (live servers through the Next `/api` proxy; backend = scratch 3.11,
YouTube in labelled mock mode)

| # | Check | Result |
|---|---|---|
| 1 | Film brief → creator demo run | `completed`, fixture-labelled; investigation: 3 questions (get_taste_profile / expand_candidates / rank_cohorts) all `answered`; 1 FACT + 1 INTERPRETATION finding; primary hypothesis (artist world) with evidence refs; 1 alternative; **all evidence refs present in run trace** |
| 2 | Save Test Card as experiment | 201, snapshot persisted |
| 3 | YouTube connect (mock) + from-youtube observation with `variant_label:"title A"` | OBSERVED, views 128, variant recorded in evidence_ref |
| 4 | Evaluation + history | INCONCLUSIVE recorded with unknowns; history retrievable |
| 5 | Live creator run without key | `failed`, "QLOO_API_KEY not configured", `result: null` — no fixture fallback |
| 6 | Cinema regression + SSR | cinema `completed`, no investigation leakage; `/creator` HTTP 200 |

## Invariants preserved

- FACT vs INTERPRETATION separated in every investigation; interpretations never
  presented as Qloo facts.
- Fixture ≠ live at every layer; live failures never substitute demo data.
- Affinity ≠ viewership guard present in every investigation's limitations.
- Append-only experiment history, idempotency, supersession untouched; observation
  semantics (zero ≠ missing) unchanged.
- No secrets: no credentials in code/diff/artefacts; secret-pattern scan clean;
  token DBs and runtime data gitignored.
- Model readiness untouched: investigation outputs and YouTube observations are NOT
  ML labels; `NOT_READY` stands.

## Not verified (honest gaps)

- **No live Qloo call** (sandbox egress blocked; no key handled) — live acceptance
  BLOCKED, owner action required.
- **No real LLM Condition A run** (no provider credentials) — comparison incomplete.
- **No live YouTube OAuth round trip** (unchanged from M13.10) — BLOCKED.
- **No native Python 3.12 run**; the one-line desugar transform is the only divergence.
- **No browser UI walkthrough** (no browser); SSR + API + build checks stand in.
- **No CI run** (GitHub unreachable).
