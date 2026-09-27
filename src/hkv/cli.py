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
    bf = sub.add_parser("backfill", help="parallel historical load of votes (reference data must be loaded)")
    bf.add_argument("--from", dest="date_from", type=dt.date.fromisoformat, required=True)
    bf.add_argument("--to", dest="date_to", type=dt.date.fromisoformat, required=True)
    bf.add_argument("--workers", type=int, default=3)
    bf.add_argument("--months", type=int, default=3, help="period size per work item")
    bf.add_argument("--skip", action="append", default=[], help="FROM..TO already loaded, e.g. 2025-01-01..2025-06-30")
    bf.add_argument("--log", type=Path, default=Path("logs/backfill.log"))
    bf.add_argument("--db", default=os.environ.get("DATABASE_URL", DEFAULT_DB))
    st = sub.add_parser("status", help="load coverage per year and backfill worker liveness")
    st.add_argument("--log", type=Path, default=Path("logs/backfill.log"))
    st.add_argument("--db", default=os.environ.get("DATABASE_URL", DEFAULT_DB))
    args = ap.parse_args(argv)

    if args.cmd == "status":
        return status(args.db, args.log)

    if args.cmd == "backfill":
        from hkv.ingest.backfill import backfill
        skip = [tuple(dt.date.fromisoformat(x) for x in s.split("..")) for s in args.skip]
        return backfill(args.db, RAW_DIR, args.date_from, args.date_to, workers=args.workers, months=args.months,
                        log_file=args.log, skip=skip)

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


def status(db_url: str, log_file: Path) -> int:
    with psycopg.connect(db_url) as conn:
        rows = conn.execute(
            """SELECT extract(year FROM v.occurred_on)::int, count(*), count(*) FILTER (WHERE c.n > 0), coalesce(sum(c.n), 0)::bigint
               FROM vote v CROSS JOIN LATERAL (SELECT count(*) AS n FROM ballot b WHERE b.vote_id = v.id) c
               GROUP BY 1 ORDER BY 1""").fetchall()
        print("year  votes  with_ballots  ballots")
        for y, n, w, b in rows:
            print(f"{y}  {n:5}  {w:12}  {b:7}")
        issues = conn.execute("SELECT issue_type, count(*) FROM data_issue WHERE status = 'open' GROUP BY 1 ORDER BY 2 DESC").fetchall()
        print("open issues:", dict(issues))
    if log_file.exists():
        now = dt.datetime.now()
        last: dict[str, dt.datetime] = {}
        for line in log_file.read_text(encoding="utf-8").splitlines()[-2000:]:
            parts = line.split()
            if len(parts) > 4 and parts[2] == "MainProcess" and parts[4] == "backfill":
                last.clear()  # a new backfill run started: older workers are gone
            if len(parts) > 2 and parts[2].startswith("SpawnPoolWorker"):
                try:
                    last[parts[2]] = dt.datetime.strptime(f"{parts[0]} {parts[1][:8]}", "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
        for worker, ts in sorted(last.items()):
            age = (now - ts).total_seconds()
            print(f"{worker}: last log {age:.0f}s ago{'  <-- STALLED?' if age > 300 else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
