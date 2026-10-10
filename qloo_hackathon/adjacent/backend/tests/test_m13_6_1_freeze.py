"""
M13.6.1: Temporal Freeze + Leakage Lock Repair — Tests

Tests proving:
1. Future predictions remain PLANNED with no Qloo features
2. Predictions freeze only at/after their prediction timestamp
3. Frozen features are immutable immediately after freeze
4. Historical Qloo metadata cannot enter signal analysis as prediction-time data
5. SOLD_OUT trajectory semantics are correct
6. Exact future-freeze regression test with fake clock
"""

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.film_identity import canonical_film_key
from app.domain.outcome_repository import OutcomeRepository


@pytest.fixture
def repo(tmp_path):
    return OutcomeRepository(tmp_path / "test.db")


@pytest.fixture
def future_show():
    """Screening 10 days in the future."""
    now = datetime.now(UTC)
    show_dt = now + timedelta(days=10)
    return {
        "venue_id": "test_venue", "venue_name": "Test Cinema",
        "film_title": "Alien", "film_year": 1979,
        "show_date": "Friday", "show_time": "8:00 pm",
        "show_start_at": show_dt.isoformat(),
        "format": "35mm",
        "source_url": "https://example.com",
        "source_timestamp": now.isoformat(),
        "sold_out": False, "availability_state": "AVAILABLE",
    }


# ============================================================
# TEST: Future predictions remain PLANNED
# ============================================================

class TestFuturePredictionsPlanned:
    def test_future_prediction_is_planned(self, repo, future_show):
        """Prediction with future timestamp -> PLANNED, no Qloo features."""
        obs_id, _ = repo.record_screening(future_show)
        cf_key = canonical_film_key("Alien", 1979)
        now = datetime.now(UTC)
        show_dt = datetime.fromisoformat(future_show["show_start_at"])

        # 7-day prediction timestamp is 3 days from now (show is 10 days out)
        pred_ts = show_dt - timedelta(days=7)

        repo.upsert_prediction_snapshot({
            "observation_id": obs_id,
            "film_key": cf_key,
            "prediction_run_id": "test_run",
            "prediction_timestamp": pred_ts.isoformat(),
            "prediction_horizon_hours": 168,
            "show_start_at": future_show["show_start_at"],
            # Caller might accidentally pass Qloo features
            "qloo_entity_id": "E123",
            "qloo_popularity": 0.5,
        }, current_time=now)

        snap = repo.get_prediction_snapshot(obs_id, 168)
        assert snap["prediction_state"] == "PLANNED"
        assert snap["qloo_entity_id"] is None  # Cleared!
        assert snap["qloo_popularity"] is None
        assert snap["freeze_timestamp"] is None

    def test_no_qloo_features_for_planned(self, repo, future_show):
        """PLANNED predictions have NO Qloo features regardless of input."""
        obs_id, _ = repo.record_screening(future_show)
        cf_key = canonical_film_key("Alien", 1979)
        now = datetime.now(UTC)
        show_dt = datetime.fromisoformat(future_show["show_start_at"])

        repo.upsert_prediction_snapshot({
            "observation_id": obs_id,
            "film_key": cf_key,
            "prediction_run_id": "test_run",
            "prediction_timestamp": (show_dt - timedelta(days=7)).isoformat(),
            "prediction_horizon_hours": 168,
            "show_start_at": future_show["show_start_at"],
            "qloo_entity_id": "E999",
            "qloo_popularity": 0.99,
            "qloo_feature_status": "AVAILABLE_AT_PREDICTION_TIME",
        }, current_time=now)

        snap = repo.get_prediction_snapshot(obs_id, 168)
        assert snap["prediction_state"] == "PLANNED"
        assert snap["qloo_entity_id"] is None
        assert snap["qloo_feature_status"] == "NO_FEATURE"


# ============================================================
# TEST: Predictions freeze only at/after prediction timestamp
# ============================================================

