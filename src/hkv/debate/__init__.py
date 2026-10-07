"""What the sides argued: the plenum debate on a bill that reached a final vote (roadmap L7, step 2).

The Knesset publishes one transcript per sitting ("דברי הכנסת", KNS_DocumentPlenumSession group 28), not per bill
(per-bill excerpts stopped in November 2017). The transcript marks agenda items and speakers, in three generations:

- 2018 on, .docx: "<< הצח >> title << הצח >>" (also "<< נושא >>") for an agenda item; "<< דובר >> name (faction):
  << דובר >>", "<< דובר_המשך >>" for a speech, "<< יור >>" for the chair and "<< קריאה >>" for an interjection;
- about 2009–2017, Word 97: the same structure as hidden lines "<title>" and "<name (faction):>";
- earlier, Word 97 without markers: the table of contents names the agenda items, and speakers are lines of their
  own ending with a colon.

The agenda items whose title matches the bill are cut out of the transcripts of every sitting where the bill was
voted on (vote.session_id; a vote after midnight belongs to the sitting that started the day before). The second and
third reading is often just the committee chair and the reservations' presenters; the general debate happens at the
first (government bills) or preliminary (private bills) reading, so all of them are read. Speakers are listed from
the text itself, with no model: who spoke, at which readings, how many times and how much, resolved to the member
and their faction on the day of their first speech (hkv.people): a member who left before the final vote is still
found, under the faction they spoke for. The model then writes a neutral summary and the main
arguments for and against, each pointing to the numbered speeches it comes from; the job checks the pointers, the
language and the numbers. Nothing is silently skipped: a bill whose final sitting has no transcript yet is waiting
(retried on the next run; after TRANSCRIPT_WAIT_DAYS the sittings that have one are used), and one whose debate
cannot be found or summarised gets an open data_issue `debate_failed` (retried with `--retry-failed`).

Not covered: a debate held at a sitting with no vote on the bill (a filibuster that ran into the next day is cut
at the sitting of the vote), and the committee discussions.
"""

from __future__ import annotations

import datetime as dt
import difflib
import hashlib
import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import psycopg

from hkv.llm import HEBREW_QUOTES, complete_sentence, gershayim
from hkv.notes import docx_text, fetch, legacy_doc_text
from hkv.people import Roster
from hkv.sources.odata import SourceBlocked
from hkv.topics import he_norm

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-5"
TRANSCRIPT_GROUP = 28
MAX_CHARS = 150_000           # speeches sent to the model; longer debates (filibusters) are cut evenly per speech
TRANSCRIPT_WAIT_DAYS = 120    # transcripts usually appear within days, sometimes two months later
MAX_ARGUMENTS_PER_SIDE = 5
TITLE_MATCH = 0.9

_HEBREW = re.compile(r"[֐-׿]")
_DIGITS = re.compile(r"\d+")
_DOCX_TAG = re.compile(r"^\s*<< (\S+) >>\s*(.*?)\s*<< \1 >>\s*$")
_LEGACY_TAG = re.compile(r"^\s*<([^<>]{2,400})>\s*$")
_SPEAKER_LINE = re.compile(r"^[^.!?<>]{3,90}:$")
_LABEL = re.compile(r"^(?P<name>.+?)\s*(?:\((?P<aff>[^()]*(?:\([^()]*\)[^()]*)*)\))?\s*:?\s*$")
TOPIC_TAGS, SPEECH_TAGS, CONTINUE_TAG, CHAIR_TAG = {"הצח", "נושא"}, {"דובר", "דובר_המשך"}, "דובר_המשך", "יור"
_CHAIR = re.compile(r'^(?:היו"ר|היו״ר|יו"ר הישיבה)\s')
_OFFICIAL = re.compile(r"^(?:מזכיר|מזכירת|סגן מזכיר|סגנית מזכיר)")
LEGACY_MIN_SPEECH = 150       # untagged generations print a named interjection like a speech; shorter ones count as such


class DebateError(RuntimeError):
    """Why a vote gets no debate; the message is the data_issue reason."""


# -- transcripts ----------------------------------------------------------------------------------

@dataclass
class Turn:
    kind: str            # topic, speech, continue, chair, call, text
    label: str = ""      # agenda title or speaker label as printed
    text: str = ""


