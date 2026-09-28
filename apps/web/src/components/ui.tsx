import Link from "next/link";
import type { ReactNode } from "react";
import type { Choice, Rate, VoteSummary } from "@/lib/api";
import { bidiSafe, formatDate, percent, STAGE } from "@/lib/labels";
import styles from "./ui.module.css";

export function He({ children, as: Tag = "span", className = "" }: { children: ReactNode; as?: "span" | "h1" | "p"; className?: string }) {
  return <Tag className={`he ${className}`} lang="he" dir="rtl">{children}</Tag>;
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
export function RateStat({ label, rate, unit }: { label: string; rate: Rate; unit: string }) {
  return <Stat label={label} value={percent(rate)} detail={`${rate.numerator.toLocaleString("ru-RU")} из ${rate.denominator.toLocaleString("ru-RU")} ${unit}`} />;
}

export function Stats({ children }: { children: ReactNode }) {
  return <div className={styles.stats}>{children}</div>;
}

const CHOICE_TEXT: Record<Choice, string> = { for: "за", against: "против", abstain: "возд." };

export function ChoiceMark({ choice, text }: { choice: Choice | null; text?: string }) {
  return (
    <span className={styles.choice}>
      <span className={`${styles.dot} ${choice ? styles[choice] : styles.none}`} aria-hidden />
      {text ?? (choice ? CHOICE_TEXT[choice] : "—")}
    </span>
  );
}

/** One vote in a list: date, stage, linked title, and a slot for what the page wants to show about it. */
export function VoteLine({ vote, children }: { vote: VoteSummary; children?: ReactNode }) {
  return (
    <li className={styles.voteLine}>
      <div className={styles.voteMain}>
        <span className="small muted">
          {formatDate(vote.occurred_on)} · {vote.stage ? STAGE[vote.stage] : "—"}
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

export function NextPage({ href }: { href: string | null }) {
  return href ? <p className={styles.next}><Link href={href}>Более ранние →</Link></p> : null;
}

export function withParams(path: string, params: Record<string, string | undefined>): string {
  const q = new URLSearchParams(Object.entries(params).filter((e): e is [string, string] => !!e[1]));
  const s = q.toString();
  return s ? `${path}?${s}` : path;
}
