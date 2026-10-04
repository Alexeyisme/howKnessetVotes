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
