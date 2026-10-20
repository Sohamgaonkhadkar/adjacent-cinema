# Adjacent Cinema

**Adjacent** is a cultural decision-support product for independent filmmakers, with a preserved **Cinema Mode** for venue programming. Creator Mode follows a bounded, auditable path:

> cultural evidence → hypothesis to test → experiment → observation → evaluation

Qloo signals are framed as **cultural affinity**, not audience size, viewing probability, attendance, conversion, or revenue. An affinity signal can inform a hypothesis; it does not prove that anyone will watch a film. When evidence is missing, ambiguous, or insufficient, Adjacent says so rather than filling the gap with a plausible answer.

## Try the labelled demo

The fixture demo runs without a Qloo key and is explicitly labelled as fixture data throughout the run, evidence trace, and result. It is not a live-Qloo substitute.

1. Start the backend and frontend using the steps below.
2. Open `http://localhost:3000/creator?demo=fixture`, or visit `/creator` and choose **View labelled fixture demo (offline)**.
3. Use `/cinema` to explore the separate cinema-programming surface.

The live Creator path is available to an authorized local operator when `QLOO_API_KEY` is configured in the **backend process**. The browser only calls the same-origin `/api` path; Next.js proxies it server-side. A missing key or failed live request is an honest failure, never a switch to fixtures.

## Local development

The backend targets Python 3.12 or newer. Install and start it from `qloo_hackathon/adjacent`:

```bash
cd qloo_hackathon/adjacent
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
make test
make lint
make run
```

In a second terminal:

```bash
cd qloo_hackathon/adjacent/frontend
npm ci
ADJACENT_API_ORIGIN=http://127.0.0.1:8000 npm run dev -- --hostname 0.0.0.0
```

Then visit `http://localhost:3000`. For a production Next.js deployment, set the server-side `ADJACENT_API_ORIGIN` to the backend service origin wherever the host evaluates `next.config.ts` (typically at build time). Do not put the backend URL or Qloo key in a `NEXT_PUBLIC_*` variable. Direct browser-to-backend requests are not the supported path.

## Live Qloo setup

1. Configure `QLOO_API_KEY` through an authorized local environment or deployment secret manager; never commit it, put it in client-side configuration, or paste it into an issue or chat.
2. Use the hackathon API host from `.env.example` unless the authorized Qloo setup specifies otherwise.
3. Start/restart the backend and use **Analyse cultural position** in Creator Mode.
4. Confirm the run itself reports `data_status: "measured"` and inspect its trace. A health status or a skipped live test is not proof of a successful live run.

Without a key, `/creator/run` fails honestly; `/creator/run/demo` is the separate fixture path. See [`qloo_hackathon/adjacent/docs/NEXT_LIVE_CHECKLIST.md`](qloo_hackathon/adjacent/docs/NEXT_LIVE_CHECKLIST.md) for the current live-validation gate.

## What the product preserves

- **Bounded, deterministic agent:** typed Qloo operations, explicit phases and stop reasons, per-run limits, no generic chatbot loop, and no silently substituted fixture output.
- **Entity safety:** a candidate is usable only after title/year verification; an external-ID hit does not override a contradictory title or year, and an explicitly different IMDb ID is a mismatch. Ambiguous, mismatched, and unresolved inputs remain unusable.
- **Evidence provenance:** Qloo calls carry trace IDs; facts, interpretations, hypotheses, limitations, and unknowns remain distinct. Fixture and measured statuses stay separate.
- **Testable decisions:** Creator Mode produces a positioning bet and Test Card. Saving, adopting, editing, observing, and evaluating remain distinct lifecycle steps; saved provenance is immutable and request-idempotent.
- **Sponsorship workflow (FilmSponsor):** a bounded Creator Mode surface for sponsorship campaigns — live Qloo brand discovery with per-query evidence and interpretation limits, creator-written sponsorship drafts (versioned), an official-source review step required before approval, approval-gated export, and manual outreach/outcome recording (observed zero ≠ missing). Without a configured Qloo key, brand discovery reports an honest unavailable state — no brands, affinity values, or outcomes are ever fabricated.
- **Cinema Mode:** remains available at `/cinema`; venue programming is not replaced by the Creator workflow.
- **Optional integrations:** grounded synthesis is provider-gated. YouTube Analytics is a single-connection, creator-authorized local integration, not a public multi-user service. No locally trained model is claimed.

