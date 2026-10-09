import Link from "./Link";
import { Summary } from "./Title";
import { AlignmentBadge, ChoiceMark, He } from "./ui";
import type { BillDebate, BillReservations, PrintedMember, ProseText } from "@/lib/api";
import { getT } from "@/i18n/server";
import styles from "./BillPositions.module.css";

/** L7 step 2–3 texts are short machine sentences: the translation in the UI language, else the Hebrew. */
async function Prose({ p }: { p: ProseText }) {
  const t = await getT();
  return t.locale !== "he" && p.text ? <span dir="auto" title={p.text_he}>{p.text}</span> : <He>{p.text_he}</He>;
}

/** A member as the document prints them: linked and in the UI language when resolved, else the printed Hebrew. */
async function Member({ m, faction = true }: { m: PrintedMember; faction?: boolean }) {
  const t = await getT();
  const name = m.person_id ? <Link href={`/members/${m.person_id}`}>{t.person(m)}</Link> : <He>{m.name_he}</He>;
  const f = faction && (m.faction_name ?? m.faction_name_he);
  return <span className={styles.member}>{name}{f && <span className="muted"> ({f})</span>}</span>;
}

async function List({ members, faction = true }: { members: PrintedMember[]; faction?: boolean }) {
  return <>{members.map((m, n) => <span key={n}>{n > 0 && ", "}<Member m={m} faction={faction} /></span>)}</>;
}

/** What was said in the plenum: a summary, the arguments by side with who made them, and every speaker with how
 *  they voted in the end. */
export async function Debate({ debate, page }: { debate: BillDebate; page: string }) {
  const t = await getT();
  const d = t.d.bill;
  const sides = (["for", "against"] as const).map((side) => ({ side, args: debate.arguments.filter((a) => a.side === side) }));
  return (
    <section className="card">
      <h2 className="section-title">{d.debateTitle}</h2>
      <Summary he={debate.summary.text_he} text={debate.summary.text} origin={debate.summary.text_origin} page={page} />
      <div className={styles.sides}>
        {sides.map(({ side, args }) => (
          <div key={side} className={styles.side}>
            <h3 className={styles.sideTitle}><ChoiceMark choice={side} text={side === "for" ? d.debateFor : d.debateAgainst} /></h3>
            {args.length === 0 ? <p className="small muted">{d.debateNone}</p> : (
              <ul className={styles.args}>
                {args.map((a, n) => (
                  <li key={n}>
                    <Prose p={a} />
                    <div className="small"><List members={a.speakers.map((i) => debate.speakers[i]).filter(Boolean)} /></div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
      <details className={styles.more}>
        <summary className="small" style={{ cursor: "pointer" }}>{d.debateSpeakers(debate.speakers.length)}</summary>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{d.debateCols.member}</th><th>{d.debateCols.faction}</th><th>{d.debateCols.readings}</th>
                <th className="num">{d.debateCols.speeches}</th><th>{d.debateCols.final}</th>
              </tr>
            </thead>
            <tbody>
              {debate.speakers.map((s, n) => (
                <tr key={n}>
                  <td><Member m={s} faction={false} />{!s.person_id && s.affiliation_he && <He className="muted small"> ({s.affiliation_he})</He>}</td>
                  <td>{s.faction_name ?? s.faction_name_he ?? "—"}{s.alignment && s.alignment !== "unknown" && <> <AlignmentBadge role={s.alignment} /></>}</td>
                  <td className="small">{s.stages.map((x) => t.d.stage[x]).join(", ")}</td>
                  <td className="num">{t.num(s.speeches)}</td>
                  <td>{s.final_participation ? <ChoiceMark choice={s.final_choice} text={t.ballot(s.final_choice, s.final_participation)} />
                    : <span className="small muted">{s.person_id ? d.noRecord : "—"}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <p className="small muted" style={{ marginTop: 8 }}>
        {d.debateNote}{debate.truncated && <> {d.debateTruncated}</>}{" "}
        {d.debateSources(debate.sources.length)}:{" "}
        {debate.sources.map((u, n) => <span key={u}>{n > 0 && ", "}<a href={u} rel="noopener">{n + 1}</a></span>)}
        {" · "}<Link href={`/suggest?page=${page}`} prefetch={false} rel="nofollow">{t.d.common.report}</Link>
      </p>
    </section>
  );
}

/** The reservations to the second reading: counts by faction (with coalition/opposition on the final vote date),
 *  who proposed what, and who asked to speak. */
export async function Reservations({ r, page }: { r: BillReservations; page: string }) {
  const t = await getT();
  const d = t.d.bill;
  return (
    <section className="card">
      <h2 className="section-title">{d.reservationsTitle}</h2>
      {r.total === 0 ? <p>{d.reservationsNone}</p> : (
        <>
          <p>{d.reservationsLead(r.total)}</p>
          {r.summary && <Summary he={r.summary.text_he} text={r.summary.text} origin={r.summary.text_origin} page={page} />}
          {r.by_faction.length > 0 && (
            <>
              <h3 className={styles.sub}>{d.reservationsByFaction}</h3>
              <ul className={styles.factions}>
                {r.by_faction.map((f) => (
                  <li key={f.faction_id}>
                    <Link href={`/factions/${f.faction_id}`}>{t.faction(f)}</Link>
                    {f.alignment && f.alignment !== "unknown" && <> <AlignmentBadge role={f.alignment} /></>}
                    <span className="small muted num"> · {d.reservationsCount(f.reservations, f.members)}</span>
                  </li>
                ))}
              </ul>
              <p className="small muted">{d.reservationsJoint}{r.unresolved_proposers > 0 && <> {d.reservationsUnresolved(r.unresolved_proposers)}</>}</p>
            </>
          )}
          <details className={styles.more}>
            <summary className="small" style={{ cursor: "pointer" }}>{d.reservationsGroups}</summary>
            <ul className={styles.groups}>
              {r.groups.map((g, n) => (
                <li key={n}>
                  <strong><He>{g.label_he}</He></strong> <span className="small muted num">· {t.num(g.reservations)}</span>
                  {g.gist && <div><Prose p={g.gist} /></div>}
                  {g.sections.length > 0 && <div className="small muted">{d.reservationsSections} <He>{g.sections.join(", ")}</He></div>}
                  {(g.members.length > 1 || g.members[0]?.name_he !== g.label_he) && <div className="small"><List members={g.members} faction={false} /></div>}
                </li>
              ))}
            </ul>
          </details>
        </>
      )}
      {r.speak_requests.length > 0 && <p className="small" style={{ marginTop: 8 }}>{d.reservationsSpeak} <List members={r.speak_requests} /></p>}
      <p className="small muted" style={{ marginTop: 8 }}>
        {r.total > 0 && <>{d.reservationsNote}{!r.numbers_checked && <> {d.reservationsUnchecked}</>} </>}
        <a href={r.source_url} rel="noopener">{d.reservationsSource}</a>
        {" · "}<Link href={`/suggest?page=${page}`} prefetch={false} rel="nofollow">{t.d.common.report}</Link>
      </p>
    </section>
  );
}
