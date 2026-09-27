"""Public read-only REST API, /api/v1 (architecture.md §13, MVP subset).

Public IDs are the official Knesset IDs (vote, bill, faction, person), so every object
can be checked against the source; `source_url` points at the official vote card.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_DB = "postgresql://knesset:knesset@localhost:5433/knesset"
VOTE_CARD = "https://main.knesset.gov.il/Activity/plenum/Votes/Pages/vote.aspx?voteId={}"

Stage = Literal["preliminary", "first", "second", "third", "not_applicable", "unknown"]
MotionType = Literal["adopt_bill", "reject_bill", "adopt_section", "reservation", "no_confidence", "agenda",
                     "secondary_legislation", "procedural", "other", "unknown"]


# -- response models (the OpenAPI contract) --------------------------------------------------------

class Counts(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    for_: int = Field(alias="for")
    against: int
    abstain: int
    present_not_voting: int
    other: int  # participated_choice_unavailable, absent_reported, unknown
    total_records: int


class OfficialTotals(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    for_: int = Field(alias="for")
    against: int
    abstain: int
    is_accepted: bool | None
    source: str


class BillRef(BaseModel):
    id: int
    title_he: str


class VoteSummary(BaseModel):
    id: int
    occurred_on: dt.date
    occurred_at: dt.datetime | None
    term: int
    title_he: str
    subject_he: str | None
    question_he: str | None
    motion_type: MotionType | None
    stage: Stage | None
    method: str
    status: str
    bills: list[BillRef]
    roll_call: Counts
    source_url: str


class FactionBreakdown(BaseModel):
    faction_id: int
    name_he: str
    counts: Counts
    majority: Literal["for", "against", "abstain", "mixed", "none"]
    ambiguous_records: int


class VoteDetail(VoteSummary):
    official_totals: OfficialTotals | None
    totals_match: bool | None  # official totals vs roll-call records counted by the source
    excluded_from_official_total: int  # records the legacy source marks as not in the official totals
    by_faction: list[FactionBreakdown]
    unresolved_faction_records: int


class Ballot(BaseModel):
    person_id: int
    name_he: str
    faction_id: int | None
    faction_name_he: str | None
    faction_ambiguous: bool
    choice: Literal["for", "against", "abstain"] | None
    participation: str
    source_result_code: int
    source: Literal["knesset_odata_v4", "knesset_votes_legacy"]
    counted_in_official_total: bool | None


class Meta(BaseModel):
    date_basis: str = "vote_date"
    timezone: str = "Asia/Jerusalem"
    filters: dict
    note: str | None = None


class VoteList(BaseModel):
    data: list[VoteSummary]
    meta: Meta
    next_cursor: str | None


class VoteDetailResponse(BaseModel):
    data: VoteDetail
    meta: Meta


class BallotList(BaseModel):
    data: list[Ballot]
    meta: Meta


# -- app -------------------------------------------------------------------------------------------

def db(request: Request):
    with request.app.state.pool.connection() as conn:
        yield conn


Conn = Annotated[Connection, Depends(db)]


def create_app(database_url: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pool = ConnectionPool(database_url or os.environ.get("DATABASE_URL", DEFAULT_DB), min_size=1, max_size=10,
                                        kwargs={"row_factory": dict_row}, open=True)
        yield
        app.state.pool.close()

    app = FastAPI(title="howKnessetVotes API", version="0.1.0", lifespan=lifespan,
                  description="Plenum roll-call votes of the Knesset. IDs are official Knesset IDs.")

    @app.get("/api/v1/votes", response_model=VoteList)
    def list_votes(
        conn: Conn,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
        stage: Annotated[list[Stage] | None, Query()] = None,
        motion_type: Annotated[list[MotionType] | None, Query()] = None,
        bill: Annotated[list[int] | None, Query(description="Knesset bill ID")] = None,
        faction: Annotated[list[int] | None, Query(description="Knesset faction ID: votes with at least one roll-call record of the faction")] = None,
        person: Annotated[list[int] | None, Query(description="Knesset person ID: votes with a roll-call record of the person")] = None,
        q: Annotated[str | None, Query(min_length=2, description="Substring of the Hebrew title")] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: str | None = None,
    ):
        filters = {k: v for k, v in dict(date_from=date_from, date_to=date_to, stage=stage, motion_type=motion_type, bill=bill,
                                         faction=faction, person=person, q=q).items() if v is not None}
        where, params = ["true"], {}
        if date_from:
            where.append("v.occurred_on >= %(date_from)s"); params["date_from"] = date_from
        if date_to:
            where.append("v.occurred_on <= %(date_to)s"); params["date_to"] = date_to
        if stage:
            where.append("coalesce(k.stage, v.stage) = ANY(%(stage)s)"); params["stage"] = stage
        if motion_type:
            where.append("coalesce(k.motion_type, v.motion_type) = ANY(%(motion)s)"); params["motion"] = motion_type
        if bill:
            where.append("EXISTS (SELECT 1 FROM vote_subject s JOIN bill b ON b.id = s.bill_id WHERE s.vote_id = v.id AND b.knesset_bill_id = ANY(%(bill)s))")
            params["bill"] = bill
        if faction:
            where.append("EXISTS (SELECT 1 FROM ballot x JOIN faction f ON f.id = x.faction_id WHERE x.vote_id = v.id AND f.knesset_faction_id = ANY(%(faction)s))")
            params["faction"] = faction
        if person:
            where.append("EXISTS (SELECT 1 FROM ballot x JOIN person p ON p.id = x.person_id WHERE x.vote_id = v.id AND p.knesset_person_id = ANY(%(person)s))")
            params["person"] = person
        if q:
            where.append("v.title_he ILIKE %(q)s"); params["q"] = f"%{q}%"
        if cursor:
            try:
                c_on, c_id = json.loads(base64.urlsafe_b64decode(cursor))
            except Exception as e:  # noqa: BLE001
                raise HTTPException(400, "invalid cursor") from e
            where.append("(v.occurred_on, v.knesset_vote_id) < (%(c_on)s::date, %(c_id)s)"); params.update(c_on=c_on, c_id=c_id)
        params["limit"] = limit + 1
        rows = conn.execute(f"{VOTE_SELECT} WHERE {' AND '.join(where)} ORDER BY v.occurred_on DESC, v.knesset_vote_id DESC LIMIT %(limit)s", params).fetchall()
        more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = base64.urlsafe_b64encode(json.dumps([rows[-1]["occurred_on"].isoformat(), rows[-1]["id"]]).encode()).decode() if more else None
        return {"data": [vote_summary(r) for r in rows], "meta": Meta(filters=filters, note=COUNTS_NOTE), "next_cursor": next_cursor}

    @app.get("/api/v1/votes/{vote_id}", response_model=VoteDetailResponse)
    def get_vote(vote_id: int, conn: Conn):
        row = conn.execute(f"{VOTE_SELECT} WHERE v.knesset_vote_id = %s", (vote_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "vote not found")
        detail = vote_summary(row)
        off = conn.execute(
            """SELECT for_count, against_count, abstain_count, is_accepted, source FROM vote_result_official o
               JOIN vote v ON v.id = o.vote_id WHERE v.knesset_vote_id = %s""", (vote_id,)).fetchone()
        official = OfficialTotals(for_=off["for_count"], against=off["against_count"], abstain=off["abstain_count"],
                                  is_accepted=off["is_accepted"], source=off["source"]) if off else None
        factions = conn.execute(
            f"""SELECT f.knesset_faction_id, f.name_he, {COUNT_COLUMNS}, count(*) FILTER (WHERE b.faction_ambiguous) AS ambiguous
                FROM ballot b JOIN vote v ON v.id = b.vote_id JOIN faction f ON f.id = b.faction_id
                WHERE v.knesset_vote_id = %s GROUP BY 1, 2 ORDER BY count(*) DESC, 2""", (vote_id,)).fetchall()
        unresolved = conn.execute(
            "SELECT count(*) AS n FROM ballot b JOIN vote v ON v.id = b.vote_id WHERE v.knesset_vote_id = %s AND b.faction_id IS NULL",
            (vote_id,)).fetchone()["n"]
        # compare with the official totals only the records the legacy source says were counted
        counted = conn.execute(
            """SELECT count(*) FILTER (WHERE b.choice = 'for') AS f, count(*) FILTER (WHERE b.choice = 'against') AS a,
                      count(*) FILTER (WHERE b.choice = 'abstain') AS ab
               FROM ballot b JOIN vote v ON v.id = b.vote_id WHERE v.knesset_vote_id = %s AND b.counted_in_official_total IS NOT FALSE""",
            (vote_id,)).fetchone()
        return {
            "data": VoteDetail(
                **detail.model_dump(),
                official_totals=official,
                totals_match=None if official is None else (counted["f"], counted["a"], counted["ab"]) == (official.for_, official.against, official.abstain),
                excluded_from_official_total=conn.execute(
                    """SELECT count(*) AS n FROM ballot b JOIN vote v ON v.id = b.vote_id
                       WHERE v.knesset_vote_id = %s AND b.counted_in_official_total IS FALSE""", (vote_id,)).fetchone()["n"],
                by_faction=[FactionBreakdown(faction_id=f["knesset_faction_id"], name_he=f["name_he"].strip(), counts=counts(f),
                                             majority=majority(counts(f)), ambiguous_records=f["ambiguous"]) for f in factions],
                unresolved_faction_records=unresolved,
            ),
            "meta": Meta(filters={"id": vote_id}, note=COUNTS_NOTE),
        }

    @app.get("/api/v1/votes/{vote_id}/ballots", response_model=BallotList)
    def get_ballots(vote_id: int, conn: Conn):
        if conn.execute("SELECT 1 FROM vote WHERE knesset_vote_id = %s", (vote_id,)).fetchone() is None:
            raise HTTPException(404, "vote not found")
        rows = conn.execute(
            """SELECT p.knesset_person_id, p.first_name_he, p.last_name_he, f.knesset_faction_id, f.name_he AS faction_name,
                      b.faction_ambiguous, b.choice, b.participation, b.source_result_code, b.source, b.counted_in_official_total
               FROM ballot b JOIN vote v ON v.id = b.vote_id JOIN person p ON p.id = b.person_id
               LEFT JOIN faction f ON f.id = b.faction_id
               WHERE v.knesset_vote_id = %s ORDER BY f.name_he NULLS LAST, p.last_name_he, p.first_name_he""", (vote_id,)).fetchall()
        return {
            "data": [Ballot(person_id=r["knesset_person_id"], name_he=f"{r['first_name_he']} {r['last_name_he']}",
                            faction_id=r["knesset_faction_id"], faction_name_he=r["faction_name"].strip() if r["faction_name"] else None,
                            faction_ambiguous=r["faction_ambiguous"], choice=r["choice"], participation=r["participation"],
                            source_result_code=r["source_result_code"], source=r["source"], counted_in_official_total=r["counted_in_official_total"]) for r in rows],
            "meta": Meta(filters={"id": vote_id}, note="MKs without a record are not listed: no record does not mean absent."),
        }

    return app


COUNTS_NOTE = ("roll_call counts roll-call records only. MKs without a record are not counted and are not 'absent'. "
               "Official totals exist only for votes up to 2021-07 (legacy source).")

COUNT_COLUMNS = """count(*) FILTER (WHERE b.choice = 'for') AS n_for,
                   count(*) FILTER (WHERE b.choice = 'against') AS n_against,
                   count(*) FILTER (WHERE b.choice = 'abstain') AS n_abstain,
                   count(*) FILTER (WHERE b.participation = 'present_not_voting') AS n_present,
                   count(*) FILTER (WHERE b.participation NOT IN ('cast', 'present_not_voting')) AS n_other,
                   count(*) AS n_total"""

VOTE_SELECT = f"""
    SELECT v.knesset_vote_id AS id, v.occurred_on, v.occurred_at, v.term_number, v.title_he, v.subject_he,
           coalesce(v.for_option_he, v.legacy_item_he) AS for_option_he,
           coalesce(k.motion_type, v.motion_type) AS motion_type, coalesce(k.stage, v.stage) AS stage, v.method, v.status,
           coalesce((SELECT json_agg(json_build_object('id', b.knesset_bill_id, 'title_he', b.title_he) ORDER BY b.knesset_bill_id)
                     FROM vote_subject s JOIN bill b ON b.id = s.bill_id WHERE s.vote_id = v.id), '[]') AS bills,
           c.*
    FROM vote v
    LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
    CROSS JOIN LATERAL (SELECT {COUNT_COLUMNS} FROM ballot b WHERE b.vote_id = v.id) c"""


def counts(r: dict) -> Counts:
    return Counts(for_=r["n_for"], against=r["n_against"], abstain=r["n_abstain"], present_not_voting=r["n_present"],
                  other=r["n_other"], total_records=r["n_total"])


def majority(c: Counts) -> str:
    """Strict majority among for/against/abstain (architecture.md §10)."""
    cast = c.for_ + c.against + c.abstain
    if cast == 0:
        return "none"
    for name, n in (("for", c.for_), ("against", c.against), ("abstain", c.abstain)):
        if 2 * n > cast:
            return name
    return "mixed"


def vote_summary(r: dict) -> VoteSummary:
    return VoteSummary(id=r["id"], occurred_on=r["occurred_on"], occurred_at=r["occurred_at"], term=r["term_number"],
                       title_he=r["title_he"], subject_he=r["subject_he"], question_he=r["for_option_he"],
                       motion_type=r["motion_type"], stage=r["stage"], method=r["method"], status=r["status"],
                       bills=[BillRef(**b) for b in r["bills"]], roll_call=counts(r), source_url=VOTE_CARD.format(r["id"]))


app = create_app()
