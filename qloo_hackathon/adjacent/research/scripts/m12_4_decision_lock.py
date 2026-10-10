#!/usr/bin/env python3
"""M12.4: Actionability & Decision Lock.

Fixes:
1. Rule-based consistency check (not independent validation)
2. Three separated concepts: provenance, cultural evidence, programming value
3. Rebuilt actionability (total=10, 5 components)
4. Hard programmability rules
5. Top 5 → ONE Programme Bet
6. Deterministic opportunity ranking
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
# PRIMARY CONTEXTS: INDEPENDENT/COMMUNITY ONLY
# ============================================================

PRIMARY_CONTEXTS = [
    {
        "context_id": "prince_charles_london_2026_10",
        "venue": "Prince Charles Cinema",
        "city": "London",
        "venue_type": "INDEPENDENT",
        "classification_basis": "Independent repertory cinema, not part of any chain",
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
    {
        "context_id": "genesis_london_2026_10",
        "venue": "Genesis Cinema",
        "city": "London",
        "venue_type": "INDEPENDENT",
        "classification_basis": "Independent community cinema in Stepney Green",
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
]

SECONDARY_CONTEXTS = [
    {
        "context_id": "ritzy_brixton_2026_10",
        "venue": "Ritzy Picturehouse",
        "city": "London",
        "venue_type": "CHAIN",
        "classification_basis": "Part of Picturehouses chain (Cineworld-owned)",
        "source_url": "https://www.picturehouses.com",
        "programme_window": "October 2026",
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
# HARD PROGRAMMABILITY RULES
# ============================================================

DOMAIN_PROGRAMMABILITY = {
    "artist": {
        "formats": [
            "screening + live performance",
            "soundtrack listening event",
            "artist discussion panel",
            "themed screening season with artist introduction",
        ],
        "requires": "specific artist name + concrete event format",
        "reject_if": "vague 'partner with artist' or 'explore this music'",
    },
    "book": {
        "formats": [
            "screening + author Q&A",
            "book club screening event",
            "reading + film pairing",
            "literary discussion with film clips",
        ],
        "requires": "specific book title + concrete event format",
        "reject_if": "vague 'explore literary connections'",
    },
    "tv_show": {
        "formats": [
            "themed screening season",
            "pilot episode preview + discussion",
            "TV-to-film comparison event",
        ],
        "requires": "specific show title + concrete pairing rationale",
        "reject_if": "vague 'screen related TV content'",
    },
    "podcast": {
        "formats": [
            "live recording + film screening",
            "podcast host discussion + film",
            "themed podcast listening event",
        ],
        "requires": "specific podcast name + concrete event format",
        "reject_if": "vague 'podcast partnership'",
    },
    "brand": {
        "formats": [
            "co-branded screening event",
            "brand-sponsored themed season",
            "cultural partnership event",
        ],
        "requires": "specific brand + legitimate cinema-compatible event",
        "reject_if": "vague 'brand partnership' or 'sponsorship'",
    },
}


def score_entity_opportunity(entity: dict, programme_films: list[str]) -> dict:
    """Score a single non-film entity opportunity.
    
    Five components, total = 10.
    Deterministic, no LLM.
    """
    affinity = entity.get("affinity") or 0
    domain = entity.get("domain", "")
    title = entity.get("title", "")
    qualifying = entity.get("qualifying_members", 0)
    total_members = entity.get("total_members", 0)
    call_id = entity.get("qloo_call_id")
    cohort_id = entity.get("cohort_id")
    
    # A. RETRIEVAL PROVENANCE (not scored, binary flag)
    has_provenance = bool(call_id and cohort_id)
    
    # B. CULTURAL EVIDENCE (not scored, binary flag)
    has_cultural_evidence = affinity >= 0.7 and qualifying >= 3
    
    # C. RELEVANCE (0-2)
    relevance = 2 if affinity >= 0.85 else 1 if affinity >= 0.7 else 0
    
    # D. EVIDENCE STRENGTH (0-2)
    evidence_strength = 2 if affinity >= 0.85 and qualifying >= 10 else 1 if affinity >= 0.7 and qualifying >= 3 else 0
    
    # E. PROGRAMMABILITY (0-2)
    domain_rules = DOMAIN_PROGRAMMABILITY.get(domain, {})
    formats = domain_rules.get("formats", [])
    if domain in DOMAIN_PROGRAMMABILITY and formats:
        if qualifying >= 5 and affinity >= 0.7:
            programmability = 2
        elif qualifying >= 3:
            programmability = 1
        else:
            programmability = 0
    else:
        programmability = 0
    
    # F. DISTINCTIVENESS (0-2)
    # Non-film domains are inherently distinct from film-only baseline
    distinctiveness = 2 if domain not in ("movie",) and affinity >= 0.7 else 1 if domain not in ("movie",) else 0
    
    # G. TESTABILITY (0-2)
    # Can this form a concrete experiment?
    if domain in DOMAIN_PROGRAMMABILITY and programmability >= 2:
        testability = 2
    elif domain in DOMAIN_PROGRAMMABILITY and programmability >= 1:
        testability = 1
    else:
        testability = 0
    
    total = relevance + evidence_strength + programmability + distinctiveness + testability
    
    if total >= 8:
        classification = "STRONG"
    elif total >= 6:
        classification = "PLAUSIBLE"
    elif total >= 4:
        classification = "WEAK"
    else:
        classification = "REJECT"
    
    # Generate concrete experiment if programmable
    experiment = None
    if programmability >= 2 and domain in DOMAIN_PROGRAMMABILITY:
        formats = DOMAIN_PROGRAMMABILITY[domain]["formats"]
        experiment = formats[0]  # Pick the first concrete format
    
    return {
        "entity_title": title,
        "domain": domain,
        "affinity": round(affinity, 4),
        "qualifying_members": qualifying,
        "total_members": total_members,
        "cohort_id": cohort_id,
        "qloo_call_id": call_id,
        "programme_films": programme_films[:3],
        # Three separated concepts
        "retrieval_provenance": has_provenance,
        "cultural_evidence": has_cultural_evidence,
        # Five scored components
        "relevance": relevance,
        "evidence_strength": evidence_strength,
        "programmability": programmability,
        "distinctiveness": distinctiveness,
        "testability": testability,
        "total_score": total,
        "classification": classification,
        "experiment": experiment,
    }


def deduplicate_opportunities(opportunities: list) -> list:
    """Remove duplicate entities and duplicate conceptual opportunities."""
    seen_titles = set()
    seen_concepts = set()  # (domain, first_word_of_title)
    unique = []
    
    for opp in opportunities:
        title = opp["entity_title"]
        domain = opp["domain"]
        concept_key = (domain, title.split()[0] if title else "")
        
        if title in seen_titles:
            continue
        if concept_key in seen_concepts:
            continue
        
        seen_titles.add(title)
        seen_concepts.add(concept_key)
        unique.append(opp)
    
    return unique


def rank_opportunities(opportunities: list) -> list:
    """Rank opportunities by deterministic score.
    
    opportunity_score = 0.30 * affinity_norm + 0.20 * evidence_norm + 
                        0.20 * programmability_norm + 0.15 * distinctiveness_norm + 
                        0.15 * testability_norm
    """
    for opp in opportunities:
        affinity_norm = opp["affinity"]  # Already 0-1
        evidence_norm = opp["evidence_strength"] / 2.0
        program_norm = opp["programmability"] / 2.0
        distinct_norm = opp["distinctiveness"] / 2.0
        test_norm = opp["testability"] / 2.0
        
        opp["opportunity_score"] = round(
            0.30 * affinity_norm +
            0.20 * evidence_norm +
            0.20 * program_norm +
            0.15 * distinct_norm +
            0.15 * test_norm,
            4
        )
    
    return sorted(opportunities, key=lambda x: (-x["opportunity_score"], x["entity_title"]))


def select_programme_bet(top_opportunities: list, programme_bet_data: dict) -> dict:
    """Select ONE primary Programme Bet from top opportunities."""
    if not top_opportunities:
        return None
    
    primary = top_opportunities[0]
    
    return {
        "primary_entity": primary["entity_title"],
        "primary_domain": primary["domain"],
        "affinity": primary["affinity"],
        "opportunity_score": primary["opportunity_score"],
        "classification": primary["classification"],
        "experiment": primary["experiment"],
        "why": f"This {primary['domain']} has the highest opportunity score ({primary['opportunity_score']:.3f}) "
               f"with affinity {primary['affinity']:.3f} and {primary['qualifying_members']} qualifying members.",
        "evidence": {
            "retrieval_provenance": primary["retrieval_provenance"],
            "cultural_evidence": primary["cultural_evidence"],
            "qloo_call_id": primary["qloo_call_id"],
            "cohort_id": primary["cohort_id"],
        },
        "falsification": f"This hypothesis is rejected if a subsequent analysis of a similar programme "
                         f"does not produce a {primary['domain']} cohort with affinity ≥ 0.7 in the top-3 ranked opportunities.",
        "alternatives": [
            {
                "entity": t["entity_title"],
                "domain": t["domain"],
                "score": t["opportunity_score"],
                "reason_not_selected": f"Lower opportunity score ({t['opportunity_score']:.3f} vs {primary['opportunity_score']:.3f})",
            }
            for t in top_opportunities[1:5]
        ],
    }


async def run_qloo_evaluation(context: dict) -> dict:
    """Run Qloo pipeline and extract candidates with full provenance."""
    films = context["films"]
    
    try:
        state = await run_live_async(films, render=False, resolver_delay_s=1.0)
        
        coverage = {
            "total": len(films),
            "resolved": len(state.resolved_items),
            "resolution_rate": round(len(state.resolved_items) / len(films), 2),
        }
        
        programme_names = [p.resolved_name or p.title for p in state.resolved_items]
        
        # Extract ALL non-film candidates with provenance
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
        
        # Sort by affinity
        all_nonfilm.sort(key=lambda x: -(x.get("affinity") or 0))
        
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
            resolved_names=programme_names,
            programme_adjacency_scores=pa_scores,
            cohort_breadth_scores=pb_scores,
            programme_adjacency_bands=pa_bands,
            cohort_breadth_bands=pb_bands,
            programme_adjacency_call_ids=pa_calls,
            cohort_breadth_call_ids=pb_calls,
            rejected_cohorts=state.rejected,
        )
        
        nonfilm_domains = list(set(c["domain"] for c in all_nonfilm))
        
        return {
            "success": True,
            "coverage": coverage,
            "programme_names": programme_names,
            "raw_nonfilm_candidates": all_nonfilm,
            "raw_count": len(all_nonfilm),
            "nonfilm_domains": nonfilm_domains,
            "programme_bet_raw": bet.to_dict() if bet else None,
            "taste_tags": [t.name for t in state.taste_tags[:10]] if state.taste_tags else [],
        }
    except Exception as e:
        return {"success": False, "error": str(e), "raw_nonfilm_candidates": [], "raw_count": 0}


async def run_evaluation():
    """Run M12.4 evaluation with decision lock."""
    print("=" * 70)
    print("M12.4: ACTIONABILITY & DECISION LOCK")
    print("=" * 70)
    print(f"Primary contexts (independent): {len(PRIMARY_CONTEXTS)}")
    print(f"Secondary contexts (chain): {len(SECONDARY_CONTEXTS)}")
    print()
    
    all_contexts = PRIMARY_CONTEXTS + SECONDARY_CONTEXTS
    results = []
    
    for i, ctx in enumerate(all_contexts):
        is_primary = ctx in PRIMARY_CONTEXTS
        label = "PRIMARY" if is_primary else "SECONDARY"
        
        print(f"\n{'='*70}")
        print(f"CONTEXT {i+1} [{label}]: {ctx['venue']} ({ctx['venue_type']})")
        print(f"  Films: {len(ctx['films'])}")
        print(f"{'='*70}")
        
        # Run Qloo
        print(f"  Running Qloo...")
        qloo = await run_qloo_evaluation(ctx)
        
        if not qloo["success"]:
            print(f"  FAILED: {qloo.get('error')}")
            results.append({
                "context_id": ctx["context_id"],
                "venue": ctx["venue"],
                "venue_type": ctx["venue_type"],
                "is_primary": is_primary,
                "qloo_success": False,
                "qloo_error": qloo.get("error"),
            })
            continue
        
        cov = qloo["coverage"]
        print(f"  Resolved: {cov['resolved']}/{cov['total']} ({cov['resolution_rate']:.0%})")
        print(f"  Raw non-film candidates: {qloo['raw_count']}")
        print(f"  Non-film domains: {qloo['nonfilm_domains']}")
        
        # Step 1: Score all raw candidates
        scored = []
        for c in qloo["raw_nonfilm_candidates"]:
            scored.append(score_entity_opportunity(c, qloo["programme_names"]))
        
        # Step 2: Deduplicate
        deduped = deduplicate_opportunities(scored)
        print(f"  After deduplication: {len(deduped)}")
        
        # Step 3: Filter by cultural evidence
        with_evidence = [s for s in deduped if s["cultural_evidence"]]
        print(f"  With cultural evidence: {len(with_evidence)}")
        
        # Step 4: Filter by programmability
        programmable = [s for s in with_evidence if s["programmability"] >= 1]
        print(f"  Programmable: {len(programmable)}")
        
        # Step 5: Rank
        ranked = rank_opportunities(programmable)
        
        # Step 6: Classify
        strong = [r for r in ranked if r["classification"] == "STRONG"]
        plausible = [r for r in ranked if r["classification"] == "PLAUSIBLE"]
        weak = [r for r in ranked if r["classification"] == "WEAK"]
        rejected = [r for r in ranked if r["classification"] == "REJECT"]
        
        print(f"\n  Classification:")
        print(f"    STRONG: {len(strong)}")
        print(f"    PLAUSIBLE: {len(plausible)}")
        print(f"    WEAK: {len(weak)}")
        print(f"    REJECT: {len(rejected)}")
        
        # Step 7: Top 5
        top_5 = ranked[:5]
        print(f"\n  TOP 5:")
        for j, opp in enumerate(top_5):
            print(f"    {j+1}. {opp['entity_title']} ({opp['domain']}) — "
                  f"score={opp['opportunity_score']:.3f}, "
                  f"aff={opp['affinity']:.3f}, "
                  f"class={opp['classification']}")
            if opp["experiment"]:
                print(f"       → {opp['experiment']}")
        
        # Step 8: Select Programme Bet
        programme_bet = select_programme_bet(top_5, qloo.get("programme_bet_raw"))
        
        if programme_bet:
            print(f"\n  PROGRAMME BET:")
            print(f"    Primary: {programme_bet['primary_entity']} ({programme_bet['primary_domain']})")
            print(f"    Score: {programme_bet['opportunity_score']:.3f}")
            print(f"    Experiment: {programme_bet['experiment']}")
            print(f"    Falsification: {programme_bet['falsification'][:80]}...")
        
        # Rule-based consistency check (NOT independent validation)
        consistency_results = []
        for opp in top_5:
            # Rule-based: does the algorithmic classification match the score thresholds?
            score = opp["total_score"]
            if score >= 8:
                expected = "STRONG"
            elif score >= 6:
                expected = "PLAUSIBLE"
            elif score >= 4:
                expected = "WEAK"
            else:
                expected = "REJECT"
            consistent = opp["classification"] == expected
            consistency_results.append({
                "entity": opp["entity_title"],
                "classification": opp["classification"],
                "expected_from_rules": expected,
                "consistent": consistent,
            })
        
        consistent_count = sum(1 for c in consistency_results if c["consistent"])
        print(f"\n  RULE-BASED CONSISTENCY CHECK: {consistent_count}/{len(consistency_results)}")
        print(f"  (Note: This is a deterministic consistency check, NOT independent validation)")
        
        result = {
            "context_id": ctx["context_id"],
            "venue": ctx["venue"],
            "city": ctx["city"],
            "venue_type": ctx["venue_type"],
            "is_primary": is_primary,
            "classification_basis": ctx["classification_basis"],
            "programme_window": ctx["programme_window"],
            "programme_films": ctx["films"],
            "qloo_success": True,
            "qloo_coverage": cov,
            "programme_names": qloo["programme_names"],
            "raw_qloo_candidates": qloo["raw_count"],
            "evidence_pass_count": len(with_evidence),
            "programmability_pass_count": len(programmable),
            "strong_opportunity_count": len(strong),
            "plausible_opportunity_count": len(plausible),
            "top_5": top_5,
            "primary_programme_bet": programme_bet,
            "consistency_check": consistency_results,
            "nonfilm_domains": qloo["nonfilm_domains"],
            "taste_tags": qloo["taste_tags"],
        }
        results.append(result)
    
    # ============================================================
    # AGGREGATE (PRIMARY ONLY)
    # ============================================================
    primary_results = [r for r in results if r.get("is_primary")]
    secondary_results = [r for r in results if not r.get("is_primary")]
    
    print(f"\n{'='*70}")
    print("AGGREGATE — PRIMARY (INDEPENDENT) CONTEXTS ONLY")
    print(f"{'='*70}")
    
    for r in primary_results:
        print(f"\n  {r['venue']}:")
        print(f"    Raw candidates: {r.get('raw_qloo_candidates', 0)}")
        print(f"    Evidence pass: {r.get('evidence_pass_count', 0)}")
        print(f"    Programmable: {r.get('programmability_pass_count', 0)}")
        print(f"    Strong: {r.get('strong_opportunity_count', 0)}")
        bet = r.get("primary_programme_bet")
        if bet:
            print(f"    Programme Bet: {bet['primary_entity']} ({bet['primary_domain']})")
    
    # Save
    output = {
        "evaluation_date": datetime.now(timezone.utc).isoformat(),
        "evaluation_version": "M12.4",
        "primary_contexts": len(primary_results),
        "secondary_contexts": len(secondary_results),
        "results": results,
    }
    
    output_path = adjacent_root / "data" / "processed" / "m12_4_decision_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nResults saved to: {output_path}")
    
    return output


if __name__ == "__main__":
    asyncio.run(run_evaluation())