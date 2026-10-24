# M13.17 — Judge Demo, Safe Fallback, and Owner/ChatGPT Handoff

**Status:** review branch/CI evidence only; this is an operator checklist, not a deployment record. PR CI run #225 passed native Python 3.12 offline tests and 8 live-marked Qloo contract tests, including the direct explainability response shape. No hosted-production or browser acceptance was performed in this work session.

## Read-only deployment compatibility notes

- `render.yaml` defines a private FastAPI service on Python **3.12.15**, one Uvicorn worker and a persistent `/data` disk, plus a Node **22.23.4** Next.js service in the same region. It sets public-demo mode on, public-live mode off, enables the FilmSponsor guest-demo feature, and requires the exact frontend guest origin as an unsynced secret/config value.
- `frontend/next.config.ts` rewrites browser-relative `/api/*` requests server-side to `ADJACENT_API_ORIGIN`; the Qloo API key is not a frontend variable. Render's private `hostport` reference is normalized to an `http://` origin at Next config load/build time.
- FastAPI's direct CORS allowlist is opt-in through exact `ADJACENT_CORS_ORIGINS`; absent configuration it permits localhost development origins only. The intended browser-to-API path is the same-origin Next rewrite, so production browser calls should not need wildcard CORS.
- FilmSponsor guest-session origin checks use `ADJACENT_FILMSPONSOR_GUEST_ORIGINS`. `render.yaml` leaves it unset until the exact frontend origin is supplied. The backend should see the browser frontend `Origin` through the same-origin rewrite; the backend hostname is not the allowlist entry. Secure cookies remain enabled in the blueprint.
- The deployment runbook and README contain hosted URLs/configuration claims, but this review did not connect to, inspect, or operate any hosted service. Blueprint presence, a static build, and an old health record do not validate production. No deployment setting was edited.
- This remains a single-process/single-host demo topology: in-memory run/SSE state and process-local controls are not multi-replica durable. SQLite's persistent disk is distinct from volatile run state. Public live use still requires owner approval, secure Qloo credentials, and edge/API-gateway quotas.

## Short, honest demo path (3–4 minutes)

1. **Set the evidence boundary (15 seconds).** Say: “Affinity is cultural similarity, not audience size, views, attendance, sponsorship likelihood, or a forecast. The run status on screen says whether this is fixture or measured.”
2. **Creator — explain the decision (60–90 seconds).** Enter one film and a few comparable works/themes. Use only the explicit fixture route/button for an offline walk-through, and leave its `FIXTURE` badge visible. For a live presentation, first complete the owner handoff below; show the actual successful Qloo trace and resolved title/year/ID rather than relabeling a fixture.
3. **Inspect one cultural result (30–45 seconds).** Open the returned cohort/member and explain that attribution is shown only when the provider returns a valid attribution for one of the verified input seeds. If absent, say “not returned”/“unavailable”; do not translate absence into a zero.
4. **Edit the Test Card (30–45 seconds).** Review and, if appropriate, edit comparison protocol, primary measure, decision prompt, and observation window. The Cinema prompt is observational and cannot establish causality. Export the edited plain-text card and confirm the values match the visible fields.
5. **Save/reopen (30–45 seconds, private/local only).** Save as a planned experiment, refresh, reopen it, and verify the exact saved snapshot. Saving does not execute the test. Do not attempt shared experiment writes in anonymous public-demo mode; the public guard intentionally disables them.
6. **Cinema / FilmSponsor (optional 30 seconds).** Show Cinema's editable test guidance as observational. For FilmSponsor, use a disposable guest session/campaign only; without a measured Qloo brand-discovery response, say discovery is unavailable and do not show invented brands, scores, outreach, or outcomes.

### Offline fallback

- Use `/creator?demo=fixture` or the explicit fixture path in Cinema. Preserve the fixture notice throughout the walkthrough; fixture mode is not evidence of live provider success.
- If live mode is unavailable or fails, stop at the honest error state. Do not quietly switch to a fixture mid-run, change the `data_status`, or present a prior live/fixture artifact as a current run.
- Export the Test Card only as an experiment plan. It does not establish that an A/B split, screening, campaign or observation occurred.
- The frontend build, Node tests and render smoke are not browser-driven, hosted-production or live-provider checks. Describe their scope precisely.

