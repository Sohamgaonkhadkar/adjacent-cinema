# Configuration reference

Every variable the application reads, which service needs it, and what the
product does when it is absent. **Nothing here is required to run, test or
review the application**: with no variables set at all the backend starts, all
four routes render, fixture runs complete end-to-end, and each provider-gated
feature reports an honest `unavailable`/`blocked` state instead of inventing
data.

Two deployment services read these values:

| Service | What runs there | Reads |
|---|---|---|
| **Backend** — Render (`adjacent-cinema-api`, FastAPI) | Qloo calls, SQLite persistence, YouTube OAuth, optional LLM synthesis, public-demo guardrails | every variable in the *Backend* tables below |
| **Frontend** — Vercel (`adjacent-cinema-web`, Next.js) | pages + same-origin `/api/*` proxy and trusted client-IP attestation | `ADJACENT_API_ORIGIN`, optional `ADJACENT_PROXY_SHARED_SECRET` |

`ADJACENT_API_ORIGIN` is read at **build time** by `frontend/next.config.ts` and
is never exposed to browser JavaScript: the browser only ever calls relative
`/api/...` paths. `ADJACENT_PROXY_SHARED_SECRET`, when configured, is read only
by the server-side Next.js proxy and backend; it must never use a `NEXT_PUBLIC_`
prefix. No provider credential is read by browser code or returned by an API
response, a trace row or a log line.

> Secrets belong in the service's dashboard environment (Render → Environment,
> Vercel → Project Settings → Environment Variables) or in a local `.env` that is
> never committed. `deploy.env.example` is the only committed template and
> contains no values.

---

## 1. Backend — required for production

| Variable | Required | Default | Absent means | Notes |
|---|---|---|---|---|
| `QLOO_API_KEY` | to run **live** analysis | unset → mock mode | `POST /run` and `POST /creator/run` fail honestly (`status: "failed"`, `error: "QLOO_API_KEY not configured"`, `result: null`); `/run/demo` fixture runs still work | Server-side only. Never logged; `/api/health` reports presence as `qloo_configured` plus a SHA-256 fingerprint, never the key |
| `QLOO_BASE_URL` | no | `https://hackathon.api.qloo.com` | uses the hackathon host | Staging/production Qloo hosts reject the hackathon key with 401 — do not repoint this |
| `QLOO_TRUSTED_BASE_URL` | no | same as `QLOO_BASE_URL` | uses the default | Read by the official `@qloo/qloo-harness` probe so both sides agree |
| `ADJACENT_EXPERIMENTS_DB` | yes, on Render | `./experiments.db` under the backend dir | writes to the container filesystem and is lost on redeploy | Render Blueprint sets `/data/experiments.db` on the mounted disk. Must be on a persistent volume |
| `ADJACENT_FILMSPONSOR_GUEST_ORIGINS` | yes, if FilmSponsor is public | empty → guest sessions refused | FilmSponsor shows *“Guest-demo origin is not allowed.”* | Exact frontend origin, e.g. `https://adjacent-cinema.vercel.app`. Comma-separate multiple origins. Never `*` |

## 2. Backend — deployment posture

| Variable | Values | Effect |
|---|---|---|
| `ADJACENT_PUBLIC_DEMO` | `1` / unset | `1` switches on anonymous-demo guardrails: bounded runs, transient run reads, no shared experiments, no YouTube, no synthesis, and sanitised failure text |
| `ADJACENT_PROXY_SHARED_SECRET` | optional; identical value on the paired Vercel frontend and Render backend | When set on both sides, Next.js strips caller-supplied attestation headers and stamps a single Vercel-validated client IP with this token; the backend accepts that IP only with a constant-time token match. Render-direct requests fall back to its `CF-Connecting-IP` edge header. If unset, no custom attestation is trusted and the backend falls back to the trusted edge/socket IP; per-client quotas for Vercel-proxied users may collapse into one shared bucket |
| `ADJACENT_PUBLIC_LIVE` | `1` / unset | Allows bounded **live** Cinema/Creator runs *in addition to* a configured `QLOO_API_KEY`. Requires `ADJACENT_PUBLIC_DEMO=1`. Off means live runs are refused with an explanatory message and the labelled fixture path is offered instead |
| `ADJACENT_FILMSPONSOR_GUEST_DEMO` | `1` / unset | Enables the guest workspace (no account) used by `/creator/sponsor`. **Only takes effect when `ADJACENT_PUBLIC_DEMO=1`** and at least one origin is listed in `ADJACENT_FILMSPONSOR_GUEST_ORIGINS`; otherwise `/api/health` reports `filmsponsor_guest_enabled: false` and the page shows the honest blocked state |
| `ADJACENT_FILMSPONSOR_GUEST_COOKIE_SECURE` | `1` (default) | Keep `1` on HTTPS. Set `0` **only** for plain-HTTP local development, and only for `http://localhost`/`http://127.0.0.1` origins — insecure cookies are rejected for any other origin |
| `ADJACENT_CORS_ORIGINS` | comma-separated origins | Only needed if the browser calls the backend **directly**. The shipped topology uses the same-origin Next.js proxy, so this stays empty. `*` is ignored |

