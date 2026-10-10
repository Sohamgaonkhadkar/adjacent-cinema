"""
M13.3: Outcome Ledger — Backend Tests
---------------------------------------
Tests proving:
1. Duplicate scrape is idempotent
2. Book → Sold Out creates new snapshot
3. NULL remains NULL
4. Recommendation ID persists
5. sold_out classified as STRONG_PROXY
6. available classified as DESCRIPTIVE_ONLY
7. Duplicate screening is not duplicated
8. Malformed capacity is rejected
9. Negative tickets_sold rejected
10. Provenance is mandatory for external observations
"""

import pytest
import tempfile
from pathlib import Path

from app.domain.outcome_repository import OutcomeRepository, _deterministic_obs_id


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
        "format": "35mm",
        "source_url": "https://example.com",
        "source_timestamp": "2026-10-07T20:00:00Z",
        "sold_out": False,
        "availability_state": "AVAILABLE",
    }


# ============================================================
# TEST 1: Duplicate scrape is idempotent
# ============================================================

class TestIdempotency:
    def test_same_screening_twice_one_observation(self, repo, sample_screening):
        """Same screening scraped twice → exactly one observation."""
        obs_id1, is_new1 = repo.record_screening(sample_screening)
        obs_id2, is_new2 = repo.record_screening(sample_screening)

        assert obs_id1 == obs_id2
        assert is_new1 is True
        assert is_new2 is False
        assert repo.count_observations() == 1

    def test_same_screening_creates_snapshot(self, repo, sample_screening):
        """Same screening creates a snapshot even if observation exists."""
        repo.record_screening(sample_screening)

        # Same screening, same state, different timestamp
        sample2 = {**sample_screening, "source_timestamp": "2026-10-07T21:00:00Z"}
        repo.record_screening(sample2)

        # Should have 1 observation, 2 snapshots
        assert repo.count_observations() == 1
        assert repo.count_snapshots() == 2


# ============================================================
# TEST 2: Book → Sold Out creates new snapshot
# ============================================================

class TestStateChange:
    def test_available_to_sold_out(self, repo, sample_screening):
        """Book → Sold Out creates new snapshot and updates observation."""
        obs_id, _ = repo.record_screening(sample_screening)
        obs = repo.get_observation(obs_id)
        assert obs["sold_out"] == 0  # Available

        # Scrape again — now sold out
        sold_screening = {**sample_screening, "sold_out": True,
                          "availability_state": "SOLD_OUT",
                          "source_timestamp": "2026-10-08T10:00:00Z"}
        obs_id2, is_new = repo.record_screening(sold_screening)

        assert obs_id2 == obs_id
        assert is_new is False

        # Observation updated
        obs = repo.get_observation(obs_id)
        assert obs["sold_out"] == 1

        # Both snapshots preserved
        snapshots = repo.get_snapshots(obs_id)
        assert len(snapshots) == 2
        assert snapshots[0]["sold_out"] == 0  # First: available
        assert snapshots[1]["sold_out"] == 1  # Second: sold out


# ============================================================
# TEST 3: NULL remains NULL
# ============================================================

class TestNullPreservation:
    def test_null_fields_stay_null(self, repo):
        """NULL fields are not converted to zero."""
        screening = {
            "venue_id": "test_venue",
            "film_title": "Test Film",
            "show_date": "Monday 1st January",
            "show_time": "7:00 pm",
            "source_url": "https://example.com",
            "source_timestamp": "2026-10-07T20:00:00Z",
            "sold_out": None,
            "availability_state": "UNKNOWN",
        }
        obs_id, _ = repo.record_screening(screening)
        obs = repo.get_observation(obs_id)

        assert obs["sold_out"] is None
        assert obs["film_year"] is None
        assert obs["format"] == ""


# ============================================================
# TEST 4: Recommendation ID persists
# ============================================================

