# Zero-cost preview deployment

This guide deploys Adjacent Cinema for a personal/student demo using **Vercel Hobby for Next.js** and a **Render Free web service for FastAPI**. It avoids the paid plans and persistent disk in the default `render.yaml`.

This is a hobby/demo arrangement, not a durable production deployment. Render Free services sleep after 15 minutes without traffic and their local files are lost on spin-down, restart or redeploy. The SQLite-backed experiment and FilmSponsor records can disappear. Keep `QLOO_API_KEY` unset and public live Qloo disabled.

## Cost and limits

- Vercel Hobby is $0/month for eligible personal, non-commercial projects; see the [current plan](https://vercel.com/docs/plans).
- Render Free web service is $0/month within the included usage; see [Render's free-service limits](https://render.com/docs/free).
- No paid domain, persistent disk, paid database or Qloo key is needed for the fixture demo. Use the default HTTPS hostnames.

This is $0 only while staying within free-tier terms and included usage. Render has usage caps and free web services have limited CPU/RAM, cold starts and ephemeral storage. Monitor both hosting dashboards, do not upgrade any service, and do not store important records here.

## Part A — create the frontend project on Vercel first

1. Open the [Vercel Dashboard](https://vercel.com/dashboard) and import `Sohamgaonkhadkar/adjacent-cinema` from GitHub.
2. Set **Root Directory** to `qloo_hackathon/adjacent/frontend`.
3. Select Node.js 22 if asked. Use the Next.js framework preset and build command `npm run build`.
4. Deploy branch `arena/9d8b618a-adjacent-cinema`. For a stable project URL while testing this feature branch, set the Vercel project's **Production Branch** to `arena/9d8b618a-adjacent-cinema` under Project Settings → Git. This changes only Vercel's deployment configuration; it does not change GitHub's `main` branch.
5. You may leave `ADJACENT_API_ORIGIN` unset for this first build; it defaults to localhost, so API requests will not work yet. Copy the actual HTTPS Vercel project origin, e.g. `https://YOUR-PROJECT.vercel.app`.

Use the Vercel Hobby plan only if this is an eligible personal, non-commercial project. Do not add a paid custom domain or upgrade the plan.

## Part B — deploy the backend on Render Free

1. Open the [Render Dashboard](https://dashboard.render.com/) and click **New → Blueprint**.
2. Connect `Sohamgaonkhadkar/adjacent-cinema`.
3. Set **Blueprint Path** to `render-free.yaml` (not the default `render.yaml`).
4. Select branch `arena/9d8b618a-adjacent-cinema`.
5. Review the Blueprint preview: it must create exactly one **Web Service** named `adjacent-cinema-api-free` on the **Free** plan. It must not create a private service, a persistent disk or a paid frontend.
6. When prompted for `ADJACENT_FILMSPONSOR_GUEST_ORIGINS`, enter the exact Vercel origin copied in Part A. Use origin only, no route path, wildcard or trailing slash.
7. Deploy and wait for the service to become healthy. Copy its actual public URL, e.g. `https://adjacent-cinema-api-free.onrender.com`; use the exact hostname Render assigns.
8. Open `https://YOUR-API-URL/health`. It should return HTTP 200 and report public/demo mode with live Qloo disabled.

This Blueprint does not set `QLOO_API_KEY`; do not add one for the first preview.

## Part C — connect Vercel to the backend

1. In Vercel, open Project Settings → Environment Variables.
2. Add `ADJACENT_API_ORIGIN` with the actual Render backend origin from Part B, including `https://` and with no path or trailing slash.
3. Enable it for the environment that serves your chosen branch (Production if you made this branch the production branch; otherwise Preview).
4. Redeploy the Vercel frontend so Next.js rebuilds with the correct server-side rewrite destination.

The browser calls same-origin `/api/*`; Next.js forwards those requests to `ADJACENT_API_ORIGIN`. Do not create a `NEXT_PUBLIC_QLOO_API_KEY` or place any provider credential in the frontend.

## Part D — keep the guest workspace scoped to the correct frontend

Check the Render backend environment has these settings:

- `ADJACENT_PUBLIC_DEMO=1`
- `ADJACENT_PUBLIC_LIVE=0`
- `ADJACENT_FILMSPONSOR_GUEST_DEMO=1`
- `ADJACENT_FILMSPONSOR_GUEST_COOKIE_SECURE=1`
- `ADJACENT_FILMSPONSOR_GUEST_ORIGINS` = exact Vercel frontend origin

If you use a different Vercel deployment origin later, update the backend value to that exact origin and redeploy the backend. Never use `*`. Do not enable public live Qloo without separate access controls, upstream quotas and explicit approval of usage costs.

## Part E — verify the public demo

Replace `YOUR-PROJECT` and `YOUR-API-URL` with the actual provider URLs:

```bash
curl -i https://YOUR-API-URL/health
curl -i https://YOUR-PROJECT.vercel.app/api/health
curl -I https://YOUR-PROJECT.vercel.app/
curl -I 'https://YOUR-PROJECT.vercel.app/creator?demo=fixture'
curl -I https://YOUR-PROJECT.vercel.app/cinema
curl -I https://YOUR-PROJECT.vercel.app/creator/sponsor
```

Then open the actual Vercel URL in a browser and submit a Creator fixture request, try the Cinema fixture workflow, inspect FilmSponsor guest initialization, test fingerprint interactions and export a Test Card as `.txt`. Verify the fixture label is visible and there are no broken API requests in the browser Network panel.

## What does not persist on this free stack

Render Free has an ephemeral filesystem. The database configured at `/tmp/experiments.db` allows demo workflows to run but is not durable. Saved experiments, observations, campaigns, drafts and guest sessions can disappear after idle spin-down, restart or redeploy. Run/SSE history is process-local too. Render's free Postgres has its own limitation: it expires after 30 days, so it is not a safe long-term substitute for production data.

Use this deployment to demonstrate workflows, not to store real creator/campaign records. If durable data becomes necessary, stop and redesign the storage layer before migrating to a paid or independently free durable database.

## Troubleshooting

- **Page renders but API calls fail:** check `ADJACENT_API_ORIGIN` in the Vercel environment and redeploy Vercel.
- **First request is slow or shows a wake-up page:** Render Free may have spun down; wait for the backend to start and retry.
- **FilmSponsor guest workspace is rejected:** check `ADJACENT_FILMSPONSOR_GUEST_ORIGINS` matches the exact Vercel origin in your address bar.
- **Saved data disappears:** expected limitation of the free filesystem; this deployment is not durable.
- **Blueprint offers paid resources:** cancel before confirming. You selected `render.yaml` instead of `render-free.yaml`.

For the paid/persistent Render topology, see [DEPLOYMENT.md](DEPLOYMENT.md). The existing paid `render.yaml` is intentionally unchanged.
