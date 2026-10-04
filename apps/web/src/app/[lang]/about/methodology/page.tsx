import type { Metadata } from "next";
import Link from "@/components/Link";
import { methodology } from "@/i18n/content/methodology";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const d = (await getT()).d.methodology;
  return { title: d.title, description: d.description };
}

export default async function Methodology() {
  const t = await getT();
  const sections = methodology(t.locale, (href, text) => <Link href={href}>{text}</Link>);
  return (
    <article className="stack prose">
      <header className="page-head">
        <h1>{t.d.methodology.title}</h1>
        <p className="muted">{t.d.methodology.description}</p>
      </header>
      {sections.map((s) => (
        <section key={s.id} className="card" id={s.id}>
          <h2 className="section-title">{s.title}</h2>
          {s.body}
        </section>
      ))}
    </article>
  );
}
