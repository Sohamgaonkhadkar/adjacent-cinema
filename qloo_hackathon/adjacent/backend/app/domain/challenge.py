"""Decision Challenge — challenge a recommendation instead of accepting it.

Three questions, answered from evidence the run **already holds**:

1. **Necessity** — would the recommendation survive without Qloo's cultural
   affinity signal? Two counterfactuals are computed over the same retrieved
   candidates:
     * *affinity withheld*: every ordering key that depends on an affinity
       number is removed, leaving popularity novelty, breadth and the cohort id;
     * *popularity-only baseline*: what a "biggest overlap wins" approach would
       have recommended from the same candidates.
   If the winner is unchanged, that is reported as unchanged — together with
   whether the order below it moved and whether affinity decided any adjacent
   pair at all.

2. **Stability** — does the recommendation survive losing one of its own
   evidence items? Each scored member of each ranked cohort is removed in turn,
   the cohort is re-scored with the production arithmetic
   (:func:`app.domain.scoring.cohort_score_from`), re-gated with the production
   gate (:func:`app.evidence.evaluate_cohort`), and the whole set is re-ordered
   with the production ordering (:meth:`app.domain.scoring.CohortRanker._order`).

3. **Next checks** — which specific gaps in this run's evidence are worth
   closing, and what would close them. Deterministic rules over this run's own
   numbers; no model-generated advice.

Design constraints this module obeys:

* **No I/O and no Qloo calls.** Everything is recomputed from the finished
  run's cached evidence, so a challenge can never quietly spend quota or turn a
  fixture run into a partly-live one.
* **One implementation of the arithmetic.** The counterfactual imports the
  production score, gate and ordering functions. It does not reimplement them.
* **No invented numbers.** There is no confidence, probability, likelihood or
  percentage anywhere: a decision is *stable* under a stated rule or it is not,
  and the rule is printed next to the verdict.
* **Deterministic.** Two calls on the same state return byte-identical output;
  there are no clocks, no randomness and no hash-order dependence.

A counterfactual is a *diagnostic*, not a claim about the world. "Affinity
withheld changes the winner" does not prove the affinity evidence is correct;
"affinity withheld changes nothing" does not prove the affinity evidence is
uninformative. The payload says so in ``limits``.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from .. import evidence
from ..qloo.models import BAND_MEDIUM
from .cohorts import CandidateCohort, MemberEvidence
from .scoring import CohortRanker, RankingResult, cohort_score_from

if TYPE_CHECKING:  # pragma: no cover - import cycle avoidance
    from ..agent.state import AdjacentState

SCHEMA = "adjacent.decision-challenge/1"

#: Coordinates are "stable" / "fragile" / "undetermined" only. No numeric score.
STABLE = "stable"
FRAGILE = "fragile"
UNDETERMINED = "undetermined"

#: Minimum evaluated leave-one-out scenarios before "stable" may be claimed.
#: One surviving removal is not evidence of robustness.
MIN_SCENARIOS_FOR_STABLE = 2

#: How close (in novelty terms) a runner-up must be to count as "marginal".
MARGINAL_NOVELTY_DELTA = 0.05

#: The production ordering keys, named in the order they are compared.
ORDER_KEYS = (
    "evidence_strength",
    "novelty_proxy",
    "qualifying_members",
    "mean_affinity_within_context",
    "cohort_id",
)

#: Which of those keys are derived from an affinity number. Removing the
#: affinity signal removes exactly these.
AFFINITY_DERIVED_KEYS = frozenset(
    {"evidence_strength", "qualifying_members", "mean_affinity_within_context"}
)

PUBLIC_LIMITS: tuple[str, ...] = (
    "Cultural affinity is a Qloo taste measurement. It is not attendance, audience "
    "size, conversion, revenue or an outcome forecast, and nothing here estimates them.",
    "A counterfactual is a diagnostic over this run's evidence, not proof that the "
    "affinity signal is correct, complete, or free of bias.",
    "Removing a comparable film from the programme would require new Qloo scoring calls. "
    "That scenario is offered as a next check, never simulated here.",
    "Qloo's behavioural graph may already contain the programme titles themselves. "
    "Adjacent does not currently control for that exposure, so a live result may partly "
    "reflect how those titles have already been received.",
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _score_field(cohort: CandidateCohort, field: str) -> float | None:
    score = cohort.score
    if score is None:
        return None
    value = getattr(score, field, None)
    return float(value) if isinstance(value, (int, float)) else None


def _strength(cohort: CandidateCohort) -> int:
    """Lower is stronger. Mirrors the ranker's own mapping, reusing its table."""
    from .scoring import REJECTED_RANK, STRENGTH_RANK

    verdict = cohort.verdict
    if verdict is None or not verdict.sufficient:
        return REJECTED_RANK
    return STRENGTH_RANK.get(str(verdict.reason_code), 2)


