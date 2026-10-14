"""Tests for two-sided Programme Bet (M11.3: scientifically accurate)."""

from app.domain.programme_bet import build_programme_bet


class MockMember:
    def __init__(self, name: str, entity_id: str = "test"):
        self.name = name
        self.entity_id = entity_id


class MockScore:
    def __init__(self, mean_affinity: float, call_id: str = "test-call"):
        self.mean_affinity = mean_affinity
        self.max_affinity = mean_affinity + 0.1
        self.novelty_proxy = 0.5
        self.call_id = call_id


class MockVerdict:
    def __init__(self):
        self.reason_code = "strong"
        self.sufficient = True


class MockCohort:
    def __init__(
        self,
        cohort_id: str,
        domain: str,
        members: list,
        score: MockScore | None = None,
    ):
        self.cohort_id = cohort_id
        self.domain = domain
        self.members = members
        self.score = score
        self.verdict = MockVerdict()
        self.rejection = None

    @property
    def qualifying_members(self):
        return [m for m in self.members if hasattr(m, "affinity") and m.affinity and m.affinity >= 0.5]


class MockScoredMember:
    def __init__(self, name: str, affinity: float, entity_id: str = "test"):
        self.name = name
        self.entity_id = entity_id
        self.affinity = affinity
        self.scored = type("obj", (object,), {
            "entity_id": entity_id,
            "name": name,
            "type": "urn:entity:movie",
            "subtype": None,
            "affinity": affinity,
            "popularity": 0.5,
            "tags": [],
        })()
        self.call_id = "test-call"
        self.is_marginal = affinity < 0.6

    @property
    def band(self):
        if self.affinity >= 0.6:
            return "High"
        elif self.affinity >= 0.5:
            return "Medium"
        return "Low"


class MockGeography:
    def __init__(self):
        self.sufficient = True
        self.city = "London"
        self.city_display = "London"
        self.total_cells = 25
        self.call_id = "geo-call"


class MockTag:
    def __init__(self, name: str):
        self.name = name


