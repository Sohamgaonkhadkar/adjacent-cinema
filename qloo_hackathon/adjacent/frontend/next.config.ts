import type { NextConfig } from "next";

// Server-side rewrite only. Browser code always calls the relative /api path;
// production must set ADJACENT_API_ORIGIN to the backend origin.
const apiOrigin = (process.env.ADJACENT_API_ORIGIN || "http://127.0.0.1:8000").replace(/\/+$/, "");

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
