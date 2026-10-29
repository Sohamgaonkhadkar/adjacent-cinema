/**
 * Map framing and layer visibility for the returned affinity cells.
 *
 * Kept out of the component so the decisions that produced a blank map can be
 * tested without a browser. There were two of them, and they compounded:
 *
 *  1. the opening zoom came from a coarse ladder (9 / 11 / 13) that only
 *     considered how wide the spread was, not whether the cells would fit in
 *     the panel. A run whose cells spanned ~4.5° opened at zoom 9, where the
 *     panel covers under 2° — every point was off-screen and the map looked
 *     empty even though each coordinate was valid;
 *  2. the point layer used `minzoom: 11` unconditionally, so in point-only mode
 *     (density withheld below the ten-cell claim budget) a run that opened
 *     below 11 had nothing drawn at all.
 *
 * The plan now fits the view to the cells themselves and keeps the point layer
 * visible at whatever zoom that produces. Nothing here invents a coordinate:
 * the bounds are computed only from cells the provider returned.
 */

export interface MapCell {
  latitude: number;
  longitude: number;
}

export interface AffinityMapCell extends MapCell {
  affinity: number | null | undefined;
}

export type GeographyMapSource<T extends AffinityMapCell> = {
  cells?: T[] | null;
  highest_affinity_cells?: T[] | null;
};

/** Keep the full returned cell set; fall back to ranked cells only if that set is empty/unscored. */
export function selectScoredMapCells<T extends AffinityMapCell>(
  geography: GeographyMapSource<T>,
): Array<T & { affinity: number }> {
  const all = (geography.cells ?? []).filter(
    (cell): cell is T & { affinity: number } =>
      typeof cell.affinity === "number" && Number.isFinite(cell.affinity),
  );
  if (all.length > 0) return all;
  return (geography.highest_affinity_cells ?? []).filter(
    (cell): cell is T & { affinity: number } =>
      typeof cell.affinity === "number" && Number.isFinite(cell.affinity),
  );
}

/** Zoom at which the crisp detail circles join the density surface. */
export const POINT_DETAIL_MIN_ZOOM = 11;

/** Zoom where we stop showing the smoothed density surface and leave crisp cell markers. */
export const HEAT_SURFACE_MAX_ZOOM = 13;

/** Whether the density surface remains visible at this zoom. */
export function heatSurfaceVisibleAtZoom(plan: MapLayerPlan, zoom: number): boolean {
  return plan.heat.enabled && zoom < plan.heat.maxzoom;
}

/** Framing for a single cell (or coincident cells): one point, not a world view. */
export const POINT_SPREAD_ZOOM = 13;

/** Space kept between the outermost cells and the edge of the panel, in px. */
export const FIT_PADDING_PX = 36;

export type LngLatTuple = [number, number];

export interface MapLayerPlan {
  /** Centre of the returned cells, as [lng, lat] — the order MapLibre wants. */
  centre: LngLatTuple;
  /** Bounding box of the returned cells: [[west, south], [east, north]]. */
  bounds: [LngLatTuple, LngLatTuple];
  /** Handed to MapLibre so the view fits the cells instead of a guessed zoom. */
  fit: { padding: number; maxZoom: number };
  /** Largest spread, in degrees, between the returned cells. */
  spread: number;
  density: boolean;
  /** Layer configuration, so "is the point layer visible here" is testable. */
  points: { minzoom: number };
  heat: { enabled: boolean; maxzoom: number };
}

/**
 * Points must be visible wherever the map opens. In density mode the circles
 * are a zoom-in detail layer over the density surface, which is why they keep
 * their zoom floor. In point-only mode they are the entire rendering, so they
 * start at the map's own minimum zoom.
 */
export function pointLayerMinZoom(density: boolean): number {
  return density ? POINT_DETAIL_MIN_ZOOM : 0;
}

/** Are the returned cells drawn at this zoom? */
export function pointsVisibleAtZoom(plan: MapLayerPlan, zoom: number): boolean {
  return zoom >= plan.points.minzoom;
}

/** True when the cell falls inside the plan's box (used by the tests and the browser pass). */
export function boundsContain(
  plan: MapLayerPlan,
  cell: MapCell,
): boolean {
  const [[west, south], [east, north]] = plan.bounds;
  return cell.longitude >= west && cell.longitude <= east && cell.latitude >= south && cell.latitude <= north;
}

/** Build the framing/layer plan for the returned cells, or null when there are none. */
export function buildMapLayerPlan(cells: MapCell[], density: boolean): MapLayerPlan | null {
  if (cells.length === 0) return null;

  const lats = cells.map((cell) => cell.latitude);
  const lngs = cells.map((cell) => cell.longitude);
  const west = Math.min(...lngs);
  const east = Math.max(...lngs);
  const south = Math.min(...lats);
  const north = Math.max(...lats);
  const spread = Math.max(east - west, north - south);

  return {
    centre: [(west + east) / 2, (south + north) / 2],
    bounds: [
      [west, south],
      [east, north],
    ],
    // `maxZoom` keeps a single cell (or a tight cluster) from filling the panel
    // with one enormous circle; `padding` keeps edge cells off the border.
    fit: { padding: FIT_PADDING_PX, maxZoom: POINT_SPREAD_ZOOM },
    spread,
    density,
    points: { minzoom: pointLayerMinZoom(density) },
    heat: { enabled: density, maxzoom: density ? HEAT_SURFACE_MAX_ZOOM : 0 },
  };
}
