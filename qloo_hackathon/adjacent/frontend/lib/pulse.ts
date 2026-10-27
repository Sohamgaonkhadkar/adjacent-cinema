/**
 * Audience Pulse — view model for the pre-registered poll.
 *
 * The panel and the participant page share one rule with the backend: the
 * creator's decision rule is fixed before collection, the arithmetic is a share
 * of the responses actually stored, and a small sample is INCONCLUSIVE. Nothing
 * in this file invents a number: missing counts stay `null` and an unreadable
 * payload becomes an explicit state, never a zero.
 */

export type PulseCollectionStatus = "OPEN" | "SCHEDULED" | "CLOSED" | "EXPIRED";
export type PulseOutcome = "SUPPORTED" | "CONTRADICTED" | "INCONCLUSIVE";

export interface PulseOption {
  option_id: string;
  label: string;
}

export interface PulseOptionCount extends PulseOption {
  count: number;
  share: number | null;
}

export interface PulseCounts {
  total: number;
  unrecognised: number;
  options: PulseOptionCount[];
}

export interface PulseCollection {
  status: PulseCollectionStatus;
  accepting_responses: boolean;
  reason: string;
}

export interface PulseRule {
  kind: string;
  option_id: string;
  option_label: string;
  threshold: number;
  min_responses: number;
  statement: string;
}

export interface PulseEvaluationRecord {
  evaluation_id: string;
  poll_id: string;
  created_at: string;
  outcome: PulseOutcome;
  rationale: string;
  rule_applied: PulseRule;
  counts: { total: number; options: PulseOptionCount[]; unrecognised: number };
  sample_size: number;
  collection_status: string;
  limitations: string[];
  supersedes_id: string | null;
}

export interface PulsePoll {
  poll_id: string;
  experiment_id: string;
  created_at: string;
  share_token: string;
  question: string;
  options: PulseOption[];
  hypothesis: string;
  decision_rule: PulseRule;
  opens_at: string;
  closes_at: string;
  closed_at: string | null;
  frozen_at: string | null;
  definition_frozen: boolean;
  response_count: number;
  counts: PulseCounts;
  collection: PulseCollection;
  evaluation_preview?: PulseEvaluationRecord;
  latest_evaluation: PulseEvaluationRecord | null;
}

export interface PulseOwnerPollResponse {
  schema: string;
  poll: PulsePoll;
  responses?: { response_id: string; option_id: string; submitted_at: string }[];
  evaluations: PulseEvaluationRecord[];
  share_path?: string;
}

export interface PulsePollListResponse {
  schema: string;
  sharing_enabled: boolean;
  polls: { poll: PulsePoll; share_path: string }[];
}

export interface SharedPulse {
  schema: string;
  question: string;
  options: PulseOption[];
  opens_at: string;
  closes_at: string;
  collection: PulseCollection;
  counts?: { total: number; options: PulseOptionCount[] };
  limitations: string[];
  already_responded: boolean;
}

export type PulseTone = "live" | "neutral" | "warn" | "fail";

// ─── Formatting ─────────────────────────────────────────────────────────────

const SHARE_FALLBACK = "—";

export function formatShare(share: number | null | undefined): string {
  if (typeof share !== "number" || Number.isNaN(share)) return SHARE_FALLBACK;
  return `${Math.round(share * 100)}%`;
}

