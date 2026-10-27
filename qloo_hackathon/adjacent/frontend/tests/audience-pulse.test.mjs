import assert from "node:assert/strict";
import test from "node:test";

/**
 * Audience Pulse — view-model contract.
 *
 * The poll is the one place in this app where a number could be mistaken for a
 * verdict. These tests pin the parts that decide what a creator and a
 * participant are told: draft validation before publishing, the participant
 * state machine (including every unavailable path), the owner summary, and the
 * rule that a small sample reads as inconclusive rather than as support.
 */

const {
  PULSE_MIN_RESPONSES_FLOOR,
  buildBallotState,
  buildOwnerPulseView,
  describeCollection,
  describeOutcome,
  distributionRows,
  evaluationLine,
  evaluationRequestSeed,
  formatPulseTime,
  formatPulseWindow,
  formatShare,
  pulseErrorMessage,
  remainingEvidenceLine,
  summariseCounts,
  validatePulseDraft,
} = await import("../lib/pulse.ts");

const NOW = new Date("2026-03-10T12:00:00Z");
const later = (days) => new Date(NOW.getTime() + days * 86_400_000).toISOString();

function draft(overrides = {}) {
  return {
    question: "Would you watch this at a Friday late show?",
    options: ["Yes", "No", "Not sure"],
    opensAt: "2026-03-10T11:00",
    closesAt: "2026-03-24T11:00",
    ruleOptionIndex: 0,
    thresholdPercent: 60,
    minResponses: 10,
    ...overrides,
  };
}

const rule = {
  kind: "option_share_at_least",
  option_id: "opt-1",
  option_label: "Yes",
  threshold: 0.6,
  min_responses: 10,
  statement: "SUPPORTED when 60% or more of valid responses choose “Yes”…",
};

function evaluation(overrides = {}) {
  return {
    evaluation_id: "eval-1",
    poll_id: "poll-1",
    created_at: "2026-03-20T10:00:00+00:00",
    outcome: "INCONCLUSIVE",
    rationale: "4 valid response(s) were recorded and the rule requires at least 10.",
    rule_applied: rule,
    counts: { total: 4, options: [], unrecognised: 0 },
    sample_size: 4,
    collection_status: "OPEN",
    limitations: ["Respondents choose to open the link."],
    supersedes_id: null,
    ...overrides,
  };
}

function poll(overrides = {}) {
  return {
    poll_id: "poll-1",
    experiment_id: "exp-1",
    created_at: "2026-03-10T11:30:00+00:00",
    share_token: "token-abc",
    question: "Would you watch this at a Friday late show?",
    options: [
      { option_id: "opt-1", label: "Yes" },
      { option_id: "opt-2", label: "No" },
    ],
    hypothesis: "Artist-led framing reaches a late-show audience.",
    decision_rule: rule,
    opens_at: "2026-03-10T11:00:00+00:00",
    closes_at: "2026-03-24T11:00:00+00:00",
    closed_at: null,
    frozen_at: null,
    definition_frozen: false,
    response_count: 0,
    counts: {
      total: 0,
      unrecognised: 0,
      options: [
        { option_id: "opt-1", label: "Yes", count: 0, share: null },
        { option_id: "opt-2", label: "No", count: 0, share: null },
      ],
    },
    collection: {
      status: "OPEN",
      accepting_responses: true,
      reason: "Collection is open until 2026-03-24T11:00:00+00:00.",
    },
    latest_evaluation: null,
    ...overrides,
  };
}

const sharedOpen = {
  schema: "adjacent.audience-pulse/1",
  question: "Would you watch this at a Friday late show?",
  options: [
    { option_id: "opt-1", label: "Yes" },
    { option_id: "opt-2", label: "No" },
  ],
  opens_at: "2026-03-10T11:00:00+00:00",
  closes_at: "2026-03-24T11:00:00+00:00",
  collection: {
    status: "OPEN",
    accepting_responses: true,
    reason: "Collection is open until 2026-03-24T11:00:00+00:00.",
  },
  limitations: ["Respondents choose to open the link, so the sample is self-selected."],
  already_responded: false,
};

// ─── Draft validation ───────────────────────────────────────────────────────

test("a complete draft produces the payload the backend expects", () => {
  const result = validatePulseDraft(draft(), NOW);
  assert.equal(result.ok, true);
  assert.deepEqual(result.errors, {});
  assert.equal(result.payload.options.length, 3);
  assert.equal(result.payload.decision_rule.option_id, "opt-1");
  assert.equal(result.payload.decision_rule.threshold, 0.6);
  assert.equal(result.payload.decision_rule.min_responses, 10);
  // Timestamps carry a zone, because the backend rejects a naive one.
  assert.match(result.payload.opens_at, /Z$|\+00:00$/);
  assert.match(result.payload.closes_at, /Z$|\+00:00$/);
});

