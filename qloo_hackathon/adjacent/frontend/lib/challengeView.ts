/**
 * View model for the Decision Challenge.
 *
 * The backend already decided what is true about this run; this module only
 * decides how to say it. It is deliberately pure and dependency-free so it can
 * be unit-tested under Node without a browser, and so no component can invent a
 * claim the payload does not contain.
 *
 * Two rules are enforced here rather than in the components:
 *   1. A missing or unavailable payload never renders as a reassuring default.
 *      It always produces an explicit "not calculated" state.
 *   2. No derived text may state or imply a probability, confidence interval,
 *      attendance estimate or success rate. Stability is a rule outcome.
 */

import type {
  DecisionChallengeData,
  DecisionReceipt,
  NextCheck,
  PairwiseComparison,
  StabilityScenario,
} from "@/types/adjacent";

export type Tone = "live" | "fixture" | "warn" | "fail" | "neutral";

export interface ChallengeRow {
  id: string;
  label: string;
  detail: string;
  tone: Tone;
}

export interface ChallengeView {
  available: boolean;
  unavailableReason: string | null;
  dataStatus: string;
  statusTone: Tone;
  headline: string;
  statement: string | null;
  necessityRows: ChallengeRow[];
  stabilityVerdict: string;
  stabilityTone: Tone;
  stabilityReason: string;
  stabilityRule: string;
  stabilityRows: ChallengeRow[];
  skipped: { id: string; text: string }[];
  /** The winner-vs-same-type comparison, or an explicit reason there is none. */
  pairwise: { tone: Tone; label: string; detail: string; callId: string | null } | null;
  checks: NextCheck[];
  receipt: DecisionReceipt | null;
  limits: string[];
  counts: { label: string; value: string }[];
}

const NEUTRAL_ROW = (id: string, label: string, detail: string): ChallengeRow => ({
  id,
  label,
  detail,
  tone: "neutral",
});

export function toneForStatus(status: string | null | undefined): Tone {
  if (status === "measured" || status === "live") return "live";
  if (status === "fixture" || status === "demo") return "fixture";
  if (status === "unavailable" || status === "insufficient") return "warn";
  if (status === "failed" || status === "error") return "fail";
  return "neutral";
}

export function toneForVerdict(verdict: string | null | undefined): Tone {
  if (verdict === "stable") return "live";
  if (verdict === "fragile") return "warn";
  return "neutral";
}

/** "no other position moves" / "1 other position moves" / "2 other positions move". */
function movedPositions(count: number): string {
  if (!count) return "no other position moves";
  return count === 1 ? "1 other position moves" : `${count} other positions move`;
}

/** A reader-facing name for a cohort, or an honest placeholder — never a raw urn. */
export const UNLABELLED = "an unlabelled grouping";

function labelFor(
  order: { cohort_id: string; label: string }[] | undefined,
  id: string | null | undefined,
): string {
  if (!id) return "nothing";
  const entry = (order ?? []).find((item) => item.cohort_id === id);
  return entry?.label || UNLABELLED;
}

function scenarioRow(
  scenario: StabilityScenario,
  nameOf: (id: string | null | undefined) => string,
): ChallengeRow {
  const name = scenario.removed.name ?? scenario.removed.entity_id;
  const affinity =
    typeof scenario.removed.affinity === "number" ? scenario.removed.affinity.toFixed(2) : "no score";
  return {
    id: `${scenario.removed_from.cohort_id}:${scenario.removed.entity_id}`,
    label: `Without ${name}`,
    detail: scenario.winner_changed
      ? `Removing ${name} moves the recommendation to ${nameOf(scenario.winner_after)}. ` +
        `This ${scenario.removed.band} item (affinity ${affinity}) in ${scenario.removed_from.label} is load-bearing.`
      : `Removing ${name} leaves the recommendation unchanged` +
        `${scenario.cohort_still_admitted ? "" : ", even though its own cohort drops below the evidence gate"}. ` +
        `This ${scenario.removed.band} item (affinity ${affinity}) is not load-bearing.`,
    tone: scenario.winner_changed ? "warn" : "neutral",
  };
}

