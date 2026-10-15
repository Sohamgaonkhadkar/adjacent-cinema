"""Role-B synthesis: bounded, claim-level grounded briefs (M13.12 → M13.13 v2).

The deterministic investigation remains the product's decision engine. This
layer only renders it into a creator-facing brief, and it is strictly bounded:

* Input: ONLY the film context + the investigation produced by the real
  pipeline. It never re-executes tools and never sees credentials.
* Output: one fixed JSON schema (SYNTHESIS_KEYS). Schema v2 (M13.13) adds a
  structured ``claims`` list so grounding can be evaluated per claim, not
  just per identifier: {statement, claim_type, evidence_refs, rationale,
  limitations}. v1 payloads (no ``claims``) are REJECTED — never silently
  accepted — and produce the labelled deterministic fallback.
* Validation is deterministic and runs AFTER the model. Two guarantees are
  distinguished explicitly (see metadata["guarantees"]):
    - REFERENCE INTEGRITY (checked): every cited ref-shaped id and urn:
      entity id exists in the investigation's recorded evidence.
    - SEMANTIC SUPPORT (NOT guaranteed): that a cited call substantively
      supports the statement cannot be decided by a deterministic validator;
      structural rules (FACT must cite, UNKNOWN must not, HYPOTHESIS may not
      exist when the investigation abstained) constrain the space instead.
* A failed synthesis is never presented as model output — the caller receives
  a clearly labelled ``deterministic_fallback`` with the error recorded.
* No provider → the route reports BLOCKED; no silent stub, ever.

Known limitations (documented, not hidden): the forbidden-claims guard is a
pattern list, not a proof; semantic support is constrained structurally, not
verified.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .llm_provider import CompletionProvider

SYNTHESIS_SCHEMA_VERSION = "2.1"

SYNTHESIS_KEYS: tuple[str, ...] = (
    "summary",
    "hypothesis_restated",
    "rationale",
    "alternatives",
    "next_experiment",
    "caveats",
    "claims",
    "experiment_proposal",
)

#: Structured experiment proposal (M13.14). Field vocabulary deliberately
#: mirrors the existing Test Card / SaveExperimentRequest so an adopted
#: proposal maps 1:1 onto a saved experiment — no second schema.
PROPOSAL_KINDS: tuple[str, ...] = ("test", "information_gathering")
PROPOSAL_TEST_FIELDS: tuple[str, ...] = (
    "hypothesis",
    "action_plan",
    "success_criteria",
    "observation_window",
    "falsification",
)
MAX_METRICS = 8
MAX_ASSUMPTIONS = 6

CLAIM_TYPES: tuple[str, ...] = ("FACT", "INTERPRETATION", "HYPOTHESIS", "UNKNOWN")

MAX_FIELD_CHARS = 2000
MAX_ALTERNATIVES = 5
MAX_CAVEATS = 8
MAX_CLAIMS = 12
MAX_CLAIM_STATEMENT_CHARS = 600
MAX_CLAIM_REFS = 6

#: Deterministic safety net — not exhaustive, and documented as such.
FORBIDDEN_CLAIM_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"will go viral", "virality claim"),
    (r"\bguarantee[sd]?\b", "guarantee language"),
    (r"\bwill (reach|get|gain)\b.{0,40}\b(views|subscribers)\b", "viewership prediction"),
    (r"\bpredict[sed]*\b.{0,40}\b(views|retention|revenue)\b", "performance prediction"),
    (r"\bcaus(es|ed|ation)\b.{0,40}\b(views|success|growth)\b", "causal claim"),
)

#: Ref-shaped tokens: UUID call ids (uuid4 / uuid4-cNNN) and recorder ids
#: ({run_id}-cNNN). Cited ids outside the investigation's real set are
#: treated as fabricated.
_REF_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:-c\d+)?\b"
    r"|\b[A-Za-z0-9][\w.-]*-c\d{3,}\b"
)
_URN_PATTERN = re.compile(r"\burn:[A-Za-z0-9_:.\-]+")

#: Phrases that make a restated hypothesis consistent with an investigation
#: that abstained (checked only when the investigation has no primary).
_INSUFFICIENT_ACK = ("no hypothesis", "insufficient", "not supported", "no evidence")

SYSTEM_PROMPT = (
    "You write decision briefs for independent filmmakers from a structured "
    "cultural investigation. Rules: use ONLY the evidence provided; every "
    "FACT claim must cite the given evidence refs exactly as provided; "
    "INTERPRETATION claims should cite the facts they rest on; HYPOTHESIS "
    "claims propose a positioning decision to test and must not present it "
    "as established; UNKNOWN claims carry no refs; never invent entity ids "
    "(urn:...) or call ids; never predict views, retention or revenue; never "
    "claim virality or causation; cultural affinity is similarity, not "
    "demand; if the investigation concluded evidence was insufficient, say "
    "so and do not propose a positioning recommendation. Reply with ONLY a "
    "JSON object with exactly these keys: " + ", ".join(SYNTHESIS_KEYS) + ". "
    "'alternatives' and 'caveats' are lists of strings; 'claims' is a list "
    "of objects with keys: statement (string), claim_type (FACT | "
    "INTERPRETATION | HYPOTHESIS | UNKNOWN), evidence_refs (list of given "
    "ids), rationale (string), limitations (string, may be empty). "
    "'experiment_proposal' is an object: kind ('test' only when the "
    "investigation produced a supported hypothesis, otherwise "
    "'information_gathering'), hypothesis, action_plan, success_criteria, "
    "observation_window, falsification (all non-empty strings for kind "
    "'test'), relevant_metrics (non-empty list of observable metrics or "
    "observations), assumptions (list), limitations (string). A proposal is "
    "a proposal — never claim it was run or validated."
)

GUARANTEES: dict[str, str] = {
    "reference_integrity": (
        "checked — every cited ref-shaped id and urn: entity id is verified "
        "to exist in this investigation's recorded evidence"
    ),
    "semantic_support": (
        "NOT guaranteed — validators enforce structure (FACT must cite, "
        "UNKNOWN must not cite, no hypothesis claims when the investigation "
        "abstained) but cannot prove a cited call substantively supports "
        "each statement"
    ),
}


def collect_evidence_refs(investigation: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for question in investigation.get("questions", []):
        refs.update(question.get("evidence_refs") or [])
    for finding in investigation.get("findings", []):
        refs.update(finding.get("evidence_refs") or [])
    hyp = investigation.get("hypotheses") or {}
    if hyp.get("primary"):
        refs.update(hyp["primary"].get("evidence_refs") or [])
    for alt in hyp.get("alternatives", []) or []:
        refs.update(alt.get("evidence_refs") or [])
    refs.update((investigation.get("provenance") or {}).get("call_ids") or [])
    return {r for r in refs if r}


def investigation_has_facts(investigation: dict[str, Any]) -> bool:
    return any(
        f.get("claim_type") == "FACT" for f in investigation.get("findings", [])
    )


def investigation_abstained(investigation: dict[str, Any]) -> bool:
    return not ((investigation.get("hypotheses") or {}).get("primary"))


def build_user_prompt(investigation: dict[str, Any]) -> str:
    """The model sees the investigation JSON — nothing else, no credentials."""
    return (
        "Film context:\n"
        + json.dumps(investigation.get("film", {}), indent=2)
        + "\n\nInvestigation (evidence refs are opaque ids; cite them exactly "
        "as given when stating facts):\n"
        + json.dumps(investigation, indent=2)
    )


def _validate_claims(
    claims: Any, investigation: dict[str, Any], known_refs: set[str]
) -> list[str]:
    """Claim-level grounding rules (M13.13). Deterministic, structural."""
    issues: list[str] = []
    if not isinstance(claims, list):
        return ["claims must be a list"]
    if not claims:
        return ["claims must not be empty — a brief without structured claims is rejected"]
    if len(claims) > MAX_CLAIMS:
        issues.append(f"claims exceeds {MAX_CLAIMS} entries")
    abstained = investigation_abstained(investigation)
    has_facts = investigation_has_facts(investigation)
    for i, claim in enumerate(claims):
        label = f"claims[{i}]"
        if not isinstance(claim, dict):
            issues.append(f"{label} must be an object")
            continue
        statement = claim.get("statement")
        if not isinstance(statement, str) or not statement.strip():
            issues.append(f"{label}.statement must be a non-empty string")
            continue
        if len(statement) > MAX_CLAIM_STATEMENT_CHARS:
            issues.append(f"{label}.statement exceeds {MAX_CLAIM_STATEMENT_CHARS} chars")
        ctype = claim.get("claim_type")
        if ctype not in CLAIM_TYPES:
            issues.append(f"{label}.claim_type must be one of {', '.join(CLAIM_TYPES)}")
            continue
        refs = claim.get("evidence_refs")
        if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):
            issues.append(f"{label}.evidence_refs must be a list of strings")
            continue
        if len(refs) > MAX_CLAIM_REFS:
            issues.append(f"{label}.evidence_refs exceeds {MAX_CLAIM_REFS} entries")
        dangling = [r for r in refs if r and r not in known_refs]
        if dangling:
            issues.append(
                f"{label} cites evidence ref(s) that do not exist in this "
                f"investigation: {', '.join(dangling[:3])}"
            )
        # Type-specific grounding rules.
        if ctype == "FACT" and not refs:
            issues.append(
                f"{label}: FACT claim without evidence refs — facts must cite "
                f"the call(s) that produced them"
            )
        if ctype == "UNKNOWN" and refs:
            issues.append(f"{label}: UNKNOWN claim must not cite evidence refs")
        if ctype == "HYPOTHESIS" and abstained:
            issues.append(
                f"{label}: HYPOTHESIS claim contradicts the investigation, "
                f"which concluded no hypothesis is supported"
            )
        if ctype == "INTERPRETATION" and has_facts and not refs:
            issues.append(
                f"{label}: INTERPRETATION claim cites nothing although the "
                f"investigation contains FACT findings to rest on"
            )
        # Unsupported entity identifiers (reference integrity for urn: ids).
        blob = " ".join(
            str(claim.get(k, "")) for k in ("statement", "rationale", "limitations")
        )
        investigation_blob = json.dumps(investigation)
        for urn in _URN_PATTERN.findall(blob):
            token = urn.rstrip(".,;:")
            if token not in investigation_blob:
                issues.append(f"{label}: unsupported entity identifier {token}")
    return issues


def _validate_proposal(proposal: Any, investigation: dict[str, Any]) -> list[str]:
    """Structured experiment-proposal rules (M13.14).

    A `test` proposal asserts there is a supported hypothesis to test — it is
    rejected outright when the investigation abstained. An abstaining
    investigation may only yield `information_gathering` proposals, which say
    what to collect, not what positioning will work.
    """
    issues: list[str] = []
    if not isinstance(proposal, dict):
        return ["experiment_proposal must be an object"]
    kind = proposal.get("kind")
    if kind not in PROPOSAL_KINDS:
        return [f"experiment_proposal.kind must be one of {', '.join(PROPOSAL_KINDS)}"]
    if kind == "test":
        if investigation_abstained(investigation):
            issues.append(
                "experiment_proposal.kind 'test' contradicts the investigation, "
                "which concluded no hypothesis is supported — only "
                "information_gathering may be proposed"
            )
        for field in PROPOSAL_TEST_FIELDS:
            value = proposal.get(field)
            if not isinstance(value, str) or not value.strip():
                issues.append(f"experiment_proposal.{field} must be a non-empty string for kind 'test'")
            elif len(value) > MAX_FIELD_CHARS:
                issues.append(f"experiment_proposal.{field} exceeds {MAX_FIELD_CHARS} chars")
        metrics = proposal.get("relevant_metrics")
        if not isinstance(metrics, list) or not metrics or not all(
            isinstance(m, str) and m.strip() for m in metrics
        ):
            issues.append("experiment_proposal.relevant_metrics must be a non-empty list of strings")
        elif len(metrics) > MAX_METRICS:
            issues.append(f"experiment_proposal.relevant_metrics exceeds {MAX_METRICS} entries")
    else:  # information_gathering
        action = proposal.get("action_plan")
        if not isinstance(action, str) or not action.strip():
            issues.append(
                "experiment_proposal.action_plan must say what information to collect"
            )
        elif len(action) > MAX_FIELD_CHARS:
            issues.append(f"experiment_proposal.action_plan exceeds {MAX_FIELD_CHARS} chars")
    assumptions = proposal.get("assumptions", [])
    if not isinstance(assumptions, list) or not all(isinstance(a, str) for a in assumptions):
        issues.append("experiment_proposal.assumptions must be a list of strings")
    elif len(assumptions) > MAX_ASSUMPTIONS:
        issues.append(f"experiment_proposal.assumptions exceeds {MAX_ASSUMPTIONS} entries")
    limitations = proposal.get("limitations", "")
    if not isinstance(limitations, str) or len(limitations) > MAX_FIELD_CHARS:
        issues.append("experiment_proposal.limitations must be a string within bounds")
    return issues


def validate_synthesis(payload: Any, investigation: dict[str, Any]) -> list[str]:
    """Deterministic post-validation. Returns a list of issues ([] = valid).

    Guarantees REFERENCE INTEGRITY (cited ids exist). Does NOT and cannot
    guarantee SEMANTIC SUPPORT — see GUARANTEES.
    """
    issues: list[str] = []
    if not isinstance(payload, dict):
        return ["output is not a JSON object"]
    for key in SYNTHESIS_KEYS:
        if key not in payload:
            issues.append(f"missing key: {key}")
    if issues:
        return issues

    for key in ("summary", "hypothesis_restated", "rationale", "next_experiment"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(f"{key} must be a non-empty string")
        elif len(value) > MAX_FIELD_CHARS:
            issues.append(f"{key} exceeds {MAX_FIELD_CHARS} chars")

    for list_key, cap in (("alternatives", MAX_ALTERNATIVES), ("caveats", MAX_CAVEATS)):
        value = payload.get(list_key)
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            issues.append(f"{list_key} must be a list of strings")
        elif len(value) > cap:
            issues.append(f"{list_key} exceeds {cap} entries")

    known = collect_evidence_refs(investigation)

    # Claim-level grounding (M13.13).
    issues.extend(_validate_claims(payload.get("claims"), investigation, known))

    # Structured experiment proposal (M13.14).
    issues.extend(_validate_proposal(payload.get("experiment_proposal"), investigation))

    # Free-text fields: ref integrity + forbidden claims.
    cited = set()
    for key in SYNTHESIS_KEYS:
        value = payload.get(key)
        if isinstance(value, str):
            text = value
        elif isinstance(value, list):
            text = " ".join(v for v in value if isinstance(v, str))
        else:
            text = ""
        cited.update(_REF_PATTERN.findall(text or ""))
    dangling = sorted(c for c in cited if c not in known)
    if dangling:
        issues.append(
            f"cites {len(dangling)} evidence ref(s) that do not exist in this "
            f"investigation: {', '.join(dangling[:3])}"
        )

    # Contradiction with an abstaining investigation (beyond claim types).
    if investigation_abstained(investigation):
        restated = str(payload.get("hypothesis_restated") or "").lower()
        if not any(phrase in restated for phrase in _INSUFFICIENT_ACK):
            issues.append(
                "synthesis contradicts the investigation: it restates a "
                "hypothesis although the investigation concluded evidence is "
                "insufficient"
            )

    blob = json.dumps(payload).lower()
    for regex, label in FORBIDDEN_CLAIM_PATTERNS:
        if re.search(regex, blob):
            issues.append(f"forbidden claim pattern: {label}")
    return issues


def deterministic_fallback(investigation: dict[str, Any], error: str) -> dict[str, Any]:
    """Labelled, honest fallback — a failed model call never looks like a
    successful model result. Emits structured claims too, so the contract is
    identical whichever method produced the brief."""
    hyp = (investigation.get("hypotheses") or {}).get("primary") or {}
    experiment = investigation.get("experiment") or {}
    findings = investigation.get("findings", [])
    facts = [f for f in findings if f.get("claim_type") == "FACT"]

    claims: list[dict[str, Any]] = []
    for f in facts[:MAX_CLAIMS // 2]:
        claims.append({
            "statement": f.get("statement", ""),
            "claim_type": "FACT",
            "evidence_refs": list(f.get("evidence_refs") or []),
            "rationale": "Recorded by the pipeline from a real Qloo call.",
            "limitations": "",
        })
    if hyp:
        claims.append({
            "statement": hyp.get("statement", ""),
            "claim_type": "HYPOTHESIS",
            "evidence_refs": list(hyp.get("evidence_refs") or []),
            "rationale": str(hyp.get("supporting_evidence") or ""),
            "limitations": "A hypothesis to test, not a measured audience fact.",
        })
    for oq in investigation.get("open_questions", [])[: MAX_CLAIMS - len(claims)]:
        claims.append({
            "statement": oq,
            "claim_type": "UNKNOWN",
            "evidence_refs": [],
            "rationale": "",
            "limitations": "Unresolved by the available evidence.",
        })

    if hyp and experiment:
        proposal: dict[str, Any] = {
            "kind": "test",
            "hypothesis": hyp.get("statement", ""),
            "action_plan": experiment.get("action_plan", ""),
            "success_criteria": experiment.get("success_criteria", ""),
            "observation_window": experiment.get("observation_window", ""),
            "falsification": experiment.get("falsification", ""),
            "relevant_metrics": [
                "creator-recorded responses that reference the named cultural world",
            ],
            "assumptions": list(hyp.get("assumptions", []) or [])[:MAX_ASSUMPTIONS],
            "limitations": "Deterministic fallback — no model reasoning was available.",
        }
    else:
        proposal = {
            "kind": "information_gathering",
            "hypothesis": "",
            "action_plan": (
                "Collect more resolvable seed references (specific films, "
                "artists, works) and re-run the investigation before testing "
                "any positioning framing."
            ),
            "success_criteria": "",
            "observation_window": "",
            "falsification": "",
            "relevant_metrics": [
                "number of seed references that resolve to Qloo entities",
                "interest tags returned by the taste profile",
            ],
            "assumptions": [],
            "limitations": (
                "The investigation abstained: there is no supported hypothesis "
                "to test yet. This is an information-gathering action, not a "
                "positioning experiment."
            ),
        }

    return {
        "summary": (
            "Deterministic summary (LLM synthesis unavailable): "
            + (facts[0]["statement"] if facts else "the investigation recorded no factual findings.")
        ),
        "hypothesis_restated": (
            hyp.get("statement") or "No hypothesis was supported by the evidence."
        ),
        "rationale": hyp.get("supporting_evidence") or "No supporting evidence recorded.",
        "alternatives": [
            alt.get("statement", "")
            for alt in (investigation.get("hypotheses") or {}).get("alternatives", [])
            if alt.get("statement")
        ][:MAX_ALTERNATIVES],
        "next_experiment": experiment.get("success_criteria") or "No experiment was proposed.",
        "caveats": (investigation.get("limitations") or [])[:MAX_CAVEATS],
        "claims": claims,
        "experiment_proposal": proposal,
        "_fallback_error": error,
    }


def synthesize_investigation(
    investigation: dict[str, Any], provider: CompletionProvider
) -> dict[str, Any]:
    """Run the bounded synthesis. Always returns {synthesis, metadata}."""
    known_refs = sorted(collect_evidence_refs(investigation))
    base_metadata: dict[str, Any] = {
        "schema_version": SYNTHESIS_SCHEMA_VERSION,
        "provider_kind": provider.kind,
        "model": getattr(provider, "model", None),
        "evidence_refs_available": known_refs,
        "guarantees": GUARANTEES,
    }

    try:
        raw = provider.complete(SYSTEM_PROMPT, build_user_prompt(investigation))
    except Exception as exc:  # provider failure is honest (BaseException propagates)
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return {
            "synthesis": deterministic_fallback(investigation, str(exc)),
            "metadata": {
                **base_metadata,
                "method": "deterministic_fallback",
                "validation": "not applicable (model call failed)",
                "llm_error": str(exc),
            },
        }

    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        payload = json.loads(text)
    except ValueError as exc:
        return {
            "synthesis": deterministic_fallback(investigation, f"malformed JSON: {exc}"),
            "metadata": {
                **base_metadata,
                "method": "deterministic_fallback",
                "validation": "failed: malformed JSON",
                "llm_error": f"malformed JSON: {exc}",
            },
        }

    issues = validate_synthesis(payload, investigation)
    if issues:
        return {
            "synthesis": deterministic_fallback(investigation, "; ".join(issues)),
            "metadata": {
                **base_metadata,
                "method": "deterministic_fallback",
                "validation": "failed: " + "; ".join(issues[:3]),
                "llm_error": "output rejected by validation",
            },
        }

    return {
        "synthesis": payload,
        "metadata": {
            **base_metadata,
            "method": provider.kind,  # "live_llm" | "stub" — never ambiguous
            "validation": "passed",
        },
    }
