import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  buildPositioningMultiverse,
  orderPositioningStrategies,
  readSavedPositioningSnapshot,
} from "../lib/positioningArena.ts";

function member(entityId, affinity, callId, tags = [], attribution = true) {
  return {
    entity_id: entityId,
    name: entityId.replace("entity-", ""),
    type: "urn:entity:artist",
    affinity,
    band: "high",
    popularity: 0.5,
    call_id: callId,
    tags: tags.map((tagId) => ({ tag_id: tagId, name: tagId === "tag-shared" ? "shared provider tag" : null })),
    qloo_attributions: attribution ? [{ entity_id: "seed-1", score: 0.4 }] : [],
    qloo_attribution_status: attribution ? "returned" : "missing",
  };
}

function sourceCohort({ id, domain, rank, mean, novelty, callId, entities, tag = "tag-shared", verdict = "strong" }) {
  return {
    cohort_id: id,
    domain,
    context_id: `ctx:${domain}`,
    rank,
    member_count: 2,
    qualifying_count: 2,
    verdict,
    score: { call_id: callId, context_id: `ctx:${domain}`, mean_affinity: mean, novelty_proxy: novelty },
    members: entities.map((entity, index) => member(entity, index ? mean - 0.03 : mean + 0.03, callId, tag ? [tag] : [])),
  };
}

function makeResult(overrides = {}) {
  const ranked = [
    sourceCohort({ id: "artist:anchor", domain: "urn:entity:artist", rank: 1, mean: 0.78, novelty: 0.2, callId: "score-artists", entities: ["entity-artist-1", "entity-artist-2"] }),
    sourceCohort({ id: "book:bridge", domain: "urn:entity:book", rank: 2, mean: 0.69, novelty: 0.45, callId: "score-books", entities: ["entity-book-1", "entity-book-2"] }),
    sourceCohort({ id: "artist:frontier", domain: "urn:entity:artist", rank: 3, mean: 0.63, novelty: 0.75, callId: "score-artists", entities: ["entity-artist-3", "entity-artist-4"], tag: "tag-other", verdict: "moderate" }),
  ];
  return {
    data_status: "measured",
    mode: "creator",
    film: { title: "Night Harbour", logline: "", genre: "drama", language: "English", release_goal: "" },
    programme: {
      items: [
        {
          title: "Verified Source Film",
          resolved: true,
          qloo_entity_id: "seed-1",
          qloo_name: "Verified Source Film",
          resolution_evidence: {
            qloo_entity_id: "seed-1",
            qloo_name: "Verified Source Film",
            match_status: "VERIFIED",
            call_id: "resolve-1",
            related_call_ids: [],
          },
        },
        { title: "Unresolved Reference", resolved: false, qloo_entity_id: null, resolution_evidence: { match_status: "UNRESOLVED", call_id: "resolve-miss", related_call_ids: [] } },
      ],
      resolved_count: 1,
      total_count: 2,
    },
    cohorts: { ranked, rejected: [], total_ranked: ranked.length, total_rejected: 0 },
    theme_inputs: [],
    test_card: null,
    programme_bet: null,
    evidence: { qloo_calls: 3, trace_rows: 3, stop_reason: "complete", stop_message: null },
    city: "",
    ...overrides,
  };
}

function makeTrace(dataStatus = "measured") {
  return ["resolve-1", "score-artists", "score-books"].map((call_id) => ({
    call_id,
    tool: "fixture-or-qloo-call",
    endpoint: "/v2/insights",
    data_status: dataStatus,
    source: dataStatus === "fixture" ? "mock" : "qloo",
  }));
}

function makeMultiverse(result = makeResult(), trace = makeTrace()) {
  return buildPositioningMultiverse(result, trace, "run-123", "completed");
}

test("fixed source evidence produces identical strategies and policy ordering", () => {
  const first = makeMultiverse();
  const second = makeMultiverse();
  assert.deepEqual(first, second);
  const policy = { fit: 50, exploration: 25, breadth: 25 };
  assert.deepEqual(orderPositioningStrategies(first, policy), orderPositioningStrategies(second, policy));
});

