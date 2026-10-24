import assert from "node:assert/strict";
import test from "node:test";
import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
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

async function startMockApiFromBuiltRewrite() {
  const manifestPath = new URL("../.next/routes-manifest.json", import.meta.url);
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  const rewriteGroups = Object.values(manifest.rewrites ?? {});
  const rewrite = rewriteGroups
    .flatMap((group) => Array.isArray(group) ? group : [])
    .find((rule) => rule.source === "/api/:path*" && typeof rule.destination === "string");

  assert.ok(rewrite, "production routes manifest is missing the same-origin /api rewrite");
  const wildcardSuffix = "/:path*";
  const destination = rewrite.destination.endsWith(wildcardSuffix)
    ? rewrite.destination.slice(0, -wildcardSuffix.length)
    : rewrite.destination;
  const target = new URL(destination);
  assert.ok(
    ["127.0.0.1", "localhost", "::1"].includes(target.hostname),
    "proxy smoke test must use its isolated local API origin; got " + target.origin,
  );
  const port = Number(target.port || (target.protocol === "https:" ? 443 : 80));
  const server = createServer((request, response) => {
    if (request.url === "/health") {
      response.writeHead(200, { "content-type": "application/json; charset=utf-8" });
      response.end(JSON.stringify({ status: "ok", service: "adjacent-proxy-smoke" }));
      return;
    }
    response.writeHead(404, { "content-type": "application/json; charset=utf-8" });
    response.end(JSON.stringify({ detail: "Unexpected smoke-test path" }));
  });
  await new Promise((resolve, reject) => {
    const onError = (error) => {
      server.off("listening", onListening);
      reject(new Error("Could not start proxy smoke API on " + target.origin + ": " + error.message));
    };
    const onListening = () => {
      server.off("error", onError);
      resolve();
    };
    server.once("error", onError);
    server.once("listening", onListening);
    server.listen(port);
  });
  return server;
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
        ADJACENT_API_ORIGIN: process.env.ADJACENT_API_ORIGIN ?? "http://127.0.0.1:8000",
      },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  child.stdout.setEncoding("utf8").on("data", (chunk) => { logs += chunk; });
  child.stderr.setEncoding("utf8").on("data", (chunk) => { logs += chunk; });

  let mockApi;
  try {
    mockApi = await startMockApiFromBuiltRewrite();
    await waitForServer(child, baseUrl + "/", () => logs);
    const apiHealth = await fetch(baseUrl + "/api/health", {
      signal: AbortSignal.timeout(5_000),
    });
    assert.equal(apiHealth.status, 200, "/api/health did not reach the configured backend proxy");
    assert.deepEqual(await apiHealth.json(), {
      status: "ok",
      service: "adjacent-proxy-smoke",
    });

    for (const route of routes) {
      const response = await fetch(baseUrl + route, {
        headers: { accept: "text/html" },
        signal: AbortSignal.timeout(10_000),
      });
      const contentType = response.headers.get("content-type") ?? "";
      const html = await response.text();
      assert.equal(response.status, 200, route + " returned HTTP " + response.status + "\n" + logs);
      assert.equal(response.headers.get("x-content-type-options"), "nosniff", route + " missing nosniff header");
      assert.equal(response.headers.get("x-frame-options"), "DENY", route + " missing clickjacking protection");
      assert.equal(response.headers.get("x-powered-by"), null, route + " exposes the framework header");
      assert.match(contentType, /text\/html/i, route + " did not return HTML");
      assert.ok(html.length > 1_000, route + " returned suspiciously little HTML");
      assert.doesNotMatch(
        html,
        /Internal Server Error|Application error: a server-side exception has occurred/i,
        route + " contains a server error page",
      );
      assert.match(html, /<html[\s>]/i, route + " did not render an HTML document");

      // The stylesheet is part of the deliverable: a purge that removes a class
      // the markup still uses ships an unstyled page and nothing else catches it.
      const stylesheet = html.match(/href="(\/_next\/static\/[^"]+\.css)"/);
      assert.ok(stylesheet, route + " did not link a stylesheet");
      const cssResponse = await fetch(baseUrl + stylesheet[1], { signal: AbortSignal.timeout(10_000) });
      assert.equal(cssResponse.status, 200, route + " stylesheet returned HTTP " + cssResponse.status);
      const css = await cssResponse.text();
      for (const selector of [".paper-card", ".film-gate", ".chip-live", ".btn-primary", ".type-kicker", ".img-frame"]) {
        assert.ok(css.includes(selector), route + " stylesheet is missing " + selector);
      }
      for (const utility of [".bg-ink", ".text-amber", ".font-display"]) {
        assert.ok(css.includes(utility), route + " stylesheet is missing the utility " + utility);
      }
    }
  } finally {
    child.kill("SIGTERM");
    await Promise.race([
      new Promise((resolve) => child.once("exit", resolve)),
      delay(5_000),
    ]);
    if (child.exitCode === null) child.kill("SIGKILL");
    if (mockApi) {
      await new Promise((resolve) => mockApi.close(resolve));
    }
  }
});
