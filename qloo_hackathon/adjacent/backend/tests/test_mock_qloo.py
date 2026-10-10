"""Fixture-backed client: typed responses, provenance, and the refusal to invent.

These tests are the reason the project can proceed before the API key exists.
They also pin the two behaviours Adjacent is judged on: no fabricated data, and
no recommendation when the evidence does not support one.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from app import evidence
from app.config import Settings
from app.qloo import MockQlooClient, load_fixture
from app.qloo.errors import NotFoundError
from app.qloo.models import (
    Band,
    EntityAffinityResponse,
    HeatmapResponse,
    TagAffinityResponse,
    band_for,
    clears_medium,
)

STRONG = "portland_strong"
INSUFFICIENT = "insufficient_evidence"


def make_client(settings: Settings, fixture: str = STRONG) -> MockQlooClient:
    return MockQlooClient(settings, fixture=fixture, run_id=f"test-{fixture}")


# --- 3/4/5. typed responses -------------------------------------------------


def test_mock_returns_typed_tag_affinity_response(no_key_settings: Settings) -> None:
    client = make_client(no_key_settings)

    async def run() -> TagAffinityResponse:
        response = await client.tags(filter_query="slow observational documentary")
        return response

    response = asyncio.run(run())
    assert isinstance(response, TagAffinityResponse) or hasattr(response, "results")
    assert response.source == "mock"
    assert response.data_status == "fixture"
    assert response.results and isinstance(response.results[0].tag_id, str)


def test_mock_returns_typed_entity_affinity_response(no_key_settings: Settings) -> None:
    fixture = load_fixture(STRONG, fixtures_dir=no_key_settings.fixtures_dir)
    client = make_client(no_key_settings)

    response = asyncio.run(
        client.insights(
            filter_type="urn:entity:artist",
            signal_interests_entities=fixture.entity_ids,
            take=12,
        )
    )
    assert isinstance(response, EntityAffinityResponse)
    assert response.data_status == "fixture"
    assert all(e.affinity is not None for e in response.results)
    # popularity and tags are preserved for provenance
    assert any(e.popularity is not None for e in response.results)
    assert any(e.tags for e in response.results)
    assert all(e.raw for e in response.results), "raw payload must be kept for provenance"


def test_mock_returns_typed_heatmap_response(no_key_settings: Settings) -> None:
    fixture = load_fixture(STRONG, fixtures_dir=no_key_settings.fixtures_dir)
    client = make_client(no_key_settings)

    response = asyncio.run(
        client.insights(
            filter_type="urn:heatmap",
            signal_interests_entities=fixture.entity_ids,
            filter_location_query="Portland, Oregon",
            filter_location_radius=0,
            output_heatmap_boundary="urn:geohash",
        )
    )
    assert isinstance(response, HeatmapResponse)
    assert response.cells
    cell = response.cells[0]
    assert cell.lat is not None and cell.lng is not None
    assert cell.geohash and cell.affinity is not None
    assert response.locality and response.locality.get("state") == "Oregon"
    # The model must state what heatmap cells are, so no UI can overclaim.
    assert any("not counts of people" in n for n in response.notes)


# --- provenance -------------------------------------------------------------


def test_all_mock_responses_are_marked_as_fixture_data(no_key_settings: Settings) -> None:
    fixture = load_fixture(STRONG, fixtures_dir=no_key_settings.fixtures_dir)
    client = make_client(no_key_settings)

    responses = asyncio.run(_collect(client, fixture.entity_ids))
    assert responses
    for response in responses:
        assert response.source == "mock"
        assert response.data_status == "fixture"
        assert response.is_fixture is True


async def _collect(client: MockQlooClient, ids: list[str]) -> list[object]:
    return [
        await client.insights(filter_type="urn:tag", signal_interests_entities=ids),
        await client.insights(filter_type="urn:entity:artist", signal_interests_entities=ids),
        await client.insights(
            filter_type="urn:heatmap",
            signal_interests_entities=ids,
            filter_location_query="Portland, Oregon",
        ),
    ]


def test_fixture_files_declare_they_are_synthetic() -> None:
    for name in (STRONG, INSUFFICIENT):
        fixture = load_fixture(name)
        assert fixture.data.get("_fixture") is True
        notice = fixture.data.get("_fixture_notice", "")
        assert "NOT measured Qloo output" in notice
        assert fixture.description, f"{name} should describe what it is for"


def test_trace_rows_record_source_and_fixture_status(no_key_settings: Settings) -> None:
    fixture = load_fixture(STRONG, fixtures_dir=no_key_settings.fixtures_dir)
    client = make_client(no_key_settings)
    asyncio.run(_collect(client, fixture.entity_ids))
    rows = client.recorder.rows
    assert rows
    assert {r.source for r in rows} == {"mock"}
    assert {r.data_status for r in rows} == {"fixture"}
    assert all(any("SYNTHETIC FIXTURE DATA" in n for n in r.notes) for r in rows)


# --- no fabrication ---------------------------------------------------------


def test_missing_fixture_branch_returns_empty_and_says_so(no_key_settings: Settings) -> None:
    fixture = load_fixture(INSUFFICIENT, fixtures_dir=no_key_settings.fixtures_dir)
    client = make_client(no_key_settings, INSUFFICIENT)

    # urn:entity:place has no branch at all in this fixture, so the mock must
    # return an empty result set with an explanatory note rather than invent data.
    response = asyncio.run(
        client.insights(filter_type="urn:entity:place", signal_interests_entities=fixture.entity_ids or ["x"])
    )
    assert response.results == []
    row = client.recorder.rows[-1]
    assert any("empty result set rather than inventing data" in n for n in row.notes) or any(
        "no fixture branch" in n for n in row.notes
    )


def test_empty_entity_lookup_raises_not_found_like_the_live_api(no_key_settings: Settings) -> None:
    client = make_client(no_key_settings, INSUFFICIENT)
    with pytest.raises(NotFoundError):
        asyncio.run(client.entities(entity_ids=["does-not-exist-0000"]))


def test_backfill_is_detected_and_labelled(no_key_settings: Settings) -> None:
    fixture = load_fixture(STRONG, fixtures_dir=no_key_settings.fixtures_dir)
    client = make_client(no_key_settings)
    asyncio.run(
        client.insights(
            filter_type="urn:entity:artist",
            signal_interests_entities=fixture.entity_ids,
            backfill_cross_domain_take=2,
            take=12,
        )
    )
    row = client.recorder.rows[-1]
    assert row.backfill_detected is True
    assert any("backfill" in n.lower() for n in row.notes)


# --- 10. insufficiency produces no fabricated recommendation ----------------


def test_strong_fixture_yields_multiple_evidence_backed_cohorts() -> None:
    """At least 3 cross-domain candidate groups clear the evidence gate."""
    fixture = load_fixture(STRONG)
    client = MockQlooClient(Settings.from_env(qloo_api_key=None, rate_limit_rps=0.0), fixture=STRONG)

    async def gather() -> dict[str, list]:
        out = {}
        for domain in (
            "urn:entity:artist",
            "urn:entity:movie",
            "urn:entity:tv_show",
            "urn:entity:book",
            "urn:entity:brand",
        ):
            response = await client.insights(
                filter_type=domain, signal_interests_entities=fixture.entity_ids, take=12
            )
            out[domain] = list(response.results)
        return out

    domains = asyncio.run(gather())
    verdicts = {d: evidence.evaluate_cohort(members) for d, members in domains.items()}
    sufficient = [d for d, v in verdicts.items() if v.sufficient]
    insufficient = [d for d, v in verdicts.items() if v.insufficient]

    assert len(sufficient) >= 3, f"expected >=3 cohorts, got {sufficient}"
    assert "urn:entity:brand" in insufficient, "the weak brand cohort must be REJECTED"
    assert verdicts["urn:entity:brand"].reason_code == "weak_evidence"


def test_sub_medium_tags_are_excluded_from_evidence() -> None:
    fixture = load_fixture(STRONG)
    client = MockQlooClient(Settings.from_env(qloo_api_key=None, rate_limit_rps=0.0), fixture=STRONG)

    response = asyncio.run(
        client.insights(filter_type="urn:tag", signal_interests_entities=fixture.entity_ids, take=50)
    )
    sub_medium = [t for t in response.results if not clears_medium(t.affinity)]
    assert sub_medium, "fixture should contain a sub-Medium tag to exercise exclusion"
    verdict = evidence.evaluate_tags(response.results)
    assert verdict.sufficient  # there are tags above Medium
    assert band_for(sub_medium[0].affinity) is Band.LOW
    for tag_id in fixture.expectations["sub_medium_tag_ids"]:
        assert any(t.tag_id == tag_id for t in sub_medium)


def test_insufficient_fixture_produces_no_fabricated_recommendation() -> None:
    """The headline behaviour: say 'not enough evidence' instead of inventing one."""
    fixture = load_fixture(INSUFFICIENT)
    client = MockQlooClient(Settings.from_env(qloo_api_key=None, rate_limit_rps=0.0), fixture=INSUFFICIENT)
    supplied = fixture.entity_ids or ["none"]

    async def gather() -> tuple[list, list, object]:
        artists = await client.insights(
            filter_type="urn:entity:artist", signal_interests_entities=supplied, take=12
        )
        movies = await client.insights(
            filter_type="urn:entity:movie", signal_interests_entities=supplied, take=12
        )
        heatmap = await client.insights(
            filter_type="urn:heatmap",
            signal_interests_entities=supplied,
            filter_location_query="Springfield, Nowhere",
        )
        return list(artists.results), list(movies.results), heatmap

    artists, movies, heatmap = asyncio.run(gather())

    cohort_verdict = evidence.evaluate_cohort_set([artists, movies])
    assert cohort_verdict.insufficient
    assert cohort_verdict.reason_code == "insufficient_cohorts"
    assert cohort_verdict.message == evidence.MSG_NO_ADJACENT_AUDIENCE

    geo_verdict = evidence.evaluate_heatmap(heatmap.results)
    assert geo_verdict.insufficient
    assert geo_verdict.reason_code == "insufficient_heatmap_cells"

    tag_response = asyncio.run(
        client.insights(filter_type="urn:tag", signal_interests_entities=supplied, take=50)
    )
    tag_verdict = evidence.evaluate_tags(tag_response.results)
    assert tag_verdict.insufficient
    assert tag_verdict.message == evidence.MSG_NO_TAGS

    resolution_verdict = evidence.evaluate_programme_resolution(len(supplied))
    assert resolution_verdict.insufficient
    assert resolution_verdict.reason_code == "insufficient_resolved_titles"

    # And the two-sided bet must refuse too.
    bet_verdict = evidence.evaluate_two_sided_bet(0.44, 0.51)
    assert bet_verdict.insufficient
    assert bet_verdict.message == evidence.MSG_WEAK_BET


def test_strong_fixture_supports_a_geographic_claim_and_insufficient_does_not() -> None:
    strong = load_fixture(STRONG)
    weak = load_fixture(INSUFFICIENT)
    assert strong.expectations["geography_claim_supported"] is True
    assert weak.expectations["geography_claim_supported"] is False

    client_strong = MockQlooClient(Settings.from_env(qloo_api_key=None, rate_limit_rps=0.0), fixture=STRONG)
    strong_heat = asyncio.run(
        client_strong.insights(
            filter_type="urn:heatmap",
            signal_interests_entities=strong.entity_ids,
            filter_location_query="Portland, Oregon",
        )
    )
    assert evidence.evaluate_heatmap(strong_heat.results).sufficient


# --- fixture/mock integrity -------------------------------------------------


def test_programme_ids_and_expectations_are_consistent() -> None:
    strong = load_fixture(STRONG)
    assert len(strong.entity_ids) == strong.expectations["resolved_entity_count"]
    assert strong.expectations["min_cross_domain_count"] >= 4
    for weak_name in strong.expectations["weak_candidate_names"]:
        assert weak_name, "weak candidate names must be recorded"


def test_mock_and_fixture_agree_on_entity_ids(no_key_settings: Settings) -> None:
    fixture = load_fixture(STRONG, fixtures_dir=no_key_settings.fixtures_dir)
    client = make_client(no_key_settings)
    response = asyncio.run(client.entities(external_ids={"imdb": ["tt7594358"]}))
    assert {e.entity_id for e in response.results} == set(fixture.entity_ids)
    assert response.requested_external == {"imdb": ["tt7594358"]}


def test_trace_rows_serialise_without_error(no_key_settings: Settings) -> None:
    fixture = load_fixture(STRONG, fixtures_dir=no_key_settings.fixtures_dir)
    client = make_client(no_key_settings)
    asyncio.run(_collect(client, fixture.entity_ids))
    payload = json.loads(client.recorder.to_json())
    assert len(payload) == client.recorder.call_count
    assert all(row["endpoint"] for row in payload)
