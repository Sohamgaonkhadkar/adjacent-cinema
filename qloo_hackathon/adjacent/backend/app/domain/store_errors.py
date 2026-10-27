"""Shared persistence errors.

``DuplicateRequest`` lives here rather than in either repository module because
both the experiment repository and the poll mixin it composes need to raise it,
and a mixin cannot import the class from the module that imports the mixin.
``app.domain.experiment_repository`` re-exports it, so existing imports keep
working.
"""

from __future__ import annotations

from typing import Any


class DuplicateRequest(Exception):
    """Raised with the already-stored row when a request_id is replayed."""

    def __init__(self, existing: dict[str, Any]) -> None:
        self.existing = existing
        super().__init__("duplicate request_id")


__all__ = ["DuplicateRequest"]
