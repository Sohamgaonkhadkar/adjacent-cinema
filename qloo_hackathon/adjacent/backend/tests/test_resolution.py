"""Tests for the trusted entity resolver.

Tests 1-4: resolution status tests (always runnable)
Tests 5-6: mismatched/unresolved entity safety tests (always runnable)
Tests 7-10: live-only tests (require QLOO_API_KEY)
"""

from __future__ import annotations

import asyncio
import os

import pytest
from app.agent.budget import Budget
from app.agent.state import AdjacentState, ProgrammeItem
from app.api.routes import _build_result
from app.live_runner import LivePipeline
from app.qloo.models import EntitiesResponse, ScoredEntity, SearchResponse
from app.resolution.contract import MatchMethod, MatchStatus, ResolvedEntity
from app.resolution.resolver import EntityResolver, verify_search_result

_HAS_KEY = bool((os.environ.get("QLOO_API_KEY") or "").strip())

_skip_no_key = pytest.mark.skipif(
    not _HAS_KEY,
    reason="QLOO_API_KEY not available — live tests require a real key",
)

# ---------------------------------------------------------------------------
# §1-4: Resolution status tests (always runnable, no API key needed)
# ---------------------------------------------------------------------------


class TestVerifySearchResult:
    """Test the verification logic against known entity structures."""

    def test_verified_when_title_and_year_match(self):
        entity = {"name": "Perfect Days", "disambiguation": "2023"}
        status, notes = verify_search_result("Perfect Days", 2023, entity)
        assert status == MatchStatus.VERIFIED
        assert any("year matches" in n for n in notes)

    def test_mismatch_when_year_conflicts(self):
        entity = {"name": "Perfect Days", "disambiguation": "2014"}
        status, notes = verify_search_result("Perfect Days", 2023, entity)
        assert status == MatchStatus.MISMATCH
        assert any("year mismatch" in n for n in notes)

    def test_ambiguous_when_input_has_year_but_entity_does_not(self):
        entity = {"name": "Perfect Days", "disambiguation": ""}
        status, notes = verify_search_result("Perfect Days", 2023, entity)
        assert status == MatchStatus.AMBIGUOUS
        assert any("no year" in n.lower() for n in notes)

    def test_mismatch_when_title_differs(self):
        entity = {"name": "The Purple Rose of Cairo", "disambiguation": "1985"}
        status, notes = verify_search_result("Taipei Story", 1985, entity)
        assert status == MatchStatus.MISMATCH
        assert any("title mismatch" in n for n in notes)

    def test_ambiguous_when_no_year_anywhere(self):
        entity = {"name": "Le Samourai", "disambiguation": ""}
        status, notes = verify_search_result("Le Samourai", None, entity)
        assert status == MatchStatus.AMBIGUOUS
        assert any("no year" in n.lower() for n in notes)

    def test_accent_normalisation(self):
        entity = {"name": "Le Samouraï", "disambiguation": "1967"}
        status, notes = verify_search_result("Le Samourai", 1967, entity)
        assert status == MatchStatus.VERIFIED
        assert any("accent" in n.lower() for n in notes)

    def test_year_from_release_year_property(self):
        entity = {
            "name": "Perfect Days",
            "disambiguation": "",
            "properties": {"release_year": 2023},
        }
        status, _notes = verify_search_result("Perfect Days", 2023, entity)
        assert status == MatchStatus.VERIFIED


