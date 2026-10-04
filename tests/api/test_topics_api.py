"""Topics and search over the recorded slice. Bills in it:
2196976 'חוק-יסוד: הממשלה (תיקון - כשירותם של שרים)' -> governance;
2229019 'נוכחות עורך דין בחקירת קטינים ואנשים עם מוגבלות' -> family + welfare (third reading = vote 46699)."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from hkv.api.app import create_app
from hkv.topics import sync
from tests.ingest.test_loader import SLICE, ingest


@pytest.fixture(scope="module")
def client(new_database):
    url = new_database()
    ingest(url, SLICE)
    with psycopg.connect(url, autocommit=True) as conn:
        sync(conn)
    with TestClient(create_app(url)) as c:
        yield c


def search(client, q):
    return client.get("/api/v1/search", params={"q": q}).json()["data"]


def test_bill_topics_are_marked_automatic(client):
    b = client.get("/api/v1/bills/2229019").json()["data"]
    assert {t["slug"] for t in b["topics"]} >= {"family", "welfare"}
    assert all(t["origin"] == "rule" and t["review_state"] == "unreviewed" and t["evidence"] for t in b["topics"])


def test_topic_faction_stats_use_final_reading(client):
    t = client.get("/api/v1/topics/family", params={"term": 25}).json()
    stats = {f["faction"]["id"]: f for f in t["data"]["factions"]}
    ballots_46699 = {r["MkId"] for r in SLICE["KNS_PlenumVoteResult"] if r["VoteID"] == 46699}
    assert sum(f["votes"] for f in stats.values()) >= 1 and len(ballots_46699) == 5
    assert all(f["votes"] == f["majority_for"] + f["majority_against"] + f["other"] for f in stats.values())
    assert "official classification" in t["meta"]["note"] and "been reviewed" in t["meta"]["note"]
    assert t["data"]["label_en"] == "Family, children and equality" and t["data"]["label"] == t["data"]["label_he"] and t["data"]["aliases_en"]
    en = client.get("/api/v1/topics", params={"lang": "en"}).json()["data"]
    assert all(x["label"] == x["label_en"] for x in en)


def test_votes_and_bills_filter_by_topic(client):
    assert [v["id"] for v in client.get("/api/v1/votes", params={"topic": "governance"}).json()["data"]] == [37689]
    assert [b["id"] for b in client.get("/api/v1/bills", params={"topic": "welfare"}).json()["data"]] == [2229019]


def test_search_russian_topics_and_factions(client):
    assert [t["slug"] for t in search(client, "выборы")["topics"]] == ["governance"]
    assert "Ликуд" in {f["short_ru"] for f in search(client, "ликуд")["factions"]}
    assert search(client, "выборы")["script"] == "cyrillic"


def test_search_hebrew_normalised_and_numbers(client):
    assert [b["id"] for b in search(client, "קטינים")["bills"]] == [2229019]
    assert [b["id"] for b in search(client, "חוק־יסוד")["bills"]] == [2196976]  # maqaf in the query
    assert [b["id"] for b in search(client, "2229019")["bills"]] == [2229019]
    assert search(client, "בן גביר")["members"][0]["id"] == 30811
