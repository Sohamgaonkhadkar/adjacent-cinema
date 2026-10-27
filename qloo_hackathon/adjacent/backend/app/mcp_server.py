"""Adjacent Cinema MCP server — three read-oriented tools over the real app.

Design
------
* **It is a thin adapter.** Every tool calls the same runner, same reader and
  same domain functions the website uses. There is no second ranker, no second
  scoring path, and no scoring logic in this file.
* **Fixture by default.** `analyze_film_positioning` runs the labelled fixture
  pipeline unless the operator sets `ADJACENT_MCP_ALLOW_LIVE=1` *and* the server
  has a key. Live runs are capped per session so a client cannot burn the
  provider budget.
* **Failures are values.** Every tool returns a dict with an explicit `status`;
  an upstream failure or a missing run becomes `unavailable`/`error` with a
  reason, never a fabricated success. Exception messages are not echoed.
* **No secrets, no private data.** The key stays in the server process. Nothing
  here reads experiment records, guest sessions or environment values.
* **stdio only.** No network listener is opened, so there is no public endpoint
  to secure. The transport is the SDK's stdio implementation.

Run it with the backend package on the path:

    PYTHONPATH=backend python -m app.mcp_server

Client configuration (placeholders only — no real values):

    {
      "mcpServers": {
        "adjacent-cinema": {
          "command": "python",
          "args": ["-m", "app.mcp_server"],
          "env": {
            "PYTHONPATH": "/absolute/path/to/qloo_hackathon/adjacent/backend",
            "ADJACENT_MCP_ALLOW_LIVE": "0"
          }
        }
      }
    }
"""

from __future__ import annotations

import os
import re
import sys
from contextlib import suppress
from typing import Any

SCHEMA = "adjacent.mcp-tool-result/1"

#: How many live analyses one server session may run. Deliberately small: the
#: budget guard exists so an agent cannot spend a hackathon key.
MAX_LIVE_RUNS_PER_SESSION = int(os.environ.get("ADJACENT_MCP_MAX_LIVE_RUNS", "2") or 2)

#: Fixture analyses are free but still bounded, so a loop cannot spin forever.
MAX_FIXTURE_RUNS_PER_SESSION = 10

MANY_MEMBERS = 10

PUBLIC_LIMITS: tuple[str, ...] = (
    "Cultural affinity is a Qloo taste measurement. It is not attendance, audience size, "
    "conversion, revenue or an outcome forecast.",
    "A comparison describes the two entity groups supplied. A pair with no readable value is "
    "unevaluated, not refuted.",
    "Counterfactuals are computed over the run's own admitted candidate pool. They test "
    "ranking sensitivity, not what a fresh provider query would retrieve.",
)

_ENTITY_ID = re.compile(r"^urn:[a-z_]+:[a-z_]+:[^\s]+$", re.IGNORECASE)
#: A run id is interpolated into a URL path, so it must be a plain identifier:
#: no slashes, dots or percent-escapes that could address another API resource.
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_ENTITY_TYPE = re.compile(r"^urn:entity:[a-z_]+$", re.IGNORECASE)

#: Runs created in this session, so `get_evidence_report` can read them back
#: without a database or a shared store.
_SESSION_RUNS: dict[str, dict[str, Any]] = {}
_COUNTERS = {"live": 0, "fixture": 0}


class ToolInputError(ValueError):
    """A caller-supplied argument failed validation."""


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def _clean_programme(programme: Any) -> list[dict[str, Any]]:
    if not isinstance(programme, list) or not programme:
        raise ToolInputError("programme must be a non-empty list of film references")
    if len(programme) > 5:
        raise ToolInputError("programme accepts at most 5 film references per analysis")
    cleaned: list[dict[str, Any]] = []
    for item in programme:
        if not isinstance(item, dict):
            raise ToolInputError("each programme item must be an object")
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ToolInputError("each programme item needs a non-empty title")
        year = item.get("year")
        if year is not None and not isinstance(year, int):
            raise ToolInputError("year must be an integer when supplied")
        imdb_id = item.get("imdb_id")
        if imdb_id is not None and not isinstance(imdb_id, str):
            raise ToolInputError("imdb_id must be a string when supplied")
        entity_id = item.get("entity_id")
        if entity_id is not None and not isinstance(entity_id, str):
            raise ToolInputError("entity_id must be a string when supplied")
        cleaned.append(
            {
                "title": title.strip(),
                "year": year,
                "imdb_id": imdb_id,
                "entity_id": entity_id,
            }
        )
    return cleaned


