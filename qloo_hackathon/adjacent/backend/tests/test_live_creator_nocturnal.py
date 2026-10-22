"""Targeted live Creator-path regression for the reported Nocturnal Drifter failure.

This controlled case uses known reference films to exercise the live Creator
pipeline and its post-processing. It is not the unavailable original request
payload; it must never print provider bodies or credential material.
"""

from __future__ import annotations

import asyncio
import logging
import os

import pytest
from app.api.creator_routes import (
    CreatorRunRequest,
    ReferenceInput,
    _execute_creator_run,
)
from app.api.routes import run_store
from app.config import Settings

_HAS_KEY = bool((os.environ.get("QLOO_API_KEY") or "").strip())


@pytest.mark.live
@pytest.mark.skipif(not _HAS_KEY, reason="QLOO_API_KEY not available — live Creator test requires a real key")
def test_nocturnal_drifter_creator_pipeline_does_not_fail_with_typeerror(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Exercise resolution → analysis → Creator artifacts against live Qloo."""
    assert Settings.from_env().has_api_key

    request = CreatorRunRequest(
        title="Nocturnal Drifter",
        logline="An independent thriller following a lone night-shift drifter through a city.",
        genre="thriller",
        language="English",
        release_goal="Independent film release",
        references=[
            ReferenceInput(title="Nightcrawler", year=2014),
            ReferenceInput(title="After Hours", year=1985),
        ],
    )
    record = run_store.create(
        city="",
        venue_name="Creator: Nocturnal Drifter live regression",
        programme=request.seeds(),
    )

    caplog.set_level(logging.ERROR)
    asyncio.run(_execute_creator_run(record, request))

    # The route intentionally maps provider/tool exceptions to a safe failed
    # run. In this targeted case, failed means this live scenario needs triage;
    # logs carry only sanitized source-frame labels and exception type.
    assert record.status.value in {"completed", "insufficient"}, (
        "Live Nocturnal Drifter Creator pipeline terminated as failed; "
        f"phase={record.current_phase or 'unknown'}, "
        f"stop_reason={record.stop_reason or 'unknown'}, "
        f"error_type_logged={'TypeError' if 'error_type=TypeError' in caplog.text else 'not TypeError/unknown'}. "
        "Inspect sanitized log frames, not exception text or provider payloads."
    )
    assert "QLOO_API_KEY" not in caplog.text
