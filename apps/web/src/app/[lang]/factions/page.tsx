import type { Metadata } from "next";
import Link from "@/components/Link";
import { TermSelect } from "@/components/TermSelect";
import { FactionName } from "@/components/ui";
import { listFactions } from "@/lib/api";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.factions.title };
}

export default async function FactionsPage({ searchParams }: PageProps<"/[lang]/factions">) {
  const t = await getT();
  const d = t.d.factions;
  const sp = await searchParams;
  const term = typeof sp.term === "string" && sp.term ? sp.term : undefined;
  const { data, meta } = await listFactions({ term });
  const shown = String(meta.filters.term ?? term ?? "");

  return (
    <div className="stack">
      <header className="page-head"><h1>{d.title}</h1></header>
      <form className="search" action={t.href("/factions")}>
        <TermSelect value={shown} />
        <button type="submit">{t.d.common.show}</button>
      </form>
      <p className="small muted">{d.lead}</p>
      <div className="card table-scroll">
        <table>
          <thead><tr><th>{d.faction}</th><th>{d.period}</th><th className="num">{d.membersEver}</th><th className="num">{d.records}</th></tr></thead>
          <tbody>
            {data.map((f) => (
              <tr key={f.id}>
                <td><Link href={`/factions/${f.id}`}><FactionName f={f} he="inline" /></Link></td>
                <td className="small">{t.period(f.valid.valid_from, f.valid.valid_to)}</td>
                <td className="num">{f.members_ever}</td>
                <td className="num">{t.num(f.roll_call_records)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