class TestResolvedEntity:
    """Test the ResolvedEntity contract."""

    def test_resolved_only_when_verified(self):
        for status in MatchStatus:
            entity = ResolvedEntity(
                input_title="test",
                match_status=status,
            )
            if status == MatchStatus.VERIFIED:
                assert entity.resolved is True
                assert entity.usable is True
            else:
                assert entity.resolved is False
                assert entity.usable is False

    def test_to_dict(self):
        entity = ResolvedEntity(
            input_title="Perfect Days",
            input_year=2023,
            qloo_entity_id="abc-123",
            qloo_name="Perfect Days",
            match_status=MatchStatus.VERIFIED,
            match_method=MatchMethod.SEARCH_WITH_YEAR,
        )
        d = entity.to_dict()
        assert d["input_title"] == "Perfect Days"
        assert d["match_status"] == "VERIFIED"
        assert d["match_method"] == "search_with_year"
        assert d["qloo_entity_id"] == "abc-123"

    def test_live_pipeline_preserves_sanitized_resolution_evidence(self):
        class FixedResolver:
            async def resolve_programme(self, _items):
                return [
                    ResolvedEntity(
                        input_title="Perfect Days",
                        input_year=2023,
                        qloo_entity_id="qloo-film-2023",
                        qloo_name="Perfect Days",
                        qloo_entity_type="urn:entity:movie",
                        qloo_year=2023,
                        match_status=MatchStatus.VERIFIED,
                        match_method=MatchMethod.SEARCH_WITH_YEAR,
                        verification_notes=["year matches: 2023"],
                        call_id="resolution-run-c001",
                        related_call_ids=["resolution-run-c002"],
                        raw_result={"private_test_payload": "not exposed"},
                    )
                ]

        state = AdjacentState(
            run_id="resolution-run",
            data_status="measured",
            programme=[
                ProgrammeItem(
                    title="Perfect Days",
                    year=2023,
                    imdb_id=None,
                    declared_entity_id=None,
                )
            ],
        )
        pipeline = LivePipeline(
            object(), FixedResolver(), [{"title": "Perfect Days", "year": 2023}]
        )

        resolved = asyncio.run(pipeline.resolve_programme(state, Budget()))
        payload = _build_result(state, "")
        item = payload["programme"]["items"][0]
        evidence = item["resolution_evidence"]

        assert resolved.resolved == 1
        assert item["resolved"] is True
        assert item["qloo_entity_id"] == "qloo-film-2023"
        assert evidence["match_status"] == "VERIFIED"
        assert evidence["match_method"] == "search_with_year"
        assert evidence["qloo_year"] == 2023
        assert evidence["verification_notes"] == ["year matches: 2023"]
        assert evidence["call_id"] == "resolution-run-c001"
        assert evidence["related_call_ids"] == ["resolution-run-c002"]
        assert state.resolution_call_ids == ["resolution-run-c001", "resolution-run-c002"]
        assert "raw_result" not in evidence
        assert "private_test_payload" not in str(evidence)


# ---------------------------------------------------------------------------
# §5-6: Safety tests (always runnable with mock resolver)
# ---------------------------------------------------------------------------


class TestResolverSafety:
    """Test that mismatches and unresolved entities are safely rejected."""

    def test_mismatch_never_marked_resolved(self):
        """A MISMATCH entity must never be marked as resolved/usable."""
        entity = ResolvedEntity(
            input_title="Taipei Story",
            input_year=1985,
            qloo_name="The Purple Rose of Cairo",
            match_status=MatchStatus.MISMATCH,
        )
        assert entity.resolved is False
        assert entity.usable is False

    def test_unresolved_never_marked_resolved(self):
        entity = ResolvedEntity(
            input_title="Unknown Film",
            match_status=MatchStatus.UNRESOLVED,
        )
        assert entity.resolved is False
        assert entity.usable is False

    def test_ambiguous_never_marked_resolved(self):
        entity = ResolvedEntity(
            input_title="Le Samourai",
            qloo_name="Le Samourai",
            match_status=MatchStatus.AMBIGUOUS,
        )
        assert entity.resolved is False
        assert entity.usable is False

    def test_nonverified_resolution_statuses_never_feed_downstream_calls(self):
        """Mismatched/unresolved/ambiguous IDs stay out of affinity and positioning."""
        statuses = [MatchStatus.UNRESOLVED, MatchStatus.AMBIGUOUS, MatchStatus.MISMATCH]

        class FixedResolver:
            async def resolve_programme(self, _items):
                return [
                    ResolvedEntity(
                        input_title=f"Film {index}",
                        input_year=2000 + index,
                        qloo_entity_id=f"unsafe-qloo-id-{index}",
                        qloo_name=f"Film {index}",
                        match_status=status,
                        verification_notes=[f"fixture status: {status.value}"],
                    )
                    for index, status in enumerate(statuses)
                ]

        class NoCallClient:
            def __init__(self):
                self.calls = 0

            async def insights(self, **_kwargs):
                self.calls += 1
                raise AssertionError("non-verified entities must not reach Qloo calculations")

        state = AdjacentState(
            run_id="nonverified-resolution",
            data_status="measured",
            programme=[
                ProgrammeItem(
                    title=f"Film {index}",
                    year=2000 + index,
                    imdb_id=None,
                    declared_entity_id=None,
                )
                for index in range(len(statuses))
            ],
        )
        client = NoCallClient()
        pipeline = LivePipeline(
            client,
            FixedResolver(),
            [{"title": f"Film {index}", "year": 2000 + index} for index in range(len(statuses))],
        )

        async def run_downstream_gates():
            await pipeline.resolve_programme(state, Budget())
            await pipeline.get_taste_profile(state, Budget())
            await pipeline.expand_candidates(state, Budget())
            await pipeline.rank_cohorts(state, Budget())

        asyncio.run(run_downstream_gates())

        assert state.resolved_ids == []
        assert all(item.resolved_entity_id is None for item in state.programme)
        assert client.calls == 0


