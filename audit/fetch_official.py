"""Download selected official Knesset OData tables to audit/raw/official/*.jsonl.

v4 pages are capped at 100 rows server-side; we follow @odata.nextLink.
An empty body with HTTP 200 (seen when a query times out server-side) is
treated as an error, never as "no rows".
"""

from __future__ import annotations

import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

V4 = "https://knesset.gov.il/OdataV4/ParliamentInfo"
LEGACY = "https://knesset.gov.il/Odata/Votes.svc"
UA = "howKnessetVotes-audit/0.1 (civic research)"
OUT = Path(__file__).parent / "raw" / "official"

JOBS = {
    "kns_plenumvote_2015": (V4, "KNS_PlenumVote", {"$filter": "VoteDateTime ge 2015-01-01T00:00:00+02:00", "$orderby": "Id"}),
    "kns_person": (V4, "KNS_Person", {"$orderby": "Id"}),
    "kns_persontoposition_mk_faction": (V4, "KNS_PersonToPosition", {"$filter": "PositionID eq 43 or PositionID eq 61 or PositionID eq 54 or PositionID eq 48", "$orderby": "Id"}),
    "kns_faction": (V4, "KNS_Faction", {"$orderby": "Id"}),
    "kns_knessetdates": (V4, "KNS_KnessetDates", {"$orderby": "Id"}),
    "kns_bill_k20plus": (V4, "KNS_Bill", {"$filter": "KnessetNum ge 20", "$orderby": "Id"}),
    "kns_status": (V4, "KNS_Status", {"$orderby": "Id"}),
    "legacy_vote_hdr_2015": (LEGACY, "View_vote_rslts_hdr_Approved", {"$filter": "vote_date ge datetime'2015-01-01T00:00:00'", "$orderby": "vote_id"}),
}


def fetch(url: str) -> dict:
    for attempt in range(5):
        time.sleep(0.4 + attempt * 2 + random.random() * 0.3)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            if not body:
                raise ValueError("empty 200 body")
            return json.loads(body)
        except Exception as e:  # noqa: BLE001
            print(f"retry {attempt}: {e} {url[:160]}", file=sys.stderr, flush=True)
    raise RuntimeError(url)


def run(name: str) -> None:
    base, entity, params = JOBS[name]
    url = f"{base}/{entity}?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    path = OUT / f"{name}.jsonl"
    n = 0
    with path.open("w", encoding="utf-8") as f:
        while url:
            d = fetch(url)
            for row in d["value"]:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += len(d["value"])
            url = d.get("@odata.nextLink") or d.get("odata.nextLink")
            if url and not url.startswith("http"):
                url = f"{base}/{url}"
    print(f"{name}: {n} rows", flush=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for job in sys.argv[1:] or JOBS:
        run(job)
