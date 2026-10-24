"""Candidate cohort construction — deterministic, explainable, fixture-faithful.

A *candidate cohort* is a group of entities Qloo returned as adjacent to the
programme, grouped by a rule that can be stated and re-run. It is a **grouping
decision only**: it carries no scores of its own. Scores are attached later, by
the ranker, from a single scoring context (see `scoring.py`).

Construction rules, in order (deterministic):

  1. **Tag-linked clusters** (kind=`tag_cluster`). Within one entity domain, link
     any two candidates that share at least one Qloo tag id from the response.
     Connected components with >= 2 members become cohorts. This is the strongest
     available signal because it is a relationship Qloo actually returned.
  2. **Domain groups** (kind=`domain_group`). Candidates not already in a tag
     cluster are grouped by their entity domain. A group with >= 2 candidates
     becomes a cohort.
  3. **Singletons** (kind=`singleton_group`). A single remaining candidate is kept
     as a candidate cohort so it can be *explicitly rejected* as
     `insufficient_members` rather than silently disappearing.

Every cohort records why it exists (`construction_reason`), the machine-readable
basis for that reason (`construction_evidence`), and which Qloo call(s) its
members came from. Nothing here invents, adjusts or interpolates a measurement.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..qloo.models import BAND_HIGH_MIN, BAND_MEDIUM, ScoredEntity

# --- cohort kinds -----------------------------------------------------------

KIND_TAG_CLUSTER = "tag_cluster"
KIND_SUBTYPE_GROUP = "subtype_group"
KIND_DOMAIN_GROUP = "domain_group"
KIND_SINGLETON = "singleton_group"

#: Popularity at/above which a candidate is flagged OVERSATURATED (see
#: reasons.ExclusionCode). This is OUR product threshold, chosen so a mass-audience
#: title is never presented as an "adjacent, undiscovered" audience. It is not a
#: Qloo-published band and it is never used to change an affinity number.
POPULARITY_CEILING = 0.85

#: Domains the agent may expand into. Order is fixed so runs are reproducible.
#: (Cinema beachhead: the programme is films; adjacent culture is everything else.)
DEFAULT_EXPANSION_DOMAINS: tuple[str, ...] = (
    "urn:entity:artist",
    "urn:entity:movie",
    "urn:entity:tv_show",
    "urn:entity:book",
    "urn:entity:brand",
)


@dataclass(frozen=True)
class MemberEvidence:
    """One scored member, with the call that produced its numbers.

    `scored` is the untouched `ScoredEntity` from the response, so the evidence
    gate and any consumer see exactly what Qloo returned.
    """

    scored: ScoredEntity
    call_id: str
    is_marginal: bool  # Medium band (< High) — near the threshold, worth flagging
    qloo_attribution_status: str = "requested"
    allowed_qloo_seed_ids: tuple[str, ...] | None = None

    @property
    def entity_id(self) -> str:
        return self.scored.entity_id

    @property
    def name(self) -> str | None:
        return self.scored.name

    @property
    def affinity(self) -> float | None:
        return self.scored.affinity

    @property
    def popularity(self) -> float | None:
        return self.scored.popularity

    @property
    def band(self) -> str:
        return self.scored.band.value

    def qloo_attributions(self) -> list[dict[str, Any]]:
        """Return only validated per-seed attribution from Qloo's raw response.

        The provider's explainability object can vary or be absent. Preserve the
        evidence only when its shape, entity IDs and finite 0–1 scores validate;
        never infer a contribution from affinity alone.
        """
        raw = self.scored.raw if isinstance(self.scored.raw, dict) else {}
        query = raw.get("query") if isinstance(raw.get("query"), dict) else {}
        explanation = query.get("explainability") if isinstance(query.get("explainability"), dict) else {}
        values = explanation.get("signal.interests.entities")
        if not isinstance(values, list):
            return []

        valid: list[tuple[str, float]] = []
        allowed_seed_ids = (
            {seed_id.casefold() for seed_id in self.allowed_qloo_seed_ids}
            if self.allowed_qloo_seed_ids is not None
            else None
        )
        for item in values:
            if not isinstance(item, dict):
                continue
            entity_id = item.get("entity_id")
            score = item.get("score")
            if not isinstance(entity_id, str) or not entity_id.strip():
                continue
            entity_id = entity_id.strip()
            if allowed_seed_ids is not None and entity_id.casefold() not in allowed_seed_ids:
                continue
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                continue
            try:
                numeric_score = float(score)
            except (OverflowError, ValueError):
                continue
            if not math.isfinite(numeric_score) or not 0 <= numeric_score <= 1:
                continue
            valid.append((entity_id, numeric_score))

        # Conflicting/repeated provider entries are ambiguous. Drop every copy
        # rather than letting response order silently select a contribution.
        counts: dict[str, int] = {}
        for entity_id, _ in valid:
            normalized_id = entity_id.casefold()
            counts[normalized_id] = counts.get(normalized_id, 0) + 1
        return [
            {"entity_id": entity_id, "score": round(score, 6)}
            for entity_id, score in valid
            if counts[entity_id.casefold()] == 1
        ]

    def to_dict(self) -> dict[str, Any]:
        attributions = self.qloo_attributions()
        attribution_status = self.qloo_attribution_status
        if attribution_status == "requested":
            attribution_status = "returned" if attributions else "missing"
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "type": self.scored.type,
            "subtype": self.scored.subtype,
            "affinity": self.affinity,
            "band": self.band,
            "popularity": self.popularity,
            "is_marginal": self.is_marginal,
            "tags": [t.tag_id for t in self.scored.tags],
            "call_id": self.call_id,
            "qloo_attributions": attributions,
            "qloo_attribution_status": attribution_status,
        }


@dataclass
class CandidateCohort:
    """A grouping of candidate entities, before scoring."""

    cohort_id: str
    domain: str
    kind: str
    member_ids: list[str]
    construction_reason: str
    construction_evidence: dict[str, Any] = field(default_factory=dict)
    source_call_ids: list[str] = field(default_factory=list)

    # Filled by the ranker (scoring.py). Empty until then.
    members: list[MemberEvidence] = field(default_factory=list)
    excluded_members: list[Any] = field(default_factory=list)  # list[Exclusion]
    unscored_member_ids: list[str] = field(default_factory=list)
    context_id: str | None = None
    score: Any | None = None  # CohortScore
    verdict: Any | None = None  # EvidenceVerdict
    rejected: bool = False
    rejection: Any | None = None  # Rejection
    rank: int | None = None

    @property
    def qualifying_members(self) -> list[MemberEvidence]:
        return [m for m in self.members if m.affinity is not None and m.affinity >= BAND_MEDIUM]

    @property
    def marginal_members(self) -> list[MemberEvidence]:
        return [m for m in self.members if m.affinity is not None and m.affinity < BAND_HIGH_MIN]

    @property
    def member_count(self) -> int:
        return len(self.member_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cohort_id": self.cohort_id,
            "domain": self.domain,
            "kind": self.kind,
            "member_count": self.member_count,
            "qualifying_members": len(self.qualifying_members),
            "construction_reason": self.construction_reason,
            "construction_evidence": self.construction_evidence,
            "source_call_ids": self.source_call_ids,
            "context_id": self.context_id,
            "members": [m.to_dict() for m in self.members],
            "excluded_members": [e.to_dict() for e in self.excluded_members],
            "unscored_member_ids": self.unscored_member_ids,
            "score": self.score.to_dict() if self.score is not None else None,
            "verdict": self.verdict.as_dict() if self.verdict is not None else None,
            "rejected": self.rejected,
            "rejection": self.rejection.to_dict() if self.rejection is not None else None,
            "rank": self.rank,
        }


def _tag_ids(entity: ScoredEntity) -> set[str]:
    return {t.tag_id for t in entity.tags if t.tag_id}


def _tag_components(entities: Sequence[ScoredEntity]) -> list[list[ScoredEntity]]:
    """Connected components over "shares at least one tag id".

    Deterministic: entities are visited in the order given, and components are
    returned in order of first appearance.
    """
    tagged = [e for e in entities if _tag_ids(e)]
    by_tag: dict[str, list[str]] = {}
    for entity in tagged:
        for tag in _tag_ids(entity):
            by_tag.setdefault(tag, []).append(entity.entity_id)

    parent: dict[str, str] = {e.entity_id: e.entity_id for e in tagged}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)  # deterministic representative

    for ids in by_tag.values():
        for other in ids[1:]:
            union(ids[0], other)

    grouped: dict[str, list[ScoredEntity]] = {}
    for entity in tagged:
        grouped.setdefault(find(entity.entity_id), []).append(entity)
    return list(grouped.values())


def _dominant_tags(members: Sequence[ScoredEntity]) -> list[str]:
    """Tag ids shared by at least two members, most-shared first (deterministic)."""
    counts: dict[str, int] = {}
    for entity in members:
        for tag in _tag_ids(entity):
            counts[tag] = counts.get(tag, 0) + 1
    shared = [(tag, n) for tag, n in counts.items() if n >= 2]
    return [tag for tag, _n in sorted(shared, key=lambda kv: (-kv[1], kv[0]))]


def build_candidate_cohorts(
    candidates_by_domain: Mapping[str, Sequence[ScoredEntity]],
    *,
    source_call_ids: Mapping[str, str] | None = None,
    domains_in_order: Sequence[str] = DEFAULT_EXPANSION_DOMAINS,
) -> list[CandidateCohort]:
    """Group the candidate pool into candidate cohorts. Pure function, no I/O."""
    call_ids = dict(source_call_ids or {})
    cohorts: list[CandidateCohort] = []

    ordered_domains = list(domains_in_order) + [d for d in candidates_by_domain if d not in domains_in_order]

    for domain in ordered_domains:
        entities = [e for e in candidates_by_domain.get(domain, []) if e.entity_id]
        if not entities:
            continue
        domain_call = call_ids.get(domain)
        source_ids = [domain_call] if domain_call else []

        # 1. tag-linked clusters
        clustered: set[str] = set()
        for index, members in enumerate(_tag_components(entities), start=1):
            if len(members) < 2:
                continue  # a lone tagged entity falls through to the domain group
            for member in members:
                clustered.add(member.entity_id)
            shared = _dominant_tags(members)
            cohorts.append(
                CandidateCohort(
                    cohort_id=f"{domain}:tag_cluster:{index}",
                    domain=domain,
                    kind=KIND_TAG_CLUSTER,
                    member_ids=[m.entity_id for m in members],
                    construction_reason=(
                        f"{len(members)} {domain.split(':')[-1]} entities returned for this "
                        f"programme share Qloo tag(s) {', '.join(shared) or '(none)'} — grouped "
                        "together because the shared tags are a relationship Qloo returned, not "
                        "an assumption."
                    ),
                    construction_evidence={
                        "rule": "shared_tag_component",
                        "shared_tags": shared,
                        "member_count": len(members),
                        "call_id": domain_call,
                    },
                    source_call_ids=source_ids,
                )
            )

        # 2. subtype groups — Qloo returned a subtype for each candidate; a
        #    subtype shared by 2+ candidates is a returned relationship, so it
        #    groups them without us asserting anything.
        remaining = [e for e in entities if e.entity_id not in clustered]
        grouped: set[str] = set()
        for index, (subtype, members) in enumerate(_subtype_groups(remaining), start=1):
            if len(members) < 2:
                continue  # a lone subtype falls through to the domain group
            for member in members:
                grouped.add(member.entity_id)
            cohorts.append(
                CandidateCohort(
                    cohort_id=f"{domain}:subtype:{subtype}:{index}",
                    domain=domain,
                    kind=KIND_SUBTYPE_GROUP,
                    member_ids=[m.entity_id for m in members],
                    construction_reason=(
                        f"{len(members)} {_noun(domain)} entities returned for this programme "
                        f"share the Qloo subtype '{subtype}' — grouped because the subtype is a "
                        "property Qloo returned for every member, not a classification we applied."
                    ),
                    construction_evidence={
                        "rule": "shared_subtype_group",
                        "subtype": subtype,
                        "member_count": len(members),
                        "call_id": domain_call,
                    },
                    source_call_ids=source_ids,
                )
            )

        # 3/4. whatever is left, by domain; a lone leftover is kept so it can be
        #      explicitly rejected rather than silently dropped.
        leftover = [e for e in entities if e.entity_id not in clustered | grouped]
        if leftover:
            kind = KIND_DOMAIN_GROUP if len(leftover) >= 2 else KIND_SINGLETON
            reason = (
                f"{len(leftover)} additional {_noun(domain)} entities returned for this programme "
                "share no Qloo tag and no Qloo subtype with another candidate, so the only "
                "relationship Qloo returned for them is the entity type itself."
                if kind == KIND_DOMAIN_GROUP
                else (
                    f"a single {_noun(domain)} entity was returned that shares no Qloo tag and no "
                    "Qloo subtype with another candidate — kept as a candidate cohort so it can be "
                    "explicitly rejected as insufficient_members rather than silently dropped."
                )
            )
            cohorts.append(
                CandidateCohort(
                    cohort_id=f"{domain}:domain_group:{len(cohorts)}",
                    domain=domain,
                    kind=kind,
                    member_ids=[e.entity_id for e in leftover],
                    construction_reason=reason,
                    construction_evidence={
                        "rule": "domain_grouping_fallback",
                        "member_count": len(leftover),
                        "subtype_groups_excluded": sorted(grouped & {e.entity_id for e in entities}),
                        "call_id": domain_call,
                    },
                    source_call_ids=source_ids,
                )
            )

    return cohorts


def _noun(domain: str) -> str:
    """'urn:entity:tv_show' → 'tv_show' (used only in explanatory prose)."""
    return domain.split(":")[-1]


def _subtype_groups(
    entities: Sequence[ScoredEntity],
) -> list[tuple[str, list[ScoredEntity]]]:
    """Group by Qloo-returned subtype, in first-appearance order. Unsubtyped
    entities form a group under the label '(no subtype returned)'."""
    groups: dict[str, list[ScoredEntity]] = {}
    for entity in entities:
        key = entity.subtype or "(no subtype returned)"
        groups.setdefault(key, []).append(entity)
    return list(groups.items())


def members_by_id(entities: Iterable[ScoredEntity]) -> dict[str, ScoredEntity]:
    return {e.entity_id: e for e in entities}
