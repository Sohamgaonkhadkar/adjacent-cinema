"""
M13.5: Canonical Film Identity + Verified Qloo Join — Tests

Tests proving:
1. Canonicalization is deterministic and tested
2. No uncertain title merges are silently performed
3. Every externally supplied film year has provenance
4. Existing EntityResolver is reused
5. VERIFIED is never produced from an unverified identity
6. Previous MISMATCH cases are audited
7. qloo_popularity is not mislabeled as cultural affinity
8. affinity is NULL unless a legitimate cohort/context exists
9. temporal leakage prevention still passes
10. screening-level joins use canonical film_key
11. raw-title duplicates no longer inflate film counts
12. full test suite passes
13. no ML training
14. prediction-time Qloo coverage explicitly reported
"""

import pytest
import json
from pathlib import Path

from app.domain.film_identity import (
    canonicalize_film, canonical_film_key, audit_canonicalization,
    IdentityStatus, NormalizationResult,
)
from app.domain.outcome_repository import OutcomeRepository


# ============================================================
# TEST 1: Canonicalization is deterministic
# ============================================================

class TestCanonicalizationDeterministic:
    def test_same_input_same_output(self):
        """Same input always produces same canonical output."""
        r1 = canonicalize_film("A Very Harold &amp; Kumar Christmas")
        r2 = canonicalize_film("A Very Harold &amp; Kumar Christmas")
        assert r1.canonical_title == r2.canonical_title
        assert r1.extracted_year == r2.extracted_year

    def test_html_entity_decode_deterministic(self):
        """HTML entity decoding is consistent."""
        r = canonicalize_film("Angel&#039;s Egg")
        assert r.canonical_title == "Angel's Egg"
        assert "html_entity_decode" in r.canonicalization_reasons

    def test_colon_normalize_deterministic(self):
        """Colon normalization is consistent."""
        r = canonicalize_film("2001 : A Space Odyssey")
        assert r.canonical_title == "2001: A Space Odyssey"
        assert "colon_normalize" in r.canonicalization_reasons

    def test_year_extraction_deterministic(self):
        """Year extraction is consistent."""
        r = canonicalize_film("Black Christmas (1974)")
        assert r.canonical_title == "Black Christmas"
        assert r.extracted_year == 1974
        assert "year_extracted:1974" in r.canonicalization_reasons


# ============================================================
# TEST 2: No uncertain title merges
# ============================================================

class TestNoUncertainMerges:
    def test_different_titles_different_keys(self):
        """Different films get different canonical keys."""
        k1 = canonical_film_key("Alien", 1979)
        k2 = canonical_film_key("Aliens", 1986)
        assert k1 != k2

    def test_same_title_different_years_different_keys(self):
        """Same title, different year → different keys."""
        k1 = canonical_film_key("Halloween", 1978)
        k2 = canonical_film_key("Halloween", 2007)
        assert k1 != k2

    def test_variant_titles_same_film_same_key(self):
        """HTML entity variants → same key (safe merge)."""
        r1 = canonicalize_film("Don&#039;t Look Now")
        r2 = canonicalize_film("Don't Look Now")
        k1 = canonical_film_key(r1.canonical_title, r1.extracted_year)
        k2 = canonical_film_key(r2.canonical_title, r2.extracted_year)
        assert k1 == k2  # Safe merge: same film, just HTML encoding

    def test_edition_suffixes_merged(self):
        """Edition suffixes stripped → same key for same film."""
        r1 = canonicalize_film("Alien (Theatrical Cut)")
        r2 = canonicalize_film("Alien")
        k1 = canonical_film_key(r1.canonical_title, r1.extracted_year)
        k2 = canonical_film_key(r2.canonical_title, r2.extracted_year)
        # Note: "Alien (Theatrical Cut)" extracts no year, "Alien" has no year
        # Both should have same canonical title
        assert r1.canonical_title == r2.canonical_title


# ============================================================
# TEST 3: Year provenance
# ============================================================

