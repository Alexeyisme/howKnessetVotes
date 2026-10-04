// Glossary terms per locale. The `he` column is the Hebrew term as written in Knesset documents (not shown in the
// Hebrew UI, where the term itself is Hebrew).

import type { ReactNode } from "react";
import type { Locale } from "../config";
import type { Dict } from "../dict/ru";

export type Term = { id: string; term: string; he: string; text: ReactNode };

type L = (href: string, text: string) => ReactNode;

export function glossary(locale: Locale, d: Dict, link: L): Term[] {
  const h = d.stageHint;
  if (locale === "en") return [
    { id: "plenum", term: "Plenum", he: "מליאה", text: "The full sitting of all 120 members. The votes on this site are plenum votes; committee votes are not included." },
    { id: "term", term: "Knesset (the 25th Knesset)", he: "הכנסת ה־25", text: "The Knesset elected in one election. It usually serves until the next election: by law up to four years, in practice often less." },
    { id: "faction", term: "Faction (party)", he: "סיעה", text: <>A group of members in the Knesset. Usually matches a list that won seats in the election, but it can split or merge with another. The site shows a member&apos;s faction <strong>on the day of the vote</strong>, not today&apos;s.</> },
    { id: "preliminary", term: "Preliminary reading", he: "קריאה טרומית", text: h.preliminary },
    { id: "first", term: "First reading", he: "קריאה ראשונה", text: h.first },
    { id: "second", term: "Second reading", he: "קריאה שנייה", text: h.second },
    { id: "third", term: "Third reading", he: "קריאה שלישית", text: h.third },
    { id: "reservation", term: "Reservation", he: "הסתייגות", text: <>An amendment to the bill&apos;s text in second reading, usually from the opposition. Each reservation is voted on separately, so one law can have hundreds of votes. &ldquo;For&rdquo; in such a vote is for the amendment, <strong>not for the law</strong>.</> },
    { id: "sections", term: "Vote on sections", he: "הצבעה על סעיפים", text: "In second reading the sections of the bill are approved one by one or in groups. The final position on the law shows in the third reading." },
    { id: "quorum", term: "Quorum and majority", he: "מניין חוקי ורוב", text: <>The plenum has <strong>no quorum</strong>: a law passes by a simple majority of those voting, even if only a few members are in the hall. That is why uncontroversial bills often pass with 10–20 votes. A majority of all 120 members (61 votes) is needed only for some decisions: a no-confidence motion and changes to entrenched provisions of Basic Laws.</> },
    { id: "no-confidence", term: "No-confidence motion", he: "הצעת אי-אמון", text: "A motion to replace the government. To pass it needs at least 61 votes for and an agreed candidate for prime minister." },
    { id: "bill-types", term: "Private member's, government and committee bills", he: "הצעת חוק פרטית / ממשלתית / של ועדה", text: "A private bill is introduced by a member and goes through a preliminary reading. A government bill is introduced by the government and starts at the first reading. A committee bill is prepared by a Knesset committee." },
    { id: "coalition", term: "Coalition and opposition", he: "קואליציה ואופוזיציה", text: "The coalition is the factions supporting the government; the rest are the opposition. The coalition can change during a Knesset term." },
    { id: "norwegian", term: "The “Norwegian law”", he: "החוק הנורבגי", text: "A minister can resign their Knesset seat, which passes to the next person on the list. If the minister leaves the government, they return to the Knesset. So faction rosters change." },
    { id: "roll-call", term: "Roll-call record", he: "הצבעה שמית", text: <>A record of how a specific member voted. No record <strong>does not mean</strong> the member was absent: they may have been in the hall and not voted. More in the {link("/about/methodology#records", "methodology")}.</> },
    { id: "present", term: "Present, did not vote", he: "נוכח", text: "The member registered as present but did not choose for, against or abstain." },
  ];
  if (locale === "ar") return [
    { id: "plenum", term: "الهيئة العامة", he: "מליאה", text: "الجلسة العامة لكل أعضاء الكنيست الـ120. التصويتات في هذا الموقع هي تصويتات الهيئة العامة؛ تصويتات اللجان غير مشمولة." },
    { id: "term", term: "دورة الكنيست (الكنيست الـ25)", he: "הכנסת ה־25", text: "الكنيست المنتخبة في انتخابات واحدة. تعمل عادةً حتى الانتخابات التالية: وفق القانون حتى أربع سنوات، وفي الواقع أقل في أحيان كثيرة." },
    { id: "faction", term: "الكتلة (الحزب)", he: "סיעה", text: <>مجموعة من أعضاء الكنيست. تطابق عادةً قائمة فازت بمقاعد في الانتخابات، لكنها قد تنقسم أو تتّحد مع أخرى. يعرض الموقع كتلة العضو <strong>يوم التصويت</strong>، لا كتلته اليوم.</> },
    { id: "preliminary", term: "القراءة التمهيدية", he: "קריאה טרומית", text: h.preliminary },
    { id: "first", term: "القراءة الأولى", he: "קריאה ראשונה", text: h.first },
    { id: "second", term: "القراءة الثانية", he: "קריאה שנייה", text: h.second },
    { id: "third", term: "القراءة الثالثة", he: "קריאה שלישית", text: h.third },
    { id: "reservation", term: "تحفّظ", he: "הסתייגות", text: <>تعديل على نص اقتراح القانون في القراءة الثانية، تقدّمه المعارضة عادةً. يُصوَّت على كل تحفّظ على حدة، لذا قد يكون لقانون واحد مئات التصويتات. «مع» في مثل هذا التصويت تعني تأييد التعديل، <strong>لا تأييد القانون</strong>.</> },
    { id: "sections", term: "التصويت على البنود", he: "הצבעה על סעיפים", text: "في القراءة الثانية تُقرّ بنود اقتراح القانون واحدًا واحدًا أو في مجموعات. الموقف النهائي من القانون يظهر في القراءة الثالثة." },
    { id: "quorum", term: "النصاب والأغلبية", he: "מניין חוקי ורוב", text: <>لا يوجد <strong>نصاب</strong> في الهيئة العامة: يُقرّ القانون بأغلبية عادية من المصوّتين، حتى لو كان في القاعة عدد قليل من الأعضاء. لذلك كثيرًا ما تُقرّ اقتراحات قوانين غير خلافية بـ10–20 صوتًا. أغلبية أعضاء الكنيست الـ120 (61 صوتًا) مطلوبة فقط لبعض القرارات: اقتراح حجب الثقة وتغيير الأحكام المحصّنة في قوانين الأساس.</> },
    { id: "no-confidence", term: "اقتراح حجب الثقة", he: "הצעת אי-אמון", text: "اقتراح لاستبدال الحكومة. لإقراره يلزم 61 صوتًا مؤيدًا على الأقل ومرشح متّفق عليه لرئاسة الحكومة." },
    { id: "bill-types", term: "اقتراح قانون خاص، حكومي ومن لجنة", he: "הצעת חוק פרטית / ממשלתית / של ועדה", text: "الاقتراح الخاص يقدّمه عضو كنيست ويمرّ بقراءة تمهيدية. الاقتراح الحكومي تقدّمه الحكومة ويبدأ بالقراءة الأولى. اقتراح اللجنة تُعدّه إحدى لجان الكنيست." },
    { id: "coalition", term: "الائتلاف والمعارضة", he: "קואליציה ואופוזיציה", text: "الائتلاف هو الكتل الداعمة للحكومة؛ والباقي هي المعارضة. قد يتغيّر تركيب الائتلاف خلال دورة الكنيست." },
    { id: "norwegian", term: "«القانون النرويجي»", he: "החוק הנורבגי", text: "يمكن للوزير أن يستقيل من الكنيست، فينتقل مقعده إلى التالي في القائمة. إذا ترك الوزير الحكومة يعود إلى الكنيست. لذلك يتغيّر تركيب الكتل." },
    { id: "roll-call", term: "سجل اسمي", he: "הצבעה שמית", text: <>سجل يبيّن كيف صوّت عضو كنيست معيّن. غياب السجل <strong>لا يعني</strong> أن العضو كان غائبًا: ربما كان في القاعة ولم يصوّت. التفاصيل في {link("/about/methodology#records", "المنهجية")}.</> },
    { id: "present", term: "حاضر، لم يصوّت", he: "נוכח", text: "سُجّل العضو حاضرًا لكنه لم يختر مع أو ضد أو امتنع." },
  ];
  if (locale === "he") return [
    { id: "plenum", term: "מליאה", he: "", text: "הישיבה של כל 120 חברי הכנסת. ההצבעות באתר הן הצבעות המליאה; הצבעות בוועדות אינן כלולות." },
    { id: "term", term: "כנסת (הכנסת ה-25)", he: "", text: "הכנסת שנבחרה בבחירות מסוימות. בדרך כלל היא מכהנת עד הבחירות הבאות: לפי החוק עד ארבע שנים, ובפועל לעיתים פחות." },
    { id: "faction", term: "סיעה", he: "", text: <>קבוצת חברי כנסת. בדרך כלל תואמת רשימה שנבחרה בבחירות, אך היא יכולה להתפצל או להתאחד עם אחרת. האתר מציג את סיעת חבר הכנסת <strong>ביום ההצבעה</strong>, ולא את סיעתו היום.</> },
    { id: "preliminary", term: "קריאה טרומית", he: "", text: h.preliminary },
    { id: "first", term: "קריאה ראשונה", he: "", text: h.first },
    { id: "second", term: "קריאה שנייה", he: "", text: h.second },
    { id: "third", term: "קריאה שלישית", he: "", text: h.third },
    { id: "reservation", term: "הסתייגות", he: "", text: <>הצעה לשינוי נוסח הצעת החוק בקריאה שנייה, בדרך כלל מהאופוזיציה. מצביעים על כל הסתייגות בנפרד, ולכן לחוק אחד יכולות להיות מאות הצבעות. ״בעד״ בהצבעה כזו הוא בעד ההסתייגות, <strong>לא בעד החוק</strong>.</> },
    { id: "sections", term: "הצבעה על סעיפים", he: "", text: "בקריאה שנייה מאשרים את סעיפי הצעת החוק אחד-אחד או בקבוצות. העמדה הסופית כלפי החוק נראית בקריאה השלישית." },
    { id: "quorum", term: "מניין חוקי ורוב", he: "", text: <>במליאה <strong>אין מניין חוקי</strong>: חוק מתקבל ברוב רגיל של המצביעים, גם אם באולם נמצאים חברי כנסת מעטים. לכן הצעות חוק שאינן שנויות במחלוקת עוברות לעיתים קרובות ב-10–20 קולות. רוב של חברי הכנסת (61 קולות) נדרש רק בהחלטות מסוימות: הצעת אי-אמון ושינוי הוראות משוריינות בחוקי היסוד.</> },
    { id: "no-confidence", term: "הצעת אי-אמון", he: "", text: "הצעה להחליף את הממשלה. כדי שתתקבל נדרשים לפחות 61 קולות בעד ומועמד מוסכם לראשות הממשלה." },
    { id: "bill-types", term: "הצעת חוק פרטית, ממשלתית ושל ועדה", he: "", text: "הצעה פרטית מוגשת בידי חבר כנסת ועוברת קריאה טרומית. הצעה ממשלתית מוגשת בידי הממשלה ומתחילה בקריאה ראשונה. הצעת חוק של ועדה מוכנה בידי ועדה של הכנסת." },
    { id: "coalition", term: "קואליציה ואופוזיציה", he: "", text: "הקואליציה היא הסיעות התומכות בממשלה; השאר הן האופוזיציה. הרכב הקואליציה יכול להשתנות במהלך הכנסת." },
    { id: "norwegian", term: "״החוק הנורבגי״", he: "", text: "שר יכול להתפטר מהכנסת, ומקומו עובר לבא בתור ברשימה. אם השר עוזב את הממשלה, הוא חוזר לכנסת. לכן הרכב הסיעות משתנה." },
    { id: "roll-call", term: "רישום שמי", he: "", text: <>רישום של האופן שבו הצביע חבר כנסת מסוים. היעדר רישום <strong>אינו אומר</strong> שחבר הכנסת נעדר: ייתכן שהיה באולם ולא הצביע. פרטים {link("/about/methodology#records", "במתודולוגיה")}.</> },
    { id: "present", term: "נוכח, לא הצביע", he: "", text: "חבר הכנסת נרשם כנוכח, אך לא בחר בעד, נגד או נמנע." },
  ];
  return [
    { id: "plenum", term: "Пленум", he: "מליאה", text: "Общее заседание всех 120 депутатов. Здесь проходят голосования, которые показывает сайт. Голосования в комиссиях сюда не входят." },
    { id: "term", term: "Созыв (Кнессет N-го созыва)", he: "הכנסת ה־25", text: "Кнессет, избранный на одних выборах. Обычно работает до следующих выборов: по закону до четырёх лет, на практике часто меньше." },
    { id: "faction", term: "Фракция", he: "סיעה", text: <>Группа депутатов в Кнессете. Обычно соответствует списку, прошедшему на выборах, но может расколоться или объединиться с другой. Сайт показывает фракцию депутата <strong>на дату голосования</strong>, а не нынешнюю.</> },
    { id: "preliminary", term: "Предварительное чтение", he: "קריאה טרומית", text: h.preliminary },
    { id: "first", term: "Первое чтение", he: "קריאה ראשונה", text: h.first },
    { id: "second", term: "Второе чтение", he: "קריאה שנייה", text: h.second },
    { id: "third", term: "Третье чтение", he: "קריאה שלישית", text: h.third },
    { id: "reservation", term: "Оговорка", he: "הסתייגות", text: <>Поправка к тексту законопроекта во втором чтении, чаще всего от оппозиции. По каждой оговорке голосуют отдельно, поэтому у одного закона бывают сотни голосований. «За» в таком голосовании — за поправку, <strong>а не за закон</strong>.</> },
    { id: "sections", term: "Голосование по статьям", he: "הצבעה על סעיפים", text: "Во втором чтении статьи законопроекта утверждают по отдельности или группами. Итоговое отношение к закону видно в третьем чтении." },
    { id: "quorum", term: "Кворум и большинство", he: "מניין חוקי ורוב", text: <>Кворума в пленуме <strong>нет</strong>: закон принимается простым большинством проголосовавших, даже если в зале несколько депутатов. Поэтому бесспорные законопроекты часто проходят 10–20 голосами. Большинство от всех 120 депутатов (61 голос) нужно только для некоторых решений: вотума недоверия и изменения «защищённых» положений основных законов.</> },
    { id: "no-confidence", term: "Вотум недоверия", he: "הצעת אי-אמון", text: "Предложение сменить правительство. Чтобы пройти, нужно не меньше 61 голоса «за» и согласованный кандидат на пост главы правительства." },
    { id: "bill-types", term: "Частный, правительственный законопроект и законопроект комиссии", he: "הצעת חוק פרטית / ממשלתית / של ועדה", text: "Частный вносит депутат; он проходит предварительное чтение. Правительственный вносит правительство; он начинается сразу с первого чтения. Законопроект комиссии готовит комиссия Кнессета." },
    { id: "coalition", term: "Коалиция и оппозиция", he: "קואליציה ואופוזיציה", text: "Коалиция — фракции, поддерживающие правительство; остальные — оппозиция. Состав коалиции меняется во время созыва." },
    { id: "norwegian", term: "«Норвежский закон»", he: "החוק הנורבגי", text: "Министр может сложить мандат депутата, и его место займёт следующий по списку. Если министр уходит из правительства, он возвращается в Кнессет. Поэтому депутаты в списке фракции меняются." },
    { id: "roll-call", term: "Поимённая запись", he: "הצבעה שמית", text: <>Запись о том, как проголосовал конкретный депутат. Если записи нет, это <strong>не значит</strong>, что депутат отсутствовал: он мог быть в зале и не голосовать. Подробнее — в {link("/about/methodology#records", "методологии")}.</> },
    { id: "present", term: "Присутствовал, не голосовал", he: "נוכח", text: "Депутат отметился как присутствующий, но не выбрал «за», «против» или «воздержался»." },
  ];
}
