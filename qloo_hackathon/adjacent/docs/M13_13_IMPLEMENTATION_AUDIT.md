# M13.13 — Implementation Audit (Gate 1)

Date: 2026-10-11. Everything below was verified in this session by direct
inspection/execution, not taken from prior handoffs.

## Baseline facts (verified this session)

| Fact | Verification | Result |
|---|---|---|
| Sandbox re-cloned | `git reflog` | clone at `89aea4c` (GitHub main = merged PR #1), branch `arena/6462c00a-adjacent-cinema` recreated from `ee7363e` (initial commit) |
| Prior local commits | `git cat-file -t 3bae0ce` / `f8fe6ff` | **do not exist in this clone** — they were never pushed; GitHub main's merged PR #1 predates M13.9–M13.12 |
| Working tree | file inspection + test run | contains the **complete M13.12 end-state** (all files present); verified via `ruff` (clean) and `pytest` (**552 passed, 8 skipped**, labelled 3.11 scratch) before committing |
| Baseline commit | `git log` | restored state committed as **`e875e58`** on the session branch; tree clean after |
| GitHub remote | `git ls-remote` | **unreachable** (gnutls TLS failure) — local commits only |
| Credentials (names only, values never read) | env check | `QLOO_API_KEY`, `ADJACENT_LLM_API_KEY`, `ADJACENT_LLM_BASE_URL`, `ADJACENT_LLM_MODEL`, `YOUTUBE_CLIENT_ID/SECRET` all **unset**; `/tmp/qloo.env` not touched |
| Python | `python3 --version` | 3.11.2 only; repo requires 3.12 (PEP 695) → labelled scratch desugar for test runs |
| Tooling | rebuilt this session | ruff 0.17.0 + pytest 9.1.1 venv; `npm ci` for frontend |

## Execution path (traced through code, not docs)

1. `POST /creator/run` (`creator_routes.py`) → validates film input → creates
   run record → background `_post_pipeline_creator`.
2. `AgentOrchestrator` (`backend/app/agent/orchestrator.py`): explicit
   PLAN→SELECT→ACT→EVALUATE→STOP state machine over a fixed phase table
   (`resolve_programme → get_taste_profile → expand_candidates →
   rank_cohorts`), typed stops (`insufficiency`, `budget_exhausted`, `error`,
   `invalid_input`), defensive `MAX_ITERATIONS=24`. No LLM in the loop.
3. Qloo tools execute through the real client (or labelled MockQlooClient
   fixture); every call recorded with a `call_id` in the recorder;
   `state.trace_rows` exposes them.
4. `creator_analysis.build_positioning_bet` + `build_creator_test_card`
   derive the positioning decision from ranked cohorts only.
5. `cultural_investigation.build_investigation` assembles q0–q6, typed
   findings, hypotheses, experiment; `verify_evidence_refs` (route) strips
   refs not in `state.trace_rows` and records a limitation.
6. **Synthesis is a separate, on-demand endpoint** (`POST
   /creator/synthesize`, `GET /creator/synthesis-status`) gated on
   `ADJACENT_LLM_API_KEY`, with test-only provider override.
7. `POST /experiments` merges `investigation_summary` + validated
   `evidence_refs` into provenance; unresolved refs go to
   `provenance.unresolved_evidence_refs`.
8. Observations/evaluations preserve zero≠missing, idempotency,
   supersession (M13.9 repository, unchanged).

## Key product question — answered by code inspection

**Is synthesis integrated into the creator experience? NO.**
`grep -rn "synthes" frontend/` → **zero references** (app, lib, components,
types). The capability exists server-side but the product never requests,
displays or distinguishes it. It is an isolated endpoint. → Gate 2 fixes
this with a minimal, labelled integration (no visual redesign).

## Verified gaps

- **G1 — Synthesis isolated from the creator journey** (above).
- **G2 — No claim-level grounding in the synthesis contract.** M13.12
  validates *reference integrity* globally (cited ids must exist in the
  investigation) but any claim may cite any valid id: a FACT with no refs, a
  FACT whose cited call has nothing to do with the statement, or a HYPOTHESIS
  presented despite an insufficient investigation all pass. No entity-id
  (`urn:`) check, no FACT-requires-refs rule, no
  insufficient-contradiction rule, no semantic-support honesty field.
- **G3 — Provider hardening gaps.** Timeout exists (60 s); no retry loops
  (good); **no bounded response size**; redaction is correct.
- **G4 — Benchmark brief↔fixture mismatch.** 4 of 5 briefs (B1–B4: urban
  drama, rural family drama, analog horror, diaspora drama) all map to the
  single `portland_strong` fixture; B5 maps to `insufficient_evidence`.
  Scores therefore measure rubric mechanics on stand-in evidence, NOT
  brief-aligned grounding; fixture name is absent from run metadata.
- **G5 — Abstention penalised.** B5's honest no-hypothesis outcome scores
  decision_quality 2/5 because schema/specificity/falsifiability criteria
  assume a recommendation exists. No `abstention_quality` category; no
  `NOT_APPLICABLE` for decision criteria on no-hypothesis outputs.
- **G6 — Investigation quality: largely complete** (q0/q5/q6, claim
  taxonomy, dangling-ref stripping, insufficiency paths — all regression
  tested in `test_m13_12_agent_intelligence.py`, re-verified passing this
  session). Remaining: strengthen hypothesis-discrimination and
  geography-insufficiency test coverage; no architecture change justified.
- **G7 — Experiment provenance: works end-to-end** (route merges + filters
  refs against `record.trace`; E2E-verified in M13.12 and covered by
  tests). Keep separation: synthesis must not rewrite saved decisions.
- **G8 — API contract** must add claim-level synthesis structure and the
  reference-integrity vs semantic-support distinction.

## Planned changes (this milestone)

1. **Gate 2:** minimal creator-facing Decision Brief integration (status +
   on-demand generation + method labelling) — frontend wiring only, no
   redesign.
2. **Gate 3:** synthesis schema 2.0 — structured `claims[]` (statement,
   claim_type, evidence_refs, rationale, limitations), deterministic
   validators (FACT requires resolving refs; UNKNOWN forbids refs;
   hypothesis-vs-insufficiency contradiction; `urn:` entity-id resolution;
   existing forbidden-claims + bounds), provider response-size bound,
   metadata `guarantees: {reference_integrity: checked, semantic_support:
   not_guaranteed}`.
3. **Gate 5:** harness rubric 3.0 — `abstention_quality` category,
   `NOT_APPLICABLE` decision criteria on no-hypothesis outputs, fixture name
   + `fixture_alignment` in run metadata, methodology rewritten to state the
   mismatch limitation. No new Qloo-shaped fixtures: near-tie/narrow-breadth
   logic is covered by deterministic unit tests, and inventing new
   "recorded API" fixtures would imply real Qloo behaviour that was never
   observed.
4. **Gates 4/6:** targeted regression tests (hypothesis discrimination,
   geography insufficiency, provenance separation), no rewrites.
5. **Gate 7:** `docs/M13_13_API_CONTRACT.md` + contract doc updates.
6. **Gate 8:** full verification + handoff.

Not planned (explicitly): frontend redesign, new frameworks, multi-agent
orchestration, model training, new providers, new Qloo endpoints.
