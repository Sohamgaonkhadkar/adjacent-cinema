import assert from "node:assert/strict";
import test from "node:test";

/**
 * Decision Challenge — view-model contract.
 *
 * These tests run the real formatter over payloads shaped like the backend's.
 * They exist because the one thing a challenge view must never do is sound more
 * certain than its evidence: an unavailable payload has to read as unavailable,
 * a fragile verdict has to read as fragile, and a downloaded receipt has to
 * carry its data status and its limits.
 */

const { buildChallengeView, formatDecisionReceipt, challengeExportSections, toneForStatus, pairwiseRow } =
  await import("../lib/challengeView.ts");

const fixtureChallenge = {
  schema: "adjacent.decision-challenge/1",
  available: true,
  unavailable_reason: null,
  data_status: "fixture",
  recommendation: { cohort_id: "urn:entity:artist:tag_cluster:1", label: "artist · Brian Eno" },
  necessity_statement:
    "With Qloo's affinity numbers removed, the recommendation is still artist · Brian Eno.",
  necessity: {
    method: "two counterfactuals",
    qloo_calls_made: 0,
    pool_size: 3,
    affinity_withheld: {
      production_winner: "urn:entity:artist:tag_cluster:1",
      counterfactual_winner: "urn:entity:artist:tag_cluster:1",
      winner_changed: false,
      moves: [],
      ranks_moved: 0,
      changed_below_first: false,
      dropped_out: [],
      entered: [],
      order: [
        { cohort_id: "urn:entity:artist:tag_cluster:1", label: "artist · Brian Eno" },
        { cohort_id: "urn:entity:book:subtype:nonfiction:1", label: "book · A Field Guide" },
      ],
      ordering_keys: ["novelty_proxy"],
      removed_keys: ["evidence_strength"],
      top_pair_tied_without_affinity: false,
      runner_up: "urn:entity:book:subtype:nonfiction:1",
    },
    popularity_only: {
      production_winner: "urn:entity:artist:tag_cluster:1",
      counterfactual_winner: "urn:entity:movie:subtype:documentary:2",
      winner_changed: true,
      moves: [],
      ranks_moved: 0,
      changed_below_first: false,
      dropped_out: [],
      entered: [],
      order: [
        { cohort_id: "urn:entity:movie:subtype:documentary:2", label: "movie · Baraka" },
        { cohort_id: "urn:entity:artist:tag_cluster:1", label: "artist · Brian Eno" },
      ],
      ordering_keys: ["median_popularity"],
    },
    affinity_decided_pairs: [],
    adjacent_pairs_examined: 2,
    gate: {
      admitted_with_affinity_gate: ["urn:entity:artist:tag_cluster:1"],
      structurally_admitted: ["urn:entity:artist:tag_cluster:1", "urn:entity:brand:domain_group:7"],
      suppressed_by_affinity_gate: [
        { cohort_id: "urn:entity:brand:domain_group:7", label: "brand · Everyday Objects" },
      ],
      admitted_without_structural_support: [],
    },
    production_order: ["urn:entity:artist:tag_cluster:1"],
  },
  stability: {
    verdict: "fragile",
    reason: "2 of 3 single-item removals change the recommendation",
    rule: "Fragile if any single removable evidence item changes the winning cohort.",
    evaluated: 3,
    skipped: [
      {
        cohort_id: "urn:entity:artist:tag_cluster:1",
        entity_id: "e-solo",
        name: "Solo",
        reason: "the cohort would have no scored members left",
      },
    ],
    flips: [
      {
        removed: {
          entity_id: "e-grouper",
          name: "Grouper",
          affinity: 0.71,
          band: "high",
          popularity: 0.24,
          call_id: "call-1",
        },
        removed_from: {
          cohort_id: "urn:entity:artist:tag_cluster:1",
          label: "artist · Brian Eno",
          call_id: "call-1",
        },
        winner_after: "urn:entity:book:subtype:nonfiction:1",
        winner_after_label: "book · A Field Guide",
      },
    ],
    scenarios: [
      {
        removed: {
          entity_id: "e-grouper",
          name: "Grouper",
          affinity: 0.71,
          band: "high",
          popularity: 0.24,
          call_id: "call-1",
        },
        removed_from: {
          cohort_id: "urn:entity:artist:tag_cluster:1",
          label: "artist · Brian Eno",
          call_id: "call-1",
        },
        cohort_still_admitted: true,
        winner_after: "urn:entity:book:subtype:nonfiction:1",
        winner_after_label: "book · A Field Guide",
        winner_changed: true,
        order_after: ["urn:entity:book:subtype:nonfiction:1"],
      },
      {
        removed: {
          entity_id: "e-basinski",
          name: "William Basinski",
          affinity: 0.64,
          band: "high",
          popularity: 0.21,
          call_id: "call-1",
        },
        removed_from: {
          cohort_id: "urn:entity:artist:subtype:composer:1",
          label: "artist · Hildur",
          call_id: "call-1",
        },
        cohort_still_admitted: true,
        winner_after: "urn:entity:artist:tag_cluster:1",
        winner_changed: false,
        order_after: ["urn:entity:artist:tag_cluster:1"],
      },
    ],
    member_scope: "Each scored member of each ranked cohort, removed one at a time.",
  },
  next_checks: [
    {
      id: "fragile_decision",
      title: "One evidence item is holding the recommendation up",
      detail: "Removing Grouper changes the winner.",
      uncertainty_addressed: "whether the recommendation is a property of the programme",
      proposed_check: {
        action: "Check that entity's fit with the venue before screening.",
        operation: "rank_cohorts",
        estimated_qloo_calls: 1,
        available_now: true,
        unavailable_reason: "",
      },
      evidence_call_ids: ["call-1"],
    },
  ],
  counts: {
    cohorts_ranked: 3,
    cohorts_rejected: 2,
    evidence_items_tested: 3,
    qloo_calls_made: 0,
  },
  receipt: {
    schema: "adjacent.decision-challenge/1",
    run_id: "run-1",
    data_status: "fixture",
    recommendation: {
      cohort_id: "urn:entity:artist:tag_cluster:1",
      domain: "urn:entity:artist",
      kind: "tag_cluster",
      label: "artist · Brian Eno",
      member_names: ["Brian Eno", "Grouper"],
      mean_affinity: 0.713333,
      novelty_proxy: 0.76,
      strength: "strong",
      call_id: "call-1",
      construction_reason: "shared Qloo tags",
    },
    basis: { ordering_keys: ["evidence_strength"], affinity_decided_pairs: 0, adjacent_pairs_examined: 2 },
    necessity: {
      winner_without_affinity: "urn:entity:artist:tag_cluster:1",
      affinity_changed_winner: false,
      ranks_moved_without_affinity: 0,
      popularity_only_winner: "urn:entity:movie:subtype:documentary:2",
      popularity_would_differ: true,
    },
    stability: { verdict: "fragile", reason: "2 of 3 single-item removals change the recommendation", evaluated: 3, flips: 1 },
    next_checks: [{ id: "fragile_decision", title: "One evidence item is holding the recommendation up" }],
    limits: ["Cultural affinity is a Qloo taste measurement. It is not attendance."],
    call_ids: ["call-1"],
  },
  limits: ["Cultural affinity is a Qloo taste measurement. It is not attendance."],
};

