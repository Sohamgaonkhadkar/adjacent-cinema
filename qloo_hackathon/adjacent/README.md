# Adjacent Cinema — developer guide

For the product story, architecture diagram and feature overview, start at the
[root README](../../README.md). The production application is live at
[adjacent-cinema.vercel.app](https://adjacent-cinema.vercel.app), with the Next.js
frontend on Vercel and the FastAPI backend on
[Render](https://adjacent-cinema.onrender.com). This guide focuses on development,
configuration and verification. Live Qloo requests are made by the backend and
require `QLOO_API_KEY` to be configured server-side; it must never be placed in
browser code or committed to this repository.

The Docker Compose and Render Blueprint deployment paths are documented in
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md); either requires a connected host or
hosting account and is not a hosted deployment by itself.

## Prerequisites and repository layout

- Python **3.12 or newer** for the backend (`pyproject.toml`); Python 3.12 is
  used by CI.
- Node.js **22** and npm for the frontend (Node 22 is used by CI).
- A Qloo key is optional for local fixtures and offline tests. Live Qloo
  workflows require `QLOO_API_KEY` in the backend process.

Important paths:

- `backend/app/api/` — FastAPI routes for run/SSE, Creator and experiment
  records, FilmSponsor, and YouTube.
- `backend/app/agent/`, `backend/app/domain/`, `backend/app/resolution/` —
  bounded agent flow, deterministic domain logic, experiment and FilmSponsor
  persistence, and film identity verification.
- `backend/app/qloo/` — Qloo client, typed response models, call tracing, and
  request parameter registry/validation.
- `backend/tests/` — fixture-backed tests, including guest-session isolation and
  public-demo boundaries.
- `frontend/app/` and `frontend/lib/` — Next.js pages and the browser API
  adapter.
- `scripts/` — Qloo probe and FilmSponsor live gate.
- `docs/` — contracts, Qloo setup, deployment proposal and validation notes.

Runtime databases, virtual environments and `.env` files are local data. See
`.gitignore`; never commit credentials or runtime campaign/experiment data.

## Local setup and start

From the repository root, start the backend in Terminal 1:

```bash
cd qloo_hackathon/adjacent
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
# Optional: edit .env locally, keeping secrets out of Git.
set -a && . ./.env && set +a
make run
```

`make run` starts Uvicorn on `0.0.0.0:8000`. The backend reads its environment;
it does not automatically load `.env`. Without a key, health reports mock mode.
The live client refuses construction without a key. Fixture routes are separate,
explicitly labelled endpoints.

Start the frontend in Terminal 2:

```bash
cd qloo_hackathon/adjacent/frontend
npm ci
ADJACENT_API_ORIGIN=http://127.0.0.1:8000 npm run dev -- --hostname 0.0.0.0
```

Open `http://localhost:3000`. Browser code uses same-origin `/api/*`;
`next.config.ts` performs the server-side rewrite. The local default backend
destination is `http://127.0.0.1:8000`. For a hosted frontend, set
`ADJACENT_API_ORIGIN` in the Next.js server/build environment. Never use
`NEXT_PUBLIC_*` for the backend URL or provider keys.

## Fixture and live Qloo modes

- **Offline fixture:** Creator Mode has `/creator/run/demo`; Cinema has
  `/run/demo`. Both are explicitly labelled and report `data_status: "fixture"`.
  Use `/creator?demo=fixture` or the in-page fixture buttons. No Qloo key is
  required.
- **Live:** `QLOO_API_KEY` must be set in the backend environment. Use the
  authorized hackathon API host (`QLOO_BASE_URL` defaults to
  `https://hackathon.api.qloo.com`). Never place a key in the frontend, commit
  it, or paste it into an issue/chat.
- **No silent fallback:** if live Qloo is unavailable, the request reports an
  honest failure; it does not switch to fixtures. FilmSponsor brand discovery
  returns 503 without a configured Qloo key and stores no substitute discovery.

To explicitly configure a key, use an approved secret manager or a local-only
`.env`, then export the file into the backend shell before starting Uvicorn. The
checked-in [`.env.example`](.env.example) documents Qloo host/timeouts,
public-demo flags, guest-mode flags, the Next.js proxy destination and optional
YouTube settings. Qloo's own setup notes are in
[`docs/QLOO_SETUP.md`](docs/QLOO_SETUP.md).

Useful no-key checks from this directory (with `ADJACENT_PUBLIC_DEMO` unset;
`make mock-run` uses a local debug route that public mode hides):

```bash
make probe       # dry-run/mock Qloo probe; no network call to live Qloo
make mock-run    # local fixture response
```

A measured live result must be verified from the run/report and its trace; a
configured key or healthy backend is not proof of a successful Qloo request.
After the authorized key is set, the commands for real calls are:

```bash
make probe-live
python scripts/filmsponsor_live_gate.py
```

Both commands make real Qloo requests and should only be run intentionally with
an authorized backend key. **They were not run for this README update.** The
live gate's status/output is not a pass if it says blocked or if a test was
skipped. See [`docs/NEXT_LIVE_CHECKLIST.md`](docs/NEXT_LIVE_CHECKLIST.md).

## Test and quality commands

Backend, from this directory with the Python environment active:

```bash
make test
make lint
make ci
```

Equivalent direct commands are `python -m pytest -rs` and
`python -m ruff check .`. The CI backend job uses Python 3.12 and runs lint,
fixture-backed tests and a dry-run probe. Its live-Qloo step is conditional on
the CI secret and can be skipped.

Frontend, from `frontend/`:

```bash
npm ci
npx tsc --noEmit
npm run build
```

The CI frontend job runs `npm ci` and `npm run build` on Node 22; Next's
production build includes TypeScript validation.

**CI status is commit-specific.** See the [latest GitHub Actions runs](https://github.com/Sohamgaonkhadkar/adjacent-cinema/actions) for the current commit. The CI workflow runs the Python 3.12 backend gates, frontend regression/build/route-smoke gates, and both container builds. The live-Qloo step runs only when the repository secret is configured; check whether it passed or was skipped. A passing workflow validates that commit's checks, not a hosted deployment, production browser behavior or long-term service health.
## Storage and data flow

- Run/SSE records live in an in-memory store and are not durable history.
- Creator experiments, observations and evaluations use SQLite. The default is
  `data/processed/experiments.db`; set `ADJACENT_EXPERIMENTS_DB` to override it.
- FilmSponsor stores campaigns, Qloo discovery reports, versioned drafts, source
  reviews and outreach records in the same SQLite workspace. Discovery evidence
  includes source/call identifiers and interpretation limits. Drafts and
  outcomes are creator-entered; affinity is not a sponsorship or commercial
  prediction.
- Optional LLM synthesis uses `ADJACENT_LLM_API_KEY` (and optional
  `ADJACENT_LLM_BASE_URL` / `ADJACENT_LLM_MODEL`) in the backend environment. It
  renders a completed investigation; deterministic investigation and Qloo
  execution do not depend on it. It is disabled in public-demo mode.

See [`docs/FRONTEND_CONTRACT.md`](docs/FRONTEND_CONTRACT.md) for API shapes and
page contracts.

## Public-demo and FilmSponsor guest security

Keep `ADJACENT_PUBLIC_DEMO` unset for ordinary local single-user development. Do
not expose that unauthenticated local mode directly to the internet. Public mode
is enabled only by `ADJACENT_PUBLIC_DEMO=1`; it blocks shared experiment access,
YouTube data/write routes, synthesis, debug endpoints and API docs, and allows
only bounded routes/labelled fixtures. Public live Cinema and Creator analysis
additionally require `ADJACENT_PUBLIC_LIVE=1` and a backend Qloo key. Rate limits are partly
process-local; a public host requires an external edge/API-gateway quota.

Public FilmSponsor guest workspaces are a separate opt-in and remain **off by
default**. Required backend settings:

```text
ADJACENT_PUBLIC_DEMO=1
ADJACENT_FILMSPONSOR_GUEST_DEMO=1
ADJACENT_FILMSPONSOR_GUEST_ORIGINS=https://exact-frontend.example
ADJACENT_FILMSPONSOR_GUEST_COOKIE_SECURE=1
ADJACENT_EXPERIMENTS_DB=/durable/local/path/experiments.db
```

Configure `ADJACENT_API_ORIGIN` server-side on Next.js so browser traffic goes
through the same-origin proxy and the API receives the expected Origin. Origins
must be exact; wildcard and URL paths are not accepted. Insecure cookies are
allowed only for explicitly configured localhost HTTP development, using
`ADJACENT_FILMSPONSOR_GUEST_COOKIE_SECURE=0` locally—not on a public host.

If the page says `Guest-demo origin is not allowed.`, copy the origin (scheme
and host only) from the deployed frontend's address bar and compare it with
`ADJACENT_FILMSPONSOR_GUEST_ORIGINS` in the Render **backend** environment. The
origin is the frontend hostname, not the Render API hostname. Prefer the stable
Vercel domain under Project Settings → Domains; deployment-specific preview
hostnames change. Multiple trusted origins are comma-separated; wildcards are
rejected. Backend logs identify `missing_origin`, `origin_mismatch`, or
`cross_site` without exposing the allowlist. After an environment change,
redeploy/restart the backend and check `/api/health` for
`filmsponsor_guest_enabled: true`.

The server issues an eight-hour HttpOnly/SameSite=Strict bearer cookie and a
CSRF helper cookie. Writes require the CSRF header and an exact allowed Origin.
Campaigns and their discoveries, drafts, reviews, approvals, exports and
outreach are owner-scoped; legacy rows without a guest owner are not
guest-visible. Limits include 500 active sessions, 120 API
requests/minute/session, 10 campaigns/session, global/per-campaign record caps
and a 16 KiB request-body limit. The guest feature does not grant access to
Creator experiments or other protected route families.

**Data retention and cleanup:** expiry immediately prevents authentication
and blocks further writes (SQLite triggers refuse inserts against an expired
session). Cleanup of expired session rows and their entire campaign tree
(campaigns, discoveries, drafts, source-reviews and outreach) is handled by:

1. **Opportunistic sweep** — every `issue_or_rotate` and `authenticate` call
   deletes any expired sessions it finds in the same transaction.
2. **Scheduled CLI command** — for the planned single-host OCI deployment, run
   the following on a regular schedule so cleanup happens even when no guest
   visits the app:

   ```bash
   # From the Adjacent root with the Python environment active:
   python -m app.cli cleanup-guest-sessions
   # Or with an explicit database path:
   python -m app.cli cleanup-guest-sessions --db /durable/path/experiments.db
   # Suppress output when nothing was cleaned (useful for cron):
   python -m app.cli cleanup-guest-sessions --quiet
   ```

   **Recommended cron entry** (run hourly; adjust for your retention posture):

   ```cron
   0 * * * *  cd /opt/adjacent && .venv/bin/python -m app.cli cleanup-guest-sessions --quiet
   ```

   Or as a **systemd timer** (`adjacent-guest-cleanup.timer`):

   ```ini
   [Unit]
   Description=Sweep expired Adjacent guest sessions

   [Timer]
   OnCalendar=hourly
   Persistent=true

   [Install]
   WantedBy=timers.target
   ```

   The command is idempotent, transaction-safe (uses `BEGIN IMMEDIATE` +
   rollback on error), and safe to run concurrently with a live Uvicorn
   server. It opens its own short-lived connection and exits immediately.

   Session revocation (`DELETE /filmsponsor/guest-session`) deletes the
   campaign tree synchronously inside the request. The scheduled command
   catches sessions that expired without an explicit revoke.

SQLite runs in WAL mode and is intended for a durable **single-host local
filesystem**. Do not put the database/WAL on network storage or use independent
replica copies. A single backend process is the conservative baseline; global
HTTP limiter state is process-local. Before any public exposure, separately
configure HTTPS, durable storage, restrictive database/backup permissions,
appropriate encryption at rest, ingress-log redaction and external quotas. None
of those OCI/host controls has been verified in this repository. No deployment
manifest, OCI deployment or public URL is verified.

For the complete public route rules and current limits, see
[`docs/FRONTEND_CONTRACT.md`](docs/FRONTEND_CONTRACT.md) and
[ADR-006](docs/adr/006-deployment-topology.md) (a proposal, not a deployment
record).

## Architecture and status references

- [Qloo setup](docs/QLOO_SETUP.md)
- [Frontend/API contract](docs/FRONTEND_CONTRACT.md)
- [Deployment topology proposal](docs/adr/006-deployment-topology.md)
- [Decision Challenge design](docs/adr/007-decision-challenge.md) — necessity,
  stability and next checks recomputed from the run's own cached evidence
- [Live-Qloo checklist](docs/NEXT_LIVE_CHECKLIST.md)
- [Historical live-Qloo report](docs/LIVE_QLOO_VALIDATION.md) — historical only;
  not current connectivity proof
- [MIT license](../../LICENSE)

There is no separate contribution guide. Use GitHub issues/pull requests, and
never include credentials, confidential film material or personal data in a
commit.
