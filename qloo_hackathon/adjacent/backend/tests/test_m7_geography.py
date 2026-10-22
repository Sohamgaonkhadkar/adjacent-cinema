"""M7 tests — Geography parsing, Programme Bet, Test Card."""

import json

from backend.app.domain.geography import (
    GeographyResult,
    HeatmapCellResult,
    build_geography_result,
)
from backend.app.domain.programme_bet import ProgrammeBet, build_programme_bet
from backend.app.domain.test_card import TestCard as CardResult, build_test_card
from backend.app.qloo.models import parse_entity_affinity, parse_heatmap, parse_tag_affinity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_heatmap_cell(lat, lng, affinity, geohash="gcabcd"):
    """Create a mock HeatmapCell-like object matching Qloo models.HeatmapCell."""
    from unittest.mock import MagicMock
    cell = MagicMock()
    cell.lat = lat
    cell.lng = lng
    cell.geohash = geohash
    cell.affinity = affinity
    cell.affinity_rank = 1
    cell.popularity = 0.3
    cell.raw = None
    return cell


def _mock_heatmap_response(cell_count: int = 15):
    """Create a mock HeatmapResponse-like object."""
    from unittest.mock import MagicMock
    cells = [_make_heatmap_cell(51.5 + i * 0.01, -0.1 + i * 0.01,
                                0.5 + i * 0.02, f"gc{i:04d}")
             for i in range(cell_count)]

    response = MagicMock()
    response.results = cells  # HeatmapResponse.results is list[HeatmapCell]
    response.locality = None
    response.call_id = "call_geography_001"
    response.boundary = None
    return response


def _make_scored_tag(tag_id, name, affinity, popularity=0.5):
    """Create a mock ScoredTag-like object."""
    from unittest.mock import MagicMock

    from backend.app.qloo.models import band_for
    tag = MagicMock()
    tag.tag_id = tag_id
    tag.name = name
    tag.affinity = affinity
    tag.popularity = popularity
    tag.band = band_for(affinity)
    tag.subtype = "urn:tag:genre"
    tag.parent_type = None
    tag.raw = None
    return tag


def _make_cohort(cohort_id, domain, affinity, name, count=5):
    """Create a realistic CandidateCohort-like object for Programme Bet."""
    from unittest.mock import MagicMock

    from backend.app.qloo.models import band_for

    members = []
    for i in range(count):
        member_affinity = max(0.0, affinity - i * 0.05)
        m = MagicMock()
        m.entity_id = f"entity_{cohort_id}_{i}"
        m.name = f"{name} Member {i}"
        m.affinity = member_affinity
        m.band = band_for(member_affinity)
        m.popularity = 0.5
        m.call_id = f"call_{cohort_id}"
        m.is_marginal = member_affinity < 0.6
        members.append(m)

    score = MagicMock()
    score.context_id = f"ctx_{cohort_id}"
    score.call_id = f"call_{cohort_id}"
    score.mean_affinity = affinity
    score.max_affinity = affinity
    score.min_affinity = affinity * 0.5
    score.median_popularity = 0.5
    score.novelty_proxy = 0.5
    score.qualifying_members = count
    score.total_members = count
    score.member_affinities = tuple(m.affinity for m in members)
    score.partial = False

    cohort = MagicMock()
    cohort.cohort_id = cohort_id
    cohort.domain = domain
    cohort.kind = "entity_cohort"
    cohort.rank = 1
    cohort.member_count = count
    cohort.members = members
    cohort.score = score
    cohort.verdict = MagicMock(reason_code="accept")
    cohort.rejected = False
    cohort.rejection = None

    return cohort


# ---------------------------------------------------------------------------
# Geography tests
# ---------------------------------------------------------------------------


