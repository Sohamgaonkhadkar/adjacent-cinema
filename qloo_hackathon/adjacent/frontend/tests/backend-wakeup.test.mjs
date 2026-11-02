import assert from "node:assert/strict";
import test from "node:test";
import {
  BackendHealthError,
  createRun,
  getHealth,
  waitForBackendReady,
} from "../lib/api.ts";

const originalFetch = globalThis.fetch;
const originalNow = Date.now;
let nowOffset = 0;
Date.now = () => originalNow() + nowOffset;

const healthyResponse = () =>
  new Response(JSON.stringify({
    status: "ok",
    service: "adjacent-backend",
    mode: "public_demo",
    public_demo: true,
    live_creator_available: true,
  }), {
    status: 200,
    headers: { "content-type": "application/json" },
  });

test("backend wake-up retries transient cold-start responses until health succeeds", async () => {
  let calls = 0;
  const attempts = [];

  globalThis.fetch = async () => {
    calls += 1;
    if (calls < 3) {
      return new Response(JSON.stringify({ detail: "service is starting" }), {
        status: 503,
        headers: { "content-type": "application/json" },
      });
    }
    return healthyResponse();
  };

  try {
    const health = await waitForBackendReady({
      maxWaitMs: 1_000,
      requestTimeoutMs: 100,
      retryDelayMs: 1,
      onAttempt: (attempt) => attempts.push(attempt),
    });
    assert.equal(health.status, "ok");
    assert.equal(calls, 3);
    assert.deepEqual(attempts, [1, 2, 3]);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("direct page health checks share the recent successful wake-up result", async () => {
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    throw new Error("health cache should have avoided another network call");
  };

  try {
    const health = await getHealth();
    assert.equal(health.status, "ok");
    assert.equal(calls, 0);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("API requests recheck readiness after the health cache expires", async () => {
  nowOffset = 60_000;
  const requested = [];
  globalThis.fetch = async (url, init) => {
    requested.push({ url: String(url), method: init?.method ?? "GET" });
    if (String(url).endsWith("/health")) return healthyResponse();
    if (String(url).endsWith("/run")) {
      return new Response(JSON.stringify({ run_id: "run-after-idle" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }
    throw new Error("Unexpected API request: " + String(url));
  };

  try {
    const run = await createRun({ city: "London", venue_name: "Test House", programme: [] });
    assert.equal(run.run_id, "run-after-idle");
    assert.equal(requested.length, 2);
    assert.ok(requested[0].url.endsWith("/health"));
    assert.equal(requested[1].method, "POST");
    assert.ok(requested[1].url.endsWith("/run"));
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("simultaneous wake-up checks share one health request", async () => {
  nowOffset = 120_000;
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    await new Promise((resolve) => setTimeout(resolve, 5));
    return healthyResponse();
  };

  try {
    const [first, second] = await Promise.all([
      waitForBackendReady({ retryDelayMs: 1 }),
      waitForBackendReady({ retryDelayMs: 1 }),
    ]);
    assert.equal(first.status, "ok");
    assert.equal(second.status, "ok");
    assert.equal(calls, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("backend wake-up stops retrying permanent client errors", async () => {
  nowOffset = 180_000;
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    return new Response(JSON.stringify({ detail: "not found" }), {
      status: 404,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    await assert.rejects(
      waitForBackendReady({
        maxWaitMs: 1_000,
        requestTimeoutMs: 100,
        retryDelayMs: 1,
      }),
      (error) => error instanceof BackendHealthError && error.status === 404,
    );
    assert.equal(calls, 1);
  } finally {
    globalThis.fetch = originalFetch;
    Date.now = originalNow;
  }
});
