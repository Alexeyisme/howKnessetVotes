"""Plenum debates (L7 step 2): the bill's agenda items are cut out of the sitting transcripts in all three generations
of the format, speakers are listed and resolved without a model, the model output is checked, and the API serves
the debate with each speaker's faction and final vote."""

from __future__ import annotations

import datetime as dt
import html
import zipfile
from io import BytesIO

import psycopg
import pytest
from fastapi.testclient import TestClient

from hkv.api.app import create_app
from hkv.debate import (Item, Speech, StubSummarizer, Turn, _one_list, candidates, check, fit, matches, segments, speeches, split_label,
                        sync, turns)
from hkv.ingest.loader import Loader
from hkv.translate import StubTranslator, sync as sync_translations
from tests.ingest.test_loader import SLICE, FixtureSource, ingest

BILL, SESSION = 2229019, 2245272
TITLE = 'הצעת חוק נוכחות עורך דין בחקירת קטינים ואנשים עם מוגבלות (תיקוני חקיקה והוראת שעה), התשפ"ו–2026'
KARIV_SPEECH = "אדוני היושב-ראש, החוק הזה נחוץ כדי להגן על 300 קטינים בשנה, ולכן נתמוך בו."
ROTMAN_SPEECH = "אני מציג את הצעת החוק בשם הוועדה, ויש בה הסדר מאוזן."
TRANSCRIPT = [
    "<< נושא >> מסמכים שהונחו על שולחן הכנסת << נושא >>",
    "<< יור >> היו\"ר אמיר אוחנה: << יור >>", "תודה.",
    "<< הצח >> הצעת חוק אחרת לגמרי, התשפ\"ו–2026 << הצח >>",
    "<< דובר >> משה טור פז (יש עתיד): << דובר >>", "נאום על חוק אחר.",
    f"<< הצח >> {TITLE} << הצח >>",
    "<< יור >> היו\"ר אמיר אוחנה: << יור >>", "נעבור לנושא הבא.",
    "<< דובר >> שמחה רוטמן (יו\"ר ועדת החוקה, חוק ומשפט): << דובר >>", ROTMAN_SPEECH,
    "<< דובר >> גלעד קריב (העבודה): << דובר >>", KARIV_SPEECH,
    "<< קריאה >> שמחה רוטמן (הציונות הדתית): << קריאה >>", "זה לא נכון.",
    "<< דובר_המשך >> גלעד קריב (העבודה): << דובר_המשך >>", "ובכל זאת, יש לתקן את הסעיף.",
    "<< דובר >> פלוני אלמוני (סיעה דמיונית): << דובר >>", "נאום של מי שאינו חבר כנסת ידוע.",
    "<< נושא >> מסמכים שהונחו על שולחן הכנסת << נושא >>",
    "<< דובר >> מזכיר הכנסת דן מרזוק: << דובר >>", "הודעה.",
]
PLENUM_DOCS = [
    {"Id": 501, "PlenumSessionID": SESSION, "GroupTypeID": 28, "GroupTypeDesc": "דברי הכנסת", "ApplicationID": 1,
     "ApplicationDesc": "DOC", "FilePath": "https://fs.knesset.gov.il//25/Plenum/25_ptm_501.doc", "LastUpdatedDate": "2026-07-28T18:00:00"},
    {"Id": 502, "PlenumSessionID": 999, "GroupTypeID": 28, "GroupTypeDesc": "דברי הכנסת", "ApplicationID": 1,
     "ApplicationDesc": "DOC", "FilePath": "https://fs.knesset.gov.il//25/Plenum/25_ptm_502.doc", "LastUpdatedDate": "2026-07-28T18:00:00"},
]


def docx(paragraphs: list[str]) -> bytes:
    body = "".join(f'<w:p><w:r><w:t xml:space="preserve">{html.escape(p)}</w:t></w:r></w:p>' for p in paragraphs)
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", f'<?xml version="1.0"?><w:document xmlns:w="x"><w:body>{body}</w:body></w:document>')
    return buf.getvalue()


def legacy_text(lines: list[str]) -> str:
    """What hkv.notes.legacy_doc_text gives for a 2009–2017 Word 97 transcript: hidden "<…>" structure lines."""
    return "\n".join(lines)


