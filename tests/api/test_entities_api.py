"""Members, factions, bills endpoints over the recorded slice, with one synthetic dissent added:
a Likud MK votes against in vote 37689, where the other 31 Likud members voted for."""

from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from hkv.api.app import create_app
from tests.ingest.test_loader import BEN_GVIR, SLICE, ingest

LIKUD = 1096
LIKUD_IN_37689 = sorted(
    r["MkId"] for r in SLICE["KNS_PlenumVoteResult"] if r["VoteID"] == 37689 and any(
        p["PersonID"] == r["MkId"] and p["PositionID"] == 54 and p["FactionID"] == LIKUD for p in SLICE["KNS_PersonToPosition"]))
DISSENTER = LIKUD_IN_37689[0]


@pytest.fixture(scope="module")
def client(new_database):
    data = copy.deepcopy(SLICE)
    for r in data["KNS_PlenumVoteResult"]:
        if r["VoteID"] == 37689 and r["MkId"] == DISSENTER:
            r.update(ResultCode=8, ResultDesc="נגד")
    url = new_database()
    ingest(url, data)
    with TestClient(create_app(url)) as c:
        yield c


def test_member_deviation_and_participation(client):
    m = client.get(f"/api/v1/members/{DISSENTER}").json()["data"]
    dev = m["stats"]["deviation_from_faction"]
    assert dev["numerator"] == 1 and dev["denominator"] >= 1  # compared with 31 Likud colleagues voting for
    p = m["stats"]["participation"]
    assert p["numerator"] == m["roll_call_records"] - m["stats"]["choices"].get("present_not_voting", 0) - m["stats"]["choices"].get("other", 0)
    assert p["denominator"] >= p["numerator"]
    rows = client.get(f"/api/v1/members/{DISSENTER}/votes", params={"deviated": True}).json()["data"]
    assert [(r["vote"]["id"], r["choice"], r["faction_majority"], r["deviates"]) for r in rows] == [(37689, "against", "for", True)]


def test_member_faction_history_after_split(client):
    m = client.get(f"/api/v1/members/{BEN_GVIR}").json()["data"]
    names = [f["faction"]["name_he"] for f in m["factions"] if f["faction"]["term"] == 25]
    assert names[0] == "הציונות הדתית" and "עוצמה יהודית" in names[-1]


def test_faction_cohesion_counts_the_dissent(client):
    f = client.get(f"/api/v1/factions/{LIKUD}").json()["data"]
    c = f["stats"]["cohesion"]
    assert c["denominator"] - c["numerator"] == 1
    assert f["stats"]["unanimous_votes"]["denominator"] - f["stats"]["unanimous_votes"]["numerator"] == 1
    split = client.get(f"/api/v1/factions/{LIKUD}/votes", params={"split_only": True}).json()["data"]
    assert [(v["vote"]["id"], v["faction_counts"]["for"], v["faction_counts"]["against"], v["majority"]) for v in split] == [
        (37689, len(LIKUD_IN_37689) - 1, 1, "for")]
    votes = lambda **p: [v["vote"]["id"] for v in client.get(f"/api/v1/factions/{LIKUD}/votes", params=p).json()["data"]]  # noqa: E731
    assert 37689 in votes(min_cast=0) and votes(min_cast=120) == []
    assert votes(contested=True) == []          # no coalition data in the fixture, so nothing is contested


def test_compare_members_and_factions(client):
    other = LIKUD_IN_37689[1]
    c = client.get("/api/v1/compare/members", params={"a": DISSENTER, "b": other}).json()["data"]
    assert c["agreement"]["denominator"] >= 1 and c["agreement"]["denominator"] - c["agreement"]["numerator"] == 1
    assert [(d["vote"]["id"], d["a"]["choice"], d["b"]["choice"]) for d in c["differences"]] == [(37689, "against", "for")]
    same = client.get("/api/v1/compare/members", params={"a": other, "b": other}).json()["data"]
    assert same["agreement"]["numerator"] == same["agreement"]["denominator"] and same["differences"] == []
    f = client.get("/api/v1/compare/factions", params={"a": LIKUD, "b": LIKUD}).json()["data"]
    assert f["differences"] == [] and f["agreement"]["denominator"] >= 1
    assert client.get("/api/v1/compare/members", params={"a": 1, "b": other}).status_code == 404