class TestBuildGeographyResult:
    """Test the geography tool's parsing logic."""

    def test_parses_cells_correctly(self):
        resp = _mock_heatmap_response(15)
        result = build_geography_result("London, UK", resp, "call_001")

        assert isinstance(result, GeographyResult)
        assert result.city == "London, UK"
        assert result.call_id == "call_001"
        assert result.total_cells == 15
        assert result.data_status == "measured"

    def test_cells_have_coordinates(self):
        resp = _mock_heatmap_response(5)
        result = build_geography_result("London, UK", resp, "call_002")

        for cell in result.cells:
            assert isinstance(cell, HeatmapCellResult)
            assert 51.0 <= cell.latitude <= 52.0
            assert -1.0 <= cell.longitude <= 0.0
            assert cell.geohash
            assert 0.0 <= cell.affinity <= 1.0

    def test_highest_affinity_sorted_desc(self):
        resp = _mock_heatmap_response(20)
        result = build_geography_result("London, UK", resp, "call_003")

        affinities = [c.affinity for c in result.highest_affinity_cells]
        assert affinities == sorted(affinities, reverse=True)

    def test_top_10_highest_affinity(self):
        resp = _mock_heatmap_response(50)
        result = build_geography_result("London, UK", resp, "call_004")

        assert len(result.highest_affinity_cells) == 10
        assert result.total_cells == 50

    def test_insufficient_cells(self):
        resp = _mock_heatmap_response(3)
        result = build_geography_result("London, UK", resp, "call_005")

        assert not result.sufficient
        assert result.total_cells == 3
        assert "3 cells" in result.note

    def test_empty_heatmap(self):
        from unittest.mock import MagicMock
        resp = MagicMock()
        resp.results = []
        resp.locality = None
        resp.call_id = "call_006"

        result = build_geography_result("London, UK", resp, "call_006")
        assert not result.sufficient
        assert result.total_cells == 0
        assert len(result.cells) == 0

    def test_sufficient_threshold(self):
        resp = _mock_heatmap_response(10)
        result = build_geography_result("London, UK", resp, "call_007")
        assert result.sufficient

        resp2 = _mock_heatmap_response(9)
        result2 = build_geography_result("London, UK", resp2, "call_008")
        assert not result2.sufficient

    def test_to_dict(self):
        resp = _mock_heatmap_response(12)
        result = build_geography_result("London, UK", resp, "call_009")

        d = result.to_dict()
        assert d["city"] == "London, UK"
        assert d["total_cells"] == 12
        assert d["data_status"] == "measured"
        assert d["call_id"] == "call_009"
        assert len(d["highest_affinity_cells"]) == 10
        assert "latitude" in d["highest_affinity_cells"][0]
        assert "longitude" in d["highest_affinity_cells"][0]
        assert "affinity" in d["highest_affinity_cells"][0]

    def test_zero_and_missing_affinity_remain_distinct(self):
        parsers = (
            (parse_entity_affinity, "entities"),
            (parse_tag_affinity, "tags"),
            (parse_heatmap, "heatmap"),
        )
        for parser, collection in parsers:
            common = {
                "call_id": "affinity-test",
                "source": "qloo",
                "data_status": "measured",
                "endpoint": "/v2/insights",
            }
            zero_payload = {
                "results": {
                    collection: [
                        {
                            "id": "item-1",
                            "name": "Zero score",
                            "location": {"latitude": 51.5, "longitude": -0.1},
                            "query": {"affinity": 0.0},
                            "affinity": 0.75,
                        }
                    ]
                }
            }
            missing_payload = {
                "results": {
                    collection: [
                        {
                            "id": "item-2",
                            "name": "Missing score",
                            "location": {"latitude": 51.6, "longitude": -0.2},
                            "query": {},
                        }
                    ]
                }
            }
            assert parser(zero_payload, **common).results[0].affinity == 0.0
            assert parser(missing_payload, **common).results[0].affinity is None

        response = parse_heatmap(
            {
                "results": {
                    "heatmap": [
                        {
                            "location": {"latitude": 51.5, "longitude": -0.1},
                            "query": {"affinity": 0.0},
                        },
                        {
                            "location": {"latitude": 51.6, "longitude": -0.2},
                            "query": {},
                        },
                    ]
                }
            },
            call_id="heatmap-affinity-test",
            source="qloo",
            data_status="measured",
            endpoint="/v2/insights",
        )
        result = build_geography_result("London, UK", response)
        assert [cell.affinity for cell in result.cells] == [0.0, None]
        assert [cell.affinity for cell in result.highest_affinity_cells] == [0.0]
        assert result.total_cells == 2
        assert not result.sufficient
        assert result.to_dict()["highest_affinity_cells"][0]["affinity"] == 0.0

    def test_to_dict_is_json_serialisable(self):
        resp = _mock_heatmap_response(12)
        result = build_geography_result("London, UK", resp, "call_010")
        json.dumps(result.to_dict())


# ---------------------------------------------------------------------------
# Programme Bet tests
# ---------------------------------------------------------------------------


