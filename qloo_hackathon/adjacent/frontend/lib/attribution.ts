/**
 * "Why this result?" — the bounded explainability disclosure.
 *
 * Provider attribution is a per-seed contribution weight Qloo returned for one
 * candidate entity. This module turns it into sentences that:
 *
 *   * name the reference film each seed id belongs to (never print a raw id),
 *   * say which call produced the attribution (the scoring call, or the one
 *     bounded follow-up for the winning cohort),
 *   * and, when there is nothing to show, say why — absence is not zero.
 *
 * It never computes a contribution, sums weights into a total, or implies that a
 * weight measures audience size, causality or revenue.
 */

import type { BoundedAttribution, CohortMember, ProgrammeFilm } from "@/types/adjacent";

export interface Contributor {
  entityName: string;
  origin: "scoring" | "bounded" | null;
  callId: string | null;
  seeds: { label: string; weight: number }[];
}

export interface WhyResult {
  available: boolean;
  contributors: Contributor[];
  headline: string;
  statement: string;
  note: string;
  limits: string[];
}

const UNRESOLVED_SEED = "a reference this run did not resolve to a title";

const BOUNDED_REASON: Record<string, string> = {
  missing: "Qloo returned no usable per-seed contribution for the winning cohort.",
  failed: "The optional attribution call did not complete, so no attribution is shown.",
  unavailable_budget: "The run's call budget did not allow the optional attribution call.",
  not_needed: "This run did not attempt the follow-up attribution call.",
  returned: "Provider attribution is attached to this cohort.",
};

export function seedTitles(
  programme: { items: ProgrammeFilm[] } | null | undefined,
): Map<string, string> {
  const map = new Map<string, string>();
  for (const item of programme?.items ?? []) {
    if (item.qloo_entity_id) {
      map.set(item.qloo_entity_id.toLowerCase(), item.title);
    }
  }
  return map;
}

export function whyThisResult(
  members: CohortMember[] | null | undefined,
  programme: { items: ProgrammeFilm[] } | null | undefined,
  bounded: BoundedAttribution | null | undefined,
): WhyResult {
  const titles = seedTitles(programme);
  const list = members ?? [];

  const contributors: Contributor[] = [];
  for (const member of list) {
    const attributions = member.qloo_attributions ?? [];
    if (attributions.length === 0) continue;
    const origin = member.qloo_attribution_origin ?? null;
    contributors.push({
      entityName: member.name ?? member.entity_id,
      origin,
      // A bounded follow-up carries one call id for the whole shortlist; the
      // member's own call_id is the scoring call and must not be presented as
      // the source of this attribution.
      callId: origin === "bounded" ? (bounded?.call_id ?? null) : (member.call_id ?? null),
      seeds: attributions.map((item) => ({
        label: titles.get(item.entity_id.toLowerCase()) ?? UNRESOLVED_SEED,
        weight: item.score,
      })),
    });
  }

  const originKinds = new Set(contributors.map((item) => item.origin));
  const origin =
    originKinds.size === 1
      ? (contributors[0]?.origin ?? null)
      : contributors.length > 0
        ? null
        : null;

  const note =
    origin === "bounded"
      ? "Provider attribution from one bounded follow-up call covering the highest-affinity members of this cohort. The affinity scores above still come from the original scoring call."
      : origin === "scoring"
        ? "Provider attribution returned with the scoring call for this cohort."
        : contributors.length > 0
          ? "Provider attribution from more than one call; each entry names its own call id."
          : "";

  const limits = [
    "A contribution weight is Qloo's own per-seed number for this candidate. It is not audience size, attendance, conversion, revenue or a causal effect.",
    "Only the members shown received a validated contribution; a member without one is unknown, not zero.",
  ];

  if (contributors.length === 0) {
    const status = bounded?.status ?? null;
    const statement = status
      ? (BOUNDED_REASON[status] ??
        `The optional attribution call reported '${status}' for this run.`)
      : "No provider attribution is attached to the winning cohort, so none is shown.";
    return {
      available: false,
      contributors: [],
      headline: "No provider explanation returned",
      statement,
      note: "Absence is not zero: no contribution value was inferred for any member.",
      limits,
    };
  }

  return {
    available: true,
    contributors: contributors.slice(0, 3),
    headline:
      origin === "bounded"
        ? "Explained by one bounded follow-up call"
        : "Explained by the scoring call",
    statement:
      contributors.length === 1
        ? `Qloo attributed this result to ${contributors[0].entityName}.`
        : `Qloo attributed this result to ${contributors.length} members of this cohort.`,
    note,
    limits,
  };
}
