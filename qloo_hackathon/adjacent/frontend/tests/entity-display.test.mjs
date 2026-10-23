import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { normalizeEntityName } from "../lib/entityDisplay.ts";

const graph = await readFile(new URL("../components/AdjacencyGraph.tsx", import.meta.url), "utf8");
const types = await readFile(new URL("../types/adjacent.ts", import.meta.url), "utf8");

test("provider names retain canonical Unicode, trim presentation whitespace and reject explanation/URN masquerades", () => {
  assert.equal(normalizeEntityName("  Cafe\u0301  Polyp  "), "Café Polyp");
  assert.equal(normalizeEntityName("The Hero With æAsterios"), "The Hero With æAsterios");
  assert.equal(normalizeEntityName("urn:entity:book"), null);
  assert.equal(normalizeEntityName("28 book entities returned for this programme share Qloo tags"), null);
  assert.equal(normalizeEntityName(" \n\t "), null);
  assert.equal(normalizeEntityName(null), null);
});

test("cohort label is distinct from provider identity, grouping prose and raw subtype", () => {
  assert.match(graph, /cohortDisplayLabel\(c\.kind, c\.domain, c\.rank/);
  assert.doesNotMatch(graph, /memberLabel\s*\+\s*[`"']/);
  assert.doesNotMatch(graph, /construction_reason\s*\?\?\s*\(\?/);
  assert.match(graph, /Grouping note/);
  assert.match(graph, /Read provider-backed grouping explanation/);
  assert.match(graph, /All \{active\.node\.members\.length\} returned members and evidence tags/);
  assert.match(graph, /activeMember\.member\.entity_id/);
  assert.match(graph, /activeMember\.member\.tags/);
  assert.match(graph, /<title>\{member\.name\}<\/title>/);
  assert.match(types, /name: string \| null;/);
  assert.match(types, /tags\?: \{ tag_id: string; name: string \| null; subtype: string \| null \}\[\]/);
});

test("interactive entity nodes expose full names and keyboard activation", () => {
  assert.match(graph, /aria-label=\{member\.name \+ ", member of "/);
  assert.match(graph, /onKeyDown=\{\(e\) =>/);
  assert.match(graph, /e\.key === "Enter" \|\| e\.key === " "/);
  assert.match(graph, /normalizeEntityName\(member\.name\) \?\? "Name unavailable"/);
});
