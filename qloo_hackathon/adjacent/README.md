# Adjacent — application and backend guide

See the [repository README](../../README.md) for the judge-facing overview, full local setup, public-demo posture, and current deployment status. This folder contains the Python API, Next.js frontend, fixtures, and detailed product/architecture documentation.

## Current product path

Creator Mode is the primary product surface: a bounded agent uses typed Qloo operations to resolve cultural references, inspect cultural-affinity signals, rank adjacent clusters, produce a positioning hypothesis/Test Card, and preserve traceable evidence. Cinema Mode remains available separately. Fixture data is a labelled offline demonstration; it is never substituted for a failed live request.

## Backend commands

Requires Python 3.12 or newer:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
make test
make lint
make run
```

The API listens on port 8000. With no `QLOO_API_KEY`, the health response reports mock mode; a live Creator request fails honestly. The labelled fixture path remains available:

```bash
make mock-run
```

## Frontend

```bash
cd frontend
npm ci
ADJACENT_API_ORIGIN=http://127.0.0.1:8000 npm run dev
```

Browser requests use relative `/api` URLs. Next.js rewrites these on the server using `ADJACENT_API_ORIGIN`; a production frontend must configure that server-side value. Do not use a browser-visible `NEXT_PUBLIC_*` backend URL or place a Qloo key in frontend configuration.

## Live Qloo and provenance

Configure `QLOO_API_KEY` only in the authorized backend runtime. Creator Mode's live path uses `EntityResolver`; title/year conflicts and ambiguous mappings are not usable. A supplied external ID must also agree with the input identity. Every trace reference remains addressable, and the run reports measured versus fixture status explicitly.

The October 6 live report in `docs/LIVE_QLOO_VALIDATION.md` is a historical observation, not proof of current connectivity. It recorded Taipei Story (`tt0089853`) mapping to The Purple Rose of Cairo and no Perfect Days resolution. Offline regressions now enforce safe mismatch/insufficiency behavior; rerun the live gate before claiming a current Qloo result.

## Storage and integrations

- Run records are held in an in-memory store. Public-demo mode retains a bounded, temporary recent window; it does not create durable run history.
- Experiments, observations, and evaluations use the existing append-only SQLite repository. Runtime databases are gitignored. Public-demo mode disables shared experiment reads and writes.
- YouTube Analytics is a single-connection integration with creator consent and stored tokens. It is not exposed in public-demo mode and must not be deployed as a public multi-user connection.
- Optional grounded synthesis is provider-gated; it is disabled in public-demo mode. No generic chatbot or locally trained model is claimed.

## Anonymous public-demo configuration

For an anonymous demo, set `ADJACENT_PUBLIC_DEMO=1` in the backend environment. Fixture runs remain available with body, rate, concurrency, and cache-retention bounds. Live Creator runs are off unless the owner explicitly sets `ADJACENT_PUBLIC_LIVE=1` and configures the server-side Qloo key. Shared experiments, YouTube, synthesis execution, debug endpoints, and OpenAPI/docs are blocked. Apply an edge/gateway quota too: the in-process limits do not coordinate across workers or replicas.

See `.env.example`, `docs/adr/006-deployment-topology.md`, and [`docs/FINALIZATION_STATUS.md`](docs/FINALIZATION_STATUS.md). No hosted deployment URL or manifest is currently verified.
