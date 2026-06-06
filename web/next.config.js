/** @type {import('next').NextConfig} */
const API_BASE = process.env.API_BASE || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    // Proxy /api/* to the FastAPI backend so the browser talks same-origin.
    return [{ source: "/api/:path*", destination: `${API_BASE}/api/:path*` }];
  },
};

module.exports = nextConfig;
