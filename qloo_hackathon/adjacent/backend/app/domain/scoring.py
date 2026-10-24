"""Cohort ranking under a single-normalisation discipline.

Why this file is shaped the way it is
-------------------------------------
Qloo affinity scores are normalised **per query**. Two scores produced by two
different queries are therefore not comparable as raw numbers. Building cohorts
by calling the scorer once per cohort would recreate exactly that error, so the
ranker never does it.

The rules implemented here:

  * **One logical operation.** `CohortRanker.build_and_rank_cohorts()` is recorded
    in the trace as exactly ONE `build_and_rank_cohorts` row. There is no
    `rank_cohort_A()`. The operation is what the agent calls.
  * **One scoring call per scoring context, never per cohort.** A scoring context
    is an entity type (`filter.type`), because the API scores one entity type per
    call. All cohorts in a domain are scored from that domain's single call, via
    `filter.results.entities` — the documented "score exactly these entities"
    filter. This is also the shape the live implementation will use; only the
    client changes.
  * **Scores are comparable only inside their context.** Each `CohortScore`
    carries its `context_id`, and the deterministic ordering uses only
    normalisation-safe keys first — evidence strength (band-based), novelty
    (a popularity percentile), and qualifying-member count. Raw affinity is used
    as the final tiebreaker *within* a context, and if it would ever have to
    order cohorts from different contexts the ranker raises a flag
    (`cross_context_tiebreak_used`) instead of doing it silently.

Nothing in this module invents, scales or adjusts a measurement.
"""

from __future__ import annotations

import itertools
import json
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .. import evidence
from ..qloo.errors import QlooError
from ..qloo.models import BAND_MEDIUM, ScoredEntity
from .cohorts import POPULARITY_CEILING, CandidateCohort, MemberEvidence
from .reasons import Exclusion, ExclusionCode, Rejection, RejectionCode

#: Lower is stronger. Anything the gate accepts is either "strong" or "moderate".
STRENGTH_RANK: dict[str, int] = {"strong": 0, "moderate": 1}
REJECTED_RANK = 9


@dataclass(frozen=True)
class CohortScore:
    """A cohort's numbers, all of which come from ONE scoring context."""

    context_id: str
    call_id: str
    mean_affinity: float | None
    max_affinity: float | None
    min_affinity: float | None
    median_popularity: float | None
    novelty_proxy: float | None
    qualifying_members: int
    total_members: int
    member_affinities: tuple[float, ...] = ()
    partial: bool = False  # some members were not returned by the scoring call

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "call_id": self.call_id,
            "mean_affinity": self.mean_affinity,
            "max_affinity": self.max_affinity,
            "min_affinity": self.min_affinity,
            "median_popularity": self.median_popularity,
            "novelty_proxy": self.novelty_proxy,
            "qualifying_members": self.qualifying_members,
            "total_members": self.total_members,
            "partial": self.partial,
        }


@dataclass(frozen=True)
class ScoringContext:
    """One entity type, scored in one call. The unit of comparability."""

    context_id: str
    domain: str
    call_id: str
    filter_type: str
    data_status: str
    requested_ids: tuple[str, ...]
    scored: Mapping[str, ScoredEntity]
    explainability_status: str = "not_requested_limit"

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "domain": self.domain,
            "call_id": self.call_id,
            "filter_type": self.filter_type,
            "data_status": self.data_status,
            "requested": len(self.requested_ids),
            "returned": len(self.scored),
            "explainability_status": self.explainability_status,
        }


@dataclass
class RankingResult:
    operation_call_id: str
    contexts: list[ScoringContext] = field(default_factory=list)
    all_cohorts: list[CandidateCohort] = field(default_factory=list)
    ranked: list[CandidateCohort] = field(default_factory=list)
    rejected: list[CandidateCohort] = field(default_factory=list)
    ordering: list[dict[str, Any]] = field(default_factory=list)
    cross_context_tiebreak_used: bool = False
    scoring_call_ids: list[str] = field(default_factory=list)
    qloo_calls_made: int = 0
    unscored_member_ids: list[str] = field(default_factory=list)

    @property
    def scored_entity_count(self) -> int:
        return sum(len(c.scored) for c in self.contexts)


def _mean(values: Sequence[float]) -> float | None:
    return round(statistics.fmean(values), 6) if values else None


