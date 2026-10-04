import type { Metadata } from "next";
import Link from "@/components/Link";
import { listVotes } from "@/lib/api";
import { MAIN_MOTIONS, missingRollCallText } from "@/lib/labels";
import { getT } from "@/i18n/server";
import styles from "./list.module.css";

// Default view: votes on bills as a whole and no-confidence motions. Reservations, article and procedural votes
// (most of the rows) are one click away under "all votes".
const FILTERS: { key: string; params: Record<string, string | string[]> }[] = [
  { key: "main", params: { motion_type: MAIN_MOTIONS } },
  { key: "contested", params: { stage: "third", motion_type: "adopt_bill", contested: "true", min_cast: "60" } },
  { key: "final", params: { stage: "third", motion_type: "adopt_bill" } },
  { key: "first", params: { stage: "first", motion_type: "adopt_bill" } },
  { key: "preliminary", params: { stage: "preliminary", motion_type: "adopt_bill" } },
  { key: "all", params: {} },
];

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.votes.title };
}

export default async function VotesPage({ searchParams }: PageProps<"/[lang]/votes">) {
  const sp = await searchParams;
  const t = await getT();
  const d = t.d.votes;
  const view = FILTERS.find((f) => f.key === sp.view) ?? FILTERS[0];
  const cursor = typeof sp.cursor === "string" ? sp.cursor : undefined;
  const { data, next_cursor } = await listVotes({ ...view.params, cursor, limit: "30" });

  return (
    <>
      <h1 className={styles.h1}>{d.title}</h1>
      {d.lead[view.key] && <p className="muted" style={{ marginBottom: 12 }}>{d.lead[view.key]}</p>}
      <nav className={styles.filters} aria-label={d.filtersLabel}>
        {FILTERS.map((f) => (
          <Link key={f.key} href={f.key === "main" ? "/votes" : `/votes?view=${f.key}`} className={styles.chip}
                aria-current={f.key === view.key ? "page" : undefined}>{d.filters[f.key]}</Link>
        ))}
      </nav>
      <ol className={styles.list}>
        {data.map((v) => (
          <li key={v.id} className={styles.item}>
            <Link href={`/votes/${v.id}`} className={styles.link}>
              <span className="small muted">{t.date(v.occurred_on)} · {v.stage ? t.d.stage[v.stage] : "—"}{v.motion_type && view.key === "all" ? ` · ${t.d.motion[v.motion_type]}` : ""}</span>
              <span className={`${styles.title} he`} lang="he" dir="rtl">{v.title_he}</span>
              <span className="small num">
                {v.roll_call.total_records > 0 ? t.d.rc.line(v.roll_call.for, v.roll_call.against, v.roll_call.abstain) : missingRollCallText(v.method, t)}
              </span>
              {view.key === "contested" && v.blocs && <span className="small muted num">{t.d.blocs.line(v.blocs.coalition, v.blocs.opposition)}</span>}
            </Link>
          </li>
        ))}
      </ol>
      {data.length === 0 && <p className="muted">{t.d.common.noVotes}</p>}
      {next_cursor && (
        <p style={{ marginTop: 16 }}>
          <Link href={`/votes?${new URLSearchParams({ ...(view.key !== "main" ? { view: view.key } : {}), cursor: next_cursor })}`}>{t.d.common.earlier}</Link>
        </p>
      )}
    </>
  );
}
