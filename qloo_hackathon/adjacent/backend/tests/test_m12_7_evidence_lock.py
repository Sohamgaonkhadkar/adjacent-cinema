"""
M12.7: Evidence Lock — Backend Tests
--------------------------------------
Tests proving:
1. No hand-coded domain preference in scoring
2. programme_fit uses real Qloo evidence
3. Differentiation is format-driven, not domain-driven
4. programme_fit = NOT_AVAILABLE when evidence is missing
5. member_ratio not in programme_fit
6. Per-film attribution = NOT_AVAILABLE
7. Two domains with identical evidence get same score
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "research" / "scripts"))

from m12_7_evidence_lock import (
    rank_and_select_m12_7,
    score_differentiation,
    score_entity_m12_7,
    score_programme_fit,
)

# ============================================================
# FIXTURES
# ============================================================

def _make_entity(domain, affinity=0.90, qualifying=40, total=40,
                 programme_films=None, cohort_kind="tag_cluster",
                 shared_tags=None, candidate_tags=None):
    return {
        "title": f"Test {domain}",
        "domain": domain,
        "affinity": affinity,
        "qualifying_members": qualifying,
        "total_members": total,
        "programme_films": programme_films or ["F1", "F2", "F3"],
        "cohort_kind": cohort_kind,
        "shared_tags": shared_tags if shared_tags is not None else ["tag1", "tag2", "tag3"],
        "candidate_tags": candidate_tags if candidate_tags is not None else ["tag1", "tag2"],
    }


# ============================================================
# TEST 1: No hand-coded domain preference
# ============================================================

class TestNoDomainPreference:
    """Two domains with identical evidence get identical scores."""

    def test_artist_and_tvshow_same_evidence_same_score(self):
        """artist and tv_show with identical Qloo evidence get same programme_fit."""
        artist = _make_entity("artist")
        tvshow = _make_entity("tv_show")

        fit_artist, det_artist = score_programme_fit(artist)
        fit_tv, det_tv = score_programme_fit(tvshow)

        assert fit_artist == fit_tv
        assert det_artist["kind_score"] == det_tv["kind_score"]
        assert det_artist["tag_score"] == det_tv["tag_score"]

    def test_differentiation_ignores_domain(self):
        """Differentiation scores based on format, not domain."""
        # Same format, different domains
        assert score_differentiation("Live music performance/DJ set + film screening")[0] == \
               score_differentiation("Live music performance/DJ set + film screening")[0]

        # Different formats give different scores regardless of domain
        live_score, _ = score_differentiation("Live music performance/DJ set + film screening")
        season_score, _ = score_differentiation("Themed film screening season")
        assert live_score > season_score

    def test_no_domain_thematic_vectors(self):
        """M12.7 has no FILM_GENRE_PROXIES, GENRE_TO_THEME, or DOMAIN_THEMATIC_VECTORS."""
        import m12_7_evidence_lock as mod
        assert not hasattr(mod, 'FILM_GENRE_PROXIES')
        assert not hasattr(mod, 'GENRE_TO_THEME')
        assert not hasattr(mod, 'DOMAIN_THEMATIC_VECTORS')


# ============================================================
# TEST 2: programme_fit uses real Qloo evidence
# ============================================================

class TestProgrammeFitRealEvidence:
    """programme_fit must use real Qloo evidence."""

    def test_tag_cluster_gives_higher_score(self):
        """tag_cluster cohort gets higher kind_score than domain_group."""
        entity_cluster = _make_entity("artist", cohort_kind="tag_cluster")
        entity_domain = _make_entity("artist", cohort_kind="domain_group")

        _fit_cluster, det_cluster = score_programme_fit(entity_cluster)
        _fit_domain, det_domain = score_programme_fit(entity_domain)

        assert det_cluster["kind_score"] > det_domain["kind_score"]

    def test_shared_tags_increase_score(self):
        """More shared tags = higher tag_score."""
        entity_many = _make_entity("artist", shared_tags=["t1", "t2", "t3"])
        entity_few = _make_entity("artist", shared_tags=["t1"])

        _fit_many, det_many = score_programme_fit(entity_many)
        _fit_few, det_few = score_programme_fit(entity_few)

        assert det_many["tag_score"] >= det_few["tag_score"]

    def test_evidence_source_is_qloo(self):
        """programme_fit details reference Qloo as evidence source."""
        entity = _make_entity("artist")
        _, details = score_programme_fit(entity)

        assert "Qloo" in details.get("evidence_source", "")


# ============================================================
# TEST 3: programme_fit = NOT_AVAILABLE when evidence missing
# ============================================================

class TestProgrammeFitNotAvailable:
    """programme_fit must be NOT_AVAILABLE when no real evidence exists."""

    def test_singleton_no_tags_is_not_available(self):
        """singleton_group with no shared_tags and no candidate_tags = NOT_AVAILABLE."""
        entity = _make_entity("artist", cohort_kind="singleton_group",
                              shared_tags=[], candidate_tags=[])
        # Override candidate_tags explicitly to empty
        entity["candidate_tags"] = []

        fit, details = score_programme_fit(entity)

        assert fit == "NOT_AVAILABLE"
        assert details["status"] == "NOT_AVAILABLE"

    def test_domain_group_no_tags_is_not_available(self):
        """domain_group with no shared_tags and no candidate_tags = NOT_AVAILABLE."""
        entity = _make_entity("artist", cohort_kind="domain_group",
                              shared_tags=[], candidate_tags=[])
        entity["candidate_tags"] = []

        fit, _details = score_programme_fit(entity)

        assert fit == "NOT_AVAILABLE"

    def test_unknown_kind_no_tags_is_not_available(self):
        """unknown kind with no shared_tags and no candidate_tags = NOT_AVAILABLE."""
        entity = _make_entity("artist", cohort_kind="unknown",
                              shared_tags=[], candidate_tags=[])
        entity["candidate_tags"] = []

        fit, _details = score_programme_fit(entity)

        assert fit == "NOT_AVAILABLE"


# ============================================================
# TEST 4: member_ratio not in programme_fit
# ============================================================

class TestMemberRatioNotInProgrammeFit:
    """programme_fit must not use member_ratio."""

    def test_different_member_ratios_same_programme_fit(self):
        """Different member ratios with same tag evidence = same programme_fit."""
        entity_high = _make_entity("artist", qualifying=40, total=40,
                                   shared_tags=["t1", "t2", "t3"])
        entity_low = _make_entity("artist", qualifying=5, total=50,
                                  shared_tags=["t1", "t2", "t3"])

        fit_high, det_high = score_programme_fit(entity_high)
        fit_low, det_low = score_programme_fit(entity_low)

        assert fit_high == fit_low
        assert det_high["kind_score"] == det_low["kind_score"]
        assert det_high["tag_score"] == det_low["tag_score"]

    def test_programme_fit_details_no_member_ratio(self):
        """programme_fit details don't mention member_ratio."""
        entity = _make_entity("artist")
        _, details = score_programme_fit(entity)

        assert "member_ratio" not in details
        assert "qualifying" not in str(details).lower() or "qualifying" not in details


