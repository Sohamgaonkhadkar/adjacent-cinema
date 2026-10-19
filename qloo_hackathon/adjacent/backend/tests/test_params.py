"""Strict parameter validation.

Reason this file exists: Qloo SILENTLY IGNORES parameters it does not recognise,
so a typo produces an empty result set that looks like "no data". These tests
are the guard against ever shipping one of those.
"""

from __future__ import annotations

import pytest
from app.qloo.errors import (
    DeprecatedParameterError,
    InvalidCombinationError,
    InvalidFilterTypeError,
    InvalidValueError,
    UnverifiedParameterError,
)
from app.qloo.params import (
    EP_AUDIENCES,
    EP_ENTITIES,
    EP_INSIGHTS,
    EP_SEARCH,
    EP_TRENDING,
    EXTERNAL_ID_FAMILIES,
    REGISTRY,
    ParamStatus,
    build_params,
    registry_summary,
    unverified_params,
)

# --- 1. unknown parameter --------------------------------------------------


def test_unknown_parameter_raises() -> None:
    with pytest.raises(UnverifiedParameterError, match="allowlist"):
        build_params(EP_INSIGHTS, {"filter.type": "urn:tag", "made_up_param": "x"})


def test_unknown_parameter_raises_for_kwarg_style_names() -> None:
    with pytest.raises(UnverifiedParameterError):
        build_params(EP_INSIGHTS, {"filter_type": "urn:tag", "signal_interests_entity": ["a"]})


# --- 2. wrong endpoint / wrong combination ---------------------------------


def test_parameter_documented_for_another_endpoint_raises() -> None:
    with pytest.raises(UnverifiedParameterError, match="documented for"):
        build_params(
            EP_TRENDING,
            {
                "filter.type": "urn:entity:movie",
                "filter.start_date": "2026-09-01",
                "filter.end_date": "2026-10-01",
                "filter_results_entities": ["x"],  # /v2/insights only
            },
        )


def test_documented_movie_types_filter_passes_search_allowlist() -> None:
    built = build_params(
        EP_SEARCH,
        {"query": "Perfect Days", "types": ["urn:entity:movie"], "take": 5},
    )

    assert built.params["types"] == ["urn:entity:movie"]
    assert built.as_query()["types"] == "urn:entity:movie"
    assert built.unverified_used == []


def test_results_entities_rejected_for_tag_filter_type() -> None:
    with pytest.raises(InvalidCombinationError, match="ENTITY types"):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:tag",
                "signal.interests.entities": ["a"],
                "filter.results.entities": ["b"],
            },
        )


def test_demographic_signal_rejected_for_tag_filter_type() -> None:
    with pytest.raises(InvalidCombinationError):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:tag",
                "signal.interests.entities": ["a"],
                "signal.demographics.audiences": ["urn:audience:x"],
            },
        )


def test_deprecated_filter_type_raises() -> None:
    with pytest.raises(DeprecatedParameterError, match="DEPRECATED"):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:entity:audience",
                "signal.interests.entities": ["a"],
            },
        )


def test_invalid_filter_type_raises() -> None:
    with pytest.raises(InvalidFilterTypeError):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:entity:sandwich",
                "signal.interests.entities": ["a"],
            },
        )


def test_heatmap_requires_location_and_signal() -> None:
    with pytest.raises(InvalidCombinationError, match=r"filter\.location\.query"):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:heatmap",
                "signal.interests.entities": ["a"],
            },
        )
    with pytest.raises(InvalidCombinationError, match="at least one signal"):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:heatmap",
                "filter.location.query": "Leeds, UK",
            },
        )


def test_heatmap_only_params_rejected_elsewhere() -> None:
    with pytest.raises(InvalidCombinationError, match=r"filter\.type=urn:heatmap"):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:entity:movie",
                "signal.interests.entities": ["a"],
                "filter.location.radius": 0,
            },
        )


# --- unverified parameters --------------------------------------------------


def test_unverified_parameter_raises_without_opt_in() -> None:
    with pytest.raises(UnverifiedParameterError, match="UNVERIFIED"):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:tag",
                "signal.interests.entities": ["a"],
                "filter.parents.types": ["urn:entity:movie"],
            },
        )


def test_unverified_parameter_allowed_with_explicit_opt_in_and_recorded() -> None:
    built = build_params(
        EP_INSIGHTS,
        {
            "filter.type": "urn:tag",
            "signal.interests.entities": ["a"],
            "filter.parents.types": ["urn:entity:movie"],
        },
        allow_unverified=True,
    )
    assert built.unverified_used == ["filter.parents.types"]
    assert any("UNVERIFIED" in w for w in built.warnings)


def test_every_unverified_param_has_an_open_question() -> None:
    for spec in unverified_params():
        assert spec.open_question, f"{spec.name} is UNVERIFIED but records no open question"


# --- value validation -------------------------------------------------------


def test_popularity_range_validated() -> None:
    with pytest.raises(InvalidValueError, match="between 0 and 1"):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:entity:movie",
                "signal.interests.entities": ["a"],
                "filter.popularity.min": 55,
            },
        )


