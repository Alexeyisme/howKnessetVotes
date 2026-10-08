// Typed client for the hkv REST API (src/hkv/api/app.py). Server-side only.

import { connection } from "next/server";
import { getLocale } from "@/i18n/server";

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

export type Alignment = "coalition" | "opposition" | "external_support" | "unknown";
export interface BlocCounts { for: number; against: number; abstain: number }
/** cast votes by coalition / opposition members on the vote date; contested = the two majorities differed */
export interface Blocs { coalition: BlocCounts; opposition: BlocCounts; contested: boolean }

/** R4: machine or editor translation of a Hebrew title; `title` is in the ?lang= language (null when none) */
export interface Titled { title?: string | null; title_origin?: "machine" | "editor" | null; title_en?: string | null; title_ru?: string | null; title_ar?: string | null }

export interface VoteSummary extends Titled {
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
  bills: ({ id: number; title_he: string; sides?: DebateSides | null } & Titled)[];
  roll_call: Counts;
  blocs?: Blocs | null;
  source_url: string;
}

/** en/ru names of a member (official Knesset website, Wikidata or curated); null when unknown */
export interface PersonNames { name_he: string; name_ru?: string | null; name_en?: string | null; name_ar?: string | null }
/** name_* = full name, short_* = for tables and charts */
export interface FactionNames {
  name_he: string; name_ru?: string | null; short_ru?: string | null; name_en?: string | null; short_en?: string | null;
  name_ar?: string | null; short_ar?: string | null; short_he?: string | null;
}

export interface FactionBreakdown extends FactionNames {
  faction_id: number;
  counts: Counts;
  majority: Majority;
  ambiguous_records: number;
  alignment?: Alignment | null;
}

export interface VoteDetail extends VoteSummary {
  official_totals: { for: number; against: number; abstain: number; is_accepted: boolean | null; source: string } | null;
  totals_match: boolean | null;
  excluded_from_official_total: number;
  by_faction: FactionBreakdown[];
  unresolved_faction_records: number;
}