## ChatGPT / authorized owner live-integration handoff

The direct Qloo endpoint contract has passed in PR CI, but integrated live application-path and hosted-production acceptance remain reserved to ChatGPT/the authorized owner. Use the trusted current runtime; never put a key in chat, a repository file, a browser bundle, screenshots, command history, or logs.

### A. Live Qloo acceptance (backend only)

1. Confirm the deployed/checked-out code revision and runtime configuration without printing secret values. Supply `QLOO_API_KEY` only through the trusted backend secret/environment mechanism. Confirm the Qloo base URL is the authorized hackathon host. Keep `ADJACENT_PUBLIC_LIVE=0` unless the owner explicitly approves public Qloo spend and edge quotas; a key alone is not authorization for anonymous public use.
2. Start with one small, non-confidential live Creator input. Check exact entity resolution (name/title, year and entity ID), the run's `data_status`, and the actual trace rows. A label alone is insufficient: confirm the successful trace source is Qloo, the HTTP status is successful, and each evidence call ID belongs to this run. Do not paste raw provider bodies or the secret.
3. For a bounded scoring context (at most 12 unique candidates), inspect whether the outgoing `/v2/insights` request includes `feature.explainability=true` and whether the provider response contains the documented `query.explainability.signal.interests.entities` shape. Confirm only returned finite scores in [0,1] for verified input-seed IDs are surfaced. If Qloo omits attribution, report it as missing, not zero.
4. If the live provider explicitly rejects that optional field with HTTP 400/422 and identifies `feature.explainability` as unsupported/invalid, the application may make **one** fallback request without it if its call budget allows. Verify both attempt IDs/statuses in trace, the operation note's rejected call ID, successful core scoring, and `unsupported` attribution status. Do not induce an unnecessary paid request just to test fallback in production. If the provider does not reject the field, no fallback claim is established by that live run.
5. Confirm unrelated 400/422 responses do not qualify; auth, 403, rate-limit, timeout, transport, server and unrelated validation failures must not be interpreted as explainability fallback. The offline `httpx.MockTransport` regression is a fixture test, not a provider test.

### B. Hosted production/browser acceptance (read-only; no production edits)

1. Verify the exact currently deployed frontend and backend revisions/builds using the provider's deployment dashboard/logs, without exposing secret values. Confirm the intended public host responds over HTTPS; do not equate the Render blueprint or a README URL with a current successful deployment.
2. From the public frontend origin, open `/`, `/creator`, `/cinema`, and `/creator/sponsor`; inspect browser Network requests. Confirm the browser calls same-origin relative `/api/*`, the Next server proxy reaches the backend, and no Qloo credential is present in requests, responses, source maps, or bundled code.
3. Check `/api/health` via the frontend proxy. Verify public-demo/live flags and `filmsponsor_guest_enabled` match the owner's intended configuration. Keep live public access off absent approved edge quotas and authorization policy.
4. Test Creator/Cinema fixture flows in a real browser and preserve the fixture label. If a live Qloo run is separately authorized, capture the redacted trace evidence described above. Check the current frontend build actually contains the editable fields, exact export values, Creator save/refresh/reopen, and Cinema observational copy.
5. For FilmSponsor, use a disposable guest workspace: confirm the browser's exact `Origin` matches the backend's configured guest-origin entry; cookie has `Secure`, `HttpOnly` and intended `SameSite`; CSRF/session ownership applies; a second browser cannot access the first campaign; expiry/recovery behaves as documented; and brand discovery is unavailable rather than fabricated when Qloo is absent. Do not change the allowlist to `*`, disable origin/CSRF checks, or mutate production configuration to make a test pass.
6. Record every observed result by category: local unit/fixture, browser, live Qloo, and hosted production. Mark any unexecuted or blocked item as pending. Only the operator who observed it should sign off.

## Eligibility organizer question

The official rules currently display the “New & Existing” sentence with the literal phrase **“Qloo 4after”**. The full exact quote and official-source link are preserved in `M13_11_HACKATHON_ELIGIBILITY_AUDIT.md`. Do not infer a correction or state that the project is eligible. Ask the organizers in writing what “Qloo 4after” means and how it applies to a project whose prior history or Qloo integration predates the Submission Period; separately confirm the entrant's own project history.
