import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { formatTestCardText, safeTextFilename } from "../lib/testCardExport.ts";

const cinemaSource = readFileSync(new URL("../app/cinema/page.tsx", import.meta.url), "utf8");
const graphSource = readFileSync(new URL("../components/AdjacencyGraph.tsx", import.meta.url), "utf8");

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


test("cultural fingerprint renders orbit guides and inspectable member nodes", () => {
  assert.match(graphSource, /className="agraph-orbit agraph-orbit-inner"/);
  assert.match(graphSource, /className="agraph-orbit agraph-orbit-outer"/);
  assert.match(graphSource, /activeMember = memberNodes\.find/);
  assert.match(graphSource, /setSelected\(isSelected \? null : member\.key\)/);
  assert.match(graphSource, /Entity affinity/);
  assert.match(graphSource, /agraph-center-halo/);
});
