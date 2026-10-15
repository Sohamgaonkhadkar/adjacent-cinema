#!/usr/bin/env python3
"""M13.11: Qloo-grounded vs LLM-only evaluation harness.

Compares two conditions on identical synthetic film briefs:

    Condition A ("llm_only")      — film context only, no Qloo evidence.
    Condition B ("qloo_grounded") — film context + the evidence the Adjacent
                                    pipeline actually retrieved (fixture or
                                    live), rendered through the same
                                    investigation → hypothesis → experiment
                                    chain the product uses.

HONESTY RULES (enforced by tests):
* Condition B in offline mode runs on LABELLED FIXTURE evidence. Fixture-based
  scores demonstrate harness MECHANICS — they are not proof of real-world
  effectiveness and are never reported as such.
* Condition A requires a real LLM provider (ADJACENT_LLM_API_KEY [+ optional
  ADJACENT_LLM_BASE_URL / ADJACENT_LLM_MODEL]). Without one it reports
  BLOCKED — it is never silently replaced by a stub. A deterministic
  ScriptedStubLLM exists for mechanism tests only and is labelled "llm_stub"
  in every artefact.
* No credential, prompt response, or personal data is written to artefacts
  beyond the structured outputs themselves.
* Rubric v3 (M13.13): `decision_quality` applies to both conditions but ONLY
  when a positioning outcome exists (honest abstention is scored by
  `abstention_quality`, never as a punitive zero); `evidence_grounding`
  applies ONLY to the grounded condition; every category reports explicit
  applicability and no misleading composite score is produced.

Usage:
    PYTHONPATH=backend python research/scripts/m13_11_qloo_vs_llm.py [--stub-a]
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

adjacent_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(adjacent_root / "backend"))

from app.agent.orchestrator import AgentOrchestrator  # noqa: E402
from app.agent.state import AdjacentState  # noqa: E402
from app.config import Settings  # noqa: E402
from app.domain.creator_analysis import (  # noqa: E402
    build_creator_test_card,
    build_positioning_bet,
    two_sided_signal_maps,
)
from app.domain.cultural_investigation import build_investigation  # noqa: E402
from app.domain.ledger import ProvenanceLedger  # noqa: E402
from app.qloo.mock import MockQlooClient  # noqa: E402
from app.runner import FixturePipeline, programme_items  # noqa: E402

# ============================================================
# BENCHMARK BRIEFS — synthetic inputs, honestly labelled
# ============================================================

#: Each brief maps to an available fixture scenario. The fixture is a DEMO
#: STAND-IN evidence source: it is not Qloo data about these (fictional)
#: films, and the artefacts say so. `insufficient_evidence` deliberately
#: exercises the honest-insufficiency path.
BRIEFS: list[dict[str, Any]] = [
    {
        "brief_id": "B1-neon-harbour",
        "title": "Neon Harbour",
        "logline": "A night-shift ferry worker befriends a insomniac musician in a port city.",
        "genre": "urban drama",
        "themes": ["isolation", "night workers", "music"],
        "fixture": "portland_strong",
    },
    {
        "brief_id": "B2-quiet-field",
        "title": "The Quiet Field",
        "logline": "Two siblings return to their late father's farmland and disagree about selling it.",
        "genre": "rural family drama",
        "themes": ["grief", "inheritance", "landscape"],
        "fixture": "portland_strong",
    },
    {
        "brief_id": "B3-static",
        "title": "Static",
        "logline": "A teenage archivist finds a cassette that seems to record the near future.",
        "genre": "analog horror short",
        "themes": ["memory", "technology dread", "adolescence"],
        "fixture": "portland_strong",
    },
    {
        "brief_id": "B4-ammas-radio",
        "title": "Amma's Radio",
        "logline": "An immigrant grandmother's pirate-radio broadcasts hold a dispersed family together.",
        "genre": "diaspora drama",
        "themes": ["language", "family", "music"],
        "fixture": "portland_strong",
    },
    {
        "brief_id": "B5-thin-ice",
        "title": "Thin Ice",
        "logline": "A climate researcher and a ferry pilot clash over a closing winter route.",
        "genre": "eco-thriller short",
        "themes": ["climate", "work", "conflict"],
        "fixture": "insufficient_evidence",  # exercises honest insufficiency
    },
]

METHODOLOGY = (
    "Offline harness, rubric v3. Condition B ran the real Adjacent pipeline "
    "over LABELLED FIXTURE evidence — recorded demo scenarios that are NOT "
    "live Qloo data about these fictional films. KNOWN LIMITATION (M13.13 "
    "audit): most briefs share one fixture (portland_strong), so scores "
    "measure the pipeline's internal consistency and the rubric's mechanics "
    "on stand-in evidence, NOT brief-aligned grounding; every run records "
    "its fixture name and a fixture_alignment label. Fixture-based scores "
    "are never evidence of real-world effectiveness. Condition A requires a "
    "configured LLM provider; without one it is BLOCKED, never stubbed. "
    "Categories: decision_quality (both conditions, only when a positioning "
    "outcome exists), evidence_grounding (grounded condition only), "
    "abstention_quality (only when the system honestly produced no "
    "recommendation — a refusal scores well only when the evidence and stop "
    "behaviour support it). No statistical significance is claimed from 5 "
    "synthetic briefs."
)

# ============================================================
# Condition B — Qloo-grounded (the product's real chain)
# ============================================================


def run_grounded_condition(brief: dict[str, Any]) -> dict[str, Any]:
    """Run the actual pipeline + investigation chain on the brief's fixture."""
    settings = Settings.from_env(
        qloo_api_key=None, rate_limit_rps=0.0, max_retries=0, retry_backoff_base_s=0.0
    )
    client = MockQlooClient(settings, fixture=brief["fixture"], run_id=f"eval-{brief['brief_id']}")
    fx = client.fixture
    seeds = [brief["title"], *brief.get("themes", [])]
    state = AdjacentState(
        run_id=f"eval-{brief['brief_id']}",
        fixture_name=brief["fixture"],
        scenario=fx.scenario,
        fixture_notice=client.notice,
        data_status="fixture",
        description=f"Evaluation brief {brief['brief_id']}",
        programme=programme_items(fx.programme),
    )
    state.ledger = ProvenanceLedger(recorder=client.recorder, data_status="fixture")
    state = asyncio.run(AgentOrchestrator(FixturePipeline(client, fx)).run(state))

    bet = None
    test_card = None
    if state.stop_reason == "complete" and state.ranked:
        bet = build_positioning_bet(
            ranked_cohorts=state.ranked,
            taste_tags=state.taste_tags,
            film_title=brief["title"],
            seeds=seeds,
            signals=two_sided_signal_maps(state),
            rejected_cohorts=state.rejected,
            data_status="fixture",
        )
        if bet:
            test_card = build_creator_test_card(
                bet=bet,
                film_title=brief["title"],
                seeds=seeds,
                release_goal="festival + YouTube release",
            )
    investigation = build_investigation(
        state,
        film={"title": brief["title"], "logline": brief["logline"], "genre": brief["genre"]},
        seeds=seeds,
        bet=bet,
        test_card=test_card,
        data_status="fixture",
    )

    primary = investigation["hypotheses"]["primary"]
    positioning: dict[str, Any] | None = None
    if primary and test_card is not None and bet is not None:
        positioning = {
            "hypothesis": primary["statement"],
            "world": primary["world"],
            "success_criteria": test_card.success_criteria,
            "observation_window": test_card.observation_window,
            "action_plan": test_card.programming_direction,
            "falsification": primary["falsification"],
        }
    return {
        "condition": "qloo_grounded",
        "brief_id": brief["brief_id"],
        "film_title": brief["title"],
        "positioning": positioning,
        "evidence_refs": investigation["provenance"]["call_ids"],
        "fact_claims": sum(
            1 for f in investigation["findings"] if f.get("claim_type") == "FACT"
        ),
        "unsupported_fact_claims": sum(
            1 for f in investigation["findings"]
            if f.get("claim_type") == "FACT" and not f.get("evidence_refs")
        ),
        "_hypothesis_refs": (primary or {}).get("evidence_refs", []) if primary else [],
        "limitations": investigation["limitations"],
        "open_questions": investigation["open_questions"],
        "data_status": "fixture",
        "generator": {"kind": "rule_based_grounded", "model": None},
        "stop_reason": state.stop_reason,
    }