## Public-demo posture

There is no verified public deployment at the time of this update. Before exposing the API anonymously, set `ADJACENT_PUBLIC_DEMO=1` in the backend environment. This mode:

- keeps Qloo credentials server-side and accepts only bounded Creator requests plus fixed, labelled fixture runs;
- caps total HTTP traffic at 120 requests per API-observed peer IP/minute, 2,400 requests/process/minute, and 64 in-flight requests (including SSE streams); run creation is additionally capped at 2 live or 12 fixture runs per peer IP/hour, 12 live or 60 fixture runs/process/hour, and 2 live or 4 fixture runs in flight;
- caps POST body sizes and keeps at most 100 completed volatile run records; completed records older than six hours are pruned on create/read. Behind a same-origin proxy, several users may share the API's peer-IP bucket;
- blocks shared experiment reads/writes, YouTube authorization/data/write routes, synthesis execution, debug endpoints, and API documentation; the YouTube status route reports disabled;
- redacts raw provider/internal failure details from public run responses, SSE error events, and trace rows while keeping safe status and call provenance;
- disables live Creator runs unless the owner separately sets `ADJACENT_PUBLIC_LIVE=1` **and** configures the backend Qloo key;
- uses exact-origin CORS configuration when direct cross-origin use is needed; the supported browser flow is the same-origin Next.js proxy.

The limits are process-local, not a replacement for an edge/API gateway quota. A multi-worker or replicated deployment needs an external shared limiter and must review run-data privacy before enabling live Creator requests. Public live runs retain only a bounded, temporary in-memory result; do not submit confidential or unreleased material to an anonymous demo. Shared experiment storage and the single-connection YouTube integration remain disabled in public-demo mode.

## Validation and deployment status

**Evidence snapshot: 19 October 2026.** The checked sandbox shell had no `QLOO_API_KEY` (and no `QLOO_BASE_URL` override); no live Qloo call was made. A no-key contract test reports mock mode, while the earlier local API preview explicitly ran in `public_demo` mode with fixtures available and live unavailable. The 6 October live report is historical and includes a Taipei Story / Purple Rose of Cairo mapping mismatch. Offline regressions now enforce title/year agreement and reject endpoint disagreement, but current Qloo behavior still requires an authorized live rerun. Release commit `485e06a` passed GitHub's Python 3.12 backend and frontend CI jobs; its conditional live-Qloo step was skipped, not passed, and is not proof of a live call.

No public deployment URL, deployment record, or deploy manifest was found. Do not treat a local preview or a fixture run as a hosted/live result. The full current-session evidence and remaining gates are recorded in [`qloo_hackathon/adjacent/docs/FINALIZATION_STATUS.md`](qloo_hackathon/adjacent/docs/FINALIZATION_STATUS.md).

## Repository map

- [`qloo_hackathon/adjacent/backend/`](qloo_hackathon/adjacent/backend/) — FastAPI, explicit agent, typed Qloo integration, entity resolution, provenance, experiment lifecycle, and YouTube boundary.
- [`qloo_hackathon/adjacent/frontend/`](qloo_hackathon/adjacent/frontend/) — Next.js Creator and Cinema interfaces; browser API calls use `/api`.
- [`qloo_hackathon/adjacent/docs/`](qloo_hackathon/adjacent/docs/) — architecture, API contract, verification history, and current gates.
- [`LICENSE`](LICENSE) — MIT.
