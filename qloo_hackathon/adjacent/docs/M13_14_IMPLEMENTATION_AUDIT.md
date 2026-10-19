# M13.14 — Implementation Audit (Phase 0)

> **Historical snapshot (11 October 2026).** Its branch, repository, and test-state details describe that session only and are superseded by [`FINALIZATION_STATUS.md`](FINALIZATION_STATUS.md), dated 16 October 2026.

Date: 2026-10-11. All facts verified in that session by direct
inspection/execution.

## Baseline (verified)

| Fact | Result |
|---|---|
| Branch / HEAD | `arena/6462c00a-adjacent-cinema` @ **`090b394`** (M13.13), tree clean |
| Baseline commit | `e875e58` (restored M1–M13.12 state) intact beneath it |
| Test suite | **585 passed, 8 skipped** re-run this session (labelled 3.11 scratch desugar; system Python 3.11.2) |
| Tooling | ruff 0.17.0, pytest 9.1.1 (persisted venv); frontend `node_modules` present (`next`, `tsc` binaries verified) |
| Credentials (names only) | `QLOO_API_KEY`, `ADJACENT_LLM_*`, `YOUTUBE_CLIENT_*` all **unset**; `/tmp/qloo.env` absent this session; nothing retrieved from history |
| GitHub | `git ls-remote` → TLS failure — **still unreachable**; no push/CI claims possible |

## Three decision layers — current state (traced through code)

**Layer A — investigation** (`cultural_investigation.py` → run result):
complete and protected. `verify_evidence_refs` strips dangling refs at
emit time; the investigation is stored in the run record and never mutated
by synthesis (synthesis only reads it).

**Layer B — Decision Brief** (`synthesis.py` + `/creator/synthesize`):
schema 2.0 with structured claims, claim-level validation, guarantees
metadata, honest fallback. Panel renders it on the creator page (M13.13).
**Gap B1:** `next_experiment` is a single free-text string — not a
structured, testable proposal; nothing distinguishes a positioning test
from an information-gathering recommendation when the investigation
abstained.

**Layer C — saved decision** (`experiment_repository.py` +
`POST /experiments`): provenance carries `investigation_summary` +
validated `evidence_refs` (unresolved → `provenance.unresolved_evidence_refs`).
Idempotent twice over: replayed `request_id` AND a second save for the same
`source_run_id` both return the ORIGINAL record (`dedupe_key run:{id}`) —
one saved decision per run, by design; M13.14 must preserve this.
**Gap C1:** the synthesis that informed a decision is NOT retained — the
frontend save path never sends it and the route has no field for it.
**Gap C2:** no distinction between a model-proposed experiment and the
version the creator actually saved (edits are invisible).

## Remaining gaps (what M13.14 must close)

- **B1** Structured `experiment_proposal` in the synthesis contract
  (kind: `test` | `information_gathering`; hypothesis, action, success
  criteria, window, falsification, relevant metrics, assumptions,
  limitations), reusing the existing Test Card field vocabulary — with
  validation that a `test` proposal cannot exist when the investigation
  abstained.
- **C1** Immutable, sanitised synthesis snapshot persisted in the existing
  provenance JSON when the creator adopts a proposal (allowlisted keys
  only; claims' refs re-verified against the source run's trace; fixture
  `data_status` carried; no credentials/provider payloads).
- **C2** `adopted_proposal` + computed `creator_edits` in provenance so a
  reviewer can always tell what the model proposed from what the creator
  saved.
- **W1** Adoption workflow in the Decision Brief panel: "Use this
  experiment" → editable draft → explicit confirm → save. A draft never
  persists anything; an existing saved decision for the run is never
  overwritten (dedupe surfaces the original honestly).

## Explicitly NOT changing

The orchestrator, tools, investigation builder, provider abstraction,
rubric-3.0 harness, observation/evaluation semantics (zero≠missing,
supersession, YouTube source metadata), repository schema/DB, cinema flow,
homepage/map/visual design.
