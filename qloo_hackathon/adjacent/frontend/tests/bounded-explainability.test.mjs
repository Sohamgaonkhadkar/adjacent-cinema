import assert from "node:assert/strict";
import test from "node:test";

/**
 * "Why this result?" — provider attribution, mapped back to the programme.
 *
 * Two failure modes are pinned here: printing a raw entity id as if it were a
 * film, and presenting the scoring call as the source of attribution that
 * actually came from the bounded follow-up.
 */

const { whyThisResult, seedTitles } = await import("../lib/attribution.ts");

const programme = {
  items: [
    { title: "Perfect Days", year: 2023, imdb_id: null, resolved: true, qloo_entity_id: "urn:entity:movie:0", qloo_name: "Perfect Days" },
    { title: "Roma", year: 2018, imdb_id: null, resolved: true, qloo_entity_id: "urn:entity:movie:1", qloo_name: "Roma" },
  ],
};

const member = (overrides = {}) => ({
  entity_id: "urn:entity:artist:eno",
  name: "Brian Eno",
  affinity: 0.81,
  band: "High",
  call_id: "scoring-call-1",
  qloo_attributions: [{ entity_id: "urn:entity:movie:0", score: 0.44 }],
  qloo_attribution_status: "returned_bounded",
  qloo_attribution_origin: "bounded",
  ...overrides,
});

test("seed ids are mapped to reference film titles", () => {
  const view = whyThisResult([member()], programme, {
    status: "returned",
    call_id: "bounded-call-1",
    members_updated: 1,
  });
  assert.equal(view.available, true);
  assert.equal(view.contributors[0].seeds[0].label, "Perfect Days");
  assert.equal(view.contributors[0].seeds[0].weight, 0.44);
  assert.equal(view.headline, "Explained by one bounded follow-up call");
});

test("bounded attribution cites the bounded call, not the scoring call", () => {
  const view = whyThisResult([member()], programme, { status: "returned", call_id: "bounded-call-1" });
  assert.equal(view.contributors[0].callId, "bounded-call-1");
  assert.match(view.note, /bounded follow-up/);
  assert.match(view.note, /still come from the original scoring call/);
});

test("inline attribution cites the scoring call", () => {
  const view = whyThisResult(
    [member({ qloo_attribution_origin: "scoring", qloo_attribution_status: "returned", call_id: "scoring-call-9" })],
    programme,
    { status: "not_needed", call_id: null },
  );
  assert.equal(view.contributors[0].callId, "scoring-call-9");
  assert.equal(view.headline, "Explained by the scoring call");
});

test("an unknown seed is never printed as an identifier", () => {
  const view = whyThisResult(
    [member({ qloo_attributions: [{ entity_id: "urn:entity:movie:999", score: 0.1 }] })],
    programme,
    { status: "returned", call_id: "bounded-call-1" },
  );
  assert.equal(view.contributors[0].seeds[0].label, "a reference this run did not resolve to a title");
  assert.doesNotMatch(JSON.stringify(view), /urn:entity:/);
});

test("no attribution is an explicit state, not a zero", () => {
  for (const status of ["missing", "failed", "unavailable_budget"]) {
    const view = whyThisResult([member({ qloo_attributions: [], qloo_attribution_origin: null, qloo_attribution_status: status })], programme, {
      status,
      call_id: null,
    });
    assert.equal(view.available, false, status);
    assert.equal(view.headline, "No provider explanation returned");
    assert.match(view.note, /Absence is not zero/);
    assert.deepEqual(view.contributors, []);
  }
});

test("members without attribution are ignored and never counted as zero", () => {
  const view = whyThisResult(
    [member({ entity_id: "urn:entity:artist:one", name: "One", qloo_attributions: [] }), member()],
    programme,
    { status: "returned", call_id: "bounded-call-1" },
  );
  assert.equal(view.contributors.length, 1);
  assert.equal(view.contributors[0].entityName, "Brian Eno");
  assert.match(view.limits.join(" "), /unknown, not zero/);
});

test("limits never describe a weight as audience size or a causal effect", () => {
  const view = whyThisResult([member()], programme, { status: "returned", call_id: "bounded-call-1" });
  const text = JSON.stringify(view).toLowerCase();
  assert.match(text, /not audience size/);
  assert.doesNotMatch(text, /attendance lift|predicted revenue|causal effect of/);
});

test("no programme resolves to an empty map rather than throwing", () => {
  assert.equal(seedTitles(null).size, 0);
  const view = whyThisResult([member()], null, { status: "returned", call_id: "bounded-call-1" });
  assert.equal(view.contributors[0].seeds[0].label, "a reference this run did not resolve to a title");
});
