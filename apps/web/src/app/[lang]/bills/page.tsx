import type { Metadata } from "next";
import Link from "@/components/Link";
import { TermSelect } from "@/components/TermSelect";
import { Title } from "@/components/Title";
import { He, NextPage, withParams } from "@/components/ui";
import { listBills } from "@/lib/api";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.bills.title };
}

export default async function BillsPage({ searchParams }: PageProps<"/[lang]/bills">) {
  const t = await getT();
  const d = t.d.bills;
  const sp = await searchParams;
  const str = (k: string) => (typeof sp[k] === "string" && sp[k] ? (sp[k] as string) : undefined);
  const q = str("q")?.trim();
  const term = str("term");
  const passed = str("passed");
  const topic = str("topic");
  const cursor = str("cursor");
  const { data, next_cursor } = await listBills({ q: q && q.length >= 2 ? q : undefined, term, topic, third_reading: passed ? "true" : undefined, cursor, limit: "30" });

  return (
    <div className="stack">
      <header className="page-head"><h1>{d.title}</h1></header>
      <form className="search" action={t.href("/bills")}>
        <input name="q" defaultValue={q} placeholder={d.searchPh} lang="he" dir="auto" />
        <TermSelect value={term} all />
        {topic && <input type="hidden" name="topic" value={topic} />}
        <label className="small" style={{ alignSelf: "center" }}>
          <input type="checkbox" name="passed" value="1" defaultChecked={!!passed} /> {d.onlyPassed}
        </label>
        <button type="submit">{t.d.common.find}</button>
      </form>
      <p className="small muted">{d.lead}</p>
      <ul className="card" style={{ listStyle: "none", padding: 0 }}>
        {data.map((b) => (
          <li key={b.id} style={{ padding: "10px 16px", borderBottom: "1px solid var(--hairline)" }}>
            <Link href={`/bills/${b.id}`} style={{ display: "block", fontWeight: 600, color: "var(--ink)" }}><Title he={b.title_he} t={b} compact /></Link>
            <span className="small muted">
              {t.d.common.term(b.term)} · {t.d.common.votesCount(b.votes)}{b.last_vote_on && ` · ${t.d.common.lastVote(t.date(b.last_vote_on))}`}
              {b.passed_third_reading && ` · ${t.d.common.passedThird}`}
              {b.status_he && <> · <He>{b.status_he}</He></>}
              {b.sides?.speakers || b.sides?.reservations ? ` · ${t.d.sides.counts(b.sides.speakers, b.sides.reservations)}` : null}
            </span>
          </li>
        ))}
      </ul>
      {data.length === 0 && <p className="muted">{t.d.common.nothingFound}</p>}
      <NextPage href={next_cursor ? withParams("/bills", { q, term, topic, passed, cursor: next_cursor }) : null} />
    </div>
  );
}
