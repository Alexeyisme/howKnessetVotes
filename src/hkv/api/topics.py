"""Topics and search (architecture.md §9, §10).

Topic assignments are rule-based and unreviewed; responses say so. Topic statistics use final-reading
votes on the bill as a whole (stage third, motion adopt_bill) and inherit the topic from the bill.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from hkv.api.common import Conn, Meta, Stage
from hkv.api.entities import BILL_SELECT, BillSummary, FactionRef, bill_summary
from hkv.topics import HE_PREFIX, RULES_VERSION, he_norm

router = APIRouter(prefix="/api/v1")

TOPIC_NOTE = (f"Topics are assigned automatically from bill titles by keyword rules (version {RULES_VERSION}) and have not "
              "been reviewed by an editor; a vote inherits the topics of its bill.")


class TopicSummary(BaseModel):
    slug: str
    label_ru: str
    label_he: str
    bills: int


class FactionTopicStats(BaseModel):
    faction: FactionRef
    faction_ru: str | None
    votes: int                    # final-reading votes on topic bills in which the faction cast at least one vote
    majority_for: int
    majority_against: int
    other: int                    # abstain majority, split, or no strict majority


class TopicDetail(TopicSummary):
    aliases_ru: list[str]
    term: int
    stage: list[str]
    factions: list[FactionTopicStats]
    recent_bills: list[BillSummary]


class SearchResult(BaseModel):
    topics: list[TopicSummary]
    bills: list[BillSummary]
    members: list[dict]
    factions: list[dict]
    script: Literal["hebrew", "cyrillic", "latin", "number", "other"]


TOPIC_SELECT = """
    SELECT t.id, t.slug, ru.label AS label_ru, he.label AS label_he,
           (SELECT count(*) FROM bill_topic bt WHERE bt.topic_id = t.id AND bt.review_state <> 'rejected'
              AND EXISTS (SELECT 1 FROM vote_subject vs WHERE vs.bill_id = bt.bill_id)) AS bills
    FROM topic t JOIN topic_label ru ON ru.topic_id = t.id AND ru.language = 'ru' JOIN topic_label he ON he.topic_id = t.id AND he.language = 'he'"""


def topic_summary(r: dict) -> TopicSummary:
    return TopicSummary(slug=r["slug"], label_ru=r["label_ru"], label_he=r["label_he"], bills=r["bills"])


@router.get("/topics", response_model=dict)
def list_topics(conn: Conn):
    rows = conn.execute(f"{TOPIC_SELECT} ORDER BY t.sort").fetchall()
    return {"data": [topic_summary(r) for r in rows], "meta": Meta(filters={}, note=TOPIC_NOTE)}


@router.get("/topics/{slug}", response_model=dict)
def get_topic(slug: str, conn: Conn, term: int | None = None, stage: Annotated[list[Stage] | None, Query()] = None):
    t = conn.execute(f"{TOPIC_SELECT} WHERE t.slug = %s", (slug,)).fetchone()
    if t is None:
        raise HTTPException(404, "topic not found")
    if term is None:
        term = conn.execute("SELECT max(term_number) AS t FROM vote").fetchone()["t"]
    stages = stage or ["third"]
    rows = conn.execute(
        """WITH v AS (
               SELECT DISTINCT v.id FROM vote v
               JOIN vote_subject vs ON vs.vote_id = v.id
               JOIN bill_topic bt ON bt.bill_id = vs.bill_id AND bt.topic_id = %(topic)s AND bt.review_state <> 'rejected'
               LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
               WHERE v.term_number = %(term)s AND v.status = 'valid' AND coalesce(k.stage, v.stage) = ANY(%(stages)s)
                 AND coalesce(k.motion_type, v.motion_type) IN ('adopt_bill', 'adopt_section')
           ), per AS (
               SELECT b.faction_id, b.vote_id, count(*) FILTER (WHERE b.choice = 'for') f, count(*) FILTER (WHERE b.choice = 'against') a,
                      count(*) FILTER (WHERE b.choice = 'abstain') ab
               FROM ballot b JOIN v ON v.id = b.vote_id WHERE b.faction_id IS NOT NULL AND b.choice IS NOT NULL GROUP BY 1, 2
           )
           SELECT f.knesset_faction_id, f.name_he, f.term_number, fl.name AS ru, count(*) AS votes,
                  count(*) FILTER (WHERE 2 * per.f > per.f + per.a + per.ab) AS maj_for,
                  count(*) FILTER (WHERE 2 * per.a > per.f + per.a + per.ab) AS maj_against
           FROM per JOIN faction f ON f.id = per.faction_id LEFT JOIN faction_label fl ON fl.faction_id = f.id AND fl.language = 'ru'
           GROUP BY 1, 2, 3, 4 ORDER BY count(*) DESC, 2""",
        {"topic": t["id"], "term": term, "stages": stages}).fetchall()
    bills = conn.execute(
        f"""SELECT * FROM ({BILL_SELECT} WHERE EXISTS (SELECT 1 FROM bill_topic bt WHERE bt.bill_id = b.id AND bt.topic_id = %s AND bt.review_state <> 'rejected')
               AND EXISTS (SELECT 1 FROM vote_subject vs WHERE vs.bill_id = b.id)) x ORDER BY last_vote_on DESC NULLS LAST LIMIT 20""",
        (t["id"],)).fetchall()
    aliases = [r["alias"] for r in conn.execute("SELECT alias FROM topic_alias WHERE topic_id = %s AND language = 'ru' ORDER BY alias", (t["id"],))]
    detail = TopicDetail(
        **topic_summary(t).model_dump(), aliases_ru=aliases, term=term, stage=stages,
        factions=[FactionTopicStats(faction=FactionRef(id=r["knesset_faction_id"], name_he=r["name_he"].strip(), term=r["term_number"]),
                                    faction_ru=r["ru"], votes=r["votes"], majority_for=r["maj_for"], majority_against=r["maj_against"],
                                    other=r["votes"] - r["maj_for"] - r["maj_against"]) for r in rows],
        recent_bills=[bill_summary(b) for b in bills])
    return {"data": detail, "meta": Meta(filters={"slug": slug, "term": term, "stage": stages}, note=(
        TOPIC_NOTE + " Faction counts: votes on these bills (as a whole in the chosen stages, and article votes in second reading "
        "when 'second' is chosen) where the faction's casting members had a strict majority for or against. Reservation and "
        "procedural votes are excluded."))}


_HEBREW = re.compile(r"[֐-׿]")
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")


def detect_script(q: str) -> str:
    if q.strip().isdigit():
        return "number"
    if _HEBREW.search(q):
        return "hebrew"
    if _CYRILLIC.search(q):
        return "cyrillic"
    if re.search(r"[a-zA-Z]", q):
        return "latin"
    return "other"


@router.get("/search", response_model=dict)
def search(conn: Conn, q: Annotated[str, Query(min_length=2, max_length=200)]):
    """One box for everything. Hebrew: bills, members, factions (normalised, typo-tolerant). Russian: topics by name
    and synonyms, factions by Russian name. Number: bill, vote or private-bill number."""
    script = detect_script(q)
    topics: list[TopicSummary] = []
    bills: list = []
    members: list[dict] = []
    factions: list[dict] = []
    if script in ("cyrillic", "latin"):
        ql = q.strip().lower()
        topics = [topic_summary(r) for r in conn.execute(
            f"""{TOPIC_SELECT} WHERE EXISTS (SELECT 1 FROM topic_alias a WHERE a.topic_id = t.id AND a.language = 'ru'
                   AND (lower(a.alias) LIKE %(like)s OR %(q)s LIKE '%%' || lower(a.alias) || '%%' OR similarity(lower(a.alias), %(q)s) > 0.35))
                ORDER BY t.sort""", {"q": ql, "like": f"%{ql}%"})]
        factions = [dict(r) for r in conn.execute(
            """SELECT f.knesset_faction_id AS id, f.name_he, fl.name AS name_ru, f.term_number AS term FROM faction_label fl
               JOIN faction f ON f.id = fl.faction_id WHERE fl.language = 'ru' AND (lower(fl.name) LIKE %(like)s OR similarity(lower(fl.name), %(q)s) > 0.4)
                 AND EXISTS (SELECT 1 FROM ballot b WHERE b.faction_id = f.id)
               ORDER BY f.term_number DESC LIMIT 20""", {"q": ql, "like": f"%{ql}%"})]
    elif script == "hebrew":
        n = he_norm(q)
        params = {"n": n, "like": f"%{n}%"}
        members = [dict(r) for r in conn.execute(
            """SELECT p.knesset_person_id AS id, p.first_name_he || ' ' || p.last_name_he AS name_he FROM person p
               WHERE (he_norm(p.first_name_he || ' ' || p.last_name_he) LIKE %(like)s OR %(n)s <%% he_norm(p.first_name_he || ' ' || p.last_name_he))
                 AND EXISTS (SELECT 1 FROM ballot b WHERE b.person_id = p.id)
               ORDER BY word_similarity(%(n)s, he_norm(p.first_name_he || ' ' || p.last_name_he)) DESC LIMIT 10""", {"n": n, "like": f"%{n}%"})]
        factions = [dict(r) for r in conn.execute(
            """SELECT f.knesset_faction_id AS id, f.name_he, fl.name AS name_ru, f.term_number AS term FROM faction f
               LEFT JOIN faction_label fl ON fl.faction_id = f.id AND fl.language = 'ru'
               WHERE he_norm(f.name_he) LIKE %(like)s AND EXISTS (SELECT 1 FROM ballot b WHERE b.faction_id = f.id)
               ORDER BY f.term_number DESC LIMIT 10""", {"like": f"%{n}%"})]
        # whole word (with prefixes) > substring > typo-tolerant word similarity; fuzzy only when nothing matched exactly
        word = rf"(^|[ (]){HE_PREFIX}{re.escape(n)}($|[ ),.:;])"
        params["word"] = word
        exact = conn.execute(
            f"""SELECT * FROM ({BILL_SELECT} WHERE he_norm(b.title_he) LIKE %(like)s AND EXISTS (SELECT 1 FROM vote_subject vs WHERE vs.bill_id = b.id)) x
                ORDER BY (he_norm(title_he) ~ %(word)s) DESC, last_vote_on DESC NULLS LAST LIMIT 20""", params).fetchall()
        fuzzy = [] if len(exact) >= 5 or members or factions else conn.execute(
            f"""SELECT * FROM ({BILL_SELECT} WHERE %(n)s <%% he_norm(b.title_he) AND he_norm(b.title_he) NOT LIKE %(like)s
                   AND EXISTS (SELECT 1 FROM vote_subject vs WHERE vs.bill_id = b.id)) x
                ORDER BY word_similarity(%(n)s, he_norm(title_he)) DESC, last_vote_on DESC NULLS LAST LIMIT %(k)s""",
            {**params, "k": 20 - len(exact)}).fetchall()
        bills = [bill_summary(r) for r in [*exact, *fuzzy]]
        topics = [topic_summary(r) for r in conn.execute(
            f"""{TOPIC_SELECT} WHERE EXISTS (SELECT 1 FROM topic_alias a WHERE a.topic_id = t.id AND a.language = 'he' AND he_norm(a.alias) = %s)
                ORDER BY t.sort""", (n,))]
    elif script == "number":
        num = int(q.strip())
        bills = [bill_summary(r) for r in conn.execute(
            f"{BILL_SELECT} WHERE b.knesset_bill_id = %(n)s OR b.private_number = %(n)s OR b.bill_number = %(n)s LIMIT 20", {"n": num})]
    return {"data": SearchResult(topics=topics, bills=bills, members=members, factions=factions, script=script),
            "meta": Meta(filters={"q": q}, note="Member names are searchable in Hebrew only for now." if script == "cyrillic" else None)}
