// The Speaker's election as the site shows it: when it was several votes on one day, those votes side by side, each
// with the MK its subject puts forward (lib/voteKinds.ts says why such a vote gets no verdict of its own).

import { getBallots, listVotes, type Ballot, type VoteSummary } from "./api";
import { candidateIn, sameElection, voteKind } from "./voteKinds";

export interface RoundVote { vote: VoteSummary; candidate: Ballot | null }

/** The votes of the Speaker's election this vote belongs to, or null when it is not one or was the only vote. */
export async function speakerRound(vote: VoteSummary): Promise<RoundVote[] | null> {
  if (vote.bills.length > 0 || voteKind(vote) !== "speaker") return null;
  const day = await listVotes({ q: vote.title_he, date_from: vote.occurred_on, date_to: vote.occurred_on, limit: "50" });
  const round = sameElection(vote, day.data);
  if (round.length < 2) return null;
  // a candidate is an MK, and this vote's roll call lists the MKs with their names in every language
  const people = round.some((v) => v.subject_he) ? (await getBallots(vote.id)).data : [];
  return round.map((v) => ({ vote: v, candidate: candidateIn(v.subject_he, people) }));
}
