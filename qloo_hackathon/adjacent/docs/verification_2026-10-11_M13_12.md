# Verification Record — M13.12 (2026-10-11)

Environment facts (re-verified at milestone start): system Python 3.11.2 only
(repo targets 3.12 — all Python runs below use the **labelled 3.11 scratch
desugar** at `/tmp/adj-scratch`, never presented as native 3.12); GitHub
remote unreachable (TLS handshake failure) — commits are local only;
`ADJACENT_LLM_API_KEY`, `QLOO_API_KEY` (env), YouTube env all unset;
`/tmp/qloo.env` untouched.

## Commands run and exact results

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check backend research` (ruff 0.17.0) | **All checks passed** |
| Backend suite | `python -m pytest backend/tests -q` (3.11 scratch) | **552 passed, 8 skipped, 0 failed** (M13.11 baseline: 514 passed) |
| Harness, no provider | `python research/scripts/m13_11_qloo_vs_llm.py` | grounded decision_quality **0.88**, evidence_grounding **1.0** (n=5, fixture); Condition A **BLOCKED** (`ADJACENT_LLM_API_KEY` unset) |
| Harness, stub mechanism test | `… --stub-a` | stub decision_quality 0.60 vs grounded 0.88; stub labelled `llm_stub`; grounding not applicable to baseline |
| Human-rating template | written by harness | `data/processed/m13_12_human_rating_template.csv` (rows empty — no human ratings exist or are claimed) |
| Frontend typecheck | `./node_modules/.bin/tsc --noEmit` | exit 0 |
| Frontend build | `npm run build` | success; routes `/`, `/_not-found`, `/creator` prerendered |
| Live HTTP E2E (scratch uvicorn, port 8123) | curl sequence | 4/4: synthesis-status honest BLOCKED; demo run completed; synthesize → **503** naming `ADJACENT_LLM_API_KEY`; POST /experiments merged `investigation_summary`, kept real ref, dropped `ghost-c999` into `provenance.unresolved_evidence_refs` |
| Secret scan | pattern scan over all changed files (see commit step) | no credentials in any diff |

## New/updated tests (this milestone)

- `test_m13_12_agent_intelligence.py` — 20 tests: q0 context framing (3),
  adaptive q5/q6 (4), typed claims (3), hypothesis quality + no forced
  recommendation (2), evidence-ref verification incl. API resolution (3),
  plus demo-run structural assertions.
- `test_m13_12_synthesis.py` — 19 tests: validation (valid/malformed/missing
  keys/fabricated ref/real ref/4 forbidden-claim patterns/oversized),
  provider failure → labelled fallback, fallback truthfulness on
  insufficient evidence, prompt credential-freedom, provider config +
  redaction, routes (blocked status, 404, 503, stub-labelled 200, fallback
  200, override status).
- `test_m13_11_investigation_eval.py` — updated to rubric v2 (category
  scores, applicability, run metadata; q1 looked up by tool since q0 may
  precede it).

## What was NOT verified here (honest gaps)

- **Live Qloo API** — egress-blocked; all Qloo evidence in tests/harness is
  labelled fixture. Live acceptance remains an owner action.
- **Real LLM condition (Condition A)** — no provider configured; BLOCKED,
  not stubbed. No real-vs-grounded comparison is claimed.
- **Live YouTube** — no OAuth possible from sandbox; M13.10 single-user
  behaviour unchanged and re-tested via fixtures only.
- **Human evaluation** — template exists; zero ratings collected. None
  reported anywhere.
- **GitHub push / CI** — remote unreachable; local commits only.
