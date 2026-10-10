#!/usr/bin/env python3
"""M13.6.4: Deterministic Coverage & Integrity Audit.

Read-only audit of the outcome ledger producing honest, reconciled metrics.

Usage:
    python -m research.scripts.m13_6_4_coverage_audit [--json]

Metrics produced:
  A. Film Resolution Coverage
  B. Snapshot Existence Coverage
  C. Prediction-Time Temporal Coverage
  D. Usable Feature Coverage (non-empty tags, temporally eligible)
  E. Empty-Signal Coverage
  F. Retrospective-Only Coverage
  G. No-Resolution / No-Feature Coverage

Every metric documents its denominator, numerator, counting unit, and SQL.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def run_audit(conn: sqlite3.Connection) -> dict:
    """Run the full coverage and integrity audit. Read-only."""

    # ====================================================================
    # Basic counts
    # ====================================================================
    total_predictions = conn.execute(
        "SELECT COUNT(*) FROM prediction_snapshot"
    ).fetchone()[0]

    planned_count = conn.execute(
        "SELECT COUNT(*) FROM prediction_snapshot WHERE prediction_state = 'PLANNED'"
    ).fetchone()[0]

    frozen_count = conn.execute(
        "SELECT COUNT(*) FROM prediction_snapshot WHERE prediction_state = 'FROZEN'"
    ).fetchone()[0]

    outcome_final_count = conn.execute(
        "SELECT COUNT(*) FROM prediction_snapshot WHERE prediction_state = 'OUTCOME_FINAL'"
    ).fetchone()[0]

    censored_count = conn.execute(
        "SELECT COUNT(*) FROM prediction_snapshot WHERE prediction_state = 'CENSORED'"
    ).fetchone()[0]

    # Distinct films in PLANNED
    planned_films = conn.execute(
        "SELECT COUNT(DISTINCT film_key) FROM prediction_snapshot WHERE prediction_state = 'PLANNED'"
    ).fetchone()[0]

    # Distinct films in all states
    all_films = conn.execute(
        "SELECT COUNT(DISTINCT film_key) FROM prediction_snapshot"
    ).fetchone()[0]

    # Feature snapshot totals
    feat_total = conn.execute(
        "SELECT COUNT(*) FROM qloo_feature_snapshot"
    ).fetchone()[0]
    feat_distinct = conn.execute(
        "SELECT COUNT(DISTINCT film_key) FROM qloo_feature_snapshot"
    ).fetchone()[0]

    # ====================================================================
    # A. FILM RESOLUTION COVERAGE
    # Denominator: distinct PLANNED films
    # Numerator: those with a qloo_entity_id in film_resolution
    # Unit: canonical films
    # Temporal rule: none (resolution is static)
    # ====================================================================
    films_with_entity = conn.execute("""
        SELECT COUNT(DISTINCT p.film_key)
        FROM prediction_snapshot p
        JOIN film_resolution fr ON p.film_key = fr.film_key
        WHERE p.prediction_state = 'PLANNED'
        AND fr.qloo_entity_id IS NOT NULL
    """).fetchone()[0]

    films_no_entity = planned_films - films_with_entity

    resolution_coverage = {
        "metric": "A_FILM_RESOLUTION_COVERAGE",
        "denominator": planned_films,
        "numerator": films_with_entity,
        "pct": round(films_with_entity / planned_films * 100, 1) if planned_films else 0,
        "unit": "distinct_planned_films",
        "temporal_rule": "none",
        "detail": f"{films_with_entity} of {planned_films} PLANNED films have a Qloo entity_id",
    }

    # ====================================================================
    # B. SNAPSHOT EXISTENCE COVERAGE
    # Denominator: distinct PLANNED films
    # Numerator: those with at least one feature snapshot (any quality)
    # Unit: canonical films
    # ====================================================================
    films_with_snapshot = conn.execute("""
        SELECT COUNT(DISTINCT p.film_key)
        FROM prediction_snapshot p
        WHERE p.prediction_state = 'PLANNED'
        AND EXISTS (
            SELECT 1 FROM qloo_feature_snapshot q WHERE q.film_key = p.film_key
        )
    """).fetchone()[0]

    snapshot_coverage = {
        "metric": "B_SNAPSHOT_EXISTENCE_COVERAGE",
        "denominator": planned_films,
        "numerator": films_with_snapshot,
        "pct": round(films_with_snapshot / planned_films * 100, 1) if planned_films else 0,
        "unit": "distinct_planned_films",
        "temporal_rule": "none",
        "detail": f"{films_with_snapshot} of {planned_films} PLANNED films have at least one snapshot row",
    }

    # ====================================================================
    # C. PREDICTION-TIME TEMPORAL COVERAGE
    # Denominator: PLANNED prediction records
    # Numerator: those with a feature snapshot retrieved_at <= prediction_timestamp
    # Unit: prediction snapshots
    # Temporal rule: feature.retrieved_at <= prediction.prediction_timestamp
    # ====================================================================
    temporal_eligible = conn.execute("""
        SELECT COUNT(DISTINCT p.prediction_id)
        FROM prediction_snapshot p
        JOIN qloo_feature_snapshot q ON p.film_key = q.film_key
        WHERE p.prediction_state = 'PLANNED'
        AND q.retrieved_at <= p.prediction_timestamp
    """).fetchone()[0]

    temporal_coverage = {
        "metric": "C_PREDICTION_TIME_TEMPORAL_COVERAGE",
        "denominator": planned_count,
        "numerator": temporal_eligible,
        "pct": round(temporal_eligible / planned_count * 100, 2) if planned_count else 0,
        "unit": "planned_prediction_snapshots",
        "temporal_rule": "feature.retrieved_at <= prediction.prediction_timestamp",
        "detail": f"{temporal_eligible} of {planned_count} PLANNED predictions have a temporally eligible snapshot",
    }

    # ====================================================================
    # D. USABLE FEATURE COVERAGE
    # Denominator: PLANNED prediction records
    # Numerator: those with non-empty, temporally eligible feature tags
    # Unit: prediction snapshots
    # Temporal rule: feature.retrieved_at <= prediction.prediction_timestamp
    # ====================================================================
    usable_features = conn.execute("""
        SELECT COUNT(DISTINCT p.prediction_id)
        FROM prediction_snapshot p
        JOIN qloo_feature_snapshot q ON p.film_key = q.film_key
        WHERE p.prediction_state = 'PLANNED'
        AND q.candidate_tags IS NOT NULL
        AND q.candidate_tags != '[]'
        AND q.retrieved_at <= p.prediction_timestamp
    """).fetchone()[0]

    usable_coverage = {
        "metric": "D_USABLE_FEATURE_COVERAGE",
        "denominator": planned_count,
        "numerator": usable_features,
        "pct": round(usable_features / planned_count * 100, 2) if planned_count else 0,
        "unit": "planned_prediction_snapshots",
        "temporal_rule": "feature.retrieved_at <= prediction.prediction_timestamp AND non-empty tags",
        "detail": f"{usable_features} of {planned_count} PLANNED predictions have temporally eligible non-empty features",
    }

    # Film-level usable
    usable_films = conn.execute("""
        SELECT COUNT(DISTINCT q.film_key)
        FROM qloo_feature_snapshot q
        WHERE q.candidate_tags IS NOT NULL
        AND q.candidate_tags != '[]'
        AND EXISTS (
            SELECT 1 FROM prediction_snapshot p
            WHERE p.film_key = q.film_key AND p.prediction_state = 'PLANNED'
        )
    """).fetchone()[0]

    usable_film_coverage = {
        "metric": "D2_USABLE_FEATURE_COVERAGE_FILM_LEVEL",
        "denominator": planned_films,
        "numerator": usable_films,
        "pct": round(usable_films / planned_films * 100, 1) if planned_films else 0,
        "unit": "distinct_planned_films",
        "temporal_rule": "has non-empty tags (film level)",
        "detail": f"{usable_films} of {planned_films} PLANNED films have at least one non-empty feature snapshot",
    }

    # ====================================================================
    # E. EMPTY-SIGNAL COVERAGE
    # Films with resolved entity but empty API response
    # ====================================================================
    empty_signal = conn.execute("""
        SELECT COUNT(DISTINCT q.film_key)
        FROM qloo_feature_snapshot q
        WHERE (q.candidate_tags = '[]' OR q.candidate_tags IS NULL)
        AND EXISTS (
            SELECT 1 FROM prediction_snapshot p
            WHERE p.film_key = q.film_key AND p.prediction_state = 'PLANNED'
        )
    """).fetchone()[0]

    empty_signal_coverage = {
        "metric": "E_EMPTY_SIGNAL_COVERAGE",
        "numerator": empty_signal,
        "unit": "distinct_planned_films",
        "detail": f"{empty_signal} PLANNED films have snapshots with empty tags (API returned no signal)",
    }

    # ====================================================================
    # F. RETROSPECTIVE-ONLY COVERAGE
    # Predictions frozen with retrospective metadata, not prediction-time features
    # ====================================================================
    retro_only = conn.execute("""
        SELECT COUNT(*) FROM prediction_snapshot
        WHERE prediction_state IN ('FROZEN', 'OUTCOME_FINAL')
        AND qloo_feature_status = 'RETROSPECTIVE_ONLY'
    """).fetchone()[0]

    retro_coverage = {
        "metric": "F_RETROSPECTIVE_ONLY",
        "numerator": retro_only,
        "unit": "frozen_and_outcome_predictions",
        "detail": f"{retro_only} frozen/outcome predictions have RETROSPECTIVE_ONLY status",
    }

    # ====================================================================
    # G. NO-RESOLUTION / NO-FEATURE
    # ====================================================================
    no_resolution = conn.execute("""
        SELECT COUNT(DISTINCT p.film_key)
        FROM prediction_snapshot p
        WHERE p.prediction_state = 'PLANNED'
        AND NOT EXISTS (
            SELECT 1 FROM film_resolution fr
            WHERE fr.film_key = p.film_key AND fr.qloo_entity_id IS NOT NULL
        )
    """).fetchone()[0]

    no_feature_coverage = {
        "metric": "G_NO_RESOLUTION",
        "numerator": no_resolution,
        "denominator": planned_films,
        "unit": "distinct_planned_films",
        "detail": f"{no_resolution} PLANNED films have no resolvable Qloo entity",
    }

    # ====================================================================
    # Outcome audit
    # ====================================================================
    outcome_stats = conn.execute("""
        SELECT outcome_status, COUNT(*) FROM prediction_snapshot
        WHERE prediction_state = 'OUTCOME_FINAL'
        GROUP BY outcome_status
    """).fetchall()
    outcome_dict = {r[0]: r[1] for r in outcome_stats}

    frozen_qloo_status = conn.execute("""
        SELECT qloo_feature_status, COUNT(*) FROM prediction_snapshot
        WHERE prediction_state = 'FROZEN'
        GROUP BY qloo_feature_status
    """).fetchall()
    frozen_qloo_dict = {r[0]: r[1] for r in frozen_qloo_status}

    # AVAILABLE_AT_PREDICTION_TIME with actual signal
    available_with_signal = conn.execute("""
        SELECT COUNT(*)
        FROM prediction_snapshot p
        JOIN qloo_feature_snapshot q ON p.film_key = q.film_key
        WHERE p.prediction_state = 'FROZEN'
        AND p.qloo_feature_status = 'AVAILABLE_AT_PREDICTION_TIME'
        AND q.candidate_tags IS NOT NULL
        AND q.candidate_tags != '[]'
    """).fetchone()[0]

    available_without_signal = frozen_qloo_dict.get('AVAILABLE_AT_PREDICTION_TIME', 0) - available_with_signal

    # ====================================================================
    # Reconciliation
    # ====================================================================
    reconciliation = {
        "planned_films": planned_films,
        "films_with_entity": films_with_entity,
        "films_no_entity": films_no_entity,
        "films_with_snapshot": films_with_snapshot,
        "films_with_entity_no_snapshot": films_with_entity - films_with_snapshot,
        "usable_signal_films": usable_films,
        "empty_signal_films": empty_signal,
        "no_resolution_films": no_resolution,
        "sum_check": films_no_entity + usable_films + empty_signal,
        "equals_planned": films_no_entity + usable_films + empty_signal == planned_films,
    }

    # ====================================================================
    # Defect summary
    # ====================================================================
    defects = []

    # Defect 1: Coverage inflation
    if snapshot_coverage["pct"] > usable_coverage["pct"] * 2:
        defects.append({
            "id": "D1_COVERAGE_INFLATION",
            "severity": "HIGH",
            "description": (
                f"Snapshot existence ({snapshot_coverage['pct']}%) reported as feature coverage "
                f"when usable signal is only {usable_coverage['pct']}%"
            ),
        })

    # Defect 2: Empty snapshots (code fixed in M13.6.4, existing snapshots remain)
    if empty_signal > 0:
        defects.append({
            "id": "D2_EMPTY_SNAPSHOTS_EXIST",
            "severity": "LOW",
            "description": (
                f"{empty_signal} films have empty feature snapshots. "
                f"Code fix in M13.6.4: collector now allows re-collection for empty snapshots. "
                f"Existing empty rows remain in DB as provenance records."
            ),
        })

    # Defect 3: AVAILABLE_AT_PREDICTION_TIME without signal
    if available_without_signal > 0:
        defects.append({
            "id": "D3_MISLEADING_FEATURE_STATUS",
            "severity": "HIGH",
            "description": (
                f"{available_without_signal} FROZEN predictions are marked "
                f"AVAILABLE_AT_PREDICTION_TIME but have zero Qloo tags"
            ),
        })

    # Defect 4: All outcomes positive-only
    if outcome_dict.get("SOLD_OUT_OBSERVED", 0) > 0 and outcome_dict.get("AVAILABLE_NEAR_SHOWTIME", 0) == 0:
        defects.append({
            "id": "D4_POSITIVE_ONLY_OUTCOMES",
            "severity": "HIGH",
            "description": (
                f"All {outcome_dict.get('SOLD_OUT_OBSERVED', 0)} linked outcomes are "
                f"SOLD_OUT_OBSERVED with zero AVAILABLE_NEAR_SHOWTIME labels. "
                f"Severe selection bias: only observable sold-out events were linked."
            ),
        })

    # Defect 5: Popularity sourced from retrospective data
    retro_pop = conn.execute("""
        SELECT COUNT(*) FROM qloo_feature_snapshot
        WHERE qloo_popularity IS NOT NULL
        AND (candidate_tags = '[]' OR candidate_tags IS NULL)
    """).fetchone()[0]
    if retro_pop > 0:
        defects.append({
            "id": "D5_RETROSPECTIVE_POPULARITY",
            "severity": "MEDIUM",
            "description": (
                f"{retro_pop} feature snapshots have popularity values sourced from "
                f"film_resolution (retrospective metadata) rather than the API response"
            ),
        })

    return {
        "audit_version": "M13.6.4",
        "db_totals": {
            "total_predictions": total_predictions,
            "planned": planned_count,
            "frozen": frozen_count,
            "outcome_final": outcome_final_count,
            "censored": censored_count,
            "distinct_planned_films": planned_films,
            "distinct_all_films": all_films,
            "feature_snapshots_total": feat_total,
            "feature_snapshots_distinct_films": feat_distinct,
        },
        "coverage_metrics": {
            "A_film_resolution": resolution_coverage,
            "B_snapshot_existence": snapshot_coverage,
            "C_temporal_eligibility": temporal_coverage,
            "D_usable_features": usable_coverage,
            "D2_usable_features_film": usable_film_coverage,
            "E_empty_signal": empty_signal_coverage,
            "F_retrospective_only": retro_coverage,
            "G_no_resolution": no_feature_coverage,
        },
        "outcome_audit": {
            "outcome_status_distribution": outcome_dict,
            "frozen_qloo_status_distribution": frozen_qloo_dict,
            "available_at_pred_time_with_signal": available_with_signal,
            "available_at_pred_time_without_signal": available_without_signal,
        },
        "reconciliation": reconciliation,
        "defects": defects,
        "all_planned_films_count": planned_films,
    }


def main():
    parser = argparse.ArgumentParser(description="M13.6.4 Coverage Audit")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    db_path = ROOT / "data" / "processed" / "outcome_ledger.db"
    conn = sqlite3.connect(str(db_path))

    audit = run_audit(conn)
    conn.close()

    if args.json:
        print(json.dumps(audit, indent=2, default=str))
        return

    # Pretty print
    print("=" * 72)
    print("M13.6.4: DETERMINISTIC COVERAGE & INTEGRITY AUDIT")
    print("=" * 72)

    db = audit["db_totals"]
    print(f"\n--- DATABASE TOTALS ---")
    print(f"  Total predictions:        {db['total_predictions']}")
    print(f"  PLANNED:                  {db['planned']}")
    print(f"  FROZEN:                   {db['frozen']}")
    print(f"  OUTCOME_FINAL:            {db['outcome_final']}")
    print(f"  CENSORED:                 {db['censored']}")
    print(f"  Distinct PLANNED films:   {db['distinct_planned_films']}")
    print(f"  Feature snapshots:        {db['feature_snapshots_total']} total, {db['feature_snapshots_distinct_films']} distinct films")

    print(f"\n--- COVERAGE METRICS ---")
    for key, m in audit["coverage_metrics"].items():
        denom = m.get("denominator", "N/A")
        numer = m.get("numerator", 0)
        pct = m.get("pct", "N/A")
        pct_str = f"{pct}%" if pct != "N/A" else "N/A"
        print(f"  {m['metric']:<50} {numer:>5}/{denom:<5} = {pct_str:>7}  [{m['unit']}]")
        print(f"    {m['detail']}")

    rec = audit["reconciliation"]
    print(f"\n--- RECONCILIATION ---")
    print(f"  PLANNED films:              {rec['planned_films']}")
    print(f"  - No entity:                {rec['films_no_entity']}")
    print(f"  - Has entity:               {rec['films_with_entity']}")
    print(f"    - With snapshot:          {rec['films_with_snapshot']}")
    print(f"    - With usable signal:     {rec['usable_signal_films']}")
    print(f"    - Empty signal only:      {rec['empty_signal_films']}")
    print(f"  SUM CHECK: {rec['films_no_entity']} + {rec['usable_signal_films']} + {rec['empty_signal_films']} = {rec['sum_check']} {'✅' if rec['equals_planned'] else '❌ MISMATCH'}")

    oa = audit["outcome_audit"]
    print(f"\n--- OUTCOME AUDIT ---")
    print(f"  Outcome statuses: {oa['outcome_status_distribution']}")
    print(f"  FROZEN Qloo status: {oa['frozen_qloo_status_distribution']}")
    print(f"  AVAILABLE_AT_PRED_TIME with signal:    {oa['available_at_pred_time_with_signal']}")
    print(f"  AVAILABLE_AT_PRED_TIME without signal: {oa['available_at_pred_time_without_signal']}")

    print(f"\n--- CONFIRMED DEFECTS ---")
    for d in audit["defects"]:
        print(f"  [{d['severity']}] {d['id']}: {d['description']}")

    if not audit["defects"]:
        print("  None found.")

    print()


if __name__ == "__main__":
    main()
