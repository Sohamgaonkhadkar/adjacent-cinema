import assert from "node:assert/strict";
import test from "node:test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const frontendDir = fileURLToPath(new URL("..", import.meta.url));
const routes = ["/", "/creator", "/cinema", "/creator/sponsor"];

async function getFreePort() {
  const { createServer } = await import("node:net");
  const server = createServer();
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("Could not reserve a local port");
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  return address.port;
}

async function waitForServer(child, baseUrl, readLogs) {
  const deadline = Date.now() + 30_000;
  let lastError;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error("Next.js exited before readiness (code " + child.exitCode + ").\n" + readLogs());
    }
    try {
      const response = await fetch(baseUrl, { signal: AbortSignal.timeout(2_000) });
      if (response.status === 200) return;
      lastError = new Error("Readiness request returned HTTP " + response.status);
    } catch (error) {
      lastError = error;
    }
    await delay(250);
  }
  throw new Error("Next.js did not become ready: " + String(lastError) + "\n" + readLogs());
}

test("production build renders every primary web surface", async () => {
  const port = await getFreePort();
  const baseUrl = "http://127.0.0.1:" + port;
  let logs = "";
  const child = spawn(
    process.execPath,
    ["node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", String(port)],
    {
      cwd: frontendDir,
      env: {
        ...process.env,
        NODE_ENV: "production",
        NEXT_TELEMETRY_DISABLED: "1",
        ADJACENT_API_ORIGIN: "http://127.0.0.1:8000",
      },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  child.stdout.setEncoding("utf8").on("data", (chunk) => { logs += chunk; });
  child.stderr.setEncoding("utf8").on("data", (chunk) => { logs += chunk; });

  try {
    await waitForServer(child, baseUrl + "/", () => logs);
    for (const route of routes) {
      const response = await fetch(baseUrl + route, {
        headers: { accept: "text/html" },
        signal: AbortSignal.timeout(10_000),
      });
      const contentType = response.headers.get("content-type") ?? "";
      const html = await response.text();
      assert.equal(response.status, 200, route + " returned HTTP " + response.status + "\n" + logs);
      assert.match(contentType, /text\/html/i, route + " did not return HTML");
      assert.ok(html.length > 1_000, route + " returned suspiciously little HTML");
      assert.doesNotMatch(
        html,
        /Internal Server Error|Application error: a server-side exception has occurred/i,
        route + " contains a server error page",
      );
      assert.match(html, /<html[\s>]/i, route + " did not render an HTML document");
    }
  } finally {
    child.kill("SIGTERM");
    await Promise.race([
      new Promise((resolve) => child.once("exit", resolve)),
      delay(5_000),
    ]);
    if (child.exitCode === null) child.kill("SIGKILL");
  }
});
