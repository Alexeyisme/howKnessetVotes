import Link from "./Link";
import { VoteCard, VoteCards } from "./VoteCard";
import { listVotes } from "@/lib/api";
import { MAIN_MOTIONS } from "@/lib/labels";
import { getT } from "@/i18n/server";
import styles from "./VoteFeed.module.css";

// "main": votes on bills as a whole and no-confidence motions. Reservations, article and procedural votes (most of
// the rows) are one click away under "all votes".
const FILTERS: { key: string; params: Record<string, string | string[]> }[] = [
  { key: "main", params: { motion_type: MAIN_MOTIONS } },
  { key: "contested", params: { stage: "third", motion_type: "adopt_bill", contested: "true", min_cast: "60" } },
  { key: "final", params: { stage: "third", motion_type: "adopt_bill" } },
  { key: "first", params: { stage: "first", motion_type: "adopt_bill" } },
  { key: "preliminary", params: { stage: "preliminary", motion_type: "adopt_bill" } },
  { key: "all", params: {} },
];

/** The vote list with its view chips and paging, on /votes and on topic pages (`filter`: e.g. the topic). When the
 *  visitor has not picked a view and the default one is empty, `fallback` is shown instead (a topic with no
 *  contested votes shows its final votes). */
export async function VoteFeed({ base, sp, filter = {}, defaultView = "main", fallback }: {
  base: string; sp: Record<string, string | string[] | undefined>; filter?: Record<string, string>;
  defaultView?: string; fallback?: string;
}) {
  const t = await getT();
  const d = t.d.votes;
  const picked = FILTERS.find((f) => f.key === sp.view);
  const cursor = typeof sp.cursor === "string" ? sp.cursor : undefined;
  let view = picked ?? FILTERS.find((f) => f.key === defaultView)!;
  let res = await listVotes({ ...view.params, ...filter, cursor, limit: "30" });
  if (!picked && !cursor && fallback && res.data.length === 0) {
    view = FILTERS.find((f) => f.key === fallback)!;
    res = await listVotes({ ...view.params, ...filter, limit: "30" });
  }
  const href = (key: string, extra: Record<string, string> = {}) => {
    const qs = new URLSearchParams({ ...(key !== defaultView ? { view: key } : {}), ...extra }).toString();
    return qs ? `${base}?${qs}` : base;
  };

  return (
    <>
      {d.lead[view.key] && <p className="muted" style={{ marginBottom: 12 }}>{d.lead[view.key]}</p>}
      <nav className={styles.filters} aria-label={d.filtersLabel}>
        {FILTERS.map((f) => (
          <Link key={f.key} href={href(f.key)} className={styles.chip} scroll={false}
                aria-current={f.key === view.key ? "page" : undefined}>{d.filters[f.key]}</Link>
        ))}
      </nav>
      <VoteCards>
        {res.data.map((v) => <VoteCard key={v.id} vote={v} showMotion={view.key === "all"} />)}
      </VoteCards>
      {res.data.length === 0 && <p className="muted">{t.d.common.noVotes}</p>}
      {res.next_cursor && (
        <p style={{ marginTop: 16 }}><Link href={href(view.key, { cursor: res.next_cursor })}>{t.d.common.earlier}</Link></p>
      )}
    </>
  );
}
