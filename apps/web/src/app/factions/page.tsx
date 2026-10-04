import type { Metadata } from "next";
import Link from "next/link";
import { TermSelect } from "@/components/TermSelect";
import { FactionName } from "@/components/ui";
import { listFactions } from "@/lib/api";
import { period } from "@/lib/labels";

export const metadata: Metadata = { title: "Фракции" };

export default async function FactionsPage({ searchParams }: PageProps<"/factions">) {
  const sp = await searchParams;
  const term = typeof sp.term === "string" && sp.term ? sp.term : undefined;
  const { data, meta } = await listFactions({ term });
  const shown = String(meta.filters.term ?? term ?? "");

  return (
    <div className="stack">
      <header className="page-head"><h1>Фракции</h1></header>
      <form className="search" action="/factions">
        <TermSelect value={shown} />
        <button type="submit">Показать</button>
      </form>
      <p className="small muted">
        Фракция — объединение депутатов в Кнессете конкретного созыва; одна фракция может состоять из нескольких партий. Голоса относятся к фракции на дату голосования.
      </p>
      <div className="card table-scroll">
        <table>
          <thead><tr><th>Фракция</th><th>Период</th><th className="num">Членов за всё время</th><th className="num">Поимённых записей</th></tr></thead>
          <tbody>
            {data.map((f) => (
              <tr key={f.id}>
                <td><Link href={`/factions/${f.id}`}><FactionName f={f} he="inline" /></Link></td>
                <td className="small">{period(f.valid.valid_from, f.valid.valid_to)}</td>
                <td className="num">{f.members_ever}</td>
                <td className="num">{f.roll_call_records.toLocaleString("ru-RU")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
