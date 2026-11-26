// What was put to the vote, in the site's languages. The Knesset words the question (the "for" option; in the legacy
// source, the item) from a closed list: 53 wordings in 37,000 votes, so they are written here by hand instead of
// going through machine translation. The subject is the same wordings again (legacy source) or a numbered part of a
// bill ("הסתייגות 12", "סעיפים 1–13"), read by pattern. Anything else (a candidate's name, a free-text subject) gets
// no text here and stays in Hebrew. The terms are the site's own: оговорка / reservation, статья / section,
// комиссия Кнессета / House Committee, Организационная комиссия / Arrangements Committee.

import type { Locale } from "../config";

type Lang = Exclude<Locale, "he">;
type Text = Record<Lang, string>;

const COMMITTEE2: Text = {
  ru: "Передать законопроект в комиссию для подготовки ко второму и третьему чтениям",
  en: "To refer the bill to a committee to be prepared for the second and third readings",
  ar: "إحالة اقتراح القانون إلى اللجنة لإعداده للقراءتين الثانية والثالثة",
};
const AGENDA: Text = { ru: "Включить тему в повестку дня Кнессета", en: "To include the matter on the Knesset's agenda", ar: "إدراج الموضوع في جدول أعمال الكنيست" };
const AGENDA_PLENUM: Text = { ru: "Включить тему в повестку дня пленума", en: "To include the matter on the plenum's agenda", ar: "إدراج الموضوع في جدول أعمال الهيئة العامة" };
const NOT_AGENDA: Text = { ru: "Не включать тему в повестку дня Кнессета", en: "Not to include the matter on the Knesset's agenda", ar: "عدم إدراج الموضوع في جدول أعمال الكنيست" };
const NOT_AGENDA_PLENUM: Text = { ru: "Не включать тему в повестку дня пленума", en: "Not to include the matter on the plenum's agenda", ar: "عدم إدراج الموضوع في جدول أعمال الهيئة العامة" };
const REMOVE_BILL: Text = { ru: "Снять законопроект с повестки дня", en: "To remove the bill from the agenda", ar: "شطب اقتراح القانون عن جدول الأعمال" };
const SUMMARY: Text = { ru: "Предложение итогового решения", en: "A proposed resolution summing up the debate", ar: "اقتراح قرار لتلخيص النقاش" };
const ARRANGEMENTS: Text = { ru: "Предложение Организационной комиссии", en: "A proposal of the Arrangements Committee", ar: "اقتراح اللجنة المنظمة" };
const COMMITTEE_NOTICE: Text = { ru: "Сообщение комиссии", en: "A committee's notice", ar: "بيان لجنة" };

