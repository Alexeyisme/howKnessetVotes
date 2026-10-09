// Locale-aware helpers for Server Components. The locale is the root [lang] segment (next/root-params), so pages and
// components call getT() instead of passing the language down.

import { lang } from "next/root-params";
import type { FactionNames, PartyRef, PersonNames, Rate } from "@/lib/api";
import { DEFAULT_LOCALE, DIR, INTL, isLocale, localize, type Locale } from "./config";
import { ar } from "./dict/ar";
import { en } from "./dict/en";
import { he } from "./dict/he";
import { ru, type Dict } from "./dict/ru";

const DICTS: Record<Locale, Dict> = { ru, en, he, ar };

export async function getLocale(): Promise<Locale> {
  const l = await lang();
  return isLocale(l) ? l : DEFAULT_LOCALE;
}

export type T = ReturnType<typeof makeT>;

export function makeT(locale: Locale) {
  const intl = INTL[locale];
  const dateFmt = new Intl.DateTimeFormat(intl, { day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jerusalem" });
  const timeFmt = new Intl.DateTimeFormat(intl, { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jerusalem" });
  const pctFmt = new Intl.NumberFormat(intl, { style: "percent", maximumFractionDigits: 1 });
  const d = DICTS[locale];
  const t = {
    locale,
    d,
    dir: DIR[locale],
    href: (path: string) => localize(locale, path),
    num: (n: number) => n.toLocaleString(intl),
    date: (isoDate: string) => dateFmt.format(new Date(`${isoDate.slice(0, 10)}T12:00:00+02:00`)),
    time: (iso: string | null) => (iso ? timeFmt.format(new Date(iso)) : null),
    // Arabic: Intl's percent form keeps "47.4%" in order inside Arabic text (a bare "%" after Arabic words flips to the left)
    pct: (r: Rate) => (r.value == null ? "—" : locale === "ar" ? pctFmt.format(r.value) : `${(r.value * 100).toLocaleString(intl, { maximumFractionDigits: 1 })}%`),
    period: (from: string, to: string | null) => `${t.date(from)} — ${to ? t.date(to) : d.common.present}`,
    /** a member's name in the UI language; Hebrew when there is none (and always in the Hebrew UI) */
    person: (p: PersonNames): string => (locale === "he" ? null : p[`name_${locale}`]) ?? p.name_he,
    /** a faction's short (default) or full name in the UI language, falling back to the official Hebrew name */
    faction: (f: FactionNames, full = false): string => {
      // Hebrew: the official name is the full one (short_he only where it is a long list name)
      const [name, short] = locale === "he" ? [f.name_he, f.short_he] : [f[`name_${locale}`], f[`short_${locale}`]];
      return (full ? name ?? short : short ?? name) ?? f.name_he;
    },
    party: (p: PartyRef) => (locale === "he" ? p.name_he : p[`name_${locale}`] ?? p.name_he),
    topic: (x: { label_ru: string; label_he: string; label_en?: string | null; label_ar?: string | null }) =>
      locale === "ru" ? x.label_ru : locale === "he" ? x.label_he : x[`label_${locale}`] ?? x.label_ru,
    ballot: (choice: "for" | "against" | "abstain" | null, participation: string) =>
      choice ? d.choice[choice] : d.participation[participation] ?? participation,
  };
  return t;
}

export async function getT() {
  return makeT(await getLocale());
}
