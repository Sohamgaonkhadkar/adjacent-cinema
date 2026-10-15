# M13.14 — Deployment Readiness Checklist

Delta over `M13_13_DEPLOYMENT_READINESS.md` (all items there remain valid).

| # | Item | State | Notes |
|---|------|-------|-------|
| 1 | Qloo credentials | OWNER ACTION | unchanged — `QLOO_API_KEY` unset (checked by name only); egress blocked; live acceptance BLOCKED here. |
| 2 | LLM provider | OPTIONAL | unchanged — synthesis honestly blocked (status + 503) without `ADJACENT_LLM_API_KEY`; deterministic investigation + adoption of the deterministic Test Card fully functional without it. Provider bounds intact (60 s, 100k chars, no retries). |
| 3 | Snapshot integrity | VERIFIED | server-side allowlist sanitisation (credential-shaped keys stripped, E2E-proven); refs verified against source-run trace; unresolved refs recorded, never stored as proof; replays cannot mutate stored snapshots. |
| 4 | Decision-history safety | VERIFIED | adoption never overwrites: request_id idempotency + one-decision-per-run dedupe return the original record; investigation is immutable (regression-tested). |
| 5 | Secrets hygiene | VERIFIED | secret-pattern scan over all changed files pre-commit; no credential storage in snapshots by construction. |
| 6 | Repository state | NOTE | GitHub unreachable (TLS) all session — local commits only; owner must push `arena/6462c00a-adjacent-cinema` (baseline `e875e58` + M13.13 `090b394` + M13.14 commit). GitHub main still lacks M13.9+. |
| 7 | Python runtime | NOTE | unchanged — deploy on 3.12+; sandbox testing via labelled 3.11 scratch desugar only. |
| 8 | Frontend | VERIFIED | `tsc --noEmit` clean; `next build` succeeds. Adoption UI uses existing visual conventions — cinematic redesign untouched (separate workstream). |
| 9 | YouTube | SINGLE-USER ONLY | unchanged. |
| 10 | Public deployment | NOT RECOMMENDED YET | unchanged — no auth layer. |

Owner actions: (1) supply Qloo key → live acceptance; (2) optionally supply
LLM key → live synthesis + real Condition A; (3) push the branch and open a
PR.
