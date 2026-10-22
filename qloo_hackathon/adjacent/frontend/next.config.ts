import type { NextConfig } from "next";

// Server-side rewrite only. Browser code always calls the relative /api path;
// production must set ADJACENT_API_ORIGIN to the backend origin.
const configuredApiOrigin = process.env.ADJACENT_API_ORIGIN || "http://127.0.0.1:8000";
// Render Blueprint references expose private services as host:port. Local/Docker
// origins already include a scheme; normalize both forms for Next.js rewrites.
const apiOrigin = ( /^https?:\/\//i.test(configuredApiOrigin)
  ? configuredApiOrigin
  : `http://${configuredApiOrigin}`
).replace(/\/+$/, "");

const nextConfig: NextConfig = {
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
