import type { Metadata } from "next";
import { NewTermNotice } from "@/components/NewTermNotice";
import { TermSelect } from "@/components/TermSelect";
import { MemberChip, MemberGrid } from "@/components/ui";
import { currentTerm, latestVotedTerm, listMembers, termWithoutVotes } from "@/lib/api";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.members.title };
}

// A grid of portraits and names instead of a table: 120 four-column rows did not fit a phone.
export default async function MembersPage({ searchParams }: PageProps<"/[lang]/members">) {
  const t = await getT();
  const d = t.d.members;
  const sp = await searchParams;
  const asked = typeof sp.term === "string" && sp.term ? sp.term : undefined;
  const q = typeof sp.q === "string" && sp.q.trim().length >= 2 ? sp.q.trim() : undefined;
  let term = asked ?? await currentTerm();
  let { data } = await listMembers({ term: q ? undefined : term, q });
  // a Knesset sworn in before the source lists its MKs: show the last one that voted rather than an empty page
  if (!asked && !q && data.length === 0) {
    term = await latestVotedTerm();
    ({ data } = await listMembers({ term }));
  }
  const noVotes = !q && data.length > 0 && await termWithoutVotes(term);

  return (
    <div className="stack">
      <header className="page-head"><h1>{d.title}</h1></header>
      <NewTermNotice fallback={asked || q ? undefined : term} />
      <form className="search" action={t.href("/members")}>
        <input name="q" defaultValue={q} placeholder={d.searchPh} dir="auto" />
        <TermSelect value={term} />
        <button type="submit">{t.d.common.show}</button>
      </form>
      <p className="small muted">{q ? d.searchAll(data.length)
        : noVotes ? d.termCountNoVotes(term, data.length) : d.termCount(term, data.length)}</p>
      <MemberGrid>
        {data.map((m) => <MemberChip key={m.id} m={m} faction={m.last_faction} />)}
      </MemberGrid>
      {data.length === 0 && <p className="muted">{t.d.common.nothingFound}</p>}
    </div>
  );
}
