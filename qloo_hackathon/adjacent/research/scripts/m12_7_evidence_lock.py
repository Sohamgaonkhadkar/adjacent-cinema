#!/usr/bin/env python3
"""M12.7: Evidence Lock — Replace hand-coded programme fit with real evidence.

Removes:
- FILM_GENRE_PROXIES
- GENRE_TO_THEME
- DOMAIN_THEMATIC_VECTORS
- member_ratio from programme_fit
- Hardcoded domain differentiation scores

Uses instead:
- Real Qloo tags from MemberEvidence
- Cohort construction evidence (shared_tags, kind)
- Event format for differentiation (not domain)
- programme_fit = NOT_AVAILABLE if insufficient real evidence
"""

import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

adjacent_root = Path(__file__).parent.parent.parent
env_path = adjacent_root / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ[key.strip()] = value.strip()

sys.path.insert(0, str(adjacent_root / 'backend'))

from app.config import Settings
from app.live_runner import run_live_async

# ============================================================
# CONTEXTS
# ============================================================

PRIMARY_CONTEXTS = [
    {
        "context_id": "genesis_london_2026_10",
        "venue": "Genesis Cinema",
        "city": "London",
        "venue_type": "INDEPENDENT",
        "source_url": "https://genesiscinema.co.uk",
        "programme_window": "October 2026",
        "films": [
            {"title": "American History X", "year": 1998, "imdb_id": "tt0120586"},
            {"title": "Rosemary's Baby", "year": 1968, "imdb_id": "tt0063522"},
            {"title": "Halloween", "year": 1978, "imdb_id": "tt0077651"},
            {"title": "Parasite", "year": 2019, "imdb_id": "tt6751668"},
            {"title": "The Substance", "year": 2024, "imdb_id": "tt17526714"},
            {"title": "Conclave", "year": 2024, "imdb_id": "tt20215234"},
        ],
    },
    {
        "context_id": "prince_charles_london_2026_10",
        "venue": "Prince Charles Cinema",
        "city": "London",
        "venue_type": "INDEPENDENT",
        "source_url": "https://princecharlescinema.com",
        "programme_window": "October 2026 (Horror season)",
        "films": [
            {"title": "The Thing", "year": 1982, "imdb_id": "tt0084787"},
            {"title": "The Shining", "year": 1980, "imdb_id": "tt0081505"},
            {"title": "Suspiria", "year": 1977, "imdb_id": "tt0076786"},
            {"title": "Perfect Blue", "year": 1997, "imdb_id": "tt0156887"},
            {"title": "Akira", "year": 1988, "imdb_id": "tt0094625"},
            {"title": "Possession", "year": 1981, "imdb_id": "tt0082933"},
            {"title": "Halloween", "year": 1978, "imdb_id": "tt0077651"},
            {"title": "Rosemary's Baby", "year": 1968, "imdb_id": "tt0063522"},
        ],
    },
]


# ============================================================
# NO HAND-CODED THEMATIC VECTORS
# ============================================================
# M12.7: FILM_GENRE_PROXIES, GENRE_TO_THEME, DOMAIN_THEMATIC_VECTORS
# are DELETED from the primary scoring path.
# Programme fit uses real Qloo evidence only.


# ============================================================
# COMPONENT 1: ENTITY_FIT (signal strength)
# ============================================================
# INPUTS: affinity, qualifying_members, total_members
# OVERLAP: NONE

def score_entity_fit(affinity: float, qualifying: int, total: int) -> tuple[int, dict]:
    if affinity >= 0.90 and qualifying >= 15:
        return 2, {"reason": f"Strong signal: affinity={affinity:.3f}, {qualifying} qualifying members"}
    elif affinity >= 0.85 and qualifying >= 10:
        return 1, {"reason": f"Moderate signal: affinity={affinity:.3f}, {qualifying} qualifying members"}
    else:
        return 0, {"reason": f"Weak signal: affinity={affinity:.3f}, {qualifying} qualifying members"}


