import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const css = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

function mediaBlock(source, header) {
  const start = source.indexOf(header);
  assert.notEqual(start, -1, `missing media rule: ${header}`);
  const open = source.indexOf("{", start);
  assert.notEqual(open, -1, `missing opening brace for ${header}`);
  let depth = 0;
  for (let i = open; i < source.length; i += 1) {
    if (source[i] === "{") depth += 1;
    if (source[i] === "}") {
      depth -= 1;
      if (depth === 0) return source.slice(open + 1, i);
    }
  }
  assert.fail(`unterminated media rule: ${header}`);
}

test("responsive intake gives title, year, IMDb and remove control usable grid areas", () => {
  const mobile = mediaBlock(css, "@media (max-width: 900px)");
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
