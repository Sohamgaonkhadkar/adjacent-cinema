# Verification Record — M13.14 (2026-10-11)

Environment (re-verified at start): branch `arena/6462c00a-adjacent-cinema`
@ `090b394`, clean; all provider env vars unset (names only; values never
read; nothing retrieved from conversation history); GitHub unreachable
(TLS); Python 3.11.2 only → all Python runs on the **labelled 3.11 scratch
desugar** (`/tmp/adj-scratch`), never presented as native 3.12; tooling
ruff 0.17.0 / pytest 9.1.1 / node_modules verified present.

## Commands and exact results (post-change)

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check --no-cache backend research` (repo root config) | **All checks passed** |
| Backend suite | `python -m pytest backend/tests -q` (3.11 scratch) | **603 passed, 8 skipped, 0 failed** (start of session: 585 → **+18 tests**) |
| Frontend typecheck | `./node_modules/.bin/tsc --noEmit` | exit 0 |
| Frontend build | `npm run build` | success (/, /_not-found, /creator) |
| Live HTTP E2E (scratch uvicorn :8125) | curl adoption flow | **all green**: demo run completed → adopt w/ snapshot (credential-shaped key stripped; refs verified vs run trace; `ghost-c999` → unresolved; `creator_edits` computed; original proposal preserved) → replay returns `duplicate: true` with snapshot **unchanged** (tamper rejected) |
| Secret scan | pattern scan over all changed files | zero matches (grep exit 1, verified as grep's own status) |

## New tests (test_m13_14_adoption.py, 16 tests) + updates

- Proposal validation (8): valid test-kind; missing/blank field; empty &
  oversized metrics; invalid kind; **test-kind rejected when investigation
  abstained**; information_gathering accepted when abstained; i-g requires
  an action; v2.0 payload (no proposal) rejected end-to-end → fallback.
- Fallback proposals (2): mirrors investigation experiment when supported;
  honest information_gathering (empty hypothesis) when abstaining; both pass
  the validator.
- Adoption persistence (6): snapshot sanitised + ref-verified; creator edits
  attributable (`creator_edits`, `adoption`); replay idempotent + snapshot
  immutable; **investigation byte-identical after adoption**; snapshot
  without source run labelled unverified; information-gathering adoption
  honest (edit attributed to creator).
- Updated for schema 2.1: `test_m13_12_synthesis.py` and
  `test_m13_13_model_quality.py` payloads carry `experiment_proposal`;
  M13.13 investigation fixture enriched to the real full-experiment shape
  (its thin fixture was unrealistic — the fallback validator-parity check
  caught it).

## Honest notes / failures found during the milestone

1. Three of my new-test assertions initially mismatched intended behaviour
   (merged unresolved-ref list; unverified snapshots keep refs with explicit
   status) — assertions corrected to the design, code unchanged.
2. A stale ruff cache and a scratch-dir ruff run (no repo config) produced
   misleading results — final lint run from the repo root with `--no-cache`.

## NOT verified here (unchanged honest gaps)

Live Qloo (egress-blocked; fixture-labelled evidence only) · real LLM
condition / live synthesis (no provider; BLOCKED, never stubbed) · live
YouTube (single-user, fixtures only) · human evaluation (none collected) ·
GitHub push/CI (remote unreachable; local commits only) · browser-level UI
testing (no tooling — adoption panel verified via tsc/build + endpoint E2E)
· native Python 3.12 execution (unavailable).
