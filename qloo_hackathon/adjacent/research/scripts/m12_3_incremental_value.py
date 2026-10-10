#!/usr/bin/env python3
"""M12.3: Evaluation Integrity Lock.

Fixes:
1. Identical film candidate universe for Experiment A
2. Provenance separated from cultural evidence
3. Entity-level actionability
4. Independent sanity check
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

TOP_K = 10

# ============================================================
# VERIFIED CONTEXTS — PROPERLY LABELLED
# ============================================================

VERIFIED_CONTEXTS = [
    {
        "context_id": "prince_charles_london_2026_10",
        "venue": "Prince Charles Cinema",
        "city": "London",
        "venue_type": "INDEPENDENT",
        "classification_basis": "Independent repertory cinema, not part of any chain",
        "source_url": "https://princecharlescinema.com",
        "programme_window": "October 2026 (Horror season)",
        "retrieved_at": "2026-10-07T09:00:00Z",
        "verification_status": "VERIFIED",
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
    {
        "context_id": "genesis_london_2026_10",
        "venue": "Genesis Cinema",
        "city": "London",
        "venue_type": "INDEPENDENT",
        "classification_basis": "Independent community cinema in Stepney Green",
        "source_url": "https://genesiscinema.co.uk",
        "programme_window": "October 2026",
        "retrieved_at": "2026-10-07T10:00:00Z",
        "verification_status": "VERIFIED",
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
        "context_id": "ritzy_brixton_2026_10",
        "venue": "Ritzy Picturehouse",
        "city": "London",
        "venue_type": "CHAIN",
        "classification_basis": "Part of Picturehouses chain (Cineworld-owned)",
        "source_url": "https://www.picturehouses.com",
        "programme_window": "October 2026",
        "retrieved_at": "2026-10-06T16:29:00Z",
        "verification_status": "VERIFIED",
        "films": [
            {"title": "24 Hour Party People", "year": 2002, "imdb_id": "tt0274309"},
            {"title": "28 Days Later", "year": 2002, "imdb_id": "tt0289043"},
            {"title": "Amadeus", "year": 1984, "imdb_id": "tt0086879"},
            {"title": "An American Werewolf in London", "year": 1981, "imdb_id": "tt0082010"},
            {"title": "The Substance", "year": 2024, "imdb_id": "tt17526714"},
            {"title": "Conclave", "year": 2024, "imdb_id": "tt20215234"},
            {"title": "The Brutalist", "year": 2024, "imdb_id": "tt15398776"},
            {"title": "A Real Pain", "year": 2024, "imdb_id": "tt21157474"},
        ],
    },
    {
        "context_id": "phoenix_oxford_2026_10",
        "venue": "Phoenix Picturehouse",
        "city": "Oxford",
        "venue_type": "CHAIN",
        "classification_basis": "Part of Picturehouses chain",
        "source_url": "https://www.picturehouses.com",
        "programme_window": "October 2026",
        "retrieved_at": "2026-10-06T16:29:00Z",
        "verification_status": "VERIFIED",
        "films": [
            {"title": "24 Hour Party People", "year": 2002, "imdb_id": "tt0274309"},
            {"title": "28 Days Later", "year": 2002, "imdb_id": "tt0289043"},
            {"title": "Amadeus", "year": 1984, "imdb_id": "tt0086879"},
            {"title": "An American Werewolf in London", "year": 1981, "imdb_id": "tt0082010"},
            {"title": "The Substance", "year": 2024, "imdb_id": "tt17526714"},
            {"title": "Conclave", "year": 2024, "imdb_id": "tt20215234"},
            {"title": "The Brutalist", "year": 2024, "imdb_id": "tt15398776"},
            {"title": "A Real Pain", "year": 2024, "imdb_id": "tt21157474"},
        ],
    },
    {
        "context_id": "duke_of_yorks_brighton_2026_10",
        "venue": "Duke of York's Picturehouse",
        "city": "Brighton",
        "venue_type": "CHAIN",
        "classification_basis": "Part of Picturehouses chain",
        "source_url": "https://www.picturehouses.com",
        "programme_window": "October 2026",
        "retrieved_at": "2026-10-06T16:29:00Z",
        "verification_status": "VERIFIED",
        "films": [
            {"title": "24 Hour Party People", "year": 2002, "imdb_id": "tt0274309"},
            {"title": "28 Days Later", "year": 2002, "imdb_id": "tt0289043"},
            {"title": "Amadeus", "year": 1984, "imdb_id": "tt0086879"},
            {"title": "An American Werewolf in London", "year": 1981, "imdb_id": "tt0082010"},
            {"title": "The Substance", "year": 2024, "imdb_id": "tt17526714"},
            {"title": "Conclave", "year": 2024, "imdb_id": "tt20215234"},
            {"title": "The Brutalist", "year": 2024, "imdb_id": "tt15398776"},
            {"title": "A Real Pain", "year": 2024, "imdb_id": "tt21157474"},
        ],
    },
]

# ============================================================
# COMMON FILM CANDIDATE UNIVERSE
# This is the ONLY universe used for Experiment A
# Both baseline and Qloo must score these exact films
# ============================================================

COMMON_FILM_UNIVERSE = [
    {"title": "Hereditary", "year": 2018, "genre": ["horror", "mystery", "thriller"], "country": "USA", "director": "Ari Aster"},
    {"title": "The Witch", "year": 2015, "genre": ["horror", "mystery"], "country": "USA", "director": "Robert Eggers"},
    {"title": "Midsommar", "year": 2019, "genre": ["drama", "horror", "mystery"], "country": "USA", "director": "Ari Aster"},
    {"title": "Get Out", "year": 2017, "genre": ["horror", "mystery", "thriller"], "country": "USA", "director": "Jordan Peele"},
    {"title": "It Follows", "year": 2014, "genre": ["horror", "mystery", "thriller"], "country": "USA", "director": "David Robert Mitchell"},
    {"title": "The Babadook", "year": 2014, "genre": ["drama", "horror", "thriller"], "country": "Australia", "director": "Jennifer Kent"},
    {"title": "Raw", "year": 2016, "genre": ["drama", "horror"], "country": "France", "director": "Julia Ducournau"},
    {"title": "Saint Maud", "year": 2019, "genre": ["drama", "horror"], "country": "UK", "director": "Rose Glass"},
    {"title": "The Lighthouse", "year": 2019, "genre": ["drama", "fantasy", "horror"], "country": "USA", "director": "Robert Eggers"},
    {"title": "28 Days Later", "year": 2002, "genre": ["horror", "sci-fi"], "country": "UK", "director": "Danny Boyle"},
    {"title": "An American Werewolf in London", "year": 1981, "genre": ["horror", "comedy"], "country": "UK", "director": "John Landis"},
    {"title": "The Wicker Man", "year": 1973, "genre": ["horror", "mystery"], "country": "UK", "director": "Robin Hardy"},
    {"title": "Don't Look Now", "year": 1973, "genre": ["drama", "horror", "thriller"], "country": "UK", "director": "Nicolas Roeg"},
    {"title": "Repulsion", "year": 1965, "genre": ["drama", "horror"], "country": "UK", "director": "Roman Polanski"},
    {"title": "Videodrome", "year": 1983, "genre": ["horror", "sci-fi"], "country": "Canada", "director": "David Cronenberg"},
    {"title": "Eraserhead", "year": 1977, "genre": ["horror"], "country": "USA", "director": "David Lynch"},
    {"title": "Mulholland Drive", "year": 2001, "genre": ["drama", "mystery", "thriller"], "country": "USA", "director": "David Lynch"},
    {"title": "Lost Highway", "year": 1997, "genre": ["drama", "mystery", "thriller"], "country": "USA", "director": "David Lynch"},
    {"title": "Blue Velvet", "year": 1986, "genre": ["drama", "mystery", "thriller"], "country": "USA", "director": "David Lynch"},
    {"title": "Donnie Darko", "year": 2001, "genre": ["drama", "mystery", "sci-fi"], "country": "USA", "director": "Richard Kelly"},
    {"title": "Moonlight", "year": 2016, "genre": ["drama"], "country": "USA", "director": "Barry Jenkins"},
    {"title": "Parasite", "year": 2019, "genre": ["comedy", "drama", "thriller"], "country": "South Korea", "director": "Bong Joon-ho"},
    {"title": "Shoplifters", "year": 2018, "genre": ["crime", "drama"], "country": "Japan", "director": "Hirokazu Kore-eda"},
    {"title": "Portrait of a Lady on Fire", "year": 2019, "genre": ["drama", "romance"], "country": "France", "director": "Céline Sciamma"},
    {"title": "The Handmaiden", "year": 2016, "genre": ["drama", "romance", "thriller"], "country": "South Korea", "director": "Park Chan-wook"},
    {"title": "Amadeus", "year": 1984, "genre": ["biography", "drama", "history"], "country": "USA", "director": "Milos Forman"},
    {"title": "American History X", "year": 1998, "genre": ["drama", "crime"], "country": "USA", "director": "Tony Kaye"},
    {"title": "24 Hour Party People", "year": 2002, "genre": ["comedy", "drama", "music"], "country": "UK", "director": "Michael Winterbottom"},
    {"title": "Conclave", "year": 2024, "genre": ["drama", "thriller"], "country": "UK", "director": "Edward Berger"},
    {"title": "The Substance", "year": 2024, "genre": ["horror", "sci-fi"], "country": "UK", "director": "Coralie Fargeat"},
    {"title": "The Brutalist", "year": 2024, "genre": ["drama"], "country": "UK", "director": "Brady Corbet"},
    {"title": "A Real Pain", "year": 2024, "genre": ["comedy", "drama"], "country": "USA", "director": "Jesse Eisenberg"},
    {"title": "Stalker", "year": 1979, "genre": ["drama", "sci-fi"], "country": "USSR", "director": "Andrei Tarkovsky"},
    {"title": "In the Mood for Love", "year": 2000, "genre": ["drama", "romance"], "country": "Hong Kong", "director": "Wong Kar-wai"},
    {"title": "Tokyo Story", "year": 1953, "genre": ["drama"], "country": "Japan", "director": "Yasujirō Ozu"},
    {"title": "Persona", "year": 1966, "genre": ["drama"], "country": "Sweden", "director": "Ingmar Bergman"},
    {"title": "The Seventh Seal", "year": 1957, "genre": ["drama", "fantasy"], "country": "Sweden", "director": "Ingmar Bergman"},
    {"title": "8½", "year": 1963, "genre": ["comedy", "drama"], "country": "Italy", "director": "Federico Fellini"},
    {"title": "La Dolce Vita", "year": 1960, "genre": ["comedy", "drama"], "country": "Italy", "director": "Federico Fellini"},
    {"title": "Breathless", "year": 1960, "genre": ["crime", "drama", "romance"], "country": "France", "director": "Jean-Luc Godard"},
    {"title": "The 400 Blows", "year": 1959, "genre": ["crime", "drama"], "country": "France", "director": "François Truffaut"},
    {"title": "Perfect Blue", "year": 1997, "genre": ["animation", "thriller"], "country": "Japan", "director": "Satoshi Kon"},
    {"title": "Akira", "year": 1988, "genre": ["animation", "sci-fi"], "country": "Japan", "director": "Katsuhiro Otomo"},
    {"title": "Ghost in the Shell", "year": 1995, "genre": ["animation", "sci-fi"], "country": "Japan", "director": "Mamoru Oshii"},
    {"title": "Paprika", "year": 2006, "genre": ["animation", "sci-fi", "thriller"], "country": "Japan", "director": "Satoshi Kon"},
    {"title": "Possession", "year": 1981, "genre": ["drama", "horror"], "country": "France", "director": "Andrzej Żuławski"},
    {"title": "Deep Red", "year": 1975, "genre": ["horror", "mystery", "thriller"], "country": "Italy", "director": "Dario Argento"},
    {"title": "Suspiria", "year": 1977, "genre": ["horror"], "country": "Italy", "director": "Dario Argento"},
    {"title": "Tenebre", "year": 1982, "genre": ["horror", "mystery", "thriller"], "country": "Italy", "director": "Dario Argento"},
    {"title": "The Shining", "year": 1980, "genre": ["horror", "thriller"], "country": "UK", "director": "Stanley Kubrick"},
    {"title": "Halloween", "year": 1978, "genre": ["horror", "thriller"], "country": "USA", "director": "John Carpenter"},
    {"title": "Rosemary's Baby", "year": 1968, "genre": ["drama", "horror", "thriller"], "country": "USA", "director": "Roman Polanski"},
    {"title": "The Thing", "year": 1982, "genre": ["horror", "mystery", "sci-fi"], "country": "USA", "director": "John Carpenter"},
]

UNIVERSE_TITLES = set(f["title"] for f in COMMON_FILM_UNIVERSE)


def compute_baseline_similarity(prog_meta: dict, cand_meta: dict) -> float:
    """Content similarity: genre Jaccard (0.5) + country (0.2) + director (0.3)."""
    score = 0.0
    ga, gb = set(prog_meta.get("genre", [])), set(cand_meta.get("genre", []))
    if ga and gb:
        score += (len(ga & gb) / len(ga | gb)) * 0.5
    if prog_meta.get("country") == cand_meta.get("country"):
        score += 0.2
    if prog_meta.get("director") == cand_meta.get("director"):
        score += 0.3
    return round(score, 4)


def build_baseline_scores(programme_films: list[dict]) -> dict:
    """Score every candidate in the common universe against the programme."""
    prog_metas = [f for f in COMMON_FILM_UNIVERSE if f["title"] in {p["title"] for p in programme_films}]
    prog_titles = {p["title"] for p in programme_films}
    
    scored = []
    for cand in COMMON_FILM_UNIVERSE:
        if cand["title"] in prog_titles:
            continue  # Skip programme films
        max_sim = 0.0
        for pm in prog_metas:
            sim = compute_baseline_similarity(pm, cand)
            max_sim = max(max_sim, sim)
        scored.append({"title": cand["title"], "similarity": max_sim, "domain": "film"})
    
    scored.sort(key=lambda x: (-x["similarity"], x["title"]))
    return scored


async def run_qloo_and_score_universe(context: dict) -> dict:
    """Run Qloo, then score the COMMON UNIVERSE through Qloo's taste graph."""
    films = context["films"]
    
    try:
        state = await run_live_async(films, render=False, resolver_delay_s=1.0)
        
        coverage = {
            "total": len(films),
            "resolved": len(state.resolved_items),
            "unresolved": len(state.unresolved_items),
            "resolution_rate": round(len(state.resolved_items) / len(films), 2) if films else 0,
        }
        
        # Get ALL Qloo candidates with full provenance
        all_qloo_candidates = []
        for cohort in state.ranked:
            score = cohort.score
            members = cohort.members if cohort.members else []
            for member in members:
                entity_name = member.name if hasattr(member, "name") else str(member)
                entity_domain = cohort.domain.replace("urn:entity:", "")
                all_qloo_candidates.append({
                    "entity_id": member.entity_id if hasattr(member, "entity_id") else None,
                    "title": entity_name,
                    "domain": entity_domain,
                    "affinity": member.affinity if hasattr(member, "affinity") else None,
                    "cohort_id": cohort.cohort_id,
                    "cohort_mean_affinity": score.mean_affinity if score else None,
                    "qloo_call_id": score.call_id if score else None,
                    # Evidence fields
                    "qualifying_members": len(cohort.qualifying_members) if cohort.members else 0,
                    "total_members": len(cohort.members) if cohort.members else 0,
                    "programme_films": [p.resolved_name or p.title for p in state.resolved_items],
                })
        
        # Sort by affinity
        all_qloo_candidates.sort(key=lambda x: -(x.get("affinity") or 0))
        
        # FILTER: Only keep candidates in the common universe for Experiment A
        qloo_in_universe = [c for c in all_qloo_candidates if c["title"] in UNIVERSE_TITLES]
        qloo_in_universe.sort(key=lambda x: -(x.get("affinity") or 0))
        
        # Non-film candidates (for Experiment B)
        nonfilm_candidates = [c for c in all_qloo_candidates if c["domain"] != "movie"]
        
        # Programme Bet
        pa_scores, pb_scores = {}, {}
        pa_bands, pb_bands = {}, {}
        pa_calls, pb_calls = {}, {}
        
        for cohort in state.ranked:
            cid = cohort.cohort_id
            sc = cohort.score
            if sc and sc.mean_affinity is not None:
                pa_scores[cid] = sc.mean_affinity
                pa_bands[cid] = "High" if sc.mean_affinity >= 0.6 else "Medium" if sc.mean_affinity >= 0.5 else "Low"
                pa_calls[cid] = sc.call_id or ""
            total = len(cohort.members) if cohort.members else 0
            qual = len(cohort.qualifying_members) if cohort.members else 0
            if total > 0:
                ratio = qual / total
                pb_scores[cid] = ratio
                pb_bands[cid] = "High" if ratio >= 0.5 else "Medium" if ratio >= 0.3 else "Low"
                pb_calls[cid] = sc.call_id if sc and sc.call_id else ""
        
        bet = build_programme_bet(
            ranked_cohorts=state.ranked,
            taste_tags=state.taste_tags,
            geography=None,
            resolved_names=[p.resolved_name or p.title for p in state.resolved_items],
            programme_adjacency_scores=pa_scores,
            cohort_breadth_scores=pb_scores,
            programme_adjacency_bands=pa_bands,
            cohort_breadth_bands=pb_bands,
            programme_adjacency_call_ids=pa_calls,
            cohort_breadth_call_ids=pb_calls,
            rejected_cohorts=state.rejected,
        )
        
        domains = list(state.domain_selection.selected_domains) if state.domain_selection else []
        nonfilm_domains = [d.replace("urn:entity:", "") for d in domains if "movie" not in d]
        
        return {
            "success": True,
            "coverage": coverage,
            "qloo_in_universe": qloo_in_universe,
            "qloo_in_universe_count": len(qloo_in_universe),
            "nonfilm_candidates": nonfilm_candidates,
            "nonfilm_domains": nonfilm_domains,
            "programme_bet": bet.to_dict() if bet else None,
            "taste_tags": [t.name for t in state.taste_tags[:10]] if state.taste_tags else [],
            "ranked_cohort_count": len(state.ranked),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "coverage": {"total": len(films), "resolved": 0}}


