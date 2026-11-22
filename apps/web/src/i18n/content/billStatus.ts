// The Knesset's bill statuses (KNS_Status, 23 values on bills with a plenum vote) in the site's languages. The Hebrew
// is the official text; these are ours. A status that is not here is shown in Hebrew, never guessed.

import type { Locale } from "../config";

type Tr = Record<Exclude<Locale, "he">, string>;

const STATUS: Record<string, Tr> = {
  "התקבלה בקריאה שלישית": { en: "passed third reading", ru: "принят в третьем чтении", ar: "أُقرّ في القراءة الثالثة" },
  "נעצרה": { en: "stopped", ru: "остановлен", ar: "توقّف" },
  "מוזגה עם הצעת חוק אחרת": { en: "merged with another bill", ru: "объединён с другим законопроектом", ar: "دُمج مع اقتراح قانون آخر" },
  "הוסבה להצעה לסדר היום": { en: "converted into a motion for the agenda", ru: "преобразован в предложение к повестке дня", ar: "حُوّل إلى اقتراح لجدول الأعمال" },
  "הונחה על שולחן הכנסת לדיון מוקדם": { en: "tabled for the preliminary reading", ru: "внесён в Кнессет к предварительному чтению", ar: "وُضع على طاولة الكنيست للقراءة التمهيدية" },
  "במליאה לדיון מוקדם": { en: "in the plenum for the preliminary reading", ru: "в пленуме, предварительное чтение", ar: "في الهيئة العامة للقراءة التمهيدية" },
  "בוועדת הכנסת לקביעת הוועדה המטפלת": { en: "in the House Committee, which decides the committee to handle it", ru: "в комиссии Кнессета, которая определит профильную комиссию", ar: "في لجنة الكنيست لتحديد اللجنة المختصة" },
  "הכנה לקריאה ראשונה": { en: "in committee, being prepared for the first reading", ru: "готовится в комиссии к первому чтению", ar: "قيد الإعداد في اللجنة للقراءة الأولى" },
  "אושרה בוועדה לקריאה ראשונה": { en: "approved by the committee for the first reading", ru: "одобрен комиссией к первому чтению", ar: "أقرّته اللجنة للقراءة الأولى" },
  "הונחה על שולחן הכנסת לקריאה ראשונה": { en: "tabled for the first reading", ru: "внесён в Кнессет к первому чтению", ar: "وُضع على طاولة الكنيست للقراءة الأولى" },
  "לדיון במליאה לקראת הקריאה הראשונה": { en: "awaiting the plenum debate before the first reading", ru: "ожидает обсуждения в пленуме перед первым чтением", ar: "بانتظار نقاش الهيئة العامة قبل القراءة الأولى" },
  "הכנה לקריאה שנייה ושלישית": { en: "in committee, being prepared for the second and third readings", ru: "готовится в комиссии ко второму и третьему чтениям", ar: "قيد الإعداد في اللجنة للقراءتين الثانية والثالثة" },
  "אושרה בוועדה לקריאה שנייה-שלישית": { en: "approved by the committee for the second and third readings", ru: "одобрен комиссией ко второму и третьему чтениям", ar: "أقرّته اللجنة للقراءتين الثانية والثالثة" },
  "הונחה על שולחן הכנסת לקריאה שנייה-שלישית": { en: "tabled for the second and third readings", ru: "внесён в Кнессет ко второму и третьему чтениям", ar: "وُضع على طاولة الكنيست للقراءتين الثانية والثالثة" },
  "לדיון במליאה לקראת קריאה שנייה-שלישית": { en: "awaiting the plenum debate before the second and third readings", ru: "ожидает обсуждения в пленуме перед вторым и третьим чтениями", ar: "بانتظار نقاش الهيئة العامة قبل القراءتين الثانية والثالثة" },
  "הוחזרה לוועדה להכנה לקריאה שלישית": { en: "returned to the committee to be prepared for the third reading", ru: "возвращён в комиссию для подготовки к третьему чтению", ar: "أُعيد إلى اللجنة للإعداد للقراءة الثالثة" },
  "לדיון במליאה לקראת קריאה שלישית": { en: "awaiting the plenum debate before the third reading", ru: "ожидает обсуждения в пленуме перед третьим чтением", ar: "بانتظار نقاش الهيئة العامة قبل القراءة الثالثة" },
  // "continuity": carrying a bill over from the previous Knesset at the stage it had reached
  "בדיון בוועדה על החלת דין רציפות": { en: "in committee: whether to carry the bill over from the previous Knesset", ru: "в комиссии: вопрос о переносе законопроекта из прошлого созыва", ar: "في اللجنة: نقاش حول مواصلة تشريع الاقتراح من الدورة السابقة" },
  "לדיון במליאה על החלת דין רציפות": { en: "awaiting the plenum debate on carrying the bill over from the previous Knesset", ru: "ожидает обсуждения в пленуме о переносе законопроекта из прошлого созыва", ar: "بانتظار نقاش الهيئة العامة حول مواصلة تشريع الاقتراح من الدورة السابقة" },
  "הבקשה לדין רציפות נדחתה במליאה": { en: "the plenum refused to carry the bill over from the previous Knesset", ru: "пленум отказал в переносе законопроекта из прошлого созыва", ar: "رفضت الهيئة العامة مواصلة تشريع الاقتراح من الدورة السابقة" },
  "לאישור פיצול במליאה": { en: "awaiting the plenum's approval of a split", ru: "ожидает одобрения разделения в пленуме", ar: "بانتظار مصادقة الهيئة العامة على التقسيم" },
  "לאישור מיזוג בוועדת הכנסת": { en: "awaiting the House Committee's approval of a merger", ru: "ожидает одобрения объединения в комиссии Кнессета", ar: "بانتظار مصادقة لجنة الكنيست على الدمج" },
  "להסרה מסדר היום לבקשת ועדה": { en: "to be removed from the agenda at a committee's request", ru: "подлежит снятию с повестки дня по просьбе комиссии", ar: "للشطب من جدول الأعمال بطلب من لجنة" },
};

/** The status in the locale, or null where it has to stay in Hebrew (the Hebrew site, or a status we have not seen). */
export function billStatus(locale: Locale, he: string | null): string | null {
  return locale === "he" || !he ? null : STATUS[he.trim()]?.[locale] ?? null;
}