class TestBuildProgrammeBet:
    def test_basic_bet(self):
        """Test basic Programme Bet creation."""
        members = [MockScoredMember("Film A", 0.7), MockScoredMember("Film B", 0.6)]
        cohort = MockCohort("test:cohort:1", "urn:entity:movie", members, MockScore(0.65))
        tags = [MockTag("Comedy"), MockTag("Drama")]

        bet = build_programme_bet(
            ranked_cohorts=[cohort],
            taste_tags=tags,
            geography=None,
            resolved_names=["Film A", "Film B"],
        )

        assert bet is not None
        assert bet.primary_domain == "movie"
        assert bet.primary_mean_affinity == 0.65

    def test_programme_adjacency_populated(self):
        """Test that programme adjacency is populated when provided."""
        members = [MockScoredMember("Film A", 0.7), MockScoredMember("Film B", 0.6)]
        cohort = MockCohort("test:cohort:1", "urn:entity:movie", members, MockScore(0.65))

        bet = build_programme_bet(
            ranked_cohorts=[cohort],
            taste_tags=[],
            geography=None,
            resolved_names=["Film A"],
            programme_adjacency_scores={"test:cohort:1": 0.65},
            cohort_breadth_scores={"test:cohort:1": 0.5},
            programme_adjacency_bands={"test:cohort:1": "High"},
            cohort_breadth_bands={"test:cohort:1": "Medium"},
            programme_adjacency_call_ids={"test:cohort:1": "adj-call"},
            cohort_breadth_call_ids={"test:cohort:1": "breadth-call"},
        )

        assert bet is not None
        assert bet.programme_adjacency == 0.65
        assert bet.cohort_breadth == 0.5
        assert bet.adjacency_band == "High"
        assert bet.breadth_band == "Medium"
        assert bet.adjacency_call_id == "adj-call"
        assert bet.breadth_call_id == "breadth-call"

    def test_two_sided_none_when_no_evidence(self):
        """Test that signals are None when no evidence provided."""
        members = [MockScoredMember("Film A", 0.7)]
        cohort = MockCohort("test:cohort:1", "urn:entity:movie", members, MockScore(0.65))

        bet = build_programme_bet(
            ranked_cohorts=[cohort],
            taste_tags=[],
            geography=None,
            resolved_names=["Film A"],
        )

        assert bet is not None
        assert bet.programme_adjacency is None
        assert bet.cohort_breadth is None

    def test_rejected_candidates_included(self):
        """Test that rejected candidates are included."""
        members = [MockScoredMember("Film A", 0.7)]
        cohort = MockCohort("test:cohort:1", "urn:entity:movie", members, MockScore(0.65))

        rejected = MockCohort("test:cohort:2", "urn:entity:book", [], MockScore(0.3))
        rejected.rejected = True
        rejected.rejection = type("Rejection", (), {
            "code": type("Code", (), {"value": "weak_evidence"})(),
            "detail": "Only 1 member above Medium",
        })()

        bet = build_programme_bet(
            ranked_cohorts=[cohort],
            taste_tags=[],
            geography=None,
            resolved_names=["Film A"],
            rejected_cohorts=[rejected],
        )

        assert bet is not None
        assert len(bet.rejected_candidates) == 1
        assert bet.rejected_candidates[0]["reason"] == "weak_evidence"

    def test_geography_signal(self):
        """Test geography signal is included."""
        members = [MockScoredMember("Film A", 0.7)]
        cohort = MockCohort("test:cohort:1", "urn:entity:movie", members, MockScore(0.65))
        geography = MockGeography()

        bet = build_programme_bet(
            ranked_cohorts=[cohort],
            taste_tags=[],
            geography=geography,
            resolved_names=["Film A"],
        )

        assert bet is not None
        assert "London" in bet.geographic_signal
        assert bet.geography_call_id == "geo-call"

    def test_falsification_condition(self):
        """Test that falsification condition is always included."""
        members = [MockScoredMember("Film A", 0.7)]
        cohort = MockCohort("test:cohort:1", "urn:entity:movie", members, MockScore(0.65))

        bet = build_programme_bet(
            ranked_cohorts=[cohort],
            taste_tags=[],
            geography=None,
            resolved_names=["Film A"],
        )

        assert bet is not None
        assert "Do not continue" in bet.falsification_condition

    def test_to_dict_includes_two_sided(self):
        """Test that to_dict() includes two-sided signals."""
        members = [MockScoredMember("Film A", 0.7)]
        cohort = MockCohort("test:cohort:1", "urn:entity:movie", members, MockScore(0.65))

        bet = build_programme_bet(
            ranked_cohorts=[cohort],
            taste_tags=[],
            geography=None,
            resolved_names=["Film A"],
            programme_adjacency_scores={"test:cohort:1": 0.65},
            cohort_breadth_scores={"test:cohort:1": 0.5},
            programme_adjacency_bands={"test:cohort:1": "High"},
            cohort_breadth_bands={"test:cohort:1": "Medium"},
        )

        d = bet.to_dict()
        assert "two_sided_signals" in d
        assert d["two_sided_signals"]["programme_adjacency"] == 0.65
        assert d["two_sided_signals"]["cohort_breadth"] == 0.5
        assert "methodology_note" in d["two_sided_signals"]

    def test_no_cohorts_returns_none(self):
        """Test that empty cohorts returns None."""
        bet = build_programme_bet(
            ranked_cohorts=[],
            taste_tags=[],
            geography=None,
            resolved_names=[],
        )
        assert bet is None

    def test_deterministic(self):
        """Test that same inputs produce same outputs."""
        members = [MockScoredMember("Film A", 0.7)]
        cohort = MockCohort("test:cohort:1", "urn:entity:movie", members, MockScore(0.65))
        kwargs = {
            "ranked_cohorts": [cohort],
            "taste_tags": [MockTag("Comedy")],
            "geography": None,
            "resolved_names": ["Film A"],
            "programme_adjacency_scores": {"test:cohort:1": 0.65},
            "cohort_breadth_scores": {"test:cohort:1": 0.5},
            "programme_adjacency_bands": {"test:cohort:1": "High"},
            "cohort_breadth_bands": {"test:cohort:1": "Medium"},
            "programme_adjacency_call_ids": {"test:cohort:1": "adj-call"},
            "cohort_breadth_call_ids": {"test:cohort:1": "breadth-call"},
        }
        bet1 = build_programme_bet(**kwargs)
        bet2 = build_programme_bet(**kwargs)
        assert bet1.to_dict() == bet2.to_dict()