def transcript_text(data: bytes) -> str:
    if data[:2] == b"PK":
        return docx_text(data)
    if data[:4] == b"\xd0\xcf\x11\xe0":
        return legacy_doc_text(data)
    raise DebateError("unsupported_format")


def turns(text: str) -> list[Turn]:
    """The transcript as a flat list of agenda items, speaker labels and paragraphs."""
    lines = [ln.strip() for ln in text.split("\n")]
    if any(_DOCX_TAG.match(ln) for ln in lines[:2000] if "<<" in ln):
        return _tagged(lines, docx=True)
    if sum(bool(_LEGACY_TAG.match(ln)) for ln in lines) >= 3:
        return _tagged(lines, docx=False)
    return _untagged(lines)


def _speaker_kind(label: str) -> str:
    if _CHAIR.match(label):
        return "chair"
    if label.startswith("קריא") or _OFFICIAL.match(label):
        return "call"
    return "speech"


def _tagged(lines: list[str], docx: bool) -> list[Turn]:
    out: list[Turn] = []
    for ln in lines:
        if not ln:
            continue
        m = _DOCX_TAG.match(ln) if docx else _LEGACY_TAG.match(ln)
        if not m:
            if docx and ln.startswith("<<"):
                continue
            out.append(Turn("text", text=ln))
            continue
        if docx:
            tag, body = m[1], m[2].strip()
            if tag in TOPIC_TAGS:
                out.append(Turn("topic", body))
            elif tag in SPEECH_TAGS:
                kind = _speaker_kind(body)
                out.append(Turn("continue" if kind == "speech" and tag == CONTINUE_TAG else kind, body.rstrip(":").strip()))
            elif tag == CHAIR_TAG:
                out.append(Turn("chair", body.rstrip(":").strip()))
            elif tag.startswith("קריא"):
                out.append(Turn("call", body.rstrip(":").strip()))
            # other tags (סיום…) carry no speech
        else:
            body = m[1].strip()
            if body.endswith(":") or body.startswith("קריא"):
                out.append(Turn(_speaker_kind(body), body.rstrip(":").strip()))
            else:
                out.append(Turn("topic", body))
    return out


def _untagged(lines: list[str]) -> list[Turn]:
    toc = {lines[i + 1] for i, ln in enumerate(lines[:-1]) if ln.startswith("HYPERLINK") and lines[i + 1]}
    titles = {t for t in toc if not t.endswith(":") and not t.startswith("PAGEREF")}
    last_toc = max((i for i, ln in enumerate(lines) if ln.startswith(("HYPERLINK", "PAGEREF"))), default=-1)
    out: list[Turn] = []
    for ln in lines[last_toc + 1:]:
        if not ln:
            continue
        if ln in titles:
            out.append(Turn("topic", ln))
        elif _SPEAKER_LINE.match(ln):
            out.append(Turn(_speaker_kind(ln), ln.rstrip(":").strip()))
        else:
            out.append(Turn("text", text=ln))
    return out


def _title_key(title: str) -> str:
    t = he_norm(title)
    return re.sub(r"^(?:הצעת|הצעות)\s+", "", t)


def matches(topic: str, titles: Sequence[str]) -> bool:
    """An agenda item is the bill's when its title is the bill's (up to punctuation and a slight rewording), or it
    is a joint debate whose title contains it."""
    k = _title_key(topic)
    for t in titles:
        tk = _title_key(t)
        if not tk:
            continue
        if k == tk or tk in k or difflib.SequenceMatcher(None, k, tk).ratio() >= TITLE_MATCH:
            return True
    return False


def segments(stream: list[Turn], titles: Sequence[str]) -> list[tuple[str, list[Turn]]]:
    """(agenda title, its turns) for every agenda item of the bill in the transcript."""
    out: list[tuple[str, list[Turn]]] = []
    current: list[Turn] | None = None
    for t in stream:
        if t.kind == "topic":
            current = None
            if matches(t.label, titles):
                current = []
                out.append((t.label, current))
        elif current is not None:
            current.append(t)
    return out


# -- speeches and speakers ------------------------------------------------------------------------

STAGES = ["preliminary", "first", "second", "third"]
STAGE_HE = {"preliminary": "קריאה טרומית", "first": "קריאה ראשונה", "second": "קריאה שנייה ושלישית", "third": "קריאה שנייה ושלישית"}


