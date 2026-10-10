"""M13.6: Prospective Temporal Qloo Signal Experiment.

Pipeline:
1. Scrape PCC for current inventory
2. Identify eligible future screenings
3. Create prediction snapshots at fixed horizons (7d, 3d, 1d)
4. Freeze Qloo features at prediction time
5. Update outcomes for past predictions
6. Run leakage audit
7. Export prospective benchmark

Constraints:
- Does NOT train ML
- Does NOT relabel historical observations
- Does NOT claim Qloo predicts attendance
- Idempotent: repeated runs don't create duplicate snapshots
"""

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
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
from app.domain.film_identity import canonical_film_key
from app.domain.qloo_signal import assess_feature, temporal_signal_status
from app.collectors.prince_charles import collect_prince_charles


# Fixed prediction horizons (hours)
PREDICTION_HORIZONS = [168, 72, 24]  # 7d, 3d, 1d

# Final observation window (hours before showtime)
# "Available near showtime" means observed available within this window
FINAL_OBSERVATION_WINDOW_HOURS = 2


def generate_run_id() -> str:
    """Generate a deterministic prediction run ID."""
    now = datetime.now(timezone.utc)
    return hashlib.sha256(
        f"prediction_run|{now.strftime('%Y%m%d')}|{now.strftime('%H%M%S')}".encode()
    ).hexdigest()[:16]


def compute_day_of_week(show_start_at: str) -> str:
    """Extract day of week from ISO timestamp."""
    try:
        dt = datetime.fromisoformat(show_start_at)
        return dt.strftime("%A")
    except (ValueError, TypeError):
        return ""


def compute_start_hour(show_start_at: str) -> int | None:
    """Extract hour from ISO timestamp."""
    try:
        dt = datetime.fromisoformat(show_start_at)
        return dt.hour
    except (ValueError, TypeError):
        return None


def step1_collect_pcc(repo: OutcomeRepository) -> dict:
    """Step 1: Scrape PCC for current inventory."""
    print(f"\n{'='*70}")
    print("STEP 1: COLLECT PCC INVENTORY")
    print(f"{'='*70}")

    result = collect_prince_charles()

    if not result["success"]:
        print(f"  FAILED: {result.get('error')}")
        return {"success": False, "screenings": 0}

    screenings = result["screenings"]
    print(f"  Source: {result['source_url']}")
    print(f"  Timestamp: {result['source_timestamp']}")
    print(f"  Screenings extracted: {len(screenings)}")

    new_count = 0
    for s in screenings:
        obs_id, is_new = repo.record_screening(s)
        if is_new:
            new_count += 1

    print(f"  New observations: {new_count}")
    print(f"  Duplicates: {len(screenings) - new_count}")

    return {"success": True, "screenings": len(screenings), "new": new_count}


