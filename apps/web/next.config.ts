import type { NextConfig } from "next";

const API_URL = process.env.HKV_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // self-contained server bundle for the Docker image (apps/web/Dockerfile)
  output: "standalone",
  // the share images read the font files at request time; the standalone bundle only ships what is traced
  outputFileTracingIncludes: { "/**/opengraph-image": ["./src/fonts/*.woff"] },
  // In production Caddy sends /api to the API before Next sees it; this makes the browser-side search box work in
  // `next dev` / `next start` too.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default nextConfig;
