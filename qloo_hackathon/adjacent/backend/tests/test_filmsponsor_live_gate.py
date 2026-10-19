"""Offline safety regressions for the separately gated FilmSponsor script."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.resolution.resolver import EntityResolver

PROJECT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_DIR / "scripts" / "filmsponsor_live_gate.py"
_SCRIPT_SPEC = importlib.util.spec_from_file_location("filmsponsor_live_gate", SCRIPT_PATH)
assert _SCRIPT_SPEC is not None and _SCRIPT_SPEC.loader is not None
_gate = importlib.util.module_from_spec(_SCRIPT_SPEC)
_SCRIPT_SPEC.loader.exec_module(_gate)


def _entity(
    entity_id: str,
    *,
    name: str = "Perfect Days",
    year: int = 2023,
    entity_types: tuple[str, ...] = ("urn:entity:movie",),
    imdb_ids: tuple[str, ...] = (),
) -> SimpleNamespace:
    raw = {
        "name": name,
        "types": list(entity_types),
        "properties": {"release_year": year},
        "external": {"imdb": list(imdb_ids)},
    }
    if entity_types:
        raw["type"] = entity_types[0]
    return SimpleNamespace(
        entity_id=entity_id,
        name=name,
        type=entity_types[0] if entity_types else None,
        subtype=None,
        popularity=None,
        raw=raw,
    )


class _ResolverClient:
    """In-memory transport double; the tests below never perform network I/O."""

    def __init__(self, search_results: list[SimpleNamespace], entity_results: list[SimpleNamespace]):
        self.search_results = search_results
        self.entity_results = entity_results
        self.search_calls: list[dict[str, object]] = []
        self.entity_calls: list[dict[str, object]] = []

    async def search(self, **kwargs: object) -> SimpleNamespace:
        self.search_calls.append(kwargs)
        return SimpleNamespace(results=self.search_results, call_id="search-call")

    async def entities(self, **kwargs: object) -> SimpleNamespace:
        self.entity_calls.append(kwargs)
        return SimpleNamespace(results=self.entity_results, call_id="entities-call")


def test_missing_key_blocks_before_network_or_artifacts(tmp_path: Path) -> None:
    """No-key subprocess is blocked, not reported as fixture or measured live data."""
    env = os.environ.copy()
    env.pop("QLOO_API_KEY", None)

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["overall_verdict"] == "BLOCKED"
    assert report["mode"] == "blocked"
    assert report["source"] == "none"
    assert report["data_status"] == "not_run"
    assert report["live_requests"] == 0
    assert report["max_logical_gets"] == _gate.MAX_LOGICAL_GETS
    assert report["credential_value_emitted"] is False
    assert report["raw_responses_saved"] is False
    assert list(tmp_path.iterdir()) == []


def test_film_gate_uses_production_resolver_for_typed_external_id_match() -> None:
    imdb_id = "tt1234567"
    search_entity = _entity("entity-movie-1", imdb_ids=(imdb_id,))
    external_entity = _entity("entity-movie-1", imdb_ids=(imdb_id,))
    client = _ResolverClient([search_entity], [external_entity])
    resolver = EntityResolver(client, delay_s=0.0)
    film = {"title": "Perfect Days", "year": 2023, "imdb_id": imdb_id}

    record = asyncio.run(_gate._resolve_film(resolver, film))

    assert client.search_calls[0]["types"] == ["urn:entity:movie"]
    assert client.entity_calls[0]["external_ids"] == {"imdb": [imdb_id]}
    assert record["verdict"] == "PASS"
    assert record["resolution"]["status"] == "VERIFIED"
    assert record["resolution"]["method"] == "external_id"
    assert record["resolution"]["external_id_corroborated"] is True
    assert record["resolution"]["candidate"] == {
        "entity_id": "entity-movie-1",
        "name": "Perfect Days",
        "year": 2023,
        "type": "urn:entity:movie",
    }
    assert set(record["resolution"]["call_ids"]) == {"search-call", "entities-call"}
    assert "raw_result" not in record["resolution"]


def test_film_gate_preserves_production_resolver_ambiguity() -> None:
    client = _ResolverClient(
        [
            _entity("entity-movie-1"),
            _entity("entity-movie-2"),
        ],
        [],
    )
    resolver = EntityResolver(client, delay_s=0.0)
    film = {"title": "Perfect Days", "year": 2023}

    record = asyncio.run(_gate._resolve_film(resolver, film))

    assert record["verdict"] == "AMBIGUOUS"
    assert record["resolution"]["status"] == "AMBIGUOUS"
    assert record["resolution"]["candidate"] is None
    assert client.entity_calls == []


def test_gate_client_enforces_twelve_logical_get_limit() -> None:
    class CountingClient:
        def __init__(self) -> None:
            self.calls = 0

        async def tags(self, **_kwargs: object) -> None:
            self.calls += 1

    raw_client = CountingClient()
    client = _gate._BudgetedQlooClient(raw_client)

    async def call_to_limit() -> None:
        for _ in range(_gate.MAX_LOGICAL_GETS):
            await client.tags()
        with pytest.raises(_gate._GateStopped):
            await client.tags()

    asyncio.run(call_to_limit())

    assert raw_client.calls == _gate.MAX_LOGICAL_GETS
    assert client.logical_gets == _gate.MAX_LOGICAL_GETS
    assert client.halted is True
    assert client.halt_reason["error_type"] == "LogicalGetBudgetExceeded"
