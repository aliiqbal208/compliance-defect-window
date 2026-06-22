/** @type {import('next').NextConfig} */
const BACKEND = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig = {
  async rewrites() {
    // Proxy API calls to the FastAPI backend so the browser stays same-origin.
    return [{ source: "/api/:path*", destination: `${BACKEND}/api/:path*` }];
  },
};

module.exports = nextConfig;
