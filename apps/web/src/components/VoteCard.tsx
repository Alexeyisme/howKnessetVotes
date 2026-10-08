import Link from "./Link";
import { Sides } from "./Sides";
import { Title } from "./Title";
import type { VoteSummary } from "@/lib/api";
import { missingRollCallText, verdict } from "@/lib/labels";
import { getT } from "@/i18n/server";
import styles from "./VoteCard.module.css";

const PLENUM = 120;

/** One vote as a card: the outcome in words first, the Hebrew title second, then one bar for the whole plenum (so a
 *  5:0 vote is visibly a low-turnout vote), when the blocs differed the coalition/opposition line, and on final votes the
 *  two sides of the plenum debate (L7) with how many spoke and how many reservations were filed. Used wherever
 *  votes are listed for a first-time visitor (home, /votes). */
export async function VoteCard({ vote, showMotion = false }: { vote: VoteSummary; showMotion?: boolean }) {
  const t = await getT();
  const rc = vote.roll_call;
  const cast = rc.for + rc.against + rc.abstain;
  const out = verdict(vote, t);
  const meta = [t.date(vote.occurred_on), vote.stage ? t.d.stage[vote.stage] : null, showMotion && vote.motion_type ? t.d.motion[vote.motion_type] : null]
    .filter(Boolean).join(" · ");
  const sides = vote.bills.find((b) => b.sides)?.sides;
  const sideCounts = sides ? t.d.sides.counts(sides.speakers, sides.reservations) : "";
  const segments = [
    { key: "for", n: rc.for, cls: styles.for, label: t.d.breakdown.for },
    { key: "abstain", n: rc.abstain, cls: styles.abstain, label: t.d.breakdown.abstain },
    { key: "against", n: rc.against, cls: styles.against, label: t.d.breakdown.against },
  ];

  return (
    <li className={styles.item}>
      <Link href={`/votes/${vote.id}`} className={styles.link}>
        <span className="small muted">{meta}</span>
        {out ? (
          <span className={styles.verdict} data-accepted={out.accepted ? "yes" : "no"}>{out.text}</span>
        ) : (
          <span className="small muted">{rc.total_records > 0 ? t.d.rc.line(rc.for, rc.against, rc.abstain) : missingRollCallText(vote.method, t)}</span>
        )}
        <Title he={vote.title_he} t={vote} compact className={styles.title} />
        {cast > 0 && (
          <>
            <span className={styles.bar} role="img" aria-label={`${t.d.rc.line(rc.for, rc.against, rc.abstain)}; ${t.d.rc.cast120(cast)}`}>
              {segments.map((s) => s.n > 0 && (
                <span key={s.key} className={`${styles.seg} ${s.cls}`} style={{ width: `${(100 * s.n) / PLENUM}%` }} title={`${s.label}: ${s.n}`} />
              ))}
            </span>
            <span className={`small num ${styles.counts}`}>
              {t.d.rc.line(rc.for, rc.against, rc.abstain)} <span className="muted">· {t.d.rc.cast120(cast)}</span>
            </span>
          </>
        )}
        {vote.blocs?.contested && (
          <span className={`small num ${styles.blocs}`}>{t.d.blocs.short(vote.blocs.coalition, vote.blocs.opposition)}</span>
        )}
        {sides && <Sides sides={sides} />}
        {sideCounts && <span className="small muted num">{sideCounts}</span>}
      </Link>
    </li>
  );
}

export function VoteCards({ children }: { children: React.ReactNode }) {
  return <ul className={styles.list}>{children}</ul>;
}