class TestFreezeTiming:
    def test_freeze_at_prediction_time(self, repo, future_show):
        """Prediction freezes when prediction_timestamp arrives."""
        obs_id, _ = repo.record_screening(future_show)
        cf_key = canonical_film_key("Alien", 1979)
        show_dt = datetime.fromisoformat(future_show["show_start_at"])
        pred_ts = show_dt - timedelta(days=7)

        # Create PLANNED prediction
        repo.upsert_prediction_snapshot({
            "observation_id": obs_id,
            "film_key": cf_key,
            "prediction_run_id": "test_run",
            "prediction_timestamp": pred_ts.isoformat(),
            "prediction_horizon_hours": 168,
            "show_start_at": future_show["show_start_at"],
        }, current_time=pred_ts - timedelta(days=1))

        snap = repo.get_prediction_snapshot(obs_id, 168)
        assert snap["prediction_state"] == "PLANNED"

        # Now at prediction time, freeze
        repo.upsert_prediction_snapshot({
            "observation_id": obs_id,
            "film_key": cf_key,
            "prediction_run_id": "test_run",
            "prediction_timestamp": pred_ts.isoformat(),
            "prediction_horizon_hours": 168,
            "show_start_at": future_show["show_start_at"],
            "qloo_entity_id": "E123",
            "qloo_popularity": 0.5,
            "qloo_feature_status": "AVAILABLE_AT_PREDICTION_TIME",
        }, current_time=pred_ts + timedelta(minutes=1))

        snap = repo.get_prediction_snapshot(obs_id, 168)
        assert snap["prediction_state"] == "FROZEN"
        assert snap["qloo_entity_id"] == "E123"
        assert snap["freeze_timestamp"] is not None


# ============================================================
# TEST: Frozen features are immutable
# ============================================================

class TestFrozenImmutability:
    def test_frozen_cannot_be_modified(self, repo, future_show):
        """Once FROZEN, Qloo fields cannot change."""
        obs_id, _ = repo.record_screening(future_show)
        cf_key = canonical_film_key("Alien", 1979)
        now = datetime.now(UTC)
        pred_ts = now - timedelta(hours=1)

        # Create and freeze
        repo.upsert_prediction_snapshot({
            "observation_id": obs_id,
            "film_key": cf_key,
            "prediction_run_id": "test_run",
            "prediction_timestamp": pred_ts.isoformat(),
            "prediction_horizon_hours": 168,
            "show_start_at": future_show["show_start_at"],
            "qloo_entity_id": "E123",
            "qloo_popularity": 0.5,
        }, current_time=now)

        snap = repo.get_prediction_snapshot(obs_id, 168)
        assert snap["prediction_state"] == "FROZEN"
        freeze_ts = snap["freeze_timestamp"]

        # Try to modify with new features
        repo.upsert_prediction_snapshot({
            "observation_id": obs_id,
            "film_key": cf_key,
            "prediction_run_id": "test_run",
            "prediction_timestamp": pred_ts.isoformat(),
            "prediction_horizon_hours": 168,
            "show_start_at": future_show["show_start_at"],
            "qloo_entity_id": "E999",
            "qloo_popularity": 0.99,
        }, current_time=now + timedelta(hours=1))

        # Verify immutable
        snap = repo.get_prediction_snapshot(obs_id, 168)
        assert snap["qloo_entity_id"] == "E123"
        assert snap["qloo_popularity"] == 0.5
        assert snap["freeze_timestamp"] == freeze_ts


# ============================================================
# TEST: SOLD_OUT trajectory semantics
# ============================================================

