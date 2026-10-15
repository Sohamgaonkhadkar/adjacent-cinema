# M13.12 — Deployment Readiness Checklist

| # | Item | State | Notes |
|---|------|-------|-------|
| 1 | Qloo credentials | OWNER ACTION | `QLOO_API_KEY` via runtime secret mechanism only. Never in source, logs, artefacts, commits. Sandbox cannot reach `hackathon.api.qloo.com`; live acceptance remains BLOCKED here. |
| 2 | LLM synthesis credentials | OPTIONAL | `ADJACENT_LLM_API_KEY` (+ optional `ADJACENT_LLM_BASE_URL`, `ADJACENT_LLM_MODEL`). Unset → synthesis honestly BLOCKED (503 + `/creator/synthesis-status`); the deterministic product is fully functional without it. |
| 3 | YouTube OAuth | SINGLE-USER ONLY | One-owner token flow. Do **not** expose as a public multi-user service without real auth boundaries (per-user consent, token isolation, session auth). Not implemented — out of scope by decision. |
| 4 | Secrets hygiene | VERIFIED | Secret-pattern scan over all changed files before commit; `/creator/synthesis-status`, synthesis metadata, provider `redacted()`, and artefacts contain no credentials by construction. |
| 5 | Data at rest | OK | Runtime DBs (`data/runtime/youtube_auth.db`, `data/processed/experiments.db`) gitignored; no token DBs or generated private data committed. |
| 6 | Honesty states | VERIFIED | Fixture data labelled in every payload; BLOCKED ≠ stubbed; failed model calls labelled `deterministic_fallback` with the error recorded; empty result ≠ API error. |
| 7 | Python runtime | NOTE | Repo targets Python 3.12 (PEP 695 generics). Local sandbox has 3.11 only — tests run via a **labelled desugared scratch copy**, never presented as native 3.12. Deploy on 3.12+. |
| 8 | Frontend build | VERIFIED | `tsc --noEmit` clean; `next build` succeeds (routes `/`, `/creator`). |
| 9 | GitHub remote | BLOCKED | Sandbox egress to GitHub fails (TLS). Commits are local; owner must push from their environment. Never claimed as pushed here. |
| 10 | Public deployment | NOT RECOMMENDED YET | No auth layer exists; the app is single-creator tooling. Multi-user exposure requires item 3 + authentication + rate limiting first. |

Owner-only actions: (1) supply Qloo key at runtime and re-run live acceptance;
(2) optionally supply an LLM key to enable Role-B synthesis; (3) push the
branch when network access is available.
