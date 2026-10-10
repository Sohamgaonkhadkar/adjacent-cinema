"""M13.4: Temporal Qloo Join & Leakage-Safe Proxy Benchmark.

Pipeline:
1. Collect PCC screenings (with normalized timestamps)
2. Resolve unique films to Qloo entities via existing resolver
3. Create Qloo feature snapshots (popularity from resolution)
4. Build analytical benchmark with prediction-time leakage prevention
5. Run resolution quality audit
6. Run availability-snapshot analysis
7. Run bias/coverage audit

Constraints:
- Does NOT train ML
- Does NOT treat AVAILABLE as negative outcome
- Does NOT use future Qloo information
- Uses existing EntityResolver (no second resolver)
"""

import asyncio
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

from app.domain.outcome_repository import OutcomeRepository, film_key
from app.collectors.prince_charles import collect_prince_charles
from app.config import Settings


async def resolve_films(repo: OutcomeRepository, limit: int | None = None,
                        dry_run: bool = False) -> dict:
    """Resolve unique films to Qloo entities.

    Uses existing EntityResolver. Resolves each unique film once.
    """
    from app.qloo.client import QlooClient
    from app.resolution.resolver import EntityResolver
    from app.resolution.contract import MatchStatus

    unique_films = repo.get_unique_films()
    print(f"\n  Unique films to resolve: {len(unique_films)}")

    if limit:
        unique_films = unique_films[:limit]
        print(f"  Limited to: {len(unique_films)}")

    if dry_run:
        print("  DRY RUN — no API calls")
        return {"resolved": 0, "ambiguous": 0, "mismatch": 0, "unresolved": 0, "skipped": 0}

    # Check which films are already resolved
    existing_resolutions = {r["film_key"]: r for r in repo.list_all_film_resolutions()}
    to_resolve = []
    skipped = 0
    for film in unique_films:
        fk = film_key(film["film_title"], film.get("film_year"))
        if fk in existing_resolutions:
            skipped += 1
        else:
            to_resolve.append(film)

    print(f"  Already resolved: {skipped}")
    print(f"  To resolve: {len(to_resolve)}")

    if not to_resolve:
        return {"resolved": 0, "ambiguous": 0, "mismatch": 0, "unresolved": 0, "skipped": skipped}

    # Create Qloo client and resolver
    settings = Settings.from_env()
    client = QlooClient(settings)
    resolver = EntityResolver(client, delay_s=1.5)

    stats = {"resolved": 0, "ambiguous": 0, "mismatch": 0, "unresolved": 0, "skipped": skipped}

    try:
        for i, film in enumerate(to_resolve):
            title = film["film_title"]
            year = film.get("film_year")
            fk = film_key(title, year)

            print(f"  [{i+1}/{len(to_resolve)}] {title} ({year})...", end=" ", flush=True)

            try:
                result = await resolver.resolve_item(title=title, year=year)
                status = result.match_status.value

                resolution = {
                    "film_key": fk,
                    "film_title": title,
                    "film_year": year,
                    "film_url": film.get("film_url"),
                    "resolution_status": status,
                    "resolved_title": result.qloo_name,
                    "resolved_year": result.qloo_year,
                    "qloo_entity_id": result.qloo_entity_id,
                    "qloo_name": result.qloo_name,
                    "qloo_entity_type": result.qloo_entity_type,
                    "qloo_popularity": result.qloo_popularity,
                    "qloo_call_id": result.call_id,
                    "resolution_provenance": f"resolver/{result.match_method.value if result.match_method else 'search'}",
                    "resolution_timestamp": datetime.now(timezone.utc).isoformat(),
                }

                repo.record_film_resolution(resolution)

                if status == "VERIFIED":
                    stats["resolved"] += 1
                    print(f"✓ {result.qloo_name} ({result.qloo_entity_id})")

                    # Also create a Qloo feature snapshot with popularity
                    repo.record_qloo_features({
                        "film_key": fk,
                        "qloo_entity_id": result.qloo_entity_id,
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "qloo_popularity": result.qloo_popularity,
                        "qloo_domain": "film",
                        "qloo_call_id": result.call_id,
                        "provenance": "resolution/search",
                    })

                elif status == "AMBIGUOUS":
                    stats["ambiguous"] += 1
                    print(f"? AMBIGUOUS: {result.qloo_name}")
                elif status == "MISMATCH":
                    stats["mismatch"] += 1
                    print(f"✗ MISMATCH: {result.qloo_name}")
                else:
                    stats["unresolved"] += 1
                    print(f"✗ UNRESOLVED")

            except Exception as e:
                stats["unresolved"] += 1
                print(f"✗ ERROR: {e}")

                # Record as unresolved
                repo.record_film_resolution({
                    "film_key": fk,
                    "film_title": title,
                    "film_year": year,
                    "film_url": film.get("film_url"),
                    "resolution_status": "UNRESOLVED",
                    "resolution_provenance": f"resolver/error:{str(e)[:100]}",
                    "resolution_timestamp": datetime.now(timezone.utc).isoformat(),
                })

    finally:
        await client.aclose()

    return stats


