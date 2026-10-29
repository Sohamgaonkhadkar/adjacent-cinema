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

## Current hosted status

The current split deployment uses [Vercel for the frontend](https://adjacent-cinema.vercel.app) and [Render for the API](https://adjacent-cinema.onrender.com). The most recent functional release is [PR #29](https://github.com/Sohamgaonkhadkar/adjacent-cinema/pull/29), commit [`7e93e15`](https://github.com/Sohamgaonkhadkar/adjacent-cinema/commit/7e93e153ec39d4e85e9c4c34c6d9f98f3ca29880); its CI run [40906289638](https://github.com/Sohamgaonkhadkar/adjacent-cinema/actions/runs/40906289638) passed backend, frontend and container-build jobs. The follow-up documentation release [PR #30](https://github.com/Sohamgaonkhadkar/adjacent-cinema/pull/30) passed the same jobs in [run 40907360747](https://github.com/Sohamgaonkhadkar/adjacent-cinema/actions/runs/40907360747). The 29 October production route smoke check returned HTTP 200 for `/`, `/creator`, `/cinema` and `/creator/sponsor`; this is a dated observation, not a continuing uptime guarantee. The expanded live-Qloo evaluation is linked below and is distinct from browser acceptance.

The project owner confirmed three browser walkthroughs as passed on 29 October: FilmSponsor guest/campaign and live discovery with Origin/cookie/CSRF checks; second-session isolation plus revocation/expiry; and Audience Pulse link/vote/repeat-response/close/evaluate. These are owner-confirmed results recorded in the checklist, not browser telemetry independently captured by this README update. Earlier Render logs include origin-mismatch rejections, so the successful flow does not remove the separate open item to confirm trusted-proxy configuration alignment. This is not a full security audit or uptime guarantee.

The public demo intentionally disables optional LLM synthesis and shared experiment APIs. `/api/creator/synthesis-status` reports synthesis unavailable; `/api/experiments` returns 403 by design. See the root [hackathon fit and verification notes](../../README.md#fit-to-the-qloo-agentic-hackathon) for the judge walkthrough and evidence limitations.

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

## Live counterfactual evaluation

Two live-Qloo reports are preserved separately; the original three-programme result has not been overwritten.

- Historical baseline, schema `adjacent.live-counterfactual-evaluation/1`: [Markdown](docs/verification/live_counterfactual_evaluation.md) · [JSON](docs/verification/live_counterfactual_evaluation.json)
- Latest expanded evaluation, schema `adjacent.live-counterfactual-evaluation/2`, generated 29 October 2026: [Markdown](docs/verification/live_counterfactual_evaluation_v2.md) · [JSON](docs/verification/live_counterfactual_evaluation_v2.json)

The `/2` report executed the **nine prespecified programmes** using the production live runner and the existing Decision Challenge on each same cached run. Results: **9 attempted, 8 evaluable, 1 not evaluable**. For the eight evaluable programmes, affinity-withheld ranking changed the winner in **0/8** runs, while popularity-only changed the winner in **8/8**. No structurally sized cohort was suppressed by the affinity gate, and affinity did not decide the first separating adjacent pair in these runs.

The non-evaluable ninth scenario, regional-language cinema, is retained in the report: no film references resolved to admitted candidate cohorts, so there was no recommendation to challenge. The pipeline did not fill the gap with fixtures or inferred evidence. This is an explicit insufficiency outcome, not a failed programme silently removed from the denominator.

Across the eight evaluable programmes, mean top-five overlap with the production ranking was **1.000** after withholding affinity-derived ordering keys and **0.950** for popularity-only. Mean Kendall tau-b was **1.000** for affinity-withheld and **-1.000** for popularity-only. These are within-pool ranking-agreement measurements, not external ground truth; they do not establish that a recommendation is correct or predict attendance, audience size, conversion, revenue or ROI.

The `/2` report includes **28/28 scoring contexts** with `not_requested_limit` explainability status: each context had 50 requested candidate IDs, above the configured 12-candidate attribution bound. Some inputs remained unresolved (including Taipei Story); unresolved identities were not replaced with fixtures. No per-seed contribution is claimed from these contexts.

The `/v2/analysis/compare` call is bounded and traced, but the public Qloo documentation does not define a verified response schema and this repository has no verified response sample. The reader therefore refuses to interpret numeric fields; report rows may show `unsupported_response_shape`. This is an intentional evidence boundary, not a measured similarity result.

To reproduce the expanded evaluation using an authorized live `QLOO_API_KEY`:

```bash
python research/scripts/live_counterfactual_evaluation.py --output-dir docs/verification --limit 9
```

The evaluator refuses to run without a live key and never silently uses fixture data. Application trace IDs are generated by Adjacent, scoped to individual runs, and are not Qloo-issued request IDs. The report states the limitations and preserves unevaluable runs rather than presenting a more flattering denominator.

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

## Evidence surfaces added on top of the ranking

Both surfaces below are additive: they never alter the programme, the cohorts or
the ranking, and they spend no provider call beyond the ones named.

- **Comparables Audit** and **Why this result?** — the former makes a capped set of explicit Qloo
  compare calls between resolved references. The public Compare reference does
  not document the response payload schema, so the current reader reports
  `no_readable_field` instead of interpreting guessed metrics; fixture rows are
  `not_modelled_in_fixture`, and failures remain `failed`. Each pair carries its
  call id. A pair with no value is unevaluated, not refuted, and the audit
  short-circuits after an upstream failure instead of retrying blindly. A failed
  compare carries its failure class (`timeout`, `authentication`, `upstream`, …)
  and HTTP status, never the exception text or the response body, and a call that
  never left the process is not charged to the run's budget.
- **Qloo Impact Lab** and **Why this result?** — the three-condition
  counterfactual table (`full_analysis`, `affinity_withheld`, `popularity_only`)
  and the bounded per-seed attribution panel. Kendall tau-b is reported as
  `not computable` when it is undefined rather than as `0.0`; no payload uses the
  words probability, confidence or likelihood.

## Audience Pulse (optional pre-registered poll)

A saved Test Card can become a small audience poll. The creator writes the
question, 2–5 options, the collection window and the decision rule **before** any
response is collected; the first stored response freezes that definition in the
database (a trigger rejects later edits to the question, options, rule,
hypothesis or window). Evaluating applies the frozen rule:

- `SUPPORTED` — the chosen option's share of valid responses is at or above the
  pre-registered threshold, with the creator's minimum sample met;
- `CONTRADICTED` — that sample exists and the share is lower;
- `INCONCLUSIVE` — fewer responses than the rule requires, no responses, or the
  rule cannot decide. A handful of votes never becomes a result.

Sharing is off by default. Set `ADJACENT_PULSE_SHARE_ENABLED=1` to serve the
participant link; without it, creation returns 503 and says why. The participant
surface is one token-scoped GET and one POST, both rate-limited, bounded by the
collection window and a per-poll ceiling of 5,000 responses; the POST requires the
`HttpOnly` session cookie that the GET issued and refuses a second response from
the same session. Only a SHA-256 digest of that cookie is stored — no raw cookie,
no IP address, no account. The owner routes live under `/experiments/…/pulse`
and stay blocked by the public-demo guard, so enabling the flag on a public host
opens exactly the ballot, not the experiment API.

Counts are stored responses, never estimates: an empty poll reads as zero
responses, and unresolved entries are reported separately. The sample is whoever
opened the link, so the evaluation says in its own words that it is
self-selected, is not attendance, revenue or an audience prediction, and does not
establish anything about the wider audience.

Files: `backend/app/domain/pulse.py` (validation, tabulation, evaluation),
`backend/app/domain/pulse_repository.py` (schema, trigger, storage),
`backend/app/api/pulse_routes.py` (owner + participant routes),
`frontend/lib/pulse.ts`, `frontend/components/nf/AudiencePulse.tsx`,
`frontend/app/pulse/[token]/page.tsx`. Contract and limits:
[`docs/FRONTEND_CONTRACT.md`](docs/FRONTEND_CONTRACT.md) §6b.

## MCP server (optional)

`backend/app/mcp_server.py` exposes three read-only tools —
`analyze_film_positioning`, `compare_film_groups`, `get_evidence_report` — over
the same runner and reader the app uses. Fixture mode is the default; live mode
requires `ADJACENT_MCP_ALLOW_LIVE=1` plus a key and is capped per session.

```bash
python -m pip install -e '.[mcp]'
PYTHONPATH=backend python -m app.mcp_server        # stdio transport
python -m pytest backend/tests/test_mcp_server.py -q
```

See [`docs/MCP_SERVER.md`](docs/MCP_SERVER.md) for the tool table, the client
configuration and the safety properties. There is no public endpoint.

## Test and quality commands

Backend, from this directory with the Python environment active:

```bash
make test
make lint
make ci
```

Equivalent direct commands are `python -m pytest -rs` and
`python -m ruff check .`. Targeted backend suites, all offline:

```bash
python -m pytest backend/tests/test_audience_pulse.py -q       # Audience Pulse (51)
python -m pytest backend/tests/test_pairwise_comparison.py -q  # /v2/analysis/compare reader (24)
python -m pytest backend/tests/test_impact_lab.py -q           # tau-b, overlap, receipt (11)
python -m pytest backend/tests/test_comparables_audit.py -q    # Comparables Audit (12)
python -m pytest backend/tests/test_bounded_attribution.py -q  # Why this result? (7)
python -m pytest backend/tests/test_mcp_server.py -q           # MCP adapter (39, skipped without the mcp extra)
```

The CI backend job uses Python 3.12 and runs lint, fixture-backed tests and a
dry-run probe. Its live-Qloo step is conditional on the CI secret and can be
skipped.

Frontend, from `frontend/`:

```bash
npm ci
npx tsc --noEmit
npm run build            # required before test:render
```

Every `npm run test:*` suite is wired into CI; `node --experimental-strip-types
--test tests/<file>.test.mjs` runs one directly if you are iterating.

| Suite | Covers | Tests |
|---|---|---|
| `test:recovery` | run recovery after reload | 3 |
| `test:layout` | responsive layout assertions | 4 |
| `test:creator-ui` | failure-stage visibility | 8 |
| `test:positioning` | Cultural Multiverse selection policy | 10 |
| `test:entity-display` | entity rendering and fingerprint a11y | 3 |
| `test:contract` | frontend/backend request contract, idempotency | 11 |
| `test:challenge` | Decision Challenge view model, Impact Lab, receipt export | 31 |
| `test:comparables` | Comparables Audit view model | 8 |
| `test:explainability` | "Why this result?" panel | 8 |
| `test:pulse` | Audience Pulse view model and form validation | 35 |
| `test:proxy` | trusted client-IP proxy headers | 3 |
| `test:render` | production-rendered routes (needs `npm run build`) | 1 |

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
default in local configuration**. The current hosted health response reports
`filmsponsor_guest_enabled: true`; this flag confirms enablement, not the complete
browser Origin/cookie/CSRF/session-isolation contract. Required backend settings:

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
appropriate encryption at rest, ingress-log redaction and external quotas. The OCI single-host deployment is not claimed. The split Vercel/Render public URL
is currently deployed and was smoke-checked as described near the top of this guide.
The hosted app is not thereby certified for production multi-tenancy: in particular,
confirm the exact FilmSponsor Origin/cookie flow and trusted-proxy configuration
before relying on it beyond the bounded hackathon demo.

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
- [Current live-Qloo checklist](docs/NEXT_LIVE_CHECKLIST.md)
- [MIT license](../../LICENSE)

There is no separate contribution guide. Use GitHub issues/pull requests, and
never include credentials, confidential film material or personal data in a
commit.
