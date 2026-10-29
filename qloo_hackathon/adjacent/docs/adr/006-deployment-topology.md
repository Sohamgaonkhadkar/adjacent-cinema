# ADR-006: Deployment Topology

## Status

**PROPOSED — not deployed or revalidated.** This supersedes the earlier “FROZEN” label: the repository contains no deployment manifest or verified hosted environment as of 16 October 2026.

## Historical proposal (4 October 2026)

- Next.js frontend on a managed frontend host (Vercel was the candidate).
- FastAPI backend on a persistent service (Fly.io was the candidate).
- No serverless backend for the SSE/run process.

The proposal was motivated by persistent SSE connections, a small operational surface, and a server-side boundary for Qloo credentials. These provider selections and cost assumptions have **not** been implemented or confirmed.

## What the code actually does

- The frontend calls relative `/api` paths. Next.js rewrites them server-side using `ADJACENT_API_ORIGIN`; its local default is `http://127.0.0.1:8000`. A hosted frontend must set the backend origin in its server environment. No browser-visible `NEXT_PUBLIC_API_URL` is required.
- Qloo credentials are read by the backend from `QLOO_API_KEY`; they must remain in a backend secret store.
- Run records are process-local and in-memory. Experiment/observation/evaluation history and single-connection YouTube tokens use SQLite at `ADJACENT_EXPERIMENTS_DB` and `ADJACENT_YT_TOKEN_DB` (runtime files are gitignored).
- There is no `DATABASE_URL` adapter, PostgreSQL schema, Docker/Fly/Vercel/Render configuration, deployment record, or verified public URL in this checkout.
- The experiment store and YouTube token store are single-workspace designs, not a multi-user isolation boundary.

## Anonymous demo boundary

Set `ADJACENT_PUBLIC_DEMO=1` before exposing the backend anonymously. This permits fixed labelled fixture runs and bounded Creator inputs; shared experiment access, YouTube, synthesis execution, debug endpoints, and API docs are blocked. Live Creator runs additionally require explicit `ADJACENT_PUBLIC_LIVE=1` and a backend Qloo key. Limits are in-process; a multi-worker or replicated service needs edge quotas or a shared limiter. The public-demo flag is a narrow demo posture, not authentication.

## Deployment gates before claiming readiness

1. Choose and configure the actual frontend/backend hosts; record their real URLs and commit/deployment identity.
2. Set `ADJACENT_API_ORIGIN` server-side and verify the same-origin `/api` proxy and SSE path from the hosted frontend.
3. Configure exact CORS origins only if a direct cross-origin API client is intentionally supported.
4. Choose storage semantics. Do not mount one SQLite file concurrently across workers or present it as per-user storage.
5. Enable `ADJACENT_PUBLIC_DEMO=1` for an anonymous demo; keep live Creator disabled until the owner approves quotas/privacy and deploys edge limits. Keep YouTube and shared experiment writes disabled without an ownership boundary.
6. Run the live-Qloo gate using an authorized secret, and separately verify fixture labels, public write denial, request limits, and secret redaction.

**Current deployment result:** the Vercel/Render deployment has a recorded production route smoke check; remaining operational gates are in [`../NEXT_LIVE_CHECKLIST.md`](../NEXT_LIVE_CHECKLIST.md). This proposed Compose/Caddy topology is separate from the current hosted arrangement.
