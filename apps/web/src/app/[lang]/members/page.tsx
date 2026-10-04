import type { Metadata } from "next";
import Link from "@/components/Link";
import { TermSelect } from "@/components/TermSelect";
import { FactionName, PersonName } from "@/components/ui";
import { listMembers } from "@/lib/api";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.members.title };
}

export default async function MembersPage({ searchParams }: PageProps<"/[lang]/members">) {
  const t = await getT();
  const d = t.d.members;
  const sp = await searchParams;
  const term = typeof sp.term === "string" && sp.term ? sp.term : "25";
  const q = typeof sp.q === "string" && sp.q.trim().length >= 2 ? sp.q.trim() : undefined;
  const { data } = await listMembers({ term: q ? undefined : term, q });

  return (
    <div className="stack">
      <header className="page-head"><h1>{d.title}</h1></header>
      <form className="search" action={t.href("/members")}>
        <input name="q" defaultValue={q} placeholder={d.searchPh} dir="auto" />
        <TermSelect value={term} />
        <button type="submit">{t.d.common.show}</button>
      </form>
      <p className="small muted">{q ? d.searchAll(data.length) : d.termCount(term, data.length)}</p>
      <div className="card table-scroll">
        <table>
          <thead><tr><th>{d.member}</th><th>{d.lastFaction}</th><th>{d.terms}</th><th className="num">{d.records}</th></tr></thead>
          <tbody>
            {data.map((m) => (
              <tr key={m.id}>
                <td><Link href={`/members/${m.id}`}><PersonName p={m} he="title" /></Link></td>
                <td>{m.last_faction ? <Link href={`/factions/${m.last_faction.id}`}><FactionName f={m.last_faction} /></Link> : "—"}</td>
                <td className="small">{m.terms.join(", ")}</td>
                <td className="num">{t.num(m.roll_call_records)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
