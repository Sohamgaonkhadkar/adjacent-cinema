import assert from "node:assert/strict";
import test from "node:test";
import { watchRunWithRecovery } from "../lib/runRecovery.ts";

function fakeTimers() {
  const queue = [];
  return {
    queue,
    schedule(callback, delay) {
      const timer = { callback, delay, cancelled: false };
      queue.push(timer);
      return timer;
    },
    cancel(timer) {
      timer.cancelled = true;
    },
    async runNext() {
      const timer = queue.shift();
      assert.ok(timer, "expected exactly one scheduled retry");
      if (!timer.cancelled) timer.callback();
      await new Promise((resolve) => setImmediate(resolve));
    },
  };
}

function fakeStream() {
  let onError;
  let stopped = false;
  return {
    start: (_id, _onEvent, onStreamError) => {
      onError = onStreamError;
      return () => { stopped = true; };
    },
    disconnect: () => onError(new Error("simulated SSE disconnect")),
    isStopped: () => stopped,
  };
}

test("transient SSE disconnect reconciles a running record until completed", async () => {
  const timers = fakeTimers();
  const stream = fakeStream();
  const observed = [];
  let polls = 0;
  let current = true;
  let exhausted = 0;
  const stop = watchRunWithRecovery("run-1", {
    isCurrent: () => current,
    stream: stream.start,
    fetchRun: async (runId) => {
      assert.equal(runId, "run-1");
      polls += 1;
      return { status: polls === 1 ? "running" : "completed" };
    },
    onEvent: () => {},
    onRun: (run) => observed.push(run.status),
    onExhausted: () => exhausted++,
    delaysMs: [10, 20],
    schedule: timers.schedule,
    cancel: timers.cancel,
  });

  stream.disconnect();
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(observed, ["running"]);
  assert.equal(timers.queue.length, 1);
  assert.equal(timers.queue[0].delay, 10);
  await timers.runNext();
  assert.deepEqual(observed, ["running", "completed"]);
  assert.equal(timers.queue.length, 0);
  assert.equal(exhausted, 0);
  assert.equal(stream.isStopped(), true);
  current = false;
  stop();
});

test("a reconciled terminal failure stops without scheduling another poll", async () => {
  const timers = fakeTimers();
  const stream = fakeStream();
  const observed = [];
  let exhausted = 0;
  const stop = watchRunWithRecovery("run-2", {
    isCurrent: () => true,
    stream: stream.start,
    fetchRun: async () => ({ status: "failed" }),
    onEvent: () => {},
    onRun: (run) => observed.push(run.status),
    onExhausted: () => exhausted++,
    schedule: timers.schedule,
    cancel: timers.cancel,
  });

  stream.disconnect();
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(observed, ["failed"]);
  assert.equal(timers.queue.length, 0);
  assert.equal(exhausted, 0);
  assert.equal(stream.isStopped(), true);
  stop();
});

test("stopping a watch cancels its sole pending retry and suppresses further fetches", async () => {
  const timers = fakeTimers();
  const stream = fakeStream();
  let polls = 0;
  const stop = watchRunWithRecovery("run-3", {
    isCurrent: () => true,
    stream: stream.start,
    fetchRun: async () => {
      polls += 1;
      return { status: "running" };
    },
    onEvent: () => {},
    onRun: () => {},
    onExhausted: () => assert.fail("unexpected exhaustion"),
    schedule: timers.schedule,
    cancel: timers.cancel,
  });
  stream.disconnect();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(timers.queue.length, 1);
  stop();
  assert.equal(timers.queue[0].cancelled, true);
  assert.equal(stream.isStopped(), true);
  await timers.runNext();
  assert.equal(polls, 1);
});
