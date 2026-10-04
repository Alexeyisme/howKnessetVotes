import type { Metadata } from "next";
import { headers } from "next/headers";
import { notFound } from "next/navigation";
import Link from "@/components/Link";
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

async function LanguageSwitcher() {
  const t = await getT();
  const path = await currentPath();
  return (
    <nav className="lang-switch" aria-label={t.d.nav.language}>
      {LOCALES.map((l) => (
        // plain <a>: a full page load, so the whole tree (direction, names) re-renders in the new language
        <a key={l} href={localize(l, path)} hrefLang={l} lang={l} aria-current={l === t.locale ? "true" : undefined}>{LANG_NAME[l]}</a>
      ))}
    </nav>
  );
}

export default async function RootLayout({ children, params }: LayoutProps<"/[lang]">) {
  if (!isLocale((await params).lang)) notFound();
  const t = await getT();
  const d = t.d;
  return (
    <html lang={t.locale} dir={DIR[t.locale]}>
      <body>
        <header className="site-header">
          <div className="wrap">
            <Link href="/" className="brand">{d.site.name}</Link>
            <nav className="nav" aria-label={d.nav.label}>
              <Link href="/votes">{d.nav.votes}</Link>
              <Link href="/topics">{d.nav.topics}</Link>
              <Link href="/bills">{d.nav.bills}</Link>
              <Link href="/members">{d.nav.members}</Link>
              <Link href="/parties">{d.nav.factions}</Link>
            </nav>
            <form action={t.href("/search")} className="header-search" role="search">
              <input name="q" placeholder={d.nav.searchPh} aria-label={d.nav.searchLabel} dir="auto" />
            </form>
            <LanguageSwitcher />
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="wrap small muted" style={{ paddingBottom: 32 }}>
          <p><DataAsOf /></p>
          <p style={{ marginTop: 6 }}>
            {d.footer.sources} <a href="https://oknesset.org" target="_blank" rel="noopener">{d.footer.oknesset}</a>.{" "}
            <Link href="/about/methodology">{d.footer.methodology}</Link> · <Link href="/about/glossary">{d.footer.glossary}</Link> ·{" "}
            {/* /docs is the API's (FastAPI) page, served by Caddy, not a route of this app */}
            {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
            <a href="/docs">{d.footer.api}</a>
          </p>
        </footer>
      </body>
    </html>
  );
}
