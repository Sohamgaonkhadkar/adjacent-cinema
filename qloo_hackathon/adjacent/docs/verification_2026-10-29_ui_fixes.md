# Verification — stage photograph and geography panel fixes (2026-10-29)

PR: [#26](https://github.com/Sohamgaonkhadkar/adjacent-cinema/pull/26) · branch
`arena/a4114fe5-adjacent-cinema` · not merged.

Three rounds of work are recorded here: the two UI defects reported after PR #24,
two more discovered while verifying them in a real browser, and the evidence for
each. Screenshots live in
[`docs/evidence/2026-10-29-ui-fixes/`](evidence/2026-10-29-ui-fixes/) — paths below
are repo-root-relative.

Summary of what is **browser-verified** and what is **test-verified only** is in
the last two sections. Nothing here is claimed on the strength of CI alone.

---

## 1. Stage photograph collapsed to a ~10rem strip

### Root cause (not `h-full`)

Tailwind emits the position utilities in a fixed order. Read from the compiled
stylesheet of this build (`.next/static/chunks/*.css`):

| class | byte offset |
| --- | --- |
| `.absolute` | 8148 |
| `.fixed` | 8176 |
| `.relative` | 8198 |
| `.sticky` | 8226 |

Equal specificity, so `.relative` wins. `PhotoFrame` rendered
`cn("relative", className)`, so every caller asking for `absolute inset-0`
resolved to `position: relative`: the `<figure>` stayed in flow with `height:
auto`, `.img-frame`'s `height: 100%` resolved against `auto`, the frame fell back
to its `min-height` (10rem desktop / 8rem under 600px), and the sibling
`absolute inset-0` gradient overlay still covered the whole `min-h-[300px]`
container. PR #24's "add `absolute inset-0 h-full w-full`" could not work for
exactly this reason.

### Fix

`PhotoFrame` takes `fill`, which sets `position: absolute; inset: 0` as an
**inline style** (class-order independent), plus the matching classes. Call
sites migrated: `PositioningArena` stage; `HomeMultiverse` Anchor, Bridge (×2),
Frontier and dossier frames. Anchor/Bridge/dossier also collapsed on the
single-column layout, where a percentage height has no definite parent.

### Measured in the browser (1440×1000, and 390×844 for the phone case)

`figure` box = `.img-frame` box = rendered `<img>` box, `object-fit: cover`, for
every fill frame:

| State | figure | frame | img |
| --- | --- | --- | --- |
| Anchor (desktop) | 802×442 | 802×442 | 802×442 |
| Bridge (desktop, both frames) | 687×280 | 687×280 | 687×280 |
| Frontier (desktop) | 1374×520 | 1374×520 | 1374×520 |
| Anchor (390px wide) | 356×320 | 356×320 | 356×320 |

Screenshots: `01-home-anchor-stage.jpg`, `02-home-bridge-stage.jpg`,
`03-home-frontier-stage.jpg`, `04-home-phone-anchor.jpg`,
`05-cinema-mode-hero.jpg` (Cinema Mode hero, 1440×700, frame = figure).

Before this change the same frames measured 160px tall (the `min-height`) inside
the full-height column — the strip in the report.

---

## 2. Geography panel: "MAP WITHHELD" in an empty box

### Root cause A — the claim gate decided what was rendered

`backend/app/domain/geography.py`: cells without an affinity are dropped, then
`sufficient = len(scored) >= 10`; `to_dict()` sends only `highest_affinity_cells`
(top ten scored). The page required `sufficient` before rendering anything, then
said *"No usable coordinates returned"* and hid the table of cells that had come
back. A run with six real scored cells produced a large empty dashed box and a
false statement.

### Root cause B — the map could not draw at all (found in the browser)

Two independent defects in `GeographyMap`:

1. The point layer was pinned to `minzoom: 11` while the map opened at zoom 9 for
   a city-wide spread, so **point-only mode drew nothing below zoom 11**.
2. The opening zoom came from a coarse ladder (9 / 11 / 13) computed from the
   spread only. Measured: four cells spanning 4.5° opened at zoom 9, where a
   643×378 panel covers under 2° — **every point was off-screen**. The map looked
   empty with four perfectly valid coordinates.

And one defect that made *every* GeoJSON layer invisible in the production build:

3. maplibre-gl 6 fetches its worker from a sibling `maplibre-gl-worker.mjs`
   resolved against the bundle URL. Next/Turbopack does not emit that asset:
   `GET /maplibre-gl-worker.mjs` → **404**, console
   `Error: Worker failed to load`, style and basemap still painted, affinity
   layers empty. Measured before the fix: `mapAmberPixels = 0` with a fully
   populated 10-cell response.

### Fixes

- `lib/geographyView.ts` (new) separates "is there anything to plot" from "has
  the run earned a density claim" from "did the run return an artefact". Scored
  cells always render; below the ten-cell budget they render as **points with no
  density shading** and the panel says why; cells without affinity and missing
  artefacts get factual panels (`components/GeographyAbsence.tsx`). No pin,
  coordinate or measurement is invented; the backend threshold is unchanged.
- `lib/geographyMap.ts` (new) replaces the zoom ladder with a fitted view:
  `bounds` = bounding box of the returned cells, `fitBoundsOptions` = `{padding:
  36, maxZoom: 13}` (the ceiling keeps a single cell readable). The point layer
  floor is `0` in point-only mode and stays `11` in density mode, where the
  circles remain a zoom-in detail layer over the density surface.
- `scripts/copy-maplibre-worker.mjs` copies `maplibre-gl-worker.mjs` and
  `maplibre-gl-shared.mjs` into `public/maplibre/` on `predev`/`prebuild`
  (generated, gitignored); `GeographyMap` calls
  `setWorkerUrl("/maplibre/maplibre-gl-worker.mjs")`.

### Measured in the browser after the fixes

| State | What rendered | Screenshot |
| --- | --- | --- |
| Dense (`/run/demo`, 24 cells, 10 scored, `sufficient: true`) | heat + points, 10 cells inside the fitted view, `mapAmberPixels = 2114`, no tile-error banner | `06-geography-density.jpg` |
| Sparse (4 scored cells spanning 4.5°) | heading "Coordinates returned — density withheld.", "Coverage 4 of 10 cells · density surface withheld", 4 points visible, no heat layer, `mapAmberPixels = 644` | `07-geography-sparse-points.jpg` |
| Unmapped (4 cells, none with affinity) | "Cells returned without an affinity score." · Cells with coordinates **4** · With affinity **0** · map not drawn | `08-geography-no-affinity.jpg` |
| Absent (run returned no artefact) | "This run returned no geography artefact." · Cells with coordinates **Not returned** · With affinity **Not returned** | `09-geography-absent.jpg` |

---

## 3. Absence panel reported an unknown affinity count as zero

`GeographyAbsence` hard-coded `With affinity: 0`. For the `absent` state (no
geography artefact in the run) that asserts a number nobody measured. The facts
strip now comes from `geographyFacts(view, city)` in `lib/geographyView.ts`:

| state | Cells with coordinates | With affinity |
| --- | --- | --- |
| `absent` | `Not returned` | `Not returned` |
| `unmapped`, cells came back without scores | the returned count | `0` (measured) |
| `unmapped`, no cells came back | `0` | `0` (measured) |

Verified in the browser: `absent` → both `Not returned`; `unmapped` →
`4` / `0`. Screenshots 08 and 09 above.

---

## 4. Extra defect found while inspecting console errors: nested anchors

`/` logged `Minified React error #418` (hydration mismatch) on every load — with
and without request interception, so not an artefact of the sandbox. The dev
overlay named the cause: `<Link>` in `Portals` (`app/page.tsx:301,312`) wraps a
`PhotoFrame` whose `figcaption` contained `<a>Pexels</a>`. `<a>` cannot contain
`<a>`; the parser hoists the inner anchor and hydration fails for the page.

Fixed by `PhotoFrame`'s `creditLink` prop: the two portal tiles render the credit
as plain text instead of a nested link (`creditLink={false}`). After the fix the
home page logs no hydration error and the rendered HTML has no anchor nesting
(max depth 1, asserted in the render smoke test).

---

## 5. Commands run and results

All run in this workspace on 2026-10-29.

| Command | Result |
| --- | --- |
| `npm run build` (Turbopack + TypeScript, incl. `prebuild` worker copy) | pass |
| `npm run test:recovery` | 3 pass |
| `npm run test:layout` | 6 pass |
| `npm run test:geography` | 14 pass |
| `npm run test:geography-map` | 9 pass |
| `npm run test:creator-ui` | 8 pass |
| `npm run test:positioning` | 10 pass |
| `npm run test:entity-display` | 3 pass |
| `npm run test:contract` | 11 pass |
| `npm run test:proxy` | 3 pass |
| `npm run test:challenge` | 31 pass |
| `npm run test:comparables` | 8 pass |
| `npm run test:explainability` | 8 pass |
| `npm run test:pulse` | 35 pass |
| `npm run test:render` (production build, 5 routes) | 1 pass |
| `pytest -m "not live"` (backend, untouched by this PR) | 888 passed, 2 skipped, 8 deselected |

Frontend total: 149 assertions across 13 suites plus the production render smoke
test, which now also asserts that no rendered `<a>` nests another, that no
photograph carries both `relative` and `absolute`, that the compiled stylesheet
still emits `.absolute` before `.relative`, and that both maplibre worker assets
return 200.

New regression tests:

- `tests/geography-map.test.mjs` — fitted bounds contain every returned cell;
  point layer floor `0` in point-only mode so points are visible at any zoom the
  fit produces; density mode unchanged (`minzoom` 11, heat on); single-cell
  framing; empty input produces no plan; component wiring (`bounds`,
  `fitBoundsOptions`, `minzoom: plan.points.minzoom`, `setWorkerUrl`).
- `tests/geography-view.test.mjs` — cell/claim split, plus the facts strip:
  `absent` never prints `0`, `unmapped` prints the returned count and a measured
  `0`, and the two never mix.
- `tests/responsive-layout.test.mjs` — the two static regex tests from PR #24 are
  replaced by wiring assertions that would have caught these bugs.
- `tests/render-smoke.mjs` — rendered-HTML assertions listed above, including the
  worker assets that must be served from `public/`.

## 6. How the browser evidence was produced

No browser was installable through the usual route in this sandbox (Playwright's
download CDN, Google storage and the Debian mirrors are unreachable; `apt` cannot
install `libnss3`). A real Chromium runs with the build shipped by
`@sparticuz/chromium` plus that package's bundled AL2023 shared libraries:

```bash
# decompress the bundled libs, then point Chromium at them
LD_LIBRARY_PATH=/tmp/al2023/lib /tmp/chromium --version   # Chromium 153.0.8010.0
```

Playwright (`p.chromium.launch(executable_path="/tmp/chromium", ...)`) drives it
against the **production build** (`next start`) talking to the real backend on
`127.0.0.1:8000`; measurements come from `getBoundingClientRect()` /
`getComputedStyle()` in the page, and the map evidence from pixel counts of the
map screenshot.

Two hostname substitutions were necessary because the sandbox has no outbound
network. Both are recorded here so the evidence is not overstated:

1. `images.pexels.com` → a locally generated JPEG of the same dimensions. The
   property under test is how the frame sizes the photo, not which bitmap loads.
2. `demotiles.maplibre.org` → a minimal dark style with no tile sources. The
   affinity cells still come from the backend; only the basemap is a stub, which
   is why the map captures show points on a flat background.

Data for the geography states:

- **Dense**: the real `/run/demo` fixture (`portland_strong`) — 24 cells, 10
  scored, `sufficient: true`, `data_status: "fixture"`.
- **Sparse / unmapped / absent**: sandbox-only scaffolding on a scratch copy of
  the backend (`/tmp/backendrun`, never committed) that replaces the heatmap step
  with four hand-authored cells (London, Manchester, Bristol, Edinburgh), or
  drops the step entirely. These are **hand-authored test fixtures**, labelled
  `fixture` in the payload's `data_status`, used to reach states a live key would
  have to produce. They are not Qloo data.

## 7. Not verified

- **The Vercel preview for this PR was not opened.** `https://adjacent-cinema-git-arena-a4114fe5-adja-385d8a-sohamgaonkhadkar.vercel.app/`
  is unreachable from this sandbox (`curl` returns `000`); all browser evidence
  above comes from an equivalent local production build.
- **Deployed production was not checked**, for the same reason.
- The basemap was stubbed (see §6), so nothing here verifies that
  `demotiles.maplibre.org` loads in a real browser; the component's existing
  "Basemap tiles could not be loaded" fallback still covers that case.
- No live Qloo run: the sparse, unmapped and absent states were reached with
  hand-authored fixtures, so this does not evidence how often a real key returns
  fewer than ten scored cells.
- Fonts were blocked (`fonts.googleapis.com`), which changes typography in the
  captures but not layout geometry.

## 8. Status

Both reported defects have a root-cause fix, regression tests, and browser
evidence from a production build. PR #26 is **open, not merged** — the reviewer
still has to look at the screens, and the two Vercel-preview checks above remain
outstanding from this environment.
