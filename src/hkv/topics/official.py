"""Official law classification -> our topics (docs/roadmap.md T1).

The Knesset classifies laws (not bills) into 51 categories. A bill gets the categories of the laws it creates or
amends (KNS_LawBinding, LawTypeID 2 = bill) - only of the law named in its title, so consequential amendments to
other laws do not add topics. Categories without a matching topic are kept in the tables but give no
topic. Assignments are stored as origin='official' with the category as evidence; they win over keyword rules for
the same topic (topics.sync inserts them first).
"""

from __future__ import annotations

import logging

import psycopg

from hkv.sources.odata import PageSource, chunks, or_filter

log = logging.getLogger("hkv.topics.official")

MAX_OFFICIAL_TOPICS = 3

# KNS_IsraelLawClassificiation.ClassificiationID -> topic slug (None: no matching topic)
CATEGORY_TOPIC: dict[int, str | None] = {
    1: "immigration",        # אזרחות, תושבות וכניסה לישראל
    2: "governance",         # בחירות
    3: "defense",            # ביטחון
    4: "police",             # ביטחון הפנים
    5: "housing",            # בינוי ושיכון
    6: "finance-consumer",   # בנקאות וכספים
    7: "health",             # בריאות
    9: "religion",           # דתות
    10: "environment",       # הגנת הסביבה
    11: None,                # חוץ
    12: "budget",            # חוקי הסדרים
    13: "governance",        # חוק-יסוד
    14: "education",         # חינוך
    15: "agriculture",       # חקלאות
    16: "governance",        # כנסת
    17: None,                # מדע
    18: None,                # מועדים
    19: "taxes",             # מיסוי
    20: None,                # מסחר ותעשייה
    21: "family",            # מעמד אישי
    22: "health",            # מקצועות הבריאות
    23: "housing",           # מקרקעין
    24: None,                # משפט אזרחי
    25: None,                # משפט מינהלי
    26: "justice",           # משפט פלילי
    27: None,                # ניהול נכסים
    28: None,                # ספורט
    29: "transport",         # ספנות
    30: "justice",           # ערכאות שיפוטיות
    31: None,                # פיתוח והשקעות
    32: "finance-consumer",  # פנסיה, ביטוח ושוק ההון
    33: "finance-consumer",  # צרכנות
    34: "immigration",       # קליטת עלייה
    35: "justice",           # ראיות וסדרי דין
    36: "governance",        # ראשי המדינה
    37: "welfare",           # רווחה
    38: "local-government",  # רשויות מקומיות
    39: None,                # שירות הציבור
    40: None,                # תאגידים
    41: "transport",         # תחבורה ובטיחות בדרכים
    42: None,                # תיירות
    43: "housing",           # תכנון ובנייה
    44: "transport",         # תעופה
    45: "labor",             # תעסוקה
    46: "budget",            # תקציב
    48: "communications",    # תקשורת
    49: None,                # תרבות
    50: "environment",       # תשתיות
    51: "budget",            # מילווה למדינה
    52: "communications",    # טכנולוגיה וסייבר
    53: "emergency",         # מצב חירום
}


