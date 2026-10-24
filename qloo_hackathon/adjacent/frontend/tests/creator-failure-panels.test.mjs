import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { formatTestCardText, safeTextFilename } from "../lib/testCardExport.ts";
import { createTestDesign, readSavedTestDesign, testDesignExportSections, updateTestDesign } from "../lib/testCardDesign.ts";

const cinemaSource = readFileSync(new URL("../app/cinema/page.tsx", import.meta.url), "utf8");
const graphSource = readFileSync(new URL("../components/nf/CulturalFingerprint.tsx", import.meta.url), "utf8");

const source = readFileSync(new URL("../app/creator/page.tsx", import.meta.url), "utf8");

test("failed Creator runs keep investigation, fingerprint, and decision-brief steps navigable", () => {
  assert.match(source, /result \|\| \(failed && !analysing\)/);
  assert.match(source, /result\?\.cohorts \|\| \(failed && !analysing\)/);
  assert.match(source, /result\?\.investigation \|\| \(failed && !analysing\)/);

  assert.match(source, /id="analysis"[^>]*aria-labelledby="analysis-unavailable-title"/);
  assert.match(source, /id="fingerprint"[^>]*aria-labelledby="fingerprint-unavailable-title"/);
  assert.match(source, /id="brief"[^>]*aria-labelledby="brief-unavailable-title"/);

  assert.match(source, /The run failed before a structured investigation could be produced/);
  assert.match(source, /A fingerprint requires verified cultural cohorts/);
  assert.match(source, /The decision brief depends on the structured investigation above/);
  assert.match(source, /no substitute or fixture fingerprint is shown/);
});

test("creator mode supports end-to-end fixture mode submission and honest live mode error", () => {
  assert.match(source, /isFixtureMode/);
  assert.match(source, /createCreatorDemoRun\(payload\)/);
  assert.match(source, /createCreatorRun\(payload\)/);
  assert.match(source, /FIXTURE DEMO MODE ACTIVE/);
  assert.match(source, /Analyse cultural position \(fixture demo\)/);
});


test("Creator and Cinema offer a plain-text test card export", () => {
  assert.match(source, /className="test-card-export"/);
  assert.ok(source.includes("PLAIN TEXT · .TXT"));
  assert.match(cinemaSource, /className="test-card-export"/);

  const text = formatTestCardText({
    title: "Cinema × Contemporary Classical",
    context: "CINEMA: Sample House · London",
    dataStatus: "fixture",
    sections: [
      { label: "Audience hypothesis", value: "A composer-led event may invite a new conversation." },
      { label: "Empty field", value: "" },
    ],
    provenance: { call_id: "call-123", missing_value: null },
    footerNote: "Illustrative fixture, not live data.",
  });
  assert.match(text, /EXPERIMENT TEST CARD/);
  assert.match(text, /DATA STATUS: FIXTURE/);
  assert.match(text, /AUDIENCE HYPOTHESIS/);
  assert.match(text, /CALL ID: call-123/);
  assert.ok(text.includes("Illustrative fixture, not live data."));
  assert.ok(!text.includes('{"title"'));
  assert.ok(!text.includes("[object Object]"));
  assert.equal(safeTextFilename("Cinema × Contemporary Classical"), "cinema-contemporary-classical");
  assert.equal(safeTextFilename("!!!"), "adjacent-test-card");
});


