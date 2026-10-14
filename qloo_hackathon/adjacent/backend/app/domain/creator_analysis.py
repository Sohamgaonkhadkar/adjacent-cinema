"""Creator Mode analysis layer (M13.9).

Turns the SAME evidence pipeline used by Cinema Mode (resolved entities →
Qloo taste tags → ranked cohorts → optional geography) into creator-facing
decision artefacts:

* a **Positioning Bet** — the creator analogue of the Programme Bet, reusing
  the `ProgrammeBet` dataclass and contract so provenance, two-sided signals
  and fixture/measured labelling behave identically;
* a **Creator Test Card** — reusing the `TestCard` dataclass so the existing
  success-criteria / observation-window / falsification contract applies.

Non-negotiables inherited from the cinema pipeline:
* affinity is cultural similarity, never predicted views, retention,
  attendance or revenue;
* `data_status` mirrors the run's real source ("measured" for live Qloo,
  "fixture" for the labelled demo);
* missing evidence is stated as missing, never converted into signal.
"""

from __future__ import annotations

from typing import Any

from .programme_bet import ProgrammeBet
from .test_card import TestCard


def two_sided_signal_maps(state: Any) -> dict[str, dict[str, Any]]:
    """Compute the two-sided evidence maps from ranked cohorts.

    Mirrors the cinema path in routes._post_pipeline_artifacts:
    A. programme adjacency — mean affinity (cultural proximity)
    B. cohort breadth — qualifying/total ratio (coverage)
    """
    adjacency_scores: dict[str, float] = {}
    breadth_scores: dict[str, float] = {}
    adjacency_bands: dict[str, str] = {}
    breadth_bands: dict[str, str] = {}
    adjacency_calls: dict[str, str] = {}
    breadth_calls: dict[str, str] = {}

    for cohort in getattr(state, "ranked", []) or []:
        cid = cohort.cohort_id
        score = cohort.score
        if score and score.mean_affinity is not None:
            adjacency_scores[cid] = score.mean_affinity
            adjacency_bands[cid] = (
                "High" if score.mean_affinity >= 0.6
                else "Medium" if score.mean_affinity >= 0.5
                else "Low"
            )
            adjacency_calls[cid] = score.call_id or ""
        total = len(cohort.members) if cohort.members else 0
        qualifying = len(cohort.qualifying_members) if cohort.members else 0
        if total > 0:
            ratio = qualifying / total
            breadth_scores[cid] = ratio
            breadth_bands[cid] = "High" if ratio >= 0.5 else "Medium" if ratio >= 0.3 else "Low"
            breadth_calls[cid] = score.call_id if score and score.call_id else ""

    return {
        "adjacency_scores": adjacency_scores,
        "breadth_scores": breadth_scores,
        "adjacency_bands": adjacency_bands,
        "breadth_bands": breadth_bands,
        "adjacency_calls": adjacency_calls,
        "breadth_calls": breadth_calls,
    }