def load(conn: psycopg.Connection, v4: PageSource, bill_ids: list[int] | None = None) -> dict[str, int]:
    """Refresh law categories and bill->law bindings: all bills (one pass over LawTypeID 2), or only `bill_ids`."""
    counts = {}
    laws = [r for p in v4.pages("KNS_IsraelLaw", {"$select": "Id,Name,IsBasicLaw,IsBudgetLaw"}) for r in p.rows]
    rows = [r for p in v4.pages("KNS_IsraelLawClassificiation", {}) for r in p.rows]
    with conn.transaction():
        for r in laws:
            conn.execute("""INSERT INTO israel_law VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO UPDATE
                            SET name_he = EXCLUDED.name_he, is_basic_law = EXCLUDED.is_basic_law, is_budget_law = EXCLUDED.is_budget_law""",
                         (r["Id"], " ".join(r["Name"].split()), bool(r.get("IsBasicLaw")), bool(r.get("IsBudgetLaw"))))
        conn.execute("DELETE FROM israel_law_classification")
        for r in rows:
            conn.execute("""INSERT INTO israel_law_classification VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                         (r["IsraelLawID"], r["ClassificiationID"], " ".join(r["ClassificiationDesc"].split())))
    counts["classifications"] = len(rows)

    if bill_ids is None:
        bindings = [r for p in v4.pages("KNS_LawBinding", {"$filter": "LawTypeID eq 2"}) for r in p.rows]
    else:
        bindings = [r for ch in chunks(bill_ids) for p in v4.pages("KNS_LawBinding", {"$filter": f"LawTypeID eq 2 and ({or_filter('LawID', ch)})"})
                    for r in p.rows]
    ours = dict(conn.execute("SELECT knesset_bill_id, id FROM bill").fetchall())
    with conn.transaction():
        n = 0
        for r in bindings:
            bid = ours.get(r["LawID"])
            if bid and r.get("IsraelLawID"):
                n += conn.execute("""INSERT INTO bill_law VALUES (%s, %s, %s) ON CONFLICT (bill_id, israel_law_id) DO UPDATE
                                     SET binding_type_he = EXCLUDED.binding_type_he""",
                                  (bid, r["IsraelLawID"], r.get("BindingTypeDesc"))).rowcount
        mark_primary(conn)
    counts["bill_law"] = n
    counts["laws"] = len(laws)
    log.info("official law classification: %s", counts)
    return counts


def mark_primary(conn: psycopg.Connection) -> None:
    """Primary binding = the law named in the bill title (its name without the Hebrew-year suffix);
    a bill that names none of its laws keeps all of them as primary."""
    conn.execute("""
        WITH m AS (
            SELECT bl.bill_id, bl.israel_law_id,
                   he_norm(b.title_he) LIKE '%' || he_norm(regexp_replace(l.name_he, ',\\s*ה?תש.*$', '')) || '%' AS named
            FROM bill_law bl JOIN bill b ON b.id = bl.bill_id JOIN israel_law l ON l.id = bl.israel_law_id)
        UPDATE bill_law bl SET is_primary = m.named OR NOT EXISTS (SELECT 1 FROM m m2 WHERE m2.bill_id = m.bill_id AND m2.named)
        FROM m WHERE m.bill_id = bl.bill_id AND m.israel_law_id = bl.israel_law_id""")


def assign(conn: psycopg.Connection, topic_ids: dict[str, int]) -> int:
    """Replace unreviewed official assignments from the stored tables (call inside topics.sync's transaction)."""
    conn.execute("DELETE FROM bill_topic WHERE origin = 'official' AND review_state = 'unreviewed'")
    rows = conn.execute(
        """SELECT bl.bill_id, array_agg(DISTINCT c.classification_id) AS cats, array_agg(DISTINCT c.label_he) AS labels,
                  count(DISTINCT bl.israel_law_id) AS laws
           FROM bill_law bl JOIN israel_law_classification c ON c.israel_law_id = bl.israel_law_id
           WHERE bl.is_primary GROUP BY bl.bill_id""").fetchall()
    labels = dict(conn.execute("SELECT DISTINCT classification_id, label_he FROM israel_law_classification").fetchall())
    n = 0
    for bill_id, cats, _, _laws in rows:
        slugs = {CATEGORY_TOPIC.get(cat): labels[cat] for cat in sorted(cats) if CATEGORY_TOPIC.get(cat)}
        # omnibus legislation (arrangements laws, emergency-regulation packages) is classified into many areas;
        # that says little about the bill's subject, so keyword rules alone decide there
        if len(slugs) > MAX_OFFICIAL_TOPICS:
            continue
        for slug, label in slugs.items():
            n += conn.execute(
                """INSERT INTO bill_topic (bill_id, topic_id, origin, evidence) VALUES (%s, %s, 'official', %s)
                   ON CONFLICT (bill_id, topic_id) DO NOTHING""", (bill_id, topic_ids[slug], label)).rowcount
    return n
