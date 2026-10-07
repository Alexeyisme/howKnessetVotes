"""Bill descriptions from explanatory notes (L7): document links load, the notes are cut out of the proposal, the
description is stored or the failure recorded once, and the API serves it (with translations) only where there is
no official summary."""

from __future__ import annotations

import zipfile
from io import BytesIO

import psycopg
import pytest
from fastapi.testclient import TestClient

from hkv.api.app import create_app
from hkv.ingest.loader import Loader
from hkv.notes import Item, StubSummarizer, candidates, check, docx_text, notes_section, prepare, sync
from hkv.translate import StubTranslator, sync as sync_translations
from tests.ingest.test_loader import SLICE, FixtureSource, ingest

WITH_NOTES, NO_NOTES = 2229019, 2196976
NOTES = "מוצע לקבוע כי הקנס יעמוד על 5000 שקלים, משום שהקנס הקיים אינו מרתיע."
PROPOSAL = ["מספר פנימי: 1", "הצעת חוק לדוגמה, התשפ\"ו-2026", "1.", "בחוק העיקרי, בסעיף 3, במקום \"100\" יבוא \"5000\".",
            "דברי הסבר", NOTES, "---------------------------------", "הוגשה ליו\"ר הכנסת והסגנים"]
DOCS = [
    {"Id": 1, "BillID": WITH_NOTES, "GroupTypeID": 1, "GroupTypeDesc": "הצעת חוק לדיון מוקדם", "ApplicationID": 1,
     "ApplicationDesc": "DOC", "FilePath": "https://fs.knesset.gov.il/\\25\\law\\25_lst_1.docx", "LastUpdatedDate": "2026-01-01T00:00:00"},
    {"Id": 2, "BillID": WITH_NOTES, "GroupTypeID": 1, "GroupTypeDesc": "הצעת חוק לדיון מוקדם", "ApplicationID": 2,
     "ApplicationDesc": "PDF", "FilePath": "https://fs.knesset.gov.il/\\25\\law\\25_lst_1.pdf", "LastUpdatedDate": "2026-01-01T00:00:00"},
    {"Id": 3, "BillID": NO_NOTES, "GroupTypeID": 1, "GroupTypeDesc": "הצעת חוק לדיון מוקדם", "ApplicationID": 1,
     "ApplicationDesc": "DOC", "FilePath": "https://fs.knesset.gov.il/25/law/25_lst_3.docx", "LastUpdatedDate": "2026-01-01T00:00:00"},
    {"Id": 4, "BillID": 999, "GroupTypeID": 1, "GroupTypeDesc": "x", "ApplicationID": 1, "ApplicationDesc": "DOC",
     "FilePath": "https://fs.knesset.gov.il/25/law/x.docx", "LastUpdatedDate": "2026-01-01T00:00:00"},   # not our bill
]


def docx(paragraphs: list[str]) -> bytes:
    body = "".join(f'<w:p><w:r><w:t xml:space="preserve">{p.replace("&", "&amp;").replace(chr(34), "&quot;")}</w:t></w:r></w:p>'
                   for p in paragraphs)
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", f'<?xml version="1.0"?><w:document xmlns:w="x"><w:body>{body}</w:body></w:document>')
    return buf.getvalue()


@pytest.fixture(scope="module")
def url(new_database):
    url = new_database()
    ingest(url, SLICE)
    with psycopg.connect(url) as conn:
        Loader(conn, FixtureSource({"KNS_DocumentBill": DOCS})).load_documents([WITH_NOTES, NO_NOTES])
    return url


@pytest.fixture(scope="module")
def cache(tmp_path_factory):
    """The files as fetch() would have cached them, so the test needs no network."""
    root = tmp_path_factory.mktemp("files")
    (root / "25/law").mkdir(parents=True)
    (root / "25/law/25_lst_1.docx").write_bytes(docx(PROPOSAL))
    (root / "25/law/25_lst_3.docx").write_bytes(docx(PROPOSAL[:4]))   # a proposal without notes
    return root