# ============================================================
# COMPONENT 2: EVENT_FEASIBILITY (can we do this?)
# ============================================================
# INPUTS: domain, programme_films count
# OVERLAP: NONE

def score_event_feasibility(entity: dict) -> tuple[int, dict]:
    domain = entity.get("domain", "")
    programme_films = entity.get("programme_films", [])
    
    if len(programme_films) < 2:
        return 0, {"feasible": False, "format": None,
                    "reason": "Fewer than 2 programme films support this candidate"}
    
    if domain == "artist":
        if len(programme_films) >= 3:
            return 2, {"feasible": True, "format": "Live music performance/DJ set + film screening",
                       "reason": f"{len(programme_films)} programme films support music event"}
        else:
            return 1, {"feasible": True, "format": "Curated music + film screening",
                       "reason": f"{len(programme_films)} programme films provide moderate support"}
    elif domain == "tv_show":
        if len(programme_films) >= 3:
            return 2, {"feasible": True, "format": "Themed film screening season",
                       "reason": f"{len(programme_films)} programme films support themed season"}
        else:
            return 1, {"feasible": True, "format": "Double bill screening",
                       "reason": f"{len(programme_films)} programme films — limited thematic breadth"}
    elif domain == "book":
        if len(programme_films) >= 3:
            return 2, {"feasible": True, "format": "Film screening + book reading/discussion",
                       "reason": f"{len(programme_films)} programme films support literary event"}
        else:
            return 1, {"feasible": True, "format": "Film screening + reading",
                       "reason": f"{len(programme_films)} programme films — moderate support"}
    elif domain == "podcast":
        return 1, {"feasible": True, "format": "Live podcast recording + film screening",
                   "reason": "Podcast event is feasible but harder to execute"}
    else:
        return 0, {"feasible": False, "format": None,
                    "reason": f"Domain '{domain}' has no defined cinema event format"}


# ============================================================
# COMPONENT 3: PROGRAMME_FIT (real Qloo evidence only)
# ============================================================
# INPUTS: cohort_kind, shared_tags, candidate_tags
# SOURCE: Qloo API (MemberEvidence.tags, CandidateCohort.construction_evidence)
# OVERLAP: NONE — does not use affinity, member counts, or domain name
#
# M12.7: programme_fit uses ONLY real Qloo evidence:
# - cohort kind (tag_cluster > subtype_group > domain_group)
# - shared tags from construction evidence (real Qloo tags)
# - NOT member_ratio (removed — overlaps with entity_fit)
# - NOT hand-coded thematic vectors (deleted)
#
# If no real tag data is available, programme_fit = NOT_AVAILABLE

