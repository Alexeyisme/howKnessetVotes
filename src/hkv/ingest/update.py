"""Regular incremental update (architecture.md §12).

Re-reads a trailing window of days rather than trusting LastUpdatedDate: date/LastUpdatedDate
filters on KNS_PlenumVoteResult time out server-side (docs/audit/source-audit.md), and a window
also picks up retroactive corrections, which land in row_revision.

Quick mode (every 10 minutes during sittings, hkv-update-quick.timer): votes of the last day only, no reference
data; if no vote, ballot or revision was added, it stops there (a few seconds, one OData query). Otherwise it runs
the same follow-up as a full update: topics, names of new MKs, coalition blocs, title translations, a release.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
from importlib.metadata import version

import psycopg

from hkv.ingest.loader import Loader
from hkv.coalition import derive as derive_coalitions, load_positions as load_gov_positions
from hkv.names import LiveSources, NameSources, sync_factions, sync_members, sync_parties
from hkv.sources.odata import ODataClient, PageSource
from hkv.topics import sync as sync_topics
from hkv.topics.official import load as load_official

log = logging.getLogger("hkv.update")
METRIC_VERSION = "1"


def _fingerprint(conn: psycopg.Connection) -> tuple:
    """Changes when a vote or ballot is added or a source correction is recorded."""
    return conn.execute("""SELECT (SELECT count(*) FROM vote), (SELECT count(*) FROM ballot),
                                  (SELECT coalesce(max(id), 0) FROM row_revision)""").fetchone()


def update(conn: psycopg.Connection, v4: PageSource, *, days: int = 30, today: dt.date | None = None,
           reference: bool = True, names: NameSources | None = None, quick: bool = False) -> dict:
    today = today or dt.date.today()
    date_from = today - dt.timedelta(days=days)
    loader = Loader(conn, v4)
    before = _fingerprint(conn)
    if reference and not quick:
        log.info("reference data")
        loader.load_reference()
        load_gov_positions(conn, v4)
    log.info("votes %s..%s", date_from, today)
    ids = loader.load_votes(date_from, today, label=f"update {date_from}..{today}")
    if quick and _fingerprint(conn) == before:
        log.info("quick: nothing new in %s..%s (%d votes in window)", date_from, today, len(ids))
        return {"votes": len(ids), "changed": False}
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
    sync_parties(conn)
    derive_coalitions(conn)  # memberships and posts may have changed
    # titles of new bills and votes get their en/ru (and ar) translations when the server has an API key
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from hkv.translate import ClaudeTranslator, sync as sync_translations
            langs = [x for x in os.environ.get("HKV_TRANSLATE_LANGS", "en,ru").split(",") if x]
            log.info("translations: %s", sync_translations(conn, ClaudeTranslator(), langs))
        except Exception:  # a translation failure must not fail the vote update
            log.exception("title translation failed; votes are loaded")
    summary = release(conn, note=f"update {date_from}..{today}: {len(ids)} votes")
    log.info("done: %d votes in window, release %s", len(ids), summary["id"])
    return {"votes": len(ids), "changed": True, "release": str(summary["id"])}


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
