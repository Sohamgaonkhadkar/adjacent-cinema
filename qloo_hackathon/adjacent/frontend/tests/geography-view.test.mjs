import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import {
  GEOGRAPHY_CLAIM_THRESHOLD,
  GEOGRAPHY_NOT_RETURNED,
  buildGeographyView,
  geographyFacts,
  scoredCells,
} from "../lib/geographyView.ts";

/**
 * The geography chapter used to render a large empty "map withheld" panel for
 * every run that came back with fewer than ten scored cells — including runs
 * that had returned several perfectly good cells. These tests pin the split
 * between "no claims are supported" and "there is nothing to draw", which is
 * the distinction that was collapsed into a single boolean.
 */

function cell(index, affinity = 0.9 - index * 0.01) {
  return {
    latitude: 45.5 + index * 0.01,
    longitude: -122.7 - index * 0.01,
    geohash: `c20f${String(index).padStart(3, "0")}`,
    affinity,
    affinity_rank: index + 1,
    popularity: 0.2,
  };
}

function geography(overrides = {}) {
  const cells = overrides.highest_affinity_cells ?? [];
  return {
    city: "Portland, Oregon",
    city_display: "Portland",
    total_cells: overrides.total_cells ?? cells.length,
    highest_affinity_cells: cells,
    call_id: "call_geo_1",
    data_status: "measured",
    source: "qloo",
    sufficient: overrides.sufficient ?? cells.length >= GEOGRAPHY_CLAIM_THRESHOLD,
    note: overrides.note ?? "",
    ...overrides,
  };
}

test("a full cell budget draws the map with density shading", () => {
  const cells = Array.from({ length: 24 }, (_, index) => cell(index));
  const view = buildGeographyView(geography({ highest_affinity_cells: cells }), "Portland, Oregon");

  assert.equal(view.mode, "map");
  if (view.mode !== "map") return;
  assert.equal(view.cells.length, 24);
  assert.equal(view.density, true);
  assert.equal(view.coverage, "complete");
  assert.match(view.body, /Portland, Oregon/);
  assert.match(view.body, /not attendance or footfall/);
});

test("below the claim threshold the returned cells are still plotted, without density", () => {
  const cells = Array.from({ length: 6 }, (_, index) => cell(index));
  const view = buildGeographyView(geography({ highest_affinity_cells: cells }), "");

  assert.equal(view.mode, "map", "six returned cells must render, not an empty withheld panel");
  if (view.mode !== "map") return;
  assert.equal(view.cells.length, 6);
  assert.equal(view.density, false, "a density surface would imply a concentration claim");
  assert.equal(view.coverage, "partial");
  assert.match(view.headline, /density withheld/);
  assert.match(view.body, /below the 10/);
  // The city label falls back to the artefact's own display name.
  assert.match(view.body, /Portland/);
});

test("a sufficient flag alone cannot unlock density without the cells behind it", () => {
  const cells = Array.from({ length: 3 }, (_, index) => cell(index));
  const view = buildGeographyView(
    geography({ highest_affinity_cells: cells, sufficient: true }),
    "Portland",
  );

  assert.equal(view.mode, "map");
  if (view.mode !== "map") return;
  assert.equal(view.density, false);
  assert.equal(view.coverage, "partial");
});

test("cells that came back without an affinity score are reported, never plotted as zero", () => {
  const cells = [
    { ...cell(0), affinity: null },
    { ...cell(1), affinity: null },
    { ...cell(2), affinity: null },
  ];
  const view = buildGeographyView(
    geography({ highest_affinity_cells: cells, total_cells: 3, sufficient: false }),
    "Portland",
  );

  assert.equal(view.mode, "unmapped");
  if (view.mode !== "unmapped") return;
  assert.equal(view.returned, 3);
  assert.equal(view.cells.length, 0);
  assert.match(view.headline, /without an affinity score/);
  assert.match(view.body, /missing value is not a measured zero/i);
});

test("a completed heatmap that returned no cells says so instead of implying low activity", () => {
  const view = buildGeographyView(
    geography({ highest_affinity_cells: [], total_cells: 0, sufficient: false }),
    "Brighton, United Kingdom",
  );

  assert.equal(view.mode, "unmapped");
  if (view.mode !== "unmapped") return;
  assert.equal(view.returned, 0);
  assert.match(view.headline, /No heatmap cells returned/);
  assert.match(view.body, /absence of evidence/);
  assert.match(view.body, /Brighton, United Kingdom/);
});

test("a run with no geography artefact is not described as a measured absence", () => {
  const view = buildGeographyView(null, "Leeds");

  assert.equal(view.mode, "absent");
  if (view.mode !== "absent") return;
  assert.equal(view.returned, 0);
  assert.match(view.headline, /no geography artefact/);
  assert.match(view.body, /Leeds/);
  assert.match(view.body, /none are inferred/);
});

