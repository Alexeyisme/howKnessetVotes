import type { ReactNode } from "react";
import type { Alignment, Choice, FactionNames, PersonNames, Rate, VoteSummary } from "@/lib/api";
import { getT } from "@/i18n/server";
import { bidiSafe } from "@/lib/labels";
import Link from "./Link";
import styles from "./ui.module.css";

export function He({ children, as: Tag = "span", className = "" }: { children: ReactNode; as?: "span" | "h1" | "p"; className?: string }) {
  return <Tag className={`he ${className}`} lang="he" dir="rtl">{children}</Tag>;
}

/** A member's name in the UI language with the Hebrew original. `he`: "inline" shows both, "title" keeps Hebrew as a
 *  tooltip. The Hebrew UI shows the Hebrew name only. */
export async function PersonName({ p, he = "inline" }: { p: PersonNames; he?: "inline" | "title" }) {
  const t = await getT();
  const name = t.person(p);
  if (name === p.name_he) return <He>{p.name_he}</He>;
  if (he === "title") return <span title={p.name_he}>{name}</span>;
  return <>{name} <He className="muted small">{p.name_he}</He></>;
}

/** A faction's short name (or full list name) in the UI language, falling back to the official Hebrew name. */
export async function FactionName({ f, full = false, he = "title" }: { f: FactionNames; full?: boolean; he?: "inline" | "title" }) {
  const t = await getT();
  const name = t.faction(f, full);
  if (name === f.name_he) return <He>{f.name_he}</He>;
  if (he === "title") return <span title={f.name_he}>{name}</span>;
  return <>{name} <He className="muted small">{f.name_he}</He></>;
}

/** A member as a chip: portrait, name, party. Grids of these replace member tables on phones. */
export async function MemberChip({ m, faction }: { m: PersonNames & { id: number; photo_url?: string | null }; faction?: FactionNames | null }) {
  const t = await getT();
  const name = t.person(m);
  return (
    <li className={styles.chip}>
      <Link href={`/members/${m.id}`} className={styles.chipLink}>
        {m.photo_url ? (
          // official portrait, linked from the Knesset website rather than copied
          // eslint-disable-next-line @next/next/no-img-element
          <img src={m.photo_url} alt="" width={40} height={50} loading="lazy" referrerPolicy="no-referrer" className={styles.chipPhoto} />
        ) : <span className={styles.chipPhoto} aria-hidden />}
        <span className={styles.chipText}>
          <span className={styles.chipName} title={name !== m.name_he ? m.name_he : undefined}>{name}</span>
          {faction && <span className="small muted">{t.faction(faction)}</span>}
        </span>
      </Link>
    </li>
  );
}

export function MemberGrid({ children }: { children: ReactNode }) {
  return <ul className={styles.chips}>{children}</ul>;
}

export function Stat({ label, value, detail }: { label: string; value: ReactNode; detail?: ReactNode }) {
  return (
    <div className={styles.stat}>
      <div className="small muted">{label}</div>
      <div className={styles.statValue}>{value}</div>
      {detail && <div className="small muted">{detail}</div>}
    </div>
  );
}

/** A rate always shows its numerator and denominator (architecture.md §10). */
export async function RateStat({ label, rate, unit }: { label: string; rate: Rate; unit: string }) {
  const t = await getT();
  return <Stat label={label} value={t.pct(rate)} detail={t.d.common.rateDetail(t.num(rate.numerator), t.num(rate.denominator), unit)} />;
}

export function Stats({ children }: { children: ReactNode }) {
  return <div className={styles.stats}>{children}</div>;
}

export async function ChoiceMark({ choice, text }: { choice: Choice | null; text?: string }) {
  const t = await getT();
  return (
    <span className={styles.choice}>
      <span className={`${styles.dot} ${choice ? styles[choice] : styles.none}`} aria-hidden />
      {text ?? (choice ? t.d.choiceShort[choice] : "—")}
    </span>
  );
}

/** One vote in a list: date, stage, linked title, and a slot for what the page wants to show about it. */
export async function VoteLine({ vote, children }: { vote: VoteSummary; children?: ReactNode }) {
  const t = await getT();
  return (
    <li className={styles.voteLine}>
      <div className={styles.voteMain}>
        <span className="small muted">
          {t.date(vote.occurred_on)} · {vote.stage ? t.d.stage[vote.stage] : "—"}
          {vote.subject_he && <> · <He>{bidiSafe(vote.subject_he)}</He></>}
        </span>
        <Link href={`/votes/${vote.id}`} className={styles.voteTitle}><He>{vote.title_he}</He></Link>
      </div>
      {children && <div className={styles.voteSide}>{children}</div>}
    </li>
  );
}

export function VoteList({ children }: { children: ReactNode }) {
  return <ul className={styles.voteList}>{children}</ul>;
}

export function Tabs({ items }: { items: { href: string; label: string; current: boolean }[] }) {
  return (
    <nav className={styles.tabs}>
      {items.map((t) => (
        <Link key={t.href} href={t.href} className={styles.tab} aria-current={t.current ? "page" : undefined}>{t.label}</Link>
      ))}
    </nav>
  );
}

export async function NextPage({ href }: { href: string | null }) {
  const t = await getT();
  return href ? <p className={styles.next}><Link href={href}>{t.d.common.earlier}</Link></p> : null;
}

export function withParams(path: string, params: Record<string, string | undefined>): string {
  const q = new URLSearchParams(Object.entries(params).filter((e): e is [string, string] => !!e[1]));
  const s = q.toString();
  return s ? `${path}?${s}` : path;
}

/** Coalition / opposition label; the colour is a neutral outline so it never competes with the for/against colours. */
export async function AlignmentBadge({ role }: { role: Alignment }) {
  const t = await getT();
  return <span className={`${styles.align} ${styles[`align_${role}`] ?? ""}`}>{t.d.alignment[role]}</span>;
}
