"""Loader against a recorded slice of real Knesset data (tests/fixtures/slice_votes.json).

The slice: vote 37689 (2022-12-13, date only, 114 ballots, right after the Religious Zionism split)
and votes 46699/46700 (2026-07-28, third and second reading of one bill, 5 ballots each).
"""

from __future__ import annotations

import copy
import datetime as dt
import json
from pathlib import Path
from typing import Iterator

import psycopg
import pytest

from hkv.ingest import mapping as m
from hkv.ingest.loader import Loader
from hkv.sources.odata import Page

SLICE = json.loads((Path(__file__).parents[1] / "fixtures" / "slice_votes.json").read_text(encoding="utf-8"))
PERIOD = (dt.date(2022, 1, 1), dt.date(2026, 12, 31))
BEN_GVIR = 30811  # Religious Zionism -> Otzma Yehudit on 2022-11-20


class FixtureSource:
    """Serves every recorded row of a resource regardless of filters; the loader must filter itself."""

    def __init__(self, data: dict[str, list[dict]]) -> None:
        self.data = data

    def pages(self, resource: str, params: dict[str, str]) -> Iterator[Page]:
        rows = self.data.get(resource, [])
        yield Page("knesset_odata_v4", resource, f"fixture:{resource}", json.dumps(rows).encode(), rows)


def ingest(url: str, data: dict) -> Loader:
    with psycopg.connect(url) as conn:
        loader = Loader(conn, FixtureSource(data))
        loader.load_reference()
        ids = loader.load_votes(*PERIOD)
        loader.resolve_affiliations(ids)
    return loader


def one(url: str, sql: str, *params):
    with psycopg.connect(url) as conn:
        return conn.execute(sql, params).fetchone()


def table_counts(url: str) -> dict[str, int]:
    tables = ["person", "mandate", "faction", "faction_membership", "plenum_session", "bill", "vote", "vote_subject", "ballot", "row_revision"]
    with psycopg.connect(url) as conn:
        return {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}


@pytest.fixture
def loaded(new_database):
    url = new_database()
    ingest(url, SLICE)
    return url


def test_votes_and_ballots_loaded(loaded):
    counts = table_counts(loaded)
    assert counts["vote"] == 3
    assert counts["ballot"] == len(SLICE["KNS_PlenumVoteResult"]) == 124
    assert counts["vote_subject"] == 3
    assert counts["row_revision"] == 0


def test_date_only_vote_has_no_time(loaded):
    assert one(loaded, "SELECT occurred_at, occurred_on FROM vote WHERE knesset_vote_id = 37689") == (None, dt.date(2022, 12, 13))
    at, on = one(loaded, "SELECT occurred_at, occurred_on FROM vote WHERE knesset_vote_id = 46699")
    assert at is not None and on == dt.date(2026, 7, 28)


def test_vote_question_is_classified(loaded):
    rows = dict(psycopg.connect(loaded).execute(
        """SELECT v.knesset_vote_id, k.motion_type || '/' || k.stage FROM vote v JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id"""
    ).fetchall())
    assert rows == {46699: "adopt_bill/third", 46700: "adopt_section/second", 37689: "adopt_bill/preliminary"}


def test_every_ballot_gets_faction_and_mandate_at_vote_date(loaded):
    assert one(loaded, "SELECT count(*) FILTER (WHERE faction_id IS NULL), count(*) FILTER (WHERE mandate_id IS NULL) FROM ballot") == (0, 0)
    # after the split, the historical faction is the new one, not 'הציונות הדתית'
    name, ambiguous = one(loaded, """SELECT f.name_he, b.faction_ambiguous FROM ballot b JOIN faction f ON f.id = b.faction_id
                                     JOIN person p ON p.id = b.person_id JOIN vote v ON v.id = b.vote_id
                                     WHERE p.knesset_person_id = %s AND v.knesset_vote_id = 37689""", BEN_GVIR)
    assert "עוצמה יהודית" in name and not ambiguous


def test_reimport_is_idempotent(loaded):
    before = table_counts(loaded)
    ingest(loaded, SLICE)
    assert table_counts(loaded) == before
    assert one(loaded, "SELECT count(*) FROM ingestion_run WHERE status <> 'succeeded'") == (0,)


def test_source_correction_keeps_previous_version(loaded):
    data = copy.deepcopy(SLICE)
    row = next(r for r in data["KNS_PlenumVoteResult"] if r["ResultCode"] == 7)
    row.update(ResultCode=8, ResultDesc="נגד")
    ingest(loaded, data)
    assert one(loaded, "SELECT choice FROM ballot WHERE knesset_ballot_id = %s", row["Id"]) == ("against",)
    old = one(loaded, "SELECT old_row->>'choice' FROM row_revision r JOIN ballot b ON b.id = r.row_id WHERE b.knesset_ballot_id = %s", row["Id"])
    assert old == ("for",)


def test_vote_on_faction_switch_day_is_flagged_ambiguous(new_database):
    """Source gives only the day of the switch, so a vote that day cannot be attributed with certainty."""
    data = copy.deepcopy(SLICE)
    memberships = sorted((r for r in data["KNS_PersonToPosition"] if r["PersonID"] == BEN_GVIR and r["PositionID"] == 54 and r["KnessetNum"] == 25),
                         key=lambda r: r["StartDate"])
    first, second = memberships[0], memberships[1]
    first["FinishDate"] = second["StartDate"] = "2022-12-13T00:00:00+02:00"
    url = new_database()
    ingest(url, data)
    name, ambiguous = one(url, """SELECT f.name_he, b.faction_ambiguous FROM ballot b JOIN faction f ON f.id = b.faction_id
                                  JOIN person p ON p.id = b.person_id JOIN vote v ON v.id = b.vote_id
                                  WHERE p.knesset_person_id = %s AND v.knesset_vote_id = 37689""", BEN_GVIR)
    assert "עוצמה יהודית" in name and ambiguous


