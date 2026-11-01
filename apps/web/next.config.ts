import type { NextConfig } from "next";

const API_URL = process.env.HKV_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // self-contained server bundle for the Docker image (apps/web/Dockerfile)
  output: "standalone",
  // the share images read the font files at request time; the standalone bundle only ships what is traced
  outputFileTracingIncludes: { "/**/*": ["./src/fonts/*.woff"] },
  // The API responses cached by fetch (src/lib/api.ts, revalidate 600) stay in Next's in-memory LRU only. On disk the
  // cache keeps one file per API URL and never evicts: crawlers made it 25 GB in three weeks and it filled the
  // server's disk on 2026-11-01.
  cacheMaxMemorySize: 128 * 1024 * 1024,
  experimental: { isrFlushToDisk: false },
  // In production Caddy sends /api to the API before Next sees it; this makes the browser-side search box work in
  // `next dev` / `next start` too.
  // The party compass (parties x topics) was removed on 2026-10-09: a party voting "for a topic" says nothing without
  // knowing what each bill does. Old links go to the topics, where every vote is shown with its bill.
  async redirects() {
    return [
      { source: "/:lang(he|en|ru|ar)/compass", destination: "/:lang/topics", permanent: true },
      { source: "/compass", destination: "/topics", permanent: true },
    ];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default nextConfig;