const PHRASES: Record<string, Text> = {
  // bills
  "להעביר את הצעת החוק לוועדה להכנה לקריאה ראשונה": {
    ru: "Передать законопроект в комиссию для подготовки к первому чтению",
    en: "To refer the bill to a committee to be prepared for the first reading",
    ar: "إحالة اقتراح القانون إلى اللجنة لإعداده للقراءة الأولى",
  },
  "להעביר את הצעת החוק לוועדה להכנה לקריאה שניה ושלישית": COMMITTEE2,
  "להעביר את הצעת החוק לוועדה": { ru: "Передать законопроект в комиссию", en: "To refer the bill to a committee", ar: "إحالة اقتراح القانون إلى اللجنة" },
  "להעביר את הצעת החוק לוועדה שתקבע ועדת הכנסת": {
    ru: "Передать законопроект в комиссию, которую определит комиссия Кнессета",
    en: "To refer the bill to a committee chosen by the House Committee",
    ar: "إحالة اقتراح القانون إلى اللجنة التي تحددها لجنة الكنيست",
  },
  "להעביר את הצעת החוק לוועדה שתקבע ועדת הכנסת להכנה לקריאה ראשונה": {
    ru: "Передать законопроект в комиссию, которую определит комиссия Кнессета, для подготовки к первому чтению",
    en: "To refer the bill to a committee chosen by the House Committee, to be prepared for the first reading",
    ar: "إحالة اقتراح القانون إلى اللجنة التي تحددها لجنة الكنيست لإعداده للقراءة الأولى",
  },
  "להעביר את הצעת החוק לוועדה שתקבע ועדת הכנסת להכנה לקריאה שניה ושלישית": {
    ru: "Передать законопроект в комиссию, которую определит комиссия Кнессета, для подготовки ко второму и третьему чтениям",
    en: "To refer the bill to a committee chosen by the House Committee, to be prepared for the second and third readings",
    ar: "إحالة اقتراح القانون إلى اللجنة التي تحددها لجنة الكنيست لإعداده للقراءتين الثانية والثالثة",
  },
  "להעביר את הצעת החוק לוועדה שתקבע הוועדה המסדרת להכנה לקריאה ראשונה": {
    ru: "Передать законопроект в комиссию, которую определит Организационная комиссия, для подготовки к первому чтению",
    en: "To refer the bill to a committee chosen by the Arrangements Committee, to be prepared for the first reading",
    ar: "إحالة اقتراح القانون إلى اللجنة التي تحددها اللجنة المنظمة لإعداده للقراءة الأولى",
  },
  "להעביר את הצעת החוק לוועדה שתקבע הוועדה המסדרת להכנה לקריאה שניה ושלישית": {
    ru: "Передать законопроект в комиссию, которую определит Организационная комиссия, для подготовки ко второму и третьему чтениям",
    en: "To refer the bill to a committee chosen by the Arrangements Committee, to be prepared for the second and third readings",
    ar: "إحالة اقتراح القانون إلى اللجنة التي تحددها اللجنة المنظمة لإعداده للقراءتين الثانية والثالثة",
  },
  "לקבל בקריאה שנייה": { ru: "Принять во втором чтении", en: "To adopt on second reading", ar: "الإقرار بالقراءة الثانية" },
  "קריאה שנייה": { ru: "Второе чтение", en: "Second reading", ar: "القراءة الثانية" },
  "לקבל את הצעת החוק בקריאה שלישית": { ru: "Принять законопроект в третьем чтении", en: "To adopt the bill on third reading", ar: "إقرار اقتراح القانون بالقراءة الثالثة" },
  "אישור החוק": { ru: "Утверждение закона", en: "Approval of the law", ar: "إقرار القانون" },
  "שם החוק": { ru: "Название закона", en: "The name of the law", ar: "اسم القانون" },
  "לקבל את ההסתייגות": { ru: "Принять оговорку", en: "To accept the reservation", ar: "قبول التحفّظ" },
  "הסתייגות": { ru: "Оговорка", en: "Reservation", ar: "تحفّظ" },
  "להסיר את הצעת החוק מסדר-היום": REMOVE_BILL,
  "להסיר מסדר-היום את הצעת החוק": REMOVE_BILL,
  "להסיר מסדר-היום": { ru: "Снять с повестки дня", en: "To remove from the agenda", ar: "الشطب عن جدول الأعمال" },
  "להחזיר את הצעת החוק לוועדה": { ru: "Вернуть законопроект в комиссию", en: "To return the bill to the committee", ar: "إعادة اقتراح القانون إلى اللجنة" },
  "להחזיר את הצעת החוק לדיון בוועדה": {
    ru: "Вернуть законопроект на обсуждение в комиссию", en: "To return the bill to the committee for debate", ar: "إعادة اقتراح القانون إلى اللجنة لبحثه",
  },
  "להשהות את ההצבעה על הצעת החוק": { ru: "Приостановить голосование по законопроекту", en: "To suspend the vote on the bill", ar: "تعليق التصويت على اقتراح القانون" },
  "לדחות את ההצבעה למועד אחר": { ru: "Перенести голосование на другой срок", en: "To postpone the vote to another date", ar: "تأجيل التصويت إلى موعد آخر" },
  "להפוך את הצעת החוק להצעה לסדר-היום ולהעביר לוועדה": {
    ru: "Преобразовать законопроект в предложение на повестку дня и передать в комиссию",
    en: "To turn the bill into a motion for the agenda and refer it to a committee",
    ar: "تحويل اقتراح القانون إلى اقتراح لجدول الأعمال وإحالته إلى اللجنة",
  },
  "לקבל את המלצת ועדת הכנסת להעביר את הצעת החוק מוועדה לוועדה": {
    ru: "Принять рекомендацию комиссии Кнессета о передаче законопроекта из одной комиссии в другую",
    en: "To accept the House Committee's recommendation to move the bill from one committee to another",
    ar: "قبول توصية لجنة الكنيست بنقل اقتراح القانون من لجنة إلى أخرى",
  },
  "לאשר תיקון טעות בחוק שהתקבל": {
    ru: "Утвердить исправление ошибки в принятом законе", en: "To approve the correction of an error in an adopted law", ar: "الموافقة على تصحيح خطأ في قانون أُقرّ",
  },
  "החלטה בדבר תיקון טעות בחוק": { ru: "Решение об исправлении ошибки в законе", en: "Decision to correct an error in a law", ar: "قرار بتصحيح خطأ في قانون" },
  "לאשר את חקיקת המשנה": { ru: "Утвердить подзаконный акт", en: "To approve the secondary legislation", ar: "الموافقة على التشريع الثانوي" },
  // continuity
  "להחיל דין רציפות על הצעת החוק": { ru: "Применить к законопроекту преемственность", en: "To apply continuity to the bill", ar: "تطبيق الاستمرارية على اقتراح القانون" },
  "להחיל דין רציפות": { ru: "Применить преемственность", en: "To apply continuity", ar: "تطبيق الاستمرارية" },
  "לא להחיל דין רציפות על הצעת החוק": { ru: "Не применять к законопроекту преемственность", en: "Not to apply continuity to the bill", ar: "عدم تطبيق الاستمرارية على اقتراح القانون" },
  "התנגדות להחיל דין רציפות": { ru: "Возражение против применения преемственности", en: "Objection to applying continuity", ar: "اعتراض على تطبيق الاستمرارية" },
  // no confidence
  "להביע אי-אמון בממשלה": { ru: "Выразить недоверие правительству", en: "To express no confidence in the government", ar: "حجب الثقة عن الحكومة" },
  "הצעת אי-אמון בממשלה": { ru: "Вотум недоверия правительству", en: "No-confidence motion", ar: "اقتراح حجب الثقة عن الحكومة" },
  // the agenda
  "לכלול את הנושא בסדר-היום של הכנסת": AGENDA,
  "לכלול את הנושא בסדר היום של המליאה": AGENDA_PLENUM,
  "לא לכלול את הנושא בסדר-היום של הכנסת": NOT_AGENDA,
  "לא לכלול את הנושא בסדר היום של המליאה": NOT_AGENDA_PLENUM,
  "להעביר את הנושא לדיון בוועדה": { ru: "Передать тему на обсуждение в комиссию", en: "To refer the matter to a committee for debate", ar: "إحالة الموضوع إلى اللجنة لبحثه" },
  "להעביר את הנושא לוועדה": { ru: "Передать тему в комиссию", en: "To refer the matter to a committee", ar: "إحالة الموضوع إلى اللجنة" },
  "להעביר את הנושא לדיון בוועדה שתקבע ועדת הכנסת": {
    ru: "Передать тему на обсуждение в комиссию, которую определит комиссия Кнессета",
    en: "To refer the matter for debate to a committee chosen by the House Committee",
    ar: "إحالة الموضوع لبحثه في اللجنة التي تحددها لجنة الكنيست",
  },
  "העברת הנושא לוועדה שתקבע ועדת הכנסת": {
    ru: "Передача темы в комиссию, которую определит комиссия Кнессета",
    en: "Referring the matter to a committee chosen by the House Committee",
    ar: "إحالة الموضوع إلى اللجنة التي تحددها لجنة الكنيست",
  },
  "לקבל את הצעת סיכום הדיון": { ru: "Принять предложение итогового решения", en: "To adopt the proposed resolution summing up the debate", ar: "قبول اقتراح القرار لتلخيص النقاش" },
  "הצעת סיכום": SUMMARY,
  "הצעת הסיכום": SUMMARY,
  "לקבל את המלצת ועדת הכנסת להעביר את ההצעה לסדר היום מוועדה לוועדה": {
    ru: "Принять рекомендацию комиссии Кнессета о передаче предложения на повестку дня из одной комиссии в другую",
    en: "To accept the House Committee's recommendation to move the motion for the agenda from one committee to another",
    ar: "قبول توصية لجنة الكنيست بنقل الاقتراح لجدول الأعمال من لجنة إلى أخرى",
  },
  // proposals, notices and decisions
  "לאשר את ההצעה": { ru: "Утвердить предложение", en: "To approve the proposal", ar: "الموافقة على الاقتراح" },
  "הצבעה": { ru: "Голосование", en: "Vote", ar: "تصويت" },
  "לקבל את ההחלטה בדבר": { ru: "Принять решение", en: "To adopt the decision", ar: "قبول القرار" },
  "החלטה בדבר": { ru: "Решение", en: "Decision", ar: "قرار" },
  "הצעת ועדה": { ru: "Предложение комиссии", en: "A committee's proposal", ar: "اقتراح لجنة" },
  "לקבל את הצעת ועדת": { ru: "Принять предложение комиссии", en: "To accept the committee's proposal", ar: "قبول اقتراح اللجنة" },
  "הצעת ועדת הכנסת": { ru: "Предложение комиссии Кнессета", en: "A proposal of the House Committee", ar: "اقتراح لجنة الكنيست" },
  "לקבל את הצעת ועדת הכנסת": { ru: "Принять предложение комиссии Кнессета", en: "To accept the House Committee's proposal", ar: "قبول اقتراح لجنة الكنيست" },
  "הצעת הוועדה המסדרת": ARRANGEMENTS,
  "לקבל את הצעת הוועדה המסדרת": { ru: "Принять предложение Организационной комиссии", en: "To accept the Arrangements Committee's proposal", ar: "قبول اقتراح اللجنة المنظمة" },
  "הצעה בדבר הרכב הוועדה המסדרת": {
    ru: "Предложение о составе Организационной комиссии", en: "A proposal on the make-up of the Arrangements Committee", ar: "اقتراح بشأن تركيبة اللجنة المنظمة",
  },
  "לקבל את ההצעה בדבר הרכב הוועדה המסדרת": {
    ru: "Принять предложение о составе Организационной комиссии", en: "To accept the proposal on the make-up of the Arrangements Committee",
    ar: "قبول الاقتراح بشأن تركيبة اللجنة المنظمة",
  },
  "הצעת סיעה": { ru: "Предложение фракции", en: "A faction's proposal", ar: "اقتراح كتلة" },
  "לקבל את הצעת חבר הכנסת": { ru: "Принять предложение депутата Кнессета", en: "To accept the MK's proposal", ar: "قبول اقتراح عضو الكنيست" },
  "הודעת הממשלה": { ru: "Сообщение правительства", en: "The government's notice", ar: "بيان الحكومة" },
  "לקבל את הודעת הממשלה": { ru: "Принять сообщение правительства", en: "To accept the government's notice", ar: "قبول بيان الحكومة" },
  "הודעת ראש הממשלה": { ru: "Сообщение премьер-министра", en: "The Prime Minister's notice", ar: "بيان رئيس الحكومة" },
  "לקבל את הודעת ראש הממשלה": { ru: "Принять сообщение премьер-министра", en: "To accept the Prime Minister's notice", ar: "قبول بيان رئيس الحكومة" },
  "הודעת יושב-ראש ועדת הכנסת": { ru: "Сообщение председателя комиссии Кнессета", en: "Notice by the chair of the House Committee", ar: "بيان رئيس لجنة الكنيست" },
  "הודעת ועדת הכנסת": { ru: "Сообщение комиссии Кнессета", en: "The House Committee's notice", ar: "بيان لجنة الكنيست" },
  "הודעת וועדה": COMMITTEE_NOTICE,
};