test("a null challenge is reported as not calculated, never as reassurance", () => {
  const view = buildChallengeView(null);
  assert.equal(view.available, false);
  assert.match(view.headline, /Not calculated/);
  assert.match(view.unavailableReason, /Nothing is inferred/);
  assert.equal(view.receipt, null);
  assert.deepEqual(view.necessityRows, []);
});

test("an explicitly unavailable challenge keeps the backend's reason", () => {
  const view = buildChallengeView({
    ...fixtureChallenge,
    available: false,
    unavailable_reason: "This run produced no candidate cohorts.",
    necessity: null,
    stability: null,
    receipt: null,
  });
  assert.equal(view.available, false);
  assert.match(view.unavailableReason, /no candidate cohorts/);
});

test("a fragile verdict leads the stability rows", () => {
  const view = buildChallengeView(fixtureChallenge);
  assert.equal(view.stabilityVerdict, "fragile");
  assert.equal(view.headline, "Fragile recommendation");
  assert.match(view.stabilityRows[0].detail, /load-bearing/);
  assert.match(view.stabilityRows[0].detail, /Grouper/);
  // The non-flip row is still shown, so the reader sees what did not matter.
  assert.ok(view.stabilityRows.some((row) => /leaves the recommendation unchanged/.test(row.detail)));
});

