import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

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