def build_benchmark(repo: OutcomeRepository, output_path: Path) -> dict:
    """Build the analytical benchmark with leakage-safe Qloo features."""
    benchmark_rows = repo.build_analytical_benchmark()

    # Compute audit stats
    total = len(benchmark_rows)
    with_verified = sum(1 for r in benchmark_rows if r["resolution_status"] == "VERIFIED")
    with_prediction_feature = sum(1 for r in benchmark_rows
                                   if r["qloo_feature_status"] == "AVAILABLE_AT_PREDICTION_TIME")
    with_future_feature = sum(1 for r in benchmark_rows
                               if r["qloo_feature_status"] == "FUTURE_FEATURE_UNAVAILABLE")
    sold_out = sum(1 for r in benchmark_rows if r["sold_out_observed"] == 1)
    available = sum(1 for r in benchmark_rows if r["sold_out_observed"] == 0)
    model_target_1 = sum(1 for r in benchmark_rows if r["model_target"] == 1)
    model_target_null = sum(1 for r in benchmark_rows if r["model_target"] is None)

    # Lead time distribution
    lead_time_buckets = {}
    for r in benchmark_rows:
        bucket = r.get("lead_time_bucket", "unknown")
        lead_time_buckets[bucket] = lead_time_buckets.get(bucket, 0) + 1

    benchmark = {
        "version": "M13.4",
        "collection_date": datetime.now(timezone.utc).isoformat(),
        "description": "Leakage-safe analytical benchmark with temporal Qloo join",
        "schema": {
            "model_target": "1=SOLD_OUT, NULL=AVAILABLE (AVAILABLE is NOT 0)",
            "qloo_feature_status": "AVAILABLE_AT_PREDICTION_TIME|FUTURE_FEATURE_UNAVAILABLE|NO_FEATURE",
            "sold_out_observed": "1=sold out, 0=available, NULL=unknown",
        },
        "stats": {
            "total_observations": total,
            "with_verified_entity": with_verified,
            "with_prediction_time_feature": with_prediction_feature,
            "with_future_feature": with_future_feature,
            "sold_out": sold_out,
            "available": available,
            "model_target_1": model_target_1,
            "model_target_null": model_target_null,
            "lead_time_distribution": lead_time_buckets,
        },
        "observations": benchmark_rows,
    }

    output_path.write_text(json.dumps(benchmark, indent=2, default=str))
    return benchmark


