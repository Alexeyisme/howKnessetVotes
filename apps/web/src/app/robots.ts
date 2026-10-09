import type { MetadataRoute } from "next";

const SITE_URL = process.env.SITE_URL ?? "https://knessetvotes.org";

// Crawlers made most of the traffic (2026-10-09), much of it on URL spaces without end: a correction form per
// translated title, search results, every page of every filtered list. Entity pages stay open and are in the sitemap.
// Cloudflare prepends its content-signals block to this file.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      disallow: ["/*/suggest", "/*/search", "/*/compare?", "/*?*cursor=", "/*?*topic=", "/*?*_rsc=", "/api/", "/u/"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
