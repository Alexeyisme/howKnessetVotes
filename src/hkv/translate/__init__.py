"""Machine translation of Hebrew titles and official bill summaries (docs/ux-requirements.md R4; roadmap L6, L7).

Distinct Hebrew strings (bill and vote titles) are translated once per language and stored by the SHA-256 of the
source in text_translation. A fixed glossary keeps ~22,000 titles consistent; automatic checks reject translations
that lose a number or keep Hebrew letters, and log them as data_issue rows instead of storing them. The translator
is pluggable: ClaudeTranslator in production, StubTranslator in tests.

Two kinds of text share the table and the checks: "title" (bill and vote titles) and "summary" (the official
`SummaryLaw` of a bill, a paragraph of plain prose, so it gets its own prompt and smaller batches).

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
from collections.abc import Iterable, Sequence
from typing import Protocol

import psycopg

log = logging.getLogger(__name__)

LANGUAGES = ("en", "ru", "ar")
KINDS = ("title", "summary")
BATCH = {"title": 20, "summary": 5}   # a summary averages ~850 Hebrew characters, the longest ~6,400
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

LANGUAGE_NAME = {"en": "English", "ru": "Russian", "ar": "Arabic"}

# Terms that must read the same in every title. The Hebrew year ("התשפ\"ו-2026") keeps only the Gregorian year.
GLOSSARY = {
    "en": [("הצעת חוק", "Bill"), ("חוק", "Law"), ("חוק-יסוד / חוק יסוד", "Basic Law"), ("תיקון מס' N", "Amendment No. N"),
           ("הוראת שעה", "temporary provision"), ("תיקוני חקיקה", "legislative amendments"), ("פקודת", "Ordinance"),
           ("תקנות", "Regulations"), ("הצעת אי-אמון", "no-confidence motion"), ("התשפ\"ו-2026", "2026")],
    "ru": [("הצעת חוק", "Законопроект"), ("חוק", "Закон"), ("חוק-יסוד / חוק יסוד", "Основной закон"), ("תיקון מס' N", "поправка № N"),
           ("הוראת שעה", "временное положение"), ("תיקוני חקיקה", "поправки к законодательству"), ("פקודת", "Указ"),
           ("תקנות", "Правила"), ("הצעת אי-אמון", "вотум недоверия"), ("התשפ\"ו-2026", "2026")],
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
           ("הכנסת ה-25", "الكنيست الـ25")],
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
    if kind == "summary":
        return (
            f"You translate the Knesset's official summaries of laws from Hebrew into {name} for a public "
            f"voting-record website. Each summary is a short paragraph of plain prose. Translate it faithfully and "
            f"completely, in clear neutral {name}: no omissions, no additions, no explanations, no editorialising. "
            f"Keep every number, amount, percentage and date as digits. Dates: the Hebrew text often gives a "
            f"Hebrew-calendar date followed by the Gregorian one in parentheses, e.g. 'כ\"ג בשבט התשפ\"ז (31 בינואר 2027)'; "
            f"write only the Gregorian date ('31 January 2027'), never the Hebrew month, day or year. Law names follow the register of official "
            f"legal titles in {name}. Use this glossary consistently:\n{glossary}\n"
            f"{LANGUAGE_NOTES.get(lang, '')}"
            f"Return only the translations, one per input, in the same order."
        )
    return (
        f"You translate titles of Israeli Knesset bills and plenum votes from Hebrew into {name} for a public "
        f"voting-record website. Translate each title faithfully and tersely, in the register of official legal "
        f"titles in {name}. Keep every number, amendment number and year exactly; drop the Hebrew calendar year and "
        f"keep only the Gregorian one; keep parentheses and their order; do not add, explain or editorialise; do not "
        f"transliterate Hebrew words that have a standard {name} equivalent. Use this glossary consistently:\n{glossary}\n"
        f"{LANGUAGE_NOTES.get(lang, '')}"
        f"Return only the translations, one per input, in the same order."
    )


LANGUAGE_NOTES = {
    "ar": ("Write Modern Standard Arabic as used on the Knesset website's Arabic pages and in Israeli Arabic-language "
           "media. Names of people are transliterated, never translated (ישראל as a first name is يسرائيل); party "
           "abbreviations become the Arabic party names in the glossary, not transliterations. "),
}


def model_for(lang: str, kind: str = "title") -> str:
    if kind == "summary":
        return os.environ.get("HKV_TRANSLATE_MODEL_SUMMARY") or SUMMARY_MODEL
    return (os.environ.get(f"HKV_TRANSLATE_MODEL_{lang.upper()}") or LANGUAGE_MODELS.get(lang)
            or os.environ.get("HKV_TRANSLATE_MODEL") or DEFAULT_MODEL)


class ClaudeTranslator:
    """Batches of titles through the Claude API with a JSON-schema output (one string per input)."""

    def __init__(self, model: str | None = None):
        import anthropic  # imported here so the API and tests do not need the package

        self.client = anthropic.Anthropic()
        self.fixed_model = model  # None: per language (model_for)
        self.model = model or os.environ.get("HKV_TRANSLATE_MODEL", DEFAULT_MODEL)

    def model_for(self, lang: str, kind: str = "title") -> str:
        return self.fixed_model or model_for(lang, kind)

    def translate(self, titles: Sequence[str], lang: str, kind: str = "title") -> list[str]:
        payload = json.dumps([{"n": i + 1, "he": t} for i, t in enumerate(titles)], ensure_ascii=False)
        response = self.client.messages.create(
            model=self.model_for(lang, kind),
            max_tokens=16000,
            system=[{"type": "text", "text": system_prompt(lang, kind), "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": f"Translate these {len(titles)} {kind}s:\n{payload}"}],
            output_config={"format": {"type": "json_schema", "schema": {
                "type": "object",
                "properties": {"translations": {"type": "array", "items": {"type": "string"}}},
                "required": ["translations"], "additionalProperties": False,
            }}},
        )
        if response.stop_reason == "refusal":
            raise RuntimeError(f"translation refused: {response.stop_details}")
        text = next(b.text for b in response.content if b.type == "text")
        out = json.loads(text)["translations"]
        if len(out) != len(titles):
            raise RuntimeError(f"expected {len(titles)} translations, got {len(out)}")
        return out


def check(source: str, target: str) -> str | None:
    """Why a translation must not be stored, or None. Numbers must survive, Hebrew must not, length must be sane."""
    if not target or not target.strip():
        return "empty"
    if _HEBREW.search(target):
        return "hebrew_left"
    missing = [d for d in _DIGITS.findall(source) if d not in target and not _is_hebrew_year(source, d)]
    if missing:
        return f"numbers_missing:{','.join(missing)}"
    if len(target) > 3 * len(source) + 40:
        return "too_long"
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
         retry_failed: bool = False, since: str | None = None, kinds: Iterable[str] = KINDS) -> dict:
    """Translate what is missing, store what passes the checks, log the rest as data_issue rows (one open issue per
    text and language; it is resolved once the text gets a translation). Counts are keyed `en`, `en_failed` for
    titles and `en_summary`, `en_summary_failed` for summaries."""
    counts: dict[str, int] = {}
    for lang in langs:
        _resolve_translated(conn, lang)
        for kind in kinds:
            model = getattr(translator, "model_for", lambda *_: translator.model)(lang, kind)
            todo = pending(conn, lang, limit, retry_failed, since, kind)
            stored = failed = 0
            for i in range(0, len(todo), BATCH[kind]):
                for h, source, target in _translate_batch(translator, todo[i:i + BATCH[kind]], lang, kind):
                    why = check(source, target)
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
                           ON CONFLICT (source_sha256, language) DO NOTHING""", (h, lang, target.strip(), model))
                    stored += 1
                _resolve_translated(conn, lang)
                conn.commit()
            key = lang if kind == "title" else f"{lang}_{kind}"
            counts[key] = stored
            counts[f"{key}_failed"] = failed
            log.info("translate %s %s: %d stored, %d failed checks, %d were pending", lang, kind, stored, failed, len(todo))
    return counts


def _resolve_translated(conn: psycopg.Connection, lang: str) -> None:
    """Failed-check issues of titles that have a translation now (a later run or an editor) are resolved."""
    conn.execute(
        """UPDATE data_issue i SET status = 'resolved', resolved_at = now()
           WHERE i.issue_type = 'translation_check_failed' AND i.status = 'open' AND i.details->>'language' = %s
             AND EXISTS (SELECT 1 FROM text_translation x WHERE x.source_sha256 = i.external_ref AND x.language = %s)""", (lang, lang))
