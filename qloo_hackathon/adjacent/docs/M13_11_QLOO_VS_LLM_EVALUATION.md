# M13.11 — Qloo-grounded vs LLM-only Evaluation: Methodology & Results

Harness: `research/scripts/m13_11_qloo_vs_llm.py` · Tests:
`backend/tests/test_m13_11_investigation_eval.py` · Artefact (fixture run):
`data/processed/m13_11_qloo_vs_llm_20261010_205748.json` (committed, labelled).

## 1. The claim under test

**"Grounding positioning advice in retrieved Qloo evidence produces output that is more
traceable and more falsifiable than the same model's ungrounded advice."** This is a
hypothesis about the *system*, tested with a repeatable harness — not an assertion.

## 2. Conditions

- **Condition B — `qloo_grounded`:** the brief runs through the REAL product chain
  (orchestrator → typed Qloo tools over the configured provider → investigation →
  Positioning Bet → Test Card). Offline runs use the labelled fixture provider;
  `data_status` and limitations say so in every artefact.
- **Condition A — `llm_only`:** the same brief goes to an LLM with an explicit
  "you have NO access to cultural-affinity data" prompt and an identical output schema.
  Requires `ADJACENT_LLM_API_KEY` (+ optional `ADJACENT_LLM_BASE_URL`,
  `ADJACENT_LLM_MODEL`). **Without a provider, Condition A reports BLOCKED — it is
  never silently stubbed.** A deterministic `ScriptedStubLLM` exists for mechanism
  tests only and is labelled `llm_stub` in every artefact.

Consistency controls: identical briefs, identical output schema, identical rubric;
LLM temperature fixed at 0.2 when a real provider is used; model identity recorded in
artefact metadata. Randomness across repeated LLM runs is NOT controlled beyond
temperature — documented, not hidden.

## 3. Benchmark

Five **synthetic** film briefs (`BRIEFS`), varied by genre/theme, each mapped to an
available fixture scenario. One brief deliberately maps to `insufficient_evidence` to
exercise the honest-insufficiency path. The fixture is a **demo stand-in** evidence
source: it is not Qloo data about these fictional films, and artefacts state this.
Five briefs support mechanism validation, not statistical claims — none are made.

## 4. Rubric (automated, deterministic; anchors in `RUBRIC_ANCHORS`)

| Criterion | Anchor (score 1) |
|---|---|
| schema_valid | all required positioning fields present, non-empty |
| evidence_traceable | ≥1 evidence ref AND every ref exists in the run's evidence set. Condition A scores 0 **by construction** (no evidence access) — that asymmetry is the hypothesis under test, stated openly |
| specific_world | hypothesis names a cultural world beyond the input genre |
| falsifiable | success criteria + observation window + falsification all concrete |
| uncertainty_handled | ≥1 limitation recorded |
| information_beyond_generic | ≥2 evidence-linked claim sources or grounded-specific world |

A human-rating CSV template (rater_type column distinguishes human vs automated) is
part of the harness design; **no human ratings have been collected, and none are
claimed.** An LLM evaluator is NOT used — the rubric is deterministic code.

## 5. Results of the 2026-10-11 fixture run (labelled)

| Condition | n | avg total (max 6) | status |
|---|---|---|---|
| qloo_grounded (fixture evidence) | 5 | **5.4** | ran |
| llm_only | 0 | — | **BLOCKED — `ADJACENT_LLM_API_KEY` not configured** |

Interpretation (honest): the grounded condition's mechanics work end-to-end and its
outputs are evidence-traceable and falsifiable on fixture data. **No comparison result
exists yet** because Condition A has never run against a real LLM. The 5.4/6 figure is
NOT a benchmark win — it is one condition's mechanics score on demo data. The one
point lost on the insufficiency brief is the harness working as designed (no
hypothesis fabricated when evidence fails the gate).

## 6. Reproducing / completing the comparison

```
# mechanics (fixture, no credentials needed):
PYTHONPATH=backend python research/scripts/m13_11_qloo_vs_llm.py
# mechanism test of Condition A plumbing (labelled stub, NOT a real LLM):
PYTHONPATH=backend python research/scripts/m13_11_qloo_vs_llm.py --stub-a
# real comparison — owner supplies:
#   ADJACENT_LLM_API_KEY (+ optional ADJACENT_LLM_BASE_URL / ADJACENT_LLM_MODEL)
#   QLOO_API_KEY for a live-evidence grounded condition (else fixtures, labelled)
```

## 7. Limitations

1. Condition A never executed against a real LLM here → **comparison incomplete**.
2. Condition B ran on fixtures → fixture-based evaluation, not real-world effectiveness.
3. 5 synthetic briefs → no statistical significance claimed or possible.
4. The rubric measures structure/traceability, not persuasion or commercial quality;
   those need the (uncollected) human ratings.
5. More Qloo results ≠ better advice: the harness scores traceability and
   falsifiability, deliberately not "amount of evidence".