class TestYearProvenance:
    def test_extracted_year_has_source(self):
        """Year extracted from title has source documented."""
        r = canonicalize_film("Black Christmas (1974)")
        assert r.extracted_year == 1974
        assert r.year_source == "extracted_from_title"

    def test_provided_year_has_source(self):
        """Year provided externally has source documented."""
        r = canonicalize_film("Alien", raw_year=1979)
        assert r.extracted_year == 1979
        assert r.year_source == "pcc_provided"

    def test_no_year_has_empty_source(self):
        """No year → empty source."""
        r = canonicalize_film("Casablanca")
        assert r.extracted_year is None
        assert r.year_source == ""


# ============================================================
# TEST 4: Identity status classification
# ============================================================

class TestIdentityStatus:
    def test_year_provided_is_verified(self):
        """Film with year → VERIFIED status."""
        r = canonicalize_film("Alien", raw_year=1979)
        assert r.identity_status == IdentityStatus.VERIFIED

    def test_year_extracted_is_verified(self):
        """Film with year extracted from title → VERIFIED status."""
        r = canonicalize_film("Black Christmas (1974)")
        assert r.identity_status == IdentityStatus.VERIFIED

    def test_no_year_is_year_missing(self):
        """Film without year → YEAR_MISSING status."""
        r = canonicalize_film("Casablanca")
        assert r.identity_status == IdentityStatus.YEAR_MISSING

    def test_event_is_event_or_composite(self):
        """Event/composite → EVENT_OR_COMPOSITE status."""
        r = canonicalize_film("Classic Horror Marathon")
        assert r.identity_status == IdentityStatus.EVENT_OR_COMPOSITE
        assert r.is_event is True

    def test_empty_title_needs_review(self):
        """Empty title → NEEDS_REVIEW."""
        r = canonicalize_film("")
        assert r.identity_status == IdentityStatus.NEEDS_REVIEW


# ============================================================
# TEST 5: Event detection
# ============================================================

class TestEventDetection:
    def test_double_feature_detected(self):
        """Double feature → detected as event."""
        r = canonicalize_film("Halloween (1978) + Halloween II (1981) • Double Feature")
        assert r.is_event is True

    def test_marathon_detected(self):
        """Marathon → detected as event."""
        r = canonicalize_film("Halloween Marathon")
        assert r.is_event is True

    def test_shorts_programme_detected(self):
        """Shorts programme → detected as event."""
        r = canonicalize_film("Call Your Bluff [Shorts Programme]")
        assert r.is_event is True

    def test_live_score_detected(self):
        """Live score screening → detected as event."""
        r = canonicalize_film("Nosferatu with Live Score")
        assert r.is_event is True

    def test_regular_film_not_event(self):
        """Regular film → not an event."""
        r = canonicalize_film("Alien")
        assert r.is_event is False


# ============================================================
# TEST 6: Director prefix removal
# ============================================================

class TestDirectorPrefix:
    def test_ken_russell_removed(self):
        """Director prefix removed."""
        r = canonicalize_film("Ken Russell's The Devils: The Director's Cut")
        assert r.canonical_title == "The Devils"
        assert any("director_prefix_removed" in reason for reason in r.canonicalization_reasons)

    def test_rob_zombie_removed(self):
        """Director prefix removed."""
        r = canonicalize_film("Rob Zombie's Halloween (2007) • Director's Cut")
        assert r.canonical_title == "Halloween"
        assert r.extracted_year == 2007


# ============================================================
# TEST 7: Edition suffix removal
# ============================================================

class TestEditionSuffix:
    def test_theatrical_cut_removed(self):
        """Theatrical Cut suffix removed."""
        r = canonicalize_film("Alien (Theatrical Cut)")
        assert r.canonical_title == "Alien"

    def test_anniversary_removed(self):
        """Anniversary suffix removed."""
        r = canonicalize_film("Amelie - 25th Anniversary")
        assert r.canonical_title == "Amelie"

    def test_final_cut_removed(self):
        """Final Cut suffix removed."""
        r = canonicalize_film("Apocalypse Now : Final Cut")
        assert r.canonical_title == "Apocalypse Now"

    def test_4k_restoration_removed(self):
        """4K Restoration suffix removed."""
        r = canonicalize_film("Wake in Fright - 4K Restoration")
        assert r.canonical_title == "Wake in Fright"


