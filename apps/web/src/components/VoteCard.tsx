import { About, lead } from "./About";
import Link from "./Link";
import { Sides } from "./Sides";
import { Title } from "./Title";
import type { FactionNames, VoteSummary } from "@/lib/api";
import { bidiSafe, missingRollCallText, partialTurnout, verdict } from "@/lib/labels";
import { speakerRound } from "@/lib/speaker";
import { voteKind, type VoteKind } from "@/lib/voteKinds";
import { voteKindText } from "@/i18n/content/voteKinds";
import { isNumberedSubject, subjectText } from "@/i18n/content/votePhrases";
import { getT } from "@/i18n/server";
import styles from "./VoteCard.module.css";

const PLENUM = 120;

// kinds whose explanation the card repeats: agenda motions and summary resolutions are thousands of votes with the
// same text, and their titles already say what they are (the vote page still explains them)
const CARD_KINDS: VoteKind[] = ["speaker", "deputies", "arrangements", "arrangementsProposal", "continuity", "government"];

/** One vote as a card: the outcome in words first (a Speaker's election held as several votes has no outcome of its own: lib/voteKinds.ts), the Hebrew title second, then one bar for the whole plenum (so a
 *  5:0 vote is visibly a low-turnout vote), when the blocs differed the coalition/opposition line (with no government yet, how many factions were on each side), when whole factions cast no vote how many did, and on final votes the
 *  start of the law's official summary and the two sides of the plenum debate (L7) with how many spoke and how many reservations were filed. Used wherever
 *  votes are listed for a first-time visitor (home, /votes). */
export async function VoteCard({ vote, showMotion = false, note, brief = false, compact = false }:
  { vote: VoteSummary; showMotion?: boolean; note?: React.ReactNode; /** the card above already explained this kind of vote */ brief?: boolean;
    /** on a phone: the outcome, the title and the tally only (the home page, where a full card was a screen each) */ compact?: boolean }) {
  const t = await getT();
  const rc = vote.roll_call;
  const cast = rc.for + rc.against + rc.abstain;
  const round = await speakerRound(vote);
  const out = round ? null : verdict(vote, t);
  const candidate = round?.find((r) => r.vote.id === vote.id)?.candidate;
  const splitShown = vote.blocs?.contested || (!vote.blocs && vote.faction_sides?.opposed);
  const partial = splitShown ? null : partialTurnout(vote);
  // who was on each side, by name; the bare numbers where the server has not rebuilt the lists yet
  const named = !!vote.faction_sides?.for_factions?.length && !!vote.faction_sides.against_factions?.length;
  const names = (fs: FactionNames[]) => fs.map((f) => t.faction(f)).join(", ");
  // "outside the readings" and "other decision" say nothing, so they are left out
  const meta = [t.date(vote.occurred_on), vote.stage && vote.stage !== "not_applicable" ? t.d.stage[vote.stage] : null,
    showMotion && vote.motion_type && vote.motion_type !== "other" ? t.d.motion[vote.motion_type] : null]
    .filter(Boolean).join(" · ");
  // which reservation or section of the bill: all that tells apart the votes on one bill in a list
  const part = isNumberedSubject(vote.subject_he) ? subjectText(vote.subject_he, t.locale) ?? bidiSafe(vote.subject_he!) : null;
  const sides = vote.bills.find((b) => b.sides)?.sides;
  const described = vote.bills.find((b) => b.about);
  // a vote not on a bill: the start of what this kind of vote decides, as a bill's card shows its description
  const kind = vote.bills.length === 0 ? voteKind(vote) : null;
  const kindText = kind && !brief && CARD_KINDS.includes(kind) ? voteKindText(t.locale, kind) : null;
  const sideCounts = sides ? t.d.sides.counts(sides.speakers, sides.reservations) : "";
  const segments = [
    { key: "for", n: rc.for, cls: styles.for, label: t.d.breakdown.for },
    { key: "abstain", n: rc.abstain, cls: styles.abstain, label: t.d.breakdown.abstain },
    { key: "against", n: rc.against, cls: styles.against, label: t.d.breakdown.against },
  ];

  return (
    <li className={styles.item} data-compact={compact ? "" : undefined}>
      <Link href={`/votes/${vote.id}`} className={styles.link}>
        <span className="small muted">{meta}</span>
        {round ? (
          <span className={styles.verdict} data-accepted="na">{t.d.vote.round.one(round.length)}</span>
        ) : out ? (
          <span className={styles.verdict} data-accepted={out.accepted ? "yes" : "no"}>{out.text}</span>
        ) : (
          <span className="small muted">{rc.total_records > 0 ? t.d.rc.line(rc.for, rc.against, rc.abstain) : missingRollCallText(vote.method, t)}</span>
        )}
        <Title he={vote.title_he} t={vote} compact className={styles.title} />
        {candidate && t.locale !== "he" && <span className="small">{t.d.vote.round.candidate} {t.person(candidate)}</span>}
        {part && <span className={`small ${styles.part}`} dir="auto">{part}</span>}
        {described?.about && <span className={`${styles.about} ${styles.more}`}><About about={described.about} bill={described.id} max={240} compact /></span>}
        {kindText && (
          <span className={`${styles.about} ${styles.more}`}>
            <span className="small muted">{t.d.vote.kindLabel}</span>
            <span>{lead(kindText.text, t.locale, 240)}</span>
          </span>
        )}
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
        {/* no government on the vote date (a new Knesset before its government): how the factions divided instead */}
        {!vote.blocs && vote.faction_sides?.opposed && (named ? (
          <>
            <span className={`small ${styles.blocs}`}>{t.d.rc.for}: <span className={styles.sideNames}>{names(vote.faction_sides.for_factions!)}</span></span>
            <span className={`small ${styles.blocs}`}>{t.d.rc.against}: <span className={styles.sideNames}>{names(vote.faction_sides.against_factions!)}</span></span>
          </>
        ) : (
          <span className={`small num ${styles.blocs}`}>{t.d.blocs.factions(vote.faction_sides.for, vote.faction_sides.against)}</span>
        ))}
        {/* "44 for, 0 against" by one side alone is not agreement */}
        {partial && <span className={`small num ${styles.blocs}`}>{t.d.blocs.voted(partial.voted, partial.total)}</span>}
        {note && <span className={`small ${styles.note}`}>{note}</span>}
        {sides && <span className={styles.more} style={{ display: "contents" }}><Sides sides={sides} /></span>}
        {sideCounts && <span className={`small muted num ${styles.more}`}>{sideCounts}</span>}
      </Link>
    </li>
  );
}

/** `short`: on a phone only the first three cards show (the home page; the link under the list leads to the rest). */
export function VoteCards({ children, short = false }: { children: React.ReactNode; short?: boolean }) {
  return <ul className={styles.list} data-short={short ? "" : undefined}>{children}</ul>;
}
