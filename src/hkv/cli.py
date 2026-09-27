"""hkv ingest --from 2025-01-01 --to 2025-06-30   |   hkv verify --from ... --to ... --sample 30"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

import psycopg

from hkv.ingest.loader import Loader
from hkv.ingest.verify import coverage, sample_against_source
from hkv.sources.odata import ODataClient

DEFAULT_DB = "postgresql://knesset:knesset@localhost:5433/knesset"
RAW_DIR = Path(os.environ.get("HKV_RAW_DIR", Path(__file__).resolve().parents[2] / "data" / "raw"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hkv")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("ingest", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--from", dest="date_from", type=dt.date.fromisoformat, required=True)
        p.add_argument("--to", dest="date_to", type=dt.date.fromisoformat, required=True)
        p.add_argument("--db", default=os.environ.get("DATABASE_URL", DEFAULT_DB))
    sub.choices["ingest"].add_argument("--skip-reference", action="store_true", help="do not reload terms/people/factions/positions")
    sub.choices["verify"].add_argument("--sample", type=int, default=20)
    args = ap.parse_args(argv)

    v4 = ODataClient(raw_dir=RAW_DIR)
    with psycopg.connect(args.db) as conn:
        if args.cmd == "ingest":
            loader = Loader(conn, v4)
            if not args.skip_reference:
                loader.load_reference()
                print("reference loaded", flush=True)
            ids = loader.load_votes(args.date_from, args.date_to)
            print(f"votes loaded: {len(ids)}", flush=True)
            loader.resolve_affiliations(ids)
            print(f"affiliations: {dict(loader.counts)}", flush=True)
        else:
            for key, rows in coverage(conn, args.date_from, args.date_to).items():
                print(f"{key}: {rows}")
            diffs = sample_against_source(conn, v4, args.date_from, args.date_to, args.sample)
            bad = [d for d in diffs if d["missing_in_db"] or d["extra_in_db"]]
            print(f"sample vs source: {len(diffs)} votes, {len(bad)} differ")
            for d in bad:
                print(f"  {d}")
            return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
