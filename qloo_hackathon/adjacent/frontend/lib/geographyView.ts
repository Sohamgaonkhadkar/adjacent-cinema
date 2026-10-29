import type { GeographyData, HeatmapCell } from "@/types/adjacent";

/**
 * What the geography chapter is allowed to state, derived from what the run
 * actually returned.
 *
 * The backend refuses to call a heatmap "sufficient" below ten scored cells
 * (`backend/app/domain/geography.py`). That gate exists to stop a handful of
 * points being written up as a concentration claim. It is *not* a reason to
 * throw the returned cells away: hiding nine real cells behind an empty
 * "withheld" panel misrepresents the run in the opposite direction, and it was
 * the reason the geography panel rendered as a large blank rectangle.
 *
 * So the view separates three questions that were previously collapsed into a
 * single `sufficient` flag:
 *
 *  - are there scored cells to draw at all?      → map vs. no map
 *  - is there a full cell budget for density?    → density shading vs. points
 *  - did the run return an artefact at all?      → measured absence vs. no run
 *
 * Nothing here invents a coordinate, a pin or a measurement: every cell in the
 * output came back from the provider, and a missing affinity is never a zero.
 */

/** Cells the backend needs before it will describe a geographic concentration. */
export const GEOGRAPHY_CLAIM_THRESHOLD = 10;

export type ScoredCell = HeatmapCell & { affinity: number };

function hasAffinity(cell: HeatmapCell): cell is ScoredCell {
  return typeof cell.affinity === "number" && Number.isFinite(cell.affinity);
}

/** The cells this run returned that carry both a coordinate and a score. */
export function scoredCells(geography: GeographyData | null | undefined): ScoredCell[] {
  if (!geography) return [];
  const cells = geography.highest_affinity_cells ?? geography.cells ?? [];
  return cells.filter(hasAffinity);
}

export type GeographyView =
  | {
      mode: "map";
      cells: ScoredCell[];
      /** Density shading is a concentration statement, so it needs the full budget. */
      density: boolean;
      coverage: "complete" | "partial";
      headline: string;
      body: string;
    }
  | {
      mode: "unmapped";
      cells: [];
      /** Cells with coordinates that came back, scored or not. */
      returned: number;
      headline: string;
      body: string;
    }
  | { mode: "absent"; cells: []; returned: 0; headline: string; body: string };

export function buildGeographyView(
  geography: GeographyData | null | undefined,
  city: string,
): GeographyView {
  const label = city?.trim() || geography?.city_display?.trim() || geography?.city?.trim() || "This city";

  if (!geography) {
    return {
      mode: "absent",
      cells: [],
      returned: 0,
      headline: "This run returned no geography artefact.",
      body: `${label} is still recorded as venue context. The heatmap step did not complete for this run, so no coordinates, pins or density surface are shown — and none are inferred.`,
    };
  }

  const cells = scoredCells(geography);
  const density = geography.sufficient && cells.length >= GEOGRAPHY_CLAIM_THRESHOLD;

  if (cells.length > 0) {
    return {
      mode: "map",
      cells,
      density,
      coverage: density ? "complete" : "partial",
      headline: density ? "Coordinates returned by this run." : "Coordinates returned — density withheld.",
      body: density
        ? `${label} is drawn from ${cells.length} returned affinity cells. Affinity is a cultural-similarity signal, not attendance or footfall.`
        : `This run returned ${cells.length} scored cell${cells.length === 1 ? "" : "s"} for ${label} — below the ${GEOGRAPHY_CLAIM_THRESHOLD} the method needs before shading a density surface. Those cells are plotted as points; no concentration, footfall or attendance claim is made from them.`,
    };
  }

  const returned = geography.total_cells ?? 0;
  return {
    mode: "unmapped",
    cells: [],
    returned,
    headline:
      returned > 0 ? "Cells returned without an affinity score." : "No heatmap cells returned for this city.",
    body:
      returned > 0
        ? `${returned} cell${returned === 1 ? "" : "s"} came back with a coordinate but no affinity value. A missing value is not a measured zero, so nothing is drawn on a map.`
        : `The heatmap request completed and returned no cells for ${label}. That is an absence of evidence, not evidence of low cultural activity, so no pins or shading are drawn.`,
  };
}
