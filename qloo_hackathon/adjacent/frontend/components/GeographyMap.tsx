"use client";

import { useEffect, useRef, useState } from "react";
import { Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { GeographyData, HeatmapCell } from "@/types/adjacent";

function hasAffinity(cell: HeatmapCell): cell is HeatmapCell & { affinity: number } {
  return cell.affinity !== null && cell.affinity !== undefined;
}

/**
 * Affinity heat map for the cells the backend actually returned.
 *
 * The basemap comes from a public tile host, which is the one thing on this page
 * the application cannot verify offline. If those tiles fail, the component says
 * so and falls back to the returned cells as text: the evidence survives the
 * map, and a blank canvas is never passed off as "no signal here".
 */
export default function GeographyMap({ geography }: { geography: GeographyData }) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<InstanceType<typeof MapLibreMap> | null>(null);
  const [tilesUnavailable, setTilesUnavailable] = useState(false);
  const allCells = geography.cells ?? geography.highest_affinity_cells ?? [];
  const cells = allCells.filter(hasAffinity);
  const ranked = [...cells].sort((left, right) => (right.affinity ?? 0) - (left.affinity ?? 0));

  useEffect(() => {
    if (!mapContainer.current || mapRef.current || cells.length === 0) return;

    const lats = cells.map((c) => c.latitude);
    const lngs = cells.map((c) => c.longitude);
    const centreLat = (Math.min(...lats) + Math.max(...lats)) / 2;
    const centreLng = (Math.min(...lngs) + Math.max(...lngs)) / 2;

    const latSpread = Math.max(...lats) - Math.min(...lats);
    const lngSpread = Math.max(...lngs) - Math.min(...lngs);
    const maxSpread = Math.max(latSpread, lngSpread);
    const zoom = maxSpread > 0.5 ? 9 : maxSpread > 0.1 ? 11 : 13;

    const map = new MapLibreMap({
      container: mapContainer.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: [centreLng, centreLat],
      zoom: zoom,
      attributionControl: { compact: true },
    });

    // A failed style/tile request is reported, not silently rendered as an
    // empty beige rectangle.
    map.on("error", () => setTilesUnavailable(true));

    map.on("load", () => {
      const features = cells.map((cell) => ({
        type: "Feature" as const,
        properties: { affinity: cell.affinity },
        geometry: {
          type: "Point" as const,
          coordinates: [cell.longitude, cell.latitude],
        },
      }));

      map.addSource("affinity", {
        type: "geojson",
        data: { type: "FeatureCollection", features },
      });

      map.addLayer({
        id: "affinity-heat",
        type: "heatmap",
        source: "affinity",
        maxzoom: 15,
        paint: {
          "heatmap-weight": [
            "interpolate",
            ["linear"],
            ["get", "affinity"],
            0,
            0,
            1,
            1,
          ],
          "heatmap-intensity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            0,
            1,
            15,
            3,
          ],
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(194,154,110,0)",
            0.2,
            "rgba(194,154,110,0.35)",
            0.4,
            "rgba(194,154,110,0.55)",
            0.6,
            "rgba(194,154,110,0.72)",
            0.8,
            "rgba(194,154,110,0.86)",
            1,
            "rgba(224,196,154,1)",
          ],
          "heatmap-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            0,
            2,
            15,
            20,
          ],
          "heatmap-opacity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            7,
            0.8,
            15,
            0.6,
          ],
        },
      });

      map.addLayer({
        id: "affinity-points",
        type: "circle",
        source: "affinity",
        minzoom: 11,
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["get", "affinity"],
            0,
            3,
            1,
            10,
          ],
          "circle-color": "rgb(194,154,110)",
          "circle-opacity": 0.75,
          "circle-stroke-color": "rgb(233,228,218)",
          "circle-stroke-width": 1,
        },
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [geography, cells.length]);

  if (cells.length === 0) {
    return (
      <div className="flex min-h-[12rem] items-center justify-center border border-dashed border-line-strong p-6 text-center">
        <p className="caption max-w-sm">
          No affinity scores were returned to map. Missing values are not drawn as zero.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="relative h-[300px] w-full overflow-hidden border border-line bg-ink-3 md:h-[380px]">
        <div ref={mapContainer} className="h-full w-full" aria-label={`Affinity heat map for ${geography.city_display}`} />
        {tilesUnavailable && (
          <div className="pointer-events-none absolute inset-x-0 top-0 border-b border-line bg-ink/95 px-4 py-2">
            <p className="caption">
              Basemap tiles could not be loaded — the returned cells are listed below instead.
            </p>
          </div>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="caption">
          {geography.city_display || geography.city} · {geography.total_cells} cells returned ·{" "}
          {cells.length} with an affinity score
        </p>
        <div className="flex items-center gap-3">
          {[
            ["Low", "bg-amber/30"],
            ["Medium", "bg-amber/60"],
            ["High", "bg-amber"],
          ].map(([label, tone]) => (
            <span key={label} className="flex items-center gap-1.5">
              <span className={`inline-block h-2 w-2 rounded-full ${tone}`} />
              <span className="caption">{label}</span>
            </span>
          ))}
        </div>
      </div>

      {tilesUnavailable && (
        <ol className="mt-4 divide-y divide-line border-y border-line">
          {ranked.slice(0, 5).map((cell, index) => (
            <li
              key={cell.geohash ?? `${cell.latitude},${cell.longitude}`}
              className="flex items-baseline justify-between gap-3 py-2"
            >
              <span className="font-mono text-[0.68rem] text-paper-2">
                {String(index + 1).padStart(2, "0")} ·{" "}
                {cell.geohash ?? `${cell.latitude.toFixed(3)}, ${cell.longitude.toFixed(3)}`}
              </span>
              <span className="caption">
                affinity {cell.affinity?.toFixed(2)}
                {typeof cell.affinity_rank === "number" ? ` · rank ${cell.affinity_rank}` : ""}
              </span>
          </li>
          ))}
        </ol>
      )}
      <p className="caption mt-2">
        Cell affinity is relative cultural similarity inside one Qloo scoring context. It is not a
        footfall, attendance or revenue estimate.
      </p>
    </div>
  );
}