@dataclass
class Speaker:
    label: str
    name: str
    affiliation: str | None
    speeches: int = 0
    chars: int = 0
    stages: list[str] = field(default_factory=list)
    person_id: object = None
    faction_id: object = None


@dataclass
class Speech:
    speaker: int         # index into speakers
    stage: str
    text: str
    on: dt.date | None = None   # the sitting's date


def split_label(label: str) -> tuple[str, str | None]:
    m = _LABEL.match(label)
    return (m["name"].strip(), (m["aff"] or "").strip() or None) if m else (label, None)


def speeches(parts: list[tuple]) -> tuple[list[Speaker], list[Speech]]:
    """Speeches in order with their speakers, from (stage, turns, legacy[, date]) parts. A continuation after an interjection
    or the chair joins the speech it continues; the chair, interjections and officials are left out. In the untagged
    generations (legacy) a short "speech" is a named interjection and is dropped too."""
    speakers: list[Speaker] = []
    by_label: dict[str, int] = {}
    out: list[Speech] = []
    for stage, turns_, legacy, *rest in parts:
        on = rest[0] if rest else None
        part: list[Speech] = []
        current: Speech | None = None
        for t in turns_:
            if t.kind in ("speech", "continue"):
                name, aff = split_label(t.label)
                key = he_norm(name)
                if key not in by_label:
                    by_label[key] = len(speakers)
                    speakers.append(Speaker(t.label, name, aff))
                i = by_label[key]
                if t.kind == "continue" and part and part[-1].speaker == i:
                    current = part[-1]
                else:
                    current = Speech(i, stage, "", on)
                    part.append(current)
            elif t.kind in ("chair", "call", "topic"):
                current = None
            elif t.kind == "text" and current is not None:
                current.text += (" " if current.text else "") + t.text
        out += [s for s in part if s.text.strip() and (not legacy or len(s.text) >= LEGACY_MIN_SPEECH)]
    used = sorted({s.speaker for s in out}, key=lambda i: next(n for n, s in enumerate(out) if s.speaker == i))
    remap = {old: new for new, old in enumerate(used)}
    speakers = [speakers[i] for i in used]
    for s in out:
        s.speaker = remap[s.speaker]
        sp = speakers[s.speaker]
        sp.speeches += 1
        sp.chars += len(s.text)
        if s.stage not in sp.stages:
            sp.stages.append(s.stage)
    for sp in speakers:
        sp.stages.sort(key=STAGES.index)
    return speakers, out


def fit(speeches_: list[Speech], budget: int = MAX_CHARS) -> tuple[list[str], bool]:
    """Speech texts within the budget: when the debate is longer, every speech is cut to the same cap (short ones
    stay whole), so a filibuster's hundred speeches all keep their opening."""
    lengths = [len(s.text) for s in speeches_]
    if sum(lengths) <= budget:
        return [s.text for s in speeches_], False
    lo, hi = 0, max(lengths)
    while lo < hi:   # the largest cap that fits
        mid = (lo + hi + 1) // 2
        if sum(min(n, mid) for n in lengths) <= budget:
            lo = mid
        else:
            hi = mid - 1
    return [s.text if len(s.text) <= lo else s.text[:lo] + " […]" for s in speeches_], True


# -- the model ------------------------------------------------------------------------------------

SYSTEM = (
    "You summarise Israeli Knesset plenum debates for a public, non-partisan voting-record website. You get the "
    "speeches on one bill in the plenum, numbered, each headed by the reading it was made at and the speaker as the "
    "transcript prints them (name, and faction or role in parentheses). Write in Hebrew. "
    "summary: two or three neutral sentences on what the bill does and what the debate turned on. "
    "arguments: the main arguments made for the bill and against it, at most five per side, most important first. "
    "Each is one sentence that states the argument itself (not \"X said\"), with the numbers of the speeches that made "
    "it. A speech's side is what it argues, not the speaker's party. Use only what the speeches say: no outside "
    "facts, no judgement of which side is right, no loaded words the speakers' own arguments do not need; insults, "
    "procedure and thanks are not arguments. If one side made no arguments, give none for it. Keep numbers as digits "
    "exactly as in the speeches. Dates: only the Gregorian date. " + HEBREW_QUOTES
)
SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "arguments": {"type": "array", "items": {
            "type": "object",
            "properties": {"side": {"type": "string", "enum": ["for", "against"]}, "text": {"type": "string"},
                           "speeches": {"type": "array", "items": {"type": "integer"}}},
            "required": ["side", "text", "speeches"], "additionalProperties": False}},
    },
    "required": ["summary", "arguments"], "additionalProperties": False,
}


