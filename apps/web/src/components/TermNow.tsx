import Link from "./Link";
import { Title } from "./Title";
import { getVote, listVotes, type FactionNames, type VoteDetail, type VoteSummary } from "@/lib/api";
import { partialTurnout, verdict } from "@/lib/labels";
import { speakerRound, type RoundVote } from "@/lib/speaker";
import { byDay, cell, likeKey, numbered, twoGroups, type Cell } from "@/lib/termNow";
import { voteKind } from "@/lib/voteKinds";
import { voteKindText } from "@/i18n/content/voteKinds";
import { isNumberedSubject, subjectText } from "@/i18n/content/votePhrases";
import { getT } from "@/i18n/server";
import styles from "./TermNow.module.css";

// The list holds the term's latest votes up to this many, the table the latest of those: the page is for a Knesset's
// first weeks, before its government; after that /votes shows the ordinary feed again.
const MAX_VOTES = 100;
const MAX_COLUMNS = 30;
// The two-groups statement rests on well-attended votes only, like the site's "factions on opposite sides" view: with
// nine MKs in the plenum (the state-of-emergency vote, 8:1) a faction's "majority" is one or two people.
const MIN_CAST = 60;
const SYMBOL: Record<Cell, string> = { for: "+", against: "−", abstain: "0", mixed: "±", none: "·", no_record: "" };

/** A new Knesset before its government, on one page: whether its factions fell into the same two groups every time,
 *  a table of factions by votes, and the votes by day with runs of look-alike votes as one entry. All of it is what
 *  the roll calls show; no group is called a coalition. */