test("the rule option is taken from the option the creator picks", () => {
  const result = validatePulseDraft(draft({ ruleOptionIndex: 1 }), NOW);
  assert.equal(result.payload.decision_rule.option_id, "opt-2");
});

test("an empty question is refused", () => {
  const result = validatePulseDraft(draft({ question: "   " }), NOW);
  assert.equal(result.ok, false);
  assert.equal(result.payload, null);
  assert.match(result.errors.question, /one question/i);
});

test("questions and options are length-bounded", () => {
  const longQuestion = validatePulseDraft(draft({ question: "x".repeat(241) }), NOW);
  assert.equal(longQuestion.ok, false);
  assert.match(longQuestion.errors.question, /240/);

  const longOption = validatePulseDraft(
    draft({ options: ["Yes", "y".repeat(121)] }),
    NOW,
  );
  assert.equal(longOption.ok, false);
  assert.match(longOption.errors.options, /120/);
});

test("fewer than two options cannot be published", () => {
  const result = validatePulseDraft(draft({ options: ["Yes", "  "] }), NOW);
  assert.equal(result.ok, false);
  assert.match(result.errors.options, /at least 2/);
});

test("more than five options cannot be published", () => {
  const result = validatePulseDraft(
    draft({ options: ["a", "b", "c", "d", "e", "f"] }),
    NOW,
  );
  assert.equal(result.ok, false);
  assert.match(result.errors.options, /at most 5/);
});

test("duplicate options are refused instead of merged", () => {
  const result = validatePulseDraft(draft({ options: ["Yes", "yes"] }), NOW);
  assert.equal(result.ok, false);
  assert.match(result.errors.options, /duplicate/i);
});

test("a window that closes before it opens is refused", () => {
  const result = validatePulseDraft(
    draft({ opensAt: "2026-03-12T11:00", closesAt: "2026-03-11T11:00" }),
    NOW,
  );
  assert.equal(result.ok, false);
  assert.match(result.errors.closesAt, /close after it opens/);
});

test("a window shorter than an hour is refused", () => {
  const result = validatePulseDraft(
    draft({ opensAt: "2026-03-11T11:00", closesAt: "2026-03-11T11:30" }),
    NOW,
  );
  assert.equal(result.ok, false);
  assert.match(result.errors.closesAt, /at least 1 hour/);
});

test("a window longer than ninety days is refused", () => {
  const result = validatePulseDraft(
    draft({ opensAt: "2026-03-11T11:00", closesAt: later(120) }),
    NOW,
  );
  assert.equal(result.ok, false);
  assert.match(result.errors.closesAt, /within 90 days/);
});

test("a window that has already closed is refused", () => {
  const result = validatePulseDraft(
    draft({ opensAt: "2026-01-01T11:00", closesAt: "2026-02-01T11:00" }),
    NOW,
  );
  assert.equal(result.ok, false);
  assert.match(result.errors.closesAt, /still be open/);
});

test("the threshold must be a real share of responses", () => {
  assert.match(
    validatePulseDraft(draft({ thresholdPercent: 0 }), NOW).errors.thresholdPercent,
    /above 0%/,
  );
  assert.match(
    validatePulseDraft(draft({ thresholdPercent: 120 }), NOW).errors.thresholdPercent,
    /at most 100%/,
  );
});

test("the minimum sample cannot drop below the floor", () => {
  const result = validatePulseDraft(
    draft({ minResponses: PULSE_MIN_RESPONSES_FLOOR - 1 }),
    NOW,
  );
  assert.equal(result.ok, false);
  assert.match(result.errors.minResponses, /at least 5/);
});

test("the rule must name an option that exists", () => {
  const result = validatePulseDraft(draft({ ruleOptionIndex: 7 }), NOW);
  assert.equal(result.ok, false);
  assert.match(result.errors.ruleOptionIndex, /support the hypothesis/);
});

// ─── Participant states ────────────────────────────────────────────────────

test("the ballot is shown for an open poll", () => {
  const state = buildBallotState({ data: sharedOpen });
  assert.equal(state.kind, "open");
  assert.deepEqual(state.options.map((option) => option.label), ["Yes", "No"]);
  assert.match(state.window, /2026-03-10/);
  // Totals stay out of the payload while collection is open.
  assert.equal("counts" in state, false);
});

test("a browser that already answered is told so, not shown the ballot again", () => {
  const state = buildBallotState({ data: { ...sharedOpen, already_responded: true } });
  assert.equal(state.kind, "answered");
  assert.match(state.detail, /already answered/i);
  assert.equal("counts" in state, false);
});

