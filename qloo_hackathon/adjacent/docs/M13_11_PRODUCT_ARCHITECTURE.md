# M13.11 — Product Architecture (post-pivot)

Date: 2026-10-11, with a current-code reference. This records the architecture as it
exists in code, why the creator positioning workflow is primary, and what was live-
verified vs environment-blocked in that session. No current live-Qloo request or hosted
deployment was verified on 16 October 2026; see [`FINALIZATION_STATUS.md`](FINALIZATION_STATUS.md).

## 1. Product thesis

**Adjacent = a cultural decision agent for independent filmmakers and YouTube
short-film creators.** The chain that defines it:

    Qloo-backed cultural evidence → explainable positioning hypothesis
    → concrete experiment → observed outcome → evidence-based evaluation

Cinema Mode (venue programming) remains functional and untouched; Creator Mode is the
primary surface. The differentiator is NOT "an LLM that talks about culture" — it is
that every cultural claim cites the API call that produced it, hypotheses are
falsifiable, and outcomes are recorded append-only.

## 2. The agent (what actually runs)

`backend/app/agent/` — a deliberate, auditable state machine, not an autonomous loop
and not an LLM:

- **Orchestrator** (`orchestrator.py`): PLAN → SELECT → ACT → EVALUATE → STOP over a
  fixed phase table; every transition recorded; hard budget ceilings
  (`budget.py`); typed stop decisions (`stop.py`) that distinguish `complete`,
  `insufficiency`, `budget_exhausted`, `error`, `invalid_input` — insufficiency is
  never a euphemism for failure.
- **Typed tools** (`tools.py`): `resolve_programme` (/entities), `get_taste_profile`
  (/v2/insights urn:tag), `expand_candidates` (/v2/insights per domain),
  `rank_cohorts` (evidence-gated ranking), `assess_evidence` (pure gate). The
  orchestrator cannot touch HTTP or fixtures — a `PipelineRuntime` supplies
  implementations (`FixturePipeline` offline; `LivePipeline` over `QlooClient`).
- **Investigation layer** (`domain/cultural_investigation.py`, M13.11): converts the
  completed run state into the structured account — questions asked → tool + operation
  → status → evidence refs (real `call_id`s) → FACT vs INTERPRETATION findings →
  primary hypothesis + alternatives + rejected worlds → limitations → open questions →
  experiment. Deterministic; it cannot invent entities because every FACT is bound to
  a recorded call. Emitted as the `investigation` SSE event and `result.investigation`.

No LLM is used in the product path. The only LLM integration is the evaluation
harness's Condition A (`research/scripts/m13_11_qloo_vs_llm.py`), which is
provider-gated and honestly BLOCKED without owner credentials.

## 3. Evidence & provenance

- Every Qloo call carries a `call_id` through `ProvenanceLedger`; state retains
  resolution/taste/expansion/rank call ids; `GET /run/{id}/trace` exposes them.
- Bets/Test Cards embed `provenance` (primary/adjacency/breadth/geography call ids);
  the investigation's `provenance.call_ids` is verified (by test) to be a subset of
  the run trace.
- Experiments snapshot the decision at save time; later evidence never rewrites it.
  Observations store `source`, `evidence_ref` (JSON: provider, data_status, video,
  period, retrieved_at, row_count, variant_label), and keep interpretation separate
  from metrics. Zero ≠ missing is enforced at provider, API and UI layers.

## 4. Learning loop

Cultural evidence → Positioning Bet → Test Card → saved experiment → observations
(manual, or YouTube-authorized with per-video/per-period provenance) → evaluations
(SUPPORTED/CONTRADICTED/INCONCLUSIVE, supersede with history) → open questions feed
the next investigation. YouTube data is an **instrument**, never proof of cultural
causation; variant labels (M13.11) record A/B context without implying attribution.

## 5. Live vs demo boundaries (architectural, enforced)

- Live creator run without `QLOO_API_KEY` → honest `failed`, `result: null` (test +
  E2E verified). Fixture demo → labelled at result/bet/card/investigation levels.
- YouTube: `not_configured` → 503 authorize / 409 data; `ADJACENT_YT_MOCK=1` opt-in
  labelled mock; live failures never fall back to mock (typed errors → 4xx/5xx).
- Evaluation harness: Condition A blocked without LLM key; stub labelled `llm_stub`.

## 6. Configuration (owner-supplied; never hardcoded)

| Variable | Purpose |
|---|---|
| `QLOO_API_KEY` | live Qloo (runtime secret mechanism only) |
| `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` / `YOUTUBE_REDIRECT_URI` | YouTube OAuth (default redirect `http://localhost:3000/api/youtube/callback`) |
| `ADJACENT_YT_MOCK` | opt-in labelled YouTube demo |
| `ADJACENT_LLM_API_KEY` / `ADJACENT_LLM_BASE_URL` / `ADJACENT_LLM_MODEL` | evaluation harness Condition A |
| `ADJACENT_EXPERIMENTS_DB` / `ADJACENT_YT_TOKEN_DB` | storage overrides (defaults gitignored) |

## 7. Deployment prerequisites & limits

- **Single-user local posture.** No app-level auth exists (verified). The YouTube
  connection is single-connection by design; do NOT expose publicly as multi-user
  without an ownership boundary.
- Python 3.12 target (PEP 695 in `qloo/models.py`); this sandbox ran tests on a
  labelled 3.11 desugar scratch copy — native 3.12 verification is an environment gap.
- Live gates BLOCKED in this environment: Qloo API (egress), YouTube OAuth
  (credentials), LLM provider (credentials), GitHub push/CI (network).
- Hosted demo for submission: not deployed; owner action.

## 8. Why not a heavier agent framework

The existing orchestrator already provides real tool execution, budgets, typed
results, and auditable stops. Adding an LLM-driven loop would add nondeterminism,
cost, and hallucination surface while removing the property that makes the product
defensible: every cultural claim is bound to a recorded API call. The M13.11
investigation layer strengthens the existing framework instead — the decision made
after inspecting the code, per the milestone's own guidance.
