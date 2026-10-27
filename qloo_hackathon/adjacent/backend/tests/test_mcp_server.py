"""Tests for the MCP server adapter.

Two levels:
* direct calls to the tool functions (fast, no SDK transport), and
* one real client↔server round trip over the SDK's in-memory streams, so the
  registered tools are proven reachable through the protocol and not just
  importable.

The server is a thin adapter: these tests assert it reports the *same* runner
result, labels fixture data, bounds live use, and turns every failure into an
explicit value.
"""

from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any

import pytest
from app import mcp_server
from app.mcp_server import (
    analyze_film_positioning,
    build_server,
    compare_film_groups,
    get_evidence_report,
)
from app.runner import run_fixture_async

MCP_SDK = pytest.importorskip("mcp", reason="the MCP SDK is optional for the web app")


@pytest.fixture(autouse=True)
def _reset_counters(monkeypatch: pytest.MonkeyPatch) -> None:
    mcp_server._COUNTERS["live"] = 0
    mcp_server._COUNTERS["fixture"] = 0
    mcp_server._SESSION_RUNS.clear()
    monkeypatch.delenv("ADJACENT_MCP_ALLOW_LIVE", raising=False)
    monkeypatch.delenv("ADJACENT_MCP_API_ORIGIN", raising=False)


def _tool_module_source() -> str:
    return inspect.getsource(mcp_server)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_exposes_exactly_the_read_oriented_tools() -> None:
    server = build_server()
    tools = asyncio.run(server.list_tools())
    names = sorted(tool.name for tool in tools)
    assert names == [
        "analyze_film_positioning",
        "compare_film_groups",
        "get_evidence_report",
    ]
    for tool in tools:
        assert tool.description, f"{tool.name} must describe itself"


def test_tool_descriptions_state_fixture_default_and_limits() -> None:
    server = build_server()
    tools = {tool.name: (tool.description or "") for tool in asyncio.run(server.list_tools())}
    combined = " ".join(tools.values()).lower()
    assert "fixture" in combined
    assert "never an inferred similarity" in tools["compare_film_groups"].lower()


def test_registry_has_no_write_or_delete_tools() -> None:
    server = build_server()
    for tool in asyncio.run(server.list_tools()):
        lowered = tool.name.lower()
        assert not lowered.startswith(("delete", "remove", "update", "create", "write"))
        assert "delete" not in lowered


def test_module_imports_without_the_mcp_sdk_on_the_web_path() -> None:
    # The FastAPI app must never require the SDK; build_server imports it lazily.
    source = _tool_module_source()
    top_level = source.split("def build_server", 1)[0]
    assert "from mcp" not in top_level
    assert "import mcp" not in top_level


# ---------------------------------------------------------------------------
# analyze_film_positioning
# ---------------------------------------------------------------------------


def test_analyze_returns_the_same_result_as_the_runner() -> None:
    report = asyncio.run(analyze_film_positioning([{"title": "Perfect Days", "year": 2023}]))
    assert report["schema"] == "adjacent.mcp-tool-result/1"
    assert report["status"] == "complete"
    assert report["available"] is True
    assert report["data_status"] == "fixture"

    # Same runner, same ordering: the adapter adds provenance, not judgement.
    direct = asyncio.run(run_fixture_async("portland_strong", render=False))
    assert [c["cohort_id"] for c in report["ranked_cohorts"]] == [
        c.cohort_id for c in direct.ranked[:3]
    ]
    assert report["evidence"]["qloo_calls"] == direct.calls_made
    assert report["evidence"]["stop_reason"] == direct.stop_reason


def test_analyze_is_explicitly_labelled_as_fixture_data() -> None:
    report = asyncio.run(analyze_film_positioning([{"title": "Perfect Days"}]))
    assert report["data_status"] == "fixture"
    assert "not the submitted titles" in report["programme_note"]
    assert report["requested_programme"] == [{"title": "Perfect Days", "year": None}]
    assert any("not attendance" in limit for limit in report["limitations"])


def test_analyze_reports_call_ids_for_every_claim_it_shapes() -> None:
    report = asyncio.run(analyze_film_positioning([{"title": "Perfect Days"}]))
    assert report["call_ids"], "a completed run must expose its trace call ids"
    for cohort in report["ranked_cohorts"]:
        assert cohort["score_call_id"] in report["call_ids"]
        for member in cohort["members"]:
            assert member["affinity"] is not None


