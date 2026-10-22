import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const css = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

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

test("responsive intake gives title, year, IMDb and remove control usable grid areas", () => {
  const mobile = mediaBlocks(css, "@media (max-width: 900px)").find((block) =>
    block.includes(".intake-row"),
  );
  assert.ok(mobile, "missing responsive intake grid rule");
  assert.match(
    mobile,
    /\.intake-row\s*\{[^}]*grid-template-columns:\s*22px\s+minmax\(0,\s*1fr\)\s+minmax\(0,\s*1fr\)\s+28px;/s,
  );
  assert.match(
    mobile,
    /grid-template-areas:\s*"idx title title rm"\s*"\. year imdb \."/,
  );
  assert.match(mobile, /\.intake-row-index\s*\{\s*grid-area:\s*idx;/);
  assert.match(
    mobile,
    /\.intake-row-fields:not\(\.intake-year\):not\(\.intake-imdb\)\s*\{\s*grid-area:\s*title;/,
  );
  assert.match(mobile, /\.intake-year\s*\{\s*grid-area:\s*year;/);
  assert.match(mobile, /\.intake-imdb\s*\{\s*grid-area:\s*imdb;/);
  assert.match(mobile, /\.intake-remove\s*\{\s*grid-area:\s*rm;/);
});