test("necessity rows name the mainstream baseline difference", () => {
  const view = buildChallengeView(fixtureChallenge);
  const baseline = view.necessityRows.find((row) => row.id === "popularity-baseline");
  assert.ok(baseline);
  assert.match(baseline.label, /mainstream baseline would recommend something else/);
  assert.match(baseline.detail, /movie · Baraka/);
});

test("a top-pair tie is stated as a tie, not as a stable winner", () => {
  const tied = {
    ...fixtureChallenge,
    necessity: {
      ...fixtureChallenge.necessity,
      affinity_withheld: { ...fixtureChallenge.necessity.affinity_withheld, top_pair_tied_without_affinity: true },
    },
  };
  const view = buildChallengeView(tied);
  const tie = view.necessityRows.find((row) => row.id === "tie");
  assert.ok(tie);
  assert.match(tie.label, /indistinguishable/);
  assert.equal(tie.tone, "warn");
});

test("suppressed candidate groupings are named, not silently dropped", () => {
  const view = buildChallengeView(fixtureChallenge);
  const suppressed = view.necessityRows.find((row) => row.id === "suppressed");
  assert.ok(suppressed);
  assert.match(suppressed.label, /held back by the affinity threshold/);
  // The reader gets the cohort's own label, not the identifier behind it.
  assert.match(suppressed.detail, /brand · Everyday Objects/);
  assert.doesNotMatch(suppressed.detail, /urn:/);
});

test("no reader-facing text ever prints a raw cohort identifier", () => {
  const view = buildChallengeView(fixtureChallenge);
  const lines = [
    ...view.necessityRows.map((row) => `${row.label} ${row.detail}`),
    ...view.stabilityRows.map((row) => `${row.label} ${row.detail}`),
    view.stabilityReason,
    view.statement ?? "",
    formatDecisionReceipt(fixtureChallenge),
  ];
  for (const line of lines) {
    assert.doesNotMatch(line, /urn:entity:/, line);
    assert.doesNotMatch(line, /\(s\)/, line);
  }
});

test("an unresolvable cohort is described, never shown as a bare identifier", () => {
  const orphaned = {
    ...fixtureChallenge,
    stability: {
      ...fixtureChallenge.stability,
      flips: [
        {
          ...fixtureChallenge.stability.flips[0],
          winner_after: "urn:entity:artist:tag_cluster:99",
          winner_after_label: null,
        },
      ],
      scenarios: [],
    },
  };
  const view = buildChallengeView(orphaned);
  assert.ok(view.stabilityRows.length > 0);
  assert.doesNotMatch(view.stabilityRows[0].detail, /urn:entity:/);
});

test("skipped items are surfaced with their reason", () => {
  const view = buildChallengeView(fixtureChallenge);
  assert.equal(view.skipped.length, 1);
  assert.match(view.skipped[0].text, /could not|was not tested/i);
  assert.match(view.skipped[0].text, /no scored members left/);
});

