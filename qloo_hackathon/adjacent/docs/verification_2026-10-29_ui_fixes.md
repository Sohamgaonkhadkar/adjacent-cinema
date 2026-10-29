# Verification — stage photograph and geography panel fixes (2026-10-29)

Scope: PR #26, branch `arena/a4114fe5-adjacent-cinema`, commit `232942d`.

Two UI defects were reported after PR #24 shipped:

1. Cinema/Cultural Multiverse photographs rendering as a thin strip at the top of
   a large empty dark column.
2. The Geography panel showing a large dashed box reading "MAP WITHHELD —
   INSUFFICIENT GEOGRAPHIC EVIDENCE".

This note records what was measured, and — in the last section — what was not.

## 1. Stage photograph: root cause

**The frame was never tall enough to show the photograph, because the
photograph's figure never became absolutely positioned.**

Tailwind emits the position utilities in a fixed order. Read from the compiled
stylesheet of the current production build
(`.next/static/chunks/*.css`):

| class | byte offset in the stylesheet |
| --- | --- |
| `.absolute` | 8148 |
| `.fixed` | 8176 |
| `.relative` | 8198 |
| `.sticky` | 8226 |

Equal specificity, so `.relative` wins. `PhotoFrame` rendered
`cn("relative", className)` — a hard-coded `relative` ahead of whatever the
caller passed. Every call site asking to fill its container (`absolute inset-0`)
therefore resolved to `position: relative`:

- the `<figure>` stayed in normal flow, so its height stayed `auto`;
- `.img-frame { height: 100% }` resolved against `auto`, which is `auto`;
- `.img-frame { min-height }` (10rem desktop, 8rem under 600px) became the height;
- the sibling `absolute inset-0` gradient overlay still covered the whole
  `min-h-[300px]`/`[380px]` container.

That is the reported picture: a ~160px band of photography above an empty dark
column. It is also why PR #24's change — adding `absolute inset-0 h-full w-full`
to the arena's `PhotoFrame` — could not have worked: the class was emitted and
then overridden by the component's own `relative`.

`fill` now sets `position: absolute; inset: 0` as an inline style, which no
utility order can override, and the call sites below use it:

| File | Call site |
| --- | --- |
| `components/nf/PositioningArena.tsx` | strategy stage |
| `components/nf/HomeMultiverse.tsx` | Anchor stage |
| `components/nf/HomeMultiverse.tsx` | Bridge stage (two frames) |
| `components/nf/HomeMultiverse.tsx` | Frontier stage |
| `components/nf/HomeMultiverse.tsx` | dossier photograph |

The Anchor, Bridge and dossier frames had a second instance of the same class of
bug on the single-column layout: `h-full` inside a container whose height was
only a `min-height`, so the frame fell back to 10rem there too.

## 2. Geography: root cause and what the page now says

Backend (`backend/app/domain/geography.py`): cells without an affinity are
dropped, then `sufficient = len(scored) >= 10`, and `to_dict()` sends only
`highest_affinity_cells` (the top ten scored cells).

Traced payload from the local `/run/demo` route (fixture `portland_strong`,
labelled fixture data):

```
total_cells: 24   sufficient: true   highest_affinity_cells: 10 scored   note: ""
```

Frontend (before): `hasGeography = Boolean(geography?.sufficient && …)`. The
claim gate decided whether anything rendered, the fallback text asserted "No
usable coordinates returned", and the table of returned cells was hidden behind
the same flag. A live run with 1–9 scored cells therefore produced an empty box
plus a statement that was not true.

Frontend (after, `lib/geographyView.ts`): scored cells are always plotted;
density shading requires the ≥10 budget and is withheld below it (the points are
still drawn, labelled "Coverage n of 10 cells · density surface withheld"); cells
returned without an affinity get a factual panel (city, cells returned, 0 with
affinity, map not drawn); a run with no artefact says so instead of implying a
measured absence. No pin, coordinate or measurement is invented, and the backend
threshold is unchanged.

## 3. What was run

- `npm run build` (Turbopack + TypeScript): pass.
- 12 node suites, 134 assertions: pass, including the new
  `tests/geography-view.test.mjs` (8 cases).
- `npm run test:render` against the production build: pass. It now reads the
  rendered HTML and emitted CSS and asserts the `.absolute`/`.relative` order,
  that no rendered photograph carries both, and that the home page's fill
  photograph has an explicit absolute position.
- Local `/run/demo` payload trace (above).

## 4. What was not run

- **No rendered-screen screenshots and no browser DOM/computed-style
  inspection.** No browser engine could be installed in this environment:
  Playwright's download CDN is unreachable, `@sparticuz/chromium` fails on a
  missing `libnspr4`/`libnss3`, PySide6's QtWebEngine needs GL/NSS libraries that
  are not present, and the Debian mirrors are unreachable, so the missing
  libraries cannot be installed. The CSS-order evidence above comes from the
  built stylesheet, not from `getComputedStyle`.
- The "below the claim budget" and "cells returned without affinity" panels are
  covered by unit tests and markup inspection only; no live Qloo run produced
  those payloads in this environment.
- Deployed production was not checked.

Both issues therefore stay open until someone has looked at the rendered page.