/** UTC-rendered timestamp: the collection window must mean one thing to everyone. */
export function formatPulseTime(value: string | null | undefined): string {
  if (typeof value !== "string" || !value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  const iso = parsed.toISOString();
  return `${iso.slice(0, 10)} ${iso.slice(11, 16)} UTC`;
}

export function formatPulseWindow(opensAt: string, closesAt: string): string {
  return `${formatPulseTime(opensAt)} → ${formatPulseTime(closesAt)}`;
}

export function describeCollection(collection: PulseCollection | null | undefined): {
  label: string;
  tone: PulseTone;
  detail: string;
} {
  const status = collection?.status;
  const detail = collection?.reason ?? "The collection window was not reported.";
  if (status === "OPEN") return { label: "Collecting responses", tone: "live", detail };
  if (status === "SCHEDULED") return { label: "Not open yet", tone: "neutral", detail };
  if (status === "CLOSED") return { label: "Closed by the creator", tone: "neutral", detail };
  if (status === "EXPIRED") return { label: "Window expired", tone: "warn", detail };
  return { label: "Collection status unavailable", tone: "warn", detail };
}

export function describeOutcome(outcome: PulseOutcome | null | undefined): {
  label: string;
  tone: PulseTone;
  explanation: string;
} {
  if (outcome === "SUPPORTED") {
    return {
      label: "Supported",
      tone: "live",
      explanation: "The pre-registered share was met on the responses actually collected.",
    };
  }
  if (outcome === "CONTRADICTED") {
    return {
      label: "Contradicted",
      tone: "fail",
      explanation: "The sample was large enough and the pre-registered share was not met.",
    };
  }
  if (outcome === "INCONCLUSIVE") {
    return {
      label: "Inconclusive",
      tone: "warn",
      explanation: "The rule could not decide on the responses collected so far.",
    };
  }
  return {
    label: "Not evaluated",
    tone: "neutral",
    explanation: "No evaluation has been recorded for this poll.",
  };
}

export function summariseCounts(counts: PulseCounts | null | undefined): string {
  if (!counts || typeof counts.total !== "number") return "No counts reported.";
  if (counts.total === 0) return "0 responses recorded — an empty poll, not missing data.";
  const ranked = [...counts.options].sort((a, b) => b.count - a.count);
  const top = ranked[0];
  const tail =
    top && top.count > 0
      ? ` · most chosen: “${top.label}” (${top.count} of ${counts.total}, ${formatShare(top.share)})`
      : "";
  const stray = counts.unrecognised > 0 ? ` · ${counts.unrecognised} unmatched response(s)` : "";
  const noun = counts.total === 1 ? "response" : "responses";
  return `${counts.total} ${noun} recorded${tail}${stray}`;
}

// ─── Owner view ─────────────────────────────────────────────────────────────

export interface PulsePollRow {
  pollId: string;
  question: string;
  hypothesis: string;
  ruleStatement: string;
  window: string;
  collectionStatus: PulseCollectionStatus | null;
  collection: { label: string; tone: PulseTone; detail: string };
  headline: string;
  counts: PulseCounts;
  frozen: boolean;
  sharePath: string | null;
  latest: PulseEvaluationRecord | null;
  preview: PulseEvaluationRecord | null;
}

export interface OwnerPulseView {
  available: boolean;
  reason: string;
  sharingEnabled: boolean;
  rows: PulsePollRow[];
}

export function buildOwnerPulseView(
  list: PulsePollListResponse | null | undefined,
): OwnerPulseView {
  if (!list || !Array.isArray(list.polls)) {
    return {
      available: false,
      reason: "The poll list was not returned by this deployment.",
      sharingEnabled: false,
      rows: [],
    };
  }
  return {
    available: true,
    reason: "",
    sharingEnabled: Boolean(list.sharing_enabled),
    rows: list.polls.map(({ poll, share_path }) => ({
      pollId: poll.poll_id,
      question: poll.question,
      hypothesis: poll.hypothesis,
      ruleStatement: poll.decision_rule?.statement ?? "No decision rule recorded.",
      window: formatPulseWindow(poll.opens_at, poll.closes_at),
      collectionStatus: poll.collection?.status ?? null,
      collection: describeCollection(poll.collection),
      headline: summariseCounts(poll.counts),
      counts: poll.counts,
      frozen: Boolean(poll.definition_frozen),
      sharePath: share_path || null,
      latest: poll.latest_evaluation ?? null,
      preview: poll.evaluation_preview ?? null,
    })),
  };
}

/** Bar widths for the distribution. Zero-response polls render nothing. */
export function distributionRows(
  counts: PulseCounts | null | undefined,
): { optionId: string; label: string; count: number; share: number | null; widthPercent: number }[] {
  if (!counts || !Array.isArray(counts.options)) return [];
  return counts.options.map((option) => ({
    optionId: option.option_id,
    label: option.label,
    count: option.count,
    share: option.share,
    widthPercent: typeof option.share === "number" ? Math.round(option.share * 100) : 0,
  }));
}

/** One-line explanation of what the recorded evaluation did, for the receipt. */
export function evaluationLine(evaluation: PulseEvaluationRecord | null | undefined): string {
  if (!evaluation) return "No evaluation recorded. The counts above are observations, not a verdict.";
  const outcome = describeOutcome(evaluation.outcome);
  return `${outcome.label} · ${evaluation.rationale}`;
}

/**
 * Seed for an evaluation's idempotency key.
 *
 * The key is derived from what the rule would actually read — the stored sample
 * and the collection state — so a double click resolves to the record the
 * backend already wrote, while a genuinely new evaluation (after more responses
 * arrived) is allowed its own id.
 */
export function evaluationRequestSeed(row: {
  pollId: string;
  counts: PulseCounts;
  collectionStatus: PulseCollectionStatus | null;
}): { poll: string; sample: number; collected: PulseCollectionStatus | null } {
  return {
    poll: row.pollId,
    sample: row.counts?.total ?? 0,
    collected: row.collectionStatus,
  };
}

// ─── Participant view ───────────────────────────────────────────────────────

export type BallotState =
  | { kind: "loading" }
  | { kind: "unavailable"; title: string; detail: string }
  | { kind: "error"; detail: string; limitations: string[] }
  | {
      kind: "open";
      question: string;
      options: PulseOption[];
      window: string;
      limitations: string[];
    }
  | {
      kind: "answered";
      question: string;
      detail: string;
      limitations: string[];
    }
  | {
      kind: "closed";
      question: string;
      status: PulseCollectionStatus;
      reason: string;
      counts: { total: number; options: PulseOptionCount[] } | null;
      limitations: string[];
    };

export function buildBallotState(input: {
  loading?: boolean;
  error?: string | null;
  status?: number | null;
  data?: SharedPulse | null;
}): BallotState {
  if (input.loading) return { kind: "loading" };
  if (input.error) {
    const unavailable = input.status === 404 || input.status === 503;
    if (unavailable) {
      return {
        kind: "unavailable",
        title: "This poll is not available",
        detail: input.error,
      };
    }
    return { kind: "error", detail: input.error, limitations: [] };
  }
  const data = input.data;
  if (!data || !Array.isArray(data.options) || data.options.length === 0) {
    return {
      kind: "unavailable",
      title: "This poll is not available",
      detail: "The link returned no ballot. Nothing is shown rather than a placeholder poll.",
    };
  }
  const limitations = Array.isArray(data.limitations) ? data.limitations : [];
  if (!data.collection?.accepting_responses) {
    return {
      kind: "closed",
      question: data.question,
      status: data.collection?.status ?? "EXPIRED",
      reason: data.collection?.reason ?? "This poll is not accepting responses.",
      counts: data.counts ?? null,
      limitations,
    };
  }
  if (data.already_responded) {
    return {
      kind: "answered",
      question: data.question,
      detail:
        "This browser has already answered. One response per session keeps the count honest; totals stay hidden until collection closes.",
      limitations,
    };
  }
  return {
    kind: "open",
    question: data.question,
    options: data.options,
    window: formatPulseWindow(data.opens_at, data.closes_at),
    limitations,
  };
}

// ─── Draft validation (mirrors the backend, never replaces it) ──────────────

export interface PulseDraft {
  question: string;
  options: string[];
  opensAt: string;
  closesAt: string;
  ruleOptionIndex: number;
  thresholdPercent: number;
  minResponses: number;
}

export interface PulseDraftValidation {
  ok: boolean;
  errors: Partial<Record<keyof PulseDraft | "form", string>>;
  payload: {
    question: string;
    options: { label: string }[];
    opens_at: string;
    closes_at: string;
    decision_rule: { kind: string; option_id: string; threshold: number; min_responses: number };
  } | null;
}

export const PULSE_MIN_RESPONSES_FLOOR = 5;
export const PULSE_MIN_WINDOW_HOURS = 1;
export const PULSE_MAX_WINDOW_DAYS = 90;
export const PULSE_MIN_OPTIONS = 2;
export const PULSE_MAX_OPTIONS = 5;

export function validatePulseDraft(draft: PulseDraft, now: Date = new Date()): PulseDraftValidation {
  const errors: PulseDraftValidation["errors"] = {};

  const question = draft.question.trim().replace(/\s+/g, " ");
  if (!question) errors.question = "Write the one question you will ask.";
  else if (question.length > 240) errors.question = "Keep the question to 240 characters.";

  const labels = draft.options.map((option) => option.trim().replace(/\s+/g, " "));
  const filled = labels.filter(Boolean);
  if (filled.length < PULSE_MIN_OPTIONS) {
    errors.options = `A poll needs at least ${PULSE_MIN_OPTIONS} non-empty options.`;
  } else if (filled.length > PULSE_MAX_OPTIONS) {
    errors.options = `A poll accepts at most ${PULSE_MAX_OPTIONS} options.`;
  } else if (new Set(filled.map((label) => label.toLowerCase())).size !== filled.length) {
    errors.options = "Two options read the same; a duplicate cannot be counted separately.";
  } else if (filled.some((label) => label.length > 120)) {
    errors.options = "Keep each option to 120 characters.";
  }

  const opens = new Date(draft.opensAt);
  const closes = new Date(draft.closesAt);
  if (Number.isNaN(opens.getTime())) errors.opensAt = "Set when collection opens.";
  if (Number.isNaN(closes.getTime())) errors.closesAt = "Set when collection closes.";
  if (!errors.opensAt && !errors.closesAt) {
    const hours = (closes.getTime() - opens.getTime()) / 3_600_000;
    if (closes <= opens) errors.closesAt = "The window must close after it opens.";
    else if (hours < PULSE_MIN_WINDOW_HOURS) {
      errors.closesAt = `The window must stay open for at least ${PULSE_MIN_WINDOW_HOURS} hour.`;
    } else if (hours > PULSE_MAX_WINDOW_DAYS * 24) {
      errors.closesAt = `The window must close within ${PULSE_MAX_WINDOW_DAYS} days.`;
    } else if (closes.getTime() <= now.getTime()) {
      errors.closesAt = "The window must still be open when you publish it.";
    }
  }

  if (!Number.isFinite(draft.thresholdPercent) || draft.thresholdPercent <= 0 || draft.thresholdPercent > 100) {
    errors.thresholdPercent = "Set a threshold above 0% and at most 100%.";
  }
  if (
    !Number.isInteger(draft.minResponses) ||
    draft.minResponses < PULSE_MIN_RESPONSES_FLOOR ||
    draft.minResponses > 5000
  ) {
    errors.minResponses = `Before deciding anything the rule needs at least ${PULSE_MIN_RESPONSES_FLOOR} responses.`;
  }
  if (
    !Number.isInteger(draft.ruleOptionIndex) ||
    draft.ruleOptionIndex < 0 ||
    draft.ruleOptionIndex >= filled.length
  ) {
    errors.ruleOptionIndex = "Choose which option would support the hypothesis.";
  }

  const ok = Object.keys(errors).length === 0;
  return {
    ok,
    errors,
    payload: ok
      ? {
          question,
          options: filled.map((label) => ({ label })),
          opens_at: opens.toISOString(),
          closes_at: closes.toISOString(),
          decision_rule: {
            kind: "option_share_at_least",
            option_id: `opt-${draft.ruleOptionIndex + 1}`,
            threshold: Math.round(draft.thresholdPercent) / 100,
            min_responses: draft.minResponses,
          },
        }
      : null,
  };
}

/** Turn a failed request into a state a creator can act on. */
export function pulseErrorMessage(status: number | null | undefined, detail: unknown): string {
  if (typeof detail === "string" && detail) return detail;
  if (status === 503) {
    return (
      "Audience Pulse sharing is disabled on this deployment. The backend needs " +
      "ADJACENT_PULSE_SHARE_ENABLED=1 before a poll link can collect responses."
    );
  }
  if (status === 404) return "That poll is not on this deployment any more.";
  if (status === 409) return "This poll is not accepting that response.";
  if (status === 422) return "The poll definition was rejected; check the question, options and rule.";
  if (status === 429) return "This connection has sent too many responses. Try again later.";
  return "The poll request did not complete. Nothing was recorded.";
}

export function remainingEvidenceLine(evaluation: PulseEvaluationRecord | null | undefined): string {
  if (!evaluation) return "";
  const remaining = evaluation.rule_applied?.min_responses
    ? evaluation.rule_applied.min_responses - evaluation.sample_size
    : 0;
  if (evaluation.outcome === "INCONCLUSIVE" && remaining > 0) {
    return `${remaining} more valid response(s) would let the pre-registered rule decide.`;
  }
  return "";
}