test("the receipt renders its data status and limits", () => {
  const text = formatDecisionReceipt(fixtureChallenge);
  assert.match(text, /DECISION RECEIPT/);
  assert.match(text, /Data status: FIXTURE/);
  assert.match(text, /LIMITATIONS/);
  assert.match(text, /not attendance/);
  assert.match(text, /STABILITY/);
  assert.match(text, /FRAGILE/);
  assert.match(text, /call-1/);
});

test("the receipt for a missing challenge says so instead of printing a blank one", () => {
  const text = formatDecisionReceipt(null);
  assert.match(text, /No receipt is available/);
  assert.doesNotMatch(text, /Data status: LIVE/);
});

test("the receipt never claims a probability or attendance figure", () => {
  const text = formatDecisionReceipt(fixtureChallenge).toLowerCase();
  for (const banned of ["probability", "confidence interval", "attendance estimate", "success rate", "conversion rate"]) {
    assert.equal(text.includes(banned), false, `receipt must not mention ${banned}`);
  }
});

test("the exported test card carries the stability finding", () => {
  const sections = challengeExportSections(fixtureChallenge);
  assert.ok(sections.some((section) => /Decision stability/.test(section.label)));
  assert.ok(sections.some((section) => /not a probability/i.test(section.label)));
  assert.ok(sections.some((section) => /popularity-only baseline/.test(section.label)));
  assert.ok(sections.some((section) => /Investigate before screening/.test(section.label)));
});

test("nothing is appended to an export when no challenge exists", () => {
  assert.deepEqual(challengeExportSections(null), []);
  assert.deepEqual(
    challengeExportSections({ ...fixtureChallenge, available: false, receipt: null }),
    [],
  );
});

test("the backend's degraded record renders as unavailable, not as a result", () => {
  // Shape emitted by routes._build_challenge when the challenge itself throws:
  // every computed section is explicitly null, and an error diagnostic is attached.
  const degraded = {
    schema: "adjacent.decision-challenge/1",
    available: false,
    unavailable_reason:
      "The decision challenge could not be computed for this run. The analysis above is unaffected.",
    error: "RuntimeError",
    data_status: "fixture",
    necessity: null,
    stability: null,
    next_checks: [],
    receipt: null,
  };

  const view = buildChallengeView(degraded);
  assert.equal(view.available, false);
  assert.equal(view.headline, "Not calculated");
  assert.match(view.unavailableReason, /could not be computed/);
  assert.equal(view.receipt, null);
  assert.deepEqual(view.checks, []);
  // Nothing is invented for the missing sections.
  assert.equal(view.necessityRows.length, 1);
  assert.match(view.necessityRows[0].label, /Not calculated/);
  assert.equal(view.stabilityVerdict, "undetermined");
  const receipt = formatDecisionReceipt(degraded);
  assert.match(receipt, /No receipt is available/);
  assert.doesNotMatch(receipt, /RECOMMENDATION/);
  assert.doesNotMatch(receipt, /Data status: LIVE/);
  assert.deepEqual(challengeExportSections(degraded), []);
});

test("data status maps to the same chip tones the rest of the product uses", () => {
  assert.equal(toneForStatus("measured"), "live");
  assert.equal(toneForStatus("fixture"), "fixture");
  assert.equal(toneForStatus("insufficient"), "warn");
  assert.equal(toneForStatus("failed"), "fail");
  assert.equal(toneForStatus(undefined), "neutral");
});

// ─── Pairwise comparison (`/v2/analysis/compare`) ───────────────────────────
// The response schema is not modelled by the backend, so the UI may only ever
// print a value the payload actually carried. These tests pin that boundary.