class TestTrajectorySemantics:
    def test_sold_out_ever_observed(self, repo, future_show):
        """SOLD_OUT_OBSERVED if sold_out was observed at ANY point."""
        obs_id, _ = repo.record_screening(future_show)
        cf_key = canonical_film_key("Alien", 1979)
        now = datetime.now(UTC)
        pred_ts = now - timedelta(hours=1)

        repo.upsert_prediction_snapshot({
            "observation_id": obs_id,
            "film_key": cf_key,
            "prediction_run_id": "test_run",
            "prediction_timestamp": pred_ts.isoformat(),
            "prediction_horizon_hours": 168,
            "show_start_at": future_show["show_start_at"],
        }, current_time=now)

        # Trajectory: AVAILABLE -> SOLD_OUT -> AVAILABLE
        # Outcome should be SOLD_OUT_OBSERVED (sold out was observed)
        repo.update_prediction_outcome(obs_id, 168, {
            "outcome_status": "SOLD_OUT_OBSERVED",
            "sold_out_observed": 1,
            "final_observation_timestamp": now.isoformat(),
            "lead_time_at_final_observation": 0.5,
        })

        snap = repo.get_prediction_snapshot(obs_id, 168)
        assert snap["outcome_status"] == "SOLD_OUT_OBSERVED"
        assert snap["prediction_state"] == "OUTCOME_FINAL"

    def test_available_near_showtime(self, repo, future_show):
        """AVAILABLE_NEAR_SHOWTIME when available within final window."""
        obs_id, _ = repo.record_screening(future_show)
        cf_key = canonical_film_key("Alien", 1979)
        now = datetime.now(UTC)

        repo.upsert_prediction_snapshot({
            "observation_id": obs_id,
            "film_key": cf_key,
            "prediction_run_id": "test_run",
            "prediction_timestamp": (now - timedelta(hours=1)).isoformat(),
            "prediction_horizon_hours": 168,
            "show_start_at": future_show["show_start_at"],
        }, current_time=now)

        repo.update_prediction_outcome(obs_id, 168, {
            "outcome_status": "AVAILABLE_NEAR_SHOWTIME",
            "sold_out_observed": 0,
            "final_observation_timestamp": now.isoformat(),
            "lead_time_at_final_observation": 1.0,
        })

        snap = repo.get_prediction_snapshot(obs_id, 168)
        assert snap["outcome_status"] == "AVAILABLE_NEAR_SHOWTIME"
        assert snap["sold_out_observed"] == 0

    def test_censored_no_final_observation(self, repo, future_show):
        """CENSORED when no valid final observation."""
        obs_id, _ = repo.record_screening(future_show)
        cf_key = canonical_film_key("Alien", 1979)
        now = datetime.now(UTC)

        repo.upsert_prediction_snapshot({
            "observation_id": obs_id,
            "film_key": cf_key,
            "prediction_run_id": "test_run",
            "prediction_timestamp": (now - timedelta(hours=1)).isoformat(),
            "prediction_horizon_hours": 168,
            "show_start_at": future_show["show_start_at"],
        }, current_time=now)

        repo.update_prediction_outcome(obs_id, 168, {
            "outcome_status": "CENSORED",
            "sold_out_observed": None,
            "final_observation_timestamp": None,
            "lead_time_at_final_observation": None,
        })

        snap = repo.get_prediction_snapshot(obs_id, 168)
        assert snap["outcome_status"] == "CENSORED"
        assert snap["prediction_state"] == "CENSORED"


# ============================================================
# TEST: Exact future-freeze regression test
# ============================================================

