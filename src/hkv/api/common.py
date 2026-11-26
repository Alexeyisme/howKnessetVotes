"""Shared API models, DB dependency and vote query pieces."""

from __future__ import annotations

import datetime as dt
import re
from typing import Annotated, ClassVar, Literal

from fastapi import Depends, Request
from psycopg import Connection
from pydantic import BaseModel, ConfigDict, Field

from hkv.api.names import (BallotFactionNames, ExplanationTranslations, FactionNames, PersonNames, ProseText, SummaryTranslations,
                           TitleTranslations)

DEFAULT_DB = "postgresql://knesset:knesset@localhost:5433/knesset"
VOTE_CARD = "https://main.knesset.gov.il/Activity/plenum/Votes/Pages/vote.aspx?voteId={}"

# Lists, search and party pages show MKs and factions with roll-call records. The newest Knesset's MKs and factions
# are listed before their first vote too, so a new Knesset is visible from the day it is sworn in (26th: 2026-11-10).
# SQL conditions on `p` (person) and `f` (faction).
LISTED_PERSON = """(EXISTS (SELECT 1 FROM ballot b WHERE b.person_id = p.id)
    OR EXISTS (SELECT 1 FROM mandate m WHERE m.person_id = p.id AND m.term_number = (SELECT max(number) FROM knesset_term)))"""
LISTED_FACTION = """(EXISTS (SELECT 1 FROM ballot b WHERE b.faction_id = f.id)
    OR (f.term_number = (SELECT max(number) FROM knesset_term) AND EXISTS (SELECT 1 FROM faction_membership fm WHERE fm.faction_id = f.id)))"""

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


class SideArgument(ProseText):
    speakers: int  # how many speakers made this point


class DebateSides(BaseModel):
    """The plenum fight over a bill in brief, for cards (L7): each side's argument made by the most speakers, how many
    members spoke and how many reservations were filed. The arguments come in pairs or not at all: a debate summary
    sometimes has arguments for one side only, and a card must not show one side alone."""
    argument_for: SideArgument | None
    argument_against: SideArgument | None
    speakers: int | None      # members who spoke in the debate; None when there is no debate summary
    reservations: int | None  # reservations filed to the second reading; None when they were not extracted


class BillAbout(SummaryTranslations, ExplanationTranslations):
    """What a bill does, for cards: the official summary, or where there is none our description from the sponsors'
    explanatory notes (as on the bill page, which labels it as their account). Exactly one of the two is set."""
    summary_he: str | None = None
    explanation_he: str | None = None


class BillRef(TitleTranslations):
    id: int
    title_he: str
    topics: list[str] = []            # topic slugs (rule-based or official), e.g. to spread a selection over topics
    sides: DebateSides | None = None  # final votes only (attach_sides)
    about: BillAbout | None = None    # final votes only (attach_sides)


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


class FactionSides(BaseModel):
    """How many factions' majorities voted for and against (a strict majority of the faction's members who voted).
    Needs no government, unlike Blocs: it shows which votes were fought over while a new government is formed."""
    model_config = ConfigDict(populate_by_name=True)
    for_: int = Field(alias="for")
    against: int
    opposed: bool  # factions on both sides
    voted: int | None = None   # factions with at least one for/against/abstain record
    total: int | None = None   # factions of that Knesset with a member on the vote date; voted < total = whole factions did not vote


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
    faction_sides: FactionSides | None = None
    source_url: str


class FactionBreakdown(FactionNames):
    _faction_key: ClassVar[str] = "faction_id"
    faction_id: int
    name_he: str
    counts: Counts
    majority: Literal["for", "against", "abstain", "mixed", "none"]
    ambiguous_records: int
    alignment: Literal["coalition", "opposition", "external_support", "unknown"] | None = None  # on the vote date


class FactionWithoutRecords(FactionNames):
    """A faction of the vote's Knesset that had members on the vote date and has no record in this vote: not for,
    not against, not present. No record is not a choice, so it is listed apart from by_faction."""
    _faction_key: ClassVar[str] = "faction_id"
    faction_id: int
    name_he: str
    members: int  # its members on the vote date


