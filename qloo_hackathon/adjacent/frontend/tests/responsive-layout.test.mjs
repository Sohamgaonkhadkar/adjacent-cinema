import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import test from "node:test";

/**
 * Static responsive-layout gate.
 *
 * There is no browser in CI, so the "does it collapse on a phone" question is
 * answered from the markup and the stylesheet:
 *
 *  - no content grid may hard-code three or more columns below a breakpoint;
 *  - the shell must ship its own mobile navigation, not a shrunken desktop bar;
 *  - the fixed-width rules that pillarbox photography must have a small-screen
 *    override in the stylesheet.
 *
 * These are the failure modes that actually shipped before (a 3-up strategy
 * grid that crushed to 90px cards on a 375px viewport). They are not a
 * substitute for a visual pass, which the handoff notes state plainly.
 */

const root = fileURLToPath(new URL("..", import.meta.url));
const css = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");
const nav = readFileSync(new URL("../components/nf/Nav.tsx", import.meta.url), "utf8");

function mediaBlocks(source, header) {
  const blocks = [];
  let cursor = 0;
  while (true) {
    const start = source.indexOf(header, cursor);
    if (start === -1) break;
    const open = source.indexOf("{", start);
    assert.notEqual(open, -1, `missing opening brace for ${header}`);
    let depth = 0;
    let closed = false;
    for (let i = open; i < source.length; i += 1) {
      if (source[i] === "{") depth += 1;
      if (source[i] === "}") {
        depth -= 1;
        if (depth === 0) {
          blocks.push(source.slice(open + 1, i));
          cursor = i + 1;
          closed = true;
          break;
        }
      }
    }
    assert.ok(closed, `unterminated media rule: ${header}`);
  }
  return blocks;
}

function componentSources() {
  const files = [];
  for (const dir of ["app", "components"]) {
    const walk = (relative) => {
      for (const entry of readdirSync(`${root}${relative}`, { withFileTypes: true })) {
        const next = `${relative}/${entry.name}`;
        if (entry.isDirectory()) walk(next);
        else if (entry.name.endsWith(".tsx")) files.push(next);
      }
    };
    walk(`/${dir}`);
  }
  return files.map((file) => ({ file, source: readFileSync(`${root}${file}`, "utf8") }));
}

test("no view hard-codes three or more content columns below a breakpoint", () => {
  const offenders = [];
  for (const { file, source } of componentSources()) {
    for (const match of source.matchAll(/className=(?:"([^"]*)"|\{`([^`]*)`\})/g)) {
      const classes = (match[1] ?? match[2] ?? "").split(/\s+/);
      for (const token of classes) {
        const unprefixed = /^grid-cols-(\d+)$/.exec(token);
        if (unprefixed && Number(unprefixed[1]) >= 3) {
          offenders.push(`${file}: ${token}`);
        }
      }
    }
  }
  assert.deepEqual(offenders, [], `multi-column grids without a breakpoint: ${offenders.join(", ")}`);
});

test("the shell ships a real mobile navigation instead of a shrunken desktop bar", () => {
  // Desktop links are hidden below `lg`, the toggle is hidden from `lg` up, and
  // the menu button owns its expanded state for assistive technology.
  assert.match(nav, /hidden items-center gap-8 lg:flex/);
  assert.match(nav, /aria-label=\{open \? "Close menu" : "Open menu"\}/);
  assert.match(nav, /aria-expanded=\{open\}/);
  assert.match(nav, /aria-controls="mobile-nav"/);
  assert.match(nav, /className="inline-flex h-11 w-11[^"]*lg:hidden"/);
  assert.match(nav, /id="mobile-nav"[^>]*lg:hidden/);
  // Every destination the design exposes is reachable from the mobile sheet.
  for (const href of ['"/"', '"/creator"', '"/cinema"', '"/creator/sponsor"']) {
    assert.ok(nav.includes(href), `mobile navigation is missing ${href}`);
  }
});

test("the stylesheet keeps small-screen overrides for the fixed-width media frames", () => {
  const narrow = mediaBlocks(css, "@media (max-width: 600px)");
  const reduced = mediaBlocks(css, "@media (prefers-reduced-motion: reduce)");
  assert.ok(reduced.length >= 1, "missing the reduced-motion block");
  assert.ok(narrow.length > 0, "missing the narrow-viewport block");
  const all = narrow.join("\n");
  // The film gate is a fixed 18px pillar on each edge; on a narrow card it must
  // shrink rather than eat the frame.
  assert.match(all, /\.film-gate::before,\s*\n\s*\.film-gate::after/);
  assert.match(all, /width: 10px/);
  assert.match(all, /\.paper-card/);
  // Long provider identifiers must be allowed to wrap instead of overflowing.
  assert.match(css, /overflow-wrap:\s*anywhere/);
  // The ported views carry their breakpoints in Tailwind utilities; the CSS
  // media rules above are the small-screen refinements a utility cannot express.
});

test("reduced-motion visitors get the same layout without the animation", () => {
  const blocks = mediaBlocks(css, "@media (prefers-reduced-motion: reduce)");
  // One global safety net kills every duration; one targets the ported
  // entrance animations that rely on clip-path/transform rather than duration.
  assert.ok(blocks.length >= 2, "expected the global and the component-level block");
  const block = blocks.find((candidate) => candidate.includes(".enter-aperture"));
  assert.ok(block, "no reduced-motion block covers the ported entrance animations");
  for (const selector of [".enter-aperture", ".beam", ".img-frame img", ".drawer-enter"]) {
    assert.ok(block.includes(selector), `reduced-motion block does not neutralise ${selector}`);
  }
  assert.match(block, /animation:\s*none !important/);
  assert.match(block, /transition:\s*none !important/);
});
