# Current live-Qloo validation gate

**Latest recorded production route smoke check: 29 October 2026, after PR #29.** The production deployment for functional release commit `7e93e153ec39d4e85e9c4c34c6d9f98f3ca29880` was marked READY by Vercel; `/`, `/creator`, `/cinema`, `/creator/sponsor` returned HTTP 200 and `/api/health` returned a healthy response. This confirms server-side route availability, not every browser interaction. On 29 October, the live-Qloo counterfactual evaluation was expanded to nine prespecified programmes; the versioned `/2` report is linked below. The project owner confirmed three browser walkthroughs, recorded below as owner-reported passes rather than independently captured telemetry. Trusted-proxy alignment, external anonymous-traffic quotas/monitoring and the optional organizer eligibility clarification remain open gates.

A 6 October 2026 probe surfaced two historical title-resolution anomalies: `tt0089853` / Taipei Story was associated with The Purple Rose of Cairo, and `tt7594358` / Perfect Days did not resolve. These are regression examples, not proof of current provider behavior. Offline tests now reject title/year conflicts, preserve a title-search `MISMATCH` even if an external-ID lookup independently verifies a candidate, and keep unresolved results unresolved; they do not establish what Qloo returns today.

## Current completed checks

- Production routes `/`, `/creator`, `/cinema`, and `/creator/sponsor` returned HTTP 200 on 27 October 2026.
- Proxied `/api/health` returned HTTP 200 with `mode="public_demo"`, fixtures available, live Creator available and FilmSponsor guest mode enabled.
- The preserved [three-programme report, schema `/1`](verification/live_counterfactual_evaluation.md) records the original sample. The newer [nine-programme report, schema `/2`](verification/live_counterfactual_evaluation_v2.md) and [JSON results](verification/live_counterfactual_evaluation_v2.json) were generated 29 October using the live provider: 9 attempted, 8 evaluable and 1 non-evaluable due to no admitted candidate cohorts. This evaluation does not verify hosted browser flows.
- PR #29 merged on 29 October as [`7e93e15`](https://github.com/Sohamgaonkhadkar/adjacent-cinema/commit/7e93e153ec39d4e85e9c4c34c6d9f98f3ca29880). Post-merge CI passed backend, frontend and container-build: [run 40906289638](https://github.com/Sohamgaonkhadkar/adjacent-cinema/actions/runs/40906289638). Vercel marked the functional release deployment READY. That release adds adaptive verified-signal coverage, an explicit Creator exploratory-coverage notice, and a crisp zoom-in map handoff; it also preserves the entire returned scored cell set. The older PR #24 geography empty-state and Multiverse fixes remain included.

## Covered by automated tests (not the same as browser acceptance)

These properties are asserted by the offline suite, so a failure here is a real
regression rather than an untested assumption:

- guest sessions: cross-session isolation, ownership filtering on every campaign
  and child path, expired/revoked/missing sessions failing closed, CSRF and exact
  Origin enforcement on writes, bearer cookie flags, storage caps, expiry cleanup
  (`backend/tests/test_filmsponsor_guest_sessions.py`);
- Audience Pulse: definition freeze at the database level, one response per
  session, closed/expired/scheduled refusal, response ceiling, rate limiting,
  append-only evaluations, cross-experiment id rejection, reopen persistence
  (`backend/tests/test_audience_pulse.py`);
- compare refusal: no provider payload yields a metric until the response schema
  is verified (`backend/tests/test_pairwise_comparison.py`).

What the suite cannot show is how a real browser and the deployed proxy behave —
that is the list below.

## Browser walkthrough status and remaining operational gates

The project owner confirmed on 29 October 2026 that the first three browser walkthroughs below were verified. The checkboxes record owner-reported PASS status; no new browser session or telemetry was independently captured by this documentation change.

