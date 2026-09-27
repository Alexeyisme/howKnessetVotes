"""API over the recorded slice (see tests/ingest/test_loader.py)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from hkv.api.app import create_app
from tests.ingest.test_loader import BEN_GVIR, SLICE, ingest


@pytest.fixture(scope="module")
def client(new_database):
    url = new_database()
    ingest(url, SLICE)
    with TestClient(create_app(url)) as c:
        yield c


def test_list_is_newest_first_with_cursor(client):
    page1 = client.get("/api/v1/votes", params={"limit": 2}).json()
    assert [v["id"] for v in page1["data"]] == [46700, 46699]
    assert page1["meta"]["date_basis"] == "vote_date"
    page2 = client.get("/api/v1/votes", params={"limit": 2, "cursor": page1["next_cursor"]}).json()
    assert [v["id"] for v in page2["data"]] == [37689] and page2["next_cursor"] is None


def test_filters(client):
    ids = lambda **p: [v["id"] for v in client.get("/api/v1/votes", params=p).json()["data"]]  # noqa: E731
    assert ids(stage="third") == [46699]
    assert ids(stage=["second", "third"]) == [46700, 46699]
    assert ids(date_from="2022-12-13", date_to="2022-12-13") == [37689]
    assert ids(bill=2229019) == [46700, 46699]
    assert ids(person=BEN_GVIR) == [37689]
    assert client.get("/api/v1/votes", params={"stage": "fourth"}).status_code == 422
    assert client.get("/api/v1/votes", params={"cursor": "garbage"}).status_code == 400


def test_vote_detail_counts_and_factions(client):
    v = client.get("/api/v1/votes/37689").json()["data"]
    rc = v["roll_call"]
    assert rc["total_records"] == 114 and rc["for"] + rc["against"] + rc["abstain"] + rc["present_not_voting"] + rc["other"] == 114
    assert sum(f["counts"]["total_records"] for f in v["by_faction"]) == 114 and v["unresolved_faction_records"] == 0
    assert v["official_totals"] is None and v["totals_match"] is None  # no official totals after 2021
    assert v["occurred_at"] is None and v["occurred_on"] == "2022-12-13"
    assert v["source_url"].endswith("voteId=37689")
    assert all(f["majority"] in {"for", "against", "abstain", "mixed", "none"} for f in v["by_faction"])


def test_ballots(client):
    rows = client.get("/api/v1/votes/46699/ballots").json()["data"]
    assert len(rows) == 5 and all(r["faction_id"] for r in rows)
    assert client.get("/api/v1/votes/1/ballots").status_code == 404