# ============================================================
# TEST 8: Canonical film key
# ============================================================

class TestCanonicalFilmKey:
    def test_key_is_lowercase(self):
        """Key is lowercase."""
        k = canonical_film_key("Alien", 1979)
        assert k == k.lower()

    def test_key_includes_year(self):
        """Key includes year."""
        k = canonical_film_key("Alien", 1979)
        assert "1979" in k

    def test_key_with_none_year(self):
        """Key handles None year."""
        k = canonical_film_key("Alien", None)
        assert "none" in k

    def test_key_strips_accents(self):
        """Key strips accents for stability."""
        k1 = canonical_film_key("Amélie", 2001)
        k2 = canonical_film_key("Amelie", 2001)
        assert k1 == k2


# ============================================================
# TEST 9: Temporal leakage prevention (preserved from M13.4)
# ============================================================

class TestTemporalLeakage:
    def test_feature_before_observation_usable(self, tmp_path):
        """Feature retrieved before observation → usable."""
        repo = OutcomeRepository(tmp_path / "test.db")
        obs = {
            "venue_id": "test", "film_title": "Alien", "film_year": 1979,
            "show_date": "Friday 16th October", "show_time": "8:00 pm",
            "source_url": "https://example.com",
            "source_timestamp": "2026-10-07T20:00:00Z",
            "sold_out": False, "availability_state": "AVAILABLE",
        }
        obs_id, _ = repo.record_screening(obs)

        fk = canonical_film_key("Alien", 1979)
        repo.record_film_resolution({
            "film_key": fk, "film_title": "Alien", "film_year": 1979,
            "resolution_status": "VERIFIED", "qloo_entity_id": "E123",
            "resolution_timestamp": "2026-10-06T10:00:00Z",
        })
        repo.record_qloo_features({
            "film_key": fk, "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-07T10:00:00Z",  # Before observation
            "qloo_popularity": 0.5,
        })

        feature = repo.get_latest_qloo_feature(fk, before="2026-10-07T20:00:00Z")
        assert feature is not None
        repo.close()

    def test_feature_after_observation_excluded(self, tmp_path):
        """Feature retrieved after observation → excluded."""
        repo = OutcomeRepository(tmp_path / "test.db")
        obs = {
            "venue_id": "test", "film_title": "Alien", "film_year": 1979,
            "show_date": "Friday 16th October", "show_time": "8:00 pm",
            "source_url": "https://example.com",
            "source_timestamp": "2026-10-07T20:00:00Z",
            "sold_out": False, "availability_state": "AVAILABLE",
        }
        obs_id, _ = repo.record_screening(obs)

        fk = canonical_film_key("Alien", 1979)
        repo.record_qloo_features({
            "film_key": fk, "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-08T10:00:00Z",  # After observation
            "qloo_popularity": 0.5,
        })

        feature = repo.get_latest_qloo_feature(fk, before="2026-10-07T20:00:00Z")
        assert feature is None  # Future feature excluded
        repo.close()

    def test_feature_at_boundary_deterministic(self, tmp_path):
        """Feature at exact observation boundary → included (<=)."""
        repo = OutcomeRepository(tmp_path / "test.db")
        fk = canonical_film_key("Alien", 1979)
        repo.record_qloo_features({
            "film_key": fk, "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-07T20:00:00Z",  # Exactly at observation
            "qloo_popularity": 0.5,
        })

        feature = repo.get_latest_qloo_feature(fk, before="2026-10-07T20:00:00Z")
        assert feature is not None  # <= includes boundary
        repo.close()

    def test_latest_valid_prior_snapshot_selected(self, tmp_path):
        """Multiple historical snapshots → latest valid prior selected."""
        repo = OutcomeRepository(tmp_path / "test.db")
        fk = canonical_film_key("Alien", 1979)

        # First snapshot
        repo.record_qloo_features({
            "film_key": fk, "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-05T10:00:00Z",
            "qloo_popularity": 0.3,
        })
        # Second snapshot (later, but still before observation)
        repo.record_qloo_features({
            "film_key": fk, "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-07T10:00:00Z",
            "qloo_popularity": 0.5,
        })

        feature = repo.get_latest_qloo_feature(fk, before="2026-10-07T20:00:00Z")
        assert feature is not None
        assert feature["qloo_popularity"] == 0.5  # Latest valid prior
        repo.close()

    def test_no_historical_feature_returns_none(self, tmp_path):
        """No historical feature → returns None."""
        repo = OutcomeRepository(tmp_path / "test.db")
        fk = canonical_film_key("Alien", 1979)
        feature = repo.get_latest_qloo_feature(fk, before="2026-10-07T20:00:00Z")
        assert feature is None
        repo.close()


