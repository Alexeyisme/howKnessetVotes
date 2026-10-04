// Typed client for the hkv REST API (src/hkv/api/app.py). Server-side only.

import { connection } from "next/server";

const API_URL = process.env.HKV_API_URL ?? "http://127.0.0.1:8000";

export type Stage = "preliminary" | "first" | "second" | "third" | "not_applicable" | "unknown";
export type MotionType =
  | "adopt_bill" | "reject_bill" | "adopt_section" | "reservation" | "no_confidence"
  | "agenda" | "secondary_legislation" | "procedural" | "other" | "unknown";
export type Choice = "for" | "against" | "abstain";
export type Majority = Choice | "mixed" | "none";

export interface Counts {
  for: number;
  against: number;
  abstain: number;
  present_not_voting: number;
  other: number;
  total_records: number;
}

export interface VoteSummary {
  id: number;
  occurred_on: string;
  occurred_at: string | null;
  term: number;
  title_he: string;
  subject_he: string | null;
  question_he: string | null;
  motion_type: MotionType | null;
  stage: Stage | null;
  method: string;
  status: string;
  bills: { id: number; title_he: string }[];
  roll_call: Counts;
  source_url: string;
}

export interface FactionBreakdown {
  faction_id: number;
  name_he: string;
  name_ru: string | null;
  counts: Counts;
  majority: Majority;
  ambiguous_records: number;
}

export interface VoteDetail extends VoteSummary {
  official_totals: { for: number; against: number; abstain: number; is_accepted: boolean | null; source: string } | null;
  totals_match: boolean | null;
  excluded_from_official_total: number;
  by_faction: FactionBreakdown[];
  unresolved_faction_records: number;
}

export interface Ballot {
  person_id: number;
  name_he: string;
  faction_id: number | null;
  faction_name_he: string | null;
  faction_ambiguous: boolean;
  choice: Choice | null;
  participation: string;
  source_result_code: number;
  source: "knesset_odata_v4" | "knesset_votes_legacy";
  counted_in_official_total: boolean | null;
}

export interface Meta {
  date_basis: string;
  timezone: string;
  filters: Record<string, unknown>;
  note: string | null;
}

export class NotFound extends Error {}

async function get<T>(path: string): Promise<T> {
  await connection(); // render at request time, never at build time (the API is not reachable during the image build)
  // data changes a few times a day (scheduled update); a short cache keeps page views off the database
  const res = await fetch(`${API_URL}${path}`, { headers: { Accept: "application/json" }, next: { revalidate: 600 } });
  if (res.status === 404) throw new NotFound(path);
  if (!res.ok) throw new Error(`API ${res.status} for ${path}`);
  return (await res.json()) as T;
}

export const getVote = (id: number) => get<{ data: VoteDetail; meta: Meta }>(`/api/v1/votes/${id}`);
export const getBallots = (id: number) => get<{ data: Ballot[]; meta: Meta }>(`/api/v1/votes/${id}/ballots`);

export function listVotes(params: Record<string, string | string[] | undefined>) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    for (const item of Array.isArray(v) ? v : v ? [v] : []) qs.append(k, item);
  }
  return get<{ data: VoteSummary[]; meta: Meta; next_cursor: string | null }>(`/api/v1/votes?${qs}`);
}

// -- members, factions, bills -------------------------------------------------------------------

export interface Rate { numerator: number; denominator: number; value: number | null }
export interface FactionRef { id: number; name_he: string; term: number }
export interface Interval { valid_from: string; valid_to: string | null }

export interface MemberSummary {
  id: number;
  name_he: string;
  gender: string | null;
  terms: number[];
  last_faction: FactionRef | null;
  roll_call_records: number;
}

export interface MemberDetail extends MemberSummary {
  mandates: (Interval & { term: number })[];
  factions: (Interval & { faction: FactionRef })[];
  stats: {
    participation: Rate;
    choices: Record<string, number>;
    deviation_from_faction: Rate;
    bills_initiated: number;
    bills_joined: number;
  };
}