## 3. Backend — optional provider integrations

| Variable | Feature | Absent means | Where it belongs |
|---|---|---|---|
| `ADJACENT_LLM_API_KEY` | Optional Decision-Brief synthesis (`POST /creator/synthesize`) | `GET /creator/synthesis-status` returns `available: false` with a `blocked_reason`; the route returns 503 `LLM synthesis not configured (ADJACENT_LLM_API_KEY unset)`. The deterministic product is complete without it | Backend only |
| `ADJACENT_LLM_BASE_URL` | OpenAI-compatible endpoint | unset → provider default | Backend |
| `ADJACENT_LLM_MODEL` | model id | unset → provider default | Backend |
| `YOUTUBE_CLIENT_ID` | YouTube Analytics observations | `/youtube/status` reports not configured; `GET /youtube/authorize` returns 503 with the env-var name | Backend |
| `YOUTUBE_CLIENT_SECRET` | as above | as above | Backend — **never** in the frontend |
| `YOUTUBE_REDIRECT_URI` | as above | as above | Backend; must match the Google Cloud OAuth client exactly, e.g. `https://adjacent-cinema.onrender.com/youtube/callback` |
| `ADJACENT_YT_TOKEN_DB` | refresh-token storage | `./youtube_tokens.db` next to the backend | Backend; put it on the persistent disk in production (`/data/youtube_tokens.db`) |
| `ADJACENT_YT_MOCK` | **test/demo only** | off | When `1`, YouTube routes serve clearly-labelled mock data (`data_status: "mock"`). Never enable in a deployment that claims live analytics |

## 4. Backend — tuning (all optional)

| Variable | Default | Purpose |
|---|---|---|
| `QLOO_CONNECT_TIMEOUT_S` | `1.5` | TCP connect budget |
| `QLOO_READ_TIMEOUT_S` | `8.0` | response read budget |
| `QLOO_MAX_RETRIES` | `3` | retries on transport/5xx |
| `QLOO_RETRY_BACKOFF_BASE_S` | `0.5` | exponential backoff base |
| `QLOO_RATE_LIMIT_RPS` | `3.0` | client-side rate limit |
| `QLOO_PROBE_CITIES` | `London, UK;New York, NY;Portland, Oregon` | cities the coverage probe queries. **Semicolon**-separated (a comma belongs to the city name) |

## 5. Frontend — required

| Variable | Service | Default | Absent means |
|---|---|---|---|
| `ADJACENT_API_ORIGIN` | Vercel (build time) | `http://127.0.0.1:8000` | Build succeeds but every `/api/*` call is proxied to a non-existent local backend, so the UI shows its honest “backend unreachable” states. Set it to the Render backend origin, e.g. `https://adjacent-cinema.onrender.com` |

## 6. Frontend — optional

| Variable | Default | Purpose |
|---|---|---|
| `NODE_VERSION` | — | Render/Vercel build image pin (`22`) |
| `PYTHON_VERSION` | — | Render backend image pin (`3.12.15`) |
| `ADJACENT_DEV_ORIGINS` | empty | **`next dev` only**, comma-separated origins allowed to fetch dev resources (HMR, chunks) cross-origin — needed for sandbox previews and tunnels, e.g. `3000-abc.e2b.app,localhost:3000`. Never set on a deployed service; the production build ignores it |

---

