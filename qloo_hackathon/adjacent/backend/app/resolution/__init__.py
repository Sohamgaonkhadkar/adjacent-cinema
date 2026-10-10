"""Trusted entity resolution for Adjacent.

The resolver converts input programme items (title + year + optional external ID)
into verified Qloo entity IDs.  It NEVER assumes returned order matches input
order, and it NEVER trusts a mapping it cannot verify.

Match statuses:
    VERIFIED    — enough evidence confirms the entity identity
    AMBIGUOUS   — some evidence but not enough to confirm
    UNRESOLVED  — no entity found in Qloo
    MISMATCH    — entity found but clearly conflicts with input

Resolution methods (in priority order):
    1. /search with title + year → verify name + year match
    2. /entities with external ID → verify external ID is returned
"""

from __future__ import annotations

from .contract import MatchMethod, MatchStatus, ResolvedEntity

__all__ = ["MatchMethod", "MatchStatus", "ResolvedEntity"]