def test_popularity_min_greater_than_max_raises() -> None:
    with pytest.raises(InvalidCombinationError, match="min must be <="):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:entity:movie",
                "signal.interests.entities": ["a"],
                "filter.popularity.min": 0.8,
                "filter.popularity.max": 0.2,
            },
        )


def test_take_cap_enforced() -> None:
    with pytest.raises(InvalidValueError, match="take must be between"):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:entity:movie",
                "signal.interests.entities": ["a"],
                "take": 500,
            },
        )


def test_diversify_by_single_value_only() -> None:
    with pytest.raises(InvalidValueError, match="single value"):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:entity:movie",
                "signal.interests.entities": ["a"],
                "diversify.by": ["urn:tag:genre", "urn:tag:keyword"],
            },
        )


def test_backfill_cap_enforced_and_warned() -> None:
    with pytest.raises(InvalidValueError, match="maximum of 20"):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:entity:movie",
                "signal.interests.entities": ["a"],
                "backfill.cross_domain.take": 99,
            },
        )
    built = build_params(
        EP_INSIGHTS,
        {
            "filter.type": "urn:entity:movie",
            "signal.interests.entities": ["a"],
            "backfill.cross_domain.take": 5,
        },
    )
    assert any("FILLER" in w for w in built.warnings)


def test_required_params_enforced() -> None:
    with pytest.raises(InvalidCombinationError, match="requires"):
        build_params(EP_TRENDING, {"filter.type": "urn:entity:movie"})
    with pytest.raises(InvalidCombinationError, match="requires"):
        build_params("/v2/analysis/compare", {"filter.type": "urn:entity:movie"})


def test_trending_requires_both_dates() -> None:
    with pytest.raises(InvalidCombinationError, match=r"filter\.end_date"):
        build_params(
            EP_TRENDING,
            {
                "filter.type": "urn:entity:movie",
                "filter.start_date": "2026-09-01",
            },
        )


# --- normalisation ----------------------------------------------------------


def test_valid_query_builds_expected_wire_params() -> None:
    built = build_params(
        EP_INSIGHTS,
        {
            "filter.type": "urn:tag",
            "signal.interests.entities": ["a", "b"],
            "take": 50,
        },
    )
    flat = built.as_query()
    assert flat["filter.type"] == "urn:tag"
    assert flat["signal.interests.entities"] == "a,b"
    assert flat["take"] == "50"


def test_booleans_serialise_lowercase() -> None:
    built = build_params(
        EP_INSIGHTS,
        {
            "filter.type": "urn:entity:movie",
            "signal.interests.entities": ["a"],
            "feature.explainability": True,
        },
    )
    assert built.as_query()["feature.explainability"] == "true"


def test_empty_values_are_dropped_not_sent() -> None:
    built = build_params(
        EP_INSIGHTS,
        {
            "filter.type": "urn:entity:movie",
            "signal.interests.entities": ["a"],
            "signal.interests.tags": [],
            "filter.popularity.min": None,
        },
    )
    assert "signal.interests.tags" not in built.params
    assert set(built.dropped_empty) == {"signal.interests.tags", "filter.popularity.min"}


def test_literal_api_key_as_a_param_name_is_rejected() -> None:
    """Defence in depth: a key can never be smuggled into a query string."""
    with pytest.raises(UnverifiedParameterError):
        build_params(EP_INSIGHTS, {"api_key": "whatever", "filter.type": "urn:tag"})


# --- registry integrity -----------------------------------------------------


def test_registry_has_no_duplicates_and_all_are_covered() -> None:
    rows = registry_summary()
    names = [r["param"] for r in rows]
    assert len(names) == len(set(names))
    assert "/v2/insights" in {e for r in rows for e in r["endpoints"]}


def test_external_id_families_are_registered_for_entities() -> None:
    rows = {r["param"]: r for r in registry_summary()}
    for family in EXTERNAL_ID_FAMILIES:
        key = f"external.{family}.ids"
        assert key in rows, f"{key} missing from the registry"
        assert EP_ENTITIES in rows[key]["endpoints"]


def test_unknown_external_family_is_rejected() -> None:
    with pytest.raises(UnverifiedParameterError):
        build_params(EP_ENTITIES, {"external.netflix.ids": ["123"]})


def test_parents_types_is_verified_for_audiences_but_not_for_insights() -> None:
    """Verification is per-endpoint: a parameter can be fine on one and not another."""
    spec = REGISTRY["filter.parents.types"]
    assert spec.status_for(EP_AUDIENCES) is ParamStatus.VERIFIED
    assert spec.status_for(EP_INSIGHTS) is ParamStatus.UNVERIFIED

    # The validator must agree with the spec.
    built = build_params(EP_AUDIENCES, {"filter.parents.types": ["urn:audience:leisure"], "take": 10})
    assert built.as_query()["filter.parents.types"] == "urn:audience:leisure"

    with pytest.raises(UnverifiedParameterError):
        build_params(
            EP_INSIGHTS,
            {
                "filter.type": "urn:tag",
                "signal.interests.entities": ["a"],
                "filter.parents.types": ["urn:audience:leisure"],
            },
        )
