"""Cultural Investigation layer (M13.11).

Turns one completed creator run into a structured, auditable account of the
agent's investigation:

    questions asked → typed tools executed → Qloo evidence (by call_id)
    → findings (FACT vs INTERPRETATION, strictly separated)
    → positioning hypothesis + evidence-linked alternatives
    → limitations + open questions → a testable experiment

Design rules:
* DETERMINISTIC. No LLM is required or invoked; nothing here can hallucinate
  an entity. Every FACT statement cites the call_id(s) that produced it.
* Interpretations (band labels, reachability hypotheses) are explicitly
  labelled INTERPRETATION and never presented as Qloo-returned facts.
* Absent evidence produces honest statuses ("insufficient", "unavailable"),
  never substitute signal. With no ranked cohorts there are no hypotheses.
* `data_status` mirrors the run's real source ("measured" | "fixture").

The investigation is built from the same `AdjacentState` the orchestrator
filled, so the tool history it reports is the tool history that actually ran.
"""

from __future__ import annotations

import uuid
from typing import Any

#: Standard guard repeated on every investigation — affinity is cultural
#: similarity, never a viewership/revenue claim.
AFFINITY_GUARD = (
    "Cultural affinity measures similarity between expressed interests; it is "
    "not evidence that any audience will watch, enjoy or share the film."
)


def _q(
    qid: str,
    question: str,
    tool: str,
    operation: str,
    status: str,
    evidence_refs: list[str],
    summary: str,
) -> dict[str, Any]:
    return {
        "id": qid,
        "question": question,
        "tool": tool,
        "operation": operation,
        "status": status,  # answered | insufficient | unavailable
        "evidence_refs": [r for r in evidence_refs if r],
        "summary": summary,
    }