def _clone(cohort: CandidateCohort) -> CandidateCohort:
    """A mutable copy safe to re-score and re-order without touching the run."""
    return CandidateCohort(
        cohort_id=cohort.cohort_id,
        domain=cohort.domain,
        kind=cohort.kind,
        member_ids=list(cohort.member_ids),
        construction_reason=cohort.construction_reason,
        construction_evidence=dict(cohort.construction_evidence or {}),
        source_call_ids=list(cohort.source_call_ids),
        members=list(cohort.members),
        excluded_members=list(cohort.excluded_members),
        unscored_member_ids=list(cohort.unscored_member_ids),
        context_id=cohort.context_id,
        score=cohort.score,
        verdict=cohort.verdict,
        rejected=cohort.rejected,
        rejection=cohort.rejection,
        rank=None,
    )


def _order_clones(clones: Sequence[CandidateCohort]) -> tuple[list[str], list[str]]:
    """Run the production ordering over a set of cohort clones.

    Returns ``(ranked_ids, rejected_ids)``. This calls the real
    :meth:`CohortRanker._order`, so a counterfactual cannot disagree with the
    product's own ranking rules.
    """
    result = RankingResult(operation_call_id="counterfactual", all_cohorts=list(clones))
    CohortRanker._order(result)
    return (
        [c.cohort_id for c in result.ranked],
        [c.cohort_id for c in result.rejected],
    )


def cohort_labels(cohorts: Sequence[CandidateCohort]) -> dict[str, str]:
    """Readable, unique labels: ``domain · strongest member name``.

    ``domain · kind`` alone collides (two artist tag-clusters are common), and a
    colliding label in a counterfactual table is worse than no label — the reader
    cannot tell which cohort moved. Labels are de-duplicated deterministically.
    """
    base: dict[str, str] = {}
    for cohort in cohorts:
        domain = cohort.domain.replace("urn:entity:", "")
        top = cohort.members[0].name if cohort.members else None
        base[cohort.cohort_id] = f"{domain} · {top}" if top else f"{domain} · {cohort.kind}"

    grouped: dict[str, list[str]] = {}
    for cohort_id, label in base.items():
        grouped.setdefault(label, []).append(cohort_id)
    labels: dict[str, str] = {}
    for label, ids in grouped.items():
        if len(ids) == 1:
            labels[ids[0]] = label
        else:
            for index, cohort_id in enumerate(ids, start=1):
                labels[cohort_id] = f"{label} ({index})"
    return labels


def _member_view(member: MemberEvidence) -> dict[str, Any]:
    return {
        "entity_id": member.entity_id,
        "name": member.name,
        "affinity": member.affinity,
        "band": member.band,
        "popularity": member.popularity,
        "call_id": member.call_id,
    }


def _decisive_key(
    left: CandidateCohort, right: CandidateCohort, ranked_order: Sequence[str]
) -> str:
    """Which production key first separates two adjacent cohorts?"""
    position = {cid: index for index, cid in enumerate(ranked_order)}

    def key(cohort: CandidateCohort) -> tuple[Any, ...]:
        novelty = _score_field(cohort, "novelty_proxy")
        mean = _score_field(cohort, "mean_affinity")
        return (
            _strength(cohort),
            -(novelty if novelty is not None else -1.0),
            -len(cohort.qualifying_members),
            -(mean if mean is not None else -1.0),
            position.get(cohort.cohort_id, len(position)),
        )

    left_key, right_key = key(left), key(right)
    for index, name in enumerate(ORDER_KEYS):
        if left_key[index] != right_key[index]:
            return name
    return ORDER_KEYS[-1]


# ---------------------------------------------------------------------------
# 1. Necessity
# ---------------------------------------------------------------------------


def _withheld_key(cohort: CandidateCohort) -> tuple[Any, ...]:
    """Affinity-withheld ordering: novelty → breadth → id.

    Every affinity-derived key is gone. What remains is a provider field that is
    *not* an affinity (popularity, via the novelty proxy), the size of the
    grouping, and a deterministic tie-break.
    """
    novelty = _score_field(cohort, "novelty_proxy")
    admitted = 0 if len(cohort.members) >= evidence.MIN_COHORT_MEMBERS else 1
    return (
        admitted,
        -(novelty if novelty is not None else -1.0),
        -len(cohort.members),
        cohort.cohort_id,
    )


