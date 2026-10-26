import { NextResponse, type NextRequest } from "next/server";
import { buildTrustedProxyHeaders } from "./lib/proxyClientIp";

/**
 * The backend is public, so a custom client-IP header alone is not trustworthy.
 * Stamp one only after the request crosses Vercel's ingress, which overwrites
 * X-Forwarded-For, and only when the Preview/Production server secret is set.
 * The backend verifies the matching token before using the supplied IP.
 */
export function proxy(request: NextRequest) {
  const headers = buildTrustedProxyHeaders(
    request.headers,
    process.env.ADJACENT_PROXY_SHARED_SECRET,
  );
  return NextResponse.next({ request: { headers } });
}

export const config = {
  matcher: ["/api/:path*"],
};
