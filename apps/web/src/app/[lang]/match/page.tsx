import type { Metadata } from "next";
import { MatchQuiz, type MatchParty, type MatchSide, type MatchVote } from "@/components/MatchQuiz";
import { getVote, listVotes, type ProseText, type VoteSummary } from "@/lib/api";
import { verdict } from "@/lib/labels";
import { getT } from "@/i18n/server";
import Link from "@/components/Link";

const QUESTIONS = 12;
const PER_TOPIC = 2;
const TOPIC_GAP_DAYS = 30;

// The highest-turnout votes come in packages (a budget is four or five laws passed the same day or two, debated
// together), so taken as they are the quiz asks the same question several times with the same arguments. Going down
// the turnout order: one question per sitting day, at most PER_TOPIC per topic, and questions sharing a topic at
// least TOPIC_GAP_DAYS apart (a package can span two sittings).
function spread(byTurnout: VoteSummary[]): VoteSummary[] {
  const topics = (v: VoteSummary) => new Set(v.bills.flatMap((b) => b.topics));
  const days = (a: string, b: string) => Math.abs(Date.parse(a) - Date.parse(b)) / 86_400_000;
  const out: VoteSummary[] = [];
  for (const v of byTurnout) {
    if (out.length === QUESTIONS) break;
    const mine = topics(v);
    const shared = out.filter((o) => [...topics(o)].some((s) => mine.has(s)));
    if (out.some((o) => o.occurred_on === v.occurred_on)) continue;
    if ([...mine].some((s) => out.filter((o) => topics(o).has(s)).length >= PER_TOPIC)) continue;
    if (shared.some((o) => days(o.occurred_on, v.occurred_on) < TOPIC_GAP_DAYS)) continue;
    out.push(v);
  }
  return out;
}

// The latest Knesset's questions in date order; a new Knesset takes over only once it has a full set, otherwise its
// first months would give a quiz of one or two questions.
function latestFull(pool: VoteSummary[]): VoteSummary[] {
  const turnout = (v: VoteSummary) => v.roll_call.for + v.roll_call.against + v.roll_call.abstain;
  const sets = [...new Set(pool.map((v) => v.term))]
    .map((term) => spread(pool.filter((v) => v.term === term).sort((a, b) => turnout(b) - turnout(a))));
  const set = sets.find((s) => s.length === QUESTIONS) ?? sets[0] ?? [];
  return set.sort((a, b) => a.occurred_on.localeCompare(b.occurred_on));
}

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.match.title };
}

// R6 VoteMatch. No curation: the questions are the contested final votes of the latest Knesset with the most members
// voting, spread over sittings and topics (spread), so the selection rule is printed on the page and anyone can check it. A party's "answer" is the strict
// majority of its members on that vote (from the vote page's breakdown); abstentions and splits do not count.
export default async function MatchPage({ searchParams }: PageProps<"/[lang]/match">) {
  const t = await getT();
  const d = t.d.match;
  const sp = await searchParams;
  const pool = await listVotes({ stage: "third", motion_type: "adopt_bill", contested: "true", min_cast: "60", limit: "100" });
  const current = latestFull(pool.data);
  const term = current[0]?.term;
  // A shared result names its questions (?q=ids): the set changes with new votes, and the answers are by position.
  // Answers without ?q= are from before links carried it and cannot be matched to questions, so they are dropped.
  const shared = typeof sp.q === "string" && /^\d+(,\d+){0,11}$/.test(sp.q) && sp.q !== current.map((v) => v.id).join(",")
    ? await Promise.all(sp.q.split(",").map((id) => getVote(Number(id)).then((r) => r.data)))
        .then((vs) => vs.every((v) => v.motion_type === "adopt_bill" && v.stage === "third") ? vs : null).catch(() => null)
    : null;
  const details = shared ?? await Promise.all(current.map((v) => getVote(v.id).then((r) => r.data)));
  const parties = new Map<number, MatchParty>();
  const votes: MatchVote[] = details.map((v) => {
    const out = verdict(v, t);
    const stands: Record<number, "for" | "against"> = {};
    for (const f of v.by_faction) {
      if (f.majority !== "for" && f.majority !== "against") continue;
      stands[f.faction_id] = f.majority;
      if (!parties.has(f.faction_id)) parties.set(f.faction_id, { id: f.faction_id, name: t.faction(f), alignment: f.alignment ?? null });
    }
    const sides = v.bills.find((b) => b.sides?.argument_for && b.sides.argument_against)?.sides;
    const side = (a: ProseText & { speakers: number }): MatchSide => {
      const tr = t.locale !== "he" ? a.text : null;
      return { text: tr ?? a.text_he, he: !tr, made: t.d.sides.made(a.speakers) };
    };
    return { id: v.id, date: t.date(v.occurred_on), title_he: v.title_he, title: t.locale !== "he" ? v.title ?? null : null, outcome: out?.text ?? "", line: t.d.rc.line(v.roll_call.for, v.roll_call.against, v.roll_call.abstain), stands,
             sides: sides?.argument_for && sides.argument_against ? { for: side(sides.argument_for), against: side(sides.argument_against) } : null };
  });
  const answers = typeof sp.a === "string" && typeof sp.q === "string" && (shared || sp.q === current.map((v) => v.id).join(",")) ? sp.a : "";

  return (
    <div className="stack">
      <header className="page-head"><h1>{d.title}</h1></header>
      {votes.length === 0 ? <p className="muted">{t.d.common.noVotes}</p> : (
        <>
          {shared ? <p className="muted">{d.earlier} <Link href="/match">{d.current}</Link></p>
                  : <p className="muted">{d.lead(votes.length, term)}</p>}
          <MatchQuiz votes={votes} parties={[...parties.values()]} initial={answers} locale={t.locale}
                     labels={{ question: d.question, yes: d.yes, no: d.no, skip: d.skip, resultTitle: d.resultTitle,
                               progress: votes.map((_, i) => d.progress(i + 1, votes.length)),
                               agree: Array.from({ length: votes.length + 1 }, (_, m) => Array.from({ length: m + 1 }, (_, n) => d.agree(n, m))),
                               noAnswers: d.noAnswers, again: d.again, share: d.share, copied: d.copied, yours: d.yours, passed: d.passed,
                               alignment: t.d.alignment, choice: t.d.choice, sidesFor: t.d.sides.for, sidesAgainst: t.d.sides.against,
                               sidesNote: t.d.sides.note }} />
        </>
      )}
    </div>
  );
}