class TestProgrammeBet:
    """Test the Programme Bet engine."""

    def test_basic_bet(self):
        ranked = [_make_cohort("c1", "urn:entity:book", 0.65, "Literary Fiction")]
        tags = [_make_scored_tag("t1", "Art House", 0.7)]
        bet = build_programme_bet(
            ranked_cohorts=ranked,
            taste_tags=tags,
            geography=None,
            resolved_names=["Perfect Days"],
        )

        assert bet is not None
        assert isinstance(bet, ProgrammeBet)
        assert bet.primary_domain == "book"
        assert bet.primary_cohort_name == "Literary Fiction Member 0"
        assert bet.primary_mean_affinity == 0.65
        assert "Art House" in bet.cultural_bridge
        assert "if" in bet.falsification_condition.lower()

    def test_two_cohorts_primary_and_runner_up(self):
        ranked = [
            _make_cohort("c1", "urn:entity:book", 0.65, "Literary Fiction"),
            _make_cohort("c2", "urn:entity:music", 0.55, "Jazz"),
        ]
        bet = build_programme_bet(
            ranked_cohorts=ranked,
            taste_tags=[],
            geography=None,
            resolved_names=["Perfect Days", "Paris Texas"],
        )

        assert bet.primary_domain == "book"
        assert bet.runner_up_domain == "music"
        assert bet.runner_up_cohort_name == "Jazz Member 0"

    def test_no_cohorts_returns_none(self):
        bet = build_programme_bet(
            ranked_cohorts=[],
            taste_tags=[],
            geography=None,
            resolved_names=["Perfect Days"],
        )
        assert bet is None

    def test_falsification_is_concrete(self):
        ranked = [_make_cohort("c1", "urn:entity:book", 0.65, "Literary Fiction")]
        bet = build_programme_bet(
            ranked_cohorts=ranked,
            taste_tags=[],
            geography=None,
            resolved_names=["Perfect Days"],
        )

        assert bet is not None
        assert "if" in bet.falsification_condition.lower()
        assert "rejected" in bet.falsification_condition.lower()
        assert "book" in bet.falsification_condition.lower()

    def test_geographic_signal_with_geography(self):
        geo = GeographyResult(
            city="London, UK",
            city_display="London, Greater London",
            cells=[
                HeatmapCellResult(51.5, -0.1, 0.8, "gc", None, None, "call_geo"),
                HeatmapCellResult(51.6, -0.2, 0.7, "gd", None, None, "call_geo"),
            ],
            total_cells=2,
            highest_affinity_cells=[
                HeatmapCellResult(51.5, -0.1, 0.8, "gc", None, None, "call_geo"),
            ],
            call_id="call_geo",
            data_status="measured",
            sufficient=False,
        )

        ranked = [_make_cohort("c1", "urn:entity:book", 0.65, "Literary Fiction")]
        bet = build_programme_bet(
            ranked_cohorts=ranked,
            taste_tags=[],
            geography=geo,
            resolved_names=["Perfect Days"],
        )

        assert bet is not None
        assert "2 cells" in bet.geographic_signal
        assert bet.geography_call_id is None  # not sufficient → no call_id

    def test_geographic_signal_without_geography(self):
        ranked = [_make_cohort("c1", "urn:entity:book", 0.65, "Literary Fiction")]
        bet = build_programme_bet(
            ranked_cohorts=ranked,
            taste_tags=[],
            geography=None,
            resolved_names=["Perfect Days"],
        )

        assert bet is not None
        assert "not available" in bet.geographic_signal.lower()

    def test_to_dict_nested_structure(self):
        ranked = [_make_cohort("c1", "urn:entity:book", 0.65, "Literary Fiction")]
        bet = build_programme_bet(
            ranked_cohorts=ranked,
            taste_tags=[],
            geography=None,
            resolved_names=["Perfect Days"],
        )

        d = bet.to_dict()
        assert d["primary"]["domain"] == "book"
        assert d["data_status"] == "measured"
        assert "falsification_condition" in d
        assert "why" in d
        assert "cultural_bridge" in d
        json.dumps(d)

    def test_programming_direction_mentions_domain(self):
        ranked = [_make_cohort("c1", "urn:entity:book", 0.65, "Literary Fiction")]
        bet = build_programme_bet(
            ranked_cohorts=ranked,
            taste_tags=[_make_scored_tag("t1", "Art House", 0.7)],
            geography=None,
            resolved_names=["Perfect Days"],
        )

        assert bet is not None
        assert "book" in bet.programming_direction.lower()


# ---------------------------------------------------------------------------
# Test Card tests
# ---------------------------------------------------------------------------


class TestTestCard:
    """Test the Test Card builder."""

    def test_builds_from_bet(self):
        ranked = [_make_cohort("c1", "urn:entity:book", 0.65, "Literary Fiction")]
        bet = build_programme_bet(
            ranked_cohorts=ranked,
            taste_tags=[_make_scored_tag("t1", "Art House", 0.7)],
            geography=None,
            resolved_names=["Perfect Days", "Paris Texas"],
        )
        assert bet is not None

        card = build_test_card(bet, ["Perfect Days", "Paris Texas"], "London, UK")
        assert isinstance(card, CardResult)
        assert "Book" in card.title
        assert "London" in card.title
        assert "2 film" in card.programme_context
        assert card.audience_hypothesis
        assert card.falsification_condition
        assert card.provenance["primary_call_id"]

    def test_serialisable(self):
        ranked = [_make_cohort("c1", "urn:entity:book", 0.65, "Literary Fiction")]
        bet = build_programme_bet(
            ranked_cohorts=ranked,
            taste_tags=[],
            geography=None,
            resolved_names=["Perfect Days"],
        )
        assert bet is not None

        card = build_test_card(bet, ["Perfect Days"], "London, UK")
        d = card.to_dict()
        json.dumps(d)

        assert d["data_status"] == "measured"
        assert d["title"]
        assert d["falsification_condition"]

    def test_provenance_tracks_call_ids(self):
        ranked = [_make_cohort("c1", "urn:entity:book", 0.65, "Literary Fiction")]
        bet = build_programme_bet(
            ranked_cohorts=ranked,
            taste_tags=[],
            geography=None,
            resolved_names=["Perfect Days"],
        )
        assert bet is not None

        card = build_test_card(bet, ["Perfect Days"], "London, UK")
        assert "primary_call_id" in card.provenance
        assert "data_status" in card.provenance
