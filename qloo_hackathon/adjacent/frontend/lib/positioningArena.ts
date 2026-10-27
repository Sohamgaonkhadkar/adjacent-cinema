import type {
  AdjacentRunResult,
  CohortMember,
  RankedCohort,
  TraceRow,
} from "@/types/adjacent";

export const POSITIONING_CALCULATION_VERSION = "cultural-positioning-v1" as const;
export const POSITIONING_POLICY_VERSION = "weighted-ordinal-preference-v1" as const;
export const DEFAULT_POSITIONING_POLICY = Object.freeze({ fit: 50, exploration: 25, breadth: 25 });

export type PositioningType = "ANCHOR" | "BRIDGE" | "FRONTIER";
export type PositioningAvailability = "available" | "unavailable";
export type AttributionAuditStatus = "returned" | "missing" | "unsupported" | "not_requested";
export type PositioningDimensionName = "fit" | "exploration" | "breadth";
export type PositioningPolicy = Record<PositioningDimensionName, number>;

export interface PositioningEntityRef {
  entity_id: string;
  name: string;
  domain: string;
  cohort_id: string;
  call_id: string;
  affinity: number;
  data_status: "measured" | "fixture";
}

export interface PositioningEvidenceRef {
  kind: "candidate_affinity" | "shared_qloo_tag" | "shared_seed_attribution";
  description: string;
  call_ids: string[];
  cohort_ids: string[];
  entity_ids: string[];
  source_seed_id?: string;
  qloo_tag_id?: string;
  data_status: "measured" | "fixture";
}

export interface PositioningDimension {
  available: boolean;
  value: number | null;
  unit: string;
  comparison_group: string | null;
  explanation: string;
}

export interface EvidenceChallenge {
  source_inputs: Array<{
    title: string;
    entity_id: string | null;
    resolution_status: string;
    call_ids: string[];
  }>;
  attribution_status: AttributionAuditStatus;
  attribution_statuses: AttributionAuditStatus[];
  attribution_detail: string;
  supporting_call_ids: string[];
  unresolved_references: string[];
  limitations: string[];
  observation_that_supports: string;
  observation_that_contradicts: string;
}

export interface PositioningStrategy {
  id: "anchor" | "bridge" | "frontier";
  type: PositioningType;
  availability: PositioningAvailability;
  unavailable_reason: string | null;
  thesis: string;
  creative_direction: string;
  entity_refs: PositioningEntityRef[];
  source_cohort_ids: string[];
  evidence_refs: PositioningEvidenceRef[];
  data_status: "measured" | "fixture" | "unknown";
  source_rank: number | null;
  evidence_strength: "strong" | "moderate" | null;
  dimensions: {
    fit: PositioningDimension;
    exploration: PositioningDimension;
    breadth: PositioningDimension;
  };
  why_selected: string;
  tradeoffs: string[];
  falsifiable_hypothesis: string;
  suggested_test: {
    comparison_protocol: string;
    primary_measure: string;
    decision_rule: string;
    observation_window: string;
  };
  evidence_challenge: EvidenceChallenge;
}

export interface PositioningMultiverse {
  calculation_version: typeof POSITIONING_CALCULATION_VERSION;
  source_run_id: string | null;
  film_title: string;
  data_status: "measured" | "fixture" | "unknown";
  strategies: PositioningStrategy[];
  source_limitations: string[];
}

export interface StrategyOrderEntry {
  strategy_id: PositioningStrategy["id"];
  rank: number;
  preference_index: number | null;
  used_dimensions: PositioningDimensionName[];
  unavailable_dimensions: Partial<Record<PositioningDimensionName, string>>;
  explanation: string;
}

export interface PositioningOrdering {
  formula_version: typeof POSITIONING_POLICY_VERSION;
  policy: PositioningPolicy;
  entries: StrategyOrderEntry[];
  notes: string[];
}

interface Candidate {
  cohort: RankedCohort;
  members: CohortMember[];
  sourceCallId: string;
  sourceContextId: string;
  qualifying: CohortMember[];
  contextCohorts: RankedCohort[];
  fitRank: number;
  noveltyRank: number | null;
}

interface SourceInputAudit {
  title: string;
  entityId: string;
  resolutionStatus: string;
  callIds: string[];
  unresolvedCallIds: string[];
}

const emptyDimension = (explanation: string): PositioningDimension => ({
  available: false,
  value: null,
  unit: "unavailable",
  comparison_group: null,
  explanation,
});

function finite01(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;
}

function statusOf(value: unknown): "measured" | "fixture" | "unknown" {
  return value === "measured" || value === "fixture" ? value : "unknown";
}

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

function traceMap(traceRows: TraceRow[], dataStatus: "measured" | "fixture" | "unknown") {
  const calls = new Map<string, TraceRow>();
  for (const row of traceRows) {
    if (typeof row.call_id !== "string" || !row.call_id) continue;
    if (dataStatus !== "unknown" && row.data_status !== dataStatus) continue;
    calls.set(row.call_id, row);
  }
  return calls;
}

