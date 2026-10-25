# M20 — Deployment and Judge-Readiness Analysis

**Observed:** 2026-10-25  
**Scope:** Production vs feature Preview, Vercel-to-Render API routing, live Qloo, Cinema identity input, public-demo rate limits, and the recommended judge path.

This note distinguishes **directly observed responses**, **repository configuration**, and **remaining owner actions**. HTTP 200 and a green build are necessary checks, not proof of every interactive flow.

## Executive summary

The Production and feature Preview are deliberately serving different frontend versions:

- **Production** (`https://adjacent-cinema.vercel.app`) currently serves the older UI. Its Cinema chapter rail contains **Cinema, Programme, Cultural field, Opportunity, Test**; it does not contain the newer **Challenge** chapter or the IMDb-ID field.
- **Feature Preview** (`https://adjacent-cinema-git-arena-41d4ba64-adja-d0737b-sohamgaonkhadkar.vercel.app`) serves the Nightfall port on PR #17. Its Cinema chapter rail includes **Challenge**, and its Cinema form includes an IMDb-ID field.
- Both `/api/health` endpoints returned HTTP 200. The production route is not failing merely because its UI is older: the same-origin API proxy reaches a backend in both environments.
- The deployed Render services are public **Web Services**: Production tracks `main`; the separate Preview service tracks `arena/41d4ba64-adjacent-cinema`. The root `render.yaml` describes an alternative Blueprint topology using a private backend, not the topology currently inspected in the Render dashboard.
- Live API smoke tests on the feature-branch Preview previously produced measured Qloo-backed Cinema, Creator, and FilmSponsor results. CI also passed on commit `481b12d99c6ff8ba08af102ff98689150c8fb316`. The follow-up rate-limit, identity-input, and run-start-timeout changes are on this same draft branch and must pass their own final CI/deployment checks before being treated as accepted.

## 1. Directly observed deployment probes

| Probe | Observed result | Interpretation |
|---|---|---|
| Production `GET /api/health` | HTTP 200; `service=adjacent-backend`, `mode=public_demo`, `fixture_demo_available=true`, `live_creator_available=true`, `filmsponsor_guest_enabled=true` | Production Vercel proxy reaches the Production backend, and the health response advertises live Creator and FilmSponsor guest capability |
| Production `GET /cinema` | HTTP 200; title `Adjacent — Cultural Intelligence for Independent Cinema`; five chapter labels; no Challenge chapter | The Production frontend has not yet received the Nightfall port/Decision Challenge version |
| Feature Preview `GET /api/health` | HTTP 200; same public-demo health shape; live Creator and FilmSponsor guest capability are true | Feature Preview frontend reaches its backend |
| Feature Preview `GET /cinema` | HTTP 200; title `Adjacent Cinema — Every film belongs to more than one world`; Challenge chapter and IMDb-ID input appear in rendered markup | The ported frontend is deployed to Preview |
| Feature Preview `GET /creator/sponsor` | HTTP 200 | Page renders; this alone does not prove browser guest-session and campaign interactions |
| Render services | Production service is a public Web Service tracking `main`; Preview service is a separate public Web Service tracking `arena/41d4ba64-adjacent-cinema` | Vercel can route through the public Render origins; do not infer reachability from the alternative `pserv` Blueprint alone |
| PR #17 | OPEN, draft=true, merged=false | Feature code remains isolated from `main` |

### Which build is the judge seeing?

Use these URLs intentionally:

