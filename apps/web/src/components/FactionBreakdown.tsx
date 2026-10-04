import Link from "./Link";
import { PersonName } from "./ui";
import type { Ballot, Choice, FactionBreakdown as Row } from "@/lib/api";
import { getT } from "@/i18n/server";
import styles from "./FactionBreakdown.module.css";

// Diverging order: for | abstain (neutral midpoint) | against.
const SEGMENTS: { key: Choice; className: string }[] = [
  { key: "for", className: styles.for },
  { key: "abstain", className: styles.abstain },
  { key: "against", className: styles.against },
];

export async function Legend() {
  const d = (await getT()).d.breakdown;
  return (
    <ul className={styles.legend} aria-label={d.legend}>
      {SEGMENTS.map((s) => (
        <li key={s.key}><span className={`${styles.swatch} ${s.className}`} aria-hidden /> {d[s.key]}</li>
      ))}
    </ul>
  );
}

export async function FactionBreakdown({ rows, ballots }: { rows: Row[]; ballots: Ballot[] }) {
  const t = await getT();
  const d = t.d.breakdown;
  // One scale for all factions, so bar length compares faction participation, not just shares.
  const scale = Math.max(1, ...rows.map((r) => r.counts.for + r.counts.against + r.counts.abstain));
  const byFaction = new Map<number, Ballot[]>();
  for (const b of ballots) {
    if (b.faction_id == null) continue;
    byFaction.set(b.faction_id, [...(byFaction.get(b.faction_id) ?? []), b]);
  }

  return (
    <div className={styles.list}>
      {rows.map((r) => {
        const members = byFaction.get(r.faction_id) ?? [];
        const name = t.faction(r);
        return (
          <details key={r.faction_id} className={styles.row}>
            <summary className={styles.summary}>
              <span className={styles.name}>
                {name !== r.name_he && <span className={styles.nameRu}>{name}</span>}
                <span className="he" lang="he" dir="rtl">{r.name_he}</span>
              </span>
              <span className={styles.bar} role="img" aria-label={`${name}: ${d.counts(r.counts)}`}>
                {SEGMENTS.map((s) => {
                  const n = r.counts[s.key];
                  if (!n) return null;
                  return (
                    <span key={s.key} className={`${styles.seg} ${s.className}`} style={{ width: `${(100 * n) / scale}%` }}
                          title={`${d[s.key]}: ${n}`} />
                  );
                })}
              </span>
              <span className={`${styles.counts} num`}>
                {d.counts(r.counts)}
                <span className={styles.majority}> — {t.d.majority[r.majority]}</span>
                {r.ambiguous_records > 0 && <span title={d.ambiguousTitle}>{d.ambiguous(r.ambiguous_records)}</span>}
              </span>
            </summary>
            <p className="small" style={{ padding: "0 4px" }}><Link href={`/factions/${r.faction_id}`}>{d.factionPage}</Link></p>
            <ul className={styles.members}>
              {members.map((b) => (
                <li key={b.person_id}>
                  <Link href={`/members/${b.person_id}`}><PersonName p={b} he="title" /></Link>
                  <span className={`${styles.choice} ${b.choice ? styles[`c_${b.choice}`] : ""}`}>{t.ballot(b.choice, b.participation)}</span>
                </li>
              ))}
            </ul>
          </details>
        );
      })}
    </div>
  );
}