def score_programme_fit(entity: dict) -> tuple[int | str, dict]:
    """Programme fit from real Qloo evidence only.
    
    Inputs: cohort_kind, shared_tags (from construction_evidence),
            candidate_tags (from MemberEvidence)
    Source: Qloo API — real tags, real construction evidence
    Overlap: NONE
    """
    cohort_kind = entity.get("cohort_kind", "unknown")
    shared_tags = entity.get("shared_tags", [])
    candidate_tags = entity.get("candidate_tags", [])
    
    # Dimension A: Cohort construction quality
    # tag_cluster = Qloo found shared tags (strongest relationship)
    # subtype_group = Qloo found shared subtype
    # domain_group = only domain in common (weakest)
    # singleton_group = single candidate (insufficient)
    kind_scores = {
        "tag_cluster": 2,
        "subtype_group": 1,
        "domain_group": 0,
        "singleton_group": 0,
    }
    kind_score = kind_scores.get(cohort_kind, 0)
    
    # Dimension B: Tag evidence
    # shared_tags = tags that Qloo returned as connecting the cohort
    # candidate_tags = tags on this specific entity
    # More shared tags = stronger Qloo-returned relationship
    if shared_tags:
        tag_score = min(len(shared_tags), 2)  # cap at 2
    elif candidate_tags:
        tag_score = 1  # entity has tags but no shared tags
    else:
        tag_score = 0  # no tag data
    
    # Check if we have real evidence
    has_real_evidence = (
        cohort_kind in ("tag_cluster", "subtype_group") or
        len(shared_tags) > 0 or
        len(candidate_tags) > 0
    )
    
    if not has_real_evidence:
        return "NOT_AVAILABLE", {
            "status": "NOT_AVAILABLE",
            "reason": "No real Qloo tag or construction evidence available",
            "cohort_kind": cohort_kind,
            "shared_tags": shared_tags,
            "candidate_tag_count": len(candidate_tags),
        }
    
    # Combined programme fit
    raw = (kind_score + tag_score) / 2
    programme_fit = 2 if raw >= 1.5 else 1 if raw >= 0.5 else 0
    
    return programme_fit, {
        "status": "AVAILABLE",
        "cohort_kind": cohort_kind,
        "kind_score": kind_score,
        "shared_tags": shared_tags[:5],
        "candidate_tag_count": len(candidate_tags),
        "tag_score": tag_score,
        "programme_fit_score": programme_fit,
        "evidence_source": "Qloo API (cohort construction + entity tags)",
    }


# ============================================================
# COMPONENT 4: TESTABILITY (can we measure the outcome?)
# ============================================================
# INPUTS: event_format (string from feasibility), qualifying_members
# OVERLAP: format string shared with differentiation (NOT score)

def score_testability(entity: dict, feasibility_details: dict) -> tuple[int, dict]:
    qualifying = entity.get("qualifying_members", 0)
    event_format = feasibility_details.get("format", "")
    
    if not event_format:
        return 0, {"testable": False, "reason": "No event format defined"}
    
    # Outcome clarity: single events are more testable than seasons
    if "season" in event_format.lower():
        outcome_clarity = 1
    elif "live" in event_format.lower() or "dj" in event_format.lower() or "performance" in event_format.lower():
        outcome_clarity = 2
    elif "discussion" in event_format.lower() or "reading" in event_format.lower():
        outcome_clarity = 2
    elif "double bill" in event_format.lower():
        outcome_clarity = 2
    else:
        outcome_clarity = 1
    
    # Sample size
    if qualifying >= 30:
        sample_score = 2
    elif qualifying >= 15:
        sample_score = 1
    else:
        sample_score = 0
    
    # Confounding factors
    if "season" in event_format.lower():
        confound_score = 1
    else:
        confound_score = 2
    
    raw = (outcome_clarity + sample_score + confound_score) / 3
    testability = 2 if raw >= 1.5 else 1 if raw >= 0.5 else 0
    
    return testability, {
        "outcome_clarity": outcome_clarity,
        "sample_size_score": sample_score,
        "confound_score": confound_score,
        "testability_score": testability,
        "observable_outcome": "Attendance and engagement at the specific event",
        "measurement_note": "Success threshold TBD — requires empirical baseline from the cinema's historical data",
    }


# ============================================================
# COMPONENT 5: DIFFERENTIATION (from event format, NOT domain)
# ============================================================
# INPUTS: event_format (string from feasibility)
# M12.7: NO domain-based scoring. Domain name does not affect score.
# Score is purely from event format characteristics.

