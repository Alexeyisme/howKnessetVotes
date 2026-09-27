import Link from "next/link";
import { listVotes, type Stage } from "@/lib/api";
import { formatDate, missingRollCallText, STAGE } from "@/lib/labels";
import styles from "./home.module.css";

const FILTERS: { stage?: Stage; label: string }[] = [
  { label: "Все" },
  { stage: "third", label: "Третье чтение" },
  { stage: "first", label: "Первое чтение" },
  { stage: "preliminary", label: "Предварительное" },
];

export default async function Home({ searchParams }: PageProps<"/">) {
  const sp = await searchParams;
  const stage = typeof sp.stage === "string" ? sp.stage : undefined;
  const cursor = typeof sp.cursor === "string" ? sp.cursor : undefined;
  const { data, next_cursor } = await listVotes({ stage, cursor, limit: "30" });

  return (
    <>
      <h1 className={styles.h1}>Голосования в пленуме</h1>
      <nav className={styles.filters} aria-label="Стадия">
        {FILTERS.map((f) => (
          <Link key={f.label} href={f.stage ? `/?stage=${f.stage}` : "/"} className={styles.chip}
                aria-current={f.stage === stage ? "page" : undefined}>{f.label}</Link>
        ))}
      </nav>
      <ol className={styles.list}>
        {data.map((v) => (
          <li key={v.id} className={styles.item}>
            <Link href={`/votes/${v.id}`} className={styles.link}>
              <span className="small muted">{formatDate(v.occurred_on)} · {v.stage ? STAGE[v.stage] : "—"}</span>
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
          <Link href={`/?${new URLSearchParams({ ...(stage ? { stage } : {}), cursor: next_cursor })}`}>Более ранние →</Link>
        </p>
      )}
    </>
  );
}