test("a closed poll shows its stored totals", () => {
  const state = buildBallotState({
    data: {
      ...sharedOpen,
      collection: {
        status: "CLOSED",
        accepting_responses: false,
        reason: "Collection was closed by the owner.",
      },
      counts: {
        total: 12,
        options: [
          { option_id: "opt-1", label: "Yes", count: 8, share: 0.6667 },
          { option_id: "opt-2", label: "No", count: 4, share: 0.3333 },
        ],
      },
    },
  });
  assert.equal(state.kind, "closed");
  assert.equal(state.counts.total, 12);
  assert.equal(state.counts.options[0].count, 8);
});

test("a closed poll with no counts says so instead of showing zeroes", () => {
  const state = buildBallotState({
    data: {
      ...sharedOpen,
      collection: {
        status: "EXPIRED",
        accepting_responses: false,
        reason: "The collection window ended.",
      },
    },
  });
  assert.equal(state.kind, "closed");
  assert.equal(state.counts, null);
});

test("loading and failure are distinct states", () => {
  assert.equal(buildBallotState({ loading: true }).kind, "loading");

  const missing = buildBallotState({ status: 404, error: "This poll link is not valid." });
  assert.equal(missing.kind, "unavailable");
  assert.equal(missing.title, "This poll is not available");

  const disabled = buildBallotState({ status: 503, error: "Sharing is disabled." });
  assert.equal(disabled.kind, "unavailable");

  const broken = buildBallotState({ status: 500, error: "The poll request did not complete." });
  assert.equal(broken.kind, "error");
  assert.match(broken.detail, /did not complete/);
});

test("an empty payload never becomes a placeholder ballot", () => {
  const state = buildBallotState({ data: { ...sharedOpen, options: [] } });
  assert.equal(state.kind, "unavailable");
  assert.match(state.detail, /no ballot/i);
});

// ─── Owner view ────────────────────────────────────────────────────────────

test("a missing poll list is unavailable rather than empty", () => {
  const view = buildOwnerPulseView(null);
  assert.equal(view.available, false);
  assert.deepEqual(view.rows, []);
  assert.match(view.reason, /not returned/);
});

test("an experiment with no polls reads as no polls", () => {
  const view = buildOwnerPulseView({ schema: "x", sharing_enabled: true, polls: [] });
  assert.equal(view.available, true);
  assert.deepEqual(view.rows, []);
  assert.equal(view.sharingEnabled, true);
});

test("a deployment with sharing off is reported, not hidden", () => {
  const view = buildOwnerPulseView({ schema: "x", sharing_enabled: false, polls: [] });
  assert.equal(view.sharingEnabled, false);
});

test("poll rows carry the rule, the window and the stored headline", () => {
  const view = buildOwnerPulseView({
    schema: "x",
    sharing_enabled: true,
    polls: [
      {
        poll: poll({
          definition_frozen: true,
          response_count: 12,
          counts: {
            total: 12,
            unrecognised: 0,
            options: [
              { option_id: "opt-1", label: "Yes", count: 8, share: 0.6667 },
              { option_id: "opt-2", label: "No", count: 4, share: 0.3333 },
            ],
          },
        }),
        share_path: "/pulse/token-abc",
      },
    ],
  });
  const row = view.rows[0];
  assert.equal(row.pollId, "poll-1");
  assert.equal(row.frozen, true);
  assert.equal(row.collectionStatus, "OPEN");
  assert.equal(row.sharePath, "/pulse/token-abc");
  assert.match(row.ruleStatement, /SUPPORTED when 60%/);
  assert.match(row.window, /2026-03-10 11:00 UTC → 2026-03-24 11:00 UTC/);
  assert.match(row.headline, /12 responses recorded/);
  assert.match(row.headline, /“Yes” \(8 of 12, 67%\)/);
});

test("a poll with no responses is reported as zero, not as missing", () => {
  const view = buildOwnerPulseView({
    schema: "x",
    sharing_enabled: true,
    polls: [{ poll: poll(), share_path: "/pulse/token-abc" }],
  });
  assert.match(view.rows[0].headline, /0 responses recorded/);
  assert.match(view.rows[0].headline, /empty poll, not missing data/);
});

// ─── Formatting and language ───────────────────────────────────────────────

test("shares format as whole percentages, or as an explicit dash", () => {
  assert.equal(formatShare(0.6667), "67%");
  assert.equal(formatShare(1), "100%");
  assert.equal(formatShare(null), "—");
  assert.equal(formatShare(undefined), "—");
  assert.equal(formatShare(Number.NaN), "—");
});

