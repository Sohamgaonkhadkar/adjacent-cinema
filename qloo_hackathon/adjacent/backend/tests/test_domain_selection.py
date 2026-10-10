"""Tests for agentic domain selection (M11)."""

from app.domain.domain_selection import (
    ALL_DOMAINS,
    _count_signals,
    _extract_tag_families,
    select_domains,
)


class MockTag:
    """Mock tag for testing."""
    def __init__(self, name: str, tag_id: str = ""):
        self.name = name
        self.tag_id = tag_id


class TestExtractTagFamilies:
    def test_empty_tags(self):
        result = _extract_tag_families([])
        assert result == {}

    def test_single_tag(self):
        tags = [MockTag("Silent film", "urn:tag:genre:media:comedy")]
        result = _extract_tag_families(tags)
        assert "film" in result
        assert "silent" in result
        assert "comedy" in result

    def test_multiple_tags(self):
        tags = [
            MockTag("Music", "urn:tag:genre:media:music"),
            MockTag("Band", "urn:tag:keyword:media:band"),
        ]
        result = _extract_tag_families(tags)
        assert "music" in result
        assert "band" in result


class TestCountSignals:
    def test_no_match(self):
        family_counts = {"film": 1, "comedy": 1}
        signal_families = ("music", "band", "singer")
        count, matching = _count_signals(family_counts, signal_families)
        assert count == 0
        assert matching == ()

    def test_single_match(self):
        family_counts = {"film": 1, "music": 1}
        signal_families = ("music", "band", "singer")
        count, matching = _count_signals(family_counts, signal_families)
        assert count == 1
        assert matching == ("music",)

    def test_multiple_matches(self):
        family_counts = {"film": 1, "music": 1, "band": 1}
        signal_families = ("music", "band", "singer")
        count, matching = _count_signals(family_counts, signal_families)
        assert count == 2
        assert "music" in matching
        assert "band" in matching


class TestSelectDomains:
    def test_empty_tags(self):
        result = select_domains([])
        # Always includes movie
        assert "urn:entity:movie" in result.selected_domains
        assert result.qloo_calls_saved > 0

    def test_film_heavy_programme(self):
        tags = [
            MockTag("Silent film", "urn:tag:genre:media:film"),
            MockTag("Slapstick", "urn:tag:keyword:media:slapstick"),
            MockTag("Physical comedy", "urn:tag:keyword:media:physical_comedy"),
            MockTag("Classic Hollywood", "urn:tag:keyword:media:classic_hollywood"),
        ]
        result = select_domains(tags)
        assert "urn:entity:movie" in result.selected_domains
        # Film tags should select movie domain
        assert "urn:entity:movie" in result.selected_domains

    def test_music_related_programme(self):
        tags = [
            MockTag("Music", "urn:tag:genre:media:music"),
            MockTag("Band", "urn:tag:keyword:media:band"),
            MockTag("Singer", "urn:tag:keyword:media:singer"),
        ]
        result = select_domains(tags)
        assert "urn:entity:artist" in result.selected_domains
        assert "urn:entity:movie" in result.selected_domains  # always included

    def test_book_related_programme(self):
        tags = [
            MockTag("Book", "urn:tag:genre:media:book"),
            MockTag("Literature", "urn:tag:keyword:media:literature"),
            MockTag("Novel", "urn:tag:keyword:media:novel"),
        ]
        result = select_domains(tags)
        assert "urn:entity:book" in result.selected_domains
        assert "urn:entity:movie" in result.selected_domains  # always included

    def test_no_optional_signals(self):
        tags = [
            MockTag("Comedy", "urn:tag:genre:media:comedy"),
            MockTag("Drama", "urn:tag:genre:media:drama"),
        ]
        result = select_domains(tags)
        # Only movie (always included) and tv_show (has comedy/drama signals)
        assert "urn:entity:movie" in result.selected_domains
        assert "urn:entity:tv_show" in result.selected_domains
        # No music, book, brand, destination, podcast signals
        assert "urn:entity:artist" not in result.selected_domains
        assert "urn:entity:book" not in result.selected_domains

    def test_max_domains(self):
        tags = [
            MockTag("Music", "urn:tag:genre:media:music"),
            MockTag("Band", "urn:tag:keyword:media:band"),
            MockTag("Singer", "urn:tag:keyword:media:singer"),
            MockTag("Book", "urn:tag:genre:media:book"),
            MockTag("Literature", "urn:tag:keyword:media:literature"),
        ]
        result = select_domains(tags, max_domains=3)
        # Should include movie (always) + top 2 signal domains
        assert "urn:entity:movie" in result.selected_domains
        assert len(result.selected_domains) <= 3

    def test_deterministic(self):
        tags = [
            MockTag("Music", "urn:tag:genre:media:music"),
            MockTag("Band", "urn:tag:keyword:media:band"),
        ]
        result1 = select_domains(tags)
        result2 = select_domains(tags)
        assert result1.selected_domains == result2.selected_domains
        assert result1.skipped_domains == result2.skipped_domains

    def test_all_decisions_have_reasons(self):
        tags = [
            MockTag("Music", "urn:tag:genre:media:music"),
            MockTag("Book", "urn:tag:genre:media:book"),
        ]
        result = select_domains(tags)
        for selection in result.selections:
            assert selection.reason != ""
            assert selection.domain != ""

    def test_calls_saved(self):
        tags = [MockTag("Music", "urn:tag:genre:media:music")]
        result = select_domains(tags)
        # Should save calls by not querying irrelevant domains
        assert result.qloo_calls_saved > 0
        assert result.qloo_calls_saved == len(ALL_DOMAINS) - len(result.selected_domains)