const measuredPairwise = {
  schema: "adjacent.pairwise-comparison/1",
  data_status: "measured",
  available: true,
  status: "measured",
  reason: "",
  metric: { key: "overlap", value: 0.6314, direction: "higher_is_closer", source: "provider_reported" },
  cohorts: {
    a: {
      cohort_id: "urn:entity:artist:tag_cluster:1",
      domain: "urn:entity:artist",
      rank: 1,
      label: "artist · Brian Eno",
      member_count: 4,
      entity_ids: ["urn:entity:artist:eno"],
      member_names: ["Brian Eno"],
      truncated: false,
    },
    b: {
      cohort_id: "urn:entity:artist:subtype:composer:1",
      domain: "urn:entity:artist",
      rank: 3,
      label: "artist · Hildur Gudnadottir",
      member_count: 3,
      entity_ids: ["urn:entity:artist:gud"],
      member_names: ["Hildur Gudnadottir"],
      truncated: false,
    },
  },
  call_id: "compare-call-1",
  observed_keys: [],
  limits: [],
};

test("a measured comparison is printed with its key, direction and call id", () => {
  const row = pairwiseRow(measuredPairwise);
  assert.equal(row.tone, "live");
  assert.match(row.label, /Brian Eno vs artist · Hildur Gudnadottir/);
  assert.match(row.detail, /overlap = 0\.631/);
  assert.match(row.detail, /higher means the two groups overlap more/);
  assert.match(row.detail, /not a forecast of/);
  assert.equal(row.callId, "compare-call-1");

  const view = buildChallengeView({ ...fixtureChallenge, pairwise: measuredPairwise });
  assert.deepEqual(view.pairwise, row);

  const receipt = formatDecisionReceipt({ ...fixtureChallenge, pairwise: measuredPairwise });
  assert.match(receipt, /PAIRWISE COMPARISON/);
  assert.match(receipt, /overlap = 0\.631/);
});

test("an unrecognised response shape shows the refusal, never a number", () => {
  const refused = {
    ...measuredPairwise,
    available: false,
    status: "unsupported_response_shape",
    metric: null,
    reason:
      "The provider answered, but its response carried no numeric field this product is willing to interpret.",
    call_id: "compare-call-2",
  };
  const row = pairwiseRow(refused);
  assert.equal(row.tone, "neutral");
  assert.match(row.label, /No comparison value/);
  assert.match(row.detail, /no numeric field/);
  assert.doesNotMatch(row.detail, /\d\.\d{3}/);

  const receipt = formatDecisionReceipt({ ...fixtureChallenge, pairwise: refused });
  assert.match(receipt, /Status: unsupported_response_shape/);
  assert.doesNotMatch(receipt, /overlap =/);
});

test("a fixture run says the comparison is not modelled instead of implying a result", () => {
  const row = pairwiseRow({
    ...measuredPairwise,
    data_status: "fixture",
    available: false,
    status: "not_modelled_in_fixture",
    metric: null,
    reason: "The labelled fixture run does not model this comparison response.",
    call_id: "compare-call-3",
  });
  assert.match(row.label, /No comparison value/);
  assert.match(row.detail, /does not model/);
  assert.equal(row.callId, "compare-call-3");
});

test("a failed comparison is toned as a failure and keeps its call id", () => {
  const row = pairwiseRow({
    ...measuredPairwise,
    available: false,
    status: "failed",
    metric: null,
    reason: "The comparison call did not complete.",
    call_id: null,
  });
  assert.equal(row.tone, "fail");
  assert.equal(row.callId, null);
  assert.match(row.detail, /did not complete/);
});

test("no comparison payload means no section at all", () => {
  assert.equal(pairwiseRow(null), null);
  assert.equal(pairwiseRow(undefined), null);
  assert.equal(buildChallengeView({ ...fixtureChallenge, pairwise: undefined }).pairwise, null);
});

test("an unknown metric direction is not described as closeness", () => {
  const row = pairwiseRow({
    ...measuredPairwise,
    metric: { key: "overlap", value: 0.4, direction: "unknown", source: "provider_reported" },
  });
  assert.match(row.detail, /does not interpret the direction/);
  assert.doesNotMatch(row.detail, /overlap more/);
});