@dataclass
class Item:
    bill_id: object
    vote_id: object      # the final vote
    title: str
    document_ids: list[int]
    file_sha256: list[str]
    segment_titles: list[str]
    speakers: list[Speaker]
    speeches: list[Speech]
    texts: list[str] = field(default_factory=list)
    truncated: bool = False

    def prompt(self) -> str:
        parts = [f"The bill: {self.title}", ""]
        for n, (s, text) in enumerate(zip(self.speeches, self.texts, strict=True), 1):
            parts.append(f"[{n}] ({STAGE_HE.get(s.stage, s.stage)}) {self.speakers[s.speaker].label}:\n{text}\n")
        return gershayim("\n".join(parts))


class Summarizer(Protocol):
    model: str

    def summarize(self, item: Item) -> dict: ...


class StubSummarizer:
    """For tests: one argument per side from the first and last speeches, with the first number of the debate."""

    model = "stub"

    def summarize(self, item: Item) -> dict:
        digits = _DIGITS.findall(" ".join(item.texts))[:1]
        n = len(item.speeches)
        return {"summary": "הדיון עסק בהצעת החוק ובהשלכותיה על הציבור" + "".join(f" ({d})" for d in digits) + ".",
                "arguments": [{"side": "for", "text": "לדברי התומכים, החוק נחוץ כדי לטפל בבעיה.", "speeches": [1]},
                              {"side": "against", "text": "לדברי המתנגדים, החוק פוגע בזכויות.", "speeches": [n]}]}


class ClaudeSummarizer:
    def __init__(self, model: str | None = None):
        from hkv.llm import JsonModel

        self.llm = JsonModel(model or MODEL, SYSTEM, SCHEMA, max_tokens=4000)
        self.model = self.llm.model

    def summarize(self, item: Item) -> dict:
        return self.llm.ask(item.prompt())

    def summarize_many(self, items: Sequence[Item]) -> list[dict | Exception]:
        return self.llm.ask_many([it.prompt() for it in items])


def _is_hebrew(text: str) -> bool:
    return len(_HEBREW.findall(text)) >= len(text) / 3


def check(item: Item, out: dict) -> tuple[str | None, list[dict]]:
    """(why the result must not be stored, the arguments with speaker ordinals). Speech numbers must exist, texts
    must be Hebrew prose of sane length, and every number must come from the speeches or the title."""
    summary, args = (out.get("summary") or "").strip(), out.get("arguments") or []
    if not 40 <= len(summary) <= 900 or not _is_hebrew(summary):
        return "bad_summary", []
    if not complete_sentence(summary):
        return "summary_cut_off", []
    if not args:
        return "no_arguments", []
    source = set(_DIGITS.findall((item.title + " " + " ".join(item.texts)).replace(",", "")))
    # the model ranks the arguments, most important first, and sometimes gives more than asked: keep its top ones
    args = [a for side in ("for", "against") for a in [x for x in args if x.get("side") == side][:MAX_ARGUMENTS_PER_SIDE]]
    stored: list[dict] = []
    for a in args:
        text = (a.get("text") or "").strip()
        nums = a.get("speeches") or []
        if not 10 <= len(text) <= 400 or not _is_hebrew(text):
            return "bad_argument_text", []
        if not complete_sentence(text):
            return "argument_cut_off", []
        if not nums or any(not 1 <= n <= len(item.speeches) for n in nums):
            return "bad_speech_reference", []
        stored.append({"side": a["side"], "text_he": text,
                       "speakers": sorted({item.speeches[n - 1].speaker for n in nums})})
    missing = [d for d in _DIGITS.findall((summary + " " + " ".join(a["text_he"] for a in stored)).replace(",", "")) if d not in source]
    if missing:
        return f"numbers_not_in_debate:{','.join(missing[:5])}", []
    return None, stored


# -- the job --------------------------------------------------------------------------------------

FINAL_VOTE = "coalesce(k.motion_type, v.motion_type) = 'adopt_bill' AND coalesce(k.stage, v.stage) = 'third'"