## Final live verification (owner step)

Everything below requires credentials this repository must not contain. Run it
once, on the branch, after the variables are in place.

1. **Health** — `GET https://<frontend>/api/health` must show
   `"qloo_configured": true`, `"mode": "live"`, and `filmsponsor_guest_enabled`
   matching your intent. A `key_fingerprint` of the form `sha256:…·len=NN`
   confirms the key is present without revealing it.
2. **Live Cinema run** — `/cinema`, live mode, with a real city and 3–6 films.
   Expect a `trace` stream then `completed`, `data_status: "measured"` on every
   artefact, real `call_id`s in the evidence trace, and a geography map drawn
   from returned cells. Any 401 from Qloo surfaces as
   `Qloo rejected the request (HTTP 401). Check backend key and host
   configuration.` — if you see that, the key is right and the host is wrong, or
   vice versa; do not work around it by pointing `QLOO_BASE_URL` at a
   non-hackathon host.
3. **Live Creator run** — `/creator`, live mode. Expect a fingerprint built from
   provider entities, the Positioning Arena with at least one `available`
   strategy (or a stated reason why not), and a Test Card. Then **save** it and
   confirm the experiment appears in the archive with its frozen snapshot.
4. **Idempotency spot-check** — press *Save* twice (or reload and retry): the
   second response must be `duplicate: true` and must not create a second row.
5. **FilmSponsor** — `/creator/sponsor`: guest session initialises (no
   “origin is not allowed”), discovery returns **real** brands from Qloo, a
   draft can be saved, a source review can be recorded, approval is refused
   until both exist, and the export downloads.
6. **YouTube (only if connected)** — `/creator`, archive: *Authorize* completes
   the Google consent screen, the video list is real, and recording an
   observation stores `data_status: "live"` metrics with provenance. If you do
   not connect it, the UI must show “not configured”/“authorize first”, never
   numbers.
7. **Optional synthesis** — with `ADJACENT_LLM_API_KEY` set,
   `GET /api/creator/synthesis-status` must report `available: true` with the
   provider and model. Without it, the same route must report
   `available: false` plus a `blocked_reason`, and the Decision Brief panel must
   say so.
8. **Failure honesty** — clear `QLOO_API_KEY` on a scratch service and repeat
   step 2: the run must fail with the configuration message and no result, and
   the labelled fixture path must still complete.

### Where to set each value

| Value | Render (backend) | Vercel (frontend) |
|---|---|---|
| `QLOO_API_KEY`, `QLOO_BASE_URL` | ✅ | ✗ (never) |
| `ADJACENT_PROXY_SHARED_SECRET` | ✅ on the matching backend | ✅ on the matching Vercel environment (Preview branch-scoped where appropriate) |
| `ADJACENT_EXPERIMENTS_DB`, `ADJACENT_YT_TOKEN_DB` | ✅ (on the `/data` disk) | ✗ |
| `ADJACENT_FILMSPONSOR_GUEST_ORIGINS` | ✅ (exact Vercel origin) | ✗ |
| `ADJACENT_PUBLIC_DEMO`, `ADJACENT_PUBLIC_LIVE`, `ADJACENT_FILMSPONSOR_GUEST_DEMO`, `ADJACENT_FILMSPONSOR_GUEST_COOKIE_SECURE` | ✅ | ✗ |
| `ADJACENT_LLM_API_KEY` / `_BASE_URL` / `_MODEL` | ✅ | ✗ |
| `YOUTUBE_CLIENT_ID` / `_CLIENT_SECRET` / `_REDIRECT_URI` | ✅ | ✗ |
| `ADJACENT_API_ORIGIN` | ✗ | ✅ (build-time) |

### External accounts to have ready

- **Qloo** hackathon API key (host `https://hackathon.api.qloo.com`).
- **Google Cloud** OAuth 2.0 client (Web application) with the YouTube Analytics
  read scope and the exact redirect URI you put in `YOUTUBE_REDIRECT_URI`.
  The consent screen must be published (or the account added as a test user).
- **An OpenAI-compatible LLM endpoint + key** — only if you want Decision Brief
  synthesis.
- **Render** account with a persistent disk for the API service, and a **Vercel**
  project for the frontend (the topology `docs/DEPLOYMENT.md` describes).
