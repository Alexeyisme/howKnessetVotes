"""Bill descriptions from the sponsors' explanatory notes (roadmap L7, step 1 where SummaryLaw is missing).

The official SummaryLaw exists only from the 20th Knesset on, and not for every voted bill. Every proposal, though,
ends with explanatory notes ("דברי הסבר") written by its sponsors. For voted bills without SummaryLaw, the proposal
file (KNS_DocumentBill, see Loader.load_documents) is downloaded once, the notes are cut out of it, and the model
writes a short neutral Hebrew description, attributed to the sponsors. It lands in bill_explanation; en/ru/ar come
from hkv.translate (kind "notes"), like every other Hebrew text.

Which file: the sponsors' own proposal, so a private bill's preliminary-reading version (group 1) before the
committee's first-reading version (group 2), which is all a government bill has. Word files are read here; a PDF
(government bills are typeset two-column booklets that text extraction scrambles) goes to the model as a document.
Nothing is silently skipped: a bill whose notes cannot be found or summarised gets an open data_issue
`explanation_failed` with the reason, and is not retried automatically (`--retry-failed` does).
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import time
import urllib.request
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Protocol

import psycopg

from hkv.llm import HEBREW_QUOTES, complete_sentence, gershayim
from hkv.sources.odata import BLOCK_PAGE, USER_AGENT, SourceBlocked, _urlopen

log = logging.getLogger(__name__)

# preliminary, preliminary amended, first reading, first reading amended: the earliest is the sponsors' own text
PROPOSAL_GROUPS = [1, 51, 2, 3]
MODEL = "claude-sonnet-5"
MAX_PDF_BYTES = 25_000_000      # the API takes 32 MB per request, base64 adds a third
MAX_NOTES_CHARS = 60_000        # longer notes (arrangements laws) are cut: the description is a few sentences anyway
FETCH_DELAY_S = 0.3
BATCH_POLL_SECONDS = 60

_HEBREW = re.compile(r"[֐-׿]")
_DIGITS = re.compile(r"\d+")
_NOTES_HEADING = re.compile(r"^[ \t]*דברי[ \t\-–]+(?:ה)?הסבר[ \t]*:?[ \t]*$", re.M)   # 16th Knesset: "דברי - הסבר"
# the notes end where the filing stamp or a separator line starts
_NOTES_END = re.compile(r"^[ \t]*(?:-{5,}|_{5,}|הוגשה ליו\"ר|הונחה על שולחן הכנסת)", re.M)


class NotesError(RuntimeError):
    """Why a bill gets no description; the message is the data_issue reason."""


@dataclass
class Item:
    bill_id: str
    title: str
    document_id: int
    file_sha256: str
    notes: str | None = None     # extracted notes, or None when the model reads the PDF
    pdf: bytes | None = None


# -- files ----------------------------------------------------------------------------------------

def fetch(url: str, cache_dir: Path | None) -> bytes:
    """The file at `url` (fs.knesset.gov.il, through HKV_KNESSET_PROXY when set), kept under cache_dir so a rerun
    does not download it again."""
    path = cache_dir / url.split("fs.knesset.gov.il/", 1)[-1] if cache_dir else None
    if path and path.exists():
        return path.read_bytes()
    time.sleep(FETCH_DELAY_S)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with _urlopen(req, timeout=120) as resp:
        if BLOCK_PAGE in resp.geturl():
            raise SourceBlocked(f"redirected to {resp.geturl()}: {url}")
        data = resp.read()
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return data


def docx_text(data: bytes) -> str:
    """Paragraph text of a .docx (stdlib only: the body is XML in a zip)."""
    xml = zipfile.ZipFile(BytesIO(data)).read("word/document.xml").decode("utf-8")
    paras = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        p = re.sub(r"<w:(?:tab|br)\b[^>]*/>", " ", p)
        paras.append("".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", p)))
    text = "\n".join(x for x in paras if x.strip())
    return re.sub(r"&quot;", '"', re.sub(r"&apos;", "'", re.sub(r"&lt;", "<", re.sub(r"&gt;", ">", text)))).replace("&amp;", "&")


def legacy_doc_text(data: bytes) -> str:
    """Text runs of a Word 97 .doc: Hebrew documents store their text as UTF-16, so runs of Hebrew/ASCII code units
    are the text (field codes and styles are mostly ASCII-only noise that the notes cut drops)."""
    runs = re.findall(rb"(?:[\x20-\x7e\r\n\t]\x00|[\xb0-\xf4]\x05|[\x13-\x14\x1c-\x1f] )+", data)
    return "\n".join(r.decode("utf-16le", "replace") for r in runs if len(r) >= 40).replace("\r", "\n")


def notes_section(text: str) -> str | None:
    """The explanatory notes: from the "דברי הסבר" heading to the filing stamp or a separator line."""
    m = _NOTES_HEADING.search(text)
    if not m:
        return None
    body = text[m.end():]
    end = _NOTES_END.search(body)
    body = (body[:end.start()] if end else body).strip()
    return body if len(body) >= 40 else None


def prepare(bill_id: str, title: str, document_id: int, data: bytes) -> Item:
    """Item for the summariser; NotesError when the file cannot be used."""
    sha = hashlib.sha256(data).hexdigest()
    if data[:4] == b"%PDF":
        if len(data) > MAX_PDF_BYTES:
            raise NotesError("pdf_too_large")
        return Item(bill_id, title, document_id, sha, pdf=data)
    if data[:2] == b"PK":
        text = docx_text(data)
    elif data[:4] == b"\xd0\xcf\x11\xe0":
        text = legacy_doc_text(data)
    else:
        raise NotesError("unsupported_format")
    notes = notes_section(text)
    if notes is None:
        raise NotesError("notes_not_found")
    return Item(bill_id, title, document_id, sha, notes=notes[:MAX_NOTES_CHARS])


# -- the model ------------------------------------------------------------------------------------

SYSTEM = (
    "You write short neutral descriptions of Israeli Knesset bills for a public voting-record website, from the "
    "explanatory notes (דברי הסבר) that the bill's sponsors wrote. Write in Hebrew, two to four sentences, at most "
    "600 characters: what the bill proposes to change, and the reasons the sponsors give for it, attributed to them "
    "(\"לדברי המציעים\", \"לפי דברי ההסבר\"). Use only what the notes say: no outside facts, no evaluation, no "
    "adjectives the notes do not support, no names of Knesset members. Keep numbers as digits, exactly as in the "
    "notes. Dates: only the Gregorian date, never the Hebrew calendar. When the document holds several bills or the "
    "full text of the bill as well, describe only the bill with the given title, from its explanatory notes. If the "
    "document has no explanatory notes for that bill, set found to false and leave the description empty. "
    + HEBREW_QUOTES
)
OUTPUT_FORMAT = {"format": {"type": "json_schema", "schema": {
    "type": "object",
    "properties": {"found": {"type": "boolean"}, "description": {"type": "string"}},
    "required": ["found", "description"], "additionalProperties": False,
}}}


class Summarizer(Protocol):
    model: str

    def summarize(self, item: Item) -> str | None: ...


class StubSummarizer:
    """For tests: a Hebrew marker that passes the checks, with the notes' first number."""

    model = "stub"

    def summarize(self, item: Item) -> str | None:
        digits = _DIGITS.findall(item.notes or "")[:1]
        return "לדברי המציעים, ההצעה נועדה לשנות את החוק" + "".join(f" ({d})" for d in digits) + "."