# ---------------------------------------------------------------------------
# Offline integration regressions for historical identity edge cases
# ---------------------------------------------------------------------------


class _ResolverClientStub:
    """Offline fixture client; these responses are not live Qloo observations."""

    def __init__(self, *, search_entities: list[ScoredEntity], id_entities: list[ScoredEntity]):
        self.search_entities = search_entities
        self.id_entities = id_entities
        self.search_calls: list[dict[str, object]] = []

    async def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return SearchResponse(
            call_id="search-call-001",
            source="mock",
            data_status="fixture",
            results=self.search_entities,
        )

    async def entities(self, **_kwargs):
        return EntitiesResponse(
            call_id="external-call-001",
            source="mock",
            data_status="fixture",
            results=self.id_entities,
        )


def _qloo_entity(
    entity_id: str,
    name: str,
    year: int | None,
    *,
    imdb_id: str | None = None,
    type_evidence: tuple[str, ...] | None = ("urn:entity:movie",),
) -> ScoredEntity:
    """Build an explicitly labelled synthetic Qloo-shaped entity fixture."""
    raw = {"name": name, "properties": {}}
    entity_type = None
    subtype = None
    if type_evidence is not None:
        raw["types"] = list(type_evidence)
        entity_type = "urn:entity"
        raw["type"] = entity_type
        if type_evidence:
            subtype = type_evidence[0]
            raw["subtype"] = subtype
    if year is not None:
        raw["disambiguation"] = str(year)
        raw["properties"]["release_year"] = year
    if imdb_id:
        raw["external"] = {"imdb": [imdb_id]}
    return ScoredEntity(
        entity_id=entity_id,
        name=name,
        type=entity_type,
        subtype=subtype,
        raw=raw,
    )


