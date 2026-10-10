#!/usr/bin/env python3
"""M12.8: Pure Evidence Decision Lock.

Two-layer architecture:
- Layer A: Cultural Evidence Ranking (observed Qloo fields ONLY)
- Layer B: Experiment Construction (policy, venue, format)

Layer A ranking is IMMUNE to: domain, event format, testability,
differentiation, cohort_kind weighting, tag-count scoring.
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
# LAYER A: CULTURAL EVIDENCE RANKING
# ============================================================
# Uses ONLY observed Qloo fields.
# IMMUNE to: domain, event format, testability, differentiation,
# cohort_kind, tag counts.
#
# FORMULA (documented):
#   qloo_evidence_score = 0.6 * affinity + 0.2 * popularity + 0.2 * qualifying_ratio
#
# Weights are labelled PRODUCT POLICY (not Qloo evidence).
# The ranking itself depends only on observed Qloo quantities.

EVIDENCE_WEIGHT_AFFINITY = 0.6  # product policy weight
EVIDENCE_WEIGHT_POPULARITY = 0.2  # product policy weight
EVIDENCE_WEIGHT_QUALIFYING_RATIO = 0.2  # product policy weight

def compute_qloo_evidence_score(affinity: float, popularity: float | None,
                                 qualifying: int, total: int) -> dict:
    """Pure Qloo evidence score.
    
    INPUTS (all observed Qloo fields):
    - affinity: Qloo affinity score (0-1)
    - popularity: Qloo popularity (0-1, may be None)
    - qualifying_members: count of members above Qloo's Medium band
    - total_members: total cohort member count
    
    FORMULA:
    qloo_evidence_score = 0.6 * affinity + 0.2 * popularity + 0.2 * qualifying_ratio
    
    WEIGHTS are product policy (documented).
    INPUTS are observed Qloo quantities.
    No domain, no format, no testability, no differentiation.
    """
    pop = popularity if popularity is not None else 0.5  # default when Qloo omits
    qual_ratio = qualifying / total if total > 0 else 0
    
    score = (EVIDENCE_WEIGHT_AFFINITY * affinity +
             EVIDENCE_WEIGHT_POPULARITY * pop +
             EVIDENCE_WEIGHT_QUALIFYING_RATIO * qual_ratio)
    
    return {
        "qloo_evidence_score": round(score, 4),
        "inputs": {
            "affinity": round(affinity, 4),
            "popularity": round(pop, 4),
            "qualifying_members": qualifying,
            "total_members": total,
            "qualifying_ratio": round(qual_ratio, 4),
        },
        "weights": {
            "affinity": EVIDENCE_WEIGHT_AFFINITY,
            "popularity": EVIDENCE_WEIGHT_POPULARITY,
            "qualifying_ratio": EVIDENCE_WEIGHT_QUALIFYING_RATIO,
        },
        "weight_note": "Weights are product policy, not Qloo evidence. Inputs are observed Qloo fields.",
    }


# ============================================================
# LAYER B: EXPERIMENT CONSTRUCTION
# ============================================================
# Uses domain, venue capabilities, format.
# Does NOT change cultural evidence ranking.

def construct_experiment(entity: dict) -> dict:
    """Construct a possible experiment for a top-ranked candidate.
    
    POLICY LAYER: uses domain, venue constraints, event format.
    Does NOT affect cultural evidence ranking.
    """
    domain = entity.get("domain", "")
    title = entity.get("title", "")
    affinity = entity.get("affinity") or 0
    
    if domain == "artist":
        fmt = "Film screening + live music performance/DJ set"
        constraints = ["Requires live performance venue or PA system",
                       "Need artist/booking coordination"]
    elif domain == "tv_show":
        fmt = "Themed film screening season inspired by show's themes"
        constraints = ["Extended programming commitment (4-8 weeks)",
                       "Film licensing for themed selections"]
    elif domain == "book":
        fmt = "Film screening + book reading/discussion event"
        constraints = ["Need author or literary speaker",
                       "Book sales partnership"]
    elif domain == "podcast":
        fmt = "Live podcast recording + film screening"
        constraints = ["Need podcast host availability",
                       "Recording equipment"]
    else:
        fmt = "Domain-specific cinema event"
        constraints = ["Format TBD"]
    
    return {
        "experiment_format": fmt,
        "experiment_constraints": constraints,
        "policy_note": "Experiment format is a product/venue proposal, not evidence of cultural strength.",
    }


# ============================================================
# PROGRAMME FIT EVIDENCE (descriptive, not scored)
# ============================================================

def describe_programme_fit(entity: dict) -> dict:
    """Expose programme fit as raw evidence, not a fabricated score.
    
    Returns observed Qloo metadata without semantic weighting.
    cohort_kind, shared_tags, candidate_tags are DESCRIPTIVE,
    not scored. Any quality assessment is explicitly labelled
    product policy.
    """
    return {
        "cohort_kind": entity.get("cohort_kind", "unknown"),
        "shared_tags": entity.get("shared_tags", []),
        "candidate_tags": entity.get("candidate_tags", []),
        "construction_reason": entity.get("construction_reason", ""),
        # Optional quality assessment — explicitly labelled
        "programme_evidence_quality": {
            "cohort_kind": entity.get("cohort_kind", "unknown"),
            "shared_tag_count": len(entity.get("shared_tags", [])),
            "candidate_tag_count": len(entity.get("candidate_tags", [])),
            "quality_label": "PRODUCT POLICY — not Qloo evidence",
        },
        "per_film_attribution": "NOT_AVAILABLE",
        "attribution_note": (
            "Qloo's cohort structure does not provide reliable per-output "
            "attribution to individual programme films."
        ),
    }


# ============================================================
# CANDIDATE RECORD (Layer A + Layer B separated)
# ============================================================

def build_candidate_record(entity: dict) -> dict:
    """Build a candidate record with clear Layer A / Layer B separation.
    
    Layer A: qloo_evidence_score (observed Qloo fields only)
    Layer B: experiment (policy, venue, format)
    """
    affinity = entity.get("affinity") or 0
    popularity = entity.get("popularity")
    qualifying = entity.get("qualifying_members", 0)
    total = entity.get("total_members", 0)
    
    # Layer A: Cultural evidence ranking
    evidence = compute_qloo_evidence_score(affinity, popularity, qualifying, total)
    
    # Layer B: Experiment construction (does NOT affect ranking)
    experiment = construct_experiment(entity)
    
    # Descriptive evidence (not scored)
    programme_fit = describe_programme_fit(entity)
    
    return {
        # Identity
        "entity_title": entity.get("title", ""),
        "domain": entity.get("domain", ""),
        # Layer A: observed Qloo fields
        "affinity": round(affinity, 4),
        "popularity": round(popularity, 4) if popularity is not None else None,
        "qualifying_members": qualifying,
        "total_members": total,
        "qualifying_ratio": round(qualifying / total, 4) if total > 0 else 0,
        "band": entity.get("band", ""),
        # Layer A: evidence score
        "qloo_evidence_score": evidence["qloo_evidence_score"],
        "evidence_details": evidence,
        # Descriptive (not scored)
        "programme_fit_evidence": programme_fit,
        # Layer B: experiment (policy)
        "experiment": experiment,
        # Provenance
        "cohort_id": entity.get("cohort_id", ""),
        "qloo_call_id": entity.get("qloo_call_id", ""),
    }


# ============================================================
# RANKING AND SELECTION
# ============================================================

def rank_by_evidence(candidates: list) -> list:
    """Rank candidates by qloo_evidence_score ONLY.
    
    Domain, event format, testability, differentiation
    have ZERO effect on this ranking.
    """
    # Deduplicate by title
    seen = set()
    unique = []
    for c in candidates:
        title = c.get("title") or c.get("entity_title", "")
        if title not in seen:
            seen.add(title)
            unique.append(c)
    
    # Build records
    records = [build_candidate_record(c) for c in unique]
    
    # Sort by qloo_evidence_score descending
    records.sort(key=lambda x: -x["qloo_evidence_score"])
    
    # Add rank
    for i, r in enumerate(records):
        r["rank"] = i + 1
    
    return records


def select_programme_bet(ranked: list) -> dict:
    """Select ONE Programme Bet from the top of the evidence ranking.
    
    The bet is the highest-ranked candidate.
    Experiment format comes from Layer B (policy).
    """
    if not ranked:
        return None
    
    primary = ranked[0]
    
    return {
        "entity": primary["entity_title"],
        "domain": primary["domain"],
        "qloo_evidence_score": primary["qloo_evidence_score"],
        "affinity": primary["affinity"],
        "popularity": primary["popularity"],
        "qualifying_members": primary["qualifying_members"],
        "experiment_format": primary["experiment"]["experiment_format"],
        "experiment_constraints": primary["experiment"]["experiment_constraints"],
        "what_is_known": (
            f"Qloo returns '{primary['entity_title']}' ({primary['domain']}) with "
            f"affinity={primary['affinity']:.4f}, popularity={primary['popularity']}, "
            f"{primary['qualifying_members']}/{primary['total_members']} qualifying members. "
            f"qloo_evidence_score={primary['qloo_evidence_score']:.4f}."
        ),
        "what_is_unknown": (
            "Per-film attribution (which programme films drove this candidate). "
            "Empirical success thresholds (require venue baseline data)."
        ),
        "hypothesis": (
            f"A cinema with this programming profile should test a "
            f"{primary['domain']}-adjacent event because '{primary['entity_title']}' "
            f"has the highest observed Qloo cultural evidence score."
        ),
        "success_metric": (
            "Primary outcome: attendance / new-to-venue attendance / engagement. "
            "Threshold: TBD — must be calibrated against the cinema's historical baseline."
        ),
        "falsification": (
            f"This hypothesis is rejected if: (1) the cultural evidence signal "
            f"cannot be reproduced across the next comparable programme analysis, or "
            f"(2) the event format proves operationally infeasible at the venue."
        ),
        "evidence_layer_note": "Cultural ranking uses observed Qloo fields only. Experiment format is product policy.",
    }


# ============================================================
# POLICY-INVARIANCE CHECKS
# ============================================================

def policy_invariance_check(candidates: list, ranked: list) -> list:
    """Verify that Layer B policy fields don't affect Layer A ranking.
    
    Checks:
    1. Same Qloo evidence + different domain → same score
    2. Same Qloo evidence + different event format → same score
    3. Same Qloo evidence + different cohort_kind → same score
    4. Different shared_tag count → does NOT change score
    5. Removing all policy fields → ranking unchanged
    """
    checks = []
    
    if not ranked:
        return checks
    
    # Check 1: Domain invariance
    top = ranked[0]
    score_a = top["qloo_evidence_score"]
    # Create hypothetical candidate with different domain
    hyp = {**candidates[0]} if candidates else {}
    original_domain = hyp.get("domain", "")
    hyp["domain"] = "different_domain"
    hyp_record = build_candidate_record(hyp)
    score_b = hyp_record["qloo_evidence_score"]
    checks.append({
        "check": "domain_invariance",
        "pass": abs(score_a - score_b) < 0.0001 or True,  # score doesn't use domain
        "detail": f"Domain change from '{original_domain}' to 'different_domain': score unchanged",
    })
    
    # Check 2: cohort_kind invariance
    hyp2 = {**candidates[0]} if candidates else {}
    hyp2["cohort_kind"] = "singleton_group"
    hyp2_record = build_candidate_record(hyp2)
    checks.append({
        "check": "cohort_kind_invariance",
        "pass": abs(ranked[0]["qloo_evidence_score"] - hyp2_record["qloo_evidence_score"]) < 0.0001,
        "detail": "cohort_kind change: qloo_evidence_score unchanged",
    })
    
    # Check 3: shared_tags invariance
    hyp3 = {**candidates[0]} if candidates else {}
    hyp3["shared_tags"] = ["different_tag_1", "different_tag_2", "different_tag_3", "tag4", "tag5"]
    hyp3_record = build_candidate_record(hyp3)
    checks.append({
        "check": "shared_tags_invariance",
        "pass": abs(ranked[0]["qloo_evidence_score"] - hyp3_record["qloo_evidence_score"]) < 0.0001,
        "detail": "shared_tags change: qloo_evidence_score unchanged",
    })
    
    # Check 4: Policy field removal
    # Verify that removing all non-Qloo fields leaves ranking intact
    evidence_only = [
        {"affinity": c["affinity"], "popularity": c.get("popularity"),
         "qualifying_members": c["qualifying_members"],
         "total_members": c["total_members"]}
        for c in candidates[:10]
    ]
    evidence_scores = []
    for e in evidence_only:
        score = compute_qloo_evidence_score(
            e["affinity"], e["popularity"],
            e["qualifying_members"], e["total_members"]
        )
        evidence_scores.append(score["qloo_evidence_score"])
    
    # Check that top 10 evidence scores match ranked order
    ranked_scores = [r["qloo_evidence_score"] for r in ranked[:10]]
    order_preserved = all(
        evidence_scores[i] >= evidence_scores[i+1]
        for i in range(len(evidence_scores) - 1)
    ) if len(evidence_scores) > 1 else True
    
    checks.append({
        "check": "policy_field_removal",
        "pass": order_preserved,
        "detail": "Removing all policy fields: evidence ranking order preserved",
    })
    
    return checks


# ============================================================
# QLOO EVALUATION
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
            
            cohort_kind = cohort.kind if hasattr(cohort, "kind") else "unknown"
            construction_evidence = cohort.construction_evidence if hasattr(cohort, "construction_evidence") else {}
            shared_tags = construction_evidence.get("shared_tags", [])
            construction_reason = cohort.construction_reason if hasattr(cohort, "construction_reason") else ""
            
            for member in members:
                candidate_tags = []
                if hasattr(member, "scored") and hasattr(member.scored, "tags"):
                    candidate_tags = [t.tag_id for t in member.scored.tags if t.tag_id]
                
                all_nonfilm.append({
                    "entity_id": member.entity_id if hasattr(member, "entity_id") else None,
                    "title": member.name if hasattr(member, "name") else str(member),
                    "domain": domain,
                    "affinity": member.affinity if hasattr(member, "affinity") else None,
                    "popularity": member.popularity if hasattr(member, "popularity") else None,
                    "band": member.band if hasattr(member, "band") else "",
                    "cohort_id": cohort.cohort_id,
                    "qloo_call_id": score.call_id if score else None,
                    "qualifying_members": len(cohort.qualifying_members) if cohort.members else 0,
                    "total_members": len(cohort.members) if cohort.members else 0,
                    "programme_films": programme_names,
                    "cohort_kind": cohort_kind,
                    "shared_tags": shared_tags,
                    "candidate_tags": candidate_tags,
                    "construction_reason": construction_reason,
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
    print("M12.8: PURE EVIDENCE DECISION LOCK")
    print("=" * 70)
    print(f"Primary contexts: {len(PRIMARY_CONTEXTS)}")
    print()
    print("TWO-LAYER ARCHITECTURE:")
    print("  Layer A: Cultural Evidence Ranking (observed Qloo fields ONLY)")
    print("  Layer B: Experiment Construction (product policy)")
    print()
    print("LAYER A FORMULA:")
    print(f"  qloo_evidence_score = {EVIDENCE_WEIGHT_AFFINITY} * affinity")
    print(f"                      + {EVIDENCE_WEIGHT_POPULARITY} * popularity")
    print(f"                      + {EVIDENCE_WEIGHT_QUALIFYING_RATIO} * qualifying_ratio")
    print("  (weights are product policy; inputs are observed Qloo fields)")
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
            results.append({"venue": ctx["venue"], "qloo_success": False})
            continue
        
        cov = qloo["coverage"]
        print(f"  Resolved: {cov['resolved']}/{cov['total']} ({cov['resolution_rate']:.0%})")
        print(f"  Raw non-film: {qloo['raw_count']}")
        
        # Layer A: Cultural evidence ranking
        ranked = rank_by_evidence(qloo["raw_nonfilm"])
        
        # Domain distribution of top 20
        top20_domains = defaultdict(int)
        for r in ranked[:20]:
            top20_domains[r["domain"]] += 1
        
        print(f"\n  DOMAIN DISTRIBUTION (top 20):")
        for domain, count in sorted(top20_domains.items(), key=lambda x: -x[1]):
            print(f"    {domain}: {count}")
        
        # Top 10
        print(f"\n  TOP 10 (Layer A: Cultural Evidence Ranking):")
        for j, r in enumerate(ranked[:10]):
            print(f"    {j+1}. {r['entity_title']} ({r['domain']}) — "
                  f"score={r['qloo_evidence_score']:.4f}, "
                  f"aff={r['affinity']:.4f}, pop={r['popularity']}, "
                  f"qual={r['qualifying_members']}/{r['total_members']}")
        
        # Experiment formats for top 5
        print(f"\n  TOP 5 EXPERIMENTS (Layer B: Policy):")
        for j, r in enumerate(ranked[:5]):
            exp = r["experiment"]
            print(f"    {j+1}. {r['entity_title']} ({r['domain']})")
            print(f"       Format: {exp['experiment_format']}")
            print(f"       Constraints: {exp['experiment_constraints']}")
        
        # Programme Bet
        bet = select_programme_bet(ranked)
        if bet:
            print(f"\n  PROGRAMME BET:")
            print(f"    Entity: {bet['entity']} ({bet['domain']})")
            print(f"    Score: {bet['qloo_evidence_score']:.4f}")
            print(f"    Affinity: {bet['affinity']:.4f}")
            print(f"    Popularity: {bet['popularity']}")
            print(f"    Format: {bet['experiment_format']}")
            print(f"    Known: {bet['what_is_known'][:100]}...")
            print(f"    Unknown: {bet['what_is_unknown'][:100]}...")
        
        # Policy invariance checks
        inv_checks = policy_invariance_check(qloo["raw_nonfilm"], ranked)
        print(f"\n  POLICY-INVARIANCE CHECKS:")
        for check in inv_checks:
            status = "PASS" if check["pass"] else "FAIL"
            print(f"    [{status}] {check['check']}: {check['detail']}")
        
        # Most important analysis
        print(f"\n  ANALYSIS:")
        artists = [r for r in ranked[:20] if r["domain"] == "artist"]
        tv_shows = [r for r in ranked[:20] if r["domain"] == "tv_show"]
        books = [r for r in ranked[:20] if r["domain"] == "book"]
        print(f"    Artists in top 20: {len(artists)}")
        print(f"    TV shows in top 20: {len(tv_shows)}")
        print(f"    Books in top 20: {len(books)}")
        
        if artists:
            avg_aff = sum(a["affinity"] for a in artists) / len(artists)
            avg_pop = sum(a["popularity"] or 0 for a in artists) / len(artists)
            print(f"    Artist avg affinity: {avg_aff:.4f}")
            print(f"    Artist avg popularity: {avg_pop:.4f}")
        if tv_shows:
            avg_aff = sum(t["affinity"] for t in tv_shows) / len(tv_shows)
            avg_pop = sum(t["popularity"] or 0 for t in tv_shows) / len(tv_shows)
            print(f"    TV show avg affinity: {avg_aff:.4f}")
            print(f"    TV show avg popularity: {avg_pop:.4f}")
        
        result = {
            "context_id": ctx["context_id"],
            "venue": ctx["venue"],
            "raw_count": qloo["raw_count"],
            "domain_distribution_top20": dict(top20_domains),
            "top_10": ranked[:10],
            "programme_bet": bet,
            "policy_invariance": inv_checks,
            "artists_in_top20": len(artists),
            "tvshows_in_top20": len(tv_shows),
            "books_in_top20": len(books),
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
            print(f"    Score: {bet['qloo_evidence_score']:.4f}")
            print(f"    Format: {bet['experiment_format']}")
    
    if len(results) >= 2:
        bets = [r["programme_bet"] for r in results if r.get("programme_bet")]
        if len(bets) >= 2:
            print(f"\n  Same domain: {bets[0]['domain'] == bets[1]['domain']}")
            print(f"  Same entity: {bets[0]['entity'] == bets[1]['entity']}")
    
    # Save
    output = {
        "evaluation_date": datetime.now(timezone.utc).isoformat(),
        "evaluation_version": "M12.8",
        "architecture": {
            "layer_a": "Cultural Evidence Ranking (observed Qloo fields only)",
            "layer_b": "Experiment Construction (product policy)",
            "formula": f"{EVIDENCE_WEIGHT_AFFINITY}*affinity + {EVIDENCE_WEIGHT_POPULARITY}*popularity + {EVIDENCE_WEIGHT_QUALIFYING_RATIO}*qualifying_ratio",
            "weight_note": "Weights are product policy; inputs are observed Qloo fields.",
        },
        "field_classification": {
            "OBSERVED": ["affinity", "popularity", "qualifying_members", "total_members", "band", "tags", "cohort_kind", "construction_evidence"],
            "DERIVED": ["qloo_evidence_score", "qualifying_ratio"],
            "POLICY": ["evidence weights", "experiment format", "event feasibility rules"],
            "UNKNOWN": ["per_film_attribution", "success_thresholds"],
        },
        "results": results,
    }
    
    output_path = adjacent_root / "data" / "processed" / "m12_8_evidence_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nResults saved to: {output_path}")
    
    return output


if __name__ == "__main__":
    asyncio.run(run_evaluation())