// Locales and URL helpers. Shared by proxy.ts and the app, so no server-only imports here.

export const LOCALES = ["ru", "en", "he"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "ru";
export const LOCALE_COOKIE = "hkv_lang";
/** request header set by proxy.ts: the path without the locale prefix, plus the query string (language switcher, hreflang) */
export const PATH_HEADER = "x-hkv-path";

export const DIR: Record<Locale, "ltr" | "rtl"> = { ru: "ltr", en: "ltr", he: "rtl" };
export const INTL: Record<Locale, string> = { ru: "ru-RU", en: "en-GB", he: "he-IL" };
export const LANG_NAME: Record<Locale, string> = { ru: "Русский", en: "English", he: "עברית" };

export const isLocale = (s: string | null | undefined): s is Locale => !!s && (LOCALES as readonly string[]).includes(s);

/** Paths served by the API (Caddy routes them there), never localized. */
const NOT_LOCALIZED = /^\/(api|docs|openapi\.json)(\/|$|\?)/;

/** "/votes/1" -> "/en/votes/1"; external links, anchors and API paths are returned unchanged. */
export function localize(locale: Locale, href: string): string {
  if (!href.startsWith("/") || href.startsWith("//") || NOT_LOCALIZED.test(href)) return href;
  return href === "/" ? `/${locale}` : href.startsWith("/?") ? `/${locale}${href.slice(1)}` : `/${locale}${href}`;
}

/** Locale from the first matching language in an Accept-Language header. */
export function fromAcceptLanguage(header: string | null): Locale | null {
  if (!header) return null;
  const langs = header.split(",").map((part) => {
    const [tag, ...params] = part.trim().split(";");
    const q = params.map((p) => p.trim()).find((p) => p.startsWith("q="));
    return { lang: tag.toLowerCase().split("-")[0], q: q ? Number(q.slice(2)) || 0 : 1 };
  }).filter((l) => l.q > 0).sort((a, b) => b.q - a.q);
  for (const { lang } of langs) {
    if (lang === "iw") return "he";
    if (isLocale(lang)) return lang;
  }
  return null;
}
