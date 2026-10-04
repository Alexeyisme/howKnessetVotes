// Locale-aware helpers for Server Components. The locale is the root [lang] segment (next/root-params), so pages and
// components call getT() instead of passing the language down.

import { lang } from "next/root-params";
import type { FactionNames, PersonNames, Rate } from "@/lib/api";
import { DEFAULT_LOCALE, DIR, INTL, isLocale, localize, type Locale } from "./config";
import { en } from "./dict/en";
import { he } from "./dict/he";
import { ru, type Dict } from "./dict/ru";

const DICTS: Record<Locale, Dict> = { ru, en, he };

export async function getLocale(): Promise<Locale> {
  const l = await lang();
  return isLocale(l) ? l : DEFAULT_LOCALE;
}

export type T = ReturnType<typeof makeT>;

export function makeT(locale: Locale) {
  const intl = INTL[locale];
  const dateFmt = new Intl.DateTimeFormat(intl, { day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jerusalem" });
  const timeFmt = new Intl.DateTimeFormat(intl, { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jerusalem" });
  const d = DICTS[locale];
  const t = {
    locale,
    d,
    dir: DIR[locale],
    href: (path: string) => localize(locale, path),
    num: (n: number) => n.toLocaleString(intl),
    date: (isoDate: string) => dateFmt.format(new Date(`${isoDate.slice(0, 10)}T12:00:00+02:00`)),
    time: (iso: string | null) => (iso ? timeFmt.format(new Date(iso)) : null),
    pct: (r: Rate) => (r.value == null ? "—" : `${(r.value * 100).toLocaleString(intl, { maximumFractionDigits: 1 })}%`),
    period: (from: string, to: string | null) => `${t.date(from)} — ${to ? t.date(to) : d.common.present}`,
    /** a member's name in the UI language; Hebrew when there is none (and always in the Hebrew UI) */
    person: (p: PersonNames): string => (locale === "ru" ? p.name_ru : locale === "en" ? p.name_en : null) ?? p.name_he,
    /** a faction's short (default) or full name in the UI language, falling back to the official Hebrew name */
    faction: (f: FactionNames, full = false): string => {
      const [name, short] = locale === "ru" ? [f.name_ru, f.short_ru] : locale === "en" ? [f.name_en, f.short_en] : [null, f.short_he];
      return (full ? name ?? short : short ?? name) ?? f.name_he;
    },
    party: (p: { name_he: string; name_ru: string; name_en: string }) => (locale === "ru" ? p.name_ru : locale === "en" ? p.name_en : p.name_he),
    topic: (x: { label_ru: string; label_he: string; label_en?: string | null }) =>
      locale === "ru" ? x.label_ru : locale === "en" ? x.label_en ?? x.label_ru : x.label_he,
    ballot: (choice: "for" | "against" | "abstain" | null, participation: string) =>
      choice ? d.choice[choice] : d.participation[participation] ?? participation,
  };
  return t;
}

export async function getT() {
  return makeT(await getLocale());
}
