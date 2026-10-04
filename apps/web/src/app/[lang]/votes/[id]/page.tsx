import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "@/components/Link";
import { BallotTable, type BallotRow } from "@/components/BallotTable";
import { FactionBreakdown, Legend } from "@/components/FactionBreakdown";
import { getBallots, getVote, NotFound, type Ballot, type Counts, type VoteDetail } from "@/lib/api";
import { bidiSafe, fold, missingRollCallText, verdict } from "@/lib/labels";
import { getT, type T } from "@/i18n/server";
import styles from "./vote.module.css";

// Below this many votes cast, the page explains that the plenum has no quorum (a common "how can 11 votes pass a law?").
const FEW_VOTES = 40;

async function load(idParam: string) {
  const id = Number(idParam);
  if (!Number.isInteger(id) || id <= 0) notFound();
  try {
    const [vote, ballots] = await Promise.all([getVote(id), getBallots(id)]);
    return { vote: vote.data, ballots: ballots.data };
  } catch (e) {
    if (e instanceof NotFound) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: PageProps<"/[lang]/votes/[id]">): Promise<Metadata> {
  const { vote } = await load((await params).id);
  return { title: `${vote.title_he} — ${(await getT()).date(vote.occurred_on)}` };
}

async function Tally({ c }: { c: Counts }) {
  const d = (await getT()).d.rc;
  const tiles = [
    { label: d.for, n: c.for, cls: styles.for },
    { label: d.against, n: c.against, cls: styles.against },
    { label: d.abstained, n: c.abstain, cls: styles.abstain },
    { label: d.present, n: c.present_not_voting, cls: "" },
  ];
  return (
    <dl className={styles.tally}>
      {tiles.map((x) => (
        <div key={x.label} className={styles.tile}>
          <dt className="small muted"><span className={`${styles.dot} ${x.cls}`} aria-hidden />{x.label}</dt>
          <dd className={styles.big}>{x.n}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Ballots as localized rows for the client-side table; "deviates" = a cast vote unlike its faction's majority choice. */
function ballotRows(vote: VoteDetail, ballots: Ballot[], t: T): BallotRow[] {
  const majority = new Map(vote.by_faction.map((f) => [f.faction_id, f.majority]));
  return ballots.map((b) => {
    const name = t.person(b);
    const fm = b.faction_id != null ? majority.get(b.faction_id) : undefined;
    const faction = b.faction_id
      ? t.faction({ name_he: b.faction_name_he ?? "", name_ru: b.faction_name_ru, short_ru: b.faction_short_ru, name_en: b.faction_name_en, short_en: b.faction_short_en,
          name_ar: b.faction_name_ar, short_ar: b.faction_short_ar, short_he: b.faction_short_he })
      : "—";
    return {
      id: b.person_id, href: t.href(`/members/${b.person_id}`), name, nameHe: name !== b.name_he ? b.name_he : null,
      search: fold([b.name_he, b.name_ru, b.name_en, b.name_ar].filter(Boolean).join(" ")),
      factionId: b.faction_id, faction, factionHe: b.faction_name_he && faction !== b.faction_name_he ? b.faction_name_he : null,
      factionHref: b.faction_id ? t.href(`/factions/${b.faction_id}`) : null, ambiguous: b.faction_ambiguous,
      choice: b.choice, label: t.ballot(b.choice, b.participation),
      deviates: !!b.choice && (fm === "for" || fm === "against" || fm === "abstain") && b.choice !== fm,
      note: b.counted_in_official_total === false ? t.d.ballots.notCounted : null,
      code: b.source === "knesset_votes_legacy" ? `Votes.svc ${b.source_result_code}` : String(b.source_result_code),
    };
  });
}

export default async function VotePage({ params }: PageProps<"/[lang]/votes/[id]">) {
  const { vote, ballots } = await load((await params).id);
  const t = await getT();
  const d = t.d.vote;
  const time = t.time(vote.occurred_at);
  const hint = vote.motion_type ? t.d.motionHint[vote.motion_type] : undefined;
  const rc = vote.roll_call;
  const hasRollCall = rc.total_records > 0;
  const outcome = verdict(vote, t);
  const stageHint = vote.stage ? t.d.stageHint[vote.stage] : undefined;
  const cast = rc.for + rc.against + rc.abstain;
  const rows = hasRollCall ? ballotRows(vote, ballots, t) : [];
  const factionOptions = vote.by_faction.map((f) => ({ id: f.faction_id, name: t.faction(f) }));

  return (
    <article>
      <header className={styles.head}>
        <p className="small muted">{d.meta(`${t.date(vote.occurred_on)}${time ? `, ${time}` : ""}`, vote.term, vote.id)}</p>
        <div className={styles.badges}>
          {vote.stage && <span className="badge">{t.d.stage[vote.stage]}</span>}
          {vote.motion_type && <span className="badge">{t.d.motion[vote.motion_type]}</span>}
          <span className="badge">{t.d.methodBadge(t.d.method[vote.method] ?? vote.method)}</span>
          {vote.status !== "valid" && <span className="badge">{d.status(vote.status)}</span>}
        </div>
        <h1 className={`${styles.title} he`} lang="he" dir="rtl">{vote.title_he}</h1>
        {vote.subject_he && <p className={`${styles.subject} he`} lang="he" dir="rtl">{bidiSafe(vote.subject_he)}</p>}
        {outcome && (
          <p className={styles.verdict} data-accepted={outcome.accepted ? "yes" : "no"}>
            <strong>{outcome.text}</strong>
            <span className="num">{d.resultLine(rc.for, rc.against, rc.abstain)}</span>
            <span className="small muted">{outcome.derived ? d.derived : d.official}</span>
          </p>
        )}
        {outcome && cast > 0 && cast < FEW_VOTES && (
          <p className="small muted" style={{ marginTop: 8 }}>{d.quorum(cast)} <Link href="/about/glossary#quorum">{t.d.common.glossaryLink}</Link></p>
        )}
      </header>

      <section className="card" aria-labelledby="q">
        <h2 id="q" className="section-title">{d.question}</h2>
        {vote.question_he && (
          <p className={`${styles.question} he`} lang="he" dir="rtl">«{vote.question_he}»</p>
        )}
        {hint && <p className="note" style={{ marginTop: 10 }}>{hint}</p>}
        {stageHint && <p className="small muted" style={{ marginTop: 10 }}><strong>{t.d.stage[vote.stage!]}:</strong> {stageHint} <Link href="/about/glossary">{t.d.common.glossaryLink}</Link></p>}
        {vote.bills.length > 0 && (
          <p className="small" style={{ marginTop: 10 }}>
            {d.bill}{" "}
            {vote.bills.map((b) => (
              <Link key={b.id} href={`/bills/${b.id}`} className="he" lang="he" dir="rtl">{b.title_he}</Link>
            ))}
          </p>
        )}
      </section>

      <section className="card" aria-labelledby="res">
        <h2 id="res" className="section-title">{d.resultTitle}</h2>
        {hasRollCall ? <Tally c={rc} /> : (
          <p className="note">{d.noRecords(missingRollCallText(vote.method, t))}</p>
        )}
        {vote.official_totals && (
          <p className="small" style={{ marginTop: 12 }}>
            {d.officialTotals(vote.official_totals.for, vote.official_totals.against, vote.official_totals.abstain)}
            {vote.official_totals.is_accepted != null && (vote.official_totals.is_accepted ? d.officialAccepted : d.officialRejected)}
            {vote.excluded_from_official_total > 0 && d.excluded(vote.excluded_from_official_total)}
            {vote.totals_match === true && d.totalsMatch}
            {vote.totals_match === false && d.totalsMismatch}
          </p>
        )}
        <p className="small muted" style={{ marginTop: 12 }}>
          {d.onlyRecords}
          {!vote.official_totals && d.noOfficial}
        </p>
      </section>

      {hasRollCall && (
        <section className="card" aria-labelledby="fx">
          <h2 id="fx" className="section-title">{d.byFaction}</h2>
          {vote.blocs && (
            <p className="small" style={{ marginBottom: 10 }}>
              {vote.blocs.contested && <><strong>{t.d.blocs.contested}.</strong> </>}
              <span className="num">{t.d.blocs.line(vote.blocs.coalition, vote.blocs.opposition)}</span>
            </p>
          )}
          <Legend />
          <FactionBreakdown rows={vote.by_faction} ballots={ballots} />
          {vote.unresolved_faction_records > 0 && (
            <p className="note" style={{ marginTop: 10 }}>{d.unresolved(vote.unresolved_faction_records)}</p>
          )}
        </section>
      )}

      {hasRollCall && (
        <section className="card" aria-labelledby="rc">
          <h2 id="rc" className="section-title">{d.table(ballots.length)}</h2>
          <BallotTable rows={rows} factions={factionOptions}
                       labels={{ ...t.d.ballots, shown: t.d.ballots.shown("{n}", String(rows.length)) }} />
        </section>
      )}

      <p className="small muted" style={{ marginTop: 16 }}>
        {t.d.common.sourceKnesset} <a href={vote.source_url} target="_blank" rel="noopener">{d.sourceLink}</a>
      </p>
    </article>
  );
}