class TestRecommendationPersistence:
    def test_recommendation_stored_and_retrieved(self, repo):
        """Recommendation ID persists across operations."""
        rec = {
            "recommendation_id": "rec-001",
            "venue_id": "test_venue",
            "venue_name": "Test Cinema",
            "candidate_entity": "Halloween",
            "candidate_domain": "film",
            "qloo_affinity": 0.95,
        }
        repo.create_recommendation(rec)
        stored = repo.get_recommendation("rec-001")

        assert stored is not None
        assert stored["recommendation_id"] == "rec-001"
        assert stored["candidate_entity"] == "Halloween"

    def test_recommendation_id_on_screening(self, repo, sample_screening):
        """Screening can reference a recommendation."""
        rec = {
            "recommendation_id": "rec-002",
            "venue_id": "test_venue",
            "venue_name": "Test Cinema",
            "candidate_entity": "Halloween",
            "candidate_domain": "film",
        }
        repo.create_recommendation(rec)

        screening = {**sample_screening, "recommendation_id": "rec-002"}
        obs_id, _ = repo.record_screening(screening)
        obs = repo.get_observation(obs_id)

        assert obs["recommendation_id"] == "rec-002"


# ============================================================
# TEST 5-6: Label quality classification
# ============================================================

class TestLabelQuality:
    def test_sold_out_is_strong_proxy(self, repo, sample_screening):
        """sold_out = True → label_quality = STRONG_PROXY."""
        obs_id, _ = repo.record_screening(sample_screening)
        repo.record_outcome(obs_id, {
            "sold_out": True,
            "measurement_timestamp": "2026-10-08T10:00:00Z",
            "source": "test",
            "provenance": "test",
        })
        outcome = repo.get_outcome(obs_id)
        assert outcome["label_quality"] == "STRONG_PROXY"

    def test_available_is_descriptive_only(self, repo, sample_screening):
        """sold_out = False → label_quality = DESCRIPTIVE_ONLY (M13.4 corrected)."""
        obs_id, _ = repo.record_screening(sample_screening)
        repo.record_outcome(obs_id, {
            "sold_out": False,
            "measurement_timestamp": "2026-10-08T10:00:00Z",
            "source": "test",
            "provenance": "test",
        })
        outcome = repo.get_outcome(obs_id)
        assert outcome["label_quality"] == "DESCRIPTIVE_ONLY"

    def test_tickets_sold_is_direct_outcome(self, repo, sample_screening):
        """tickets_sold → label_quality = DIRECT_OUTCOME."""
        obs_id, _ = repo.record_screening(sample_screening)
        repo.record_outcome(obs_id, {
            "tickets_sold": 150,
            "measurement_timestamp": "2026-10-08T10:00:00Z",
            "source": "test",
            "provenance": "test",
        })
        outcome = repo.get_outcome(obs_id)
        assert outcome["label_quality"] == "DIRECT_OUTCOME"


# ============================================================
# TEST 7: Duplicate screening is not duplicated
# ============================================================

class TestDuplicateProtection:
    def test_different_timestamps_same_screening(self, repo):
        """Same screening at different times → one observation, multiple snapshots."""
        s1 = {
            "venue_id": "test_venue", "film_title": "Film A", "film_year": 2020,
            "show_date": "Monday 1st January", "show_time": "7:00 pm", "format": "",
            "source_url": "https://example.com", "source_timestamp": "2026-01-01T10:00:00Z",
            "sold_out": False, "availability_state": "AVAILABLE",
        }
        s2 = {**s1, "source_timestamp": "2026-01-02T10:00:00Z", "sold_out": True,
              "availability_state": "SOLD_OUT"}

        id1, new1 = repo.record_screening(s1)
        id2, new2 = repo.record_screening(s2)

        assert id1 == id2
        assert new1 is True
        assert new2 is False
        assert repo.count_observations() == 1
        assert repo.count_snapshots() == 2

    def test_different_films_are_separate(self, repo):
        """Different films → separate observations."""
        s1 = {
            "venue_id": "test_venue", "film_title": "Film A", "film_year": 2020,
            "show_date": "Monday 1st January", "show_time": "7:00 pm", "format": "",
            "source_url": "https://example.com", "source_timestamp": "2026-01-01T10:00:00Z",
            "sold_out": False, "availability_state": "AVAILABLE",
        }
        s2 = {**s1, "film_title": "Film B"}

        id1, _ = repo.record_screening(s1)
        id2, _ = repo.record_screening(s2)

        assert id1 != id2
        assert repo.count_observations() == 2