def test_split_label():
    assert split_label('גלעד קריב (העבודה)') == ("גלעד קריב", "העבודה")
    assert split_label('שמחה רוטמן (יו"ר ועדת החוקה, חוק ומשפט)') == ("שמחה רוטמן", 'יו"ר ועדת החוקה, חוק ומשפט')
    assert split_label("שר האנרגיה אלי כהן") == ("שר האנרגיה אלי כהן", None)


def test_matches_titles():
    assert matches(TITLE, [TITLE.replace("–", "-")])
    assert matches(TITLE, [TITLE.removeprefix("הצעת ")])                    # the law's title after it passed
    assert matches(f"הצעת חוק אחר; {TITLE}", [TITLE])                         # joint debate
    assert not matches("הצעת חוק אחרת לגמרי, התשפ\"ו–2026", [TITLE])


def test_joint_debate():
    """Budget days: several titles in a row, then one debate for all of them."""
    stream = turns("\n".join(["<< הצח >> הצעת חוק התקציב לשנת הכספים 2026 << הצח >>", "(קריאה שנייה ושלישית)",
                              f"<< הצח >> {TITLE} << הצח >>", "<< דובר >> גלעד קריב (העבודה): << דובר >>", KARIV_SPEECH,
                              "<< הצח >> הצעת חוק אחרת לגמרי << הצח >>", "<< דובר >> משה טור פז (יש עתיד): << דובר >>", "אחר."]))
    budget = segments(stream, ["הצעת חוק התקציב לשנת הכספים 2026"])
    assert [t.label for t in budget[0][1] if t.kind == "speech"] == ["גלעד קריב (העבודה)"]   # the joint debate
    assert [t.label for t in segments(stream, [TITLE])[0][1] if t.kind == "speech"] == ["גלעד קריב (העבודה)"]


def test_docx_transcript():
    stream = turns("\n".join(TRANSCRIPT))
    segs = segments(stream, [TITLE])
    assert [t for t, _ in segs] == [TITLE]
    speakers, spoken = speeches([("third", segs[0][1], False)])
    assert [s.name for s in speakers] == ["שמחה רוטמן", "גלעד קריב", "פלוני אלמוני"]   # no chair, no interjection, no official
    assert [s.speeches for s in speakers] == [1, 1, 1]                                    # the continuation joins its speech
    assert spoken[1].text == KARIV_SPEECH + " ובכל זאת, יש לתקן את הסעיף."
    assert speakers[0].affiliation == 'יו"ר ועדת החוקה, חוק ומשפט'


def test_legacy_transcripts():
    tagged = legacy_text(["<מסמכים שהונחו על שולחן הכנסת>", f"<{TITLE}>", '<היו"ר ראובן ריבלין:>', "נעבור לנושא.",
                          "<גלעד קריב (העבודה):>", "א" * 200, "<שמחה רוטמן (הציונות הדתית):>", "קצר מדי",
                          "<קריאה:>", "- - -", "<הצעת חוק אחרת>", "<משה טור פז (יש עתיד):>", "ב" * 200])
    speakers, spoken = speeches([("first", seg, True) for _, seg in segments(turns(tagged), [TITLE])])
    assert [s.name for s in speakers] == ["גלעד קריב"]        # a short "speech" in an untagged generation is an interjection
    untagged = legacy_text(["HYPERLINK \\l \"_Toc1\"", TITLE, "PAGEREF _Toc1 \\h", "HYPERLINK \\l \"_Toc2\"", "גלעד קריב (העבודה):",
                            "PAGEREF _Toc2 \\h", "פתיחת הישיבה", TITLE, 'היו"ר ראובן ריבלין:', "נעבור לנושא.",
                            "גלעד קריב (העבודה):", "א" * 200])
    speakers, _ = speeches([("first", seg, True) for _, seg in segments(turns(untagged), [TITLE])])
    assert [s.name for s in speakers] == ["גלעד קריב"]


