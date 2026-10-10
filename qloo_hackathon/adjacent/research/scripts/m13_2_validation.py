"""M13.2: Validation script — evaluation design for when data exists.

This script defines the evaluation pipeline. It does NOT run on
synthetic data. It will run on real outcomes once collected.
"""

import json
from pathlib import Path

adjacent_root = Path(__file__).parent.parent.parent


def define_baselines():
    """Define baseline comparisons for future evaluation."""
    return {
        "B0_venue_history": {
            "description": "Historical sold_out rate at this venue",
            "features": ["venue_historical_sold_out_rate"],
            "type": "binary_classification",
            "note": "Minimum bar — does anything beat the venue's base rate?",
        },
        "B1_film_metadata": {
            "description": "Film metadata only (no Qloo)",
            "features": ["genre", "year", "rating", "director_popularity", "format"],
            "type": "binary_classification",
            "note": "Can standard film features predict sold_out?",
        },
        "B2_qloo_affinity": {
            "description": "Qloo affinity only",
            "features": ["qloo_affinity"],
            "type": "binary_classification",
            "note": "Does Qloo's cultural signal alone predict outcomes?",
        },
        "B3_current_ranker": {
            "description": "Current Adjacent deterministic ranker",
            "features": ["qloo_affinity", "qloo_popularity", "qualifying_ratio"],
            "type": "ranking",
            "note": "Does the current weighted score predict outcomes?",
        },
        "B4_qloo_plus_metadata": {
            "description": "Qloo + film metadata",
            "features": ["qloo_affinity", "qloo_popularity", "genre", "year", "format"],
            "type": "binary_classification",
            "note": "Does Qloo add value beyond metadata?",
        },
    }


def define_metrics():
    """Define evaluation metrics based on target type."""
    return {
        "sold_out_binary": {
            "primary": "PR_AUC",
            "secondary": ["ROC_AUC", "F1", "Precision_at_high_recall"],
            "rationale": "Imbalanced classes — most screenings not sold out",
        },
        "occupancy_rate": {
            "primary": "MAE",
            "secondary": ["RMSE", "R_squared"],
            "rationale": "Continuous target — interpretability matters",
        },
        "ranking": {
            "primary": "NDCG_at_5",
            "secondary": ["Kendall_tau", "Hit_at_5"],
            "rationale": "We care about top-K ranking quality",
        },
    }


def define_leakage_controls():
    """Define leakage prevention rules."""
    return {
        "temporal_split": {
            "description": "Train on earlier dates, test on later dates",
            "rule": "No future information in training set",
        },
        "venue_grouping": {
            "description": "Evaluate per-venue, report macro-averaged",
            "rule": "Venue-level effects don't leak across splits",
        },
        "film_leakage": {
            "description": "Same film can appear in train and test (different screenings)",
            "rule": "But Qloo features must be from prediction-time, not future",
        },
        "qloo_temporal": {
            "description": "Use only Qloo data available at screening time",
            "rule": "No future Qloo popularity or affinity",
        },
    }


def define_readiness_gates():
    """Define gates that must pass before ML training."""
    return {
        "minimum_observations": {
            "description": "Enough observations for meaningful evaluation",
            "threshold": "Not a fixed number — assess based on variance",
            "assessment_factors": [
                "number_of_venues",
                "number_of_screenings",
                "number_of_distinct_films",
                "sold_out_rate",
                "outcome_variance",
                "time_coverage",
            ],
        },
        "target_variance": {
            "description": "Meaningful variation in target variable",
            "threshold": "sold_out rate between 5% and 50%",
            "note": "If <5% sold out, too rare. If >50%, too common.",
        },
        "venue_diversity": {
            "description": "Multiple venues to avoid venue-specific bias",
            "threshold": "At least 2 distinct venues",
        },
        "temporal_coverage": {
            "description": "Enough time to capture seasonal effects",
            "threshold": "At least 3 months of data",
        },
    }


def generate_benchmark_schema():
    """Define the benchmark observation schema."""
    return {
        "event_id": "string — unique event identifier",
        "venue_id": "string — venue identifier",
        "venue_name": "string — human-readable venue name",
        "city": "string — city name",
        "event_date": "YYYY-MM-DD",
        "film_id": "string — film identifier",
        "film_title": "string — human-readable film title",
        "film_year": "int — release year",
        "imdb_id": "string — IMDB ID if available (NULL if not)",
        "qloo_entity_id": "string — Qloo entity ID if resolved (NULL if not)",
        "domain": "string — film, tv_show, artist, etc.",
        "event_type": "string — screening, themed_season, etc.",
        "format": "string — 35mm, 4K, DCP, etc.",
        "capacity": "int — venue capacity (NULL if unavailable)",
        "tickets_sold": "int — actual tickets sold (NULL if unavailable)",
        "occupancy_rate": "float — tickets/capacity (NULL if unavailable)",
        "sold_out": "bool — venue reported sold out (NULL if not observed)",
        "ticket_price": "float — price (NULL if unavailable)",
        "qloo_affinity": "float — Qloo affinity at prediction time (NULL if unavailable)",
        "qloo_popularity": "float — Qloo popularity at prediction time (NULL if unavailable)",
        "qloo_evidence_score": "float — Adjacent evidence score (NULL if unavailable)",
        "recommendation_rank": "int — Adjacent rank (NULL if not recommended)",
        "source": "string — data source",
        "join_status": "VERIFIED | AMBIGUOUS | MISMATCH | UNRESOLVED",
        "label_quality": "DIRECT_OUTCOME | STRONG_PROXY | WEAK_PROXY | UNAVAILABLE",
        "provenance": "string — how this record was obtained",
    }


if __name__ == "__main__":
    baselines = define_baselines()
    metrics = define_metrics()
    leakage = define_leakage_controls()
    gates = define_readiness_gates()
    schema = generate_benchmark_schema()

    output = {
        "version": "M13.2",
        "baselines": baselines,
        "metrics": metrics,
        "leakage_controls": leakage,
        "readiness_gates": gates,
        "benchmark_schema": schema,
        "status": "DESIGN_ONLY — no real data to evaluate yet",
        "ml_readiness": "NOT_ML_READY",
    }

    output_path = adjacent_root / "data" / "processed" / "m13_2_validation_design.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))
    print(f"Validation design saved to: {output_path}")

    print("\n=== M13.2 VALIDATION DESIGN ===")
    print(f"Baselines defined: {len(baselines)}")
    print(f"Metric groups defined: {len(metrics)}")
    print(f"Leakage controls: {len(leakage)}")
    print(f"Readiness gates: {len(gates)}")
    print(f"Schema fields: {len(schema)}")
    print(f"\nML readiness: NOT_ML_READY")
    print(f"Reason: 0 outcome observations available")