# ============================================================
# Condition A — LLM-only
# ============================================================


from app.domain.llm_provider import LLMUnavailableError  # noqa: E402  (re-exported)


LLM_PROMPT_TEMPLATE = """You are advising an independent short-film creator on audience
positioning. You have NO access to cultural-affinity data, analytics, or audience
research — answer from your general knowledge only.

Film brief:
- Title: {title}
- Logline: {logline}
- Genre: {genre}
- Themes: {themes}

Reply with ONLY a JSON object, no markdown, with exactly these keys:
"hypothesis" (one positioning hypothesis), "world" (the cultural world it targets),
"success_criteria", "observation_window", "action_plan", "falsification",
"limitations" (a list of what you cannot know), "open_questions" (a list).
"""


class LLMGenerator(Protocol):
    kind: str

    def generate(self, brief: dict[str, Any]) -> dict[str, Any]: ...


class OpenAICompatibleLLM:
    """Real LLM condition. Delegates to the shared provider (M13.12)."""

    kind = "llm"

    def __init__(self) -> None:
        from app.domain.llm_provider import LLMProviderConfig, OpenAICompatibleProvider

        config = LLMProviderConfig.from_env()
        if not config.configured:
            raise LLMUnavailableError(
                "ADJACENT_LLM_API_KEY not configured — Condition A is BLOCKED "
                "(never silently stubbed)."
            )
        self.model = config.model
        self._provider = OpenAICompatibleProvider(config)

    def generate(self, brief: dict[str, Any]) -> dict[str, Any]:
        prompt = LLM_PROMPT_TEMPLATE.format(
            title=brief["title"],
            logline=brief["logline"],
            genre=brief["genre"],
            themes=", ".join(brief.get("themes", [])),
        )
        content = self._provider.complete(
            "You answer with a single JSON object and nothing else.", prompt
        )
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:]
        return json.loads(content)


