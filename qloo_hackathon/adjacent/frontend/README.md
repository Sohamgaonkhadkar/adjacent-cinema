# Adjacent frontend

This Next.js application provides the creator-first home page, Creator Mode at `/creator`, and the preserved Cinema Mode at `/cinema`. The fixture entry point is `/creator?demo=fixture`; its results are labelled as offline fixture data and are not live Qloo results.

## Run locally

Start the backend from `qloo_hackathon/adjacent` on port 8000, then:

```bash
cd qloo_hackathon/adjacent/frontend
npm ci
ADJACENT_API_ORIGIN=http://127.0.0.1:8000 npm run dev -- --hostname 0.0.0.0
```

The browser calls relative `/api` routes. `next.config.ts` rewrites these server-side to `ADJACENT_API_ORIGIN`; production must set that variable to the backend service origin. Do not set a browser-visible `NEXT_PUBLIC_API_URL` and do not put `QLOO_API_KEY` in frontend environment variables.

## Verify

```bash
npm run build
```

The frontend build is included in CI. For full setup, backend commands, live-versus-fixture behavior, public-demo guardrails and current verification status, see the [project README](../../../README.md), the [developer guide](../README.md) and the [live-Qloo checklist](../docs/NEXT_LIVE_CHECKLIST.md).