def score_differentiation(event_format: str) -> tuple[int, dict]:
    """Differentiation from event format only. No domain preference.
    
    Inputs: event_format (string from feasibility)
    Meaning: How different is this event from standard cinema programming?
    Overlap: NONE — no domain name used
    """
    if not event_format:
        return 0, {"reason": "No event format defined"}
    
    fmt = event_format.lower()
    
    # Live performance component: genuinely different
    has_live = any(kw in fmt for kw in ["live", "performance", "dj", "recording"])
    # Interactive component: somewhat different
    has_interactive = any(kw in fmt for kw in ["discussion", "reading", "q&a", "talk"])
    # Extended programming: somewhat different
    has_extended = any(kw in fmt for kw in ["season", "series"])
    
    if has_live:
        return 2, {"reason": "Live performance component is genuinely different from standard cinema",
                    "format_features": "live_performance"}
    elif has_interactive:
        return 1, {"reason": "Interactive component is somewhat different from standard cinema",
                    "format_features": "interactive"}
    elif has_extended:
        return 1, {"reason": "Extended programming (season) is somewhat different",
                    "format_features": "extended"}
    else:
        return 0, {"reason": "Standard screening format — not differentiated",
                    "format_features": "standard"}


# ============================================================
# SCORING ORCHESTRATOR
# ============================================================

def score_entity_m12_7(entity: dict) -> dict:
    """Score with M12.7 — no hand-coded preferences.
    
    programme_fit: real Qloo evidence only (NOT_AVAILABLE if insufficient)
    differentiation: event format only (no domain bias)
    per-film attribution: NOT_AVAILABLE (Qloo doesn't provide it)
    """
    affinity = entity.get("affinity") or 0
    qualifying = entity.get("qualifying_members", 0)
    total = entity.get("total_members", 0)
    domain = entity.get("domain", "")
    title = entity.get("title", "")
    
    # Component 1: Entity fit
    entity_fit, ef_details = score_entity_fit(affinity, qualifying, total)
    
    # Component 2: Event feasibility
    event_feasibility, fev_details = score_event_feasibility(entity)
    
    # Component 3: Programme fit (real evidence only)
    programme_fit_raw, pf_details = score_programme_fit(entity)
    
    # Component 4: Testability
    testability, test_details = score_testability(entity, fev_details)
    
    # Component 5: Differentiation (format only, no domain)
    differentiation, diff_details = score_differentiation(fev_details.get("format", ""))
    
    # Handle NOT_AVAILABLE programme_fit
    available_components = ["entity_fit", "event_feasibility", "testability", "differentiation"]
    missing_components = []
    
    if programme_fit_raw == "NOT_AVAILABLE":
        missing_components.append("programme_fit")
        programme_fit = 0  # placeholder for total, but not used in normalized score
    else:
        programme_fit = programme_fit_raw
        available_components.insert(2, "programme_fit")
    
    # Raw total (for ranking when all candidates have same availability)
    raw_total = entity_fit + event_feasibility + programme_fit + testability + differentiation
    
    # Normalized score from available components
    available_scores = [entity_fit, event_feasibility, testability, differentiation]
    if programme_fit_raw != "NOT_AVAILABLE":
        available_scores.append(programme_fit)
    
    max_possible = len(available_scores) * 2  # each component max = 2
    normalized_score = round(sum(available_scores) / max_possible * 10, 1) if max_possible > 0 else 0
    
    if raw_total >= 8:
        classification = "STRONG"
    elif raw_total >= 6:
        classification = "PLAUSIBLE"
    elif raw_total >= 4:
        classification = "WEAK"
    else:
        classification = "REJECT"
    
    return {
        "entity_title": title,
        "domain": domain,
        "affinity": round(affinity, 4),
        "qualifying_members": qualifying,
        "total_members": total,
        "programme_films": entity.get("programme_films", [])[:5],
        "entity_fit": entity_fit,
        "event_feasibility": event_feasibility,
        "programme_fit": programme_fit_raw,
        "testability": testability,
        "differentiation": differentiation,
        "raw_total": raw_total,
        "normalized_score": normalized_score,
        "classification": classification,
        "available_components": available_components,
        "missing_components": missing_components,
        "normalization_method": f"sum({len(available_scores)} components) / {max_possible} * 10",
        "entity_fit_details": ef_details,
        "event_feasibility_details": fev_details,
        "programme_fit_details": pf_details,
        "testability_details": test_details,
        "differentiation_details": diff_details,
        # Per-film attribution
        "per_film_attribution": "NOT_AVAILABLE",
        "per_film_attribution_note": (
            "Qloo's cohort structure does not provide reliable per-output attribution "
            "to individual programme films. support_count and support_ratio are NOT "
            "computed. Adjacent does not claim per-film causal attribution."
        ),
    }


