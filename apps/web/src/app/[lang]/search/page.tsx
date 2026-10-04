import type { Metadata } from "next";
import Link from "@/components/Link";
import { AlignmentBadge, FactionName, He, PersonName } from "@/components/ui";
import { listParties, search, type PartySummary } from "@/lib/api";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.search.title };
}

export default async function SearchPage({ searchParams }: PageProps<"/[lang]/search">) {
  const t = await getT();
  const d = t.d.search;
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q.trim() : "";
  const [r, parties] = q.length >= 2 ? await Promise.all([search(q).then((x) => x.data), listParties().then((x) => x.data)]) : [null, []];
  const empty = r && !r.topics.length && !r.bills.length && !r.members.length && !r.factions.length;

  // "likud" matched ten factions (one per Knesset); the visitor wants one party. Group faction hits by party and show
  // one card per party; factions that belong to no party (none in practice) keep their own row.
  const partyOf = new Map<number, PartySummary>();
  for (const p of parties) for (const f of p.factions) partyOf.set(f.id, p);
  const hitParties = new Map<string, PartySummary>();
  const looseFactions = [];
  for (const f of r?.factions ?? []) {
    const p = partyOf.get(f.id);
    if (p) hitParties.set(p.slug, p); else looseFactions.push(f);
  }

  return (
    <div className="stack">
      <header className="page-head"><h1>{d.title}</h1></header>
      <form className="search" action={t.href("/search")}>
        <input name="q" defaultValue={q} placeholder={d.ph} dir="auto" autoFocus />
        <button type="submit">{t.d.common.find}</button>
      </form>
      <p className="small muted">{d.hint}</p>
      {empty && <p className="muted">{t.d.common.nothingFound}</p>}
      {hitParties.size > 0 && (
        <section className="card"><h2 className="section-title">{d.factions}</h2>
          {[...hitParties.values()].map((p) => {
            const last = p.factions[p.factions.length - 1];
            return (
              <p key={p.slug}>
                <Link href={`/parties/${p.slug}`}><strong>{t.party(p)}</strong></Link>{" "}
                <span className="small muted">· {t.d.parties.knessets(p.terms.length)}: {p.terms[0]}–{p.terms[p.terms.length - 1]}</span>
                {last?.alignment_last && <> <AlignmentBadge role={last.alignment_last} /></>}
              </p>
            );
          })}
          {looseFactions.map((f) => (
            <p key={f.id}><Link href={`/factions/${f.id}`}><FactionName f={f} he="inline" /></Link> <span className="small muted">· {t.d.common.term(f.term)}</span></p>
          ))}
        </section>
      )}
      {r && r.members.length > 0 && (
        <section className="card"><h2 className="section-title">{d.members}</h2>
          {r.members.map((m) => <p key={m.id}><Link href={`/members/${m.id}`}><PersonName p={m} /></Link></p>)}
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
