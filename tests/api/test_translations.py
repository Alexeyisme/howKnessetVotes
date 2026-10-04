"""Title translations (R4): the sync stores what passes the checks, the API serves them per ?lang=, search finds
bills by their translated title, and visitors can file a correction (never applied)."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from hkv.api.app import create_app
from hkv.translate import StubTranslator, check, pending, sha256, sync
from tests.ingest.test_loader import SLICE, ingest

BILL = 2229019
TITLE = next(b["Name"] for b in SLICE["KNS_Bill"] if b["Id"] == BILL)


MARK = StubTranslator.mark(TITLE, "en")


class NumberDropper(StubTranslator):
    """Drops digits, so every title with a number fails the check."""

    def translate(self, titles, lang):
        return ["".join(ch for ch in self.mark(t, lang) if not ch.isdigit()) for t in titles]


@pytest.fixture(scope="module")
def url(new_database):
    url = new_database()
    ingest(url, SLICE)
    return url


@pytest.fixture(scope="module")
def client(url):
    with TestClient(create_app(url)) as c:
        yield c


def test_checks():
    assert check("חוק (תיקון מס' 4), 2026", "Law (Amendment No. 4), 2026") is None
    assert check("חוק (תיקון מס' 4), 2026", "Law (Amendment), 2026") == "numbers_missing:4"
    assert check("חוק", "חוק Law") == "hebrew_left"
    assert check("חוק", "  ") == "empty"


def test_sync_stores_and_rejects(url):
    with psycopg.connect(url) as conn:
        before = len(pending(conn, "en"))
        assert before >= 2
        counts = sync(conn, StubTranslator(), ["en"])
        assert counts["en"] == before and counts["en_failed"] == 0
        assert pending(conn, "en") == []
        row = conn.execute("SELECT text, origin, model FROM text_translation WHERE source_sha256 = %s AND language = 'en'", (sha256(TITLE),)).fetchone()
        assert row == (MARK, "machine", "stub")
        # a translator that loses numbers: nothing stored, one data_issue per failed title
        counts = sync(conn, NumberDropper(), ["ru"])
        issues = conn.execute("SELECT count(*) FROM data_issue WHERE issue_type = 'translation_check_failed'").fetchone()[0]
        assert counts["ru_failed"] == issues > 0
        assert counts["ru"] + counts["ru_failed"] == before


def test_api_title_fields_and_search(client, url):
    b = client.get(f"/api/v1/bills/{BILL}", params={"lang": "en"}).json()["data"]
    assert b["title"] == MARK and b["title_origin"] == "machine" and b["title_en"] == b["title"]
    he = client.get(f"/api/v1/bills/{BILL}").json()["data"]
    assert he["title"] is None and he["title_en"] == MARK
    v = client.get("/api/v1/votes/46699", params={"lang": "en"}).json()["data"]
    assert v["title_en"] and v["bills"][0]["title_en"] == MARK
    hits = client.get("/api/v1/search", params={"q": MARK[5:17]}).json()["data"]
    assert [x["id"] for x in hits["bills"]] == [BILL]


def test_suggestions(client, url):
    body = {"source_sha256": sha256(TITLE), "language": "en", "suggested_text": "Better title", "note": "typo", "page": "/en/bills/1"}
    r = client.post("/api/v1/suggestions", json=body)
    assert r.status_code == 201 and r.json()["id"]
    with psycopg.connect(url) as conn:
        assert conn.execute("SELECT status, suggested_text FROM translation_suggestion").fetchone() == ("open", "Better title")
        assert conn.execute("SELECT text FROM text_translation WHERE source_sha256 = %s AND language = 'en'", (sha256(TITLE),)).fetchone()[0] != "Better title"
    assert client.post("/api/v1/suggestions", json={**body, "website": "spam"}).status_code == 201   # honeypot: swallowed
    with psycopg.connect(url) as conn:
        assert conn.execute("SELECT count(*) FROM translation_suggestion").fetchone()[0] == 1
    assert client.post("/api/v1/suggestions", json={**body, "source_sha256": "zz"}).status_code == 422
