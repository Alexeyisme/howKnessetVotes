"""Cross-check Open Knesset dumps against official OData downloads.

Inputs: audit/raw/oknesset/*.csv (fetched by hand, see docs/audit/source-audit.md)
        audit/raw/official/*.jsonl (audit/fetch_official.py)
Prints markdown to stdout.
"""

from __future__ import annotations

import bisect
import collections as C
import csv
import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAW = Path(__file__).parent / "raw"
V4 = "https://knesset.gov.il/OdataV4/ParliamentInfo"
FROM = "2016-09-27"  # study period start (architecture.md §1)
FOR, AGAINST, ABSTAIN, PRESENT, VOTED, NOT_PRESENT = 7, 8, 9, 6, 11, 10


def jsonl(name: str) -> list[dict]:
    return [json.loads(line) for line in (RAW / "official" / f"{name}.jsonl").open(encoding="utf-8")]


def ok_csv(name: str) -> list[dict]:
    return list(csv.DictReader((RAW / "oknesset" / f"{name}.csv").open(encoding="utf-8")))


def v4(entity: str, params: dict[str, str]) -> list[dict]:
    """All rows, following nextLink (server caps pages at 100 rows)."""
    url = f"{V4}/{entity}?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    rows: list[dict] = []
    while url:
        time.sleep(0.5)
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "howKnessetVotes-audit/0.1", "Accept": "application/json"}), timeout=120) as r:
            d = json.loads(r.read())
        rows += d["value"]
        url = d.get("@odata.nextLink")
    return rows


def main() -> None:
    off_votes = {r["Id"]: r for r in jsonl("kns_plenumvote_2015")}
    ok_votes = {int(r["Id"]): r for r in ok_csv("kns_plenumvote") if r["VoteDateTime"][:4] >= "2015"}
    ballots: dict[int, list[dict]] = C.defaultdict(list)
    for r in ok_csv("kns_plenumvoteresult"):
        ballots[int(r["VoteID"])].append(r)

    in_period = {i: v for i, v in off_votes.items() if v["VoteDateTime"][:10] >= FROM}
    print(f"## 1. Vote headers: official v4 vs Open Knesset (since 2015)\n")
    print(f"- official: {len(off_votes)}, Open Knesset: {len(ok_votes)}")
    print(f"- only official: {len(off_votes.keys() - ok_votes.keys())}; only Open Knesset: {len(ok_votes.keys() - off_votes.keys())}")
    changed = [i for i in off_votes.keys() & ok_votes.keys() if off_votes[i]["LastUpdatedDate"][:19] != ok_votes[i]["LastUpdatedDate"][:19]]
    print(f"- LastUpdatedDate differs: {len(changed)}")
    print(f"- in study period (≥{FROM}): {len(in_period)} votes; with ≥1 ballot: {sum(1 for i in in_period if ballots.get(i))}")
    no_ballots = [v for i, v in in_period.items() if not ballots.get(i)]
    print(f"- without ballots by method: {C.Counter(v['VoteMethodDesc'] for v in no_ballots).most_common()}")

    print("\n## 2. Official totals (legacy Votes.svc) vs ballot rows\n")
    hdr = {r["vote_id"]: r for r in jsonl("legacy_vote_hdr_2015")}
    same_id = sum(1 for i in hdr if i in off_votes)
    print(f"- legacy headers since 2015: {len(hdr)}, last date {max(r['vote_date'] for r in hdr.values())[:10]}; vote_id present in v4: {same_id}")
    absent = [h for i, h in hdr.items() if i not in off_votes]
    print(f"- legacy-only vote_ids: {len(absent)}; by year {sorted(C.Counter(h['vote_date'][:4] for h in absent).items())}; "
          f"electronic {sum(1 for h in absent if h['is_elctrnc_vote'])}, sum of for+against+abstain {sum(h['total_for'] + h['total_against'] + h['total_abstain'] for h in absent)}")
    exact = mismatch = 0
    examples = []
    for vid, h in hdr.items():
        if vid not in off_votes or h["vote_date"][:10] < FROM:
            continue
        c = C.Counter(int(b["ResultCode"]) for b in ballots.get(vid, []))
        got = (c[FOR], c[AGAINST], c[ABSTAIN])
        want = (h["total_for"], h["total_against"], h["total_abstain"])
        if got == want:
            exact += 1
        else:
            mismatch += 1
            if len(examples) < 8:
                examples.append(f"  - vote {vid}: ballots {got} vs official {want}")
    print(f"- votes {FROM}…2021 with totals: exact match {exact}, mismatch {mismatch}")
    print("\n".join(examples))

    print("\n## 3. Faction on vote date (KNS_PersonToPosition, PositionID 54)\n")
    pos = jsonl("kns_persontoposition_mk_faction")
    spans: dict[int, list[tuple[str, str, int]]] = C.defaultdict(list)
    for p in pos:
        if p["PositionID"] == 54 and p["FactionID"]:
            spans[p["PersonID"]].append((p["StartDate"][:10], (p["FinishDate"] or "9999-12-31")[:10], p["FactionID"]))
    resolved = ambiguous = missing = 0
    same_day = 0
    for vid in in_period:
        d = in_period[vid]["VoteDateTime"][:10]
        for b in ballots.get(vid, []):
            hits = {f for s, e, f in spans.get(int(b["MkId"]), []) if s <= d <= e}
            strict = {f for s, e, f in spans.get(int(b["MkId"]), []) if s <= d < e}
            if len(strict) == 1:
                resolved += 1
            elif len(hits) >= 1:
                ambiguous += 1
                same_day += len(hits) > 1
            else:
                missing += 1
    total = resolved + ambiguous + missing
    print(f"- ballots in period: {total}; exactly one faction: {resolved} ({resolved / total:.2%}); boundary/overlap: {ambiguous} (of them multiple factions: {same_day}); none: {missing}")

    print("\n## 4. What is voted on (ItemID)\n")
    bills = {r["Id"] for r in jsonl("kns_bill_k20plus")}
    kinds = C.Counter("bill" if v["ItemID"] in bills else ("none" if not v["ItemID"] else "other") for v in in_period.values())
    print(f"- {dict(kinds)}")
    print(f"- ForOptionDesc (top 15):")
    for desc, n in C.Counter(v["ForOptionDesc"] for v in in_period.values()).most_common(15):
        print(f"  - {n} `{desc}`")

    print("\n## 5. Ballots: Open Knesset vs official v4 (random sample)\n")
    random.seed(20260927)
    sample = random.sample(sorted(i for i in in_period if ballots.get(i)), 40)
    diff = 0
    for vid in sample:
        off = {(r["MkId"], r["ResultCode"]) for r in v4("KNS_PlenumVoteResult", {"$filter": f"VoteID eq {vid}", "$select": "MkId,ResultCode"})}
        ok = {(int(b["MkId"]), int(b["ResultCode"])) for b in ballots[vid]}
        if off != ok:
            diff += 1
            print(f"  - vote {vid}: official {len(off)} rows, Open Knesset {len(ok)}, symmetric diff {len(off ^ ok)}")
    print(f"- sampled {len(sample)} votes; differing: {diff}")


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
