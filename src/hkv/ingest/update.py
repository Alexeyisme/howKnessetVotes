"""Regular incremental update (architecture.md §12).

Re-reads a trailing window of days rather than trusting LastUpdatedDate: date/LastUpdatedDate
filters on KNS_PlenumVoteResult time out server-side (docs/audit/source-audit.md), and a window
also picks up retroactive corrections, which land in row_revision.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from importlib.metadata import version

import psycopg

from hkv.ingest.loader import Loader
from hkv.names import LiveSources, NameSources, sync_factions, sync_members
from hkv.sources.odata import ODataClient, PageSource
from hkv.topics import sync as sync_topics
from hkv.topics.official import load as load_official

log = logging.getLogger("hkv.update")
METRIC_VERSION = "1"


def update(conn: psycopg.Connection, v4: PageSource, *, days: int = 30, today: dt.date | None = None,
           reference: bool = True, names: NameSources | None = None) -> dict:
    today = today or dt.date.today()
    date_from = today - dt.timedelta(days=days)
    loader = Loader(conn, v4)
    if reference:
        log.info("reference data")
        loader.load_reference()
    log.info("votes %s..%s", date_from, today)
    ids = loader.load_votes(date_from, today, label=f"update {date_from}..{today}")
    loader.resolve_affiliations(ids)
    # memberships may have been corrected retroactively: retry ballots that had no faction anywhere
    stale = [r[0] for r in conn.execute(
        "SELECT DISTINCT v.knesset_vote_id FROM ballot b JOIN vote v ON v.id = b.vote_id WHERE b.faction_id IS NULL")]
    if stale:
        loader.resolve_affiliations(stale)
    # bills voted in the window: refresh their official law bindings, then topics (official + keyword rules)
    bills = [r[0] for r in conn.execute(
        """SELECT DISTINCT b.knesset_bill_id FROM vote_subject vs JOIN bill b ON b.id = vs.bill_id JOIN vote v ON v.id = vs.vote_id
           WHERE v.occurred_on >= %s""", (date_from,))]
    if bills:
        try:
            load_official(conn, v4, bills)
        except Exception:  # the classification is an extra; a failure must not fail the vote update
            log.exception("official law classification failed")
    log.info("topics: %s", sync_topics(conn))  # new bills get official and rule-based topics
    # names for MKs seen for the first time; curated faction names (official current ones: `hkv names`)
    if names is None and isinstance(v4, ODataClient):
        names = LiveSources(v4.raw_dir, v4)
    if names is not None:
        try:
            sync_members(conn, names)
        except Exception:  # a name source being down must not fail the vote update
            log.exception("member names failed; votes are loaded")
    sync_factions(conn)
    summary = release(conn, note=f"update {date_from}..{today}: {len(ids)} votes")
    log.info("done: %d votes in window, release %s", len(ids), summary["id"])
    return {"votes": len(ids), "release": str(summary["id"])}


def release(conn: psycopg.Connection, note: str) -> dict:
    """Record what the published data covers now (shown by the API as 'data as of')."""
    coverage = {
        "votes": conn.execute("SELECT count(*) FROM vote").fetchone()[0],
        "ballots": conn.execute("SELECT count(*) FROM ballot").fetchone()[0],
        "first_vote_on": str(conn.execute("SELECT min(occurred_on) FROM vote").fetchone()[0]),
        "last_vote_on": str(conn.execute("SELECT max(occurred_on) FROM vote").fetchone()[0]),
        "open_issues": dict(conn.execute("SELECT issue_type, count(*) FROM data_issue WHERE status = 'open' GROUP BY 1").fetchall()),
    }
    with conn.transaction():
        rid = conn.execute(
            "INSERT INTO data_release (pipeline_version, metric_version, coverage, notes) VALUES (%s, %s, %s, %s) RETURNING id",
            (version("hkv"), METRIC_VERSION, json.dumps(coverage), note)).fetchone()[0]
    return {"id": rid, **coverage}