def step2_create_prediction_snapshots(repo: OutcomeRepository,
                                       run_id: str) -> dict:
    """Step 2: Create prediction snapshots for eligible future screenings."""
    print(f"\n{'='*70}")
    print("STEP 2: CREATE PREDICTION SNAPSHOTS")
    print(f"{'='*70}")

    now = datetime.now(timezone.utc)
    observations = repo.list_all_observations()
    canonical_films = {cf["film_key"]: cf for cf in repo.list_canonical_films()}

    # Filter to future screenings with show_start_at
    future_screenings = []
    for obs in observations:
        if not obs.get("show_start_at"):
            continue
        try:
            show_dt = datetime.fromisoformat(obs["show_start_at"])
            if show_dt.tzinfo is None:
                show_dt = show_dt.replace(tzinfo=timezone.utc)
            if show_dt > now:
                future_screenings.append(obs)
        except (ValueError, TypeError):
            continue

    print(f"  Future screenings: {len(future_screenings)}")

    # Create prediction run record
    repo.create_prediction_run({
        "prediction_run_id": run_id,
        "run_timestamp": now.isoformat(),
        "run_type": "INITIAL",
        "total_screenings": len(observations),
        "eligible_screenings": len(future_screenings),
    })

    # Create prediction snapshots for each horizon
    stats = {"total_eligible": len(future_screenings), "by_horizon": {}}

    for horizon in PREDICTION_HORIZONS:
        horizon_label = f"{horizon}h ({horizon // 24}d)"
        created = 0
        skipped = 0

        for obs in future_screenings:
            try:
                show_dt = datetime.fromisoformat(obs["show_start_at"])
                if show_dt.tzinfo is None:
                    show_dt = show_dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            # Compute prediction timestamp for this horizon
            prediction_ts = show_dt - timedelta(hours=horizon)

            # Only create if prediction time is in the past (we can observe)
            # OR if prediction time is now (within 1 hour)
            # For future predictions, we still create them as PENDING
            # They will be populated with Qloo features in step 3

            # Get canonical film key
            cf_key = canonical_film_key(obs["film_title"], obs.get("film_year"))

            # Check if canonical film exists and has resolution
            cf = canonical_films.get(cf_key)
            identity_status = cf.get("identity_status", "NO_CANONICAL") if cf else "NO_CANONICAL"

            # Skip events
            if cf and cf.get("is_event"):
                skipped += 1
                continue

            # Get existing Qloo resolution
            resolution = repo.get_film_resolution(cf_key)
            qloo_entity_id = resolution.get("qloo_entity_id") if resolution else None
            qloo_popularity = resolution.get("qloo_popularity") if resolution else None

            # Select the latest substantive Qloo row before the prediction cutoff.
            # An empty or identity-only row must not mask an earlier usable snapshot.
            feature_rows = repo.get_qloo_features_for_film(cf_key)
            feature = repo.get_latest_usable_qloo_feature(cf_key, before=prediction_ts.isoformat())
            latest_usable = repo.get_latest_usable_qloo_feature(cf_key)
            if feature:
                qloo_feature_status = "AVAILABLE_AT_PREDICTION_TIME"
            elif latest_usable:
                qloo_feature_status = "FUTURE_FEATURE_UNAVAILABLE"
            elif feature_rows:
                qloo_feature_status = "EMPTY_OR_METADATA_ONLY"
            else:
                qloo_feature_status = "NO_FEATURE"
            qloo_signal_status = temporal_signal_status(
                feature, feature_rows, prediction_ts.isoformat()
            )
            assessment = assess_feature(feature)
            candidate_tags = assessment.get("tags", []) if feature else []
            # Critical: popularity is populated ONLY from the temporally eligible
            # snapshot. Never fall back to resolution-table popularity.
            qloo_popularity = feature.get("qloo_popularity") if feature else None
            qloo_affinity = feature.get("qloo_affinity") if feature else None
            qloo_feature_ts = feature.get("retrieved_at") if feature else None
            qloo_feature_provenance = feature.get("provenance", "") if feature else ""

            # Create snapshot
            repo.upsert_prediction_snapshot({
                "observation_id": obs["observation_id"],
                "film_key": cf_key,
                "prediction_run_id": run_id,
                "prediction_timestamp": prediction_ts.isoformat(),
                "prediction_horizon_hours": horizon,
                "show_start_at": obs["show_start_at"],
                "qloo_entity_id": qloo_entity_id,
                "qloo_popularity": qloo_popularity,
                "qloo_affinity": qloo_affinity,
                "qloo_candidate_tags": candidate_tags,
                "qloo_band": feature.get("qloo_band") if feature else None,
                "qloo_domain": feature.get("qloo_domain") if feature else None,
                "qloo_feature_timestamp": qloo_feature_ts,
                "qloo_feature_status": qloo_feature_status,
                "qloo_signal_status": qloo_signal_status,
                "qloo_feature_provenance": qloo_feature_provenance,
                "qloo_call_id": feature.get("qloo_call_id") if feature else None,
                "format": obs.get("format", ""),
                "day_of_week": compute_day_of_week(obs["show_start_at"]),
                "start_hour": compute_start_hour(obs["show_start_at"]),
                "source_url": obs.get("source_url", ""),
                "source_timestamp": obs.get("source_timestamp", ""),
                "provenance": f"prediction_run/{run_id}",
            })
            created += 1

        stats["by_horizon"][horizon] = {"created": created, "skipped_events": skipped}
        print(f"  Horizon {horizon_label}: {created} snapshots created, {skipped} events skipped")

    return stats