def _median(values: Sequence[float]) -> float | None:
    return round(statistics.median(values), 6) if values else None


def _is_explainability_parameter_rejection(error: QlooError) -> bool:
    """Return true only for an explicit 4xx rejection of this optional field."""
    if error.status not in {400, 422} or error.endpoint != "/v2/insights":
        return False
    detail = error.detail
    if isinstance(detail, (dict, list)):
        message = json.dumps(detail, ensure_ascii=False).lower()
    else:
        message = str(detail or "").lower()
    if "feature.explainability" not in message:
        return False
    return any(
        marker in message
        for marker in (
            "unsupported",
            "unknown parameter",
            "unknown field",
            "unexpected",
            "unrecognized",
            "not allowed",
            "not supported",
            "invalid parameter",
            "invalid value",
            "validation",
            "must be",
            "expected",
            "valid boolean",
        )
    )


class CohortRanker:
    """Ranks candidate cohorts from a single-normalisation scoring context.

    `client` is any object satisfying the Qloo client interface
    (`QlooClient` or `MockQlooClient>=  both work unchanged).
    """

    def __init__(
        self,
        client: Any,
        *,
        programme_ids: Sequence[str],
        take: int = 50,
        tool: str = "build_and_rank_cohorts",
        max_explainability_fallbacks: int | None = None,
    ) -> None:
        if not programme_ids:
            raise ValueError("CohortRanker requires at least one programme entity id as a signal")
        self.client = client
        self.programme_ids = list(programme_ids)
        self.take = take
        self.tool = tool
        self.max_explainability_fallbacks = max_explainability_fallbacks

    # -- the single logical operation --------------------------------------
    async def build_and_rank_cohorts(self, cohorts: Sequence[CandidateCohort]) -> RankingResult:
        """Score every cohort, then rank. ONE logical operation, ONE call per context."""
        recorder = self.client.recorder
        source = "mock" if type(self.client).__name__ == "MockQlooClient" else "qloo"
        data_status = "fixture" if source == "mock" else "measured"

        by_domain: dict[str, list[CandidateCohort]] = {}
        for cohort in cohorts:
            by_domain.setdefault(cohort.domain, []).append(cohort)

        result = RankingResult(operation_call_id="", all_cohorts=list(cohorts))
        fallback_limit = (
            len(by_domain)
            if self.max_explainability_fallbacks is None
            else max(0, self.max_explainability_fallbacks)
        )
        fallbacks_remaining = min(fallback_limit, len(by_domain))

        with recorder.record(
            tool=self.tool,
            endpoint="/v2/insights",
            params={},  # a logical operation, not a single HTTP call
            source=source,  # type: ignore[arg-type]
            data_status=data_status,  # type: ignore[arg-type]
        ) as operation:
            operation.add_note(
                "LOGICAL OPERATION 'build_and_rank_cohorts': one scoring call per scoring "
                "context (entity type), never one per cohort."
            )
            operation.add_note(
                "Cohort scores are comparable ONLY within their context_id. Cross-context "
                "ordering uses band strength, novelty proxy and qualifying-member count."
            )

            for domain in sorted(by_domain):
                group = by_domain[domain]
                requested: list[str] = []
                for cohort in group:
                    for entity_id in cohort.member_ids:
                        if entity_id not in requested:
                            requested.append(entity_id)

                context_id = f"ctx:{domain}"
                # Enable the optional field only when a single bounded retry can
                # be afforded. This preserves the run's call budget and keeps
                # ordinary scoring available when no fallback capacity remains.
                if len(requested) > 12:
                    explainability_status = "not_requested_limit"
                elif fallbacks_remaining <= 0:
                    explainability_status = "not_requested_budget"
                else:
                    explainability_status = "requested"
                explainability_requested = explainability_status == "requested"
                request_args = {
                    "filter_type": domain,
                    "signal_interests_entities": self.programme_ids,
                    "filter_results_entities": requested,
                    "take": self.take,
                    "tool": f"score_context:{domain}",
                }
                if explainability_requested:
                    request_args["feature_explainability"] = True
                try:
                    response = await self.client.insights(**request_args)
                except QlooError as exc:
                    if not (
                        explainability_requested
                        and fallbacks_remaining > 0
                        and _is_explainability_parameter_rejection(exc)
                    ):
                        raise
                    fallbacks_remaining -= 1
                    result.qloo_calls_made += 1
                    explainability_status = "unsupported"
                    operation.add_note(
                        f"optional feature.explainability rejected for {domain} "
                        f"by call {exc.call_id or 'unknown'} (HTTP {exc.status}); retried once without it. "
                        "Scoring remains measured; per-seed attribution is unavailable."
                    )
                    request_args.pop("feature_explainability", None)
                    response = await self.client.insights(**request_args)
                result.qloo_calls_made += 1
                scored = {e.entity_id: e for e in response.results if e.entity_id}
                context = ScoringContext(
                    context_id=context_id,
                    domain=domain,
                    call_id=response.call_id,
                    filter_type=domain,
                    data_status=response.data_status,
                    requested_ids=tuple(requested),
                    scored=scored,
                    explainability_status=explainability_status,
                )
                result.contexts.append(context)
                result.scoring_call_ids.append(response.call_id)

                for cohort in group:
                    self._attach_scores(cohort, context)
                    self._gate(cohort)
                    result.unscored_member_ids.extend(cohort.unscored_member_ids)

            operation.add_note(
                f"scoring contexts: {len(result.contexts)} · scoring calls: "
                f"{len(result.scoring_call_ids)} · cohorts scored: {len(cohorts)} · "
                f"entities scored: {result.scored_entity_count}"
            )
            operation.add_note(f"sub-call ids: {', '.join(result.scoring_call_ids) or 'none'}")
            operation.set_result(status=200, result_count=result.scored_entity_count)
            result.operation_call_id = operation.call_id

        self._order(result)
        return result

    # -- scoring a cohort inside its context -------------------------------
    def _attach_scores(self, cohort: CandidateCohort, context: ScoringContext) -> None:
        members: list[MemberEvidence] = []
        unscored: list[str] = []
        for entity_id in cohort.member_ids:
            entity = context.scored.get(entity_id)
            if entity is None or entity.affinity is None:
                unscored.append(entity_id)
                continue
            members.append(
                MemberEvidence(
                    scored=entity,
                    call_id=context.call_id,
                    is_marginal=entity.affinity < evidence.BAND_HIGH,
                    qloo_attribution_status=context.explainability_status,
                    allowed_qloo_seed_ids=tuple(self.programme_ids),
                )
            )
        # Deterministic member order: affinity desc, then entity id.
        members.sort(key=lambda m: (-(m.affinity or 0.0), m.entity_id))
        cohort.members = members
        cohort.unscored_member_ids = unscored
        cohort.context_id = context.context_id

        # Exclusions are annotations on individual members, never deletions, and
        # they never change the evidence gate: the gate judges the whole scored
        # cohort. They answer a different question — "which member may be used as
        # this cohort's signature?"
        excluded: list[Exclusion] = []
        for entity_id in unscored:
            excluded.append(
                Exclusion(
                    entity_id=entity_id,
                    name=None,
                    code=ExclusionCode.NOT_RETURNED_BY_CONTEXT,
                    affinity=None,
                )
            )
        for member in members:
            if member.affinity is None:
                excluded.append(
                    Exclusion(
                        entity_id=member.entity_id,
                        name=member.name,
                        code=ExclusionCode.NO_AFFINITY_RETURNED,
                        affinity=None,
                    )
                )
            elif member.affinity < BAND_MEDIUM:
                excluded.append(
                    Exclusion(
                        entity_id=member.entity_id,
                        name=member.name,
                        code=ExclusionCode.BELOW_MEDIUM,
                        affinity=member.affinity,
                    )
                )
            elif member.popularity is not None and member.popularity >= POPULARITY_CEILING:
                excluded.append(
                    Exclusion(
                        entity_id=member.entity_id,
                        name=member.name,
                        code=ExclusionCode.OVERSATURATED,
                        affinity=member.affinity,
                    )
                )
        cohort.excluded_members = excluded

        affinities = [m.affinity for m in members if m.affinity is not None]
        popularities = [m.popularity for m in members if m.popularity is not None]
        median_pop = _median(popularities)
        cohort.score = CohortScore(
            context_id=context.context_id,
            call_id=context.call_id,
            mean_affinity=_mean(affinities),
            max_affinity=round(max(affinities), 6) if affinities else None,
            min_affinity=round(min(affinities), 6) if affinities else None,
            median_popularity=median_pop,
            novelty_proxy=round(1.0 - median_pop, 6) if median_pop is not None else None,
            qualifying_members=sum(1 for a in affinities if a >= BAND_MEDIUM),
            total_members=len(members),
            member_affinities=tuple(affinities),
            partial=bool(unscored),
        )

    # -- the evidence gate -------------------------------------------------
    @staticmethod
    def _gate(cohort: CandidateCohort) -> None:
        """Reuse the existing evidence gate; then map its verdict to a reason code."""
        members = [m.scored for m in cohort.members]
        verdict = evidence.evaluate_cohort(members)
        cohort.verdict = verdict
        if verdict.sufficient:
            return

        cohort.rejected = True
        qualifying = sum(1 for m in members if m.affinity is not None and m.affinity >= BAND_MEDIUM)
        # Documented precedence — see domain/reasons.py.
        if cohort.member_count < evidence.MIN_COHORT_MEMBERS:
            code = RejectionCode.INSUFFICIENT_MEMBERS
            detail = (
                f"only {cohort.member_count} candidate(s) in this grouping; "
                f"{evidence.MIN_COHORT_MEMBERS} are required before a cohort can be judged."
            )
        elif qualifying == 0:
            code = RejectionCode.INSUFFICIENT_AFFINITY
            detail = f"none of the {cohort.member_count} candidates clear the Medium band (>= {BAND_MEDIUM})."
        else:
            code = RejectionCode.WEAK_EVIDENCE
            detail = verdict.message or "evidence gate rejected the cohort."

        cohort.rejection = Rejection(
            cohort_id=cohort.cohort_id,
            domain=cohort.domain,
            code=code,
            detail=detail,
            gate_reason_code=verdict.reason_code,
            gate_message=verdict.message,
            member_count=cohort.member_count,
            qualifying_members=qualifying,
            stats=dict(verdict.stats),
        )

    # -- deterministic ordering -------------------------------------------
    @staticmethod
    def _order(result: RankingResult) -> None:
        def safe_key(cohort: CandidateCohort) -> tuple[Any, ...]:
            verdict = cohort.verdict
            if verdict is None or not verdict.sufficient:
                strength = REJECTED_RANK
            else:
                strength = STRENGTH_RANK.get(verdict.reason_code, 2)
            score = cohort.score
            novelty = score.novelty_proxy if score and score.novelty_proxy is not None else -1.0
            return (strength, -novelty, -len(cohort.qualifying_members))

        # Cross-context tiebreak check: would raw affinity be needed to separate
        # cohorts that live in DIFFERENT normalisations?
        all_cohorts = list(result.all_cohorts)
        prelim = sorted(all_cohorts, key=lambda c: (safe_key(c), c.cohort_id))
        for a, b in itertools.pairwise(prelim):
            if safe_key(a) == safe_key(b) and a.context_id != b.context_id:
                result.cross_context_tiebreak_used = True
                break

        def full_key(cohort: CandidateCohort) -> tuple[Any, ...]:
            score = cohort.score
            mean = score.mean_affinity if score and score.mean_affinity is not None else -1.0
            # Affinity is the LAST numeric key and is only ever decisive WITHIN a
            # context (guarded by the flag above).
            return (*safe_key(cohort), -mean, cohort.cohort_id)

        ordered = sorted(all_cohorts, key=full_key)
        result.ranked = [c for c in ordered if not c.rejected]
        result.rejected = [c for c in ordered if c.rejected]
        for index, cohort in enumerate(result.ranked, start=1):
            cohort.rank = index
        result.ordering = [
            {
                "rank": cohort.rank,
                "cohort_id": cohort.cohort_id,
                "context_id": cohort.context_id,
                "strength": cohort.verdict.reason_code if cohort.verdict else None,
                "novelty_proxy": cohort.score.novelty_proxy if cohort.score else None,
                "qualifying_members": len(cohort.qualifying_members),
                "mean_affinity_within_context": (cohort.score.mean_affinity if cohort.score else None),
                "reasoning": (
                    "ordered by evidence strength → novelty proxy → qualifying members; "
                    "mean affinity is a within-context tiebreaker only"
                ),
            }
            for cohort in ordered
            if not cohort.rejected
        ]