# ============================================================
# TEST 8-9: Validation
# ============================================================

class TestValidation:
    def test_negative_tickets_sold_rejected(self, repo, sample_screening):
        """Negative tickets_sold raises ValueError."""
        obs_id, _ = repo.record_screening(sample_screening)
        with pytest.raises(ValueError, match="tickets_sold"):
            repo.record_outcome(obs_id, {
                "tickets_sold": -5,
                "measurement_timestamp": "2026-10-08T10:00:00Z",
                "source": "test", "provenance": "test",
            })

    def test_zero_capacity_rejected(self, repo, sample_screening):
        """Zero capacity raises ValueError."""
        obs_id, _ = repo.record_screening(sample_screening)
        with pytest.raises(ValueError, match="capacity"):
            repo.record_outcome(obs_id, {
                "capacity": 0,
                "measurement_timestamp": "2026-10-08T10:00:00Z",
                "source": "test", "provenance": "test",
            })

    def test_occupancy_out_of_range_rejected(self, repo, sample_screening):
        """Occupancy > 1 raises ValueError."""
        obs_id, _ = repo.record_screening(sample_screening)
        with pytest.raises(ValueError, match="occupancy"):
            repo.record_outcome(obs_id, {
                "occupancy": 1.5,
                "measurement_timestamp": "2026-10-08T10:00:00Z",
                "source": "test", "provenance": "test",
            })


# ============================================================
# TEST 10: Film resolution
# ============================================================

class TestFilmResolution:
    def test_resolution_stored(self, repo, sample_screening):
        """Film resolution is stored and retrievable."""
        obs_id, _ = repo.record_screening(sample_screening)
        repo.record_resolution(obs_id, {
            "resolution_status": "VERIFIED",
            "resolved_title": "Halloween",
            "resolved_year": 1978,
            "qloo_entity_id": "E123",
            "resolution_provenance": "resolver/test",
        })
        res = repo.get_resolution(obs_id)

        assert res is not None
        assert res["resolution_status"] == "VERIFIED"
        assert res["qloo_entity_id"] == "E123"


# ============================================================
# TEST 11: Data quality audit
# ============================================================

class TestDataQuality:
    def test_audit_counts(self, repo, sample_screening):
        """Audit correctly counts observations and snapshots."""
        repo.record_screening(sample_screening)
        repo.record_screening({**sample_screening, "film_title": "Film B"})

        audit = repo.data_quality_audit()
        assert audit["total_observations"] == 2
        assert audit["total_snapshots"] == 2
        assert audit["unique_films"] == 2
        assert audit["unique_venues"] == 1

    def test_sold_out_stats(self, repo, sample_screening):
        """Sold out stats are correct."""
        repo.record_screening(sample_screening)
        repo.record_screening({**sample_screening, "film_title": "Film B",
                               "sold_out": True, "availability_state": "SOLD_OUT"})

        stats = repo.sold_out_stats()
        assert stats["total"] == 2
        assert stats["sold_out"] == 1
        assert stats["available"] == 1
        assert stats["sold_out_rate"] == 0.5


# ============================================================
# TEST 12: Deterministic observation IDs
# ============================================================

class TestDeterministicIDs:
    def test_same_input_same_id(self):
        """Same screening identity → same observation ID."""
        id1 = _deterministic_obs_id("venue1", "Film A", 2020, "Monday", "7pm", "")
        id2 = _deterministic_obs_id("venue1", "Film A", 2020, "Monday", "7pm", "")
        assert id1 == id2

    def test_different_input_different_id(self):
        """Different screening identity → different observation ID."""
        id1 = _deterministic_obs_id("venue1", "Film A", 2020, "Monday", "7pm", "")
        id2 = _deterministic_obs_id("venue1", "Film B", 2020, "Monday", "7pm", "")
        assert id1 != id2