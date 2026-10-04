"""Knesset OData client.

Source behaviour this client is built around (docs/audit/source-audit.md):
  * v4 pages are capped at 100 rows; follow @odata.nextLink.
  * a server-side timeout returns HTTP 200 with an EMPTY body -> treated as an error.
  * $apply is blocked by the WAF (HTTP 473); only $filter/$orderby/$select/$top are used.
  * after hours of paging the WAF starts answering some requests with HTTP 481 at random (the same URL
    alternates 200/481) -> a throttle: back off for long and retry, do not fail the whole period.
Every page is stored verbatim so parsing can be repeated without refetching.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Protocol

V4_URL = "https://knesset.gov.il/OdataV4/ParliamentInfo"
LEGACY_URL = "https://knesset.gov.il/Odata/Votes.svc"
log = logging.getLogger("hkv.odata")
USER_AGENT = "howKnessetVotes/0.1 (+https://github.com/Alexeyisme/howKnessetVotes)"


class SourceError(RuntimeError):
    pass


THROTTLED = (429, 481)  # retried after a long backoff (481: see module docstring)


@dataclass(frozen=True)
class Page:
    source: str          # 'knesset_odata_v4' | 'knesset_votes_legacy'
    resource: str        # entity set name
    request: str         # full URL
    body: bytes
    rows: list[dict]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()


class PageSource(Protocol):
    def pages(self, resource: str, params: dict[str, str]) -> Iterator[Page]: ...


class ODataClient:
    def __init__(self, base_url: str = V4_URL, source: str = "knesset_odata_v4", raw_dir: Path | None = None,
                 delay_s: float = 0.4, retries: int = 5, timeout_s: float = 120, throttle_s: float = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.source = source
        self.raw_dir = raw_dir
        self.delay_s = delay_s
        self.throttle_s = throttle_s
        self.retries = retries
        self.timeout_s = timeout_s

    def pages(self, resource: str, params: dict[str, str]) -> Iterator[Page]:
        url: str | None = f"{self.base_url}/{resource}?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        while url:
            body = self._get(url)
            data = json.loads(body)
            page = Page(self.source, resource, url, body, data["value"])
            self._store(page)
            yield page
            url = data.get("@odata.nextLink") or data.get("odata.nextLink")
            if url and not url.startswith("http"):
                url = f"{self.base_url}/{url}"

    def rows(self, resource: str, params: dict[str, str]) -> list[dict]:
        return [row for page in self.pages(resource, params) for row in page.rows]

    def _get(self, url: str) -> bytes:
        last: Exception | None = None
        for attempt in range(self.retries):
            time.sleep(self.delay_s * (1 + 3 * attempt) + random.random() * 0.2)
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    body = resp.read()
            except urllib.error.HTTPError as e:
                if e.code in (403, 473):
                    raise SourceError(f"blocked by source ({e.code}): {url}") from e  # do not hammer the WAF
                if e.code in THROTTLED:
                    last = e
                    wait = self.throttle_s * 2 ** attempt
                    log.warning("retry %d in %.0f s after HTTP %d (throttled): %s", attempt + 1, wait, e.code, url[:200])
                    time.sleep(wait)
                    continue
                if 400 <= e.code < 500:
                    raise SourceError(f"rejected ({e.code}): {url}") from e  # e.g. filter too complex; retrying won't help
                last = e
                log.warning("retry %d after HTTP %d: %s", attempt + 1, e.code, url[:200])
                continue
            except (urllib.error.URLError, TimeoutError) as e:
                last = e
                log.warning("retry %d after %r: %s", attempt + 1, e, url[:200])
                continue
            if not body.strip():
                last = SourceError("empty 200 response (server-side timeout)")
                log.warning("retry %d after empty 200: %s", attempt + 1, url[:200])
                continue
            return body
        raise SourceError(f"failed after {self.retries} attempts: {url}: {last}")

    def _store(self, page: Page) -> None:
        if self.raw_dir is None:
            return
        path = self.raw_dir / page.source / page.resource / f"{page.sha256}.json"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(page.body)

    def object_key(self, page: Page) -> str | None:
        return None if self.raw_dir is None else f"{page.source}/{page.resource}/{page.sha256}.json"


def or_filter(field: str, values: list[int]) -> str:
    return " or ".join(f"{field} eq {int(v)}" for v in values)


# The server rejects filters with more than ~20 comparisons (HTTP 400).
MAX_OR_TERMS = 15


def chunks(values: list[int], size: int = MAX_OR_TERMS) -> Iterator[list[int]]:
    for i in range(0, len(values), size):
        yield values[i:i + size]