def step3_update_outcomes(repo: OutcomeRepository) -> dict:
    """Step 3: Update outcomes for past predictions.

    For each PENDING prediction snapshot where the show time has passed:
    - Check if sold_out was observed
    - Compute outcome status
    """
    print(f"\n{'='*70}")
    print("STEP 3: UPDATE OUTCOMES")
    print(f"{'='*70}")

    now = datetime.now(timezone.utc)
    pending = repo.list_prediction_snapshots(outcome_status="PENDING")

    updated = 0
    for snap in pending:
        try:
            show_dt = datetime.fromisoformat(snap["show_start_at"])
            if show_dt.tzinfo is None:
                show_dt = show_dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue

        # Only update if show time has passed
        if show_dt > now:
            continue

        # Get the latest observation for this screening
        obs = repo.get_observation(snap["observation_id"])
        if not obs:
            continue

        # Get all snapshots for this observation to find final pre-show observation
        snapshots = repo.get_snapshots(snap["observation_id"])

        # Find the latest snapshot before showtime
        final_snap = None
        for s in snapshots:
            try:
                s_ts = datetime.fromisoformat(s["source_timestamp"])
                if s_ts.tzinfo is None:
                    s_ts = s_ts.replace(tzinfo=timezone.utc)
                if s_ts <= show_dt:
                    final_snap = s
            except (ValueError, TypeError):
                continue

        if not final_snap:
            # No observation before showtime
            repo.update_prediction_outcome(
                snap["observation_id"],
                snap["prediction_horizon_hours"],
                {"outcome_status": "UNKNOWN",
                 "final_observation_timestamp": None,
                 "lead_time_at_final_observation": None},
            )
            updated += 1
            continue

        # Compute lead time at final observation
        try:
            final_ts = datetime.fromisoformat(final_snap["source_timestamp"])
            if final_ts.tzinfo is None:
                final_ts = final_ts.replace(tzinfo=timezone.utc)
            lead_time_hours = (show_dt - final_ts).total_seconds() / 3600.0
        except (ValueError, TypeError):
            lead_time_hours = None

        # Determine outcome
        sold_out = final_snap.get("sold_out")

        if sold_out == 1:
            # Sold out observed
            outcome_status = "SOLD_OUT_OBSERVED"
        elif sold_out == 0 and lead_time_hours is not None and lead_time_hours <= FINAL_OBSERVATION_WINDOW_HOURS:
            # Available near showtime (within final observation window)
            outcome_status = "AVAILABLE_NEAR_SHOWTIME"
        else:
            # Censored: available but not near showtime, or unknown
            outcome_status = "CENSORED"

        repo.update_prediction_outcome(
            snap["observation_id"],
            snap["prediction_horizon_hours"],
            {"outcome_status": outcome_status,
             "sold_out_observed": sold_out,
             "final_observation_timestamp": final_snap["source_timestamp"],
             "lead_time_at_final_observation": lead_time_hours},
        )
        updated += 1

    print(f"  Pending snapshots: {len(pending)}")
    print(f"  Updated: {updated}")
    print(f"  Still pending: {len(pending) - updated}")

    return {"pending": len(pending), "updated": updated}


def step4_run_leakage_audit(repo: OutcomeRepository) -> dict:
    """Step 4: Run automated leakage audit."""
    print(f"\n{'='*70}")
    print("STEP 4: LEAKAGE AUDIT")
    print(f"{'='*70}")

    audit = repo.leakage_audit()

    print(f"  Total snapshots: {audit['total_snapshots']}")
    print(f"  Violations:")
    for check, count in audit["violations"].items():
        status = "✓ PASS" if count == 0 else f"✗ FAIL ({count})"
        print(f"    {check}: {status}")
    print(f"  Overall: {'✓ PASS' if audit['passed'] else '✗ FAIL'}")

    return audit