test("ANCHOR, BRIDGE, and FRONTIER use distinct evidence rules and candidates", () => {
  const multiverse = makeMultiverse();
  const [anchor, bridge, frontier] = multiverse.strategies;
  assert.deepEqual([anchor.type, bridge.type, frontier.type], ["ANCHOR", "BRIDGE", "FRONTIER"]);
  assert.ok([anchor, bridge, frontier].every((strategy) => strategy.availability === "available"));
  assert.deepEqual(anchor.source_cohort_ids, ["artist:anchor"]);
  assert.deepEqual(bridge.source_cohort_ids, ["artist:anchor", "book:bridge"]);
  assert.ok(bridge.evidence_refs.some((ref) => ref.kind === "shared_qloo_tag"));
  assert.deepEqual(frontier.source_cohort_ids, ["artist:frontier"]);
  assert.notDeepEqual(anchor.entity_refs.map((entity) => entity.entity_id), frontier.entity_refs.map((entity) => entity.entity_id));
  assert.match(frontier.why_selected, /higher existing novelty proxy/i);
  assert.equal(anchor.data_status, "measured");
  assert.deepEqual(anchor.evidence_challenge.attribution_statuses, ["returned"]);
  assert.match(anchor.creative_direction, /Verified Source Film/);
});

test("unsupported position types abstain with explicit reasons", () => {
  const noCohorts = makeMultiverse(makeResult({ cohorts: { ranked: [], rejected: [], total_ranked: 0, total_rejected: 0 } }));
  assert.ok(noCohorts.strategies.every((strategy) => strategy.availability === "unavailable"));
  assert.ok(noCohorts.strategies.every((strategy) => strategy.unavailable_reason?.length > 10));

  const noRelation = makeResult();
  noRelation.cohorts.ranked = noRelation.cohorts.ranked.map((cohort) => ({
    ...cohort,
    members: cohort.members.map((item) => ({ ...item, tags: [], qloo_attributions: [], qloo_attribution_status: "missing" })),
  }));
  const noBridge = makeMultiverse(noRelation);
  assert.equal(noBridge.strategies[1].availability, "unavailable");
  assert.match(noBridge.strategies[1].unavailable_reason, /no validated shared Qloo tag or per-seed attribution/i);

  const noFrontier = makeResult();
  noFrontier.cohorts.ranked[2].score.novelty_proxy = 0.2;
  const frontierAbstains = makeMultiverse(noFrontier);
  assert.equal(frontierAbstains.strategies[2].availability, "unavailable");
  assert.match(frontierAbstains.strategies[2].unavailable_reason, /higher.*novelty proxy/i);

  const separateContext = makeResult();
  separateContext.cohorts.ranked[2].context_id = "ctx:artist-other-query";
  separateContext.cohorts.ranked[2].score.context_id = "ctx:artist-other-query";
  const contextSeparated = makeMultiverse(separateContext);
  assert.equal(contextSeparated.strategies[2].availability, "unavailable");
  assert.equal(contextSeparated.strategies[0].dimensions.fit.comparison_group, "ctx:urn:entity:artist");

  const contextMismatch = makeResult();
  contextMismatch.cohorts.ranked[2].context_id = "ctx:artist-a";
  contextMismatch.cohorts.ranked[2].score.context_id = "ctx:artist-b";
  const mismatchAbstains = makeMultiverse(contextMismatch);
  assert.equal(mismatchAbstains.strategies[2].availability, "unavailable");
  assert.ok(!mismatchAbstains.strategies[2].source_cohort_ids.includes("artist:frontier"));
});

test("invalid scores, untraceable calls, and unresolved references cannot become candidates", () => {
  const invalid = makeResult();
  invalid.cohorts.ranked[0].members[0].affinity = 1.2;
  const untraceable = makeTrace().filter((row) => row.call_id !== "score-books");
  const output = makeMultiverse(invalid, untraceable);
  assert.equal(output.strategies[0].availability, "available");
  assert.ok(output.strategies[0].entity_refs.every((entity) => entity.affinity <= 1));
  assert.equal(output.strategies[1].availability, "unavailable");
  assert.ok(output.strategies[0].evidence_challenge.unresolved_references.some((value) => value.includes("Unresolved Reference")));
  assert.ok(!output.strategies[1].source_cohort_ids.includes("book:bridge"));

  const noTrace = makeMultiverse(makeResult(), []);
  assert.ok(noTrace.strategies.every((strategy) => strategy.availability === "unavailable"));
  assert.ok(noTrace.strategies.every((strategy) => strategy.evidence_refs.length === 0));
});