/**
 * Turn one comparison payload into a row, or `null` when no comparison was
 * attempted. A refusal keeps its own wording: the reader is told why the number
 * is missing instead of being shown a reassuring blank.
 */
export function pairwiseRow(
  comparison: PairwiseComparison | null | undefined,
): { tone: Tone; label: string; detail: string; callId: string | null } | null {
  if (!comparison) return null;

  const a = comparison.cohorts?.a?.label || "the top cohort";
  const b = comparison.cohorts?.b?.label || "the comparison cohort";
  const metric = comparison.metric;
  const callId = comparison.call_id ?? null;

  if (comparison.available && metric && typeof metric.value === "number") {
    const direction =
      metric.direction === "higher_is_closer"
        ? "higher means the two groups overlap more"
        : metric.direction === "lower_is_closer"
          ? "lower means the two groups overlap more"
          : "this build does not interpret the direction of that field";
    return {
      tone: "live",
      label: `${a} vs ${b}`,
      detail:
        `Qloo reported ${metric.key} = ${metric.value.toFixed(3)} between ${a} and ${b} ` +
        `(${direction}). It describes the two groups you supplied; it is not a forecast of ` +
        `attendance, revenue or campaign performance.`,
      callId,
    };
  }

  return {
    tone: comparison.status === "failed" ? "fail" : "neutral",
    label: `No comparison value for ${a} vs ${b}`,
    detail:
      comparison.reason ||
      "The comparison returned no value this build is willing to interpret.",
    callId,
  };
}

/**
 * Build the view. `challenge` may be null (older runs, or a payload that failed
 * to compute) — that is a state the reader has to see, not one to paper over.
 */