class ScriptedStubLLM:
    """DETERMINISTIC STUB for harness mechanism tests ONLY. Labelled everywhere."""

    kind = "llm_stub"

    def generate(self, brief: dict[str, Any]) -> dict[str, Any]:
        return {
            "hypothesis": (
                f"Viewers who enjoy {brief['genre']} stories about "
                f"{', '.join(brief.get('themes', [])[:2]) or 'human connection'} "
                "may respond to this film."
            ),
            "world": brief["genre"],
            "success_criteria": "Positive viewer comments after release.",
            "observation_window": "A few weeks.",
            "action_plan": "Share the film with relevant communities.",
            "falsification": "If viewers do not respond, the hypothesis is wrong.",
            "limitations": ["No audience data was available."],
            "open_questions": ["Which communities exactly?"],
        }


def run_llm_condition(brief: dict[str, Any], generator: LLMGenerator) -> dict[str, Any]:
    raw = generator.generate(brief)
    positioning = {
        "hypothesis": raw.get("hypothesis"),
        "world": raw.get("world"),
        "success_criteria": raw.get("success_criteria"),
        "observation_window": raw.get("observation_window"),
        "action_plan": raw.get("action_plan"),
        "falsification": raw.get("falsification"),
    }
    limitations = raw.get("limitations") or []
    if isinstance(limitations, str):
        limitations = [limitations]
    open_questions = raw.get("open_questions") or []
    if isinstance(open_questions, str):
        open_questions = [open_questions]
    return {
        "condition": "llm_only",
        "brief_id": brief["brief_id"],
        "film_title": brief["title"],
        "positioning": positioning,
        "evidence_refs": [],  # by construction — Condition A has no evidence access
        "limitations": limitations,
        "open_questions": open_questions,
        "data_status": "none",
        "generator": {"kind": generator.kind, "model": getattr(generator, "model", None)},
        "stop_reason": "complete",
    }


# ============================================================
# Rubric v2 (M13.12) — separated, applicability-aware categories
# ============================================================

RUBRIC_VERSION = "3.0"

DECISION_QUALITY_ANCHORS = {
    "schema_valid": "1 = all required positioning fields present and non-empty strings; 0 otherwise.",
    "specific_world": "1 = hypothesis names a specific cultural world beyond restating the input genre; 0 = generic.",
    "falsifiable": "1 = success criteria + observation window + falsification condition are all concrete; 0 otherwise.",
    "uncertainty_handled": "1 = at least one limitation recorded; 0 = none.",
    "information_beyond_generic": "1 = output adds film-specific substance beyond restating the brief (grounded: evidence-linked sources; baseline: concrete named directions); 0 otherwise.",
}

EVIDENCE_GROUNDING_ANCHORS = {
    "evidence_refs_present": "1 = at least one evidence ref cited; 0 = none.",
    "refs_resolve": "1 = every cited ref exists in the run's evidence set; 0 = dangling refs.",
    "hypothesis_cites_evidence": "1 = the primary hypothesis carries at least one evidence ref; 0 = unsupported.",
}

