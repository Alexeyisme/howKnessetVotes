"""Shared API models, DB dependency and vote query pieces."""

from __future__ import annotations

import datetime as dt
from typing import Annotated, ClassVar, Literal

from fastapi import Depends, Request
from psycopg import Connection
from pydantic import BaseModel, ConfigDict, Field

from hkv.api.names import BallotFactionNames, FactionNames, PersonNames, TitleTranslations

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


class BillRef(TitleTranslations):
    id: int
    title_he: str


class BlocCounts(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    for_: int = Field(alias="for")
    against: int
    abstain: int


class Blocs(BaseModel):
    """Cast votes by members of coalition and opposition factions on the vote date (derived from government posts)."""
    coalition: BlocCounts
    opposition: BlocCounts
    contested: bool  # both blocs had a strict majority, and they differed


class VoteSummary(TitleTranslations):
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
    blocs: Blocs | None = None
    source_url: str


class FactionBreakdown(FactionNames):
    _faction_key: ClassVar[str] = "faction_id"
    faction_id: int
    name_he: str
    counts: Counts
    majority: Literal["for", "against", "abstain", "mixed", "none"]
    ambiguous_records: int
    alignment: Literal["coalition", "opposition", "external_support", "unknown"] | None = None  # on the vote date


class VoteDetail(VoteSummary):
    official_totals: OfficialTotals | None
    totals_match: bool | None  # official totals vs roll-call records counted by the source
    excluded_from_official_total: int  # records the legacy source marks as not in the official totals
    by_faction: list[FactionBreakdown]
    unresolved_faction_records: int


class Ballot(PersonNames, BallotFactionNames):
    _person_key: ClassVar[str] = "person_id"
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
           c.*, vb.coalition_for, vb.coalition_against, vb.coalition_abstain, vb.opposition_for, vb.opposition_against,
           vb.opposition_abstain, vb.contested
    FROM vote v
    LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
    LEFT JOIN vote_bloc vb ON vb.vote_id = v.id
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
                       bills=[BillRef(**b) for b in r["bills"]], roll_call=counts(r), blocs=blocs(r), source_url=VOTE_CARD.format(r["id"]))


def blocs(r: dict) -> Blocs | None:
    if r.get("contested") is None:
        return None
    return Blocs(coalition=BlocCounts(for_=r["coalition_for"], against=r["coalition_against"], abstain=r["coalition_abstain"]),
                 opposition=BlocCounts(for_=r["opposition_for"], against=r["opposition_against"], abstain=r["opposition_abstain"]),
                 contested=r["contested"])
