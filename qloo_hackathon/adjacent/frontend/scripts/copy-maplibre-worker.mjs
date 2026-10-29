/**
 * Copy MapLibre's worker script into `public/` before dev/build.
 *
 * maplibre-gl 6 loads its worker from a sibling `.mjs` file resolved from
 * `import.meta.url` (see `dist/maplibre-gl-worker.mjs`, which imports
 * `./maplibre-gl-shared.mjs`). A bundler that does not emit those assets leaves
 * the browser fetching a 404, so the worker never starts: the style and the
 * basemap paint, but every GeoJSON-driven layer — the affinity cells — stays
 * empty and the geography panel renders as a blank map.
 *
 * Shipping the two files from `public/maplibre/` and pointing the library at
 * them with `setWorkerUrl` keeps the worker on a URL the deployment actually
 * serves. The files are generated, so they are not committed.
 */
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const source = join(root, "node_modules", "maplibre-gl", "dist");
const target = join(root, "public", "maplibre");
const files = ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"];

if (!existsSync(source)) {
  // `npm ci` has not run yet; the build would fail on the import anyway.
  console.warn("[maplibre-worker] node_modules/maplibre-gl/dist not found — skipping");
  process.exit(0);
}

mkdirSync(target, { recursive: true });
for (const file of files) {
  const from = join(source, file);
  if (!existsSync(from)) {
    console.error(`[maplibre-worker] missing ${from}`);
    process.exit(1);
  }
  copyFileSync(from, join(target, file));
}
console.log(`[maplibre-worker] copied ${files.length} files to public/maplibre`);