def build_positioning_bet(
    ranked_cohorts: list[Any],
    taste_tags: list[Any],
    film_title: str,
    seeds: list[str],
    signals: dict[str, dict[str, Any]],
    geography: Any = None,
    *,
    rejected_cohorts: list[Any] | None = None,
    data_status: str = "measured",
) -> ProgrammeBet | None:
    """Build the creator Positioning Bet from the same ranked-cohort evidence.

    Returns None when there are no ranked cohorts — an absent bet is the honest
    output, never a fabricated one.
    """
    if not ranked_cohorts:
        return None

    primary = ranked_cohorts[0]
    runner_up = ranked_cohorts[1] if len(ranked_cohorts) > 1 else None

    primary_domain = primary.domain.replace("urn:entity:", "")
    primary_members = primary.members or []
    primary_names = [m.name for m in primary_members[:5] if m.name]
    primary_affinity = primary.score.mean_affinity if primary.score else 0.0
    primary_call_id = primary.score.call_id if primary.score else None
    primary_cohort_id = getattr(primary, "cohort_id", None)

    ru_domain = None
    ru_names: list[str] = []
    ru_affinity = None
    ru_call_id = None
    if runner_up:
        ru_domain = runner_up.domain.replace("urn:entity:", "")
        ru_names = [m.name for m in (runner_up.members or [])[:3] if m.name]
        ru_affinity = runner_up.score.mean_affinity if runner_up.score else None
        ru_call_id = runner_up.score.call_id if runner_up.score else None

    adjacency_score = signals["adjacency_scores"].get(primary_cohort_id or "")
    breadth_score = signals["breadth_scores"].get(primary_cohort_id or "")
    adjacency_band = signals["adjacency_bands"].get(primary_cohort_id or "")
    breadth_band = signals["breadth_bands"].get(primary_cohort_id or "")
    adjacency_call = signals["adjacency_calls"].get(primary_cohort_id or "")
    breadth_call = signals["breadth_calls"].get(primary_cohort_id or "")

    top_tags = [t.name for t in taste_tags[:5] if t.name] if taste_tags else []
    tag_summary = ", ".join(top_tags[:3]) if top_tags else "your film's expressed themes"

    # WHY — evidence-first, creator framing.
    why_parts = []
    if primary_names:
        why_parts.append(
            f"Your references and themes ({', '.join(seeds[:3]) if seeds else 'your inputs'}) "
            f"sit closest to a cultural world around {', '.join(primary_names[:3])} "
            f"in the {primary_domain} domain."
        )
    if primary_affinity:
        why_parts.append(
            f"Measured cultural affinity with that world is "
            f"{'strong' if primary_affinity > 0.6 else 'moderate'} "
            f"(mean {primary_affinity:.2f} on Qloo's 0–1 similarity scale — "
            f"not a view or revenue forecast)."
        )
    if adjacency_score is not None and breadth_score is not None:
        why_parts.append(
            f"Evidence dimensions: cultural adjacency={adjacency_score:.2f} "
            f"({adjacency_band or '?'}), world breadth={breadth_score:.2f} "
            f"({breadth_band or '?'})."
        )
    why = " ".join(why_parts) or "Evidence supports a cultural-adjacency positioning hypothesis."

    cultural_bridge = (
        f"Your film's expressed profile ({tag_summary}) shares measured cultural "
        f"signals with {', '.join(primary_names[:2])}."
        if primary_names
        else "Cultural signals connect your film to an adjacent audience world."
    )

    if geography and getattr(geography, "sufficient", False):
        geo_signal = (
            f"Affinity concentrates around {geography.city_display or geography.city} "
            f"({geography.total_cells} heatmap cells) — relevant for location-based "
            f"community outreach, not a demand forecast."
        )
        geo_call_id = geography.call_id
    elif geography is not None:
        geo_signal = "Geographic signal too sparse to use — treat as unavailable."
        geo_call_id = None
    else:
        geo_signal = (
            "No geographic analysis: creator runs use geography only when a "
            "release location is supplied."
        )
        geo_call_id = None

    programming_direction = (
        f"Position '{film_title}' toward the {primary_domain} world "
        + (f"(e.g. {', '.join(primary_names[:2])}) " if primary_names else "")
        + "in your title framing, description and community outreach, and test "
        "that framing against your usual wording."
    )

    falsification = (
        f"Reject this positioning hypothesis if, after the release, your own "
        f"observations do not show the {primary_domain} framing connecting — "
        f"and if a re-run of this analysis on your next work does not reproduce "
        f"a {primary_domain} cohort in the top-3 ranked cultural worlds."
    )

    rejected = []
    for cohort in (rejected_cohorts or []):
        rejection = getattr(cohort, "rejection", None)
        rejected.append({
            "cohort_id": getattr(cohort, "cohort_id", "?"),
            "domain": getattr(cohort, "domain", "?"),
            "reason": rejection.code.value if rejection and hasattr(rejection, "code") else "unknown",
            "detail": rejection.detail if rejection and hasattr(rejection, "detail") else "",
        })

    return ProgrammeBet(
        primary_domain=primary_domain,
        primary_cohort_name=primary_names[0] if primary_names else primary_domain,
        primary_mean_affinity=primary_affinity,
        primary_member_count=len(primary_members),
        primary_cohort_id=primary_cohort_id,
        runner_up_domain=ru_domain,
        runner_up_cohort_name=ru_names[0] if ru_names else ru_domain,
        runner_up_mean_affinity=ru_affinity,
        programme_adjacency=adjacency_score,
        adjacency_band=adjacency_band,
        adjacency_call_id=adjacency_call,
        cohort_breadth=breadth_score,
        breadth_band=breadth_band,
        breadth_call_id=breadth_call,
        why=why,
        cultural_bridge=cultural_bridge,
        geographic_signal=geo_signal,
        programming_direction=programming_direction,
        falsification_condition=falsification,
        rejected_candidates=rejected,
        primary_call_id=primary_call_id,
        runner_up_call_id=ru_call_id,
        geography_call_id=geo_call_id,
        data_status=data_status,
    )