def rank_and_select_m12_7(scored: list) -> dict:
    """Rank and select ONE Programme Bet."""
    viable = [s for s in scored if s["classification"] in ("STRONG", "PLAUSIBLE")]
    seen = set()
    unique = []
    for v in viable:
        if v["entity_title"] not in seen:
            seen.add(v["entity_title"])
            unique.append(v)
    
    # Sort by raw_total, then affinity
    unique.sort(key=lambda x: (-x["raw_total"], -x["affinity"]))
    top_5 = unique[:5]
    
    if not top_5:
        return {"top_5": [], "programme_bet": None}
    
    primary = top_5[0]
    fev = primary.get("event_feasibility_details", {})
    pf = primary.get("programme_fit_details", {})
    
    programme_bet = {
        "entity": primary["entity_title"],
        "domain": primary["domain"],
        "affinity": primary["affinity"],
        "qualifying_members": primary["qualifying_members"],
        "supporting_films": "NOT_AVAILABLE",
        "supporting_films_note": "Per-film attribution not available from Qloo cohort structure",
        "event_format": fev.get("format", "Unknown"),
        "what_is_known": (
            f"Qloo returns {primary['domain']} entities with affinity {primary['affinity']:.3f} "
            f"and {primary['qualifying_members']} qualifying members. "
            f"Cohort kind: {pf.get('cohort_kind', 'unknown')}. "
            f"Programme fit: {pf.get('status', 'unknown')}."
        ),
        "what_is_unknown": (
            "Per-film attribution (which programme films drove this candidate). "
            "Empirical success thresholds (require venue baseline data)."
        ),
        "why": (
            f"The {primary['domain']} '{primary['entity_title']}' has cultural affinity "
            f"({primary['affinity']:.3f}) with {primary['qualifying_members']} qualifying members. "
            f"{fev.get('reason', '')}"
        ),
        "hypothesis": (
            f"A cinema with this programming profile should test a {primary['domain']}-adjacent "
            f"event because '{primary['entity_title']}' shows cultural affinity with the programme."
        ),
        "success_metric": (
            "Primary outcome: attendance / new-to-venue attendance / engagement. "
            "Threshold: TBD — must be calibrated against the cinema's historical baseline."
        ),
        "falsification": (
            f"This hypothesis is rejected if: (1) the {primary['domain']} affinity signal "
            f"cannot be reproduced across the next comparable programme analysis, or "
            f"(2) a subsequent analysis does not surface a similar {primary['domain']} "
            f"opportunity in the top-5, or (3) the event format proves operationally "
            f"infeasible at the venue."
        ),
    }
    
    alternatives = [
        {
            "entity": t["entity_title"],
            "domain": t["domain"],
            "raw_total": t["raw_total"],
            "affinity": t["affinity"],
            "programme_fit": t["programme_fit"],
            "reason_not_selected": f"Lower raw_total ({t['raw_total']} vs {primary['raw_total']})",
        }
        for t in top_5[1:5]
    ]
    
    return {"top_5": top_5, "programme_bet": programme_bet, "alternatives": alternatives}


# ============================================================
# ABLATION
# ============================================================

