"""Corrections proposed by visitors for machine translations (docs/ux-requirements.md R4).

Stored, never applied: an editor accepts a suggestion in the review queue. No account; a honeypot field and a
per-address daily limit keep bots out. The address is hashed with the day, so the table holds no identity.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from hkv.api.common import Conn

router = APIRouter(prefix="/api/v1")

DAILY_LIMIT = 20


class SuggestionIn(BaseModel):
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    language: Literal["he", "en", "ru", "ar"]
    suggested_text: str = Field(min_length=1, max_length=2000)
    note: str | None = Field(default=None, max_length=2000)
    page: str | None = Field(default=None, max_length=500)
    website: str = ""   # honeypot: real forms leave it empty


class SuggestionOut(BaseModel):
    id: str


def ip_hash(request: Request) -> str:
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0].strip()
    return hashlib.sha256(f"{ip}|{dt.date.today().isoformat()}".encode()).hexdigest()


@router.post("/suggestions", response_model=SuggestionOut, status_code=201)
def create_suggestion(body: SuggestionIn, request: Request, conn: Conn):
    if body.website:
        return SuggestionOut(id="00000000-0000-0000-0000-000000000000")  # a bot filled the honeypot: pretend
    h = ip_hash(request)
    n = conn.execute("SELECT count(*) AS n FROM translation_suggestion WHERE ip_hash = %s AND created_at > now() - interval '1 day'", (h,)).fetchone()["n"]
    if n >= DAILY_LIMIT:
        raise HTTPException(429, "too many suggestions today")
    row = conn.execute(
        """INSERT INTO translation_suggestion (source_sha256, language, page, suggested_text, note, ip_hash)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
        (body.source_sha256, body.language, body.page, body.suggested_text.strip(), body.note, h)).fetchone()
    conn.commit()
    return SuggestionOut(id=str(row["id"]))