def test_member_votes_topic_filter_and_coalition_stat(client):
    m = client.get(f"/api/v1/members/{DISSENTER}").json()["data"]
    assert set(m["stats"]["with_coalition"]) == {"numerator", "denominator", "value"}   # no coalition derivation in the slice: 0 of 0
    assert client.get(f"/api/v1/members/{DISSENTER}/votes", params={"topic": "no-such-topic"}).json()["data"] == []


def test_bills(client):
    listed = client.get("/api/v1/bills").json()["data"]
    assert {b["id"] for b in listed} == {2196976, 2229019}
    b = client.get("/api/v1/bills/2229019").json()["data"]
    assert b["passed_third_reading"] and [v["id"] for v in b["timeline"]] == [46700, 46699]  # second reading, then third
    b2 = client.get("/api/v1/bills/2196976").json()["data"]
    # the initiator is stored only if the person is known; otherwise it becomes a data_issue
    known = any(p["Id"] == 30660 for p in SLICE["KNS_Person"])
    assert [(i["person_id"], i["role"]) for i in b2["initiators"]] == ([(30660, "initiator")] if known else [])
    assert client.get("/api/v1/bills/1").status_code == 404
    assert client.get("/api/v1/members/1").status_code == 404


def test_debate_sides_on_cards(client):
    """L7 cards: the bill's most-made argument per side, only when both sides have one; on final votes only."""
    from psycopg.types.json import Jsonb
    with client.app.state.pool.connection() as conn:
        bill = conn.execute("SELECT id FROM bill WHERE knesset_bill_id = 2229019").fetchone()["id"]
        vote = conn.execute("SELECT id FROM vote WHERE knesset_vote_id = 46699").fetchone()["id"]
        speaker = conn.execute(
            """SELECT p.id, p.knesset_person_id FROM ballot b JOIN person p ON p.id = b.person_id WHERE b.vote_id = %s
               ORDER BY p.knesset_person_id LIMIT 1""", (vote,)).fetchone()
        conn.execute("""INSERT INTO bill_debate (bill_id, vote_id, document_ids, file_sha256, segment_titles, chars, truncated, summary_he, arguments)
                        VALUES (%s, %s, '{}', '{}', '{}', 0, false, 'סיכום', %s)""",
                     (bill, vote, Jsonb([{"side": "for", "text_he": "בעד", "speakers": [0]}])))
        conn.execute("""INSERT INTO bill_debate_speaker (bill_id, ordinal, label_he, name_he, person_id, speeches, chars, stages)
                        VALUES (%s, 0, 'דובר', 'דובר', %s, 2, 100, '{third}')""", (bill, speaker["id"]))
    try:
        listed = {b["id"]: b for b in client.get("/api/v1/bills").json()["data"]}
        sides = listed[2229019]["sides"]
        assert sides == {"argument_for": None, "argument_against": None, "speakers": 1, "reservations": None}  # one side only
        assert listed[2196976]["sides"] is None

        with client.app.state.pool.connection() as conn:
            conn.execute("UPDATE bill_debate SET arguments = %s WHERE bill_id = %s", (Jsonb([
                {"side": "for", "text_he": "בעד א", "speakers": [0]}, {"side": "against", "text_he": "נגד", "speakers": [0]},
                {"side": "for", "text_he": "בעד ב", "speakers": [0, 1]}]), bill))
        votes = {v["id"]: v for v in client.get("/api/v1/votes").json()["data"]}
        sides = votes[46699]["bills"][0]["sides"]
        assert (sides["argument_for"]["text_he"], sides["argument_for"]["speakers"]) == ("בעד ב", 2)  # the most speakers
        assert sides["argument_against"]["text_he"] == "נגד"
        assert votes[46700]["bills"][0]["sides"] is None  # second reading: not a final vote
        assert client.get("/api/v1/votes/46699").json()["data"]["bills"][0]["sides"] == sides

        mine = {m["vote"]["id"]: m for m in client.get(f"/api/v1/members/{speaker['knesset_person_id']}/votes").json()["data"]}
        assert mine[46699]["speeches"] == 2 and mine[46699]["vote"]["bills"][0]["sides"] == sides
        assert mine.get(46700, {}).get("speeches") is None
    finally:
        with client.app.state.pool.connection() as conn:
            conn.execute("DELETE FROM bill_debate WHERE bill_id = %s", (bill,))
