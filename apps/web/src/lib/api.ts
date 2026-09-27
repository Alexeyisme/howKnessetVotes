// Typed client for the hkv REST API (src/hkv/api/app.py). Server-side only.

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
  counts: Counts;
  majority: Majority;
  ambiguous_records: number;
}

export interface VoteDetail extends VoteSummary {
  official_totals: { for: number; against: number; abstain: number; is_accepted: boolean | null; source: string } | null;
  totals_match: boolean | null;
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
  const res = await fetch(`${API_URL}${path}`, { headers: { Accept: "application/json" } });
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
