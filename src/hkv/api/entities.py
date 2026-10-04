"""Members, factions, bills, terms (architecture.md §13). Formulas follow §10; every rate carries
its numerator and denominator."""

from __future__ import annotations

import base64
import datetime as dt
import json
from typing import Annotated, ClassVar, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from hkv.api.common import VOTE_SELECT, BillRef, Conn, Meta, MotionType, Stage, VoteSummary, vote_summary
from hkv.api.names import FactionNames, PersonNames, TopicLabels, with_names

router = APIRouter(prefix="/api/v1")
BILL_URL = "https://main.knesset.gov.il/APPS/legislation/main/bills/{}"
MIN_COLLEAGUES = 2  # a faction "majority" needs at least this many other members casting a vote

Choice = Literal["for", "against", "abstain"]


# -- models ------------------------------------------------------------------------------------------

class Rate(BaseModel):
    numerator: int
    denominator: int
    value: float | None  # numerator / denominator, None when the denominator is 0


def rate(n: int, d: int) -> Rate:
    return Rate(numerator=n, denominator=d, value=round(n / d, 4) if d else None)


class FactionRef(FactionNames):
    id: int
    name_he: str
    term: int


class Interval(BaseModel):
    valid_from: dt.date
    valid_to: dt.date | None  # exclusive; None = still current


class MandateOut(Interval):
    term: int


class MembershipOut(Interval):
    faction: FactionRef


class MemberSummary(PersonNames):
    id: int
    name_he: str
    gender: str | None
    terms: list[int]
    last_faction: FactionRef | None
    roll_call_records: int


class MemberStats(BaseModel):
    participation: Rate          # cast (for/against/abstain) / roll-call votes held during the member's mandates
    choices: dict[str, int]      # for / against / abstain / present_not_voting / other
    deviation_from_faction: Rate  # cast against the strict majority of other faction members / comparable votes
    bills_initiated: int
    bills_joined: int


class MemberDetail(MemberSummary):
    photo_url: str | None        # official portrait on the Knesset website (fs.knesset.gov.il)
    mandates: list[MandateOut]
    factions: list[MembershipOut]
    stats: MemberStats


class MemberVote(BaseModel):
    vote: VoteSummary
    choice: Choice | None
    participation: str
    faction: FactionRef | None
    faction_majority: Literal["for", "against", "abstain", "mixed", "none"]
    deviates: bool | None  # None when there is no comparable faction majority


class PartyRef(BaseModel):
    slug: str
    name_he: str
    name_ru: str
    name_en: str


class AlignmentOut(Interval):
    government: int
    role: Literal["coalition", "opposition", "external_support", "unknown"]
    origin: Literal["derived", "curated"]
    evidence: str


class FactionSummary(FactionNames):
    id: int
    name_he: str
    term: int
    valid: Interval
    members_ever: int
    roll_call_records: int
    parties: list[PartyRef] = []
    # role on the faction's last day (today for a current faction); None before a government was formed
    alignment_last: Literal["coalition", "opposition", "external_support", "unknown"] | None = None


class FactionStats(BaseModel):
    votes_with_members: int
    cohesion: Rate               # members voting with their faction's plurality choice / members casting, over all votes
    unanimous_votes: Rate        # votes where all casting members chose the same / votes with >= 2 casting members


class FactionMember(MembershipOut, PersonNames):
    _person_key: ClassVar[str] = "person_id"
    person_id: int
    name_he: str


class FactionDetail(FactionSummary):
    members: list[FactionMember]
    stats: FactionStats
    alignment: list[AlignmentOut]


class PartySummary(PartyRef):
    terms: list[int]
    factions: list[FactionSummary]   # per Knesset, oldest first (joint lists included)


class Government(BaseModel):
    number: int
    term: int | None
    valid: Interval
    prime_minister: "GovernmentPerson | None"


class GovernmentPerson(PersonNames):
    id: int
    name_he: str


class FactionVote(BaseModel):
    vote: VoteSummary
    faction_counts: dict[str, int]
    majority: Literal["for", "against", "abstain", "mixed", "none"]


class Initiator(PersonNames):
    _person_key: ClassVar[str] = "person_id"
    person_id: int
    name_he: str
    role: Literal["initiator", "joined", "withdrew"]


