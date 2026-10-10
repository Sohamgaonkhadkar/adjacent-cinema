"use client";

import { useEffect, useRef } from "react";
import { Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { GeographyData } from "@/types/adjacent";

interface Props {
  geography: GeographyData;
}

export default function GeographyMap({ geography }: Props) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<InstanceType<typeof MapLibreMap> | null>(null);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;
    const cells = geography.cells ?? geography.highest_affinity_cells ?? [];
    if (cells.length === 0) return;

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
    });

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
            "rgba(196,93,62,0)",
            0.2,
            "rgba(196,93,62,0.3)",
            0.4,
            "rgba(196,93,62,0.5)",
            0.6,
            "rgba(196,93,62,0.7)",
            0.8,
            "rgba(196,93,62,0.85)",
            1,
            "rgba(196,93,62,1)",
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
          "circle-color": "rgb(196,93,62)",
          "circle-opacity": 0.7,
          "circle-stroke-color": "rgb(245,240,235)",
          "circle-stroke-width": 1,
        },
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [geography]);

  if (!geography.cells || geography.cells.length === 0) {
    return (
      <div className="map-container flex items-center justify-center">
        <span className="mono" style={{ color: "var(--muted)", fontSize: "0.75rem" }}>
          Geographic data insufficient for visualisation
        </span>
      </div>
    );
  }

  return (
    <div>
      <div ref={mapContainer} className="map-container" />
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: "0.75rem",
          fontSize: "0.7rem",
          color: "var(--muted)",
        }}
      >
        <span className="mono">
          {geography.city_display} — {geography.total_cells} cells
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <span
              style={{
                display: "inline-block",
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: "rgba(196,93,62,0.3)",
              }}
            />
            Low
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <span
              style={{
                display: "inline-block",
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: "rgba(196,93,62,0.6)",
              }}
            />
            Medium
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <span
              style={{
                display: "inline-block",
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: "rgba(196,93,62,1)",
              }}
            />
            High
          </span>
        </span>
      </div>
    </div>
  );
}