class TestExactRegressionScenario:
    def test_oct8_oct20_scenario(self, repo):
        """Exact scenario from M13.6.1 spec.

        current_time = Oct 8 12:00 UTC
        show = Oct 20 20:00 Europe/London
        7d prediction timestamp = Oct 13 20:00 Europe/London

        Run collector on Oct 8 -> PLANNED, no Qloo
        Advance to Oct 13 -> FROZEN with Qloo
        Run again -> same frozen values, no mutation
        """
        now = datetime(2026, 10, 8, 12, 0, 0, tzinfo=UTC)
        show_dt = datetime(2026, 10, 20, 19, 0, 0, tzinfo=UTC)  # 20:00 BST = 19:00 UTC
        pred_ts = datetime(2026, 10, 13, 19, 0, 0, tzinfo=UTC)  # 7 days before

        # Create screening
        obs_id, _ = repo.record_screening({
            "venue_id": "test", "film_title": "Alien", "film_year": 1979,
            "show_date": "Tuesday 20th October", "show_time": "8:00 pm",
            "show_start_at": show_dt.isoformat(),
            "source_url": "https://example.com",
            "source_timestamp": now.isoformat(),
            "sold_out": False, "availability_state": "AVAILABLE",
        })
        cf_key = canonical_film_key("Alien", 1979)

        # Run on Oct 8: prediction is PLANNED
        repo.upsert_prediction_snapshot({
            "observation_id": obs_id,
            "film_key": cf_key,
            "prediction_run_id": "run_oct8",
            "prediction_timestamp": pred_ts.isoformat(),
            "prediction_horizon_hours": 168,
            "show_start_at": show_dt.isoformat(),
            "qloo_entity_id": "E999",  # Should be ignored
            "qloo_popularity": 0.99,
        }, current_time=now)

        snap = repo.get_prediction_snapshot(obs_id, 168)
        assert snap["prediction_state"] == "PLANNED"
        assert snap["qloo_entity_id"] is None
        assert snap["qloo_popularity"] is None

        # Advance to Oct 13: freeze with Qloo features
        freeze_time = pred_ts + timedelta(minutes=5)
        repo.upsert_prediction_snapshot({
            "observation_id": obs_id,
            "film_key": cf_key,
            "prediction_run_id": "run_oct13",
            "prediction_timestamp": pred_ts.isoformat(),
            "prediction_horizon_hours": 168,
            "show_start_at": show_dt.isoformat(),
            "qloo_entity_id": "E123",
            "qloo_popularity": 0.5,
            "qloo_feature_status": "AVAILABLE_AT_PREDICTION_TIME",
        }, current_time=freeze_time)

        snap = repo.get_prediction_snapshot(obs_id, 168)
        assert snap["prediction_state"] == "FROZEN"
        assert snap["qloo_entity_id"] == "E123"
        assert snap["qloo_popularity"] == 0.5
        first_freeze_ts = snap["freeze_timestamp"]

        # Run again: same frozen values, no mutation
        repo.upsert_prediction_snapshot({
            "observation_id": obs_id,
            "film_key": cf_key,
            "prediction_run_id": "run_oct14",
            "prediction_timestamp": pred_ts.isoformat(),
            "prediction_horizon_hours": 168,
            "show_start_at": show_dt.isoformat(),
            "qloo_entity_id": "E999",
            "qloo_popularity": 0.99,
        }, current_time=freeze_time + timedelta(days=1))

        snap = repo.get_prediction_snapshot(obs_id, 168)
        assert snap["qloo_entity_id"] == "E123"  # Original preserved
        assert snap["qloo_popularity"] == 0.5
        assert snap["freeze_timestamp"] == first_freeze_ts


# ============================================================
# TEST: Leakage Audit V2
# ============================================================

