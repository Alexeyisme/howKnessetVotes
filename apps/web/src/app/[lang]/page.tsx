import { redirect } from "next/navigation";
import Link from "@/components/Link";
import { He } from "@/components/ui";
import { listTopics, listVotes } from "@/lib/api";
import { verdict } from "@/lib/labels";
import { getT } from "@/i18n/server";
import styles from "./home.module.css";

// U1: a start page for first-time visitors: one search box for any language, topics as the way in to "how did my
// party vote on...", the latest final votes with the result in words, and tiles for the main sections.
export default async function Home({ searchParams }: PageProps<"/[lang]">) {
  const sp = await searchParams;
  const t = await getT();
  // the vote feed used to be the home page; keep its old links working
  if (sp.view || sp.cursor) redirect(t.href(`/votes?${new URLSearchParams(sp as Record<string, string>)}`));
  const d = t.d.home;
  const [topics, finals] = await Promise.all([listTopics(), listVotes({ stage: "third", motion_type: "adopt_bill", limit: "6" })]);
  const top = [...topics.data].sort((a, b) => b.bills - a.bills).slice(0, 10);

  return (
    <div className={styles.home}>
      <section className={styles.hero}>
        <h1>{d.title}</h1>
        <p className={styles.lead}>{d.lead}</p>
        <form action={t.href("/search")} className={styles.search} role="search">
          <input name="q" placeholder={d.searchPh} aria-label={t.d.nav.searchLabel} dir="auto" />
          <button type="submit">{t.d.common.find}</button>
        </form>
        <p className="small muted">
          {d.examples}{" "}
          {d.exampleQueries.map((q, n) => <span key={q}>{n > 0 && " · "}<Link href={`/search?q=${encodeURIComponent(q)}`}>{q}</Link></span>)}
        </p>
      </section>

      <section>
        <h2 className="section-title">{d.topicsTitle}</h2>
        <ul className={styles.topics}>
          {top.map((x) => (
            <li key={x.slug}><Link href={`/topics/${x.slug}`} className="chip">{t.topic(x)} <span className="muted small">{x.bills}</span></Link></li>
          ))}
        </ul>
        <p className="small" style={{ marginTop: 8 }}><Link href="/topics">{d.topicsAll}</Link></p>
      </section>

      <section>
        <h2 className="section-title">{d.finalTitle}</h2>
        <ul className={styles.finals}>
          {finals.data.map((v) => {
            const out = verdict(v, t);
            return (
              <li key={v.id}>
                <Link href={`/votes/${v.id}`} className={styles.final}>
                  <span className="small muted">{t.date(v.occurred_on)}</span>
                  <He className={styles.finalTitle}>{v.title_he}</He>
                  {out && (
                    <span className={`small ${styles.outcome}`} data-accepted={out.accepted ? "yes" : "no"}>
                      <strong>{out.text}</strong> <span className="num">{t.d.rc.line(v.roll_call.for, v.roll_call.against, v.roll_call.abstain)}</span>
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
        <p className="small" style={{ marginTop: 8 }}>
          <Link href="/votes?view=contested">{t.d.votes.filters.contested} →</Link> · <Link href="/votes?view=final">{d.finalAll}</Link>
        </p>
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
