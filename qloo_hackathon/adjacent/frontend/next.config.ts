import type { NextConfig } from "next";

// Server-side rewrite only. Browser code always calls the relative /api path;
// production must set ADJACENT_API_ORIGIN to the backend origin.
const configuredApiOrigin = process.env.ADJACENT_API_ORIGIN || "http://127.0.0.1:8000";
// Render Blueprint references expose private services as host:port. Local/Docker
// origins already include a scheme; normalize both forms for Next.js rewrites.
const apiOrigin = (/^https?:\/\//i.test(configuredApiOrigin)
  ? configuredApiOrigin
  : `http://${configuredApiOrigin}`
).replace(/\/+$/, "");

// `next dev` only serves cross-origin dev requests (HMR, chunk fetches) from
// origins listed here. Sandboxed previews and tunnels need it; production has
// no dev server at all, so this stays empty unless ADJACENT_DEV_ORIGINS is set.
const devOrigins = (process.env.ADJACENT_DEV_ORIGINS || "")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {
  poweredByHeader: false,
  ...(devOrigins.length > 0 ? { allowedDevOrigins: devOrigins } : {}),
  // The Render deployment serves Next.js directly (without the Caddy layer used
  // by Compose), so set baseline browser security headers at the app boundary.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiOrigin}/:path*`,
      },
    ];
  },
};

export default nextConfig;