export interface MemberVote {
  vote: VoteSummary;
  choice: Choice | null;
  participation: string;
  faction: FactionRef | null;
  faction_majority: Majority;
  deviates: boolean | null;
}

export interface FactionSummary {
  id: number;
  name_he: string;
  name_ru: string | null;
  term: number;
  valid: Interval;
  members_ever: number;
  roll_call_records: number;
}

export interface FactionDetail extends FactionSummary {
  members: (Interval & { person_id: number; name_he: string; faction: FactionRef })[];
  stats: { votes_with_members: number; cohesion: Rate; unanimous_votes: Rate };
}

export interface FactionVote {
  vote: VoteSummary;
  faction_counts: { for: number; against: number; abstain: number; present_not_voting: number; total_records: number };
  majority: Majority;
}

export interface BillSummary {
  id: number;
  title_he: string;
  term: number;
  origin: string | null;
  status_he: string | null;
  votes: number;
  last_vote_on: string | null;
  passed_third_reading: boolean;
  source_url: string;
}

export interface BillDetail extends BillSummary {
  topics: { slug: string; label_ru: string; origin: string; review_state: string; evidence: string | null }[];
  summary_he: string | null;
  published_on: string | null;
  initiators: { person_id: number; name_he: string; role: "initiator" | "joined" | "withdrew" }[];
  related: { id: number; title_he: string }[];
  timeline: VoteSummary[];
}

export interface Term { number: number; name_he: string | null; started_on: string; ended_on: string | null }

type Params = Record<string, string | string[] | undefined>;
type PageOf<T> = { data: T[]; meta: Meta; next_cursor: string | null };

function qs(params: Params): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) for (const item of Array.isArray(v) ? v : v ? [v] : []) q.append(k, item);
  const s = q.toString();
  return s ? `?${s}` : "";
}

export const getTerms = () => get<PageOf<Term>>(`/api/v1/terms`);
export const listMembers = (p: Params) => get<PageOf<MemberSummary>>(`/api/v1/members${qs(p)}`);
export const getMember = (id: number) => get<{ data: MemberDetail; meta: Meta }>(`/api/v1/members/${id}`);
export const getMemberVotes = (id: number, p: Params) => get<PageOf<MemberVote>>(`/api/v1/members/${id}/votes${qs(p)}`);
export const listFactions = (p: Params) => get<PageOf<FactionSummary>>(`/api/v1/factions${qs(p)}`);
export const getFaction = (id: number) => get<{ data: FactionDetail; meta: Meta }>(`/api/v1/factions/${id}`);
export const getFactionVotes = (id: number, p: Params) => get<PageOf<FactionVote>>(`/api/v1/factions/${id}/votes${qs(p)}`);
export const listBills = (p: Params) => get<PageOf<BillSummary>>(`/api/v1/bills${qs(p)}`);
export const getBill = (id: number) => get<{ data: BillDetail; meta: Meta }>(`/api/v1/bills/${id}`);
export const getStatus = () => get<{ data: { published_at: string; coverage: { last_vote_on: string; votes: number; ballots: number } } | null }>(`/api/v1/status`);

export interface TopicSummary { slug: string; label_ru: string; label_he: string; bills: number }
export interface TopicDetail extends TopicSummary {
  aliases_ru: string[];
  term: number;
  stage: string[];
  factions: { faction: FactionRef; faction_ru: string | null; votes: number; majority_for: number; majority_against: number; other: number }[];
  recent_bills: BillSummary[];
}
export interface SearchResult {
  topics: TopicSummary[];
  bills: BillSummary[];
  members: { id: number; name_he: string }[];
  factions: { id: number; name_he: string; name_ru: string | null; term: number }[];
  script: string;
}

export const listTopics = () => get<{ data: TopicSummary[]; meta: Meta }>(`/api/v1/topics`);
export const getTopic = (slug: string, p: Params) => get<{ data: TopicDetail; meta: Meta }>(`/api/v1/topics/${encodeURIComponent(slug)}${qs(p)}`);
export const search = (q: string) => get<{ data: SearchResult; meta: Meta }>(`/api/v1/search${qs({ q })}`);
