#!/usr/bin/env python3
"""M11.2: Complete Live Qloo Validation.

Runs the full pipeline with real Qloo API using the existing run_live function.
Then builds the Programme Bet with two-sided evidence.
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
    print("=== M11.2 LIVE VALIDATION ===")
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
        print(f"Domain selection: {state.domain_selection is not None}")
        
        # Build Programme Bet with two-sided evidence (same logic as routes.py)
        compatibility_scores = {}
        reach_scores = {}
        compatibility_bands = {}
        reach_bands = {}
        compatibility_call_ids = {}
        reach_call_ids = {}
        
        for cohort in state.ranked:
            cid = cohort.cohort_id
            score = cohort.score
            
            if score and score.mean_affinity is not None:
                compatibility_scores[cid] = score.mean_affinity
                compatibility_bands[cid] = (
                    "High" if score.mean_affinity >= 0.6
                    else "Medium" if score.mean_affinity >= 0.5
                    else "Low"
                )
                compatibility_call_ids[cid] = score.call_id or ""
            
            total = len(cohort.members) if cohort.members else 0
            qualifying = len(cohort.qualifying_members) if cohort.members else 0
            if total > 0:
                reach_ratio = qualifying / total
                reach_scores[cid] = reach_ratio
                reach_bands[cid] = (
                    "High" if reach_ratio >= 0.5
                    else "Medium" if reach_ratio >= 0.3
                    else "Low"
                )
                reach_call_ids[cid] = score.call_id if score and score.call_id else ""
        
        print(f"\nTwo-sided evidence:")
        print(f"  Compatibility scores: {len(compatibility_scores)}")
        print(f"  Reach scores: {len(reach_scores)}")
        
        programme_bet = build_programme_bet(
            ranked_cohorts=state.ranked,
            taste_tags=state.taste_tags,
            geography=None,
            resolved_names=[p.resolved_name or p.title for p in state.resolved_items],
            compatibility_scores=compatibility_scores,
            reach_scores=reach_scores,
            compatibility_bands=compatibility_bands,
            reach_bands=reach_bands,
            compatibility_call_ids=compatibility_call_ids,
            reach_call_ids=reach_call_ids,
            rejected_cohorts=state.rejected,
        )
        
        if programme_bet:
            print(f"\nProgramme Bet:")
            print(f"  Primary: {programme_bet.primary_cohort_name}")
            print(f"  Domain: {programme_bet.primary_domain}")
            print(f"  Mean affinity: {programme_bet.primary_mean_affinity:.3f}")
            print(f"  Compatibility: {programme_bet.current_audience_compatibility}")
            print(f"  Compatibility band: {programme_bet.compatibility_band}")
            print(f"  Reach: {programme_bet.adjacent_cohort_reach}")
            print(f"  Reach band: {programme_bet.reach_band}")
            print(f"  Compatibility call ID: {programme_bet.compatibility_call_id}")
            print(f"  Reach call ID: {programme_bet.reach_call_id}")
            print(f"  Rejected candidates: {len(programme_bet.rejected_candidates)}")
        
        # Build report
        report = {
            "pipeline": "M11.2 Live Validation",
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
            ds = state.domain_selection
            report["domain_selection"] = ds.to_dict()
        
        # Print resolution details
        print("\nResolution details:")
        for item in report["resolution_status"]:
            print(f"  {item['title']} ({item['year']}): {item['status']}")
        
        # Print domain selection
        if report["domain_selection"]:
            ds = report["domain_selection"]
            print(f"\nDomain selection:")
            print(f"  Selected: {ds['selected_domains']}")
            print(f"  Skipped: {ds['skipped_domains']}")
        
        # Print ranked cohorts
        print(f"\nRanked cohorts:")
        for cohort in state.ranked:
            score = cohort.score
            if score:
                print(f"  {cohort.domain}: {len(cohort.members)} members, "
                      f"mean_affinity={score.mean_affinity:.3f}")
            else:
                print(f"  {cohort.domain}: no score")
        
        # Print rejected cohorts
        if state.rejected:
            print(f"\nRejected cohorts:")
            for cohort in state.rejected:
                rejection = cohort.rejection
                print(f"  {cohort.domain}: {rejection.code.value if rejection else 'unknown'}")
        
        # Save report
        output_path = Path(__file__).parent.parent / "docs" / "m11_2_live_run_result.json"
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