/** A closed-list wording in the UI language; null in the Hebrew UI and for a wording that is not on the list. */
export function phrase(he: string | null | undefined, locale: Locale): string | null {
  if (!he || locale === "he") return null;
  return PHRASES[he.trim()]?.[locale] ?? null;
}

const N = "(\\d+(?:,\\d{3})*)";    // the source writes reservation 12267 as "12,267"
const RANGE = `${N}\\s*[–־-]\\s*${N}`;
const AS_COMMITTEE: Text = { ru: " в редакции комиссии", en: " as proposed by the committee", ar: " كما اقترحته اللجنة" };
const BUDGET: Record<string, Text> = {
  "הפחתת": { ru: "сокращение бюджета", en: "a budget cut", ar: "تقليص الميزانية" },
  "תוספת": { ru: "увеличение бюджета", en: "a budget increase", ar: "زيادة الميزانية" },
};

// Numbered parts of a bill. Each pattern is the whole subject; one that only resembles a pattern stays in Hebrew.
const PATTERNS: [RegExp, (m: RegExpMatchArray, l: Lang) => string][] = [
  [new RegExp(`^ה?הסתייגות (?:מס' )?${N}$`),
    (m, l) => ({ ru: `Оговорка № ${m[1]}`, en: `Reservation no. ${m[1]}`, ar: `التحفّظ رقم ${m[1]}` })[l]],
  [new RegExp(`^ה?הסתייגות ${N} לסעיף ${N}$`),
    (m, l) => ({ ru: `Оговорка № ${m[1]} к статье ${m[2]}`, en: `Reservation no. ${m[1]} to section ${m[2]}`, ar: `التحفّظ رقم ${m[1]} على البند ${m[2]}` })[l]],
  [new RegExp(`^ה?הסתייגות על סעיף ${N}$`),
    (m, l) => ({ ru: `Оговорка к статье ${m[1]}`, en: `The reservation to section ${m[1]}`, ar: `التحفّظ على البند ${m[1]}` })[l]],
  [new RegExp(`^ה?הסתייגויות לסעיף ${N}(?: לשנת התקציב ${N})?,? בדבר (הפחתת|תוספת) תקציב$`),
    (m, l) => {
      const what = BUDGET[m[3]][l];
      return {
        ru: `Оговорки к статье ${m[1]}${m[2] ? ` на бюджетный год ${m[2]}` : ""}: ${what}`,
        en: `The reservations to section ${m[1]}${m[2] ? ` for budget year ${m[2]}` : ""}: ${what}`,
        ar: `التحفّظات على البند ${m[1]}${m[2] ? ` لسنة الميزانية ${m[2]}` : ""}: ${what}`,
      }[l];
    }],
  [new RegExp(`^סעיף ${N}(,? כהצעת הוועדה)?$`),
    (m, l) => ({ ru: `Статья ${m[1]}`, en: `Section ${m[1]}`, ar: `البند ${m[1]}` })[l] + (m[2] ? AS_COMMITTEE[l] : "")],
  [new RegExp(`^סעיפים ${RANGE}(,? כהצעת הוועדה)?$`),
    (m, l) => ({ ru: `Статьи ${m[1]}–${m[2]}`, en: `Sections ${m[1]}–${m[2]}`, ar: `البنود ${m[1]}–${m[2]}` })[l] + (m[3] ? AS_COMMITTEE[l] : "")],
];

/** A vote's subject in the UI language: a numbered part of a bill by pattern, or a closed-list wording. */
export function subjectText(he: string | null | undefined, locale: Locale): string | null {
  if (!he || locale === "he") return null;
  const s = he.trim();
  for (const [re, render] of PATTERNS) {
    const m = s.match(re);
    if (m) return render(m, locale);
  }
  return phrase(s, locale);
}

/** True when the subject names a part of the bill (a reservation, a section): what tells apart the votes on one bill. */
export function isNumberedSubject(he: string | null | undefined): boolean {
  return !!he && PATTERNS.some(([re]) => re.test(he.trim()));
}

export const PHRASE_COUNT = Object.keys(PHRASES).length;