def test_zero_length_positions_become_issues(loaded):
    zero = [r for r in SLICE["KNS_PersonToPosition"] if r["FinishDate"] and r["FinishDate"][:10] <= r["StartDate"][:10]]
    got = one(loaded, "SELECT count(*) FROM data_issue WHERE issue_type = 'zero_length_position'")[0]
    assert got == len(zero)


@pytest.mark.parametrize(("code", "expected"), [(7, ("for", "cast")), (6, (None, "present_not_voting")), (99, (None, "unknown"))])
def test_ballot_codes(code, expected):
    assert m.ballot_values(code) == expected


def test_unknown_option_is_unknown():
    assert m.option_kind(12345) == ("unknown", "unknown") and m.option_kind(None) == ("unknown", "unknown")


def test_positions_with_placeholder_data_become_issues(new_database):
    data = copy.deepcopy(SLICE)
    template = next(r for r in data["KNS_PersonToPosition"] if r["PositionID"] == 43)
    data["KNS_PersonToPosition"] += [
        dict(template, Id=900001, KnessetNum=None, StartDate="1900-01-01T00:00:00+02:00", FinishDate="2006-04-17T00:00:00+03:00"),
        dict(template, Id=900002, KnessetNum=99),  # term that does not exist -> FK violation
    ]
    url = new_database()
    ingest(url, data)
    issues = psycopg.connect(url).execute(
        "SELECT external_ref, issue_type FROM data_issue WHERE external_ref LIKE 'KNS_PersonToPosition:9000%' ORDER BY 1").fetchall()
    assert issues == [("KNS_PersonToPosition:900001", "position_unresolvable"), ("KNS_PersonToPosition:900002", "position_rejected")]
    assert table_counts(url)["ballot"] == 124


def test_resume_skips_votes_with_ballots(loaded):
    """A resumed load must not refetch ballots of votes already loaded (batches are atomic)."""
    fetched: list[str] = []

    class Spy(FixtureSource):
        def pages(self, resource, params):
            fetched.append(resource)
            yield from super().pages(resource, params)

    with psycopg.connect(loaded) as conn:
        Loader(conn, Spy(SLICE)).load_votes(*PERIOD, resume=True)
    assert "KNS_PlenumVoteResult" not in fetched
    assert table_counts(loaded)["ballot"] == 124


def test_periods_cover_range_without_gaps():
    from hkv.ingest.backfill import periods
    ps = periods(dt.date(2016, 9, 27), dt.date(2017, 3, 5), 3)
    assert ps == [(dt.date(2016, 9, 27), dt.date(2016, 11, 30)), (dt.date(2016, 12, 1), dt.date(2017, 2, 28)), (dt.date(2017, 3, 1), dt.date(2017, 3, 5))]
    assert all(b + dt.timedelta(days=1) == c for (_, b), (c, _) in zip(ps, ps[1:])) and ps[-1][1] == dt.date(2017, 3, 5)


def test_batches_are_committed_before_connection_closes(new_database):
    """Regression: batches must be durable as they finish (a killed backfill worker keeps its work)."""
    url = new_database()
    with psycopg.connect(url) as conn:
        loader = Loader(conn, FixtureSource(SLICE))
        loader.load_reference()
        loader.load_votes(*PERIOD)
        # still inside the first connection: another session must already see the rows
        assert table_counts(url)["ballot"] == 124


def test_update_rereads_window_and_records_release(new_database):
    from hkv.ingest.update import update
    url = new_database()
    ingest(url, SLICE)
    data = copy.deepcopy(SLICE)
    row = next(r for r in data["KNS_PlenumVoteResult"] if r["VoteID"] == 46699)
    row.update(ResultCode=8, ResultDesc="נגד")  # a correction published by the source after the first load
    with psycopg.connect(url) as conn:
        result = update(conn, FixtureSource(data), days=5, today=dt.date(2026, 7, 30))
    assert result["votes"] == 2  # 37689 (2022) is outside the window
    assert one(url, "SELECT choice FROM ballot WHERE knesset_ballot_id = %s", row["Id"]) == ("against",)
    assert one(url, "SELECT count(*) FROM row_revision") == (1,)
    assert one(url, "SELECT coverage->>'votes', coverage->>'last_vote_on' FROM data_release") == ("3", "2026-07-28")
    # quick run with nothing new: stops after the votes, no release; a new correction makes it run the follow-up
    with psycopg.connect(url) as conn:
        assert update(conn, FixtureSource(data), days=5, today=dt.date(2026, 7, 30), quick=True) == {"votes": 2, "changed": False}
        assert one(url, "SELECT count(*) FROM data_release") == (1,)
        row.update(ResultCode=7, ResultDesc="בעד")
        assert update(conn, FixtureSource(data), days=5, today=dt.date(2026, 7, 30), quick=True)["changed"] is True
    assert one(url, "SELECT count(*) FROM data_release") == (2,)
