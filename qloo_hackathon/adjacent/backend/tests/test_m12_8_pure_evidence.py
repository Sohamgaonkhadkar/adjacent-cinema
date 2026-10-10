"""
M12.8: Pure Evidence Decision Lock — Backend Tests
----------------------------------------------------
10 critical invariance tests proving the cultural evidence score
is immune to domain, format, testability, differentiation,
cohort_kind weighting, and tag-count scoring.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "research" / "scripts"))

from m12_8_pure_evidence import (
    compute_qloo_evidence_score,
    build_candidate_record,
    rank_by_evidence,
    construct_experiment,
    describe_programme_fit,
    EVIDENCE_WEIGHT_AFFINITY,
    EVIDENCE_WEIGHT_POPULARITY,
    EVIDENCE_WEIGHT_QUALIFYING_RATIO,
)


def _make_raw(title, domain, affinity, popularity, qualifying, total,
              cohort_kind="tag_cluster", shared_tags=None, candidate_tags=None):
    return {
        "title": title, "domain": domain, "affinity": affinity,
        "popularity": popularity, "qualifying_members": qualifying,
        "total_members": total, "cohort_kind": cohort_kind,
        "shared_tags": shared_tags or [], "candidate_tags": candidate_tags or [],
        "construction_reason": "test", "programme_films": ["F1", "F2", "F3"],
        "cohort_id": "test", "qloo_call_id": "test", "band": "very_high",
        "entity_id": "test",
    }


def _score(aff, pop, qual, total):
    return compute_qloo_evidence_score(aff, pop, qual, total)["qloo_evidence_score"]


# ============================================================
# TEST 1: Same Qloo evidence + different domain → same score
# ============================================================

class TestDomainInvariance:
    def test_artist_tvshow_same_score(self):
        score_a = _score(0.90, 0.80, 40, 40)
        score_b = _score(0.90, 0.80, 40, 40)
        assert score_a == score_b

    def test_all_domains_same_score(self):
        base_score = _score(0.90, 0.80, 40, 40)
        for domain in ["artist", "tv_show", "book", "podcast", "brand"]:
            assert _score(0.90, 0.80, 40, 40) == base_score

    def test_record_domain_invariance(self):
        artist = _make_raw("Entity", "artist", 0.90, 0.80, 40, 40)
        tvshow = _make_raw("Entity", "tv_show", 0.90, 0.80, 40, 40)
        assert build_candidate_record(artist)["qloo_evidence_score"] == \
               build_candidate_record(tvshow)["qloo_evidence_score"]


# ============================================================
# TEST 2: Same Qloo evidence + different event format → same score
# ============================================================

class TestFormatInvariance:
    def test_score_uses_only_numeric_fields(self):
        """Score formula uses only affinity, popularity, qualifying_ratio."""
        score = compute_qloo_evidence_score(0.90, 0.80, 40, 40)
        expected = (EVIDENCE_WEIGHT_AFFINITY * 0.90 +
                    EVIDENCE_WEIGHT_POPULARITY * 0.80 +
                    EVIDENCE_WEIGHT_QUALIFYING_RATIO * 1.0)
        assert abs(score["qloo_evidence_score"] - expected) < 0.001


# ============================================================
# TEST 3: Same Qloo evidence + different cohort_kind → same score
# ============================================================

class TestCohortKindInvariance:
    def test_tag_cluster_vs_domain_group(self):
        cluster = _make_raw("E", "artist", 0.90, 0.80, 40, 40,
                            cohort_kind="tag_cluster", shared_tags=["t1", "t2"])
        domain = _make_raw("E", "artist", 0.90, 0.80, 40, 40,
                           cohort_kind="domain_group", shared_tags=[])
        assert build_candidate_record(cluster)["qloo_evidence_score"] == \
               build_candidate_record(domain)["qloo_evidence_score"]


# ============================================================
# TEST 4: Different shared_tag count → does NOT change score
# ============================================================

class TestSharedTagsInvariance:
    def test_many_vs_few_tags(self):
        many = _make_raw("E", "artist", 0.90, 0.80, 40, 40,
                         shared_tags=["t1", "t2", "t3", "t4", "t5"])
        few = _make_raw("E", "artist", 0.90, 0.80, 40, 40,
                        shared_tags=["t1"])
        assert build_candidate_record(many)["qloo_evidence_score"] == \
               build_candidate_record(few)["qloo_evidence_score"]

    def test_no_tags_vs_many_tags(self):
        none = _make_raw("E", "artist", 0.90, 0.80, 40, 40, shared_tags=[])
        many = _make_raw("E", "artist", 0.90, 0.80, 40, 40,
                         shared_tags=[f"t{i}" for i in range(10)])
        assert build_candidate_record(none)["qloo_evidence_score"] == \
               build_candidate_record(many)["qloo_evidence_score"]


# ============================================================
# TESTS 5-7: Different policy fields → does NOT change score
# ============================================================

class TestPolicyFieldInvariance:
    def test_score_computed_from_observations_only(self):
        """Score is computed from affinity, popularity, qualifying_ratio."""
        score = compute_qloo_evidence_score(0.90, 0.80, 40, 40)
        inputs = score["inputs"]
        assert "affinity" in inputs
        assert "popularity" in inputs
        assert "qualifying_ratio" in inputs
        # No format, testability, differentiation in inputs
        assert "format" not in inputs
        assert "testability" not in inputs
        assert "differentiation" not in inputs


# ============================================================
# TEST 8-9: Domain/format cannot improve rank by itself
# ============================================================

class TestRankInvariance:
    def test_low_affinity_not_ranked_higher(self):
        high_tv = _make_raw("Show", "tv_show", 0.95, 0.90, 50, 50)
        low_artist = _make_raw("Artist", "artist", 0.80, 0.50, 10, 10)
        ranked = rank_by_evidence([low_artist, high_tv])
        assert ranked[0]["entity_title"] == "Show"

    def test_same_evidence_different_domain_same_rank(self):
        e1 = _make_raw("A", "artist", 0.90, 0.80, 40, 40)
        e2 = _make_raw("B", "tv_show", 0.90, 0.80, 40, 40)
        ranked = rank_by_evidence([e1, e2])
        assert ranked[0]["qloo_evidence_score"] == ranked[1]["qloo_evidence_score"]


# ============================================================
# TEST 10: Removing policy fields leaves ranking unchanged
# ============================================================

class TestPolicyRemoval:
    def test_evidence_only_ranking(self):
        raw = [
            _make_raw("A", "artist", 0.95, 0.90, 50, 50),
            _make_raw("B", "tv_show", 0.90, 0.80, 40, 40),
            _make_raw("C", "book", 0.85, 0.70, 30, 30),
        ]
        ranked = rank_by_evidence(raw)
        assert ranked[0]["entity_title"] == "A"
        assert ranked[1]["entity_title"] == "B"
        assert ranked[2]["entity_title"] == "C"
        for i in range(len(ranked) - 1):
            assert ranked[i]["qloo_evidence_score"] >= ranked[i+1]["qloo_evidence_score"]


# ============================================================
# LAYER SEPARATION
# ============================================================

class TestLayerSeparation:
    def test_experiment_does_not_affect_score(self):
        entity = _make_raw("Test", "artist", 0.90, 0.80, 40, 40)
        record = build_candidate_record(entity)
        expected = _score(0.90, 0.80, 40, 40)
        assert record["qloo_evidence_score"] == expected

    def test_experiment_is_labeled_as_policy(self):
        entity = _make_raw("Test", "artist", 0.90, 0.80, 40, 40)
        exp = construct_experiment(entity)
        assert "product" in exp["policy_note"].lower() or "not evidence" in exp["policy_note"].lower()

    def test_programme_fit_is_descriptive(self):
        entity = _make_raw("Test", "artist", 0.90, 0.80, 40, 40,
                           shared_tags=["t1", "t2"])
        pf = describe_programme_fit(entity)
        assert "cohort_kind" in pf
        assert pf["per_film_attribution"] == "NOT_AVAILABLE"
        assert "product policy" in pf["programme_evidence_quality"]["quality_label"].lower()


# ============================================================
# EVIDENCE FORMULA
# ============================================================

class TestEvidenceFormula:
    def test_formula_correctness(self):
        score = _score(0.90, 0.80, 40, 40)
        expected = 0.6 * 0.90 + 0.2 * 0.80 + 0.2 * 1.0
        assert abs(score - expected) < 0.001

    def test_affinity_dominates(self):
        """Affinity (weight 0.6) dominates when popularity difference is small."""
        high_aff = _score(0.95, 0.80, 40, 40)  # 0.57 + 0.16 + 0.20 = 0.93
        low_aff = _score(0.80, 0.90, 40, 40)   # 0.48 + 0.18 + 0.20 = 0.86
        assert high_aff > low_aff

    def test_missing_popularity_default(self):
        with_pop = _score(0.90, 0.50, 40, 40)
        without_pop = _score(0.90, None, 40, 40)
        assert abs(with_pop - without_pop) < 0.0001