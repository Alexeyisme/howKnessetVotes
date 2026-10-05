import { redirect } from "next/navigation";
import Link from "@/components/Link";
import { SearchBox } from "@/components/SearchBox";
import { VoteCard, VoteCards } from "@/components/VoteCard";
import { getStatus, listTopics, listVotes } from "@/lib/api";
import { RECESS_UNTIL } from "@/lib/labels";
import { getT } from "@/i18n/server";
import styles from "./home.module.css";

// U1: a start page for first-time visitors: one search box for any language, the laws the coalition and opposition
// fought over (the question a voter asks), topics as the way in to "how did my party vote on...", and the sections.
export default async function Home({ searchParams }: PageProps<"/[lang]">) {
  const sp = await searchParams;
  const t = await getT();
  // the vote feed used to be the home page; keep its old links working
  if (sp.view || sp.cursor) redirect(t.href(`/votes?${new URLSearchParams(sp as Record<string, string>)}`));
  const d = t.d.home;
  const contestedQuery = { stage: "third", motion_type: "adopt_bill", contested: "true", min_cast: "60", limit: "5" };
  const [topics, contested, status] = await Promise.all([
    listTopics(), listVotes(contestedQuery), getStatus().then((r) => r.data, () => null),
  ]);
  // between Knessets there are no contested votes yet: fall back to the latest final votes
  const feed = contested.data.length > 0 ? contested : await listVotes({ stage: "third", motion_type: "adopt_bill", limit: "5" });
  const top = [...topics.data].sort((a, b) => b.bills - a.bills).slice(0, 10);
  const today = new Date().toISOString().slice(0, 10);
  const recess = today < RECESS_UNTIL;

  return (
    <div className={styles.home}>
      <section className={styles.hero}>
        <h1>{d.title}</h1>
        <p className={styles.lead}>{d.lead}</p>
        <SearchBox locale={t.locale} action={t.href("/search")} large
                   labels={{ placeholder: d.searchPh, label: t.d.nav.searchLabel, button: t.d.common.find, members: t.d.search.members, parties: t.d.search.factions, topics: t.d.search.topics, all: t.d.common.find }} />
        <p className="small muted">
          {d.examples}{" "}
          {d.exampleQueries.map((q, n) => <span key={q}>{n > 0 && " · "}<Link href={`/search?q=${encodeURIComponent(q)}`}>{q}</Link></span>)}
        </p>
        {status && (
          <p className={`small ${styles.fresh}`}>
            {d.latestVote(t.date(status.coverage.last_vote_on))}{recess && <> · {d.recess(t.date(RECESS_UNTIL))}</>}
          </p>
        )}
      </section>

      <section>
        <h2 className="section-title">{contested.data.length > 0 ? d.contestedTitle : d.finalTitle}</h2>
        <VoteCards>
          {feed.data.map((v) => <VoteCard key={v.id} vote={v} />)}
        </VoteCards>
        <p className="small" style={{ marginTop: 8 }}>
          <Link href="/votes?view=contested">{t.d.votes.filters.contested} →</Link> · <Link href="/votes?view=final">{d.finalAll}</Link>
        </p>
      </section>

      <section>
        <h2 className="section-title">{d.topicsTitle}</h2>
        <ul className={styles.topics}>
          {top.map((x) => (
            <li key={x.slug}><Link href={`/topics/${x.slug}`} className="chip">{t.topic(x)}</Link></li>
          ))}
        </ul>
        <p className="small" style={{ marginTop: 8 }}><Link href="/topics">{d.topicsAll}</Link></p>
      </section>

      <section>
        <h2 className="section-title">{d.browse}</h2>
        <ul className={styles.tiles}>
          {d.tiles.map((x) => (
            <li key={x.href}><Link href={x.href} className={styles.tile}><strong>{x.title}</strong><span className="small muted">{x.text}</span></Link></li>
          ))}
        </ul>
      </section>
    </div>
  );
}