test("timestamps render in UTC so the window means one thing", () => {
  assert.equal(formatPulseTime("2026-03-10T11:00:00+00:00"), "2026-03-10 11:00 UTC");
  assert.equal(formatPulseTime(null), "—");
  assert.equal(formatPulseTime("not-a-date"), "—");
  assert.match(
    formatPulseWindow("2026-03-10T11:00:00Z", "2026-03-24T11:00:00Z"),
    /2026-03-10 11:00 UTC → 2026-03-24 11:00 UTC/,
  );
});

test("collection and outcome wording never overstates the evidence", () => {
  assert.deepEqual(describeCollection(sharedOpen.collection).label, "Collecting responses");
  assert.equal(describeCollection(null).tone, "warn");
  assert.equal(describeOutcome("SUPPORTED").tone, "live");
  assert.equal(describeOutcome("INCONCLUSIVE").label, "Inconclusive");
  assert.match(describeOutcome("INCONCLUSIVE").explanation, /could not decide/);
  assert.equal(describeOutcome(null).label, "Not evaluated");

  const text = [
    describeCollection(sharedOpen.collection).detail,
    describeOutcome("SUPPORTED").explanation,
    describeOutcome("INCONCLUSIVE").explanation,
    describeOutcome(null).explanation,
    summariseCounts(poll().counts),
  ]
    .join(" ")
    .toLowerCase();
  for (const forbidden of ["probability", "confidence", "statistical", "predicted attendance"]) {
    assert.equal(text.includes(forbidden), false, `wording leaked "${forbidden}"`);
  }
});

test("an empty poll has no distribution bars to draw", () => {
  const rows = distributionRows(poll().counts);
  assert.deepEqual(
    rows.map((row) => row.widthPercent),
    [0, 0],
  );
  assert.deepEqual(distributionRows(null), []);
});

test("distribution bars use the stored shares", () => {
  const rows = distributionRows({
    total: 4,
    unrecognised: 0,
    options: [
      { option_id: "opt-1", label: "Yes", count: 3, share: 0.75 },
      { option_id: "opt-2", label: "No", count: 1, share: 0.25 },
    ],
  });
  assert.deepEqual(
    rows.map((row) => row.widthPercent),
    [75, 25],
  );
});

test("an unevaluated poll is not described as a verdict", () => {
  assert.match(evaluationLine(null), /No evaluation recorded/);
  assert.match(evaluationLine(null), /not a verdict/);
  assert.match(evaluationLine(evaluation()), /Inconclusive/);
});

test("the remaining-evidence line does the arithmetic it claims", () => {
  assert.equal(
    remainingEvidenceLine(evaluation({ sample_size: 4 })),
    "6 more valid response(s) would let the pre-registered rule decide.",
  );
  assert.equal(remainingEvidenceLine(evaluation({ sample_size: 10 })), "");
  assert.equal(remainingEvidenceLine(evaluation({ outcome: "SUPPORTED" })), "");
  assert.equal(remainingEvidenceLine(null), "");
});

test("request failures map to actionable text, with the deployment reason preserved", () => {
  assert.equal(pulseErrorMessage(422, "options must be a list"), "options must be a list");
  assert.match(pulseErrorMessage(503, null), /ADJACENT_PULSE_SHARE_ENABLED=1/);
  assert.match(pulseErrorMessage(404, { message: "nested detail" }), /not on this deployment/);
  assert.match(pulseErrorMessage(429, null), /too many responses/i);
  assert.match(pulseErrorMessage(500, null), /Nothing was recorded/);
});

test("unmatched responses are surfaced instead of folded into an option", () => {
  const text = summariseCounts({
    total: 3,
    unrecognised: 2,
    options: [{ option_id: "opt-1", label: "Yes", count: 1, share: 1 / 3 }],
  });
  assert.match(text, /2 unmatched response/);
});

test("an evaluation key changes only when the rule would read something new", () => {
  const base = {
    pollId: "poll-1",
    counts: { total: 4, unrecognised: 0, options: [] },
    collectionStatus: "OPEN",
  };
  assert.deepEqual(evaluationRequestSeed(base), {
    poll: "poll-1",
    sample: 4,
    collected: "OPEN",
  });
  // A double click, or a reload, resolves to the same stored evaluation.
  assert.deepEqual(evaluationRequestSeed({ ...base }), evaluationRequestSeed(base));
  // New responses, or a closed window, are a different evaluation.
  assert.notDeepEqual(
    evaluationRequestSeed({ ...base, counts: { ...base.counts, total: 5 } }),
    evaluationRequestSeed(base),
  );
  assert.notDeepEqual(
    evaluationRequestSeed({ ...base, collectionStatus: "CLOSED" }),
    evaluationRequestSeed(base),
  );
});
