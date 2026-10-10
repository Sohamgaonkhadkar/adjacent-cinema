"""In-memory run store — the interface for run persistence.

This module provides a clean abstraction over run storage. The in-memory
implementation is used for M6; PostgreSQL will replace it later without
rewriting API or business logic.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INSUFFICIENT = "insufficient"


@dataclass
class RunEvent:
    """A single SSE event for a run."""

    event: str  # trace, resolution, taste_dna, cohort, done, insufficiency, error
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def sse_format(self) -> str:
        import json
        return f"event: {self.event}\ndata: {json.dumps(self.data, default=str)}\n\n"


@dataclass
class RunRecord:
    """A single run record in the store."""

    run_id: str
    status: RunStatus = RunStatus.PENDING
    created_at: float = field(default_factory=time.time)
    city: str = ""
    venue_name: str = ""
    programme: list[dict[str, Any]] = field(default_factory=list)
    current_phase: str = ""
    state_json: str | None = None
    result: dict[str, Any] | None = None
    trace: list[dict[str, Any]] = field(default_factory=list)
    events: list[RunEvent] = field(default_factory=list)
    error: str | None = None
    stop_reason: str | None = None
    stop_message: str | None = None
    # SSE subscribers
    _subscribers: list[asyncio.Queue] = field(default_factory=list, repr=False)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        # Send all existing events to new subscriber
        for event in self.events:
            q.put_nowait(event)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    def emit(self, event: RunEvent) -> None:
        import contextlib
        self.events.append(event)
        for q in self._subscribers:
            with contextlib.suppress(Exception):
                q.put_nowait(event)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "city": self.city,
            "venue_name": self.venue_name,
            "programme": self.programme,
            "current_phase": self.current_phase,
            "stop_reason": self.stop_reason,
            "stop_message": self.stop_message,
            "error": self.error,
            "result": self.result,
            "trace": self.trace,
        }


class RunStore:
    """In-memory run store. Replace with PostgreSQL later."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}

    def create(
        self,
        *,
        city: str,
        venue_name: str = "",
        programme: list[dict[str, Any]],
    ) -> RunRecord:
        run_id = str(uuid.uuid4())
        record = RunRecord(
            run_id=run_id,
            city=city,
            venue_name=venue_name,
            programme=programme,
        )
        self._runs[run_id] = record
        return record

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[RunRecord]:
        return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)


# Global store instance
run_store = RunStore()