def test_analyze_echoes_city_without_inventing_geography() -> None:
    report = asyncio.run(analyze_film_positioning([{"title": "Perfect Days"}], city="Kolkata"))
    assert report["city"] == "Kolkata"


@pytest.mark.parametrize(
    "programme",
    [[], "Perfect Days", [{"title": ""}], [{"title": "A", "year": "2023"}], [{}]],
)
def test_analyze_rejects_bad_programme_without_raising(programme: Any) -> None:
    report = asyncio.run(analyze_film_positioning(programme))
    assert report["status"] == "error"
    assert report["available"] is False
    assert report["reason"]


def test_analyze_caps_the_programme_size() -> None:
    report = asyncio.run(analyze_film_positioning([{"title": f"Film {i}"} for i in range(6)]))
    assert report["status"] == "error"
    assert "at most 5" in report["reason"]


def test_live_mode_is_off_by_default_and_says_why() -> None:
    report = asyncio.run(
        analyze_film_positioning([{"title": "Perfect Days"}], mode="live")
    )
    assert report["status"] == "unavailable"
    assert report["available"] is False
    assert "ADJACENT_MCP_ALLOW_LIVE" in report["reason"]
    assert "run_id" not in report, "no run may be fabricated for a refused live request"


def test_live_mode_without_a_key_reports_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADJACENT_MCP_ALLOW_LIVE", "1")
    monkeypatch.delenv("QLOO_API_KEY", raising=False)
    report = asyncio.run(
        analyze_film_positioning([{"title": "Perfect Days"}], mode="live")
    )
    assert report["status"] == "unavailable"
    assert "QLOO_API_KEY" in report["reason"]
    assert "run_id" not in report, "a refused live run must not produce a result"


def test_live_budget_is_bounded_per_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADJACENT_MCP_ALLOW_LIVE", "1")
    monkeypatch.setenv("QLOO_API_KEY", "not-a-real-key")
    mcp_server._COUNTERS["live"] = mcp_server.MAX_LIVE_RUNS_PER_SESSION
    report = asyncio.run(
        analyze_film_positioning([{"title": "Perfect Days"}], mode="live")
    )
    assert report["status"] == "unavailable"
    assert "bound" in report["reason"]


def test_fixture_budget_is_bounded_per_session() -> None:
    mcp_server._COUNTERS["fixture"] = mcp_server.MAX_FIXTURE_RUNS_PER_SESSION
    report = asyncio.run(analyze_film_positioning([{"title": "Perfect Days"}]))
    assert report["status"] == "unavailable"
    assert "Restart the server" in report["reason"]


def test_analyze_never_leaks_the_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "qlq_do_not_leak_me_0123456789"
    monkeypatch.setenv("QLOO_API_KEY", secret)
    report = asyncio.run(analyze_film_positioning([{"title": "Perfect Days"}]))
    assert secret not in json.dumps(report)


def test_analyze_does_not_persist_anything(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple] = []

    def _explode(*args: Any, **kwargs: Any) -> None:
        calls.append((args, kwargs))
        raise AssertionError("the MCP adapter must not reach a persistence layer")

    import app.mcp_server as module

    for name in ("RunStore", "ExperimentStore", "GuestStore"):
        if hasattr(module, name):  # pragma: no cover - defensive
            monkeypatch.setattr(module, name, _explode, raising=False)
    report = asyncio.run(analyze_film_positioning([{"title": "Perfect Days"}]))
    assert report["status"] == "complete"
    assert calls == []


# ---------------------------------------------------------------------------
# compare_film_groups
# ---------------------------------------------------------------------------


def test_compare_in_fixture_mode_is_traced_but_unmeasured() -> None:
    result = asyncio.run(
        compare_film_groups(["urn:entity:movie:1"], ["urn:entity:movie:2"])
    )
    assert result["status"] == "not_modelled_in_fixture"
    assert result["available"] is False
    assert result["metric"] is None
    assert result["call_id"], "the call happened, so it must be traceable"
    assert result["limitations"]


def test_compare_live_is_refused_without_the_operator_flag() -> None:
    result = asyncio.run(
        compare_film_groups(
            ["urn:entity:movie:1"], ["urn:entity:movie:2"], mode="live"
        )
    )
    assert result["status"] == "unavailable"
    assert "ADJACENT_MCP_ALLOW_LIVE" in result["reason"]
    assert result["metric"] is None


