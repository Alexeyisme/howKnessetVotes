import Link from "next/link";
import { listVotes } from "@/lib/api";
import { formatDate, MAIN_MOTIONS, missingRollCallText, MOTION, STAGE } from "@/lib/labels";
import styles from "./home.module.css";

// Default view: votes on bills as a whole and no-confidence motions. Reservations, article and procedural votes
// (most of the rows) are one click away under "all votes".
const FILTERS: { key: string; label: string; params: Record<string, string | string[]> }[] = [
  { key: "main", label: "Главные", params: { motion_type: MAIN_MOTIONS } },
  { key: "final", label: "Окончательные (третье чтение)", params: { stage: "third", motion_type: "adopt_bill" } },
  { key: "first", label: "Первое чтение", params: { stage: "first", motion_type: "adopt_bill" } },
  { key: "preliminary", label: "Предварительное", params: { stage: "preliminary", motion_type: "adopt_bill" } },
  { key: "all", label: "Все голосования", params: {} },
];

export default async function Home({ searchParams }: PageProps<"/">) {
  const sp = await searchParams;
  const view = FILTERS.find((f) => f.key === sp.view) ?? FILTERS[0];
  const cursor = typeof sp.cursor === "string" ? sp.cursor : undefined;
  const { data, next_cursor } = await listVotes({ ...view.params, cursor, limit: "30" });

  return (
    <>
      <h1 className={styles.h1}>Голосования в пленуме</h1>
      <p className="muted" style={{ marginBottom: 12 }}>
        {view.key === "main" && "Голосования по законопроектам в целом и вотумы недоверия. Оговорки, статьи и процедурные вопросы — в «Все голосования»."}
        {view.key === "final" && "Голосования, после которых законопроект становится законом (или не становится)."}
        {view.key === "all" && "Все голосования, включая оговорки (поправки), отдельные статьи и процедурные решения."}
      </p>
      <nav className={styles.filters} aria-label="Какие голосования показать">
        {FILTERS.map((f) => (
          <Link key={f.key} href={f.key === "main" ? "/" : `/?view=${f.key}`} className={styles.chip}
                aria-current={f.key === view.key ? "page" : undefined}>{f.label}</Link>
        ))}
      </nav>
      <ol className={styles.list}>
        {data.map((v) => (
          <li key={v.id} className={styles.item}>
            <Link href={`/votes/${v.id}`} className={styles.link}>
              <span className="small muted">{formatDate(v.occurred_on)} · {v.stage ? STAGE[v.stage] : "—"}{v.motion_type && view.key === "all" ? ` · ${MOTION[v.motion_type]}` : ""}</span>
              <span className={`${styles.title} he`} lang="he" dir="rtl">{v.title_he}</span>
              <span className="small num">
                {v.roll_call.total_records > 0 ? `${v.roll_call.for} за · ${v.roll_call.against} против · ${v.roll_call.abstain} возд.` : missingRollCallText(v.method)}
              </span>
            </Link>
          </li>
        ))}
      </ol>
      {data.length === 0 && <p className="muted">Нет голосований.</p>}
      {next_cursor && (
        <p style={{ marginTop: 16 }}>
          <Link href={`/?${new URLSearchParams({ ...(view.key !== "main" ? { view: view.key } : {}), cursor: next_cursor })}`}>Более ранние →</Link>
        </p>
      )}
    </>
  );
}
