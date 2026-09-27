"""Parallel historical load: split a date range into periods and let N worker processes take them.

Each period = load_votes(resume=True) + resolve_affiliations, so a crashed or re-run backfill
continues where it stopped. Progress goes to one log file, one line per ballot batch (~10 votes),
which makes a stalled worker visible within a minute or two.

Reference data (people, factions, positions) must be loaded first: `hkv ingest ...` without --skip-reference.
"""

from __future__ import annotations

import datetime as dt
import logging
import multiprocessing as mp
import os
import time
import traceback
from pathlib import Path

import psycopg

LOG_FORMAT = "%(asctime)s %(processName)-10s %(levelname)-7s %(message)s"


def periods(date_from: dt.date, date_to: dt.date, months: int) -> list[tuple[dt.date, dt.date]]:
    out, start = [], date_from
    while start <= date_to:
        y, mth = divmod(start.month - 1 + months, 12)
        nxt = dt.date(start.year + y, mth + 1, 1)
        out.append((start, min(nxt - dt.timedelta(days=1), date_to)))
        start = nxt
    return out


def _setup_logging(log_file: Path) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    handler = logging.FileHandler(log_file, encoding="utf-8")  # O_APPEND: whole lines from several processes
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(handler)


def _worker_init(log_file: str) -> None:
    _setup_logging(Path(log_file))


def _run_period(args: tuple[str, str, dt.date, dt.date]) -> tuple[str, str, int, float]:
    db_url, raw_dir, start, end = args
    from hkv.ingest.loader import Loader
    from hkv.sources.odata import ODataClient

    label = f"{start}..{end}"
    log = logging.getLogger("hkv.backfill")
    t0 = time.monotonic()
    log.info("%s start", label)
    try:
        with psycopg.connect(db_url) as conn:
            loader = Loader(conn, ODataClient(raw_dir=Path(raw_dir)))
            ids = loader.load_votes(start, end, resume=True, label=label)
            loader.resolve_affiliations(ids)
            unresolved = loader.counts["unresolved"]
        took = time.monotonic() - t0
        log.info("%s done: %d votes, %d ballots without faction, %.0f min", label, len(ids), unresolved, took / 60)
        return label, "ok", len(ids), took
    except Exception:  # noqa: BLE001 - report and let other periods continue
        log.error("%s FAILED\n%s", label, traceback.format_exc())
        return label, "failed", 0, time.monotonic() - t0


def backfill(db_url: str, raw_dir: Path, date_from: dt.date, date_to: dt.date, *, workers: int, months: int,
             log_file: Path, skip: list[tuple[dt.date, dt.date]] = ()) -> int:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    _setup_logging(log_file)
    log = logging.getLogger("hkv.backfill")
    todo = [p for p in periods(date_from, date_to, months) if not any(s <= p[0] and p[1] <= e for s, e in skip)]
    todo.reverse()  # newest first
    log.info("backfill %s..%s: %d periods of %d months, %d workers, pid %d", date_from, date_to, len(todo), months, workers, os.getpid())
    failed = []
    ctx = mp.get_context("spawn")
    with ctx.Pool(workers, initializer=_worker_init, initargs=(str(log_file),)) as pool:
        for n, (label, status, votes, took) in enumerate(pool.imap_unordered(_run_period, [(db_url, str(raw_dir), s, e) for s, e in todo]), 1):
            log.info("progress %d/%d periods (%s %s)", n, len(todo), label, status)
            if status != "ok":
                failed.append(label)
    log.info("backfill finished: %d ok, %d failed %s", len(todo) - len(failed), len(failed), failed)
    return 1 if failed else 0