class VoteDetail(VoteSummary):
    official_totals: OfficialTotals | None
    totals_match: bool | None  # official totals vs roll-call records counted by the source
    excluded_from_official_total: int  # records the legacy source marks as not in the official totals
    by_faction: list[FactionBreakdown]
    factions_without_records: list[FactionWithoutRecords] = []  # empty when the vote has no roll call at all
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
           coalesce((SELECT json_agg(json_build_object('id', b.knesset_bill_id, 'title_he', b.title_he, 'topics', array(
                         SELECT t.slug FROM bill_topic bt JOIN topic t ON t.id = bt.topic_id
                         WHERE bt.bill_id = b.id AND bt.review_state <> 'rejected' ORDER BY t.sort)) ORDER BY b.knesset_bill_id)
                     FROM vote_subject s JOIN bill b ON b.id = s.bill_id WHERE s.vote_id = v.id), '[]') AS bills,
           c.*, vb.coalition_for, vb.coalition_against, vb.coalition_abstain, vb.opposition_for, vb.opposition_against,
           vb.opposition_abstain, vb.contested, vf.factions_for, vf.factions_against, vf.opposed, vf.factions_voted, vf.factions_total
    FROM vote v
    LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
    LEFT JOIN vote_bloc vb ON vb.vote_id = v.id
    LEFT JOIN vote_factions vf ON vf.vote_id = v.id
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
                       bills=[BillRef(**b) for b in r["bills"]], roll_call=counts(r), blocs=blocs(r),
                       faction_sides=None if r.get("opposed") is None else FactionSides(for_=r["factions_for"], against=r["factions_against"], opposed=r["opposed"],
                                                                                             voted=r.get("factions_voted"), total=r.get("factions_total")),
                       source_url=VOTE_CARD.format(r["id"]))


def blocs(r: dict) -> Blocs | None:
    if r.get("contested") is None:
        return None
    return Blocs(coalition=BlocCounts(for_=r["coalition_for"], against=r["coalition_against"], abstain=r["coalition_abstain"]),
                 opposition=BlocCounts(for_=r["opposition_for"], against=r["opposition_against"], abstain=r["opposition_abstain"]),
                 contested=r["contested"])


def debate_sides(conn, bill_ids: list[int]) -> dict[int, DebateSides]:
    """DebateSides by Knesset bill id, for the bills that have a debate summary or reservations."""
    out = {}
    for r in conn.execute(
        """SELECT b.knesset_bill_id AS id, d.arguments, r.total AS reservations,
                  (SELECT count(DISTINCT s.person_id) FROM bill_debate_speaker s WHERE s.bill_id = d.bill_id) AS speakers
           FROM bill b LEFT JOIN bill_debate d ON d.bill_id = b.id LEFT JOIN bill_reservations r ON r.bill_id = b.id
           WHERE b.knesset_bill_id = ANY(%s) AND (d.bill_id IS NOT NULL OR r.bill_id IS NOT NULL)""", (bill_ids,)):
        top: dict[str, dict] = {}
        for a in r["arguments"] or []:  # ties keep the model's order
            if a["side"] not in top or len(a["speakers"]) > len(top[a["side"]]["speakers"]):
                top[a["side"]] = a
        args = {side: SideArgument(text_he=a["text_he"], speakers=len(a["speakers"])) for side, a in top.items()} if len(top) == 2 else {}
        out[r["id"]] = DebateSides(argument_for=args.get("for"), argument_against=args.get("against"),
                                   speakers=r["speakers"] if r["arguments"] is not None else None, reservations=r["reservations"])
    return out


def bill_about(conn, bill_ids: list[int]) -> dict[int, BillAbout]:
    """BillAbout by Knesset bill id, for the bills that have an official summary or a description of their notes."""
    return {r["id"]: BillAbout(summary_he=r["summary_he"], explanation_he=r["explanation_he"]) for r in conn.execute(
        """SELECT b.knesset_bill_id AS id, b.summary_he, CASE WHEN b.summary_he IS NULL THEN e.summary_he END AS explanation_he
           FROM bill b LEFT JOIN bill_explanation e ON e.bill_id = b.id
           WHERE b.knesset_bill_id = ANY(%s) AND (b.summary_he IS NOT NULL OR e.summary_he IS NOT NULL)""", (bill_ids,))}