def resolution_quality_audit(repo: OutcomeRepository) -> dict:
    """Phase 8: Resolution quality audit."""
    # Film-level stats
    resolutions = repo.list_all_film_resolutions()
    unique_films = repo.get_unique_films()

    film_stats = {
        "total_unique_films": len(unique_films),
        "total_resolutions": len(resolutions),
        "verified": sum(1 for r in resolutions if r["resolution_status"] == "VERIFIED"),
        "ambiguous": sum(1 for r in resolutions if r["resolution_status"] == "AMBIGUOUS"),
        "mismatch": sum(1 for r in resolutions if r["resolution_status"] == "MISMATCH"),
        "unresolved": sum(1 for r in resolutions if r["resolution_status"] == "UNRESOLVED"),
    }
    film_stats["resolution_rate"] = (
        round(film_stats["verified"] / film_stats["total_unique_films"], 4)
        if film_stats["total_unique_films"] > 0 else 0
    )

    # Screening-level stats
    observations = repo.list_all_observations()
    total_screenings = len(observations)

    screening_verified = 0
    screening_unresolved = 0
    screening_with_prediction_feature = 0
    screening_with_future_feature = 0

    for obs in observations:
        fk = film_key(obs["film_title"], obs.get("film_year"))
        resolution = repo.get_film_resolution(fk)

        if resolution and resolution["resolution_status"] == "VERIFIED":
            screening_verified += 1
        else:
            screening_unresolved += 1

        feature = repo.get_latest_qloo_feature(fk, before=obs.get("source_timestamp"))
        if feature:
            screening_with_prediction_feature += 1
        else:
            latest = repo.get_latest_qloo_feature(fk)
            if latest:
                screening_with_future_feature += 1

    screening_stats = {
        "total_screenings": total_screenings,
        "screenings_with_verified_entity": screening_verified,
        "screenings_unresolved": screening_unresolved,
        "screenings_with_prediction_time_feature": screening_with_prediction_feature,
        "screenings_with_future_feature": screening_with_future_feature,
    }
    screening_stats["screening_resolution_rate"] = (
        round(screening_verified / total_screenings, 4) if total_screenings > 0 else 0
    )
    screening_stats["prediction_time_feature_rate"] = (
        round(screening_with_prediction_feature / total_screenings, 4) if total_screenings > 0 else 0
    )

    return {"film_level": film_stats, "screening_level": screening_stats}


def availability_snapshot_analysis(repo: OutcomeRepository) -> dict:
    """Phase 9: Availability-snapshot analysis."""
    observations = repo.list_all_observations()

    # Count snapshot patterns
    single_available = 0
    single_sold_out = 0
    single_unknown = 0
    available_to_sold_out = 0
    multi_snapshot_no_change = 0
    transitions = []

    for obs in observations:
        snapshots = repo.get_snapshots(obs["observation_id"])
        if len(snapshots) == 1:
            so = snapshots[0]["sold_out"]
            if so == 1:
                single_sold_out += 1
            elif so == 0:
                single_available += 1
            else:
                single_unknown += 1
        else:
            # Multi-snapshot: check for state transitions
            saw_available = False
            had_transition = False
            for snap in snapshots:
                if snap["sold_out"] == 0:
                    saw_available = True
                elif snap["sold_out"] == 1 and saw_available:
                    had_transition = True
                    available_to_sold_out += 1
                    transitions.append({
                        "observation_id": obs["observation_id"],
                        "film_title": obs["film_title"],
                        "snapshots": len(snapshots),
                    })
                    break
            if not had_transition:
                multi_snapshot_no_change += 1

    return {
        "single_snapshot_available": single_available,
        "single_snapshot_sold_out": single_sold_out,
        "single_snapshot_unknown": single_unknown,
        "available_to_sold_out_transitions": available_to_sold_out,
        "multi_snapshot_no_change": multi_snapshot_no_change,
        "total_multi_snapshot": repo.count_multi_snapshot_observations(),
        "total_state_transitions": repo.count_state_transitions(),
        "transitions": transitions[:20],  # First 20 for report
    }