#: Decision quality applies to BOTH conditions. Evidence grounding applies ONLY
#: to the grounded condition — scoring a no-evidence baseline on traceability
#: and folding it into one total is exactly the methodological error v1 made.
GROUNDING_APPLIES_TO = {"qloo_grounded"}


def _decision_quality(output: dict[str, Any]) -> dict[str, Any]:
    if not output.get("positioning"):
        # Honest abstention is not a decision-quality failure. These criteria
        # presuppose a recommendation exists; scoring them 0 would punish the
        # system for refusing to invent one. Abstention is scored separately.
        return {
            "applicable": False,
            "reason": "no positioning outcome — abstention_quality applies instead",
        }
    checks: dict[str, dict[str, Any]] = {}
    positioning = output.get("positioning") or {}
    required = ("hypothesis", "success_criteria", "observation_window", "action_plan", "falsification")
    schema_ok = bool(positioning) and all(
        isinstance(positioning.get(k), str) and positioning.get(k, "").strip() for k in required
    )
    checks["schema_valid"] = {"score": int(schema_ok), "note": "" if schema_ok else "missing/empty required fields"}

    genre = str(output.get("_genre") or "").lower()
    world = str(positioning.get("world") or "").lower()
    specific = bool(world) and world != genre and world not in ("", "general", "drama")
    if output["condition"] == "llm_only" and world and genre and world.strip() == genre.strip():
        specific = False
    checks["specific_world"] = {"score": int(specific), "note": f"world={world!r}"}

    falsifiable = schema_ok and bool(
        str(positioning.get("falsification") or "").strip()
        and len(str(positioning.get("observation_window") or "").split()) >= 3
    )
    checks["falsifiable"] = {"score": int(falsifiable), "note": ""}

    checks["uncertainty_handled"] = {"score": int(bool(output.get("limitations"))), "note": ""}

    refs = output.get("evidence_refs") or []
    beyond = (
        len(refs) >= 2
        or (output["condition"] == "qloo_grounded" and bool(positioning.get("world")))
        or (output["condition"] == "llm_only" and specific)
    )
    checks["information_beyond_generic"] = {"score": int(beyond), "note": ""}
    return {"checks": checks, "total": sum(c["score"] for c in checks.values()), "max": len(checks)}


ABSTENTION_ANCHORS = {
    "recognizes_insufficiency": "1 = the run itself stopped short of complete (evidence gate fired); 0 = claims completeness without a recommendation.",
    "explains_source": "1 = limitations name WHY evidence was insufficient; 0 = silent.",
    "avoids_unsupported_facts": "1 = no FACT claim lacks evidence refs (cited facts about what was genuinely returned are legitimate even in an abstaining run); 0 = facts asserted without support.",
    "no_forced_hypothesis": "1 = no positioning recommendation was manufactured; 0 = forced answer.",
    "identifies_next_info": "1 = open questions identify what to collect next; 0 = none.",
}


def _abstention_quality(output: dict[str, Any]) -> dict[str, Any] | None:
    """Applies ONLY to no-hypothesis outcomes. A refusal scores well only when
    the actual evidence/stop behaviour supports it — not every refusal is
    automatically correct."""
    if output.get("positioning"):
        return None
    limitations = " ".join(str(x) for x in output.get("limitations") or []).lower()
    checks = {
        "recognizes_insufficiency": {
            "score": int(output.get("stop_reason") not in (None, "complete")),
            "note": f"stop_reason={output.get('stop_reason')}",
        },
        "explains_source": {
            "score": int(any(
                p in limitations
                for p in ("unsupported", "insufficient", "no taste-profile", "no usable")
            )),
            "note": "",
        },
        "avoids_unsupported_facts": {
            "score": int(not output.get("unsupported_fact_claims")),
            "note": (
                f"unsupported_fact_claims={output.get('unsupported_fact_claims', 0)} "
                f"(of {output.get('fact_claims', 0)} FACT claims)"
            ),
        },
        "no_forced_hypothesis": {"score": 1, "note": "positioning is None"},
        "identifies_next_info": {
            "score": int(bool(output.get("open_questions"))),
            "note": "",
        },
    }
    return {"checks": checks, "total": sum(c["score"] for c in checks.values()), "max": len(checks)}