function sourceInputs(result: AdjacentRunResult, calls: Map<string, TraceRow>): SourceInputAudit[] {
  return (result.programme?.items ?? []).map((item) => {
    const resolution = item.resolution_evidence;
    const id = resolution?.qloo_entity_id ?? item.qloo_entity_id ?? null;
    const rawCalls = [resolution?.call_id, ...(resolution?.related_call_ids ?? [])]
      .filter((callId): callId is string => typeof callId === "string" && Boolean(callId));
    const verified = item.resolved === true && Boolean(id) && (
      statusOf(result.data_status) === "fixture"
        ? true
        : resolution?.match_status === "VERIFIED"
    );
    return {
      title: resolution?.qloo_name ?? item.qloo_name ?? item.title,
      entityId: verified ? id! : "",
      resolutionStatus: resolution?.match_status
        ?? (item.resolved ? (statusOf(result.data_status) === "fixture" ? "FIXTURE_RECORDED_RESOLVED" : "UNVERIFIED") : "UNRESOLVED"),
      callIds: rawCalls.filter((callId) => calls.has(callId)),
      unresolvedCallIds: rawCalls.filter((callId) => !calls.has(callId)),
    };
  });
}

function buildCandidates(
  result: AdjacentRunResult,
  calls: Map<string, TraceRow>,
): Candidate[] {
  const ranked = (result.cohorts?.ranked ?? []).filter((cohort) =>
    Number.isInteger(cohort.rank) && cohort.rank > 0
      && Boolean(cohort.cohort_id)
      && Boolean(cohort.domain)
      && (cohort.verdict === "strong" || cohort.verdict === "moderate")
      && finite01(cohort.score?.mean_affinity)
      && Array.isArray(cohort.members),
  );
  const candidates: Candidate[] = [];
  for (const cohort of ranked) {
    const checkedMembers = cohort.members.filter((member) =>
      typeof member.entity_id === "string" && member.entity_id.length > 0
        && finite01(member.affinity)
        && typeof member.call_id === "string"
        && calls.has(member.call_id),
    );
    const callIds = unique(checkedMembers.map((member) => member.call_id ?? ""));
    if (callIds.length !== 1) continue;
    const scoreCallId = cohort.score?.call_id;
    if (scoreCallId && (!calls.has(scoreCallId) || scoreCallId !== callIds[0])) continue;
    const cohortContextId = cohort.context_id;
    const scoreContextId = cohort.score?.context_id;
    if (cohortContextId && scoreContextId && cohortContextId !== scoreContextId) continue;
    const sourceContextId = scoreContextId || cohortContextId || `legacy:${cohort.domain}:${callIds[0]}`;
    const qualifying = checkedMembers.filter((member) => (member.affinity ?? -1) >= 0.5);
    if (qualifying.length < 2) continue;
    candidates.push({
      cohort,
      members: checkedMembers,
      sourceCallId: callIds[0],
      sourceContextId,
      qualifying,
      contextCohorts: [],
      fitRank: 0,
      noveltyRank: null,
    });
  }

  const contexts = new Map<string, Candidate[]>();
  for (const candidate of candidates) {
    const sameContext = contexts.get(candidate.sourceContextId) ?? [];
    sameContext.push(candidate);
    contexts.set(candidate.sourceContextId, sameContext);
  }
  for (const sameContext of contexts.values()) {
    const byFit = [...sameContext].sort((a, b) =>
      (b.cohort.score?.mean_affinity ?? -1) - (a.cohort.score?.mean_affinity ?? -1)
        || a.cohort.rank - b.cohort.rank
        || a.cohort.cohort_id.localeCompare(b.cohort.cohort_id),
    );
    const byNovelty = [...sameContext].filter((item) => finite01(item.cohort.score?.novelty_proxy))
      .sort((a, b) =>
        (b.cohort.score?.novelty_proxy ?? -1) - (a.cohort.score?.novelty_proxy ?? -1)
          || a.cohort.rank - b.cohort.rank
          || a.cohort.cohort_id.localeCompare(b.cohort.cohort_id),
      );
    for (const candidate of sameContext) {
      candidate.contextCohorts = byFit.map((item) => item.cohort);
      const candidateFit = candidate.cohort.score?.mean_affinity ?? -1;
      candidate.fitRank = 1 + byFit.filter((item) => (item.cohort.score?.mean_affinity ?? -1) > candidateFit).length;
      const candidateNovelty = candidate.cohort.score?.novelty_proxy;
      candidate.noveltyRank = finite01(candidateNovelty)
        ? 1 + byNovelty.filter((item) => (item.cohort.score?.novelty_proxy ?? -1) > candidateNovelty).length
        : null;
    }
  }
  return candidates.sort((a, b) => a.cohort.rank - b.cohort.rank || a.cohort.cohort_id.localeCompare(b.cohort.cohort_id));
}

function attributionStatuses(members: CohortMember[]): AttributionAuditStatus[] {
  const normalized = members.map((member): AttributionAuditStatus => {
    const status = member.qloo_attribution_status;
    // "returned_bounded" is real provider attribution from the winner-only
    // follow-up call. It is not "missing", and its affinity score still comes
    // from the scoring call rather than from this one.
    if (status === "returned" || status === "returned_bounded") return "returned";
    if (status === "unsupported") return status;
    if (typeof status === "string" && status.startsWith("not_requested")) return "not_requested";
    return "missing";
  });
  return [...new Set<AttributionAuditStatus>(normalized)];
}

/**
 * How many members were attributed by the bounded follow-up rather than inline.
 * Reported as a count so the reader can see which call produced the attribution.
 */
function boundedAttributionCount(members: CohortMember[]): number {
  return members.filter(
    (member) =>
      member.qloo_attribution_origin === "bounded" && member.qloo_attribution_status === "returned_bounded",
  ).length;
}