def build_investigation(
    state: Any,
    *,
    film: dict[str, Any],
    seeds: list[str],
    bet: Any,
    test_card: Any,
    geography: Any = None,
    city: str | None = None,
    data_status: str = "measured",
) -> dict[str, Any]:
    """Assemble the structured investigation from a completed run's state."""

    questions: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    limitations: list[str] = []
    open_questions: list[str] = []

    # -- Q0 (context framing, M13.12): asked only when the creator supplied
    # context beyond a title. Makes NO API call and says so.
    context_pairs = [
        ("genre", film.get("genre")),
        ("themes/seed references", ", ".join(seeds[1:4]) if len(seeds) > 1 else None),
        ("language", film.get("language")),
        ("release goal", film.get("release_goal")),
        ("logline", "supplied" if film.get("logline") else None),
    ]
    provided = [f"{name}: {value}" for name, value in context_pairs if value]
    missing = [name for name, value in context_pairs if not value]
    if provided:
        questions.append(_q(
            "q0",
            "What did the creator tell us, and what did they leave out?",
            "context_framing",
            "no API call — input validation only",
            "answered",
            [],
            "Context used to frame this investigation: " + "; ".join(provided)
            + (
                ". Not supplied (weakens the questions that follow): "
                + ", ".join(missing)
                if missing
                else "."
            ),
        ))

    # -- Q1: expressed profile (get_taste_profile over /v2/insights urn:tag)
    tags = list(getattr(state, "taste_tags", []) or [])
    resolved = getattr(state, "resolved_items", []) or []
    unresolved = getattr(state, "unresolved_items", []) or []
    taste_call = getattr(state, "taste_call_id", None)
    if tags:
        top = [t.name for t in tags[:5] if getattr(t, "name", None)]
        questions.append(_q(
            "q1",
            "Which cultural interests does this film's expressed profile carry?",
            "get_taste_profile",
            "/v2/insights?filter.type=urn:tag (signal: resolved seeds)",
            "answered",
            [taste_call or ""],
            f"{len(tags)} interest tags returned; strongest: {', '.join(top[:3]) or '—'}.",
        ))
        findings.append({
            "kind": "FACT",
            "claim_type": "FACT",
            "statement": (
                f"Qloo's taste profile for the resolved seed entities returned "
                f"{len(tags)} interest tags (top: {', '.join(top[:3]) or '—'})."
            ),
            "evidence_refs": [taste_call or ""],
        })
    else:
        questions.append(_q(
            "q1",
            "Which cultural interests does this film's expressed profile carry?",
            "get_taste_profile",
            "/v2/insights?filter.type=urn:tag (signal: resolved seeds)",
            "insufficient",
            [taste_call or ""],
            "No usable interest tags were returned — the expressed profile "
            "could not be established from the supplied seeds.",
        ))
        limitations.append(
            "No taste-profile evidence: every downstream connection in this run "
            "is unsupported."
        )

    if unresolved:
        limitations.append(
            f"{len(unresolved)} of {len(resolved) + len(unresolved)} seed "
            f"reference(s) could not be resolved to Qloo entities "
            f"({', '.join(u.title for u in unresolved[:3] if getattr(u, 'title', None)) or 'unnamed'}) "
            "— they contributed no evidence."
        )

    # -- Q2: adjacent cultural worlds (expand_candidates, one call per domain)
    expansion_calls = dict(getattr(state, "expansion_call_ids", {}) or {})
    candidates = dict(getattr(state, "candidates_by_domain", {}) or {})
    total_candidates = sum(len(v) for v in candidates.values())
    if total_candidates:
        domains = sorted(candidates.keys())
        questions.append(_q(
            "q2",
            "Which entities' cultural worlds sit adjacent to that profile?",
            "expand_candidates",
            "/v2/insights per domain (artist, film, music, …)",
            "answered",
            list(expansion_calls.values()),
            f"{total_candidates} candidate entities across {len(domains)} domain(s): "
            + ", ".join(d.replace("urn:entity:", "") for d in domains) + ".",
        ))
    else:
        questions.append(_q(
            "q2",
            "Which entities' cultural worlds sit adjacent to that profile?",
            "expand_candidates",
            "/v2/insights per domain (artist, film, music, …)",
            "insufficient",
            list(expansion_calls.values()),
            "No adjacent candidates were returned by any domain expansion.",
        ))

    # -- Q3: which world is most defensible (rank_cohorts)
    ranked = list(getattr(state, "ranked", []) or [])
    rejected = list(getattr(state, "rejected", []) or [])
    rank_calls = [
        c.score.call_id for c in ranked if getattr(c, "score", None) and c.score.call_id
    ]
    if ranked:
        top = ranked[0]
        names = [m.name for m in (top.members or [])[:3] if getattr(m, "name", None)]
        questions.append(_q(
            "q3",
            "Which adjacent world is the most defensible positioning target?",
            "rank_cohorts",
            "build_and_rank_cohorts over expanded candidates",
            "answered",
            rank_calls,
            f"{len(ranked)} cohort(s) passed the evidence gate; strongest: "
            f"{', '.join(names) or top.domain} ({top.domain.replace('urn:entity:', '')} domain).",
        ))
    else:
        questions.append(_q(
            "q3",
            "Which adjacent world is the most defensible positioning target?",
            "rank_cohorts",
            "build_and_rank_cohorts over expanded candidates",
            "insufficient",
            rank_calls,
            "No candidate world passed the evidence gate — no positioning "
            "hypothesis can be honestly supported.",
        ))

    if rejected:
        reasons = {}
        for cohort in rejected:
            rejection = getattr(cohort, "rejection", None)
            code = rejection.code.value if rejection and hasattr(rejection, "code") else "unknown"
            reasons[code] = reasons.get(code, 0) + 1
        limitations.append(
            f"{len(rejected)} candidate world(s) were excluded by the evidence "
            "gate (" + ", ".join(f"{n}× {code}" for code, n in sorted(reasons.items()))
            + "); exclusions are annotations, not deletions."
        )

    # -- Q4: geography (only meaningful when a release location was supplied)
    if city:
        if geography is not None and getattr(geography, "sufficient", False):
            questions.append(_q(
                "q4",
                "Does affinity concentrate geographically around the release location?",
                "cohort_heatmap",
                "/v2/insights?filter.type=urn:heatmap (post-pipeline, city supplied)",
                "answered",
                [getattr(geography, "call_id", "") or ""],
                f"{geography.total_cells} heatmap cells around "
                f"{getattr(geography, 'city_display', city)}.",
            ))
        elif geography is not None:
            questions.append(_q(
                "q4",
                "Does affinity concentrate geographically around the release location?",
                "cohort_heatmap",
                "/v2/insights?filter.type=urn:heatmap (post-pipeline, city supplied)",
                "insufficient",
                [getattr(geography, "call_id", "") or ""],
                "Heatmap returned too few cells to locate affinity — treated as "
                "unavailable, not as absence of audience.",
            ))
            open_questions.append(
                f"Geographic concentration around {city} is unresolved "
                "(sparse heatmap) — community-outreach targeting there is untested."
            )
        else:
            questions.append(_q(
                "q4",
                "Does affinity concentrate geographically around the release location?",
                "cohort_heatmap",
                "/v2/insights?filter.type=urn:heatmap (post-pipeline, city supplied)",
                "unavailable",
                [],
                "The heatmap call did not complete for this run.",
            ))

    # -- Adaptive follow-ups (M13.12): questions the EVIDENCE ITSELF raises.
    # Deterministic, asked only when the run's numbers justify them.
    if len(ranked) >= 2:
        top_score = ranked[0].score.mean_affinity if ranked[0].score else None
        second_score = ranked[1].score.mean_affinity if ranked[1].score else None
        if (
            top_score is not None
            and second_score is not None
            and (top_score - second_score) < 0.03
        ):
            second_names = [
                m.name for m in (ranked[1].members or [])[:2] if getattr(m, "name", None)
            ]
            rank_call_2 = ranked[1].score.call_id if ranked[1].score and ranked[1].score.call_id else ""
            questions.append(_q(
                "q5",
                "The two strongest cultural worlds are near-tied — which does the "
                "creator's own framing actually favour?",
                "rank_cohorts (follow-up)",
                "comparison of ranked[0] vs ranked[1] mean affinity",
                "insufficient",
                [c for c in [*rank_calls, rank_call_2] if c],
                f"Affinity gap between the top two worlds is under 0.03 "
                f"({top_score:.2f} vs {second_score:.2f}"
                + (f"; runner-up e.g. {', '.join(second_names)}" if second_names else "")
                + "). Affinity alone cannot break this tie — the creator's framing "
                "test must.",
            ))
    if ranked:
        top = ranked[0]
        total = len(top.members) if top.members else 0
        qualifying = len(top.qualifying_members) if getattr(top, "qualifying_members", None) else 0
        if total > 0 and qualifying / total < 0.3:
            questions.append(_q(
                "q6",
                "How much of the primary world actually qualifies — is the position "
                "narrower than it looks?",
                "rank_cohorts (follow-up)",
                "qualifying/total member ratio of ranked[0]",
                "answered",
                [c for c in rank_calls if c],
                f"Only {qualifying} of {total} candidate entities in the primary "
                f"world passed the affinity threshold — treat the position as "
                f"narrow and expect a smaller, more specific community.",
            ))

    # -- hypotheses (only from real ranked evidence)
    hypotheses: dict[str, Any] = {"primary": None, "alternatives": [], "rejected_worlds": []}
    if bet is not None and test_card is not None:
        hypotheses["primary"] = {
            "statement": test_card.audience_hypothesis,
            "cohort_id": bet.primary_cohort_id,
            "world": bet.primary_domain,
            "evidence_refs": [
                r for r in (
                    bet.primary_call_id, bet.adjacency_call_id, bet.breadth_call_id
                ) if r
            ],
            "supporting_evidence": bet.why,
            "falsification": bet.falsification_condition,
            "assumptions": [
                "The creator's stated references/themes genuinely represent the "
                "film's cultural profile.",
                "Qloo affinity between expressed interests is a legitimate "
                "positioning signal (similarity, not demand).",
            ],
            "distinguishing_evidence": (
                "Compare the creator's own post-release observations under the "
                f"{bet.primary_domain} framing against their usual framing"
                + (
                    f" and against the runner-up {bet.runner_up_domain} framing"
                    if bet.runner_up_domain
                    else ""
                )
                + "; the framing whose responses actually reference it is the "
                "one the evidence favours."
            ),
        }
        findings.append({
            "kind": "INTERPRETATION",
            "claim_type": "HYPOTHESIS",
            "statement": (
                f"Positioning hypothesis: an audience aligned with the "
                f"{bet.primary_domain} world is reachable with framing that "
                f"names that world. This is a hypothesis to test, not a "
                f"measured audience fact."
            ),
            "evidence_refs": [r for r in (bet.primary_call_id,) if r],
        })
        if bet.runner_up_domain and bet.runner_up_cohort_name:
            hypotheses["alternatives"].append({
                "statement": (
                    f"Alternative: position toward the {bet.runner_up_domain} world "
                    f"(e.g. {bet.runner_up_cohort_name}"
                    + (f", affinity {bet.runner_up_mean_affinity:.2f}" if bet.runner_up_mean_affinity else "")
                    + ")."
                ),
                "cohort_id": None,
                "world": bet.runner_up_domain,
                "evidence_refs": [r for r in (bet.runner_up_call_id,) if r],
            })
            if (
                bet.runner_up_mean_affinity
                and bet.primary_mean_affinity
                and (bet.primary_mean_affinity - bet.runner_up_mean_affinity) < 0.03
            ):
                open_questions.append(
                    "The two candidate worlds are near-tied on measured affinity — "
                    "consider testing both framings rather than committing to one."
                )
        for entry in bet.rejected_candidates:
            hypotheses["rejected_worlds"].append({
                "cohort_id": entry.get("cohort_id"),
                "world": entry.get("domain"),
                "reason": entry.get("reason"),
            })

    # -- experiment (from the Test Card; only when a hypothesis exists)
    experiment = None
    if test_card is not None:
        experiment = {
            "title": test_card.title,
            "action_plan": test_card.programming_direction,
            "success_criteria": test_card.success_criteria,
            "observation_window": test_card.observation_window,
            "falsification": test_card.falsification_condition,
        }
    else:
        open_questions.append(
            "No experiment is proposed: without a supported positioning "
            "hypothesis there is nothing defensible to test yet."
        )

    # -- standing limitations
    if data_status != "measured":
        limitations.insert(
            0,
            "This run used FIXTURE demonstration data — the entities, affinities "
            "and cohorts below are demo content, not live Qloo measurements.",
        )
    limitations.append(AFFINITY_GUARD)
    open_questions.append(
        "Whether the proposed framing actually changes reach can only be "
        "answered by the creator's own post-release observations."
    )

    # Unified claim model (M13.12): open questions surface as UNKNOWN findings
    # so one list carries FACT / INTERPRETATION / HYPOTHESIS / UNKNOWN.
    for oq in open_questions:
        findings.append({
            "kind": "UNKNOWN",
            "claim_type": "UNKNOWN",
            "statement": oq,
            "evidence_refs": [],
        })

    all_call_ids = [r for q in questions for r in q["evidence_refs"]]
    return {
        "investigation_id": str(uuid.uuid4()),
        "film": film,
        "seeds": seeds,
        "questions": questions,
        "findings": findings,
        "hypotheses": hypotheses,
        "experiment": experiment,
        "limitations": limitations,
        "open_questions": open_questions,
        "data_status": data_status,
        "provenance": {
            "call_ids": sorted(set(all_call_ids)),
            "qloo_calls_used": getattr(state, "calls_made", 0),
            "run_data_status": data_status,
        },
    }