def _popularity_key(cohort: CandidateCohort) -> tuple[Any, ...]:
    """Popularity-only baseline: the most mainstream grouping wins."""
    median_popularity = _score_field(cohort, "median_popularity")
    admitted = 0 if len(cohort.members) >= evidence.MIN_COHORT_MEMBERS else 1
    return (
        admitted,
        -(median_popularity if median_popularity is not None else -1.0),
        -len(cohort.members),
        cohort.cohort_id,
    )


def _compare_orders(
    production: Sequence[str],
    counterfactual: Sequence[str],
    labels: dict[str, str],
) -> dict[str, Any]:
    """Describe how a counterfactual ordering differs from the production one."""
    production_winner = production[0] if production else None
    counter_winner = counterfactual[0] if counterfactual else None

    position_before = {cid: index + 1 for index, cid in enumerate(production)}
    position_after = {cid: index + 1 for index, cid in enumerate(counterfactual)}
    moves = [
        {
            "cohort_id": cid,
            "label": labels.get(cid, cid),
            "rank_before": position_before[cid],
            "rank_after": position_after[cid],
            "delta": position_before[cid] - position_after[cid],
        }
        for cid in production
        if cid in position_after and position_before[cid] != position_after[cid]
    ]
    only_before = [cid for cid in production if cid not in position_after]
    only_after = [cid for cid in counterfactual if cid not in position_before]

    return {
        "production_winner": production_winner,
        "counterfactual_winner": counter_winner,
        "winner_changed": production_winner != counter_winner,
        "moves": moves,
        "ranks_moved": len(moves),
        "changed_below_first": any(move["rank_before"] > 1 for move in moves),
        "dropped_out": only_before,
        "entered": only_after,
    }


def _necessity(
    cohorts: Sequence[CandidateCohort],
    production: Sequence[str],
    labels: dict[str, str],
) -> dict[str, Any]:
    """Two counterfactuals over the *admitted* pool, plus the gate channel.

    The admitted pool is held fixed deliberately: it isolates the question "does
    the affinity number change which cohort comes first?" from the separate
    question "does the affinity *gate* change which cohorts are shown at all?".
    Those are reported as two distinct channels rather than conflated, because a
    counterfactual that silently changes the candidate set as well as the
    ordering cannot be interpreted.
    """
    by_id = {c.cohort_id: c for c in cohorts}
    pool = [by_id[cid] for cid in production if cid in by_id]

    withheld = sorted(pool, key=_withheld_key)
    popularity = sorted(pool, key=_popularity_key)
    withheld_ids = [c.cohort_id for c in withheld]
    popularity_ids = [c.cohort_id for c in popularity]

    # If the top two are identical on every non-affinity key, the production
    # winner was decided by affinity — but withholding affinity would still put
    # *one* of them first, because of the id tie-break. Saying "unchanged" there
    # would hide the result, so it is detected and reported explicitly.
    top_pair_tied = False
    if len(pool) >= 2:
        first_keys = [cid for cid in production[:2] if cid in by_id]
        if len(first_keys) == 2:
            left, right = by_id[first_keys[0]], by_id[first_keys[1]]
            top_pair_tied = _withheld_key(left)[:-1] == _withheld_key(right)[:-1]

    withheld_cmp = _compare_orders(production, withheld_ids, labels)
    popularity_cmp = _compare_orders(production, popularity_ids, labels)

    # Which adjacent pair in the production list was separated by affinity?
    decisive = []
    for left_id, right_id in itertools.pairwise(production):
        left, right = by_id.get(left_id), by_id.get(right_id)
        if left is None or right is None:
            continue
        key = _decisive_key(left, right, production)
        decisive.append(
            {
                "left": left_id,
                "right": right_id,
                "decided_by": key,
                "affinity_derived": key in AFFINITY_DERIVED_KEYS,
            }
        )
    affinity_pairs = [row for row in decisive if row["affinity_derived"]]

    # The gate is a second, separate contribution channel: removing affinity
    # replaces the affinity threshold with a purely structural one.
    admitted_with_affinity = set(production)
    structurally_admitted = {
        c.cohort_id for c in cohorts if len(c.members) >= evidence.MIN_COHORT_MEMBERS
    }
    suppressed = sorted(structurally_admitted - admitted_with_affinity)
    admitted_without_structure = sorted(admitted_with_affinity - structurally_admitted)

    return {
        "method": (
            "Both counterfactuals run over the same admitted candidate pool, so only the ordering "
            "inputs change. 'Affinity withheld' removes every key derived from an affinity number "
            "and orders by novelty, breadth and id. 'Popularity-only' orders the same pool by "
            "median popularity — what a biggest-overlap-wins approach would recommend. The effect "
            "of the affinity gate on which cohorts are admitted at all is reported separately, "
            "because that is a different question with a different answer."
        ),
        "qloo_calls_made": 0,
        "pool_size": len(pool),
        "affinity_withheld": {
            **withheld_cmp,
            "order": [
                {"cohort_id": cid, "label": labels.get(cid, cid)} for cid in withheld_ids
            ],
            "ordering_keys": ["novelty_proxy", "scored_members", "cohort_id"],
            "removed_keys": sorted(AFFINITY_DERIVED_KEYS),
            "top_pair_tied_without_affinity": top_pair_tied,
            "runner_up": production[1] if len(production) > 1 else None,
        },
        "popularity_only": {
            **popularity_cmp,
            "order": [
                {"cohort_id": cid, "label": labels.get(cid, cid)} for cid in popularity_ids
            ],
            "ordering_keys": ["median_popularity", "scored_members", "cohort_id"],
        },
        "affinity_decided_pairs": affinity_pairs,
        "adjacent_pairs_examined": len(decisive),
        "gate": {
            "admitted_with_affinity_gate": sorted(admitted_with_affinity),
            "structurally_admitted": sorted(structurally_admitted),
            "suppressed_by_affinity_gate": suppressed,
            "admitted_without_structural_support": admitted_without_structure,
        },
        "production_order": list(production),
    }


