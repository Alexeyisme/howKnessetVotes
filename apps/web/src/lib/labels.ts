// Language-independent display logic; the words are in src/i18n/dict.

import type { MotionType, Stage, VoteSummary } from "./api";
import type { T } from "@/i18n/server";

/** In RTL text an en dash / maqaf between digits is bidi-neutral and flips the range ("15–16" shows as "16–15");
 *  a hyphen-minus between digits is a European separator and keeps the order. */
export function bidiSafe(s: string): string {
  return s.replace(/(\d)\s*[–—־]\s*(\d)/g, "$1-$2");
}

/** Lower case, and Arabic without harakat, tatweel or the hamza / ta marbuta / alef maqsura distinctions (same rules
 *  as the API's ar_norm), so "احمد" finds "أحمد". For client-side name filters. */
export function fold(s: string): string {
  return s.toLowerCase().replace(/[\u064B-\u065F\u0670\u0640]/g, "").replace(/[أإآٱ]/g, "ا").replace(/ة/g, "ه")
    .replace(/ى/g, "ي").replace(/ؤ/g, "و").replace(/ئ/g, "ي");
}

// Only votes on a bill as a whole and no-confidence motions: what most readers mean by "how did they vote".
export const MAIN_MOTIONS: MotionType[] = ["adopt_bill", "no_confidence"];
// a record so that a new motion type fails the build until it is listed here
const MOTIONS: Record<MotionType, true> = { adopt_bill: true, reject_bill: true, adopt_section: true, reservation: true, no_confidence: true,
  agenda: true, secondary_legislation: true, procedural: true, other: true, unknown: true };
export const ALL_MOTIONS = Object.keys(MOTIONS) as MotionType[];

// Methods that never produce a roll-call list; for any other method zero records means "not loaded (yet)".
const NO_ROLL_CALL = new Set(["show_of_hands", "show_of_hands_counted", "secret"]);

export function missingRollCallText(method: string, t: T): string {
  return NO_ROLL_CALL.has(method) ? t.d.rc.noList(t.d.method[method] ?? method) : t.d.rc.notLoaded;
}

// Below this many votes cast the vote page explains that the plenum has no quorum (a common "how can 11 votes pass
// a law?"), and the card's bar already reads as a low turnout.
export const FEW_VOTES = 40;

/** Whole factions cast no vote in a vote that otherwise reads as agreement ("44 for, 0 against" with 5 of 11
 *  factions voting): how many voted of how many there were. Null for a low-turnout vote, where it is the rule. */
export function partialTurnout(v: Pick<VoteSummary, "roll_call" | "faction_sides">): { voted: number; total: number } | null {
  const fs = v.faction_sides, rc = v.roll_call;
  if (fs?.voted == null || fs.total == null || fs.voted >= fs.total) return null;
  return rc.for + rc.against + rc.abstain >= FEW_VOTES ? { voted: fs.voted, total: fs.total } : null;
}

type VerdictInput = Pick<VoteSummary, "motion_type" | "stage" | "roll_call"> & { official_totals?: { is_accepted: boolean | null } | null };

/** One-line outcome in plain words. Official result when published (votes up to 2021-07), otherwise derived from the
 *  roll call: simple majority of for over against (a tie is not adopted); no-confidence needs 61 votes for. */
export function verdict(v: VerdictInput, t: T): { text: string; accepted: boolean; derived: boolean } | null {
  const rc = v.roll_call;
  let accepted: boolean | null = v.official_totals?.is_accepted ?? null;
  const derived = accepted == null;
  if (accepted == null) {
    if (rc.total_records === 0 || rc.for + rc.against === 0) return null;
    accepted = v.motion_type === "no_confidence" ? rc.for >= 61 : rc.for > rc.against;
  }
  return { text: t.d.verdict(v.motion_type, v.stage as Stage | null, accepted), accepted, derived };
}
