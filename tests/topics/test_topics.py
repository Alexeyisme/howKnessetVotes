from __future__ import annotations

import psycopg
import pytest

from hkv.topics import ar_norm, classify_title, faction_ru, he_norm


@pytest.mark.parametrize("raw", ['מע"מ', "מע״מ", "מָע״מ", 'חוק־יסוד: הכנסת (תיקון מס\' 50 – הוראת שעה)', "צה\"ל", "  a  -  b "])
def test_python_and_sql_normalisation_agree(migrated, raw):
    with psycopg.connect(migrated) as conn:
        assert conn.execute("SELECT he_norm(%s)", (raw,)).fetchone()[0] == he_norm(raw)



@pytest.mark.parametrize("raw", ["أحمد الطيبي", "إيتمار بن غفير", "أيمن عودة", "مُسْتَشْفَى", "آفي  معوز", "مـسـؤولية", "Ra'am"])
def test_python_and_sql_arabic_normalisation_agree(migrated, raw):
    with psycopg.connect(migrated) as conn:
        assert conn.execute("SELECT ar_norm(%s)", (raw,)).fetchone()[0] == ar_norm(raw)
    assert ar_norm("أيمن عودة") == ar_norm("ايمن عوده")

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


def test_legal_capacity_is_not_kashrut():
    assert "religion" not in classify_title("הצעת חוק הכשרות המשפטית והאפוטרופסות (תיקון מס' 22), התשפ\"ה-2025")
    assert classify_title("הצעת חוק איסור הונאה בכשרות (תיקון), התשע\"ז-2017")["religion"] == "כשרות"


def test_official_law_classification(new_database):
    """Primary law = the one named in the bill title; a bill with more than three official topics gets none."""
    from hkv.topics import sync
    from hkv.topics.official import mark_primary
    from tests.ingest.test_loader import SLICE, ingest
    url = new_database()
    ingest(url, SLICE)
    with psycopg.connect(url, autocommit=True) as conn:
        bills = conn.execute("SELECT id, title_he FROM bill ORDER BY knesset_bill_id LIMIT 2").fetchall()
        (b1, title1), (b2, _) = bills
        named = title1.removeprefix("הצעת ").split(" (")[0].split(",")[0]
        conn.execute("INSERT INTO israel_law VALUES (1, %s, false, false), (2, 'חוק אחר, התשי\"ח-1958', false, false), (3, 'חוק שלישי', false, false)",
                     (f"{named}, התשנ\"ה-1995",))
        conn.execute("""INSERT INTO israel_law_classification VALUES (1, 7, 'בריאות'), (2, 19, 'מיסוי'),
                        (3, 3, 'ביטחון'), (3, 14, 'חינוך'), (3, 37, 'רווחה'), (3, 45, 'תעסוקה')""")
        conn.execute("INSERT INTO bill_law (bill_id, israel_law_id, binding_type_he) VALUES (%s, 1, 'מתקן'), (%s, 2, 'מתקן'), (%s, 3, 'מתקן')",
                     (b1, b1, b2))
        mark_primary(conn)
        sync(conn)
        official = lambda b: {r[0] for r in conn.execute(  # noqa: E731
            "SELECT t.slug FROM bill_topic bt JOIN topic t ON t.id = bt.topic_id WHERE bt.bill_id = %s AND bt.origin = 'official'", (b,))}
        assert official(b1) == {"health"}       # taxes came from a consequential amendment to another law
        assert official(b2) == set()            # four topics: too broad to say what the bill is about