def test_transcript_variants():
    """2018 .docx without markers ("title" + page number in the contents), a title broken over two lines in the body,
    a hidden marker broken over two lines, and amendment numbers that must agree."""
    docx_toc = ["הצעת חוק חינוך מיוחד (תיקון מס' 11), התשע\"ח–2018112", "גלעד קריב (העבודה):113", "פתיחה",
                "הצעת חוק חינוך מיוחד (תיקון מס' 11), התשע\"ח–2018", "גלעד קריב (העבודה):", "א" * 200]
    cut = TITLE.index(" ", 40)   # bodies break a long title at a space
    two_lines = ["HYPERLINK \\l \"_Toc1\"", TITLE, "PAGEREF _Toc1 \\h", "פתיחה", TITLE[:cut], TITLE[cut + 1:], "גלעד קריב (העבודה):", "א" * 200]
    marker = ["<מסמכים שהונחו על שולחן הכנסת>", "<קריאה:>", f"<{TITLE[:cut]}", f"{TITLE[cut + 1:]}>", "<גלעד קריב (העבודה):>", "א" * 200]
    for lines, title in ((docx_toc, "הצעת חוק חינוך מיוחד (תיקון מס' 11), התשע\"ח-2018"), (two_lines, TITLE), (marker, TITLE)):
        speakers, _ = speeches([("third", seg, True) for _, seg in segments(turns("\n".join(lines)), [title])])
        assert [x.name for x in speakers] == ["גלעד קריב"], lines[0]
    assert not matches("הצעת חוק לתיקון פקודת מס הכנסה (מס' 249), התשע\"ח–2018", ["הצעת חוק לתיקון פקודת מס הכנסה (מס' 248), התשע\"ח-2018"])
    assert matches("הצעת חוק התקציב לשנת הכספים 2005, התשס\"ה-", ["חוק התקציב לשנת הכספים 2005, התשס\"ה-2005"])   # a cut year


def test_fit_cuts_every_speech_to_one_cap():
    spoken = [Speech(0, "third", "א" * 100), Speech(1, "third", "ב" * 1000), Speech(2, "third", "ג" * 10)]
    texts, cut = fit(spoken, budget=300)
    assert cut and texts[0] == "א" * 100 and texts[2] == "ג" * 10 and texts[1].startswith("ב" * 190) and texts[1].endswith("[…]")
    assert fit(spoken, budget=2000) == ([s.text for s in spoken], False)


def test_check():
    item = Item("b", "v", TITLE, [1], ["0" * 64], [TITLE], [], [Speech(0, "third", KARIV_SPEECH), Speech(1, "third", "נגד")],
                [KARIV_SPEECH, "נגד"])
    good = {"summary": "הדיון עסק בהגנה על 300 קטינים בחקירות ובאיזון מול צורכי החקירה.",
            "arguments": [{"side": "for", "text": "החוק מגן על קטינים בחקירה.", "speeches": [1]},
                          {"side": "against", "text": "החוק מכביד על החקירות.", "speeches": [2, 1]}]}
    assert check(item, good) == (None, [{"side": "for", "text_he": "החוק מגן על קטינים בחקירה.", "speakers": [0]},
                                        {"side": "against", "text_he": "החוק מכביד על החקירות.", "speakers": [0, 1]}])
    assert check(item, {**good, "summary": good["summary"].replace("300", "400")})[0] == "numbers_not_in_debate:400"
    assert check(item, {**good, "arguments": [{"side": "for", "text": "החוק מגן על קטינים.", "speeches": [3]}]})[0] == "bad_speech_reference"
    assert check(item, {**good, "summary": "The debate was about minors in police interrogations."})[0] == "bad_summary"
    assert len(check(item, {**good, "arguments": [good["arguments"][0]] * 6})[1]) == 5     # the model's top five are kept
    # an unescaped quote in צה"ל ends the JSON string: a cut-off text is rejected, not stored
    assert check(item, {**good, "summary": "הדיון עסק בהגנה על 300 קטינים בחקירות ובמחסור בכוח אדם בצה"})[0] == "summary_cut_off"
    assert check(item, {**good, "arguments": []})[0] == "no_arguments"


@pytest.fixture(scope="module")
def url(new_database):
    url = new_database()
    ingest(url, SLICE)
    return url


@pytest.fixture(scope="module")
def cache(tmp_path_factory):
    root = tmp_path_factory.mktemp("files")
    (root / "25/Plenum").mkdir(parents=True)
    (root / "25/Plenum/25_ptm_501.doc").write_bytes(docx(TRANSCRIPT))
    return root