def verify_evidence_refs(
    investigation: dict[str, Any], known_call_ids: set[str]
) -> tuple[dict[str, Any], list[str]]:
    """Drop evidence references that do not resolve to a real recorded call.

    A reference that cannot be resolved is not proof; keeping it would let a
    frontend display a dangling id as evidence. Removed refs are reported so
    the run records the fact honestly. Mutates and returns the investigation.
    """
    dropped: list[str] = []

    def _clean(refs: list[str]) -> list[str]:
        kept = []
        for ref in refs:
            if ref and ref in known_call_ids:
                kept.append(ref)
            elif ref:
                dropped.append(ref)
        return kept

    for question in investigation.get("questions", []):
        question["evidence_refs"] = _clean(list(question.get("evidence_refs", [])))
    for finding in investigation.get("findings", []):
        finding["evidence_refs"] = _clean(list(finding.get("evidence_refs", [])))
    hyp = investigation.get("hypotheses") or {}
    if hyp.get("primary"):
        hyp["primary"]["evidence_refs"] = _clean(list(hyp["primary"].get("evidence_refs", [])))
    for alt in hyp.get("alternatives", []) or []:
        alt["evidence_refs"] = _clean(list(alt.get("evidence_refs", [])))
    prov = investigation.get("provenance") or {}
    prov["call_ids"] = [c for c in prov.get("call_ids", []) if c in known_call_ids]
    if dropped:
        investigation.setdefault("limitations", []).append(
            f"{len(dropped)} evidence reference(s) could not be resolved to a "
            "recorded API call in this run and were removed rather than "
            "displayed as proof."
        )
    return investigation, sorted(set(dropped))