function attributionStatus(members: CohortMember[]): AttributionAuditStatus {
  const statuses = attributionStatuses(members);
  if (statuses.includes("returned")) return "returned";
  if (statuses.includes("unsupported")) return "unsupported";
  if (statuses.includes("not_requested")) return "not_requested";
  return "missing";
}

function challengeFor(
  members: CohortMember[],
  sourceRefs: SourceInputAudit[],
  callIds: string[],
  dataStatus: "measured" | "fixture" | "unknown",
  extraLimitations: string[],
  hypothesis: string,
): EvidenceChallenge {
  const status = attributionStatus(members);
  const sourceInputsForAudit = sourceRefs.map((input) => ({
    title: input.title,
    entity_id: input.entityId || null,
    resolution_status: input.resolutionStatus,
    call_ids: input.callIds,
  }));
  const limitations = [...extraLimitations];
  if (dataStatus === "fixture") limitations.unshift("Fixture evidence is illustrative and is not a live Qloo result.");
  if (dataStatus === "unknown") limitations.unshift("Source data status is unknown; treat this strategy as unavailable for action.");
  if (status !== "returned") limitations.push(`Qloo per-seed attribution is ${status}; absence is not a zero contribution.`);
  limitations.push("Qloo affinity and attribution explain cultural similarity/model contribution, not audience size, viewership, attendance, conversion, revenue, or causal lift.");
  limitations.push("Automated reference and provenance checks do not prove that every generated sentence is semantically entailed by its cited evidence.");
  return {
    source_inputs: sourceInputsForAudit,
    attribution_status: status,
    attribution_statuses: attributionStatuses(members),
    attribution_detail: status === "returned"
      ? `Per-member statuses: ${attributionStatuses(members).join(", ") || "missing"}.${boundedAttributionCount(members) > 0 ? ` ${boundedAttributionCount(members)} of ${members.length} member(s) were attributed by one bounded follow-up call for the winning cohort; their affinity scores still come from the scoring call.` : ""} ${dataStatus === "fixture" ? "Fixture attribution values are illustrative, not a live provider response." : "Measured attribution values are provider output, not causal effects."}`
      : `No validated per-seed attribution was available (${status}); no contribution value was inferred.`,
    supporting_call_ids: unique(callIds),
    unresolved_references: unique([
      ...sourceRefs.filter((input) => !input.entityId).map((input) => `${input.title}: ${input.resolutionStatus}`),
      ...sourceRefs.flatMap((input) => input.unresolvedCallIds),
    ]),
    limitations: unique(limitations),
    observation_that_supports: `Record the selected primary measure for the strategy's version and its predeclared denominator/window; compare only as the plan specifies. Hypothesis: ${hypothesis}`,
    observation_that_contradicts: "A comparable observation that fails the creator-set decision rule may contradict the hypothesis; missing or non-comparable records remain inconclusive.",
  };
}

function entityRefs(candidate: Candidate, dataStatus: "measured" | "fixture"): PositioningEntityRef[] {
  return candidate.qualifying.map((member) => ({
    entity_id: member.entity_id,
    name: member.name?.trim() || member.entity_id,
    domain: candidate.cohort.domain,
    cohort_id: candidate.cohort.cohort_id,
    call_id: member.call_id!,
    affinity: member.affinity!,
    data_status: dataStatus,
  }));
}

function candidateEvidence(candidate: Candidate, dataStatus: "measured" | "fixture"): PositioningEvidenceRef {
  const refs = entityRefs(candidate, dataStatus);
  return {
    kind: "candidate_affinity",
    description: `${refs.length} source candidate entities clear the existing Medium similarity band in one ${candidate.cohort.domain} scoring context; the source cohort mean is ${candidate.cohort.score!.mean_affinity!.toFixed(3)}.`,
    call_ids: [candidate.sourceCallId],
    cohort_ids: [candidate.cohort.cohort_id],
    entity_ids: refs.map((ref) => ref.entity_id),
    data_status: dataStatus,
  };
}

function strategyBase(
  id: PositioningStrategy["id"],
  type: PositioningType,
  dataStatus: "measured" | "fixture" | "unknown",
  sourceRefs: SourceInputAudit[],
  why: string,
): PositioningStrategy {
  const noCohort = "No validated cohort evidence is attached.";
  return {
    id,
    type,
    availability: "unavailable",
    unavailable_reason: why,
    thesis: "No strategy generated; source evidence is insufficient.",
    creative_direction: "No creative direction generated.",
    entity_refs: [],
    source_cohort_ids: [],
    evidence_refs: [],
    data_status: dataStatus,
    source_rank: null,
    evidence_strength: null,
    dimensions: {
      fit: emptyDimension(noCohort),
      exploration: emptyDimension(noCohort),
      breadth: emptyDimension(noCohort),
    },
    why_selected: why,
    tradeoffs: [why],
    falsifiable_hypothesis: "No hypothesis generated because validated source evidence is unavailable.",
    suggested_test: {
      comparison_protocol: "Unavailable until a strategy has supported source evidence.",
      primary_measure: "Choose one sourceable measure only after selecting a supported strategy.",
      decision_rule: "Set any practical decision threshold before observing outcomes.",
      observation_window: "Set a fixed observation window before launch.",
    },
    evidence_challenge: challengeFor([], sourceRefs, [], dataStatus, [why], "No hypothesis generated."),
  };
}

