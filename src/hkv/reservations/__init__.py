"""Objections: the reservations filed for the second reading of a bill (roadmap L7, step 3).

The committee's version of a bill for the second and third reading (KNS_DocumentBill group 4, "פונץ' בננה" 101, or
a re-tabled version 46/49/103/104) ends with "הסתייגויות ובקשות רשות דיבור": numbered changes members propose to
each section, under who proposes them ("קבוצת יש עתיד מציעה:", "חבר הכנסת גלעד קריב מציע:", sometimes several
groups jointly), and the members who asked to speak. They are legal edits, not reasons, so the page shows who filed
how many on which sections plus a one-sentence gist per proposer, not a debate.

The formats differ between Knessets (groups defined up front in the 25th, "(להלן – קבוצת …)" inline before it,
alternatives "לחלופין", reservations to sections that do not exist yet "לאחרי סעיף 11"), so the model reads the
section and says which numbers belong to whom. The job then checks what can be checked against the text: the
numbers it assigned must be exactly the numbered reservations printed (no gap, no overlap, no extra), and every
member it names must appear in the text. Some PDFs give no usable numbers as text (automatic list numbering, or
lines extracted in reverse word order); then the model reads the reservation pages of the PDF itself, the numbers
are only checked for consistency (1..N, no gap, no overlap), and the row says so (numbers_checked = false). Members are resolved to their faction on the date of the final vote
(hkv.people). A bill that fails gets an open data_issue `reservations_failed` (retried with `--retry-failed`).
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Protocol

import psycopg

from hkv.debate import FINAL_VOTE
from hkv.llm import HEBREW_QUOTES, complete_sentence, gershayim
from hkv.notes import docx_text, fetch, legacy_doc_text
from hkv.people import Roster
from hkv.sources.odata import SourceBlocked
from hkv.topics import he_norm

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-5"
# committee versions; a re-tabled one (הנחה מחדש) replaces the first, so the latest document wins
VERSION_GROUPS = [4, 101, 46, 49, 103, 104]
MAX_CHARS = 300_000          # the reservations section sent to the model; longer ones (arrangements laws) fail as too_long
MAX_PDF_PAGES = 90           # the API reads at most 100 PDF pages per request

_HEBREW = re.compile(r"[֐-׿]")
_START = re.compile(r"הסתייגויות\s*ובקשות\s*רשות\s*דיבור")
_START_REVERSED = re.compile(r"דיבור\s*רשות\s*ובקשות\s*הסתייגויות")   # PDFs extracted in visual order
_SPEAK = re.compile(r"^\s*בקשות\s*רשות\s*דיבור\s*$", re.M)
_NUMBERED = re.compile(r"^\s*(\d{1,4})\s*\.(?!\d)", re.M)
_PROPOSES = re.compile(r"מציע(?:ה|ים|ות)?\b")   # "קבוצת יש עתיד מציעה:"; reversed lines keep their words


class ReservationsError(RuntimeError):
    """Why a bill gets no reservations; the message is the data_issue reason."""


def document_text(data: bytes) -> str:
    if data[:4] == b"%PDF":
        from pypdf import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages)
    if data[:2] == b"PK":
        return docx_text(data)
    if data[:4] == b"\xd0\xcf\x11\xe0":
        return legacy_doc_text(data)
    raise ReservationsError("unsupported_format")


def section_pages(data: bytes) -> tuple[bytes, str] | None:
    """The PDF pages from the last reservations heading to the end, as a PDF of their own, and their text."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(BytesIO(data))
    texts = [page.extract_text() or "" for page in reader.pages]
    starts = [i for i, t in enumerate(texts) if _START.search(t) or _START_REVERSED.search(t)]
    if not starts:
        return None
    if len(texts) - starts[-1] > MAX_PDF_PAGES:
        raise ReservationsError("too_long")
    writer = PdfWriter()
    for page in reader.pages[starts[-1]:]:
        writer.add_page(page)
    out = BytesIO()
    writer.write(out)
    return out.getvalue(), "\n".join(texts[starts[-1]:])


