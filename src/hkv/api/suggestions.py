"""Corrections proposed by visitors for machine translations (docs/ux-requirements.md R4), and mistake reports.

A suggestion with a source hash corrects one translated text; without one it is a free-text report about a page
(a wrong number, a badly summarised argument, anything). Stored, never applied: an editor accepts a suggestion in the
review queue. Each one is forwarded to the owner's Telegram chat by @knessetvotes_bot (TELEGRAM_BOT_TOKEN and
TELEGRAM_CHAT_ID, the same bot as the update alerts), because otherwise nobody would see it. No account; a honeypot
field and a per-address daily limit keep bots out. The address is hashed with the day, so the table holds no identity.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import logging
import os
import urllib.parse
import urllib.request
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field

from hkv.api.common import Conn

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

DAILY_LIMIT = 20
SITE = "https://knessetvotes.org"


class SuggestionIn(BaseModel):
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    language: Literal["he", "en", "ru", "ar"]
    suggested_text: str = Field(min_length=1, max_length=2000)
    note: str | None = Field(default=None, max_length=2000)
    contact: str | None = Field(default=None, max_length=200)
    page: str | None = Field(default=None, max_length=500)
    website: str = ""   # honeypot: real forms leave it empty


class SuggestionOut(BaseModel):
    id: str


def ip_hash(request: Request) -> str:
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0].strip()
    return hashlib.sha256(f"{ip}|{dt.date.today().isoformat()}".encode()).hexdigest()


def message(body: SuggestionIn, current: str | None) -> str:
    """Plain text for the chat (no parse mode, so nothing a visitor writes can break the formatting)."""
    head = "Translation correction" if body.source_sha256 else "Mistake report"
    lines = [f"knessetvotes.org: {head} ({body.language})"]
    if body.page:
        lines.append(SITE + body.page if body.page.startswith("/") else body.page)
    if current:
        lines += ["", "Current translation:", current]
    lines += ["", body.suggested_text.strip()]
    if body.note and body.note.strip():
        lines += ["", "Note: " + body.note.strip()]
    if body.contact and body.contact.strip():
        lines += ["", "Contact: " + body.contact.strip()]
    return "\n".join(lines)[:4000]   # Telegram's limit is 4096 characters


def notify(text: str) -> None:
    """Best effort: a failure is logged, the suggestion is already stored."""
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        log.info("suggestion stored; Telegram not configured")
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": text, "disable_web_page_preview": "true"}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=20).close()
    except Exception as e:  # the token is in the URL: log the error type only
        log.warning("Telegram notification failed: %s", type(e).__name__)


@router.post("/suggestions", response_model=SuggestionOut, status_code=201)
def create_suggestion(body: SuggestionIn, request: Request, conn: Conn, tasks: BackgroundTasks):
    if body.website:
        return SuggestionOut(id="00000000-0000-0000-0000-000000000000")  # a bot filled the honeypot: pretend
    h = ip_hash(request)
    n = conn.execute("SELECT count(*) AS n FROM translation_suggestion WHERE ip_hash = %s AND created_at > now() - interval '1 day'", (h,)).fetchone()["n"]
    if n >= DAILY_LIMIT:
        raise HTTPException(429, "too many suggestions today")
    contact = (body.contact or "").strip() or None
    row = conn.execute(
        """INSERT INTO translation_suggestion (source_sha256, language, page, suggested_text, note, contact, ip_hash)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (body.source_sha256, body.language, body.page, body.suggested_text.strip(), body.note, contact, h)).fetchone()
    current = None
    if body.source_sha256 and body.language != "he":
        t = conn.execute("SELECT text FROM text_translation WHERE source_sha256 = %s AND language = %s",
                         (body.source_sha256, body.language)).fetchone()
        current = t["text"] if t else None
    conn.commit()
    tasks.add_task(notify, message(body, current))
    return SuggestionOut(id=str(row["id"]))
