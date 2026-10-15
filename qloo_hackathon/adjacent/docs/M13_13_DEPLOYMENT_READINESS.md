# M13.13 — Deployment Readiness Checklist

Delta over `M13_12_DEPLOYMENT_READINESS.md` (items 1–10 there remain valid).

| # | Item | State | Notes |
|---|------|-------|-------|
| 1 | Qloo credentials | OWNER ACTION | unchanged — runtime secret only; sandbox egress to `hackathon.api.qloo.com` blocked; live acceptance BLOCKED here. |
| 2 | LLM provider | OPTIONAL | unchanged — `ADJACENT_LLM_API_KEY` unset → synthesis honestly blocked at status + 503; deterministic product fully functional. New in M13.13: provider responses bounded (60 s timeout, 100 000-char cap, no retries). |
| 3 | YouTube OAuth | SINGLE-USER ONLY | unchanged — no public multi-user exposure without auth boundaries. |
| 4 | Secrets hygiene | VERIFIED | secret-pattern scan over all changed files pre-commit; `guarantees`/status/redacted views secret-free by construction. |
| 5 | Repository state | NOTE | Sandbox was re-cloned this session; prior local commits (`3bae0ce` etc.) were never pushed and do not exist in this clone. Full M13.12 state was restored, verified (552 passed pre-change) and committed as baseline `e875e58` before M13.13 work began. GitHub remains unreachable (TLS) — owner must push. GitHub main currently lacks M13.9–M13.13 work. |
| 6 | Python runtime | NOTE | unchanged — repo targets 3.12; sandbox has 3.11; all Python runs use the labelled desugared scratch. Deploy on 3.12+. |
| 7 | Frontend | VERIFIED | `tsc --noEmit` clean; `next build` succeeds. Decision Brief panel is integration wiring only; visual redesign remains a separate workstream. |
| 8 | Honesty states | VERIFIED | new: synthesis method labelling reaches the UI; abstention is a first-class scored outcome; fixture mismatch disclosed in every artefact. |
| 9 | Public deployment | NOT RECOMMENDED YET | unchanged — no auth layer; single-creator tooling. |

Owner actions: (1) supply Qloo key → live acceptance; (2) optionally supply
LLM key → live synthesis + real Condition A comparison; (3) push branch
`arena/6462c00a-adjacent-cinema` (contains baseline `e875e58` + M13.13
commits) and open a PR — GitHub main is behind by M13.9–M13.13.