def ablation_analysis(scored: list, programme_bet: dict) -> list:
    if not programme_bet:
        return []
    
    bet_entity = programme_bet["entity"]
    components = ["entity_fit", "event_feasibility", "programme_fit", "testability", "differentiation"]
    
    results = []
    for removed in components:
        ablated = []
        for s in scored:
            val = s.get(removed)
            if val == "NOT_AVAILABLE":
                val = 0
            new_total = s["raw_total"] - (val if isinstance(val, (int, float)) else 0)
            ablated.append({
                "entity_title": s["entity_title"],
                "domain": s["domain"],
                "full_score": s["raw_total"],
                "ablated_score": new_total,
                "removed_component": removed,
            })
        
        ablated.sort(key=lambda x: -x["ablated_score"])
        
        bet_rank = None
        bet_ablated_score = None
        for i, a in enumerate(ablated):
            if a["entity_title"] == bet_entity:
                bet_rank = i + 1
                bet_ablated_score = a["ablated_score"]
                break
        
        new_top = ablated[0] if ablated else None
        
        results.append({
            "removed_component": removed,
            "bet_entity": bet_entity,
            "bet_full_score": next(s["raw_total"] for s in scored if s["entity_title"] == bet_entity),
            "bet_ablated_score": bet_ablated_score,
            "bet_rank": bet_rank,
            "new_top_entity": new_top["entity_title"] if new_top else None,
            "new_top_score": new_top["ablated_score"] if new_top else None,
            "rank_change": (bet_rank - 1) if bet_rank else None,
        })
    
    return results


# ============================================================
# QLOO EVALUATION (with real tag extraction)
# ============================================================

async def run_qloo_evaluation(context: dict) -> dict:
    films = context["films"]
    
    try:
        state = await run_live_async(films, render=False, resolver_delay_s=1.0)
        
        coverage = {
            "total": len(films),
            "resolved": len(state.resolved_items),
            "resolution_rate": round(len(state.resolved_items) / len(films), 2),
        }
        
        programme_names = [p.resolved_name or p.title for p in state.resolved_items]
        
        all_nonfilm = []
        for cohort in state.ranked:
            score = cohort.score
            members = cohort.members if cohort.members else []
            domain = cohort.domain.replace("urn:entity:", "")
            if domain == "movie":
                continue
            
            # Real cohort evidence
            cohort_kind = cohort.kind if hasattr(cohort, "kind") else "unknown"
            construction_evidence = cohort.construction_evidence if hasattr(cohort, "construction_evidence") else {}
            shared_tags = construction_evidence.get("shared_tags", [])
            
            for member in members:
                # Real member tags from Qloo
                candidate_tags = []
                if hasattr(member, "scored") and hasattr(member.scored, "tags"):
                    candidate_tags = [t.tag_id for t in member.scored.tags if t.tag_id]
                
                all_nonfilm.append({
                    "entity_id": member.entity_id if hasattr(member, "entity_id") else None,
                    "title": member.name if hasattr(member, "name") else str(member),
                    "domain": domain,
                    "affinity": member.affinity if hasattr(member, "affinity") else None,
                    "cohort_id": cohort.cohort_id,
                    "qloo_call_id": score.call_id if score else None,
                    "qualifying_members": len(cohort.qualifying_members) if cohort.members else 0,
                    "total_members": len(cohort.members) if cohort.members else 0,
                    "programme_films": programme_names,
                    # Real Qloo evidence (M12.7)
                    "cohort_kind": cohort_kind,
                    "shared_tags": shared_tags,
                    "candidate_tags": candidate_tags,
                    "construction_reason": cohort.construction_reason if hasattr(cohort, "construction_reason") else "",
                })
        
        all_nonfilm.sort(key=lambda x: -(x.get("affinity") or 0))
        
        return {
            "success": True,
            "coverage": coverage,
            "programme_names": programme_names,
            "raw_nonfilm": all_nonfilm,
            "raw_count": len(all_nonfilm),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "raw_nonfilm": [], "raw_count": 0}


