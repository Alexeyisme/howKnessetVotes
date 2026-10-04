"""Editorial topic taxonomy and a keyword-rule classifier for bills (architecture.md §9, MVP).

Rules match whole Hebrew words (with the usual one-letter prefixes ו ה ב ל מ ש כ) in the normalised bill
title. Every assignment is stored as origin='rule', review_state='unreviewed', with the keyword that
matched, so the UI can say "assigned automatically" and an editor can accept or reject it later.
Re-running replaces only unreviewed rule assignments.

Topic labels and aliases are ours; they are not an official Knesset classification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import psycopg

RULES_VERSION = "2026-10-04.2"

_NIQQUD = re.compile("[֑-ֽֿ-ׇ]")
_TO_SPACE = str.maketrans({"־": " ", "–": " ", "—": " ", "-": " "})
_DROP = str.maketrans("", "", "״\"׳'`")


def he_norm(t: str | None) -> str:
    """Same rules as the SQL function he_norm (db/migrations/0005)."""
    s = _NIQQUD.sub("", t or "").translate(_TO_SPACE).translate(_DROP)
    return re.sub(r"\s+", " ", s).strip().lower()


@dataclass(frozen=True)
class Topic:
    slug: str
    ru: str
    he: str
    keywords: tuple[str, ...]            # Hebrew, matched as whole words after he_norm
    ru_aliases: tuple[str, ...] = field(default=())
    description_ru: str | None = None


TOPICS: tuple[Topic, ...] = (
    Topic("budget", "Государственный бюджет", "תקציב המדינה",
          ("חוק התקציב", "תקציב המדינה", "יעדי התקציב", "התוכנית הכלכלית", "שנות התקציב", "שנת התקציב"),
          ("бюджет", "госбюджет", "закон о бюджете", "экономическая программа", "закон о договорённостях")),
    Topic("taxes", "Налоги", "מסים",
          # never the bare word מס: after normalisation "(תיקון מס' 12)" = "amendment No. 12" reads as "מס"
          ("מס הכנסה", "מסים", "מיסוי", "מעמ", "מס ערך מוסף", "מכס", "בלו", "מס רכישה", "מס שבח", "מסי", "ארנונה", "מס בולים", "מס מעסיקים"),
          ("налоги", "налог", "НДС", "подоходный налог", "налоговые льготы", "таможня", "арнона")),
    Topic("labor", "Труд и зарплаты", "עבודה ושכר",
          ("שכר", "שכר מינימום", "עובדים", "עובד", "העסקת", "שעות עבודה ומנוחה", "פיצויי פיטורים", "חופשה שנתית", "פנסיה", "פנסיוני", "הסכמים קיבוציים"),
          ("зарплата", "работа", "работники", "минимальная зарплата", "пенсия", "увольнение", "профсоюзы")),
    Topic("welfare", "Социальное обеспечение", "רווחה וביטוח לאומי",
          ("ביטוח לאומי", "הביטוח הלאומי", "גמלה", "גמלאות", "קצבה", "קצבאות", "הבטחת הכנסה", "רווחה", "נכות", "נכים", "אנשים עם מוגבלות", "אזרחים ותיקים", "ניצולי השואה"),
          ("пособия", "социальное страхование", "битуах леуми", "инвалиды", "пенсионеры", "пожилые", "переживших Холокост")),
    Topic("health", "Здравоохранение", "בריאות",
          ("בריאות", "ביטוח בריאות ממלכתי", "קופות חולים", "בתי חולים", "בית חולים", "רופאים", "רפואה", "תרופות", "סיעוד", "בריאות הנפש", "זכויות החולה"),
          ("медицина", "здоровье", "больницы", "больничные кассы", "лекарства", "врачи", "психическое здоровье")),
    Topic("education", "Образование", "חינוך",
          ("חינוך", "בתי ספר", "בית ספר", "מוסדות חינוך", "השכלה גבוהה", "סטודנטים", "מעונות יום", "לימוד חובה", "גני ילדים", "מכינות"),
          ("образование", "школы", "университеты", "студенты", "детские сады", "учителя")),
    Topic("housing", "Жильё, земля и строительство", "דיור ומקרקעין",
          ("דיור", "דירה", "דירות", "שכירות", "מקרקעין", "מקרקעי ישראל", "תכנון והבנייה", "התחדשות עירונית", "בנייה", "משכנתאות", "מכר דירות"),
          ("жильё", "квартиры", "аренда", "недвижимость", "строительство", "ипотека", "земля")),
    Topic("transport", "Транспорт", "תחבורה",
          ("תחבורה", "תעבורה", "רכבת", "רכבות", "כבישים", "כביש", "נהיגה", "רישיונות נהיגה", "רישיון נהיגה", "תעופה", "שירותי תעופה", "נמלים", "רכב", "כלי רכב", "תחבורה ציבורית"),
          ("транспорт", "автобусы", "поезд", "железная дорога", "дороги", "водительские права", "авиация", "машины", "общественный транспорт")),
    Topic("defense", "Армия и оборона", "צבא וביטחון",
          ("שירות ביטחון", "צבא", "צהל", "חיילים", "מילואים", "שירות המילואים", "משרתי המילואים", "נפגעי פעולות איבה", "משפחות החיילים", "חרבות ברזל", "חיילים משוחררים", "נכי צהל"),
          ("армия", "ЦАХАЛ", "резервисты", "милуим", "призыв", "солдаты", "оборона", "война", "Железные мечи")),
    Topic("police", "Полиция и внутренняя безопасность", "משטרה וביטחון פנים",
          ("משטרה", "המשטרה", "פקודת המשטרה", "שירות הביטחון הכללי", "שבכ", "טרור", "המאבק בטרור", "בתי הסוהר", "נשק", "כלי ירייה"),
          ("полиция", "ШАБАК", "терроризм", "тюрьмы", "оружие", "безопасность")),
    Topic("justice", "Суды и уголовное право", "משפט ועונשין",
          ("עונשין", "סדר הדין הפלילי", "בתי המשפט", "בית המשפט", "שופטים", "הוועדה לבחירת שופטים", "היועץ המשפטי לממשלה", "פרקליטות", "מעצר", "ראיות", "הוצאה לפועל", "חסינות"),
          ("суды", "судьи", "судебная реформа", "уголовный кодекс", "юридический советник", "прокуратура", "арест")),
    Topic("governance", "Государственное устройство и выборы", "משטר ובחירות",
          ("חוק יסוד", "בחירות", "הבחירות", "בחירות לכנסת", "הכנסת", "הממשלה", "מבקר המדינה", "מפלגות", "מימון מפלגות", "התפזרות הכנסת", "שרים"),
          ("основной закон", "выборы", "роспуск Кнессета", "правительство", "госконтролёр", "партии", "конституция")),
    Topic("religion", "Религия и государство", "דת ומדינה",
          ("שבת", "כשרות", "רבנות", "הרבנות הראשית", "רבנים", "גיור", "בתי הדין הרבניים", "שירותי הדת", "ישיבות", "לומדי תורה", "מקוואות", "נישואין", "גירושין", "קבורה"),
          ("религия", "шаббат", "суббота", "кашрут", "раввинат", "гиюр", "брак", "развод", "иешивы")),
    Topic("immigration", "Алия, гражданство, иммиграция", "עלייה ואזרחות",
          ("עולים", "עלייה", "קליטה", "קליטת עלייה", "אזרחות", "הכניסה לישראל", "חוק השבות", "מסתננים", "עובדים זרים"),
          ("алия", "репатрианты", "абсорбция", "гражданство", "закон о возвращении", "иностранные рабочие", "нелегалы")),
    Topic("environment", "Экология и энергетика", "סביבה ואנרגיה",
          ("סביבה", "הגנת הסביבה", "זיהום", "אוויר נקי", "פסולת", "מים", "משק המים", "חשמל", "משק החשמל", "אנרגיה", "גז טבעי", "משק הגז", "אקלים", "משק הדלק"),
          ("экология", "загрязнение", "вода", "электричество", "энергетика", "газ", "климат", "мусор", "топливо")),
    Topic("communications", "Связь, СМИ и технологии", "תקשורת וטכנולוגיה",
          ("תקשורת", "שידור", "השידור הציבורי", "שידורים", "הגנת הפרטיות", "פרטיות", "סייבר", "מאגרי מידע", "אינטרנט"),
          ("СМИ", "телевидение", "общественное вещание", "связь", "приватность", "кибер", "интернет", "данные")),
    Topic("local-government", "Местная власть", "שלטון מקומי",
          ("רשויות מקומיות", "רשות מקומית", "עיריות", "העיריות", "מועצות אזוריות", "מועצות מקומיות", "המועצות המקומיות"),
          ("муниципалитеты", "местная власть", "мэрии", "региональные советы")),
    Topic("agriculture", "Сельское хозяйство и продовольствие", "חקלאות ומזון",
          ("חקלאות", "חקלאי", "חקלאים", "מזון", "צער בעלי חיים", "בעלי חיים", "הגנה על בריאות הציבור (מזון)"),
          ("сельское хозяйство", "фермеры", "продукты", "еда", "животные", "защита животных")),
    Topic("finance-consumer", "Финансы и защита потребителей", "פיננסים וצרכנות",
          # not the bare word ביטוח: most titles with it are הביטוח הלאומי (welfare) or ביטוח בריאות (health)
          ("הגנת הצרכן", "צרכן", "בנקאות", "הבנקאות", "בנקים", "חוזה הביטוח", "חברות ביטוח", "ביטוח חובה", "ביטוח רכב",
           "שירותים פיננסיים", "הפיקוח על שירותים פיננסיים", "שוק ההון", "ניירות ערך", "אשראי", "הלוואות", "התחרות", "ההגבלים העסקיים", "חדלות פירעון"),
          ("банки", "кредиты", "потребители", "защита потребителей", "страхование", "рынок капитала", "конкуренция", "банкротство")),
    Topic("family", "Семья, дети и равноправие", "משפחה ושוויון",
          ("ילדים", "קטינים", "נוער", "הורים", "נשים", "שוויון", "שוויון זכויות", "אלימות במשפחה", "מזונות", "אימוץ", "הטרדה מינית"),
          ("дети", "подростки", "семья", "женщины", "равноправие", "домашнее насилие", "алименты", "усыновление")),
    Topic("emergency", "Чрезвычайное положение, война, COVID", "חירום",
          ("חרבות ברזל", "נגיף הקורונה", "קורונה", "הקורונה", "שעת חירום", "מצב חירום", "תקנות שעת חירום", "מלחמה"),
          ("война", "чрезвычайное положение", "коронавирус", "COVID", "ковид", "эпидемия")),
)

# English labels and search aliases (lower case), by slug.
TOPICS_EN: dict[str, tuple[str, tuple[str, ...]]] = {
    "budget": ("State budget", ("budget", "state budget", "arrangements law", "economic plan")),
    "taxes": ("Taxes", ("tax", "taxes", "vat", "income tax", "customs", "arnona")),
    "labor": ("Labor and wages", ("labor", "labour", "wages", "salary", "minimum wage", "workers", "pension", "unions")),
    "welfare": ("Welfare and social security", ("welfare", "social security", "national insurance", "bituach leumi", "disability", "allowances", "holocaust survivors")),
    "health": ("Health", ("health", "healthcare", "hospitals", "health funds", "kupot holim", "medicines", "doctors", "mental health")),
    "education": ("Education", ("education", "schools", "universities", "students", "kindergartens", "teachers")),
    "housing": ("Housing, land and construction", ("housing", "apartments", "rent", "real estate", "construction", "mortgage", "land")),
    "transport": ("Transport", ("transport", "transportation", "buses", "railway", "trains", "roads", "driving license", "aviation", "public transport")),
    "defense": ("Military and defense", ("military", "army", "idf", "defense", "reservists", "soldiers", "draft", "conscription", "war", "iron swords")),
    "police": ("Police and internal security", ("police", "shin bet", "shabak", "terrorism", "prisons", "firearms", "security")),
    "justice": ("Courts and criminal law", ("courts", "judges", "judicial reform", "judicial overhaul", "criminal law", "attorney general", "prosecution")),
    "governance": ("Government and elections", ("basic law", "elections", "knesset dissolution", "government", "state comptroller", "parties", "constitution")),
    "religion": ("Religion and state", ("religion", "shabbat", "sabbath", "kashrut", "kosher", "rabbinate", "conversion", "giyur", "marriage", "divorce", "yeshivas")),
    "immigration": ("Aliyah, citizenship and immigration", ("aliyah", "immigration", "immigrants", "olim", "absorption", "citizenship", "law of return", "foreign workers")),
    "environment": ("Environment and energy", ("environment", "pollution", "water", "electricity", "energy", "natural gas", "climate", "waste", "fuel")),
    "communications": ("Communications, media and technology", ("media", "broadcasting", "public broadcasting", "communications", "privacy", "cyber", "internet", "data")),
    "local-government": ("Local government", ("local government", "municipalities", "local authorities", "regional councils")),
    "agriculture": ("Agriculture and food", ("agriculture", "farmers", "food", "animals", "animal welfare")),
    "finance-consumer": ("Finance and consumer protection", ("banks", "banking", "credit", "loans", "consumers", "consumer protection", "insurance", "capital market", "competition", "insolvency")),
    "family": ("Family, children and equality", ("children", "youth", "family", "women", "equality", "domestic violence", "child support", "adoption")),
    "emergency": ("Emergency, war and COVID", ("war", "emergency", "state of emergency", "coronavirus", "covid", "epidemic")),
}

# Real Hebrew prefix sequences only: optional ו or ש, then optional one of ה ב ל מ כ (or מה). "לה" is not a
# prefix sequence, so להשבת ("restoring") is not the word שבת.
HE_PREFIX = "(?:[וש]?(?:מה|[הבלמכ])?)"
_PREFIX = HE_PREFIX


def _pattern(keywords: tuple[str, ...]) -> re.Pattern[str]:
    alts = sorted({he_norm(k) for k in keywords}, key=len, reverse=True)
    return re.compile(rf"(?:^|[\s(,:;]){_PREFIX}({'|'.join(re.escape(a) for a in alts)})(?=$|[\s),.:;])")


_PATTERNS = {t.slug: _pattern(t.keywords) for t in TOPICS}


# Phrases that contain a keyword but mean something else; removed before matching.
FALSE_FRIENDS = tuple(he_norm(p) for p in (
    "הכשרות המשפטית",   # legal capacity, not kashrut (כשרות)
))


def classify_title(title: str) -> dict[str, str]:
    """slug -> the keyword that matched."""
    norm = he_norm(title)
    for phrase in FALSE_FRIENDS:
        norm = norm.replace(phrase, " ")
    out = {}
    for slug, pat in _PATTERNS.items():
        m = pat.search(norm)
        if m:
            out[slug] = m.group(1)
    return out


# Russian names for factions, keyed by a distinctive part of the normalised Hebrew name. Machine-written
# (origin='machine'), shown next to the official Hebrew name, never instead of it.
FACTIONS_RU: tuple[tuple[str, str], ...] = (
    ("הליכוד", "Ликуд"),
    ("יש עתיד", "Еш Атид"),
    ("התאחדות הספרדים", "ШАС"),
    ("שס", "ШАС"),
    ("יהדות התורה", "Яадут ха-Тора"),
    ("ישראל ביתנו", "Наш дом Израиль"),
    ("ישראל ביתינו", "Наш дом Израиль"),
    ("כחול לבן", "Кахоль-лаван"),
    ("המחנה הממלכתי", "Государственный лагерь"),
    ("הציונות הדתית", "Религиозный сионизм"),
    ("עוצמה יהודית", "Оцма Йехудит"),
    ("נעם", "Ноам"),
    ("העבודה", "Авода"),
    ("הדמוקרטים", "Демократы"),
    ("מרצ", "Мерец"),
    ("הרשימה המשותפת", "Объединённый арабский список"),
    ("רעם", "РААМ"),
    ("הרשימה הערבית המאוחדת", "РААМ"),
    ("בלד", "БАЛАД"),
    ("כולנו", "Кулану"),
    ("הבית היהודי", "Еврейский дом"),
    ("המחנה הציוני", "Сионистский лагерь"),
    ("ימינה", "Ямина"),
    ("תקווה חדשה", "Новая надежда"),
    ("הימין הממלכתי", "Государственные правые"),
    ("דרך ארץ", "Дерех Эрец"),
    ("גשר", "Гешер"),
    ("ימין חדש", "Новые правые"),
    ("איחוד מפלגות הימין", "Союз правых партий"),
    ("האיחוד הלאומי", "Национальное единство"),
    ("תלם", "Тэлем"),
    ("חוסן לישראל", "Хосен ле-Исраэль"),
    # generic keys last: "ימין חדש" must not match "חדש"
    ("חדש תעל", "ХАДАШ–ТААЛЬ"),
    ("חדש", "ХАДАШ"),
)


def faction_ru(name_he: str) -> str | None:
    norm = he_norm(name_he)
    words = f" {norm} "
    for key, ru in FACTIONS_RU:
        k = he_norm(key)
        if f" {k} " in words or norm.startswith(k + " ") or norm == k:
            return ru
    return None


def sync(conn: psycopg.Connection) -> dict[str, int]:
    """Upsert the taxonomy, re-run rule assignments (unreviewed only) and machine faction labels."""
    counts: dict[str, int] = {}
    with conn.transaction():
        for i, t in enumerate(TOPICS):
            tid = conn.execute(
                """INSERT INTO topic (slug, sort) VALUES (%s, %s) ON CONFLICT (slug) DO UPDATE SET sort = EXCLUDED.sort RETURNING id""",
                (t.slug, i)).fetchone()[0]
            for lang, label in (("ru", t.ru), ("he", t.he), ("en", TOPICS_EN[t.slug][0])):
                conn.execute(
                    """INSERT INTO topic_label (topic_id, language, label, description) VALUES (%s, %s, %s, %s)
                       ON CONFLICT (topic_id, language) DO UPDATE SET label = EXCLUDED.label, description = EXCLUDED.description""",
                    (tid, lang, label, t.description_ru if lang == "ru" else None))
            conn.execute("DELETE FROM topic_alias WHERE topic_id = %s", (tid,))
            for alias in (*t.ru_aliases, t.ru):
                conn.execute("INSERT INTO topic_alias (topic_id, language, alias) VALUES (%s, 'ru', %s) ON CONFLICT DO NOTHING", (tid, alias))
            for alias in (*TOPICS_EN[t.slug][1], TOPICS_EN[t.slug][0]):
                conn.execute("INSERT INTO topic_alias (topic_id, language, alias) VALUES (%s, 'en', %s) ON CONFLICT DO NOTHING", (tid, alias))
            for kw in t.keywords:
                conn.execute("INSERT INTO topic_alias (topic_id, language, alias) VALUES (%s, 'he', %s) ON CONFLICT DO NOTHING", (tid, kw))
        topic_ids = dict(conn.execute("SELECT slug, id FROM topic").fetchall())

        conn.execute("DELETE FROM bill_topic WHERE origin = 'rule' AND review_state = 'unreviewed'")
        # official law classification first: for the same topic it wins over a keyword match
        from hkv.topics.official import assign as assign_official
        counts["bill_topics_official"] = assign_official(conn, topic_ids)
        assigned = 0
        for bill_id, title in conn.execute("SELECT id, title_he FROM bill").fetchall():
            for slug, kw in classify_title(title).items():
                assigned += conn.execute(
                    """INSERT INTO bill_topic (bill_id, topic_id, origin, evidence, rules_version) VALUES (%s, %s, 'rule', %s, %s)
                       ON CONFLICT (bill_id, topic_id) DO NOTHING""",
                    (bill_id, topic_ids[slug], kw, RULES_VERSION)).rowcount
        counts["bill_topics"] = assigned

        labelled = 0
        for fid, name in conn.execute("SELECT id, name_he FROM faction").fetchall():
            ru = faction_ru(name)
            if ru:
                labelled += conn.execute(
                    """INSERT INTO faction_label (faction_id, language, name, origin) VALUES (%s, 'ru', %s, 'machine')
                       ON CONFLICT (faction_id, language) DO UPDATE SET name = EXCLUDED.name WHERE faction_label.origin = 'machine'""",
                    (fid, ru)).rowcount
        counts["faction_labels_ru"] = labelled
    return counts