test("Creator shows bounded Qloo seed attribution and a pre-registered experiment design", () => {
  assert.match(source, /qloo_attributions/);
  assert.match(source, /QLOO INPUT ATTRIBUTION/);
  assert.match(source, /not causal effects/);
  assert.match(source, /missing attribution is not a zero score/);
  assert.match(source, /Comparison protocol/);
  assert.match(source, /Primary measure and denominator/);
  assert.match(source, /Your decision rule \/ meaningful threshold/);
  assert.match(source, /card\.comparison_protocol/);
  assert.match(source, /card\.primary_measure/);
  assert.match(source, /card\.decision_rule/);
  assert.match(source, /card\.observation_window/);
  assert.match(source, /observation_window: experimentDesign\?\.observation_window/);
  assert.match(source, /\["Observation window", "observation_window"\]/);
  assert.match(source, /PERSONALISE THE TEST BEFORE SAVING/);
  assert.match(source, /included in the export and in a newly saved snapshot/);
  assert.match(source, /Saved test design · snapshot · not executed/i);
  assert.match(cinemaSource, /COMPARISON PROTOCOL · EDIT BEFORE EXPORT/);
  assert.match(cinemaSource, /PRIMARY MEASURE · EDIT BEFORE EXPORT/);
  assert.match(cinemaSource, /DECISION RULE · PROPOSED PROMPT, SET BEFORE SCREENING/);
  assert.match(cinemaSource, /OBSERVATION WINDOW · EDIT BEFORE EXPORT/);
});

test("edited Creator and Cinema design values flow through the shared export sections unchanged", () => {
  const generated = {
    comparison_protocol: "Generated comparison prompt",
    primary_measure: "Generated primary measure",
    decision_rule: "Generated instruction; no threshold supplied",
    observation_window: "Choose a fixed observation window before launch.",
  };
  let edited = createTestDesign(generated);
  edited = updateTestDesign(edited, generated, "comparison_protocol", "My cinema's observational baseline.");
  edited = updateTestDesign(edited, generated, "primary_measure", "Tickets sold / seats available, from box office report.");
  edited = updateTestDesign(edited, generated, "decision_rule", "Revisit only if the rate exceeds last season by 4 percentage points.");
  edited = updateTestDesign(edited, generated, "observation_window", "Review records from 1–14 November only.");

  const sections = testDesignExportSections(edited);
  const text = formatTestCardText({
    title: "Editable Test Card",
    dataStatus: "fixture",
    sections,
  });
  assert.deepEqual(sections.map(({ value }) => value), [
    "My cinema's observational baseline.",
    "Tickets sold / seats available, from box office report.",
    "Revisit only if the rate exceeds last season by 4 percentage points.",
    "Review records from 1–14 November only.",
  ]);
  for (const { value } of sections) assert.ok(text.includes(value));
  assert.ok(!text.includes("Generated comparison prompt"));
});

test("saved Creator design reopens verbatim and legacy snapshots degrade gracefully", () => {
  const values = {
    comparison_protocol: "Compare current programme with the saved baseline.",
    primary_measure: "Qualified ticket-page visits / eligible impressions.",
    decision_rule: "Review only after the preselected 3-point difference is observed.",
    observation_window: "1–14 November, fixed before release.",
  };
  assert.deepEqual(readSavedTestDesign({ experiment_design: values }), values);
  assert.deepEqual(readSavedTestDesign({ primary: { cohort_name: "legacy bet" } }, "Legacy 14-day window"), {
    comparison_protocol: null,
    primary_measure: null,
    decision_rule: null,
    observation_window: "Legacy 14-day window",
  });
});

test("cultural fingerprint renders orbit guides and inspectable member nodes", () => {
  assert.match(graphSource, /viewBox="0 0 100 100"/);
  assert.match(graphSource, /polar\(index, cohorts\.length, 28\)/);
  assert.match(graphSource, /polar\(index, entities\.length, 42/);
  assert.match(graphSource, /className="graph-node"/);
  assert.match(graphSource, /setSelectedId\(entity\.id\)/);
  assert.match(graphSource, /Source call · \{selected\.sourceCallId\}/);
  assert.match(graphSource, /cultural similarity, not audience size/);
});


test("cultural fingerprint includes the reading key beneath the graph", () => {
  assert.match(graphSource, /Reading key/);
  assert.match(graphSource, /Programme anchor/);
  assert.match(graphSource, /Cultural connection/);
  assert.match(graphSource, /Position is layout, not a hidden score/);
  assert.match(graphSource, /parent cohorts/);
});
