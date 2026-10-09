import type { Metadata } from "next";
import { headers } from "next/headers";
import { notFound } from "next/navigation";
import Script from "next/script";
import Link from "@/components/Link";
import { ReportLink } from "@/components/ReportLink";
import { SearchBox } from "@/components/SearchBox";
import { rubik } from "@/fonts";
import { getStatus } from "@/lib/api";
import { DIR, isLocale, LANG_NAME, LOCALES, localize, PATH_HEADER } from "@/i18n/config";
import { getT } from "@/i18n/server";
import "../globals.css";

const SITE_URL = process.env.SITE_URL ?? "https://knessetvotes.org";

/** The current path without the locale (set by proxy.ts), for the language switcher and hreflang links. */
async function currentPath(): Promise<string> {
  return (await headers()).get(PATH_HEADER) ?? "/";
}

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  const path = (await currentPath()).split("?")[0];
  return {
    metadataBase: new URL(SITE_URL),
    title: { default: t.d.site.name, template: `%s · ${t.d.site.name}` },
    description: t.d.site.description,
    alternates: {
      canonical: localize(t.locale, path),
      languages: { ...Object.fromEntries(LOCALES.map((l) => [l, localize(l, path)])), "x-default": path },
    },
  };
}

async function DataAsOf() {
  const t = await getT();
  // the footer must not take the page down if the status endpoint is unavailable
  const data = await getStatus().then((r) => r.data, () => null);
  if (!data) return null;
  return <>{t.d.footer.asOf(t.date(data.published_at), t.date(data.coverage.last_vote_on), t.num(data.coverage.votes), t.num(data.coverage.ballots))}</>;
}

/** Four languages as a small menu (one row of four names took a line of its own on phones). */
async function LanguageSwitcher() {
  const t = await getT();
  const path = await currentPath();
  return (
    <details className="lang-menu">
      <summary aria-label={t.d.nav.language}>{LANG_NAME[t.locale]}</summary>
      <nav aria-label={t.d.nav.language}>
        {LOCALES.map((l) => (
          // plain <a>: a full page load, so the whole tree (direction, names) re-renders in the new language
          <a key={l} href={localize(l, path)} hrefLang={l} lang={l} aria-current={l === t.locale ? "true" : undefined}>{LANG_NAME[l]}</a>
        ))}
      </nav>
    </details>
  );
}

/** Magnifier for the phone header, where the search field has no room. */
function SearchIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
      <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
    </svg>
  );
}

export default async function RootLayout({ children, params }: LayoutProps<"/[lang]">) {
  if (!isLocale((await params).lang)) notFound();
  const t = await getT();
  const d = t.d;
  // the home page has its own large search box; a second one in the header only adds noise there
  const path = (await currentPath()).split("?")[0];
  const home = path === "/";
  // which nav item the page belongs to; faction pages count as "parties"
  const section = path.split("/")[1] === "factions" ? "parties" : path.split("/")[1];
  const navItems: [string, string][] = [["parties", d.nav.factions], ["match", d.nav.match], ["votes", d.nav.votes],
    ["members", d.nav.members], ["topics", d.nav.topics], ["bills", d.nav.bills], ["compare", d.nav.compare]];
  return (
    <html lang={t.locale} dir={DIR[t.locale]} className={rubik.variable}>
      <body>
        <header className="site-header">
          <div className="wrap">
            <div className="header-row">
              <Link href="/" className="brand">{d.site.name}</Link>
              <div className="header-tools">
                {!home && (
                  <>
                    <div className="header-search">
                      <SearchBox locale={t.locale} action={t.href("/search")}
                                 labels={{ placeholder: d.nav.searchPh, label: d.nav.searchLabel, members: d.search.members, parties: d.search.factions, topics: d.search.topics, all: d.common.find }} />
                    </div>
                    <Link href="/search" className="header-search-icon" aria-label={d.nav.searchLabel}><SearchIcon /></Link>
                  </>
                )}
                <LanguageSwitcher />
              </div>
            </div>
            <nav className="nav" aria-label={d.nav.label}>
              {navItems.map(([key, label]) => (
                <Link key={key} href={`/${key}`} aria-current={section === key ? "page" : undefined}>{label}</Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="wrap">
          {/* a version whose translation no native speaker has reviewed says so on every page */}
          {d.translation.beta && (
            <p className="note beta-note" role="note">{d.translation.beta} <Link href="/about/methodology#translation">{d.translation.more}</Link></p>
          )}
          {children}
        </main>
        <footer className="wrap small muted" style={{ paddingBottom: 32 }}>
          <p><DataAsOf /></p>
          <p style={{ marginTop: 6 }}>
            {d.footer.sources} <a href="https://oknesset.org" target="_blank" rel="noopener">{d.footer.oknesset}</a>.{" "}
            <Link href="/about/methodology">{d.footer.methodology}</Link> · <Link href="/about/glossary">{d.footer.glossary}</Link> ·{" "}
            <Link href="/about/methodology#translation">{d.footer.translation}</Link> ·{" "}
            {/* /docs is the API's (FastAPI) page, served by Caddy, not a route of this app */}
            {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
            <a href="/docs">{d.footer.api}</a>
          </p>
          <p style={{ marginTop: 6 }}>
            <ReportLink locale={t.locale} label={d.footer.report} />
          </p>
        </footer>
        {/* page-view counting (Umami, cookie-free; infra/compose.prod.yaml); it follows client-side navigation itself */}
        {process.env.UMAMI_WEBSITE_ID && <Script src="/u/script.js" data-website-id={process.env.UMAMI_WEBSITE_ID} strategy="afterInteractive" />}
      </body>
    </html>
  );
}
