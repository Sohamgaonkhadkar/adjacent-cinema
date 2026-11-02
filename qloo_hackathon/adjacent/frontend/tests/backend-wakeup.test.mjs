import assert from "node:assert/strict";
import test from "node:test";
import { BackendHealthError, waitForBackendReady } from "../lib/api.ts";

const originalFetch = globalThis.fetch;

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
    return new Response(
      JSON.stringify({
        status: "ok",
        service: "adjacent-backend",
        mode: "public_demo",
        public_demo: true,
        live_creator_available: true,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );
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

test("backend wake-up stops retrying permanent client errors", async () => {
  let calls = 0;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "not found" }), {
      status: (++calls, 404),
      headers: { "content-type": "application/json" },
    });

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
  }
});
