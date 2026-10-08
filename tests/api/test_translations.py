"""Title and summary translations (R4, L7): the sync stores what passes the checks, the API serves them per ?lang=,
search finds bills by their translated title, and visitors can file a correction (never applied)."""

from __future__ import annotations

import json

import psycopg
import pytest
from fastapi.testclient import TestClient

from hkv.api.app import create_app
from hkv.translate import BATCH, StubTranslator, check, pending, recheck_failed, sha256, sync
from tests.ingest.test_loader import SLICE, ingest

BILL = 2229019
TITLE = next(b["Name"] for b in SLICE["KNS_Bill"] if b["Id"] == BILL)


MARK = StubTranslator.mark(TITLE, "en")


class NumberDropper(StubTranslator):
    """Drops digits, so every title with a number fails the check."""

    def translate(self, titles, lang, kind="title"):
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
    # summaries: a numeric date keeps its day and year, the month becomes a word
    assert check("החל מיום 03.07.2026", "from 3 July 2026", "summary") is None
    assert check("שהחלה ב1.9.2025", "that began on 1 September 2025", "summary") is None
    assert check("עד ה-31.03, ומה-07 באוקטובר", "by 31 March, and from 7 October", "summary") is None
    assert check("קנס בסך 1000 ₪", "a fine of NIS 1,000", "summary") is None
    assert check("קנס בסך 6000 ₪", "штраф 6 000 шекелей", "summary") is None
    assert check("סעיף 14טו וסעיף 406(ה)", "Section 14טו and Section 406(ה)", "summary") is None
    assert check("ארגון איחוד הצלה", "منظمة إيחוד הצלה", "summary") == "hebrew_left"
    assert check("פי 1.25", "multiplied by 1", "summary") == "numbers_missing:25"   # a decimal is not a date
    assert check("סעיף 14טו", "Section 14טו") == "hebrew_left"                       # titles stay strict
    assert check("החל מיום 1.4.2026", "from April 2026", "summary") == "numbers_missing:1"
    assert check("החל מיום 1.4.2026", "from 1 April 2026") == "numbers_missing:4"


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
        # failed titles are not sent again on the next (scheduled) run, only with retry_failed; no duplicate issues
        assert pending(conn, "ru") == []
        assert sync(conn, NumberDropper(), ["ru"])["ru_failed"] == 0
        assert sync(conn, NumberDropper(), ["ru"], retry_failed=True)["ru_failed"] == issues
        assert conn.execute("SELECT count(*) FROM data_issue WHERE issue_type = 'translation_check_failed'").fetchone()[0] == issues
        # a retry that passes stores the translation and resolves the issue
        counts = sync(conn, StubTranslator(), ["ru"], retry_failed=True)
        assert counts["ru"] == issues and counts["ru_failed"] == 0
        assert conn.execute("""SELECT count(*) FROM data_issue WHERE issue_type = 'translation_check_failed'
                               AND status = 'open'""").fetchone()[0] == 0


class OneTooMany(StubTranslator):
    """Returns an extra item for batches of more than one title, like the model sometimes does."""

    def translate(self, titles, lang, kind="title"):
        out = super().translate(titles, lang)
        if len(titles) > 1:
            raise RuntimeError(f"expected {len(titles)} translations, got {len(out) + 1}")
        return out


def test_model_per_language(monkeypatch):
    from hkv.translate import model_for
    monkeypatch.delenv("HKV_TRANSLATE_MODEL", raising=False)
    assert model_for("ar") == "claude-sonnet-5" and model_for("en") == "claude-haiku-4-5-20251001"
    monkeypatch.setenv("HKV_TRANSLATE_MODEL_AR", "x")
    assert model_for("ar") == "x"
    # summaries: Sonnet in every language, whatever the title models are
    monkeypatch.setenv("HKV_TRANSLATE_MODEL", "haiku")
    assert model_for("en", "summary") == model_for("ar", "summary") == "claude-sonnet-5"