test("fixture source status remains fixture and unknown provenance abstains", () => {
  const fixture = makeResult({ data_status: "fixture" });
  const fixtureResult = makeMultiverse(fixture, makeTrace("fixture"));
  assert.equal(fixtureResult.data_status, "fixture");
  assert.ok(fixtureResult.strategies.filter((strategy) => strategy.availability === "available").every((strategy) => strategy.data_status === "fixture"));
  assert.ok(fixtureResult.source_limitations.some((limit) => /fixture data/i.test(limit)));

  const unknown = makeMultiverse(makeResult({ data_status: "unknown" }), makeTrace("measured"));
  assert.ok(unknown.strategies.every((strategy) => strategy.availability === "unavailable"));
  assert.equal(unknown.strategies[0].data_status, "unknown");
});

test("attribution and call references must match verified run inputs and trace", () => {
  const invalidRef = makeResult();
  invalidRef.cohorts.ranked = invalidRef.cohorts.ranked.map((cohort) => ({
    ...cohort,
    members: cohort.members.map((item) => ({
      ...item,
      tags: [],
      qloo_attributions: [{ entity_id: "invented-seed", score: 0.9 }],
      qloo_attribution_status: "returned",
    })),
  }));
  const multiverse = makeMultiverse(invalidRef);
  assert.equal(multiverse.strategies[1].availability, "unavailable");
  assert.ok(multiverse.strategies[0].evidence_challenge.supporting_call_ids.every((id) => makeTrace().some((row) => row.call_id === id)));
});

test("What-If priorities reorder preserved candidates without provider requests", () => {
  const multiverse = makeMultiverse();
  const candidatesBefore = JSON.stringify(multiverse.strategies);
  const fitFirst = orderPositioningStrategies(multiverse, { fit: 100, exploration: 0, breadth: 0 });
  const breadthFirst = orderPositioningStrategies(multiverse, { fit: 0, exploration: 0, breadth: 100 });
  assert.notDeepEqual(fitFirst.entries.map((item) => item.strategy_id), breadthFirst.entries.map((item) => item.strategy_id));
  assert.equal(JSON.stringify(multiverse.strategies), candidatesBefore);
  assert.match(breadthFirst.notes.join(" "), /no provider request/i);
  assert.throws(() => orderPositioningStrategies(multiverse, { fit: 101, exploration: 0, breadth: 0 }), RangeError);
  const source = readFileSync(new URL("../lib/positioningArena.ts", import.meta.url), "utf8");
  assert.doesNotMatch(source, /fetch\s*\(/);
});

test("strategy hypotheses are falsifiable test prompts, not audience forecasts", () => {
  const multiverse = makeMultiverse();
  for (const strategy of multiverse.strategies.filter((item) => item.availability === "available")) {
    assert.match(strategy.falsifiable_hypothesis, /primary action measure/i);
    assert.match(strategy.suggested_test.decision_rule, /filmmaker sets/i);
    assert.ok(!/will get \d+ views|attendance of \d+|revenue of \$|conversion probability/i.test(JSON.stringify(strategy)));
    assert.ok(strategy.tradeoffs.some((limit) => /not a forecast|not.*causal|not a success/i.test(limit)));
  }
});

test("legacy and new frozen snapshot payloads load without rewriting either", () => {
  const legacy = { primary: { cohort_id: "old-cohort" } };
  assert.equal(readSavedPositioningSnapshot(legacy), null);
  const snapshot = { snapshot_version: "cultural-positioning-snapshot-v1", selected_strategy_id: "frontier", policy: { values: { fit: 1, exploration: 2, breadth: 3 } } };
  const sourceBet = { cultural_multiverse_snapshot: snapshot };
  assert.deepEqual(readSavedPositioningSnapshot(sourceBet), snapshot);
  assert.deepEqual(sourceBet.cultural_multiverse_snapshot, snapshot);
});

test("Creator wires the frozen strategy into the existing experiment and Test Card lifecycle", () => {
  const creator = readFileSync(new URL("../app/creator/page.tsx", import.meta.url), "utf8");
  assert.match(creator, /<PositioningArena/);
  assert.match(creator, /cultural_multiverse_snapshot/);
  assert.match(creator, /selected_strategy_id/);
  assert.match(creator, /original_test_card/);
  assert.match(creator, /positioningOrdering\.formula_version/);
  assert.match(creator, /readSavedPositioningSnapshot/);
  assert.match(creator, /FROZEN CULTURAL POSITIONING/);
  assert.match(creator, /SAVED TEST DESIGN/);
});