def test_notes_section():
    assert notes_section(docx_text(docx(PROPOSAL))) == NOTES
    assert notes_section("טקסט\n  דברי  הסבר:  \n" + NOTES) == NOTES
    assert notes_section("טקסט\nדברי - הסבר\n" + NOTES) == NOTES
    assert notes_section("\n".join(PROPOSAL[:4])) is None
    assert notes_section("דברי הסבר\nקצר") is None


def test_prepare_sniffs_the_format():
    assert prepare("b", "t", 1, docx(PROPOSAL)).notes == NOTES
    pdf = prepare("b", "t", 1, b"%PDF-1.4 ...")
    assert pdf.pdf is not None and pdf.notes is None
    with pytest.raises(Exception, match="unsupported_format"):
        prepare("b", "t", 1, b"<html>")


def test_check():
    item = Item("b", "חוק, 2026", 1, "0" * 64, notes=NOTES)
    good = "לדברי המציעים, ההצעה מעלה את הקנס ל-5,000 שקלים כדי שירתיע."
    assert check(item, good) is None
    assert check(item, good.replace("5,000", "6,000")) == "numbers_not_in_notes:6000"
    assert check(item, "short") == "too_short"
    assert check(item, "The sponsors say the bill raises the fine to 5000 shekels.") == "not_hebrew"
    assert check(Item("b", "t", 1, "0" * 64, pdf=b"%PDF"), good.replace("5,000", "6,000")) is None   # PDF: no text to compare


def test_documents_loaded(url):
    with psycopg.connect(url) as conn:
        rows = conn.execute("SELECT knesset_document_id, url FROM bill_document ORDER BY 1").fetchall()
    assert rows == [(1, "https://fs.knesset.gov.il/25/law/25_lst_1.docx"), (2, "https://fs.knesset.gov.il/25/law/25_lst_1.pdf"),
                    (3, "https://fs.knesset.gov.il/25/law/25_lst_3.docx")]


def test_sync_and_api(url, cache):
    with psycopg.connect(url) as conn:
        assert {c[2] for c in candidates(conn)} == {1, 3}   # Word before PDF
        assert sync(conn, StubSummarizer(), cache) == {"pending": 2, "stored": 1, "failed": 1}
        issue = conn.execute("SELECT details->>'reason' FROM data_issue WHERE issue_type = 'explanation_failed' AND status = 'open'").fetchall()
        assert issue == [("notes_not_found",)]
        # neither is sent again on the next run; a failed one is with retry_failed, and keeps one open issue
        assert sync(conn, StubSummarizer(), cache)["pending"] == 0
        assert sync(conn, StubSummarizer(), cache, retry_failed=True) == {"pending": 1, "stored": 0, "failed": 1}
        assert conn.execute("SELECT count(*) FROM data_issue WHERE issue_type = 'explanation_failed'").fetchone()[0] == 1
        stored = conn.execute("SELECT summary_he, notes_he, model FROM bill_explanation").fetchone()
        assert stored[1:] == (NOTES, "stub")
        assert sync_translations(conn, StubTranslator(), ["en"], kinds=["notes"]) == {"en_notes": 1, "en_notes_failed": 0}
    with TestClient(create_app(url)) as client:
        b = client.get(f"/api/v1/bills/{WITH_NOTES}", params={"lang": "en"}).json()["data"]
        assert b["explanation_he"] == stored[0] and b["explanation"] == b["explanation_en"] == StubTranslator.mark(stored[0], "en")
        assert b["explanation_origin"] == "machine" and b["explanation_source_url"].endswith("25_lst_1.docx")
        assert client.get(f"/api/v1/bills/{NO_NOTES}").json()["data"]["explanation_he"] is None
    # an official summary takes over: the description is no longer shown, and no new one is requested
    with psycopg.connect(url) as conn:
        conn.execute("UPDATE bill SET summary_he = 'תקציר רשמי' WHERE knesset_bill_id = %s", (WITH_NOTES,))
        conn.commit()
    with TestClient(create_app(url)) as client:
        assert client.get(f"/api/v1/bills/{WITH_NOTES}").json()["data"]["explanation_he"] is None
