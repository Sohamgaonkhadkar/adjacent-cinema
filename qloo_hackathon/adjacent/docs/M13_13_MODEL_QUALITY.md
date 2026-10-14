# M13.13 — Model Quality: claim-level grounding

Builds on `M13_12_MODEL_ARCHITECTURE.md` (role separation, provider
abstraction, fallback honesty — unchanged). This document covers what
M13.13 changed and why.

## The problem with v1 grounding

M13.12 validated **reference integrity** globally: every ref-shaped id cited
anywhere in the brief had to exist in the investigation. That guarantee is
real but weak — a synthesis could cite a valid call id next to a statement
that call never produced, assert a FACT with no citation at all, or restate
a confident hypothesis even when the investigation had explicitly abstained.
Valid citation identifiers alone do not prove a claim is grounded.

## Schema 2.0 — structured claims

`synthesis.claims[]` (new required key; schema_version "2.0"):

```
{statement, claim_type: FACT|INTERPRETATION|HYPOTHESIS|UNKNOWN,
 evidence_refs[], rationale, limitations}
```

v1 payloads (no `claims`) are **rejected**, not silently accepted — the
caller receives the labelled `deterministic_fallback`. The fallback itself
emits structured claims (facts cite their calls; unknowns cite nothing), so
the contract is identical whichever method produced the brief — and the
fallback passes the same validator (regression-tested).

## Deterministic validators (post-model, code not prompt trust)

| Rule | Guarantee class |
|---|---|
| Schema keys, types, size bounds (2000 chars/field, ≤12 claims, ≤6 refs/claim, 600-char statements) | structural |
| Every cited ref-shaped id (UUID / `{run_id}-cNNN`) exists in the investigation's recorded refs | **reference integrity — checked** |
| Every `urn:` entity id in claim text exists in the investigation payload | **reference integrity — checked** |
| FACT claims must cite ≥1 resolving ref | structural grounding |
| UNKNOWN claims must cite nothing | honesty |
| INTERPRETATION claims must cite when FACT findings exist | structural grounding |
| HYPOTHESIS claims forbidden when the investigation abstained | contradiction guard |
| `hypothesis_restated` must acknowledge insufficiency when the investigation abstained | contradiction guard |
| Forbidden-claim patterns (virality, guarantees, viewership/revenue prediction, causal claims) scanned over the **whole payload including claims** | overclaim guard |

## The two guarantees, stated honestly (in every response's metadata)

```
guarantees:
  reference_integrity: "checked — every cited id verified to exist in this
                        investigation's recorded evidence"
  semantic_support:    "NOT guaranteed — validators enforce structure but
                        cannot prove a cited call substantively supports
                        each statement"
```

Semantic support is constrained (facts must cite real calls of the pipeline
that produced them; the input to the model is only the real investigation)
but **not verified**. No component of this system claims semantic
verification.

## Provider hardening (M13.13)

- Response-size bound: completions over 100 000 chars raise
  `LLMUnavailableError` ("…char bound") → labelled fallback. No retry loops,
  60 s timeout, injectable transport (tested offline with a huge-response
  transport).

## Product integration (was isolated in M13.12)

The creator page now renders a **Decision brief (optional)** panel under the
investigation: it queries `/creator/synthesis-status` (shows the honest
blocked reason when no provider is configured — the investigation remains
fully usable), and on demand generates the brief, labelling the method
unambiguously: `LIVE MODEL SYNTHESIS` / `STUB PROVIDER — NOT A REAL MODEL
RESULT` / `DETERMINISTIC FALLBACK — MODEL OUTPUT UNAVAILABLE OR REJECTED`,
with per-claim type badges and evidence refs. No visual redesign was
performed (separate workstream).

## Adversarial coverage (`test_m13_13_model_quality.py`, 27 tests)

FACT without refs · dangling claim ref · UNKNOWN with refs ·
INTERPRETATION unanchored while facts exist · invalid claim type · empty /
oversized claim lists · 601-char statement · unsupported `urn:` entity ·
legitimate `urn:` accepted · overclaims hidden inside claim rationales
(5 forms) · v1 payload rejected end-to-end · hypothesis claim vs abstaining
investigation · confident restatement vs abstaining investigation · honest
abstaining brief accepted · fallback structure/validator parity (incl.
abstaining) · provider size bound (raise + fallback labelling) · guarantees
metadata honesty.
