import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import test from "node:test";

/**
 * Frontend <-> backend contract gate.
 *
 * The frontend is a thin typed client over the FastAPI app: every request it
 * makes must correspond to a route that actually exists, and every body it
 * sends must only use fields the backend model accepts. Both directions have
 * broken before (a renamed route, a stale field name), and both fail here
 * without a browser, a database or a provider key.
 *
 * The backend source is read, not imported — this suite runs under Node.
 */

const backendApiDir = fileURLToPath(new URL("../../backend/app/api/", import.meta.url));
const apiSource = await readFile(new URL("../lib/api.ts", import.meta.url), "utf8");
const creatorPage = await readFile(new URL("../app/creator/page.tsx", import.meta.url), "utf8");
const cinemaPage = await readFile(new URL("../app/cinema/page.tsx", import.meta.url), "utf8");
const sponsorPage = await readFile(
  new URL("../app/creator/sponsor/page.tsx", import.meta.url),
  "utf8",
);
const archive = await readFile(new URL("../components/nf/CreatorArchive.tsx", import.meta.url), "utf8");

// ─── backend: routes and request models ─────────────────────────────────────

const backendFiles = (await readdir(backendApiDir)).filter((name) => name.endsWith(".py"));
const backendSource = (
  await Promise.all(backendFiles.map((name) => readFile(`${backendApiDir}${name}`, "utf8")))
).join("\n");

const routes = [];
// App-level routes (e.g. `/health`) live in main.py and carry no router prefix.
const routeSources = [
  ...backendFiles.map((file) => ({ file, path: `${backendApiDir}${file}` })),
  { file: "main.py", path: fileURLToPath(new URL("../../backend/app/main.py", import.meta.url)) },
];
for (const { file, path } of routeSources) {
  const source = await readFile(path, "utf8");
  const prefixMatch = source.match(/APIRouter\(([^)]*)\)/);
  const prefix =
    prefixMatch && /prefix="([^"]*)"/.test(prefixMatch[1])
      ? prefixMatch[1].match(/prefix="([^"]*)"/)[1]
      : "";
  const pattern = /@(?:router|app)\.(get|post|put|patch|delete)\(\s*"([^"]*)"/g;
  for (const match of source.matchAll(pattern)) {
    routes.push({ method: match[1].toUpperCase(), path: prefix + match[2], file });
  }
}

