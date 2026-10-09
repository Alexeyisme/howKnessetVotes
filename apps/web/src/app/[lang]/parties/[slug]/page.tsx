import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "@/components/Link";
import { AlignmentBadge, FactionName, MemberChip, MemberGrid, RateStat, Stat, Stats } from "@/components/ui";
import { VoteFeed } from "@/components/VoteFeed";
import { getFaction, getParty, listMembers, NotFound } from "@/lib/api";
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

// R1: the party is the hub a voter thinks in. The page answers "where do they stand now" first — the current list,
// coalition or opposition, how its majority voted (the same views as /votes, opening on the contested laws), who is
// in it — and keeps the Knesset-by-Knesset history behind a fold.
export default async function PartyPage({ params, searchParams }: PageProps<"/[lang]/parties/[slug]">) {
  const { slug } = await params;
  const sp = await searchParams;
  const p = await load(slug);
  const t = await getT();
  const d = t.d.parties;
  const name = t.party(p);
  const latest = p.factions[p.factions.length - 1];
  const [faction, members] = latest
    ? await Promise.all([
        getFaction(latest.id).then((r) => r.data),
        listMembers({ faction: String(latest.id) }).then((r) => r.data),
      ])
    : [null, []];
  const current = faction ? new Set(faction.members.filter((m) => !m.valid_to).map((m) => m.person_id)) : new Set<number>();
  const membersNow = members.filter((m) => current.has(m.id));

  return (
    <div className="stack">
      <header className="page-head">
        <p className="small muted">{d.kicker}</p>
        <h1>{name} {latest?.alignment_last && <AlignmentBadge role={latest.alignment_last} />}</h1>
        {t.locale !== "he" && <p className="muted he" lang="he" dir="rtl" style={{ textAlign: "start" }}>{p.name_he}</p>}
        {latest && (
          <p style={{ marginTop: 6 }}>
            {d.current(latest.term)}: <Link href={`/factions/${latest.id}`}><FactionName f={latest} full /></Link>
            {latest.parties.length > 1 && <span className="small muted"> · {latest.parties.map((x) => t.party(x)).join(" + ")}</span>}
            <span className="small muted"> · {t.period(latest.valid.valid_from, latest.valid.valid_to)}</span>
          </p>
        )}
      </header>

      {faction && (
        <Stats>
          <Stat label={d.members} value={t.num(membersNow.length)} detail={t.d.faction.members(faction.members_ever)} />
          <RateStat label={t.d.faction.cohesion} rate={faction.stats.cohesion} unit={t.d.faction.cohesionUnit} />
          <Stat label={t.d.faction.votesWithMembers} value={t.num(faction.stats.votes_with_members)} />
        </Stats>
      )}

      {latest && (
        <section>
          <h2 className="section-title">{d.votesTitle}</h2>
          <VoteFeed base={`/parties/${slug}`} sp={sp} faction={{ id: latest.id, name: t.faction(latest) }} defaultView="contested" fallback="final" />
          <p className="small" style={{ marginTop: 8 }}>
            <Link href={`/factions/${latest.id}?split=1`}>{t.d.faction.tabSplit} →</Link> · <Link href={`/factions/${latest.id}`}>{d.allVotes}</Link>
          </p>
        </section>
      )}

      {membersNow.length > 0 && (
        <section>
          <h2 className="section-title">{d.members} <span className="muted small">· {t.d.faction.members(faction!.members_ever)}</span></h2>
          <MemberGrid>
            {membersNow.map((m) => <MemberChip key={m.id} m={m} />)}
          </MemberGrid>
        </section>
      )}

      <details className="card">
        <summary className="section-title" style={{ cursor: "pointer", marginBottom: 0 }}>{d.history}</summary>
        <div className="table-scroll" style={{ marginTop: 12 }}>
          <table>
            <thead><tr><th>{d.term}</th><th>{d.faction}</th><th>{d.role}</th><th className="num">{d.members}</th><th>{d.period}</th></tr></thead>
            <tbody>
              {[...p.factions].reverse().map((f) => (
                <tr key={f.id}>
                  <td className="num">{f.term}</td>
                  <td><Link href={`/factions/${f.id}`}><FactionName f={f} full he="title" /></Link>
                    {f.parties.length > 1 && <span className="small muted"> · {f.parties.map((x) => t.party(x)).join(" + ")}</span>}</td>
                  <td>{f.alignment_last && <AlignmentBadge role={f.alignment_last} />}</td>
                  <td className="num">{f.members_ever}</td>
                  <td className="small">{t.period(f.valid.valid_from, f.valid.valid_to)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="small muted" style={{ marginTop: 8 }}>{t.d.blocs.note}</p>
      </details>
    </div>
  );
}
