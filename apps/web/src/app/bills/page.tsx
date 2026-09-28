import type { Metadata } from "next";
import Link from "next/link";
import { TermSelect } from "@/components/TermSelect";
import { He, NextPage, withParams } from "@/components/ui";
import { listBills } from "@/lib/api";
import { formatDate } from "@/lib/labels";

export const metadata: Metadata = { title: "Законопроекты" };

export default async function BillsPage({ searchParams }: PageProps<"/bills">) {
  const sp = await searchParams;
  const str = (k: string) => (typeof sp[k] === "string" && sp[k] ? (sp[k] as string) : undefined);
  const q = str("q")?.trim();
  const term = str("term");
  const passed = str("passed");
  const cursor = str("cursor");
  const { data, next_cursor } = await listBills({ q: q && q.length >= 2 ? q : undefined, term, third_reading: passed ? "true" : undefined, cursor, limit: "30" });

  return (
    <div className="stack">
      <header className="page-head"><h1>Законопроекты</h1></header>
      <form className="search" action="/bills">
        <input name="q" defaultValue={q} placeholder="Слово из названия на иврите или номер" lang="he" dir="auto" />
        <TermSelect value={term} allLabel="Все созывы" />
        <label className="small" style={{ alignSelf: "center" }}>
          <input type="checkbox" name="passed" value="1" defaultChecked={!!passed} /> только принятые в третьем чтении
        </label>
        <button type="submit">Найти</button>
      </form>
      <p className="small muted">Законопроекты, по которым голосовал пленум; сначала те, по которым голосовали недавно.</p>
      <ul className="card" style={{ listStyle: "none", padding: 0 }}>
        {data.map((b) => (
          <li key={b.id} style={{ padding: "10px 16px", borderBottom: "1px solid var(--hairline)" }}>
            <Link href={`/bills/${b.id}`} style={{ display: "block", textAlign: "right", fontWeight: 600, color: "var(--ink)" }}><He>{b.title_he}</He></Link>
            <span className="small muted">
              {b.term}-й созыв · голосований: {b.votes}{b.last_vote_on && ` · последнее ${formatDate(b.last_vote_on)}`}
              {b.passed_third_reading && " · принят в третьем чтении"}
              {b.status_he && <> · <He>{b.status_he}</He></>}
            </span>
          </li>
        ))}
      </ul>
      {data.length === 0 && <p className="muted">Ничего не найдено.</p>}
      <NextPage href={next_cursor ? withParams("/bills", { q, term, passed, cursor: next_cursor }) : null} />
    </div>
  );
}