export interface Ballot extends PersonNames {
  person_id: number;
  faction_id: number | null;
  faction_name_he: string | null;
  faction_name_ru?: string | null;
  faction_short_ru?: string | null;
  faction_name_en?: string | null;
  faction_short_en?: string | null;
  faction_name_ar?: string | null;
  faction_short_ar?: string | null;
  faction_short_he?: string | null;
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
  // ?lang= fills the display fields (`title`, `name`, `label`) in the page's language; names are also computed here
  // from the per-language fields, titles are not (R4)
  const locale = await getLocale().catch(() => "he");
  const url = `${API_URL}${path}${path.includes("?") ? "&" : "?"}lang=${locale}`;
  // data changes a few times a day (scheduled update); a short cache keeps page views off the database
  const res = await fetch(url, { headers: { Accept: "application/json" }, next: { revalidate: 600 } });
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
export interface FactionRef extends FactionNames { id: number; term: number }
export interface Interval { valid_from: string; valid_to: string | null }

export interface MemberSummary extends PersonNames {
  id: number;
  gender: string | null;
  terms: number[];
  last_faction: FactionRef | null;
  roll_call_records: number;
  photo_url: string | null;
  photo_medium_url?: string | null;
  photo_thumb_url?: string | null;
}

export interface MemberDetail extends MemberSummary {
  mandates: (Interval & { term: number })[];
  factions: (Interval & { faction: FactionRef })[];
  stats: {
    participation: Rate;
    choices: Record<string, number>;
    deviation_from_faction: Rate;
    with_coalition: Rate;
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
  speeches?: number | null;  // final votes on a bill with a debate summary: this member's speeches in it (0: did not speak)
}

export interface PartyRef { slug: string; name_he: string; name_ru: string; name_en: string; name_ar?: string | null }

export interface FactionSummary extends FactionNames {
  id: number;
  term: number;
  valid: Interval;
  members_ever: number;
  roll_call_records: number;
  parties: PartyRef[];
  alignment_last: Alignment | null;
}

export interface FactionDetail extends FactionSummary {
  members: (Interval & PersonNames & { person_id: number; faction: FactionRef })[];
  stats: { votes_with_members: number; cohesion: Rate; unanimous_votes: Rate };
  alignment: (Interval & { government: number; role: Alignment; origin: "derived" | "curated"; evidence: string })[];
}

export interface PartySummary extends PartyRef { terms: number[]; factions: FactionSummary[] }
export interface Government { number: number; term: number | null; valid: Interval; prime_minister: (PersonNames & { id: number }) | null }

export interface FactionVote {
  vote: VoteSummary;
  faction_counts: { for: number; against: number; abstain: number; present_not_voting: number; total_records: number };
  majority: Majority;
}

export interface BillSummary extends Titled {
  id: number;
  title_he: string;
  term: number;
  origin: string | null;
  status_he: string | null;
  votes: number;
  last_vote_on: string | null;
  passed_third_reading: boolean;
  source_url: string;
  sides?: DebateSides | null;
}

export interface BillDetail extends BillSummary {
  topics: { slug: string; label_ru: string; label_he: string; label_en?: string | null; label_ar?: string | null; origin: string; review_state: string; evidence: string | null }[];
  summary_he: string | null;
  summary?: string | null;
  summary_origin?: "machine" | "editor" | null;
  explanation_he?: string | null;
  explanation?: string | null;
  explanation_origin?: "machine" | "editor" | null;
  explanation_source_url?: string | null;
  published_on: string | null;
  initiators: (PersonNames & { person_id: number; role: "initiator" | "joined" | "withdrew" })[];
  related: ({ id: number; title_he: string } & Titled)[];
  timeline: VoteSummary[];
  debate?: BillDebate | null;
  reservations?: BillReservations | null;
}

/** A machine-written Hebrew text of ours with its translation in the requested language (L7 steps 2–3). */
export interface ProseText { text_he: string; text?: string | null; text_origin?: "machine" | "editor" | null }

/** L7 cards: each side's argument made by the most speakers (both or neither), members who spoke, reservations filed. */
export interface DebateSides {
  argument_for: (ProseText & { speakers: number }) | null;
  argument_against: (ProseText & { speakers: number }) | null;
  speakers: number | null;
  reservations: number | null;
}

/** A member as a document prints them, resolved to a member and their faction where possible (faction_name: short
 *  name in the requested language). */
export interface PrintedMember extends PersonNames {
  person_id: number | null;
  faction_id: number | null;
  faction_name_he: string | null;
  faction_name?: string | null;
}

export interface DebateSpeaker extends PrintedMember {
  label_he: string;
  affiliation_he: string | null;
  alignment: Alignment | null;
  stages: Stage[];
  speeches: number;
  chars: number;
  final_choice: Choice | null;
  final_participation: string | null;
}

export interface BillDebate {
  final_vote_id: number;
  summary: ProseText;
  arguments: (ProseText & { side: "for" | "against"; speakers: number[] })[];
  speakers: DebateSpeaker[];
  agenda_titles: string[];
  truncated: boolean;
  sources: string[];
  model: string | null;
}

export interface BillReservations {
  total: number;
  numbers_checked: boolean;
  summary: ProseText | null;
  groups: { label_he: string; reservations: number; sections: string[]; gist: ProseText | null; members: PrintedMember[] }[];
  by_faction: (FactionNames & { faction_id: number; alignment: Alignment | null; reservations: number; members: number })[];
  unresolved_proposers: number;
  speak_requests: PrintedMember[];
  source_url: string;
  model: string | null;
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
export const listParties = () => get<PageOf<PartySummary>>(`/api/v1/parties`);
export const getParty = (slug: string) => get<{ data: PartySummary; meta: Meta }>(`/api/v1/parties/${encodeURIComponent(slug)}`);
export const listGovernments = () => get<PageOf<Government>>(`/api/v1/governments`);
export const listBills = (p: Params) => get<PageOf<BillSummary>>(`/api/v1/bills${qs(p)}`);
export const getBill = (id: number) => get<{ data: BillDetail; meta: Meta }>(`/api/v1/bills/${id}`);
export const getStatus = () => get<{ data: { published_at: string; coverage: { last_vote_on: string; votes: number; ballots: number } } | null }>(`/api/v1/status`);

export interface TopicSummary { slug: string; label_ru: string; label_he: string; label_en?: string | null; label_ar?: string | null; bills: number }
export interface TopicDetail extends TopicSummary {
  aliases_ru: string[];
  aliases_en: string[];
  aliases_ar: string[];
  term: number;
  stage: string[];
  factions: { faction: FactionRef; faction_ru: string | null; votes: number; majority_for: number; majority_against: number; other: number }[];
  recent_bills: BillSummary[];
}
export interface SearchResult {
  topics: TopicSummary[];
  bills: BillSummary[];
  bills_total?: number | null;
  members: (PersonNames & { id: number })[];
  factions: (FactionNames & { id: number; term: number })[];
  script: string;
}

/** U7: two members or two factions on their shared votes */
export interface Comparison {
  agreement: Rate;
  differences: { vote: VoteSummary; a: { choice: Choice }; b: { choice: Choice } }[];
  stage: string[];
  motion_type: string[];
}
export const compareMembers = (a: number, b: number) => get<{ data: Comparison; meta: Meta }>(`/api/v1/compare/members${qs({ a: String(a), b: String(b) })}`);
export const compareFactions = (a: number, b: number) => get<{ data: Comparison; meta: Meta }>(`/api/v1/compare/factions${qs({ a: String(a), b: String(b) })}`);

export const listTopics = () => get<{ data: TopicSummary[]; meta: Meta }>(`/api/v1/topics`);
export const getTopic = (slug: string, p: Params) => get<{ data: TopicDetail; meta: Meta }>(`/api/v1/topics/${encodeURIComponent(slug)}${qs(p)}`);
export const search = (q: string) => get<{ data: SearchResult; meta: Meta }>(`/api/v1/search${qs({ q })}`);
