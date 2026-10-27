import assert from "node:assert/strict";
import test from "node:test";

/**
 * Comparables Audit — view-model contract.
 *
 * The one thing this view must never do is turn "Qloo returned no field this
 * build can read" into "these two films are unrelated". These tests pin the
 * wording of every non-measured state, plus the trace fields a sceptical reader
 * needs to check the row against the run.
 */

const { buildComparablesView, comparablesRow } = await import("../lib/comparables.ts");

const film = (title, index) => ({
  title,
  year: 2000 + index,
  entity_id: `urn:entity:movie:${index}`,
  resolved_name: title,
  entity_type: "urn:entity:movie",
  resolution_call_id: `resolve-${index}`,
});

const pair = (overrides = {}) => ({
  a: film("Perfect Days", 0),
  b: film("The Zone of Interest", 1),
  status: "measured",
  reason: "Qloo reported overlap = 0.420 between Perfect Days and The Zone of Interest.",
  metric: { key: "overlap", value: 0.42, direction: "higher_is_closer", source: "provider_reported" },
  call_id: "compare-1",
  observed_keys: [],
  ...overrides,
});

const audit = (overrides = {}) => ({
  schema: "adjacent.comparables-audit/1",
  data_status: "measured",
  available: true,
  status: "evaluated",
  reason: "2 reference pair(s) attempted; 1 returned a value this build can read.",
  summary: {
    resolved_references: 3,
    unresolved_references: 1,
    pairs_considered: 3,
    pairs_attempted: 2,
    pairs_measured: 1,
  },
  pairs: [pair(), pair({ status: "no_readable_field", metric: null, call_id: "compare-2", observed_keys: ["lift"] })],
  unresolved_references: [{ title: "An Unreleased Short", year: 2024 }],
  not_evaluated: [{ a: "A", b: "B", status: "not_evaluated_limit", reason: "bounded" }],
  not_evaluated_count: 4,
  max_pairs: 3,
  limits: ["A pair with no readable value is unevaluated, not refuted."],
  ...overrides,
});

test("a measured pair shows the provider key, its direction and the compare call", () => {
  const view = buildComparablesView(audit());
  const row = view.rows[0];

  assert.equal(row.status, "measured");
  assert.equal(row.statusLabel, "Measured");
  assert.equal(row.tone, "live");
  assert.match(row.metric, /overlap 0\.420/);
  assert.match(row.metric, /higher = more overlap/);
  assert.equal(row.callId, "compare-1");
  assert.deepEqual(row.resolutionCallIds, ["resolve-0", "resolve-1"]);
  assert.equal(row.pair, "Perfect Days · The Zone of Interest");
  // Panel-level summary names how many pairs actually returned a value.
  assert.equal(view.summary, "2 pairs compared, 1 returned a readable value.");
});

test("a pair with no readable field is unevaluated and never called unrelated", () => {
  const row = comparablesRow(
    pair({
      status: "no_readable_field",
      metric: null,
      call_id: "compare-2",
      observed_keys: ["lift", "results"],
      reason:
        "Qloo answered, but the response carried no numeric field this build is willing to interpret. The pair is unevaluated — not refuted.",
    }),
    1,
  );

  assert.equal(row.statusLabel, "Unevaluated · no readable field");
  assert.equal(row.tone, "neutral");
  assert.equal(row.metric, null);
  assert.deepEqual(row.observedKeys, ["lift", "results"]);
  assert.match(row.detail, /not refuted/);
  assert.doesNotMatch(row.detail, /unrelated|false/i);
});

test("provider failure and the fixture state read differently", () => {
  const failure = comparablesRow(
    pair({ status: "failed", metric: null, call_id: null, reason: "The comparison call did not complete." }),
    0,
  );
  assert.equal(failure.tone, "fail");
  assert.equal(failure.statusLabel, "Upstream failure");

  const fixture = comparablesRow(
    pair({ status: "not_modelled_in_fixture", metric: null, reason: "The labelled fixture run does not model this." }),
    0,
  );
  assert.equal(fixture.tone, "fixture");
  assert.match(fixture.statusLabel, /fixture/i);
});

test("budget refusal is a warning with no number", () => {
  const row = comparablesRow(
    pair({ status: "unavailable_budget", metric: null, call_id: null, reason: "Budget." }),
    0,
  );
  assert.equal(row.tone, "warn");
  assert.equal(row.metric, null);
});

test("insufficient input reports the backend reason instead of an empty list", () => {
  const view = buildComparablesView(
    audit({
      status: "insufficient_input",
      available: false,
      reason: "The audit needs at least two resolved reference films to compare. This run resolved 1.",
      pairs: [],
      summary: { resolved_references: 1, unresolved_references: 0, pairs_considered: 0, pairs_attempted: 0, pairs_measured: 0 },
    }),
  );

  assert.equal(view.available, false);
  assert.equal(view.status, "insufficient_input");
  assert.match(view.statement, /at least two resolved reference films/);
  assert.deepEqual(view.rows, []);
});

test("unresolved references and bounded-out pairs are both disclosed", () => {
  const view = buildComparablesView(audit());
  assert.deepEqual(view.unresolved, ["An Unreleased Short (2024)"]);
  assert.deepEqual(view.notEvaluated, ["A · B"]);
});

test("a missing audit is reported as not run, with nothing inferred", () => {
  const view = buildComparablesView(null);
  assert.equal(view.available, false);
  assert.equal(view.status, "missing");
  assert.equal(view.headline, "Not run");
  assert.match(view.statement, /Nothing is inferred/);
  assert.deepEqual(view.rows, []);
});

test("a fixture audit is toned as a fixture even when pairs exist", () => {
  const view = buildComparablesView(
    audit({
      data_status: "fixture",
      pairs: [pair({ status: "not_modelled_in_fixture", metric: null, reason: "Fixture." })],
      summary: { resolved_references: 2, unresolved_references: 0, pairs_considered: 1, pairs_attempted: 1, pairs_measured: 0 },
    }),
  );
  assert.equal(view.tone, "fixture");
  assert.match(view.headline, /no readable value/i);
});
