import Link from "./Link";
import { VoteCard, VoteCards } from "./VoteCard";
import { getFactionVotes, listVotes, type FactionVote, type VoteSummary } from "@/lib/api";
import { MAIN_MOTIONS } from "@/lib/labels";
import { getT } from "@/i18n/server";
import styles from "./VoteFeed.module.css";

// "main": votes on bills as a whole and no-confidence motions. Reservations, article and procedural votes (most of
// the rows) are one click away under "all votes". Also the views of a comparison (/compare).
export const FILTERS: { key: string; params: Record<string, string | string[]> }[] = [
  { key: "main", params: { motion_type: MAIN_MOTIONS } },
  { key: "contested", params: { stage: "third", motion_type: "adopt_bill", contested: "true", min_cast: "60" } },
  { key: "final", params: { stage: "third", motion_type: "adopt_bill" } },
  { key: "first", params: { stage: "first", motion_type: "adopt_bill" } },
  { key: "preliminary", params: { stage: "preliminary", motion_type: "adopt_bill" } },
  { key: "all", params: {} },
];

type Row = { vote: VoteSummary; party?: FactionVote };

/** The vote list with its view chips and paging, on /votes, topic pages (`filter`: the topic) and party pages
 *  (`faction`: the party's list, each card saying how its majority voted). When the visitor has not picked a view and
 *  the default one is empty, `fallback` is shown instead (a topic with no contested votes shows its final votes). */
export async function VoteFeed({ base, sp, filter = {}, defaultView = "main", fallback, faction }: {
  base: string; sp: Record<string, string | string[] | undefined>; filter?: Record<string, string>;
  defaultView?: string; fallback?: string; faction?: { id: number; name: string };
}) {
  const t = await getT();
  const d = t.d.votes;
  const picked = FILTERS.find((f) => f.key === sp.view);
  const cursor = typeof sp.cursor === "string" ? sp.cursor : undefined;
  const load = async (params: Record<string, string | string[] | undefined>): Promise<{ rows: Row[]; next: string | null }> => {
    if (faction) {
      const r = await getFactionVotes(faction.id, params);
      return { rows: r.data.map((x) => ({ vote: x.vote, party: x })), next: r.next_cursor };
    }
    const r = await listVotes(params);
    return { rows: r.data.map((vote) => ({ vote })), next: r.next_cursor };
  };
  let view = picked ?? FILTERS.find((f) => f.key === defaultView)!;
  let res = await load({ ...view.params, ...filter, cursor, limit: "30" });
  if (!picked && !cursor && fallback && res.rows.length === 0) {
    view = FILTERS.find((f) => f.key === fallback)!;
    res = await load({ ...view.params, ...filter, limit: "30" });
  }
  const href = (key: string, extra: Record<string, string> = {}) => {
    const qs = new URLSearchParams({ ...(key !== defaultView ? { view: key } : {}), ...extra }).toString();
    return qs ? `${base}?${qs}` : base;
  };

  return (
    <>
      {d.lead[view.key] && <p className="muted" style={{ marginBottom: 12 }}>{d.lead[view.key]}</p>}
      <ViewChips current={view.key} href={href} />
      <VoteCards>
        {res.rows.map(({ vote, party }) => (
          <VoteCard key={vote.id} vote={vote} showMotion={view.key === "all"}
                    note={party && <><strong>{faction!.name}: {t.d.majority[party.majority]}</strong>{" "}
                      <span className="num muted">({t.d.rc.line(party.faction_counts.for, party.faction_counts.against, party.faction_counts.abstain)})</span></>} />
        ))}
      </VoteCards>
      {res.rows.length === 0 && <p className="muted">{t.d.common.noVotes}</p>}
      {res.next && (
        <p style={{ marginTop: 16 }}><Link href={href(view.key, { cursor: res.next })}>{t.d.common.earlier}</Link></p>
      )}
    </>
  );
}

/** The view chips (main, contested, final, …), each a link built by `href(key)`. */
export async function ViewChips({ current, href }: { current: string; href: (key: string) => string }) {
  const d = (await getT()).d.votes;
  return (
    <nav className={styles.filters} aria-label={d.filtersLabel}>
      {FILTERS.map((f) => (
        <Link key={f.key} href={href(f.key)} className={styles.chip} scroll={false}
              aria-current={f.key === current ? "page" : undefined}>{d.filters[f.key]}</Link>
      ))}
    </nav>
  );
}