def test_since_keeps_recent_titles(url):
    with psycopg.connect(url) as conn:
        assert len(pending(conn, "ar", since="2100-01-01")) == 0
        assert 0 < len(pending(conn, "ar", since="2026-07-01")) <= len(pending(conn, "ar"))


def test_failed_batch_is_retried_title_by_title(url):
    with psycopg.connect(url) as conn:
        todo = len(pending(conn, "ar"))
        assert todo >= 2
        assert sync(conn, OneTooMany(), ["ar"], kinds=["title"]) == {"ar": todo, "ar_failed": 0}


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


def test_mistake_report_is_forwarded(client, url, monkeypatch):
    """A report without a source hash is stored with its contact and sent to the owner's chat; a bot's is not."""
    sent: list[str] = []
    monkeypatch.setattr("hkv.api.suggestions.notify", sent.append)
    body = {"language": "he", "suggested_text": "המספר בתקציר שגוי", "contact": " me@example.org ", "page": "/he/bills/1"}
    assert client.post("/api/v1/suggestions", json=body).status_code == 201
    with psycopg.connect(url) as conn:
        assert conn.execute("SELECT source_sha256, contact FROM translation_suggestion WHERE language = 'he'").fetchone() == (None, "me@example.org")
    assert len(sent) == 1
    assert "Message to the author (he)" in sent[0] and "https://knessetvotes.org/he/bills/1" in sent[0]
    assert "המספר בתקציר שגוי" in sent[0] and "Contact: me@example.org" in sent[0]
    assert client.post("/api/v1/suggestions", json={**body, "website": "spam"}).status_code == 201
    assert len(sent) == 1
    fix = {"source_sha256": sha256(TITLE), "language": "en", "suggested_text": "Better title"}
    assert client.post("/api/v1/suggestions", json=fix).status_code == 201
    assert "Translation correction (en)" in sent[1] and f"Current translation:\n{MARK}" in sent[1]


SUMMARY = "החוק מאריך את הוראת השעה בשנה וחצי, עד 31 בדצמבר 2026."


class KindRecorder(StubTranslator):
    """Remembers which kind of text each batch was sent as."""

    def __init__(self):
        self.kinds = []

    def translate(self, titles, lang, kind="title"):
        self.kinds.append((kind, len(titles)))
        return super().translate(titles, lang, kind)


def test_summaries(url):
    with TestClient(create_app(url)) as client, psycopg.connect(url) as conn:
        conn.execute("UPDATE bill SET summary_he = %s WHERE knesset_bill_id = %s", (SUMMARY, BILL))
        conn.commit()
        assert pending(conn, "en", kind="summary") == [(sha256(SUMMARY), SUMMARY)]
        tr = KindRecorder()
        counts = sync(conn, tr, ["en"], kinds=["summary"])
        assert counts == {"en_summary": 1, "en_summary_failed": 0} and tr.kinds == [("summary", 1)]
        assert pending(conn, "en", kind="summary") == []
        b = client.get(f"/api/v1/bills/{BILL}", params={"lang": "en"}).json()["data"]
        assert b["summary_he"] == SUMMARY
        assert b["summary"] == StubTranslator.mark(SUMMARY, "en") == b["summary_en"] and b["summary_origin"] == "machine"
        assert client.get(f"/api/v1/bills/{BILL}").json()["data"]["summary"] is None
        assert client.get(f"/api/v1/bills/{BILL}", params={"lang": "ru"}).json()["data"]["summary"] is None


class BatchStub(StubTranslator):
    """A Message Batch where the second request errored: that chunk must be sent again directly."""

    def __init__(self):
        self.direct = 0

    def translate_many(self, jobs):
        return [None if i == 1 else self.translate(texts, lang, kind) for i, (lang, kind, texts) in enumerate(jobs)]

    def translate(self, titles, lang, kind="title"):
        self.direct += 1
        return super().translate(titles, lang, kind)