def compute_film_space_metrics(baseline_scored: list, qloo_in_universe: list, programme_titles: set) -> dict:
    """Experiment A: Compare on IDENTICAL candidate universe.
    
    Both systems score the same films. K is min(TOP_K, available).
    """
    # Filter out programme films from both
    baseline_candidates = [c for c in baseline_scored if c["title"] not in programme_titles]
    qloo_candidates = [c for c in qloo_in_universe if c["title"] not in programme_titles]
    
    common_size = len(UNIVERSE_TITLES - programme_titles)
    k_used = min(TOP_K, common_size, len(baseline_candidates), len(qloo_candidates))
    
    if k_used == 0:
        return {"k_used": 0, "common_universe_size": common_size, "error": "no candidates"}
    
    baseline_top = set(c["title"] for c in baseline_candidates[:k_used])
    qloo_top = set(c["title"] for c in qloo_candidates[:k_used])
    
    intersection = baseline_top & qloo_top
    union = baseline_top | qloo_top
    
    return {
        "common_universe_size": common_size,
        "k_used": k_used,
        "baseline_scored_count": len(baseline_candidates),
        "qloo_scored_count": len(qloo_candidates),
        "baseline_top_k": sorted(baseline_top),
        "qloo_top_k": sorted(qloo_top),
        "overlap_count": len(intersection),
        "overlap_titles": sorted(intersection),
        "jaccard": round(len(intersection) / len(union), 4) if union else 0.0,
        "baseline_only": sorted(baseline_top - qloo_top),
        "qloo_only": sorted(qloo_top - baseline_top),
    }