function availableStrategy(args: {
  id: PositioningStrategy["id"];
  type: PositioningType;
  candidates: Candidate[];
  sourceRefs: SourceInputAudit[];
  result: AdjacentRunResult;
  dataStatus: "measured" | "fixture";
  thesis: string;
  creativeDirection: string;
  why: string;
  extraEvidence?: PositioningEvidenceRef[];
  extraLimitations?: string[];
  hypothesis: string;
  fit?: PositioningDimension;
  exploration?: PositioningDimension;
}): PositioningStrategy {
  const { id, type, candidates, sourceRefs, dataStatus } = args;
  const cohorts = candidates.map((candidate) => candidate.cohort);
  const members = candidates.flatMap((candidate) => candidate.qualifying);
  const refs = candidates.flatMap((candidate) => entityRefs(candidate, dataStatus));
  const callIds = unique(candidates.map((candidate) => candidate.sourceCallId));
  const domains = unique(cohorts.map((cohort) => cohort.domain));
  const strength = cohorts.every((cohort) => cohort.verdict === "strong") ? "strong" : "moderate";
  const breadth = candidates.reduce((sum, candidate) => sum + candidate.qualifying.length, 0);
  const title = (args.result.film?.title ?? "This film").trim() || "This film";
  const inputNames = unique(sourceRefs.filter((input) => Boolean(input.entityId)).map((input) => input.title)).slice(0, 5);
  const limitations = [
    `Source evidence is ${dataStatus}; strategy dimensions describe returned analysis evidence, not audience response.`,
    "Qloo affinity is cultural similarity, not a forecast of audience size, views, attendance, conversion, or revenue.",
    domains.length > 1
      ? "The source cohorts come from different Qloo scoring contexts. Their affinity values are not directly compared or averaged."
      : "Affinity is compared only within this single Qloo scoring context.",
    "The existing novelty proxy is 1 minus the cohort's median Qloo popularity; it is exploratory framing, not effectiveness or success.",
    ...(args.extraLimitations ?? []),
  ];
  const hypothesis = args.hypothesis;
  return {
    id,
    type,
    availability: "available",
    unavailable_reason: null,
    thesis: args.thesis,
    creative_direction: `${args.creativeDirection}${inputNames.length ? ` Source film references resolved in this run: ${inputNames.join(", ")}.` : " No verified source film reference is available; keep the positioning exploratory."}`,
    entity_refs: refs,
    source_cohort_ids: cohorts.map((cohort) => cohort.cohort_id),
    evidence_refs: [
      ...candidates.map((candidate) => candidateEvidence(candidate, dataStatus)),
      ...(args.extraEvidence ?? []),
    ],
    data_status: dataStatus,
    source_rank: Math.min(...cohorts.map((cohort) => cohort.rank)),
    evidence_strength: strength,
    dimensions: {
      fit: args.fit ?? emptyDimension("No single comparable scoring context supports a fit ordering for this strategy."),
      exploration: args.exploration ?? emptyDimension("No comparable novelty proxy is available for this strategy."),
      breadth: {
        available: true,
        value: domains.length,
        unit: "distinct Qloo entity domains",
        comparison_group: "This source run",
        explanation: `${domains.length} distinct returned domain(s); this is evidence breadth, not audience reach.`,
      },
    },
    why_selected: args.why,
    tradeoffs: unique(limitations),
    falsifiable_hypothesis: hypothesis,
    suggested_test: {
      comparison_protocol: `Compare the selected ${type.toLowerCase()} framing with the filmmaker's existing framing on the same channel, keeping the creative asset and exposure conditions as comparable as practical. If assignment or exposure is not comparable, label the result exploratory; do not claim causality.`,
      primary_measure: "Before launch, select one directly observable action and record raw numerator, eligible denominator, source, channel, and dates. Keep attendance, reach, feedback, and clicks separate.",
      decision_rule: "Before launch, the filmmaker sets the smallest difference that would change the decision. Adjacent supplies no numerical threshold; missing or non-comparable data stays inconclusive.",
      observation_window: "Choose a fixed window before launch; do not extend it after seeing early results.",
    },
    evidence_challenge: challengeFor(
      members,
      sourceRefs,
      callIds,
      dataStatus,
      limitations,
      hypothesis,
    ),
  };
}

function candidateTags(candidate: Candidate): Map<string, { name: string | null; member: CohortMember }> {
  const tags = new Map<string, { name: string | null; member: CohortMember }>();
  for (const member of candidate.qualifying) {
    for (const tag of member.tags ?? []) {
      if (typeof tag.tag_id !== "string" || !tag.tag_id.trim()) continue;
      tags.set(tag.tag_id, { name: tag.name ?? null, member });
    }
  }
  return tags;
}

function commonSeedAttributions(
  left: Candidate,
  right: Candidate,
  sourceRefs: SourceInputAudit[],
): string[] {
  const verifiedIds = new Set(sourceRefs.map((source) => source.entityId.toLowerCase()).filter(Boolean));
  const seedIds = (candidate: Candidate) => new Set(candidate.qualifying.flatMap((member) => {
    if (member.qloo_attribution_status !== "returned" || !Array.isArray(member.qloo_attributions)) return [];
    return member.qloo_attributions.flatMap((attribution) =>
      typeof attribution.entity_id === "string"
        && verifiedIds.has(attribution.entity_id.toLowerCase())
        && finite01(attribution.score)
        ? [attribution.entity_id]
        : [],
    );
  }));
  const rightIds = seedIds(right);
  return [...seedIds(left)].filter((id) => rightIds.has(id)).sort((a, b) => a.localeCompare(b));
}