export async function TermNow({ term, startedOn }: { term: number; startedOn: string }) {
  const t = await getT();
  const d = t.d.votes.now;
  const votes = (await listVotes({ date_from: startedOn, limit: String(MAX_VOTES) })).data.filter((v) => v.term === term);
  if (votes.length === 0) return <p className="muted">{t.d.common.noVotes}</p>;
  const no = numbered(votes);
  const columns = votes.slice(0, MAX_COLUMNS).reverse();   // the table reads in the order the votes were held
  const details = new Map<number, VoteDetail>(
    (await Promise.all(columns.map((v) => getVote(v.id).then((r) => r.data, () => null)))).flatMap((x) => (x ? [[x.id, x] as const] : [])));

  // the table's rows: every faction a vote knows, the largest first within its group
  const factions = new Map<number, FactionNames & { size: number }>();
  for (const x of details.values()) {
    for (const f of x.by_faction) factions.set(f.faction_id, { ...f, size: Math.max(factions.get(f.faction_id)?.size ?? 0, f.counts.total_records) });
    for (const f of x.factions_without_records ?? []) factions.set(f.faction_id, { ...f, size: Math.max(factions.get(f.faction_id)?.size ?? 0, f.members) });
  }
  const ids = (xs?: { id: number }[]) => (xs ?? []).map((f) => f.id);
  const groups = twoGroups(votes.filter((v) => v.roll_call.for + v.roll_call.against + v.roll_call.abstain >= MIN_CAST)
    .map((v) => ({ for: ids(v.faction_sides?.for_factions), against: ids(v.faction_sides?.against_factions) })));
  const rank = (id: number) => (groups?.a.includes(id) ? 0 : groups?.b.includes(id) ? 1 : 2);
  const rows = [...factions.entries()].sort(([a, x], [b, y]) => rank(a) - rank(b) || y.size - x.size || a - b);
  const names = (list: number[]) => list.map((id) => factions.get(id)).filter((f) => !!f).sort((x, y) => y.size - x.size).map((f) => t.faction(f)).join(", ");
  const label: Record<Cell, string> = { for: t.d.breakdown.for, against: t.d.breakdown.against, abstain: t.d.breakdown.abstain,
    mixed: t.d.majority.mixed, none: t.d.majority.none, no_record: d.noRecord };

  // runs of look-alike votes: the same kind (or bill), outcome and factions on each side; a Speaker's election held as
  // several votes is one entry whatever the sides
  const keyOf = (v: VoteSummary): string | null => {
    const kind = v.bills.length === 0 ? voteKind(v) : null;
    if (kind === "speaker") return `speaker|${v.title_he}`;
    const what = kind ?? (v.bills.length === 1 ? `bill:${v.bills[0].id}` : null);
    return likeKey(what, verdict(v, t)?.accepted ?? null, ids(v.faction_sides?.for_factions), ids(v.faction_sides?.against_factions));
  };
  const days = byDay(votes, keyOf);
  const rounds = new Map<number, RoundVote[]>();
  for (const day of days) {
    for (const e of day.entries) {
      if (e.length > 1 && keyOf(e[0])?.startsWith("speaker|")) {
        const round = await speakerRound(e[0]);
        if (round) rounds.set(e[0].id, round);
      }
    }
  }

  const sides = (v: VoteSummary) => {
    const fs = v.faction_sides;
    if (fs?.opposed && fs.for_factions?.length && fs.against_factions?.length) {
      return (
        <span className="small">
          <strong>{t.d.rc.for}:</strong> {fs.for_factions.map((f) => t.faction(f)).join(", ")}{" · "}
          <strong>{t.d.rc.against}:</strong> {fs.against_factions.map((f) => t.faction(f)).join(", ")}
        </span>
      );
    }
    const partial = partialTurnout(v);
    return partial ? <span className="small muted">{t.d.blocs.voted(partial.voted, partial.total)}</span> : null;
  };
  const outcome = (v: VoteSummary) => {
    const out = verdict(v, t);
    const rc = v.roll_call;
    return (
      <span className="small num">
        {out && <strong className={styles.verdict} data-accepted={out.accepted ? "yes" : "no"}>{out.text}</strong>}
        {out && " · "}{t.d.rc.line(rc.for, rc.against, rc.abstain)}
      </span>
    );
  };
  const range = (e: VoteSummary[]) => {
    const ns = e.map((v) => no.get(v.id)!);
    return e.length > 1 ? d.no(Math.min(...ns), Math.max(...ns)) : d.no(ns[0]);
  };

  return (
    <div className={styles.now}>
      <p className="muted">{d.lead}</p>

      {groups && (
        <section className="note" aria-labelledby="now-groups">
          <h2 id="now-groups" className={styles.h}>{d.groupsTitle}</h2>
          <p>{d.groups(groups.votes, MIN_CAST)}</p>
          <p style={{ marginTop: 6 }}><strong>{d.groupA}</strong> {names(groups.a)}</p>
          <p><strong>{d.groupB}</strong> {names(groups.b)}</p>
        </section>
      )}

      <section className="card" aria-labelledby="now-table">
        <h2 id="now-table" className="section-title">{d.table}</h2>
        <ul className={styles.legend}>
          {(Object.keys(SYMBOL) as Cell[]).map((c) => (
            <li key={c}><span className={`${styles.cell} ${styles[c]}`} aria-hidden>{SYMBOL[c]}</span> {label[c]}</li>
          ))}
        </ul>
        <div className="table-scroll">
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">{d.faction}</th>
                {columns.map((v) => (
                  <th key={v.id} scope="col" className="num"><a href={`#v${v.id}`} title={v.title ?? v.title_he}>{no.get(v.id)}</a></th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(([id, f], i) => (
                <tr key={id} data-break={i > 0 && rank(id) !== rank(rows[i - 1][0]) ? "" : undefined}>
                  <th scope="row"><Link href={`/factions/${id}`}>{t.faction(f)}</Link></th>
                  {columns.map((v) => {
                    const x = details.get(v.id);
                    const c = x ? cell(x, id) : null;
                    return (
                      <td key={v.id}>
                        {c && <Link href={`/votes/${v.id}`} className={`${styles.cell} ${styles[c]}`} title={`${d.no(no.get(v.id)!)} · ${t.faction(f)}: ${label[c]}`}>
                          <span aria-hidden>{SYMBOL[c]}</span><span className={styles.sr}>{label[c]}</span>
                        </Link>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="small muted" style={{ marginTop: 10 }}>
          {d.tableNote}{votes.length > columns.length && ` ${d.capped(columns.length, votes.length)}`}
        </p>
      </section>

      <section aria-labelledby="now-days">
        <h2 id="now-days" className="section-title">{d.days}</h2>
        {days.map((day) => (
          <div key={day.on} className={styles.day}>
            <h3 className={styles.date}>{t.date(day.on)}</h3>
            <ol className={styles.entries}>
              {day.entries.map((e) => {
                const first = e[0];
                const round = rounds.get(first.id);
                const kind = first.bills.length === 0 ? voteKind(first) : null;
                return (
                  <li key={first.id} id={e.length === 1 ? `v${first.id}` : undefined} className={styles.entry}>
                    <span className={`small num ${styles.no}`}>{range(e)}</span>
                    {e.length === 1 ? (
                      <div className={styles.body}>
                        <Link href={`/votes/${first.id}`}><Title he={first.title_he} t={first} compact /></Link>
                        {isNumberedSubject(first.subject_he) && <span className="small">{subjectText(first.subject_he, t.locale) ?? first.subject_he}</span>}
                        {outcome(first)}
                        {sides(first)}
                      </div>
                    ) : round ? (
                      // a Speaker's election: the candidacies side by side, most votes first, no verdict for any one
                      <div className={styles.body}>
                        <strong>{voteKindText(t.locale, "speaker").title}</strong>
                        <ul className={styles.sub}>
                          {round.map((r) => (
                            <li key={r.vote.id} id={`v${r.vote.id}`}>
                              <Link href={`/votes/${r.vote.id}`}>{r.candidate ? t.person(r.candidate) : d.no(no.get(r.vote.id)!)}</Link>
                              <span className="num"> — {t.d.rc.line(r.vote.roll_call.for, r.vote.roll_call.against, r.vote.roll_call.abstain)}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <div className={styles.body}>
                        <strong>{d.group(e.length, kind ? voteKindText(t.locale, kind).title : d.sameBill)}</strong>
                        {!kind && <Link href={`/bills/${first.bills[0].id}`}><Title he={first.bills[0].title_he} t={first.bills[0]} compact /></Link>}
                        {sides(first)}
                        <ul className={styles.sub}>
                          {e.map((v) => (
                            <li key={v.id} id={`v${v.id}`}>
                              <Link href={`/votes/${v.id}`}>
                                {kind ? <Title he={v.title_he} t={v} compact />
                                  : subjectText(v.subject_he, t.locale) ?? v.subject_he ?? t.d.stage[v.stage ?? "unknown"]}
                              </Link>
                              {outcome(v)}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </li>
                );
              })}
            </ol>
          </div>
        ))}
      </section>
    </div>
  );
}
