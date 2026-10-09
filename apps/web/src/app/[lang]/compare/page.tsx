import type { Metadata } from "next";
import Link from "@/components/Link";
import { ChoiceMark, FactionName, PersonName, RateStat, Stats, Tabs, VoteLine, VoteList } from "@/components/ui";
import { compareFactions, compareMembers, listFactions, listMembers, NotFound, type Comparison } from "@/lib/api";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.compare.title };
}

// U7 / R14: "does X vote like Y?" — two parties (factions of the current Knesset) or two members, the agreement rate
// with its denominator, then the votes where they differed. Selection lives in the URL: ?kind=members&a=…&b=…
export default async function ComparePage({ searchParams }: PageProps<"/[lang]/compare">) {
  const t = await getT();
  const d = t.d.compare;
  const sp = await searchParams;
  const kind = sp.kind === "members" ? "members" : "factions";
  const num = (k: string) => (typeof sp[k] === "string" && /^\d+$/.test(sp[k] as string) ? Number(sp[k]) : undefined);
  const a = num("a"), b = num("b");
  const cursor = typeof sp.cursor === "string" ? sp.cursor : undefined;
  const options = kind === "members" ? (await listMembers({ term: "25" })).data : (await listFactions({})).data;
  let result: Comparison | null = null;
  if (a && b && a !== b) {
    try {
      result = (kind === "members" ? await compareMembers(a, b, cursor) : await compareFactions(a, b, cursor)).data;
    } catch (e) {
      if (!(e instanceof NotFound)) throw e;
    }
  }
  const name = (id: number | undefined) => {
    const o = options.find((x) => x.id === id);
    if (!o) return "";
    return "name_he" in o && "terms" in o ? t.person(o) : t.faction(o as Parameters<typeof t.faction>[0]);
  };

  return (
    <div className="stack">
      <header className="page-head"><h1>{d.title}</h1></header>
      <p className="muted">{d.lead}</p>
      <Tabs items={[
        { href: "/compare", label: d.parties, current: kind === "factions" },
        { href: "/compare?kind=members", label: d.members, current: kind === "members" },
      ]} />
      <form className="search" action={t.href("/compare")}>
        <input type="hidden" name="kind" value={kind} />
        {(["a", "b"] as const).map((side) => (
          <select key={side} name={side} defaultValue={String((side === "a" ? a : b) ?? "")} aria-label={side.toUpperCase()}>
            <option value="">{side.toUpperCase()}…</option>
            {options.map((o) => <option key={o.id} value={o.id}>{"terms" in o ? t.person(o) : t.faction(o)}</option>)}
          </select>
        ))}
        <button type="submit">{t.d.common.show}</button>
      </form>

      {!result && <p className="small muted">{d.pick}</p>}
      {result && (
        <>
          <Stats>
            <RateStat label={`${d.agreement}: ${name(a)} · ${name(b)}`} rate={result.agreement} unit={d.agreementUnit} />
          </Stats>
          <section>
            <h2 className="section-title">{d.differences(result.differences_total)}</h2>
            <p className="small muted">{d.range(result.differences.length ? result.differences_offset + 1 : 0, result.differences.length ? result.differences_offset + result.differences.length : 0, result.differences_total)}</p>
            <VoteList>
              {result.differences.map((x) => (
                <VoteLine key={x.vote.id} vote={x.vote}>
                  <span className="small"><strong>{name(a)}</strong>: <ChoiceMark choice={x.a.choice} /></span>
                  <span className="small"><strong>{name(b)}</strong>: <ChoiceMark choice={x.b.choice} /></span>
                </VoteLine>
              ))}
            </VoteList>
            {result.differences.length === 0 && <p className="muted">{t.d.common.noVotes}</p>}
            <nav className="search" aria-label={d.pages}>
              {cursor && <Link href={`/compare?${new URLSearchParams({ kind, a: String(a), b: String(b) })}`}>{d.latest}</Link>}
              {result.next_cursor && <Link href={`/compare?${new URLSearchParams({ kind, a: String(a), b: String(b), cursor: result.next_cursor })}`}>{t.d.common.earlier}</Link>}
            </nav>
          </section>
          <p className="small muted">
            {kind === "members"
              ? <>{options.filter((o) => o.id === a || o.id === b).map((o) => <span key={o.id}><Link href={`/members/${o.id}`}><PersonName p={o} he="title" /></Link> · </span>)}</>
              : <>{options.filter((o) => o.id === a || o.id === b).map((o) => <span key={o.id}><Link href={`/factions/${o.id}`}><FactionName f={o as Parameters<typeof t.faction>[0]} /></Link> · </span>)}</>}
          </p>
        </>
      )}
    </div>
  );
}
