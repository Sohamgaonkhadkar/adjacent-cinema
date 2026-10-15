# M13.12 — Implementation Audit (Gate 1)

Date: 2026-10-11. Every statement below was re-verified against the working tree this
session, not copied from the M13.11 handoff.

## 1. Baseline facts (verified)

| Check | Result |
|---|---|
| Branch / HEAD | `arena/6462c00a-adjacent-cinema` @ `f8fe6ff` (M13.11); `cdcca4d`, `d7c9e08` ancestors |
| Working tree | clean (0 dirty files) at milestone start |
| M13.11 artefacts | present: 5 docs, `cultural_investigation.py`, `research/scripts/m13_11_qloo_vs_llm.py`, fixture eval JSON, `LICENSE` (MIT) |
| Tooling | ruff 0.17 venv + Python 3.11 venv + frontend `node_modules` persisted from prior turns |
| Python | system 3.11.2 only; **no 3.12/3.13 binary** → native 3.12 still unavailable |
| Credentials (names only, values never read) | `QLOO_API_KEY`, `ADJACENT_LLM_API_KEY`, `ADJACENT_LLM_BASE_URL`, `ADJACENT_LLM_MODEL`, `YOUTUBE_CLIENT_ID` all **unset** |
| GitHub | `git ls-remote` → TLS handshake terminated → **unreachable**; no push/CI possible |

## 2. What already exists (do not rebuild)

- **Agent core** (`app/agent/`): PLAN→SELECT→ACT→EVALUATE→STOP orchestrator; 5 typed
  tools; budgets; typed stop decisions (complete/insufficiency/budget_exhausted/error/
  invalid_input); `PipelineRuntime` protocol with fixture + live implementations.
  Verified by reading `orchestrator.py`, `tools.py`, `state.py`, `budget.py`, `stop.py`.
- **Investigation layer** (`domain/cultural_investigation.py`): questions q1–q4 mapped
  to real tools with statuses and call-id refs; FACT/INTERPRETATION findings; primary
  hypothesis + alternatives + rejected worlds; limitations; open questions; experiment.
- **Creator routes**: live + fixture-demo paths share `_post_pipeline_creator`;
  investigation emitted as SSE event and `result.investigation`; honest no-key failure.
- **Experiment lifecycle** (`domain/experiment_repository.py`): append-only, idempotent,
  supersession, zero≠missing, policy-deletion exception — intact (514 tests green at
  M13.11, re-run this milestone).
- **YouTube** (M13.10): OAuth boundary, token store, provider abstraction, mock mode,
  variant labels (M13.11).
- **Evaluation harness** (M13.11): conditions A/B, provider-gated LLM, deterministic
  rubric, fixture artefact.

## 3. Genuine gaps found (this milestone's work list)

1. **Fixed question set**: q1–q4 are asked regardless of context beyond the city gate.
   No context-framing question from genre/themes/language; no evidence-adaptive
   follow-ups (e.g. near-tied cohorts, thin breadth).
2. **Claim taxonomy incomplete**: findings use FACT/INTERPRETATION only; HYPOTHESIS and
   UNKNOWN live in separate structures — no unified, typed claim model.
3. **No dangling-reference defence at build time**: tests assert refs ⊆ trace, but the
   builder itself never validates; a divergent state could emit an unresolvable ref.
4. **No investigation identifier** (frontend contract wants one).
5. **Hypotheses lack distinguishing evidence** between primary and alternatives.
6. **No Role-B synthesis**: explanations are template text; no bounded LLM synthesis
   layer over the deterministic evidence (decision recorded in
   `M13_12_MODEL_ARCHITECTURE.md`).
7. **Evaluation rubric mixes applicable and inapplicable criteria into one total**
   (Condition A necessarily scores 0 on evidence-traceability) — misleading single
   score; no rubric versioning, no per-category reporting.
8. **Saved experiments don't carry the investigation summary** (provenance JSON could
   hold it, but the request contract has no fields for it).

## 4. Externally blocked (unchanged, re-verified this session)

| Blocker | State | Owner action needed |
|---|---|---|
| Live Qloo | BLOCKED — no key injected + sandbox egress to the API host blocked | inject key via supported runtime mechanism; run acceptance elsewhere if egress persists |
| LLM provider (Condition A / synthesis) | BLOCKED — `ADJACENT_LLM_API_KEY` unset | supply provider credentials |
| YouTube live OAuth | BLOCKED — no OAuth client credentials | supply console client |
| Native Python 3.12 | BLOCKED — no 3.12 binary, downloads blocked | run suite on 3.12 in CI/other env |
| Push / CI / public demo | BLOCKED — GitHub TLS failure | restore GitHub connectivity; deploy demo |

Per standing security constraints no credential was requested, recovered from
conversation history, printed, or reused; `/tmp/qloo.env` was left untouched.

## 5. Scope decision for M13.12

Address gaps 1–8 locally (all testable offline); keep all five external blockers
labelled BLOCKED with exact owner actions in `M13_12_DEPLOYMENT_READINESS.md`.
No frontend redesign (separate workstream); only minimal wiring where a contract
needs to be exercisable end-to-end.