async def run_evaluation():
    print("=" * 70)
    print("M12.7: EVIDENCE LOCK — NO HAND-CODED PREFERENCES")
    print("=" * 70)
    print(f"Primary contexts: {len(PRIMARY_CONTEXTS)}")
    print()
    print("REMOVED FROM SCORING:")
    print("  - FILM_GENRE_PROXIES (hand-coded genre mapping)")
    print("  - GENRE_TO_THEME (hand-coded theme mapping)")
    print("  - DOMAIN_THEMATIC_VECTORS (hand-coded domain themes)")
    print("  - member_ratio from programme_fit (overlaps with entity_fit)")
    print("  - Hardcoded domain differentiation scores")
    print("  - Per-film support counts (not available from Qloo)")
    print()
    print("ADDED:")
    print("  - Real Qloo tags from MemberEvidence")
    print("  - Cohort construction evidence (shared_tags, kind)")
    print("  - programme_fit = NOT_AVAILABLE if no real evidence")
    print("  - Differentiation from event format only (no domain bias)")
    print()
    
    results = []
    
    for i, ctx in enumerate(PRIMARY_CONTEXTS):
        print(f"\n{'='*70}")
        print(f"CONTEXT {i+1}: {ctx['venue']}")
        print(f"  Films: {len(ctx['films'])}")
        print(f"{'='*70}")
        
        print(f"  Running Qloo...")
        qloo = await run_qloo_evaluation(ctx)
        
        if not qloo["success"]:
            print(f"  FAILED: {qloo.get('error')}")
            results.append({"venue": ctx["venue"], "qloo_success": False, "error": qloo.get("error")})
            continue
        
        cov = qloo["coverage"]
        print(f"  Resolved: {cov['resolved']}/{cov['total']} ({cov['resolution_rate']:.0%})")
        print(f"  Raw non-film: {qloo['raw_count']}")
        
        # Score
        scored = []
        for c in qloo["raw_nonfilm"]:
            scored.append(score_entity_m12_7(c))
        
        counts = defaultdict(int)
        pf_available = 0
        pf_not_available = 0
        for s in scored:
            counts[s["classification"]] += 1
            if s["programme_fit"] == "NOT_AVAILABLE":
                pf_not_available += 1
            else:
                pf_available += 1
        
        print(f"\n  Classification breakdown:")
        for cls in ["STRONG", "PLAUSIBLE", "WEAK", "REJECT"]:
            print(f"    {cls}: {counts[cls]}")
        
        print(f"\n  Programme fit availability:")
        print(f"    AVAILABLE: {pf_available}")
        print(f"    NOT_AVAILABLE: {pf_not_available}")
        
        # Filter counts
        evidence_qualified = [s for s in scored if s["affinity"] >= 0.80 and s["qualifying_members"] >= 5]
        feasibility_qualified = [s for s in evidence_qualified if s["event_feasibility"] >= 1]
        
        print(f"\n  Filter pipeline:")
        print(f"    Raw: {qloo['raw_count']}")
        print(f"    Evidence-qualified: {len(evidence_qualified)}")
        print(f"    Feasibility-qualified: {len(feasibility_qualified)}")
        
        # Rank and select
        selection = rank_and_select_m12_7(scored)
        top_5 = selection["top_5"]
        programme_bet = selection["programme_bet"]
        
        print(f"\n  TOP 5:")
        for j, opp in enumerate(top_5):
            pf_label = opp['programme_fit'] if opp['programme_fit'] == "NOT_AVAILABLE" else str(opp['programme_fit'])
            print(f"    {j+1}. {opp['entity_title']} ({opp['domain']}) — "
                  f"raw={opp['raw_total']}, aff={opp['affinity']:.3f}, "
                  f"class={opp['classification']}")
            print(f"       entity_fit={opp['entity_fit']}, feasibility={opp['event_feasibility']}, "
                  f"prog_fit={pf_label}, test={opp['testability']}, diff={opp['differentiation']}")
            pf = opp.get('programme_fit_details', {})
            print(f"       programme_fit: status={pf.get('status', '?')}, "
                  f"kind={pf.get('cohort_kind', '?')}, "
                  f"shared_tags={len(pf.get('shared_tags', []))}")
            dd = opp.get('differentiation_details', {})
            print(f"       differentiation: {dd.get('reason', '?')}")
        
        if programme_bet:
            print(f"\n  PROGRAMME BET:")
            print(f"    Entity: {programme_bet['entity']} ({programme_bet['domain']})")
            print(f"    Affinity: {programme_bet['affinity']:.3f}")
            print(f"    Format: {programme_bet['event_format']}")
            print(f"    Known: {programme_bet['what_is_known'][:100]}...")
            print(f"    Unknown: {programme_bet['what_is_unknown'][:100]}...")
        
        # Ablation
        ablation = ablation_analysis(scored, programme_bet)
        if ablation:
            print(f"\n  ABLATION:")
            for a in ablation:
                changed = "YES" if a["rank_change"] and a["rank_change"] > 0 else "NO"
                print(f"    Remove {a['removed_component']}: bet_rank={a['bet_rank']}, "
                      f"new_top={a['new_top_entity']}, changed={changed}")
        
        result = {
            "context_id": ctx["context_id"],
            "venue": ctx["venue"],
            "qloo_success": True,
            "raw_count": qloo["raw_count"],
            "classification_counts": dict(counts),
            "programme_fit_available": pf_available,
            "programme_fit_not_available": pf_not_available,
            "top_5": top_5,
            "programme_bet": programme_bet,
            "ablation": ablation,
        }
        results.append(result)
    
    # Cross-context comparison
    print(f"\n{'='*70}")
    print("CROSS-CONTEXT COMPARISON")
    print(f"{'='*70}")
    
    for r in results:
        bet = r.get("programme_bet")
        if bet:
            print(f"\n  {r['venue']}:")
            print(f"    Bet: {bet['entity']} ({bet['domain']})")
            print(f"    Format: {bet['event_format']}")
    
    if len(results) >= 2:
        bets = [r["programme_bet"] for r in results if r.get("programme_bet")]
        if len(bets) >= 2:
            print(f"\n  Same domain: {bets[0]['domain'] == bets[1]['domain']}")
            print(f"  Same entity: {bets[0]['entity'] == bets[1]['entity']}")
    
    # What actually changed the decision
    print(f"\n{'='*70}")
    print("WHAT ACTUALLY CHANGED THE DECISION")
    print(f"{'='*70}")
    for r in results:
        ablation = r.get("ablation", [])
        if ablation:
            print(f"\n  {r['venue']}:")
            for a in ablation:
                if a.get("rank_change") and a["rank_change"] > 0:
                    print(f"    {a['removed_component']} → rank changes by {a['rank_change']}")
            # If no component changes the rank
            if not any(a.get("rank_change") and a["rank_change"] > 0 for a in ablation):
                print(f"    No single component changes the bet")
    
    # Save
    output = {
        "evaluation_date": datetime.now(timezone.utc).isoformat(),
        "evaluation_version": "M12.7",
        "methodology_notes": [
            "FILM_GENRE_PROXIES removed from primary scoring path",
            "GENRE_TO_THEME removed from primary scoring path",
            "DOMAIN_THEMATIC_VECTORS removed from primary scoring path",
            "member_ratio removed from programme_fit (overlaps with entity_fit)",
            "Hardcoded domain differentiation scores removed",
            "programme_fit uses real Qloo evidence only (tags, cohort kind)",
            "Differentiation scored from event format, not domain name",
            "Per-film attribution: NOT_AVAILABLE (Qloo doesn't provide it)",
            "programme_fit = NOT_AVAILABLE when no real tag/construction evidence exists",
        ],
        "results": results,
    }
    
    output_path = adjacent_root / "data" / "processed" / "m12_7_evidence_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nResults saved to: {output_path}")
    
    return output


if __name__ == "__main__":
    asyncio.run(run_evaluation())