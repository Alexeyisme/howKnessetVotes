import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ChoiceMark, He, NextPage, RateStat, Stat, Stats, Tabs, VoteLine, VoteList, withParams } from "@/components/ui";
import { getMember, getMemberVotes, NotFound } from "@/lib/api";
import { ballotLabel, MAJORITY, period } from "@/lib/labels";

async function load(idParam: string) {
  const id = Number(idParam);
  if (!Number.isInteger(id) || id <= 0) notFound();
  try {
    return { id, member: (await getMember(id)).data };
  } catch (e) {
    if (e instanceof NotFound) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: PageProps<"/members/[id]">): Promise<Metadata> {
  const { member } = await load((await params).id);
  return { title: member.name_he };
}

export default async function MemberPage({ params, searchParams }: PageProps<"/members/[id]">) {
  const { id, member } = await load((await params).id);
  const sp = await searchParams;
  const deviated = sp.deviated === "1";
  const cursor = typeof sp.cursor === "string" ? sp.cursor : undefined;
  const votes = await getMemberVotes(id, { deviated: deviated ? "true" : undefined, cursor, limit: "30" });
  const s = member.stats;
  const base = `/members/${id}`;

  return (
    <div className="stack">
      <header className="page-head">
        <p className="small muted">Депутат Кнессета · созывы {member.terms.join(", ")}</p>
        <He as="h1">{member.name_he}</He>
        {member.last_faction && (
          <p className="small">Последняя фракция: <Link href={`/factions/${member.last_faction.id}`}><He>{member.last_faction.name_he}</He></Link></p>
        )}
      </header>

      <Stats>
        <RateStat label="Участие в поимённых голосованиях" rate={s.participation} unit="голосований в период мандата" />
        <RateStat label="Голосовал не так, как большинство фракции" rate={s.deviation_from_faction} unit="сравнимых голосов" />
        <Stat label="Законопроекты, дошедшие до голосования" value={s.bills_initiated} detail={`как инициатор; ещё ${s.bills_joined} — присоединился`} />
      </Stats>
      <p className="note">
        Статистика — по голосованиям с 27 сентября 2016 года. Участие — доля голосований с поимённым списком за время мандата, в которых депутат голосовал за, против или воздержался. Это не посещаемость заседаний.
        Большинство фракции считается по остальным её членам, голосовавшим в тот раз (не меньше двух); расхождение не означает нарушения фракционной дисциплины.
      </p>

      <section className="card">
        <h2 className="section-title">Фракции</h2>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Фракция</th><th>Созыв</th><th>Период</th></tr></thead>
            <tbody>
              {member.factions.map((f) => (
                <tr key={`${f.faction.id}-${f.valid_from}`}>
                  <td><Link href={`/factions/${f.faction.id}`}><He>{f.faction.name_he}</He></Link></td>
                  <td className="num">{f.faction.term}</td>
                  <td className="small">{period(f.valid_from, f.valid_to)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="section-title">Голоса</h2>
        <Tabs items={[
          { href: base, label: "Все", current: !deviated },
          { href: withParams(base, { deviated: "1" }), label: "Не так, как большинство фракции", current: deviated },
        ]} />
        <VoteList>
          {votes.data.map((v) => (
            <VoteLine key={v.vote.id} vote={v.vote}>
              <ChoiceMark choice={v.choice} text={ballotLabel(v.choice, v.participation)} />
              <span className="small muted">
                {v.faction ? <He>{v.faction.name_he}</He> : "фракция не установлена"}: {MAJORITY[v.faction_majority]}
              </span>
            </VoteLine>
          ))}
        </VoteList>
        {votes.data.length === 0 && <p className="muted">Нет голосов.</p>}
        <NextPage href={votes.next_cursor ? withParams(base, { deviated: deviated ? "1" : undefined, cursor: votes.next_cursor }) : null} />
      </section>
    </div>
  );
}
