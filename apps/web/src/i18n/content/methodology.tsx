// Methodology page text per locale: one array of sections, rendered by app/[lang]/about/methodology.

import type { ReactNode } from "react";
import type { Locale } from "../config";

export type Section = { id: string; title: string; body: ReactNode };

const OK = <a href="https://oknesset.org" target="_blank" rel="noopener">Open Knesset</a>;
const gh = (text: string) => <a href="https://github.com/Alexeyisme/howKnessetVotes" target="_blank" rel="noopener">{text}</a>;

export function methodology(locale: Locale, link: (href: string, text: string) => ReactNode): Section[] {
  if (locale === "en") return [
    { id: "sources", title: "Sources", body: <>
      <p>Every vote, roll-call record, member, faction and bill on the site comes from <strong>official Knesset sources</strong>. Everything else is listed below by where it comes from, and the site labels it where it is shown.</p>
      <p><strong>Official Knesset sources</strong></p>
      <ul>
        <li><strong>Knesset open data (OData v4)</strong>: plenum votes, roll-call records, bills, sponsors, members, factions and membership, government posts (used to determine the {link("/about/methodology#coalition", "coalition")}), the official law classification (used for {link("/about/methodology#topics", "topics")}) and official law summaries. The main source.</li>
        <li><strong>The old Knesset votes service (Votes.svc)</strong>, data up to July 2021: official results and votes missing from the main source, plus flags for votes not counted in the official result.</li>
        <li><strong>The Knesset website</strong>: official member names and faction names in English, Russian and Arabic, and member photos.</li>
        <li><strong>Knesset documents</strong>: bill files with the sponsors&apos; explanatory notes, plenum transcripts (&ldquo;Divrei HaKnesset&rdquo;) and the committee&apos;s version of a bill for the second reading, with the reservations. Bill descriptions, debates and reservations are taken from them.</li>
      </ul>
      <p><strong>Other sources</strong></p>
      <ul>
        <li><strong>Wikidata</strong>: English, Russian and Arabic names for members not covered by the website, and spelling variants for search.</li>
        <li><strong>{OK}</strong> (the Hasadna public knowledge workshop): a table matching Knesset member IDs to the website&apos;s IDs, used to find names and photos. Used with attribution.</li>
      </ul>
      <p><strong>Prepared or computed by the site</strong></p>
      <ul>
        <li><strong>By hand</strong>: parties and the factions they sat as, names of factions from earlier Knessets in other languages, and a few coalition exceptions, each with a reference to its evidence.</li>
        <li><strong>Computed</strong>: results of votes after July 2021 (from roll-call records), coalition and opposition, keyword topics and all measures. The rules are on this page.</li>
        <li><strong>Written by an AI model</strong> (Claude, by Anthropic): translations, summaries of bills&apos; explanatory notes, debates and reservations. They have not been reviewed and are labelled as such; see {link("/about/methodology#ai", "How AI is used")}. Found a mistake? See {link("/about/methodology#corrections", "Mistakes and corrections")}.</li>
      </ul>
      <p className="small muted">Every vote links to its page on the Knesset website. Raw source responses are stored unchanged, so any number can be rechecked.</p></> },
    { id: "records", title: "Roll-call records and “absence”", body: <>
      <p>The open data lists only members who <strong>have a record</strong>: for, against, abstain or &ldquo;present, did not vote&rdquo;. When there is no record, the site <strong>does not count the member as absent</strong>: the source does not say so.</p>
      <p>89 votes have no roll-call records at all. These are votes by show of hands and secret ballots. For them only what was published is shown.</p></> },
    { id: "outcome", title: "Passed or not", body: <>
      <p>For votes up to July 2021 the result comes from official Knesset data. Later official results are not published in the open data, so the site derives them from the roll-call records: passed if &ldquo;for&rdquo; exceeds &ldquo;against&rdquo;; a tie does not pass; a no-confidence motion needs at least 61 votes for. Such results are labelled &ldquo;counted from roll-call records&rdquo;.</p>
      <p>The plenum has no quorum, so a law can pass with a handful of votes when nobody objects. See the {link("/about/glossary#quorum", "glossary")}.</p>
      <p className="small muted">Up to 2021 the roll call matches the official result exactly in 96.5% of votes, and to within two votes in 99.9%. The remaining differences are explained or logged for review. No numbers are adjusted to fit.</p></> },
    { id: "faction", title: "Faction on the day of the vote", body:
      <p>Each vote is attributed to the faction the member belonged to <strong>on the day of the vote</strong>. If the member switched factions that day, the vote is marked ambiguous. Votes whose faction cannot be determined (11 of 2 million) are shown separately.</p> },
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
      <p>Member names in English, Russian and Arabic come from the Knesset website; where it has none, from Wikidata. Names of factions from earlier Knessets in Russian, English and Arabic were prepared by hand. The official Hebrew name is always shown. Bill titles are shown in Hebrew, as published by the Knesset, with an automatic translation under them. Member photos are the official portraits from the Knesset website; we keep a copy and serve it ourselves, because since October 2026 the Knesset website is not reachable from outside Israel.</p> },
    { id: "translation", title: "Translation", body: <>
      <p>The site was written in Russian first; the English, Hebrew and Arabic versions are translations. All the site&apos;s own text — menus, explanations, this page and the glossary, the Russian original included — was written and translated with an AI model (Claude, by Anthropic) under the direction of the site&apos;s author.</p>
      <ul>
        <li><strong>Bill and vote titles.</strong> The Hebrew original is always shown exactly as the Knesset publishes it. In the English, Russian and Arabic versions an automatic translation by the same AI model appears under it, marked &ldquo;AI translation&rdquo;. The official Hebrew name of every member and faction is shown on their pages.</li>
        <li><strong>Bill descriptions.</strong> Where the Knesset publishes an official summary of a law, the bill page shows it, machine-translated. Where there is none (all laws before the 20th Knesset and many bills since), the page of a law whose final vote split the coalition and the opposition, or of a bill voted on since October 2026, shows an automatic summary of the explanatory notes that the sponsors attached to their bill, labelled as their account and linked to the bill&apos;s file. It is written by the same AI model, in Hebrew too, and has not been reviewed. Other bills without an official summary have no description.</li>
        <li><strong>Debates and reservations.</strong> For laws whose final vote split the coalition and the opposition, the bill page summarises what was said in the plenum, from the official transcripts of the sittings where the bill was voted on, and the reservations filed to the second reading, from the committee&apos;s version. Who spoke, their faction, how they voted, and which faction filed how many reservations are taken from the documents themselves; the summaries of the arguments and of the reservations are written by the same AI model and have not been reviewed. The arguments are paraphrases, not quotations, and not an assessment of which side is right; which speakers made each argument is the model&apos;s reading, so check the transcript (linked under every debate) before quoting anyone.</li>
        <li><strong>Members&apos; names</strong> in English, Russian and Arabic are the Knesset website&apos;s official spellings (Wikidata where the website has none).</li>
        <li><strong>Names of factions</strong> in earlier Knessets <strong>and of parties</strong> were prepared by hand from the names used in the media; for the current Knesset the website&apos;s official names are used. <strong>Topic names</strong> are ours.</li>
        <li><strong>The Arabic version is a beta.</strong> It has not yet been reviewed by a native Arabic speaker, so some Knesset terms may be imprecise. The glossary gives the Hebrew term next to each one.</li>
      </ul></> },
    { id: "ai", title: "How AI is used", body: <>
      <p>Some of the text on the site is written by AI models (Claude, by Anthropic). <strong>None of the numbers are</strong>: votes, roll-call records, results, factions, coalition and opposition, topics, measures and the quiz are computed by ordinary code, by the rules on this page, without a model. Only public Knesset documents are sent to the model; nothing about visitors is.</p>
      <p><strong>What the model writes, and from what</strong> (models as of October 2026)</p>
      <ul>
        <li><strong>Translations</strong> of bill and vote titles and of official summaries, from Hebrew into English, Russian and Arabic. Titles: Claude Haiku 4.5 (into Arabic, Claude Sonnet 5), with a fixed glossary of legal terms so that some 22,000 titles are translated consistently. Summaries and all other texts: Claude Sonnet 5. Each Hebrew text is translated once; if the Knesset changes the original, the old translation is no longer shown and the new text is translated afresh.</li>
        <li><strong>Bill descriptions</strong> where there is no official summary. The model (Claude Sonnet 5) reads the explanatory notes in the sponsors&apos; bill file and writes two to four sentences in Hebrew: what the bill changes and the reasons the sponsors give, attributed to them (&ldquo;according to the sponsors&rdquo;). The description is then translated like any other text.</li>
        <li><strong>Debates.</strong> The code itself cuts the debate on the bill out of the transcripts of every sitting where it was voted on, and lists who spoke, at which readings and how often, without a model. The model (Claude Sonnet 5) gets the numbered speeches and writes a neutral summary and up to five arguments for and five against, each pointing to the speeches it comes from; the members shown under an argument are the authors of those speeches. Cards show each side&apos;s argument made in the most speeches. When a debate is too long for one request, every speech is first shortened to the same length, and the page says so.</li>
        <li><strong>Reservations.</strong> The model (Claude Sonnet 5) reads the reservations section of the committee&apos;s version, says which numbered reservations belong to which member or group, and writes a one-sentence gist of each.</li>
      </ul>
      <p><strong>Rules the model is given.</strong> Use only the document in front of it: no outside facts, no judgement of which side is right, no loaded words, numbers exactly as in the source, only the Gregorian date. A speech&apos;s side is what it argues, not the speaker&apos;s party. Read the speeches of both sides before writing either list. The model works without extended reasoning, and its answer must follow a fixed structure. The prompts and the checks are in the site&apos;s {gh("open source code")}.</p>
      <p><strong>Automatic checks.</strong> A text that fails them is not published; it is logged as a problem for the author to look at.</p>
      <ul>
        <li>A translation keeps every number of the original, has no Hebrew letters left and is not suspiciously long.</li>
        <li>A bill description is Hebrew prose of reasonable length ending with a complete sentence; every number in it appears in the notes (when the notes can be read as text).</li>
        <li>A debate summary and its arguments are Hebrew sentences of reasonable length; every argument points to speeches that exist; every number appears in the speeches or the bill title.</li>
        <li>The reservation numbers given to proposers are exactly the numbered reservations printed in the document, with no gap, overlap or extra, and every member named appears in the text. Where the document has no readable numbers this cannot be checked, and the page says so.</li>
      </ul>
      <p><strong>What the checks cannot catch.</strong> A fluent text with the right numbers can still miss the point, put an argument on the wrong side or credit it to the wrong speaker. No person reviews these texts before they are published. That is why each one is marked &ldquo;AI summary&rdquo; or &ldquo;AI translation&rdquo; where it is shown, links to the document it was written from and has a link to report a mistake (see {link("/about/methodology#corrections", "Mistakes and corrections")}). Translations keep the Hebrew original one click away.</p></> },
    { id: "corrections", title: "Mistakes and corrections", body: <>
      <p>Much of the text on the site was written or translated by an AI model and has not been reviewed by a person, so it may contain mistakes: an inaccurate translation, a wrong number, an argument summarised badly or put on the wrong side. Vote counts, roll-call records and factions come from official data, but they can be wrong too, in the source or in our processing.</p>
      <p><strong>Your help is welcome.</strong> Next to a translated title or summary there is a &ldquo;suggest a correction&rdquo; link. For anything else, including the Hebrew summaries and the arguments of the sides, {link("/suggest", "write to the author")}: the link is under every summary and at the bottom of every page. The author reads every message and checks it before anything on the site changes; leave a contact if you would like an answer.</p></> },
    { id: "updates", title: "Updates", body: <>
      <p>Data is updated automatically: every night, and every two hours on plenum days (Monday–Wednesday). Each update rereads the last 30 days of votes to pick up source corrections. The date of the latest update is at the bottom of every page.</p>
      <p className="small muted">Terms are explained in the {link("/about/glossary", "glossary")}.</p></> },
  ];
  if (locale === "ar") return [
    { id: "sources", title: "المصادر", body: <>
      <p>كل تصويت وسجل اسمي وعضو كنيست وكتلة واقتراح قانون في الموقع مأخوذ من <strong>مصادر الكنيست الرسمية</strong>. كل ما عدا ذلك مذكور أدناه حسب مصدره، ويوسمه الموقع حيث يُعرض.</p>
      <p><strong>مصادر الكنيست الرسمية</strong></p>
      <ul>
        <li><strong>المعطيات المفتوحة للكنيست (OData v4)</strong>: تصويتات الهيئة العامة، السجلات الاسمية، اقتراحات القوانين، المبادرون، أعضاء الكنيست، الكتل والعضوية فيها، المناصب الحكومية (لتحديد {link("/about/methodology#coalition", "الائتلاف")})، التصنيف الرسمي للقوانين (لـ{link("/about/methodology#topics", "المواضيع")}) والملخصات الرسمية للقوانين. المصدر الرئيسي.</li>
        <li><strong>خدمة التصويتات القديمة للكنيست (Votes.svc)</strong>، معطيات حتى تموز/يوليو 2021: النتائج الرسمية وتصويتات غير موجودة في المصدر الرئيسي، وإشارات إلى أصوات لم تُحتسب في النتيجة الرسمية.</li>
        <li><strong>موقع الكنيست</strong>: الأسماء الرسمية لأعضاء الكنيست وللكتل بالإنجليزية والروسية والعربية، وصور أعضاء الكنيست.</li>
        <li><strong>وثائق الكنيست</strong>: ملفات اقتراحات القوانين مع الشروح التي أرفقها المبادرون، محاضر جلسات الهيئة العامة («دفري هكنيست») وصيغة اللجنة لاقتراح القانون للقراءة الثانية مع التحفظات. منها تؤخذ أوصاف الاقتراحات والنقاشات والتحفظات.</li>
      </ul>
      <p><strong>مصادر أخرى</strong></p>
      <ul>
        <li><strong>ويكي بيانات</strong>: أسماء بالإنجليزية والروسية والعربية لأعضاء كنيست لا يغطيهم الموقع، وصيغ كتابة بديلة للبحث.</li>
        <li><strong>{OK}</strong> (ورشة المعرفة العامة «هسدنا»): جدول مطابقة بين معرّفات أعضاء الكنيست ومعرّفات الموقع، لإيجاد الأسماء والصور. يُستخدم مع ذكر المصدر.</li>
      </ul>
      <p><strong>ما أعدّه الموقع أو حسبه</strong></p>
      <ul>
        <li><strong>يدويًا</strong>: الأحزاب والكتل التي مثّلتها، أسماء كتل الدورات السابقة بلغات أخرى، وبعض استثناءات الائتلاف، ولكل منها إشارة إلى الدليل.</li>
        <li><strong>بالحساب</strong>: نتائج التصويتات بعد تموز/يوليو 2021 (من السجلات الاسمية)، الائتلاف والمعارضة، المواضيع حسب الكلمات المفتاحية وكل المؤشرات. القواعد مشروحة في هذه الصفحة.</li>
        <li><strong>بنموذج ذكاء اصطناعي</strong> (Claude من شركة Anthropic): الترجمات وتلخيص الشروح المرفقة باقتراحات القوانين والنقاشات والتحفظات. لم تُراجَع، وهي موسومة بذلك؛ انظر {link("/about/methodology#ai", "كيف يُستخدم الذكاء الاصطناعي")}. وجدتم خطأ؟ انظر {link("/about/methodology#corrections", "الأخطاء والتصحيحات")}.</li>
      </ul>
      <p className="small muted">لكل تصويت رابط إلى صفحته في موقع الكنيست. تُحفظ ردود المصادر الأصلية دون تغيير، بحيث يمكن التحقق من أي رقم من جديد.</p></> },
    { id: "records", title: "السجلات الاسمية و«الغياب»", body: <>
      <p>تذكر المعطيات المفتوحة فقط أعضاء الكنيست <strong>الذين لهم سجل</strong>: مع، ضد، امتنع أو «حاضر، لم يصوّت». عندما لا يوجد سجل، <strong>لا يعتبر الموقع العضو غائبًا</strong>: المصدر لا يقول ذلك.</p>
      <p>لـ89 تصويتًا لا توجد سجلات اسمية إطلاقًا. هذه تصويتات برفع الأيدي وتصويتات سرية. يُعرض لها فقط ما نُشر.</p></> },
    { id: "outcome", title: "أُقرّ أم لا", body: <>
      <p>في التصويتات حتى تموز/يوليو 2021 تؤخذ النتيجة من المعطيات الرسمية للكنيست. النتائج اللاحقة لا تُنشر في المعطيات المفتوحة، لذا يحسبها الموقع من السجلات الاسمية: يُقرّ إذا زاد عدد «مع» على «ضد»؛ التعادل لا يُقرّ؛ اقتراح حجب الثقة يحتاج إلى 61 صوتًا مؤيدًا على الأقل. تُعلَّم هذه النتيجة بعبارة «محسوبة من السجلات الاسمية».</p>
      <p>لا يوجد نصاب في الهيئة العامة، لذا قد يُقرّ قانون بأصوات قليلة حين لا يعترض أحد. انظر {link("/about/glossary#quorum", "قاموس المصطلحات")}.</p>
      <p className="small muted">حتى 2021 تطابق القائمة الاسمية النتيجة الرسمية تمامًا في 96.5% من التصويتات، وبفارق صوتين على الأكثر في 99.9%. الفروق الباقية مفسّرة أو مسجّلة للمراجعة. لا توجد أرقام معدّلة لتتطابق.</p></> },
    { id: "faction", title: "الكتلة يوم التصويت", body:
      <p>يُنسب كل صوت إلى الكتلة التي انتمى إليها العضو <strong>يوم التصويت</strong>. إذا انتقل العضو إلى كتلة أخرى في اليوم نفسه، يُعلَّم الصوت بأنه غير محسوم. الأصوات التي لا يمكن تحديد كتلتها (11 من أصل مليونين) معروضة بشكل منفصل.</p> },
    { id: "metrics", title: "المؤشرات", body:
      <dl className="glossary">
        <div className="glossary-item"><dt><strong>المشاركة في التصويت بالأسماء</strong></dt>
          <dd>أصوات مع وضد وامتنع، مقسومة على عدد التصويتات بالأسماء خلال فترة العضوية. هذه <strong>ليست نسبة حضور</strong>: قد يكون العضو في الكنيست ولم يصوّت.</dd></div>
        <div className="glossary-item"><dt><strong>التصويت خلافًا لأغلبية الحزب</strong></dt>
          <dd>صوت العضو يختلف عن خيار الأغلبية المطلقة من أعضاء كتلته <em>الآخرين</em> الذين صوّتوا (اثنان على الأقل). المقام هو التصويتات التي وُجدت فيها مثل هذه الأغلبية. هذا <strong>لا يثبت خرق الانضباط الحزبي</strong>: ربما سمحت الكتلة بتصويت حر.</dd></div>
        <div className="glossary-item"><dt><strong>تماسك الحزب</strong></dt>
          <dd>نسبة أصوات أعضاء الكتلة التي طابقت الخيار الأكثر شيوعًا في الكتلة في التصويت نفسه، على مجمل التصويتات.</dd></div>
        <div className="glossary-item"><dt><strong>كيف صوّتت الأحزاب حسب الموضوع</strong></dt>
          <dd>تُحتسب فقط التصويتات على اقتراح القانون كاملًا (افتراضيًا في القراءة الثالثة). التحفّظات والتصويتات الإجرائية مستثناة. «أغلبية مع» تعني أن أكثر من نصف أعضاء الكتلة المصوّتين اختاروا «مع».</dd></div>
      </dl> },
    { id: "topics", title: "المواضيع", body:
      <p>تأتي المواضيع من مصدرين. الأول هو <strong>التصنيف الرسمي لقوانين الكنيست</strong> (51 فئة): يحصل اقتراح القانون على فئات القانون الذي يسنّه أو يعدّله، إذا ورد اسم ذلك القانون في عنوانه. الثاني هو <strong>كلمات مفتاحية</strong> في العنوان العبري لاقتراح القانون. إذا كانت هناك أكثر من ثلاث فئات رسمية (مثلًا في قانون التسويات) فلا تُستخدم. حيث يوجد المصدران، يتفقان في 91% من اقتراحات القوانين. لم يراجع محرّر المواضيع بعد، لذا قد توجد أخطاء. تُظهر صفحة اقتراح القانون مصدر كل موضوع. يرث التصويت كل مواضيع اقتراح القانون، حتى لو تعلّق ببند واحد.</p> },
    { id: "coalition", title: "الائتلاف والمعارضة والأحزاب", body: <>
      <p>الانتماء إلى الائتلاف <strong>مستخلص من معطيات رسمية</strong>: تنشر الكنيست قائمة كل الوزراء ونواب الوزراء مع رقم الحكومة والتواريخ. تكون الكتلة في الائتلاف في تاريخ يشغل فيه أحد أعضائها منصبًا في حكومة ذلك اليوم، وإلا فهي في المعارضة. بين الانتخابات وأداء الحكومة التالية اليمين لا يوجد ائتلاف، والموقع يذكر ذلك. الوزير الذي تنازل عن مقعده وفق «القانون النرويجي» يبقى محسوبًا على كتلته.</p>
      <p>صُحّحت بعض الاستثناءات المعروفة يدويًا ووُسمت بذلك: حزب دعم الائتلاف دون حقيبة وزارية (الموحدة، 2021–2022)، حزب استقال وزراؤه وبقي في الائتلاف (شاس، منذ تموز/يوليو 2025)، وحالات مشابهة. يكون التصويت «خلافيًا» عندما تصوّت أغلبية الائتلاف وأغلبية المعارضة بشكل مختلف.</p>
      <p><strong>الحزب</strong> يربط الكتل التي مثّلته في كل دورة كنيست (أُعدّ يدويًا). القائمة المشتركة تُحتسب لكل حزب فيها، لذا تظهر تصويتات القائمة المشتركة تحت الجبهة والتجمع والعربية للتغيير والموحدة.</p></> },
    { id: "names", title: "الأسماء", body:
      <p>أسماء أعضاء الكنيست بالعربية والإنجليزية والروسية مأخوذة من موقع الكنيست؛ وحيث لا توجد، من ويكي بيانات. أسماء كتل الدورات السابقة بالعربية أُعدّت يدويًا وفق الأسماء المتداولة في وسائل الإعلام العربية في البلاد. الاسم العبري الرسمي معروض دائمًا. عناوين اقتراحات القوانين بالعبرية، كما تنشرها الكنيست، وتحتها ترجمة آلية. صور أعضاء الكنيست هي الصور الرسمية من موقع الكنيست؛ نحتفظ بنسخة منها ونعرضها بأنفسنا، لأن موقع الكنيست لم يعد متاحًا من خارج إسرائيل منذ تشرين الأول/أكتوبر 2026.</p> },
    { id: "translation", title: "الترجمة", body: <>
      <p><strong>النسخة العربية تجريبية (بيتا).</strong> لم يراجعها بعد متحدث أصلي بالعربية، لذا قد تكون بعض مصطلحات الكنيست غير دقيقة. يورد قاموس المصطلحات المصطلح العبري بجانب كل مصطلح.</p>
      <p>كُتب الموقع أولًا بالروسية؛ النسخ العربية والعبرية والإنجليزية ترجمات. كل نصوص الموقع نفسه — القوائم والشروح وهذه الصفحة وقاموس المصطلحات، بما فيها الأصل الروسي — كُتبت وتُرجمت بمساعدة نموذج ذكاء اصطناعي (Claude من شركة Anthropic) بتوجيه من مؤلف الموقع.</p>
      <ul>
        <li><strong>عناوين اقتراحات القوانين والتصويتات.</strong> يُعرض الأصل العبري دائمًا كما تنشره الكنيست. وفي النسخ العربية والإنجليزية والروسية تظهر تحته ترجمة آلية بنموذج الذكاء الاصطناعي نفسه، موسومة «ترجمة بالذكاء الاصطناعي». والاسم العبري الرسمي لكل عضو كنيست وكتلة موجود في صفحته.</li>
        <li><strong>وصف اقتراحات القوانين.</strong> حيث تنشر الكنيست ملخصًا رسميًا للقانون، تعرضه صفحة الاقتراح مترجمًا آليًا. وحيث لا يوجد ملخص (كل القوانين قبل الكنيست العشرين وكثير من الاقتراحات بعدها)، تعرض صفحة القانون الذي انقسم فيه الائتلاف والمعارضة في التصويت النهائي، أو الاقتراح الذي جرى التصويت عليه منذ تشرين الأول/أكتوبر 2026، تلخيصًا آليًا للشروح التي أرفقها المبادرون باقتراحهم، مع الإشارة إلى أنها روايتهم ورابط إلى ملف الاقتراح. يكتبه نموذج الذكاء الاصطناعي نفسه، بالعبرية أيضًا، ولم يُراجَع. الاقتراحات الأخرى التي لا ملخص رسميًا لها بلا وصف.</li>
        <li><strong>النقاشات والتحفظات.</strong> للقوانين التي انقسم فيها الائتلاف والمعارضة في التصويت النهائي، تلخّص صفحة الاقتراح ما قيل في الهيئة العامة، من المحاضر الرسمية للجلسات التي جرى فيها التصويت على الاقتراح، والتحفظات المقدّمة للقراءة الثانية، من صيغة اللجنة. من تحدّث وكتلته وكيف صوّت، وأي كتلة قدّمت كم تحفظًا، مأخوذ من الوثائق نفسها؛ أما تلخيص الحجج والتحفظات فيكتبه نموذج الذكاء الاصطناعي نفسه ولم يُراجَع. الحجج معاد صياغتها وليست اقتباسات ولا تقييمًا لأي طرف على حق؛ ومن طرح كل حجة هو قراءة النموذج، لذا راجعوا المحضر (رابطه تحت كل نقاش) قبل الاقتباس عن أحد.</li>
        <li><strong>أسماء أعضاء الكنيست</strong> بالعربية هي الكتابة الرسمية في موقع الكنيست (ويكي بيانات حيث لا توجد في الموقع).</li>
        <li><strong>أسماء الكتل</strong> في الدورات السابقة <strong>وأسماء الأحزاب</strong> أُعدّت يدويًا وفق الأسماء المتداولة في الإعلام؛ للكنيست الحالية تُستخدم الأسماء الرسمية من موقع الكنيست. <strong>أسماء المواضيع</strong> من وضعنا.</li>
      </ul></> },
    { id: "ai", title: "كيف يُستخدم الذكاء الاصطناعي", body: <>
      <p>بعض النصوص في الموقع تكتبها نماذج ذكاء اصطناعي (Claude من شركة Anthropic). <strong>أما الأرقام فلا</strong>: التصويتات والسجلات الاسمية والنتائج والكتل والائتلاف والمعارضة والمواضيع والمؤشرات والاختبار تُحسب بشيفرة عادية وفق القواعد المذكورة في هذه الصفحة، من دون نموذج. لا يُرسَل إلى النموذج سوى وثائق الكنيست العلنية، ولا شيء عن زوار الموقع.</p>
      <p><strong>ماذا يكتب النموذج، ومن أي مصدر</strong> (النماذج حتى أكتوبر 2026)</p>
      <ul>
        <li><strong>الترجمات</strong>: عناوين اقتراحات القوانين والتصويتات والملخصات الرسمية، من العبرية إلى العربية والإنجليزية والروسية. العناوين: Claude Haiku 4.5 (إلى العربية: Claude Sonnet 5)، مع قاموس ثابت للمصطلحات القانونية لتُترجم نحو 22,000 عنوان بصورة موحّدة. الملخصات وسائر النصوص: Claude Sonnet 5. يُترجم كل نص عبري مرة واحدة؛ وإذا غيّرت الكنيست الأصل، لا تُعرض الترجمة القديمة بعد ذلك ويُترجم النص الجديد من جديد.</li>
        <li><strong>أوصاف اقتراحات القوانين</strong> التي لا ملخص رسميًا لها. يقرأ النموذج (Claude Sonnet 5) الشروح في ملف اقتراح القانون ويكتب بالعبرية من جملتين إلى أربع: ما الذي يغيّره الاقتراح، والأسباب التي يقدّمها مقدّموه، منسوبة إليهم («بحسب مقدّمي الاقتراح»). ثم يُترجم الوصف كأي نص آخر.</li>
        <li><strong>النقاشات.</strong> تقتطع الشيفرة نفسها النقاش حول اقتراح القانون من محاضر كل الجلسات التي جرى التصويت عليه فيها، وتعدّ من تحدّث وفي أي قراءات وكم مرة، من دون نموذج. يتلقى النموذج (Claude Sonnet 5) الخطابات مرقّمة ويكتب ملخصًا محايدًا وحتى خمس حجج مؤيدة وخمس معارضة، كل منها مع إحالة إلى الخطابات التي أُخذت منها؛ وأعضاء الكنيست المذكورون تحت الحجة هم أصحاب تلك الخطابات. تعرض البطاقات حجة كل طرف التي وردت في أكبر عدد من الخطابات. وإذا كان النقاش أطول من أن يتسع له طلب واحد، يُختصر كل خطاب أولًا إلى الطول نفسه، وتذكر الصفحة ذلك.</li>
        <li><strong>التحفظات.</strong> يقرأ النموذج (Claude Sonnet 5) قسم التحفظات في صيغة اللجنة، ويحدد أي التحفظات المرقّمة تعود إلى أي عضو أو مجموعة، ويكتب خلاصة كل منها في جملة واحدة.</li>
      </ul>
      <p><strong>القواعد المعطاة للنموذج.</strong> الاعتماد على الوثيقة المعروضة فقط: لا حقائق من خارجها، ولا حكم على أي طرف محق، ولا كلمات مشحونة، والأرقام كما في المصدر تمامًا، والتاريخ الميلادي فقط. جانب الخطاب يحدده ما يدافع عنه، لا حزب المتحدث. قراءة خطابات الطرفين قبل كتابة أي من القائمتين. يعمل النموذج من دون تفكير موسّع، ويجب أن يلتزم جوابه ببنية ثابتة. التعليمات والفحوص موجودة في {gh("الشيفرة المصدرية المفتوحة")} للموقع.</p>
      <p><strong>فحوص آلية.</strong> النص الذي لا يجتازها لا يُنشر، بل يُسجَّل كمشكلة يراجعها مؤلف الموقع.</p>
      <ul>
        <li>تحتفظ الترجمة بكل أرقام الأصل، ولا يبقى فيها حرف عبري، وليست طويلة على نحو مريب.</li>
        <li>وصف اقتراح القانون نص عبري متصل بطول معقول ينتهي بجملة كاملة؛ وكل رقم فيه موجود في الشروح (حين يمكن قراءتها كنص).</li>
        <li>ملخص النقاش والحجج جمل عبرية بطول معقول؛ وكل حجة تحيل إلى خطابات موجودة؛ وكل رقم موجود في الخطابات أو في عنوان اقتراح القانون.</li>
        <li>أرقام التحفظات المنسوبة إلى مقدّميها هي بالضبط التحفظات المرقّمة المطبوعة في الوثيقة، بلا فجوات أو تداخل أو زيادات، وكل عضو مذكور موجود في النص. وحين لا يمكن قراءة الأرقام في الوثيقة كنص، يتعذر هذا الفحص، وتذكر الصفحة ذلك.</li>
      </ul>
      <p><strong>ما لا تكشفه الفحوص.</strong> قد يُغفل نص سلس بأرقام صحيحة جوهر المسألة، أو يضع حجة في الجانب الخطأ، أو ينسبها إلى متحدث آخر. لا يراجع أي شخص هذه النصوص قبل نشرها. لذلك يُوسم كل منها بـ«ملخص بالذكاء الاصطناعي» أو «ترجمة بالذكاء الاصطناعي» حيث يُعرض، ويرتبط بالوثيقة التي كُتب منها، وبجانبه رابط للإبلاغ عن خطأ (انظر {link("/about/methodology#corrections", "الأخطاء والتصحيحات")}). وللترجمات، الأصل العبري على بُعد نقرة.</p></> },
    { id: "corrections", title: "الأخطاء والتصحيحات", body: <>
      <p>كثير من نصوص الموقع كتبه أو ترجمه نموذج ذكاء اصطناعي ولم يراجعه إنسان، لذا قد يحتوي على أخطاء: ترجمة غير دقيقة، أو رقم خاطئ، أو حجة لُخّصت بشكل سيئ أو نُسبت إلى الجانب الخطأ. نتائج التصويت والسجلات الاسمية والكتل مأخوذة من البيانات الرسمية، لكنها قد تكون خاطئة أيضًا، في المصدر أو في معالجتنا.</p>
      <p><strong>يسعدنا تعاونكم.</strong> بجانب كل عنوان أو ملخص مترجم رابط «اقترح تصحيحًا». ولأي شيء آخر، بما في ذلك الملخصات العبرية وحجج الجانبين، {link("/suggest", "راسلوا مؤلف الموقع")}: الرابط موجود تحت كل ملخص وأسفل كل صفحة. يقرأ المؤلف كل رسالة ويتحقق منها قبل أن يتغيّر أي شيء في الموقع؛ اتركوا وسيلة تواصل إن أردتم ردًا.</p></> },
    { id: "updates", title: "التحديث", body: <>
      <p>تُحدَّث المعطيات تلقائيًا: كل ليلة، وكل ساعتين في أيام جلسات الهيئة العامة (الاثنين–الأربعاء). في كل تحديث تُقرأ من جديد تصويتات آخر 30 يومًا لالتقاط تصحيحات المصدر. تاريخ آخر تحديث مذكور أسفل كل صفحة.</p>
      <p className="small muted">المصطلحات مشروحة في {link("/about/glossary", "قاموس المصطلحات")}.</p></> },
  ];
  if (locale === "he") return [
    { id: "sources", title: "מקורות", body: <>
      <p>כל הצבעה, רישום שמי, חבר כנסת, סיעה והצעת חוק באתר לקוחים <strong>ממקורות רשמיים של הכנסת</strong>. כל השאר מפורט להלן לפי מקורו, והאתר מסמן אותו במקום שבו הוא מוצג.</p>
      <p><strong>מקורות רשמיים של הכנסת</strong></p>
      <ul>
        <li><strong>המידע הפתוח של הכנסת (OData v4)</strong>: הצבעות במליאה, רישומים שמיים, הצעות חוק, יוזמים, חברי כנסת, סיעות וחברות בהן, תפקידים בממשלה (לקביעת {link("/about/methodology#coalition", "הקואליציה")}), הסיווג הרשמי של החוקים (ל{link("/about/methodology#topics", "נושאים")}) ותקצירי חוקים רשמיים. המקור העיקרי.</li>
        <li><strong>שירות ההצבעות הישן של הכנסת (Votes.svc)</strong>, נתונים עד יולי 2021: תוצאות רשמיות והצבעות שחסרות במקור העיקרי, וסימון קולות שלא נכללו בתוצאה הרשמית.</li>
        <li><strong>אתר הכנסת</strong>: השמות הרשמיים של חברי הכנסת ושל הסיעות באנגלית, ברוסית ובערבית, ותמונות חברי הכנסת.</li>
        <li><strong>מסמכי הכנסת</strong>: קובצי הצעות החוק עם דברי ההסבר של היוזמים, פרוטוקולי המליאה (״דברי הכנסת״) ונוסח הוועדה לקריאה השנייה עם ההסתייגויות. מהם נלקחים תיאורי ההצעות, הדיונים וההסתייגויות.</li>
      </ul>
      <p><strong>מקורות אחרים</strong></p>
      <ul>
        <li><strong>ויקינתונים</strong>: שמות באנגלית, ברוסית ובערבית לחברי כנסת שאינם באתר, וגרסאות כתיב לחיפוש.</li>
        <li><strong><a href="https://oknesset.org" target="_blank" rel="noopener">כנסת פתוחה</a></strong> (הסדנא לידע ציבורי): טבלת התאמה בין מזהי חברי הכנסת למזהי האתר, לאיתור שמות ותמונות. בשימוש עם ציון המקור.</li>
      </ul>
      <p><strong>מה שהאתר הכין או חישב</strong></p>
      <ul>
        <li><strong>ידנית</strong>: המפלגות והסיעות שבהן ישבו, שמות סיעות של כנסות קודמות בשפות אחרות, וכמה חריגים בקואליציה, כל אחד עם הפניה לראיה.</li>
        <li><strong>בחישוב</strong>: תוצאות הצבעות אחרי יולי 2021 (מהרישומים השמיים), קואליציה ואופוזיציה, נושאים לפי מילות מפתח וכל המדדים. הכללים מפורטים בדף זה.</li>
        <li><strong>במודל בינה מלאכותית</strong> (Claude של Anthropic): תרגומים ותקצירים של דברי ההסבר, הדיונים וההסתייגויות. הם לא נבדקו ומסומנים ככאלה; ראו {link("/about/methodology#ai", "איך משתמשים בבינה מלאכותית")}. מצאתם טעות? ראו {link("/about/methodology#corrections", "טעויות ותיקונים")}.</li>
      </ul>
      <p className="small muted">לכל הצבעה יש קישור לדף שלה באתר הכנסת. התשובות הגולמיות של המקורות נשמרות ללא שינוי, כך שאפשר לבדוק מחדש כל מספר.</p></> },
    { id: "records", title: "רישומים שמיים ו״היעדרות״", body: <>
      <p>במידע הפתוח מופיעים רק חברי כנסת <strong>שיש להם רישום</strong>: בעד, נגד, נמנע או ״נוכח, לא הצביע״. כשאין רישום, האתר <strong>אינו מחשיב את חבר הכנסת כנעדר</strong>: המקור אינו אומר זאת.</p>
      <p>ל-89 הצבעות אין רישומים שמיים כלל. אלה הצבעות בהרמת ידיים והצבעות חשאיות. עבורן מוצג רק מה שפורסם.</p></> },
    { id: "outcome", title: "התקבל או לא", body: <>
      <p>בהצבעות עד יולי 2021 התוצאה נלקחת מהנתונים הרשמיים של הכנסת. תוצאות מאוחרות יותר אינן מתפרסמות במידע הפתוח, ולכן האתר מחשב אותן מהרישומים השמיים: התקבל אם ״בעד״ גדול מ״נגד״; תיקו אינו מתקבל; הצעת אי-אמון דורשת לפחות 61 קולות בעד. תוצאה כזו מסומנת ״לפי הרישומים השמיים״.</p>
      <p>במליאה אין מניין חוקי, ולכן חוק יכול לעבור בקולות מעטים כשאין מתנגדים. ראו {link("/about/glossary#quorum", "במילון המונחים")}.</p>
      <p className="small muted">עד 2021 הרשימה השמית תואמת את התוצאה הרשמית במדויק ב-96.5% מההצבעות, ובהפרש של עד שני קולות ב-99.9%. שאר הפערים מוסברים או נרשמו לבדיקה. אין מספרים מותאמים.</p></> },
    { id: "faction", title: "הסיעה ביום ההצבעה", body:
      <p>כל קול משויך לסיעה שחבר הכנסת השתייך אליה <strong>ביום ההצבעה</strong>. אם עבר סיעה באותו יום, הקול מסומן כלא חד-משמעי. קולות שלא ניתן לקבוע את סיעתם (11 מתוך 2 מיליון) מוצגים בנפרד.</p> },
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
      <p>שמות חברי הכנסת באנגלית, ברוסית ובערבית לקוחים מאתר הכנסת; היכן שאין — מוויקינתונים. שמות הסיעות של כנסות קודמות ברוסית, באנגלית ובערבית הוכנו ידנית. השם הרשמי בעברית מוצג תמיד. תמונות חברי הכנסת הן התמונות הרשמיות מאתר הכנסת; אנו שומרים עותק ומציגים אותו בעצמנו, כי מאוקטובר 2026 אתר הכנסת אינו נגיש מחוץ לישראל.</p> },
    { id: "translation", title: "תרגום", body: <>
      <p>האתר נכתב תחילה ברוסית; הגרסאות בעברית, באנגלית ובערבית הן תרגומים. כל הטקסט של האתר עצמו — תפריטים, הסברים, דף זה ומילון המונחים, כולל המקור הרוסי — נכתב ותורגם בעזרת מודל בינה מלאכותית (Claude של Anthropic) בהנחיית מחבר האתר.</p>
      <ul>
        <li><strong>שמות הצעות החוק וההצבעות.</strong> המקור העברי מוצג תמיד כפי שהכנסת מפרסמת אותו. בגרסאות האנגלית, הרוסית והערבית מופיע מתחתיו תרגום אוטומטי של אותו מודל בינה מלאכותית, מסומן „תרגום AI“. השם העברי הרשמי של כל חבר כנסת וסיעה מוצג בדף שלהם.</li>
        <li><strong>תיאור הצעות החוק.</strong> היכן שהכנסת מפרסמת תקציר רשמי של החוק, דף ההצעה מציג אותו בתרגום מכונה. היכן שאין תקציר (כל החוקים לפני הכנסת העשרים והצעות רבות מאז), הדף של חוק שבהצבעה הסופית עליו נחלקו הקואליציה והאופוזיציה, או של הצעה שהוצבעה מאז אוקטובר 2026, מציג תקציר אוטומטי של דברי ההסבר שצירפו היוזמים להצעתם, עם ציון שזו עמדתם וקישור לקובץ ההצעה. הוא נכתב באותו מודל בינה מלאכותית, גם בעברית, ולא נבדק. להצעות אחרות שאין להן תקציר רשמי אין תיאור.</li>
        <li><strong>דיונים והסתייגויות.</strong> בחוקים שבהצבעה הסופית עליהם נחלקו הקואליציה והאופוזיציה, דף ההצעה מסכם מה נאמר במליאה, לפי הפרוטוקולים הרשמיים של הישיבות שבהן הצביעו על ההצעה, ואת ההסתייגויות שהוגשו לקריאה השנייה, לפי נוסח הוועדה. מי דיבר, מאיזו סיעה, איך הצביע, ואיזו סיעה הגישה כמה הסתייגויות – נלקחים מהמסמכים עצמם; את תקציר הטיעונים וההסתייגויות כותב אותו מודל בינה מלאכותית, והוא לא נבדק. הטיעונים מנוסחים מחדש ואינם ציטוטים, ואין בהם הערכה איזה צד צודק; מי העלה כל טיעון הוא קריאת המודל, ולכן לפני שמצטטים מישהו בדקו בפרוטוקול (הקישור מתחת לכל דיון).</li>
        <li><strong>שמות חברי הכנסת</strong> באנגלית, ברוסית ובערבית הם האיות הרשמי של אתר הכנסת (ויקינתונים היכן שאין באתר).</li>
        <li><strong>שמות הסיעות</strong> בכנסות קודמות <strong>ושמות המפלגות</strong> הוכנו ידנית לפי השמות המקובלים בתקשורת; בכנסת הנוכחית משמשים השמות הרשמיים מאתר הכנסת. <strong>שמות הנושאים</strong> הם שלנו.</li>
        <li><strong>הגרסה הערבית היא גרסת בטא.</strong> מי שהערבית שפת אמו עוד לא בדק אותה, ולכן ייתכן שחלק ממונחי הכנסת אינם מדויקים. במילון המונחים מופיע המונח העברי לצד כל מונח.</li>
      </ul></> },
    { id: "ai", title: "איך משתמשים בבינה מלאכותית", body: <>
      <p>חלק מהטקסטים באתר נכתבים בידי מודלים של בינה מלאכותית (Claude של Anthropic). <strong>המספרים — לא</strong>: ההצבעות, רישומי ההצבעה השמית, התוצאות, הסיעות, הקואליציה והאופוזיציה, הנושאים, המדדים והשאלון מחושבים בקוד רגיל, לפי הכללים שבדף זה, בלי מודל. למודל נשלחים רק מסמכים פומביים של הכנסת; שום דבר על המבקרים באתר.</p>
      <p><strong>מה המודל כותב, ועל סמך מה</strong> (המודלים נכון לאוקטובר 2026)</p>
      <ul>
        <li><strong>תרגומים</strong> של שמות הצעות החוק וההצבעות ושל התקצירים הרשמיים מעברית לאנגלית, לרוסית ולערבית. שמות: Claude Haiku 4.5 (לערבית: Claude Sonnet 5), עם מילון קבוע של מונחים משפטיים, כדי שכ־22,000 שמות יתורגמו באופן אחיד. תקצירים וכל שאר הטקסטים: Claude Sonnet 5. כל טקסט בעברית מתורגם פעם אחת; אם הכנסת משנה את המקור, התרגום הישן כבר לא מוצג והטקסט החדש מתורגם מחדש.</li>
        <li><strong>תיאורי הצעות חוק</strong> שאין להן תקציר רשמי. המודל (Claude Sonnet 5) קורא את דברי ההסבר בקובץ הצעת החוק וכותב בעברית שניים עד ארבעה משפטים: מה ההצעה משנה ואילו נימוקים מביאים היוזמים, בשמם („לדברי המציעים“). לאחר מכן התיאור מתורגם כמו כל טקסט אחר.</li>
        <li><strong>דיונים.</strong> הקוד עצמו חותך את הדיון בהצעת החוק מתוך הפרוטוקולים של כל הישיבות שבהן הצביעו עליה, ומונה מי דיבר, באילו קריאות וכמה פעמים — בלי מודל. המודל (Claude Sonnet 5) מקבל את הנאומים ממוספרים וכותב תקציר ניטרלי ועד חמישה טיעונים בעד וחמישה נגד, כל אחד עם הפניה לנאומים שממנו נלקח; חברי הכנסת שמופיעים תחת טיעון הם מי שנשאו את הנאומים האלה. בכרטיסים מוצג הטיעון של כל צד שעלה במספר הנאומים הגדול ביותר. כשדיון ארוך מדי לבקשה אחת, כל נאום מקוצר קודם לאותו אורך, והדף מציין זאת.</li>
        <li><strong>הסתייגויות.</strong> המודל (Claude Sonnet 5) קורא את פרק ההסתייגויות בנוסח הוועדה, קובע אילו הסתייגויות ממוספרות שייכות לאיזה חבר כנסת או קבוצה, וכותב את עיקרה של כל אחת במשפט אחד.</li>
      </ul>
      <p><strong>הכללים שהמודל מקבל.</strong> להשתמש רק במסמך שלפניו: בלי עובדות מבחוץ, בלי הכרעה איזה צד צודק, בלי מילים טעונות, מספרים בדיוק כמו במקור, ורק התאריך הלועזי. הצד של נאום נקבע לפי מה שהוא טוען, לא לפי מפלגת הדובר. לקרוא את הנאומים של שני הצדדים לפני שכותבים רשימה כלשהי. המודל עובד בלי חשיבה מורחבת, ותשובתו חייבת לעמוד במבנה קבוע. ההנחיות והבדיקות נמצאות ב{gh("קוד המקור הפתוח")} של האתר.</p>
      <p><strong>בדיקות אוטומטיות.</strong> טקסט שלא עובר אותן לא מתפרסם; הוא נרשם כבעיה שמחבר האתר בודק.</p>
      <ul>
        <li>בתרגום נשמרים כל המספרים של המקור, לא נשארות בו אותיות עבריות, והוא לא ארוך באופן חשוד.</li>
        <li>תיאור הצעת חוק הוא טקסט רציף בעברית באורך סביר שמסתיים במשפט שלם; כל מספר בו מופיע בדברי ההסבר (כשאפשר לקרוא אותם כטקסט).</li>
        <li>תקציר הדיון והטיעונים הם משפטים בעברית באורך סביר; כל טיעון מפנה לנאומים קיימים; כל מספר מופיע בנאומים או בשם הצעת החוק.</li>
        <li>מספרי ההסתייגויות שיוחסו למגישים הם בדיוק ההסתייגויות הממוספרות שמודפסות במסמך, בלי פערים, חפיפות או תוספות, וכל חבר כנסת שנזכר מופיע בטקסט. כשאי אפשר לקרוא את המספרים במסמך כטקסט, אי אפשר לבדוק זאת, והדף מציין זאת.</li>
      </ul>
      <p><strong>מה הבדיקות לא תופסות.</strong> טקסט רהוט עם המספרים הנכונים עדיין עלול להחמיץ את העיקר, לשייך טיעון לצד הלא נכון או לייחס אותו לדובר הלא נכון. אף אדם לא בודק את הטקסטים האלה לפני פרסומם. לכן כל אחד מהם מסומן „תקציר AI“ או „תרגום AI“ במקום שבו הוא מוצג, מקשר למסמך שעל סמכו נכתב, ולצדו קישור לדיווח על טעות (ראו {link("/about/methodology#corrections", "טעויות ותיקונים")}).</p></> },
    { id: "corrections", title: "טעויות ותיקונים", body: <>
      <p>חלק גדול מהטקסט באתר נכתב או תורגם בידי מודל בינה מלאכותית ולא נבדק בידי אדם, ולכן ייתכנו בו טעויות: תרגום לא מדויק, מספר שגוי, טיעון שסוכם לא טוב או שויך לצד הלא נכון. תוצאות ההצבעות, הרישומים השמיים והסיעות לקוחים מנתונים רשמיים, אך גם הם עלולים להיות שגויים, במקור או בעיבוד שלנו.</p>
      <p><strong>נשמח לעזרתכם.</strong> בגרסאות האנגלית, הרוסית והערבית יש ליד כל שם או תקציר מתורגם קישור „הציעו תיקון“. לכל דבר אחר, כולל התקצירים בעברית וטיעוני הצדדים, {link("/suggest", "כתבו למחבר האתר")}: הקישור נמצא מתחת לכל תקציר ובתחתית כל דף. המחבר קורא כל הודעה ובודק אותה לפני שמשהו באתר משתנה; השאירו פרטי קשר אם תרצו תשובה.</p></> },
    { id: "updates", title: "עדכון", body: <>
      <p>הנתונים מתעדכנים אוטומטית: בכל לילה, וכל שעתיים בימי מליאה (שני–רביעי). בכל עדכון נקראות מחדש ההצבעות של 30 הימים האחרונים, כדי לקלוט תיקונים במקור. תאריך העדכון האחרון מופיע בתחתית כל דף.</p>
      <p className="small muted">המונחים מוסברים {link("/about/glossary", "במילון המונחים")}.</p></> },
  ];
  return [
    { id: "sources", title: "Источники", body: <>
      <p>Все голосования, поимённые записи, депутаты, фракции и законопроекты на сайте взяты из <strong>официальных источников Кнессета</strong>. Всё остальное перечислено ниже по происхождению, и на сайте это помечено там, где показано.</p>
      <p><strong>Официальные источники Кнессета</strong></p>
      <ul>
        <li><strong>Открытые данные Кнессета (OData v4)</strong>: голосования в пленуме, поимённые записи, законопроекты, инициаторы, депутаты, фракции и членство в них, посты в правительстве (по ним определяется {link("/about/methodology#coalition", "коалиция")}), официальная классификация законов (для {link("/about/methodology#topics", "тем")}) и официальные резюме законов. Основной источник.</li>
        <li><strong>Старый сервис голосований Кнессета (Votes.svc)</strong>, данные до июля 2021 года: официальные итоги и голосования, которых нет в основном источнике, а также пометки о голосах, не вошедших в официальный итог.</li>
        <li><strong>Сайт Кнессета</strong>: официальные имена депутатов и названия фракций на русском, английском и арабском языках, фотографии депутатов.</li>
        <li><strong>Документы Кнессета</strong>: файлы законопроектов с пояснительными записками инициаторов, стенограммы заседаний пленума («Диврей ха-Кнессет») и версия законопроекта, подготовленная комиссией ко второму чтению, с оговорками. Из них берутся описания законопроектов, обсуждения и оговорки.</li>
      </ul>
      <p><strong>Другие источники</strong></p>
      <ul>
        <li><strong>Викиданные</strong>: английские, русские и арабские имена для депутатов, которых нет в материалах сайта, а также варианты написания для поиска.</li>
        <li><strong><a href="https://oknesset.org" target="_blank" rel="noopener">«Открытый Кнессет»</a></strong> (проект «Сикуй Хасадна» / Hasadna): таблица соответствия идентификаторов депутатов и идентификаторов сайта Кнессета, по которой находятся имена и фотографии. Используется с указанием источника.</li>
      </ul>
      <p><strong>Подготовлено или вычислено сайтом</strong></p>
      <ul>
        <li><strong>Вручную</strong>: партии и фракции, которыми они были представлены, названия фракций прежних созывов на других языках и несколько исключений в составе коалиции — у каждого есть ссылка на подтверждение.</li>
        <li><strong>Вычислено</strong>: итоги голосований после июля 2021 года (по поимённым записям), коалиция и оппозиция, темы по ключевым словам и все показатели. Правила описаны на этой странице.</li>
        <li><strong>Написано моделью ИИ</strong> (Claude, компания Anthropic): переводы, пересказы пояснительных записок, обсуждений и оговорок. Они не проверены и так и помечены; см. {link("/about/methodology#ai", "Как используется ИИ")}. Нашли ошибку? См. {link("/about/methodology#corrections", "Ошибки и исправления")}.</li>
      </ul>
      <p className="small muted">У каждого голосования есть ссылка на его карточку на сайте Кнессета. Исходные ответы источников сохраняются без изменений, чтобы любую цифру можно было перепроверить.</p></> },
    { id: "records", title: "Поимённые записи и «отсутствие»", body: <>
      <p>В открытых данных есть только депутаты, у которых <strong>есть запись</strong>: «за», «против», «воздержался» или «присутствовал, не голосовал». Если записи нет, сайт <strong>не считает депутата отсутствовавшим</strong>: источник этого не сообщает.</p>
      <p>У 89 голосований поимённых записей нет совсем. Это голосования поднятием рук и тайные голосования. Для них показывается только то, что опубликовано.</p></> },
    { id: "outcome", title: "Принято или нет", body: <>
      <p>Для голосований до июля 2021 года итог берётся из официальных данных Кнессета. Для более поздних официальный итог в открытых данных не публикуется. Тогда сайт считает его по поимённым записям: принято, если «за» больше, чем «против»; при равенстве не принято; вотум недоверия требует не меньше 61 голоса «за». Такой итог помечен «подсчёт по поимённым записям».</p>
      <p>Кворума в пленуме нет, поэтому закон, против которого никто не возражает, может пройти несколькими голосами. Подробнее — в {link("/about/glossary#quorum", "словаре")}.</p>
      <p className="small muted">До 2021 года поимённый список точно совпадает с официальным итогом в 96,5% голосований, а с расхождением не больше двух голосов — в 99,9%. Остальные расхождения объяснены или зарегистрированы для проверки. Подогнанных цифр нет.</p></> },
    { id: "faction", title: "Фракция на дату голосования", body:
      <p>Каждый голос относится к фракции, в которой депутат состоял <strong>в день голосования</strong>. Если депутат перешёл в другую фракцию в тот же день, голос помечен как неоднозначный. Голоса, для которых фракцию определить нельзя (11 из 2 млн), показаны отдельно.</p> },
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
      <p>Имена депутатов на русском, английском и арабском взяты с сайта Кнессета. Если там их нет, использованы Викиданные. Названия фракций прежних созывов на русском, английском и арабском подготовлены вручную по принятым в СМИ Израиля вариантам. Официальное название на иврите показано всегда. Названия законопроектов — на иврите, как их публикует Кнессет, с автоматическим переводом под ними. Фотографии депутатов — официальные портреты с сайта Кнессета; мы храним их копию и показываем её сами, потому что с октября 2026 года сайт Кнессета недоступен из-за пределов Израиля.</p> },
    { id: "translation", title: "Перевод", body: <>
      <p>Сайт написан сначала по-русски; английская, ивритская и арабская версии — переводы. Весь собственный текст сайта — меню, пояснения, эта страница и словарь, включая русский оригинал, — написан и переведён с помощью модели искусственного интеллекта (Claude, компания Anthropic) под руководством автора сайта.</p>
      <ul>
        <li><strong>Названия законопроектов и голосований.</strong> Ивритский оригинал всегда показан так, как его публикует Кнессет. В русской, английской и арабской версиях под ним дан автоматический перевод той же модели ИИ с пометкой «перевод ИИ». Официальное ивритское имя каждого депутата и фракции есть на их страницах.</li>
        <li><strong>Описания законопроектов.</strong> Где Кнессет публикует официальное резюме закона, страница законопроекта показывает его в машинном переводе. Где резюме нет (все законы до 20-го созыва и многие законопроекты после), страница закона, в окончательном голосовании по которому коалиция и оппозиция разошлись, или законопроекта, голосование по которому прошло с октября 2026 года, показывает автоматический пересказ пояснительной записки, которую инициаторы приложили к законопроекту, с пометкой, что это их доводы, и ссылкой на файл законопроекта. Его пишет та же модель ИИ, в том числе на иврите, и он не проверен. У остальных законопроектов без официального резюме описания нет.</li>
        <li><strong>Обсуждения и оговорки.</strong> Для законов, в окончательном голосовании по которым коалиция и оппозиция разошлись, страница законопроекта пересказывает, что говорили в пленуме — по официальным стенограммам заседаний, где по нему голосовали, — и какие оговорки подали ко второму чтению — по версии комиссии. Кто выступал, от какой фракции, как голосовал и какая фракция подала сколько оговорок, взято из самих документов; пересказ доводов и оговорок пишет та же модель ИИ, и он не проверен. Доводы пересказаны своими словами, это не цитаты и не оценка того, какая сторона права; кто высказал какой довод — прочтение модели, поэтому прежде чем цитировать кого-то, сверьтесь со стенограммой (ссылка под каждым обсуждением).</li>
        <li><strong>Имена депутатов</strong> на русском, английском и арабском — официальное написание сайта Кнессета (Викиданные, если на сайте его нет).</li>
        <li><strong>Названия фракций</strong> прежних созывов <strong>и партий</strong> подготовлены вручную по вариантам, принятым в СМИ; для текущего Кнессета используются официальные названия с сайта Кнессета. <strong>Названия тем</strong> — наши.</li>
        <li><strong>Арабская версия — бета.</strong> Её ещё не проверял носитель арабского языка, поэтому некоторые термины Кнессета могут быть неточны. В словаре рядом с каждым термином дан ивритский оригинал.</li>
      </ul></> },
    { id: "ai", title: "Как используется ИИ", body: <>
      <p>Часть текстов на сайте написана моделями ИИ (Claude, компания Anthropic). <strong>Числа — нет</strong>: голосования, поимённые записи, результаты, фракции, коалиция и оппозиция, темы, показатели и тест считаются обычным кодом по правилам на этой странице, без модели. В модель отправляются только открытые документы Кнессета; ничего о посетителях сайта.</p>
      <p><strong>Что пишет модель и из чего</strong> (модели — на октябрь 2026 года)</p>
      <ul>
        <li><strong>Переводы</strong> названий законопроектов и голосований и официальных резюме с иврита на русский, английский и арабский. Названия — Claude Haiku 4.5 (на арабский — Claude Sonnet 5) с постоянным глоссарием юридических терминов, чтобы около 22 000 названий переводились единообразно. Резюме и все остальные тексты — Claude Sonnet 5. Каждый текст на иврите переводится один раз; если Кнессет меняет оригинал, старый перевод больше не показывается, а новый текст переводится заново.</li>
        <li><strong>Описания законопроектов</strong>, у которых нет официального резюме. Модель (Claude Sonnet 5) читает пояснительную записку в файле законопроекта и пишет на иврите два–четыре предложения: что законопроект меняет и какие доводы приводят инициаторы, — от их имени («по словам инициаторов»). Затем описание переводится, как любой другой текст.</li>
        <li><strong>Обсуждения.</strong> Код сам вырезает обсуждение законопроекта из стенограмм всех заседаний, где по нему голосовали, и составляет список выступавших — кто, в каких чтениях и сколько раз — без модели. Модель (Claude Sonnet 5) получает пронумерованные выступления и пишет нейтральное резюме и до пяти доводов за и пяти против, каждый со ссылками на выступления, из которых он взят; депутаты под доводом — авторы этих выступлений. На карточках показан довод каждой стороны, прозвучавший в наибольшем числе выступлений. Если обсуждение не помещается в один запрос, все выступления сначала сокращаются до одинаковой длины, и страница об этом сообщает.</li>
        <li><strong>Оговорки.</strong> Модель (Claude Sonnet 5) читает раздел оговорок в версии комиссии, определяет, какие номера оговорок принадлежат какому депутату или группе, и пишет суть каждой в одном предложении.</li>
      </ul>
      <p><strong>Правила для модели.</strong> Использовать только данный ей документ: никаких фактов со стороны, никаких суждений о том, какая сторона права, никаких оценочных слов, числа — точно как в источнике, даты — только по григорианскому календарю. Сторона выступления определяется тем, что в нём доказывается, а не партией выступавшего. Прочитать выступления обеих сторон, прежде чем писать любой из списков. Модель работает без расширенных рассуждений, и её ответ должен соответствовать заданной структуре. Промпты и проверки — в {gh("открытом исходном коде")} сайта.</p>
      <p><strong>Автоматические проверки.</strong> Текст, который их не прошёл, не публикуется: он записывается как проблема, которую разбирает автор.</p>
      <ul>
        <li>В переводе сохранены все числа оригинала, не осталось букв иврита, и он не подозрительно длинный.</li>
        <li>Описание законопроекта — связный текст на иврите разумной длины, который заканчивается полным предложением; каждое число в нём есть в пояснительной записке (если записку удаётся прочитать как текст).</li>
        <li>Резюме обсуждения и доводы — предложения на иврите разумной длины; каждый довод ссылается на существующие выступления; каждое число есть в выступлениях или в названии законопроекта.</li>
        <li>Номера оговорок, приписанные авторам, — ровно те пронумерованные оговорки, что напечатаны в документе, без пропусков, повторов и лишних, а каждый названный депутат есть в тексте. Если номера в документе нельзя прочитать как текст, это проверить нельзя, и страница об этом сообщает.</li>
      </ul>
      <p><strong>Чего проверки не ловят.</strong> Гладкий текст с правильными числами всё равно может упустить суть, отнести довод не к той стороне или приписать его не тому выступавшему. Никто не проверяет эти тексты до публикации. Поэтому каждый из них помечен «пересказ ИИ» или «перевод ИИ» там, где показан, ссылается на документ, по которому написан, и рядом есть ссылка, чтобы сообщить об ошибке (см. {link("/about/methodology#corrections", "Ошибки и исправления")}). У переводов оригинал на иврите — в один клик.</p></> },
    { id: "corrections", title: "Ошибки и исправления", body: <>
      <p>Большая часть текста на сайте написана или переведена моделью ИИ и не проверена человеком, поэтому в нём возможны ошибки: неточный перевод, неверное число, плохо пересказанный довод или довод, отнесённый не к той стороне. Итоги голосований, поимённые записи и фракции взяты из официальных данных, но и в них возможны ошибки — в источнике или в нашей обработке.</p>
      <p><strong>Будем рады вашей помощи.</strong> Рядом с переведённым названием или резюме есть ссылка «предложить исправление». Обо всём остальном, в том числе об ивритских пересказах и доводах сторон, {link("/suggest", "напишите автору")}: ссылка есть под каждым пересказом и внизу каждой страницы. Автор читает каждое сообщение и проверяет его, прежде чем на сайте что-то изменится; оставьте контакт, если хотите получить ответ.</p></> },
    { id: "updates", title: "Обновление", body: <>
      <p>Данные обновляются автоматически: каждую ночь и каждые два часа в дни заседаний пленума (понедельник–среда). При каждом обновлении перечитываются голосования за последние 30 дней, чтобы подхватить исправления источника. Дата последнего обновления указана внизу каждой страницы.</p>
      <p className="small muted">Термины объяснены в {link("/about/glossary", "словаре")}.</p></> },
  ];
}
