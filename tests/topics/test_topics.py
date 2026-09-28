from __future__ import annotations

import psycopg
import pytest

from hkv.topics import classify_title, faction_ru, he_norm


@pytest.mark.parametrize("raw", ['מע"מ', "מע״מ", "מָע״מ", 'חוק־יסוד: הכנסת (תיקון מס\' 50 – הוראת שעה)', "צה\"ל", "  a  -  b "])
def test_python_and_sql_normalisation_agree(migrated, raw):
    with psycopg.connect(migrated) as conn:
        assert conn.execute("SELECT he_norm(%s)", (raw,)).fetchone()[0] == he_norm(raw)


def test_amendment_number_is_not_tax():
    assert "taxes" not in classify_title("הצעת חוק הרשות לפיתוח הנגב (תיקון מס' 4), התשפ\"ו-2026")
    assert classify_title("הצעת חוק מס ערך מוסף (תיקון מס' 70)")["taxes"] == "מס ערך מוסף"


@pytest.mark.parametrize(("title", "slug"), [
    ("הצעת חוק שירותי תעופה (פיצוי וסיוע בשל ביטול טיסה)", "transport"),
    ("הצעת חוק-יסוד: הכנסת (תיקון מס' 50 – הוראת שעה)", "governance"),
    ("הצעת חוק ההוצאה לפועל (הקפאת הגבלת רישיונות נהיגה) (הוראת שעה - נגיף הקורונה החדש)", "emergency"),
    ("הצעת חוק ההוצאה לפועל (הקפאת הגבלת רישיונות נהיגה)", "transport"),
    ("הצעת חוק ביטוח בריאות ממלכתי (תיקון מס' 60)", "health"),
    ("הצעת חוק לתיקון פקודת המשטרה (סמכויות)", "police"),
])
def test_classify_examples(title, slug):
    assert slug in classify_title(title)


def test_prefixes_and_whole_words():
    assert "housing" in classify_title("הצעת חוק לדירות להשכרה ולדיור מוגן")  # ל + דיור
    assert "religion" not in classify_title("הצעת חוק שבתאי")                 # שבת inside another word
    assert "religion" not in classify_title("הצעת חוק להשבת כפיפות בתי הדין")  # לה is not a prefix sequence
    assert "religion" in classify_title("הצעת חוק הפעלת תחבורה ציבורית בשבת")   # ב + שבת


@pytest.mark.parametrize(("he", "ru"), [
    ("הליכוד ", "Ликуд"), ("ימין חדש", "Новые правые"), ('חד"ש-תע"ל', "ХАДАШ–ТААЛЬ"),
    ("הרשימה המשותפת (חד\"ש, רע\"מ, תע\"ל, בל\"ד)", "Объединённый арабский список"),
    ('התאחדות הספרדים שומרי תורה תנועתו של מרן הרב עובדיה יוסף זצ"ל', "ШАС"), ("סיעה לא מוכרת", None),
])
def test_faction_russian_names(he, ru):
    assert faction_ru(he) == ru


def test_national_insurance_is_welfare_not_finance():
    t = classify_title("הצעת חוק הביטוח הלאומי (תיקון מס' 230)")
    assert "welfare" in t and "finance-consumer" not in t