def _necessity_statement(necessity: dict[str, Any], labels: dict[str, str]) -> str:
    """One deterministic sentence a programmer can act on."""
    withheld = necessity["affinity_withheld"]
    popularity = necessity["popularity_only"]
    lines: list[str] = []

    winner = withheld["production_winner"]
    winner_label = labels.get(winner, winner or "the recommendation")
    if not winner:
        return "There was no ranking to challenge: no cohort cleared the evidence gate."

    if withheld["winner_changed"]:
        alt = labels.get(withheld["counterfactual_winner"], withheld["counterfactual_winner"])
        lines.append(
            f"Removing Qloo's affinity numbers changes the recommendation from {winner_label} "
            f"to {alt}. That is a warning, not a verdict: check the evidence behind both."
        )

    if withheld["top_pair_tied_without_affinity"]:
        runner_id = necessity["affinity_withheld"].get("runner_up")
        runner_label = labels.get(runner_id, runner_id or "the runner-up")
        lines.append(
            f"{winner_label} and {runner_label} are indistinguishable once the affinity numbers are "
            f"removed — same evidence strength, same novelty, same breadth — so affinity is the only "
            f"thing that puts one in front of the other. Treat the top two as one option."
        )
    elif not withheld["winner_changed"]:
        if withheld["ranks_moved"] == 0:
            lines.append(
                f"With Qloo's affinity numbers removed, the recommendation is still "
                f"{winner_label} and the order below it does not move: affinity separated "
                f"{len(necessity['affinity_decided_pairs'])} of "
                f"{necessity['adjacent_pairs_examined']} adjacent pairs, so strength and "
                f"popularity decided this list."
            )
        else:
            lines.append(
                f"With Qloo's affinity numbers removed the recommendation is still {winner_label}, "
                f"but {withheld['ranks_moved']} other "
                f"position{'s' if withheld['ranks_moved'] != 1 else ''} change."
            )
    if popularity["winner_changed"]:
        alt = labels.get(popularity["counterfactual_winner"], popularity["counterfactual_winner"])
        lines.append(
            f"A biggest-overlap-wins approach would have recommended {alt} instead — so the taste "
            f"signal is what separates this recommendation from the mainstream pick."
        )
    else:
        lines.append(
            "A biggest-overlap-wins approach would have recommended the same cohort, so this "
            "recommendation is not distinguished from the mainstream pick by taste alone."
        )

    suppressed = necessity["gate"]["suppressed_by_affinity_gate"]
    if suppressed:
        lines.append(
            f"{len(suppressed)} candidate grouping{'s' if len(suppressed) != 1 else ''} had enough "
            f"scored members to be considered "
            f"but were suppressed by the affinity threshold: {', '.join(labels.get(cid, cid) for cid in suppressed)}."
        )
    return " ".join(lines)


# ---------------------------------------------------------------------------
# 2. Stability
# ---------------------------------------------------------------------------