def step5_export_benchmark(repo: OutcomeRepository, output_path: Path) -> dict:
    """Step 5: Export prospective benchmark."""
    print(f"\n{'='*70}")
    print("STEP 5: EXPORT PROSPECTIVE BENCHMARK")
    print(f"{'='*70}")

    snapshots = repo.list_prediction_snapshots()
    stats = repo.prediction_snapshot_stats()

    benchmark = {
        "version": "M13.6",
        "collection_date": datetime.now(timezone.utc).isoformat(),
        "description": "Prospective temporal Qloo signal experiment",
        "prediction_horizons": PREDICTION_HORIZONS,
        "outcome_definitions": {
            "SOLD_OUT_OBSERVED": "Sold out observed before show_start_at",
            "AVAILABLE_NEAR_SHOWTIME": "Available observed within 0-2h of show_start_at",
            "CENSORED": "Available but not near showtime, or insufficient observation",
            "UNKNOWN": "No observation available",
        },
        "stats": stats,
        "snapshots": snapshots,
    }

    output_path.write_text(json.dumps(benchmark, indent=2, default=str))

    print(f"  Total snapshots: {stats['total']}")
    print(f"  By horizon:")
    for h, count in stats["by_horizon"].items():
        print(f"    {h}h ({h // 24}d): {count}")
    print(f"  By outcome:")
    for status, count in stats["by_outcome"].items():
        print(f"    {status}: {count}")
    print(f"  With Qloo entity: {stats['with_qloo_entity']}")

    return {"stats": stats, "output": str(output_path)}


def step6_signal_analysis(repo: OutcomeRepository) -> dict:
    """Step 6: First Qloo signal test (descriptive only)."""
    print(f"\n{'='*70}")
    print("STEP 6: QLOO SIGNAL ANALYSIS")
    print(f"{'='*70}")

    stats = repo.prediction_snapshot_stats()
    completed = stats["by_outcome"].get("SOLD_OUT_OBSERVED", 0) + \
                stats["by_outcome"].get("AVAILABLE_NEAR_SHOWTIME", 0)

    print(f"\n  Outcome status:")
    for status, count in stats["by_outcome"].items():
        print(f"    {status}: {count}")
    print(f"\n  Completed outcomes: {completed}")

    if completed < 10:
        print(f"\n  SIGNAL_TEST_INCONCLUSIVE")
        print(f"  Reason: Too few completed outcomes ({completed}) for meaningful analysis")
        return {"status": "INCONCLUSIVE", "completed": completed}

    # Run per-horizon analysis
    for horizon in PREDICTION_HORIZONS:
        print(f"\n  Horizon {horizon}h ({horizon // 24}d):")
        snapshots = repo.list_prediction_snapshots(horizon=horizon)

        sold_out = [s for s in snapshots if s["outcome_status"] == "SOLD_OUT_OBSERVED"]
        available = [s for s in snapshots if s["outcome_status"] == "AVAILABLE_NEAR_SHOWTIME"]
        censored = [s for s in snapshots if s["outcome_status"] == "CENSORED"]
        pending = [s for s in snapshots if s["outcome_status"] == "PENDING"]

        print(f"    Total: {len(snapshots)}")
        print(f"    Sold out: {len(sold_out)}")
        print(f"    Available near showtime: {len(available)}")
        print(f"    Censored: {len(censored)}")
        print(f"    Pending: {len(pending)}")

        completed_h = len(sold_out) + len(available)
        if completed_h < 5:
            print(f"    SIGNAL_TEST_INCONCLUSIVE (n={completed_h})")
            continue

        # Simple descriptive comparison: Qloo popularity vs sold_out
        with_qloo = [s for s in sold_out + available if s.get("qloo_popularity")]
        without_qloo = [s for s in sold_out + available if not s.get("qloo_popularity")]

        if with_qloo:
            sold_out_rate_with = len([s for s in with_qloo if s["outcome_status"] == "SOLD_OUT_OBSERVED"]) / len(with_qloo)
            print(f"    Sold-out rate WITH Qloo (n={len(with_qloo)}): {sold_out_rate_with:.1%}")
        if without_qloo:
            sold_out_rate_without = len([s for s in without_qloo if s["outcome_status"] == "SOLD_OUT_OBSERVED"]) / len(without_qloo)
            print(f"    Sold-out rate WITHOUT Qloo (n={len(without_qloo)}): {sold_out_rate_without:.1%}")

    return {"status": "PRELIMINARY", "completed": completed}