def bias_coverage_audit(repo: OutcomeRepository) -> dict:
    """Phase 10: Bias/coverage audit."""
    observations = repo.list_all_observations()
    total = len(observations)

    # By lead_time_bucket
    by_lead_time = {}
    for obs in observations:
        bucket = obs.get("lead_time_bucket", "unknown")
        if bucket not in by_lead_time:
            by_lead_time[bucket] = {"total": 0, "sold_out": 0, "available": 0}
        by_lead_time[bucket]["total"] += 1
        if obs["sold_out"] == 1:
            by_lead_time[bucket]["sold_out"] += 1
        elif obs["sold_out"] == 0:
            by_lead_time[bucket]["available"] += 1

    # By day_of_week (from show_date)
    by_day = {}
    for obs in observations:
        day = obs["show_date"].split()[0] if obs["show_date"] else "unknown"
        if day not in by_day:
            by_day[day] = {"total": 0, "sold_out": 0}
        by_day[day]["total"] += 1
        if obs["sold_out"] == 1:
            by_day[day]["sold_out"] += 1

    # By format
    by_format = {}
    for obs in observations:
        fmt = obs.get("format", "") or "none"
        if fmt not in by_format:
            by_format[fmt] = {"total": 0, "sold_out": 0}
        by_format[fmt]["total"] += 1
        if obs["sold_out"] == 1:
            by_format[fmt]["sold_out"] += 1

    # By month (from show_start_at)
    by_month = {}
    for obs in observations:
        ssa = obs.get("show_start_at")
        if ssa:
            month = ssa[:7]  # "2026-10"
        else:
            month = "unknown"
        if month not in by_month:
            by_month[month] = {"total": 0, "sold_out": 0}
        by_month[month]["total"] += 1
        if obs["sold_out"] == 1:
            by_month[month]["sold_out"] += 1

    return {
        "total_observations": total,
        "sold_out_total": sum(1 for o in observations if o["sold_out"] == 1),
        "available_total": sum(1 for o in observations if o["sold_out"] == 0),
        "unknown_total": sum(1 for o in observations if o["sold_out"] is None),
        "by_lead_time_bucket": by_lead_time,
        "by_day_of_week": by_day,
        "by_format": by_format,
        "by_month": by_month,
        "note": "3.0% sold_out rate is NOT evidence that demand is 3%. It is the fraction of currently observed screenings reported sold out at collection time.",
    }