class BillSummary(BaseModel):
    id: int
    title_he: str
    term: int
    origin: str | None
    status_he: str | None
    votes: int
    last_vote_on: dt.date | None
    passed_third_reading: bool
    source_url: str


class BillTopic(TopicLabels):
    slug: str
    label_ru: str
    label_he: str
    origin: str
    review_state: str
    evidence: str | None


class BillDetail(BillSummary):
    topics: list[BillTopic]
    summary_he: str | None
    published_on: dt.date | None
    initiators: list[Initiator]
    related: list[BillRef]
    timeline: list[VoteSummary]


class Term(BaseModel):
    number: int
    name_he: str | None
    started_on: dt.date
    ended_on: dt.date | None


class Page[T](BaseModel):
    data: list[T]
    meta: Meta
    next_cursor: str | None = None


class One[T](BaseModel):
    data: T
    meta: Meta


# -- helpers -----------------------------------------------------------------------------------------

def encode_cursor(*values) -> str:
    return base64.urlsafe_b64encode(json.dumps([v.isoformat() if isinstance(v, dt.date) else v for v in values]).encode()).decode()


def decode_cursor(cursor: str) -> list:
    try:
        return json.loads(base64.urlsafe_b64decode(cursor))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, "invalid cursor") from e


def faction_ref(fid: int | None, name: str | None, term: int | None) -> FactionRef | None:
    return FactionRef(id=fid, name_he=name.strip(), term=term) if fid is not None else None


def majority_of(f: int, a: int, ab: int, cast_min: int = 1) -> str:
    cast = f + a + ab
    if cast < cast_min:
        return "none"
    for name, n in (("for", f), ("against", a), ("abstain", ab)):
        if 2 * n > cast:
            return name
    return "mixed"