def test_sync_and_api(url, cache):
    with psycopg.connect(url) as conn:
        loader = Loader(conn, FixtureSource({"KNS_DocumentPlenumSession": PLENUM_DOCS}))   # (sets autocommit: first)
        assert [c[0] for c in candidates(conn)] == []        # no coalition data in the fixture, so nothing is contested
        assert len(candidates(conn, contested_only=False)) == 1
        assert sync(conn, StubSummarizer(), cache, contested_only=False, loader=loader) == {"pending": 1, "waiting": 0, "stored": 1, "failed": 0}
        assert conn.execute("SELECT knesset_document_id FROM plenum_document").fetchall() == [(501,)]   # not the other sitting's
        assert sync(conn, StubSummarizer(), cache, contested_only=False)["pending"] == 0
        rows = conn.execute("""SELECT s.name_he, p.knesset_person_id, f.knesset_faction_id, s.stages FROM bill_debate_speaker s
                               LEFT JOIN person p ON p.id = s.person_id LEFT JOIN faction f ON f.id = s.faction_id ORDER BY s.ordinal""").fetchall()
        assert rows == [("שמחה רוטמן", 30812, 1105, ["third"]), ("גלעד קריב", 30807, 1100, ["third"]), ("פלוני אלמוני", None, None, ["third"])]
        assert sync_translations(conn, StubTranslator(), ["en"], kinds=["positions"]) == {"en_positions": 3, "en_positions_failed": 0}
    with TestClient(create_app(url)) as client:
        d = client.get(f"/api/v1/bills/{BILL}", params={"lang": "en"}).json()["data"]["debate"]
        assert d["final_vote_id"] == 46699 and d["sources"] == ["https://fs.knesset.gov.il/25/Plenum/25_ptm_501.doc"]
        assert d["summary"]["text"] == StubTranslator.mark(d["summary"]["text_he"], "en") and d["summary"]["text_origin"] == "machine"
        assert [(a["side"], a["speakers"]) for a in d["arguments"]] == [("for", [0]), ("against", [2])]
        kariv = d["speakers"][1]
        assert (kariv["person_id"], kariv["faction_id"], kariv["final_choice"], kariv["final_participation"]) == (30807, 1100, "for", "cast")
        assert kariv["faction_name"] and d["speakers"][2]["person_id"] is None


def test_redo(url, cache):
    """A debate summarised with one list that left a side empty is summarised again and replaced; then left alone."""
    with psycopg.connect(url) as conn:
        assert candidates(conn, contested_only=False, redo=True) == []
        conn.execute("""UPDATE bill_debate SET created_at = '2026-10-08',
                        arguments = jsonb_path_query_array(arguments, '$[*] ? (@.side == "for")')""")
        assert len(candidates(conn, contested_only=False, redo=True)) == 1
        assert sync(conn, StubSummarizer(), cache, contested_only=False, redo=True)["stored"] == 1
        sides = conn.execute("SELECT array_agg(a->>'side') FROM bill_debate, jsonb_array_elements(arguments) a").fetchone()[0]
        assert sorted(sides) == ["against", "for"]
        assert conn.execute("SELECT count(*) FROM bill_debate_speaker").fetchone() == (3,)
        assert candidates(conn, contested_only=False, redo=True) == []


def test_two_lists():
    out = _one_list({"summary": "s", "arguments_for": [{"text": "a", "speeches": [1]}], "arguments_against": [{"text": "b", "speeches": [2]}]})
    assert out == {"summary": "s", "arguments": [{"text": "a", "speeches": [1], "side": "for"}, {"text": "b", "speeches": [2], "side": "against"}]}


def test_waiting_for_a_transcript(new_database):
    url = new_database()
    ingest(url, SLICE)
    with psycopg.connect(url) as conn:
        # a recent vote whose sitting has no transcript yet waits, without an issue; long after, it gets one
        assert sync(conn, StubSummarizer(), None, contested_only=False, today=dt.date(2026, 8, 1)) == {"pending": 1, "waiting": 1, "stored": 0, "failed": 0}
        assert conn.execute("SELECT count(*) FROM data_issue WHERE issue_type = 'debate_failed'").fetchone() == (0,)
        assert sync(conn, StubSummarizer(), None, contested_only=False, today=dt.date(2027, 8, 1)) == {"pending": 1, "waiting": 0, "stored": 0, "failed": 1}
        assert conn.execute("SELECT details->>'reason' FROM data_issue WHERE issue_type = 'debate_failed'").fetchone() == ("transcript_missing",)


def test_turns_kinds():
    assert [t.kind for t in turns("\n".join(TRANSCRIPT[:6]))] == ["topic", "chair", "text", "topic", "speech", "text"]
    assert Turn("topic", "x").text == ""
