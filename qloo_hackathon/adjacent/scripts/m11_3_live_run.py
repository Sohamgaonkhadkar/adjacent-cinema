#!/usr/bin/env python3
"""M11.3: Complete Live Qloo Validation.

Runs the full pipeline with real Qloo API using the existing run_live function.
Then builds the Programme Bet with two-sided evidence (M11.3: scientifically accurate).
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ[key.strip()] = value.strip()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from app.config import Settings
from app.live_runner import run_live_async
from app.domain.programme_bet import build_programme_bet

# Six-film modern demo programme
PROGRAMME = [
    {"title": "Parasite", "year": 2019, "imdb_id": "tt6751668"},
    {"title": "Everything Everywhere All at Once", "year": 2022, "imdb_id": "tt6710474"},
    {"title": "Dune", "year": 2021, "imdb_id": "tt1160419"},
    {"title": "The Banshees of Inisherin", "year": 2022, "imdb_id": "tt11813216"},
    {"title": "Oppenheimer", "year": 2023, "imdb_id": "tt15398776"},
    {"title": "Past Lives", "year": 2023, "imdb_id": "tt13238346"},
]


async def run():
    """Execute the full pipeline using run_live_async."""
    print("=== M11.3 LIVE VALIDATION ===")
    print(f"Programme: {len(PROGRAMME)} films")
    print(f"City: London\n")
    
    try:
        state = await run_live_async(
            PROGRAMME,
            render=True,
            resolver_delay_s=1.0,
        )
        
        print("\n" + "=" * 60)
        print("LIVE RUN COMPLETE")
        print("=" * 60)
        print(f"Stop reason: {state.stop_reason}")
        print(f"Data status: {state.data_status}")
        print(f"Resolved items: {len(state.resolved_items)}")
        print(f"Ranked cohorts: {len(state.ranked)}")
        print(f"Rejected cohorts: {len(state.rejected)}")
        
        # Build Programme Bet with two-sided evidence (M11.3: scientifically accurate)
        programme_adjacency_scores = {}
        cohort_breadth_scores = {}
        programme_adjacency_bands = {}
        cohort_breadth_bands = {}
        programme_adjacency_call_ids = {}
        cohort_breadth_call_ids = {}
        
        for cohort in state.ranked:
            cid = cohort.cohort_id
            score = cohort.score
            
            if score and score.mean_affinity is not None:
                programme_adjacency_scores[cid] = score.mean_affinity
                programme_adjacency_bands[cid] = (
                    "High" if score.mean_affinity >= 0.6
                    else "Medium" if score.mean_affinity >= 0.5
                    else "Low"
                )
                programme_adjacency_call_ids[cid] = score.call_id or ""
            
            total = len(cohort.members) if cohort.members else 0
            qualifying = len(cohort.qualifying_members) if cohort.members else 0
            if total > 0:
                breadth_ratio = qualifying / total
                cohort_breadth_scores[cid] = breadth_ratio
                cohort_breadth_bands[cid] = (
                    "High" if breadth_ratio >= 0.5
                    else "Medium" if breadth_ratio >= 0.3
                    else "Low"
                )
                cohort_breadth_call_ids[cid] = score.call_id if score and score.call_id else ""
        
        print(f"\nTwo-sided evidence:")
        print(f"  Programme adjacency scores: {len(programme_adjacency_scores)}")
        print(f"  Cohort breadth scores: {len(cohort_breadth_scores)}")
        
        programme_bet = build_programme_bet(
            ranked_cohorts=state.ranked,
            taste_tags=state.taste_tags,
            geography=None,
            resolved_names=[p.resolved_name or p.title for p in state.resolved_items],
            programme_adjacency_scores=programme_adjacency_scores,
            cohort_breadth_scores=cohort_breadth_scores,
            programme_adjacency_bands=programme_adjacency_bands,
            cohort_breadth_bands=cohort_breadth_bands,
            programme_adjacency_call_ids=programme_adjacency_call_ids,
            cohort_breadth_call_ids=cohort_breadth_call_ids,
            rejected_cohorts=state.rejected,
        )
        
        if programme_bet:
            print(f"\nProgramme Bet:")
            print(f"  Primary: {programme_bet.primary_cohort_name}")
            print(f"  Domain: {programme_bet.primary_domain}")
            print(f"  Mean affinity: {programme_bet.primary_mean_affinity:.3f}")
            print(f"  Programme adjacency: {programme_bet.programme_adjacency}")
            print(f"  Adjacency band: {programme_bet.adjacency_band}")
            print(f"  Cohort breadth: {programme_bet.cohort_breadth}")
            print(f"  Breadth band: {programme_bet.breadth_band}")
            print(f"  Adjacency call ID: {programme_bet.adjacency_call_id}")
            print(f"  Breadth call ID: {programme_bet.breadth_call_id}")
            print(f"  Rejected candidates: {len(programme_bet.rejected_candidates)}")
        
        # Build report
        report = {
            "pipeline": "M11.3 Live Validation",
            "city": "London",
            "programme": PROGRAMME,
            "stop_reason": state.stop_reason,
            "data_status": state.data_status,
            "resolved_items": len(state.resolved_items),
            "resolution_status": [],
            "domain_selection": None,
            "ranked_cohorts": len(state.ranked),
            "rejected_cohorts": len(state.rejected),
            "programme_bet": programme_bet.to_dict() if programme_bet else None,
            "errors": [],
        }
        
        # Resolution details
        for item in state.programme:
            report["resolution_status"].append({
                "title": item.title,
                "year": item.year,
                "imdb_id": item.imdb_id,
                "status": "VERIFIED" if item.resolved else "UNRESOLVED",
                "entity_id": item.resolved_entity_id,
                "resolved_name": item.resolved_name,
            })
        
        # Domain selection
        if state.domain_selection:
            report["domain_selection"] = state.domain_selection.to_dict()
        
        # Print resolution details
        print("\nResolution details:")
        for item in report["resolution_status"]:
            print(f"  {item['title']} ({item['year']}): {item['status']}")
        
        # Print ranked cohorts
        print(f"\nRanked cohorts:")
        for cohort in state.ranked:
            score = cohort.score
            if score:
                print(f"  {cohort.domain}: {len(cohort.members)} members, "
                      f"mean_affinity={score.mean_affinity:.3f}")
            else:
                print(f"  {cohort.domain}: no score")
        
        # Save report
        output_path = Path(__file__).parent.parent / "docs" / "m11_3_live_run_result.json"
        output_path.write_text(json.dumps(report, indent=2, default=str))
        print(f"\nReport saved to: {output_path}")
        
        return state
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(run())