def candidates(conn: psycopg.Connection, limit: int | None = None, retry_failed: bool = False,
               contested_only: bool = True) -> list[tuple]:
    """(bill id, title, final vote id, final vote date) of bills with a final vote and no debate yet, most recent
    first; by default only where the coalition and opposition majorities differed on the final vote."""
    return conn.execute(
        f"""SELECT DISTINCT ON (v.occurred_on, b.id) b.id, b.title_he, v.id, v.occurred_on
            FROM vote v
            JOIN vote_subject vs ON vs.vote_id = v.id JOIN bill b ON b.id = vs.bill_id
            LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
            LEFT JOIN vote_bloc vb ON vb.vote_id = v.id
            WHERE {FINAL_VOTE} AND v.status = 'valid' AND (NOT %(contested)s OR vb.contested)
              AND NOT EXISTS (SELECT 1 FROM bill_debate d WHERE d.bill_id = b.id)
              AND (%(retry)s OR NOT EXISTS (SELECT 1 FROM data_issue i WHERE i.issue_type = 'debate_failed'
                                            AND i.status = 'open' AND i.entity_id = b.id))
            ORDER BY v.occurred_on DESC, b.id, v.occurred_at DESC NULLS LAST""" + (" LIMIT %(limit)s" if limit else ""),
        {"retry": retry_failed, "limit": limit, "contested": contested_only}).fetchall()


def sittings(conn: psycopg.Connection, bill_id) -> list[tuple]:
    """(session id, knesset session id, reading, vote titles, date) of the sittings where the bill was voted on, in
    order; the reading is the furthest one voted on at that sitting."""
    return conn.execute(
        """SELECT s.id, s.knesset_session_id,
                  (array_agg(coalesce(k.stage, v.stage) ORDER BY array_position(ARRAY['third', 'second', 'first', 'preliminary'], coalesce(k.stage, v.stage))))[1],
                  array_agg(DISTINCT v.title_he), min(v.occurred_on)
           FROM vote v JOIN vote_subject vs ON vs.vote_id = v.id JOIN plenum_session s ON s.id = v.session_id
           LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
           WHERE vs.bill_id = %s AND coalesce(k.stage, v.stage) IN ('preliminary', 'first', 'second', 'third')
           GROUP BY s.id, s.knesset_session_id ORDER BY min(v.occurred_at), s.knesset_session_id""", (bill_id,)).fetchall()


def _fail(conn: psycopg.Connection, bill_id, reason: str, **details) -> None:
    payload = json.dumps({"reason": reason, **details}, ensure_ascii=False, default=str)
    if not conn.execute("""UPDATE data_issue SET details = %s WHERE issue_type = 'debate_failed' AND status = 'open'
                           AND entity_id = %s""", (payload, bill_id)).rowcount:
        conn.execute("""INSERT INTO data_issue (entity_table, entity_id, issue_type, severity, details)
                        VALUES ('bill', %s, 'debate_failed', 'warning', %s)""", (bill_id, payload))


def _transcripts(conn: psycopg.Connection, session_id) -> list[tuple[int, str]]:
    return conn.execute("""SELECT knesset_document_id, url FROM plenum_document WHERE session_id = %s AND group_type_id = %s
                           ORDER BY knesset_document_id""", (session_id, TRANSCRIPT_GROUP)).fetchall()


def prepare(conn: psycopg.Connection, bill_id, title: str, vote_id,
            plan: list[tuple[str, list[str], list[tuple[int, str]], dt.date]], cache_dir: Path | None) -> Item:
    """Item for the summariser from (reading, vote titles, transcript files, date) per sitting; DebateError when
    there is no debate to use."""
    doc_ids, shas, found_titles, parts = [], [], [], []
    for stage, titles, docs, on in plan:
        for doc_id, url in docs:
            data = fetch(url, cache_dir)
            doc_ids.append(doc_id)
            shas.append(hashlib.sha256(data).hexdigest())
            for seg_title, seg in segments(turns(transcript_text(data)), [*titles, title]):
                found_titles.append(seg_title)
                parts.append((stage, seg, data[:2] != b"PK", on))
    if not parts:
        raise DebateError("agenda_item_not_found")
    speakers, spoken = speeches(parts)
    if not spoken:
        raise DebateError("no_speeches")
    rosters: dict[dt.date, Roster] = {}
    for i, s in enumerate(speakers):
        day = next(x.on for x in spoken if x.speaker == i)
        member = (rosters.get(day) or rosters.setdefault(day, Roster(conn, day))).find(s.name)
        if member:
            s.person_id, s.faction_id = member.person_id, member.faction_id
    texts, truncated = fit(spoken)
    return Item(bill_id, vote_id, title, doc_ids, shas, found_titles, speakers, spoken, texts, truncated)


