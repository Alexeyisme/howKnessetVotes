"""Reservations (L7 step 3): the section is cut out of the committee version, the model's attribution of numbers
to proposers is checked against the numbers printed, names must appear in the text, and the API counts per faction
(a joint reservation once per faction) with coalition/opposition context."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from hkv.api.app import create_app
from hkv.ingest.loader import Loader
from hkv.reservations import Item, candidates, check, expected_numbers, numbered, section, sync
from tests.debate.test_debate import docx
from tests.ingest.test_loader import SLICE, FixtureSource, ingest

BILL = 2229019
SECTION = [
    "הסתייגויות ובקשות רשות דיבור",
    "להצעת חוק נוכחות עורך דין בחקירת קטינים",
    "להלן שמות חברי הכנסת המסתייגים לפי קבוצות:",
    "קבוצת העבודה – חברי הכנסת מרב מיכאלי, גלעד קריב",
    "הסתייגויות",
    "לסעיף 1",
    "קבוצת העבודה מציעה:",
    "1. בפסקה (1), במקום \"14\" יבוא \"16\".",
    "2. פסקה (2) – תימחק.",
    "קבוצת העבודה וחבר הכנסת אביגדור ליברמן מציעים:",
    "3. בסופו יבוא \"(3) השר ידווח לוועדה אחת לשנה\".",
    "לסעיף 2",
    "חבר הכנסת אביגדור ליברמן מציע:",
    "4. הסעיף – יימחק.",
    "***********************",
    "בקשות רשות דיבור",
    "חברי הכנסת אופיר כץ, פלוני אלמוני",
]
DOCUMENT = ["הצעת חוק לקריאה השנייה ולקריאה השלישית", "1. בחוק העיקרי, בסעיף 2 – (1) ...", *SECTION]
GOOD = {
    "proposers": [{"label": "קבוצת העבודה", "members": ["מרב מיכאלי", "גלעד קריב"], "gist": "מוצע להעלות את הגיל ל-16 ולמחוק פסקה."},
                  {"label": "אביגדור ליברמן", "members": ["אביגדור ליברמן"], "gist": "מוצע למחוק את סעיף 2 ולחייב דיווח."}],
    "blocks": [{"proposers": ["קבוצת העבודה"], "section": "לסעיף 1", "first": 1, "last": 2},
               {"proposers": ["קבוצת העבודה", "אביגדור ליברמן"], "section": "לסעיף 1", "first": 3, "last": 3},
               {"proposers": ["אביגדור ליברמן"], "section": "לסעיף 2", "first": 4, "last": 4}],
    "speak_requests": ["אופיר כץ", "פלוני אלמוני"],
    "summary": "ההסתייגויות מבקשות להעלות את גיל ההגנה ולחייב דיווח לוועדה.",
}
DOCS = [{"Id": 77, "BillID": BILL, "GroupTypeID": 4, "GroupTypeDesc": "הצעת חוק לקריאה השנייה והשלישית", "ApplicationID": 1,
         "ApplicationDesc": "DOC", "FilePath": "https://fs.knesset.gov.il/25/law/25_ls2_77.docx", "LastUpdatedDate": "2026-07-27T00:00:00"}]


class FakeExtractor:
    model = "fake"

    def __init__(self, out: dict):
        self.out = out

    def extract(self, item: Item) -> dict:
        return self.out


def item() -> Item:
    return Item("b", "t", 1, "0" * 64, "\n".join(SECTION), numbers_checked=True)


def test_section_and_numbers():
    sec = section("תוכן העניינים: הסתייגויות ובקשות רשות דיבור עמ' 5\n" + "\n".join(DOCUMENT))
    assert sec.startswith("הסתייגויות ובקשות רשות דיבור\nלהצעת חוק")      # the last heading, not the table of contents
    assert numbered(sec) == [1, 2, 3, 4]                                       # "(1)", "16" and the speaking list are not items
    assert expected_numbers("1. א\n2. ב\n4. ג\n\"2. ציטוט\"") == {1, 2}        # the run stops at a gap
    assert section("אין כאן הסתייגויות") is None


def test_check():
    assert check(item(), GOOD) is None
    missing = {**GOOD, "blocks": GOOD["blocks"][:2]}
    assert check(item(), missing) == "numbers_mismatch:3/4"
    overlap = {**GOOD, "blocks": [*GOOD["blocks"], {"proposers": ["אביגדור ליברמן"], "section": "לסעיף 2", "first": 4, "last": 4}]}
    assert check(item(), overlap) == "overlapping_numbers"
    invented = {**GOOD, "proposers": [*GOOD["proposers"][:1], {**GOOD["proposers"][1], "members": ["יאיר לפיד"]}]}
    assert check(item(), invented) == "name_not_in_text:יאיר לפיד"
    assert check(item(), {**GOOD, "blocks": [{**GOOD["blocks"][0], "proposers": ["קבוצת יש עתיד"]}]}) == "unknown_proposer_in_block"
    assert check(item(), {**GOOD, "proposers": [], "blocks": []}) == "no_reservations_extracted"
    assert check(item(), {**GOOD, "summary": "The reservations raise the age."}) == "bad_summary"
    # PDF pages read by the model: no printed numbers to compare, but they must still be 1..N without a gap
    pdf = Item("b", "t", 1, "0" * 64, "\n".join(SECTION).replace("1. ", "").replace("4. ", ""), numbers_checked=False, pdf=b"%PDF")
    assert check(pdf, GOOD) is None
    assert check(pdf, {**GOOD, "blocks": [GOOD["blocks"][0], GOOD["blocks"][2]]}) == "numbers_not_contiguous"
    # names followed by a comma in the text, words in reverse order (PDF extracted in visual order)
    reversed_text = Item("b", "t", 1, "0" * 64, "\n".join(SECTION).replace("מרב מיכאלי,", "מיכאלי מרב,"), numbers_checked=True)
    assert check(reversed_text, GOOD) is None


def test_gershayim():
    from hkv.llm import gershayim
    assert gershayim('צה"ל ובג"ץ, "ציטוט"') == 'צה״ל ובג״ץ, "ציטוט"'   # only between Hebrew letters


@pytest.fixture(scope="module")
def url(new_database):
    url = new_database()
    ingest(url, SLICE)
    with psycopg.connect(url) as conn:
        Loader(conn, FixtureSource({"KNS_DocumentBill": DOCS})).load_documents([BILL])
    return url


@pytest.fixture(scope="module")
def cache(tmp_path_factory):
    root = tmp_path_factory.mktemp("files")
    (root / "25/law").mkdir(parents=True)
    (root / "25/law/25_ls2_77.docx").write_bytes(docx(DOCUMENT))
    return root


def test_sync_and_api(url, cache):
    with psycopg.connect(url) as conn:
        assert candidates(conn) == []                 # nothing contested in the fixture
        bad = {**GOOD, "blocks": GOOD["blocks"][:2]}
        assert sync(conn, FakeExtractor(bad), cache, contested_only=False) == {"pending": 1, "stored": 0, "failed": 1}
        assert sync(conn, FakeExtractor(GOOD), cache, contested_only=False)["pending"] == 0      # not retried by itself
        assert sync(conn, FakeExtractor(GOOD), cache, contested_only=False, retry_failed=True) == {"pending": 1, "stored": 1, "failed": 0}
        assert conn.execute("SELECT status FROM data_issue WHERE issue_type = 'reservations_failed'").fetchall() == [("resolved",)]
    with TestClient(create_app(url)) as client:
        r = client.get(f"/api/v1/bills/{BILL}", params={"lang": "en"}).json()["data"]["reservations"]
    assert (r["total"], r["numbers_checked"], r["source_url"]) == (4, True, "https://fs.knesset.gov.il/25/law/25_ls2_77.docx")
    assert [(g["label_he"], g["reservations"], g["sections"]) for g in r["groups"]] == [
        ("קבוצת העבודה", 3, ["לסעיף 1"]), ("אביגדור ליברמן", 2, ["לסעיף 1", "לסעיף 2"])]
    # Labor: reservations 1–3 by two members; Yisrael Beytenu: 3 and 4 (the joint one counts for both)
    assert [(f["faction_id"], f["reservations"], f["members"]) for f in r["by_faction"]] == [(1100, 3, 2), (1104, 2, 1)]
    assert r["by_faction"][0]["name"] and r["unresolved_proposers"] == 0
    assert [(m["person_id"], m["name_he"]) for m in r["speak_requests"]] == [(30701, "אופיר כץ"), (None, "פלוני אלמוני")]
