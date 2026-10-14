# M13.12 — Model Evaluation (rubric v2)

Supersedes the M13.11 harness methodology. Harness:
`research/scripts/m13_11_qloo_vs_llm.py`. Rubric version: **2.0**.

## Methodology fix (what was wrong in v1)

v1 scored `evidence_traceable` for BOTH conditions and folded it into one
total. The LLM-only baseline has no evidence by construction, so it scored a
guaranteed 0 on that criterion and the combined total overstated the
difference. v2 splits:

- **decision_quality** (applies to BOTH conditions, 5 criteria): schema_valid,
  specific_world, falsifiable, uncertainty_handled,
  information_beyond_generic.
- **evidence_grounding** (applies ONLY to the grounded condition, 3
  criteria): evidence_refs_present, refs_resolve,
  hypothesis_cites_evidence. For Condition A this category is reported as
  **NOT APPLICABLE** — never a misleading zero. Within the grounded
  condition, `hypothesis_cites_evidence` is itself NOT APPLICABLE on the
  insufficient-evidence path (no hypothesis exists to cite anything).

Category scores are reported separately as mean of per-run total/max (0–1).
There is no single combined score.

## Reproducibility

Every artefact (`data/processed/m13_11_qloo_vs_llm_<ts>.json`) records:
generated_at, methodology, rubric_version, rubric anchors, per-run metadata
(condition, provider_kind, model, fixture/live evidence,
evidence_refs_available), per-criterion scores with notes, applicability, and
stub/live/blocked flags. Condition A without `ADJACENT_LLM_API_KEY` is
**BLOCKED** with the reason recorded — never silently stubbed.
`--stub-a` runs the deterministic ScriptedStubLLM, labelled `llm_stub`
everywhere; it tests harness mechanics only and is not a real LLM condition.

## Results in this environment (2026-10-11)

- **Condition A (real LLM): BLOCKED** — `ADJACENT_LLM_API_KEY` not
  configured. No real comparison is claimed.
- **Condition B (qloo_grounded, LABELLED FIXTURE evidence, n=5)**:
  decision_quality **0.88**, evidence_grounding **1.0**. The 0.88 is driven
  by B5 (insufficient_evidence fixture) correctly producing no recommendation
  — scored low on decision quality honestly, with the grounding criterion
  for the missing hypothesis marked not applicable.
- **Mechanism test with `--stub-a` (NOT a real LLM condition)**: stub
  decision_quality **0.60** vs grounded **0.88**; grounding not applicable
  to the stub by construction.

Fixture-based scores demonstrate harness mechanics only. They are **not**
evidence of real-world effectiveness, and no real-world superiority is
claimed from synthetic examples.

## Human evaluation

`data/processed/m13_12_human_rating_template.csv` (written by the harness)
provides one row per brief × condition × criterion
(relevance_to_brief, specificity_of_positioning, actionability,
falsifiability, uncertainty_handling, information_gain) with anchors
0 = absent/generic, 1 = present but weak, 2 = specific/brief-tied/useful.
`rater_type` must be `human`. **No human ratings have been collected; none
are reported or implied anywhere in this repository.** An LLM evaluator is
not a substitute for human evaluation.