def _stability(
    cohorts: Sequence[CandidateCohort],
    production: Sequence[str],
    labels: dict[str, str],
) -> dict[str, Any]:
    """Leave-one-evidence-item-out, using the production score, gate and order."""
    if not production:
        return {
            "verdict": UNDETERMINED,
            "reason": "no recommendation exists to test",
            "evaluated": 0,
            "scenarios": [],
            "flips": [],
            "skipped": [],
            "rule": _stability_rule(),
        }

    by_id = {c.cohort_id: c for c in cohorts}
    contention = [by_id[cid] for cid in production if cid in by_id]
    scenarios: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for cohort in contention:
        scored_members = [m for m in cohort.members if m.affinity is not None]
        for member in scored_members:
            remaining = [m for m in cohort.members if m.entity_id != member.entity_id]
            if not remaining:
                skipped.append(
                    {
                        "cohort_id": cohort.cohort_id,
                        "entity_id": member.entity_id,
                        "name": member.name,
                        "reason": "the cohort would have no scored members left",
                    }
                )
                continue

            score = cohort_score_from(
                remaining,
                context_id=cohort.context_id or "",
                call_id=cohort.score.call_id if cohort.score else "",
                unscored=cohort.unscored_member_ids,
            )
            verdict = evidence.evaluate_cohort([m.scored for m in remaining])

            clone = _clone(cohort)
            clone.members = remaining
            clone.member_ids = [m.entity_id for m in remaining] + list(cohort.unscored_member_ids)
            clone.score = score
            clone.verdict = verdict
            clone.rejected = not verdict.sufficient
            clone.rejection = None if verdict.sufficient else cohort.rejection

            others = [_clone(other) for other in cohorts if other.cohort_id != cohort.cohort_id]
            ranked_ids, _ = _order_clones([*others, clone])

            scenarios.append(
                {
                    "removed": _member_view(member),
                    "removed_from": {
                        "cohort_id": cohort.cohort_id,
                        "label": labels.get(cohort.cohort_id, cohort.cohort_id),
                        "call_id": member.call_id,
                    },
                    "cohort_still_admitted": not clone.rejected,
                    "winner_after": ranked_ids[0] if ranked_ids else None,
                    "winner_changed": (ranked_ids[0] if ranked_ids else None) != production[0],
                    "order_after": ranked_ids,
                }
            )

    evaluated = len(scenarios)
    flips = [s for s in scenarios if s["winner_changed"]]

    if evaluated == 0:
        verdict, reason = UNDETERMINED, (
            "no ranked cohort had a removable scored member, so nothing could be re-scored"
        )
    elif flips:
        verdict, reason = FRAGILE, (
            f"{len(flips)} of {evaluated} single-item removals change the recommendation"
        )
    elif evaluated < MIN_SCENARIOS_FOR_STABLE:
        verdict, reason = UNDETERMINED, (
            f"only {evaluated} removal could be evaluated; at least {MIN_SCENARIOS_FOR_STABLE} "
            "are required before calling a decision stable"
        )
    else:
        verdict, reason = STABLE, (
            f"the recommendation survives all {evaluated} single-item removals that could be "
            "evaluated"
        )

    return {
        "verdict": verdict,
        "reason": reason,
        "rule": _stability_rule(),
        "evaluated": evaluated,
        "skipped": skipped,
        "flips": [
            {
                "removed": flip["removed"],
                "removed_from": flip["removed_from"],
                "winner_after": flip["winner_after"],
            }
            for flip in flips
        ],
        "scenarios": scenarios,
        "member_scope": (
            "Each scored member of each ranked cohort, removed one at a time. Removing a "
            "programme film (a comparable) changes the Qloo query itself and is listed under "
            "next checks instead of being simulated."
        ),
    }


def _stability_rule() -> str:
    return (
        "Fragile if any single removable evidence item changes the winning cohort. Stable only "
        f"if at least {MIN_SCENARIOS_FOR_STABLE} removals were evaluated and none changed it. "
        "Undetermined otherwise."
    )


# ---------------------------------------------------------------------------
# 3. Next checks (evidence-gap analysis)
# ---------------------------------------------------------------------------


def _gap(
    gap_id: str,
    title: str,
    detail: str,
    *,
    uncertainty_addressed: str,
    action: str,
    operation: str = "",
    estimated_calls: int = 0,
    call_ids: Sequence[str] = (),
    available: bool = True,
    unavailable_reason: str = "",
) -> dict[str, Any]:
    return {
        "id": gap_id,
        "title": title,
        "detail": detail,
        "uncertainty_addressed": uncertainty_addressed,
        "proposed_check": {
            "action": action,
            "operation": operation,
            "estimated_qloo_calls": estimated_calls,
            "available_now": available,
            "unavailable_reason": unavailable_reason,
        },
        "evidence_call_ids": list(call_ids),
    }


