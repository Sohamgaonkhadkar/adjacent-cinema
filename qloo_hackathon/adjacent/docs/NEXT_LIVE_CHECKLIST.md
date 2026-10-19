# Current live-Qloo validation gate

**Status as of 16 October 2026: BLOCKED / NOT VERIFIED IN THIS SESSION.** The checked shell had no `QLOO_API_KEY` and no `QLOO_BASE_URL` override; without a key, non-public mode is mock. The sandbox API preview was explicitly `public_demo`, with fixtures available and live Creator unavailable. The inspected GitHub CI run passed its backend job but skipped the conditional live-Qloo step; remote secret state was not verified. No live request was made here.

`LIVE_QLOO_VALIDATION.md` records observations from 6 October 2026 only. It is historical evidence, not proof of current connectivity or current resolver behavior. It records `tt0089853` / Taipei Story being associated with The Purple Rose of Cairo and `tt7594358` / Perfect Days not resolving. Offline regressions now reject title/year conflicts, keep a title-search `MISMATCH` even if an external-ID lookup independently verifies a candidate, and preserve unresolved results; they do not establish what Qloo returns today.

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
