"""A new Knesset under the outgoing government (2026-11-10, 26th Knesset): its factions have no coalition yet, and its
MKs and factions are listed before its first vote."""

from __future__ import annotations

import psycopg
import pytest

from hkv.coalition import TRANSITION_EVIDENCE, derive
from tests.coalition.test_coalition import LIKUD, NETANYAHU, role
from tests.ingest.test_loader import SLICE, ingest

NEW_MK, NEW_FACTION = 990001, 990026


@pytest.fixture(scope="module")
def db(new_database):
    url = new_database()
    ingest(url, SLICE)
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("UPDATE knesset_term SET ended_on = '2026-11-10' WHERE number = 25")
        conn.execute("INSERT INTO knesset_term (number, name_he, started_on) VALUES (26, 'העשרים ושש', '2026-11-10') ON CONFLICT DO NOTHING")
        pid = conn.execute("""INSERT INTO person (knesset_person_id, first_name_he, last_name_he) VALUES (%s, 'חדשה', 'חברת כנסת')
                              RETURNING id""", (NEW_MK,)).fetchone()[0]
        fid = conn.execute("""INSERT INTO faction (knesset_faction_id, term_number, name_he, valid) VALUES (%s, 26, 'סיעה חדשה', '[2026-11-10,)')
                              RETURNING id""", (NEW_FACTION,)).fetchone()[0]
        conn.execute("INSERT INTO mandate (person_id, term_number, valid) VALUES (%s, 26, '[2026-11-10,)')", (pid,))
        conn.execute("INSERT INTO faction_membership (person_id, faction_id, valid) VALUES (%s, %s, '[2026-11-10,)')", (pid, fid))
        pm = conn.execute("SELECT id FROM person WHERE knesset_person_id = %s", (NETANYAHU,)).fetchone()[0]
        # a re-elected MK: the Likud membership ends with the 25th Knesset, the new list continues it
        conn.execute("""UPDATE faction_membership SET valid = daterange(lower(valid), '2026-11-10')
                        WHERE person_id = %s AND upper(valid) IS NULL""", (pm,))
        conn.execute("INSERT INTO faction_membership (person_id, faction_id, valid) VALUES (%s, %s, '[2026-11-10,)')", (pm, fid))
        # the new MK is a minister of the outgoing (37th) government, then of the 38th, which is sworn in on 2027-01-10
        for row_id, person, kid, gov, lo, hi in ((1, pm, NETANYAHU, 37, "2022-12-29", None), (2, pid, NEW_MK, 37, "2026-11-10", "2027-01-10"),
                                                 (3, pid, NEW_MK, 38, "2027-01-10", None)):
            conn.execute("""INSERT INTO gov_position (knesset_position_row_id, person_id, knesset_person_id, government_number, position_id, valid)
                            VALUES (%s, %s, %s, %s, 45, daterange(%s::date, %s::date))""", (row_id, person, kid, gov, lo, hi))
        derive(conn)
    return url


def test_new_knesset_has_no_coalition_under_the_outgoing_government(db):
    with psycopg.connect(db) as conn:
        assert role(conn, NEW_FACTION, "2026-12-01") == "unknown"     # a caretaker minister does not make it coalition
        assert conn.execute("""SELECT a.evidence FROM faction_alignment a JOIN faction f ON f.id = a.faction_id
                               WHERE f.knesset_faction_id = %s AND a.government_number = 37""", (NEW_FACTION,)).fetchone() == (TRANSITION_EVIDENCE,)
        assert role(conn, NEW_FACTION, "2027-02-01") == "coalition"   # its own government is sworn in
        assert conn.execute("SELECT term_number FROM government WHERE number = 38").fetchone() == (26,)
        assert role(conn, LIKUD, "2023-06-01") == "coalition"         # the outgoing Knesset is unchanged


def test_new_knesset_is_listed_before_its_first_vote(db):
    from fastapi.testclient import TestClient

    from hkv.api.app import create_app
    with TestClient(create_app(db)) as c:
        members = c.get("/api/v1/members", params={"term": 26}).json()["data"]
        assert [m["id"] for m in members] == [NEW_MK] and members[0]["roll_call_records"] == 0
        assert NEW_MK in [m["id"] for m in c.get("/api/v1/search", params={"q": "חברת כנסת"}).json()["data"]["members"]]
        factions = c.get("/api/v1/factions").json()
        assert factions["meta"]["filters"]["term"] == 26 and [f["id"] for f in factions["data"]] == [NEW_FACTION]
        assert factions["data"][0]["alignment_last"] == "unknown"
        # older terms still list only those with roll-call records
        old = c.get("/api/v1/factions", params={"term": 25}).json()["data"]
        assert old and all(f["roll_call_records"] > 0 for f in old)


def test_newterm_report_lists_what_is_left(db):
    from hkv.newterm import render, report
    with psycopg.connect(db) as conn:
        r = report(conn)
    assert (r.term, r.votes, r.mandates, r.published) == (26, 0, 1, True)
    [f] = r.factions
    assert (f.knesset_id, f.members, f.curated, f.parties) == (NEW_FACTION, 2, False, [])
    assert f.came_from == [("likud", 1)]                                  # where its re-elected MK sat before
    assert r.no_site_id == [(NEW_MK, "חדשה חברת כנסת")] and r.missing_names == {"en": 1, "ru": 1, "ar": 1}
    assert any(t.startswith("factions.toml") for t in r.todo) and any(t.startswith("parties.toml") for t in r.todo)
    out = render(r)
    assert f"[faction.{NEW_FACTION}]" in out and "likud (1 of 2 MKs were in it last time)" in out and f"[mk.{NEW_MK}]" in out


def test_newterm_report_before_the_source_publishes(new_database):
    from hkv.newterm import report
    url = new_database()
    with psycopg.connect(url) as conn:
        conn.execute("INSERT INTO knesset_term (number, name_he, started_on) VALUES (26, 'העשרים ושש', '2026-11-10')")
        r = report(conn)
    assert not r.published and r.todo[0].startswith("wait")
