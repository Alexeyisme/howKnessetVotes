import type { Metadata } from "next";
import { MatchQuiz, type MatchParty, type MatchVote } from "@/components/MatchQuiz";
import { getVote, listVotes } from "@/lib/api";
import { verdict } from "@/lib/labels";
import { getT } from "@/i18n/server";

const QUESTIONS = 12;

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.match.title };
}

// R6 VoteMatch. No curation: the questions are the contested final votes of the latest Knesset with the most members
// voting, so the selection rule is printed on the page and anyone can check it. A party's "answer" is the strict
// majority of its members on that vote (from the vote page's breakdown); abstentions and splits do not count.
export default async function MatchPage({ searchParams }: PageProps<"/[lang]/match">) {
  const t = await getT();
  const d = t.d.match;
  const sp = await searchParams;
  const pool = await listVotes({ stage: "third", motion_type: "adopt_bill", contested: "true", min_cast: "60", limit: "100" });
  const term = pool.data[0]?.term;
  const chosen = pool.data.filter((v) => v.term === term)
    .sort((a, b) => (b.roll_call.for + b.roll_call.against + b.roll_call.abstain) - (a.roll_call.for + a.roll_call.against + a.roll_call.abstain))
    .slice(0, QUESTIONS)
    .sort((a, b) => a.occurred_on.localeCompare(b.occurred_on));
  const details = await Promise.all(chosen.map((v) => getVote(v.id).then((r) => r.data)));
  const parties = new Map<number, MatchParty>();
  const votes: MatchVote[] = details.map((v) => {
    const out = verdict(v, t);
    const stands: Record<number, "for" | "against"> = {};
    for (const f of v.by_faction) {
      if (f.majority !== "for" && f.majority !== "against") continue;
      stands[f.faction_id] = f.majority;
      if (!parties.has(f.faction_id)) parties.set(f.faction_id, { id: f.faction_id, name: t.faction(f), alignment: f.alignment ?? null });
    }
    return { id: v.id, date: t.date(v.occurred_on), title_he: v.title_he, title: t.locale !== "he" ? v.title ?? null : null, outcome: out?.text ?? "", line: t.d.rc.line(v.roll_call.for, v.roll_call.against, v.roll_call.abstain), stands };
  });
  const answers = typeof sp.a === "string" ? sp.a : "";

  return (
    <div className="stack">
      <header className="page-head"><h1>{d.title}</h1></header>
      {votes.length === 0 ? <p className="muted">{t.d.common.noVotes}</p> : (
        <>
          <p className="muted">{d.lead(votes.length, term)}</p>
          <MatchQuiz votes={votes} parties={[...parties.values()]} initial={answers} locale={t.locale}
                     labels={{ question: d.question, yes: d.yes, no: d.no, skip: d.skip, resultTitle: d.resultTitle,
                               progress: votes.map((_, i) => d.progress(i + 1, votes.length)),
                               agree: Array.from({ length: votes.length + 1 }, (_, m) => Array.from({ length: m + 1 }, (_, n) => d.agree(n, m))),
                               noAnswers: d.noAnswers, again: d.again, share: d.share, copied: d.copied, yours: d.yours, passed: d.passed,
                               alignment: t.d.alignment, choice: t.d.choice }} />
        </>
      )}
    </div>
  );
}