function bridgeEvidence(
  left: Candidate,
  right: Candidate,
  sourceRefs: SourceInputAudit[],
  dataStatus: "measured" | "fixture",
): PositioningEvidenceRef[] {
  const evidence: PositioningEvidenceRef[] = [];
  const leftTags = candidateTags(left);
  const rightTags = candidateTags(right);
  const sharedTags = [...leftTags.keys()].filter((tag) => rightTags.has(tag)).sort((a, b) => a.localeCompare(b));
  for (const tagId of sharedTags) {
    const leftMember = leftTags.get(tagId)!.member;
    const rightMember = rightTags.get(tagId)!.member;
    evidence.push({
      kind: "shared_qloo_tag",
      description: `${dataStatus === "fixture" ? "Fixture data contains" : "Qloo returned"} the same tag ID${leftTags.get(tagId)?.name ? ` (${leftTags.get(tagId)!.name})` : ""} on candidates in both domains; this is source evidence, not a label-based inference.`,
      call_ids: unique([leftMember.call_id ?? "", rightMember.call_id ?? ""]),
      cohort_ids: [left.cohort.cohort_id, right.cohort.cohort_id],
      entity_ids: [leftMember.entity_id, rightMember.entity_id],
      qloo_tag_id: tagId,
      data_status: dataStatus,
    });
  }
  for (const seedId of commonSeedAttributions(left, right, sourceRefs)) {
    const memberFor = (candidate: Candidate) => candidate.qualifying.find((member) =>
      member.qloo_attribution_status === "returned"
        && member.qloo_attributions?.some((entry) => typeof entry.entity_id === "string" && entry.entity_id.toLowerCase() === seedId.toLowerCase() && finite01(entry.score)),
    );
    const leftMember = memberFor(left);
    const rightMember = memberFor(right);
    if (!leftMember || !rightMember) continue;
    evidence.push({
      kind: "shared_seed_attribution",
      description: `${dataStatus === "fixture" ? "Fixture records include" : "Measured results include validated Qloo attribution to"} the same source film entity (${sourceRefs.find((source) => source.entityId.toLowerCase() === seedId.toLowerCase())?.title ?? seedId}) in both groups; attribution scores are not compared across calls.`,
      call_ids: unique([leftMember.call_id ?? "", rightMember.call_id ?? ""]),
      cohort_ids: [left.cohort.cohort_id, right.cohort.cohort_id],
      entity_ids: [leftMember.entity_id, rightMember.entity_id],
      source_seed_id: seedId,
      data_status: dataStatus,
    });
  }
  return evidence;
}

function strategyHypothesis(type: PositioningType, filmTitle: string, refs: PositioningEntityRef[]): string {
  const direction = refs.slice(0, 3).map((ref) => ref.name).join(", ") || "the selected cultural references";
  return `Compared with the filmmaker's existing framing, a ${type.toLowerCase()} framing of ${filmTitle} around ${direction} will produce an observable difference in the filmmaker's preselected primary action measure during the fixed comparison window. The decision rule is set by the filmmaker before launch; no audience outcome is forecast.`;
}