class TestHistoricalEntityResolutionRegressions:
    def test_taipei_story_imdb_id_cannot_verify_purple_rose_mapping(self) -> None:
        """A matching IMDb string must not bless a conflicting Qloo entity name."""
        client = _ResolverClientStub(
            search_entities=[],
            id_entities=[
                _qloo_entity(
                    "qloo-purple-rose",
                    "The Purple Rose of Cairo",
                    1985,
                    imdb_id="tt0089853",
                )
            ],
        )
        result = asyncio.run(
            EntityResolver(client, delay_s=0).resolve_item(
                "Taipei Story",
                year=1985,
                external_id="tt0089853",
                external_family="imdb",
            )
        )

        assert result.match_status == MatchStatus.MISMATCH
        assert result.qloo_name == "The Purple Rose of Cairo"
        assert result.resolved is False
        assert result.call_id == "external-call-001"
        assert result.related_call_ids == ["search-call-001"]
        assert {result.call_id, *result.related_call_ids} == {
            "search-call-001",
            "external-call-001",
        }

    def test_verified_external_id_does_not_override_title_search_mismatch(self) -> None:
        """Conflicting search and ID endpoints stay unusable, with both traces."""
        client = _ResolverClientStub(
            search_entities=[
                _qloo_entity(
                    "qloo-purple-rose",
                    "The Purple Rose of Cairo",
                    1985,
                    imdb_id="tt0089853",
                )
            ],
            id_entities=[
                _qloo_entity(
                    "qloo-taipei-story",
                    "Taipei Story",
                    1985,
                    imdb_id="tt0089853",
                )
            ],
        )

        result = asyncio.run(
            EntityResolver(client, delay_s=0).resolve_item(
                "Taipei Story",
                year=1985,
                external_id="tt0089853",
                external_family="imdb",
            )
        )

        assert result.match_status == MatchStatus.MISMATCH
        assert result.resolved is False
        assert result.qloo_name == "The Purple Rose of Cairo"
        assert result.input_external_id == "tt0089853"
        assert result.call_id == "search-call-001"
        assert result.related_call_ids == ["external-call-001"]
        assert any("cannot override" in note for note in result.verification_notes)

    def test_perfect_days_missing_from_qloo_stays_unresolved(self) -> None:
        client = _ResolverClientStub(search_entities=[], id_entities=[])
        result = asyncio.run(
            EntityResolver(client, delay_s=0).resolve_item(
                "Perfect Days",
                year=2023,
                external_id="tt7594358",
                external_family="imdb",
            )
        )

        assert result.match_status == MatchStatus.UNRESOLVED
        assert result.qloo_entity_id is None
        assert result.resolved is False
        assert result.call_id == "search-call-001"
        assert result.related_call_ids == ["external-call-001"]

    def test_exact_perfect_days_search_result_is_verified(self) -> None:
        """Fixture: one explicitly typed movie with an exact title/year match."""
        client = _ResolverClientStub(
            search_entities=[_qloo_entity("qloo-perfect-days", "Perfect Days", 2023)],
            id_entities=[],
        )
        result = asyncio.run(EntityResolver(client, delay_s=0).resolve_item("Perfect Days", year=2023))

        assert result.match_status == MatchStatus.VERIFIED
        assert result.qloo_entity_id == "qloo-perfect-days"
        assert result.qloo_entity_type == "urn:entity:movie"
        assert result.resolved is True
        assert result.call_id == "search-call-001"
        assert client.search_calls[0]["types"] == ["urn:entity:movie"]

    def test_search_result_with_explicit_non_movie_type_is_rejected(self) -> None:
        """Fixture: exact title/year is not enough when Qloo says it is a book."""
        client = _ResolverClientStub(
            search_entities=[
                _qloo_entity(
                    "qloo-book",
                    "Perfect Days",
                    2023,
                    type_evidence=("urn:entity:book",),
                )
            ],
            id_entities=[],
        )

        result = asyncio.run(EntityResolver(client, delay_s=0).resolve_item("Perfect Days", year=2023))

        assert result.match_status == MatchStatus.MISMATCH
        assert result.resolved is False
        assert result.qloo_entity_type == "urn:entity"
        assert any("non-movie entity type" in note for note in result.verification_notes)

    def test_multiple_exact_typed_movies_are_ambiguous_without_an_external_id(self) -> None:
        """Fixture: relevance order alone cannot choose between two exact films."""
        client = _ResolverClientStub(
            search_entities=[
                _qloo_entity("qloo-perfect-days-a", "Perfect Days", 2023),
                _qloo_entity("qloo-perfect-days-b", "Perfect Days", 2023),
            ],
            id_entities=[],
        )

        result = asyncio.run(EntityResolver(client, delay_s=0).resolve_item("Perfect Days", year=2023))

        assert result.match_status == MatchStatus.AMBIGUOUS
        assert result.qloo_entity_id is None
        assert result.resolved is False
        assert any("2 exact typed movie candidates" in note for note in result.verification_notes)

    def test_matching_title_year_without_type_evidence_stays_unresolved(self) -> None:
        """Fixture: an untyped Perfect Days result cannot be assumed to be a film."""
        client = _ResolverClientStub(
            search_entities=[
                _qloo_entity("qloo-untyped-perfect-days", "Perfect Days", 2023, type_evidence=None)
            ],
            id_entities=[],
        )

        result = asyncio.run(EntityResolver(client, delay_s=0).resolve_item("Perfect Days", year=2023))

        assert result.match_status == MatchStatus.UNRESOLVED
        assert result.resolved is False
        assert any("lacks explicit urn:entity:movie" in note for note in result.verification_notes)

    def test_conflicting_type_evidence_is_not_verified(self) -> None:
        """Fixture: movie plus book evidence for one entity is a type conflict."""
        client = _ResolverClientStub(
            search_entities=[
                _qloo_entity(
                    "qloo-conflicting-perfect-days",
                    "Perfect Days",
                    2023,
                    type_evidence=("urn:entity:movie", "urn:entity:book"),
                )
            ],
            id_entities=[],
        )

        result = asyncio.run(EntityResolver(client, delay_s=0).resolve_item("Perfect Days", year=2023))

        assert result.match_status == MatchStatus.MISMATCH
        assert result.resolved is False
        assert any("conflicting Qloo entity-type evidence" in note for note in result.verification_notes)

    def test_matching_imdb_does_not_verify_external_result_without_movie_type(self) -> None:
        """Fixture: echoed IMDb plus title/year still needs explicit movie type evidence."""
        client = _ResolverClientStub(
            search_entities=[],
            id_entities=[
                _qloo_entity(
                    "qloo-untyped-perfect-days",
                    "Perfect Days",
                    2023,
                    imdb_id="tt7594358",
                    type_evidence=None,
                )
            ],
        )

        result = asyncio.run(
            EntityResolver(client, delay_s=0)._resolve_by_external_id(
                "Perfect Days", 2023, "tt7594358", "imdb"
            )
        )

        assert result.match_status == MatchStatus.UNRESOLVED
        assert result.qloo_entity_id == "qloo-untyped-perfect-days"
        assert any("lacks explicit urn:entity:movie" in note for note in result.verification_notes)

    def test_matching_imdb_with_non_movie_type_is_a_mismatch(self) -> None:
        """Fixture: an echoed IMDb ID cannot turn an explicitly typed book into a film."""
        client = _ResolverClientStub(
            search_entities=[],
            id_entities=[
                _qloo_entity(
                    "qloo-book",
                    "Perfect Days",
                    2023,
                    imdb_id="tt7594358",
                    type_evidence=("urn:entity:book",),
                )
            ],
        )

        result = asyncio.run(
            EntityResolver(client, delay_s=0)._resolve_by_external_id(
                "Perfect Days", 2023, "tt7594358", "imdb"
            )
        )

        assert result.match_status == MatchStatus.MISMATCH
        assert result.resolved is False
        assert any("non-movie entity type" in note for note in result.verification_notes)

    def test_external_id_match_without_qloo_entity_id_is_unresolved(self) -> None:
        """Fixture: the echoed ID cannot be corroborated without a Qloo entity ID."""
        client = _ResolverClientStub(
            search_entities=[],
            id_entities=[
                _qloo_entity(
                    "",
                    "Perfect Days",
                    2023,
                    imdb_id="tt7594358",
                )
            ],
        )

        result = asyncio.run(
            EntityResolver(client, delay_s=0)._resolve_by_external_id(
                "Perfect Days", 2023, "tt7594358", "imdb"
            )
        )

        assert result.match_status == MatchStatus.UNRESOLVED
        assert result.qloo_entity_id is None
        assert any("no Qloo entity ID" in note for note in result.verification_notes)

    def test_external_id_can_safely_disambiguate_exact_typed_movies(self) -> None:
        """Fixture: one corroborated, typed IMDb mapping may break a search tie."""
        selected = _qloo_entity("qloo-perfect-days-a", "Perfect Days", 2023, imdb_id="tt7594358")
        client = _ResolverClientStub(
            search_entities=[
                selected,
                _qloo_entity("qloo-perfect-days-b", "Perfect Days", 2023),
            ],
            id_entities=[selected],
        )

        result = asyncio.run(
            EntityResolver(client, delay_s=0).resolve_item(
                "Perfect Days",
                year=2023,
                external_id="tt7594358",
                external_family="imdb",
            )
        )

        assert result.match_status == MatchStatus.VERIFIED
        assert result.match_method == MatchMethod.EXTERNAL_ID
        assert result.qloo_entity_id == "qloo-perfect-days-a"
        assert result.call_id == "external-call-001"
        assert result.related_call_ids == ["search-call-001"]

    def test_search_year_conflict_is_not_overridden_by_an_exact_movie_type(self) -> None:
        """Fixture: explicit movie type cannot override a wrong release year."""
        client = _ResolverClientStub(
            search_entities=[_qloo_entity("qloo-perfect-days-old", "Perfect Days", 2014)],
            id_entities=[],
        )

        result = asyncio.run(EntityResolver(client, delay_s=0).resolve_item("Perfect Days", year=2023))

        assert result.match_status == MatchStatus.MISMATCH
        assert result.qloo_year == 2014
        assert any("year mismatch" in note for note in result.verification_notes)

    def test_matching_external_id_keeps_both_trace_references(self) -> None:
        entity = _qloo_entity(
            "qloo-perfect-days", "Perfect Days", 2023, imdb_id="tt7594358"
        )
        client = _ResolverClientStub(search_entities=[entity], id_entities=[entity])
        result = asyncio.run(
            EntityResolver(client, delay_s=0).resolve_item(
                "Perfect Days",
                year=2023,
                external_id="tt7594358",
                external_family="imdb",
            )
        )

        assert result.match_status == MatchStatus.VERIFIED
        assert result.match_method == MatchMethod.EXTERNAL_ID
        assert result.call_id == "search-call-001"
        assert result.related_call_ids == ["external-call-001"]

    def test_conflicting_imdb_value_is_not_accepted_as_an_external_id_match(self) -> None:
        """A candidate that echoes another IMDb ID contradicts the supplied one."""
        client = _ResolverClientStub(
            search_entities=[],
            id_entities=[
                _qloo_entity(
                    "qloo-perfect-days",
                    "Perfect Days",
                    2023,
                    imdb_id="tt0000000",
                )
            ],
        )
        result = asyncio.run(
            EntityResolver(client, delay_s=0).resolve_item(
                "Perfect Days",
                year=2023,
                external_id="tt7594358",
                external_family="imdb",
            )
        )

        assert result.match_status == MatchStatus.MISMATCH
        assert result.resolved is False
        assert result.qloo_name == "Perfect Days"
        assert result.qloo_year == 2023
        assert any("conflicting ID" in note for note in result.verification_notes)

    def test_matching_imdb_but_conflicting_year_is_rejected(self) -> None:
        client = _ResolverClientStub(
            search_entities=[],
            id_entities=[
                _qloo_entity(
                    "qloo-perfect-days-2014",
                    "Perfect Days",
                    2014,
                    imdb_id="tt7594358",
                )
            ],
        )
        result = asyncio.run(
            EntityResolver(client, delay_s=0).resolve_item(
                "Perfect Days",
                year=2023,
                external_id="tt7594358",
                external_family="imdb",
            )
        )

        assert result.match_status == MatchStatus.MISMATCH
        assert result.qloo_year == 2014
        assert any("year mismatch" in note for note in result.verification_notes)

    def test_external_id_result_must_agree_with_verified_search_entity(self) -> None:
        searched = _qloo_entity("qloo-search-id", "Perfect Days", 2023)
        id_lookup = _qloo_entity(
            "qloo-external-id", "Perfect Days", 2023, imdb_id="tt7594358"
        )
        client = _ResolverClientStub(
            search_entities=[searched],
            id_entities=[id_lookup],
        )

        result = asyncio.run(
            EntityResolver(client, delay_s=0).resolve_item(
                "Perfect Days",
                year=2023,
                external_id="tt7594358",
                external_family="imdb",
            )
        )

        assert result.match_status == MatchStatus.MISMATCH
        assert result.resolved is False
        assert result.qloo_entity_id == "qloo-search-id"
        assert result.call_id == "search-call-001"
        assert result.related_call_ids == ["external-call-001"]
        assert any("external ID conflict" in note for note in result.verification_notes)


