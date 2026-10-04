// R9: share images. One frame, one bar, one font (the Rubik .woff subsets; satori does not read woff2), so a vote,
// a party or a member looks the same in a Telegram or WhatsApp preview as on the site. Rendered on request by
// next/og; the font files are traced into the standalone bundle (next.config.ts).

import { readFile } from "node:fs/promises";
import { join } from "node:path";
import bidiFactory from "bidi-js";
import type { ReactNode } from "react";
import { DIR, isLocale, type Locale } from "@/i18n/config";
import { makeT } from "@/i18n/server";

const bidi = bidiFactory();

/** satori has no bidi algorithm: Hebrew and Arabic come out mirrored. Reorder the string into visual order
 *  (UAX #9 via bidi-js: reverse the right-to-left runs, mirror brackets) and draw it left-to-right. One line only —
 *  the images never wrap more than a line of RTL text, which is what the overflow clips enforce. */
export function visual(text: string, dir: "ltr" | "rtl" = "rtl"): string {
  const levels = bidi.getEmbeddingLevels(text, dir);
  const chars = [...text].map((ch, i) => ((levels.levels[i] & 1) ? bidi.getMirroredCharacter(ch) ?? ch : ch));
  for (const [start, end] of bidi.getReorderSegments(text, levels)) {
    const seg = chars.slice(start, end + 1).reverse();
    chars.splice(start, seg.length, ...seg);
  }
  return chars.join("");
}

export const OG_SIZE = { width: 1200, height: 630 };
export const OG_TYPE = "image/png";

const INK = "#0b0b0b", INK2 = "#52514e", MUTED = "#6f6d67", PAGE = "#f9f9f7", TRACK = "#e8e7e2";
export const FOR = "#2a78d6", AGAINST = "#e34948", ABSTAIN = "#b5b3aa";

let fontsPromise: Promise<{ name: string; data: Buffer; weight: 400 | 700; style: "normal" }[]> | null = null;

/** Latin, Cyrillic and Hebrew subsets in both weights; satori falls through the list glyph by glyph. No Arabic:
 *  satori cannot shape Arabic (no joining forms) and its font parser rejects the Arabic subset's GSUB table. */
export function ogFonts() {
  fontsPromise ??= Promise.all(
    (["latin", "cyrillic", "hebrew"] as const).flatMap((s) => ([400, 700] as const).map(async (w) => ({
      name: "Rubik", weight: w, style: "normal" as const,
      data: await readFile(join(process.cwd(), "src", "fonts", `rubik-${s}-${w}-normal.woff`)),
    }))),
  );
  return fontsPromise;
}

/** Labels for the image. Arabic pages get English labels (see ogFonts); the Hebrew title is shown in every language. */
export function ogT(lang: string) {
  const locale: Locale = isLocale(lang) ? lang : "ru";
  return makeT(locale === "ar" ? "en" : locale);
}

/** Text in the UI language, reordered for satori when the language is right-to-left. */
export function T({ locale, children }: { locale: Locale; children: string }) {
  return <>{DIR[locale] === "rtl" ? visual(children, "rtl") : children}</>;
}

/** The frame: content, then the site name in the corner. For Hebrew and Arabic the column is right-aligned and
 *  rows run right-to-left (satori ignores `direction`, so the layout is mirrored by hand). */
export function Frame({ locale, siteName, children }: { locale: Locale; siteName: string; children: ReactNode }) {
  const rtl = DIR[locale] === "rtl";
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", padding: 56,
                  background: PAGE, color: INK, fontFamily: "Rubik" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 18, flex: 1, minHeight: 0, alignItems: rtl ? "flex-end" : "flex-start", textAlign: rtl ? "right" : "left" }}>
        {children}
      </div>
      <div style={{ display: "flex", flexDirection: rtl ? "row-reverse" : "row", justifyContent: "space-between", alignItems: "center", color: MUTED, fontSize: 26 }}>
        <span style={{ fontWeight: 700, color: INK2 }}><T locale={locale}>{siteName}</T></span>
        <span>knessetvotes.org</span>
      </div>
    </div>
  );
}

/** A row of items that runs right-to-left in RTL languages. */
export function Row({ locale, children, style }: { locale: Locale; children: ReactNode; style?: React.CSSProperties }) {
  return <div style={{ display: "flex", flexDirection: DIR[locale] === "rtl" ? "row-reverse" : "row", ...style }}>{children}</div>;
}

/** for | abstain | against on a 120-seat track, the same picture as the VoteCard bar. */
export function PlenumBar({ c, height = 28 }: { c: { for: number; against: number; abstain: number }; height?: number }) {
  const seg = (n: number, color: string) => n > 0 && <div style={{ width: `${(100 * n) / 120}%`, background: color, height: "100%" }} />;
  return (
    <div style={{ display: "flex", width: "100%", height, background: TRACK, borderRadius: height / 2, overflow: "hidden", gap: 3 }}>
      {seg(c.for, FOR)}{seg(c.abstain, ABSTAIN)}{seg(c.against, AGAINST)}
    </div>
  );
}

export const og = { INK, INK2, MUTED };
