#!/usr/bin/env python3
"""M12.5: Programme Bet Quality Lock.

Makes the decision layer genuinely discriminative.
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
from app.domain.programme_bet import build_programme_bet

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
# FEASIBILITY RULES: What makes a cinema event realistic?
# ============================================================

def assess_event_feasibility(entity: dict) -> dict:
    """Assess whether a specific entity can form a realistic cinema event.
    
    Returns feasibility assessment with concrete format or rejection reason.
    """
    domain = entity.get("domain", "")
    title = entity.get("title", "")
    affinity = entity.get("affinity") or 0
    qualifying = entity.get("qualifying_members", 0)
    programme_films = entity.get("programme_films", [])
    
    feasibility = {
        "feasible": False,
        "format": None,
        "rationale": None,
        "rejection_reason": None,
    }
    
    if domain == "artist":
        # Artist: needs concrete music/screening concept
        # A concert venue or music event paired with film screening
        if affinity >= 0.85 and qualifying >= 10:
            feasibility["feasible"] = True
            feasibility["format"] = "Film screening + live music performance/DJ set inspired by the programme's aesthetic"
            feasibility["rationale"] = f"The artist '{title}' has strong cultural affinity with the programme. A live music event would attract the same audience."
        else:
            feasibility["rejection_reason"] = "Insufficient evidence for concrete music event"
    
    elif domain == "book":
        # Book: needs concrete film/book pairing
        if affinity >= 0.85 and qualifying >= 10:
            feasibility["feasible"] = True
            feasibility["format"] = "Film screening + book reading/discussion event with themed programme"
            feasibility["rationale"] = f"The book '{title}' shares thematic DNA with the programme. A literary event would complement the film season."
        else:
            feasibility["rejection_reason"] = "Insufficient evidence for literary event"
    
    elif domain == "tv_show":
        # TV show: needs concrete cinematic relationship
        # NOT "screen the TV show" (rights issues)
        # Instead: themed season inspired by the show's audience/themes
        if affinity >= 0.85 and qualifying >= 10:
            feasibility["feasible"] = True
            feasibility["format"] = "Themed film screening season inspired by the show's audience and themes"
            feasibility["rationale"] = f"The TV show '{title}' attracts an audience with similar cultural tastes. A themed film season would reach them."
        else:
            feasibility["rejection_reason"] = "Insufficient evidence for themed season"
    
    elif domain == "podcast":
        # Podcast: needs concrete live recording/discussion
        if affinity >= 0.85 and qualifying >= 10:
            feasibility["feasible"] = True
            feasibility["format"] = "Live podcast recording + film screening with host discussion"
            feasibility["rationale"] = f"The podcast '{title}' covers themes aligned with the programme. A live event would attract the same audience."
        else:
            feasibility["rejection_reason"] = "Insufficient evidence for podcast event"
    
    elif domain == "brand":
        # Brand: needs legitimate cultural partnership
        # Most brands are NOT programmable
        feasibility["rejection_reason"] = "Brand partnerships require bespoke negotiation and are not directly programmable as cinema events"
    
    else:
        feasibility["rejection_reason"] = f"Domain '{domain}' has no defined cinema event format"
    
    return feasibility


def compute_programme_fit(entity: dict, programme_genres: set, programme_decades: set) -> dict:
    """Compute deterministic programme fit.
    
    Uses only existing Qloo/metadata evidence. No LLM.
    """
    domain = entity.get("domain", "")
    affinity = entity.get("affinity") or 0
    qualifying = entity.get("qualifying_members", 0)
    total = entity.get("total_members", 0)
    
    # Programme fit based on evidence strength
    # Higher affinity = stronger cultural relationship to programme
    if affinity >= 0.9:
        programme_fit = 2  # Strong fit
        fit_signal = "Very high cultural affinity with programme"
    elif affinity >= 0.8:
        programme_fit = 1  # Moderate fit
        fit_signal = "Moderate cultural affinity with programme"
    else:
        programme_fit = 0  # Weak fit
        fit_signal = "Low cultural affinity"
    
    # Support ratio: what fraction of cohort qualifies
    support_ratio = qualifying / total if total > 0 else 0
    
    return {
        "programme_fit": programme_fit,
        "fit_signal": fit_signal,
        "support_ratio": round(support_ratio, 3),
        "qualifying_members": qualifying,
        "total_members": total,
    }


def score_entity_discriminative(entity: dict, programme_genres: set, programme_decades: set) -> dict:
    """Score a single entity with discriminative filters.
    
    Five components, total = 10.
    NOT automatic points for non-film domain.
    """
    affinity = entity.get("affinity") or 0
    domain = entity.get("domain", "")
    title = entity.get("title", "")
    qualifying = entity.get("qualifying_members", 0)
    call_id = entity.get("qloo_call_id")
    cohort_id = entity.get("cohort_id")
    
    # A. RETRIEVAL PROVENANCE (binary flag, not scored)
    has_provenance = bool(call_id and cohort_id)
    
    # B. CULTURAL EVIDENCE (binary flag, not scored)
    has_cultural_evidence = affinity >= 0.8 and qualifying >= 5
    
    # C. ENTITY_FIT (0-2)
    # Does the SPECIFIC entity have a clear cultural relationship?
    entity_fit = 2 if affinity >= 0.9 and qualifying >= 15 else 1 if affinity >= 0.85 and qualifying >= 10 else 0
    
    # D. EVENT_FEASIBILITY (0-2)
    # Can this SPECIFIC entity form a realistic cinema event?
    feasibility = assess_event_feasibility(entity)
    event_feasibility = 2 if feasibility["feasible"] and affinity >= 0.9 else 1 if feasibility["feasible"] else 0
    
    # E. PROGRAMME_FIT (0-2)
    # Does it complement the actual programme?
    prog_fit = compute_programme_fit(entity, programme_genres, programme_decades)
    programme_fit_score = prog_fit["programme_fit"]
    
    # F. TESTABILITY (0-2)
    # Can the cinema run a concrete experiment?
    testability = 2 if feasibility["feasible"] and feasibility["format"] else 1 if feasibility["feasible"] else 0
    
    # G. DIFFERENTIATION (0-2)
    # NOT automatic for non-film. Must be genuinely different.
    if domain == "artist":
        differentiation = 2 if affinity >= 0.9 else 1  # Music event is genuinely different
    elif domain == "book":
        differentiation = 2 if affinity >= 0.9 else 1  # Literary event is genuinely different
    elif domain == "tv_show":
        differentiation = 1 if affinity >= 0.85 else 0  # Themed season is somewhat different
    elif domain == "podcast":
        differentiation = 1 if affinity >= 0.85 else 0  # Live recording is somewhat different
    else:
        differentiation = 0  # Brand/other: not clearly different
    
    total = entity_fit + event_feasibility + programme_fit_score + testability + differentiation
    
    if total >= 8:
        classification = "STRONG"
    elif total >= 6:
        classification = "PLAUSIBLE"
    elif total >= 4:
        classification = "WEAK"
    else:
        classification = "REJECT"
    
    return {
        "entity_title": title,
        "domain": domain,
        "affinity": round(affinity, 4),
        "qualifying_members": qualifying,
        "total_members": entity.get("total_members", 0),
        "cohort_id": cohort_id,
        "qloo_call_id": call_id,
        "programme_films": entity.get("programme_films", [])[:3],
        # Separated concepts
        "retrieval_provenance": has_provenance,
        "cultural_evidence": has_cultural_evidence,
        # Five discriminative components
        "entity_fit": entity_fit,
        "event_feasibility": event_feasibility,
        "programme_fit": programme_fit_score,
        "testability": testability,
        "differentiation": differentiation,
        "total_score": total,
        "classification": classification,
        # Feasibility details
        "feasibility": feasibility,
        "programme_fit_details": prog_fit,
    }


def rank_and_select(scored: list) -> dict:
    """Rank opportunities and select ONE Programme Bet."""
    # Filter: only STRONG or PLAUSIBLE
    viable = [s for s in scored if s["classification"] in ("STRONG", "PLAUSIBLE")]
    
    # Deduplicate by title
    seen = set()
    unique = []
    for v in viable:
        if v["entity_title"] not in seen:
            seen.add(v["entity_title"])
            unique.append(v)
    
    # Rank by total_score, then affinity
    unique.sort(key=lambda x: (-x["total_score"], -x["affinity"]))
    
    top_5 = unique[:5]
    
    # Select ONE Programme Bet
    if not top_5:
        return {"top_5": [], "programme_bet": None}
    
    primary = top_5[0]
    
    programme_bet = {
        "entity": primary["entity_title"],
        "domain": primary["domain"],
        "affinity": primary["affinity"],
        "qualifying_members": primary["qualifying_members"],
        "supporting_films": primary["programme_films"],
        "why": (f"The {primary['domain']} '{primary['entity_title']}' has strong cultural affinity "
                f"({primary['affinity']:.3f}) with {primary['qualifying_members']} qualifying members. "
                f"{primary['feasibility']['rationale']}"),
        "experiment": primary["feasibility"]["format"],
        "hypothesis": (f"A cinema with this programming profile should test a {primary['domain']}-adjacent "
                      f"event because '{primary['entity_title']}' shares cultural DNA with the programme."),
        "success_criterion": (f"Event attracts ≥20 attendees with ≥50% new-to-venue visitors, "
                             f"or generates ≥3 positive audience responses indicating cultural resonance."),
        "falsification": (f"This hypothesis is rejected if: (1) a similar {primary['domain']} event "
                         f"attracts <10 attendees, or (2) audience feedback indicates no cultural connection "
                         f"to the programme, or (3) a subsequent programme analysis fails to surface "
                         f"a similar {primary['domain']} opportunity."),
    }
    
    alternatives = [
        {
            "entity": t["entity_title"],
            "domain": t["domain"],
            "score": t["total_score"],
            "affinity": t["affinity"],
            "reason_not_selected": f"Lower total score ({t['total_score']} vs {primary['total_score']})",
        }
        for t in top_5[1:5]
    ]
    
    return {"top_5": top_5, "programme_bet": programme_bet, "alternatives": alternatives}


async def run_qloo_evaluation(context: dict) -> dict:
    """Run Qloo pipeline."""
    films = context["films"]
    
    try:
        state = await run_live_async(films, render=False, resolver_delay_s=1.0)
        
        coverage = {
            "total": len(films),
            "resolved": len(state.resolved_items),
            "resolution_rate": round(len(state.resolved_items) / len(films), 2),
        }
        
        programme_names = [p.resolved_name or p.title for p in state.resolved_items]
        
        # Extract non-film candidates with provenance
        all_nonfilm = []
        for cohort in state.ranked:
            score = cohort.score
            members = cohort.members if cohort.members else []
            for member in members:
                domain = cohort.domain.replace("urn:entity:", "")
                if domain == "movie":
                    continue
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
                })
        
        all_nonfilm.sort(key=lambda x: -(x.get("affinity") or 0))
        
        # Programme metadata for fit assessment
        # Use genres from programme films (deterministic, no LLM)
        programme_genres = set()
        programme_decades = set()
        for f in films:
            year = f.get("year")
            if year:
                decade = f"{(year // 10) * 10}s"
                programme_decades.add(decade)
        
        return {
            "success": True,
            "coverage": coverage,
            "programme_names": programme_names,
            "raw_nonfilm": all_nonfilm,
            "raw_count": len(all_nonfilm),
            "programme_genres": list(programme_genres),
            "programme_decades": list(programme_decades),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "raw_nonfilm": [], "raw_count": 0}


async def run_evaluation():
    """Run M12.5 evaluation."""
    print("=" * 70)
    print("M12.5: PROGRAMME BET QUALITY LOCK")
    print("=" * 70)
    print(f"Primary contexts: {len(PRIMARY_CONTEXTS)}")
    print()
    
    results = []
    
    for i, ctx in enumerate(PRIMARY_CONTEXTS):
        print(f"\n{'='*70}")
        print(f"CONTEXT {i+1}: {ctx['venue']}")
        print(f"  Films: {len(ctx['films'])}")
        print(f"{'='*70}")
        
        # Run Qloo
        print(f"  Running Qloo...")
        qloo = await run_qloo_evaluation(ctx)
        
        if not qloo["success"]:
            print(f"  FAILED: {qloo.get('error')}")
            results.append({"venue": ctx["venue"], "qloo_success": False, "error": qloo.get("error")})
            continue
        
        cov = qloo["coverage"]
        print(f"  Resolved: {cov['resolved']}/{cov['total']} ({cov['resolution_rate']:.0%})")
        print(f"  Raw non-film: {qloo['raw_count']}")
        
        # Score all candidates with discriminative filters
        scored = []
        for c in qloo["raw_nonfilm"]:
            scored.append(score_entity_discriminative(
                c, 
                set(qloo["programme_genres"]), 
                set(qloo["programme_decades"])
            ))
        
        # Count classifications
        counts = defaultdict(int)
        for s in scored:
            counts[s["classification"]] += 1
        
        print(f"\n  Classification breakdown:")
        for cls in ["STRONG", "PLAUSIBLE", "WEAK", "REJECT"]:
            print(f"    {cls}: {counts[cls]}")
        
        # Filter counts
        evidence_qualified = [s for s in scored if s["cultural_evidence"]]
        feasibility_qualified = [s for s in evidence_qualified if s["feasibility"]["feasible"]]
        programme_fit_qualified = [s for s in feasibility_qualified if s["programme_fit"] >= 1]
        
        print(f"\n  Filter pipeline:")
        print(f"    Raw: {qloo['raw_count']}")
        print(f"    Evidence-qualified: {len(evidence_qualified)}")
        print(f"    Feasibility-qualified: {len(feasibility_qualified)}")
        print(f"    Programme-fit-qualified: {len(programme_fit_qualified)}")
        
        # Rank and select
        selection = rank_and_select(scored)
        top_5 = selection["top_5"]
        programme_bet = selection["programme_bet"]
        alternatives = selection.get("alternatives", [])
        
        print(f"\n  TOP 5:")
        for j, opp in enumerate(top_5):
            print(f"    {j+1}. {opp['entity_title']} ({opp['domain']}) — "
                  f"score={opp['total_score']}, aff={opp['affinity']:.3f}, "
                  f"class={opp['classification']}")
            print(f"       entity_fit={opp['entity_fit']}, feasibility={opp['event_feasibility']}, "
                  f"prog_fit={opp['programme_fit']}, test={opp['testability']}, diff={opp['differentiation']}")
        
        if programme_bet:
            print(f"\n  PROGRAMME BET:")
            print(f"    Entity: {programme_bet['entity']} ({programme_bet['domain']})")
            print(f"    Affinity: {programme_bet['affinity']:.3f}")
            print(f"    Experiment: {programme_bet['experiment']}")
            print(f"    Hypothesis: {programme_bet['hypothesis'][:100]}...")
            print(f"    Success: {programme_bet['success_criterion'][:80]}...")
            print(f"    Falsification: {programme_bet['falsification'][:80]}...")
        
        result = {
            "context_id": ctx["context_id"],
            "venue": ctx["venue"],
            "venue_type": ctx["venue_type"],
            "programme_films": ctx["films"],
            "qloo_success": True,
            "qloo_coverage": cov,
            "programme_names": qloo["programme_names"],
            "raw_count": qloo["raw_count"],
            "evidence_qualified": len(evidence_qualified),
            "feasibility_qualified": len(feasibility_qualified),
            "programme_fit_qualified": len(programme_fit_qualified),
            "classification_counts": dict(counts),
            "top_5": top_5,
            "programme_bet": programme_bet,
            "alternatives": alternatives,
        }
        results.append(result)
    
    # ============================================================
    # CROSS-CONTEXT COMPARISON
    # ============================================================
    print(f"\n{'='*70}")
    print("CROSS-CONTEXT COMPARISON")
    print(f"{'='*70}")
    
    for r in results:
        bet = r.get("programme_bet")
        if bet:
            print(f"\n  {r['venue']}:")
            print(f"    Bet: {bet['entity']} ({bet['domain']})")
            print(f"    Experiment: {bet['experiment']}")
    
    # Check if they collapse to same type
    if len(results) >= 2:
        bets = [r["programme_bet"] for r in results if r.get("programme_bet")]
        if len(bets) >= 2:
            same_domain = bets[0]["domain"] == bets[1]["domain"]
            same_entity = bets[0]["entity"] == bets[1]["entity"]
            print(f"\n  Same domain: {same_domain}")
            print(f"  Same entity: {same_entity}")
            if same_domain and same_entity:
                print(f"  WARNING: Both contexts selected the same entity — investigate!")
    
    # Save
    output = {
        "evaluation_date": datetime.now(timezone.utc).isoformat(),
        "evaluation_version": "M12.5",
        "results": results,
    }
    
    output_path = adjacent_root / "data" / "processed" / "m12_5_quality_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nResults saved to: {output_path}")
    
    return output


if __name__ == "__main__":
    asyncio.run(run_evaluation())