# ---------------------------------------------------------------------------
# §7-10: Live-only tests (require QLOO_API_KEY)
# ---------------------------------------------------------------------------


@pytest.mark.live
@_skip_no_key
def test_live_search_resolves_known_films():
    """LIVE QLOO OBSERVATION: /search resolves known arthouse films correctly."""
    import asyncio

    from app.config import Settings
    from app.qloo.client import QlooClient

    async def _run():
        cfg = Settings.from_env()
        client = QlooClient(cfg)
        resolver = EntityResolver(client, delay_s=2.0)

        items = [
            {"title": "Perfect Days", "year": 2023},
            {"title": "The Zone of Interest", "year": 2023},
            {"title": "Taipei Story", "year": 1985},
        ]

        results = await resolver.resolve_programme(items)
        await client.aclose()

        verified = [r for r in results if r.match_status == MatchStatus.VERIFIED]
        assert len(verified) == 3, (
            f"Expected 3 verified, got {len(verified)}: "
            + ", ".join(f"{r.input_title}={r.match_status}" for r in results)
        )

        for r in results:
            assert r.qloo_entity_id is not None, f"{r.input_title} has no entity ID"
            assert r.match_method in (
                MatchMethod.SEARCH,
                MatchMethod.SEARCH_WITH_YEAR,
            ), f"{r.input_title} used unexpected method: {r.match_method}"

    asyncio.run(_run())


