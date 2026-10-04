import Link from "next/link";
import { PersonName } from "./ui";
import type { Ballot, Choice, FactionBreakdown as Row } from "@/lib/api";
import { ballotLabel, MAJORITY } from "@/lib/labels";
import styles from "./FactionBreakdown.module.css";

// Diverging order: for | abstain (neutral midpoint) | against.
const SEGMENTS: { key: Choice; label: string; className: string }[] = [
  { key: "for", label: "за", className: styles.for },
  { key: "abstain", label: "воздержались", className: styles.abstain },
  { key: "against", label: "против", className: styles.against },
];

export function Legend() {
  return (
    <ul className={styles.legend} aria-label="Легенда">
      {SEGMENTS.map((s) => (
        <li key={s.key}><span className={`${styles.swatch} ${s.className}`} aria-hidden /> {s.label}</li>
      ))}
    </ul>
  );
}

function countsText(r: Row): string {
  const c = r.counts;
  const parts = [`${c.for} за`, `${c.against} против`];
  if (c.abstain) parts.push(`${c.abstain} возд.`);
  if (c.present_not_voting) parts.push(`${c.present_not_voting} присутств., не голос.`);
  if (c.other) parts.push(`${c.other} иное`);
  return parts.join(" · ");
}

export function FactionBreakdown({ rows, ballots }: { rows: Row[]; ballots: Ballot[] }) {
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
        return (
          <details key={r.faction_id} className={styles.row}>
            <summary className={styles.summary}>
              <span className={styles.name}>
                {r.short_ru && <span className={styles.nameRu}>{r.short_ru}</span>}
                <span className="he" lang="he" dir="rtl">{r.name_he}</span>
              </span>
              <span className={styles.bar} role="img" aria-label={`${r.name_he}: ${countsText(r)}`}>
                {SEGMENTS.map((s) => {
                  const n = r.counts[s.key];
                  if (!n) return null;
                  return (
                    <span key={s.key} className={`${styles.seg} ${s.className}`} style={{ width: `${(100 * n) / scale}%` }}
                          title={`${s.label}: ${n}`} />
                  );
                })}
              </span>
              <span className={`${styles.counts} num`}>
                {countsText(r)}
                <span className={styles.majority}> — {MAJORITY[r.majority]}</span>
                {r.ambiguous_records > 0 && <span title="Голос в день смены фракции: принадлежность неоднозначна"> · {r.ambiguous_records} неоднозн.</span>}
              </span>
            </summary>
            <p className="small" style={{ padding: "0 4px" }}><Link href={`/factions/${r.faction_id}`}>Страница фракции →</Link></p>
            <ul className={styles.members}>
              {members.map((b) => (
                <li key={b.person_id}>
                  <Link href={`/members/${b.person_id}`}><PersonName p={b} he="title" /></Link>
                  <span className={`${styles.choice} ${b.choice ? styles[`c_${b.choice}`] : ""}`}>{ballotLabel(b.choice, b.participation)}</span>
                </li>
              ))}
            </ul>
          </details>
        );
      })}
    </div>
  );
}
