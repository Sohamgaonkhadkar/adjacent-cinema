import type {
  AdjacentRunResult,
  CohortMember,
  RankedCohort,
  RejectedCohort,
  TraceRow,
} from "@/types/adjacent";
import type { FingerprintNode, StageView } from "@/types/nf";
import { normalizeEntityName } from "@/lib/entityDisplay";

/**
 * Adapters that turn a *real* backend run into the view models used by the
 * ported Project Nightfall components.
 *
 * Rules enforced here:
 *  - nothing is generated when the run did not return it;
 *  - provider entity names come from provider fields only (`normalizeEntityName`);
 *  - cohort labels are editorial descriptors, never member names or prose;
 *  - a missing affinity stays `null` (rendered as "no score", never zero).
 */

export function domainLabel(domain: string | null | undefined): string {
  if (!domain) return "unknown domain";
  return domain.replace("urn:entity:", "").replace(/_/g, " ");
}

export function cohortKindLabel(kind: string | undefined, domain: string): string {
  if (kind === "subtype_group") return "Shared provider subtype";
  if (kind === "tag_cluster") return "Shared provider tags";
  if (kind === "domain_group") return "Domain-only grouping";
  if (kind === "singleton_group") return "Single candidate";
  return domainLabel(domain);
}

export function cohortDisplayLabel(kind: string | undefined, domain: string, rank: number): string {
  const grouping =
    kind === "tag_cluster"
      ? "tag group"
      : kind === "subtype_group"
        ? "subtype group"
        : kind === "domain_group"
          ? "domain group"
          : kind === "singleton_group"
            ? "candidate"
            : "group";
  return `${domainLabel(domain)} · ${grouping} #${rank}`;
}

export function memberLabel(member: CohortMember): string {
  return normalizeEntityName(member.name) ?? "Name unavailable";
}

function memberNodeId(cohort: RankedCohort, member: CohortMember, index: number): string {
  return `member-${cohort.cohort_id || cohort.domain}-${member.entity_id || index}`;
}

function cohortCallId(cohort: RankedCohort, traceRows: TraceRow[]): string | null {
  return (
    cohort.score?.call_id ??
    cohort.members.find((member) => member.call_id)?.call_id ??
    traceRows.find((row) => row.tool === `score_context:${cohort.domain}`)?.call_id ??
    null
  );
}

export function buildFingerprintNodes(
  result: AdjacentRunResult | null,
  filmTitle: string,
  traceRows: TraceRow[] = [],
  limits: { cohorts?: number; membersPerCohort?: number; tags?: number } = {},
): FingerprintNode[] {
  if (!result) return [];
  const cohortLimit = limits.cohorts ?? 6;
  const memberLimit = limits.membersPerCohort ?? 3;
  const tagLimit = limits.tags ?? 4;

  const nodes: FingerprintNode[] = [];
  const relatedRoots: string[] = [];

  // Resolved references actually used as seeds — or explicitly unresolved.
  const seedNodes: FingerprintNode[] = [];
  for (const [index, item] of (result.programme?.items ?? []).slice(0, 4).entries()) {
    const resolution = item.resolution_evidence;
    const status = resolution?.match_status;
    const resolved = Boolean(item.resolved);
    const id = `seed-${index}`;
    const label =
      normalizeEntityName(resolution?.qloo_name) ??
      normalizeEntityName(item.qloo_name) ??
      item.title?.trim() ??
      `Reference ${index + 1}`;
    seedNodes.push({
      id,
      label,
      kind: "entity",
      domain: "Film",
      affinity: null,
      claim: resolved ? "FACT" : "UNKNOWN",
      note: resolved
        ? `Identity-checked reference seed${status ? ` · ${status}` : ""}. Used as a scoring input, not as an audience overlap claim.`
        : `Unresolved reference${status ? ` · ${status}` : ""}. It was not admitted to the evidence pipeline and contributes nothing.`,
      sourceCallId: resolution?.call_id ?? resolution?.related_call_ids?.[0] ?? null,
      related: ["film"],
    });
    relatedRoots.push(id);
  }

  // Provider-resolved theme tags (only those the backend matched).
  const tagNodes: FingerprintNode[] = (result.theme_inputs ?? [])
    .filter((theme) => theme.status === "matched")
    .slice(0, tagLimit)
    .map((theme, index) => ({
      id: `theme-${index}`,
      label: normalizeEntityName(theme.qloo_name) ?? theme.input,
      kind: "tag" as const,
      domain: "Tag",
      affinity: null,
      claim: "FACT" as const,
      note: "Theme resolved as a provider tag and used as a cultural signal. Not a film title and not an audience segment.",
      sourceCallId: theme.call_id,
      related: ["film"],
    }));

  const ranked = result.cohorts?.ranked ?? [];
  const cohortNodes: FingerprintNode[] = [];
  const memberNodes: FingerprintNode[] = [];

  ranked.slice(0, cohortLimit).forEach((cohort, index) => {
    const cohortId = `cohort-${cohort.cohort_id || index}`;
    const callId = cohortCallId(cohort, traceRows);
    const members = cohort.members ?? [];
    const memberIds = members.slice(0, memberLimit).map((member, memberIndex) => {
      const id = memberNodeId(cohort, member, memberIndex);
      memberNodes.push({
        id,
        label: memberLabel(member),
        kind: "entity",
        domain: domainLabel(cohort.domain),
        affinity: member.affinity,
        band: member.band,
        claim: "FACT",
        note: `${cohortKindLabel(cohort.kind, cohort.domain)} member returned for this cohort${
          member.band ? ` · band ${member.band}` : ""
        }${typeof member.popularity === "number" ? ` · popularity ${member.popularity.toFixed(2)}` : ""}. A returned entity, not a recommendation or a predicted viewer.`,
        sourceCallId: member.call_id ?? callId,
        related: [cohortId],
      });
      return id;
    });

    cohortNodes.push({
      id: cohortId,
      label: cohortDisplayLabel(cohort.kind, cohort.domain, cohort.rank ?? index + 1),
      kind: "cohort",
      domain: domainLabel(cohort.domain),
      affinity: cohort.score?.mean_affinity ?? null,
      members: members.map(memberLabel),
      claim: "FACT",
      note: `Ranked cohort #${cohort.rank ?? index + 1} · ${cohort.member_count} member${
        cohort.member_count === 1 ? "" : "s"
      }${cohort.qualifying_count != null ? ` (${cohort.qualifying_count} qualifying)` : ""}${
        cohort.construction_reason ? `. ${cohort.construction_reason}` : "."
      } Affinity is cultural similarity, not audience size.`,
      sourceCallId: callId,
      related: ["film", ...memberIds],
    });
    relatedRoots.push(cohortId);
  });

  const rejected: FingerprintNode[] = (result.cohorts?.rejected ?? [])
    .slice(0, 4)
    .map((cohort: RejectedCohort, index) => ({
      id: `rejected-${cohort.cohort_id || index}`,
      label: cohortDisplayLabel(undefined, cohort.domain, index + 1),
      kind: "cohort",
      domain: domainLabel(cohort.domain),
      affinity: null,
      claim: "UNKNOWN",
      note: "Rejected or insufficient. Kept visible so the exclusion can be inspected rather than silently deleted.",
      related: [],
      rejected: true,
      rejectReason: cohort.rejection_reason ?? cohort.rejection_detail ?? "Reason not supplied",
    }));

  const filmNode: FingerprintNode = {
    id: "film",
    label: filmTitle || "Your film",
    kind: "film",
    claim: "HYPOTHESIS",
    note:
      "Working title under investigation. It is not a provider entity; the cultural field below is built from the references and themes that actually resolved.",
    related: ["film", ...relatedRoots],
  };

  nodes.push(filmNode, ...seedNodes, ...tagNodes, ...cohortNodes, ...memberNodes, ...rejected);
  return nodes;
}

