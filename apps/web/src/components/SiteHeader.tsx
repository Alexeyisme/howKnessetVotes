"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { LANG_NAME, LOCALES, localize, type Locale } from "@/i18n/config";
import { SearchBox, type SearchBoxLabels } from "./SearchBox";

/** Layouts survive client navigation; everything dependent on the URL belongs here. */
export function SiteHeader({ locale, brand, language, navigation, items, search }:
  { locale: Locale; brand: string; language: string; navigation: string; items: [string, string][]; search: SearchBoxLabels }) {
  const pathname = usePathname();
  const query = useSearchParams().toString();
  const path = pathname.replace(/^\/(he|en|ru|ar)(?=\/|$)/, "") || "/";
  const section = path.split("/")[1] === "factions" ? "parties" : path.split("/")[1];
  const here = path + (query ? `?${query}` : "");
  return (
    <header className="site-header">
      <div className="wrap">
        <div className="header-row">
          <Link href={localize(locale, "/")} className="brand">{brand}</Link>
          <div className="header-tools">
            {path !== "/" && <>
              <div className="header-search"><SearchBox locale={locale} action={localize(locale, "/search")} labels={search} /></div>
              <Link href={localize(locale, "/search")} className="header-search-icon" aria-label={search.label}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
                  <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
                </svg>
              </Link>
            </>}
            <details className="lang-menu" key={pathname}>
              <summary aria-label={language}>{LANG_NAME[locale]}</summary>
              <nav aria-label={language}>
                {LOCALES.map((l) => (
                  <a key={l} href={localize(l, here)} hrefLang={l} lang={l} aria-current={l === locale ? "true" : undefined}
                     onClick={(event) => {
                       // Read at click time too: quiz answers can change via history.replaceState.
                       event.currentTarget.href = localize(l, path + window.location.search) + window.location.hash;
                     }}>{LANG_NAME[l]}</a>
                ))}
              </nav>
            </details>
          </div>
        </div>
        <nav className="nav" aria-label={navigation}>
          {items.map(([key, label]) => <Link key={key} href={localize(locale, `/${key}`)} aria-current={section === key ? "page" : undefined}>{label}</Link>)}
        </nav>
      </div>
    </header>
  );
}