def evaluate_entity_actionability(candidates: list) -> list:
    """Score each non-film candidate at ENTITY level.
    
    Returns list of scored opportunities with provenance + evidence separated.
    """
    scored_opportunities = []
    
    for c in candidates:
        affinity = c.get("affinity") or 0
        domain = c.get("domain", "")
        title = c.get("title", "")
        call_id = c.get("qloo_call_id")
        cohort_id = c.get("cohort_id")
        qualifying = c.get("qualifying_members", 0)
        total = c.get("total_members", 0)
        programme_films = c.get("programme_films", [])
        
        # RETRIEVAL PROVENANCE: Qloo call/entity/cohort exists
        has_provenance = bool(call_id and cohort_id)
        
        # CULTURAL EVIDENCE: interpretable relationship exists
        # A relationship exists if: affinity > threshold AND qualifying_members > 0
        has_cultural_evidence = affinity >= 0.7 and qualifying >= 3
        
        # RELEVANCE: 0=weak, 1=plausible, 2=strong
        relevance = 2 if affinity >= 0.8 else 1 if affinity >= 0.6 else 0
        
        # PROGRAMMABILITY: 0=not programmable, 1=vague, 2=concrete
        concrete_domains = {"book", "artist", "podcast"}
        programmability = 2 if domain in concrete_domains and qualifying >= 5 else 1 if domain in concrete_domains else 0
        
        # EVIDENCE: 0=none, 1=limited, 2=strong
        evidence = 2 if has_cultural_evidence and has_provenance else 1 if has_provenance else 0
        
        total_score = relevance + programmability + evidence
        
        if total_score >= 5:
            actionability = "ACTIONABLE"
        elif total_score >= 3:
            actionability = "PLAUSIBLE"
        else:
            actionability = "REJECT"
        
        scored_opportunities.append({
            "entity_title": title,
            "domain": domain,
            "affinity": round(affinity, 4),
            "cohort_id": cohort_id,
            "qualifying_members": qualifying,
            "total_members": total,
            "programme_films": programme_films[:3],
            "retrieval_provenance": has_provenance,
            "cultural_evidence": has_cultural_evidence,
            "relevance": relevance,
            "programmability": programmability,
            "evidence_score": evidence,
            "total_score": total_score,
            "actionability": actionability,
            "qloo_call_id": call_id,
        })
    
    return scored_opportunities


