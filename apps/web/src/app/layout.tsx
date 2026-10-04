import type { Metadata } from "next";
import Link from "next/link";
import { getStatus } from "@/lib/api";
import { formatDate } from "@/lib/labels";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Как голосует Кнессет", template: "%s · Как голосует Кнессет" },
  description: "Поимённые голосования Кнессета по законопроектам: фракции и депутаты, с источником для каждой цифры.",
};

async function DataAsOf() {
  // the footer must not take the page down if the status endpoint is unavailable
  const data = await getStatus().then((r) => r.data, () => null);
  if (!data) return null;
  return (
    <>Данные обновлены {formatDate(data.published_at.slice(0, 10))}; последнее голосование — {formatDate(data.coverage.last_vote_on)}.{" "}
      {data.coverage.votes.toLocaleString("ru-RU")} голосований, {data.coverage.ballots.toLocaleString("ru-RU")} поимённых записей.</>
  );
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ru">
      <body>
        <header className="site-header">
          <div className="wrap">
            <Link href="/" className="brand">Как голосует Кнессет</Link>
            <nav className="nav" aria-label="Разделы">
              <Link href="/">Голосования</Link>
              <Link href="/topics">Темы</Link>
              <Link href="/bills">Законопроекты</Link>
              <Link href="/members">Депутаты</Link>
              <Link href="/factions">Фракции</Link>
            </nav>
            <form action="/search" className="header-search" role="search">
              <input name="q" placeholder="Поиск: тема, закон, депутат" aria-label="Поиск" dir="auto" />
            </form>
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="wrap small muted" style={{ paddingBottom: 32 }}>
          <p><DataAsOf /></p>
          <p style={{ marginTop: 6 }}>
            Источники: открытые данные Кнессета, сайт Кнессета, Викиданные, <a href="https://oknesset.org" target="_blank" rel="noopener">«Открытый Кнессет»</a>.{" "}
            <Link href="/about/methodology">Методология</Link> · <Link href="/about/glossary">Словарь</Link> · <a href="/docs">API</a>
          </p>
        </footer>
      </body>
    </html>
  );
}
