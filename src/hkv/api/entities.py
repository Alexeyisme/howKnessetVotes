"""Members, factions, bills, terms (architecture.md §13). Formulas follow §10; every rate carries
its numerator and denominator."""

from __future__ import annotations

import base64
import datetime as dt
import json
from typing import Annotated, ClassVar, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from hkv.api.common import (VOTE_SELECT, BillRef, Conn, DebateSides, Meta, MotionType, Stage, VoteSummary, attach_sides, debate_sides,
                            vote_summary)
from hkv.api.names import (BallotFactionNames, ExplanationTranslations, FactionNames, PersonNames, ProseText, SummaryTranslations,
                           TitleTranslations, TopicLabels, with_names)
from hkv.debate import FINAL_VOTE

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
    photo_url: str | None = None   # official Knesset portrait: our copy (/api/v1/members/{id}/photo.jpg), else the fs.knesset.gov.il URL
    # smaller copies for the page (migration 0016): 240 px wide for a portrait, 96 px for a chip; None until they exist
    photo_medium_url: str | None = None
    photo_thumb_url: str | None = None


class MemberStats(BaseModel):
    participation: Rate          # cast (for/against/abstain) / roll-call votes held during the member's mandates
    choices: dict[str, int]      # for / against / abstain / present_not_voting / other
    deviation_from_faction: Rate  # cast against the strict majority of other faction members / comparable votes
    with_coalition: Rate         # cast like the coalition's strict majority / cast votes where the coalition had one (U11)
    bills_initiated: int
    bills_joined: int


class MemberDetail(MemberSummary):
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
    speeches: int | None = None  # final votes on a bill with a debate summary: the member's speeches in that debate


class PartyRef(BaseModel):
    slug: str
    name_he: str
    name_ru: str
    name_en: str
    name_ar: str | None = None


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


class BillSummary(TitleTranslations):
    id: int
    title_he: str
    term: int
    origin: str | None
    status_he: str | None
    votes: int
    last_vote_on: dt.date | None
    passed_third_reading: bool
    source_url: str
    sides: DebateSides | None = None  # in lists (attach_bill_sides)


class BillTopic(TopicLabels):
    slug: str
    label_ru: str
    label_he: str
    origin: str
    review_state: str
    evidence: str | None


Alignment = Literal["coalition", "opposition", "external_support", "unknown"]


class DebateSpeaker(PersonNames, BallotFactionNames):
    """A speaker in the plenum debate, as the transcript prints them, resolved to a member where possible."""
    _person_key: ClassVar[str] = "person_id"
    person_id: int | None
    name_he: str
    label_he: str
    affiliation_he: str | None       # faction or role as printed ("בשם ועדת …")
    faction_id: int | None           # on the day of their first speech
    faction_name_he: str | None
    alignment: Alignment | None      # of that faction on the date of the final vote
    stages: list[Stage]              # readings they spoke at
    speeches: int
    chars: int
    final_choice: Choice | None      # their ballot in the final vote
    final_participation: str | None  # None: no roll-call record


class DebateArgument(ProseText):
    side: Literal["for", "against"]
    speakers: list[int]              # indexes into BillDebate.speakers


class BillDebate(BaseModel):
    """The plenum debate on the bill (hkv.debate): who spoke, and a machine summary of the arguments."""
    final_vote_id: int
    summary: ProseText
    arguments: list[DebateArgument]
    speakers: list[DebateSpeaker]
    agenda_titles: list[str]
    truncated: bool                  # long debate: every speech was shortened before summarising
    sources: list[str]               # transcript files
    model: str | None


class ReservationMember(PersonNames, BallotFactionNames):
    _person_key: ClassVar[str] = "person_id"
    person_id: int | None
    name_he: str
    faction_id: int | None
    faction_name_he: str | None


class ReservationGroup(BaseModel):
    label_he: str
    reservations: int
    sections: list[str]
    gist: ProseText | None
    members: list[ReservationMember]


