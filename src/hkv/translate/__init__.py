"""Machine translation of Hebrew titles and official bill summaries (docs/ux-requirements.md R4; roadmap L6, L7).

Distinct Hebrew strings (bill and vote titles) are translated once per language and stored by the SHA-256 of the
source in text_translation. A fixed glossary keeps ~22,000 titles consistent; automatic checks reject translations
that lose a number or keep Hebrew letters, and log them as data_issue rows instead of storing them. The translator
is pluggable: ClaudeTranslator in production, StubTranslator in tests.

Four kinds of text share the table and the checks: "title" (bill and vote titles), "summary" (the official
`SummaryLaw` of a bill, a paragraph of plain prose, so it gets its own prompt and smaller batches), "notes" (our
description of a bill from its sponsors' explanatory notes, hkv.notes; prose like a summary) and "positions" (our
summaries of the plenum debate and the reservations, hkv.debate and hkv.reservations: one-sentence arguments and
gists, attributed to the sides).

Every `hkv update` runs `sync` when the server has an API key, so only titles that are new since the last run go to
the API; when nothing is new, no request is made. A title that failed the checks is not retried automatically (it
would fail the same way on every run); `hkv translate --retry-failed` tries those again.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import tomllib
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Protocol

import psycopg

log = logging.getLogger(__name__)

LANGUAGES = ("en", "ru", "ar")
KINDS = ("title", "summary", "notes", "positions")
PROSE = ("summary", "notes", "positions")   # own prompt, prose checks, the summary model
BATCH = {"title": 20, "summary": 5, "notes": 5, "positions": 10}   # a summary averages ~850 Hebrew characters, the longest ~6,400
# Haiku: legal titles are formulaic and the checks catch lost numbers; the full history cost a few dollars with it.
# Arabic gets Sonnet: in a 30-title comparison (2026-10-05) Haiku mistranslated legal terms (התיישנות, מסגרות תקציב)
# and translated a person's name; Sonnet did not. HKV_TRANSLATE_MODEL_<LANG> overrides per language.
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
LANGUAGE_MODELS = {"ar": "claude-sonnet-5"}
# Summaries are prose, where Haiku got the meaning wrong in a 10-summary sample (2026-10-07: אישור מסע אלקטרוני as
# "electronic passport", המצב הביטחוני as «безопасная ситуация»); Sonnet did not. HKV_TRANSLATE_MODEL_SUMMARY overrides.
SUMMARY_MODEL = "claude-sonnet-5"

_HEBREW = re.compile(r"[֐-׿]")
_DIGITS = re.compile(r"\d+")
# Summaries only (prose, where the model rightly reformats): "31.03" is written "31 March"; "1000" may become "1,000"
# or "1 000"; section numbers keep their Hebrew letters ("סעיף 14טו", "406(ה)"), as translations of Israeli law do.
_SHORT_DATE = re.compile(r"(?<![\d.])(\d{1,2})\.(\d{1,2})(?!\d|\.\d)")   # "עד ה-15.04." ends a sentence
_THOUSANDS = re.compile(r"(?<=\d)[,\u00a0\u202f ](?=\d{3}(?!\d))")
_SECTION_LETTERS = re.compile(r"(?<=\d)[\u05d0-\u05ea]{1,3}|\([\u05d0-\u05ea]{1,2}\)|[\u05d0-\u05ea](?=\d)")
# A Hebrew-calendar day before its month ("27 באב התשע״ו (31 באוגוסט 2016)"): the prompt says to write only the
# Gregorian date, so the day number need not survive.
_HEBREW_DAY = re.compile(r"(?<!\d)\d{1,2}(?=\s+ב(?:תשרי|חשוון|חשון|מרחשוון|כסלו|טבת|שבט|אדר|ניסן|אייר|סיוון|סיון|תמוז|אב|אלול)(?![\u05d0-\u05ea]))")
# Typos in the Knesset's own text, by the words around them: the number named need not be in a translation, which
# cannot repeat it sensibly. The Hebrew stays as published; only the check is waived.
SOURCE_TYPOS = [
    ('התשס"ג 20000', "20000"),                                  # the year 2003 with a stray "20000"
    ("לשנות 207 ו-2018", "207"),                               # "the years 207 and 2018": 2017
    ('2005ת אויב או תושב אזור עימות), התשס"ב-2002', "2002"),      # the tail of another title glued on
    ('2005וטקים), התשס"ד-2004', "2004"),                        # the same
    ("14,5000 מקומות", "5000"),                                 # 14,500 prison places
]
# Idioms: the number is a figure of speech and a translation rightly has none ("at the last minute").
IDIOMS = [("בדקה ה-90", "90")]
_NUMERIC_DATE = re.compile(r"(?<!\d)(\d{1,2})[./](\d{1,2})[./](\d{2,4})(?!\d)")   # also "ב1.9.2025"

LANGUAGE_NAME = {"en": "English", "ru": "Russian", "ar": "Arabic"}

# Terms that must read the same in every title. The Hebrew year ("התשפ\"ו-2026") keeps only the Gregorian year.
GLOSSARY = {
    "en": [("הצעת חוק", "Bill"), ("חוק", "Law"), ("חוק-יסוד / חוק יסוד", "Basic Law"), ("תיקון מס' N", "Amendment No. N"),
           ("הוראת שעה", "temporary provision"), ("תיקוני חקיקה", "legislative amendments"), ("פקודת", "Ordinance"),
           ("תקנות", "Regulations"), ("הצעת אי-אמון", "no-confidence motion"), ("התשפ\"ו-2026", "2026"),
           ("אישור מסע אלקטרוני (Israel's ETA-IL; not a passport or a journey)", "electronic travel authorization (ETA-IL)"),
           # from the 20-bill sample of descriptions and debates (2026-10-08)
           ("דברי הסבר", "explanatory notes"), ("המציעים / יוזמי ההצעה", "the sponsors"),
           ("דיינים (judges of the rabbinical courts)", "dayanim (rabbinical court judges)"),
           ("אסירים ביטחוניים", "security prisoners"), ("תקני כשרות / ריבוי תקנים (kashrut standards, not staff positions)", "kashrut standards"),
           ("מבצע עם כלביא (June 2025, Iran)", "Operation Rising Lion"), ("מבצע מרכבות גדעון", "Operation Gideon's Chariots"),
           ("מבצע שאגת הארי", "Operation Lion's Roar"),
           # as the vote page explains it (apps/web i18n/content/voteKinds.tsx)
           ("הוועדה המסדרת", "Arrangements Committee"),
           # one name for the office everywhere (the search finds a law by it): 2026-11-26
           ("היועץ המשפטי לממשלה / היועצת המשפטית לממשלה", "Attorney General"),
           # vote 42577 (2026-11-22): the title came out as "tax and Nmexes updates"
           ("מס יסף (the extra income tax on high incomes; not VAT)", "surtax")],
    "ru": [("הצעת חוק", "Законопроект"), ("חוק", "Закон"), ("חוק-יסוד / חוק יסוד", "Основной закон"), ("תיקון מס' N", "поправка № N"),
           ("הוראת שעה", "временное положение"), ("תיקוני חקיקה", "поправки к законодательству"), ("פקודת", "Указ"),
           ("תקנות", "Правила"), ("הצעת אי-אמון", "вотум недоверия"), ("התשפ\"ו-2026", "2026"),
           ("אישור מסע אלקטרוני (Israel's ETA-IL; not a passport or a journey)", "электронное разрешение на въезд (ETA-IL)"),
           # from the 20-bill sample of descriptions and debates (2026-10-08)
           ("דברי הסבר", "пояснительная записка"), ("המציעים / יוזמי ההצעה", "инициаторы законопроекта (not «авторы»)"),
           ("דיינים (judges of the rabbinical courts)", "даяны (судьи раввинских судов)"),
           ("אסירים ביטחוניים", "заключённые по делам безопасности"), ("תקני כשרות / ריבוי תקנים (kashrut standards, not staff positions)", "стандарты кашрута"),
           ("מבצע עם כלביא (June 2025, Iran)", "операция «Народ как лев»"), ("מבצע מרכבות גדעון", "операция «Колесницы Гидеона»"),
           ("מבצע שאגת הארי", "операция «Рык льва»"), ("בג\"ץ", "БАГАЦ (Высший суд справедливости)"),
           # as the vote page explains it (apps/web i18n/content/voteKinds.tsx); not «Комитет по регламенту»
           ("הוועדה המסדרת", "Организационная комиссия"), ("הכנסת / כנסת", "Кнессет (double с)"),
           # 2026-11-26: one home page had «советник юстиции правительства», «Генеральный прокурор» and «юридический
           # советник правительства» for the same office, and «временный комитет» next to «комиссия»
           ("היועץ המשפטי לממשלה / היועצת המשפטית לממשלה (NOT «Генеральный прокурор», NOT «советник юстиции»)", "юридический советник правительства"),
           ("ועדה / ועדת / הוועדה (a committee of the Knesset or of the state; NOT «комитет»)", "комиссия"),
           ("מס יסף (the extra income tax on high incomes; NOT НДС)", "дополнительный налог")],
    "ar": [("הצעת חוק", "اقتراح قانون"), ("חוק", "قانون"), ("חוק-יסוד / חוק יסוד", "قانون أساس"), ("תיקון מס' N", "تعديل رقم N"),
           ("הוראת שעה", "حكم مؤقت"), ("תיקוני חקיקה", "تعديلات تشريعية"), ("פקודת", "مرسوم"),
           ("תקנות", "أنظمة"), ("הצעת אי-אמון", "اقتراح حجب الثقة"), ("התשפ\"ו-2026", "2026"),
           # from the 2026-10-05 sample: terms the models got wrong or inconsistent with the site's Arabic UI
           ("יישוב / יישובים (towns, villages; NOT settlements)", "بلدة / بلدات"), ("התנחלות / התנחלויות (West Bank settlements)", "مستوطنة / مستوطنات"),
           ("תקציב", "ميزانية"), ("התיישנות", "التقادم"), ("העברת הצעת חוק (to a committee)", "إحالة اقتراح قانون"),
           ("סעיף (of a law or the Knesset rules)", "المادة"), ("תקנון הכנסת", "النظام الداخلي للكنيست"),
           ("הסתייגות", "تحفظ"), ("הצעה לסדר היום", "اقتراح لجدول الأعمال"), ("מליאה", "الهيئة العامة"),
           ("ועדת הכנסת", "لجنة الكنيست"), ("ועדת הכספים", "لجنة المالية"), ("ועדת החוקה, חוק ומשפט", "لجنة الدستور والقانون والقضاء"),
           ("הוועדה המסדרת", "اللجنة المنظمة"), ("בג\"ץ", "المحكمة العليا"), ("בתי דין רבניים", "المحاكم الحاخامية"),
           ("היועץ המשפטי לממשלה / היועצת המשפטית לממשלה", "المستشار القضائي للحكومة"),
           ("חרבות ברזל", "السيوف الحديدية"), ("ביטוח לאומי", "التأمين الوطني"), ("מועצה אזורית", "مجلس إقليمي"),
           ("חד\"ש", "الجبهة"), ("בל\"ד", "التجمع"), ("רע\"ם", "الموحدة"), ("תע\"ל", "العربية للتغيير"),
           ("הרשימה המשותפת", "القائمة المشتركة"), ("ש\"ס", "شاس"), ("הליכוד", "الليكود"), ("יש עתיד", "يش عتيد"),
           ("יהדות התורה", "يهدوت هتوراه"), ("ישראל ביתנו", "يسرائيل بيتينو"), ("כחול לבן", "أزرق أبيض"),
           # from the 50-title sample (2026-10-05): one wording for recurring phrases
           ("הצעת אי-אמון / הצעה להביע אי אמון בממשלה", "اقتراح حجب الثقة عن الحكومة"), ("בנושא", "بشأن"), ("מטעם סיעת / סיעות", "باسم كتلة / كتل"),
           ("הצעה רגילה / דחופה לסדר היום", "اقتراح عادي / عاجل لجدول الأعمال"), ("צער בעלי חיים", "الرفق بالحيوان"),
           ("ביטוח בריאות ממלכתי", "التأمين الصحي الرسمي"), ("אומנה", "الحضانة البديلة"), ("ועדה מחוזית / מחוז", "لجنة لوائية / لواء"),
           # bill references and Knesset numbers keep their digits (the checks reject Hebrew letters and lost numbers)
           ("(פ/3088/25) private bill reference; כ/ committee, מ/ government", "(ف/3088/25); ك/ ، م/"),
           ("הכנסת ה-25", "الكنيست الـ25"),
           ("אישור מסע אלקטרוני (Israel's ETA-IL)", "تصريح سفر إلكتروني (ETA-IL)"),
           # from the 20-bill sample of descriptions and debates (2026-10-08)
           ("דברי הסבר", "المذكرة التفسيرية"), ("המציעים / יוזמי ההצעה", "مقدمو الاقتراح"),
           ("דיינים (judges of the rabbinical courts; NOT sharia judges)", "قضاة المحاكم الحاخامية (الدايانيم)"),
           ("אסירים ביטחוניים", "الأسرى الأمنيون"), ("תקני כשרות / ריבוי תקנים (kashrut standards, not staff positions)", "معايير الكشروت"),
           ("מבצע עם כלביא (June 2025, Iran)", "عملية «الأسد الصاعد»"), ("מבצע מרכבות גדעון", "عملية «عربات جدعون»"),
           ("מבצע שאגת הארי", "عملية «زئير الأسد»"), ("ציני (cynical)", "انتهازي (not ساخر, which means sarcastic)"),
           ("מס יסף (the extra income tax on high incomes)", "الضريبة الإضافية")],
}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Translator(Protocol):
    model: str

    def translate(self, titles: Sequence[str], lang: str, kind: str = "title") -> list[str]: ...


class StubTranslator:
    """For tests and dry runs: a Latin marker that passes the checks (keeps the numbers, no Hebrew) and identifies
    the source by its hash prefix, instead of a translation."""

    model = "stub"

    @staticmethod
    def mark(text: str, lang: str) -> str:
        return " ".join([f"[{lang}]", sha256(text)[:12], *_DIGITS.findall(text)])

    def translate(self, titles: Sequence[str], lang: str, kind: str = "title") -> list[str]:
        return [self.mark(t, lang) for t in titles]


def system_prompt(lang: str, kind: str = "title") -> str:
    name = LANGUAGE_NAME[lang]
    glossary = "\n".join(f"- {he} → {tr}" for he, tr in GLOSSARY[lang])
    if kind in PROSE:
        what = {"summary": "the Knesset's official summaries of laws",
                "notes": "short descriptions of bills, written from the sponsors' explanatory notes (keep the attribution to the sponsors)",
                "positions": ("short neutral summaries of Knesset plenum debates and of the reservations filed to bills, and "
                              "one-sentence arguments made for or against a bill (keep each argument's wording neutral and "
                              "its attribution as it is)")}[kind]
        return (
            f"You translate {what} from Hebrew into {name} for a public "
            f"voting-record website. Each summary is a short paragraph of plain prose. Translate it faithfully and "
            f"completely, in clear neutral {name}: no omissions, no additions, no explanations, no editorialising. "
            f"Keep every number, amount, percentage and date as digits, never as a word (ה-90 is 'the 90th' or 'the 90s', "
            f"2 ילדים is '2 children', ערוץ 2 is 'Channel 2'). Dates: the Hebrew text often gives a "
            f"Hebrew-calendar date followed by the Gregorian one in parentheses, e.g. 'כ\"ג בשבט התשפ\"ז (31 בינואר 2027)'; "
            f"write only the Gregorian date ('31 January 2027'), never the Hebrew month, day or year. Law names follow the register of official "
            f"legal titles in {name}. Names of military operations are translated as {name}-language media name "
            f"them, never transliterated. Write every word in {name}: no Hebrew letters and no words of another language "
            f"(not «security-заключённые»). Where a Hebrew word has several senses, choose by context (תקן is a standard "
            f"in kashrut or regulation and a staff position in budgets). Use this glossary consistently:\n{glossary}\n"
            f"{LANGUAGE_NOTES.get(lang, '')}"
            f"Return only the translations, one per input, in the same order."
        )
    return (
        f"You translate titles of Israeli Knesset bills and plenum votes from Hebrew into {name} for a public "
        f"voting-record website. Translate each title faithfully and tersely, in the register of official legal "
        f"titles in {name}. Keep every number, amendment number and year exactly, as digits and never as a word "
        f"(פי 5 is '5-fold', 5 שנים is '5 years', שנות ה-50 is 'the 50s'); drop the Hebrew calendar year and "
        f"keep only the Gregorian one; keep parentheses and their order; do not add, explain or editorialise; do not "
        f"transliterate Hebrew words that have a standard {name} equivalent. Names of places, hospitals, companies, "
        f"organisations and customs that have none are written in {name} letters: the result has no Hebrew letter, "
        f"not even one inside a name. Use this glossary consistently:\n{glossary}\n"
        f"{LANGUAGE_NOTES.get(lang, '')}"
        f"Return only the translations, one per input, in the same order."
    )


LANGUAGE_NOTES = {
    "ar": ("Write Modern Standard Arabic as used on the Knesset website's Arabic pages and in Israeli Arabic-language "
           "media. Names of people are transliterated, never translated (ישראל as a first name is يسرائيل); party "
           "abbreviations become the Arabic party names in the glossary, not transliterations. "),
}


def model_for(lang: str, kind: str = "title") -> str:
    if kind in PROSE:
        return os.environ.get("HKV_TRANSLATE_MODEL_SUMMARY") or SUMMARY_MODEL
    return (os.environ.get(f"HKV_TRANSLATE_MODEL_{lang.upper()}") or LANGUAGE_MODELS.get(lang)
            or os.environ.get("HKV_TRANSLATE_MODEL") or DEFAULT_MODEL)


# Translation needs no reasoning, and Sonnet 5 thinks by default (billed as output); Haiku 4.5 does not.
NO_THINKING_PARAM = ("claude-haiku-",)
BATCH_POLL_SECONDS = 60
OUTPUT_FORMAT = {"format": {"type": "json_schema", "schema": {
    "type": "object",
    "properties": {"translations": {"type": "array", "items": {"type": "string"}}},
    "required": ["translations"], "additionalProperties": False,
}}}


class ClaudeTranslator:
    """Batches of titles through the Claude API with a JSON-schema output (one string per input). `translate` sends
    one request; `translate_many` sends many as one Message Batch (half price, results within hours), for backlogs."""

    def __init__(self, model: str | None = None):
        import anthropic  # imported here so the API and tests do not need the package

        self.client = anthropic.Anthropic()
        self.fixed_model = model  # None: per language (model_for)
        self.model = model or os.environ.get("HKV_TRANSLATE_MODEL", DEFAULT_MODEL)

    def model_for(self, lang: str, kind: str = "title") -> str:
        return self.fixed_model or model_for(lang, kind)

    def _params(self, titles: Sequence[str], lang: str, kind: str) -> dict:
        model = self.model_for(lang, kind)
        payload = json.dumps([{"n": i + 1, "he": t} for i, t in enumerate(titles)], ensure_ascii=False)
        params = dict(
            model=model,
            max_tokens=16000,
            system=[{"type": "text", "text": system_prompt(lang, kind), "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": f"Translate these {len(titles)} {kind}s:\n{payload}"}],
            output_config=OUTPUT_FORMAT,
        )
        if not model.startswith(NO_THINKING_PARAM):
            params["thinking"] = {"type": "disabled"}
        return params

    @staticmethod
    def _parse(message, n: int) -> list[str]:
        if message.stop_reason == "refusal":
            raise RuntimeError(f"translation refused: {message.stop_details}")
        text = next(b.text for b in message.content if b.type == "text")
        out = json.loads(text)["translations"]
        if len(out) != n:
            raise RuntimeError(f"expected {n} translations, got {len(out)}")
        return out

    def translate(self, titles: Sequence[str], lang: str, kind: str = "title") -> list[str]:
        return self._parse(self.client.messages.create(**self._params(titles, lang, kind)), len(titles))

    def translate_many(self, jobs: Sequence[tuple[str, str, Sequence[str]]]) -> list[list[str] | None]:
        """(lang, kind, texts) per request, all in one Message Batch; waits until it has ended. None where a request
        failed (the caller sends those again one by one)."""
        batch = self.client.messages.batches.create(requests=[
            {"custom_id": str(i), "params": self._params(texts, lang, kind)} for i, (lang, kind, texts) in enumerate(jobs)])
        log.info("message batch %s: %d requests", batch.id, len(jobs))
        while batch.processing_status != "ended":
            time.sleep(BATCH_POLL_SECONDS)
            batch = self.client.messages.batches.retrieve(batch.id)
            c = batch.request_counts
            log.info("message batch %s: %s, %d processing, %d succeeded, %d errored", batch.id, batch.processing_status,
                     c.processing, c.succeeded, c.errored)
        out: list[list[str] | None] = [None] * len(jobs)
        for r in self.client.messages.batches.results(batch.id):
            i = int(r.custom_id)
            if r.result.type != "succeeded":
                log.warning("message batch %s: request %d %s", batch.id, i, r.result.type)
                continue
            try:
                out[i] = self._parse(r.result.message, len(jobs[i][2]))
            except Exception:
                log.warning("message batch %s: request %d unusable", batch.id, i, exc_info=True)
        return out


# The site's spellings that a model sometimes misses, fixed before a translation is stored (they never change a
# number or a meaning): "Кнесет" is not a substring of "Кнессет", and the replacement keeps the ending (Кнесета).
SPELLING = {"ru": [(re.compile(r"Кнесет"), "Кнессет"), (re.compile(r"кнесет"), "кнессет")]}


# Glossary terms the checks enforce: where the Hebrew has the term, the translation must contain one of these (lower
# case, a stem where the word inflects). For terms a model has got wrong: "מס יסף" came out as "Nmexes" and as VAT.
# The Attorney General ("the government's legal adviser"): Russian titles had a dozen names for the office («Генеральный
# прокурор», «государственный советник», «юрисконсульт»…), so a search for one found a fraction of the laws. The term
# is matched without its first letter (ליועץ, היועץ) and in the feminine.
_ATTORNEY_GENERAL = {"en": ("attorney general", "attorney-general"),
                     "ru": ("юридический советник", "юридического советника", "юридическому советнику", "юридическим советник",
                            "юридическом советнике", "юридические советники", "юридических советник", "юридическая советниц",
                            "юридической советниц", "юридическую советницу"),
                     "ar": ("مستشار القضائي", "مستشارة القضائية")}
REQUIRED = [("מס יסף", {"en": ("surtax",), "ru": ("дополнительн",), "ar": ("إضافي",)}),
            ("יועץ המשפטי לממשלה", _ATTORNEY_GENERAL), ("יועצת המשפטית לממשלה", _ATTORNEY_GENERAL)]


# A number the translation rightly writes as a word: decades and ordinals read that way in Arabic ("التسعينيات",
# "القناة الثانية"), and small numbers sometimes in every language ("five-fold", "one-twelfth", "the first schedule"). Lower-case stems per language; a
# number whose word is in the translation is not missing.
NUMBER_WORDS = {
    "en": {"1": ("first", "one-", " one "), "12": ("twel",), "2": ("two", "second", "twice"), "3": ("three", "third"), "4": ("four",), "5": ("five", "fifth"), "6": ("six",),
           "7": ("seven",), "8": ("eight",), "9": ("nine", "ninth"), "10": ("ten",), "20": ("twent",), "30": ("thirt",),
           "40": ("fort",), "50": ("fift",), "60": ("sixt",), "70": ("sevent",), "80": ("eight",), "90": ("ninet",)},
    "ru": {"1": ("перв", " один ", " одна ", " одно "), "12": ("двенадцат",), "2": ("дв", "втор"), "3": ("тр", "трет"), "4": ("четыр", "четв"), "5": ("пят",), "6": ("шест",), "7": ("сем", "седьм"),
           "8": ("восьм", "восем"), "9": ("девят",), "10": ("десят",), "20": ("двадцат",), "30": ("тридцат",), "40": ("сорок", "сороков"),
           "50": ("пятидесят", "пятьдесят"), "60": ("шестидесят", "шестьдесят"), "70": ("семидесят", "семьдесят"),
           "80": ("восьмидесят", "восемьдесят"), "90": ("девяност",)},
    "ar": {"1": ("الأول", "واحد"), "12": ("اثني عشر", "اثنا عشر", "الثاني عشر", "الثانية عشرة"), "2": ("اثن", "ثاني"), "3": ("ثلاث", "ثالث"), "4": ("أربع", "رابع"), "5": ("خمس", "خامس"), "6": ("ست", "سادس"),
           "7": ("سبع", "سابع"), "8": ("ثمان", "ثامن"), "9": ("تسع", "تاسع"), "10": ("عشر", "عاشر"), "20": ("عشرين", "عشرون"),
           "30": ("ثلاثين", "ثلاثون"), "40": ("أربعين", "أربعون"), "50": ("خمسين", "خمسون"), "60": ("ستين", "ستون"),
           "70": ("سبعين", "سبعون"), "80": ("ثمانين", "ثمانون"), "90": ("تسعين", "تسعون")},
}

# Arabic only: the model now and then leaves a Hebrew letter inside a name it is writing in Arabic letters
# ("برזيلي", "بזק"). Inside a word that has Arabic letters, each Hebrew letter becomes its Arabic counterpart; a word
# left wholly in Hebrew is not touched and still fails the check.
_HE_TO_AR = str.maketrans({"א": "ا", "ב": "ب", "ג": "غ", "ד": "د", "ה": "ه", "ו": "و", "ז": "ز", "ח": "ح", "ט": "ط", "י": "ي",
                           "כ": "ك", "ך": "ك", "ל": "ل", "מ": "م", "ם": "م", "נ": "ن", "ן": "ن", "ס": "س", "ע": "ع", "פ": "ف",
                           "ף": "ف", "צ": "ص", "ץ": "ص", "ק": "ق", "ר": "ر", "ש": "ش", "ת": "ت"})
_MIXED_WORD = re.compile(r"[^\s]*[\u0600-\u06FF][^\s]*")


def one_script(text: str, lang: str) -> str:
    """Arabic: Hebrew letters inside a word written in Arabic letters, as Arabic letters. Other languages: unchanged."""
    if lang != "ar":
        return text
    return _MIXED_WORD.sub(lambda m: m[0].translate(_HE_TO_AR) if _HEBREW.search(m[0]) else m[0], text)


def spell(text: str, lang: str) -> str:
    for pattern, repl in SPELLING.get(lang, []):
        text = pattern.sub(repl, text)
    return text


def check(source: str, target: str, kind: str = "title", lang: str | None = None) -> str | None:
    """Why a translation must not be stored, or None. Numbers must survive, Hebrew must not, length must be sane, and
    with `lang` the enforced glossary terms (REQUIRED) must be there.
    In a summary a numeric date ("1.4.2026", "31.03") is written with the month as a word ("1 April 2026"), so only
    its day and year have to survive; thousands separators and leading zeros may change; section numbers may keep
    their Hebrew letters."""
    if not target or not target.strip():
        return "empty"
    if _HEBREW.search(_SECTION_LETTERS.sub("", target) if kind in PROSE else target):
        return "hebrew_left"
    waived = {n for words, n in SOURCE_TYPOS + IDIOMS if words in source}
    if kind in PROSE:
        source = _HEBREW_DAY.sub("", source)
        source = _NUMERIC_DATE.sub(lambda m: f"{int(m[1])} {m[3]}", source)
        source = _SHORT_DATE.sub(lambda m: str(int(m[1])) if 1 <= int(m[1]) <= 31 and 1 <= int(m[2]) <= 12 else m[0], source)
        target = _THOUSANDS.sub("", target)
        missing = [d for d in _DIGITS.findall(source) if str(int(d)) not in target]
    else:
        # "ה-07 באוקטובר" is rightly "7 October": a leading zero may go, the number may not
        missing = [d for d in _DIGITS.findall(source) if d not in target and str(int(d)) not in _DIGITS.findall(target)
                   and not _is_hebrew_year(source, d)]
    words = NUMBER_WORDS.get(lang or "", {})
    low = target.lower()
    missing = [d for d in missing if d not in waived and not any(w in low for w in words.get(str(int(d)), ()))]
    if missing:
        return f"numbers_missing:{','.join(missing)}"
    if len(target) > 3 * len(source) + 40:
        return "too_long"
    return missing_term(source, target, lang) if lang else None


def missing_term(source: str, target: str, lang: str) -> str | None:
    for term, wanted in REQUIRED:
        if term in source and lang in wanted and not any(w in target.lower() for w in wanted[lang]):
            return f"term_missing:{term}"
    return None


def _is_hebrew_year(source: str, digits: str) -> bool:
    """A Gregorian year in the source is kept; the Hebrew year has no digits, so no digit is ever exempt. Hook for later."""
    return False


SOURCES = {
    "title": """SELECT b.title_he AS t, max(v.occurred_on) AS last FROM bill b
                JOIN vote_subject vs ON vs.bill_id = b.id JOIN vote v ON v.id = vs.vote_id GROUP BY 1
                UNION ALL
                SELECT v.title_he, max(v.occurred_on) FROM vote v GROUP BY 1""",
    # only bills that were voted on in the plenum: the site has no page for the others
    "summary": """SELECT b.summary_he AS t, max(v.occurred_on) AS last FROM bill b
                  JOIN vote_subject vs ON vs.bill_id = b.id JOIN vote v ON v.id = vs.vote_id GROUP BY 1""",
    "notes": """SELECT e.summary_he AS t, max(v.occurred_on) AS last FROM bill_explanation e
                JOIN vote_subject vs ON vs.bill_id = e.bill_id JOIN vote v ON v.id = vs.vote_id GROUP BY 1""",
    "positions": """SELECT d.summary_he AS t, v.occurred_on AS last FROM bill_debate d JOIN vote v ON v.id = d.vote_id
                    UNION ALL
                    SELECT a->>'text_he', v.occurred_on FROM bill_debate d JOIN vote v ON v.id = d.vote_id
                    CROSS JOIN jsonb_array_elements(d.arguments) a
                    UNION ALL
                    SELECT t, max(v.occurred_on) FROM (SELECT r.bill_id, r.summary_he AS t FROM bill_reservations r
                                                       UNION ALL SELECT g.bill_id, g.gist_he FROM bill_reservation_group g) x
                    JOIN vote_subject vs ON vs.bill_id = x.bill_id JOIN vote v ON v.id = vs.vote_id GROUP BY t""",
}


def pending(conn: psycopg.Connection, lang: str, limit: int | None = None, retry_failed: bool = False,
            since: str | None = None, kind: str = "title") -> list[tuple[str, str]]:
    """(sha, hebrew) of distinct texts of `kind` without a translation in `lang`, most recently voted first.
    Texts with an open failed-check issue in `lang` are left out unless `retry_failed`; `since` (ISO date) keeps
    texts last voted on or after that date."""
    rows = conn.execute(
        f"""WITH src AS ({SOURCES[kind]})
           SELECT t, title_sha(t) AS h FROM src
           WHERE t IS NOT NULL AND t <> ''
           GROUP BY t HAVING NOT EXISTS (SELECT 1 FROM text_translation x WHERE x.source_sha256 = title_sha(t) AND x.language = %(lang)s)
              AND (%(since)s::date IS NULL OR max(last) >= %(since)s::date)
              AND (%(retry)s OR NOT EXISTS (SELECT 1 FROM data_issue i WHERE i.issue_type = 'translation_check_failed' AND i.status = 'open'
                                            AND i.external_ref = title_sha(t) AND i.details->>'language' = %(lang)s))
           ORDER BY max(last) DESC NULLS LAST""" + (" LIMIT %(limit)s" if limit else ""),
        {"lang": lang, "retry": retry_failed, "limit": limit, "since": since}).fetchall()
    return [(r[1], r[0]) for r in rows]


def _translate_batch(translator: Translator, batch: list[tuple[str, str]], lang: str, kind: str = "title") -> list[tuple[str, str, str]]:
    """(sha, source, target) for a batch. If the batch fails (e.g. the model returned 21 translations for 20 titles),
    each title is sent alone, so one odd title costs one retry instead of 20 untranslated titles."""
    try:
        out = translator.translate([t for _, t in batch], lang, kind)
        return [(h, source, target) for (h, source), target in zip(batch, out, strict=True)]
    except Exception:
        if len(batch) == 1:
            log.exception("translation failed (%s): %s", lang, batch[0][1][:120])
            return []
        log.warning("translation batch failed (%s, %d titles); retrying one by one", lang, len(batch), exc_info=True)
        return [row for item in batch for row in _translate_batch(translator, [item], lang, kind)]


def sync(conn: psycopg.Connection, translator: Translator, langs: Iterable[str] = LANGUAGES, limit: int | None = None,
         retry_failed: bool = False, since: str | None = None, kinds: Iterable[str] = KINDS, batch: bool = False) -> dict:
    """Translate what is missing, store what passes the checks, log the rest as data_issue rows (one open issue per
    text and language; it is resolved once the text gets a translation). Counts are keyed `en`, `en_failed` for
    titles and `en_summary`, `en_summary_failed` for summaries. `batch`: everything pending, in every language, goes
    as one Message Batch first (translators with `translate_many`); requests that failed in it are sent directly."""
    plan = []
    apply_fixes(conn)
    for lang in langs:
        _resolve_translated(conn, lang)
        for kind in kinds:
            model = getattr(translator, "model_for", lambda *_: translator.model)(lang, kind)
            plan.append((lang, kind, model, pending(conn, lang, limit, retry_failed, since, kind)))
    batched: dict[tuple[str, str, int], list[str] | None] = {}
    if batch and hasattr(translator, "translate_many"):
        keys = [(lang, kind, i) for lang, kind, _, todo in plan for i in range(0, len(todo), BATCH[kind])]
        jobs = [(lang, kind, [t for _, t in todo[i:i + BATCH[kind]]]) for lang, kind, _, todo in plan for i in range(0, len(todo), BATCH[kind])]
        if jobs:
            batched = dict(zip(keys, translator.translate_many(jobs), strict=True))
    counts: dict[str, int] = {}
    for lang, kind, model, todo in plan:
        stored = failed = 0
        for i in range(0, len(todo), BATCH[kind]):
            chunk = todo[i:i + BATCH[kind]]
            out = batched.get((lang, kind, i))
            rows = ([(h, source, target) for (h, source), target in zip(chunk, out, strict=True)] if out is not None
                    else _translate_batch(translator, chunk, lang, kind))
            for h, source, target in rows:
                target = one_script(target, lang)
                why = check(source, target, kind, lang)
                if why:
                    failed += 1
                    details = json.dumps({"language": lang, "kind": kind, "reason": why, "source": source, "target": target, "model": model})
                    if not conn.execute(
                            """UPDATE data_issue SET details = %s WHERE issue_type = 'translation_check_failed' AND status = 'open'
                               AND external_ref = %s AND details->>'language' = %s""", (details, h, lang)).rowcount:
                        conn.execute(
                            """INSERT INTO data_issue (external_ref, issue_type, severity, details)
                               VALUES (%s, 'translation_check_failed', 'warning', %s)""", (h, details))
                    continue
                conn.execute(
                    """INSERT INTO text_translation (source_sha256, language, text, origin, model) VALUES (%s, %s, %s, 'machine', %s)
                       ON CONFLICT (source_sha256, language) DO NOTHING""", (h, lang, spell(target.strip(), lang), model))
                stored += 1
            _resolve_translated(conn, lang)
            conn.commit()
        key = lang if kind == "title" else f"{lang}_{kind}"
        counts[key] = stored
        counts[f"{key}_failed"] = failed
        log.info("translate %s %s: %d stored, %d failed checks, %d were pending", lang, kind, stored, failed, len(todo))
    return counts


def recheck_failed(conn: psycopg.Connection) -> dict[str, int]:
    """Run the current checks again on translations that failed earlier ones (the target is kept in the issue), and
    store those that pass now. No API call: after a check is relaxed, the earlier work is not paid for twice."""
    counts: dict[str, int] = {"open": 0, "stored": 0, "fixes": apply_fixes(conn)}
    for lang in LANGUAGES:
        _resolve_translated(conn, lang)
    for h, d in conn.execute("""SELECT external_ref, details FROM data_issue
                                 WHERE issue_type = 'translation_check_failed' AND status = 'open'""").fetchall():
        counts["open"] += 1
        if d.get("target"):
            d["target"] = one_script(d["target"], d["language"])
        if d.get("target") and check(d["source"], d["target"], d.get("kind", "title"), d["language"]) is None:
            conn.execute("""INSERT INTO text_translation (source_sha256, language, text, origin, model) VALUES (%s, %s, %s, 'machine', %s)
                            ON CONFLICT (source_sha256, language) DO NOTHING""", (h, d["language"], spell(d["target"].strip(), d["language"]), d.get("model")))
            counts["stored"] += 1
    for lang in LANGUAGES:
        _resolve_translated(conn, lang)
    conn.commit()
    log.info("recheck: %s", counts)
    return counts


def apply_fixes(conn: psycopg.Connection) -> int:
    """Store the hand-corrected machine translations of fixes.toml for texts that have none yet. No API call. A fix
    that fails the checks is not stored (and is logged): the file gets no way around them."""
    stored = 0
    for f in tomllib.loads((Path(__file__).parent / "fixes.toml").read_text())["fix"]:
        lang, text = f["language"], one_script(f["text"], f["language"])
        why = check(f["he"], text, f.get("kind", "title"), lang)
        if why:
            log.warning("fixes.toml: a %s fix fails the check (%s): %s", lang, why, f["he"][:60])
            continue
        stored += conn.execute(
            """INSERT INTO text_translation (source_sha256, language, text, origin, model) VALUES (%s, %s, %s, 'machine', %s)
               ON CONFLICT (source_sha256, language) DO NOTHING""", (sha256(f["he"]), lang, spell(text.strip(), lang), f.get("model"))).rowcount
    conn.commit()
    return stored


def drop_missing_terms(conn: psycopg.Connection) -> dict[str, int]:
    """Delete stored machine translations that lack an enforced glossary term (REQUIRED), so the next run translates
    them again with the term in the prompt. No API call. Translations an editor wrote or approved are kept."""
    counts: dict[str, int] = {}
    for kind in KINDS:
        for term, wanted in REQUIRED:
            rows = conn.execute(
                f"""WITH src AS ({SOURCES[kind]})
                    SELECT DISTINCT x.source_sha256, x.language, s.t, x.text FROM src s
                    JOIN text_translation x ON x.source_sha256 = title_sha(s.t)
                    WHERE s.t LIKE %s AND x.origin = 'machine'""", (f"%{term}%",)).fetchall()
            for h, lang, source, text in rows:
                if missing_term(source, text, lang):
                    conn.execute("DELETE FROM text_translation WHERE source_sha256 = %s AND language = %s AND origin = 'machine'", (h, lang))
                    counts[lang] = counts.get(lang, 0) + 1
    conn.commit()
    log.info("dropped translations missing a glossary term: %s", counts)
    return counts


def _resolve_translated(conn: psycopg.Connection, lang: str) -> None:
    """Failed-check issues of titles that have a translation now (a later run or an editor) are resolved."""
    conn.execute(
        """UPDATE data_issue i SET status = 'resolved', resolved_at = now()
           WHERE i.issue_type = 'translation_check_failed' AND i.status = 'open' AND i.details->>'language' = %s
             AND EXISTS (SELECT 1 FROM text_translation x WHERE x.source_sha256 = i.external_ref AND x.language = %s)""", (lang, lang))
