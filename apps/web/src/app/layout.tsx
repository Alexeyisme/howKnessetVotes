import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Как голосует Кнессет", template: "%s · Как голосует Кнессет" },
  description: "Поимённые голосования Кнессета по законопроектам: фракции и депутаты, с источником для каждой цифры.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ru">
      <body>
        <header className="site-header">
          <div className="wrap">
            <Link href="/" className="brand">Как голосует Кнессет</Link>
            <span className="muted small">данные: OData Кнессета</span>
          </div>
        </header>
        <main className="wrap">{children}</main>
      </body>
    </html>
  );
}
