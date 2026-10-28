import type { NextConfig } from "next";

const apiTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ["127.0.0.1"],
  agentRules: false,
  devIndicators: false,
  async rewrites() {
    // Same-origin /api/* in the browser, proxied to FastAPI. Keeps the client
    // free of cross-origin concerns and avoids a CORS preflight on every add.
    return [
      {
        source: "/api/:path*",
        destination: `${apiTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