async def run_m13_6():
    """Run the full M13.6 pipeline."""
    print("=" * 70)
    print("M13.6: PROSPECTIVE TEMPORAL QLOO SIGNAL EXPERIMENT")
    print("=" * 70)

    db_path = adjacent_root / "data" / "processed" / "outcome_ledger.db"
    repo = OutcomeRepository(db_path)
    print(f"\nRepository: {db_path}")

    # Generate prediction run ID
    run_id = generate_run_id()
    print(f"Prediction run ID: {run_id}")

    # Step 1: Collect PCC inventory
    collect_result = step1_collect_pcc(repo)

    # Step 2: Create prediction snapshots
    snapshot_result = step2_create_prediction_snapshots(repo, run_id)

    # Step 3: Update outcomes
    outcome_result = step3_update_outcomes(repo)

    # Step 4: Leakage audit
    leakage_result = step4_run_leakage_audit(repo)

    # Step 5: Export benchmark
    benchmark_path = adjacent_root / "data" / "processed" / "m13_6_prospective_benchmark.json"
    benchmark_result = step5_export_benchmark(repo, benchmark_path)

    # Step 6: Signal analysis
    signal_result = step6_signal_analysis(repo)

    # Save audit
    audit_path = adjacent_root / "data" / "processed" / "m13_6_audit.json"
    audit_path.write_text(json.dumps({
        "version": "M13.6",
        "collection_date": datetime.now(timezone.utc).isoformat(),
        "prediction_run_id": run_id,
        "collection": collect_result,
        "snapshots": snapshot_result,
        "outcomes": outcome_result,
        "leakage_audit": leakage_result,
        "benchmark_stats": benchmark_result.get("stats"),
        "signal_analysis": signal_result,
    }, indent=2, default=str))

    repo.close()

    # Final summary
    print(f"\n{'='*70}")
    print("M13.6 FINAL SUMMARY")
    print(f"{'='*70}")

    bs = benchmark_result.get("stats", {})
    print(f"\n  Prediction run: {run_id}")
    print(f"  Prediction snapshots: {bs.get('total', 0)}")
    print(f"    7d (168h): {bs.get('by_horizon', {}).get(168, 0)}")
    print(f"    3d (72h): {bs.get('by_horizon', {}).get(72, 0)}")
    print(f"    1d (24h): {bs.get('by_horizon', {}).get(24, 0)}")
    print(f"  With Qloo entity: {bs.get('with_qloo_entity', 0)}")

    print(f"\n  Outcome status:")
    for status, count in bs.get("by_outcome", {}).items():
        print(f"    {status}: {count}")

    print(f"\n  Leakage audit: {'✓ PASS' if leakage_result.get('passed') else '✗ FAIL'}")

    print(f"\n  Signal test: {signal_result.get('status', 'UNKNOWN')}")
    if signal_result.get("status") == "INCONCLUSIVE":
        print(f"  Completed outcomes: {signal_result.get('completed', 0)}")
        print(f"  Reason: Too few completed outcomes for meaningful analysis")

    print(f"\n  Benchmark: {benchmark_path}")
    print(f"  Audit: {audit_path}")


if __name__ == "__main__":
    asyncio.run(run_m13_6())