export function buildPositioningMultiverse(
  result: AdjacentRunResult | null,
  traceRows: TraceRow[],
  sourceRunId: string | null = null,
  runStatus: string | null = "completed",
): PositioningMultiverse | null {
  if (!result) return null;
  const dataStatus = statusOf(result.data_status);
  const calls = traceMap(traceRows, dataStatus);
  const allSourceInputs = sourceInputs(result, calls);
  const verifiedInputs = allSourceInputs.filter((input) => Boolean(input.entityId));
  const commonUnavailable = runStatus !== "completed"
    ? "Positioning Arena is available only after the Creator run completes."
    : result.mode !== "creator"
      ? "Positioning Arena requires a completed Creator run."
      : dataStatus === "unknown"
      ? "The run has no verified measured/fixture data status."
      : null;
  const candidates = buildCandidates(result, calls);
  const filmTitle = (result.film?.title ?? "Untitled film").trim() || "Untitled film";
  const reasons = result.programme?.items?.filter((item) => !item.resolved).map((item) => `Unresolved source input: ${item.title}.`) ?? [];
  const insufficient = "No cohort clears the existing evidence gate with at least two trace-linked members at or above Qloo's Medium (0.5) band.";

  let anchor = strategyBase("anchor", "ANCHOR", dataStatus, allSourceInputs, commonUnavailable ?? insufficient);
  if (!commonUnavailable && dataStatus !== "unknown" && candidates.length > 0) {
    const best = candidates[0];
    const refs = entityRefs(best, dataStatus);
    const thesis = `Position ${filmTitle} toward the ${best.cohort.domain.replace("urn:entity:", "")} cultural world represented by ${refs.slice(0, 3).map((ref) => ref.name).join(", ")}.`;
    const hypothesis = strategyHypothesis("ANCHOR", filmTitle, refs);
    anchor = availableStrategy({
      id: "anchor", type: "ANCHOR", candidates: [best], sourceRefs: allSourceInputs, result, dataStatus,
      thesis,
      creativeDirection: `Use the supported ${best.cohort.domain.replace("urn:entity:", "")} references ${refs.slice(0, 3).map((ref) => ref.name).join(", ")} as creative framing prompts; retain the filmmaker's voice and test the framing against the existing version.`,
      why: `Selected from the completed run's existing cohort order (rank ${best.cohort.rank}), which prioritizes the existing evidence verdict, novelty proxy, qualifying-member count, and within-context affinity tiebreak. No affinity values from separate Qloo contexts are compared.`,
      hypothesis,
      fit: {
        available: true, value: best.fitRank, unit: "within-context affinity rank (lower is stronger)",
        comparison_group: best.sourceContextId,
        explanation: `Rank ${best.fitRank} of ${best.contextCohorts.length} eligible cohort(s) in the same Qloo scoring context, ordered by returned mean affinity. This is ordinal, not a calibrated score.`,
      },
      exploration: finite01(best.cohort.score?.novelty_proxy) && best.noveltyRank !== null
        ? { available: true, value: best.cohort.score!.novelty_proxy!, unit: "existing novelty proxy", comparison_group: best.sourceContextId, explanation: `Within this Qloo scoring context, novelty rank ${best.noveltyRank}; source proxy is 1 − median Qloo popularity.` }
        : emptyDimension("The source cohort did not include a validated novelty proxy."),
      extraLimitations: reasons,
    });
  }

  let bridge = strategyBase("bridge", "BRIDGE", dataStatus, allSourceInputs, commonUnavailable ?? "No evidence-backed cross-domain relationship was returned.");
  if (!commonUnavailable && dataStatus !== "unknown") {
    const pairs: Array<{ left: Candidate; right: Candidate; evidence: PositioningEvidenceRef[] }> = [];
    for (let i = 0; i < candidates.length; i += 1) {
      for (let j = i + 1; j < candidates.length; j += 1) {
        const left = candidates[i];
        const right = candidates[j];
        if (left.cohort.domain === right.cohort.domain) continue;
        const relation = bridgeEvidence(left, right, verifiedInputs, dataStatus);
        const unionIds = unique([...left.qualifying, ...right.qualifying].map((member) => member.entity_id));
        if (relation.length && (unionIds.length > (candidates[0]?.qualifying.length ?? 0)
          || unionIds.some((id) => !candidates[0]?.qualifying.some((member) => member.entity_id === id)))) {
          pairs.push({ left, right, evidence: relation });
        }
      }
    }
    pairs.sort((a, b) =>
      Math.min(a.left.cohort.rank, a.right.cohort.rank) - Math.min(b.left.cohort.rank, b.right.cohort.rank)
        || Math.max(a.left.cohort.rank, a.right.cohort.rank) - Math.max(b.left.cohort.rank, b.right.cohort.rank)
        || `${a.left.cohort.cohort_id}|${a.right.cohort.cohort_id}`.localeCompare(`${b.left.cohort.cohort_id}|${b.right.cohort.cohort_id}`),
    );
    const pair = pairs[0];
    if (pair) {
      const refs = [...entityRefs(pair.left, dataStatus), ...entityRefs(pair.right, dataStatus)];
      const thesis = `Test a bridge between the ${pair.left.cohort.domain.replace("urn:entity:", "")} and ${pair.right.cohort.domain.replace("urn:entity:", "")} worlds through the source-recorded shared tag or source-film attribution.`;
      const hypothesis = strategyHypothesis("BRIDGE", filmTitle, refs);
      bridge = availableStrategy({
        id: "bridge", type: "BRIDGE", candidates: [pair.left, pair.right], sourceRefs: allSourceInputs, result, dataStatus,
        thesis,
        creativeDirection: `Explore a film framing that puts ${refs.slice(0, 2).map((ref) => ref.name).join(" and ")} in conversation only through the recorded shared relation; do not imply the referenced entities are directly connected beyond the returned tag/attribution evidence.`,
        why: `Selected because two strong/moderate cohorts in distinct domains share ${pair.evidence.map((item) => item.kind === "shared_qloo_tag" ? `${dataStatus === "fixture" ? "fixture-recorded tag" : "Qloo tag"} ${item.qloo_tag_id}` : `${dataStatus === "fixture" ? "fixture attribution" : "validated attribution"} to source ${item.source_seed_id}`).join("; ")}. Attribution weights are not compared across calls.`,
        hypothesis,
        extraEvidence: pair.evidence,
        extraLimitations: ["This is a shared-evidence bridge, not proof of an audience overlap or a direct cultural relationship between candidate entities."],
        fit: emptyDimension("Bridge source cohorts come from distinct Qloo query contexts; their affinities cannot be compared or averaged."),
        exploration: emptyDimension("Bridge source cohorts come from distinct contexts; novelty proxies are not compared across queries."),
      });
    } else if (candidates.length < 2 || !verifiedInputs.length) {
      bridge.unavailable_reason = !verifiedInputs.length
        ? "No source film/reference was verified in the run; a cross-domain bridge cannot be attributed to an actual input."
        : "Fewer than two eligible distinct-domain cohorts are available."
      bridge.why_selected = bridge.unavailable_reason;
      bridge.tradeoffs = [bridge.unavailable_reason];
    } else {
      bridge.unavailable_reason = "No validated shared Qloo tag or per-seed attribution links two eligible cohorts in distinct domains; no bridge was inferred from labels alone.";
      bridge.why_selected = bridge.unavailable_reason;
      bridge.tradeoffs = [bridge.unavailable_reason];
    }
  }

  let frontier = strategyBase("frontier", "FRONTIER", dataStatus, allSourceInputs, commonUnavailable ?? "No less-conventional alternative meets the minimum evidence requirement in the anchor's scoring context.");
  if (!commonUnavailable && dataStatus !== "unknown" && anchor.availability === "available") {
    const anchorCandidate = candidates.find((candidate) => candidate.cohort.cohort_id === anchor.source_cohort_ids[0]);
    const anchorEntityIds = new Set(anchor.entity_refs.map((ref) => ref.entity_id));
    const alternatives = candidates.filter((candidate) =>
      candidate.sourceContextId === anchorCandidate?.sourceContextId
        && candidate.cohort.cohort_id !== anchorCandidate?.cohort.cohort_id
        && finite01(candidate.cohort.score?.novelty_proxy)
        && finite01(anchorCandidate?.cohort.score?.novelty_proxy)
        && (candidate.cohort.score?.novelty_proxy ?? -1) > (anchorCandidate?.cohort.score?.novelty_proxy ?? 1)
        && candidate.qualifying.some((member) => !anchorEntityIds.has(member.entity_id)),
    ).sort((a, b) =>
      (b.cohort.score!.novelty_proxy! - a.cohort.score!.novelty_proxy!)
        || a.cohort.rank - b.cohort.rank
        || a.cohort.cohort_id.localeCompare(b.cohort.cohort_id),
    );
    const frontierCandidate = alternatives[0];
    if (frontierCandidate) {
      const refs = entityRefs(frontierCandidate, dataStatus);
      const hypothesis = strategyHypothesis("FRONTIER", filmTitle, refs);
      frontier = availableStrategy({
        id: "frontier", type: "FRONTIER", candidates: [frontierCandidate], sourceRefs: allSourceInputs, result, dataStatus,
        thesis: `Explore a less-conventional direction in the same ${frontierCandidate.cohort.domain.replace("urn:entity:", "")} scoring context, using its higher existing novelty proxy (${frontierCandidate.cohort.score!.novelty_proxy!.toFixed(3)}) and its independently passing evidence gate.`,
        creativeDirection: `Use ${refs.slice(0, 3).map((ref) => ref.name).join(", ")} as exploratory reference points. Make the framing visibly experimental; novelty does not imply effectiveness.`,
        why: `Selected as a distinct, qualifying alternative to the anchor with a higher existing novelty proxy in the same scoring context. The cohort passes the existing two-member Medium-band evidence gate; novelty is not a success claim.`,
        hypothesis,
        extraLimitations: ["Frontier is exploratory because its same-context median popularity is lower than the anchor's; this does not establish effectiveness, audience demand, or success."],
        fit: {
          available: true, value: frontierCandidate.fitRank, unit: "within-context affinity rank (lower is stronger)",
          comparison_group: frontierCandidate.sourceContextId,
          explanation: `Rank ${frontierCandidate.fitRank} of ${frontierCandidate.contextCohorts.length} eligible cohort(s) in the same Qloo context; raw affinity is not compared outside this context.`,
        },
        exploration: {
          available: true, value: frontierCandidate.cohort.score!.novelty_proxy!, unit: "existing novelty proxy", comparison_group: frontierCandidate.sourceContextId,
          explanation: `Higher than the anchor within this same scoring context; source proxy is 1 − median Qloo popularity.`,
        },
      });
    } else {
      frontier.unavailable_reason = "No distinct alternative in the anchor's same scoring context has both the existing minimum evidence gate and a higher, non-missing novelty proxy. Novelty was not inferred from labels.";
      frontier.why_selected = frontier.unavailable_reason;
      frontier.tradeoffs = [frontier.unavailable_reason];
    }
  }

  return {
    calculation_version: POSITIONING_CALCULATION_VERSION,
    source_run_id: sourceRunId,
    film_title: filmTitle,
    data_status: dataStatus,
    strategies: [anchor, bridge, frontier],
    source_limitations: unique([
      ...(dataStatus === "fixture" ? ["This run is fixture data; it demonstrates workflow only and is not live provider evidence."] : []),
      ...(dataStatus === "unknown" ? ["Run provenance is not measured or fixture; no strategy may be treated as supported."] : []),
      ...reasons,
      "Qloo similarity scores from separate scoring contexts are not directly comparable; this engine uses within-context ranks only.",
    ]),
  };
}