async def run_m13_4(dry_run: bool = False, resolve_limit: int | None = None):
    """Run the full M13.4 pipeline."""
    print("=" * 70)
    print("M13.4: TEMPORAL QLOO JOIN & LEAKAGE-SAFE PROXY BENCHMARK")
    print("=" * 70)

    # Initialize repository
    db_path = adjacent_root / "data" / "processed" / "outcome_ledger.db"
    repo = OutcomeRepository(db_path)
    print(f"\nRepository: {db_path}")

    # Phase 1: Collect PCC screenings (with normalized timestamps)
    print(f"\n{'='*70}")
    print("PHASE 1: Prince Charles Cinema Collection (M13.4 timestamps)")
    print(f"{'='*70}")

    result = collect_prince_charles()

    if not result["success"]:
        print(f"  FAILED: {result.get('error')}")
        print(f"  Continuing with existing data...")
    else:
        screenings = result["screenings"]
        print(f"  Source: {result['source_url']}")
        print(f"  Timestamp: {result['source_timestamp']}")
        print(f"  Screenings extracted: {len(screenings)}")

        # Check timestamp normalization
        with_timestamps = sum(1 for s in screenings if s.get("show_start_at"))
        print(f"  With normalized timestamps: {with_timestamps}/{len(screenings)}")

        # Store screenings
        new_count = 0
        for s in screenings:
            obs_id, is_new = repo.record_screening(s)
            if is_new:
                new_count += 1

        print(f"  New observations: {new_count}")
        print(f"  Duplicate (same screening): {len(screenings) - new_count}")

    # Phase 2: Qloo Resolution
    print(f"\n{'='*70}")
    print("PHASE 2: Qloo Resolution for Unique Films")
    print(f"{'='*70}")

    resolution_stats = await resolve_films(repo, limit=resolve_limit, dry_run=dry_run)
    print(f"\n  Resolution stats:")
    print(f"    Verified: {resolution_stats.get('resolved', 0)}")
    print(f"    Ambiguous: {resolution_stats.get('ambiguous', 0)}")
    print(f"    Mismatch: {resolution_stats.get('mismatch', 0)}")
    print(f"    Unresolved: {resolution_stats.get('unresolved', 0)}")
    print(f"    Skipped (already resolved): {resolution_stats.get('skipped', 0)}")

    # Phase 3: Resolution Quality Audit
    print(f"\n{'='*70}")
    print("PHASE 3: Resolution Quality Audit")
    print(f"{'='*70}")

    audit = resolution_quality_audit(repo)
    print(f"\n  Film-level:")
    print(f"    Unique films: {audit['film_level']['total_unique_films']}")
    print(f"    Verified: {audit['film_level']['verified']}")
    print(f"    Ambiguous: {audit['film_level']['ambiguous']}")
    print(f"    Mismatch: {audit['film_level']['mismatch']}")
    print(f"    Unresolved: {audit['film_level']['unresolved']}")
    print(f"    Resolution rate: {audit['film_level']['resolution_rate']:.2%}")

    print(f"\n  Screening-level:")
    print(f"    Total screenings: {audit['screening_level']['total_screenings']}")
    print(f"    With verified entity: {audit['screening_level']['screenings_with_verified_entity']}")
    print(f"    With prediction-time feature: {audit['screening_level']['screenings_with_prediction_time_feature']}")
    print(f"    With future feature: {audit['screening_level']['screenings_with_future_feature']}")
    print(f"    Screening resolution rate: {audit['screening_level']['screening_resolution_rate']:.2%}")
    print(f"    Prediction-time feature rate: {audit['screening_level']['prediction_time_feature_rate']:.2%}")

    # Phase 4: Availability-Snapshot Analysis
    print(f"\n{'='*70}")
    print("PHASE 4: Availability-Snapshot Analysis")
    print(f"{'='*70}")

    snapshot_analysis = availability_snapshot_analysis(repo)
    print(f"\n  Single snapshot (available): {snapshot_analysis['single_snapshot_available']}")
    print(f"  Single snapshot (sold out): {snapshot_analysis['single_snapshot_sold_out']}")
    print(f"  Multi-snapshot (total): {snapshot_analysis['total_multi_snapshot']}")
    print(f"  AVAILABLE → SOLD_OUT transitions: {snapshot_analysis['available_to_sold_out_transitions']}")
    print(f"  Note: transitions are 'observed transition time', NOT 'true sell-through time'")

    # Phase 5: Bias/Coverage Audit
    print(f"\n{'='*70}")
    print("PHASE 5: Bias/Coverage Audit")
    print(f"{'='*70}")

    bias = bias_coverage_audit(repo)
    print(f"\n  Total: {bias['total_observations']}")
    print(f"  Sold out: {bias['sold_out_total']} ({bias['sold_out_total']/bias['total_observations']:.1%})")
    print(f"  Available: {bias['available_total']}")
    print(f"  Unknown: {bias['unknown_total']}")

    print(f"\n  By lead time bucket:")
    for bucket, stats in sorted(bias["by_lead_time_bucket"].items()):
        so_rate = stats["sold_out"] / stats["total"] if stats["total"] > 0 else 0
        print(f"    {bucket}: {stats['total']} screenings, {stats['sold_out']} sold out ({so_rate:.1%})")

    print(f"\n  By format:")
    for fmt, stats in sorted(bias["by_format"].items(), key=lambda x: -x[1]["total"]):
        so_rate = stats["sold_out"] / stats["total"] if stats["total"] > 0 else 0
        print(f"    {fmt}: {stats['total']} screenings, {stats['sold_out']} sold out ({so_rate:.1%})")

    print(f"\n  By month:")
    for month, stats in sorted(bias["by_month"].items()):
        so_rate = stats["sold_out"] / stats["total"] if stats["total"] > 0 else 0
        print(f"    {month}: {stats['total']} screenings, {stats['sold_out']} sold out ({so_rate:.1%})")

    # Phase 6: Build Analytical Benchmark
    print(f"\n{'='*70}")
    print("PHASE 6: Build Analytical Benchmark")
    print(f"{'='*70}")

    benchmark_path = adjacent_root / "data" / "processed" / "m13_4_qloo_proxy_benchmark.json"
    benchmark = build_benchmark(repo, benchmark_path)
    print(f"  Output: {benchmark_path}")
    print(f"  Total rows: {benchmark['stats']['total_observations']}")
    print(f"  With verified entity: {benchmark['stats']['with_verified_entity']}")
    print(f"  With prediction-time feature: {benchmark['stats']['with_prediction_time_feature']}")
    print(f"  With future feature: {benchmark['stats']['with_future_feature']}")
    print(f"  model_target=1 (SOLD_OUT): {benchmark['stats']['model_target_1']}")
    print(f"  model_target=NULL (AVAILABLE): {benchmark['stats']['model_target_null']}")

    # Phase 7: Data Quality Summary
    print(f"\n{'='*70}")
    print("PHASE 7: Data Quality Summary")
    print(f"{'='*70}")

    sold_out_stats = repo.sold_out_stats()
    print(f"\n  Screenings: {sold_out_stats['total']}")
    print(f"  Unique films: {repo.data_quality_audit()['unique_films']}")
    print(f"  Film resolution: {audit['film_level']['verified']} / {audit['film_level']['total_unique_films']}")
    print(f"  Screening resolution: {audit['screening_level']['screenings_with_verified_entity']} / {audit['screening_level']['total_screenings']}")
    print(f"  Prediction-time Qloo feature: {audit['screening_level']['screenings_with_prediction_time_feature']} / {audit['screening_level']['total_screenings']}")
    print(f"  Future Qloo feature: {audit['screening_level']['screenings_with_future_feature']} / {audit['screening_level']['total_screenings']}")
    print(f"  Sold out: {sold_out_stats['sold_out']}")
    print(f"  Available: {sold_out_stats['available']}")
    print(f"  Multi-snapshot: {snapshot_analysis['total_multi_snapshot']}")
    print(f"  State transitions: {snapshot_analysis['total_state_transitions']}")

    # Save audit reports
    audit_path = adjacent_root / "data" / "processed" / "m13_4_audit.json"
    audit_path.write_text(json.dumps({
        "version": "M13.4",
        "collection_date": datetime.now(timezone.utc).isoformat(),
        "resolution_audit": audit,
        "snapshot_analysis": snapshot_analysis,
        "bias_audit": bias,
        "sold_out_stats": sold_out_stats,
    }, indent=2, default=str))

    repo.close()

    print(f"\n{'='*70}")
    print("M13.4 COMPLETE")
    print(f"{'='*70}")
    print(f"  ML readiness: NOT_ML_READY")
    print(f"  Benchmark: {benchmark_path}")
    print(f"  Audit: {audit_path}")
    print(f"  Label semantics: CORRECTED (sold_out=False → DESCRIPTIVE_ONLY)")
    print(f"  Timestamps: NORMALIZED (Europe/London)")
    print(f"  Lead time: MODELED (bucketed)")
    print(f"  Prediction-time leakage: BLOCKED")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="M13.4: Temporal Qloo Join Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls")
    parser.add_argument("--resolve-limit", type=int, default=None, help="Limit number of films to resolve")
    args = parser.parse_args()

    asyncio.run(run_m13_4(dry_run=args.dry_run, resolve_limit=args.resolve_limit))