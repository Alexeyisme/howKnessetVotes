import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "@/components/Link";
import { He, NextPage, PersonName, RateStat, Stat, Stats, Tabs, VoteLine, VoteList, withParams } from "@/components/ui";
import { getFaction, getFactionVotes, NotFound } from "@/lib/api";
import { getT } from "@/i18n/server";

async function load(idParam: string) {
  const id = Number(idParam);
  if (!Number.isInteger(id) || id <= 0) notFound();
  try {
    return { id, faction: (await getFaction(id)).data };
  } catch (e) {
    if (e instanceof NotFound) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: PageProps<"/[lang]/factions/[id]">): Promise<Metadata> {
  const { faction } = await load((await params).id);
  const t = await getT();
  return { title: t.d.faction.titleWithTerm(t.faction(faction), faction.term) };
}

export default async function FactionPage({ params, searchParams }: PageProps<"/[lang]/factions/[id]">) {
  const { id, faction } = await load((await params).id);
  const t = await getT();
  const d = t.d.faction;
  const sp = await searchParams;
  const split = sp.split === "1";
  const cursor = typeof sp.cursor === "string" ? sp.cursor : undefined;
  const votes = await getFactionVotes(id, { split_only: split ? "true" : undefined, cursor, limit: "30" });
  const current = faction.members.filter((m) => !m.valid_to);
  const former = faction.members.filter((m) => m.valid_to);
  const base = `/factions/${id}`;
  const full = t.faction(faction, true);
  const english = t.locale !== "en" && faction.name_en;

  return (
    <div className="stack">
      <header className="page-head">
        <p className="small muted">{d.kicker(faction.term, t.period(faction.valid.valid_from, faction.valid.valid_to))}</p>
        {full !== faction.name_he ? <h1>{full}</h1> : <He as="h1">{faction.name_he}</He>}
        {english && <p className="muted">{faction.name_en}</p>}
        {full !== faction.name_he && <He as="p">{faction.name_he}</He>}
      </header>

      <Stats>
        <Stat label={d.votesWithMembers} value={t.num(faction.stats.votes_with_members)} />
        <RateStat label={d.cohesion} rate={faction.stats.cohesion} unit={d.cohesionUnit} />
        <RateStat label={d.unanimous} rate={faction.stats.unanimous_votes} unit={d.unanimousUnit} />
      </Stats>

      <section className="card">
        <h2 className="section-title">{d.members(faction.members_ever)}</h2>
        <ul style={{ listStyle: "none", columns: "2 240px", columnGap: 24 }}>
          {current.map((m) => (
            <li key={`${m.person_id}-${m.valid_from}`} style={{ padding: "3px 0", breakInside: "avoid" }}>
              <Link href={`/members/${m.person_id}`}><PersonName p={m} he="title" /></Link>
            </li>
          ))}
        </ul>
        {former.length > 0 && (
          <details style={{ marginTop: 10 }}>
            <summary style={{ cursor: "pointer" }} className="small">{d.former(former.length)}</summary>
            <table style={{ marginTop: 8 }}>
              <tbody>
                {former.map((m) => (
                  <tr key={`${m.person_id}-${m.valid_from}`}>
                    <td><Link href={`/members/${m.person_id}`}><PersonName p={m} he="title" /></Link></td>
                    <td className="small">{t.period(m.valid_from, m.valid_to)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        )}
      </section>

      <section>
        <h2 className="section-title">{d.votes}</h2>
        <Tabs items={[
          { href: base, label: d.tabAll, current: !split },
          { href: withParams(base, { split: "1" }), label: d.tabSplit, current: split },
        ]} />
        <VoteList>
          {votes.data.map((v) => {
            const c = v.faction_counts;
            return (
              <VoteLine key={v.vote.id} vote={v.vote}>
                <span className="num">{t.d.rc.line(c.for, c.against, c.abstain)}</span>
                <span className="small muted">{t.d.majority[v.majority]}</span>
              </VoteLine>
            );
          })}
        </VoteList>
        {votes.data.length === 0 && <p className="muted">{t.d.common.noVotes}</p>}
        <NextPage href={votes.next_cursor ? withParams(base, { split: split ? "1" : undefined, cursor: votes.next_cursor }) : null} />
      </section>
    </div>
  );
}
