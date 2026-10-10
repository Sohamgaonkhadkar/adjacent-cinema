"""Shared pytest fixtures.

Also makes `app` importable when pytest is run from anywhere (the Makefile runs
it from `backend/`, but this keeps `pytest` working from the repo root too).
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402
from app.config import Settings  # noqa: E402

FAKE_KEY = "test-key-not-real-0000"


@pytest.fixture
def no_key_settings() -> Settings:
    """No key at all: mock mode. Pacing and retries disabled so tests stay fast."""
    return Settings.from_env(
        qloo_api_key=None,
        rate_limit_rps=0.0,
        max_retries=0,
        retry_backoff_base_s=0.0,
    )


@pytest.fixture
def fake_key_settings() -> Settings:
    """A non-real key, so the live client can be constructed against a fake transport."""
    return Settings.from_env(
        qloo_api_key=FAKE_KEY,
        rate_limit_rps=0.0,
        max_retries=0,
        retry_backoff_base_s=0.0,
    )
