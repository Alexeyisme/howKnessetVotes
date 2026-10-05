import localFont from "next/font/local";

// Rubik (OFL, see LICENSE-OFL.txt): one family for Latin, Cyrillic, Hebrew and Arabic, so the four sites share one
// voice. Self-hosted: no request to a font CDN. The .woff twins of these files feed the share images (next/og).
export const rubik = localFont({
  variable: "--font-rubik",
  display: "swap",
  src: [
    { path: "./rubik-latin-400-normal.woff2", weight: "400" },
    { path: "./rubik-latin-700-normal.woff2", weight: "700" },
    { path: "./rubik-cyrillic-400-normal.woff2", weight: "400" },
    { path: "./rubik-cyrillic-700-normal.woff2", weight: "700" },
    { path: "./rubik-hebrew-400-normal.woff2", weight: "400" },
    { path: "./rubik-hebrew-700-normal.woff2", weight: "700" },
    { path: "./rubik-arabic-400-normal.woff2", weight: "400" },
    { path: "./rubik-arabic-700-normal.woff2", weight: "700" },
  ],
});
