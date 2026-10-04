import Link from "next/link";
import type { TopicDetail } from "@/lib/api";
import { FactionName } from "./ui";
import styles from "./TopicFactions.module.css";

/** Diverging bars: votes where the faction's majority was against (left, red) / for (right, blue) the bill.
 *  Neutral "no clear majority" stays as text. One scale for all rows; every bar carries its number. */
export function TopicFactions({ rows }: { rows: TopicDetail["factions"] }) {
  const scale = Math.max(1, ...rows.map((r) => Math.max(r.majority_for, r.majority_against)));
  return (
    <div>
      <div className={styles.axisLegend} aria-hidden>
        <span><span className={`${styles.swatch} ${styles.against}`} /> большинство против</span>
        <span>большинство за <span className={`${styles.swatch} ${styles.for}`} /></span>
      </div>
      <ul className={styles.list}>
        {rows.map((r) => (
          <li key={r.faction.id} className={styles.row}>
            <Link href={`/factions/${r.faction.id}`} className={styles.name}>
              <FactionName f={r.faction} />
            </Link>
            <div className={styles.bars} role="img"
                 aria-label={`${r.faction.short_ru ?? r.faction.name_he}: ${r.majority_for} за, ${r.majority_against} против, ${r.other} без явного большинства, из ${r.votes}`}>
              <div className={styles.left}>
                {r.majority_against > 0 && <span className="num small">{r.majority_against}</span>}
                <span className={`${styles.bar} ${styles.against}`} style={{ width: `${(100 * r.majority_against) / scale}%` }} />
              </div>
              <div className={styles.right}>
                <span className={`${styles.bar} ${styles.for}`} style={{ width: `${(100 * r.majority_for) / scale}%` }} />
                {r.majority_for > 0 && <span className="num small">{r.majority_for}</span>}
              </div>
            </div>
            <span className="small muted num">из {r.votes}{r.other > 0 && ` · ${r.other} без явного большинства`}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
