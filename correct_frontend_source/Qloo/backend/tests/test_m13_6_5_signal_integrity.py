"""M13.6.5 regressions for feature substance, temporal integrity and joins."""
from datetime import datetime, timedelta, timezone

from app.domain.film_identity import canonical_film_key
from app.domain.outcome_repository import OutcomeRepository, film_key
from app.domain.qloo_signal import (
    CULTURAL_SIGNAL,
    EMPTY_SNAPSHOT,
    IDENTITY_ONLY,
    INVALID_SIGNAL_SCHEMA,
    POPULARITY_ONLY,
    assess_feature,
    latest_feature,
)
from research.scripts.m13_6_prospective import step2_create_prediction_snapshots


def feature(at, **overrides):
    row = {
        "retrieved_at": at,
        "qloo_entity_id": "qloo:film:1",
        "qloo_affinity": None,
        "qloo_popularity": None,
        "candidate_tags": "[]",
        "provenance": "insights-api",
    }
    row.update(overrides)
    return row


def test_empty_snapshot_is_not_cultural_signal():
    assessment = assess_feature(feature("2026-10-01T10:00:00Z", qloo_popularity=0.88))
    assert assessment["status"] == POPULARITY_ONLY
    assert assessment["has_cultural_signal"] is False
    assert assessment["has_usable_feature"] is True


def test_nonempty_valid_tags_are_cultural_signal():
    assessment = assess_feature(feature(
        "2026-10-01T10:00:00Z", candidate_tags='[{"name":"psychological thriller"}]'
    ))
    assert assessment["status"] == CULTURAL_SIGNAL
    assert assessment["valid_tag_count"] == 1


def test_zero_affinity_is_valid_numeric_signal():
    assessment = assess_feature(feature("2026-10-01T10:00:00Z", qloo_affinity=0.0))
    assert assessment["status"] == CULTURAL_SIGNAL
    assert assessment["has_affinity"] is True


def test_identity_only_is_not_a_cultural_signal():
    assessment = assess_feature(feature("2026-10-01T10:00:00Z"))
    assert assessment["status"] == IDENTITY_ONLY
    assert not assessment["has_cultural_signal"]


def test_malformed_nonempty_tag_schema_is_not_accepted():
    assessment = assess_feature(feature("2026-10-01T10:00:00Z", candidate_tags='{"tag":"no-list"}'))
    assert assessment["status"] == INVALID_SIGNAL_SCHEMA
    assert not assessment["has_cultural_signal"]


def test_latest_empty_row_does_not_mask_earlier_signal():
    rows = [
        feature("2026-10-01T10:00:00Z", candidate_tags='["slow cinema"]'),
        feature("2026-10-02T10:00:00Z", candidate_tags="[]", qloo_popularity=None),
    ]
    selected = latest_feature(rows, before="2026-10-03T00:00:00Z", cultural_only=True)
    assert selected["retrieved_at"] == "2026-10-01T10:00:00Z"


def test_timestamp_comparison_normalizes_offsets_and_respects_cutoff():
    rows = [
        feature("2026-10-01T12:00:00+02:00", candidate_tags='["older"]'),
        feature("2026-10-01T11:00:00Z", candidate_tags='["later"]'),
    ]
    selected = latest_feature(rows, before="2026-10-01T12:00:00Z", cultural_only=True)
    assert selected["candidate_tags"] == '["later"]'
    assert latest_feature(rows, before="2026-10-01T09:59:59Z", cultural_only=True) is None


def test_prediction_builder_never_falls_back_to_resolution_popularity(tmp_path):
    repo = OutcomeRepository(tmp_path / "no-fallback.db")
    now = datetime.now(timezone.utc)
    show_dt = now + timedelta(days=12)
    obs = {
        "venue_id": "test-venue", "venue_name": "Test Venue", "film_title": "Alien",
        "film_year": 1979, "show_date": show_dt.strftime("%A %d %B"), "show_time": "8:00 pm",
        "show_start_at": show_dt.isoformat(), "format": "35mm",
        "source_url": "https://example.test/show", "source_timestamp": now.isoformat(),
        "sold_out": False, "availability_state": "AVAILABLE",
    }
    obs_id, _ = repo.record_screening(obs)
    fk = canonical_film_key("Alien", 1979)
    repo.record_film_resolution({
        "film_key": fk, "film_title": "Alien", "film_year": 1979,
        "resolution_status": "RESOLVED", "qloo_entity_id": "entity-1",
        "qloo_popularity": 0.97, "resolution_provenance": "entity-search",
    })

    step2_create_prediction_snapshots(repo, "test-run-no-fallback")
    rows = repo.list_prediction_snapshots()
    assert len(rows) == 3
    assert all(row["qloo_entity_id"] == "entity-1" for row in rows)
    assert all(row["qloo_popularity"] is None for row in rows)
    assert all(row["qloo_feature_timestamp"] is None for row in rows)
    assert all(row["qloo_signal_status"] == "NO_FEATURE" for row in rows)
    repo.close()


