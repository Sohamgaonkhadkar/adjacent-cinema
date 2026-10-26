import test from "node:test";
import assert from "node:assert/strict";
import {
  buildTrustedProxyHeaders,
  TRUSTED_CLIENT_IP_HEADER,
  TRUSTED_PROXY_TOKEN_HEADER,
} from "../lib/proxyClientIp.ts";

test("strips caller-supplied attestation when no shared secret is configured", () => {
  const incoming = new Headers({
    "x-forwarded-for": "198.51.100.9",
    [TRUSTED_CLIENT_IP_HEADER]: "203.0.113.99",
    [TRUSTED_PROXY_TOKEN_HEADER]: "attacker-controlled",
  });

  const outgoing = buildTrustedProxyHeaders(incoming, undefined);
  assert.equal(outgoing.get("x-forwarded-for"), "198.51.100.9");
  assert.equal(outgoing.has(TRUSTED_CLIENT_IP_HEADER), false);
  assert.equal(outgoing.has(TRUSTED_PROXY_TOKEN_HEADER), false);
});

test("attests one valid Vercel client IP with the server-side shared secret", () => {
  const incoming = new Headers({
    "x-forwarded-for": "198.51.100.9",
    [TRUSTED_CLIENT_IP_HEADER]: "203.0.113.99",
    [TRUSTED_PROXY_TOKEN_HEADER]: "attacker-controlled",
  });

  const outgoing = buildTrustedProxyHeaders(incoming, "preview-secret");
  assert.equal(outgoing.get(TRUSTED_CLIENT_IP_HEADER), "198.51.100.9");
  assert.equal(outgoing.get(TRUSTED_PROXY_TOKEN_HEADER), "preview-secret");
});

test("does not attest a forwarded chain, malformed address, or absent address", () => {
  for (const xff of [
    "198.51.100.9, 10.0.0.1",
    "not-an-ip",
    "",
  ]) {
    const incoming = new Headers({
      "x-forwarded-for": xff,
      [TRUSTED_CLIENT_IP_HEADER]: "203.0.113.99",
      [TRUSTED_PROXY_TOKEN_HEADER]: "attacker-controlled",
    });
    const outgoing = buildTrustedProxyHeaders(incoming, "preview-secret");
    assert.equal(outgoing.has(TRUSTED_CLIENT_IP_HEADER), false);
    assert.equal(outgoing.has(TRUSTED_PROXY_TOKEN_HEADER), false);
  }
});
