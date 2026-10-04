import type { Metadata } from "next";
import Link from "@/components/Link";
import { AlignmentBadge } from "@/components/ui";
import { listParties, type PartySummary } from "@/lib/api";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.parties.title };
}

export default async function PartiesPage() {
  const t = await getT();
  const d = t.d.parties;
  const { data } = await listParties();
  const latest = (p: PartySummary) => p.factions[p.factions.length - 1];

  return (
    <div className="stack">
      <header className="page-head"><h1>{d.title}</h1></header>
      <p className="small muted">{d.lead}</p>
      <ul className="card" style={{ listStyle: "none", columns: "2 300px", columnGap: 32 }}>
        {data.filter((p) => p.factions.length > 0).map((p) => {
          const last = latest(p);
          return (
            <li key={p.slug} style={{ padding: "6px 0", breakInside: "avoid" }}>
              <Link href={`/parties/${p.slug}`}><strong>{t.party(p)}</strong></Link>{" "}
              <span className="small muted">· {d.knessets(p.terms.length)}: {p.terms[0]}–{p.terms[p.terms.length - 1]}</span>
              {last.term === Math.max(...data.flatMap((x) => x.terms)) && last.alignment_last && <> <AlignmentBadge role={last.alignment_last} /></>}
            </li>
          );
        })}
      </ul>
      <p><Link href="/factions">{d.byTerm}</Link></p>
    </div>
  );
}
