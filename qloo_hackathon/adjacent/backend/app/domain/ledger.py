"""Provenance ledger — the mechanism that makes "every displayed number is
traceable" enforceable rather than aspirational.

Rendered output never formats a number itself. Every numeric value that reaches
the CLI (or any future UI) is formatted through the ledger, which records where
the number came from:

  * `qloo_call`    — an affinity, popularity, count or aggregate derived from one
                     Qloo response. The referenced `call_id` MUST exist as a trace
                     row; if it does not, the ledger reports it as unverified.
  * `fixture_file` — a fact read out of the fixture file itself (e.g. a film's
                     year). Declared as such; never presented as a measurement.
  * `input`        — a value the user supplied.

Consequence: a number cannot be printed without a declared source, because there
is no code path that formats one any other way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..qloo.trace import TraceRecorder

SOURCE_QLOO_CALL = "qloo_call"
SOURCE_FIXTURE_FILE = "fixture_file"
SOURCE_INPUT = "input"
SOURCE_RUN_INTERNAL = "run_internal"
SOURCE_UNKNOWN = "unknown"


@dataclass(frozen=True)
class NumberRef:
    label: str
    value: float | int
    source: str
    source_kind: str
    rendered: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "source": self.source,
            "source_kind": self.source_kind,
            "rendered": self.rendered,
        }


def _source_kind(source: str | None, call_id: str | None) -> tuple[str, str]:
    if call_id:
        return call_id, SOURCE_QLOO_CALL
    if source:
        if source.startswith("file:"):
            return source, SOURCE_FIXTURE_FILE
        if source.startswith("input:"):
            return source, SOURCE_INPUT
        if source.startswith("run:"):
            # A count of the pipeline's own bookkeeping (calls made, rows in the
            # trace). It is not a measurement and is never presented as one.
            return source, SOURCE_RUN_INTERNAL
        return source, SOURCE_UNKNOWN
    raise ValueError(
        "refusing to render a number with no declared source: pass call_id=... (Qloo-derived) "
        "or source='file:...' / 'input:...' / 'run:...'"
    )


@dataclass
class ProvenanceLedger:
    recorder: TraceRecorder
    data_status: str = "fixture"
    numbers: list[NumberRef] = field(default_factory=list)

    # -- registration ------------------------------------------------------
    def fmt(
        self,
        value: float | int | None,
        *,
        label: str,
        call_id: str | None = None,
        source: str | None = None,
        decimals: int = 2,
        dash: str = "—",
    ) -> str:
        """Format a number and record its provenance. `None` renders as a dash."""
        if value is None:
            return dash
        resolved_source, kind = _source_kind(source, call_id)
        rendered = f"{value:.{decimals}f}" if isinstance(value, float) else str(value)
        self.numbers.append(
            NumberRef(label=label, value=value, source=resolved_source, source_kind=kind, rendered=rendered)
        )
        return rendered

    def fmt_pct(
        self,
        value: float | None,
        *,
        label: str,
        call_id: str | None = None,
        source: str | None = None,
    ) -> str:
        if value is None:
            return "—"
        resolved_source, kind = _source_kind(source, call_id)
        rendered = f"{value * 100:.0f}%"
        self.numbers.append(
            NumberRef(label=label, value=value, source=resolved_source, source_kind=kind, rendered=rendered)
        )
        return rendered

    # -- audit -------------------------------------------------------------
    def traced_call_ids(self) -> set[str]:
        return {row.call_id for row in self.recorder.rows}

    def audit(self) -> dict[str, Any]:
        traced = self.traced_call_ids()
        qloo_backed = [n for n in self.numbers if n.source_kind == SOURCE_QLOO_CALL]
        fixture_backed = [n for n in self.numbers if n.source_kind == SOURCE_FIXTURE_FILE]
        run_backed = [n for n in self.numbers if n.source_kind == SOURCE_RUN_INTERNAL]
        unverified = [n for n in qloo_backed if n.source not in traced]
        return {
            "numbers_displayed": len(self.numbers),
            "qloo_call_backed": len(qloo_backed),
            "fixture_file_backed": len(fixture_backed),
            "run_internal": len(run_backed),
            "other_backed": len(fixture_backed) + len(run_backed),
            "unverified": [n.to_dict() for n in unverified],
            "distinct_call_ids": len({n.source for n in qloo_backed}),
            "trace_rows_available": len(self.recorder.rows),
            "data_status": self.data_status,
        }

    def problems(self) -> list[str]:
        problems = [
            f"{n['label']} = {n['rendered']} references call {n['source']}, which has no trace row"
            for n in self.audit()["unverified"]
        ]
        problems += [
            f"{n.label} = {n.rendered} has an undeclared source '{n.source}'"
            for n in self.numbers
            if n.source_kind == SOURCE_UNKNOWN
        ]
        return problems
