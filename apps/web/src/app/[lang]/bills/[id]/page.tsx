import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Debate, Reservations } from "@/components/BillPositions";
import Link from "@/components/Link";
import { Summary, Title, titleText } from "@/components/Title";
import { He, PersonName, VoteLine, VoteList } from "@/components/ui";
import { getBill, type MotionType, NotFound } from "@/lib/api";
import { MAIN_MOTIONS, verdict } from "@/lib/labels";
import { getT } from "@/i18n/server";

async function load(idParam: string) {
  const id = Number(idParam);
  if (!Number.isInteger(id) || id <= 0) notFound();
  try {
    return (await getBill(id)).data;
  } catch (e) {
    if (e instanceof NotFound) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: PageProps<"/[lang]/bills/[id]">): Promise<Metadata> {
  const bill = await load((await params).id);
  return { title: titleText(bill.title_he, bill, (await getT()).locale) };
}

export default async function BillPage({ params }: PageProps<"/[lang]/bills/[id]">) {
  const bill = await load((await params).id);
  const t = await getT();
  const d = t.d.bill;
  const initiators = bill.initiators.filter((i) => i.role === "initiator");
  const joined = bill.initiators.filter((i) => i.role !== "initiator");
  const milestones = bill.timeline.filter((v) => MAIN_MOTIONS.includes(v.motion_type as MotionType) || v.motion_type === "reject_bill");
  const others = bill.timeline.filter((v) => !milestones.includes(v));

  return (
    <div className="stack">
      <header className="page-head">
        <p className="small muted">
          {d.kicker(bill.origin ? t.d.origin[bill.origin] ?? bill.origin : "", bill.term)}
          {bill.published_on && d.published(t.date(bill.published_on))}
        </p>
        <Title as="h1" he={bill.title_he} t={bill} page={`/bills/${bill.id}`} />
        {bill.status_he && <p style={{ marginTop: 8 }}><span className="badge">{d.status} <He>{bill.status_he}</He></span></p>}
        {bill.topics.length > 0 && (
          <p className="small" style={{ marginTop: 8 }}>
            {d.topics}{" "}
            {bill.topics.map((x, n) => (
              <span key={x.slug}>{n > 0 && ", "}<Link href={`/topics/${x.slug}`}
              title={x.origin === "official" ? d.officialTitle(x.evidence ?? "") : x.evidence ? d.ruleTitle(x.evidence) : undefined}>{t.topic(x)}</Link>{x.origin === "official" && "*"}</span>
            ))}
            <span className="muted small">
              {bill.topics.some((x) => x.origin === "official") && d.officialNote}
              {bill.topics.some((x) => x.origin === "rule") && d.ruleNote}
            </span>
          </p>
        )}
      </header>

      {bill.summary_he && (
        <section className="card">
          <h2 className="section-title">{d.summaryTitle}</h2>
          <Summary he={bill.summary_he} text={bill.summary} origin={bill.summary_origin} page={`/bills/${bill.id}`} />
        </section>
      )}

      {/* L7: no official summary: our machine summary of the sponsors' explanatory notes, labelled as their account */}
      {!bill.summary_he && bill.explanation_he && (
        <section className="card">
          <h2 className="section-title">{d.explanationTitle}</h2>
          <Summary he={bill.explanation_he} text={bill.explanation} origin={bill.explanation_origin} page={`/bills/${bill.id}`} />
          <p className="small muted" style={{ marginTop: 6 }}>
            {d.explanationNote}
            {bill.explanation_source_url && <> · <a href={bill.explanation_source_url} rel="noopener">{d.explanationSource}</a></>}
          </p>
        </section>
      )}

      {bill.initiators.length > 0 && (
        <section className="card">
          <h2 className="section-title">{d.initiators}</h2>
          <p>
            {initiators.map((i, n) => (
              <span key={i.person_id}>{n > 0 && ", "}<Link href={`/members/${i.person_id}`}><PersonName p={i} he="title" /></Link></span>
            ))}
          </p>
          {joined.length > 0 && (
            <p className="small muted" style={{ marginTop: 6 }}>
              {d.also} {joined.map((i, n) => (
                <span key={i.person_id}>{n > 0 && ", "}<Link href={`/members/${i.person_id}`}><PersonName p={i} he="title" /></Link> ({t.d.initiatorRole[i.role]})</span>
              ))}
            </p>
          )}
        </section>
      )}

      {/* U4: the bill as a story — the votes on the bill as a whole per reading first; reservations and sections (most
          of the rows) behind a count */}
      <section>
        <h2 className="section-title">{d.milestones}</h2>
        <VoteList>
          {milestones.map((v) => {
            const out = verdict(v, t);
            return (
              <VoteLine key={v.id} vote={v}>
                {out ? <strong>{out.text}</strong> : <span className="small muted">{t.d.rc.noRollCall}</span>}
                <span className="small num muted">{v.roll_call.total_records ? t.d.rc.line(v.roll_call.for, v.roll_call.against, v.roll_call.abstain) : ""}</span>
              </VoteLine>
            );
          })}
        </VoteList>
        {milestones.length === 0 && <p className="muted">{t.d.common.noVotes}</p>}
      </section>

      {/* L7 steps 2–3: the plenum debate and the reservations (contested final votes first) */}
      {bill.debate && <Debate debate={bill.debate} page={`/bills/${bill.id}`} />}
      {bill.reservations && <Reservations r={bill.reservations} page={`/bills/${bill.id}`} />}

      {others.length > 0 && (
        <details className="card">
          <summary className="section-title" style={{ cursor: "pointer", marginBottom: 0 }}>{d.otherVotes(others.length)}</summary>
          <p className="small muted" style={{ margin: "10px 0 8px" }}>{d.timelineHint}</p>
          <VoteList>
            {others.map((v) => (
              <VoteLine key={v.id} vote={v}>
                <span className="num">
                  {v.roll_call.total_records ? t.d.rc.line(v.roll_call.for, v.roll_call.against, 0) : t.d.rc.noRollCall}
                </span>
                {v.motion_type && <span className="small muted">{t.d.motion[v.motion_type]}</span>}
              </VoteLine>
            ))}
          </VoteList>
        </details>
      )}

      {bill.related.length > 0 && (
        <section className="card">
          <h2 className="section-title">{d.related}</h2>
          <ul style={{ listStyle: "none" }}>
            {bill.related.map((r) => <li key={r.id}><Link href={`/bills/${r.id}`}><Title he={r.title_he} t={r} compact /></Link></li>)}
          </ul>
        </section>
      )}

      <p className="small muted">
        {t.d.common.sourceKnesset} <a href={bill.source_url} target="_blank" rel="noopener">{d.sourceLink}</a>
      </p>
    </div>
  );
}
