#!/usr/bin/env python3
"""M12.9: Evidence Score Robustness Lock.

Tests whether the Programme Bet is robust across scoring policies.
Separates candidate-level from cohort-level evidence.
"""

import asyncio
import json
import math
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

PRIMARY_CONTEXTS = [
    {
        "context_id": "genesis_london_2026_10",
        "venue": "Genesis Cinema",
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
# SCORING POLICIES (deterministic, not "models")
# ============================================================

POLICIES = {
    "affinity_only": lambda aff, pop, qr: aff,
    "affinity_qualifying": lambda aff, pop, qr: 0.8 * aff + 0.2 * qr,
    "affinity_popularity": lambda aff, pop, qr: 0.8 * aff + 0.2 * pop,
    "balanced": lambda aff, pop, qr: 0.6 * aff + 0.2 * pop + 0.2 * qr,
}


def score_candidate(entity: dict, policy_fn) -> dict:
    """Score a candidate under a given policy.
    
    Separates candidate-level from cohort-level evidence.
    """
    affinity = entity.get("affinity") or 0
    popularity = entity.get("popularity")
    pop = popularity if popularity is not None else 0.5
    qualifying = entity.get("qualifying_members", 0)
    total = entity.get("total_members", 0)
    qr = qualifying / total if total > 0 else 0
    
    score = policy_fn(affinity, pop, qr)
    
    return {
        "entity_title": entity.get("title", ""),
        "domain": entity.get("domain", ""),
        # CANDIDATE-LEVEL evidence (from Qloo, per-entity)
        "candidate_evidence": {
            "affinity": round(affinity, 4),
            "popularity": round(pop, 4),
            "band": entity.get("band", ""),
            "candidate_tags": entity.get("candidate_tags", []),
            "candidate_tag_count": len(entity.get("candidate_tags", [])),
        },
        # COHORT-LEVEL evidence (shared by all cohort members)
        "cohort_evidence": {
            "qualifying_members": qualifying,
            "total_members": total,
            "qualifying_ratio": round(qr, 4),
            "cohort_kind": entity.get("cohort_kind", "unknown"),
            "shared_tags": entity.get("shared_tags", []),
            "shared_tag_count": len(entity.get("shared_tags", [])),
            "construction_reason": entity.get("construction_reason", ""),
        },
        # Score under this policy
        "score": round(score, 4),
        # Attribution
        "per_film_attribution": "NOT_AVAILABLE",
    }


def rank_under_policy(candidates: list, policy_fn) -> list:
    """Rank candidates under a scoring policy."""
    seen = set()
    unique = []
    for c in candidates:
        title = c.get("title", "")
        if title not in seen:
            seen.add(title)
            unique.append(c)
    
    scored = [score_candidate(c, policy_fn) for c in unique]
    scored.sort(key=lambda x: -x["score"])
    for i, s in enumerate(scored):
        s["rank"] = i + 1
    return scored


def kendall_tau(rank_a: list, rank_b: list) -> float:
    """Kendall tau rank correlation between two rankings.
    
    Returns value between -1 (perfect disagreement) and +1 (perfect agreement).
    """
    # Build rank maps
    map_a = {r["entity_title"]: r["rank"] for r in rank_a}
    map_b = {r["entity_title"]: r["rank"] for r in rank_b}
    
    # Common entities
    common = sorted(set(map_a.keys()) & set(map_b.keys()))
    n = len(common)
    if n < 2:
        return 1.0
    
    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            a_i, a_j = map_a[common[i]], map_a[common[j]]
            b_i, b_j = map_b[common[i]], map_b[common[j]]
            
            dir_a = 1 if a_i < a_j else (-1 if a_i > a_j else 0)
            dir_b = 1 if b_i < b_j else (-1 if b_i > b_j else 0)
            
            if dir_a == dir_b:
                concordant += 1
            elif dir_a != 0 and dir_b != 0:
                discordant += 1
    
    total_pairs = concordant + discordant
    if total_pairs == 0:
        return 1.0
    return (concordant - discordant) / total_pairs


def overlap_at_k(rank_a: list, rank_b: list, k: int) -> int:
    """Count overlapping entities in top-k of both rankings."""
    set_a = {r["entity_title"] for r in rank_a[:k]}
    set_b = {r["entity_title"] for r in rank_b[:k]}
    return len(set_a & set_b)


async def run_qloo_evaluation(context: dict) -> dict:
    films = context["films"]
    try:
        state = await run_live_async(films, render=False, resolver_delay_s=1.0)
        programme_names = [p.resolved_name or p.title for p in state.resolved_items]
        
        all_nonfilm = []
        for cohort in state.ranked:
            score = cohort.score
            members = cohort.members if cohort.members else []
            domain = cohort.domain.replace("urn:entity:", "")
            if domain == "movie":
                continue
            
            cohort_kind = cohort.kind if hasattr(cohort, "kind") else "unknown"
            construction_evidence = cohort.construction_evidence if hasattr(cohort, "construction_evidence") else {}
            shared_tags = construction_evidence.get("shared_tags", [])
            construction_reason = cohort.construction_reason if hasattr(cohort, "construction_reason") else ""
            
            for member in members:
                candidate_tags = []
                if hasattr(member, "scored") and hasattr(member.scored, "tags"):
                    candidate_tags = [t.tag_id for t in member.scored.tags if t.tag_id]
                
                all_nonfilm.append({
                    "title": member.name if hasattr(member, "name") else str(member),
                    "domain": domain,
                    "affinity": member.affinity if hasattr(member, "affinity") else None,
                    "popularity": member.popularity if hasattr(member, "popularity") else None,
                    "band": member.band if hasattr(member, "band") else "",
                    "qualifying_members": len(cohort.qualifying_members) if cohort.members else 0,
                    "total_members": len(cohort.members) if cohort.members else 0,
                    "cohort_kind": cohort_kind,
                    "shared_tags": shared_tags,
                    "candidate_tags": candidate_tags,
                    "construction_reason": construction_reason,
                    "programme_films": programme_names,
                })
        
        all_nonfilm.sort(key=lambda x: -(x.get("affinity") or 0))
        return {"success": True, "raw_nonfilm": all_nonfilm, "raw_count": len(all_nonfilm)}
    except Exception as e:
        return {"success": False, "error": str(e), "raw_nonfilm": [], "raw_count": 0}


async def run_evaluation():
    print("=" * 70)
    print("M12.9: EVIDENCE SCORE ROBUSTNESS LOCK")
    print("=" * 70)
    
    all_results = []
    
    for ctx in PRIMARY_CONTEXTS:
        print(f"\n{'='*70}")
        print(f"CONTEXT: {ctx['venue']}")
        print(f"{'='*70}")
        
        qloo = await run_qloo_evaluation(ctx)
        if not qloo["success"]:
            print(f"  FAILED: {qloo.get('error')}")
            continue
        
        candidates = qloo["raw_nonfilm"]
        print(f"  Raw non-film: {qloo['raw_count']}")
        
        # Run all policies
        policy_rankings = {}
        for policy_name, policy_fn in POLICIES.items():
            policy_rankings[policy_name] = rank_under_policy(candidates, policy_fn)
        
        # Baseline: affinity_only
        baseline = policy_rankings["affinity_only"]
        
        # ============================================================
        # REPORT PER POLICY
        # ============================================================
        for policy_name, ranked in policy_rankings.items():
            print(f"\n  --- POLICY: {policy_name} ---")
            print(f"  Top 10:")
            for j, r in enumerate(ranked[:10]):
                ce = r["candidate_evidence"]
                cohe = r["cohort_evidence"]
                print(f"    {j+1}. {r['entity_title']:25s} ({r['domain']:8s}) "
                      f"score={r['score']:.4f} "
                      f"aff={ce['affinity']:.4f} pop={ce['popularity']:.4f} "
                      f"qr={cohe['qualifying_ratio']:.4f}")
            
            # Domain distribution top 20
            top20_domains = defaultdict(int)
            for r in ranked[:20]:
                top20_domains[r["domain"]] += 1
            print(f"  Domain top 20: {dict(top20_domains)}")
            
            # Programme Bet
            winner = ranked[0]
            print(f"  Winner: {winner['entity_title']} ({winner['domain']}), score={winner['score']:.4f}")
            
            # Rank of affinity_only winner
            if policy_name != "affinity_only":
                baseline_winner = baseline[0]["entity_title"]
                rank_of_baseline = next(
                    (r["rank"] for r in ranked if r["entity_title"] == baseline_winner), None
                )
                print(f"  Rank of baseline winner ({baseline_winner}): {rank_of_baseline}")
        
        # ============================================================
        # SENSITIVITY ANALYSIS
        # ============================================================
        print(f"\n  --- SENSITIVITY vs affinity_only ---")
        sensitivity = {}
        for policy_name, ranked in policy_rankings.items():
            if policy_name == "affinity_only":
                continue
            
            tau = kendall_tau(baseline, ranked)
            top5_overlap = overlap_at_k(baseline, ranked, 5)
            top10_overlap = overlap_at_k(baseline, ranked, 10)
            winner_same = baseline[0]["entity_title"] == ranked[0]["entity_title"]
            
            sensitivity[policy_name] = {
                "kendall_tau": round(tau, 4),
                "top5_overlap": top5_overlap,
                "top10_overlap": top10_overlap,
                "winner_same": winner_same,
                "winner": ranked[0]["entity_title"],
                "winner_domain": ranked[0]["domain"],
            }
            
            print(f"    {policy_name:25s} tau={tau:.4f} "
                  f"top5={top5_overlap}/5 top10={top10_overlap}/10 "
                  f"winner_same={winner_same}")
        
        # ============================================================
        # WINNER STABILITY
        # ============================================================
        winners = [(pn, r[0]["entity_title"], r[0]["domain"], r[0]["score"])
                   for pn, r in policy_rankings.items()]
        unique_winners = set(w[1] for w in winners)
        
        print(f"\n  --- WINNER STABILITY ---")
        for pn, name, domain, score in winners:
            print(f"    {pn:25s} → {name} ({domain}), score={score:.4f}")
        print(f"    Unique winners: {len(unique_winners)}")
        print(f"    Winner list: {sorted(unique_winners)}")
        
        robust = len(unique_winners) <= 2  # at most 2 different winners across 4 policies
        
        # ============================================================
        # EVIDENCE CLASSIFICATION
        # ============================================================
        print(f"\n  --- EVIDENCE CLASSIFICATION ---")
        # Check: is qualifying_ratio the same for all top candidates?
        top10_qr = [r["cohort_evidence"]["qualifying_ratio"] for r in baseline[:10]]
        qr_all_same = len(set(top10_qr)) <= 1
        print(f"    Top-10 qualifying_ratio all identical: {qr_all_same}")
        if qr_all_same:
            print(f"    → qualifying_ratio has ZERO differentiating power in top 10")
        
        # Check: popularity range in top 10
        top10_pop = [r["candidate_evidence"]["popularity"] for r in baseline[:10]]
        pop_range = max(top10_pop) - min(top10_pop)
        print(f"    Top-10 popularity range: {min(top10_pop):.4f} to {max(top10_pop):.4f} (spread={pop_range:.4f})")
        
        # Check: affinity range in top 10
        top10_aff = [r["candidate_evidence"]["affinity"] for r in baseline[:10]]
        aff_range = max(top10_aff) - min(top10_aff)
        print(f"    Top-10 affinity range: {min(top10_aff):.4f} to {max(top10_aff):.4f} (spread={aff_range:.4f})")
        
        result = {
            "venue": ctx["venue"],
            "raw_count": qloo["raw_count"],
            "policy_rankings": {
                pn: {
                    "top_10": [
                        {"title": r["entity_title"], "domain": r["domain"],
                         "score": r["score"],
                         "affinity": r["candidate_evidence"]["affinity"],
                         "popularity": r["candidate_evidence"]["popularity"],
                         "qr": r["cohort_evidence"]["qualifying_ratio"]}
                        for r in ranked[:10]
                    ],
                    "winner": ranked[0]["entity_title"],
                    "winner_domain": ranked[0]["domain"],
                    "winner_score": ranked[0]["score"],
                    "domain_top20": dict(defaultdict(int, **{r["domain"]: 0 for r in ranked[:20]})),
                }
                for pn, ranked in policy_rankings.items()
            },
            "sensitivity": sensitivity,
            "winner_stability": {
                "unique_winners": sorted(unique_winners),
                "robust": robust,
            },
            "evidence_classification": {
                "qualifying_ratio_all_same_top10": qr_all_same,
                "popularity_range_top10": round(pop_range, 4),
                "affinity_range_top10": round(aff_range, 4),
            },
        }
        all_results.append(result)
    
    # ============================================================
    # FINAL INTERPRETATION
    # ============================================================
    print(f"\n{'='*70}")
    print("FINAL INTERPRETATION")
    print(f"{'='*70}")
    print()
    print("OBSERVED QLOO: affinity, popularity, bands, tags, cohort membership")
    print("DERIVED: qualifying_ratio, normalized scores, rank correlations")
    print("PRODUCT POLICY: weights (0.6/0.2/0.2 or other)")
    print("UNKNOWN: actual attendance impact, per-film attribution, success thresholds")
    print()
    
    for r in all_results:
        venue = r["venue"]
        s = r["sensitivity"]
        ws = r["winner_stability"]
        ec = r["evidence_classification"]
        
        print(f"  {venue}:")
        print(f"    Winner stability: {'ROBUST' if ws['robust'] else 'SENSITIVE'}")
        print(f"    Unique winners: {ws['unique_winners']}")
        print(f"    qualifying_ratio differentiating: {not ec['qualifying_ratio_all_same_top10']}")
        print(f"    Popularity spread in top 10: {ec['popularity_range_top10']:.4f}")
        print(f"    Affinity spread in top 10: {ec['affinity_range_top10']:.4f}")
        
        for policy_name, sens in s.items():
            print(f"    vs {policy_name}: tau={sens['kendall_tau']:.4f}, "
                  f"winner_same={sens['winner_same']}")
    
    # Save
    output = {
        "evaluation_date": datetime.now(timezone.utc).isoformat(),
        "evaluation_version": "M12.9",
        "scoring_policies": list(POLICIES.keys()),
        "field_classification": {
            "CANDIDATE_EVIDENCE": ["affinity", "popularity", "band", "candidate_tags"],
            "COHORT_EVIDENCE": ["qualifying_members", "total_members", "qualifying_ratio", "cohort_kind", "shared_tags", "construction_evidence"],
            "DERIVED": ["qloo_evidence_score", "qualifying_ratio", "rank_correlations"],
            "PRODUCT_POLICY": ["scoring_weights"],
            "UNKNOWN": ["actual_attendance_impact", "per_film_attribution", "success_thresholds"],
        },
        "results": all_results,
    }
    
    output_path = adjacent_root / "data" / "processed" / "m12_9_robustness_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nResults saved to: {output_path}")
    return output


if __name__ == "__main__":
    asyncio.run(run_evaluation())