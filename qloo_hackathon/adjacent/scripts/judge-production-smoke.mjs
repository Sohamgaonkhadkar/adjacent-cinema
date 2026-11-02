#!/usr/bin/env node
/**
 * Bounded production HTTP smoke for the judge-facing Adjacent Cinema deployment.
 *
 * Verifies live HTTPS responses, the actual same-origin backend proxy, and one
 * explicitly LABELLED fixture run. No Qloo credentials, live Qloo requests,
 * sponsorship writes, or outcome claims. This is NOT a browser interaction test.
 *
 * node scripts/judge-production-smoke.mjs --fixture
 * JUDGE_ORIGIN=https://example.org node scripts/judge-production-smoke.mjs
 */
import { mkdir, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

const origin = (process.env.JUDGE_ORIGIN || "https://adjacent-cinema.vercel.app").replace(/\/+$/, "");
const output = process.env.JUDGE_REPORT || "judge-production-smoke-report.json";
const fixture = process.argv.includes("--fixture");
const base = new URL(origin);
if (base.protocol !== "https:" && !["localhost", "127.0.0.1"].includes(base.hostname)) {
  throw new Error("Remote smoke origin must be HTTPS");
}
if (base.pathname !== "/" || base.search || base.hash || base.username || base.password) {
  throw new Error("Expected a clean site origin, not a URL with path or credentials");
}

const results = [];
const report = {
  schema: "adjacent.judge-production-smoke/1",
  checked_at_utc: new Date().toISOString(),
  origin: base.origin,
  fixture_requested: fixture,
  checks: results,
  status: "in_progress",
  scope: "HTTP route, backend health and labelled-fixture API check; not a browser walkthrough or live-Qloo evaluation.",
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function request(path, init = {}, timeout = 12_000) {
  const response = await fetch(new URL(path, base), {
    ...init,
    redirect: "follow",
    signal: AbortSignal.timeout(timeout),
    headers: {
      "User-Agent": "Adjacent-Judge-Release-Smoke/1",
      "Cache-Control": "no-cache",
      ...(init.headers || {}),
    },
  });
  return response;
}

function check(name, passed, info = "") {
  results.push({ name, status: passed ? "passed" : "failed", detail: info });
  console.log((passed ? "PASS" : "FAIL") + " " + name + (info ? " — " + info : ""));
}

async function fetchHealth() {
  let last = "not attempted";
  for (let i = 0; i < 7; i++) {
    try {
      const response = await request("/api/health", {}, 20_000);
      const text = await response.text();
      const payload = JSON.parse(text);
      if (response.ok && payload.service === "adjacent-backend" && payload.status === "ok") {
        check("same-origin API health", true, `HTTP ${response.status}; mode=${payload.mode || "unspecified"}`);
        report.backend = {
          status: payload.status,
          mode: payload.mode || "unknown",
          public_demo: payload.public_demo === true,
          fixture_demo_available: payload.fixture_demo_available === true,
          live_creator_available: payload.live_creator_available === true,
          filmsponsor_guest_enabled: payload.filmsponsor_guest_enabled === true,
        };
        return payload;
      }
      last = `HTTP ${response.status}; backend response did not match expected health contract`;
    } catch (error) {
      last = error instanceof Error ? error.name : "unavailable";
    }
    if (i < 6) await sleep(6_000);
  }
  check("same-origin API health", false, last);
  return null;
}

async function checkRoutes() {
  for (const [path, expected] of [
    ["/", "Every film belongs"],
    ["/creator", "Creator"],
    ["/cinema", "Cinema"],
    ["/creator/sponsor", "FilmSponsor"],
  ]) {
    try {
      const response = await request(path, { headers: { accept: "text/html" } }, 20_000);
      const html = await response.text();
      const htmlOk = response.status === 200 &&
        /text\/html/.test(response.headers.get("content-type") || "") &&
        html.length > 1_000 && html.includes(expected) &&
        !/Application error: a server-side exception|Internal Server Error/i.test(html);
      const secure = response.headers.get("x-content-type-options") === "nosniff";
      check("page " + path, htmlOk && secure,
        `HTTP ${response.status}; html=${html.length}; nosniff=${secure}`);
    } catch (error) {
      check("page " + path, false, error instanceof Error ? error.name : "fetch error");
    }
  }
}

async function checkSingleFixture(label, path) {
  try {
    const start = await request(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Origin: base.origin },
      body: "{}",
    }, 20_000);
    const payload = await start.json();
    if (!start.ok || typeof payload.run_id !== "string" || !payload.run_id) {
      check(label + " fixture start", false, `HTTP ${start.status}; no usable run_id`);
      return;
    }
    check(label + " fixture start", true, `HTTP ${start.status}`);
    for (let i = 0; i < 20; i++) {
      await sleep(1_500);
      const read = await request("/api/run/" + encodeURIComponent(payload.run_id), {}, 15_000);
      if (!read.ok) {
        check(label + " fixture completion", false, `GET returned HTTP ${read.status}`);
        return;
      }
      const state = await read.json();
      if (state.status === "completed" || state.status === "insufficient" || state.status === "failed") {
        const dataStatus = state.result?.data_status;
        const valid = state.status === "completed" && dataStatus === "fixture";
        check(label + " fixture completion", valid,
          `status=${state.status}; data_status=${dataStatus || "none"}`);
        report[label + "_fixture"] = {
          status: state.status,
          data_status: dataStatus || null,
          stop_reason: state.stop_reason || null,
          trace_count: Array.isArray(state.trace) ? state.trace.length : 0,
        };
        return;
      }
    }
    check(label + " fixture completion", false, "no terminal response in 30 seconds");
  } catch (error) {
    check(label + " fixture", false, error instanceof Error ? error.name : "request error");
  }
}

async function checkFixture(health) {
  if (!fixture) return;
  if (!health || health.fixture_demo_available !== true) {
    check("fixture readiness", false, "backend health absent or fixture not advertised");
    return;
  }
  // Both requests use explicit mock/fixture routes, never spend Qloo quota.
  await checkSingleFixture("cinema", "/api/run/demo");
  await checkSingleFixture("creator", "/api/creator/run/demo");
}

try {
  await checkRoutes();
  const health = await fetchHealth();
  await checkFixture(health);
} finally {
  report.status = results.every((r) => r.status === "passed") ? "passed" : "failed";
  await mkdir(dirname(output), { recursive: true });
  await writeFile(output, JSON.stringify(report, null, 2) + "\n", "utf8");
  console.log("Report:", output, "status:", report.status);
}

if (report.status !== "passed") process.exitCode = 1;