def _evidence_grounding(output: dict[str, Any]) -> dict[str, Any] | None:
    if output.get("condition") not in GROUNDING_APPLIES_TO:
        return None  # NOT APPLICABLE — never a misleading zero
    refs = output.get("evidence_refs") or []
    available = set(output.get("_available_refs") or refs)
    checks: dict[str, dict[str, Any]] = {
        "evidence_refs_present": {
            "score": int(bool(refs)),
            "note": f"{len(refs)} ref(s)",
        },
        "refs_resolve": {
            "score": int(bool(refs) and all(r in available for r in refs)),
            "note": "" if refs else "no refs",
        },
    }
    if output.get("positioning"):
        checks["hypothesis_cites_evidence"] = {
            "score": int(bool(output.get("_hypothesis_refs") or [])),
            "note": "",
        }
    else:
        # Insufficient-evidence path: no primary hypothesis exists, so the
        # criterion is NOT APPLICABLE — never scored as a misleading zero.
        checks["hypothesis_cites_evidence"] = {
            "score": None,
            "note": "no primary hypothesis (insufficient-evidence path); not applicable",
        }
    scored = [c for c in checks.values() if c["score"] is not None]
    return {"checks": checks, "total": sum(c["score"] for c in scored), "max": len(scored)}


def score_output(output: dict[str, Any]) -> dict[str, Any]:
    """Rubric v3: per-category scores with explicit applicability."""
    grounding = _evidence_grounding(output)
    abstention = _abstention_quality(output)
    applicable = [
        name
        for name, cat in (
            ("decision_quality", _decision_quality(output)),
            ("evidence_grounding", grounding),
            ("abstention_quality", abstention),
        )
        if cat and cat.get("checks")
    ]
    return {
        "rubric_version": RUBRIC_VERSION,
        "decision_quality": _decision_quality(output),
        "evidence_grounding": grounding,
        "abstention_quality": abstention,
        "categories_applicable": applicable,
    }


# ============================================================
# Human-rating template (independent raters; never fabricated here)
# ============================================================

HUMAN_RATING_CRITERIA = (
    "relevance_to_brief,specificity_of_positioning,actionability,"
    "falsifiability,uncertainty_handling,information_gain"
)
HUMAN_RATING_ANCHORS = (
    "0 = absent/generic; 1 = present but weak or partly off-brief; "
    "2 = specific, brief-tied and useful. Rater must be human; "
    "rater_type column records 'human'. No LLM-produced ratings are valid here."
)


def write_human_rating_template(path: Path, briefs: list[dict[str, Any]] | None = None) -> Path:
    import csv

    briefs = briefs if briefs is not None else BRIEFS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "brief_id", "condition", "criterion", "score_0_2", "rater_type", "rater_id", "notes",
        ])
        for brief in briefs:
            for condition in ("qloo_grounded", "llm_only"):
                for criterion in HUMAN_RATING_CRITERIA.split(","):
                    writer.writerow([brief["brief_id"], condition, criterion, "", "human", "", ""])
    return path


# ============================================================
# Runner + artefacts (v2)
# ============================================================


