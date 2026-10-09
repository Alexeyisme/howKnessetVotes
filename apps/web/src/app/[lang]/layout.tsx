import type { Metadata } from "next";
import { headers } from "next/headers";
import { notFound } from "next/navigation";
import Script from "next/script";
import { Suspense } from "react";
import { LangCookie } from "@/components/LangCookie";
import Link from "@/components/Link";
import { ReportLink } from "@/components/ReportLink";
import { SiteHeader } from "@/components/SiteHeader";
import { rubik } from "@/fonts";
import { getStatus } from "@/lib/api";
import { DIR, isLocale, LOCALES, localize, PATH_HEADER } from "@/i18n/config";
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

export default async function RootLayout({ children, params }: LayoutProps<"/[lang]">) {
  if (!isLocale((await params).lang)) notFound();
  const t = await getT();
  const d = t.d;
  const navItems: [string, string][] = [["parties", d.nav.factions], ["match", d.nav.match], ["votes", d.nav.votes],
    ["members", d.nav.members], ["topics", d.nav.topics], ["bills", d.nav.bills], ["compare", d.nav.compare]];
  return (
    <html lang={t.locale} dir={DIR[t.locale]} className={rubik.variable}>
      <body>
        <Suspense fallback={<header className="site-header"><div className="wrap brand">{d.site.name}</div></header>}>
          <SiteHeader locale={t.locale} brand={d.site.name} language={d.nav.language} navigation={d.nav.label} items={navItems}
                      search={{ placeholder: d.nav.searchPh, label: d.nav.searchLabel, members: d.search.members,
                                parties: d.search.factions, topics: d.search.topics, all: d.common.find }} />
        </Suspense>
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
            <a href="/docs">{d.footer.api}</a> ·{" "}
            <a href="https://github.com/Alexeyisme/howKnessetVotes" target="_blank" rel="noopener">{d.footer.source}</a>
          </p>
          <p style={{ marginTop: 6 }}>
            <ReportLink locale={t.locale} label={d.footer.report} />
          </p>
        </footer>
        <LangCookie locale={t.locale} />
        {/* page-view counting (Umami, cookie-free; infra/compose.prod.yaml); it follows client-side navigation itself */}
        {process.env.UMAMI_WEBSITE_ID && <Script src="/u/script.js" data-website-id={process.env.UMAMI_WEBSITE_ID} strategy="afterInteractive" />}
      </body>
    </html>
  );
}
