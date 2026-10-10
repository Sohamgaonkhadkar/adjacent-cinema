"""Tests for the trusted entity resolver.

Tests 1-4: resolution status tests (always runnable)
Tests 5-6: mismatched/unresolved entity safety tests (always runnable)
Tests 7-10: live-only tests (require QLOO_API_KEY)
"""

from __future__ import annotations

import os

import pytest
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
