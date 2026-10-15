# M13.13 — Model Evaluation (rubric v3)

Supersedes `M13_12_MODEL_EVALUATION.md` (rubric 2.0). Harness:
`research/scripts/m13_11_qloo_vs_llm.py`, `RUBRIC_VERSION = "3.0"`.

## What the M13.13 audit found wrong

1. **Abstention was penalised.** B5 (insufficient-evidence fixture) honestly
   produced no hypothesis and scored decision_quality 2/5 because
   schema/specificity/falsifiability criteria presuppose a recommendation.
   A benchmark must not punish the system for refusing to invent one.
2. **Brief↔fixture mismatch was under-disclosed.** B1–B4 (urban drama, rural
   family drama, analog horror, diaspora drama) all evaluate against the one
   recorded `portland_strong` scenario. Scores therefore measured the
   pipeline's internal consistency + rubric mechanics on stand-in evidence,
   NOT brief-aligned grounding. The fixtures themselves were labelled
   synthetic, but run metadata did not carry the fixture identity or the
   mismatch.

## Rubric v3

| Category | Applies when | Criteria |
|---|---|---|
| decision_quality | a positioning outcome exists (both conditions) | schema_valid, specific_world, falsifiable, uncertainty_handled, information_beyond_generic |
| evidence_grounding | grounded condition | evidence_refs_present, refs_resolve, hypothesis_cites_evidence (per-criterion NOT_APPLICABLE when no hypothesis) |
| **abstention_quality** | **no positioning outcome exists** | recognizes_insufficiency, explains_source, avoids_unsupported_facts, no_forced_hypothesis, identifies_next_info |

- No-hypothesis outputs get `decision_quality: {applicable: false, reason}` —
  never a punitive zero.
- **Refusals are not automatically good.** `recognizes_insufficiency`
  requires the run's own stop behaviour (`stop_reason != complete`);
  `explains_source` requires limitations naming the cause;
  `avoids_unsupported_facts` requires zero FACT claims lacking evidence refs
  (a cited fact about what Qloo genuinely returned — e.g. "N tags returned"
  — is legitimate even in an abstaining run and is not penalised). A
  fabricated refusal scores ≤1/5 (regression-tested).
- Every run records `fixture`, `fixture_alignment` ("stand-in — NOT Qloo
  data about this brief's specific themes"), provider_kind, model,
  rubric_version, and available refs.
- METHODOLOGY (embedded in every artefact) states the mismatch limitation
  explicitly.
- No new Qloo-shaped fixtures were added: near-tie / narrow-breadth /
  geography-insufficiency behaviour is covered by deterministic unit tests
  over synthetic in-memory states (`test_m13_12_agent_intelligence.py`), and
  inventing new "recorded API response" fixtures would imply real Qloo
  behaviour that was never observed.

## Results in this environment (2026-10-11, labelled fixtures, n=5)

| Category | qloo_grounded | llm_only |
|---|---|---|
| decision_quality | **1.0** (n=4; B5 correctly not applicable) | BLOCKED |
| evidence_grounding | **1.0** (n=5) | NOT APPLICABLE |
| abstention_quality | **1.0** (n=1, B5 — earned, not automatic) | BLOCKED |

Condition A (real LLM) remains **BLOCKED** — `ADJACENT_LLM_API_KEY` not
configured. No real comparison, no real-world superiority, no statistical
significance is claimed from 5 synthetic briefs on stand-in fixtures.
`--stub-a` remains a mechanics-only test labelled `llm_stub`.

## Human evaluation

Unchanged: `m13_12_human_rating_template.csv` (0–2 anchors, `rater_type`
must be human). **No human ratings exist; none are reported or implied.**
