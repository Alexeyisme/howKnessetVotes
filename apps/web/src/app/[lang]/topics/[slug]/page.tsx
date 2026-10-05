import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "@/components/Link";
import { TermSelect } from "@/components/TermSelect";
import { TopicFactions } from "@/components/TopicFactions";
import { Title } from "@/components/Title";
import { He } from "@/components/ui";
import { getTopic, NotFound } from "@/lib/api";
import { getT } from "@/i18n/server";

async function load(slug: string, term?: string) {
  try {
    return (await getTopic(slug, { term })).data;
  } catch (e) {
    if (e instanceof NotFound) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: PageProps<"/[lang]/topics/[slug]">): Promise<Metadata> {
  return { title: (await getT()).topic(await load((await params).slug)) };
}

export default async function TopicPage({ params, searchParams }: PageProps<"/[lang]/topics/[slug]">) {
  const { slug } = await params;
  const sp = await searchParams;
  const term = typeof sp.term === "string" && sp.term ? sp.term : undefined;
  const x = await load(slug, term);
  const t = await getT();
  const d = t.d.topic;
  const label = t.topic(x);
  const aliases = (t.locale === "he" ? [] : x[`aliases_${t.locale}`] ?? []).filter((a) => a.toLowerCase() !== label.toLowerCase());

  return (
    <div className="stack">
      <header className="page-head">
        <p className="small muted">{d.kicker}{t.locale !== "he" && <> · <He>{x.label_he}</He></>}</p>
        <h1>{label}</h1>
        {aliases.length > 0 && <p className="small muted">{d.aliases} {aliases.join(", ")}</p>}
      </header>

      <section className="card">
        <h2 className="section-title">{d.factionsTitle(x.term)}</h2>
        <form className="search" action={t.href(`/topics/${slug}`)}>
          <TermSelect value={String(x.term)} />
          <button type="submit">{t.d.common.show}</button>
        </form>
        <p className="small muted" style={{ marginBottom: 12 }}>{d.factionsHint}</p>
        {x.factions.length > 0 ? <TopicFactions rows={x.factions} /> : <p className="muted">{d.none}</p>}
      </section>

      <section>
        <h2 className="section-title">{d.bills(x.bills)}</h2>
        <ul className="card" style={{ listStyle: "none" }}>
          {x.recent_bills.map((b) => (
            <li key={b.id} style={{ padding: "8px 16px", borderBottom: "1px solid var(--hairline)" }}>
              <Link href={`/bills/${b.id}`} style={{ display: "block", fontWeight: 600, color: "var(--ink)" }}><Title he={b.title_he} t={b} compact /></Link>
              <span className="small muted">{t.d.common.term(b.term)}{b.last_vote_on && d.lastVote(t.date(b.last_vote_on))}{b.passed_third_reading && ` · ${t.d.common.passed}`}</span>
            </li>
          ))}
        </ul>
        <p style={{ marginTop: 8 }}><Link href={`/bills?topic=${slug}`}>{d.allBills}</Link></p>
      </section>
    </div>
  );
}
