import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  FIT_PADDING_PX,
  POINT_DETAIL_MIN_ZOOM,
  POINT_SPREAD_ZOOM,
  boundsContain,
  buildMapLayerPlan,
  pointLayerMinZoom,
  pointsVisibleAtZoom,
} from "../lib/geographyMap.ts";

/**
 * The geography panel could render a blank map with perfectly valid cells. Two
 * causes, both covered here:
 *
 *  - the opening zoom was a guess from the spread (9 / 11 / 13), so a run whose
 *    cells spanned several degrees opened at a zoom where they were all
 *    off-screen;
 *  - the point layer was pinned to `minzoom: 11`, so in point-only mode a run
 *    that opened below 11 drew nothing at all.
 */

function cell(latitude, longitude, affinity = 0.7) {
  return { latitude, longitude, affinity, geohash: null, affinity_rank: null, popularity: null };
}

/** Four cities across Great Britain: wide spread, sparse scores. */
const WIDE = [cell(51.5074, -0.1278), cell(53.4808, -2.2426), cell(51.4545, -2.5879), cell(55.9533, -3.1883)];

/** Three cells inside a few blocks. */
const TIGHT = [cell(51.5074, -0.1278), cell(51.5079, -0.1281), cell(51.5081, -0.1275)];

test("the view is fitted to the returned cells, so none of them opens off-screen", () => {
  const plan = buildMapLayerPlan(WIDE, false);
  assert.ok(plan);
  for (const point of WIDE) {
    assert.equal(boundsContain(plan, point), true, `cell ${point.latitude},${point.longitude} is outside the fitted view`);
  }
  // The bounds are the box MapLibre is asked to fit, with padding and a zoom
  // ceiling — not a zoom number computed from the spread.
  assert.deepEqual(plan.bounds, [
    [-3.1883, 51.4545],
    [-0.1278, 55.9533],
  ]);
  assert.deepEqual(plan.fit, { padding: FIT_PADDING_PX, maxZoom: POINT_SPREAD_ZOOM });
  assert.equal(plan.spread > 4, true);
});

test("point-only mode draws its points at whatever zoom the fit produces", () => {
  for (const [label, cells] of [["wide", WIDE], ["tight", TIGHT]]) {
    const plan = buildMapLayerPlan(cells, false);
    assert.ok(plan, label);
    assert.equal(plan.points.minzoom, 0, `${label}: points must not have a zoom floor in point-only mode`);
    for (const zoom of [0, 3, 5, 6, 8, 9, 11, 13, 18, 22]) {
      assert.equal(pointsVisibleAtZoom(plan, zoom), true, `${label}: points hidden at zoom ${zoom}`);
    }
    for (const point of cells) {
      assert.equal(boundsContain(plan, point), true, `${label}: cell outside the fitted view`);
    }
  }
});

test("point-only mode never draws a density surface", () => {
  const plan = buildMapLayerPlan(WIDE, false);
  assert.ok(plan);
  assert.equal(plan.density, false);
  assert.equal(plan.heat.enabled, false, "a sparse run must not render a heatmap");
});

test("density mode keeps the circles as a zoom-in detail layer", () => {
  const plan = buildMapLayerPlan(WIDE, true);
  assert.ok(plan);
  assert.equal(plan.heat.enabled, true);
  assert.equal(plan.points.minzoom, POINT_DETAIL_MIN_ZOOM);
  // Unchanged behaviour: the density surface carries the wide view, the circles
  // join it once the reader is close enough for them not to look like noise.
  assert.equal(pointsVisibleAtZoom(plan, 6), false);
  assert.equal(pointsVisibleAtZoom(plan, 9), false);
  assert.equal(pointsVisibleAtZoom(plan, 11), true);
  assert.equal(pointsVisibleAtZoom(plan, 14), true);
});

test("only the point floor and the heat layer depend on the claim budget", () => {
  assert.equal(pointLayerMinZoom(false), 0);
  assert.equal(pointLayerMinZoom(true), POINT_DETAIL_MIN_ZOOM);
  for (const cells of [WIDE, TIGHT]) {
    const sparse = buildMapLayerPlan(cells, false);
    const dense = buildMapLayerPlan(cells, true);
    assert.deepEqual(sparse.bounds, dense.bounds, "framing must not depend on the claim budget");
    assert.deepEqual(sparse.centre, dense.centre);
    assert.deepEqual(sparse.fit, dense.fit);
  }
});

test("a single returned cell frames a point view rather than a world view", () => {
  const plan = buildMapLayerPlan([cell(45.5, -122.75)], false);
  assert.ok(plan);
  assert.deepEqual(plan.centre, [-122.75, 45.5]);
  assert.deepEqual(plan.bounds, [
    [-122.75, 45.5],
    [-122.75, 45.5],
  ]);
  // Degenerate bounds would make fitBounds zoom to maximum; the ceiling keeps
  // the single cell readable.
  assert.equal(plan.fit.maxZoom, POINT_SPREAD_ZOOM);
  assert.equal(pointsVisibleAtZoom(plan, POINT_SPREAD_ZOOM), true);
});

test("bounds and centre come from the returned cells only", () => {
  const plan = buildMapLayerPlan([cell(10, 20), cell(12, 24)], false);
  assert.ok(plan);
  assert.deepEqual(plan.bounds, [
    [20, 10],
    [24, 12],
  ]);
  assert.deepEqual(plan.centre, [22, 11], "centre is [lng, lat]");
  assert.equal(plan.spread, 4);
});

test("no cells means no plan, so the map is never drawn from nothing", () => {
  assert.equal(buildMapLayerPlan([], false), null);
  assert.equal(buildMapLayerPlan([], true), null);
});

// Node cannot render the TSX component, so this asserts the wiring the browser
// pass exercises: the component must take its framing and point-layer floor
// from the plan above rather than re-deriving any of them.
test("GeographyMap takes its framing and point floor from the plan", () => {
  const source = readFileSync(new URL("../components/GeographyMap.tsx", import.meta.url), "utf8");
  assert.match(source, /buildMapLayerPlan\(cells, density\)/);
  assert.match(source, /bounds: plan\.bounds/);
  assert.match(source, /fitBoundsOptions: plan\.fit/);
  assert.match(source, /minzoom: plan\.points\.minzoom/);
  assert.doesNotMatch(source, /minzoom: 11/, "the point layer must not hard-code a zoom floor again");
  assert.doesNotMatch(source, /zoom: (9|11|13)\b/, "the opening zoom must come from the fitted bounds");
  // The worker must be served from public/, otherwise maplibre 6 fetches a 404
  // and no GeoJSON layer renders at all.
  assert.match(source, /setWorkerUrl\("\/maplibre\/maplibre-gl-worker\.mjs"\)/);
});