// ─── Investigation stages ──────────────────────────────────────────────────

const STAGE_DEFS = [
  {
    id: "validate",
    label: "Validate inputs",
    detail: "Title, references and themes are checked before anything is queried.",
  },
  {
    id: "resolve",
    label: "Resolve identities",
    detail: "Comparable works are matched to provider entities. Unresolved titles stay unresolved.",
  },
  {
    id: "tags",
    label: "Resolve theme tags",
    detail: "Themes are queried as tags, not as extra film titles.",
  },
  {
    id: "profile",
    label: "Build taste profile",
    detail: "A cultural profile is assembled only from the signals that resolved.",
  },
  {
    id: "expand",
    label: "Expand adjacent worlds",
    detail: "Neighbouring cohorts are requested within the run's bounded budget.",
  },
  {
    id: "rank",
    label: "Rank and exclude",
    detail: "Cohorts are ranked; insufficient worlds remain visible as rejections.",
  },
  {
    id: "compose",
    label: "Compose the brief",
    detail: "A Programme Bet and Test Card are written from the returned evidence.",
  },
] as const;

type StageId = (typeof STAGE_DEFS)[number]["id"];

const EVENT_TO_STAGE: Record<string, StageId> = {
  resolution: "resolve",
  taste_dna: "profile",
  cohort: "rank",
  heatmap: "rank",
  bet: "compose",
  test_card: "compose",
};

export function buildStageViews({
  started,
  status,
  events,
}: {
  started: boolean;
  status: string | null;
  events: Array<{ event: string }>;
}): StageView[] {
  const terminal = status === "completed" || status === "insufficient" || status === "failed";
  const completed = status === "completed";
  const seen = new Set(events.map((event) => EVENT_TO_STAGE[event.event]).filter(Boolean));
  const running = status === "running" || status === "pending" || status === "queued";

  return STAGE_DEFS.map((stage, index) => {
    let state: StageView["state"] = "wait";
    if (!started) {
      state = "wait";
    } else if (completed) {
      state = "done";
    } else if (seen.has(stage.id)) {
      state = "done";
    } else if (running) {
      // The first unobserved stage is the one currently in flight. The backend
      // does not stream a per-stage phase, so this is deliberately presented as
      // "in progress or next", never as a completed step.
      const firstUnseen = STAGE_DEFS.findIndex((candidate) => !seen.has(candidate.id));
      state = index === firstUnseen ? "now" : "wait";
    } else if (terminal) {
      state = "skipped";
    }
    return { ...stage, state };
  });
}

export function stageStatusLabel(state: StageView["state"]): string {
  if (state === "done") return "DONE";
  if (state === "now") return "NOW";
  if (state === "skipped") return "NOT REACHED";
  return "WAIT";
}

// ─── Text helpers ──────────────────────────────────────────────────────────

export function affinityText(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(2) : "no score";
}

export function filmTitleOf(result: AdjacentRunResult | null, fallback = ""): string {
  const film = result?.film as { title?: string } | undefined;
  return (film?.title ?? fallback ?? "").trim();
}

export function strategyPhotoKey(
  id: "anchor" | "bridge" | "frontier",
): "cinemaEmpty" | "editingTable" | "projectorLens" {
  return id === "anchor" ? "cinemaEmpty" : id === "bridge" ? "editingTable" : "projectorLens";
}