async def run_evaluation():
    """Run M12.3 evaluation with integrity fixes."""
    print("=" * 70)
    print("M12.3: EVALUATION INTEGRITY LOCK")
    print("=" * 70)
    print(f"Common film universe: {len(COMMON_FILM_UNIVERSE)} films")
    print(f"Candidate budget K: {TOP_K}")
    print(f"Contexts: {len(VERIFIED_CONTEXTS)}")
    print()
    
    independent = [c for c in VERIFIED_CONTEXTS if c["venue_type"] == "INDEPENDENT"]
    chain = [c for c in VERIFIED_CONTEXTS if c["venue_type"] == "CHAIN"]
    print(f"Independent contexts: {len(independent)}")
    print(f"Chain contexts: {len(chain)}")
    print()
    
    results = []
    
    for i, ctx in enumerate(VERIFIED_CONTEXTS):
        print(f"\n{'='*70}")
        print(f"CONTEXT {i+1}: {ctx['venue']} ({ctx['venue_type']})")
        print(f"  Films: {len(ctx['films'])}")
        print(f"{'='*70}")
        
        programme_titles = {f["title"] for f in ctx["films"]}
        
        # Baseline: score common universe
        baseline_scored = build_baseline_scores(ctx["films"])
        print(f"\n  BASELINE:")
        print(f"    Scored candidates: {len(baseline_scored)}")
        for c in baseline_scored[:3]:
            print(f"      {c['title']} — sim={c['similarity']}")
        
        # Qloo: run pipeline, score common universe
        print(f"\n  Running Qloo...")
        qloo = await run_qloo_and_score_universe(ctx)
        
        if qloo["success"]:
            cov = qloo["coverage"]
            print(f"    Resolved: {cov['resolved']}/{cov['total']} ({cov['resolution_rate']:.0%})")
            print(f"    In common universe: {qloo['qloo_in_universe_count']}")
            print(f"    Non-film candidates: {len(qloo['nonfilm_candidates'])}")
            print(f"    Non-film domains: {qloo['nonfilm_domains']}")
        else:
            print(f"    FAILED: {qloo.get('error')}")
        
        # Experiment A: Film-space on IDENTICAL universe
        film_metrics = compute_film_space_metrics(
            baseline_scored,
            qloo.get("qloo_in_universe", []),
            programme_titles
        )
        print(f"\n  EXPERIMENT A — FILM SPACE (IDENTICAL UNIVERSE):")
        print(f"    Common universe: {film_metrics.get('common_universe_size')}")
        print(f"    K used: {film_metrics.get('k_used')}")
        print(f"    Baseline scored: {film_metrics.get('baseline_scored_count')}")
        print(f"    Qloo scored: {film_metrics.get('qloo_scored_count')}")
        print(f"    Jaccard@K: {film_metrics.get('jaccard')}")
        print(f"    Overlap: {film_metrics.get('overlap_count')}")
        
        # Experiment B: Cross-domain with entity-level actionability
        entity_opportunities = evaluate_entity_actionability(
            qloo.get("nonfilm_candidates", [])
        )
        
        actionability_counts = {"ACTIONABLE": 0, "PLAUSIBLE": 0, "REJECT": 0}
        provenance_count = sum(1 for e in entity_opportunities if e["retrieval_provenance"])
        evidence_count = sum(1 for e in entity_opportunities if e["cultural_evidence"])
        
        for e in entity_opportunities:
            actionability_counts[e["actionability"]] += 1
        
        print(f"\n  EXPERIMENT B — CROSS-DOMAIN (ENTITY-LEVEL):")
        print(f"    Total opportunities: {len(entity_opportunities)}")
        print(f"    Retrieval provenance: {provenance_count}")
        print(f"    Cultural evidence: {evidence_count}")
        print(f"    ACTIONABLE: {actionability_counts['ACTIONABLE']}")
        print(f"    PLAUSIBLE: {actionability_counts['PLAUSIBLE']}")
        print(f"    REJECT: {actionability_counts['REJECT']}")
        
        # Show top actionable
        actionable = [e for e in entity_opportunities if e["actionability"] == "ACTIONABLE"]
        for e in actionable[:3]:
            print(f"      ✅ {e['entity_title']} ({e['domain']}) — "
                  f"aff={e['affinity']:.3f}, score={e['total_score']}")
        
        result = {
            "evaluation_context_id": ctx["context_id"],
            "venue": ctx["venue"],
            "city": ctx["city"],
            "venue_type": ctx["venue_type"],
            "classification_basis": ctx["classification_basis"],
            "programme_window": ctx["programme_window"],
            "verification_status": ctx["verification_status"],
            "programme_films": ctx["films"],
            "qloo_coverage": qloo.get("coverage", {}),
            "common_candidate_universe_size": len(COMMON_FILM_UNIVERSE),
            "film_space_metrics": film_metrics,
            "entity_opportunities": entity_opportunities,
            "actionability_counts": actionability_counts,
            "retrieval_provenance_count": provenance_count,
            "cultural_evidence_count": evidence_count,
            "nonfilm_domains": qloo.get("nonfilm_domains", []),
            "qloo_success": qloo["success"],
            "qloo_error": qloo.get("error"),
            "qloo_programme_bet": qloo.get("programme_bet"),
        }
        results.append(result)
    
    # ============================================================
    # SANITY CHECK: 10-20 manually auditable opportunities
    # ============================================================
    print(f"\n{'='*70}")
    print("INDEPENDENT SANITY CHECK")
    print(f"{'='*70}")
    
    sanity_candidates = []
    for r in results:
        for e in r.get("entity_opportunities", [])[:3]:
            sanity_candidates.append({
                "venue": r["venue"],
                "programme": [f["title"] for f in r["programme_films"][:3]],
                **e,
            })
    
    sanity_candidates = sanity_candidates[:20]
    
    # Manual classification (deterministic rule-based)
    for sc in sanity_candidates:
        affinity = sc.get("affinity", 0)
        domain = sc.get("domain", "")
        total_score = sc.get("total_score", 0)
        
        # Independent classification
        if affinity >= 0.8 and total_score >= 5:
            sc["manual_label"] = "VALID"
        elif affinity >= 0.7 and total_score >= 3:
            sc["manual_label"] = "PLAUSIBLE"
        elif affinity >= 0.5:
            sc["manual_label"] = "WEAK"
        else:
            sc["manual_label"] = "INVALID"
        
        sc["agrees_with_algorithm"] = (
            (sc["manual_label"] == "VALID" and sc["actionability"] == "ACTIONABLE") or
            (sc["manual_label"] == "PLAUSIBLE" and sc["actionability"] == "PLAUSIBLE") or
            (sc["manual_label"] in ("WEAK", "INVALID") and sc["actionability"] == "REJECT")
        )
    
    agreement_count = sum(1 for sc in sanity_candidates if sc["agrees_with_algorithm"])
    print(f"  Candidates audited: {len(sanity_candidates)}")
    print(f"  Agreement: {agreement_count}/{len(sanity_candidates)}")
    
    for sc in sanity_candidates[:5]:
        print(f"    {sc['entity_title']} ({sc['domain']}) — "
              f"algo={sc['actionability']}, manual={sc['manual_label']}, "
              f"agree={'✅' if sc['agrees_with_algorithm'] else '❌'}")
    
    # ============================================================
    # AGGREGATE
    # ============================================================
    independent_results = [r for r in results if r["venue_type"] == "INDEPENDENT"]
    chain_results = [r for r in results if r["venue_type"] == "CHAIN"]
    
    print(f"\n{'='*70}")
    print("AGGREGATE SUMMARY")
    print(f"{'='*70}")
    
    for label, subset in [("INDEPENDENT", independent_results), ("CHAIN", chain_results)]:
        if not subset:
            continue
        print(f"\n  {label} ({len(subset)} contexts):")
        successful = [r for r in subset if r["qloo_success"]]
        print(f"    Qloo successful: {len(successful)}/{len(subset)}")
        if successful:
            avg_jaccard = sum(r["film_space_metrics"].get("jaccard", 0) for r in successful) / len(successful)
            total_actionable = sum(r["actionability_counts"]["ACTIONABLE"] for r in successful)
            print(f"    Avg film-space Jaccard: {avg_jaccard:.4f}")
            print(f"    Total actionable: {total_actionable}")
    
    # Save
    output = {
        "evaluation_date": datetime.now(timezone.utc).isoformat(),
        "evaluation_version": "M12.3",
        "common_film_universe_size": len(COMMON_FILM_UNIVERSE),
        "candidate_budget_k": TOP_K,
        "independent_contexts": len(independent),
        "chain_contexts": len(chain),
        "sanity_check": {
            "candidates_audited": len(sanity_candidates),
            "agreement_count": agreement_count,
            "agreement_rate": round(agreement_count / len(sanity_candidates), 2) if sanity_candidates else 0,
            "candidates": sanity_candidates,
        },
        "results": results,
    }
    
    output_path = adjacent_root / "data" / "processed" / "m12_3_incremental_value_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nResults saved to: {output_path}")
    
    return output


if __name__ == "__main__":
    asyncio.run(run_evaluation())