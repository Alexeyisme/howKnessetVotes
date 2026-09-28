import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { He, VoteLine, VoteList } from "@/components/ui";
import { getBill, NotFound } from "@/lib/api";
import { formatDate, INITIATOR_ROLE, MOTION, ORIGIN } from "@/lib/labels";

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

export async function generateMetadata({ params }: PageProps<"/bills/[id]">): Promise<Metadata> {
  return { title: (await load((await params).id)).title_he };
}

export default async function BillPage({ params }: PageProps<"/bills/[id]">) {
  const bill = await load((await params).id);
  const initiators = bill.initiators.filter((i) => i.role === "initiator");
  const joined = bill.initiators.filter((i) => i.role !== "initiator");

  return (
    <div className="stack">
      <header className="page-head">
        <p className="small muted">
          Законопроект {bill.origin ? ORIGIN[bill.origin] ?? bill.origin : ""} · {bill.term}-й созыв
          {bill.published_on && ` · опубликован как закон ${formatDate(bill.published_on)}`}
        </p>
        <He as="h1">{bill.title_he}</He>
        {bill.status_he && <p style={{ marginTop: 8 }}><span className="badge">Статус: <He>{bill.status_he}</He></span></p>}
      </header>

      {bill.summary_he && <section className="card"><He as="p">{bill.summary_he}</He></section>}

      {bill.initiators.length > 0 && (
        <section className="card">
          <h2 className="section-title">Инициаторы</h2>
          <p>
            {initiators.map((i, n) => (
              <span key={i.person_id}>{n > 0 && ", "}<Link href={`/members/${i.person_id}`}><He>{i.name_he}</He></Link></span>
            ))}
          </p>
          {joined.length > 0 && (
            <p className="small muted" style={{ marginTop: 6 }}>
              Также: {joined.map((i, n) => (
                <span key={i.person_id}>{n > 0 && ", "}<Link href={`/members/${i.person_id}`}><He>{i.name_he}</He></Link> ({INITIATOR_ROLE[i.role]})</span>
              ))}
            </p>
          )}
        </section>
      )}

      <section>
        <h2 className="section-title">Все голосования в пленуме ({bill.timeline.length})</h2>
        <p className="small muted" style={{ marginBottom: 8 }}>
          По порядку. Голосования по оговоркам и отдельным статьям показаны отдельно от голосования за законопроект в целом.
        </p>
        <VoteList>
          {bill.timeline.map((v) => (
            <VoteLine key={v.id} vote={v}>
              <span className="num">
                {v.roll_call.total_records ? `${v.roll_call.for} за · ${v.roll_call.against} против` : "без поимённого списка"}
              </span>
              {v.motion_type && <span className="small muted">{MOTION[v.motion_type]}</span>}
            </VoteLine>
          ))}
        </VoteList>
      </section>

      {bill.related.length > 0 && (
        <section className="card">
          <h2 className="section-title">Связанные законопроекты</h2>
          <ul style={{ listStyle: "none" }}>
            {bill.related.map((r) => <li key={r.id}><Link href={`/bills/${r.id}`}><He>{r.title_he}</He></Link></li>)}
          </ul>
        </section>
      )}

      <p className="small muted">
        Источник: <a href={bill.source_url} target="_blank" rel="noopener">карточка законопроекта в базе законодательства Кнессета ↗</a>
      </p>
    </div>
  );
}