def run_comparison(
    briefs: list[dict[str, Any]] | None = None,
    llm_generator: LLMGenerator | None = None,
) -> dict[str, Any]:
    """Run both conditions over the briefs. Condition A is BLOCKED without a generator."""
    briefs = briefs if briefs is not None else BRIEFS
    runs: list[dict[str, Any]] = []
    condition_a_status = "ran"
    condition_a_error: str | None = None

    for brief in briefs:
        grounded = run_grounded_condition(brief)
        grounded["_available_refs"] = list(grounded["evidence_refs"])
        grounded["_genre"] = brief["genre"]
        grounded.setdefault("_hypothesis_refs", [])
        runs.append({
            "output": grounded,
            "scores": score_output(grounded),
            "run_metadata": {
                "rubric_version": RUBRIC_VERSION,
                "condition": "qloo_grounded",
                "provider_kind": grounded["generator"]["kind"],
                "model": None,
                "qloo_evidence": "fixture",
                "fixture": brief["fixture"],
                "fixture_alignment": (
                    "stand-in — the fixture evidence is a recorded demo scenario, "
                    "NOT Qloo data about this brief's specific themes"
                ),
                "evidence_refs_available": grounded["evidence_refs"],
            },
        })

        if llm_generator is not None:
            try:
                llm_out = run_llm_condition(brief, llm_generator)
                llm_out["_available_refs"] = []
                llm_out["_genre"] = brief["genre"]
                llm_out["_hypothesis_refs"] = []
                runs.append({
                    "output": llm_out,
                    "scores": score_output(llm_out),
                    "run_metadata": {
                        "rubric_version": RUBRIC_VERSION,
                        "condition": "llm_only",
                        "provider_kind": llm_generator.kind,
                        "model": getattr(llm_generator, "model", None),
                        "qloo_evidence": "none (by construction)",
                        "evidence_refs_available": [],
                    },
                })
            except Exception as exc:  # honest failure capture, no silent skip
                runs.append({
                    "output": {"condition": "llm_only", "brief_id": brief["brief_id"], "error": str(exc)},
                    "scores": None,
                    "failed": True,
                    "run_metadata": {
                        "rubric_version": RUBRIC_VERSION,
                        "condition": "llm_only",
                        "provider_kind": llm_generator.kind,
                        "error": str(exc),
                    },
                })
        else:
            condition_a_status = "blocked"

    if llm_generator is None:
        try:
            OpenAICompatibleLLM()
        except LLMUnavailableError as exc:
            condition_a_error = str(exc)

    def category_avg(cond: str, category: str) -> dict[str, Any]:
        scored = [
            r for r in runs
            if r.get("scores")
            and r["output"].get("condition") == cond
            and isinstance(r["scores"].get(category), dict)
            and r["scores"][category].get("checks")
        ]
        if not scored:
            return {"n": 0, "avg": None, "applicable": False}
        return {
            "n": len(scored),
            "avg": round(
                sum(r["scores"][category]["total"] / r["scores"][category]["max"] for r in scored)
                / len(scored),
                3,
            ),
            "scale": "0–1 (mean of per-run total/max)",
            "applicable": True,
        }

    summary = {
        "rubric_version": RUBRIC_VERSION,
        "note": (
            "Categories are reported separately. evidence_grounding applies ONLY "
            "to the grounded condition; decision_quality applies ONLY when a "
            "positioning outcome exists (honest abstention is scored by "
            "abstention_quality instead, never as a punitive zero)."
        ),
        "qloo_grounded": {
            "decision_quality": category_avg("qloo_grounded", "decision_quality"),
            "evidence_grounding": category_avg("qloo_grounded", "evidence_grounding"),
            "abstention_quality": category_avg("qloo_grounded", "abstention_quality"),
        },
        "llm_only": {
            "decision_quality": category_avg("llm_only", "decision_quality"),
            "evidence_grounding": {"applicable": False, "reason": "criterion not applicable to a no-evidence baseline"},
            "abstention_quality": category_avg("llm_only", "abstention_quality"),
        },
        "condition_a_status": condition_a_status,
        "condition_a_error": condition_a_error,
    }
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "methodology": METHODOLOGY,
        "rubric_version": RUBRIC_VERSION,
        "rubric_anchors": {
            "decision_quality": DECISION_QUALITY_ANCHORS,
            "evidence_grounding": EVIDENCE_GROUNDING_ANCHORS,
            "abstention_quality": ABSTENTION_ANCHORS,
            "applicability": (
                "decision_quality: both conditions, only when a positioning outcome exists; "
                "evidence_grounding: grounded condition only; "
                "abstention_quality: only when no positioning outcome exists"
            ),
        },
        "human_rating_anchors": HUMAN_RATING_ANCHORS,
        "summary": summary,
        "runs": runs,
    }


def write_artifact(result: dict[str, Any], directory: Path | None = None) -> Path:
    directory = directory or (adjacent_root / "data" / "processed")
    directory.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = directory / f"m13_11_qloo_vs_llm_{ts}.json"
    path.write_text(json.dumps(result, indent=2, default=str))
    return path


def main() -> None:
    stub = "--stub-a" in sys.argv
    generator: LLMGenerator | None = None
    if stub:
        print("NOTE: --stub-a uses the deterministic ScriptedStubLLM — MECHANISM TEST ONLY,")
        print("      labelled llm_stub in artefacts; it is NOT a real LLM condition.")
        generator = ScriptedStubLLM()
    result = run_comparison(llm_generator=generator)
    path = write_artifact(result)
    template = write_human_rating_template(
        adjacent_root / "data" / "processed" / "m13_12_human_rating_template.csv"
    )
    print(json.dumps(result["summary"], indent=2))
    print(f"artefact: {path}")
    print(f"human rating template: {template}")


if __name__ == "__main__":
    main()
