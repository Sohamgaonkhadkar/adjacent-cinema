# ADR-006: Deployment Topology

## Status

FROZEN

## Date

4 October 2026

## Decision

- Frontend: Vercel (Next.js App Router)
- Backend: Fly.io (single small machine, always-on)
- Database: Fly Postgres or Neon free tier
- No microservices, no Kubernetes, no serverless functions for the backend

## Rationale

1. **SSE requires persistent connections.** Serverless cold starts would stall an SSE stream mid-demo. A persistent process keeps the connection and the in-flight call budget intact.
2. **Simplicity.** Single backend service is simpler, faster to build, easier to demo.
3. **Cost.** Fly.io free tier is sufficient for hackathon workload. Neon free tier for PostgreSQL.
4. **Next.js on Vercel.** Zero-config deployment, edge functions, automatic preview URLs.

## Alternative Considered

- All on Vercel (serverless) — rejected: SSE requires persistent connections
- All on Fly.io — rejected: Next.js benefits from Vercel's edge network
- AWS/GCP — rejected: too much infrastructure for a hackathon
- Docker Compose locally — rejected: not demoable to judges

## Consequence

- Two deployment targets: Vercel (frontend) + Fly.io (backend)
- Backend needs CORS configured for Vercel origin
- Backend needs `QLOO_API_KEY`, `DATABASE_URL`, `LLM_API_KEY` as Fly secrets
- Frontend needs `NEXT_PUBLIC_API_URL` pointing to Fly backend

## Trigger to Revisit

If Fly.io's free tier becomes insufficient, or if the hackathon requires a different deployment target.