def test_past_prediction_row_is_immutable_even_while_pending(tmp_path):
    repo = OutcomeRepository(tmp_path / "freeze.db")
    now = datetime.now(timezone.utc)
    show_dt = now + timedelta(days=10)
    obs = {
        "venue_id": "test-venue", "venue_name": "Test Venue", "film_title": "Alien",
        "film_year": 1979, "show_date": show_dt.strftime("%A %d %B"), "show_time": "8:00 pm",
        "show_start_at": show_dt.isoformat(), "format": "35mm",
        "source_url": "https://example.test/show", "source_timestamp": now.isoformat(),
        "sold_out": False, "availability_state": "AVAILABLE",
    }
    obs_id, _ = repo.record_screening(obs)
    timestamp = (now - timedelta(hours=2)).isoformat()
    pred_id = repo.upsert_prediction_snapshot({
        "observation_id": obs_id, "film_key": film_key("Alien", 1979),
        "prediction_run_id": "initial", "prediction_timestamp": timestamp,
        "prediction_horizon_hours": 24, "show_start_at": show_dt.isoformat(),
        "qloo_popularity": None, "qloo_feature_status": "NO_FEATURE",
        "qloo_signal_status": "NO_FEATURE",
    })
    repo.upsert_prediction_snapshot({
        "observation_id": obs_id, "film_key": film_key("Alien", 1979),
        "prediction_run_id": "retry", "prediction_timestamp": timestamp,
        "prediction_horizon_hours": 24, "show_start_at": show_dt.isoformat(),
        "qloo_popularity": 0.99, "qloo_feature_timestamp": now.isoformat(),
        "qloo_feature_status": "AVAILABLE_AT_PREDICTION_TIME",
        "qloo_signal_status": "POPULARITY_ONLY_AT_PREDICTION_TIME",
    })
    saved = repo.get_prediction_snapshot(obs_id, 24)
    assert saved["prediction_id"] == pred_id
    assert saved["qloo_popularity"] is None
    assert saved["qloo_feature_timestamp"] is None
    repo.close()


def test_html_encoded_title_does_not_create_second_screening(tmp_path):
    repo = OutcomeRepository(tmp_path / "identity.db")
    now = datetime.now(timezone.utc)
    show_dt = now + timedelta(days=10)
    common = {
        "venue_id": "pcc", "venue_name": "PCC", "film_year": 1979,
        "show_date": "Friday 19 October", "show_time": "20:00", "show_start_at": show_dt.isoformat(),
        "format": "35mm", "source_url": "https://example.test/show",
        "sold_out": False, "availability_state": "AVAILABLE",
    }
    first_id, first_new = repo.record_screening({
        **common, "film_title": "Angel's Egg", "source_timestamp": now.isoformat()
    })
    second_id, second_new = repo.record_screening({
        **common, "film_title": "Angel&#039;s Egg",
        "source_timestamp": (now + timedelta(minutes=1)).isoformat()
    })
    assert first_new is True
    assert second_new is False
    assert second_id == first_id
    assert len(repo.list_all_observations()) == 1
    assert len(repo.get_snapshots(first_id)) == 2
    repo.close()


def test_leakage_audit_flags_prediction_created_after_cutoff(tmp_path):
    repo = OutcomeRepository(tmp_path / "retrospective-row.db")
    now = datetime.now(timezone.utc)
    show_dt = now + timedelta(days=10)
    obs = {
        "venue_id": "test-venue", "venue_name": "Test Venue", "film_title": "Alien",
        "film_year": 1979, "show_date": show_dt.strftime("%A %d %B"), "show_time": "8:00 pm",
        "show_start_at": show_dt.isoformat(), "format": "35mm",
        "source_url": "https://example.test/show", "source_timestamp": now.isoformat(),
        "sold_out": False, "availability_state": "AVAILABLE",
    }
    obs_id, _ = repo.record_screening(obs)
    repo.upsert_prediction_snapshot({
        "observation_id": obs_id, "film_key": film_key("Alien", 1979),
        "prediction_run_id": "late-run", "prediction_timestamp": (now - timedelta(minutes=1)).isoformat(),
        "prediction_horizon_hours": 24, "show_start_at": show_dt.isoformat(),
        "qloo_feature_status": "NO_FEATURE", "qloo_signal_status": "NO_FEATURE",
    })
    audit = repo.leakage_audit()
    assert audit["passed"] is False
    assert audit["violations"]["snapshot_created_after_prediction_timestamp"] == 1
    repo.close()