def build_creator_test_card(
    bet: ProgrammeBet,
    film_title: str,
    seeds: list[str],
    release_goal: str,
) -> TestCard:
    """Build the creator Test Card from a Positioning Bet (same dataclass).

    Success criteria are observations the creator can actually make — never
    predicted views, retention or revenue.
    """
    title = f"Test: {bet.primary_domain.title()}-world positioning for '{film_title}'"

    programme_context = (
        f"Analysis seeds: {', '.join(seeds[:5])}"
        + (f" and {len(seeds) - 5} more" if len(seeds) > 5 else "")
        + (f" · release goal: {release_goal}" if release_goal else "")
        + "."
    )

    others = bet.primary_member_count - 1
    represented_by = (
        f"{bet.primary_cohort_name} and {others} similar entit{'y' if others == 1 else 'ies'}"
        if others > 0
        else f"{bet.primary_cohort_name} (the single qualifying entity found)"
    )
    audience_hypothesis = (
        f"An audience aligned with the {bet.primary_domain} cultural world — "
        f"represented by {represented_by}, mean affinity "
        f"{bet.primary_mean_affinity:.2f} — is reachable with positioning that "
        f"names that world, more than with your current default framing."
    )

    runner_up = "No runner-up world identified."
    if bet.runner_up_domain and bet.runner_up_cohort_name:
        runner_up = (
            f"Runner-up: {bet.runner_up_cohort_name} in the {bet.runner_up_domain} world"
            + (f" (affinity {bet.runner_up_mean_affinity:.2f})" if bet.runner_up_mean_affinity else "")
            + "."
        )

    success_criteria = (
        f"The test succeeds if your own post-release records show: (1) responses, "
        f"comments or shares that reference the {bet.primary_domain} framing you "
        f"tested, and (2) the framing's reach compared against your own recent "
        f"baseline for comparable releases. Adjacent predicts no view counts, "
        f"retention or revenue — judge by what you observe."
    )

    observation_window = (
        "Observe for the first two weeks after release (most short-film attention "
        "arrives in the first days), then record what you saw. Re-run this "
        "analysis on your next work within one comparable cycle to confirm or "
        "falsify the adjacency."
    )

    provenance: dict[str, Any] = {
        "primary_call_id": bet.primary_call_id,
        "runner_up_call_id": bet.runner_up_call_id,
        "geography_call_id": bet.geography_call_id,
        "primary_cohort_id": bet.primary_cohort_id,
        "data_status": bet.data_status,
    }

    return TestCard(
        title=title,
        programme_context=programme_context,
        audience_hypothesis=audience_hypothesis,
        cultural_bridge=bet.cultural_bridge,
        geographic_signal=bet.geographic_signal,
        programming_direction=bet.programming_direction,
        primary_evidence=bet.why,
        runner_up=runner_up,
        falsification_condition=bet.falsification_condition,
        success_criteria=success_criteria,
        observation_window=observation_window,
        provenance=provenance,
        data_status=bet.data_status,
    )