export function buildChallengeView(
  challenge: DecisionChallengeData | null | undefined,
): ChallengeView {
  if (!challenge) {
    return {
      available: false,
      unavailableReason:
        "This run has no decision challenge attached. Nothing is inferred in its place — re-run the analysis to compute one.",
      dataStatus: "unknown",
      statusTone: "neutral",
      headline: "Not calculated",
      statement: null,
      necessityRows: [],
      stabilityVerdict: "undetermined",
      stabilityTone: "neutral",
      stabilityReason: "No challenge was computed for this run.",
      stabilityRule: "",
      stabilityRows: [],
      skipped: [],
      pairwise: null,
      checks: [],
      receipt: null,
      limits: [],
      counts: [],
    };
  }

  const statusTone = toneForStatus(challenge.data_status);
  const necessity = challenge.necessity;
  const stability = challenge.stability;

  const necessityRows: ChallengeRow[] = [];
  if (!necessity) {
    necessityRows.push(
      NEUTRAL_ROW("necessity-missing", "Not calculated", "No necessity analysis was produced for this run."),
    );
  } else {
    const withheld = necessity.affinity_withheld;
    const popularity = necessity.popularity_only;

    if (withheld.top_pair_tied_without_affinity) {
      necessityRows.push({
        id: "tie",
        label: "The top two are indistinguishable without affinity",
        detail:
          "They match on evidence strength, novelty and breadth. Affinity is the only thing separating them, so treat the top two as one option rather than as a ranked first and second.",
        tone: "warn",
      });
    } else if (withheld.winner_changed) {
      necessityRows.push({
        id: "affinity-changed-winner",
        label: "Affinity decides the recommendation",
        detail: `Without the affinity numbers the recommendation changes to 
          ${labelFor(withheld.order, withheld.counterfactual_winner)}. That makes the recommendation 
          dependent on this one signal — a reason to test it, not a reason to trust it more.`,
        tone: "warn",
      });
    } else {
      necessityRows.push({
        id: "affinity-order",
        label:
          withheld.ranks_moved === 0
            ? "Affinity does not reorder this list"
            : `Affinity moves ${withheld.ranks_moved} position${withheld.ranks_moved === 1 ? "" : "s"}`,
        detail:
          withheld.ranks_moved === 0
            ? `Affinity separated ${necessity.affinity_decided_pairs.length} of ${necessity.adjacent_pairs_examined} adjacent pairs. Strength and novelty decided the order.`
            : `The winner is unchanged, but ${withheld.ranks_moved} position${withheld.ranks_moved === 1 ? "" : "s"} below it move when the affinity numbers are removed.`,
        tone: "neutral",
      });
    }

    necessityRows.push({
      id: "popularity-baseline",
      label: popularity.winner_changed
        ? "A mainstream baseline would recommend something else"
        : "A mainstream baseline would recommend the same cohort",
      detail: popularity.winner_changed
        ? `Ordering the same candidates by popularity alone picks ${labelFor(popularity.order, popularity.counterfactual_winner)}. The taste signal is what makes this recommendation different from the mainstream pick.`
        : "Ordering the same candidates by popularity alone produces the same cohort, so taste is not what distinguishes this recommendation.",
      tone: popularity.winner_changed ? "live" : "neutral",
    });

    const suppressed = necessity.gate.suppressed_by_affinity_gate;
    if (suppressed.length) {
      necessityRows.push({
        id: "suppressed",
        label: `${suppressed.length} grouping${suppressed.length === 1 ? "" : "s"} held back by the affinity threshold`,
        detail: `These had enough scored members to be shown but did not clear the affinity gate, so they never reached the list: ${suppressed
          .map((entry) => entry.label || UNLABELLED)
          .join(", ")}.`,
        tone: "neutral",
      });
    }
  }

  // Every labelled cohort the payload mentions, so a counterfactual winner can be
  // named even when it was not in the admitted pool.
  const labelsById: Record<string, string> = {};
  for (const entry of [
    ...(necessity?.affinity_withheld.order ?? []),
    ...(necessity?.popularity_only.order ?? []),
    ...(necessity?.gate.suppressed_by_affinity_gate ?? []),
  ]) {
    if (entry.label) labelsById[entry.cohort_id] = entry.label;
  }
  for (const flip of stability?.flips ?? []) {
    if (flip.winner_after && flip.winner_after_label) {
      labelsById[flip.winner_after] = flip.winner_after_label;
    }
  }
  const nameOf = (id: string | null | undefined) =>
    id ? (labelsById[id] || UNLABELLED) : "nothing";

  const flips = stability?.flips ?? [];
  const stabilityRows: ChallengeRow[] = [];
  if (stability) {
    // Flips first: the reader needs the bad news before the reassuring rows.
    stabilityRows.push(
      ...flips.map((flip) =>
        scenarioRow(
          {
            removed: flip.removed,
            removed_from: flip.removed_from,
            cohort_still_admitted: false,
            winner_after: flip.winner_after,
            winner_changed: true,
            order_after: [],
          },
          nameOf,
        ),
      ),
    );
    stabilityRows.push(
      ...(stability.scenarios ?? [])
        .filter((scenario) => !scenario.winner_changed)
        .slice(0, 6)
        .map((scenario) => scenarioRow(scenario, nameOf)),
    );
  }

  const counts: { label: string; value: string }[] = [];
  if (challenge.counts) {
    counts.push({ label: "Evidence items re-scored", value: String(challenge.counts.evidence_items_tested) });
    counts.push({ label: "Cohorts ranked", value: String(challenge.counts.cohorts_ranked) });
    counts.push({ label: "Cohorts rejected", value: String(challenge.counts.cohorts_rejected) });
    counts.push({ label: "Extra Qloo calls", value: String(challenge.counts.qloo_calls_made) });
  }

  const headline = !challenge.available
    ? "Not calculated"
    : (stability?.verdict ?? "undetermined") === "fragile"
      ? "Fragile recommendation"
      : (stability?.verdict ?? "undetermined") === "stable"
        ? "Stable under the stated rule"
        : "Stability undetermined";

  return {
    available: challenge.available,
    unavailableReason: challenge.unavailable_reason,
    dataStatus: challenge.data_status,
    statusTone,
    headline,
    statement: challenge.necessity_statement ?? null,
    necessityRows,
    stabilityVerdict: stability?.verdict ?? "undetermined",
    stabilityTone: toneForVerdict(stability?.verdict),
    stabilityReason: stability?.reason ?? "No stability analysis was produced for this run.",
    stabilityRule: stability?.rule ?? "",
    stabilityRows,
    skipped: (stability?.skipped ?? []).map((skip, index) => ({
      id: `${skip.cohort_id}:${skip.entity_id}:${index}`,
      text: `${skip.name ?? skip.entity_id} was not tested: ${skip.reason}.`,
    })),
    pairwise: pairwiseRow(challenge.pairwise),
    checks: challenge.next_checks ?? [],
    receipt: challenge.receipt,
    limits: challenge.limits ?? [],
    counts,
  };
}

