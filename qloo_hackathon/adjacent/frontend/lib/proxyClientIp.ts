import { isIP } from "node:net";

export const TRUSTED_CLIENT_IP_HEADER = "x-adjacent-client-ip";
export const TRUSTED_PROXY_TOKEN_HEADER = "x-adjacent-proxy-token";

/**
 * Build request headers for the Next.js-to-Render proxy.
 *
 * Vercel overwrites X-Forwarded-For with the connecting client's address before
 * this code runs. We accept only one valid IP literal, then attest it using a
 * server-side shared secret. Caller-supplied attestation headers are always
 * removed first. If the secret or trusted IP is missing, the backend falls
 * back to the Render edge's CF-Connecting-IP / socket peer.
 */
export function buildTrustedProxyHeaders(
  incoming: Headers,
  sharedSecret: string | undefined,
): Headers {
  const headers = new Headers(incoming);

  // Never relay caller-controlled claims about which proxy or client is trusted.
  headers.delete(TRUSTED_CLIENT_IP_HEADER);
  headers.delete(TRUSTED_PROXY_TOKEN_HEADER);

  const secret = sharedSecret?.trim();
  if (!secret) return headers;

  const clientIp = incoming.get("x-forwarded-for")?.trim();
  if (!clientIp || clientIp.includes(",") || isIP(clientIp) === 0) {
    return headers;
  }

  headers.set(TRUSTED_CLIENT_IP_HEADER, clientIp);
  headers.set(TRUSTED_PROXY_TOKEN_HEADER, secret);
  return headers;
}