class ClaudeSummarizer:
    """One request per bill; `summarize_many` sends a backlog as one Message Batch (half price)."""

    def __init__(self, model: str | None = None):
        import anthropic  # imported here so the API and tests do not need the package

        self.client = anthropic.Anthropic()
        self.model = model or MODEL

    def _params(self, item: Item) -> dict:
        content: list[dict] = []
        if item.pdf is not None:
            content.append({"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                                           "data": base64.standard_b64encode(item.pdf).decode("ascii")}})
            content.append({"type": "text", "text": gershayim(f"The bill: {item.title}")})
        else:
            content.append({"type": "text", "text": gershayim(f"The bill: {item.title}\n\nExplanatory notes:\n{item.notes}")})
        return dict(model=self.model, max_tokens=4000, thinking={"type": "disabled"},
                    system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
                    messages=[{"role": "user", "content": content}], output_config=OUTPUT_FORMAT)

    @staticmethod
    def _parse(message) -> str | None:
        if message.stop_reason == "refusal":
            raise RuntimeError(f"refused: {message.stop_details}")
        out = json.loads(next(b.text for b in message.content if b.type == "text"))
        return out["description"].strip() if out["found"] else None

    def summarize(self, item: Item) -> str | None:
        return self._parse(self.client.messages.create(**self._params(item)))

    def summarize_many(self, items: Sequence[Item]) -> list[str | None | Exception]:
        batch = self.client.messages.batches.create(requests=[
            {"custom_id": str(i), "params": self._params(it)} for i, it in enumerate(items)])
        log.info("message batch %s: %d bills", batch.id, len(items))
        while batch.processing_status != "ended":
            time.sleep(BATCH_POLL_SECONDS)
            batch = self.client.messages.batches.retrieve(batch.id)
            c = batch.request_counts
            log.info("message batch %s: %d processing, %d succeeded, %d errored", batch.id, c.processing, c.succeeded, c.errored)
        out: list[str | None | Exception] = [RuntimeError("missing from batch")] * len(items)
        for r in self.client.messages.batches.results(batch.id):
            i = int(r.custom_id)
            try:
                if r.result.type != "succeeded":
                    raise RuntimeError(f"batch request {r.result.type}")
                out[i] = self._parse(r.result.message)
            except Exception as e:
                out[i] = e
        return out


def check(item: Item, text: str) -> str | None:
    """Why a description must not be stored, or None. It must be Hebrew prose of sane length, and (when we have the
    notes as text) every number in it must appear in the title or the notes: a made-up number is the likeliest
    factual error, and the cheapest to catch."""
    if not text or len(text) < 40:
        return "too_short"
    if len(text) > 1000:
        return "too_long"
    if len(_HEBREW.findall(text)) < len(text) / 3:
        return "not_hebrew"
    if not complete_sentence(text):
        return "cut_off"
    if item.notes is not None:
        source = set(_DIGITS.findall(item.title + " " + item.notes.replace(",", "")))
        missing = [d for d in _DIGITS.findall(text.replace(",", "")) if d not in source]
        if missing:
            return f"numbers_not_in_notes:{','.join(missing)}"
    return None


# -- the job --------------------------------------------------------------------------------------

def candidates(conn: psycopg.Connection, limit: int | None = None, retry_failed: bool = False, contested_only: bool = False,
               since=None) -> list[tuple]:
    """(bill id, title, document id, url) for voted bills without an official summary or a description, most recently
    voted first, with the sponsors' proposal file: the earliest proposal group, Word before PDF. `contested_only`:
    bills whose final vote split the coalition and the opposition (as hkv.debate); `since`: bills voted on or after
    that date (the daily update describes new bills only; the backlog is a manual batch)."""
    return conn.execute(
        """SELECT b.id, b.title_he, d.knesset_document_id, d.url
           FROM bill b
           JOIN LATERAL (SELECT max(v.occurred_on) AS last FROM vote_subject vs JOIN vote v ON v.id = vs.vote_id
                         WHERE vs.bill_id = b.id) lv ON lv.last IS NOT NULL
           JOIN LATERAL (SELECT * FROM bill_document d WHERE d.bill_id = b.id AND d.group_type_id = ANY(%(groups)s)
                           AND d.format IN ('DOC', 'PDF')
                         ORDER BY array_position(%(groups)s, d.group_type_id), d.format = 'PDF', d.knesset_document_id
                         LIMIT 1) d ON true
           WHERE coalesce(b.summary_he, '') = ''
             AND NOT EXISTS (SELECT 1 FROM bill_explanation e WHERE e.bill_id = b.id)
             AND (%(since)s::date IS NULL OR lv.last >= %(since)s::date)
             AND (NOT %(contested)s OR EXISTS (
                   SELECT 1 FROM vote_subject vs JOIN vote v ON v.id = vs.vote_id JOIN vote_bloc vb ON vb.vote_id = v.id AND vb.contested
                   LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
                   WHERE vs.bill_id = b.id AND v.status = 'valid'
                     AND coalesce(k.motion_type, v.motion_type) = 'adopt_bill' AND coalesce(k.stage, v.stage) = 'third'))
             AND (%(retry)s OR NOT EXISTS (SELECT 1 FROM data_issue i WHERE i.issue_type = 'explanation_failed'
                                           AND i.status = 'open' AND i.entity_id = b.id))
           ORDER BY lv.last DESC""" + (" LIMIT %(limit)s" if limit else ""),
        {"groups": PROPOSAL_GROUPS, "retry": retry_failed, "limit": limit, "contested": contested_only, "since": since}).fetchall()


def _fail(conn: psycopg.Connection, bill_id, reason: str, **details) -> None:
    """One open issue per bill, updated with the latest reason."""
    payload = json.dumps({"reason": reason, **details}, ensure_ascii=False, default=str)
    if not conn.execute("""UPDATE data_issue SET details = %s WHERE issue_type = 'explanation_failed' AND status = 'open'
                           AND entity_id = %s""", (payload, bill_id)).rowcount:
        conn.execute("""INSERT INTO data_issue (entity_table, entity_id, issue_type, severity, details)
                        VALUES ('bill', %s, 'explanation_failed', 'warning', %s)""", (bill_id, payload))


def sync(conn: psycopg.Connection, summarizer: Summarizer, cache_dir: Path | None = None, limit: int | None = None,
         retry_failed: bool = False, batch: bool = False, contested_only: bool = False, since=None) -> dict[str, int]:
    """Describe the bills that need it. Files are fetched first; with `batch` (and a summariser that has
    `summarize_many`) all requests then go as one Message Batch, otherwise one by one."""
    counts = {"pending": 0, "stored": 0, "failed": 0}
    items: list[Item] = []
    for bill_id, title, doc_id, url in candidates(conn, limit, retry_failed, contested_only, since):
        counts["pending"] += 1
        try:
            items.append(prepare(bill_id, title, doc_id, fetch(url, cache_dir)))
        except SourceBlocked:
            raise
        except NotesError as e:
            _fail(conn, bill_id, str(e), document=doc_id, url=url)
            counts["failed"] += 1
        except Exception as e:  # a missing or broken file: recorded, the rest goes on
            _fail(conn, bill_id, "fetch_failed", document=doc_id, url=url, error=repr(e)[:500])
            counts["failed"] += 1
        conn.commit()
    log.info("explanations: %d pending, %d files ready (%d PDF)", counts["pending"], len(items), sum(i.pdf is not None for i in items))
    if batch and items and hasattr(summarizer, "summarize_many"):
        results = summarizer.summarize_many(items)
    else:
        results = []
        for it in items:
            try:
                results.append(summarizer.summarize(it))
            except Exception as e:
                log.warning("explanation failed for %s", it.title[:80], exc_info=True)
                results.append(e)
    for it, text in zip(items, results, strict=True):
        why = ("model_error:" + repr(text)[:300] if isinstance(text, Exception)
               else "no_notes_in_document" if text is None else check(it, text))
        if why:
            _fail(conn, it.bill_id, why, document=it.document_id, description=None if isinstance(text, Exception) else text)
            counts["failed"] += 1
        else:
            conn.execute("""INSERT INTO bill_explanation (bill_id, document_id, file_sha256, notes_he, summary_he, model)
                            VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (bill_id) DO NOTHING""",
                         (it.bill_id, it.document_id, it.file_sha256, it.notes, text, summarizer.model))
            conn.execute("""UPDATE data_issue SET status = 'resolved', resolved_at = now()
                            WHERE issue_type = 'explanation_failed' AND status = 'open' AND entity_id = %s""", (it.bill_id,))
            counts["stored"] += 1
        conn.commit()
    log.info("explanations: %s", counts)
    return counts
