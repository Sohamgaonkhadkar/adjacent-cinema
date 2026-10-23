# Zero-cost preview deployment

This guide deploys the current feature branch using **Vercel Hobby for Next.js** and a **Render Free web service for FastAPI**. It avoids the paid plans and persistent disk in the default `render.yaml`.

This is a hobby/demo arrangement, not a durable production deployment. Render Free services sleep after 15 minutes without traffic and their local files are lost on spin-down, restart or redeploy. The SQLite-backed experiment and FilmSponsor records can disappear. Keep `QLOO_API_KEY` unset and public live Qloo disabled for this preview.

## Cost and limits

- Vercel Hobby: $0/month for eligible personal, non-commercial projects; see the [current plan](https://vercel.com/docs/plans).
- Render Free web service: $0/month within the included usage; see [Render's free-service limits](https://render.com/docs/free).
- No paid domain, persistent disk, paid database or Qloo key is needed for the fixture demo. Use the default HTTPS hostnames.

Render free services have limited CPU/RAM, cold starts, ephemeral storage and included usage caps. Do not treat this as a reliable always-on website or a place to keep important records. Watch the hosting dashboards for usage/charge notifications and do not upgrade any service.

## Part A — deploy the backend on Render Free

1. Open the [Render Dashboard](https://dashboard.render.com/) and click **New → Blueprint**.
2. Connect `Sohamgaonkhadkar/adjacent-cinema`.
3. Set **Blueprint Path** to `render-free.yaml` (not the default `render.yaml`).
4. Select branch `arena/9d8b618a-adjacent-cinema`.
5. Review the preview: it must create exactly one **Web Service** named `adjacent-cinema-api-free` on the **Free** plan. It must not create a private service, a persistent disk or a paid frontend.
6. Deploy and wait for the service to become healthy.
7. Copy the service's actual public URL, e.g. `https://adjacent-cinema-api-free.onrender.com`. Use the exact URL shown by Render—do not assume the example hostname is available.
8. Open `https://YOUR-API-URL/health`. It should return HTTP 200 and report public/demo mode with live Qloo disabled.

No `QLOO_API_KEY` is set by this Blueprint. Do not add one for the first preview.

## Part B — deploy the frontend on Vercel Hobby

1. Open the [Vercel Dashboard](https://vercel.com/dashboard) and import `Sohamgaonkhadkar/adjacent-cinema` from GitHub.
2. Set **Root Directory** to `qloo_hackathon/adjacent/frontend`.
3. Select Node.js 22 if Vercel asks for a runtime version. Use the standard Next.js framework preset and build command `npm run build`.
4. Before the first production build, add the environment variable:
   - Name: `ADJACENT_API_ORIGIN`
   - Value: the actual Render backend origin copied in Part A, including `https://` and with no trailing slash/path.
   - Environment: the deployment environment you are using (Preview for a feature-branch deployment or Production for the configured production branch).
5. For a stable demo URL from the feature branch, configure the Vercel project's production branch as `arena/9d8b618a-adjacent-cinema` under Project Settings → Git, or use its branch-specific preview URL and configure the exact same origin below. This changes only Vercel's deployment branch setting, not GitHub's `main` branch.
6. Deploy and copy the actual HTTPS frontend origin assigned by Vercel.

The frontend uses a server-side Next.js rewrite from browser-relative `/api/*` requests to `ADJACENT_API_ORIGIN`. Keep provider secrets out of frontend variables. Do not create a `NEXT_PUBLIC_QLOO_API_KEY` variable.

## Part C — connect the exact frontend origin to guest sessions

1. Return to the Render backend service → **Environment**.
2. Set `ADJACENT_FILMSPONSOR_GUEST_ORIGINS` to the exact Vercel origin, such as `https://YOUR-PROJECT.vercel.app`—origin only, no path, wildcard or trailing slash.
3. Leave these safety settings intact:
   - `ADJACENT_PUBLIC_DEMO=1`
   - `ADJACENT_PUBLIC_LIVE=0`
   - `ADJACENT_FILMSPONSOR_GUEST_DEMO=1`
   - `ADJACENT_FILMSPONSOR_GUEST_COOKIE_SECURE=1`
4. Save changes and redeploy/restart the backend if Render does not do so automatically.

The backend has a public URL in this free arrangement; the request guard and disabled live mode are important. Do not enable public live Qloo without separate access controls, upstream quotas and explicit approval of usage costs.

## Part D — verify the public demo

Replace `YOUR-PROJECT` and `YOUR-API-URL` with the actual URLs assigned by the providers:

```bash
curl -i https://YOUR-API-URL/health
curl -i https://YOUR-PROJECT.vercel.app/api/health
curl -I https://YOUR-PROJECT.vercel.app/
curl -I 'https://YOUR-PROJECT.vercel.app/creator?demo=fixture'
curl -I https://YOUR-PROJECT.vercel.app/cinema
curl -I https://YOUR-PROJECT.vercel.app/creator/sponsor
```

Then use a real browser to submit a Creator fixture request, try the Cinema fixture workflow, inspect FilmSponsor guest initialization, test the fingerprint interactions and export a Test Card as `.txt`. Verify the fixture label is present and there are no broken API requests in the browser network panel.

## What does not persist on this free stack

Render Free has an ephemeral filesystem. The database configured at `/tmp/experiments.db` is there only to let the demo workflows run; it is not durable. The service can lose saved experiments, observations, campaigns, drafts and guest sessions after idle spin-down, restart or deployment. Run/SSE history is process-local too. A free Render Postgres database is not a safe long-term substitute because Render states that its free databases expire after 30 days.

Use this deployment to demonstrate workflows, not to store real creator/campaign records. If durable data becomes necessary, stop and redesign the storage layer before migrating to a paid or independently free durable database.

## Troubleshooting

- **Vercel page renders but API calls fail:** check that `ADJACENT_API_ORIGIN` is correct in the environment for that deployment and redeploy Vercel.
- **First request is slow or shows a wake-up page:** Render Free may have spun down; wait for the backend to start and retry.
- **FilmSponsor guest workspace is rejected by Origin/CSRF checks:** the Render variable must exactly match the Vercel origin that is open in your browser.
- **SQLite or saved data disappears:** expected limitation of the free filesystem; this deployment is not durable.
- **Blueprint offers paid resources:** cancel before confirming. You selected `render.yaml` instead of `render-free.yaml`.

For the paid/persistent Render topology, see [DEPLOYMENT.md](DEPLOYMENT.md). The existing paid `render.yaml` is intentionally unchanged.
