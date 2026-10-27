"""Comparables audit: reference-vs-reference comparison, reported honestly.

The audit answers a claim the filmmaker made implicitly — "these references
belong together" — with whatever Qloo actually returned, and it never turns a
missing answer into a refutation.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from app.agent.state import AdjacentState, ProgrammeItem
from app.domain.comparables import MAX_PAIRS, SCHEMA, build_comparables_audit
from app.qloo.models import RawResponse


@dataclass
class _CompareClient:
    payload: dict[str, Any] | None = None
    error: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def compare(self, **kwargs: Any) -> RawResponse:
        self.calls.append(dict(kwargs))
        if self.error is not None:
            raise self.error
        return RawResponse(
            call_id=f"compare-{len(self.calls)}",
            source="qloo",
            data_status="measured",
            endpoint="/v2/analysis/compare",
            data=self.payload or {},
        )


def _item(title: str, index: int, *, resolved: bool = True) -> ProgrammeItem:
    return ProgrammeItem(
        title=title,
        year=2000 + index,
        imdb_id=None,
        declared_entity_id=None,
        resolved_entity_id=f"urn:entity:movie:{index}" if resolved else None,
        resolved_name=title if resolved else None,
        entity_type="urn:entity:movie" if resolved else None,
        source_call_id=f"resolve-{index}" if resolved else None,
    )


def _state(titles: list[str], *, resolved: bool = True, data_status: str = "measured") -> AdjacentState:
    return AdjacentState(
        run_id="run-1",
        data_status=data_status,
        programme=[_item(title, index, resolved=resolved) for index, title in enumerate(titles)],
    )


def _run(state: AdjacentState, client: _CompareClient, *, budget: int = MAX_PAIRS) -> dict[str, Any]:
    return asyncio.run(build_comparables_audit(client, state, budget_remaining=budget))


def test_measured_pair_reports_the_provider_key_and_call() -> None:
    client = _CompareClient(payload={"overlap": 0.42})
    audit = _run(_state(["Perfect Days", "The Zone of Interest"]), client)

    assert audit["schema"] == SCHEMA
    assert audit["status"] == "evaluated"
    assert audit["summary"]["pairs_measured"] == 1
    row = audit["pairs"][0]
    assert row["status"] == "measured"
    assert row["metric"] == {
        "key": "overlap",
        "value": 0.42,
        "direction": "higher_is_closer",
        "source": "provider_reported",
    }
    assert "0.420" in row["reason"]
    assert row["call_id"] == "compare-1"

    call = client.calls[0]
    assert call["a_signal_interests_entities"] == ["urn:entity:movie:0"]
    assert call["b_signal_interests_entities"] == ["urn:entity:movie:1"]
    assert call["filter_type"] == "urn:entity:movie"
    assert call["model"] == "descriptive"


def test_unreadable_payload_is_unevaluated_not_refuted() -> None:
    client = _CompareClient(payload={"lift": 2.0, "secret": "provider body"})
    audit = _run(_state(["A", "B"]), client)

    row = audit["pairs"][0]
    assert row["status"] == "no_readable_field"
    assert row["metric"] is None
    assert "lift" in row["observed_keys"]
    assert "not refuted" in row["reason"]
    assert "2.0" not in str(row)
    assert "provider body" not in str(row)
    assert audit["summary"]["pairs_measured"] == 0


def test_fixture_run_never_presents_a_comparison_as_measured() -> None:
    client = _CompareClient(payload={"results": []})
    audit = _run(_state(["A", "B"], data_status="fixture"), client)

    assert audit["pairs"][0]["status"] == "not_modelled_in_fixture"
    assert audit["pairs"][0]["call_id"] == "compare-1"
    assert audit["pairs"][0]["metric"] is None
    assert audit["summary"]["pairs_measured"] == 0


def test_upstream_failure_is_reported_per_pair_and_does_not_stop_the_audit() -> None:
    client = _CompareClient(error=RuntimeError("upstream exploded"))
    audit = _run(_state(["A", "B", "C"]), client)

    assert [row["status"] for row in audit["pairs"]] == [
        "failed",
        "not_attempted_after_failure",
        "not_attempted_after_failure",
    ]
    # One upstream failure is enough — the remaining pairs are not retried.
    assert len(client.calls) == 1
    assert audit["pairs"][0]["observed_keys"] == ["RuntimeError"]
    assert "Nothing is inferred" in audit["pairs"][1]["reason"]
    assert all(row["metric"] is None for row in audit["pairs"])
    assert "not evidence about the two groups" in audit["pairs"][0]["reason"]
    assert "upstream exploded" not in str(audit)


def test_budget_is_charged_per_call_and_shortfall_is_explicit() -> None:
    client = _CompareClient(payload={"overlap": 0.3})
    audit = _run(_state(["A", "B", "C", "D"]), client, budget=1)

    assert len(client.calls) == 1
    statuses = [row["status"] for row in audit["pairs"]]
    assert statuses == ["measured", "unavailable_budget", "unavailable_budget"]
    assert audit["summary"]["pairs_unavailable_budget"] == 2


def test_no_budget_makes_no_call_at_all() -> None:
    client = _CompareClient(payload={"overlap": 0.3})
    audit = _run(_state(["A", "B"]), client, budget=0)

    assert client.calls == []
    assert audit["pairs"][0]["status"] == "unavailable_budget"
    assert audit["status"] == "unevaluated"


def test_single_resolved_reference_is_insufficient_input_and_calls_nothing() -> None:
    client = _CompareClient(payload={"overlap": 0.3})
    audit = _run(_state(["Only Film"]), client)

    assert audit["status"] == "insufficient_input"
    assert audit["available"] is False
    assert client.calls == []
    assert "at least two resolved reference films" in audit["reason"]


def test_unresolved_references_are_listed_and_never_compared() -> None:
    state = _state(["A", "B"])
    state.programme.append(_item("Unreleased Short", 9, resolved=False))
    client = _CompareClient(payload={"overlap": 0.2})
    audit = _run(state, client)

    assert audit["unresolved_references"] == [{"title": "Unreleased Short", "year": 2009}]
    assert len(client.calls) == 1
    assert audit["summary"]["resolved_references"] == 2


def test_pairs_are_capped_and_closest_references_are_compared_first() -> None:
    client = _CompareClient(payload={"overlap": 0.2})
    audit = _run(_state(["A", "B", "C", "D"]), client)

    pairs = [(row["a"]["title"], row["b"]["title"]) for row in audit["pairs"]]
    assert pairs == [("A", "B"), ("B", "C"), ("C", "D")]
    assert audit["summary"]["pairs_considered"] == 6
    assert audit["not_evaluated_count"] == 3
    assert len(audit["not_evaluated"]) == 3
    assert audit["not_evaluated"][0]["status"] == "not_evaluated_limit"


def test_rows_carry_the_resolution_call_so_the_chain_is_auditable() -> None:
    client = _CompareClient(payload={"overlap": 0.5})
    audit = _run(_state(["A", "B"]), client)

    row = audit["pairs"][0]
    assert row["a"]["resolution_call_id"] == "resolve-0"
    assert row["b"]["resolution_call_id"] == "resolve-1"
    assert row["a"]["entity_id"] == "urn:entity:movie:0"


# ---------------------------------------------------------------------------
# API surface: Creator runs carry the audit, Cinema runs do not
# ---------------------------------------------------------------------------


def _run_to_terminal(client: Any, run_id: str) -> dict[str, Any]:
    deadline = time.time() + 60
    final: dict[str, Any] = {}
    while time.time() < deadline:
        final = client.get(f"/run/{run_id}").json()
        if final.get("status") in {"completed", "failed", "insufficient"}:
            return final
        time.sleep(0.1)
    raise AssertionError(f"run {run_id} never finished: {final}")


def test_creator_fixture_run_publishes_the_audit() -> None:
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    run_id = client.post("/creator/run/demo").json()["run_id"]
    final = _run_to_terminal(client, run_id)
    assert final["status"] == "completed", final.get("error")

    audit = final["result"]["comparables_audit"]
    assert audit["data_status"] == "fixture"
    assert audit["status"] == "evaluated"
    assert audit["summary"]["pairs_attempted"] == MAX_PAIRS
    assert len(audit["pairs"]) == MAX_PAIRS
    # Fixture runs make the call and label the outcome; they never show a value.
    assert audit["summary"]["pairs_measured"] == 0
    assert all(row["call_id"] for row in audit["pairs"])
    assert all(row["metric"] is None for row in audit["pairs"])


def test_cinema_run_has_no_comparables_audit() -> None:
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    run_id = client.post("/run/demo").json()["run_id"]
    final = _run_to_terminal(client, run_id)
    assert final["status"] == "completed"
    assert "comparables_audit" not in final["result"]