def person_id(conn, knesset_id: int):
    row = conn.execute("SELECT id FROM person WHERE knesset_person_id = %s", (knesset_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "member not found")
    return row["id"]


# -- terms -------------------------------------------------------------------------------------------

@router.get("/terms", response_model=Page[Term])
@with_names
def list_terms(conn: Conn):
    rows = conn.execute("SELECT number, name_he, started_on, ended_on FROM knesset_term WHERE number > 0 ORDER BY number DESC").fetchall()
    return {"data": rows, "meta": Meta(filters={})}


# -- members -----------------------------------------------------------------------------------------

MEMBER_SELECT = """
    SELECT p.id AS pk, p.knesset_person_id AS id, p.first_name_he || ' ' || p.last_name_he AS name_he, p.gender,
           (SELECT array_agg(DISTINCT m.term_number ORDER BY m.term_number) FROM mandate m WHERE m.person_id = p.id) AS terms,
           lf.knesset_faction_id AS lf_id, lf.name_he AS lf_name, lf.term_number AS lf_term,
           (SELECT count(*) FROM ballot b WHERE b.person_id = p.id) AS records
    FROM person p
    LEFT JOIN LATERAL (SELECT f.knesset_faction_id, f.name_he, f.term_number FROM faction_membership fm JOIN faction f ON f.id = fm.faction_id
                       WHERE fm.person_id = p.id ORDER BY lower(fm.valid) DESC LIMIT 1) lf ON true"""


def member_summary(r: dict) -> MemberSummary:
    return MemberSummary(id=r["id"], name_he=r["name_he"], gender=r["gender"], terms=r["terms"] or [],
                         last_faction=faction_ref(r["lf_id"], r["lf_name"], r["lf_term"]), roll_call_records=r["records"])


@router.get("/members", response_model=Page[MemberSummary])
@with_names
def list_members(conn: Conn, term: int | None = None, q: Annotated[str | None, Query(min_length=2)] = None,
                 faction: int | None = None):
    """MKs with at least one roll-call record; filter by term (held a mandate), name substring (any language), or faction membership."""
    where, params = ["EXISTS (SELECT 1 FROM ballot b WHERE b.person_id = p.id)"], {}
    if term:
        where.append("EXISTS (SELECT 1 FROM mandate m WHERE m.person_id = p.id AND m.term_number = %(term)s)"); params["term"] = term
    if q:
        # Hebrew name, or any English/Russian name or variant (person_alias)
        where.append("""((p.first_name_he || ' ' || p.last_name_he) ILIKE %(q)s
                        OR EXISTS (SELECT 1 FROM person_alias a WHERE a.person_id = p.id AND a.full_name ILIKE %(q)s))"""); params["q"] = f"%{q}%"
    if faction:
        where.append("""EXISTS (SELECT 1 FROM faction_membership fm JOIN faction f ON f.id = fm.faction_id
                               WHERE fm.person_id = p.id AND f.knesset_faction_id = %(faction)s)"""); params["faction"] = faction
    rows = conn.execute(f"{MEMBER_SELECT} WHERE {' AND '.join(where)} ORDER BY p.last_name_he, p.first_name_he", params).fetchall()
    return {"data": [member_summary(r) for r in rows], "meta": Meta(filters={"term": term, "q": q, "faction": faction})}


# Strict majority of the OTHER members of the member's faction who cast a vote (architecture.md §10).
MEMBER_VOTES_CTE = f"""
    WITH mine AS (
        SELECT b.vote_id, b.faction_id, b.choice, b.participation FROM ballot b WHERE b.person_id = %(pid)s
    ), maj AS (
        SELECT m.vote_id, o.f, o.a, o.ab FROM mine m CROSS JOIN LATERAL (
            SELECT count(*) FILTER (WHERE x.choice = 'for') f, count(*) FILTER (WHERE x.choice = 'against') a,
                   count(*) FILTER (WHERE x.choice = 'abstain') ab
            FROM ballot x WHERE x.vote_id = m.vote_id AND x.faction_id = m.faction_id AND x.person_id <> %(pid)s) o
        WHERE m.faction_id IS NOT NULL
    ), cmp AS (
        SELECT m.*, maj.f, maj.a, maj.ab,
               CASE WHEN coalesce(maj.f + maj.a + maj.ab, 0) < {MIN_COLLEAGUES} THEN NULL
                    WHEN 2 * maj.f > maj.f + maj.a + maj.ab THEN 'for'
                    WHEN 2 * maj.a > maj.f + maj.a + maj.ab THEN 'against'
                    WHEN 2 * maj.ab > maj.f + maj.a + maj.ab THEN 'abstain' END AS majority
        FROM mine m LEFT JOIN maj USING (vote_id)
    )"""


@router.get("/members/{member_id}", response_model=One[MemberDetail])
@with_names
def get_member(member_id: int, conn: Conn):
    pid = person_id(conn, member_id)
    r = conn.execute(f"{MEMBER_SELECT} WHERE p.id = %s", (pid,)).fetchone()
    mandates = conn.execute("SELECT term_number AS term, lower(valid) AS valid_from, upper(valid) AS valid_to FROM mandate WHERE person_id = %s ORDER BY lower(valid)",
                            (pid,)).fetchall()
    factions = conn.execute(
        """SELECT f.knesset_faction_id, f.name_he, f.term_number, lower(fm.valid) AS valid_from, upper(fm.valid) AS valid_to
           FROM faction_membership fm JOIN faction f ON f.id = fm.faction_id WHERE fm.person_id = %s ORDER BY lower(fm.valid)""", (pid,)).fetchall()
    choices = {x["k"]: x["v"] for x in conn.execute(
        """SELECT CASE WHEN choice IS NOT NULL THEN choice WHEN participation = 'present_not_voting' THEN participation ELSE 'other' END AS k,
                  count(*) AS v FROM ballot WHERE person_id = %s GROUP BY 1""", (pid,))}
    # denominator: votes that have a roll call and fall inside one of the member's mandates
    available = conn.execute(
        """SELECT count(*) AS n FROM vote v WHERE EXISTS (SELECT 1 FROM ballot b WHERE b.vote_id = v.id)
             AND EXISTS (SELECT 1 FROM mandate m WHERE m.person_id = %s AND m.valid @> v.occurred_on)""", (pid,)).fetchone()["n"]
    cast = conn.execute(
        """SELECT count(*) AS n FROM ballot b JOIN vote v ON v.id = b.vote_id WHERE b.person_id = %s AND b.choice IS NOT NULL
             AND EXISTS (SELECT 1 FROM mandate m WHERE m.person_id = b.person_id AND m.valid @> v.occurred_on)""", (pid,)).fetchone()["n"]
    dev = conn.execute(f"""{MEMBER_VOTES_CTE}
        SELECT count(*) FILTER (WHERE choice IS NOT NULL AND majority IS NOT NULL) AS comparable,
               count(*) FILTER (WHERE choice IS NOT NULL AND majority IS NOT NULL AND choice <> majority) AS deviated FROM cmp""",
                       {"pid": pid}).fetchone()
    bills = dict((x["role"], x["n"]) for x in conn.execute("SELECT role, count(*) AS n FROM bill_initiator WHERE person_id = %s GROUP BY 1", (pid,)))
    base = member_summary(r)
    return {
        "data": MemberDetail(
            **base.model_dump(),
            photo_url=(ph := conn.execute("SELECT url FROM person_photo WHERE person_id = %s", (pid,)).fetchone()) and ph["url"],
            mandates=mandates,
            factions=[MembershipOut(faction=faction_ref(f["knesset_faction_id"], f["name_he"], f["term_number"]),
                                    valid_from=f["valid_from"], valid_to=f["valid_to"]) for f in factions],
            stats=MemberStats(participation=rate(cast, available), choices=choices,
                              deviation_from_faction=rate(dev["deviated"], dev["comparable"]),
                              bills_initiated=bills.get("initiator", 0), bills_joined=bills.get("joined", 0)),
        ),
        "meta": Meta(filters={"id": member_id}, note=(
            "participation = votes cast (for/against/abstain) / roll-call votes held while the member had a mandate; "
            "it is not attendance. deviation = cast votes differing from the strict majority of the other faction members "
            f"who voted (at least {MIN_COLLEAGUES}); it is not evidence of breaking discipline.")),
    }


@router.get("/members/{member_id}/votes", response_model=Page[MemberVote])
@with_names
def member_votes(member_id: int, conn: Conn, date_from: dt.date | None = None, date_to: dt.date | None = None,
                 stage: Annotated[list[Stage] | None, Query()] = None, motion_type: Annotated[list[MotionType] | None, Query()] = None,
                 deviated: bool = False, limit: Annotated[int, Query(ge=1, le=100)] = 50, cursor: str | None = None):
    pid = person_id(conn, member_id)
    where, params = ["true"], {"pid": pid, "limit": limit + 1}
    if date_from:
        where.append("v.occurred_on >= %(date_from)s"); params["date_from"] = date_from
    if date_to:
        where.append("v.occurred_on <= %(date_to)s"); params["date_to"] = date_to
    if stage:
        where.append("coalesce(k.stage, v.stage) = ANY(%(stage)s)"); params["stage"] = stage
    if motion_type:
        where.append("coalesce(k.motion_type, v.motion_type) = ANY(%(motion)s)"); params["motion"] = motion_type
    if deviated:
        where.append("cmp.choice IS NOT NULL AND cmp.majority IS NOT NULL AND cmp.choice <> cmp.majority")
    if cursor:
        c_on, c_id = decode_cursor(cursor)
        where.append("(v.occurred_on, v.knesset_vote_id) < (%(c_on)s::date, %(c_id)s)"); params.update(c_on=c_on, c_id=c_id)
    rows = conn.execute(f"""{MEMBER_VOTES_CTE}
        SELECT v.knesset_vote_id AS vid, v.occurred_on, cmp.choice, cmp.participation, cmp.f, cmp.a, cmp.ab, cmp.majority,
               f.knesset_faction_id, f.name_he AS faction_name, f.term_number AS faction_term
        FROM cmp JOIN vote v ON v.id = cmp.vote_id
        LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
        LEFT JOIN faction f ON f.id = cmp.faction_id
        WHERE {' AND '.join(where)} ORDER BY v.occurred_on DESC, v.knesset_vote_id DESC LIMIT %(limit)s""", params).fetchall()
    more, rows = len(rows) > limit, rows[:limit]
    summaries = {s["id"]: vote_summary(s) for s in conn.execute(f"{VOTE_SELECT} WHERE v.knesset_vote_id = ANY(%s)", ([r["vid"] for r in rows],))}
    data = [MemberVote(
        vote=summaries[r["vid"]], choice=r["choice"], participation=r["participation"],
        faction=faction_ref(r["knesset_faction_id"], r["faction_name"], r["faction_term"]),
        faction_majority=r["majority"] or ("none" if r["f"] is None or (r["f"] + r["a"] + r["ab"]) < MIN_COLLEAGUES else "mixed"),
        deviates=None if r["choice"] is None or r["majority"] is None else r["choice"] != r["majority"],
    ) for r in rows]
    return {"data": data, "meta": Meta(filters={"id": member_id, "deviated": deviated, "stage": stage, "motion_type": motion_type}),
            "next_cursor": encode_cursor(rows[-1]["occurred_on"], rows[-1]["vid"]) if more else None}


# -- factions ----------------------------------------------------------------------------------------

FACTION_SELECT = """
    SELECT f.id AS pk, f.knesset_faction_id AS id, f.name_he, f.term_number AS term, lower(f.valid) AS valid_from, upper(f.valid) AS valid_to,
           (SELECT fl.name FROM faction_label fl WHERE fl.faction_id = f.id AND fl.language = 'ru') AS name_ru,
           (SELECT count(DISTINCT fm.person_id) FROM faction_membership fm WHERE fm.faction_id = f.id) AS members_ever,
           (SELECT count(*) FROM ballot b WHERE b.faction_id = f.id) AS records,
           (SELECT coalesce(json_agg(json_build_object('slug', p.slug, 'name_he', p.name_he, 'name_ru', p.name_ru, 'name_en', p.name_en) ORDER BY p.sort), '[]')
              FROM party_faction pf JOIN party p ON p.slug = pf.party_slug WHERE pf.faction_id = f.id) AS parties,
           (SELECT a.role FROM faction_alignment a WHERE a.faction_id = f.id
              AND a.valid @> least(coalesce(upper(f.valid) - 1, current_date), current_date)) AS alignment_last
    FROM faction f"""


def faction_summary(r: dict) -> FactionSummary:
    return FactionSummary(id=r["id"], name_he=r["name_he"].strip(), term=r["term"], valid=Interval(valid_from=r["valid_from"], valid_to=r["valid_to"]),
                          members_ever=r["members_ever"], roll_call_records=r["records"],
                          parties=[PartyRef(**p) for p in r["parties"]], alignment_last=r["alignment_last"])


@router.get("/factions", response_model=Page[FactionSummary])
@with_names
def list_factions(conn: Conn, term: int | None = None):
    """Factions with at least one roll-call record; by default of the latest term that has votes."""
    if term is None:
        term = conn.execute("SELECT max(term_number) AS t FROM vote").fetchone()["t"]
    rows = conn.execute(f"{FACTION_SELECT} WHERE f.term_number = %s AND EXISTS (SELECT 1 FROM ballot b WHERE b.faction_id = f.id) ORDER BY records DESC",
                        (term,)).fetchall()
    return {"data": [faction_summary(r) for r in rows], "meta": Meta(filters={"term": term})}


def faction_pk(conn, knesset_id: int):
    row = conn.execute(f"{FACTION_SELECT} WHERE f.knesset_faction_id = %s", (knesset_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "faction not found")
    return row


@router.get("/factions/{faction_id}", response_model=One[FactionDetail])
@with_names
def get_faction(faction_id: int, conn: Conn):
    r = faction_pk(conn, faction_id)
    members = conn.execute(
        """SELECT p.knesset_person_id, p.first_name_he || ' ' || p.last_name_he AS name_he, lower(fm.valid) AS valid_from, upper(fm.valid) AS valid_to
           FROM faction_membership fm JOIN person p ON p.id = fm.person_id WHERE fm.faction_id = %s
           ORDER BY upper(fm.valid) IS NOT NULL, p.last_name_he, lower(fm.valid)""", (r["pk"],)).fetchall()
    s = conn.execute(
        """WITH per_vote AS (
               SELECT vote_id, count(*) FILTER (WHERE choice = 'for') f, count(*) FILTER (WHERE choice = 'against') a,
                      count(*) FILTER (WHERE choice = 'abstain') ab
               FROM ballot WHERE faction_id = %s GROUP BY vote_id)
           SELECT count(*) AS votes, coalesce(sum(greatest(f, a, ab)), 0) AS with_plurality, coalesce(sum(f + a + ab), 0) AS cast_total,
                  count(*) FILTER (WHERE f + a + ab >= 2) AS multi, count(*) FILTER (WHERE f + a + ab >= 2 AND greatest(f, a, ab) = f + a + ab) AS unanimous
           FROM per_vote""", (r["pk"],)).fetchone()
    fref = FactionRef(id=r["id"], name_he=r["name_he"].strip(), term=r["term"])
    return {
        "data": FactionDetail(
            **faction_summary(r).model_dump(),
            members=[FactionMember(person_id=m["knesset_person_id"], name_he=m["name_he"], faction=fref,
                                   valid_from=m["valid_from"], valid_to=m["valid_to"]) for m in members],
            stats=FactionStats(votes_with_members=s["votes"], cohesion=rate(s["with_plurality"], s["cast_total"]),
                               unanimous_votes=rate(s["unanimous"], s["multi"])),
            alignment=[AlignmentOut(**a) for a in conn.execute(
                """SELECT government_number AS government, role, origin, evidence, lower(valid) AS valid_from, upper(valid) AS valid_to
                   FROM faction_alignment WHERE faction_id = %s ORDER BY lower(valid)""", (r["pk"],))],
        ),
        "meta": Meta(filters={"id": faction_id}, note=(
            "cohesion = members casting the faction's most common choice / members casting, summed over votes. "
            "unanimous = votes where every casting member chose the same / votes with at least two casting members.")),
    }


@router.get("/factions/{faction_id}/votes", response_model=Page[FactionVote])
@with_names
def faction_votes(faction_id: int, conn: Conn, stage: Annotated[list[Stage] | None, Query()] = None,
                  motion_type: Annotated[list[MotionType] | None, Query()] = None, split_only: bool = False,
                  limit: Annotated[int, Query(ge=1, le=100)] = 50, cursor: str | None = None):
    r = faction_pk(conn, faction_id)
    where, params = ["true"], {"fid": r["pk"], "limit": limit + 1}
    if stage:
        where.append("coalesce(k.stage, v.stage) = ANY(%(stage)s)"); params["stage"] = stage
    if motion_type:
        where.append("coalesce(k.motion_type, v.motion_type) = ANY(%(motion)s)"); params["motion"] = motion_type
    if split_only:
        where.append("greatest(c.f, c.a, c.ab) < c.f + c.a + c.ab")
    if cursor:
        c_on, c_id = decode_cursor(cursor)
        where.append("(v.occurred_on, v.knesset_vote_id) < (%(c_on)s::date, %(c_id)s)"); params.update(c_on=c_on, c_id=c_id)
    rows = conn.execute(f"""
        WITH c AS (SELECT vote_id, count(*) FILTER (WHERE choice = 'for') f, count(*) FILTER (WHERE choice = 'against') a,
                          count(*) FILTER (WHERE choice = 'abstain') ab, count(*) FILTER (WHERE participation = 'present_not_voting') p,
                          count(*) n FROM ballot WHERE faction_id = %(fid)s GROUP BY vote_id)
        SELECT v.knesset_vote_id AS vid, v.occurred_on, c.f, c.a, c.ab, c.p, c.n FROM c JOIN vote v ON v.id = c.vote_id
        LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
        WHERE {' AND '.join(where)} ORDER BY v.occurred_on DESC, v.knesset_vote_id DESC LIMIT %(limit)s""", params).fetchall()
    more, rows = len(rows) > limit, rows[:limit]
    summaries = {s["id"]: vote_summary(s) for s in conn.execute(f"{VOTE_SELECT} WHERE v.knesset_vote_id = ANY(%s)", ([x["vid"] for x in rows],))}
    data = [FactionVote(vote=summaries[x["vid"]], majority=majority_of(x["f"], x["a"], x["ab"]),
                        faction_counts={"for": x["f"], "against": x["a"], "abstain": x["ab"], "present_not_voting": x["p"], "total_records": x["n"]})
            for x in rows]
    return {"data": data, "meta": Meta(filters={"id": faction_id, "split_only": split_only}),
            "next_cursor": encode_cursor(rows[-1]["occurred_on"], rows[-1]["vid"]) if more else None}


# -- bills -------------------------------------------------------------------------------------------

BILL_SELECT = """
    SELECT b.id AS pk, b.knesset_bill_id AS id, b.title_he, b.term_number AS term, b.origin_type AS origin, s.label_he AS status_he,
           b.summary_he, b.published_on,
           (SELECT count(*) FROM vote_subject vs WHERE vs.bill_id = b.id) AS votes,
           (SELECT max(v.occurred_on) FROM vote_subject vs JOIN vote v ON v.id = vs.vote_id WHERE vs.bill_id = b.id) AS last_vote_on,
           EXISTS (SELECT 1 FROM vote_subject vs JOIN vote v ON v.id = vs.vote_id LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
                   WHERE vs.bill_id = b.id AND coalesce(k.stage, v.stage) = 'third') AS third
    FROM bill b LEFT JOIN bill_status s ON s.knesset_status_id = b.status_id"""


def bill_summary(r: dict) -> BillSummary:
    return BillSummary(id=r["id"], title_he=r["title_he"], term=r["term"], origin=r["origin"], status_he=r["status_he"],
                       votes=r["votes"], last_vote_on=r["last_vote_on"], passed_third_reading=r["third"], source_url=BILL_URL.format(r["id"]))


@router.get("/bills", response_model=Page[BillSummary])
@with_names
def list_bills(conn: Conn, q: Annotated[str | None, Query(min_length=2)] = None, term: int | None = None,
               third_reading: bool | None = None, topic: str | None = None,
               limit: Annotated[int, Query(ge=1, le=100)] = 50, cursor: str | None = None):
    """Bills that were voted on in the plenum; newest vote first."""
    where, params = ["EXISTS (SELECT 1 FROM vote_subject vs WHERE vs.bill_id = b.id)"], {"limit": limit + 1}
    if q:
        where.append("(b.title_he ILIKE %(q)s OR b.knesset_bill_id::text = %(qraw)s OR b.private_number::text = %(qraw)s)")
        params.update(q=f"%{q}%", qraw=q.strip().lstrip("פP/-"))
    if term:
        where.append("b.term_number = %(term)s"); params["term"] = term
    if topic:
        where.append("""EXISTS (SELECT 1 FROM bill_topic bt JOIN topic t ON t.id = bt.topic_id
                                WHERE bt.bill_id = b.id AND t.slug = %(topic)s AND bt.review_state <> 'rejected')"""); params["topic"] = topic
    inner = f"{BILL_SELECT} WHERE {' AND '.join(where)}"
    outer = ["true"]
    if third_reading is not None:
        outer.append("third = %(third)s"); params["third"] = third_reading
    if cursor:
        c_on, c_id = decode_cursor(cursor)
        outer.append("(last_vote_on, id) < (%(c_on)s::date, %(c_id)s)"); params.update(c_on=c_on, c_id=c_id)
    rows = conn.execute(f"SELECT * FROM ({inner}) x WHERE {' AND '.join(outer)} ORDER BY last_vote_on DESC, id DESC LIMIT %(limit)s", params).fetchall()
    more, rows = len(rows) > limit, rows[:limit]
    return {"data": [bill_summary(r) for r in rows], "meta": Meta(filters={"q": q, "term": term, "third_reading": third_reading, "topic": topic}),
            "next_cursor": encode_cursor(rows[-1]["last_vote_on"], rows[-1]["id"]) if more else None}


@router.get("/bills/{bill_id}", response_model=One[BillDetail])
@with_names
def get_bill(bill_id: int, conn: Conn):
    r = conn.execute(f"{BILL_SELECT} WHERE b.knesset_bill_id = %s", (bill_id,)).fetchone()
    if r is None:
        raise HTTPException(404, "bill not found")
    initiators = conn.execute(
        """SELECT p.knesset_person_id AS person_id, p.first_name_he || ' ' || p.last_name_he AS name_he, i.role
           FROM bill_initiator i JOIN person p ON p.id = i.person_id WHERE i.bill_id = %s ORDER BY i.role, i.ordinal NULLS LAST""", (r["pk"],)).fetchall()
    related = conn.execute(
        """SELECT b2.knesset_bill_id AS id, b2.title_he FROM bill_relation br
           JOIN bill b2 ON b2.id = CASE WHEN br.from_bill_id = %(b)s THEN br.to_bill_id ELSE br.from_bill_id END
           WHERE %(b)s IN (br.from_bill_id, br.to_bill_id)""", {"b": r["pk"]}).fetchall()
    timeline = conn.execute(
        f"{VOTE_SELECT} WHERE EXISTS (SELECT 1 FROM vote_subject vs WHERE vs.vote_id = v.id AND vs.bill_id = %s) ORDER BY v.occurred_on, v.ordinal NULLS LAST, v.knesset_vote_id",
        (r["pk"],)).fetchall()
    topics = conn.execute(
        """SELECT t.slug, l.label AS label_ru, he.label AS label_he, bt.origin, bt.review_state, bt.evidence FROM bill_topic bt JOIN topic t ON t.id = bt.topic_id
           JOIN topic_label l ON l.topic_id = t.id AND l.language = 'ru' JOIN topic_label he ON he.topic_id = t.id AND he.language = 'he' WHERE bt.bill_id = %s AND bt.review_state <> 'rejected' ORDER BY t.sort""",
        (r["pk"],)).fetchall()
    return {"data": BillDetail(**bill_summary(r).model_dump(), topics=topics, summary_he=r["summary_he"], published_on=r["published_on"],
                               initiators=initiators, related=related, timeline=[vote_summary(t) for t in timeline]),
            "meta": Meta(filters={"id": bill_id})}


# -- parties and governments --------------------------------------------------------------------------

@router.get("/parties", response_model=Page[PartySummary])
@with_names
def list_parties(conn: Conn):
    """Parties across Knessets (curated): each with its per-term factions, joint lists included."""
    return {"data": [party_summary(conn, p) for p in conn.execute("SELECT * FROM party ORDER BY sort")],
            "meta": Meta(filters={}, note=PARTY_NOTE)}


@router.get("/parties/{slug}", response_model=One[PartySummary])
@with_names
def get_party(slug: str, conn: Conn):
    p = conn.execute("SELECT * FROM party WHERE slug = %s", (slug,)).fetchone()
    if p is None:
        raise HTTPException(404, "party not found")
    return {"data": party_summary(conn, p), "meta": Meta(filters={"slug": slug}, note=PARTY_NOTE)}


PARTY_NOTE = ("A party links the factions it sat as in each Knesset (curated). A joint list belongs to every member party, "
              "so its votes appear under each of them. Only factions with roll-call records are listed.")


def party_summary(conn, p: dict) -> PartySummary:
    rows = conn.execute(
        f"""{FACTION_SELECT} WHERE EXISTS (SELECT 1 FROM party_faction pf WHERE pf.faction_id = f.id AND pf.party_slug = %s)
              AND EXISTS (SELECT 1 FROM ballot b WHERE b.faction_id = f.id) ORDER BY lower(f.valid), f.knesset_faction_id""", (p["slug"],)).fetchall()
    factions = [faction_summary(r) for r in rows]
    return PartySummary(slug=p["slug"], name_he=p["name_he"], name_ru=p["name_ru"], name_en=p["name_en"],
                        terms=sorted({f.term for f in factions}), factions=factions)


@router.get("/governments", response_model=Page[Government])
@with_names
def list_governments(conn: Conn):
    """Governments (derived from official government posts), newest first."""
    rows = conn.execute(
        """SELECT g.number, g.term_number, lower(g.valid) AS valid_from, upper(g.valid) AS valid_to, p.knesset_person_id,
                  p.first_name_he || ' ' || p.last_name_he AS pm_he
           FROM government g LEFT JOIN person p ON p.id = g.prime_minister_person_id ORDER BY g.number DESC""").fetchall()
    return {"data": [Government(number=r["number"], term=r["term_number"], valid=Interval(valid_from=r["valid_from"], valid_to=r["valid_to"]),
                                prime_minister=GovernmentPerson(id=r["knesset_person_id"], name_he=r["pm_he"]) if r["knesset_person_id"] else None)
                     for r in rows],
            "meta": Meta(filters={}, note="Derived from KNS_PersonToPosition: a government runs from its first post to the next government's first post.")}
