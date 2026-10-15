# Verification Record — M13.13 (2026-10-11)

Environment (re-verified this session): sandbox **re-cloned** — branch
`arena/6462c00a-adjacent-cinema` recreated from `ee7363e`; prior unpushed
commits absent; working tree held the full M13.12 state and was verified
(ruff clean; 552 passed / 8 skipped) **before** being committed as baseline
`e875e58`. GitHub unreachable (TLS). All provider env vars unset (checked by
name only; values never read; `/tmp/qloo.env` untouched). System Python
3.11.2 → all Python runs on the **labelled 3.11 scratch desugar**
(`/tmp/adj-scratch`), never presented as native 3.12. Toolchain rebuilt
this session: ruff 0.17.0, pytest 9.1.1, `npm ci` (exit 0).

## Commands run and exact results (post-change)

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check --no-cache backend research` | **All checks passed** (note: a stale ruff cache once masked a syntax error; `--no-cache` used thereafter) |
| Backend suite | `python -m pytest backend/tests -q` (3.11 scratch) | **585 passed, 8 skipped, 0 failed** (baseline this session: 552 passed → +33 tests) |
| Harness v3, no provider | `python research/scripts/m13_11_qloo_vs_llm.py` | grounded decision_quality **1.0** (n=4, B5 correctly NOT_APPLICABLE), evidence_grounding **1.0** (n=5), abstention_quality **1.0** (n=1); Condition A **BLOCKED** |
| Harness artefact | `data/processed/m13_11_qloo_vs_llm_<ts>.json` (scratch) | rubric_version 3.0; per-run fixture + fixture_alignment labels; abstention anchors embedded |
| Frontend typecheck | `./node_modules/.bin/tsc --noEmit` | exit 0 |
| Frontend build | `npm run build` | success (`/`, `/_not-found`, `/creator` prerendered) |
| Live HTTP E2E (scratch uvicorn :8124) | curl sequence | **5/5**: synthesis-status honest BLOCKED; demo run completed; synthesize → **503**; unknown run → **404**; investigation contract fields present (investigation_id, claim types FACT/HYPOTHESIS/UNKNOWN, q0–q3) |
| Secret scan | pattern scan over all changed files | zero matches (grep exit 1) |

## New/updated tests this milestone

- `test_m13_13_model_quality.py` — **27 tests**: claim-level grounding (12),
  insufficiency contradiction (3), adversarial overclaims incl. claims-embedded
  (7), fallback structure/validator parity (2), provider size bound (2),
  rubric v3 behaviour incl. "fabricated refusal scores ≤1/5" (5 → listed by
  class; count from pytest).
- `test_m13_12_agent_intelligence.py` — +2 (geography insufficiency:
  sparse-heatmap vs missing-call honesty).
- `test_m13_12_synthesis.py` — updated to schema 2.0 (structured-claims
  payloads; route test asserts claim-level refs resolve and guarantees
  metadata is honest).
- `test_m13_11_investigation_eval.py` — rubric 3.0 version assertions,
  methodology prefix.

## Test-fixes-made-honest (failures found and corrected during this milestone)

1. Harness `avoids_unsupported_facts` initially penalised B5's single
   **cited** FACT ("Qloo returned N tags") — criterion corrected to count
   only FACT claims **lacking** evidence refs; B5 abstention 4/5 → 5/5 earned.
2. Three of my own new-test assertions mismatched actual (correct) message
   strings ("size bound" vs "char bound"; methodology prefix) — assertions
   corrected to the real strings, not the code bent to the tests.
3. A dropped closing paren in the harness METHODOLOGY patch (caught by
   `ast.parse` after ruff's cache masked it) — fixed and re-verified.

## What was NOT verified here (honest gaps)

- **Live Qloo** — egress-blocked; all evidence labelled fixture.
- **Real LLM condition / live synthesis** — no provider; BLOCKED, not stubbed.
- **Live YouTube** — unchanged single-user, fixture tests only.
- **Human evaluation** — template only; zero ratings collected.
- **GitHub push / CI** — remote unreachable; local commits only.
- **Browser-level UI testing** — no browser tooling in sandbox; the Decision
  Brief panel is verified via `tsc`/build + endpoint E2E, not visually.
- **Native Python 3.12 execution** — unavailable; labelled scratch only.
