import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "@/components/Link";
import { ChoiceMark, FactionName, He, NextPage, RateStat, Stat, Stats, Tabs, VoteLine, VoteList, withParams } from "@/components/ui";
import { getMember, getMemberVotes, listTopics, NotFound } from "@/lib/api";
import { getT } from "@/i18n/server";
import styles from "./member.module.css";

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

export async function generateMetadata({ params }: PageProps<"/[lang]/members/[id]">): Promise<Metadata> {
  const { member } = await load((await params).id);
  return { title: (await getT()).person(member) };
}

// U5: who this is and the short answer first (photo, party, one sentence), then the details. The vote list opens on
// final votes, the ones that made or did not make laws.
const TABS = ["final", "all", "deviated"] as const;

export default async function MemberPage({ params, searchParams }: PageProps<"/[lang]/members/[id]">) {
  const { id, member } = await load((await params).id);
  const t = await getT();
  const d = t.d.member;
  const sp = await searchParams;
  const tab = TABS.find((x) => x === sp.tab) ?? (sp.deviated === "1" ? "deviated" : "final");
  const cursor = typeof sp.cursor === "string" ? sp.cursor : undefined;
  const topic = typeof sp.topic === "string" && sp.topic ? sp.topic : undefined;
  const filter = tab === "final" ? { stage: "third", motion_type: "adopt_bill" } : tab === "deviated" ? { deviated: "true" } : {};
  const [votes, topics] = await Promise.all([getMemberVotes(id, { ...filter, topic, cursor, limit: "30" }), listTopics()]);
  const tabParam = tab === "final" ? undefined : tab;
  const s = member.stats;
  const base = `/members/${id}`;
  const name = t.person(member);
  const current = member.mandates.some((m) => !m.valid_to);
  const others = [member.name_he, t.locale !== "en" ? member.name_en : member.name_ru].filter((x) => x && x !== name);

  return (
    <div className="stack">
      <header className={styles.head}>
        {member.photo_url && (
          <figure className={styles.photo}>
            {/* official portrait, linked from the Knesset website rather than copied */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={member.photo_url} alt={name} width={120} height={150} referrerPolicy="no-referrer" loading="lazy" />
            <figcaption className="small muted">{d.photoCredit}</figcaption>
          </figure>
        )}
        <div className={styles.who}>
          <p className="small muted">{d.kicker(member.terms.join(", "))}</p>
          <h1 className={styles.name} dir="auto">{name}</h1>
          {others.length > 0 && (
            <p className="muted">{others.map((o, n) => <span key={o}>{n > 0 && " · "}{o === member.name_he ? <He>{o}</He> : o}</span>)}</p>
          )}
          {member.last_faction && (
            <p>{current ? d.currentFaction : d.lastFaction}{" "}
              <Link href={`/factions/${member.last_faction.id}`}><FactionName f={member.last_faction} /></Link>
              <span className="small muted"> · {t.d.common.term(member.last_faction.term)}</span>
            </p>
          )}
          <p className={styles.summary}>
            {d.summary({
              part: t.pct(s.participation), cast: t.num(s.participation.numerator), avail: t.num(s.participation.denominator),
              dev: s.deviation_from_faction.numerator, comparable: t.num(s.deviation_from_faction.denominator), initiated: s.bills_initiated,
            })}
          </p>
        </div>
      </header>

      <section>
        <h2 className="section-title">{d.votes}</h2>
        <Tabs items={[
          { href: withParams(base, { topic }), label: d.tabFinal, current: tab === "final" },
          { href: withParams(base, { tab: "all", topic }), label: d.tabAll, current: tab === "all" },
          { href: withParams(base, { tab: "deviated", topic }), label: `${d.tabDeviated} · ${s.deviation_from_faction.numerator}`, current: tab === "deviated" },
        ]} />
        {/* R7: a topic filter — "how did my MK vote on housing" — as a plain GET form, so the URL is shareable */}
        <form className="search" action={t.href(base)}>
          {tabParam && <input type="hidden" name="tab" value={tabParam} />}
          <select name="topic" defaultValue={topic ?? ""} aria-label={d.topicFilter}>
            <option value="">{d.topicFilter}: {t.d.common.all}</option>
            {topics.data.map((x) => <option key={x.slug} value={x.slug}>{t.topic(x)}</option>)}
          </select>
          <button type="submit">{t.d.common.show}</button>
        </form>
        {tab === "final" && <p className="small muted" style={{ marginBottom: 8 }}>{d.finalHint}</p>}
        <VoteList>
          {votes.data.map((v) => (
            <VoteLine key={v.vote.id} vote={v.vote}>
              <ChoiceMark choice={v.choice} text={t.ballot(v.choice, v.participation)} />
              <span className="small muted">
                {v.faction ? <FactionName f={v.faction} /> : t.d.common.factionUnknown}: {t.d.majority[v.faction_majority]}
              </span>
            </VoteLine>
          ))}
        </VoteList>
        {votes.data.length === 0 && <p className="muted">{d.noVotes}</p>}
        <NextPage href={votes.next_cursor ? withParams(base, { tab: tabParam, topic, cursor: votes.next_cursor }) : null} />
      </section>

      <Stats>
        <RateStat label={d.withCoalition} rate={s.with_coalition} unit={d.withCoalitionUnit} />
        <RateStat label={d.deviation} rate={s.deviation_from_faction} unit={d.deviationUnit} />
        <RateStat label={d.participation} rate={s.participation} unit={d.participationUnit} />
        <Stat label={d.bills} value={s.bills_initiated} detail={d.billsDetail(s.bills_joined)} />
      </Stats>
      <p className="small"><Link href={`/compare?kind=members&a=${id}`}>{d.compareLink}</Link></p>
      <p className="note">{d.note}</p>

      <section className="card">
        <h2 className="section-title">{d.factions}</h2>
        <div className="table-scroll">
          <table>
            <thead><tr><th>{d.faction}</th><th>{d.term}</th><th>{d.period}</th></tr></thead>
            <tbody>
              {member.factions.map((f) => (
                <tr key={`${f.faction.id}-${f.valid_from}`}>
                  <td><Link href={`/factions/${f.faction.id}`}><FactionName f={f.faction} he="inline" /></Link></td>
                  <td className="num">{f.faction.term}</td>
                  <td className="small">{t.period(f.valid_from, f.valid_to)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