def _next_checks(
    state: AdjacentState,
    cohorts: Sequence[CandidateCohort],
    production: Sequence[str],
    necessity: dict[str, Any],
    stability: dict[str, Any],
) -> list[dict[str, Any]]:
    """Deterministic, evidence-cited investigation suggestions."""
    checks: list[dict[str, Any]] = []
    by_id = {c.cohort_id: c for c in cohorts}
    ranked = [by_id[cid] for cid in production if cid in by_id]
    ranking = getattr(state, "ranking", None)

    # A. No recommendation at all.
    if not ranked:
        rejected = list(getattr(state, "rejected", []))
        codes: dict[str, int] = {}
        for cohort in rejected:
            code = None
            if getattr(cohort, "rejection", None) is not None:
                code = str(getattr(cohort.rejection, "code", "") or "")
            codes[code or "unknown"] = codes.get(code or "unknown", 0) + 1
        summary = ", ".join(f"{code} ×{count}" for code, count in sorted(codes.items())) or "none"
        checks.append(
            _gap(
                "no_admitted_cohort",
                "Nothing cleared the evidence gate",
                f"{len(rejected)} candidate cohort(s) were rejected ({summary}). No recommendation "
                "was substituted.",
                uncertainty_addressed=(
                    "whether the candidate pool is too thin or the programme's taste is too "
                    "heterogeneous to support an adjacent-audience claim"
                ),
                action=(
                    "Add one or two more programme titles closest to the domain you expected "
                    "Qloo to surface, then re-run. If every cohort was rejected for "
                    "'insufficient_members', the expansion domains are the constraint instead."
                ),
                operation="expand_candidates / rank_cohorts",
                estimated_calls=2,
            )
        )

    # B. Members Qloo did not return a score for.
    unscored = list(getattr(ranking, "unscored_member_ids", []) or [])
    if unscored:
        checks.append(
            _gap(
                "unscored_members",
                f"{len(unscored)} candidate(s) came back without a score",
                "A candidate that was discovered but not scored cannot support or weaken the "
                "recommendation, and its absence silently shrinks the cohort it belonged to.",
                uncertainty_addressed="whether the ranking is missing an entity that would have changed it",
                action=(
                    "Re-score exactly those entity ids with filter.results.entities on the same "
                    "entity type, then re-run the ranking."
                ),
                operation="rank_cohorts (/v2/insights with filter.results.entities)",
                estimated_calls=max(1, len({c.domain for c in cohorts})),
                call_ids=[c.score.call_id for c in ranked if c.score][:3],
            )
        )

    # C. Per-seed attribution missing (this is what makes "which comparable
    #    supported this" answerable at all).
    attribution_status: dict[str, int] = {}
    for cohort in ranked:
        for member in cohort.members:
            status = member.qloo_attribution_status
            attribution_status[status] = attribution_status.get(status, 0) + 1
    missing_attribution = sum(
        count
        for status, count in attribution_status.items()
        if status in {"missing", "unsupported", "not_requested_limit", "not_requested_budget"}
    )
    if missing_attribution:
        limited = attribution_status.get("not_requested_limit", 0)
        unsupported = attribution_status.get("unsupported", 0)
        why = (
            "the request asked for per-seed attribution but the provider returned none"
            if attribution_status.get("missing")
            else "the optional feature.explainability field was rejected by the provider"
            if unsupported
            else f"{limited} member(s) were scored in a call that asked for more than 12 entities, "
            "so attribution was not requested"
        )
        checks.append(
            _gap(
                "attribution_unavailable",
                "Per-comparable attribution is missing for this run",
                f"{missing_attribution} ranked member(s) have no per-seed attribution: {why}. "
                "Without it, Adjacent can say which cohort won but not which of your films carried it.",
                uncertainty_addressed=(
                    "which programme title is actually responsible for the recommendation, and "
                    "therefore which title to vary first"
                ),
                action=(
                    "Re-score the winning domain with feature.explainability=true on at most 12 "
                    "entities, which is the documented limit for that optional field."
                ),
                operation="rank_cohorts (/v2/insights with feature.explainability)",
                estimated_calls=1,
                call_ids=[c.score.call_id for c in ranked if c.score][:3],
            )
        )

    # D. Thin winner.
    if ranked:
        winner = ranked[0]
        qualifying = len(winner.qualifying_members)
        if qualifying <= evidence.MIN_COHORT_MEMBERS:
            checks.append(
                _gap(
                    "thin_winner",
                    "The recommendation rests on the minimum evidence it needs",
                    f"The winning cohort has {qualifying} member(s) at or above the Medium band "
                    f"({BAND_MEDIUM}); the gate requires {evidence.MIN_COHORT_MEMBERS}. Losing any "
                    "one of them changes the arithmetic.",
                    uncertainty_addressed="whether the winning grouping is real or an artefact of two adjacent entities",
                    action=(
                        "Add one comparable title close to this cohort's world and re-run; a cohort "
                        "that survives a fourth candidate is a stronger basis for a screening."
                    ),
                    operation="expand_candidates / rank_cohorts",
                    estimated_calls=2,
                    call_ids=[winner.score.call_id] if winner.score else [],
                )
            )

    # E. Marginal runner-up.
    if len(ranked) >= 2:
        winner, runner_up = ranked[0], ranked[1]
        winner_novelty = _score_field(winner, "novelty_proxy")
        runner_novelty = _score_field(runner_up, "novelty_proxy")
        same_band = _strength(winner) == _strength(runner_up)
        close = (
            winner_novelty is not None
            and runner_novelty is not None
            and abs(winner_novelty - runner_novelty) <= MARGINAL_NOVELTY_DELTA
        )
        if same_band and close:
            checks.append(
                _gap(
                    "marginal_runner_up",
                    "The runner-up is within noise of the winner",
                    f"Both cohorts are '{winner.verdict.reason_code if winner.verdict else 'unknown'}' "
                    f"strength and their novelty proxies differ by "
                    f"{abs((winner_novelty or 0) - (runner_novelty or 0)):.3f}. A small change in "
                    "the evidence could reorder them.",
                    uncertainty_addressed="whether the top two recommendations are distinguishable from this evidence",
                    action=(
                        "Treat the top two as one option when planning, or add a comparable that "
                        "separates them. A pairwise comparison between the two cohorts is not "
                        "offered: the analysis/compare endpoint is declared in this repository's "
                        "parameter registry but has no verified client implementation."
                    ),
                    operation="expand_candidates / rank_cohorts",
                    estimated_calls=2,
                    call_ids=[winner.score.call_id] if winner.score else [],
                    available=True,
                )
            )

    # F. Fragile decision — name the exact item that flipped it.
    if stability.get("verdict") == FRAGILE and stability.get("flips"):
        first = stability["flips"][0]
        removed = first.get("removed") or {}
        checks.append(
            _gap(
                "fragile_decision",
                "One evidence item is holding the recommendation up",
                f"Removing {removed.get('name') or removed.get('entity_id')} from "
                f"{first.get('removed_from', {}).get('label', 'the winning cohort')} changes the "
                f"winner to {first.get('winner_after') or 'a different cohort'}.",
                uncertainty_addressed=(
                    "whether the recommendation is a property of the programme or of a single "
                    "adjacent entity"
                ),
                action=(
                    "Check that entity's fit with the venue before screening, or add a comparable "
                    "that supports the same world independently of it."
                ),
                operation="rank_cohorts",
                estimated_calls=1,
                call_ids=[first.get("removed_from", {}).get("call_id") or ""],
            )
        )

    # G. Necessity findings, in two directions.
    if ranked and necessity["affinity_withheld"]["winner_changed"]:
        checks.append(
            _gap(
                "affinity_decisive",
                "The recommendation depends on the affinity signal alone",
                "Without the affinity numbers the winner changes and no other retrieved signal "
                "reproduces it.",
                uncertainty_addressed="whether the recommendation would survive a different, non-taste baseline",
                action=(
                    "Record this as the specific claim under test in the Test Card and state, "
                    "before the screening, which evidence would falsify it."
                ),
                estimated_calls=0,
            )
        )
    elif ranked and not necessity["affinity_decided_pairs"]:
        checks.append(
            _gap(
                "order_is_popularity_driven",
                "The order is decided by novelty, not by affinity margins",
                "Affinity separated none of the adjacent pairs in this list. It still decided "
                "which cohorts were admitted, but among the admitted cohorts the ranking follows "
                "popularity novelty. A reader could reasonably ask what the affinity numbers "
                "added beyond admission.",
                uncertainty_addressed=(
                    "whether the taste signal is doing more than filtering — i.e. whether the "
                    "recommendation would survive a different taste input"
                ),
                action=(
                    "Run the same programme with one comparable changed and compare the two "
                    "recommendations. That is the only way to test the taste claim itself; this "
                    "run cannot answer it, and Adjacent does not simulate it."
                ),
                operation="resolve_programme / expand_candidates / rank_cohorts (new run)",
                estimated_calls=4,
            )
        )

    return checks


