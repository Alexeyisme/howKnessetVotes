// What a vote that is not on a bill decides, per kind (lib/voteKinds.ts) and locale. Each text says only what the
// source it links to says (the section is named in `source`); written for the site, not taken from the Knesset.

import type { Locale } from "../config";
import type { VoteKind } from "@/lib/voteKinds";

type Text = { title: string; text: string; source: string };

const TEXTS: Record<Locale, Record<VoteKind, Text>> = {
  ru: {
    speaker: {
      title: "Выборы председателя Кнессета",
      text: "Кнессет избирает председателя из числа своих депутатов. Пока председатель не избран, его обязанности исполняет прежний председатель, если он снова избран в Кнессет.",
      source: "Основной закон: Кнессет, §20",
    },
    deputies: {
      title: "Выборы заместителей председателя Кнессета",
      text: "Кнессет избирает заместителей председателя из числа своих депутатов. Вместе с председателем они образуют президиум Кнессета; заместителей не больше семи, если комиссия Кнессета не решит иначе большинством в три четверти (Закон о Кнессете, §10).",
      source: "Основной закон: Кнессет, §20",
    },
    arrangements: {
      title: "Выборы Организационной комиссии",
      text: "Это временная комиссия нового Кнессета. Её избирают как можно скорее после выборов, а возглавляет её депутат от фракции того, кому президент поручил сформировать правительство. Места распределяются по размеру фракций: у каждой фракции из четырёх и более депутатов есть представитель. Комиссия предлагает Кнессету состав постоянных комиссий, до их избрания выполняет функции комиссии Кнессета и может создать временные финансовую комиссию и комиссию по иностранным делам и обороне. Голосуют за предложенный состав комиссии.",
      source: "Закон о Кнессете, §2א",
    },
    arrangementsProposal: {
      title: "Предложение Организационной комиссии",
      text: "Организационная комиссия — временная комиссия нового Кнессета, которая работает, пока не избраны постоянные комиссии. Она предлагает Кнессету их состав, до избрания комиссии Кнессета выполняет её функции и может создать временные финансовую комиссию и комиссию по иностранным делам и обороне. Голосуют за её предложение.",
      source: "Закон о Кнессете, §2א",
    },
    continuity: {
      title: "Преемственность законопроекта",
      text: "Работа над законопроектом, начатая в прошлом Кнессете, продолжается в новом, только если он так решит. Если законопроект прошёл первое чтение и был передан в комиссию, новое правительство (или профильная комиссия) может заявить, что хочет продолжить его; любая фракция может в течение двух недель возразить. Если Кнессет решает применить преемственность, он продолжает работу с того места, где она остановилась, и может засчитать прежние обсуждения как свои.",
      source: "Закон о преемственности обсуждения законопроектов, 1993, §§1–6",
    },
    government: {
      title: "Решение правительства, которому нужно одобрение Кнессета",
      text: "Без голосования Кнессета правительство не может ввести в свой состав нового министра (§15), перераспределить обязанности между министрами, передать другому министру полномочия, данные законом, а также создать, объединить, разделить или упразднить министерство (§31). Голосуют за то, чтобы одобрить решение правительства.",
      source: "Основной закон: правительство, §§15, 31",
    },
    agendaSummary: {
      title: "Предложение итогового решения",
      text: "После обсуждения в пленуме фракции могут внести предложение итогового решения; каждое ставится на голосование одним вопросом, даже если в нём несколько пунктов. Такое решение — не закон, а позиция Кнессета по теме обсуждения.",
      source: "Регламент Кнессета, §56",
    },
    agenda: {
      title: "Предложение на повестку дня",
      text: "Депутат предлагает Кнессету обсудить тему и обосновывает её; затем правительство говорит, согласно ли оно включить тему в повестку, или предлагает обсудить её в комиссии. Голосуют о том, будет ли тема обсуждаться дальше — в пленуме или в комиссии (что именно поставлено на голосование, сказано выше). Если автор удовлетворён ответом правительства, голосования нет. Закон таким голосованием не принимается.",
      source: "Регламент Кнессета, §§52–53",
    },
  },
  en: {
    speaker: {
      title: "Election of the Speaker of the Knesset",
      text: "The Knesset elects its Speaker from among its members. Until then, the outgoing Speaker stays in office if re-elected to the Knesset.",
      source: "Basic Law: The Knesset, §20",
    },
    deputies: {
      title: "Election of the Deputy Speakers",
      text: "The Knesset elects the Deputy Speakers from among its members. Together with the Speaker they form the Knesset Presidium; there are at most seven, unless the House Committee decides otherwise by a three-quarters majority (Knesset Law, §10).",
      source: "Basic Law: The Knesset, §20",
    },
    arrangements: {
      title: "Election of the Arrangements Committee",
      text: "A temporary committee of a new Knesset. It is elected as soon as possible after the election and chaired by a member of the faction of the member the President has asked to form a government. Seats follow the factions' size: every faction of four or more members has a representative. The committee proposes the make-up of the standing committees, acts as the House Committee until one is elected, and may set up temporary finance and foreign affairs and defense committees. The vote is on the proposed make-up of the committee.",
      source: "Knesset Law, §2A",
    },
    arrangementsProposal: {
      title: "A proposal of the Arrangements Committee",
      text: "The Arrangements Committee is a temporary committee of a new Knesset that works until the standing committees are elected. It proposes their make-up, acts as the House Committee until one is elected, and may set up temporary finance and foreign affairs and defense committees. The vote is on its proposal.",
      source: "Knesset Law, §2A",
    },
    continuity: {
      title: "Continuity of a bill",
      text: "Work on a bill begun in the previous Knesset continues in the new one only if it so decides. For a bill that passed its first reading and went to a committee, the new government (or the relevant committee) may announce that it wants to continue it; any faction may object within two weeks. If the Knesset applies continuity, it picks the bill up where it stopped and may treat the earlier debates as its own.",
      source: "Continuity of Debate on Bills Law, 1993, §§1–6",
    },
    government: {
      title: "A government decision that needs the Knesset's approval",
      text: "Without a Knesset vote the government cannot add a minister (§15), change the division of duties between ministers, transfer a power given by law to another minister, or create, merge, split or abolish a ministry (§31). The vote is on approving the government's decision.",
      source: "Basic Law: The Government, §§15, 31",
    },
    agendaSummary: {
      title: "A proposed resolution summing up a debate",
      text: "After a plenum debate, factions may put forward a resolution summing it up; each is put to a single vote, even if it has several clauses. Such a resolution is not a law but the Knesset's position on the subject of the debate.",
      source: "Knesset Rules of Procedure, §56",
    },
    agenda: {
      title: "Motion for the agenda",
      text: "A member proposes that the Knesset discuss a subject and argues for it; the government then says whether it agrees to put the subject on the agenda, or proposes that a committee discuss it. The vote decides whether the subject is taken further, in the plenum or in a committee (the question above says which). If the proposer is satisfied with the government's answer, there is no vote. No law is passed by this vote.",
      source: "Knesset Rules of Procedure, §§52–53",
    },
  },
  he: {
    speaker: {
      title: "בחירת יושב ראש הכנסת",
      text: "הכנסת בוחרת מבין חבריה יושב ראש. עד לבחירתו ממשיך לכהן יושב ראש הכנסת היוצאת, אם שב ונבחר לכנסת.",
      source: "חוק-יסוד: הכנסת, סעיף 20",
    },
    deputies: {
      title: "בחירת סגנים ליושב ראש הכנסת",
      text: "הכנסת בוחרת מבין חבריה סגנים ליושב הראש. יחד איתו הם נשיאות הכנסת; מספר הסגנים לא יעלה על שבעה, אלא אם כן החליטה ועדת הכנסת אחרת ברוב של שלושה רבעים (חוק הכנסת, סעיף 10).",
      source: "חוק-יסוד: הכנסת, סעיף 20",
    },
    arrangements: {
      title: "בחירת הוועדה המסדרת",
      text: "ועדה זמנית של כנסת חדשה. היא נבחרת מוקדם ככל האפשר לאחר הבחירות, ובראשה עומד חבר כנסת מסיעתו של מי שהנשיא הטיל עליו להרכיב את הממשלה. המקומות בה מחולקים לפי גודל הסיעות: לכל סיעה של ארבעה חברים או יותר יש נציג. הוועדה מציעה לכנסת את הרכב הוועדות הקבועות, ממלאת את תפקידי ועדת הכנסת עד שזו נבחרת, ורשאית להקים ועדות זמניות לענייני כספים ולענייני חוץ וביטחון. ההצבעה היא על ההרכב המוצע של הוועדה.",
      source: "חוק הכנסת, סעיף 2א",
    },
    arrangementsProposal: {
      title: "הצעת הוועדה המסדרת",
      text: "הוועדה המסדרת היא ועדה זמנית של כנסת חדשה, הפועלת עד שנבחרות הוועדות הקבועות. היא מציעה את הרכבן, ממלאת את תפקידי ועדת הכנסת עד שזו נבחרת, ורשאית להקים ועדות זמניות לענייני כספים ולענייני חוץ וביטחון. ההצבעה היא על הצעתה.",
      source: "חוק הכנסת, סעיף 2א",
    },
    continuity: {
      title: "דין רציפות",
      text: "הדיון בהצעת חוק שהחל בכנסת היוצאת נמשך בכנסת החדשה רק אם היא מחליטה על כך. על הצעת חוק שעברה קריאה ראשונה והועברה לוועדה, רשאים הממשלה החדשה (או הוועדה הנוגעת בדבר) להודיע שהם רוצים להמשיך בה; כל סיעה רשאית להתנגד תוך שבועיים. החליטה הכנסת להחיל רציפות, היא ממשיכה לדון בהצעה מהמקום שבו נעצרה, ורשאית לנהוג בדיונים הקודמים כאילו היו דיוניה.",
      source: "חוק רציפות הדיון בהצעות חוק, התשנ\"ג-1993, סעיפים 1–6",
    },
    government: {
      title: "החלטת ממשלה הטעונה אישור הכנסת",
      text: "בלי הצבעה בכנסת הממשלה אינה יכולה לצרף שר נוסף (סעיף 15), לשנות את חלוקת התפקידים בין השרים, להעביר לשר אחר סמכות הנתונה על פי חוק, או לאחד, לחלק, לבטל ולהקים משרדים (סעיף 31). ההצבעה היא על אישור החלטת הממשלה.",
      source: "חוק-יסוד: הממשלה, סעיפים 15, 31",
    },
    agendaSummary: {
      title: "הצעת החלטה לסיכום הדיון",
      text: "אחרי דיון במליאה רשאיות הסיעות להגיש הצעת החלטה לסיכום הדיון; כל הצעה מועמדת להצבעה אחת, גם אם יש בה כמה סעיפים. החלטה כזו אינה חוק, אלא עמדת הכנסת בנושא הדיון.",
      source: "תקנון הכנסת, סעיף 56",
    },
    agenda: {
      title: "הצעה לסדר היום",
      text: "חבר כנסת מציע לכנסת לדון בנושא ומנמק את הצעתו; הממשלה מודיעה אם היא מסכימה לכלול את הנושא בסדר היום, או מציעה שיידון בוועדה. ההצבעה מכריעה אם הנושא יידון הלאה, במליאה או בוועדה (השאלה שלמעלה אומרת על מה בדיוק). אם המציע מסתפק בתשובת הממשלה, אין מצביעים. בהצבעה כזו לא מתקבל חוק.",
      source: "תקנון הכנסת, סעיפים 52–53",
    },
  },
  ar: {
    speaker: {
      title: "انتخاب رئيس الكنيست",
      text: "ينتخب الكنيست رئيسه من بين أعضائه. وإلى أن يُنتخب، يواصل رئيس الكنيست السابق مهامه إذا أعيد انتخابه للكنيست.",
      source: "قانون أساس: الكنيست، البند 20",
    },
    deputies: {
      title: "انتخاب نواب رئيس الكنيست",
      text: "ينتخب الكنيست نواب الرئيس من بين أعضائه. ويشكّلون مع الرئيس هيئة رئاسة الكنيست؛ ولا يزيد عددهم على سبعة، إلا إذا قررت لجنة الكنيست غير ذلك بأغلبية ثلاثة أرباع (قانون الكنيست، البند 10).",
      source: "قانون أساس: الكنيست، البند 20",
    },
    arrangements: {
      title: "انتخاب اللجنة المنظمة",
      text: "لجنة مؤقتة للكنيست الجديد. تُنتخب في أقرب وقت ممكن بعد الانتخابات، ويرأسها عضو من كتلة من كلّفه رئيس الدولة بتشكيل الحكومة. تُوزَّع المقاعد فيها بحسب حجم الكتل: لكل كتلة من أربعة أعضاء أو أكثر ممثل. تقترح اللجنة على الكنيست تركيبة اللجان الدائمة، وتتولى مهام لجنة الكنيست إلى أن تُنتخب، ويجوز لها إقامة لجنتين مؤقتتين للمالية وللخارجية والأمن. التصويت على التركيبة المقترحة للجنة.",
      source: "قانون الكنيست، البند 2أ",
    },
    arrangementsProposal: {
      title: "اقتراح اللجنة المنظمة",
      text: "اللجنة المنظمة لجنة مؤقتة للكنيست الجديد تعمل إلى أن تُنتخب اللجان الدائمة. تقترح تركيبتها، وتتولى مهام لجنة الكنيست إلى أن تُنتخب، ويجوز لها إقامة لجنتين مؤقتتين للمالية وللخارجية والأمن. التصويت على اقتراحها.",
      source: "قانون الكنيست، البند 2أ",
    },
    continuity: {
      title: "استمرارية مشروع قانون",
      text: "لا يستمر العمل على مشروع قانون بدأ في الكنيست السابق إلا إذا قرر الكنيست الجديد ذلك. فمشروع القانون الذي اجتاز القراءة الأولى وأُحيل إلى لجنة، يجوز للحكومة الجديدة (أو للجنة المختصة) أن تعلن رغبتها في مواصلته؛ ويجوز لأي كتلة الاعتراض خلال أسبوعين. وإذا قرر الكنيست تطبيق الاستمرارية، يواصل العمل من حيث توقف، ويجوز له اعتبار المداولات السابقة مداولاته.",
      source: "قانون استمرارية المداولات في مشاريع القوانين، 1993، البنود 1–6",
    },
    government: {
      title: "قرار حكومي يحتاج إلى موافقة الكنيست",
      text: "لا تستطيع الحكومة من دون تصويت الكنيست ضمّ وزير جديد (البند 15)، أو تغيير توزيع المهام بين الوزراء، أو نقل صلاحية ممنوحة بموجب قانون إلى وزير آخر، أو إنشاء وزارة أو دمجها أو تقسيمها أو إلغاؤها (البند 31). التصويت على الموافقة على قرار الحكومة.",
      source: "قانون أساس: الحكومة، البندان 15 و31",
    },
    agendaSummary: {
      title: "اقتراح قرار لتلخيص النقاش",
      text: "بعد نقاش في الهيئة العامة، يجوز للكتل تقديم اقتراح قرار لتلخيص النقاش؛ ويُطرح كل اقتراح في تصويت واحد حتى لو تضمّن عدة بنود. ومثل هذا القرار ليس قانونًا، بل موقف الكنيست في موضوع النقاش.",
      source: "النظام الداخلي للكنيست، البند 56",
    },
    agenda: {
      title: "اقتراح لجدول الأعمال",
      text: "يقترح عضو كنيست أن يناقش الكنيست موضوعًا ويعلّل اقتراحه؛ ثم تعلن الحكومة هل توافق على إدراج الموضوع في جدول الأعمال، أو تقترح أن تناقشه لجنة. يحسم التصويت هل يُناقَش الموضوع لاحقًا، في الهيئة العامة أو في لجنة (السؤال أعلاه يوضح ذلك). وإذا اكتفى المقترِح بردّ الحكومة لا يجري تصويت. ولا يُقَرّ قانون بهذا التصويت.",
      source: "النظام الداخلي للكنيست، البندان 52–53",
    },
  },
};

export function voteKindText(locale: Locale, kind: VoteKind): Text {
  return TEXTS[locale][kind];
}