def _clean_entity_group(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ToolInputError(f"{name} must be a non-empty list of Qloo entity ids")
    if len(value) > MANY_MEMBERS:
        raise ToolInputError(f"{name} accepts at most {MANY_MEMBERS} entity ids")
    cleaned: list[str] = []
    for entity_id in value:
        if not isinstance(entity_id, str) or not _ENTITY_ID.match(entity_id.strip()):
            raise ToolInputError(
                f"{name} entries must be Qloo entity ids of the form urn:entity:<type>:<id>"
            )
        cleaned.append(entity_id.strip())
    return cleaned


# ---------------------------------------------------------------------------
# Result shaping
# ---------------------------------------------------------------------------


def _unavailable(status: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "available": False,
        "reason": reason,
        "limitations": list(PUBLIC_LIMITS),
        **extra,
    }


def _compare_unavailable(status: str, reason: str, **extra: Any) -> dict[str, Any]:
    """A compare that produced no value still states so in the same shape."""
    return _unavailable(
        status,
        reason,
        metric=None,
        call_id=None,
        observed_keys=[],
        **extra,
    )


def _live_allowed() -> bool:
    return (os.environ.get("ADJACENT_MCP_ALLOW_LIVE", "0") or "").strip() in {"1", "true", "yes"}


def _cohort_summary(cohort: Any) -> dict[str, Any]:
    score = getattr(cohort, "score", None)
    members = []
    for member in list(getattr(cohort, "members", []) or [])[:5]:
        members.append(
            {
                "entity_id": member.entity_id,
                "name": member.name,
                "affinity": member.affinity,
                "band": member.band,
                "attribution_origin": getattr(member, "attribution_origin", None),
                "attribution": member.qloo_attributions()[:3],
            }
        )
    return {
        "cohort_id": getattr(cohort, "cohort_id", ""),
        "domain": getattr(cohort, "domain", ""),
        "kind": getattr(cohort, "kind", ""),
        "rank": getattr(cohort, "rank", None),
        "mean_affinity": getattr(score, "mean_affinity", None) if score else None,
        "novelty_proxy": getattr(score, "novelty_proxy", None) if score else None,
        "score_call_id": getattr(score, "call_id", None) if score else None,
        "members": members,
    }


def _challenge_summary(state: Any) -> dict[str, Any] | None:
    from .domain.challenge import build_decision_challenge

    try:
        challenge = build_decision_challenge(state)
    except Exception as exc:  # a broken challenge must not fail the tool
        return {"available": False, "reason": f"challenge unavailable: {type(exc).__name__}"}

    necessity = challenge.get("necessity") or {}
    withheld = necessity.get("affinity_withheld") or {}
    popularity = necessity.get("popularity_only") or {}
    recommendation = challenge.get("recommendation") or {}
    return {
        "available": bool(challenge.get("available")),
        "data_status": challenge.get("data_status"),
        "recommendation": recommendation.get("label"),
        "affinity_withheld": {
            "winner_changed": withheld.get("winner_changed"),
            "top_overlap": withheld.get("top_overlap"),
            "rank_correlation": withheld.get("rank_correlation"),
        },
        "popularity_only": {
            "winner_changed": popularity.get("winner_changed"),
            "top_overlap": popularity.get("top_overlap"),
            "rank_correlation": popularity.get("rank_correlation"),
        },
        "stability_verdict": (challenge.get("stability") or {}).get("verdict"),
        "limits": challenge.get("limits"),
    }


def _state_report(state: Any) -> dict[str, Any]:
    """Everything a client needs to inspect one completed analysis."""
    evidence = {
        "qloo_calls": state.calls_made,
        "trace_rows": len(state.trace_rows),
        "stop_reason": state.stop_reason,
        "bounded_attribution": (
            state.ranking.bounded_attribution if state.ranking is not None else None
        ),
    }
    call_ids = sorted(
        {
            str(row.get("call_id"))
            for row in state.trace_rows
            if isinstance(row.get("call_id"), str) and row.get("call_id")
        }
    )
    return {
        "schema": SCHEMA,
        "status": "complete" if state.stop_reason == "complete" else state.stop_reason,
        "available": state.stop_reason == "complete" and bool(state.ranked),
        "run_id": state.run_id,
        "data_status": state.data_status,
        "programme": [
            {
                "title": item.title,
                "year": item.year,
                "resolved": item.resolved,
                "resolved_name": item.resolved_name,
                "entity_id": item.resolved_entity_id,
                "source_call_id": item.source_call_id,
            }
            for item in state.programme
        ],
        "ranked_cohorts": [_cohort_summary(cohort) for cohort in state.ranked[:3]],
        "rejected_cohorts": [
            {
                "cohort_id": cohort.cohort_id,
                "domain": cohort.domain,
                "reason": getattr(getattr(cohort, "rejection", None), "reason", None),
            }
            for cohort in state.rejected[:5]
        ],
        "challenge": _challenge_summary(state),
        "pairwise": state.pairwise,
        "evidence": evidence,
        "call_ids": call_ids,
        "limitations": list(PUBLIC_LIMITS),
    }


# ---------------------------------------------------------------------------
# Tool implementations (SDK-agnostic; the server below registers them)
# ---------------------------------------------------------------------------


async def analyze_film_positioning(
    programme: list[dict[str, Any]],
    city: str | None = None,
    mode: str = "fixture",
) -> dict[str, Any]:
    """Run the real Adjacent analysis for a short programme and return its evidence.

    Fixture mode is the default and makes no provider calls. Live mode requires
    the operator to enable it (`ADJACENT_MCP_ALLOW_LIVE=1`) and a configured key.
    """
    try:
        items = _clean_programme(programme)
    except ToolInputError as exc:
        return _unavailable("error", str(exc))

    if mode not in {"fixture", "live"}:
        return _unavailable("error", "mode must be 'fixture' or 'live'")

    if mode == "live":
        if not _live_allowed():
            return _unavailable(
                "unavailable",
                "Live analyses are disabled for this MCP server. The operator must set "
                "ADJACENT_MCP_ALLOW_LIVE=1; fixture mode is available without a key.",
            )
        if _COUNTERS["live"] >= MAX_LIVE_RUNS_PER_SESSION:
            return _unavailable(
                "unavailable",
                f"This server session has already run {MAX_LIVE_RUNS_PER_SESSION} live "
                "analyses, which is its bound. Restart the server to reset it.",
            )
        from .config import Settings

        if not Settings.from_env().has_api_key:
            return _unavailable(
                "unavailable",
                "QLOO_API_KEY is not configured on this MCP server, so no live analysis "
                "can run. Fixture mode is available and is labelled as such.",
            )
        from .live_runner import run_live_async

        _COUNTERS["live"] += 1
        try:
            state = await run_live_async(items, render=False)
        except Exception as exc:
            return _unavailable(
                "unavailable",
                "The live analysis did not complete. No fixture result was substituted.",
                error_type=type(exc).__name__,
            )
    else:
        if _COUNTERS["fixture"] >= MAX_FIXTURE_RUNS_PER_SESSION:
            return _unavailable(
                "unavailable",
                f"This server session has already run {MAX_FIXTURE_RUNS_PER_SESSION} fixture "
                "analyses, which is its bound. Restart the server to reset it.",
            )
        from .runner import run_fixture_async

        _COUNTERS["fixture"] += 1
        try:
            # The labelled fixture carries its own programme; the submitted titles
            # are echoed back in the payload so the caller can see what was asked.
            state = await run_fixture_async("portland_strong", render=False)
        except Exception as exc:
            return _unavailable(
                "unavailable",
                "The fixture analysis did not complete.",
                error_type=type(exc).__name__,
            )

    report = _state_report(state)
    report["city"] = city or None
    report["requested_programme"] = [
        {"title": item["title"], "year": item["year"]} for item in items
    ]
    if mode == "fixture":
        report["programme_note"] = (
            "Fixture mode runs the labelled fixture programme, not the submitted titles; the "
            "submitted titles are echoed in requested_programme and were not analysed."
        )
    _SESSION_RUNS[state.run_id] = report
    return report


async def compare_film_groups(
    group_a: list[str],
    group_b: list[str],
    filter_type: str = "urn:entity:movie",
    mode: str = "fixture",
) -> dict[str, Any]:
    """Compare two groups of resolved Qloo entity ids with `/v2/analysis/compare`."""
    try:
        a_ids = _clean_entity_group(group_a, "group_a")
        b_ids = _clean_entity_group(group_b, "group_b")
    except ToolInputError as exc:
        return _compare_unavailable("error", str(exc))

    if not isinstance(filter_type, str) or not _ENTITY_TYPE.match(filter_type.strip()):
        return _compare_unavailable("error", "filter_type must be an entity type such as urn:entity:movie")
    filter_type = filter_type.strip()

    from .domain.comparables import compare_entity_groups

    if mode == "live":
        if not _live_allowed():
            return _compare_unavailable(
                "unavailable",
                "Live comparisons are disabled for this MCP server. The operator must set "
                "ADJACENT_MCP_ALLOW_LIVE=1.",
            )
        from .config import Settings

        if not Settings.from_env().has_api_key:
            return _compare_unavailable("unavailable", "QLOO_API_KEY is not configured on this server.")
        from .qloo.client import QlooClient

        client = QlooClient(Settings.from_env())
        data_status = "measured"
    else:
        from .qloo.mock import MockQlooClient

        client = MockQlooClient()
        data_status = "fixture"

    try:
        outcome = await compare_entity_groups(
            client,
            a_ids,
            b_ids,
            filter_type=filter_type,
            data_status=data_status,
            tool="mcp_compare_film_groups",
        )
    finally:
        close = getattr(client, "aclose", None)
        if callable(close):
            # Closing a transport must not mask the comparison's own result.
            with suppress(Exception):
                await close()

    return {
        "schema": SCHEMA,
        "status": outcome["status"],
        "available": outcome["status"] == "measured",
        "data_status": data_status,
        "metric": outcome["metric"],
        "reason": outcome["reason"],
        "call_id": outcome["call_id"],
        "observed_keys": outcome["observed_keys"],
        "groups": {"a": a_ids, "b": b_ids, "filter_type": filter_type},
        "limitations": list(PUBLIC_LIMITS),
    }


async def get_evidence_report(run_id: str) -> dict[str, Any]:
    """Return a completed run's result, evidence and provenance without changing it."""
    if not isinstance(run_id, str) or not run_id.strip():
        return _unavailable("error", "run_id must be a non-empty string")
    run_id = run_id.strip()
    if not _RUN_ID.match(run_id):
        return _unavailable(
            "error",
            "run_id must be a plain identifier of letters, digits, hyphens or underscores "
            "(1–64 characters); anything else could address a different API resource.",
        )

    report = _SESSION_RUNS.get(run_id)
    if report is not None:
        return {**report, "source": "mcp_session"}

    origin = (os.environ.get("ADJACENT_MCP_API_ORIGIN", "") or "").strip().rstrip("/")
    if not origin:
        return _unavailable(
            "unavailable",
            "This run is not in this MCP session and no backend origin is configured. Set "
            "ADJACENT_MCP_API_ORIGIN to read completed runs from the Adjacent API.",
            run_id=run_id,
        )

    import httpx

    url = f"{origin}/run/{run_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.get(url)
    except Exception as exc:
        return _unavailable(
            "unavailable",
            "The Adjacent API could not be reached.",
            run_id=run_id,
            error_type=type(exc).__name__,
        )

    if response.status_code == 404:
        return _unavailable("unavailable", "No such run on the Adjacent API.", run_id=run_id)
    if response.status_code >= 400:
        return _unavailable(
            "unavailable",
            f"The Adjacent API answered HTTP {response.status_code}.",
            run_id=run_id,
        )

    payload = response.json()
    if payload.get("status") not in {"completed", "insufficient"}:
        return _unavailable(
            "unavailable",
            f"Run {run_id} is '{payload.get('status')}', not completed. Nothing is inferred "
            "from a partial run.",
            run_id=run_id,
        )

    result = payload.get("result") or {}
    evidence = result.get("evidence") or {}
    return {
        "schema": SCHEMA,
        "status": payload.get("status"),
        "available": bool(result),
        "run_id": run_id,
        "source": "adjacent_api",
        "data_status": result.get("data_status"),
        "city": result.get("city"),
        "programme": result.get("programme"),
        "ranked_cohorts": result.get("cohorts", {}).get("ranked", [])[:3],
        "challenge": result.get("challenge"),
        "pairwise": result.get("pairwise"),
        "evidence": evidence,
        "call_ids": sorted(
            {
                str(row.get("call_id"))
                for row in payload.get("trace", [])
                if isinstance(row.get("call_id"), str) and row.get("call_id")
            }
        ),
        "limitations": list(PUBLIC_LIMITS),
    }


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


def build_server() -> Any:
    """Build the MCPServer. Imported lazily so the web app never needs the SDK."""
    from mcp.server.mcpserver import MCPServer

    server = MCPServer(
        name="adjacent-cinema",
        title="Adjacent Cinema",
        version="0.1.0",
        instructions=(
            "Read-only tools over Adjacent Cinema's existing analysis. Fixture mode is the "
            "default and makes no provider calls; live mode requires the operator to enable "
            "it. Every result states its data status, its limits and the call ids behind it."
        ),
    )

    @server.tool(
        name="analyze_film_positioning",
        description=(
            "Run Adjacent's existing analysis for up to five film references and return the "
            "ranked evidence, the counterfactual summary, data status, limitations and trace "
            "call ids. Fixture mode by default; live mode only when the operator enables it."
        ),
    )
    async def analyze_film_positioning_tool(
        programme: list[dict[str, Any]],
        city: str | None = None,
        mode: str = "fixture",
    ) -> dict[str, Any]:
        return await analyze_film_positioning(programme, city=city, mode=mode)

    @server.tool(
        name="compare_film_groups",
        description=(
            "Compare two groups of resolved Qloo entity ids with the same reader the website "
            "uses. Returns a provider-reported metric when one is readable, or an explicit "
            "unevaluated/unavailable state — never an inferred similarity."
        ),
    )
    async def compare_film_groups_tool(
        group_a: list[str],
        group_b: list[str],
        filter_type: str = "urn:entity:movie",
        mode: str = "fixture",
    ) -> dict[str, Any]:
        return await compare_film_groups(
            group_a, group_b, filter_type=filter_type, mode=mode
        )

    @server.tool(
        name="get_evidence_report",
        description=(
            "Retrieve a completed run's result, evidence, limitations and provenance without "
            "changing its decision. Reads runs created in this MCP session, or completed runs "
            "from the Adjacent API when ADJACENT_MCP_API_ORIGIN is configured."
        ),
    )
    async def get_evidence_report_tool(run_id: str) -> dict[str, Any]:
        return await get_evidence_report(run_id)

    return server


def main() -> int:
    try:
        server = build_server()
    except ImportError:
        print(
            "The MCP SDK is not installed. Install it with: pip install 'mcp>=2,<3'",
            file=sys.stderr,
        )
        return 2

    # stdio only: no listener, no origin handling, no public endpoint.
    server.run("stdio")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through the client test
    raise SystemExit(main())


__all__ = [
    "analyze_film_positioning",
    "build_server",
    "compare_film_groups",
    "get_evidence_report",
    "main",
]
