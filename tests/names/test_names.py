"""Member and faction names (hkv.names) over the recorded slice, with a fake website/Wikidata."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from hkv.api.app import create_app
from hkv.names import MkDetails, SiteMk, WikidataMk, match_by_name, sync_factions, sync_members
from tests.ingest.test_loader import BEN_GVIR, SLICE, ingest

NETANYAHU = 965
OTZMA = 1106


def test_match_by_name():
    cands = {1: "מירי רגב", 2: "אלי כהן", 3: "מאיר כהן", 4: "אלי כהן"}
    assert match_by_name("מירי מרים רגב", cands) == 1          # middle name on one side only
    assert match_by_name("אלי כהן", cands) is None              # two people with the same name: never guess
    assert match_by_name("מאיר יצחק כהן", cands) == 3
    assert match_by_name("יעקב כהן", cands) is None             # one shared token is not enough


class FakeSources:
    def site_codes(self):
        return {NETANYAHU: 90}                                    # official PersonID -> website ID

    def current_mks(self):
        return [SiteMk(1056, "איתמר בן גביר")]                    # matched by name

    def wikidata_mks(self):
        return [WikidataMk("Q43723", 90, "בנימין נתניהו", "Benjamin Netanyahu", "Биньямин Нетаньяху", ("Bibi",), ("Биби",))]

    def mk_details(self, site_id, lang):
        return {
            (90, "ru"): MkDetails("Биньямин  Нетаньяху", "Ликуд"), (90, "en"): MkDetails("Benjamin Netanyahu", "Likud"),
            (1056, "ru"): MkDetails("Итамар Бен-Гвир", "«Оцма Йехудит» во главе с Итамаром Бен-Гвиром"),
            (1056, "en"): MkDetails("Itamar Ben Gvir", "Otzma Yehudit Chaired by Itamar Ben Gvir"),
        }.get((site_id, lang))


@pytest.fixture(scope="module")
def db(new_database):
    url = new_database()
    ingest(url, SLICE)
    with psycopg.connect(url, autocommit=True) as conn:
        counts = sync_members(conn, FakeSources())
        sync_factions(conn, FakeSources())
    return url, counts


def test_members_get_official_names_and_unresolved_become_issues(db):
    url, counts = db
    assert counts["site_id:kns_mksitecode"] == 1 and counts["site_id:site_current_list"] == 1
    with psycopg.connect(url) as conn:
        names = dict(conn.execute(
            "SELECT p.knesset_person_id, n.ru FROM person_name n JOIN person p ON p.id = n.person_id WHERE n.ru IS NOT NULL").fetchall())
        assert names == {NETANYAHU: "Биньямин Нетаньяху", BEN_GVIR: "Итамар Бен-Гвир"}  # whitespace normalised
        missing = conn.execute("SELECT count(*) FROM data_issue WHERE issue_type = 'person_name_missing' AND status = 'open'").fetchone()[0]
        assert missing == counts["people"] - 2
        # second run without refresh does not touch people who already have official names
        assert sync_members(conn, FakeSources())["todo"] == counts["people"] - 2


def test_faction_names_official_full_curated_short(db):
    url, _ = db
    with psycopg.connect(url) as conn:
        row = conn.execute("""SELECT l.name, l.short_name, l.origin FROM faction_label l JOIN faction f ON f.id = l.faction_id
                              WHERE f.knesset_faction_id = %s AND l.language = 'ru'""", (OTZMA,)).fetchone()
        assert row == ("«Оцма Йехудит» во главе с Итамаром Бен-Гвиром", "Оцма Йехудит", "official")
        curated = conn.execute("""SELECT l.name FROM faction_label l JOIN faction f ON f.id = l.faction_id
                                  WHERE f.knesset_faction_id = 972 AND l.language = 'en'""").fetchone()
        assert curated == ("New Hope",)


def test_api_returns_names_and_searches_them(db):
    url, _ = db
    with TestClient(create_app(url)) as c:
        m = c.get(f"/api/v1/members/{BEN_GVIR}").json()["data"]
        assert (m["name_ru"], m["name_en"]) == ("Итамар Бен-Гвир", "Itamar Ben Gvir")
        assert m["last_faction"]["short_ru"] == "Оцма Йехудит"
        vote = c.get("/api/v1/votes/37689/ballots").json()["data"]
        ben_gvir = next(b for b in vote if b["person_id"] == BEN_GVIR)
        assert ben_gvir["name_ru"] == "Итамар Бен-Гвир" and ben_gvir["faction_short_ru"]
        for q, script in (("бен-гвир", "cyrillic"), ("нетаньяху", "cyrillic"), ("биби", "cyrillic"), ("netanyahu", "latin"), ("bibi", "latin")):
            res = c.get("/api/v1/search", params={"q": q}).json()["data"]
            assert res["script"] == script
            assert res["members"] and res["members"][0]["id"] in (BEN_GVIR, NETANYAHU), q
