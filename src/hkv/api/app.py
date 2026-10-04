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
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from hkv.api.common import (COUNT_COLUMNS, COUNTS_NOTE, DEFAULT_DB, VOTE_SELECT, Ballot, BallotList, Conn, FactionBreakdown, Meta,
                            MotionType, OfficialTotals, Stage, VoteDetail, VoteDetailResponse, VoteList, counts, majority, vote_summary)
from hkv.api.entities import router
from hkv.api.names import with_names
from hkv.api.suggestions import router as suggestions_router
from hkv.api.topics import router as topics_router


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

    @with_names
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
        topic: Annotated[list[str] | None, Query(description="Topic slug (rule-based, inherited from the bill)")] = None,
        contested: Annotated[bool, Query(description="only votes where the coalition and opposition majorities differed")] = False,
        min_cast: Annotated[int | None, Query(ge=0, le=120, description="at least this many for/against/abstain records")] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: str | None = None,
    ):
        filters = {k: v for k, v in dict(date_from=date_from, date_to=date_to, stage=stage, motion_type=motion_type, bill=bill,
                                         faction=faction, person=person, q=q, topic=topic, min_cast=min_cast).items() if v is not None}
        if contested:
            filters["contested"] = True
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
        if topic:
            where.append("""EXISTS (SELECT 1 FROM vote_subject s JOIN bill_topic bt ON bt.bill_id = s.bill_id JOIN topic t ON t.id = bt.topic_id
                                    WHERE s.vote_id = v.id AND t.slug = ANY(%(topic)s) AND bt.review_state <> 'rejected')""")
            params["topic"] = topic
        if contested:
            where.append("vb.contested")
        if min_cast is not None:
            where.append("c.n_for + c.n_against + c.n_abstain >= %(min_cast)s"); params["min_cast"] = min_cast
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

    @with_names
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
            f"""SELECT f.knesset_faction_id, f.name_he, a.role AS alignment, {COUNT_COLUMNS}, count(*) FILTER (WHERE b.faction_ambiguous) AS ambiguous
                FROM ballot b JOIN vote v ON v.id = b.vote_id JOIN faction f ON f.id = b.faction_id
                LEFT JOIN faction_alignment a ON a.faction_id = f.id AND a.valid @> v.occurred_on
                WHERE v.knesset_vote_id = %s GROUP BY 1, 2, 3 ORDER BY count(*) DESC, 2""", (vote_id,)).fetchall()
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
                                             majority=majority(counts(f)), ambiguous_records=f["ambiguous"],
                                             alignment=f["alignment"]) for f in factions],
                unresolved_faction_records=unresolved,
            ),
            "meta": Meta(filters={"id": vote_id}, note=COUNTS_NOTE),
        }

    @app.get("/api/v1/votes/{vote_id}/ballots", response_model=BallotList)

    @with_names
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

    app.include_router(router)
    app.include_router(topics_router)
    app.include_router(suggestions_router)

    @app.get("/api/v1/status")

    @with_names
    def status(conn: Conn):
        """When the data was last refreshed and what it covers."""
        r = conn.execute("SELECT published_at, notes, coverage FROM data_release ORDER BY published_at DESC LIMIT 1").fetchone()
        return {"data": r, "meta": {"note": "coverage of the latest data release"}}

    return app


app = create_app()
