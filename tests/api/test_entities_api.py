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


def test_bill_about_on_final_vote_cards(client):
    """Cards on final votes carry what the law does (the official summary); other stages do not repeat it."""
    with client.app.state.pool.connection() as conn:
        old = conn.execute("SELECT summary_he FROM bill WHERE knesset_bill_id = 2229019").fetchone()["summary_he"]
        conn.execute("UPDATE bill SET summary_he = 'תקציר' WHERE knesset_bill_id = 2229019")
    try:
        votes = {v["id"]: v for v in client.get("/api/v1/votes", params={"lang": "ru"}).json()["data"]}
        about = votes[46699]["bills"][0]["about"]
        assert about["summary_he"] == "תקציר" and about["explanation_he"] is None
        assert votes[46700]["bills"][0]["about"] is None  # second reading: not a final vote
        assert client.get("/api/v1/votes/46699").json()["data"]["bills"][0]["about"]["summary_he"] == "תקציר"
    finally:
        with client.app.state.pool.connection() as conn:
            conn.execute("UPDATE bill SET summary_he = %s WHERE knesset_bill_id = 2229019", (old,))

def test_bill_about_on_every_compared_reading(client):
    """A comparison lists every reading of a bill (here a preliminary one), and each carries what the law does."""
    with client.app.state.pool.connection() as conn:
        old = conn.execute("SELECT summary_he FROM bill WHERE knesset_bill_id = 2196976").fetchone()["summary_he"]
        conn.execute("UPDATE bill SET summary_he = 'תקציר' WHERE knesset_bill_id = 2196976")
    try:
        diffs = client.get("/api/v1/compare/members", params={"a": DISSENTER, "b": LIKUD_IN_37689[1]}).json()["data"]["differences"]
        assert [(d["vote"]["id"], d["vote"]["stage"]) for d in diffs] == [(37689, "preliminary")]
        assert diffs[0]["vote"]["bills"][0]["about"]["summary_he"] == "תקציר"
    finally:
        with client.app.state.pool.connection() as conn:
            conn.execute("UPDATE bill SET summary_he = %s WHERE knesset_bill_id = 2196976", (old,))


@pytest.mark.parametrize('kind,a,b', [('members', DISSENTER, LIKUD_IN_37689[1]), ('factions', LIKUD, 1102)])
def test_compare_contested_and_turnout_filters(client, kind, a, b):
    """The /votes views apply to comparisons, the agreement rate included: only contested votes, a minimum turnout."""
    url = f'/api/v1/compare/{kind}'
    rate = lambda **p: client.get(url, params={'a': a, 'b': b, **p}).json()['data']['agreement']['denominator']
    assert rate() == 1 and rate(min_cast=60) == 1 and rate(min_cast=120) == 0
    assert rate(contested='true') == 0  # vote 37689 is not contested ...
    with client.app.state.pool.connection() as conn:
        conn.execute("""INSERT INTO vote_bloc SELECT id, 0, 0, 0, 0, 0, 0, true FROM vote WHERE knesset_vote_id = 37689""")
    try:
        assert rate(contested='true') == 1  # ... until the blocs differ on it
    finally:
        with client.app.state.pool.connection() as conn:
            conn.execute("DELETE FROM vote_bloc WHERE vote_id = (SELECT id FROM vote WHERE knesset_vote_id = 37689)")


def test_faction_splits_from_memberships(client):
    """A faction that ended or started mid-Knesset names where its members went or came from that day."""
    moves = lambda fs, key: {f["id"]: [(m["id"], m["members"], m["on"], m["renamed"]) for m in f[key]] for f in fs if f[key]}
    listed = client.get("/api/v1/factions", params={"term": 25}).json()["data"]
    # National Unity was renamed Blue and White - National Unity: the same group, a new faction record
    assert moves(listed, "continued_as") == {1098: [(1110, 6, "2025-07-08", True)]}
    assert moves([client.get("/api/v1/factions/1110").json()["data"]], "continued_from") == {1110: [(1098, 6, "2025-07-08", True)]}
    assert moves(listed, "continued_from")[1108] == [(1098, 3, "2024-03-13", False)]  # New Hope split off; National Unity went on
    # Idan Roll left Yesh Atid, which still exists: a split, not a rename
    assert moves([client.get("/api/v1/factions/1109").json()["data"]], "continued_from") == {1109: [(1102, 1, "2025-01-14", False)]}
    assert 1103 not in moves(listed, "continued_from")
    detail = client.get("/api/v1/factions/1098").json()["data"]
    assert [(m["id"], m["members"]) for m in detail["continued_as"]] == [(1110, 6)] and detail["continued_from"] == []


def test_comparison_paging_preserves_global_rate_and_all_disagreements(client, monkeypatch):
    import datetime as dt
    from hkv.api import entities
    from hkv.api.common import VoteSummary

    template = VoteSummary.model_validate(client.get('/api/v1/votes/37689').json()['data'])
    rows = [dict(vid=i, occurred_on=dt.date(2025, 1, 1), a='for', b='against') for i in range(205, 0, -1)]
    rows += [dict(vid=0, occurred_on=dt.date(2024, 1, 1), a='for', b='for'),
             dict(vid=206, occurred_on=dt.date(2025, 1, 1), a='for', b=None)]

    class Conn:
        def execute(self, _query, params):
            return [{'id': vid} for vid in params[0]]

    monkeypatch.setattr(entities, 'vote_summary', lambda row: template.model_copy(update={'id': row['id']}))
    monkeypatch.setattr(entities, 'attach_about', lambda conn, votes: None)
    monkeypatch.setattr(entities, 'attach_sides', lambda conn, votes: None)
    pages = []
    cursor = None
    while True:
        page = entities._compare(Conn(), rows, [], ['adopt_bill'], cursor=cursor)
        pages.append(page)
        if not page.next_cursor:
            break
        cursor = page.next_cursor
    assert [len(p.differences) for p in pages] == [100, 100, 5]
    assert [p.differences_offset for p in pages] == [0, 100, 200]
    assert all(p.differences_total == 205 and p.agreement.numerator == 1 and p.agreement.denominator == 206 for p in pages)
    assert [d.vote.id for p in pages for d in p.differences] == list(range(205, 0, -1))


@pytest.mark.parametrize('kind,a,b', [('members', DISSENTER, LIKUD_IN_37689[1]), ('factions', LIKUD, LIKUD)])
def test_compare_pagination_contract_and_bad_cursors(client, kind, a, b):
    import base64
    import json
    params = {'a': a, 'b': b, 'limit': 1}
    data = client.get(f'/api/v1/compare/{kind}', params=params).json()['data']
    assert data['differences_total'] == data['agreement']['denominator'] - data['agreement']['numerator']
    assert data['differences_offset'] == 0 and data['next_cursor'] is None
    for malformed in ['not-base64', base64.urlsafe_b64encode(json.dumps(['2025-01-01', True]).encode()).decode(),
                      base64.urlsafe_b64encode(b'["2025-01-01"]').decode()]:
        assert client.get(f'/api/v1/compare/{kind}', params={**params, 'cursor': malformed}).status_code == 400
    assert client.get(f'/api/v1/compare/{kind}', params={**params, 'limit': 101}).status_code == 422
