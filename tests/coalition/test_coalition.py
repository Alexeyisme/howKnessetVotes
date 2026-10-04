"""Governments and coalition roles derived from government posts (hkv.coalition), over the recorded slice."""

from __future__ import annotations

import datetime as dt

import psycopg
import pytest

from hkv.coalition import _merge, _norwegian, _subtract, apply_overrides, derive
from hkv.names import sync_parties
from tests.ingest.test_loader import SLICE, ingest

D = dt.date
NETANYAHU = 965
LIKUD, YESH_ATID = 1096, 1102


def test_span_helpers():
    assert _merge([(D(2020, 1, 1), D(2020, 2, 1)), (D(2020, 2, 20), D(2020, 3, 1))], gap=30) == [(D(2020, 1, 1), D(2020, 3, 1))]
    assert _merge([(D(2020, 1, 1), D(2020, 2, 1)), (D(2020, 4, 1), D(2020, 5, 1))], gap=30) == [(D(2020, 1, 1), D(2020, 2, 1)), (D(2020, 4, 1), D(2020, 5, 1))]
    assert _subtract([(D(2020, 1, 1), D(2020, 12, 31))], [(D(2020, 3, 1), D(2020, 4, 1))]) == [(D(2020, 1, 1), D(2020, 3, 1)), (D(2020, 4, 1), D(2020, 12, 31))]
    # a minister who leaves the Knesset mid-post (Norwegian law, 2015+) keeps counting for the faction ...
    post = (D(2021, 6, 13), D(2022, 11, 15))
    assert _norwegian((D(2021, 4, 6), D(2021, 6, 15)), post, [D(2021, 4, 6)]) == (D(2021, 4, 6), D(2022, 11, 15))
    # ... unless they join another faction, and not before the law existed
    assert _norwegian((D(2021, 4, 6), D(2021, 6, 15)), post, [D(2021, 4, 6), D(2021, 7, 1)]) == (D(2021, 4, 6), D(2021, 6, 15))
    assert _norwegian((D(2003, 2, 17), D(2005, 12, 10)), (D(2004, 9, 6), D(2006, 4, 17)), []) == (D(2003, 2, 17), D(2005, 12, 10))


@pytest.fixture(scope="module")
def db(new_database):
    url = new_database()
    ingest(url, SLICE)
    with psycopg.connect(url, autocommit=True) as conn:
        pid = conn.execute("SELECT id FROM person WHERE knesset_person_id = %s", (NETANYAHU,)).fetchone()[0]
        for row_id, gov, lo, hi in ((1, 36, "2021-06-13", "2022-12-29"), (2, 37, "2022-12-29", None)):
            person = pid if gov == 37 else None   # government 36: a PM who is not in the slice
            conn.execute("""INSERT INTO gov_position (knesset_position_row_id, person_id, knesset_person_id, government_number, position_id, valid)
                            VALUES (%s, %s, %s, %s, 45, daterange(%s::date, %s::date))""", (row_id, person, NETANYAHU if person else 1, gov, lo, hi))
        derive(conn)
        sync_parties(conn)
    return url


def role(conn, faction: int, on: str) -> str | None:
    r = conn.execute("""SELECT a.role FROM faction_alignment a JOIN faction f ON f.id = a.faction_id
                        WHERE f.knesset_faction_id = %s AND a.valid @> %s::date""", (faction, on)).fetchone()
    return r and r[0]


def test_governments_and_roles(db):
    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT number, lower(valid), upper(valid) FROM government ORDER BY 1").fetchall() == [
            (36, D(2021, 6, 13), D(2022, 12, 29)), (37, D(2022, 12, 29), None)]
        assert role(conn, LIKUD, "2023-06-01") == "coalition"        # the PM's faction
        assert role(conn, YESH_ATID, "2023-06-01") == "opposition"


def test_overrides_replace_derived_roles(db, tmp_path):
    f = tmp_path / "o.toml"
    f.write_text('[[override]]\nfaction = 1102\nfrom = "2023-10-12"\nto = "2024-06-13"\nrole = "coalition"\nevidence = "test"\n')
    with psycopg.connect(db) as conn:
        assert apply_overrides(conn, f)["overrides"] == 1
        assert [role(conn, YESH_ATID, d) for d in ("2023-10-11", "2023-10-12", "2024-06-12", "2024-06-13")] == [
            "opposition", "coalition", "coalition", "opposition"]
        conn.rollback()


def test_parties_link_factions_across_knessets(db):
    with psycopg.connect(db) as conn:
        likud = conn.execute("""SELECT count(*) FROM party_faction pf JOIN faction f ON f.id = pf.faction_id
                                WHERE pf.party_slug = 'likud'""").fetchone()[0]
        assert likud >= 1 and conn.execute("SELECT name_ru FROM party WHERE slug = 'likud'").fetchone() == ("Ликуд",)


def test_api_governments_parties_and_contested_votes(db):
    from fastapi.testclient import TestClient

    from hkv.api.app import create_app
    with TestClient(create_app(db)) as c:
        govs = c.get("/api/v1/governments").json()["data"]
        assert [g["number"] for g in govs] == [37, 36] and govs[0]["prime_minister"]["id"] == NETANYAHU
        likud = c.get("/api/v1/parties/likud", params={"lang": "en"}).json()["data"]
        assert likud["name_en"] == "Likud" and likud["factions"][-1]["alignment_last"] == "coalition"
        assert c.get("/api/v1/parties/nope").status_code == 404
        f = c.get(f"/api/v1/factions/{LIKUD}").json()["data"]
        assert f["parties"][0]["slug"] == "likud" and any(a["role"] == "coalition" for a in f["alignment"])
        votes = c.get("/api/v1/votes", params={"limit": 100}).json()["data"]
        assert all(v["blocs"] is not None for v in votes if v["roll_call"]["total_records"] and v["occurred_on"] >= "2022-12-29")
        contested = c.get("/api/v1/votes", params={"contested": "true", "min_cast": 3}).json()
        assert contested["meta"]["filters"]["contested"] is True
        assert all(v["blocs"]["contested"] and v["roll_call"]["for"] + v["roll_call"]["against"] + v["roll_call"]["abstain"] >= 3
                   for v in contested["data"])
        some = next(v for v in votes if v["blocs"])
        detail = c.get(f"/api/v1/votes/{some['id']}").json()["data"]
        assert {r["alignment"] for r in detail["by_faction"]} <= {"coalition", "opposition", None}
