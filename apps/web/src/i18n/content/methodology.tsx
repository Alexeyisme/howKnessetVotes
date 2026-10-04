// Methodology page text per locale: one array of sections, rendered by app/[lang]/about/methodology.

import type { ReactNode } from "react";
import type { Locale } from "../config";

export type Section = { id: string; title: string; body: ReactNode };

const OK = <a href="https://oknesset.org" target="_blank" rel="noopener">Open Knesset</a>;

export function methodology(locale: Locale, link: (href: string, text: string) => ReactNode): Section[] {
  if (locale === "en") return [
    { id: "sources", title: "Sources", body: <>
      <ul>
        <li><strong>Knesset open data (OData v4)</strong>: plenum votes, roll-call records, bills, sponsors, members, factions and membership. The main source.</li>
        <li><strong>The old Knesset votes service (Votes.svc)</strong>, data up to July 2021: official results and votes missing from the main source, plus flags for votes not counted in the official result.</li>
        <li><strong>The Knesset website</strong>: official member names and faction names in English and Russian, and member photos.</li>
        <li><strong>Wikidata</strong>: English and Russian names for members not covered by the website, and spelling variants for search.</li>
        <li><strong>{OK}</strong> (the Hasadna public knowledge workshop): a member ID mapping table. Used with attribution.</li>
      </ul>
      <p className="small muted">Every vote links to its page on the Knesset website. Raw source responses are stored unchanged, so any number can be rechecked.</p></> },
    { id: "records", title: "Roll-call records and “absence”", body: <>
      <p>The open data lists only members who <strong>have a record</strong>: for, against, abstain or &ldquo;present, did not vote&rdquo;. When there is no record, the site <strong>does not count the member as absent</strong>: the source does not say so.</p>
      <p>89 votes have no roll-call records at all. These are votes by show of hands and secret ballots. For them only what was published is shown.</p></> },
    { id: "outcome", title: "Passed or not", body: <>
      <p>For votes up to July 2021 the result comes from official Knesset data. Later official results are not published in the open data, so the site derives them from the roll-call records: passed if &ldquo;for&rdquo; exceeds &ldquo;against&rdquo;; a tie does not pass; a no-confidence motion needs at least 61 votes for. Such results are labelled &ldquo;counted from roll-call records&rdquo;.</p>
      <p>The plenum has no quorum, so a law can pass with a handful of votes when nobody objects. See the {link("/about/glossary#quorum", "glossary")}.</p>
      <p className="small muted">Up to 2021 the roll call matches the official result in 95% of votes. The remaining differences are explained or logged for review. No numbers are adjusted to fit.</p></> },
    { id: "faction", title: "Faction on the day of the vote", body:
      <p>Each vote is attributed to the faction the member belonged to <strong>on the day of the vote</strong>. If the member switched factions that day, the vote is marked ambiguous. Votes whose faction cannot be determined (11 of 1.2 million) are shown separately.</p> },
    { id: "metrics", title: "Measures", body:
      <dl className="glossary">
        <div className="glossary-item"><dt><strong>Roll-call participation</strong></dt>
          <dd>Votes for, against and abstain, divided by the number of roll-call votes held during the member&apos;s mandate. This is <strong>not attendance</strong>: a member may have been in the Knesset and not voted.</dd></div>
        <div className="glossary-item"><dt><strong>Voting against the party majority</strong></dt>
          <dd>The member&apos;s vote differs from the choice of a strict majority of the <em>other</em> members of their faction who voted (at least two). The denominator is votes where such a majority existed. This <strong>does not prove a breach of party discipline</strong>: the party may have allowed a free vote.</dd></div>
        <div className="glossary-item"><dt><strong>Party cohesion</strong></dt>
          <dd>The share of the faction members&apos; votes matching the faction&apos;s most common choice in the same vote, over all votes.</dd></div>
        <div className="glossary-item"><dt><strong>How parties voted by topic</strong></dt>
          <dd>Only votes on the bill as a whole are counted (third reading by default). Reservations and procedural votes are excluded. &ldquo;Majority for&rdquo; means strictly more than half of the faction&apos;s voting members chose &ldquo;for&rdquo;.</dd></div>
      </dl> },
    { id: "topics", title: "Topics", body:
      <p>Topics come from two sources. The first is the <strong>Knesset&apos;s official law classification</strong> (51 categories): a bill gets the categories of the law it creates or amends, if that law is named in its title. The second is <strong>keywords</strong> in the Hebrew bill title. If there are more than three official categories (for example, the Arrangements Law), they are not used. Where both sources exist they agree on 91% of bills. Topics have not been reviewed by an editor yet, so errors are possible. The bill page shows where each topic came from. A vote inherits all topics of its bill, even when it concerns one section.</p> },
    { id: "coalition", title: "Coalition, opposition and parties", body: <>
      <p>Coalition membership is <strong>derived from official data</strong>: the Knesset lists every minister and deputy minister with the government number and dates. A faction is in the coalition on a date when one of its members holds a post in that day&apos;s government, and in the opposition otherwise. Between an election and the swearing-in of the next government there is no coalition, and the site says so. A minister who gave up their seat under the &ldquo;Norwegian law&rdquo; still counts for their faction.</p>
      <p>A few known exceptions are corrected by hand and marked as such: a party that supported the coalition without a ministry (Ra&apos;am, 2021–2022), a party whose ministers resigned while it stayed in the coalition (Shas, from July 2025), and similar cases. A vote is &ldquo;contested&rdquo; when the coalition majority and the opposition majority voted differently.</p>
      <p>A <strong>party</strong> links the factions it sat as in each Knesset (prepared by hand). A joint list counts for every party in it, so the Joint List&apos;s votes appear under Hadash, Balad, Ta&apos;al and Ra&apos;am.</p></> },
    { id: "names", title: "Names", body:
      <p>Member names in English and Russian come from the Knesset website; where it has none, from Wikidata. Russian and English names of factions from earlier Knessets were prepared by hand. The official Hebrew name is always shown. Bill titles are shown in Hebrew, as published by the Knesset. Member photos are linked from the Knesset website.</p> },
    { id: "updates", title: "Updates", body: <>
      <p>Data is updated automatically: every night, and every two hours on plenum days (Monday–Wednesday). Each update rereads the last 30 days of votes to pick up source corrections. The date of the latest update is at the bottom of every page.</p>
      <p className="small muted">Terms are explained in the {link("/about/glossary", "glossary")}.</p></> },
  ];
  if (locale === "he") return [
    { id: "sources", title: "מקורות", body: <>
      <ul>
        <li><strong>המידע הפתוח של הכנסת (OData v4)</strong>: הצבעות במליאה, רישומים שמיים, הצעות חוק, יוזמים, חברי כנסת, סיעות וחברות בהן. המקור העיקרי.</li>
        <li><strong>שירות ההצבעות הישן של הכנסת (Votes.svc)</strong>, נתונים עד יולי 2021: תוצאות רשמיות והצבעות שחסרות במקור העיקרי, וסימון קולות שלא נכללו בתוצאה הרשמית.</li>
        <li><strong>אתר הכנסת</strong>: השמות הרשמיים של חברי הכנסת ושל הסיעות באנגלית וברוסית, ותמונות חברי הכנסת.</li>
        <li><strong>ויקינתונים</strong>: שמות באנגלית וברוסית לחברי כנסת שאינם באתר, וגרסאות כתיב לחיפוש.</li>
        <li><strong><a href="https://oknesset.org" target="_blank" rel="noopener">כנסת פתוחה</a></strong> (הסדנא לידע ציבורי): טבלת התאמה של מזהי חברי הכנסת. בשימוש עם ציון המקור.</li>
      </ul>
      <p className="small muted">לכל הצבעה יש קישור לדף שלה באתר הכנסת. התשובות הגולמיות של המקורות נשמרות ללא שינוי, כך שאפשר לבדוק מחדש כל מספר.</p></> },
    { id: "records", title: "רישומים שמיים ו״היעדרות״", body: <>
      <p>במידע הפתוח מופיעים רק חברי כנסת <strong>שיש להם רישום</strong>: בעד, נגד, נמנע או ״נוכח, לא הצביע״. כשאין רישום, האתר <strong>אינו מחשיב את חבר הכנסת כנעדר</strong>: המקור אינו אומר זאת.</p>
      <p>ל-89 הצבעות אין רישומים שמיים כלל. אלה הצבעות בהרמת ידיים והצבעות חשאיות. עבורן מוצג רק מה שפורסם.</p></> },
    { id: "outcome", title: "התקבל או לא", body: <>
      <p>בהצבעות עד יולי 2021 התוצאה נלקחת מהנתונים הרשמיים של הכנסת. תוצאות מאוחרות יותר אינן מתפרסמות במידע הפתוח, ולכן האתר מחשב אותן מהרישומים השמיים: התקבל אם ״בעד״ גדול מ״נגד״; תיקו אינו מתקבל; הצעת אי-אמון דורשת לפחות 61 קולות בעד. תוצאה כזו מסומנת ״לפי הרישומים השמיים״.</p>
      <p>במליאה אין מניין חוקי, ולכן חוק יכול לעבור בקולות מעטים כשאין מתנגדים. ראו {link("/about/glossary#quorum", "במילון המונחים")}.</p>
      <p className="small muted">עד 2021 הרשימה השמית תואמת את התוצאה הרשמית ב-95% מההצבעות. שאר הפערים מוסברים או נרשמו לבדיקה. אין מספרים מותאמים.</p></> },
    { id: "faction", title: "הסיעה ביום ההצבעה", body:
      <p>כל קול משויך לסיעה שחבר הכנסת השתייך אליה <strong>ביום ההצבעה</strong>. אם עבר סיעה באותו יום, הקול מסומן כלא חד-משמעי. קולות שלא ניתן לקבוע את סיעתם (11 מתוך 1.2 מיליון) מוצגים בנפרד.</p> },
    { id: "metrics", title: "מדדים", body:
      <dl className="glossary">
        <div className="glossary-item"><dt><strong>השתתפות בהצבעות שמיות</strong></dt>
          <dd>קולות בעד, נגד ונמנע, חלקי מספר ההצבעות השמיות בתקופת הכהונה. זו <strong>אינה נוכחות</strong>: חבר הכנסת יכול היה להיות בכנסת ולא להצביע.</dd></div>
        <div className="glossary-item"><dt><strong>הצבעה נגד רוב הסיעה</strong></dt>
          <dd>הקול שונה מבחירת רוב מוחלט של <em>שאר</em> חברי הסיעה שהצביעו (לפחות שניים). המכנה הוא ההצבעות שבהן היה רוב כזה. זה <strong>אינו מוכיח הפרת משמעת סיעתית</strong>: ייתכן שהסיעה התירה הצבעה חופשית.</dd></div>
        <div className="glossary-item"><dt><strong>לכידות הסיעה</strong></dt>
          <dd>שיעור קולות חברי הסיעה שתאמו את הבחירה הנפוצה בסיעה באותה הצבעה, על פני כל ההצבעות.</dd></div>
        <div className="glossary-item"><dt><strong>איך הצביעו הסיעות לפי נושא</strong></dt>
          <dd>נספרות רק הצבעות על הצעת החוק בשלמותה (כברירת מחדל בקריאה שלישית). הסתייגויות והצבעות פרוצדורליות אינן נספרות. ״רוב בעד״ פירושו שיותר ממחצית חברי הסיעה שהצביעו בחרו ״בעד״.</dd></div>
      </dl> },
    { id: "topics", title: "נושאים", body:
      <p>הנושאים מגיעים משני מקורות. הראשון — <strong>הסיווג הרשמי של חוקי הכנסת</strong> (51 קטגוריות): הצעת חוק מקבלת את הקטגוריות של החוק שהיא יוצרת או מתקנת, אם שמו מופיע בשם ההצעה. השני — <strong>מילות מפתח</strong> בשם הצעת החוק. אם יש יותר משלוש קטגוריות רשמיות (למשל בחוק ההסדרים), הן אינן בשימוש. היכן שיש שני המקורות, הם מסכימים ב-91% מהצעות החוק. הנושאים עדיין לא נבדקו בידי עורך, ולכן ייתכנו טעויות. בדף הצעת החוק מוצג המקור של כל נושא. הצבעה מקבלת את כל הנושאים של הצעת החוק שלה, גם אם היא עוסקת בסעיף אחד.</p> },
    { id: "coalition", title: "קואליציה, אופוזיציה ומפלגות", body: <>
      <p>החברות בקואליציה <strong>נגזרת מנתונים רשמיים</strong>: הכנסת מפרסמת את כל השרים וסגני השרים עם מספר הממשלה והתאריכים. סיעה נחשבת לחלק מהקואליציה בתאריך שבו אחד מחבריה מכהן בתפקיד בממשלה של אותו יום, ואחרת — לאופוזיציה. בין הבחירות להשבעת הממשלה הבאה אין קואליציה, והאתר מציין זאת. שר שוויתר על מושבו לפי ״החוק הנורבגי״ ממשיך להיספר לסיעתו.</p>
      <p>כמה חריגים ידועים תוקנו ידנית ומסומנים ככאלה: מפלגה שתמכה בקואליציה בלי משרד (רע״ם, 2021–2022), מפלגה ששריה התפטרו אך נשארה בקואליציה (ש״ס, מיולי 2025) ומקרים דומים. הצבעה ״שנויה במחלוקת״ כשרוב הקואליציה ורוב האופוזיציה הצביעו אחרת.</p>
      <p><strong>מפלגה</strong> מקשרת את הסיעות שבהן ישבה בכל כנסת (הוכן ידנית). רשימה משותפת נספרת לכל המפלגות שבה, ולכן הצבעות הרשימה המשותפת מופיעות תחת חד״ש, בל״ד, תע״ל ורע״ם.</p></> },
    { id: "names", title: "שמות", body:
      <p>שמות חברי הכנסת באנגלית וברוסית לקוחים מאתר הכנסת; היכן שאין — מוויקינתונים. שמות הסיעות של כנסות קודמות ברוסית ובאנגלית הוכנו ידנית. השם הרשמי בעברית מוצג תמיד. תמונות חברי הכנסת מקושרות מאתר הכנסת.</p> },
    { id: "updates", title: "עדכון", body: <>
      <p>הנתונים מתעדכנים אוטומטית: בכל לילה, וכל שעתיים בימי מליאה (שני–רביעי). בכל עדכון נקראות מחדש ההצבעות של 30 הימים האחרונים, כדי לקלוט תיקונים במקור. תאריך העדכון האחרון מופיע בתחתית כל דף.</p>
      <p className="small muted">המונחים מוסברים {link("/about/glossary", "במילון המונחים")}.</p></> },
  ];
  return [
    { id: "sources", title: "Источники", body: <>
      <ul>
        <li><strong>Открытые данные Кнессета (OData v4)</strong>: голосования в пленуме, поимённые записи, законопроекты, инициаторы, депутаты, фракции и членство в них. Основной источник.</li>
        <li><strong>Старый сервис голосований Кнессета (Votes.svc)</strong>, данные до июля 2021 года: официальные итоги и голосования, которых нет в основном источнике, а также пометки о голосах, не вошедших в официальный итог.</li>
        <li><strong>Сайт Кнессета</strong>: официальные имена депутатов и названия фракций на русском и английском языках, фотографии депутатов.</li>
        <li><strong>Викиданные</strong>: английские и русские имена для депутатов, которых нет в материалах сайта, а также варианты написания для поиска.</li>
        <li><strong><a href="https://oknesset.org" target="_blank" rel="noopener">«Открытый Кнессет»</a></strong> (проект «Сикуй Хасадна» / Hasadna): таблица соответствия идентификаторов депутатов. Используется с указанием источника.</li>
      </ul>
      <p className="small muted">У каждого голосования есть ссылка на его карточку на сайте Кнессета. Исходные ответы источников сохраняются без изменений, чтобы любую цифру можно было перепроверить.</p></> },
    { id: "records", title: "Поимённые записи и «отсутствие»", body: <>
      <p>В открытых данных есть только депутаты, у которых <strong>есть запись</strong>: «за», «против», «воздержался» или «присутствовал, не голосовал». Если записи нет, сайт <strong>не считает депутата отсутствовавшим</strong>: источник этого не сообщает.</p>
      <p>У 89 голосований поимённых записей нет совсем. Это голосования поднятием рук и тайные голосования. Для них показывается только то, что опубликовано.</p></> },
    { id: "outcome", title: "Принято или нет", body: <>
      <p>Для голосований до июля 2021 года итог берётся из официальных данных Кнессета. Для более поздних официальный итог в открытых данных не публикуется. Тогда сайт считает его по поимённым записям: принято, если «за» больше, чем «против»; при равенстве не принято; вотум недоверия требует не меньше 61 голоса «за». Такой итог помечен «подсчёт по поимённым записям».</p>
      <p>Кворума в пленуме нет, поэтому закон, против которого никто не возражает, может пройти несколькими голосами. Подробнее — в {link("/about/glossary#quorum", "словаре")}.</p>
      <p className="small muted">До 2021 года поимённый список совпадает с официальным итогом в 95% голосований. Остальные расхождения объяснены или зарегистрированы для проверки. Подогнанных цифр нет.</p></> },
    { id: "faction", title: "Фракция на дату голосования", body:
      <p>Каждый голос относится к фракции, в которой депутат состоял <strong>в день голосования</strong>. Если депутат перешёл в другую фракцию в тот же день, голос помечен как неоднозначный. Голоса, для которых фракцию определить нельзя (11 из 1,2 млн), показаны отдельно.</p> },
    { id: "metrics", title: "Показатели", body:
      <dl className="glossary">
        <div className="glossary-item"><dt><strong>Участие в голосованиях</strong></dt>
          <dd>Голоса «за», «против» и «воздержался», делённые на число поимённых голосований за время мандата депутата. Это <strong>не посещаемость</strong>: депутат мог быть в Кнессете и не голосовать.</dd></div>
        <div className="glossary-item"><dt><strong>Голос против большинства фракции</strong></dt>
          <dd>Голос депутата отличается от выбора строгого большинства <em>других</em> проголосовавших членов его фракции (не меньше двух человек). Знаменатель — голосования, где такое большинство было. Это <strong>не доказывает нарушение фракционной дисциплины</strong>: фракция могла разрешить свободное голосование.</dd></div>
        <div className="glossary-item"><dt><strong>Единство фракции</strong></dt>
          <dd>Доля голосов членов фракции, совпавших с самым частым выбором фракции в том же голосовании, по всем голосованиям.</dd></div>
        <div className="glossary-item"><dt><strong>Как фракции голосовали по теме</strong></dt>
          <dd>Учитываются только голосования по законопроекту в целом (по умолчанию в третьем чтении). Оговорки и процедурные голосования исключены. «Большинство за» означает, что строго больше половины проголосовавших членов фракции выбрали «за».</dd></div>
      </dl> },
    { id: "topics", title: "Темы", body:
      <p>Темы берутся из двух источников. Первый — <strong>официальная классификация законов Кнессета</strong> (51 категория): законопроект получает категории закона, который он создаёт или изменяет, если этот закон назван в его заголовке. Второй — <strong>ключевые слова</strong> в названии законопроекта на иврите. Если официальных категорий больше трёх (например, у закона о договорённостях), они не используются. Там, где есть оба источника, они совпадают в 91% законопроектов. Темы ещё не проверены редактором, поэтому возможны ошибки. На странице законопроекта видно, откуда взялась каждая тема. Голосование получает темы своего законопроекта целиком, даже если речь об одной статье.</p> },
    { id: "coalition", title: "Коалиция, оппозиция и партии", body: <>
      <p>Принадлежность к коалиции <strong>выводится из официальных данных</strong>: Кнессет публикует всех министров и заместителей министров с номером правительства и датами. Фракция в коалиции на дату, когда кто-то из её членов занимает пост в правительстве этого дня, иначе — в оппозиции. Между выборами и присягой следующего правительства коалиции нет, и сайт так и пишет. Министр, сложивший мандат по «норвежскому закону», продолжает считаться за свою фракцию.</p>
      <p>Несколько известных исключений исправлены вручную и помечены: партия, поддерживавшая коалицию без министерских постов (РААМ, 2021–2022), партия, чьи министры ушли в отставку, но которая осталась в коалиции (ШАС, с июля 2025 года), и похожие случаи. Голосование «спорное», если большинство коалиции и большинство оппозиции голосовали по-разному.</p>
      <p><strong>Партия</strong> связывает фракции, которыми она была представлена в каждом Кнессете (подготовлено вручную). Совместный список относится ко всем входившим в него партиям, поэтому голоса Объединённого списка видны у ХАДАШ, БАЛАД, ТААЛЬ и РААМ.</p></> },
    { id: "names", title: "Имена и названия", body:
      <p>Имена депутатов на русском и английском взяты с сайта Кнессета. Если там их нет, использованы Викиданные. Названия фракций прежних созывов на русском и английском подготовлены вручную по принятым в русскоязычных СМИ Израиля вариантам. Официальное название на иврите показано всегда. Названия законопроектов — на иврите, как их публикует Кнессет. Фотографии депутатов загружаются с сайта Кнессета.</p> },
    { id: "updates", title: "Обновление", body: <>
      <p>Данные обновляются автоматически: каждую ночь и каждые два часа в дни заседаний пленума (понедельник–среда). При каждом обновлении перечитываются голосования за последние 30 дней, чтобы подхватить исправления источника. Дата последнего обновления указана внизу каждой страницы.</p>
      <p className="small muted">Термины объяснены в {link("/about/glossary", "словаре")}.</p></> },
  ];
}