@pytest.mark.live
@_skip_no_key
def test_live_search_rejects_wrong_year():
    """LIVE QLOO OBSERVATION: /search detects year mismatches."""
    import asyncio

    from app.config import Settings
    from app.qloo.client import QlooClient

    async def _run():
        cfg = Settings.from_env()
        client = QlooClient(cfg)
        resolver = EntityResolver(client, delay_s=2.0)

        # "Perfect Days" exists for 2023, not 2014
        result = await resolver.resolve_item("Perfect Days", year=2014)
        await client.aclose()

        # Should be MISMATCH (wrong year) or AMBIGUOUS, never VERIFIED
        assert result.match_status != MatchStatus.VERIFIED, (
            f"Expected non-VERIFIED for wrong year, got {result.match_status}"
        )

    asyncio.run(_run())


@pytest.mark.live
@_skip_no_key
def test_live_filter_results_entities_contract():
    """LIVE QLOO OBSERVATION: filter.results.entities scores all candidates in one query."""
    import asyncio

    import httpx
    from app.config import Settings

    async def _run():
        cfg = Settings.from_env()
        headers = {"X-Api-Key": cfg.qloo_api_key}
        base = cfg.qloo_base_url.rstrip("/")

        entity_ids = [
            "3ECAC26F-AC87-4E09-8A54-4B138B8596C6",
            "1EA804CA-FB88-4EC5-95D4-930363E85879",
        ]

        async with httpx.AsyncClient(
            base_url=base, headers=headers, timeout=30
        ) as http:
            # Get candidates
            r = await http.get(
                "/v2/insights",
                params={
                    "filter.type": "urn:entity:artist",
                    "signal.interests.entities": ",".join(entity_ids),
                    "take": 20,
                },
            )
            assert r.status_code == 200
            all_ids = [
                e.get("entity_id")
                for e in r.json().get("results", {}).get("entities", [])
                if e.get("entity_id")
            ]
            assert len(all_ids) >= 5

            # Score them all in one query
            r2 = await http.get(
                "/v2/insights",
                params={
                    "filter.type": "urn:entity:artist",
                    "signal.interests.entities": ",".join(entity_ids),
                    "filter.results.entities": ",".join(all_ids),
                    "take": 50,
                },
            )
            assert r2.status_code == 200
            ents = r2.json().get("results", {}).get("entities", [])
            scored = [
                e
                for e in ents
                if isinstance(e.get("query"), dict)
                and e["query"].get("affinity") is not None
            ]
            assert len(scored) == len(all_ids)

    asyncio.run(_run())


@pytest.mark.live
@_skip_no_key
def test_live_explainability_provenance():
    """LIVE QLOO OBSERVATION: explainability provides per-signal attribution."""
    import asyncio

    import httpx
    from app.config import Settings

    async def _run():
        cfg = Settings.from_env()
        headers = {"X-Api-Key": cfg.qloo_api_key}
        base = cfg.qloo_base_url.rstrip("/")

        async with httpx.AsyncClient(
            base_url=base, headers=headers, timeout=30
        ) as http:
            r = await http.get(
                "/v2/insights",
                params={
                    "filter.type": "urn:entity:artist",
                    "signal.interests.entities": "3ECAC26F-AC87-4E09-8A54-4B138B8596C6",
                    "feature.explainability": "true",
                    "take": 3,
                },
            )
            assert r.status_code == 200
            ents = r.json().get("results", {}).get("entities", [])
            assert len(ents) >= 1

            e = ents[0]
            q = e.get("query", {})
            assert "affinity" in q
            expl = q.get("explainability", {})
            assert isinstance(expl, dict)
            sig = expl.get("signal.interests.entities", [])
            assert len(sig) >= 1
            for attr in sig:
                assert "entity_id" in attr
                assert "score" in attr

    asyncio.run(_run())