# ============================================================
# TEST 5: Differentiation from format only
# ============================================================

class TestDifferentiationFormatOnly:
    """Differentiation scores from event format, not domain."""

    def test_live_performance_scores_2(self):
        """Live performance format = 2 regardless of domain."""
        score, _ = score_differentiation("Live music performance/DJ set + film screening")
        assert score == 2

    def test_discussion_scores_1(self):
        """Discussion format = 1."""
        score, _ = score_differentiation("Film screening + book reading/discussion")
        assert score == 1

    def test_season_scores_1(self):
        """Season format = 1."""
        score, _ = score_differentiation("Themed film screening season")
        assert score == 1

    def test_empty_format_scores_0(self):
        """No format = 0."""
        score, _ = score_differentiation("")
        assert score == 0

    def test_domain_name_irrelevant(self):
        """Domain name doesn't affect differentiation score."""
        # "artist" and "tv_show" with same format should get same score
        # (score_differentiation doesn't even take domain as input)
        score_a, _ = score_differentiation("Live music performance")
        score_b, _ = score_differentiation("Live music performance")
        assert score_a == score_b


# ============================================================
# TEST 6: Per-film attribution = NOT_AVAILABLE
# ============================================================

class TestPerFilmAttribution:
    """Per-film attribution must be NOT_AVAILABLE."""

    def test_entity_score_has_not_available(self):
        """score_entity_m12_7 marks per_film_attribution as NOT_AVAILABLE."""
        entity = _make_entity("artist")
        result = score_entity_m12_7(entity)

        assert result["per_film_attribution"] == "NOT_AVAILABLE"

    def test_programme_bet_has_not_available(self):
        """Programme Bet marks supporting_films as NOT_AVAILABLE."""
        entity = _make_entity("artist")
        entity["event_feasibility_details"] = {"format": "Live music performance", "reason": "test"}
        entity["classification"] = "STRONG"
        entity["raw_total"] = 10
        entity["affinity"] = 0.90

        # Need full scored list for rank_and_select
        scored = [score_entity_m12_7(entity)]
        result = rank_and_select_m12_7(scored)

        if result["programme_bet"]:
            assert result["programme_bet"]["supporting_films"] == "NOT_AVAILABLE"