function validPolicy(policy: PositioningPolicy): PositioningPolicy {
  for (const key of ["fit", "exploration", "breadth"] as const) {
    const value = policy[key];
    if (!Number.isInteger(value) || value < 0 || value > 100) {
      throw new RangeError(`${key} priority must be an integer from 0 to 100.`);
    }
  }
  return { fit: policy.fit, exploration: policy.exploration, breadth: policy.breadth };
}

function ordinalValues(
  strategies: PositioningStrategy[],
  dimension: "fit" | "exploration",
): Map<string, number> {
  const groups = new Map<string, PositioningStrategy[]>();
  for (const strategy of strategies) {
    const metric = strategy.dimensions[dimension];
    if (!metric.available || metric.value === null || !metric.comparison_group) continue;
    const group = groups.get(metric.comparison_group) ?? [];
    group.push(strategy);
    groups.set(metric.comparison_group, group);
  }
  const values = new Map<string, number>();
  for (const group of groups.values()) {
    const sorted = [...group].sort((a, b) => {
      const av = a.dimensions[dimension].value!;
      const bv = b.dimensions[dimension].value!;
      const delta = dimension === "fit" ? av - bv : bv - av;
      return delta || a.id.localeCompare(b.id);
    });
    let start = 0;
    while (start < sorted.length) {
      const value = sorted[start].dimensions[dimension].value;
      let end = start + 1;
      while (end < sorted.length && sorted[end].dimensions[dimension].value === value) end += 1;
      const averagePosition = (start + end - 1) / 2;
      const ordinal = sorted.length < 2 ? 0.5 : 1 - averagePosition / (sorted.length - 1);
      for (let index = start; index < end; index += 1) values.set(sorted[index].id, ordinal);
      start = end;
    }
  }
  return values;
}

