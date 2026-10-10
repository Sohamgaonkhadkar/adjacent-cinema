"""Domain layer for Milestone 1 — grouping, ranking, reasons, provenance.

Nothing in this package performs I/O except `scoring.CohortRanker`, which takes a
client and issues exactly one scoring call per scoring context. Everything else is
pure and therefore unit-testable without a fixture.
"""

from .cohorts import (
    DEFAULT_EXPANSION_DOMAINS,
    KIND_DOMAIN_GROUP,
    KIND_SINGLETON,
    KIND_TAG_CLUSTER,
    CandidateCohort,
    MemberEvidence,
    build_candidate_cohorts,
)
from .ledger import ProvenanceLedger
from .reasons import Exclusion, ExclusionCode, Rejection, RejectionCode
from .scoring import CohortRanker, CohortScore, RankingResult, ScoringContext

__all__ = [
    "DEFAULT_EXPANSION_DOMAINS",
    "KIND_DOMAIN_GROUP",
    "KIND_SINGLETON",
    "KIND_TAG_CLUSTER",
    "CandidateCohort",
    "CohortRanker",
    "CohortScore",
    "Exclusion",
    "ExclusionCode",
    "MemberEvidence",
    "ProvenanceLedger",
    "RankingResult",
    "Rejection",
    "RejectionCode",
    "ScoringContext",
    "build_candidate_cohorts",
]