@pytest.mark.parametrize(
    ("group_a", "group_b", "filter_type"),
    [
        ([], ["urn:entity:movie:2"], "urn:entity:movie"),
        (["not-an-id"], ["urn:entity:movie:2"], "urn:entity:movie"),
        (["urn:entity:movie:1"], ["urn:entity:movie:2"], "movie"),
        (
            [f"urn:entity:movie:{i}" for i in range(11)],
            ["urn:entity:movie:2"],
            "urn:entity:movie",
        ),
    ],
)
def test_compare_validates_inputs_without_raising(
    group_a: list[str], group_b: list[str], filter_type: str
) -> None:
    result = asyncio.run(compare_film_groups(group_a, group_b, filter_type=filter_type))
    assert result["status"] == "error"
    assert result["available"] is False
    assert result["metric"] is None


# ---------------------------------------------------------------------------
# get_evidence_report
# ---------------------------------------------------------------------------


def test_evidence_report_returns_the_session_run_unchanged() -> None:
    created = asyncio.run(analyze_film_positioning([{"title": "Perfect Days"}]))
    read_back = asyncio.run(get_evidence_report(created["run_id"]))
    assert read_back["source"] == "mcp_session"
    assert read_back["ranked_cohorts"] == created["ranked_cohorts"]
    assert read_back["evidence"] == created["evidence"]
    assert read_back["challenge"] == created["challenge"]


def test_evidence_report_without_origin_is_unavailable_not_invented() -> None:
    result = asyncio.run(get_evidence_report("run-that-does-not-exist"))
    assert result["status"] == "unavailable"
    assert result["available"] is False
    assert "ADJACENT_MCP_API_ORIGIN" in result["reason"]


def test_evidence_report_rejects_empty_run_id() -> None:
    result = asyncio.run(get_evidence_report("   "))
    assert result["status"] == "error"


def test_evidence_report_reports_an_unreachable_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADJACENT_MCP_API_ORIGIN", "http://127.0.0.1:9")
    result = asyncio.run(get_evidence_report("abc123"))
    assert result["status"] == "unavailable"
    assert "could not be reached" in result["reason"]


# ---------------------------------------------------------------------------
# Real protocol round trip (in-memory streams)
# ---------------------------------------------------------------------------


def test_client_round_trip_lists_and_calls_tools() -> None:
    from mcp.client.session import ClientSession
    from mcp.shared.memory import create_client_server_memory_streams

    captured: dict[str, Any] = {}

    async def scenario() -> None:
        server = build_server()
        async with create_client_server_memory_streams() as (client_streams, server_streams):
            read_client, write_client = client_streams
            read_server, write_server = server_streams
            options = server._lowlevel_server.create_initialization_options()

            async with asyncio.TaskGroup() as group:
                group.create_task(
                    server._lowlevel_server.run(read_server, write_server, options)
                )
                async with ClientSession(read_client, write_client) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    captured["names"] = sorted(tool.name for tool in listed.tools)
                    captured["analyze"] = await session.call_tool(
                        "analyze_film_positioning",
                        {"programme": [{"title": "Perfect Days", "year": 2023}]},
                    )
                    captured["live"] = await session.call_tool(
                        "analyze_film_positioning",
                        {"programme": [{"title": "Perfect Days"}], "mode": "live"},
                    )
                    captured["compare"] = await session.call_tool(
                        "compare_film_groups",
                        {
                            "group_a": ["urn:entity:movie:1"],
                            "group_b": ["urn:entity:movie:2"],
                        },
                    )

    asyncio.run(scenario())

    assert captured["names"] == [
        "analyze_film_positioning",
        "compare_film_groups",
        "get_evidence_report",
    ]

    analyze = captured["analyze"]
    assert analyze.is_error is False
    payload = analyze.structured_content or {}
    assert payload["status"] == "complete"
    assert payload["data_status"] == "fixture"
    assert payload["call_ids"]
    # The human-readable content says the same thing as the structured payload.
    text = " ".join(block.text for block in analyze.content if block.type == "text")
    assert "fixture" in text.lower()

    live = captured["live"]
    assert (live.structured_content or {})["status"] == "unavailable"
    assert "ADJACENT_MCP_ALLOW_LIVE" in (live.structured_content or {})["reason"]

    compare = captured["compare"]
    assert (compare.structured_content or {})["status"] == "not_modelled_in_fixture"
    assert (compare.structured_content or {})["metric"] is None