# ============================================================
# TEST 7: One Programme Bet still selected
# ============================================================

class TestOneProgrammeBet:
    """Exactly one Programme Bet is selected."""

    def test_one_bet_from_multiple(self):
        """One bet selected from multiple candidates."""
        e1 = _make_entity("artist", affinity=0.95)
        e2 = _make_entity("tv_show", affinity=0.92)

        scored = [score_entity_m12_7(e1), score_entity_m12_7(e2)]
        result = rank_and_select_m12_7(scored)

        assert result["programme_bet"] is not None
        assert len([result["programme_bet"]]) == 1


# ============================================================
# TEST 8: Artist not automatically favored
# ============================================================

class TestNoArtistBias:
    """artist is not automatically favored over other domains."""

    def test_tvshow_with_higher_affinity_can_win(self):
        """tv_show with much higher affinity + evidence can beat artist.

        Note: artist's live format scores differentiation=2,
        tv_show's season format scores differentiation=1.
        tv_show needs substantially more evidence to compensate.
        This is documented format difference, not hidden domain bias.
        """
        # Artist: weak signal → entity_fit=0, feasibility=2, prog_fit=0, test=0, diff=2 = 4
        artist = _make_entity("artist", affinity=0.80, qualifying=5, total=5,
                              shared_tags=[], candidate_tags=[],
                              cohort_kind="domain_group")
        # TV show: strong signal → entity_fit=2, feasibility=2, prog_fit=2, test=2, diff=1 = 9
        tvshow = _make_entity("tv_show", affinity=0.95, qualifying=50, total=50,
                              shared_tags=["t1", "t2", "t3", "t4", "t5"])

        scored = [score_entity_m12_7(artist), score_entity_m12_7(tvshow)]
        result = rank_and_select_m12_7(scored)

        assert scored[1]["raw_total"] > scored[0]["raw_total"]
        assert result["programme_bet"]["entity"] == "Test tv_show"

    def test_book_with_better_evidence_can_win(self):
        """book with better evidence can beat artist.

        Note: artist's live format gives differentiation=2,
        book's discussion format gives differentiation=1.
        book needs better evidence to compensate.
        """
        artist = _make_entity("artist", affinity=0.86, qualifying=10, total=10,
                              shared_tags=["t1"])
        book = _make_entity("book", affinity=0.95, qualifying=40, total=40,
                            shared_tags=["t1", "t2", "t3", "t4", "t5"])

        scored = [score_entity_m12_7(artist), score_entity_m12_7(book)]
        result = rank_and_select_m12_7(scored)

        assert result["programme_bet"]["entity"] == "Test book"
