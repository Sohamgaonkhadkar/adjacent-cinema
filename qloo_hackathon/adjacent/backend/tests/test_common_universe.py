"""Regression gates for the M14 same-universe, independently sourced study."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from app.domain.common_universe import (
    InvalidStudy,
    compare_common_universe,
    freeze_manifest,
    metadata_ranking,
)

ADJACENT = Path(__file__).resolve().parents[2]


def _manifest():
    return {
        "study_id": "offline-contract",
        "metadata_source": "manually curated independent metadata; no provider retrieval",
        "selection_uses_qloo": False,
        "programme": [
            {"title": "Seed", "year": 2000, "genres": ["drama"], "country": "A", "director": "X"},
        ],
        "candidates": [
            {"title": "A", "year": 2001, "genres": ["drama"], "country": "A", "director": "Y"},
            {"title": "B", "year": 2002, "genres": ["comedy"], "country": "B", "director": "Z"},
            {"title": "C", "year": 2003, "genres": ["drama"], "country": "B", "director": "Y"},
        ],
    }


def test_freeze_is_deterministic_and_excludes_provider_signals():
    manifest = _manifest()
    frozen = freeze_manifest(manifest)
    assert frozen["sha256"] == freeze_manifest(manifest)["sha256"]
    assert [r["key"] for r in metadata_ranking(frozen)] == ["a|2001", "c|2003", "b|2002"]
    assert frozen["candidates"][0]["genres"] == ["drama"]


@pytest.mark.parametrize("injection", [
    {"qloo_entity_id": "urn:any"},
    {"affinity": 0.8},
    {"qloo_rank": 1},
])
def test_provider_fields_cannot_contaminate_independent_catalog(injection):
    manifest = _manifest()
    manifest["candidates"][0].update(injection)
    with pytest.raises(InvalidStudy):
        freeze_manifest(manifest)


def test_freeze_rejects_duplicates_programme_overlap_and_nonindependent_source():
    manifest = _manifest()
    manifest["candidates"].append(dict(manifest["candidates"][0]))
    with pytest.raises(InvalidStudy, match="Duplicate"):
        freeze_manifest(manifest)

    manifest = _manifest()
    manifest["candidates"][0]["title"] = "Seed"
    manifest["candidates"][0]["year"] = 2000
    with pytest.raises(InvalidStudy, match="Programme"):
        freeze_manifest(manifest)

    manifest = _manifest()
    manifest["metadata_source"] = "Qloo search"
    with pytest.raises(InvalidStudy, match="cannot be Qloo"):
        freeze_manifest(manifest)

    manifest = _manifest()
    manifest.pop("selection_uses_qloo")
    with pytest.raises(InvalidStudy, match="explicitly"):
        freeze_manifest(manifest)


def test_blocked_without_measured_qloo_and_reports_no_invented_effect():
    frozen = freeze_manifest(_manifest())
    report = compare_common_universe(frozen)
    assert report["status"] == "blocked"
    assert report["qloo_order"] is None
    assert report["outcome_verdict"] == "not_established"
    assert report["candidate_count"] == 3


def test_real_same_pool_comparison_reports_movement_not_effectiveness():
    frozen = freeze_manifest(_manifest())
    scored = {
        "a|2001": ("movie-a", 0.30),
        "b|2002": ("movie-b", 0.95),
        "c|2003": ("movie-c", 0.70),
    }
    report = compare_common_universe(
        frozen, scored=scored, call_id="test-call-1", data_status="measured"
    )
    assert report["status"] == "evaluable"
    assert report["metadata_order"] == ["a|2001", "c|2003", "b|2002"]
    assert report["qloo_order"] == ["b|2002", "c|2003", "a|2001"]
    assert report["winner_changed"] is True
    assert report["rank_correlation"]["value"] == -1.0
    assert report["outcome_verdict"] == "not_established"


def test_missing_affinity_keeps_full_denominator_and_blocks_metrics():
    frozen = freeze_manifest(_manifest())
    report = compare_common_universe(
        frozen,
        scored={"a|2001": ("movie-a", 0.5), "b|2002": ("movie-b", None)},
        call_id="test-call-2",
        data_status="measured",
    )
    assert report["status"] == "not_evaluable"
    assert report["qloo_coverage"] == {
        "scored": 1, "of": 3, "missing_keys": ["b|2002", "c|2003"]
    }
    assert report["rank_correlation"] is None
    assert report["qloo_order"] is None


def test_reject_unknown_candidates_duplicate_mappings_fixture_and_bad_scores():
    frozen = freeze_manifest(_manifest())
    for scored in (
        {"random|1999": ("movie-x", 0.6)},
        {"a|2001": ("movie-id", 0.6), "b|2002": ("movie-id", 0.7)},
        {"a|2001": ("movie-id", float("nan"))},
        {"a|2001": ("movie-id", 1.1)},
    ):
        with pytest.raises(InvalidStudy):
            compare_common_universe(frozen, scored=scored, call_id="test-call", data_status="measured")
    with pytest.raises(InvalidStudy, match="Measured"):
        compare_common_universe(frozen, scored={}, data_status="fixture", call_id="fake")


def test_checked_in_manifest_offline_preflight_never_claims_live_evidence(tmp_path):
    script = ADJACENT / "research" / "scripts" / "m14_common_universe_live.py"
    manifest = ADJACENT / "data" / "benchmarks" / "common_universe_20261102.json"
    output = tmp_path / "report.json"
    env = dict(os.environ)
    env.pop("QLOO_API_KEY", None)
    proc = subprocess.run(
        [sys.executable, str(script), "--manifest", str(manifest), "--output", str(output)],
        capture_output=True, text=True, timeout=30, check=False, env=env,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "blocked"
    assert report["execution"] == "offline_preflight"
    assert report["live_result_claim"] is False
    assert report["candidate_count"] == 12
    assert len(report["frozen_sha256"]) == 64
