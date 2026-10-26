import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { normalizeEntityName } from "../lib/entityDisplay.ts";

const fingerprint = await readFile(
  new URL("../components/nf/CulturalFingerprint.tsx", import.meta.url),
  "utf8",
);
const nfData = await readFile(new URL("../lib/nfData.ts", import.meta.url), "utf8");
const types = await readFile(new URL("../types/adjacent.ts", import.meta.url), "utf8");

test("provider names retain canonical Unicode, trim presentation whitespace and reject explanation/URN masquerades", () => {
  assert.equal(normalizeEntityName("  Cafe\u0301  Polyp  "), "Café Polyp");
  assert.equal(normalizeEntityName("The Hero With æAsterios"), "The Hero With æAsterios");
  assert.equal(normalizeEntityName("urn:entity:book"), null);
  assert.equal(
    normalizeEntityName("28 book entities returned for this programme share Qloo tags"),
    null,
  );
  assert.equal(normalizeEntityName(" \n\t "), null);
  assert.equal(normalizeEntityName(null), null);
});

test("cohort label is distinct from provider identity, grouping prose and raw subtype", () => {
  // A cohort's display label is derived from kind/domain/rank, while a member's
  // label is the provider's own name — the two are never concatenated.
  assert.match(nfData, /cohortDisplayLabel\(cohort\.kind, cohort\.domain, cohort\.rank/);
  assert.match(nfData, /memberLabel\(member\)/);
  assert.doesNotMatch(nfData, /memberLabel\s*\+\s*[`"']/);
  assert.doesNotMatch(nfData, /construction_reason\s*\?\?\s*\(\?/);
  assert.match(fingerprint, /<title>\{cohort\.label\}<\/title>/);
  assert.match(fingerprint, /<title>\{entity\.label\}<\/title>/);
  assert.match(types, /name: string \| null;/);
  assert.match(types, /tags\?: \{ tag_id: string; name: string \| null; subtype: string \| null \}\[\]/);
});

test("interactive entity nodes expose full names and keyboard activation", () => {
  // Each node carries its own accessible name, its own Enter/Space handler and a
  // <title>, so the graph is not a mouse-only or anonymous surface.
  assert.match(fingerprint, /aria-label=\{`\$\{entity\.label\}, \$\{entity\.kind === "tag"/);
  assert.match(fingerprint, /aria-label=\{`\$\{cohort\.label\}, cohort/);
  assert.match(fingerprint, /onKeyDown=\{nodeKeyDown\(entity\.id/);
  assert.match(fingerprint, /event\.key === "Enter" \|\| event\.key === " "/);
  assert.match(fingerprint, /tabIndex=\{0\}/);
  assert.match(fingerprint, /role="button"/);
});
