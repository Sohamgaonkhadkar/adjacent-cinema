"""M13.3: Live Outcome Collection Pipeline.

Collects real screening data from Prince Charles Cinema,
resolves films to Qloo entities, and stores in the outcome ledger.

M13.3: Production data collection.
"""

import json
import os
import sys
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

from app.domain.outcome_repository import OutcomeRepository
from app.collectors.prince_charles import collect_prince_charles


def run_collection():
    """Run the live collection pipeline."""
    print("=" * 70)
    print("M13.3: LIVE OUTCOME COLLECTION PIPELINE")
    print("=" * 70)

    # Initialize repository
    db_path = adjacent_root / "data" / "processed" / "outcome_ledger.db"
    repo = OutcomeRepository(db_path)
    print(f"\nRepository: {db_path}")

    # Phase 1: Collect Prince Charles showtimes
    print(f"\n{'='*70}")
    print("PHASE 1: Prince Charles Cinema Collection")
    print(f"{'='*70}")

    result = collect_prince_charles()

    if not result["success"]:
        print(f"  FAILED: {result.get('error')}")
        print(f"  Continuing with existing data...")
    else:
        screenings = result["screenings"]
        print(f"  Source: {result['source_url']}")
        print(f"  Timestamp: {result['source_timestamp']}")
        print(f"  Raw HTML: {result.get('raw_length', '?')} bytes")
        print(f"  Screenings extracted: {len(screenings)}")

        # Store screenings
        new_count = 0
        for s in screenings:
            obs_id, is_new = repo.record_screening(s)
            if is_new:
                new_count += 1

        print(f"  New observations: {new_count}")
        print(f"  Duplicate (same screening): {len(screenings) - new_count}")

    # Phase 2: Data quality audit
    print(f"\n{'='*70}")
    print("PHASE 2: Data Quality Audit")
    print(f"{'='*70}")

    audit = repo.data_quality_audit()
    print(f"  Total observations: {audit['total_observations']}")
    print(f"  Total snapshots: {audit['total_snapshots']}")
    print(f"  Unique films: {audit['unique_films']}")
    print(f"  Unique venues: {audit['unique_venues']}")
    print(f"  Avg snapshots/observation: {audit['avg_snapshots_per_observation']}")
    print(f"  Sold out: {audit['sold_out_stats']['sold_out']}")
    print(f"  Available: {audit['sold_out_stats']['available']}")
    print(f"  Unknown: {audit['sold_out_stats']['unknown']}")
    print(f"  Sold out rate: {audit['sold_out_stats']['sold_out_rate']:.2%}")

    # Phase 3: Show recent observations
    print(f"\n{'='*70}")
    print("PHASE 3: Recent Observations")
    print(f"{'='*70}")

    recent = repo.list_observations(limit=10)
    for obs in recent:
        sold = "SOLD OUT" if obs["sold_out"] == 1 else ("AVAILABLE" if obs["sold_out"] == 0 else "?")
        print(f"  {obs['show_date']:30s} {obs['film_title'][:30]:30s} {sold}")

    # Phase 4: Save benchmark
    print(f"\n{'='*70}")
    print("PHASE 4: Benchmark Export")
    print(f"{'='*70}")

    all_obs = repo.list_observations(limit=10000)
    benchmark = {
        "version": "M13.3",
        "collection_date": datetime.now(timezone.utc).isoformat(),
        "audit": audit,
        "observations": all_obs,
    }

    benchmark_path = adjacent_root / "data" / "processed" / "m13_3_proxy_benchmark.json"
    benchmark_path.write_text(json.dumps(benchmark, indent=2, default=str))
    print(f"  Saved to: {benchmark_path}")
    print(f"  Observations: {len(all_obs)}")

    repo.close()

    print(f"\n{'='*70}")
    print("COLLECTION COMPLETE")
    print(f"{'='*70}")
    print(f"  ML readiness: NOT_ML_READY")
    print(f"  Reason: Need 3-6 months of data for meaningful analysis")
    print(f"  Status: Pipeline operational, collecting real proxy data")


if __name__ == "__main__":
    run_collection()