export function orderPositioningStrategies(
  multiverse: PositioningMultiverse,
  inputPolicy: PositioningPolicy,
): PositioningOrdering {
  const policy = validPolicy(inputPolicy);
  const available = multiverse.strategies.filter((strategy) => strategy.availability === "available");
  const fitValues = ordinalValues(available, "fit");
  const explorationValues = ordinalValues(available, "exploration");
  const breadthValues = new Map<string, number>();
  const breadthSorted = [...available].sort((a, b) =>
    (b.dimensions.breadth.value ?? 0) - (a.dimensions.breadth.value ?? 0) || a.id.localeCompare(b.id),
  );
  let breadthStart = 0;
  while (breadthStart < breadthSorted.length) {
    const value = breadthSorted[breadthStart].dimensions.breadth.value;
    let breadthEnd = breadthStart + 1;
    while (breadthEnd < breadthSorted.length && breadthSorted[breadthEnd].dimensions.breadth.value === value) breadthEnd += 1;
    const averagePosition = (breadthStart + breadthEnd - 1) / 2;
    const ordinal = breadthSorted.length < 2 ? 0.5 : 1 - averagePosition / (breadthSorted.length - 1);
    for (let index = breadthStart; index < breadthEnd; index += 1) breadthValues.set(breadthSorted[index].id, ordinal);
    breadthStart = breadthEnd;
  }

  const entries = available.map((strategy) => {
    const values: Record<PositioningDimensionName, number | undefined> = {
      fit: fitValues.get(strategy.id),
      exploration: explorationValues.get(strategy.id),
      breadth: breadthValues.get(strategy.id),
    };
    const unavailableDimensions: Partial<Record<PositioningDimensionName, string>> = {};
    for (const dimension of ["fit", "exploration", "breadth"] as const) {
      if (policy[dimension] > 0 && values[dimension] === undefined) {
        unavailableDimensions[dimension] = strategy.dimensions[dimension].explanation;
      }
    }
    const usedDimensions = (["fit", "exploration", "breadth"] as const)
      .filter((dimension) => policy[dimension] > 0 && values[dimension] !== undefined);
    const totalWeight = usedDimensions.reduce((sum, dimension) => sum + policy[dimension], 0);
    const preferenceIndex = totalWeight > 0
      ? usedDimensions.reduce((sum, dimension) => sum + policy[dimension] * values[dimension]!, 0) / totalWeight
      : null;
    const description = usedDimensions.length
      ? usedDimensions.map((dimension) => `${dimension} priority ${policy[dimension]} contributes ordinal preference ${values[dimension]!.toFixed(2)}`).join("; ")
      : "No comparable weighted dimensions are available; retain source-run rank ordering.";
    return {
      strategy_id: strategy.id,
      rank: 0,
      preference_index: preferenceIndex,
      used_dimensions: usedDimensions,
      unavailable_dimensions: unavailableDimensions,
      explanation: description,
    } satisfies StrategyOrderEntry;
  });
  entries.sort((a, b) => {
    const indexDelta = (b.preference_index ?? -1) - (a.preference_index ?? -1);
    if (indexDelta) return indexDelta;
    const aRank = multiverse.strategies.find((strategy) => strategy.id === a.strategy_id)?.source_rank ?? Number.MAX_SAFE_INTEGER;
    const bRank = multiverse.strategies.find((strategy) => strategy.id === b.strategy_id)?.source_rank ?? Number.MAX_SAFE_INTEGER;
    return aRank - bRank || a.strategy_id.localeCompare(b.strategy_id);
  });
  entries.forEach((entry, index) => { entry.rank = index + 1; });

  return {
    formula_version: POSITIONING_POLICY_VERSION,
    policy,
    entries,
    notes: [
      "Preference index is a deterministic weighted average of ordinal positions (0–1), not a calibrated score, probability, audience forecast, or effectiveness prediction.",
      "Fit and exploration are ranked only within each source Qloo scoring context; raw affinities and novelty proxies are never compared across contexts.",
      "Policy changes reorder existing strategies only. This function is pure and makes no provider request.",
    ],
  };
}

export function readSavedPositioningSnapshot(sourceBet: unknown): Record<string, unknown> | null {
  if (!sourceBet || typeof sourceBet !== "object" || Array.isArray(sourceBet)) return null;
  const snapshot = (sourceBet as Record<string, unknown>).cultural_multiverse_snapshot;
  return snapshot && typeof snapshot === "object" && !Array.isArray(snapshot)
    ? snapshot as Record<string, unknown>
    : null;
}