def test_batch_mode(url, monkeypatch):
    monkeypatch.setitem(BATCH, "title", 1)
    with psycopg.connect(url) as conn:
        conn.execute("DELETE FROM text_translation WHERE language = 'ar'")
        conn.commit()
        todo = len(pending(conn, "ar"))
        assert todo > BATCH["title"]   # at least two chunks, so one can fail
        tr = BatchStub()
        assert sync(conn, tr, ["ar"], kinds=["title"], batch=True) == {"ar": todo, "ar_failed": 0}
        assert pending(conn, "ar") == []


def test_claude_params_turn_thinking_off():
    from hkv.translate import ClaudeTranslator
    tr = ClaudeTranslator.__new__(ClaudeTranslator)
    tr.fixed_model = None
    assert tr._params(["x"], "en", "summary")["thinking"] == {"type": "disabled"}
    tr.fixed_model = "claude-haiku-4-5-20251001"
    assert "thinking" not in tr._params(["x"], "en", "title")


def test_recheck_stores_what_passes_relaxed_checks(url):
    with psycopg.connect(url) as conn:
        h = sha256("קנס בסך 1000 ₪")
        for src, target, ref in (("קנס בסך 1000 ₪", "a fine of NIS 1,000", h), ("קנס בסך 7 ₪", "a fine of NIS seven", sha256("x"))):
            conn.execute("""INSERT INTO data_issue (external_ref, issue_type, severity, details)
                            VALUES (%s, 'translation_check_failed', 'warning', %s)""",
                         (ref, json.dumps({"language": "en", "kind": "summary", "reason": "numbers_missing", "source": src,
                                           "target": target, "model": "m"})))
        conn.commit()
        assert recheck_failed(conn)["stored"] == 1
        assert conn.execute("SELECT text, model FROM text_translation WHERE source_sha256 = %s AND language = 'en'", (h,)).fetchone() == ("a fine of NIS 1,000", "m")
        assert conn.execute("SELECT status FROM data_issue WHERE external_ref = %s", (h,)).fetchone()[0] == "resolved"
        assert conn.execute("SELECT status FROM data_issue WHERE external_ref = %s", (sha256("x"),)).fetchone()[0] == "open"


def test_turnstile_and_per_visitor_limit(client, url, monkeypatch):
    """With a Turnstile secret, a message needs a token Cloudflare accepts; the daily limit counts X-Real-IP."""
    import io

    monkeypatch.setattr("hkv.api.suggestions.notify", lambda text: None)
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "test-secret")
    seen: list[bytes] = []

    def fake_urlopen(req_url, data=None, timeout=None):
        seen.append(data)
        return io.BytesIO(json.dumps({"success": b"response=good" in data}).encode())

    monkeypatch.setattr("hkv.api.suggestions.urllib.request.urlopen", fake_urlopen)
    body = {"language": "ru", "suggested_text": "Спасибо за сайт"}
    assert client.post("/api/v1/suggestions", json=body).status_code == 403                                  # no token
    assert client.post("/api/v1/suggestions", json={**body, "turnstile_token": "bad"}).status_code == 403
    assert client.post("/api/v1/suggestions", json={**body, "turnstile_token": "good"},
                       headers={"X-Real-IP": "203.0.113.7"}).status_code == 201
    assert b"remoteip=203.0.113.7" in seen[-1] and b"secret=test-secret" in seen[-1]

    monkeypatch.delenv("TURNSTILE_SECRET_KEY")
    with psycopg.connect(url) as conn:
        conn.execute("DELETE FROM translation_suggestion")
    a, b = {"X-Real-IP": "198.51.100.1"}, {"X-Real-IP": "198.51.100.2"}
    for _ in range(20):
        assert client.post("/api/v1/suggestions", json=body, headers=a).status_code == 201
    assert client.post("/api/v1/suggestions", json=body, headers=a).status_code == 429
    assert client.post("/api/v1/suggestions", json=body, headers=b).status_code == 201   # another visitor is not blocked