/**
 * Plain-text decision receipt. It writes only what the payload holds, and it
 * always carries the limitations and the data status, so a downloaded receipt
 * cannot be mistaken for a live result when it is a fixture one.
 */
export function formatDecisionReceipt(challenge: DecisionChallengeData | null | undefined): string {
  const view = buildChallengeView(challenge);
  const receipt = view.receipt;
  const lines: string[] = [];
  const rule = "─".repeat(64);

  lines.push("DECISION RECEIPT");
  lines.push(rule);
  lines.push(`Data status: ${(view.dataStatus || "unknown").toUpperCase()}`);

  if (!receipt) {
    lines.push("");
    lines.push("No receipt is available for this run.");
    lines.push(view.unavailableReason ?? "The decision challenge was not computed.");
    return `${lines.join("\n")}\n`;
  }

  lines.push(`Run: ${receipt.run_id}`);
  lines.push(`Schema: ${receipt.schema}`);
  lines.push("");
  lines.push("RECOMMENDATION");
  const recommendation = receipt.recommendation as DecisionReceipt["recommendation"] & {
    label?: string;
    member_names?: string[];
    strength?: string | null;
    call_id?: string | null;
    mean_affinity?: number | null;
    novelty_proxy?: number | null;
  };
  if (recommendation?.label) {
    lines.push(`  ${recommendation.label}`);
    if (recommendation.member_names?.length) {
      lines.push(`  Supporting entities: ${recommendation.member_names.join(", ")}`);
    }
    if (recommendation.strength) lines.push(`  Evidence strength: ${recommendation.strength}`);
    if (typeof recommendation.mean_affinity === "number") {
      lines.push(`  Mean affinity: ${recommendation.mean_affinity.toFixed(3)} (within this scoring context only)`);
    }
    if (typeof recommendation.novelty_proxy === "number") {
      lines.push(`  Novelty proxy: ${recommendation.novelty_proxy.toFixed(3)} (1 − median popularity)`);
    }
    if (recommendation.call_id) lines.push(`  Qloo call: ${recommendation.call_id}`);
  } else {
    lines.push("  No cohort cleared the evidence gate. No recommendation is recorded.");
  }

  lines.push("");
  lines.push("NECESSITY");
  lines.push(
    `  Affinity removed → winner ${receipt.necessity.affinity_changed_winner ? "CHANGES" : "unchanged"}` +
      ` (${movedPositions(receipt.necessity.ranks_moved_without_affinity)})`,
  );
  lines.push(
    `  Popularity-only baseline → ${receipt.necessity.popularity_would_differ ? "DIFFERENT cohort" : "same cohort"}`,
  );
  lines.push(
    `  Affinity decided ${receipt.basis.affinity_decided_pairs} of ${receipt.basis.adjacent_pairs_examined} adjacent pairs`,
  );

  lines.push("");
  lines.push("STABILITY");
  lines.push(`  Verdict: ${receipt.stability.verdict.toUpperCase()} (${receipt.stability.evaluated} removals evaluated)`);
  lines.push(`  ${receipt.stability.reason}`);
  if (view.stabilityRule) lines.push(`  Rule: ${view.stabilityRule}`);

  // The receipt carries its own compact copy; older receipts do not, so the
  // challenge-level payload is the fallback rather than an omission.
  const comparison = challenge?.pairwise ?? receipt.pairwise ?? null;
  if (comparison) {
    lines.push("");
    lines.push("PAIRWISE COMPARISON");
    lines.push(`  Status: ${comparison.status}`);
    if (comparison.metric) {
      const metric = comparison.metric;
      lines.push(
        `  ${metric.key} = ${metric.value.toFixed(3)} (${metric.direction}); describes the two groups supplied, not an outcome.`,
      );
    }
    if (comparison.reason) lines.push(`  ${comparison.reason}`);
    if (comparison.call_id) lines.push(`  Qloo call: ${comparison.call_id}`);
  }

  if (receipt.attribution) {
    const origins = Object.entries(receipt.attribution.origins)
      .map(([origin, count]) => `${origin} ${count}`)
      .join(", ");
    lines.push("");
    lines.push("ATTRIBUTION");
    lines.push(`  Origins: ${origins || "none"}`);
    lines.push(`  Bounded follow-up: ${receipt.attribution.bounded_status}`);
    if (receipt.attribution.bounded_call_id) {
      lines.push(`  Qloo call: ${receipt.attribution.bounded_call_id}`);
    }
  }

  if (view.checks.length) {
    lines.push("");
    lines.push("NEXT CHECKS");
    for (const check of view.checks) {
      lines.push(`  - ${check.title}`);
      if (check.proposed_check.action) lines.push(`      ${check.proposed_check.action}`);
    }
  }

  if (receipt.call_ids.length) {
    lines.push("");
    lines.push(`QLOO CALL IDS: ${receipt.call_ids.join(", ")}`);
  }

  lines.push("");
  lines.push("LIMITATIONS");
  for (const limit of receipt.limits) lines.push(`  - ${limit}`);

  lines.push(rule);
  return `${lines.join("\n")}\n`;
}


