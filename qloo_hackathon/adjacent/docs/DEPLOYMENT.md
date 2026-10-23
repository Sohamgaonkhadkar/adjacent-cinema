# Single-host deployment (Docker Compose + Caddy)

This runbook deploys the home page, Creator Mode, Cinema Mode, and FilmSponsor
on one host. Caddy terminates HTTPS; the FastAPI backend has no public host
port; Next.js proxies same-origin `/api/*` requests to the private backend
network. The SQLite workspace uses a persistent Docker volume.

## Render Blueprint option

The repository also contains a root-level `render.yaml` for a managed-host
deployment: a public Next.js frontend plus a private FastAPI service, both in
the same region. The backend has one worker and a persistent disk for SQLite;
the browser reaches it only through the same-origin Next.js proxy.

1. Connect this GitHub repository in Render and create a Blueprint from
   `render.yaml`. Select the branch you want to deploy. **This Blueprint is an
   alternative deployment path:** the current production topology uses Vercel
   for the frontend and Render for the FastAPI backend, with the source tracked
   from `main`.
2. When prompted for `ADJACENT_FILMSPONSOR_GUEST_ORIGINS`, enter the exact
   frontend origin assigned by Render (for example, its actual
   `https://…onrender.com` URL). Do not use a wildcard or the backend origin.
3. Leave `QLOO_API_KEY` unset for the first public rollout. The fixture
   experiences and pages work without it. Do not add the key to a public
   service until an upstream quota/access policy has been installed and live
   spend is explicitly approved.
4. Wait for the frontend and private API health checks, then open all four
   routes: `/`, `/creator`, `/cinema`, and `/creator/sponsor`. Check
   `/api/health` through the frontend URL and test a fixture run in a browser.
5. Review the selected Render compute plans and disk charges before confirming
   the Blueprint; this repository cannot approve billing for your account.

The Node.js build uses Node 22. The Render service-to-service origin is read at
build time and normalized in `frontend/next.config.ts`; it is not exposed to
browser JavaScript.

## FilmSponsor origin troubleshooting

The browser calls `/api/filmsponsor/guest-session` through the same-origin Next.js
rewrite. The backend sees the browser's frontend `Origin` header—not the Render
backend URL. That exact normalized frontend origin must be in the backend's
`ADJACENT_FILMSPONSOR_GUEST_ORIGINS` environment variable.

If FilmSponsor displays **“Guest-demo origin is not allowed.”**:

1. Open the deployed page that shows the error and copy only its origin from the
   address bar: scheme + hostname + optional non-default port; no path.
2. In Vercel, open the project **Settings → Domains** and identify the stable
   production domain intended for viewers. Prefer that domain over a commit- or
   branch-specific `*.vercel.app` preview hostname.
3. In the Render **backend** service, set
   `ADJACENT_FILMSPONSOR_GUEST_ORIGINS` to that exact frontend origin. Multiple
   explicitly trusted origins may be comma-separated if both are intentionally
   supported. Never use `*` or trust arbitrary Vercel subdomains.
4. Keep `ADJACENT_PUBLIC_DEMO=1`,
   `ADJACENT_FILMSPONSOR_GUEST_DEMO=1`, and
   `ADJACENT_FILMSPONSOR_GUEST_COOKIE_SECURE=1`. Save the backend environment
   and redeploy/restart that service.
5. Check `/api/health` through the frontend; in public-demo mode,
   `filmsponsor_guest_enabled` should be `true`. In browser DevTools → Network,
   inspect the POST to `/api/filmsponsor/guest-session`: its request Origin must
   match an exact configured origin. Backend logs distinguish
   `missing_origin`, `origin_mismatch`, and `cross_site` rejections without
   exposing the allowlist or session secrets.

Do not remove Origin validation, widen the allowlist, disable CSRF, or weaken
cookie/session ownership. If the stable production domain is not the hostname in
the address bar, either open the stable domain or add the actual hostname as a
second explicit origin only if it is meant to remain supported.

## Important boundaries

- This configuration is a **public fixture/demo profile**, not multi-user
  production hardening. Creator/Cinema run state is in memory and disappears on
  a backend restart; saved experiment records and FilmSponsor guest workspace
  data live in SQLite.
- Public live Cinema and Creator runs require `ADJACENT_PUBLIC_LIVE=1` plus a
  backend `QLOO_API_KEY`. Keep the flag off until external edge quotas/access
  controls are in place and the owner explicitly approves live spend. FilmSponsor
  guest discovery also uses the backend key when configured; never put the key
  in frontend variables or public source.
- No Qloo key is needed to render the pages or run the labelled fixture demos.
  Without a key, live FilmSponsor brand discovery responds as unavailable rather
  than fabricating results.
- This is one backend process with one persistent volume. Do not scale the
  backend to multiple replicas or point replicas at a shared network filesystem.
- No deployment host, DNS zone, or provider credentials are supplied by this
  repository. Running these commands on the intended host is what publishes
  the site.

## Requirements

A Linux host with Docker Engine and the Compose plugin, a DNS name you control,
and inbound TCP ports 80/443 (UDP 443 is optional). Create an A/AAAA record for
the domain pointing to the host. Do not deploy until DNS points to this host.

## Configure

From this directory on the host:

```bash
cp deploy.env.example .env
# Edit DOMAIN and ADJACENT_FILMSPONSOR_GUEST_ORIGINS to the same exact
# https:// origin for the real domain. Leave QLOO_API_KEY blank for safe demo.
chmod 600 .env
docker compose config --quiet
```

Do not use a wildcard origin. Do not put the key in the frontend environment,
a `NEXT_PUBLIC_*` variable, this file in Git, or command output/screenshots.

## Build and start

```bash
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 backend frontend caddy
```

Caddy requests an HTTPS certificate automatically once the public DNS and
firewall are correct. Certificate issuance will fail while the sample domain
is still configured or the domain does not resolve to the host.

## Smoke check

```bash
curl -fsS https://${DOMAIN}/api/health
for route in / /creator /cinema /creator/sponsor; do
  curl -fsS -o /dev/null -w "${route} %{http_code}\n" "https://${DOMAIN}${route}"
done
```

The public health response should report `mode: public_demo`. Test the labelled
fixture buttons from a real browser. FilmSponsor guest state should remain scoped
to its own browser session. An HTTP 200 check does not prove live Qloo works.

## Live Qloo acceptance

Use the authorized Qloo host/key only. First validate privately with
`ADJACENT_PUBLIC_DEMO` unset and run the project's documented live gate
intentionally. To enable any live endpoint on a public site, add an upstream
edge/API-gateway rate limit and access policy, verify owner-scoped behavior and
request costs, then configure the backend-only `QLOO_API_KEY`. Do not set
`ADJACENT_PUBLIC_LIVE=1` without reviewing the public quota policy; it permits
bounded public Creator requests but is not an authentication layer.

## Operations

- Logs: `docker compose logs -f backend frontend caddy`
- Restart: `docker compose restart`
- Upgrade after reviewing a commit: pull the approved branch/commit, then
  `docker compose up --build -d`
- Stop services: `docker compose down`
- Restart without data loss: do not add `-v` to `docker compose down`.
- Back up the SQLite file from the mounted `adjacent_data` volume before
  upgrades or maintenance.
- The backend must stay at one worker for its process-local run store/limits.
