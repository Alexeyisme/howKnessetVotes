// Kinds of votes that are not on a bill, recognised by the Hebrew title, the question or the motion type, so the vote
// page can say what such a vote decides (texts: i18n/content/voteKinds.tsx). Every kind rests on the law or the Rules
// of Procedure it links to; a vote that matches no pattern gets no explanation rather than a guess. Order matters: the
// first match wins (the Speaker's election is often "the Arrangements Committee's proposal").

export type VoteKind = "speaker" | "deputies" | "arrangements" | "arrangementsProposal" | "continuity" | "government"
  | "agendaSummary" | "agenda";

type Vote = { title_he: string; question_he?: string | null; motion_type?: string | null };

const KINDS: [VoteKind, (title: string, question: string, motion: string) => boolean][] = [
  ["speaker", (t) => /בחירת (יושב|יושבת)[\s-]ראש הכנסת|בחירת יו"ר הכנסת/.test(t)],
  ["deputies", (t) => /סגנים (זמניים )?ל(יושב|יושבת)[\s-]ראש הכנסת/.test(t)],
  ["arrangements", (t, q) => /(בחירת|הרכב) ה?וו?עדה המסדרת/.test(`${t} ${q}`)],
  ["arrangementsProposal", (t, q) => /ה?וו?עדה המסדרת/.test(`${t} ${q}`)],
  ["continuity", (t, q) => /רציפות/.test(`${t} ${q}`)],
  ["government", (t) => /הממשלה/.test(t)
    && /צירוף (שר|שרים)|חלוקת (ה)?תפקידים|העברת (סמכות|סמכויות|שטח|שטחי)|שטחי פעולה|(הקמת|ביטול|איחוד|פיצול) משרד|31 ?\([אבג]\)/.test(t)],
  ["agendaSummary", (_t, q, m) => m === "agenda" && /סיכום הדיון/.test(q)],
  ["agenda", (_t, _q, m) => m === "agenda"],
];

export function voteKind(v: Vote): VoteKind | null {
  const t = v.title_he, q = v.question_he ?? "", m = v.motion_type ?? "";
  return KINDS.find(([, match]) => match(t, q, m))?.[0] ?? null;
}

const WIKISOURCE = "https://he.wikisource.org/wiki/";
const RULES = "https://m.knesset.gov.il/Activity/Documents/RulesOfProcedure.pdf";

/** The source each explanation rests on: the law's section on Wikisource (it has an anchor per section), or the
 *  Knesset's own Rules of Procedure. */
export const KIND_SOURCE: Record<VoteKind, string> = {
  speaker: `${WIKISOURCE}חוק-יסוד:_הכנסת#סעיף_20`,
  deputies: `${WIKISOURCE}חוק-יסוד:_הכנסת#סעיף_20`,
  arrangements: `${WIKISOURCE}חוק_הכנסת#סעיף_2א`,
  arrangementsProposal: `${WIKISOURCE}חוק_הכנסת#סעיף_2א`,
  continuity: `${WIKISOURCE}חוק_רציפות_הדיון_בהצעות_חוק`,
  government: `${WIKISOURCE}חוק-יסוד:_הממשלה#סעיף_31`,
  agendaSummary: RULES,
  agenda: RULES,
};

// A Speaker's election is often several votes on one day under one title (2009, 2013, 2020, 2021, 2022, 2026), and
// each has only votes "for": 52 for, 0 against is not "adopted" when another vote that day got 66. The source does not
// say which vote elected the Speaker, so such a vote gets no verdict and the page lists the day's votes side by side.

/** The votes of one election: the same Hebrew title on the same day, most votes "for" first. */
export function sameElection<V extends { id: number; title_he: string; occurred_on: string; roll_call: { for: number } }>(vote: V, sameDay: V[]): V[] {
  return sameDay.filter((v) => v.title_he === vote.title_he && v.occurred_on === vote.occurred_on)
    .sort((a, b) => b.roll_call.for - a.roll_call.for || a.id - b.id);
}

const flat = (s: string) => s.replace(/[-־]/g, " ").replace(/\s+/g, " ").trim();

/** The MK a vote's subject puts forward ("מועמדותו של חבר הכנסת אופיר כץ", "ההצעה לבחור את חבר הכנסת מתן כהנא"), found
 *  by full Hebrew name. Null unless the subject speaks of a candidacy and names exactly one of `people`: a subject
 *  may also name the MK who made the proposal. */
export function candidateIn<P extends { name_he: string }>(subject: string | null | undefined, people: P[]): P | null {
  if (!subject || !/מועמדות|לבחור את/.test(subject)) return null;
  const s = flat(subject);
  const named = people.filter((p) => flat(p.name_he).length > 3 && s.includes(flat(p.name_he)));
  // "דוד ביטן" inside "דוד ביטן כהן" is one person, the longer name
  const own = named.filter((p) => !named.some((q) => q !== p && flat(q.name_he) !== flat(p.name_he) && flat(q.name_he).includes(flat(p.name_he))));
  return new Set(own.map((p) => flat(p.name_he))).size === 1 ? own[0] : null;
}