class ReservationFaction(FactionNames):
    _faction_key: ClassVar[str] = "faction_id"
    faction_id: int
    name_he: str
    alignment: Alignment | None
    reservations: int                # distinct reservations (co-)proposed by its members; joint ones count for each
    members: int


class BillReservations(BaseModel):
    """The reservations filed for the second reading (hkv.reservations)."""
    total: int
    numbers_checked: bool            # false: the counts were read from the PDF pages, not checked against its text
    summary: ProseText | None
    groups: list[ReservationGroup]
    by_faction: list[ReservationFaction]
    unresolved_proposers: int        # proposers not matched to a member (counted in groups, not in by_faction)
    speak_requests: list[ReservationMember]
    source_url: str
    model: str | None


class BillDetail(BillSummary, SummaryTranslations, ExplanationTranslations):
    topics: list[BillTopic]
    summary_he: str | None
    # where there is no official summary: a machine description from the sponsors' explanatory notes (hkv.notes)
    explanation_he: str | None = None
    explanation_source_url: str | None = None   # the proposal file the notes were read from
    published_on: dt.date | None
    initiators: list[Initiator]
    related: list[BillRef]
    timeline: list[VoteSummary]
    debate: BillDebate | None = None
    reservations: BillReservations | None = None


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
           (SELECT count(*) FROM ballot b WHERE b.person_id = p.id) AS records,
           ph.photo_url, ph.sizes AS photo_sizes, ph.v AS photo_v
    FROM person p
    LEFT JOIN LATERAL (SELECT f.knesset_faction_id, f.name_he, f.term_number FROM faction_membership fm JOIN faction f ON f.id = fm.faction_id
                       WHERE fm.person_id = p.id ORDER BY lower(fm.valid) DESC LIMIT 1) lf ON true
    LEFT JOIN LATERAL (SELECT CASE WHEN ph.image_sha256 IS NOT NULL
                                   THEN '/api/v1/members/' || p.knesset_person_id || '/photo.jpg?v=' || left(ph.image_sha256, 12) ELSE ph.url END AS photo_url,
                              left(ph.image_sha256, 12) AS v,
                              (SELECT array_agg(s.width) FROM person_photo_size s WHERE s.person_id = ph.person_id
                                 AND s.source_sha256 = ph.image_sha256) AS sizes
                       FROM person_photo ph WHERE ph.person_id = p.id) ph ON true"""


def photo_size_url(r: dict, width: int) -> str | None:
    return f"/api/v1/members/{r['id']}/photo-{width}.jpg?v={r['photo_v']}" if width in (r["photo_sizes"] or []) else None


def member_summary(r: dict) -> MemberSummary:
    return MemberSummary(id=r["id"], name_he=r["name_he"], gender=r["gender"], terms=r["terms"] or [],
                         last_faction=faction_ref(r["lf_id"], r["lf_name"], r["lf_term"]), roll_call_records=r["records"],
                         photo_url=r["photo_url"], photo_medium_url=photo_size_url(r, 240), photo_thumb_url=photo_size_url(r, 96))


@router.get("/members", response_model=Page[MemberSummary])
@with_names
def list_members(conn: Conn, term: int | None = None, q: Annotated[str | None, Query(min_length=2)] = None,
                 faction: int | None = None):
    """MKs with at least one roll-call record; filter by term (held a mandate), name substring (any language), or faction membership."""
    where, params = ["EXISTS (SELECT 1 FROM ballot b WHERE b.person_id = p.id)"], {}
    if term:
        where.append("EXISTS (SELECT 1 FROM mandate m WHERE m.person_id = p.id AND m.term_number = %(term)s)"); params["term"] = term
    if q:
        # Hebrew name, or any English/Russian/Arabic name or variant (person_alias); Arabic without hamza/ta marbuta distinctions
        where.append("""((p.first_name_he || ' ' || p.last_name_he) ILIKE %(q)s
                        OR EXISTS (SELECT 1 FROM person_alias a WHERE a.person_id = p.id AND (a.full_name ILIKE %(q)s
                                     OR (a.language = 'ar' AND ar_norm(a.full_name) LIKE '%%' || ar_norm(%(raw)s) || '%%'))))""")
        params["q"], params["raw"] = f"%{q}%", q
    if faction:
        where.append("""EXISTS (SELECT 1 FROM faction_membership fm JOIN faction f ON f.id = fm.faction_id
                               WHERE fm.person_id = p.id AND f.knesset_faction_id = %(faction)s)"""); params["faction"] = faction
    rows = conn.execute(f"{MEMBER_SELECT} WHERE {' AND '.join(where)} ORDER BY p.last_name_he, p.first_name_he", params).fetchall()
    return {"data": [member_summary(r) for r in rows], "meta": Meta(filters={"term": term, "q": q, "faction": faction})}


def member_votes_cte(vote_where: str = "true") -> str:
    """Strict majority of the OTHER members of the member's faction who cast a vote (architecture.md §10).

    `vote_where` filters the votes first (columns of `v` vote and `k` vote_option_kind), so the majority is counted only
    for them. Filtering afterwards made "final votes" take 3–16 s (2026-10-09): the planner cannot estimate the
    coalesce(k.stage, v.stage) filters, expects one row and recounted the majority of every ballot per vote."""
    return f"""
    WITH mine AS MATERIALIZED (
        SELECT b.vote_id, b.faction_id, b.choice, b.participation FROM ballot b
        JOIN vote v ON v.id = b.vote_id LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
        WHERE b.person_id = %(pid)s AND {vote_where}
    ), maj AS MATERIALIZED (
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


MEMBER_VOTES_CTE = member_votes_cte()


PHOTO_HEADERS = {"Cache-Control": "public, max-age=31536000, immutable"}


@router.get("/members/{member_id}/photo-{width}.jpg", response_class=Response, responses={200: {"content": {"image/jpeg": {}}}})
def member_photo_size(member_id: int, width: int, conn: Conn):
    """A smaller copy of the portrait (photo_medium_url, photo_thumb_url; migration 0016)."""
    r = conn.execute("""SELECT s.image FROM person_photo_size s JOIN person_photo ph ON ph.person_id = s.person_id
                        JOIN person p ON p.id = s.person_id
                        WHERE p.knesset_person_id = %s AND s.width = %s AND s.source_sha256 = ph.image_sha256""", (member_id, width)).fetchone()
    if r is None:
        raise HTTPException(404, "no photo of this size")
    return Response(content=bytes(r["image"]), media_type="image/jpeg", headers=PHOTO_HEADERS)


@router.get("/members/{member_id}/photo.jpg", response_class=Response, responses={200: {"content": {"image/jpeg": {}}}})
@router.get("/members/{member_id}/photo", response_class=Response, include_in_schema=False)   # URLs before 2026-10-07
def member_photo(member_id: int, conn: Conn):
    """The official portrait from the Knesset website, served from here: the Knesset file server blocks visitors
    outside Israel (migration 0014). `?v=` in photo_url changes with the image, so it may be cached for good; the .jpg
    extension lets Cloudflare cache it."""
    r = conn.execute("""SELECT ph.image, ph.content_type FROM person_photo ph JOIN person p ON p.id = ph.person_id
                        WHERE p.knesset_person_id = %s AND ph.image IS NOT NULL""", (member_id,)).fetchone()
    if r is None:
        raise HTTPException(404, "no stored photo")
    return Response(content=bytes(r["image"]), media_type=r["content_type"], headers=PHOTO_HEADERS)


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
    # "voted with the coalition": the member's choice equals the coalition members' strict majority choice on that vote
    # (vote_bloc, from the coalition derivation); counted whatever bloc the member's own faction was in
    coal = conn.execute(
        """SELECT count(*) FILTER (WHERE m.cm IS NOT NULL) AS comparable, count(*) FILTER (WHERE m.cm IS NOT NULL AND b.choice = m.cm) AS with_c
           FROM ballot b JOIN vote_bloc vb ON vb.vote_id = b.vote_id
           CROSS JOIN LATERAL (SELECT CASE WHEN 2 * vb.coalition_for > s THEN 'for' WHEN 2 * vb.coalition_against > s THEN 'against'
                                           WHEN 2 * vb.coalition_abstain > s THEN 'abstain' END AS cm
                               FROM (SELECT vb.coalition_for + vb.coalition_against + vb.coalition_abstain AS s) x) m
           WHERE b.person_id = %s AND b.choice IS NOT NULL""", (pid,)).fetchone()
    bills = dict((x["role"], x["n"]) for x in conn.execute("SELECT role, count(*) AS n FROM bill_initiator WHERE person_id = %s GROUP BY 1", (pid,)))
    base = member_summary(r)
    return {
        "data": MemberDetail(
            **base.model_dump(),
            mandates=mandates,
            factions=[MembershipOut(faction=faction_ref(f["knesset_faction_id"], f["name_he"], f["term_number"]),
                                    valid_from=f["valid_from"], valid_to=f["valid_to"]) for f in factions],
            stats=MemberStats(participation=rate(cast, available), choices=choices,
                              deviation_from_faction=rate(dev["deviated"], dev["comparable"]),
                              with_coalition=rate(coal["with_c"], coal["comparable"]),
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
                 deviated: bool = False, topic: Annotated[str | None, Query(description="topic slug of a bill the vote is about")] = None,
                 limit: Annotated[int, Query(ge=1, le=100)] = 50, cursor: str | None = None):
    pid = person_id(conn, member_id)
    where, params = ["true"], {"pid": pid, "limit": limit + 1}   # vote filters, applied inside the CTE
    if topic:
        where.append("""EXISTS (SELECT 1 FROM vote_subject s JOIN bill_topic bt ON bt.bill_id = s.bill_id JOIN topic t ON t.id = bt.topic_id
                                WHERE s.vote_id = v.id AND t.slug = %(topic)s AND bt.review_state <> 'rejected')"""); params["topic"] = topic
    if date_from:
        where.append("v.occurred_on >= %(date_from)s"); params["date_from"] = date_from
    if date_to:
        where.append("v.occurred_on <= %(date_to)s"); params["date_to"] = date_to
    if stage:
        where.append("coalesce(k.stage, v.stage) = ANY(%(stage)s)"); params["stage"] = stage
    if motion_type:
        where.append("coalesce(k.motion_type, v.motion_type) = ANY(%(motion)s)"); params["motion"] = motion_type
    if cursor:
        c_on, c_id = decode_cursor(cursor)
        where.append("(v.occurred_on, v.knesset_vote_id) < (%(c_on)s::date, %(c_id)s)"); params.update(c_on=c_on, c_id=c_id)
    after = "cmp.choice IS NOT NULL AND cmp.majority IS NOT NULL AND cmp.choice <> cmp.majority" if deviated else "true"
    rows = conn.execute(f"""{member_votes_cte(' AND '.join(where))}
        SELECT v.knesset_vote_id AS vid, v.occurred_on, cmp.choice, cmp.participation, cmp.f, cmp.a, cmp.ab, cmp.majority,
               f.knesset_faction_id, f.name_he AS faction_name, f.term_number AS faction_term
        FROM cmp JOIN vote v ON v.id = cmp.vote_id
        LEFT JOIN faction f ON f.id = cmp.faction_id
        WHERE {after} ORDER BY v.occurred_on DESC, v.knesset_vote_id DESC LIMIT %(limit)s""", params).fetchall()
    more, rows = len(rows) > limit, rows[:limit]
    summaries = {s["id"]: vote_summary(s) for s in conn.execute(f"{VOTE_SELECT} WHERE v.knesset_vote_id = ANY(%s)", ([r["vid"] for r in rows],))}
    attach_sides(conn, list(summaries.values()))
    speeches = member_speeches(conn, pid, list(summaries.values()))
    data = [MemberVote(
        vote=summaries[r["vid"]], choice=r["choice"], participation=r["participation"],
        faction=faction_ref(r["knesset_faction_id"], r["faction_name"], r["faction_term"]),
        faction_majority=r["majority"] or ("none" if r["f"] is None or (r["f"] + r["a"] + r["ab"]) < MIN_COLLEAGUES else "mixed"),
        deviates=None if r["choice"] is None or r["majority"] is None else r["choice"] != r["majority"],
        speeches=speeches.get(r["vid"]),
    ) for r in rows]
    return {"data": data, "meta": Meta(filters={"id": member_id, "deviated": deviated, "stage": stage, "motion_type": motion_type, "topic": topic}),
            "next_cursor": encode_cursor(rows[-1]["occurred_on"], rows[-1]["vid"]) if more else None}


def member_speeches(conn, pid, votes: list[VoteSummary]) -> dict[int, int]:
    """Vote id -> the member's speeches in the plenum debate on the vote's bill (0: did not speak), for final votes on
    bills with a debate summary."""
    bills = {b.id: v.id for v in votes for b in v.bills if b.sides is not None and b.sides.speakers is not None}
    if not bills:
        return {}
    out: dict[int, int] = {}
    for r in conn.execute(
        """SELECT b.knesset_bill_id AS id, coalesce(sum(s.speeches), 0) AS n FROM bill b
           LEFT JOIN bill_debate_speaker s ON s.bill_id = b.id AND s.person_id = %s
           WHERE b.knesset_bill_id = ANY(%s) GROUP BY 1""", (pid, list(bills))):
        out[bills[r["id"]]] = max(out.get(bills[r["id"]], 0), r["n"])
    return out


# -- compare (U7) -------------------------------------------------------------------------------------

class CompareSide(BaseModel):
    """What one side did on a vote where the two differed: a member's choice, or a faction's majority."""
    choice: str


class CompareDiff(BaseModel):
    vote: VoteSummary
    a: CompareSide
    b: CompareSide


class Comparison(BaseModel):
    agreement: Rate              # same choice (members) or same strict majority (factions) / votes where both took a side
    differences: list[CompareDiff]   # most recent first, capped
    stage: list[str]
    motion_type: list[str]


DIFF_LIMIT = 100


def _compare(conn, rows: list[dict], stage: list[str], motion: list[str]) -> Comparison:
    """rows: vote id, occurred_on, a, b (choices, None when that side took no side)."""
    both = [r for r in rows if r["a"] and r["b"]]
    diffs = [r for r in both if r["a"] != r["b"]][:DIFF_LIMIT]
    summaries = {s["id"]: vote_summary(s) for s in conn.execute(f"{VOTE_SELECT} WHERE v.knesset_vote_id = ANY(%s)", ([r["vid"] for r in diffs],))} if diffs else {}
    return Comparison(agreement=rate(len(both) - sum(1 for r in both if r["a"] != r["b"]), len(both)),
                      differences=[CompareDiff(vote=summaries[r["vid"]], a=CompareSide(choice=r["a"]), b=CompareSide(choice=r["b"])) for r in diffs],
                      stage=stage, motion_type=motion)


@router.get("/compare/members", response_model=One[Comparison])
@with_names
def compare_members(conn: Conn, a: int, b: int, stage: Annotated[list[Stage] | None, Query()] = None,
                    motion_type: Annotated[list[MotionType] | None, Query()] = None):
    """Two MKs on the votes both cast: agreement rate and the votes where they chose differently.
    Default scope: votes on bills as a whole and no-confidence motions, any stage."""
    pa, pb = person_id(conn, a), person_id(conn, b)
    stages, motions = stage or [], motion_type or ["adopt_bill", "no_confidence"]
    rows = conn.execute(
        """SELECT v.knesset_vote_id AS vid, v.occurred_on, x.choice AS a, y.choice AS b
           FROM ballot x JOIN ballot y ON y.vote_id = x.vote_id AND y.person_id = %(pb)s JOIN vote v ON v.id = x.vote_id
           LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
           WHERE x.person_id = %(pa)s AND x.choice IS NOT NULL AND y.choice IS NOT NULL
             AND (%(nostage)s OR coalesce(k.stage, v.stage) = ANY(%(stages)s)) AND coalesce(k.motion_type, v.motion_type) = ANY(%(motions)s)
           ORDER BY v.occurred_on DESC, v.knesset_vote_id DESC""",
        {"pa": pa, "pb": pb, "stages": stages, "nostage": not stages, "motions": motions}).fetchall()
    return {"data": _compare(conn, rows, stages, motions), "meta": Meta(filters={"a": a, "b": b, "stage": stages, "motion_type": motions}, note=(
        "agreement = votes where both chose the same of for/against/abstain / votes where both cast a vote."))}


@router.get("/compare/factions", response_model=One[Comparison])
@with_names
def compare_factions(conn: Conn, a: int, b: int, stage: Annotated[list[Stage] | None, Query()] = None,
                     motion_type: Annotated[list[MotionType] | None, Query()] = None):
    """Two factions on the votes where each had a strict majority among its casting members: agreement rate and the
    votes where the majorities differed. Default scope: votes on bills as a whole and no-confidence motions."""
    fa, fb = faction_pk(conn, a)["pk"], faction_pk(conn, b)["pk"]
    stages, motions = stage or [], motion_type or ["adopt_bill", "no_confidence"]
    rows = conn.execute(
        f"""WITH per AS (
               SELECT vote_id, faction_id, count(*) FILTER (WHERE choice = 'for') f, count(*) FILTER (WHERE choice = 'against') a,
                      count(*) FILTER (WHERE choice = 'abstain') ab
               FROM ballot WHERE faction_id IN (%(fa)s, %(fb)s) AND choice IS NOT NULL GROUP BY 1, 2),
           maj AS (
               SELECT vote_id, faction_id, CASE WHEN f + a + ab < {MIN_COLLEAGUES} THEN NULL WHEN 2 * f > f + a + ab THEN 'for'
                                               WHEN 2 * a > f + a + ab THEN 'against' WHEN 2 * ab > f + a + ab THEN 'abstain' END AS m
               FROM per)
           SELECT v.knesset_vote_id AS vid, v.occurred_on, x.m AS a, y.m AS b
           FROM maj x JOIN maj y ON y.vote_id = x.vote_id AND y.faction_id = %(fb)s JOIN vote v ON v.id = x.vote_id
           LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
           WHERE x.faction_id = %(fa)s AND x.m IS NOT NULL AND y.m IS NOT NULL
             AND (%(nostage)s OR coalesce(k.stage, v.stage) = ANY(%(stages)s)) AND coalesce(k.motion_type, v.motion_type) = ANY(%(motions)s)
           ORDER BY v.occurred_on DESC, v.knesset_vote_id DESC""",
        {"fa": fa, "fb": fb, "stages": stages, "nostage": not stages, "motions": motions}).fetchall()
    return {"data": _compare(conn, rows, stages, motions), "meta": Meta(filters={"a": a, "b": b, "stage": stages, "motion_type": motions}, note=(
        f"agreement = votes where both factions' casting members (at least {MIN_COLLEAGUES}) had the same strict majority / "
        "votes where both had one."))}


# -- factions ----------------------------------------------------------------------------------------

FACTION_SELECT = """
    SELECT f.id AS pk, f.knesset_faction_id AS id, f.name_he, f.term_number AS term, lower(f.valid) AS valid_from, upper(f.valid) AS valid_to,
           (SELECT fl.name FROM faction_label fl WHERE fl.faction_id = f.id AND fl.language = 'ru') AS name_ru,
           (SELECT count(DISTINCT fm.person_id) FROM faction_membership fm WHERE fm.faction_id = f.id) AS members_ever,
           (SELECT count(*) FROM ballot b WHERE b.faction_id = f.id) AS records,
           (SELECT coalesce(json_agg(json_build_object('slug', p.slug, 'name_he', p.name_he, 'name_ru', p.name_ru, 'name_en', p.name_en, 'name_ar', p.name_ar) ORDER BY p.sort), '[]')
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
    where, params = ["true"], {"fid": r["pk"], "limit": limit + 1}   # vote filters, applied inside the CTE (see member_votes_cte)
    if stage:
        where.append("coalesce(k.stage, v.stage) = ANY(%(stage)s)"); params["stage"] = stage
    if motion_type:
        where.append("coalesce(k.motion_type, v.motion_type) = ANY(%(motion)s)"); params["motion"] = motion_type
    if cursor:
        c_on, c_id = decode_cursor(cursor)
        where.append("(v.occurred_on, v.knesset_vote_id) < (%(c_on)s::date, %(c_id)s)"); params.update(c_on=c_on, c_id=c_id)
    after = "greatest(c.f, c.a, c.ab) < c.f + c.a + c.ab" if split_only else "true"
    rows = conn.execute(f"""
        WITH c AS MATERIALIZED (
            SELECT b.vote_id, count(*) FILTER (WHERE b.choice = 'for') f, count(*) FILTER (WHERE b.choice = 'against') a,
                   count(*) FILTER (WHERE b.choice = 'abstain') ab, count(*) FILTER (WHERE b.participation = 'present_not_voting') p,
                   count(*) n
            FROM ballot b JOIN vote v ON v.id = b.vote_id LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
            WHERE b.faction_id = %(fid)s AND {' AND '.join(where)} GROUP BY b.vote_id)
        SELECT v.knesset_vote_id AS vid, v.occurred_on, c.f, c.a, c.ab, c.p, c.n FROM c JOIN vote v ON v.id = c.vote_id
        WHERE {after} ORDER BY v.occurred_on DESC, v.knesset_vote_id DESC LIMIT %(limit)s""", params).fetchall()
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


def attach_bill_sides(conn, bills: list[BillSummary]) -> None:
    found = debate_sides(conn, [b.id for b in bills]) if bills else {}
    for b in bills:
        b.sides = found.get(b.id)


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
    data = [bill_summary(r) for r in rows]
    attach_bill_sides(conn, data)
    return {"data": data, "meta": Meta(filters={"q": q, "term": term, "third_reading": third_reading, "topic": topic}),
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
    explanation = None if r["summary_he"] else conn.execute(
        """SELECT e.summary_he, d.url FROM bill_explanation e JOIN bill_document d ON d.knesset_document_id = e.document_id
           WHERE e.bill_id = %s""", (r["pk"],)).fetchone()
    return {"data": BillDetail(**bill_summary(r).model_dump(), topics=topics, summary_he=r["summary_he"], published_on=r["published_on"],
                               explanation_he=explanation and explanation["summary_he"], explanation_source_url=explanation and explanation["url"],
                               initiators=initiators, related=related, timeline=[vote_summary(t) for t in timeline],
                               debate=bill_debate(conn, r["pk"]), reservations=bill_reservations(conn, r["pk"])),
            "meta": Meta(filters={"id": bill_id})}


def bill_debate(conn, pk) -> BillDebate | None:
    d = conn.execute(
        """SELECT d.*, v.knesset_vote_id, v.occurred_on,
                  (SELECT array_agg(p.url ORDER BY p.knesset_document_id) FROM plenum_document p
                   WHERE p.knesset_document_id = ANY(d.document_ids)) AS urls
           FROM bill_debate d JOIN vote v ON v.id = d.vote_id WHERE d.bill_id = %s""", (pk,)).fetchone()
    if d is None:
        return None
    speakers = conn.execute(
        """SELECT p.knesset_person_id AS person_id, s.name_he, s.label_he, s.affiliation_he, f.knesset_faction_id AS faction_id,
                  f.name_he AS faction_name_he, a.role AS alignment, s.stages, s.speeches, s.chars,
                  b.choice AS final_choice, b.participation AS final_participation
           FROM bill_debate_speaker s LEFT JOIN person p ON p.id = s.person_id LEFT JOIN faction f ON f.id = s.faction_id
           LEFT JOIN faction_alignment a ON a.faction_id = s.faction_id AND a.valid @> %(on)s::date
           LEFT JOIN ballot b ON b.vote_id = %(vote)s AND b.person_id = s.person_id
           WHERE s.bill_id = %(bill)s ORDER BY s.ordinal""", {"bill": pk, "vote": d["vote_id"], "on": d["occurred_on"]}).fetchall()
    return BillDebate(final_vote_id=d["knesset_vote_id"], summary=ProseText(text_he=d["summary_he"]),
                      arguments=[DebateArgument(side=a["side"], text_he=a["text_he"], speakers=a["speakers"]) for a in d["arguments"]],
                      speakers=[DebateSpeaker(**{**s, "stages": list(dict.fromkeys("third" if x == "second" else x for x in s["stages"]))})
                                for s in speakers],
                      agenda_titles=d["segment_titles"], truncated=d["truncated"], sources=d["urls"] or [], model=d["model"])


def bill_reservations(conn, pk) -> BillReservations | None:
    r = conn.execute(
        f"""SELECT r.*, d.url,
                   (SELECT max(v.occurred_on) FROM vote v JOIN vote_subject vs ON vs.vote_id = v.id
                    LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
                    WHERE vs.bill_id = r.bill_id AND {FINAL_VOTE}) AS final_on
            FROM bill_reservations r JOIN bill_document d ON d.knesset_document_id = r.document_id WHERE r.bill_id = %s""", (pk,)).fetchone()
    if r is None:
        return None
    people = conn.execute(
        """SELECT p.role, p.group_ordinal, pe.knesset_person_id AS person_id, p.name_he, f.knesset_faction_id AS faction_id,
                  f.name_he AS faction_name_he
           FROM bill_reservation_person p LEFT JOIN person pe ON pe.id = p.person_id LEFT JOIN faction f ON f.id = p.faction_id
           WHERE p.bill_id = %s ORDER BY p.role, p.ordinal""", (pk,)).fetchall()
    member = lambda x: ReservationMember(person_id=x["person_id"], name_he=x["name_he"], faction_id=x["faction_id"],  # noqa: E731
                                         faction_name_he=x["faction_name_he"])
    groups = [ReservationGroup(label_he=g["label_he"], reservations=len(g["numbers"]), sections=g["sections"],
                               gist=ProseText(text_he=g["gist_he"]) if g["gist_he"] else None,
                               members=[member(x) for x in people if x["role"] == "proposer" and x["group_ordinal"] == g["ordinal"]])
              for g in conn.execute("SELECT * FROM bill_reservation_group WHERE bill_id = %s ORDER BY cardinality(numbers) DESC, ordinal", (pk,))
              if g["numbers"]]
    by_faction = conn.execute(
        """SELECT f.knesset_faction_id AS faction_id, f.name_he, a.role AS alignment,
                  count(DISTINCT n) AS reservations, count(DISTINCT p.person_id) AS members
           FROM bill_reservation_person p
           JOIN bill_reservation_group g ON g.bill_id = p.bill_id AND g.ordinal = p.group_ordinal
           CROSS JOIN LATERAL unnest(g.numbers) n
           JOIN faction f ON f.id = p.faction_id
           LEFT JOIN faction_alignment a ON a.faction_id = f.id AND a.valid @> %(on)s::date
           WHERE p.bill_id = %(bill)s AND p.role = 'proposer'
           GROUP BY 1, 2, 3 ORDER BY 4 DESC, 2""", {"bill": pk, "on": r["final_on"]}).fetchall()
    return BillReservations(total=r["total"], numbers_checked=r["numbers_checked"],
                            summary=ProseText(text_he=r["summary_he"]) if r["summary_he"] else None,
                            groups=groups, by_faction=[ReservationFaction(**f) for f in by_faction],
                            unresolved_proposers=sum(x["role"] == "proposer" and x["faction_id"] is None for x in people),
                            speak_requests=[member(x) for x in people if x["role"] == "speaker"],
                            source_url=r["url"], model=r["model"])


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
    return PartySummary(slug=p["slug"], name_he=p["name_he"], name_ru=p["name_ru"], name_en=p["name_en"], name_ar=p["name_ar"],
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