/**
 * Sections appended to the exported Test Card so the experiment always carries
 * the fragility finding it was designed against. Empty when nothing was
 * computed — an export never implies a challenge exists when it does not.
 */
export function challengeExportSections(
  challenge: DecisionChallengeData | null | undefined,
): { label: string; value: string }[] {
  const view = buildChallengeView(challenge);
  if (!view.available || !view.receipt) return [];

  const sections = [
    {
      label: "Decision stability (not a probability)",
      value: `${view.stabilityVerdict.toUpperCase()} — ${view.stabilityReason}. Rule: ${view.stabilityRule}`,
    },
    {
      label: "Counterfactual: affinity withheld",
      value: view.receipt.necessity.affinity_changed_winner
        ? "The recommendation changes when Qloo's affinity numbers are removed."
        : `The recommendation holds without the affinity numbers (${movedPositions(view.receipt.necessity.ranks_moved_without_affinity)}). Affinity decided ${view.receipt.basis.affinity_decided_pairs} of ${view.receipt.basis.adjacent_pairs_examined} adjacent pairs.`,
    },
  ];
  if (view.receipt.necessity.popularity_would_differ) {
    sections.push({
      label: "Counterfactual: popularity-only baseline",
      value:
        "Ordering the same candidates by popularity alone selects a different cohort, so this decision is not the mainstream pick.",
    });
  }
  if (view.pairwise) {
    sections.push({
      label: "Pairwise comparison (not a forecast)",
      value: `${view.pairwise.label} — ${view.pairwise.detail}`,
    });
  }
  if (view.checks.length > 0) {
    sections.push({
      label: "Investigate before screening",
      value: `${view.checks[0].title} — ${view.checks[0].proposed_check.action}`,
    });
  }
  return sections;
}