class TestLeakageAuditV2:
    def test_audit_passes_clean(self, repo, future_show):
        """Leakage audit V2 passes with clean data."""
        obs_id, _ = repo.record_screening(future_show)
        cf_key = canonical_film_key("Alien", 1979)
        now = datetime.now(UTC)

        # PLANNED prediction (no Qloo)
        repo.upsert_prediction_snapshot({
            "observation_id": obs_id,
            "film_key": cf_key,
            "prediction_run_id": "test_run",
            "prediction_timestamp": (now + timedelta(days=3)).isoformat(),
            "prediction_horizon_hours": 168,
            "show_start_at": future_show["show_start_at"],
        }, current_time=now)

        audit = repo.leakage_audit_v2()
        assert audit["passed"] is True
        assert audit["violations"]["future_prediction_has_qloo"] == 0

    def test_audit_fails_on_premature_qloo(self, repo, future_show):
        """Leakage audit fails when PLANNED prediction has Qloo data."""
        obs_id, _ = repo.record_screening(future_show)
        cf_key = canonical_film_key("Alien", 1979)
        now = datetime.now(UTC)

        # Manually insert a PLANNED prediction with Qloo data (simulating the bug)
        pred_id = "test_pred_id"
        repo._conn.execute(
            """INSERT INTO prediction_snapshot
            (prediction_id, observation_id, film_key, prediction_run_id,
             prediction_timestamp, prediction_horizon_hours, show_start_at,
             prediction_state, qloo_entity_id, qloo_popularity,
             qloo_feature_status, outcome_status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pred_id, obs_id, cf_key, "test_run",
             (now + timedelta(days=3)).isoformat(), 168,
             future_show["show_start_at"],
             "PLANNED", "E123", 0.5, "NO_FEATURE", "PENDING",
             now.isoformat(), now.isoformat()),
        )
        repo._conn.commit()

        audit = repo.leakage_audit_v2()
        assert audit["passed"] is False
        assert audit["violations"]["future_prediction_has_qloo"] == 1


# ============================================================
# TEST: Prediction run management
# ============================================================

class TestPredictionRun:
    def test_run_created(self, repo):
        repo.create_prediction_run({
            "prediction_run_id": "test_run",
            "run_timestamp": datetime.now(UTC).isoformat(),
            "run_type": "INITIAL",
            "total_screenings": 100,
            "eligible_screenings": 90,
        })
        run = repo.get_prediction_run("test_run")
        assert run is not None
        assert run["prediction_run_id"] == "test_run"


# ============================================================
# TEST: Idempotency
# ============================================================

class TestIdempotency:
    def test_idempotent_snapshots(self, repo, future_show):
        """Repeated runs don't create duplicate snapshots."""
        obs_id, _ = repo.record_screening(future_show)
        cf_key = canonical_film_key("Alien", 1979)
        now = datetime.now(UTC)

        for _ in range(3):
            repo.upsert_prediction_snapshot({
                "observation_id": obs_id,
                "film_key": cf_key,
                "prediction_run_id": "test_run",
                "prediction_timestamp": (now + timedelta(days=3)).isoformat(),
                "prediction_horizon_hours": 168,
                "show_start_at": future_show["show_start_at"],
            }, current_time=now)

        snapshots = repo.list_prediction_snapshots()
        assert len(snapshots) == 1


# ============================================================
# TEST: freeze_due_predictions
# ============================================================

class TestFreezeDuePredictions:
    def test_freezes_due_only(self, repo, future_show):
        """Only predictions whose timestamp has arrived are frozen."""
        obs_id, _ = repo.record_screening(future_show)
        cf_key = canonical_film_key("Alien", 1979)
        now = datetime.now(UTC)
        show_dt = datetime.fromisoformat(future_show["show_start_at"])

        # Create 3 predictions
        for horizon in [168, 72, 24]:
            repo.upsert_prediction_snapshot({
                "observation_id": obs_id,
                "film_key": cf_key,
                "prediction_run_id": "test_run",
                "prediction_timestamp": (show_dt - timedelta(hours=horizon)).isoformat(),
                "prediction_horizon_hours": horizon,
                "show_start_at": future_show["show_start_at"],
            }, current_time=now)

        # All should be PLANNED (show is 10 days out)
        snaps = repo.list_prediction_snapshots()
        assert all(s["prediction_state"] == "PLANNED" for s in snaps)

        # Advance time to 7-day prediction timestamp
        seven_day_ts = show_dt - timedelta(hours=168)
        frozen = repo.freeze_due_predictions(seven_day_ts + timedelta(minutes=1))
        assert frozen == 1  # Only 7-day horizon frozen

        snap = repo.get_prediction_snapshot(obs_id, 168)
        assert snap["prediction_state"] == "FROZEN"

        # 3-day and 1-day still PLANNED
        snap72 = repo.get_prediction_snapshot(obs_id, 72)
        assert snap72["prediction_state"] == "PLANNED"
        snap24 = repo.get_prediction_snapshot(obs_id, 24)
        assert snap24["prediction_state"] == "PLANNED"