def section(text: str) -> str | None:
    """From the last "הסתייגויות ובקשות רשות דיבור" heading to the end (a table of contents may name it earlier)."""
    starts = list(_START.finditer(text))
    return text[starts[-1].start():].strip() if starts else None


def numbered(sec: str) -> list[int]:
    """The reservation numbers printed before the speaking requests (the line-initial "12." of each item), in order."""
    m = _SPEAK.search(sec)
    body = sec[:m.start()] if m else sec
    return [int(n) for n in _NUMBERED.findall(body)]


def expected_numbers(sec: str) -> set[int]:
    """1..N where N is the highest printed number that continues the sequence (quoted sub-items like "(1)" are not
    line-initial "N.", and a stray "2." inside a quoted text cannot extend the run past the real last item)."""
    seen, n = set(numbered(sec)), 0
    while n + 1 in seen:
        n += 1
    return set(range(1, n + 1))


# -- the model ------------------------------------------------------------------------------------

SYSTEM = (
    "You read the reservations section (הסתייגויות ובקשות רשות דיבור) of an Israeli Knesset bill's committee version "
    "for the second and third reading, for a public, non-partisan voting-record website. Extract:\n"
    "proposers: everyone who proposes reservations, as the document names them. A group (\"קבוצת יש עתיד\") with its "
    "members as listed; a single member (\"חבר הכנסת גלעד קריב\") as a proposer whose label is the name and whose "
    "members are just that name. Names exactly as printed, without titles (no חבר הכנסת, השר).\n"
    "blocks: consecutive numbered reservations with the same proposers: the proposer labels, the section heading "
    "they fall under as printed (\"לסעיף 1\", \"לפני סעיף 1\", \"לאחרי סעיף 11\"), and the first and last reservation "
    "number, in the order they appear; every printed number belongs to exactly one block. Joint reservations list every proposer. Unnumbered alternatives (\"לחלופין\") belong to the block before. "
    "If the document does not number its reservations at all, give each reservation as its own block with first and "
    "last 0.\n"
    "speak_requests: the members who asked to speak, names as printed (empty if \"אין\").\n"
    "summary: in Hebrew, one or two neutral sentences on what the reservations as a whole sought to change; empty if "
    "there are none.\n"
    "gists: for each proposer, one neutral Hebrew sentence on what its reservations would change. Describe, do not "
    "judge; keep numbers as digits as printed. " + HEBREW_QUOTES
)
SCHEMA = {
    "type": "object",
    "properties": {
        "proposers": {"type": "array", "items": {
            "type": "object",
            "properties": {"label": {"type": "string"}, "members": {"type": "array", "items": {"type": "string"}},
                           "gist": {"type": "string"}},
            "required": ["label", "members", "gist"], "additionalProperties": False}},
        "blocks": {"type": "array", "items": {
            "type": "object",
            "properties": {"proposers": {"type": "array", "items": {"type": "string"}}, "section": {"type": "string"},
                           "first": {"type": "integer"}, "last": {"type": "integer"}},
            "required": ["proposers", "section", "first", "last"], "additionalProperties": False}},
        "speak_requests": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
    "required": ["proposers", "blocks", "speak_requests", "summary"], "additionalProperties": False,
}


@dataclass
class Item:
    bill_id: object
    title: str
    document_id: int
    file_sha256: str
    text: str                    # the section as text (for the checks; for the model too unless pdf)
    numbers_checked: bool        # the text has the printed numbers
    pdf: bytes | None = None     # the section's pages, when the text has no usable numbers

    def prompt(self) -> str | list:
        if self.pdf is None:
            return gershayim(f"The bill: {self.title}\n\n{self.text}")
        return [{"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                                "data": base64.standard_b64encode(self.pdf).decode("ascii")}},
                {"type": "text", "text": gershayim(f"The bill: {self.title}\n\nThe pages above are the reservations section.")}]


class Extractor(Protocol):
    model: str

    def extract(self, item: Item) -> dict: ...


class StubExtractor:
    """For tests: every printed reservation to one proposer named after the first "חבר הכנסת X מציע" in the text."""

    model = "stub"

    def extract(self, item: Item) -> dict:
        m = re.search(r"חבר(?:ת)? הכנסת\s+(\S+ \S+)\s+מציע", item.text)
        nums = sorted(expected_numbers(item.text)) or ([0] if m else [])
        if not nums or not m:
            return {"proposers": [], "blocks": [], "speak_requests": [], "summary": ""}
        return {"proposers": [{"label": m[1], "members": [m[1]], "gist": "מוצע לשנות את ההגדרות בחוק."}],
                "blocks": [{"proposers": [m[1]], "section": "לסעיף 1", "first": nums[0], "last": nums[-1]}],
                "speak_requests": [], "summary": "ההסתייגויות מבקשות לצמצם את תחולת החוק."}


class ClaudeExtractor:
    def __init__(self, model: str | None = None):
        from hkv.llm import JsonModel

        self.llm = JsonModel(model or MODEL, SYSTEM, SCHEMA, max_tokens=16000)
        self.model = self.llm.model

    def extract(self, item: Item) -> dict:
        return self.llm.ask(item.prompt())

    def extract_many(self, items: Sequence[Item]) -> list[dict | Exception]:
        return self.llm.ask_many([it.prompt() for it in items])


def _squash(s: str) -> str:
    return he_norm(s).replace(" ", "")


def _hebrew_prose(text: str, lo: int, hi: int) -> bool:
    return lo <= len(text) <= hi and len(_HEBREW.findall(text)) >= len(text) / 3


def merge_proposers(out: dict) -> dict:
    """The same proposer listed twice (the model repeats a label it met again further down) becomes one, with the
    members of both."""
    merged: dict[str, dict] = {}
    for p in out.get("proposers") or []:
        if p["label"] in merged:
            m = merged[p["label"]]
            m["members"] = list(dict.fromkeys([*m["members"], *p["members"]]))
            m["gist"] = m.get("gist") or p.get("gist")
        else:
            merged[p["label"]] = {**p, "members": list(p["members"])}
    return {**out, "proposers": list(merged.values())}


def check(item: Item, out: dict) -> str | None:
    """Why the extraction must not be stored, or None. Blocks numbered 0 are reservations printed without a number
    (all of them in some documents, a "לאחרי סעיף 11" addition in others); the numbered ones are checked."""
    proposers, blocks = out.get("proposers") or [], out.get("blocks") or []
    labels = [p["label"] for p in proposers]
    if len(set(labels)) != len(labels):
        return "duplicate_proposer"
    for b in blocks:
        if not b["proposers"] or any(p not in labels for p in b["proposers"]):
            return "unknown_proposer_in_block"
        if b["first"] > b["last"] or b["first"] < 0 or (b["first"] == 0 < b["last"]):
            return "bad_range"
    numbered = [b for b in blocks if b["last"]]
    got = [n for b in numbered for n in range(b["first"], b["last"] + 1)]
    if not blocks and _PROPOSES.search(item.text):
        return "no_reservations_extracted"
    if len(got) != len(set(got)):
        return "overlapping_numbers"
    if item.numbers_checked:
        expected = expected_numbers(item.text)
        if set(got) != expected:
            return f"numbers_mismatch:{len(set(got))}/{len(expected)}"
    elif got and set(got) != set(range(1, max(got) + 1)):
        return "numbers_not_contiguous"
    if blocks and not numbered and not _PROPOSES.search(item.text):
        return "unnumbered_without_proposal"
    squashed, words = _squash(item.text), set(re.findall(r"\w+", he_norm(item.text)))
    names = [n for p in proposers for n in p["members"]] + list(out.get("speak_requests") or [])
    absent = [n for n in names if not n.strip() or (_squash(n) not in squashed and not set(re.findall(r"\w+", he_norm(n))) <= words)]
    if absent:
        return f"name_not_in_text:{absent[0][:40]}"
    if blocks:
        if not _hebrew_prose((out.get("summary") or "").strip(), 20, 600):
            return "bad_summary"
        if not complete_sentence(out["summary"]):
            return "summary_cut_off"
        used = {p for b in blocks for p in b["proposers"]}
        if any(p["label"] in used and not _hebrew_prose((p.get("gist") or "").strip(), 10, 400) for p in proposers):
            return "bad_gist"
        if any(p["label"] in used and not complete_sentence(p["gist"]) for p in proposers):
            return "gist_cut_off"
    return None


# -- the job --------------------------------------------------------------------------------------

def candidates(conn: psycopg.Connection, limit: int | None = None, retry_failed: bool = False,
               contested_only: bool = True) -> list[tuple]:
    """(bill id, title, final vote date, document id, url) of bills with a final vote and a committee version but no
    reservations yet, most recent first; by default only where the final vote was contested."""
    return conn.execute(
        f"""SELECT b.id, b.title_he, fv.occurred_on, d.knesset_document_id, d.url
            FROM bill b
            JOIN LATERAL (SELECT v.occurred_on, vb.contested FROM vote v JOIN vote_subject vs ON vs.vote_id = v.id
                          LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
                          LEFT JOIN vote_bloc vb ON vb.vote_id = v.id
                          WHERE vs.bill_id = b.id AND {FINAL_VOTE} AND v.status = 'valid'
                          ORDER BY v.occurred_on DESC LIMIT 1) fv ON true
            JOIN LATERAL (SELECT * FROM bill_document d WHERE d.bill_id = b.id AND d.group_type_id = ANY(%(groups)s)
                            AND d.format IN ('PDF', 'DOC')
                          ORDER BY d.knesset_document_id DESC, d.format = 'DOC' LIMIT 1) d ON true
            WHERE (NOT %(contested)s OR fv.contested)
              AND NOT EXISTS (SELECT 1 FROM bill_reservations r WHERE r.bill_id = b.id)
              AND (%(retry)s OR NOT EXISTS (SELECT 1 FROM data_issue i WHERE i.issue_type = 'reservations_failed'
                                            AND i.status = 'open' AND i.entity_id = b.id))
            ORDER BY fv.occurred_on DESC, b.id""" + (" LIMIT %(limit)s" if limit else ""),
        {"groups": VERSION_GROUPS, "retry": retry_failed, "limit": limit, "contested": contested_only}).fetchall()


def _fail(conn: psycopg.Connection, bill_id, reason: str, **details) -> None:
    payload = json.dumps({"reason": reason, **details}, ensure_ascii=False, default=str)
    if not conn.execute("""UPDATE data_issue SET details = %s WHERE issue_type = 'reservations_failed' AND status = 'open'
                           AND entity_id = %s""", (payload, bill_id)).rowcount:
        conn.execute("""INSERT INTO data_issue (entity_table, entity_id, issue_type, severity, details)
                        VALUES ('bill', %s, 'reservations_failed', 'warning', %s)""", (bill_id, payload))


def prepare(bill_id, title: str, document_id: int, data: bytes) -> Item:
    sha = hashlib.sha256(data).hexdigest()
    sec = section(document_text(data))
    if sec is not None and (expected_numbers(sec) or not _PROPOSES.search(sec)):   # numbered, or none filed
        if len(sec) > MAX_CHARS:
            raise ReservationsError("too_long")
        return Item(bill_id, title, document_id, sha, sec, numbers_checked=True)
    if data[:4] == b"%PDF":
        pages = section_pages(data)
        if pages is None:
            raise ReservationsError("section_not_found")
        return Item(bill_id, title, document_id, sha, pages[1], numbers_checked=False, pdf=pages[0])
    if sec is None:
        raise ReservationsError("section_not_found")
    if len(sec) > MAX_CHARS:
        raise ReservationsError("too_long")
    return Item(bill_id, title, document_id, sha, sec, numbers_checked=False)


def sync(conn: psycopg.Connection, extractor: Extractor, cache_dir: Path | None = None, limit: int | None = None,
         retry_failed: bool = False, batch: bool = False, contested_only: bool = True) -> dict[str, int]:
    counts = {"pending": 0, "stored": 0, "failed": 0}
    items: list[tuple[Item, object]] = []
    for bill_id, title, on, doc_id, url in candidates(conn, limit, retry_failed, contested_only):
        counts["pending"] += 1
        try:
            items.append((prepare(bill_id, title, doc_id, fetch(url, cache_dir)), on))
        except SourceBlocked:
            raise
        except ReservationsError as e:
            _fail(conn, bill_id, str(e), document=doc_id, url=url)
            counts["failed"] += 1
        except Exception as e:
            _fail(conn, bill_id, "fetch_failed", document=doc_id, url=url, error=repr(e)[:500])
            counts["failed"] += 1
        conn.commit()
    log.info("reservations: %d pending, %d documents ready", counts["pending"], len(items))
    if batch and items and hasattr(extractor, "extract_many"):
        results = extractor.extract_many([it for it, _ in items])
    else:
        results = []
        for it, _ in items:
            try:
                results.append(extractor.extract(it))
            except Exception as e:
                log.warning("reservations failed for %s", it.title[:80], exc_info=True)
                results.append(e)
    for (it, on), out in zip(items, results, strict=True):
        out = out if isinstance(out, Exception) else merge_proposers(out)
        why = "model_error:" + repr(out)[:300] if isinstance(out, Exception) else check(it, out)
        if why:
            _fail(conn, it.bill_id, why, document=it.document_id, output=None if isinstance(out, Exception) else out)
            counts["failed"] += 1
        else:
            store(conn, it, out, Roster(conn, on), extractor.model)
            counts["stored"] += 1
        conn.commit()
    log.info("reservations: %s", counts)
    return counts


def numbered_blocks(it: Item, out: dict) -> list[dict]:
    """The blocks with their reservation numbers; unnumbered reservations (first = last = 0) get numbers after the
    printed ones, internally only, so a joint one still counts once per faction."""
    top = max((b["last"] for b in out["blocks"]), default=0)
    extra = iter(range(top + 1, top + 1 + len(out["blocks"])))
    return [b if b["last"] else {**b, "first": (n := next(extra)), "last": n} for b in out["blocks"]]


def store(conn: psycopg.Connection, it: Item, out: dict, roster: Roster, model: str) -> None:
    out = {**out, "blocks": numbered_blocks(it, out)}
    total = len({n for b in out["blocks"] for n in range(b["first"], b["last"] + 1)})
    conn.execute("""INSERT INTO bill_reservations (bill_id, document_id, file_sha256, total, numbers_checked, summary_he, model)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (bill_id) DO NOTHING""",
                 (it.bill_id, it.document_id, it.file_sha256, total, it.numbers_checked,
                  (out.get("summary") or "").strip() or None, model))
    ordinal = 0
    for g, p in enumerate(out["proposers"]):
        blocks = [b for b in out["blocks"] if p["label"] in b["proposers"]]
        numbers = sorted({n for b in blocks for n in range(b["first"], b["last"] + 1)})
        sections = list(dict.fromkeys(b["section"].strip() for b in blocks))
        conn.execute("""INSERT INTO bill_reservation_group (bill_id, ordinal, label_he, numbers, sections, gist_he)
                        VALUES (%s, %s, %s, %s, %s, %s)""",
                     (it.bill_id, g, p["label"].strip(), numbers, sections, (p.get("gist") or "").strip() or None))
        for name in p["members"]:
            member = roster.find(name)
            conn.execute("""INSERT INTO bill_reservation_person (bill_id, role, ordinal, group_ordinal, name_he, person_id, faction_id)
                            VALUES (%s, 'proposer', %s, %s, %s, %s, %s)""",
                         (it.bill_id, ordinal, g, name.strip(), member and member.person_id, member and member.faction_id))
            ordinal += 1
    for n, name in enumerate(out.get("speak_requests") or []):
        member = roster.find(name)
        conn.execute("""INSERT INTO bill_reservation_person (bill_id, role, ordinal, name_he, person_id, faction_id)
                        VALUES (%s, 'speaker', %s, %s, %s, %s)""",
                     (it.bill_id, n, name.strip(), member and member.person_id, member and member.faction_id))
    conn.execute("""UPDATE data_issue SET status = 'resolved', resolved_at = now()
                    WHERE issue_type = 'reservations_failed' AND status = 'open' AND entity_id = %s""", (it.bill_id,))
