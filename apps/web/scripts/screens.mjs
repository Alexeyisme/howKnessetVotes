// Screenshot matrix for design review: pages × locales × phone/desktop widths (see docs/ux-requirements.md, §5.6).
// Run from apps/web:  npx -y playwright@1 install chromium && node scripts/screens.mjs [base-url] [out-dir]
// Example: node scripts/screens.mjs https://knessetvotes.org ../../data/screens
import { existsSync, mkdirSync } from "node:fs";
import { chromium } from "playwright";

const base = (process.argv[2] ?? "http://localhost:3000").replace(/\/$/, "");
const out = process.argv[3] ?? "screens";
// Stable, representative objects: a contested final vote, the biggest party, a busy MK, the largest topic.
const pages = {
  home: "/", votes: "/votes", vote: "/votes/46611", party: "/parties/likud", member: "/members/12951",
  topic: "/topics/justice", search: "/search?q=likud",
};
const viewports = [["m", 390, 844], ["d", 1280, 900]];
const locales = ["ru", "en", "he"];

mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
for (const [vp, width, height] of viewports) {
  for (const lang of locales) {
    for (const scheme of ["light", "dark"]) {
      const ctx = await browser.newContext({ viewport: { width, height }, colorScheme: scheme });
      const page = await ctx.newPage();
      for (const [name, path] of Object.entries(pages)) {
        const file = `${out}/${name}-${lang}-${vp}-${scheme}.png`;
        if (existsSync(file)) continue; // resumable
        let ok = false;
        for (let i = 0; i < 3 && !ok; i++) {
          try { await page.goto(`${base}/${lang}${path}`, { waitUntil: "load", timeout: 90_000 }); ok = true; }
          catch (e) { console.warn("retry", file, String(e.message).split("\n")[0]); await page.waitForTimeout(2000); }
        }
        if (ok) await page.screenshot({ path: file, fullPage: true });
      }
      await ctx.close();
    }
  }
}
await browser.close();
