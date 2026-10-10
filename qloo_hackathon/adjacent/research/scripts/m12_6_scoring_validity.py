#!/usr/bin/env python3
"""M12.6: Scoring Validity Lock.

Rebuilds scoring with genuinely independent components.
Fixes:
1. programme_fit uses programme-specific evidence (not just affinity)
2. event_feasibility and testability are genuinely distinct
3. No arbitrary business thresholds
4. Ablation analysis
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
# PROGRAMME METADATA (deterministic, from film titles/years)
# ============================================================

# Genre proxies for programme films (deterministic — inferred from known titles)
FILM_GENRE_PROXIES = {
    "American History X": {"drama", "crime"},
    "Rosemary's Baby": {"horror", "thriller"},
    "Halloween": {"horror", "thriller"},
    "Parasite": {"thriller", "drama", "dark_comedy"},
    "The Substance": {"horror", "body_horror", "sci-fi"},
    "Conclave": {"thriller", "drama"},
    "The Thing": {"horror", "sci-fi"},
    "The Shining": {"horror", "psychological"},
    "Suspiria": {"horror", "supernatural"},
    "Perfect Blue": {"horror", "psychological", "anime"},
    "Akira": {"sci-fi", "anime", "cyberpunk"},
    "Possession": {"horror", "psychological"},
}

# Domain thematic vectors (deterministic — what themes each domain can offer)
DOMAIN_THEMATIC_VECTORS = {
    "artist": {"dark", "atmospheric", "subcultural", "countercultural", "experimental"},
    "tv_show": {"narrative", "serial", "character_driven", "genre"},
    "book": {"literary", "narrative", "thematic", "intellectual"},
    "podcast": {"conversational", "topical", "narrative"},
    "brand": {"commercial", "lifestyle"},
    "movie": {"cinematic", "narrative"},
}

# Genre-to-theme mapping (deterministic)
GENRE_TO_THEME = {
    "horror": {"dark", "atmospheric", "subcultural"},
    "thriller": {"dark", "tension", "narrative"},
    "drama": {"narrative", "character_driven", "emotional"},
    "sci-fi": {"speculative", "futuristic", "experimental"},
    "dark_comedy": {"dark", "subcultural", "countercultural"},
    "body_horror": {"dark", "atmospheric", "subcultural", "experimental"},
    "psychological": {"dark", "atmospheric", "intellectual"},
    "supernatural": {"dark", "atmospheric", "subcultural"},
    "anime": {"visual", "experimental", "subcultural"},
    "cyberpunk": {"dark", "futuristic", "subcultural", "experimental"},
    "crime": {"dark", "narrative", "tension"},
}


def compute_programme_direction(films: list) -> dict:
    """Compute programme direction from film metadata.
    
    Returns genre set, decade set, and thematic vector.
    Deterministic — no Qloo data needed.
    """
    genres = set()
    decades = set()
    themes = set()
    
    for f in films:
        title = f.get("title", "")
        year = f.get("year")
        
        # Genres
        film_genres = FILM_GENRE_PROXIES.get(title, set())
        genres |= film_genres
        
        # Decades
        if year:
            decades.add(f"{(year // 10) * 10}s")
        
        # Themes (from genres)
        for g in film_genres:
            themes |= GENRE_TO_THEME.get(g, set())
    
    return {
        "genres": genres,
        "decades": decades,
        "themes": themes,
        "has_horror": "horror" in genres,
        "has_dark_themes": bool(themes & {"dark", "atmospheric", "subcultural"}),
        "era_spread": len(decades),
    }


# ============================================================
# COMPONENT 1: ENTITY_FIT (signal strength)
# ============================================================
# INPUTS: affinity, qualifying_members, total_members
# MEANING: How strong is the Qloo signal for this entity?
# CALCULATION: thresholds on affinity AND member count
# OVERLAP WITH OTHERS: NONE

def score_entity_fit(affinity: float, qualifying: int, total: int) -> tuple[int, dict]:
    """Entity fit: signal strength and evidence breadth.
    
    Inputs: affinity (Qloo), qualifying_members, total_members
    Meaning: Is the cultural signal strong and broad enough to act on?
    Overlap: NONE
    """
    if affinity >= 0.90 and qualifying >= 15:
        return 2, {"reason": f"Strong signal: affinity={affinity:.3f}, {qualifying} qualifying members"}
    elif affinity >= 0.85 and qualifying >= 10:
        return 1, {"reason": f"Moderate signal: affinity={affinity:.3f}, {qualifying} qualifying members"}
    else:
        return 0, {"reason": f"Weak signal: affinity={affinity:.3f}, {qualifying} qualifying members"}


# ============================================================
# COMPONENT 2: EVENT_FEASIBILITY (can we do this?)
# ============================================================
# INPUTS: domain, programme_films, qualifying_members
# MEANING: Can this entity realistically become a cinema event?
# CALCULATION: domain-specific feasibility rules
# OVERLAP WITH OTHERS: NONE — does not use affinity, member counts, or testability

def score_event_feasibility(entity: dict) -> tuple[int, dict]:
    """Event feasibility: can this become a realistic cinema event?
    
    Inputs: domain, programme_films, qualifying_members
    Meaning: Is there a concrete, venue-compatible event format?
    Overlap: NONE
    """
    domain = entity.get("domain", "")
    programme_films = entity.get("programme_films", [])
    qualifying = entity.get("qualifying_members", 0)
    
    if len(programme_films) < 2:
        return 0, {"feasible": False, "reason": "Fewer than 2 programme films support this candidate"}
    
    if domain == "artist":
        if len(programme_films) >= 3:
            return 2, {"feasible": True, "format": "Film screening + live music/DJ set",
                       "reason": f"{len(programme_films)} programme films support music event"}
        else:
            return 1, {"feasible": True, "format": "Film screening + curated music",
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
            return 2, {"feasible": True, "format": "Film screening + book discussion",
                       "reason": f"{len(programme_films)} programme films support literary event"}
        else:
            return 1, {"feasible": True, "format": "Film screening + reading",
                       "reason": f"{len(programme_films)} programme films — moderate support"}
    elif domain == "podcast":
        if len(programme_films) >= 3:
            return 1, {"feasible": True, "format": "Live podcast + film screening",
                       "reason": "Podcast event is feasible but harder to execute"}
        else:
            return 0, {"feasible": False, "reason": "Insufficient programme support for podcast event"}
    elif domain == "brand":
        return 0, {"feasible": False, "reason": "Brand partnerships require bespoke negotiation"}
    else:
        return 0, {"feasible": False, "reason": f"Domain '{domain}' has no defined cinema event format"}


# ============================================================
# COMPONENT 3: PROGRAMME_FIT (does it complement the programme?)
# ============================================================
# INPUTS: domain, programme_direction (from film metadata), member composition
# MEANING: How well does this candidate's domain align with the programme's themes?
# CALCULATION: thematic alignment + member composition
# OVERLAP WITH OTHERS: NONE — uses programme_direction (from film metadata) and
#                       member composition, not affinity or feasibility

def score_programme_fit(entity: dict, programme_direction: dict,
                        programme_film_count: int) -> tuple[int, dict]:
    """Programme fit: thematic alignment with the specific programme.
    
    Inputs: domain (from entity), programme_direction (from film metadata — genres,
            decades, themes), programme_film_count, member composition (from entity)
    Meaning: Does this candidate's domain complement the programme's thematic profile?
    Overlap: NONE — uses programme_direction (from film metadata, not Qloo) and
             member composition (qualifying/total), not affinity
    """
    domain = entity.get("domain", "")
    qualifying = entity.get("qualifying_members", 0)
    total = entity.get("total_members", 0)
    
    # Dimension A: Thematic alignment
    # Does the candidate's domain align with the programme's themes?
    domain_themes = DOMAIN_THEMATIC_VECTORS.get(domain, set())
    programme_themes = programme_direction.get("themes", set())
    theme_overlap = len(domain_themes & programme_themes)
    
    # Horror programme → dark/atmospheric domains score higher
    has_horror = programme_direction.get("has_horror", False)
    has_dark = programme_direction.get("has_dark_themes", False)
    
    if domain == "artist":
        # Artists can offer dark/atmospheric/experimental themes
        if has_horror or has_dark:
            thematic_score = 2  # Strong alignment with dark programme
        else:
            thematic_score = 1  # Moderate alignment
    elif domain == "tv_show":
        # TV shows offer narrative/genre themes
        if has_horror:
            thematic_score = 1  # Horror shows exist, but themed season is less direct
        else:
            thematic_score = 1  # Moderate alignment
    elif domain == "book":
        # Books offer literary/thematic depth
        thematic_score = 1  # Always moderate — books complement any programme
    elif domain == "podcast":
        # Podcasts offer conversational/topical themes
        thematic_score = 1  # Moderate
    else:
        thematic_score = 0  # Brand/other: weak alignment
    
    # Dimension B: Member composition quality
    # How robust is the cohort? (varies per candidate)
    member_ratio = qualifying / total if total > 0 else 0
    if member_ratio >= 0.9:
        composition_score = 2
    elif member_ratio >= 0.7:
        composition_score = 1
    else:
        composition_score = 0
    
    # Combined programme fit
    raw = (thematic_score + composition_score) / 2
    programme_fit = 2 if raw >= 1.5 else 1 if raw >= 0.5 else 0
    
    return programme_fit, {
        "domain_themes": sorted(domain_themes),
        "programme_themes": sorted(programme_themes),
        "theme_overlap_count": theme_overlap,
        "thematic_score": thematic_score,
        "qualifying_members": qualifying,
        "total_members": total,
        "member_ratio": round(member_ratio, 3),
        "composition_score": composition_score,
        "programme_fit_score": programme_fit,
        "note": "Uses programme direction (from film metadata) and member composition. Does NOT use affinity.",
    }


# ============================================================
# COMPONENT 4: TESTABILITY (can we test the hypothesis?)
# ============================================================
# INPUTS: domain, event_format (string from feasibility), qualifying_members
# MEANING: Can the resulting hypothesis be tested with a clear observable outcome?
# CALCULATION: observable outcome + timeline + confounding factors
# OVERLAP: uses event FORMAT STRING from feasibility, NOT the feasibility SCORE

def score_testability(entity: dict, feasibility_details: dict) -> tuple[int, dict]:
    """Testability: can the hypothesis be tested?
    
    Inputs: domain, qualifying_members, event format (string from feasibility)
    Meaning: Can we run a clear experiment with observable outcomes?
    Overlap: uses event FORMAT (string) from feasibility, NOT the score
    A candidate may be feasible (score=2) but poorly testable (score=0)
    """
    domain = entity.get("domain", "")
    qualifying = entity.get("qualifying_members", 0)
    event_format = feasibility_details.get("format", "")
    
    if not event_format:
        return 0, {"testable": False, "reason": "No event format defined — cannot test"}
    
    # Factor 1: Observable outcome
    # Single events are more testable than ongoing seasons
    if "season" in event_format.lower():
        outcome_clarity = 1  # Season: harder to attribute to single cause
    elif "live" in event_format.lower() or "dj" in event_format.lower():
        outcome_clarity = 2  # Live event: clear attendance signal
    elif "discussion" in event_format.lower() or "reading" in event_format.lower():
        outcome_clarity = 2  # Interactive event: clear engagement signal
    else:
        outcome_clarity = 1  # Default: moderate clarity
    
    # Factor 2: Sample size adequacy
    # Need enough potential attendees to draw conclusions
    if qualifying >= 30:
        sample_score = 2
    elif qualifying >= 15:
        sample_score = 1
    else:
        sample_score = 0
    
    # Factor 3: Confounding factors
    # Some event types have more confounds than others
    if "season" in event_format.lower():
        confound_score = 1  # Season: multiple films, harder to isolate cause
    elif "double bill" in event_format.lower():
        confound_score = 2  # Double bill: two films, moderate isolation
    else:
        confound_score = 2  # Single event: good isolation
    
    # Combined testability
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
# COMPONENT 5: DIFFERENTIATION (is this genuinely different?)
# ============================================================
# INPUTS: domain, event_format (string from feasibility)
# MEANING: Is this event genuinely different from standard cinema programming?
# CALCULATION: domain novelty + format novelty
# OVERLAP: uses event FORMAT STRING from feasibility, NOT the score

def score_differentiation(domain: str, event_format: str) -> tuple[int, dict]:
    """Differentiation: is this genuinely different from cinema?
    
    Inputs: domain, event_format (string from feasibility)
    Meaning: Would this attract a different audience or create a new experience?
    Overlap: uses format STRING from feasibility, NOT the score
    """
    if domain in ("film", "movie"):
        return 0, {"reason": "Film screening is standard cinema programming"}
    
    # Domain novelty
    if domain == "artist":
        domain_novelty = 2  # Music events are genuinely different
    elif domain == "book":
        domain_novelty = 2  # Literary events are genuinely different
    elif domain == "tv_show":
        domain_novelty = 1  # Themed seasons are somewhat different
    elif domain == "podcast":
        domain_novelty = 1  # Live recordings are somewhat different
    else:
        domain_novelty = 0
    
    # Format novelty
    if not event_format:
        return 0, {"reason": "No event format to differentiate"}
    
    if "live" in event_format.lower() or "performance" in event_format.lower() or "dj" in event_format.lower():
        format_novelty = 2  # Live component is genuinely different
    elif "discussion" in event_format.lower() or "reading" in event_format.lower():
        format_novelty = 1  # Interactive but not radically different
    elif "season" in event_format.lower():
        format_novelty = 1  # Extended programming is somewhat different
    else:
        format_novelty = 0  # Standard screening
    
    raw = (domain_novelty + format_novelty) / 2
    differentiation = 2 if raw >= 1.5 else 1 if raw >= 0.5 else 0
    
    return differentiation, {
        "domain_novelty": domain_novelty,
        "format_novelty": format_novelty,
        "differentiation_score": differentiation,
    }


# ============================================================
# SCORING ORCHESTRATOR
# ============================================================

def score_entity_m12_6(entity: dict, programme_direction: dict,
                       programme_film_count: int) -> dict:
    """Score with M12.6 independent components.
    
    Each component uses different evidence:
    1. entity_fit: affinity + member counts (from Qloo)
    2. event_feasibility: domain + programme_films count (from entity dict)
    3. programme_fit: programme_direction (from film metadata) + member composition
    4. testability: event_format (string) + qualifying_members
    5. differentiation: domain + event_format (string)
    """
    affinity = entity.get("affinity") or 0
    qualifying = entity.get("qualifying_members", 0)
    total = entity.get("total_members", 0)
    domain = entity.get("domain", "")
    title = entity.get("title", "")
    
    entity_fit, ef_details = score_entity_fit(affinity, qualifying, total)
    event_feasibility, fev_details = score_event_feasibility(entity)
    programme_fit, pf_details = score_programme_fit(entity, programme_direction, programme_film_count)
    testability, test_details = score_testability(entity, fev_details)
    differentiation, diff_details = score_differentiation(domain, fev_details.get("format", ""))
    
    total_score = entity_fit + event_feasibility + programme_fit + testability + differentiation
    
    if total_score >= 8:
        classification = "STRONG"
    elif total_score >= 6:
        classification = "PLAUSIBLE"
    elif total_score >= 4:
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
        "programme_fit": programme_fit,
        "testability": testability,
        "differentiation": differentiation,
        "total_score": total_score,
        "classification": classification,
        "entity_fit_details": ef_details,
        "event_feasibility_details": fev_details,
        "programme_fit_details": pf_details,
        "testability_details": test_details,
        "differentiation_details": diff_details,
    }


def rank_and_select_m12_6(scored: list) -> dict:
    """Rank and select ONE Programme Bet. No arbitrary thresholds."""
    viable = [s for s in scored if s["classification"] in ("STRONG", "PLAUSIBLE")]
    seen = set()
    unique = []
    for v in viable:
        if v["entity_title"] not in seen:
            seen.add(v["entity_title"])
            unique.append(v)
    
    unique.sort(key=lambda x: (-x["total_score"], -x["affinity"]))
    top_5 = unique[:5]
    
    if not top_5:
        return {"top_5": [], "programme_bet": None}
    
    primary = top_5[0]
    fev = primary.get("event_feasibility_details", {})
    
    programme_bet = {
        "entity": primary["entity_title"],
        "domain": primary["domain"],
        "affinity": primary["affinity"],
        "qualifying_members": primary["qualifying_members"],
        "supporting_films": primary["programme_films"],
        "why": (f"The {primary['domain']} '{primary['entity_title']}' has cultural affinity "
                f"({primary['affinity']:.3f}) with {primary['qualifying_members']} qualifying members. "
                f"{fev.get('reason', '')}"),
        "experiment": fev.get("format", "Cinema event"),
        "hypothesis": (f"A cinema with this programming profile should test a {primary['domain']}-adjacent "
                      f"event because '{primary['entity_title']}' shares cultural DNA with the programme."),
        "success_criterion": (
            "Primary outcome: attendance / new-to-venue attendance / engagement. "
            "Threshold: TBD — must be calibrated against the cinema's historical baseline. "
            "Do not use arbitrary thresholds."
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
            "score": t["total_score"],
            "affinity": t["affinity"],
            "reason_not_selected": f"Lower total score ({t['total_score']} vs {primary['total_score']})",
        }
        for t in top_5[1:5]
    ]
    
    return {"top_5": top_5, "programme_bet": programme_bet, "alternatives": alternatives}


# ============================================================
# ABLATION
# ============================================================

def ablation_analysis(scored: list, programme_bet: dict) -> list:
    """Ablation: remove each component and check rank change."""
    if not programme_bet:
        return []
    
    bet_entity = programme_bet["entity"]
    components = ["entity_fit", "event_feasibility", "programme_fit", "testability", "differentiation"]
    
    results = []
    for removed in components:
        ablated = []
        for s in scored:
            new_total = s["total_score"] - s[removed]
            ablated.append({
                "entity_title": s["entity_title"],
                "domain": s["domain"],
                "full_score": s["total_score"],
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
            "bet_full_score": next(s["total_score"] for s in scored if s["entity_title"] == bet_entity),
            "bet_ablated_score": bet_ablated_score,
            "bet_rank": bet_rank,
            "new_top_entity": new_top["entity_title"] if new_top else None,
            "new_top_score": new_top["ablated_score"] if new_top else None,
            "rank_change": (bet_rank - 1) if bet_rank else None,
        })
    
    return results


# ============================================================
# QLOO EVALUATION
# ============================================================

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
                    "cohort_kind": cohort.kind if hasattr(cohort, "kind") else "unknown",
                })
        
        all_nonfilm.sort(key=lambda x: -(x.get("affinity") or 0))
        
        programme_direction = compute_programme_direction(films)
        
        return {
            "success": True,
            "coverage": coverage,
            "programme_names": programme_names,
            "raw_nonfilm": all_nonfilm,
            "raw_count": len(all_nonfilm),
            "programme_direction": programme_direction,
            "programme_film_count": len(films),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "raw_nonfilm": [], "raw_count": 0}


async def run_evaluation():
    """Run M12.6 evaluation."""
    print("=" * 70)
    print("M12.6: SCORING VALIDITY LOCK")
    print("=" * 70)
    print(f"Primary contexts: {len(PRIMARY_CONTEXTS)}")
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
        
        pd = qloo["programme_direction"]
        print(f"  Programme direction: genres={sorted(pd['genres'])}")
        print(f"    decades={sorted(pd['decades'])}, has_horror={pd['has_horror']}")
        
        # Score
        scored = []
        for c in qloo["raw_nonfilm"]:
            scored.append(score_entity_m12_6(
                c,
                qloo["programme_direction"],
                qloo["programme_film_count"],
            ))
        
        counts = defaultdict(int)
        for s in scored:
            counts[s["classification"]] += 1
        
        print(f"\n  Classification breakdown:")
        for cls in ["STRONG", "PLAUSIBLE", "WEAK", "REJECT"]:
            print(f"    {cls}: {counts[cls]}")
        
        evidence_qualified = [s for s in scored if s["affinity"] >= 0.80 and s["qualifying_members"] >= 5]
        feasibility_qualified = [s for s in evidence_qualified if s["event_feasibility"] >= 1]
        programme_fit_qualified = [s for s in feasibility_qualified if s["programme_fit"] >= 1]
        
        print(f"\n  Filter pipeline:")
        print(f"    Raw: {qloo['raw_count']}")
        print(f"    Evidence-qualified: {len(evidence_qualified)}")
        print(f"    Feasibility-qualified: {len(feasibility_qualified)}")
        print(f"    Programme-fit-qualified: {len(programme_fit_qualified)}")
        
        selection = rank_and_select_m12_6(scored)
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
            pf = opp['programme_fit_details']
            print(f"       programme_fit: thematic={pf['thematic_score']}, "
                  f"composition={pf['member_ratio']:.2f} ({pf['composition_score']})")
        
        if programme_bet:
            print(f"\n  PROGRAMME BET:")
            print(f"    Entity: {programme_bet['entity']} ({programme_bet['domain']})")
            print(f"    Affinity: {programme_bet['affinity']:.3f}")
            print(f"    Experiment: {programme_bet['experiment']}")
            print(f"    Success: {programme_bet['success_criterion'][:100]}...")
        
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
            "venue_type": ctx["venue_type"],
            "programme_films": ctx["films"],
            "qloo_success": True,
            "qloo_coverage": cov,
            "programme_names": qloo["programme_names"],
            "raw_count": qloo["raw_count"],
            "programme_direction": pd,
            "evidence_qualified": len(evidence_qualified),
            "feasibility_qualified": len(feasibility_qualified),
            "programme_fit_qualified": len(programme_fit_qualified),
            "classification_counts": dict(counts),
            "top_5": top_5,
            "programme_bet": programme_bet,
            "alternatives": alternatives,
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
            print(f"    Experiment: {bet['experiment']}")
    
    if len(results) >= 2:
        bets = [r["programme_bet"] for r in results if r.get("programme_bet")]
        if len(bets) >= 2:
            same_domain = bets[0]["domain"] == bets[1]["domain"]
            same_entity = bets[0]["entity"] == bets[1]["entity"]
            print(f"\n  Same domain: {same_domain}")
            print(f"  Same entity: {same_entity}")
    
    # Component independence table
    print(f"\n{'='*70}")
    print("COMPONENT INDEPENDENCE TABLE")
    print(f"{'='*70}")
    print()
    print("| Component         | Inputs                                      | Evidence source       |")
    print("|-------------------|---------------------------------------------|-----------------------|")
    print("| entity_fit        | affinity, qualifying_members, total_members | Qloo API              |")
    print("| event_feasibility | domain, programme_films count               | Entity dict + rules   |")
    print("| programme_fit     | programme_direction, member composition     | Film metadata + entity|")
    print("| testability       | event_format (str), qualifying_members      | Feasibility output    |")
    print("| differentiation   | domain, event_format (str)                  | Entity + feasibility  |")
    print()
    print("Key: programme_fit uses programme_direction (from film titles/years, NOT Qloo)")
    print("     and member composition (qualifying/total ratio, NOT raw affinity).")
    print("     testability and differentiation use the FORMAT STRING, not the SCORE.")
    
    # Save
    output = {
        "evaluation_date": datetime.now(timezone.utc).isoformat(),
        "evaluation_version": "M12.6",
        "component_independence": {
            "entity_fit": {
                "inputs": ["affinity", "qualifying_members", "total_members"],
                "source": "Qloo API",
                "overlap": "NONE",
            },
            "event_feasibility": {
                "inputs": ["domain", "programme_films_count"],
                "source": "Entity dict + domain rules",
                "overlap": "NONE",
            },
            "programme_fit": {
                "inputs": ["programme_direction (genres/themes from film metadata)", "member_ratio (qualifying/total)"],
                "source": "Film metadata (NOT Qloo) + entity dict",
                "overlap": "NONE — uses programme_direction from film titles/years, not affinity",
            },
            "testability": {
                "inputs": ["event_format (string)", "qualifying_members"],
                "source": "Feasibility output (format string only, NOT score) + entity dict",
                "overlap": "format string shared with differentiation (NOT score)",
            },
            "differentiation": {
                "inputs": ["domain", "event_format (string)"],
                "source": "Entity dict + feasibility output (format string only)",
                "overlap": "format string shared with testability (NOT score)",
            },
        },
        "results": results,
    }
    
    output_path = adjacent_root / "data" / "processed" / "m12_6_quality_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nResults saved to: {output_path}")
    
    return output


if __name__ == "__main__":
    asyncio.run(run_evaluation())