- **Production:** [adjacent-cinema.vercel.app](https://adjacent-cinema.vercel.app)
- **Feature Preview:** [Cinema Mode Preview](https://adjacent-cinema-git-arena-41d4ba64-adja-d0737b-sohamgaonkhadkar.vercel.app/cinema)
- **Feature Preview FilmSponsor:** [FilmSponsor Preview](https://adjacent-cinema-git-arena-41d4ba64-adja-d0737b-sohamgaonkhadkar.vercel.app/creator/sponsor)
- **Draft PR:** [PR #17](https://github.com/Sohamgaonkhadkar/adjacent-cinema/pull/17)

The Production UI being older is expected while PR #17 remains draft. Do not describe the new design as live on the Production domain until the PR is approved/merged and a Production deployment is deliberately performed.

## 2. Live integration evidence

The following are API-level integration smoke tests against the feature-branch Preview backend. They used real provider calls; they were not fixture numbers.

| Workflow | Observed result |
|---|---|
| Cinema `POST /run` | Terminal status `completed`; `data_status=measured`; 6 programme items submitted; 4 resolved; 21 Qloo calls; `challenge.available=true` |
| Creator `POST /creator/run` | Terminal status `completed`; `data_status=measured`; 5/5 reference films resolved; 22 Qloo calls; 7 ranked cohorts; no run error |
| FilmSponsor guest flow | Guest-session creation and revocation HTTP 200; campaign creation HTTP 201; brand discovery HTTP 200; `data_status=measured`; 10 brand results from 6 provider call IDs; no outreach sent |
| CI before the follow-up fixes | GitHub Actions run #365 on `481b12d` passed backend (including live-Qloo tests), frontend, and container-build jobs |

A separate Creator probe with only two submitted comparables correctly returned `insufficient` when Qloo verified only one. The evidence gate was not weakened. A subsequent well-formed run with five references completed successfully.

**Limit:** these provider API checks do not substitute for a human clicking through the browser, checking visual behavior at desktop/mobile sizes, or completing the optional YouTube OAuth / LLM synthesis integrations. The page SSR/HTTP probes verify route availability and rendered content, not pixel fidelity.

## 3. Fixes on the feature branch

### Public-demo rate limiting behind Render

The screenshot showing `Public demo run capacity reached` exposed that the limiter used the socket peer address, which can represent a shared Render proxy rather than each visitor. The feature branch now derives a client bucket from Render's forwarded client IP, validates it as an IPv4/IPv6 literal, and falls back to the socket peer for a malformed or absent header. Both the live-run limiter and the general request guard use this helper.

Regression coverage checks IPv4/IPv6 parsing, malformed-header fallback, same-client throttling, and independent quotas for distinct client IPs. Global and concurrency quotas remain in place: live runs are capped at 2 per client/hour, 12 globally/hour, with at most 2 active per process. These are per-process public-demo limits, not authentication.

### Cinema identity resolution

The prior Cinema frontend blocked live analysis unless at least one IMDb ID was supplied. The actual backend resolver accepts optional IMDb IDs and attempts a typed Qloo `/search`, then verifies title/year/type; ambiguous or mismatched candidates remain unresolved rather than guessed. The feature branch removes the unnecessarily strict frontend hard gate. IMDb IDs remain available and are prefetched for the sample programme, but a title/year-only request can reach the backend's verified resolver.

The UI now explains that IMDb IDs improve precision while ambiguous matches are reported honestly. This keeps the frontend consistent with backend capability without weakening the resolver's match rules.

### Render cold starts and run-start requests

The ordinary API timeout remains 12 seconds. The feature branch gives only run-start requests a bounded 75-second budget to accommodate a sleeping free Render service. This applies to Cinema live/fixture starts and Creator live/fixture starts; polling, normal reads, and unrelated writes remain on the standard timeout. Timeout messages continue to warn that a run may already have been accepted, so users should check status before retrying.

## 4. Deployment configuration notes

- The currently inspected Production Render Web Service tracks `main`; the Preview Render Web Service tracks the feature branch. The Preview is a separate service so the UI and backend code versions can match while PR #17 is in draft.
- Vercel's `ADJACENT_API_ORIGIN` is a build-time, server-side rewrite target. Keep it server-only; do not rename it to a `NEXT_PUBLIC_*` variable.
- FilmSponsor must trust the exact frontend `Origin` through backend-only `ADJACENT_FILMSPONSOR_GUEST_ORIGINS`. Do not use wildcards or remove CSRF/origin validation.
- Qloo credentials belong only in Render backend secrets. Never commit credentials, print them in logs, or place them in frontend variables.
- The root `render.yaml` describes an alternative deployment topology in which Next.js and a private FastAPI service are both hosted on Render. The actual Production and feature Preview inspected here are Vercel frontend + public Render backend Web Services. Keep that distinction explicit when using the Blueprint.
- The API health response currently advertises live Creator and FilmSponsor guest availability. This is a public-demo profile; live Qloo calls remain bounded but the run limit is not an authentication or spending-control layer.

## 5. Judge walkthrough (about 60 seconds)

1. Open the **feature Preview**, not Production, while PR #17 remains draft.
2. Start with Creator Studio's labelled fixture option if you need a predictable, no-provider-call demonstration. Keep the fixture label visible; do not present fixture outputs as live Qloo evidence.
3. Open Cinema Mode and run the labelled fixture once to show the workflow and Decision Challenge. The Challenge chapter should be present between Opportunity and Test.
4. For the live Qloo proof, switch to live analysis, enter 3–6 real film titles and years, and add IMDb IDs when known. Wait for the run to finish; only call it live if the result reports measured data and trace/provider call IDs.
5. Open FilmSponsor, start the guest workspace, create a campaign, and run discovery. Only call discovery live if the result says measured and exposes real provider provenance.
6. If a public limit is genuinely exhausted, show the honest retry message; do not bypass the limiter by repeatedly restarting the backend.

## 6. Remaining work and release gates

1. **Final CI for the follow-up commits:** confirm GitHub Actions is green on the latest PR head after the rate-limit test, optional-IMDb change, and 75-second run-start timeout change. Confirm the latest Vercel Preview and Preview Render backend are ready on a matching revision.
2. **Browser interaction and visual review:** click through the fixture and live run flows in the browser; inspect desktop and mobile; check the MapLibre/WebGL geography view. HTTP/SSR checks do not replace this.
3. **Production release is a separate, owner-approved action:** PR #17 is still draft and Production intentionally serves the old UI. Do not merge or deploy the feature branch without explicit approval.
4. **Security hygiene:** because the Qloo key was pasted into a chat, rotate it in Qloo and update only the backend Render secret after verification. Confirm the new key works without printing or committing it. Do not include the secret value in this repository.

Not yet independently verified end-to-end: YouTube OAuth, the optional LLM synthesis provider response, and pixel-level browser comparison. They should remain described as unverified/optional rather than reported as successful.