# ---------------------------------------------------------------------------
# 4. Decision receipt
# ---------------------------------------------------------------------------


def build_receipt(
    state: AdjacentState,
    challenge: dict[str, Any],
) -> dict[str, Any]:
    """A compact, inspectable summary of what was recommended and how sure we are."""
    cohorts = list(getattr(state, "ranked", []) or [])
    winner = cohorts[0] if cohorts else None
    recommendation: dict[str, Any] = {}
    if winner is not None:
        recommendation = {
            "cohort_id": winner.cohort_id,
            "domain": winner.domain,
            "kind": winner.kind,
            "label": f"{winner.domain.replace('urn:entity:', '')} · {winner.kind}",
            "member_names": [m.name for m in winner.members if m.name][:6],
            "mean_affinity": _score_field(winner, "mean_affinity"),
            "novelty_proxy": _score_field(winner, "novelty_proxy"),
            "strength": winner.verdict.reason_code if winner.verdict else None,
            "call_id": winner.score.call_id if winner.score else None,
            "construction_reason": winner.construction_reason,
        }

    necessity = challenge.get("necessity") or {}
    stability = challenge.get("stability") or {}
    withheld = necessity.get("affinity_withheld") or {}
    popularity = necessity.get("popularity_only") or {}

    call_ids: list[str] = []
    for cid in (recommendation.get("call_id"),):
        if cid:
            call_ids.append(cid)

    return {
        "schema": SCHEMA,
        "run_id": getattr(state, "run_id", ""),
        "data_status": getattr(state, "data_status", "unknown"),
        "recommendation": recommendation,
        "basis": {
            "ordering_keys": list(ORDER_KEYS),
            "affinity_decided_pairs": len(necessity.get("affinity_decided_pairs") or []),
            "adjacent_pairs_examined": necessity.get("adjacent_pairs_examined", 0),
        },
        "necessity": {
            "winner_without_affinity": withheld.get("counterfactual_winner"),
            "affinity_changed_winner": withheld.get("winner_changed"),
            "ranks_moved_without_affinity": withheld.get("ranks_moved", 0),
            "popularity_only_winner": popularity.get("counterfactual_winner"),
            "popularity_would_differ": popularity.get("winner_changed"),
        },
        "stability": {
            "verdict": stability.get("verdict", UNDETERMINED),
            "reason": stability.get("reason", ""),
            "evaluated": stability.get("evaluated", 0),
            "flips": len(stability.get("flips") or []),
        },
        "next_checks": [
            {"id": check["id"], "title": check["title"]}
            for check in (challenge.get("next_checks") or [])
        ],
        "limits": list(PUBLIC_LIMITS),
        "call_ids": sorted({cid for cid in call_ids if cid}),
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_decision_challenge(state: AdjacentState) -> dict[str, Any]:
    """Assemble the whole challenge from a finished run. Pure and deterministic."""
    ranked = list(getattr(state, "ranked", []) or [])
    rejected = list(getattr(state, "rejected", []) or [])
    cohorts = [*ranked, *rejected]
    production = [c.cohort_id for c in ranked]

    base: dict[str, Any] = {
        "schema": SCHEMA,
        "data_status": getattr(state, "data_status", "unknown"),
        "limits": list(PUBLIC_LIMITS),
    }

    if not cohorts:
        return {
            **base,
            "available": False,
            "unavailable_reason": (
                "This run produced no candidate cohorts, so there is no recommendation to "
                "challenge. Nothing has been inferred in place of the missing evidence."
            ),
            "necessity": None,
            "stability": None,
            "next_checks": [],
            "receipt": None,
        }

    labels = cohort_labels(cohorts)
    necessity = _necessity(cohorts, production, labels)
    stability = _stability(cohorts, production, labels)
    checks = _next_checks(state, cohorts, production, necessity, stability)

    challenge: dict[str, Any] = {
        **base,
        "available": True,
        "unavailable_reason": None,
        "recommendation": {
            "cohort_id": production[0] if production else None,
            "label": labels.get(production[0], "") if production else "",
        },
        "necessity": necessity,
        "necessity_statement": _necessity_statement(necessity, labels),
        "stability": stability,
        "next_checks": checks,
        "counts": {
            "cohorts_ranked": len(ranked),
            "cohorts_rejected": len(rejected),
            "evidence_items_tested": stability.get("evaluated", 0),
            "qloo_calls_made": 0,
        },
    }
    challenge["receipt"] = build_receipt(state, challenge)
    return challenge