def attach_about(conn, votes: list[VoteSummary]) -> None:
    """Put BillAbout on the bills of these votes, whatever their stage (a comparison lists every reading of a bill)."""
    found = bill_about(conn, list({b.id for v in votes for b in v.bills})) if votes else {}
    for v in votes:
        for b in v.bills:
            b.about = found.get(b.id)


def attach_sides(conn, votes: list[VoteSummary]) -> None:
    """Put the bill's DebateSides and BillAbout on the bills of final votes only: on every reservation vote they would
    repeat themselves."""
    finals = [v for v in votes if v.motion_type == "adopt_bill" and v.stage == "third"]
    found = debate_sides(conn, list({b.id for v in finals for b in v.bills})) if finals else {}
    for v in finals:
        for b in v.bills:
            b.sides = found.get(b.id)
    attach_about(conn, finals)


# -- search helpers ----------------------------------------------------------------------------------

_HEBREW = re.compile(r"[֐-׿]")
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_ARABIC = re.compile(r"[\u0600-\u06FF]")


def detect_script(q: str) -> str:
    if q.strip().isdigit():
        return "number"
    if _HEBREW.search(q):
        return "hebrew"
    if _CYRILLIC.search(q):
        return "cyrillic"
    if _ARABIC.search(q):
        return "arabic"
    if re.search(r"[a-zA-Z]", q):
        return "latin"
    return "other"


FTS_CONFIG = {"ru": "russian", "en": "english", "ar": "arabic"}   # must match the indexes of migration 0019
SCRIPT_LANG = {"cyrillic": "ru", "latin": "en", "arabic": "ar"}


def translated_title_match(conn: Connection, q: str) -> tuple[str, dict] | None:
    """SQL condition on `bill b` and its parameters: the bill's title translated into the query's language
    (text_translation, R4) has every word of the query. None for a Hebrew query, a number, or no words at all.

    A title has a word if it has the same stem, or a word that starts with the query's word as typed. Stems alone
    miss forms the stemmer splits ("призыв" is stemmed to "приз", "призыве" to "призыв"). Only when no voted bill
    matches that way does a stem also match as the start of a longer one, so "налоги" still finds a lone
    "налоговый"; doing that always found "признание" for "призыв" and "банкротство" for "банки". The stem-start
    condition stays in both cases: it is the one the index of migration 0019 answers."""
    lang = SCRIPT_LANG.get(detect_script(q))
    words = re.findall(r"[^\W_]+", q)
    if not lang or not words:
        return None
    cfg = f"'{FTS_CONFIG[lang]}'::regconfig"
    params = {"lang": lang, "tsq": " & ".join(f"{w}:*" for w in words), "words": words} | {f"w{i}": w for i, w in enumerate(words)}
    loose = f"""x.language = %(lang)s AND to_tsvector({cfg}, x.text) @@ to_tsquery({cfg}, %(tsq)s)
                AND x.source_sha256 = title_sha(b.title_he)"""
    strict = loose + "".join(
        f" AND (to_tsvector({cfg}, x.text) @@ plainto_tsquery({cfg}, %(w{i})s) OR x.text ~* ('\\m' || %(w{i})s))" for i in range(len(words)))
    found = conn.execute(f"""SELECT EXISTS (SELECT 1 FROM bill b WHERE EXISTS (SELECT 1 FROM text_translation x WHERE {strict})
                                            AND EXISTS (SELECT 1 FROM vote_subject vs WHERE vs.bill_id = b.id)) AS found""", params).fetchone()
    found = found["found"] if isinstance(found, dict) else found[0]
    return f"EXISTS (SELECT 1 FROM text_translation x WHERE {strict if found else loose})", params


# How many of the query's words the translated title of row `q` has as written (not only as a stem): the order of
# search results, so that "reasonableness" lists titles with that word before those with "reasonable".
TITLE_WORD_HITS = """(SELECT count(*) FROM unnest(%(words)s::text[]) w WHERE EXISTS (
                         SELECT 1 FROM text_translation x WHERE x.language = %(lang)s AND x.source_sha256 = title_sha(q.title_he)
                           AND x.text ILIKE '%%' || w || '%%'))"""
