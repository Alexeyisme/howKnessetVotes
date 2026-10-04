"use client";

// U6: the roll call as a filterable list: by name (any language), by faction, and "against own faction's majority".
// A table on wide screens, cards on phones (BallotTable.module.css). Rows arrive localized from the server.

import NextLink from "next/link";
import { useMemo, useState } from "react";
import { fold } from "@/lib/labels";
import styles from "./BallotTable.module.css";

export interface BallotRow {
  id: number;
  href: string;
  name: string;
  nameHe: string | null;      // shown as a tooltip when the name is not Hebrew
  search: string;             // all names, folded (lib/labels fold)
  factionId: number | null;
  faction: string;
  factionHe: string | null;
  factionHref: string | null;
  ambiguous: boolean;
  choice: "for" | "against" | "abstain" | null;
  label: string;
  deviates: boolean;
  note: string | null;
  code: string;
}

export interface BallotLabels {
  member: string; factionThen: string; vote: string; code: string;
  filterName: string; filterNamePh: string; filterFaction: string; allFactions: string;
  deviates: string; deviatesMark: string; shown: string;
}

export function BallotTable({ rows, factions, labels }: { rows: BallotRow[]; factions: { id: number; name: string }[]; labels: BallotLabels }) {
  const [q, setQ] = useState("");
  const [faction, setFaction] = useState("");
  const [deviates, setDeviates] = useState(false);
  const shown = useMemo(() => {
    const needle = fold(q.trim());
    return rows.filter((r) => (!needle || r.search.includes(needle)) && (!faction || String(r.factionId) === faction) && (!deviates || r.deviates));
  }, [rows, q, faction, deviates]);
  const anyDeviates = rows.some((r) => r.deviates);

  return (
    <div>
      <div className={styles.filters}>
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={labels.filterNamePh} aria-label={labels.filterName} dir="auto" />
        <select value={faction} onChange={(e) => setFaction(e.target.value)} aria-label={labels.filterFaction}>
          <option value="">{labels.allFactions}</option>
          {factions.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
        </select>
        {anyDeviates && (
          <label className="small"><input type="checkbox" checked={deviates} onChange={(e) => setDeviates(e.target.checked)} /> {labels.deviates}</label>
        )}
      </div>
      <p className="small muted" aria-live="polite">{labels.shown.replace("{n}", String(shown.length))}</p>
      <table className={styles.table}>
        <thead><tr><th>{labels.member}</th><th>{labels.factionThen}</th><th>{labels.vote}</th><th className={styles.codeCol}>{labels.code}</th></tr></thead>
        <tbody>
          {shown.map((r) => (
            <tr key={r.id}>
              <td className={styles.name}><NextLink href={r.href} title={r.nameHe ?? undefined}>{r.name}</NextLink></td>
              <td className={styles.faction}>
                {r.factionHref ? <NextLink href={r.factionHref} title={r.factionHe ?? undefined}>{r.faction}</NextLink> : r.faction}
                {r.ambiguous ? " *" : ""}
              </td>
              <td className={styles.vote}>
                <span className={`${styles.dot} ${r.choice ? styles[r.choice] : styles.none}`} aria-hidden />
                {r.label}
                {r.deviates && <span className={styles.flag}> · {labels.deviatesMark}</span>}
                {r.note && <span className="muted small"> · {r.note}</span>}
              </td>
              <td className={`num muted ${styles.codeCol}`}>{r.code}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
