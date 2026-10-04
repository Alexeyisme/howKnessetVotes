import type { Metadata } from "next";
import Link from "@/components/Link";
import { He } from "@/components/ui";
import { glossary } from "@/i18n/content/glossary";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const d = (await getT()).d.glossary;
  return { title: d.title, description: d.description };
}

export default async function Glossary() {
  const t = await getT();
  const terms = glossary(t.locale, t.d, (href, text) => <Link href={href}>{text}</Link>);
  return (
    <article className="stack">
      <header className="page-head">
        <h1>{t.d.glossary.title}</h1>
        <p className="muted">{t.d.glossary.lead}</p>
      </header>
      <dl className="card glossary">
        {terms.map((x) => (
          <div key={x.id} id={x.id} className="glossary-item">
            <dt><strong>{x.term}</strong> {x.he && <He className="muted small">{x.he}</He>}</dt>
            <dd>{x.text}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}
