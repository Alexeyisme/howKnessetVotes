"""Member and faction names (hkv.names) over the recorded slice, with a fake website/Wikidata."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from hkv.api.app import create_app
from hkv.names import MkDetails, SiteMk, WikidataMk, _set_photo, cache_photos, match_by_name, sync_factions, sync_members
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
            (90, "ru"): MkDetails("Биньямин  Нетаньяху", "Ликуд"), (90, "en"): MkDetails("Benjamin Netanyahu", "Likud", "https://fs.knesset.gov.il/globaldocs/MK/90/1_90_3_1.jpeg"),
            (1056, "ru"): MkDetails("Итамар Бен-Гвир", "«Оцма Йехудит» во главе с Итамаром Бен-Гвиром"),
            (1056, "en"): MkDetails("Itamar Ben Gvir", "Otzma Yehudit Chaired by Itamar Ben Gvir"),
            (90, "ar"): MkDetails("بنيامين نتنياهو", "الليكود"), (1056, "ar"): MkDetails("إيتمار بن غفير", "عوتسما يهوديت"),
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
        assert (m["name_ru"], m["name_en"], m["name_ar"]) == ("Итамар Бен-Гвир", "Itamar Ben Gvir", "إيتمار بن غفير")
        assert m["last_faction"]["short_ru"] == "Оцма Йехудит"
        vote = c.get("/api/v1/votes/37689/ballots").json()["data"]
        ben_gvir = next(b for b in vote if b["person_id"] == BEN_GVIR)
        assert ben_gvir["name_ru"] == "Итамар Бен-Гвир" and ben_gvir["faction_short_ru"]
        for q, script in (("бен-гвир", "cyrillic"), ("нетаньяху", "cyrillic"), ("биби", "cyrillic"), ("netanyahu", "latin"), ("bibi", "latin"),
                          ("نتنياهو", "arabic"), ("ايتمار بن غفير", "arabic")):  # a bare alef finds إيتمار
            res = c.get("/api/v1/search", params={"q": q}).json()["data"]
            assert res["script"] == script
            assert res["members"] and res["members"][0]["id"] in (BEN_GVIR, NETANYAHU), q


def test_api_lang_picks_display_names_and_photo(db):
    url, _ = db
    with TestClient(create_app(url)) as c:
        he = c.get(f"/api/v1/members/{NETANYAHU}").json()["data"]
        assert he["name"] == he["name_he"] and he["last_faction"]["name"] == he["last_faction"]["name_he"]
        assert he["photo_url"] == "https://fs.knesset.gov.il/globaldocs/MK/90/1_90_3_1.jpeg"
        en = c.get(f"/api/v1/members/{NETANYAHU}", params={"lang": "en"}).json()["data"]
        assert en["name"] == "Benjamin Netanyahu" and en["last_faction"]["short"] == en["last_faction"]["short_en"]
        ballots = c.get("/api/v1/votes/37689/ballots", params={"lang": "ru"}).json()["data"]
        ben_gvir = next(b for b in ballots if b["person_id"] == BEN_GVIR)
        assert (ben_gvir["name"], ben_gvir["faction_name"]) == ("Итамар Бен-Гвир", ben_gvir["faction_short_ru"])
        ar = c.get(f"/api/v1/members/{NETANYAHU}", params={"lang": "ar"}).json()["data"]
        assert ar["name"] == "بنيامين نتنياهو" and ar["last_faction"]["short"] == "الليكود"
        assert c.get("/api/v1/members", params={"lang": "fr"}).status_code == 422
        # a long official Hebrew list name gets a curated short form for the Hebrew UI
        otzma = c.get(f"/api/v1/factions/{OTZMA}", params={"lang": "he"}).json()["data"]
        assert (otzma["short_he"], otzma["short"], otzma["name"]) == ("עוצמה יהודית", "עוצמה יהודית", otzma["name_he"])


def test_member_list_filters_by_name_in_any_language(db):
    url, _ = db
    with TestClient(create_app(url)) as c:
        for q in ("Нетаньяху", "netanyahu", "נתניהו", "نتنياهو"):
            assert [m["id"] for m in c.get("/api/v1/members", params={"q": q}).json()["data"]] == [NETANYAHU], q


JPEG = b"\xff\xd8\xff" + b"x" * 2000


def test_photo_copies_are_served_from_here(db):
    """The Knesset file server blocks visitors outside Israel (migration 0014): the API serves a stored copy."""
    url, _ = db
    with psycopg.connect(url) as conn:
        n = conn.execute("SELECT count(*) FROM person_photo").fetchone()[0]
        assert n > 0
        def failing(u):
            raise ValueError("not an image: text/html")
        assert cache_photos(conn, failing) == {"todo": n, "failed": n}
        assert cache_photos(conn, lambda u: (JPEG, "image/jpeg")) == {"todo": n, "stored": n}
        assert cache_photos(conn, lambda u: (JPEG, "image/jpeg")) == {"todo": 0}
    with TestClient(create_app(url)) as c:
        m = c.get(f"/api/v1/members/{NETANYAHU}").json()["data"]
        assert m["photo_url"].startswith(f"/api/v1/members/{NETANYAHU}/photo?v=")
        r = c.get(m["photo_url"])
        assert r.status_code == 200 and r.content == JPEG and r.headers["content-type"] == "image/jpeg"
        assert "immutable" in r.headers["cache-control"]
        assert c.get("/api/v1/members/999999999/photo").status_code == 404
    with psycopg.connect(url) as conn:
        # a new portrait URL on the Knesset website drops the old copy until it is fetched again
        pid = conn.execute("SELECT id FROM person WHERE knesset_person_id = %s", (NETANYAHU,)).fetchone()[0]
        assert _set_photo(conn, pid, "https://fs.knesset.gov.il/globaldocs/MK/90/new.jpeg") == 1
        conn.commit()
    with TestClient(create_app(url)) as c:
        assert c.get(f"/api/v1/members/{NETANYAHU}").json()["data"]["photo_url"] == "https://fs.knesset.gov.il/globaldocs/MK/90/new.jpeg"