/** Field names of a pydantic model, as written in the backend source. */
function modelFields(className) {
  const start = backendSource.indexOf(`class ${className}(BaseModel)`);
  assert.notEqual(start, -1, `backend model ${className} not found`);
  const body = backendSource.slice(start);
  const end = body.search(/\nclass |\n# ---/);
  const block = end === -1 ? body : body.slice(0, end);
  return new Set(
    [...block.matchAll(/^\s{4}([a-z_][a-z0-9_]*)\s*:/gm)].map((match) => match[1]),
  );
}

// ─── frontend: the calls the client actually makes ──────────────────────────

function frontendCalls() {
  const calls = new Map(); // "METHOD /path" -> call site kind

  const record = (method, literal, kind) => {
    const raw = literal.replace(/\$\{[^}]*\}/g, "{param}");
    if (raw.includes("{param}${") || !raw.startsWith("/")) return;
    const normalised = raw.replace(/\/+/g, "/").replace(/\?.*$/, "").replace(/\/+$/, "");
    calls.set(`${method} ${normalised}`, kind);
  };

  // The client always goes through one of these helpers.
  const helperPatterns = [
    /fetch\(\s*`\$\{API_BASE\}([^`]*)`/g,
    /fetchWithTimeout\(\s*`([^`]+)`/g,
    /fetchWithTimeout\(\s*"([^"]+)"/g,
    /fetchJsonWithTimeout(?:<[^>]*>)?\(\s*`([^`]+)`/g,
    /fetchJsonWithTimeout(?:<[^>]*>)?\(\s*"([^"]+)"/g,
  ];
  for (const pattern of helperPatterns) {
    for (const match of apiSource.matchAll(pattern)) {
      const window = apiSource.slice(match.index, match.index + 260);
      const method = window.match(/method:\s*"([A-Z]+)"/);
      record(method ? method[1] : "GET", match[1], match[1].startsWith("/filmsponsor") ? "sponsorFetch" : "fetch");
    }
  }
  // These two read helpers encapsulate a fetch, so the route's HTTP method is GET.
  // Record their call sites directly instead of guessing from nearby code text.
  for (const match of apiSource.matchAll(/sponsorFetchJson(?:<[^>]*>)?\(\s*`([^`]+)`/g)) {
    record("GET", match[1], "sponsorFetchJson");
  }
  for (const match of apiSource.matchAll(/sponsorFetchJson(?:<[^>]*>)?\(\s*"([^"]+)"/g)) {
    record("GET", match[1], "sponsorFetchJson");
  }
  for (const match of apiSource.matchAll(/postJson(?:<[^>]*>)?\(\s*`([^`]+)`/g)) {
    record("POST", match[1], "postJson");
  }
  for (const match of apiSource.matchAll(/postJson(?:<[^>]*>)?\(\s*"([^"]+)"/g)) {
    record("POST", match[1], "postJson");
  }
  // Paths chosen at runtime before being posted (Creator live vs fixture).
  for (const match of apiSource.matchAll(/const path = isDemo \? "([^"]+)" : "([^"]+)"/g)) {
    record("POST", match[1], "createCreatorRun");
    record("POST", match[2], "createCreatorRun");
  }
  return calls;
}

const calls = frontendCalls();
const routeKeys = new Set(routes.map((route) => `${route.method} ${route.path}`));

/** `{param}` in a frontend call must line up with `{placeholder}` in the route. */
function matchesRoute(key) {
  if (routeKeys.has(key)) return true;
  const [method, path] = key.split(" ");
  const wanted = path.split("/");
  return routes.some((route) => {
    if (route.method !== method) return false;
    const parts = route.path.split("/");
    if (parts.length !== wanted.length) return false;
    return parts.every((part, index) => part.startsWith("{") || part === wanted[index]);
  });
}

test("every request the client makes is a route the backend serves", () => {
  const missing = [...calls.keys()].filter((key) => !matchesRoute(key));
  assert.deepEqual(missing, [], `frontend calls with no backend route: ${missing.join(", ")}`);
  assert.ok(calls.size >= 18, `expected the client to cover the product surface, saw ${calls.size}`);
});

test("the client covers the read, write and streaming operations the product needs", () => {
  for (const required of [
    "POST /run",
    "POST /run/demo",
    "GET /run/{param}",
    "POST /creator/run",
    "POST /creator/run/demo",
    "GET /experiments",
    "GET /experiments/{param}",
    "POST /experiments",
    "POST /experiments/{param}/observations",
    "POST /experiments/{param}/evaluations",
    "GET /creator/synthesis-status",
    "POST /creator/synthesize",
    "GET /youtube/status",
    "POST /youtube/disconnect",
    "POST /experiments/{param}/observations/from-youtube",
    "POST /filmsponsor/guest-session",
    "GET /filmsponsor/campaigns",
    "POST /filmsponsor/campaigns",
    "POST /filmsponsor/campaigns/{param}/discover",
    "POST /filmsponsor/campaigns/{param}/drafts",
    "POST /filmsponsor/campaigns/{param}/drafts/{param}/source-reviews",
    "POST /filmsponsor/campaigns/{param}/drafts/{param}/approve",
    "POST /filmsponsor/campaigns/{param}/outreach",
    "GET /filmsponsor/campaigns/{param}/export",
  ]) {
    assert.ok(calls.has(required), `client no longer calls ${required}`);
    assert.ok(matchesRoute(required), `backend no longer serves ${required}`);
  }
});

// ─── request bodies: only fields the backend declares ───────────────────────

/** Keys of a TS object literal body, ignoring nested objects one level deep. */
function objectKeys(source, anchor) {
  const start = source.indexOf(anchor);
  assert.notEqual(start, -1, `anchor not found: ${anchor}`);
  const open = anchor.trimEnd().endsWith("{")
    ? start + anchor.trimEnd().length - 1
    : source.indexOf("{", start + anchor.length);
  assert.notEqual(open, -1, `no object literal after ${anchor}`);
  let depth = 0;
  let end = open;
  for (let index = open; index < source.length; index += 1) {
    if (source[index] === "{") depth += 1;
    else if (source[index] === "}") {
      depth -= 1;
      if (depth === 0) {
        end = index;
        break;
      }
    }
  }
  const body = source.slice(open + 1, end);
  const keys = new Set();
  let level = 0;
  let line = "";
  for (const char of body) {
    if (char === "{" || char === "[" || char === "(") level += 1;
    if (char === "}" || char === "]" || char === ")") level -= 1;
    if (char === "\n" && level === 0) {
      const key = line.match(/^\s*([a-z_][a-z0-9_]*)\s*:/);
      if (key) keys.add(key[1]);
      line = "";
    } else {
      line += char;
    }
  }
  const tail = line.match(/^\s*([a-z_][a-z0-9_]*)\s*:/);
  if (tail) keys.add(tail[1]);
  return keys;
}

function assertSubset(keys, modelName, label) {
  const allowed = modelFields(modelName);
  const extra = [...keys].filter((key) => !allowed.has(key));
  assert.deepEqual(extra, [], `${label} sends fields ${modelName} does not accept: ${extra.join(", ")}`);
  assert.ok(keys.size > 0, `${label} sent an empty body`);
}

test("parsed request bodies only use fields the backend models declare", () => {
  assertSubset(
    new Set(["city", "venue_name", "programme"]),
    "RunRequest",
    "POST /run (lib/api.ts createRun)",
  );
  assertSubset(
    objectKeys(apiSource, "export interface CreatorRunRequest"),
    "CreatorRunRequest",
    "POST /creator/run (CreatorRunRequest interface)",
  );
  assertSubset(
    objectKeys(creatorPage, "await saveExperiment({"),
    "SaveExperimentRequest",
    "Creator save",
  );
  assertSubset(
    objectKeys(archive, "await addObservation(experiment.experiment_id, {"),
    "ObservationRequest",
    "CreatorArchive observation",
  );
  assertSubset(
    objectKeys(archive, "await addEvaluation(experiment.experiment_id, {"),
    "EvaluationRequest",
    "CreatorArchive evaluation",
  );
  assertSubset(
    objectKeys(archive, "await recordYouTubeObservation(experimentId, {"),
    "FromYouTubeObservationRequest",
    "CreatorArchive YouTube observation",
  );
  assertSubset(
    objectKeys(sponsorPage, "await createSponsorCampaign({"),
    "CreateCampaignRequest",
    "FilmSponsor campaign create",
  );
  assertSubset(
    objectKeys(sponsorPage, "await saveSponsorDraft(detail.campaign.campaign_id, {"),
    "SaveDraftRequest",
    "FilmSponsor draft",
  );
  assertSubset(
    objectKeys(sponsorPage, "await addSponsorSourceReview(detail.campaign.campaign_id, draftId, {"),
    "SourceReviewRequest",
    "FilmSponsor source review",
  );
  assertSubset(
    objectKeys(sponsorPage, "await addSponsorOutreach(detail.campaign.campaign_id, {"),
    "OutreachRequest",
    "FilmSponsor outreach",
  );
});

test("run, fixture, session-revoke and YouTube-disconnect writes use bounded requests", () => {
  const section = (start, end) => {
    const from = apiSource.indexOf(start);
    assert.notEqual(from, -1, `function not found: ${start}`);
    const to = apiSource.indexOf(end, from + start.length);
    assert.notEqual(to, -1, `function boundary not found: ${end}`);
    return apiSource.slice(from, to);
  };
  const createRun = section("export async function createRun", "export async function getRun");
  const createDemoRun = section("export async function createDemoRun", "export function streamRun");
  const revokeGuest = section("export async function revokeSponsorGuestSession", "async function sponsorFetch");
  const disconnectYouTube = section("export async function disconnectYouTube", "// ── Role-B synthesis");
  assert.match(createRun, /fetchJsonWithTimeout/);
  assert.match(createDemoRun, /fetchJsonWithTimeout/);
  assert.match(revokeGuest, /fetchWithTimeout/);
  assert.match(disconnectYouTube, /fetchJsonWithTimeout/);
  for (const [name, source] of [["createRun", createRun], ["createDemoRun", createDemoRun], ["revoke guest", revokeGuest], ["disconnect YouTube", disconnectYouTube]]) {
    assert.doesNotMatch(source, /await fetch\(/, `${name} must not bypass the abort-aware timeout helpers`);
  }
});

test("run, experiment, provider and synthesis reads use bounded JSON requests", () => {
  const section = (start, end) => {
    const from = apiSource.indexOf(start);
    assert.notEqual(from, -1, `function not found: ${start}`);
    const to = apiSource.indexOf(end, from + start.length);
    assert.notEqual(to, -1, `function boundary not found: ${end}`);
    return apiSource.slice(from, to);
  };
  const reads = [
    ["getRun", section("export async function getRun", "/**\n * Start the explicitly labelled fixture demo run")],
    ["getExperiment", section("export async function getExperiment", "// ---------------------------------------------------------------------------\n// YouTube integration")],
    ["youtubeStatus", section("export async function youtubeStatus", "/** Begins the consent flow")],
    ["youtubeVideos", section("export async function youtubeVideos", "export async function youtubeMetrics")],
    ["youtubeMetrics", section("export async function youtubeMetrics", "export async function recordYouTubeObservation")],
    ["getSynthesisStatus", section("export async function getSynthesisStatus", "export function synthesizeRun")],
  ];
  for (const [name, source] of reads) {
    assert.match(source, /fetchJsonWithTimeout/, `${name} must use the bounded JSON request helper`);
    assert.doesNotMatch(source, /await fetch\(/, `${name} must not bypass the abort-aware timeout helper`);
  }
});

test("JSON bodies remain under the request timeout for write and FilmSponsor responses", () => {
  const section = (start, end) => {
    const from = apiSource.indexOf(start);
    assert.notEqual(from, -1, `function not found: ${start}`);
    const to = end ? apiSource.indexOf(end, from + start.length) : apiSource.length;
    assert.notEqual(to, -1, `function boundary not found: ${end}`);
    return apiSource.slice(from, to);
  };
  const postJson = section("async function postJson<T>", "export function createCreatorRun");
  const sponsorJson = section("async function sponsorFetchJson<T>", "async function postJson<T>");
  const sponsorGet = section("export async function getSponsorCampaign", "/**\n * Runs live Qloo brand discovery");
  const sponsorExport = section("export async function exportSponsorCampaign", null);
  assert.match(postJson, /fetchJsonWithTimeout/);
  assert.match(sponsorJson, /fetchJsonWithTimeout/);
  assert.match(sponsorGet, /sponsorFetchJson/);
  assert.match(sponsorExport, /sponsorFetchJson/);
  for (const [name, source] of [["postJson", postJson], ["sponsor campaign lookup", sponsorGet], ["sponsor export", sponsorExport]]) {
    assert.doesNotMatch(source, /await res\.json\(/, `${name} must not parse the body after clearing the timeout`);
  }
});

test("the synthesized decision brief is requested by run id", () => {
  assert.match(apiSource, /postJson<SynthesisResponse>\("\/creator\/synthesize", \{ run_id: runId \}/);
  assert.ok(modelFields("SynthesizeRequest").has("run_id"));
});

// ─── honesty rules the UI must keep ────────────────────────────────────────

test("a run is only treated as complete when the backend said so and returned a result", () => {
  assert.match(creatorPage, /validResult/);
  assert.match(creatorPage, /data_status/);
  assert.match(cinemaPage, /data_status/);
  // Fixture runs must reach the UI through the labelled demo endpoint.
  assert.match(apiSource, /\/run\/demo/);
  assert.match(apiSource, /\/creator\/run\/demo/);
  // The failure panel must quote the backend's own stop message.
  assert.match(cinemaPage, /run\?\.stop_message/);
  assert.match(creatorPage, /run\?\.stop_message/);
});

test("Cinema live runs require at least one explicit IMDb ID before making a request", () => {
  // The public backend intentionally does not guess title matches. Keep that
  // constraint visible and validate before starting a run, rather than letting
  // the analysis fail after the UI has shown progress.
  assert.ok(cinemaPage.includes("aria-label={`IMDb ID ${index + 1}`}"));
  assert.ok(cinemaPage.includes('imdbId: item.imdb_id ?? ""'), "loading the sample programme should prefill its known IMDb IDs");
  assert.match(cinemaPage, /imdb_id: imdbId \|\| undefined/);
  assert.match(cinemaPage, /if \(!items\.some\(\(item\) => item\.imdb_id\)\)/);
  assert.match(cinemaPage, /Live analysis needs an IMDb ID for at least one film/);
});

test("writes are idempotent on content, so a retry cannot duplicate a record", async () => {
  const { stableRequestId } = await import("../lib/requestId.ts");
  const payload = { kind: "ANALYTICS", metrics: { views: 12, watch_time_minutes: null } };
  assert.equal(stableRequestId("obs-x", payload), stableRequestId("obs-x", payload));
  assert.notEqual(stableRequestId("obs-x", payload), stableRequestId("obs-x", { ...payload, kind: "SURVEY" }));
  assert.notEqual(
    stableRequestId("obs-x", { a: 1, b: 2 }),
    stableRequestId("obs-x", { a: 2, b: 1 }),
  );
  for (const source of [archive, sponsorPage, apiSource]) {
    assert.doesNotMatch(source, /request_id:\s*`[^`]*\$\{Date\.now\(\)\}/);
    assert.doesNotMatch(source, /request_id:\s*`[^`]*\$\{crypto\.randomUUID\(\)\}/);
  }
  assert.match(archive, /stableRequestId\(`obs-\$\{experiment\.experiment_id\}`/);
  assert.match(archive, /stableRequestId\(`eval-\$\{experiment\.experiment_id\}`/);
  assert.match(sponsorPage, /stableRequestId\(`spd-draft-\$\{detail\.campaign\.campaign_id\}`/);
  assert.match(sponsorPage, /stableRequestId\(`spd-out-\$\{detail\.campaign\.campaign_id\}`/);
});
