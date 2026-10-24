import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { previewIndex, strategies, suggestStrategy } from "../lib/nightfallMultiverseData.ts";

const component = await readFile(new URL("../components/HomeMultiversePreview.tsx", import.meta.url), "utf8");
const data = await readFile(new URL("../lib/nightfallMultiverseData.ts", import.meta.url), "utf8");
const creator = await readFile(new URL("../app/creator/page.tsx", import.meta.url), "utf8");
const navigation = await readFile(new URL("../components/NightfallNavigation.tsx", import.meta.url), "utf8");

test("homepage Multiverse preserves the archive's three interactive concept strategies", () => {
  assert.deepEqual(strategies.map(({ id }) => id), ["anchor", "bridge", "frontier"]);
  assert.match(data, /CONCEPT PREVIEW/);
  assert.match(component, /Illustrative evidence map/);
  assert.match(component, /type=\"range\"/);
  assert.match(component, /Apply to preview/);
  assert.match(component, /Open decision dossier/);
  assert.match(component, /does not reorder the stage/);
});

test("the published preview calculation is deterministic and isolated from API calls", () => {
  const priorities = { evidence: 80, distinct: 55, range: 25 };
  assert.deepEqual(previewIndex(priorities), {
    anchor: Math.round(0.5 * 80 + 0.3 * (100 - 25) + 0.2 * (100 - 55)),
    bridge: Math.round(0.4 * 55 + 0.4 * 80 + 0.2 * 25),
    frontier: Math.round(0.5 * 25 + 0.3 * 55 + 0.2 * (100 - 80)),
  });
  assert.equal(suggestStrategy(priorities).id, "anchor");
  assert.doesNotMatch(component, /fetch\(|\/api\//);
});

test("the live Creator Arena remains a distinct run-gated stage and is directly discoverable", () => {
  assert.match(creator, /id=\"positioning\"/);
  assert.match(creator, /completed Creator run supplies inspectable source evidence/);
  assert.match(creator, /startDemoRun\(\)/);
  assert.ok(navigation.includes('href: "/#multiverse"'));
});
