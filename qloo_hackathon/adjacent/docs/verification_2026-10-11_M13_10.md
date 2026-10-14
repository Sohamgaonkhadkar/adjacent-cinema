# M13.10 Verification Report — exact counts

Date: 2026-10-11. Environment: sandbox with Python 3.11 only (native 3.12 unobtainable —
source downloads blocked); backend suite executed on a **labelled desugar scratch copy**
(single transform: `class ToolResult[T](_Base)` → `Generic[T]` form in
`app/qloo/models.py`; production sources untouched and remain 3.12-syntax). Frontend
checks ran on the production tree. GitHub remote unreachable this session (TLS handshake
terminated) — **no push, no CI run; CI status for this work is unknown, not green.**

## Static checks (production tree)

| Check | Command | Result |
|---|---|---|
| Ruff 0.17.0 | `ruff check .` | **All checks passed** (findings in new code fixed during the session: 1 syntax error + F821, I001, B905, RUF012, F841, F401) |
| TypeScript | `npx tsc --noEmit` | **0 errors** |
| Next build | `npm run build` | **Clean; routes `/`, `/_not-found`, `/creator`** |

## Backend suite (scratch 3.11 copy, `-m "not live"`)

**503 passed, 1 skipped, 7 deselected** (M13.9 baseline was 479p/1s/7d →
**+24 new M13.10 tests, zero regressions** in creator/cinema suites).

New file `test_m13_10_youtube.py` (24 tests):
- Status honesty: `not_configured` mode, 503 authorize without credentials (2)
- OAuth: unknown state 400, state single-use, state survives restart + expiry, denied
  consent redirect, mock connect exposes metadata but never tokens (5)
- Live provider units via `httpx.MockTransport`: metric mapping, observed-zero vs empty
  report, partial reports, quota/permission error typing, refresh `invalid_grant`,
  best-effort revocation (6)
- Data routes: videos 409 unconnected, from-youtube 409 unconnected (no observation
  written), full mock flow with provenance + idempotent retry, empty report → PARTIAL
  not zero, quota → 429 + no observation, unknown video 404, period validation
  (future/inverted) 422, unknown experiment 404 (8)
- Disconnect: credentials + YouTube observations deleted, tombstone added, manual
  observations and evaluations kept, tombstone contains no API data values (1)
- Token-leakage sweep across status/videos/metrics/observation/detail/disconnect
  responses (1)
- Live-mode honesty: authorize URL carries consent+offline+both scopes and no
  write/monetary scopes; callback with unreachable token endpoint → honest
  `yt=error` redirect, no stored connection (1)

**Defects found and fixed by these checks:** (1) invalid `return … from exc` syntax;
(2) `YouTubeProviderError` missing from imports after cleanup (F821); (3) the
unconnected mock path bypassed error mapping, leaking `QuotaExceeded` as a 500;
(4) mock authorize redirect broke behind the `/api` proxy (found in E2E, fixed with the
`via=proxy` parameter + proxy-native default redirect URI).

## End-to-end (live servers through the Next `/api` proxy)

Backend: uvicorn from the scratch 3.11 copy with `ADJACENT_YT_MOCK=1` (labelled — not
the 3.12 production runtime, not real YouTube); frontend: production `next start`.

| # | Check | Result |
|---|---|---|
| 1 | `GET /api/youtube/authorize?via=proxy` | 302 → `/api/youtube/callback?code=…&state=…` (proxy-routable) |
| 2 | callback | 302 → `/creator?yt=connected`; status shows mock channel, **no token in body** |
| 3 | `POST /experiments/…/observations/from-youtube` | `OBSERVED`, views 128, `source: mock_youtube_analytics`, evidence_ref with provider/period/retrieved_at |
| 4 | evaluation recorded alongside | `INCONCLUSIVE` with unknowns |
| 5 | `POST /api/youtube/disconnect` | credentials deleted; 1 YT observation deleted; tombstone added; **evaluation history kept** |
| 6 | cinema `/run/demo` regression | completed; no YouTube fields leaked into the result |
| 7 | `GET /creator` SSR | HTTP 200 |

## Invariants preserved

- Fixture/mock ≠ live everywhere: mock mode is opt-in, labelled at every layer, and
  never a fallback for live failures.
- Zero is data; empty is not: rows with 0 → OBSERVED zeros; no rows → PARTIAL + note.
- Append-only history intact: disconnect performs an explicit, documented,
  policy-required deletion with a tombstone — corrections still supersede.
- Qloo affinity never presented as predicted views; YouTube metrics never presented as
  causal proof (UI states both explicitly).
- Model readiness untouched: YouTube observations are NOT eligible ML labels;
  `NOT_READY` stands.
- No secrets: no credential in code, logs, responses, or the diff; token DB gitignored
  (`data/runtime/`); secret-pattern scan of the full diff clean.

## Not verified (honest gaps)

- **No live YouTube authorization or API call** — no OAuth client credentials exist for
  this project; live acceptance is BLOCKED, not passed.
- **No live Qloo call** (unchanged from M13.9; egress-blocked, key untouched).
- **No native 3.12 run**; the one-line desugar transform is the only divergence.
- **No browser UI walkthrough** (no browser in sandbox); SSR + API + build checks stand in.
- **No CI run** (GitHub unreachable).