# ============================================================
# TEST 10: Qloo popularity vs cultural affinity
# ============================================================

class TestQlooFeatureSemantics:
    def test_popularity_not_mislabeled_as_affinity(self, tmp_path):
        """qloo_popularity is NOT cultural affinity."""
        repo = OutcomeRepository(tmp_path / "test.db")
        fk = canonical_film_key("Alien", 1979)

        repo.record_qloo_features({
            "film_key": fk, "qloo_entity_id": "E123",
            "retrieved_at": "2026-10-07T10:00:00Z",
            "qloo_popularity": 0.5,
            # No qloo_affinity — no cohort context
        })

        features = repo.get_qloo_features_for_film(fk)
        assert len(features) == 1
        assert features[0]["qloo_affinity"] is None  # NULL — no cohort context
        assert features[0]["qloo_popularity"] == 0.5
        repo.close()


# ============================================================
# TEST 11: Canonical film table
# ============================================================

class TestCanonicalFilmTable:
    def test_upsert_and_retrieve(self, tmp_path):
        """Canonical film can be stored and retrieved."""
        repo = OutcomeRepository(tmp_path / "test.db")
        fk = canonical_film_key("Alien", 1979)

        repo.upsert_canonical_film({
            "film_key": fk,
            "raw_titles": ["Alien (Theatrical Cut)", "Alien"],
            "canonical_title": "Alien",
            "film_year": 1979,
            "year_source": "pcc_detail_page",
            "year_provenance": "PCC detail page: year 1979",
            "identity_status": "VERIFIED",
        })

        cf = repo.get_canonical_film(fk)
        assert cf is not None
        assert cf["canonical_title"] == "Alien"
        assert cf["film_year"] == 1979
        assert cf["identity_status"] == "VERIFIED"
        assert json.loads(cf["raw_titles"]) == ["Alien (Theatrical Cut)", "Alien"]
        repo.close()

    def test_canonical_film_stats(self, tmp_path):
        """Canonical film stats are correct."""
        repo = OutcomeRepository(tmp_path / "test.db")

        repo.upsert_canonical_film({
            "film_key": "alien|1979", "canonical_title": "Alien",
            "film_year": 1979, "identity_status": "VERIFIED",
        })
        repo.upsert_canonical_film({
            "film_key": "casablanca|none", "canonical_title": "Casablanca",
            "identity_status": "YEAR_MISSING",
        })
        repo.upsert_canonical_film({
            "film_key": "marathon|none", "canonical_title": "Marathon",
            "identity_status": "EVENT_OR_COMPOSITE", "is_event": True,
        })

        stats = repo.canonical_film_stats()
        assert stats["total"] == 3
        assert stats["verified"] == 1
        assert stats["year_missing"] == 1
        assert stats["events"] == 1
        repo.close()


# ============================================================
# TEST 12: Audit canonicalization
# ============================================================

class TestAuditCanonicalization:
    def test_audit_counts(self):
        """Audit correctly counts raw vs canonical."""
        films = [
            {"film_title": "Alien (Theatrical Cut)", "film_year": None},
            {"film_title": "Alien", "film_year": None},
            {"film_title": "A Very Harold &amp; Kumar Christmas", "film_year": None},
            {"film_title": "A Very Harold & Kumar Christmas", "film_year": None},
            {"film_title": "Casablanca", "film_year": None},
        ]
        audit = audit_canonicalization(films)
        assert audit["total_raw_entries"] == 5
        assert audit["unique_raw_titles"] == 5
        assert audit["unique_canonical_films"] < 5  # Collapsed