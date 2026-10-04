import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "@/components/Link";
import { AlignmentBadge, FactionName } from "@/components/ui";
import { getParty, NotFound } from "@/lib/api";
import { getT } from "@/i18n/server";

async function load(slug: string) {
  try {
    return (await getParty(slug)).data;
  } catch (e) {
    if (e instanceof NotFound) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: PageProps<"/[lang]/parties/[slug]">): Promise<Metadata> {
  return { title: (await getT()).party(await load((await params).slug)) };
}

export default async function PartyPage({ params }: PageProps<"/[lang]/parties/[slug]">) {
  const p = await load((await params).slug);
  const t = await getT();
  const d = t.d.parties;
  const name = t.party(p);

  return (
    <div className="stack">
      <header className="page-head">
        <p className="small muted">{d.kicker}</p>
        <h1>{name}</h1>
        {t.locale !== "he" && <p className="muted he" lang="he" dir="rtl" style={{ textAlign: "start" }}>{p.name_he}</p>}
      </header>
      <div className="card table-scroll">
        <table>
          <thead><tr><th>{d.term}</th><th>{d.faction}</th><th>{d.period}</th><th className="num">{d.members}</th><th>{d.role}</th></tr></thead>
          <tbody>
            {[...p.factions].reverse().map((f) => (
              <tr key={f.id}>
                <td className="num">{f.term}</td>
                <td><Link href={`/factions/${f.id}`}><FactionName f={f} full he="title" /></Link>
                  {f.parties.length > 1 && <span className="small muted"> · {f.parties.map((x) => t.party(x)).join(" + ")}</span>}</td>
                <td className="small">{t.period(f.valid.valid_from, f.valid.valid_to)}</td>
                <td className="num">{f.members_ever}</td>
                <td>{f.alignment_last && <AlignmentBadge role={f.alignment_last} />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="small muted">{t.d.blocs.note}</p>
    </div>
  );
}
