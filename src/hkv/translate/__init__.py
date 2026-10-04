"""Machine translation of Hebrew titles (docs/ux-requirements.md R4; roadmap L6).

Distinct Hebrew strings (bill and vote titles) are translated once per language and stored by the SHA-256 of the
source in text_translation. A fixed glossary keeps 3,600 titles consistent; automatic checks reject translations
that lose a number or keep Hebrew letters, and log them as data_issue rows instead of storing them. The translator
is pluggable: ClaudeTranslator in production, StubTranslator in tests.
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
BATCH = 20
DEFAULT_MODEL = "claude-opus-5-5"

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
           ("תקנות", "أنظمة"), ("הצעת אי-אמון", "اقتراح حجب الثقة"), ("התשפ\"ו-2026", "2026")],
}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Translator(Protocol):
    model: str

    def translate(self, titles: Sequence[str], lang: str) -> list[str]: ...


class StubTranslator:
    """For tests and dry runs: a Latin marker that passes the checks (keeps the numbers, no Hebrew) and identifies
    the source by its hash prefix, instead of a translation."""

    model = "stub"

    @staticmethod
    def mark(text: str, lang: str) -> str:
        return " ".join([f"[{lang}]", sha256(text)[:12], *_DIGITS.findall(text)])

    def translate(self, titles: Sequence[str], lang: str) -> list[str]:
        return [self.mark(t, lang) for t in titles]


def system_prompt(lang: str) -> str:
    name = LANGUAGE_NAME[lang]
    glossary = "\n".join(f"- {he} → {tr}" for he, tr in GLOSSARY[lang])
    return (
        f"You translate titles of Israeli Knesset bills and plenum votes from Hebrew into {name} for a public "
        f"voting-record website. Translate each title faithfully and tersely, in the register of official legal "
        f"titles in {name}. Keep every number, amendment number and year exactly; drop the Hebrew calendar year and "
        f"keep only the Gregorian one; keep parentheses and their order; do not add, explain or editorialise; do not "
        f"transliterate Hebrew words that have a standard {name} equivalent. Use this glossary consistently:\n{glossary}\n"
        f"Return only the translations, one per input, in the same order."
    )


class ClaudeTranslator:
    """Batches of titles through the Claude API with a JSON-schema output (one string per input)."""

    def __init__(self, model: str | None = None):
        import anthropic  # imported here so the API and tests do not need the package

        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("HKV_TRANSLATE_MODEL", DEFAULT_MODEL)

    def translate(self, titles: Sequence[str], lang: str) -> list[str]:
        payload = json.dumps([{"n": i + 1, "he": t} for i, t in enumerate(titles)], ensure_ascii=False)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            system=[{"type": "text", "text": system_prompt(lang), "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": f"Translate these {len(titles)} titles:\n{payload}"}],
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


def pending(conn: psycopg.Connection, lang: str, limit: int | None = None) -> list[tuple[str, str]]:
    """(sha, hebrew) of distinct bill and vote titles without a translation in `lang`, most recently voted first."""
    rows = conn.execute(
        """WITH src AS (
               SELECT b.title_he AS t, max(v.occurred_on) AS last FROM bill b
               JOIN vote_subject vs ON vs.bill_id = b.id JOIN vote v ON v.id = vs.vote_id GROUP BY 1
               UNION ALL
               SELECT v.title_he, max(v.occurred_on) FROM vote v GROUP BY 1)
           SELECT t, title_sha(t) AS h FROM src
           WHERE t IS NOT NULL AND t <> ''
           GROUP BY t HAVING NOT EXISTS (SELECT 1 FROM text_translation x WHERE x.source_sha256 = title_sha(t) AND x.language = %s)
           ORDER BY max(last) DESC NULLS LAST""" + (" LIMIT %s" if limit else ""),
        (lang, limit) if limit else (lang,)).fetchall()
    return [(r[1], r[0]) for r in rows]


def sync(conn: psycopg.Connection, translator: Translator, langs: Iterable[str] = LANGUAGES, limit: int | None = None) -> dict:
    """Translate what is missing, store what passes the checks, log the rest as data_issue rows."""
    counts: dict[str, int] = {}
    for lang in langs:
        todo = pending(conn, lang, limit)
        stored = failed = 0
        for i in range(0, len(todo), BATCH):
            batch = todo[i:i + BATCH]
            try:
                out = translator.translate([t for _, t in batch], lang)
            except Exception:  # one bad batch must not stop the run; the titles stay pending
                log.exception("translation batch failed (%s, %d titles)", lang, len(batch))
                continue
            for (h, source), target in zip(batch, out):
                why = check(source, target)
                if why:
                    failed += 1
                    conn.execute(
                        """INSERT INTO data_issue (external_ref, issue_type, severity, details)
                           VALUES (%s, 'translation_check_failed', 'warning', %s)""",
                        (h, json.dumps({"language": lang, "reason": why, "source": source, "target": target, "model": translator.model})))
                    continue
                conn.execute(
                    """INSERT INTO text_translation (source_sha256, language, text, origin, model) VALUES (%s, %s, %s, 'machine', %s)
                       ON CONFLICT (source_sha256, language) DO NOTHING""", (h, lang, target.strip(), translator.model))
                stored += 1
            conn.commit()
        counts[lang] = stored
        counts[f"{lang}_failed"] = failed
        log.info("translate %s: %d stored, %d failed checks, %d were pending", lang, stored, failed, len(todo))
    return counts
