import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { He, NextPage, PersonName, RateStat, Stat, Stats, Tabs, VoteLine, VoteList, withParams } from "@/components/ui";
import { getFaction, getFactionVotes, NotFound } from "@/lib/api";
import { MAJORITY, period } from "@/lib/labels";

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

export async function generateMetadata({ params }: PageProps<"/factions/[id]">): Promise<Metadata> {
  const { faction } = await load((await params).id);
  return { title: `${faction.short_ru ?? faction.name_he} (${faction.term}-й созыв)` };
}

export default async function FactionPage({ params, searchParams }: PageProps<"/factions/[id]">) {
  const { id, faction } = await load((await params).id);
  const sp = await searchParams;
  const split = sp.split === "1";
  const cursor = typeof sp.cursor === "string" ? sp.cursor : undefined;
  const votes = await getFactionVotes(id, { split_only: split ? "true" : undefined, cursor, limit: "30" });
  const current = faction.members.filter((m) => !m.valid_to);
  const former = faction.members.filter((m) => m.valid_to);
  const base = `/factions/${id}`;

  return (
    <div className="stack">
      <header className="page-head">
        <p className="small muted">Фракция Кнессета {faction.term}-го созыва · {period(faction.valid.valid_from, faction.valid.valid_to)}</p>
        {faction.name_ru && <h1>{faction.name_ru}</h1>}
        {faction.name_en && <p className="muted">{faction.name_en}</p>}
        {faction.name_ru ? <He as="p">{faction.name_he}</He> : <He as="h1">{faction.name_he}</He>}
      </header>

      <Stats>
        <Stat label="Голосований с участием членов" value={faction.stats.votes_with_members.toLocaleString("ru-RU")} />
        <RateStat label="Единство" rate={faction.stats.cohesion} unit="голосов совпали с самым частым выбором фракции" />
        <RateStat label="Голосовали единогласно" rate={faction.stats.unanimous_votes} unit="голосований (где голосовали двое и больше)" />
      </Stats>

      <section className="card">
        <h2 className="section-title">Состав ({faction.members_ever} за всё время)</h2>
        <ul style={{ listStyle: "none", columns: "2 240px", columnGap: 24 }}>
          {current.map((m) => (
            <li key={`${m.person_id}-${m.valid_from}`} style={{ padding: "3px 0", breakInside: "avoid" }}>
              <Link href={`/members/${m.person_id}`}><PersonName p={m} he="title" /></Link>
            </li>
          ))}
        </ul>
        {former.length > 0 && (
          <details style={{ marginTop: 10 }}>
            <summary style={{ cursor: "pointer" }} className="small">Бывшие члены фракции ({former.length})</summary>
            <table style={{ marginTop: 8 }}>
              <tbody>
                {former.map((m) => (
                  <tr key={`${m.person_id}-${m.valid_from}`}>
                    <td><Link href={`/members/${m.person_id}`}><PersonName p={m} he="title" /></Link></td>
                    <td className="small">{period(m.valid_from, m.valid_to)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        )}
      </section>

      <section>
        <h2 className="section-title">Голосования</h2>
        <Tabs items={[
          { href: base, label: "Все", current: !split },
          { href: withParams(base, { split: "1" }), label: "Фракция голосовала по-разному", current: split },
        ]} />
        <VoteList>
          {votes.data.map((v) => {
            const c = v.faction_counts;
            return (
              <VoteLine key={v.vote.id} vote={v.vote}>
                <span className="num">{c.for} за · {c.against} против{c.abstain ? ` · ${c.abstain} возд.` : ""}</span>
                <span className="small muted">{MAJORITY[v.majority]}</span>
              </VoteLine>
            );
          })}
        </VoteList>
        {votes.data.length === 0 && <p className="muted">Нет голосований.</p>}
        <NextPage href={votes.next_cursor ? withParams(base, { split: split ? "1" : undefined, cursor: votes.next_cursor }) : null} />
      </section>
    </div>
  );
}
