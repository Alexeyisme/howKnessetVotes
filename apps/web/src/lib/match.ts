import type { ReactNode } from "react";
import type { Majority } from "./api";

// R6 scoring, kept apart from the component so it can be tested (scripts/match.test.mjs).

export const MIN_COMPARABLE = 6;
export type Answer = "f" | "a" | "s";
export type Stand = Majority | "missing" | "ambiguous";
export interface MatchParty { id: number; name: string }
/** One side's most-made argument in the plenum debate (L7), as display strings; `he`: the text is the Hebrew original. */
export interface MatchSide { text: string; he: boolean; made: string }
export interface MatchVote {
  id: number; date: string; title_he: string; title: string | null; outcome: string; line: string; stands: Record<number, Stand>;
  about?: ReactNode;  // what the law does: start of the official summary or the sponsors' notes, rendered on the server
  sides: { for: MatchSide; against: MatchSide } | null;
}

export function parseAnswers(initial: string, length: number): Answer[] {
  return /^[fas]*$/.test(initial) && initial.length <= length ? initial.split("") as Answer[] : [];
}

export function scoreParties(votes: Pick<MatchVote, "stands">[], parties: MatchParty[], answers: Answer[]) {
  const scores = parties.map((p) => {
    const agreed: number[] = [], differed: number[] = [], excluded: number[] = [];
    votes.forEach((v, i) => {
      const mine = answers[i];
      if (!mine || mine === "s") return;
      const stand = v.stands[p.id];
      if (stand !== "for" && stand !== "against") { excluded.push(i); return; }
      ((mine === "f") === (stand === "for") ? agreed : differed).push(i);
    });
    const comparable = agreed.length + differed.length;
    return { ...p, agreed, differed, excluded, comparable, eligible: comparable >= MIN_COMPARABLE,
             share: comparable ? agreed.length / comparable : 0, rank: 0, tied: false };
  }).sort((a, b) => Number(b.eligible) - Number(a.eligible) || b.share - a.share || b.comparable - a.comparable || a.id - b.id);
  // Cross multiplication gives equal ranks even for different denominators (6/6 and 8/8).
  const equal = (a: typeof scores[number], b: typeof scores[number]) => a.agreed.length * b.comparable === b.agreed.length * a.comparable;
  scores.forEach((p, i) => {
    if (!p.eligible) return;
    p.rank = i > 0 && equal(p, scores[i - 1]) ? scores[i - 1].rank : i + 1;
    p.tied = (i > 0 && equal(p, scores[i - 1])) || (i + 1 < scores.length && scores[i + 1].eligible && equal(p, scores[i + 1]));
  });
  return scores;
}
