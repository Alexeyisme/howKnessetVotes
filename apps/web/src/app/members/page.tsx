import type { Metadata } from "next";
import Link from "next/link";
import { TermSelect } from "@/components/TermSelect";
import { He } from "@/components/ui";
import { listMembers } from "@/lib/api";

export const metadata: Metadata = { title: "Депутаты" };

export default async function MembersPage({ searchParams }: PageProps<"/members">) {
  const sp = await searchParams;
  const term = typeof sp.term === "string" && sp.term ? sp.term : "25";
  const q = typeof sp.q === "string" && sp.q.trim().length >= 2 ? sp.q.trim() : undefined;
  const { data } = await listMembers({ term: q ? undefined : term, q });

  return (
    <div className="stack">
      <header className="page-head"><h1>Депутаты</h1></header>
      <form className="search" action="/members">
        <input name="q" defaultValue={q} placeholder="Имя на иврите, например לפיד" lang="he" dir="auto" />
        <TermSelect value={term} />
        <button type="submit">Показать</button>
      </form>
      <p className="small muted">{q ? `Поиск по всем созывам: ${data.length}` : `${term}-й созыв: ${data.length} депутатов с поимёнными голосами`}</p>
      <div className="card table-scroll">
        <table>
          <thead><tr><th>Депутат</th><th>Последняя фракция</th><th>Созывы</th><th className="num">Поимённых записей</th></tr></thead>
          <tbody>
            {data.map((m) => (
              <tr key={m.id}>
                <td><Link href={`/members/${m.id}`}><He>{m.name_he}</He></Link></td>
                <td>{m.last_faction ? <Link href={`/factions/${m.last_faction.id}`}><He>{m.last_faction.name_he}</He></Link> : "—"}</td>
                <td className="small">{m.terms.join(", ")}</td>
                <td className="num">{m.roll_call_records.toLocaleString("ru-RU")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
