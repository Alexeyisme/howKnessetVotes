import type { Metadata } from "next";
import { TermSelect } from "@/components/TermSelect";
import { MemberChip, MemberGrid } from "@/components/ui";
import { listMembers } from "@/lib/api";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.members.title };
}

// A grid of portraits and names instead of a table: 120 four-column rows did not fit a phone.
export default async function MembersPage({ searchParams }: PageProps<"/[lang]/members">) {
  const t = await getT();
  const d = t.d.members;
  const sp = await searchParams;
  const term = typeof sp.term === "string" && sp.term ? sp.term : "25";
  const q = typeof sp.q === "string" && sp.q.trim().length >= 2 ? sp.q.trim() : undefined;
  const { data } = await listMembers({ term: q ? undefined : term, q });

  return (
    <div className="stack">
      <header className="page-head"><h1>{d.title}</h1></header>
      <form className="search" action={t.href("/members")}>
        <input name="q" defaultValue={q} placeholder={d.searchPh} dir="auto" />
        <TermSelect value={term} />
        <button type="submit">{t.d.common.show}</button>
      </form>
      <p className="small muted">{q ? d.searchAll(data.length) : d.termCount(term, data.length)}</p>
      <MemberGrid>
        {data.map((m) => <MemberChip key={m.id} m={m} faction={m.last_faction} />)}
      </MemberGrid>
      {data.length === 0 && <p className="muted">{t.d.common.nothingFound}</p>}
    </div>
  );
}
