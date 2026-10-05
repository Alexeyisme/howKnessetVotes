import type { Metadata } from "next";
import Link from "@/components/Link";
import { TermSelect } from "@/components/TermSelect";
import { AlignmentBadge, FactionName } from "@/components/ui";
import { getTopic, listFactions, listTopics, type TopicDetail } from "@/lib/api";
import { getT } from "@/i18n/server";
import styles from "./compass.module.css";

const TOPICS_SHOWN = 12;

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.compass.title };
}

// R2: the one-screen answer — parties (rows, coalition first) × topics (columns); a cell is the party's majority on
// the final readings of bills in that topic. "Contested only" drops the government bills everyone in the coalition
// votes for, leaving the votes where the blocs actually differed.
export default async function CompassPage({ searchParams }: PageProps<"/[lang]/compass">) {
  const t = await getT();
  const d = t.d.compass;
  const sp = await searchParams;
  const contested = sp.view === "contested";
  const [factions, topics] = await Promise.all([listFactions({ term: typeof sp.term === "string" ? sp.term : undefined }), listTopics()]);
  const term = String(factions.meta.filters.term ?? "");
  const top = [...topics.data].sort((a, b) => b.bills - a.bills).slice(0, TOPICS_SHOWN);
  const details = await Promise.all(top.map((x) => getTopic(x.slug, { term, contested: contested ? "true" : undefined }).then((r) => r.data)));
  const cell = new Map<string, TopicDetail["factions"][number]>();
  for (const x of details) for (const f of x.factions) cell.set(`${x.slug}:${f.faction.id}`, f);
  // rows: factions that voted on any of these topics, coalition first, then by size
  const order = { coalition: 0, external_support: 1, opposition: 2, unknown: 3 } as const;
  const rows = factions.data
    .filter((f) => top.some((x) => cell.has(`${x.slug}:${f.id}`)))
    .sort((a, b) => order[a.alignment_last ?? "unknown"] - order[b.alignment_last ?? "unknown"] || b.roll_call_records - a.roll_call_records);

  return (
    <div className="stack">
      <header className="page-head"><h1>{d.title}</h1></header>
      <p className="muted">{d.lead}</p>
      <form className="search" action={t.href("/compass")}>
        <TermSelect value={term} />
        {contested && <input type="hidden" name="view" value="contested" />}
        <button type="submit">{t.d.common.show}</button>
      </form>
      <nav className={styles.toggle} aria-label={t.d.votes.filtersLabel}>
        <Link href={`/compass?term=${term}`} className="chip" aria-current={!contested ? "page" : undefined}>{d.all}</Link>
        <Link href={`/compass?term=${term}&view=contested`} className="chip" aria-current={contested ? "page" : undefined}>{d.contestedOnly}</Link>
      </nav>
      <div className={styles.scroll}>
        <table className={styles.grid}>
          <thead>
            <tr>
              <th className={styles.party}>{d.party}</th>
              {top.map((x) => <th key={x.slug} className={styles.topic}><Link href={`/topics/${x.slug}?term=${term}`}>{t.topic(x)}</Link></th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((f) => (
              <tr key={f.id}>
                <th className={styles.party}>
                  <Link href={`/factions/${f.id}`}><FactionName f={f} /></Link>
                  {f.alignment_last && f.alignment_last !== "unknown" && <span className={styles.badge}><AlignmentBadge role={f.alignment_last} /></span>}
                </th>
                {top.map((x) => {
                  const c = cell.get(`${x.slug}:${f.id}`);
                  if (!c || c.votes === 0) return <td key={x.slug} className={styles.empty} aria-label={d.empty} />;
                  const kind = c.majority_for > c.majority_against ? "for" : c.majority_against > c.majority_for ? "against" : "split";
                  const share = Math.max(c.majority_for, c.majority_against) / c.votes;
                  return (
                    <td key={x.slug} className={styles.cell} data-kind={kind} style={{ "--share": share } as React.CSSProperties}
                        title={d.cell(c.majority_for, c.majority_against, c.votes)}>
                      <Link href={`/topics/${x.slug}?term=${term}`} aria-label={`${t.faction(f)}, ${t.topic(x)}: ${d.cell(c.majority_for, c.majority_against, c.votes)}`}>
                        <span className="num">{kind === "against" ? c.majority_against : c.majority_for}<span className={styles.of}>/{c.votes}</span></span>
                      </Link>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p className="muted">{t.d.common.noVotes}</p>}
      <p className="small muted">{t.d.topic.factionsHint} {t.d.blocs.note}</p>
    </div>
  );
}
