import type { Metadata } from "next";
import Link from "@/components/Link";
import { FactionName, He, PersonName } from "@/components/ui";
import { search } from "@/lib/api";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.search.title };
}

export default async function SearchPage({ searchParams }: PageProps<"/[lang]/search">) {
  const t = await getT();
  const d = t.d.search;
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q.trim() : "";
  const r = q.length >= 2 ? (await search(q)).data : null;
  const empty = r && !r.topics.length && !r.bills.length && !r.members.length && !r.factions.length;

  return (
    <div className="stack">
      <header className="page-head"><h1>{d.title}</h1></header>
      <form className="search" action={t.href("/search")}>
        <input name="q" defaultValue={q} placeholder={d.ph} dir="auto" autoFocus />
        <button type="submit">{t.d.common.find}</button>
      </form>
      <p className="small muted">{d.hint}</p>
      {empty && <p className="muted">{t.d.common.nothingFound}</p>}
      {r && r.members.length > 0 && (
        <section className="card"><h2 className="section-title">{d.members}</h2>
          {r.members.map((m) => <p key={m.id}><Link href={`/members/${m.id}`}><PersonName p={m} /></Link></p>)}
        </section>
      )}
      {r && r.factions.length > 0 && (
        <section className="card"><h2 className="section-title">{d.factions}</h2>
          {r.factions.map((f) => (
            <p key={f.id}><Link href={`/factions/${f.id}`}><FactionName f={f} he="inline" /></Link> <span className="small muted">· {t.d.common.term(f.term)}</span></p>
          ))}
        </section>
      )}
      {r && r.topics.length > 0 && (
        <section className="card"><h2 className="section-title">{d.topics}</h2>
          {r.topics.map((x) => <p key={x.slug}><Link href={`/topics/${x.slug}`}>{t.topic(x)}</Link> <span className="small muted">· {t.d.common.billsCount(x.bills)}</span></p>)}
        </section>
      )}
      {r && r.bills.length > 0 && (
        <section className="card"><h2 className="section-title">{d.bills}</h2>
          {r.bills.map((b) => (
            <p key={b.id} style={{ padding: "4px 0" }}>
              <Link href={`/bills/${b.id}`} style={{ display: "block", textAlign: "right" }}><He>{b.title_he}</He></Link>
              <span className="small muted">{t.d.common.term(b.term)} · {t.d.common.votesCount(b.votes)}{b.passed_third_reading && ` · ${t.d.common.passed}`}</span>
            </p>
          ))}
        </section>
      )}
    </div>
  );
}