- [x] **PASS · owner-confirmed 29 Oct 2026.** FilmSponsor guest session and campaign creation, live brand discovery, exact Origin and cookie/CSRF behaviour checked in a normal browser.
- [x] **PASS · owner-confirmed 29 Oct 2026.** A second session was checked for isolation from the first session's campaign; revocation/expiry behaviour was verified.
- [x] **PASS · owner-confirmed 29 Oct 2026.** Audience Pulse participant flow completed with sharing enabled: open the share link, submit a vote, verify `already_responded` after reload, then close and evaluate from the owner view.
- [x] **PASS · verified 30 Oct 2026.** Vercel/Render trusted-proxy shared-secret alignment confirmed privately; secret values were not exposed or committed.
- [x] **PASS · 30 Oct 2026.** Live Qloo use remains limited to bounded demo traffic. Higher anonymous traffic will not be enabled until external quotas, monitoring and acceptable usage limits are reviewed.
- [x] **PASS · evidence recorded 30 Oct 2026.** Qloo is integrated into the working application for verified entity resolution, cultural insights, cross-domain discovery and cohort scoring. The repository's initial commit is dated 10 Oct 2026, after the 30 Sep submission-period start ([official rules](https://qloo.devpost.com/rules); [initial commit](https://github.com/Sohamgaonkhadkar/adjacent-cinema/commit/ee7363e39b16a2fae35d70e7cc1ef48d0811f668)). This records the implementation and available project timeline, not a separate written organizer ruling.

## Safe procedure for an authorized operator

Never paste a Qloo key into chat, an issue, a frontend variable, or a committed file. Configure it through an authorized local environment or secret manager. The test suite does not need it for fixture coverage.

1. **Configure the backend only.** Set `QLOO_API_KEY` in the backend process environment. Use the approved Qloo base URL; do not print or copy key material. Restart the backend after changing secrets.
2. **Check mode without publishing diagnostics.** Confirm the backend reports live mode and key configured. Do not copy the key fingerprint into a report; a mode check is not a successful live query.
3. **Run the live probe.** From `qloo_hackathon/adjacent`:

   ```bash
   make probe-live
   ```

   This sends real requests and must fail if no key is present; it never falls back to fixtures. Record the date, API host, pass/fail, and non-sensitive result counts only.
4. **Run the live-marked contract tests.**

   ```bash
   python -m pytest -m live -rs
   ```

   A skipped test is not a pass. Investigate any expected-resolution failure rather than weakening it to make CI green.
5. **Verify Creator Mode manually.** Submit a bounded reference set through the live Creator path. Confirm `data_status="measured"`, inspect the actual Qloo call IDs, and verify every resolved title/year. If the provider returns a contradictory mapping (including Taipei Story → The Purple Rose of Cairo), expect `MISMATCH` and no downstream use. If Perfect Days is absent, expect `UNRESOLVED`; do not fill in an entity or score.
6. **Save a sanitized report.** Do not include keys, key fragments, fingerprints, tokens, raw secret-bearing environment, or unreviewed upstream payloads. Distinguish live calls from fixtures and record any skipped checks as blocked/skipped.

## Offline regressions (always runnable)

Run from `qloo_hackathon/adjacent`:

```bash
python -m pytest backend/tests/test_resolution.py backend/tests/test_public_demo.py -q
python -m ruff check .
```

The Taipei Story / Purple Rose of Cairo regressions use synthetic **mock** entities; the conflicting mapping remains `MISMATCH`. Additional mock regressions reject an explicitly different IMDb ID or conflicting year; a full title/year/IMDb-ID match remains verified; differing search/ID entity IDs are rejected; and a title-search `MISMATCH` is not overridden by a separately verified external-ID result. The Perfect Days absence regression verifies empty mock search and ID responses remain `UNRESOLVED`. These deterministic tests are not live observations.

## Do not claim until verified

- Do not describe the October 6 probe as current live acceptance.
- Do not call a skipped GitHub live step a pass.
- Do not present the local fixture preview as Qloo output or as a hosted deployment.
- Do not publish a deployment URL or live result without a recorded, authorized check.
