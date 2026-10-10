"""
M13.4: Temporal Qloo Join & Leakage-Safe Proxy Benchmark — Tests

Tests proving:
1.  sold_out=True → STRONG_PROXY
2.  sold_out=False → DESCRIPTIVE_ONLY (NOT STRONG_PROXY)
3.  sold_out=None → UNAVAILABLE
4.  tickets_sold → DIRECT_OUTCOME
5.  lead_time calculation is correct
6.  negative lead time rejected (returns negative, bucket = post_show)
7.  timezone conversion is correct
8.  future Qloo feature is excluded
9.  prediction-time Qloo feature is accepted
10. resolution is cached per unique film
11. one Qloo resolution can serve multiple screenings
12. snapshot history preserved
13. AVAILABLE never becomes model target 0 automatically
14. Qloo feature timestamp is preserved
15. provenance required
16. duplicate snapshots remain idempotent
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from app.domain.outcome_repository import (
    OutcomeRepository, _deterministic_obs_id, film_key,
    _model_target, _label_quality_for_sold_out,
    compute_lead_time, lead_time_bucket,
)
from app.collectors.prince_charles import _parse_show_datetime, _is_bst


@pytest.fixture
def repo(tmp_path):
    """Create a temporary repository for testing."""
    db_path = tmp_path / "test_outcome.db"
    return OutcomeRepository(db_path)


@pytest.fixture
def sample_screening():
    return {
        "venue_id": "test_venue",
        "venue_name": "Test Cinema",
        "film_title": "Halloween",
        "film_year": 1978,
        "show_date": "Friday 31st October",
        "show_time": "8:00 pm",
        "show_start_at": "2026-10-31T20:00:00+00:00",
        "format": "35mm",
        "source_url": "https://example.com",
        "source_timestamp": "2026-10-07T20:00:00Z",
        "sold_out": False,
        "availability_state": "AVAILABLE",
    }


# ============================================================
# TEST 1: sold_out=True → STRONG_PROXY
# ============================================================

class TestSoldOutStrongProxy:
    def test_sold_out_true_is_strong_proxy(self, repo, sample_screening):
        """sold_out=True → label_quality=STRONG_PROXY."""
        obs_id, _ = repo.record_screening(sample_screening)
        repo.record_outcome(obs_id, {
            "sold_out": True,
            "measurement_timestamp": "2026-10-08T10:00:00Z",
            "source": "test",
            "provenance": "test",
        })
        outcome = repo.get_outcome(obs_id)
        assert outcome["label_quality"] == "STRONG_PROXY"

    def test_label_quality_function_true(self):
        """_label_quality_for_sold_out(True) == STRONG_PROXY."""
        assert _label_quality_for_sold_out(True) == "STRONG_PROXY"


# ============================================================
# TEST 2: sold_out=False → DESCRIPTIVE_ONLY (NOT STRONG_PROXY)
# ============================================================

class TestAvailableDescriptiveOnly:
    def test_sold_out_false_is_descriptive_only(self, repo, sample_screening):
        """sold_out=False → label_quality=DESCRIPTIVE_ONLY, NOT STRONG_PROXY."""
        obs_id, _ = repo.record_screening(sample_screening)
        repo.record_outcome(obs_id, {
            "sold_out": False,
            "measurement_timestamp": "2026-10-08T10:00:00Z",
            "source": "test",
            "provenance": "test",
        })
        outcome = repo.get_outcome(obs_id)
        assert outcome["label_quality"] == "DESCRIPTIVE_ONLY"
        assert outcome["label_quality"] != "STRONG_PROXY"

    def test_label_quality_function_false(self):
        """_label_quality_for_sold_out(False) == DESCRIPTIVE_ONLY."""
        assert _label_quality_for_sold_out(False) == "DESCRIPTIVE_ONLY"


# ============================================================
# TEST 3: sold_out=None → UNAVAILABLE
# ============================================================

class TestUnknownUnavailable:
    def test_sold_out_none_is_unavailable(self, repo):
        """sold_out=None → label_quality=UNAVAILABLE."""
        screening = {
            "venue_id": "test_venue",
            "film_title": "Unknown Film",
            "show_date": "Monday 1st January",
            "show_time": "7:00 pm",
            "source_url": "https://example.com",
            "source_timestamp": "2026-10-07T20:00:00Z",
            "sold_out": None,
            "availability_state": "UNKNOWN",
        }
        obs_id, _ = repo.record_screening(screening)
        repo.record_outcome(obs_id, {
            "sold_out": None,
            "measurement_timestamp": "2026-10-08T10:00:00Z",
            "source": "test",
            "provenance": "test",
        })
        outcome = repo.get_outcome(obs_id)
        assert outcome["label_quality"] == "UNAVAILABLE"

    def test_label_quality_function_none(self):
        """_label_quality_for_sold_out(None) == UNAVAILABLE."""
        assert _label_quality_for_sold_out(None) == "UNAVAILABLE"


# ============================================================
# TEST 4: tickets_sold → DIRECT_OUTCOME
# ============================================================

class TestTicketsSoldDirectOutcome:
    def test_tickets_sold_overrides_to_direct(self, repo, sample_screening):
        """tickets_sold present → label_quality=DIRECT_OUTCOME regardless of sold_out."""
        obs_id, _ = repo.record_screening(sample_screening)
        repo.record_outcome(obs_id, {
            "sold_out": False,
            "tickets_sold": 150,
            "measurement_timestamp": "2026-10-08T10:00:00Z",
            "source": "test",
            "provenance": "test",
        })
        outcome = repo.get_outcome(obs_id)
        assert outcome["label_quality"] == "DIRECT_OUTCOME"

    def test_occupancy_overrides_to_direct(self, repo, sample_screening):
        """occupancy present → label_quality=DIRECT_OUTCOME."""
        obs_id, _ = repo.record_screening(sample_screening)
        repo.record_outcome(obs_id, {
            "sold_out": False,
            "occupancy": 0.85,
            "measurement_timestamp": "2026-10-08T10:00:00Z",
            "source": "test",
            "provenance": "test",
        })
        outcome = repo.get_outcome(obs_id)
        assert outcome["label_quality"] == "DIRECT_OUTCOME"


# ============================================================
# TEST 5: lead_time calculation is correct
# ============================================================

class TestLeadTimeCalculation:
    def test_lead_time_24_hours(self):
        """24 hours before show → lead_time_hours ≈ 24."""
        show = "2026-10-31T20:00:00+00:00"
        obs = "2026-10-30T20:00:00Z"
        lt = compute_lead_time(show, obs)
        assert lt is not None
        assert abs(lt - 24.0) < 0.01

    def test_lead_time_30_days(self):
        """30 days before show → lead_time_hours ≈ 720."""
        show = "2026-10-31T20:00:00+00:00"
        obs = "2026-10-01T20:00:00Z"
        lt = compute_lead_time(show, obs)
        assert lt is not None
        assert abs(lt - 720.0) < 0.01

    def test_lead_time_none_when_missing(self):
        """None when show_start_at is missing."""
        lt = compute_lead_time(None, "2026-10-07T20:00:00Z")
        assert lt is None

    def test_lead_time_none_when_no_source(self):
        """None when source_timestamp is missing."""
        lt = compute_lead_time("2026-10-31T20:00:00+00:00", None)
        assert lt is None


# ============================================================
# TEST 6: negative lead time identified
# ============================================================

class TestNegativeLeadTime:
    def test_negative_lead_time_detected(self):
        """Post-show observation has negative lead time."""
        show = "2026-10-07T10:00:00+00:00"
        obs = "2026-10-07T20:00:00Z"  # 10 hours after show
        lt = compute_lead_time(show, obs)
        assert lt is not None
        assert lt < 0

    def test_negative_lead_time_bucket_is_post_show(self):
        """Negative lead time → bucket = 'post_show'."""
        assert lead_time_bucket(-10.0) == "post_show"


# ============================================================
# TEST 7: timezone conversion is correct
# ============================================================

class TestTimezoneConversion:
    def test_october_evening_is_bst(self):
        """October 9th 8:20pm is BST (+01:00) in 2026 (before Oct 25)."""
        result = _parse_show_datetime("Friday 9th October", "8:20 pm")
        assert result is not None
        assert "+01:00" in result  # BST
        assert "2026-10-09T20:20:00" in result

    def test_november_evening_is_gmt(self):
        """November 1st is GMT (+00:00)."""
        result = _parse_show_datetime("Sunday 1st November", "3:10 pm")
        assert result is not None
        assert "+00:00" in result  # GMT
        assert "2026-11-01T15:10:00" in result

    def test_noon_pm(self):
        """12:15 pm stays as 12:15 (not 0:15)."""
        result = _parse_show_datetime("Saturday 10th October", "12:15 pm")
        assert result is not None
        assert "T12:15:00" in result

    def test_midnight_am(self):
        """12:00 am becomes 00:00."""
        result = _parse_show_datetime("Monday 1st January", "12:00 am")
        assert result is not None
        assert "T00:00:00" in result

    def test_bst_detection_summer(self):
        """June is BST."""
        dt = datetime(2026, 6, 15, 20, 0)
        assert _is_bst(dt) is True

    def test_bst_detection_winter(self):
        """December is GMT (not BST)."""
        dt = datetime(2026, 12, 15, 20, 0)
        assert _is_bst(dt) is False

    def test_invalid_date_returns_none(self):
        """Unparseable date returns None."""
        result = _parse_show_datetime("Not a date", "8:00 pm")
        assert result is None

    def test_invalid_time_returns_none(self):
        """Unparseable time returns None."""
        result = _parse_show_datetime("Friday 9th October", "noon")
        assert result is None


# ============================================================
# TEST 8: future Qloo feature is excluded
# ============================================================

class TestFutureFeatureExcluded:
    def test_future_feature_excluded_at_prediction_time(self, repo, sample_screening):
        """Qloo feature retrieved AFTER observation is excluded."""
        obs_id, _ = repo.record_screening(sample_screening)
        fk = film_key("Halloween", 1978)

        # Record resolution
        repo.record_film_resolution({
            "film_key": fk,
            "film_title": "Halloween",
            "film_year": 1978,
            "resolution_status": "VERIFIED",
            "qloo_entity_id": "E123",
            "resolution_timestamp": "2026-10-07T20:00:00Z",
        })

        # Feature retrieved AFTER the observation (2026-10-07T20:00:00Z)
        repo.record_qloo_features({
            "film_key": fk,
            "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-08T10:00:00Z",  # AFTER observation
            "qloo_affinity": 0.8,
            "qloo_popularity": 0.5,
        })

        # Get feature with prediction-time constraint
        obs = repo.get_observation(obs_id)
        feature = repo.get_latest_qloo_feature(fk, before=obs["source_timestamp"])
        assert feature is None  # Future feature excluded


# ============================================================
# TEST 9: prediction-time Qloo feature is accepted
# ============================================================

class TestPredictionTimeFeatureAccepted:
    def test_feature_before_observation_is_accepted(self, repo, sample_screening):
        """Qloo feature retrieved BEFORE observation is accepted."""
        obs_id, _ = repo.record_screening(sample_screening)
        fk = film_key("Halloween", 1978)

        repo.record_film_resolution({
            "film_key": fk,
            "film_title": "Halloween",
            "film_year": 1978,
            "resolution_status": "VERIFIED",
            "qloo_entity_id": "E123",
            "resolution_timestamp": "2026-10-06T10:00:00Z",
        })

        # Feature retrieved BEFORE the observation (2026-10-07T20:00:00Z)
        repo.record_qloo_features({
            "film_key": fk,
            "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-07T10:00:00Z",  # BEFORE observation
            "qloo_affinity": 0.8,
            "qloo_popularity": 0.5,
        })

        obs = repo.get_observation(obs_id)
        feature = repo.get_latest_qloo_feature(fk, before=obs["source_timestamp"])
        assert feature is not None
        assert feature["qloo_affinity"] == 0.8


# ============================================================
# TEST 10: resolution is cached per unique film
# ============================================================

class TestResolutionCachedPerFilm:
    def test_same_film_same_resolution(self, repo):
        """Same film (title+year) → same film_key, one resolution."""
        fk1 = film_key("Halloween", 1978)
        fk2 = film_key("Halloween", 1978)
        assert fk1 == fk2

        repo.record_film_resolution({
            "film_key": fk1,
            "film_title": "Halloween",
            "film_year": 1978,
            "resolution_status": "VERIFIED",
            "qloo_entity_id": "E123",
            "resolution_timestamp": "2026-10-07T20:00:00Z",
        })

        res = repo.get_film_resolution(fk2)
        assert res is not None
        assert res["qloo_entity_id"] == "E123"

    def test_different_film_different_resolution(self, repo):
        """Different film → different film_key."""
        fk1 = film_key("Halloween", 1978)
        fk2 = film_key("The Thing", 1982)
        assert fk1 != fk2


# ============================================================
# TEST 11: one Qloo resolution can serve multiple screenings
# ============================================================

class TestResolutionServesMultipleScreenings:
    def test_two_screenings_share_resolution(self, repo):
        """Two screenings of the same film share one resolution."""
        # Screening 1
        s1 = {
            "venue_id": "test_venue", "film_title": "Halloween", "film_year": 1978,
            "show_date": "Friday 31st October", "show_time": "6:00 pm", "format": "35mm",
            "source_url": "https://example.com", "source_timestamp": "2026-10-07T10:00:00Z",
            "sold_out": False, "availability_state": "AVAILABLE",
        }
        # Screening 2 (same film, different time)
        s2 = {
            "venue_id": "test_venue", "film_title": "Halloween", "film_year": 1978,
            "show_date": "Friday 31st October", "show_time": "9:00 pm", "format": "35mm",
            "source_url": "https://example.com", "source_timestamp": "2026-10-07T10:00:00Z",
            "sold_out": True, "availability_state": "SOLD_OUT",
        }

        obs_id1, _ = repo.record_screening(s1)
        obs_id2, _ = repo.record_screening(s2)
        assert obs_id1 != obs_id2  # Different screenings

        # Record resolution once
        repo.record_film_resolution({
            "film_key": film_key("Halloween", 1978),
            "film_title": "Halloween",
            "film_year": 1978,
            "resolution_status": "VERIFIED",
            "qloo_entity_id": "E123",
            "resolution_timestamp": "2026-10-07T10:00:00Z",
        })

        # Both screenings can access the same resolution
        res1 = repo.get_resolution(obs_id1)
        res2 = repo.get_resolution(obs_id2)
        assert res1 is not None
        assert res2 is not None
        assert res1["qloo_entity_id"] == res2["qloo_entity_id"]


# ============================================================
# TEST 12: snapshot history preserved
# ============================================================

class TestSnapshotHistoryPreserved:
    def test_state_change_preserves_all_snapshots(self, repo, sample_screening):
        """Book → Sold Out creates two snapshots, both preserved."""
        obs_id, _ = repo.record_screening(sample_screening)

        sold_screening = {**sample_screening, "sold_out": True,
                          "availability_state": "SOLD_OUT",
                          "source_timestamp": "2026-10-08T10:00:00Z"}
        repo.record_screening(sold_screening)

        snapshots = repo.get_snapshots(obs_id)
        assert len(snapshots) == 2
        assert snapshots[0]["sold_out"] == 0  # First: available
        assert snapshots[1]["sold_out"] == 1  # Second: sold out


# ============================================================
# TEST 13: AVAILABLE never becomes model target 0
# ============================================================

class TestModelTargetNeverZero:
    def test_available_model_target_is_none(self, repo, sample_screening):
        """sold_out=False (AVAILABLE) → model_target=None, NOT 0."""
        obs_id, _ = repo.record_screening(sample_screening)
        obs = repo.get_observation(obs_id)
        assert obs["model_target"] is None

    def test_sold_out_model_target_is_one(self, repo, sample_screening):
        """sold_out=True → model_target=1."""
        sold = {**sample_screening, "sold_out": True, "availability_state": "SOLD_OUT"}
        obs_id, _ = repo.record_screening(sold)
        obs = repo.get_observation(obs_id)
        assert obs["model_target"] == 1

    def test_unknown_model_target_is_none(self, repo):
        """sold_out=None → model_target=None."""
        screening = {
            "venue_id": "test_venue", "film_title": "Unknown Film",
            "show_date": "Monday 1st January", "show_time": "7:00 pm",
            "source_url": "https://example.com", "source_timestamp": "2026-10-07T20:00:00Z",
            "sold_out": None, "availability_state": "UNKNOWN",
        }
        obs_id, _ = repo.record_screening(screening)
        obs = repo.get_observation(obs_id)
        assert obs["model_target"] is None

    def test_model_target_function(self):
        """_model_target: 1→1, 0→None, None→None."""
        assert _model_target(1) == 1
        assert _model_target(0) is None
        assert _model_target(None) is None


# ============================================================
# TEST 14: Qloo feature timestamp is preserved
# ============================================================

class TestQlooFeatureTimestampPreserved:
    def test_retrieval_timestamp_stored(self, repo, sample_screening):
        """Qloo feature retrieval timestamp is stored and retrievable."""
        obs_id, _ = repo.record_screening(sample_screening)
        fk = film_key("Halloween", 1978)

        repo.record_film_resolution({
            "film_key": fk,
            "film_title": "Halloween",
            "film_year": 1978,
            "resolution_status": "VERIFIED",
            "qloo_entity_id": "E123",
            "resolution_timestamp": "2026-10-07T10:00:00Z",
        })

        repo.record_qloo_features({
            "film_key": fk,
            "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-07T15:00:00Z",
            "qloo_affinity": 0.8,
            "qloo_popularity": 0.5,
            "qloo_call_id": "call-001",
        })

        features = repo.get_qloo_features_for_film(fk)
        assert len(features) == 1
        assert features[0]["retrieved_at"] == "2026-10-07T15:00:00Z"
        assert features[0]["qloo_call_id"] == "call-001"

    def test_multiple_snapshots_preserved(self, repo, sample_screening):
        """Multiple Qloo snapshots for same film are preserved."""
        obs_id, _ = repo.record_screening(sample_screening)
        fk = film_key("Halloween", 1978)

        repo.record_film_resolution({
            "film_key": fk, "film_title": "Halloween", "film_year": 1978,
            "resolution_status": "VERIFIED", "qloo_entity_id": "E123",
            "resolution_timestamp": "2026-10-01T10:00:00Z",
        })

        # First snapshot
        repo.record_qloo_features({
            "film_key": fk, "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-05T10:00:00Z",
            "qloo_affinity": 0.7, "qloo_popularity": 0.4,
        })

        # Second snapshot (later retrieval)
        repo.record_qloo_features({
            "film_key": fk, "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-10T10:00:00Z",
            "qloo_affinity": 0.9, "qloo_popularity": 0.6,
        })

        features = repo.get_qloo_features_for_film(fk)
        assert len(features) == 2
        assert features[0]["qloo_affinity"] == 0.7
        assert features[1]["qloo_affinity"] == 0.9


# ============================================================
# TEST 15: provenance required
# ============================================================

class TestProvenanceRequired:
    def test_resolution_has_provenance(self, repo, sample_screening):
        """Resolution record has provenance field."""
        obs_id, _ = repo.record_screening(sample_screening)
        repo.record_resolution(obs_id, {
            "resolution_status": "VERIFIED",
            "qloo_entity_id": "E123",
            "resolution_provenance": "resolver/search_with_year",
            "resolution_timestamp": "2026-10-07T20:00:00Z",
        })
        res = repo.get_resolution(obs_id)
        assert res["resolution_provenance"] == "resolver/search_with_year"

    def test_feature_has_provenance(self, repo, sample_screening):
        """Qloo feature snapshot has provenance field."""
        obs_id, _ = repo.record_screening(sample_screening)
        fk = film_key("Halloween", 1978)

        repo.record_film_resolution({
            "film_key": fk, "film_title": "Halloween", "film_year": 1978,
            "resolution_status": "VERIFIED", "qloo_entity_id": "E123",
            "resolution_timestamp": "2026-10-07T10:00:00Z",
        })

        repo.record_qloo_features({
            "film_key": fk, "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-07T15:00:00Z",
            "provenance": "insights/film_affinity",
        })

        features = repo.get_qloo_features_for_film(fk)
        assert features[0]["provenance"] == "insights/film_affinity"


# ============================================================
# TEST 16: duplicate snapshots remain idempotent
# ============================================================

class TestDuplicateSnapshotsIdempotent:
    def test_same_snapshot_twice_one_record(self, repo, sample_screening):
        """Same snapshot (same timestamp) → INSERT OR IGNORE, one record."""
        obs_id, _ = repo.record_screening(sample_screening)

        # Record again with same timestamp
        repo.record_screening(sample_screening)

        snapshots = repo.get_snapshots(obs_id)
        assert len(snapshots) == 1  # Idempotent

    def test_different_snapshots_different_records(self, repo, sample_screening):
        """Different timestamps → different snapshots."""
        obs_id, _ = repo.record_screening(sample_screening)

        s2 = {**sample_screening, "source_timestamp": "2026-10-08T10:00:00Z"}
        repo.record_screening(s2)

        snapshots = repo.get_snapshots(obs_id)
        assert len(snapshots) == 2


# ============================================================
# TEST: lead_time_bucket classification
# ============================================================

class TestLeadTimeBucket:
    def test_bucket_0_24h(self):
        assert lead_time_bucket(12.0) == "0-24h"
        assert lead_time_bucket(0.5) == "0-24h"
        assert lead_time_bucket(24.0) == "0-24h"

    def test_bucket_1_3d(self):
        assert lead_time_bucket(48.0) == "1-3d"
        assert lead_time_bucket(72.0) == "1-3d"

    def test_bucket_4_7d(self):
        assert lead_time_bucket(120.0) == "4-7d"
        assert lead_time_bucket(168.0) == "4-7d"

    def test_bucket_8_14d(self):
        assert lead_time_bucket(240.0) == "8-14d"
        assert lead_time_bucket(336.0) == "8-14d"

    def test_bucket_15_30d(self):
        assert lead_time_bucket(480.0) == "15-30d"
        assert lead_time_bucket(720.0) == "15-30d"

    def test_bucket_30d_plus(self):
        assert lead_time_bucket(1000.0) == "30d+"

    def test_bucket_none(self):
        assert lead_time_bucket(None) is None

    def test_bucket_negative(self):
        assert lead_time_bucket(-5.0) == "post_show"


# ============================================================
# TEST: analytical benchmark construction
# ============================================================

class TestAnalyticalBenchmark:
    def test_benchmark_row_structure(self, repo, sample_screening):
        """Benchmark row has all required fields."""
        obs_id, _ = repo.record_screening(sample_screening)
        fk = film_key("Halloween", 1978)

        repo.record_film_resolution({
            "film_key": fk, "film_title": "Halloween", "film_year": 1978,
            "resolution_status": "VERIFIED", "qloo_entity_id": "E123",
            "resolution_timestamp": "2026-10-06T10:00:00Z",
        })

        repo.record_qloo_features({
            "film_key": fk, "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-07T10:00:00Z",  # Before observation
            "qloo_affinity": 0.8, "qloo_popularity": 0.5,
            "qloo_band": "high", "qloo_domain": "film",
        })

        benchmark = repo.build_analytical_benchmark()
        assert len(benchmark) == 1

        row = benchmark[0]
        assert row["observation_id"] == obs_id
        assert row["film_title"] == "Halloween"
        assert row["film_year"] == 1978
        assert row["show_start_at"] == "2026-10-31T20:00:00+00:00"
        assert row["observation_timestamp"] == "2026-10-07T20:00:00Z"
        assert row["lead_time_hours"] is not None
        assert row["lead_time_bucket"] is not None
        assert row["sold_out_observed"] == 0
        assert row["model_target"] is None  # AVAILABLE → NULL, not 0
        assert row["qloo_entity_id"] == "E123"
        assert row["qloo_affinity"] == 0.8
        assert row["qloo_popularity"] == 0.5
        assert row["qloo_feature_status"] == "AVAILABLE_AT_PREDICTION_TIME"
        assert row["resolution_status"] == "VERIFIED"

    def test_benchmark_excludes_future_features(self, repo, sample_screening):
        """Benchmark marks future features as FUTURE_FEATURE_UNAVAILABLE."""
        obs_id, _ = repo.record_screening(sample_screening)
        fk = film_key("Halloween", 1978)

        repo.record_film_resolution({
            "film_key": fk, "film_title": "Halloween", "film_year": 1978,
            "resolution_status": "VERIFIED", "qloo_entity_id": "E123",
            "resolution_timestamp": "2026-10-06T10:00:00Z",
        })

        # Feature retrieved AFTER observation (2026-10-07T20:00:00Z)
        repo.record_qloo_features({
            "film_key": fk, "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-08T10:00:00Z",
            "qloo_affinity": 0.8, "qloo_popularity": 0.5,
        })

        benchmark = repo.build_analytical_benchmark()
        row = benchmark[0]
        assert row["qloo_feature_status"] == "FUTURE_FEATURE_UNAVAILABLE"
        assert row["qloo_affinity"] is None  # Not used for this observation

    def test_benchmark_sold_out_model_target(self, repo):
        """Sold out screening → model_target=1."""
        screening = {
            "venue_id": "test_venue", "film_title": "Sold Film", "film_year": 2020,
            "show_date": "Friday 31st October", "show_time": "8:00 pm", "format": "",
            "source_url": "https://example.com", "source_timestamp": "2026-10-07T10:00:00Z",
            "sold_out": True, "availability_state": "SOLD_OUT",
        }
        repo.record_screening(screening)

        benchmark = repo.build_analytical_benchmark()
        row = benchmark[0]
        assert row["sold_out_observed"] == 1
        assert row["model_target"] == 1


# ============================================================
# TEST: film_key utility
# ============================================================

class TestFilmKey:
    def test_film_key_normalizes(self):
        """film_key normalizes title (strip, lower)."""
        fk1 = film_key("  Halloween  ", 1978)
        fk2 = film_key("halloween", 1978)
        assert fk1 == fk2

    def test_film_key_with_none_year(self):
        """film_key handles None year."""
        fk = film_key("Film", None)
        assert fk == "film|None"


# ============================================================
# TEST: multi-snapshot and state transition counting
# ============================================================

class TestMultiSnapshotAndTransitions:
    def test_multi_snapshot_count(self, repo, sample_screening):
        """Count observations with >1 snapshot."""
        obs_id, _ = repo.record_screening(sample_screening)
        s2 = {**sample_screening, "source_timestamp": "2026-10-08T10:00:00Z"}
        repo.record_screening(s2)

        assert repo.count_multi_snapshot_observations() == 1

    def test_state_transition_count(self, repo, sample_screening):
        """Count AVAILABLE → SOLD_OUT transitions."""
        obs_id, _ = repo.record_screening(sample_screening)
        sold = {**sample_screening, "sold_out": True, "availability_state": "SOLD_OUT",
                "source_timestamp": "2026-10-08T10:00:00Z"}
        repo.record_screening(sold)

        assert repo.count_state_transitions() == 1