def sync(conn: psycopg.Connection, summarizer: Summarizer, cache_dir: Path | None = None, limit: int | None = None,
         retry_failed: bool = False, batch: bool = False, contested_only: bool = True, loader=None,
         today: dt.date | None = None) -> dict[str, int]:
    """Summarise the debates that need it. With a `loader` (hkv.ingest.Loader), transcript links of the sittings
    that have none yet are fetched first."""
    today = today or dt.date.today()
    counts = {"pending": 0, "waiting": 0, "stored": 0, "failed": 0}
    todo = [(r, sittings(conn, r[0])) for r in candidates(conn, limit, retry_failed, contested_only)]
    if loader is not None:
        missing = sorted({s[1] for _, ss in todo for s in ss if not _transcripts(conn, s[0])})
        if missing:
            loader.load_plenum_documents(missing)
            conn.commit()
    items: list[Item] = []
    for (bill_id, title, vote_id, on), ss in todo:
        counts["pending"] += 1
        plan = [(stage, titles, _transcripts(conn, sid), day) for sid, _, stage, titles, day in ss]
        recent = (today - on).days <= TRANSCRIPT_WAIT_DAYS
        if recent and (not plan or not plan[-1][2]):   # the final sitting's transcript is not out yet
            counts["waiting"] += 1
            continue
        plan = [p for p in plan if p[2]]
        try:
            if not plan:
                raise DebateError("transcript_missing")
            items.append(prepare(conn, bill_id, title, vote_id, plan, cache_dir))
        except SourceBlocked:
            raise
        except DebateError as e:
            _fail(conn, bill_id, str(e), sittings=[s[1] for s in ss])
            counts["failed"] += 1
        except Exception as e:  # a missing or broken file: recorded, the rest goes on
            _fail(conn, bill_id, "fetch_failed", sittings=[s[1] for s in ss], error=repr(e)[:500])
            counts["failed"] += 1
        conn.commit()
    log.info("debates: %d pending, %d waiting for a transcript, %d ready (%d cut to fit)", counts["pending"], counts["waiting"],
             len(items), sum(i.truncated for i in items))
    if batch and items and hasattr(summarizer, "summarize_many"):
        results = summarizer.summarize_many(items)
    else:
        results = []
        for it in items:
            try:
                results.append(summarizer.summarize(it))
            except Exception as e:
                log.warning("debate summary failed for %s", it.title[:80], exc_info=True)
                results.append(e)
    for it, out in zip(items, results, strict=True):
        why, args = ("model_error:" + repr(out)[:300], []) if isinstance(out, Exception) else check(it, out)
        if why:
            _fail(conn, it.bill_id, why, output=None if isinstance(out, Exception) else out)
            counts["failed"] += 1
        else:
            store(conn, it, out["summary"].strip(), args, summarizer.model)
            counts["stored"] += 1
        conn.commit()
    log.info("debates: %s", counts)
    return counts


def store(conn: psycopg.Connection, it: Item, summary: str, args: list[dict], model: str) -> None:
    conn.execute("""INSERT INTO bill_debate (bill_id, vote_id, document_ids, file_sha256, segment_titles, chars, truncated,
                                             summary_he, arguments, model)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (bill_id) DO NOTHING""",
                 (it.bill_id, it.vote_id, it.document_ids, it.file_sha256, it.segment_titles, sum(map(len, it.texts)),
                  it.truncated, summary, json.dumps(args, ensure_ascii=False), model))
    for n, s in enumerate(it.speakers):
        conn.execute("""INSERT INTO bill_debate_speaker (bill_id, ordinal, label_he, name_he, affiliation_he, person_id, faction_id,
                                                         speeches, chars, stages)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                     (it.bill_id, n, s.label, s.name, s.affiliation, s.person_id, s.faction_id, s.speeches, s.chars, s.stages))
    conn.execute("""UPDATE data_issue SET status = 'resolved', resolved_at = now()
                    WHERE issue_type = 'debate_failed' AND status = 'open' AND entity_id = %s""", (it.bill_id,))