test("scored cells ignore non-finite affinities and never invent coordinates", () => {
  const source = geography({
    highest_affinity_cells: [
      cell(0, 0.5),
      { ...cell(1), affinity: Number.NaN },
      { ...cell(2), affinity: null },
    ],
  });

  const cells = scoredCells(source);
  assert.equal(cells.length, 1);
  assert.equal(cells[0].latitude, source.highest_affinity_cells[0].latitude);
  assert.equal(scoredCells(null).length, 0);
});

test("geography copy keeps the product's bounded-claim language", () => {
  const views = [
    buildGeographyView(geography({ highest_affinity_cells: Array.from({ length: 24 }, (_, i) => cell(i)) }), "Portland"),
    buildGeographyView(geography({ highest_affinity_cells: Array.from({ length: 4 }, (_, i) => cell(i)) }), "Portland"),
    buildGeographyView(geography({ highest_affinity_cells: [], total_cells: 2 }), "Portland"),
    buildGeographyView(null, "Portland"),
  ];

  for (const view of views) {
    const copy = `${view.headline} ${view.body}`.toLowerCase();
    for (const forbidden of ["probability", "confidence", "likelihood of", "attendance forecast"]) {
      assert.ok(!copy.includes(forbidden), `geography copy must not claim "${forbidden}"`);
    }
  }
});


// ── Facts strip: an unknown count is never printed as zero ───────────────────

function factsFor(view, city = "Portland, Oregon") {
  assert.notEqual(view.mode, "map");
  return Object.fromEntries(geographyFacts(view, city).map((fact) => [fact.label, fact.value]));
}

test("no artefact returned reports an unknown affinity count, never zero", () => {
  const view = buildGeographyView(null, "Leeds");
  const facts = factsFor(view, "Leeds");

  assert.equal(facts["With affinity"], GEOGRAPHY_NOT_RETURNED);
  assert.equal(facts["With affinity"], "Not returned");
  assert.notEqual(facts["With affinity"], "0", "a run with no artefact never measured zero");
  assert.equal(facts["Cells with coordinates"], GEOGRAPHY_NOT_RETURNED);
  assert.equal(facts["Map / pins"], "Not drawn");
  assert.equal(facts["City context"], "Leeds");
});

test("cells returned without affinity do support a printed zero", () => {
  const cells = [{ ...cell(0), affinity: null }, { ...cell(1), affinity: null }];
  const view = buildGeographyView(
    geography({ highest_affinity_cells: cells, total_cells: 2, sufficient: false }),
    "Portland, Oregon",
  );
  const facts = factsFor(view);

  assert.equal(view.mode, "unmapped");
  assert.equal(facts["With affinity"], "0");
  assert.equal(facts["Cells with coordinates"], "2", "the two inspected cells are counted");
  assert.equal(facts["Map / pins"], "Not drawn");
});

test("an artefact that returned no cells at all still reports a measured zero", () => {
  const view = buildGeographyView(
    geography({ highest_affinity_cells: [], total_cells: 0, sufficient: false }),
    "Brighton",
  );
  const facts = factsFor(view, "Brighton");

  assert.equal(view.mode, "unmapped");
  assert.equal(facts["Cells with coordinates"], "0");
  assert.equal(facts["With affinity"], "0");
});

test("the facts strip never mixes a measured count with an unknown one", () => {
  const absent = factsFor(buildGeographyView(null, "Leeds"), "Leeds");
  assert.equal(absent["Cells with coordinates"], absent["With affinity"]);

  const unmapped = factsFor(
    buildGeographyView(geography({ highest_affinity_cells: [], total_cells: 3 }), "Leeds"),
    "Leeds",
  );
  assert.equal(Number.isFinite(Number(unmapped["Cells with coordinates"])), true);
  assert.equal(Number.isFinite(Number(unmapped["With affinity"])), true);
});

test("an empty city falls back to a label instead of printing nothing", () => {
  const facts = factsFor(buildGeographyView(null, ""), "");
  assert.equal(facts["City context"], "Recorded per run");
});

// ── Component wiring ───────────────────────────────────────────────────────
// Node cannot render these TSX components (no JSX transform in the test
// runner), so the panel's wiring is asserted against the source and the
// rendered behaviour is checked in the browser pass recorded in
// docs/verification_2026-10-29_ui_fixes.md.

test("the absence panel takes its counts from the view model", () => {
  const source = readFileSync(new URL("../components/GeographyAbsence.tsx", import.meta.url), "utf8");
  assert.match(source, /geographyFacts\(view, city\)/);
  assert.doesNotMatch(source, /With affinity"\s*,\s*value:\s*"0"/);
  assert.doesNotMatch(source, /Cells returned"\s*,\s*value:\s*String\(view\.returned\)/);
});

test("empty ranked cells fall back to the scored full-cell response", () => {
  const cells = [cell(0), cell(1), { ...cell(2), affinity: Number.NaN }];
  const view = buildGeographyView(
    geography({ highest_affinity_cells: [], cells, total_cells: cells.length }),
    "Portland",
  );
  assert.equal(view.mode, "map");
  if (view.mode !== "map") return;
  assert.deepEqual(view.cells.map((item) => item.geohash), [cells[0].geohash, cells[1].geohash]);
});
