"""Machine-readable rejection and exclusion reason codes.

Rule: reasons are decided by deterministic code in this module and in the domain
layer. Nothing else — and specifically no model, since none is involved — may
invent a reason string. The CLI renders the `detail` text that was produced here.

Precedence for a rejected *cohort* (documented so the behaviour is predictable):

    1. insufficient_members   — the group has fewer than MIN_COHORT_MEMBERS candidates
    2. insufficient_affinity  — no member clears the Medium band (>= 0.5)
    3. weak_evidence          — members clear Medium, but the evidence gate still
                                rejects the cohort (too few above Medium/High)

`rejected_cohort()` implements exactly that order and records the evidence gate's
own verdict alongside, so nothing is lost when a more specific code wins.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RejectionCode(StrEnum):
    """Why a candidate cohort did not survive the evidence gate."""

    WEAK_EVIDENCE = "weak_evidence"
    INSUFFICIENT_MEMBERS = "insufficient_members"
    INSUFFICIENT_AFFINITY = "insufficient_affinity"
    NO_VALID_COHORT = "no_valid_cohort"
    UNSCORED_MEMBERS = "unscored_members"


class ExclusionCode(StrEnum):
    """Why an individual candidate is not usable as a signature entity.

    NOTE: exclusions are annotations, never deletions. An excluded entity stays
    visible in the output, with this code, so the reader can disagree with it.
    """

    BELOW_MEDIUM = "below_medium"
    NO_AFFINITY_RETURNED = "no_affinity_returned"
    NOT_RETURNED_BY_CONTEXT = "not_returned_by_context"
    #: Popularity at or above POPULARITY_CEILING (cohorts.py). This threshold is a
    #: PRODUCT RULE, not a Qloo-published band: an entity the mass audience already
    #: knows is a poor "adjacent but undiscovered" target. Flagged, not hidden.
    OVERSATURATED = "oversaturated"


@dataclass(frozen=True)
class Rejection:
    """A cohort that was considered and refused. Rendered, never hidden."""

    cohort_id: str
    domain: str
    code: RejectionCode
    detail: str
    gate_reason_code: str | None = None
    gate_message: str = ""
    member_count: int = 0
    qualifying_members: int = 0
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cohort_id": self.cohort_id,
            "domain": self.domain,
            "reason_code": self.code.value,
            "detail": self.detail,
            "gate_reason_code": self.gate_reason_code,
            "gate_message": self.gate_message,
            "member_count": self.member_count,
            "qualifying_members": self.qualifying_members,
            "stats": self.stats,
        }


@dataclass(frozen=True)
class Exclusion:
    """A candidate excluded from a cohort's qualifying members, with its reason."""

    entity_id: str
    name: str | None
    code: ExclusionCode
    affinity: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "reason_code": self.code.value,
            "affinity": self.affinity,
        }
