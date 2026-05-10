import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Proxy all /api/v1/* requests to the FastAPI backend.
  // This puts both frontend and API on the same origin (localhost:3000),
  // so cookies set by the backend work without any cross-origin issues.
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://127.0.0.1:8000/api/v1/:path*",
      },
    ];
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "i.scdn.co" },
      { protocol: "https", hostname: "mosaic.scdn.co" },
      { protocol: "https", hostname: "*.spotifycdn.com" },
    ],
  },
};

export default nextConfig;
