import type { Metadata } from "next";
import Link from "next/link";
import { He } from "@/components/ui";
import { search } from "@/lib/api";

export const metadata: Metadata = { title: "Поиск" };

export default async function SearchPage({ searchParams }: PageProps<"/search">) {
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q.trim() : "";
  const r = q.length >= 2 ? (await search(q)).data : null;
  const empty = r && !r.topics.length && !r.bills.length && !r.members.length && !r.factions.length;

  return (
    <div className="stack">
      <header className="page-head"><h1>Поиск</h1></header>
      <form className="search" action="/search">
        <input name="q" defaultValue={q} placeholder="Тема по-русски, название закона или имя на иврите, номер" dir="auto" autoFocus />
        <button type="submit">Найти</button>
      </form>
      <p className="small muted">
        По-русски ищутся темы и фракции (например, «транспорт», «ликуд»). Названия законов и имена депутатов — на иврите, с учётом опечаток. Номер — законопроект.
      </p>
      {empty && <p className="muted">Ничего не найдено.</p>}
      {r && r.topics.length > 0 && (
        <section className="card"><h2 className="section-title">Темы</h2>
          {r.topics.map((t) => <p key={t.slug}><Link href={`/topics/${t.slug}`}>{t.label_ru}</Link> <span className="small muted">· {t.bills} законопр.</span></p>)}
        </section>
      )}
      {r && r.factions.length > 0 && (
        <section className="card"><h2 className="section-title">Фракции</h2>
          {r.factions.map((f) => (
            <p key={f.id}><Link href={`/factions/${f.id}`}>{f.name_ru && `${f.name_ru} · `}<He>{f.name_he}</He></Link> <span className="small muted">· {f.term}-й созыв</span></p>
          ))}
        </section>
      )}
      {r && r.members.length > 0 && (
        <section className="card"><h2 className="section-title">Депутаты</h2>
          {r.members.map((m) => <p key={m.id}><Link href={`/members/${m.id}`}><He>{m.name_he}</He></Link></p>)}
        </section>
      )}
      {r && r.bills.length > 0 && (
        <section className="card"><h2 className="section-title">Законопроекты</h2>
          {r.bills.map((b) => (
            <p key={b.id} style={{ padding: "4px 0" }}>
              <Link href={`/bills/${b.id}`} style={{ display: "block", textAlign: "right" }}><He>{b.title_he}</He></Link>
              <span className="small muted">{b.term}-й созыв · голосований: {b.votes}{b.passed_third_reading && " · принят"}</span>
            </p>
          ))}
        </section>
      )}
    </div>
  );
}
