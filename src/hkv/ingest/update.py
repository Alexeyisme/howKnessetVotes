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
from hkv.names import LiveSources, NameSources, cache_photos, sync_factions, sync_members, sync_parties
from hkv.sources.odata import ODataClient, PageSource
from hkv.topics import sync as sync_topics
from hkv.topics.official import load as load_official

log = logging.getLogger("hkv.update")
METRIC_VERSION = "1"
RECESS_DAYS = 14                          # no vote for this long: the Knesset is in recess
REFERENCE_MAX_AGE = dt.timedelta(hours=20)
# Machine text per run: an update must finish well inside its 2-hour systemd limit, and a direct request takes ~10 s.
# A sitting day brings a few dozen new texts; a backlog (a new language, a new kind of text) is for
# `hkv translate --batch` / `hkv notes --batch`. 2026-10-07: adding Arabic made the daily update translate the whole
# Arabic backlog one request at a time until systemd killed it.
TRANSLATE_LIMIT = int(os.environ.get("HKV_UPDATE_TRANSLATE_LIMIT", "60"))   # texts per language and kind (<= ~30 requests per language)
NOTES_LIMIT = int(os.environ.get("HKV_UPDATE_NOTES_LIMIT", "20"))           # bills (one request each)
# debates and reservations of contested final votes (one larger request each: a debate is up to ~60k tokens)
POSITIONS_LIMIT = int(os.environ.get("HKV_UPDATE_POSITIONS_LIMIT", "5"))


def _reference_fresh(conn: psycopg.Connection, today: dt.date) -> bool:
    """In a recess, reference data (MKs, factions, posts: ~120 of a full run's ~130 requests) is reloaded by the
    daily run only, not by every 2-hourly one. Sitting days always reload it: new MKs must exist before their ballots."""
    last_vote, loaded = conn.execute(
        """SELECT (SELECT max(occurred_on) FROM vote),
                  (SELECT max(finished_at) FROM ingestion_run WHERE resource = 'KNS_PersonToPosition' AND status = 'succeeded')""",
    ).fetchone()
    in_recess = last_vote is None or last_vote < today - dt.timedelta(days=RECESS_DAYS)
    return in_recess and loaded is not None and loaded > dt.datetime.now(dt.timezone.utc) - REFERENCE_MAX_AGE


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
    skipped = False
    if reference and not quick:
        if _reference_fresh(conn, today):
            log.info("reference data: recess and loaded in the last %s, skipped", REFERENCE_MAX_AGE)
            skipped = True
        else:
            log.info("reference data")
            loader.load_reference()
            load_gov_positions(conn, v4)
    log.info("votes %s..%s", date_from, today)
    ids = loader.load_votes(date_from, today, label=f"update {date_from}..{today}")
    if skipped and _fingerprint(conn) != before:
        # the recess ended: the new votes may have MKs we don't know yet, so reload reference data and read them again
        log.info("new votes after the recess: reference data, then the votes again")
        loader.load_reference()
        load_gov_positions(conn, v4)
        ids = loader.load_votes(date_from, today, label=f"update {date_from}..{today}")
    # ballots skipped for an MK unknown at the time (quick runs, the pass above) and loaded since
    conn.execute("""UPDATE data_issue d SET status = 'resolved', resolved_at = now()
                    FROM ballot b WHERE d.status = 'open' AND d.issue_type = 'ballot_unknown_person'
                      AND d.external_ref = 'KNS_PlenumVoteResult:' || b.knesset_ballot_id""")
    conn.commit()
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
            if isinstance(names, LiveSources):
                cache_photos(conn)  # new or changed portraits, served from our domain (migration 0014)
        except Exception:  # a name source being down must not fail the vote update
            log.exception("member names failed; votes are loaded")
    sync_factions(conn)
    sync_parties(conn)
    derive_coalitions(conn)  # memberships and posts may have changed
    if bills:
        try:  # document links of the bills voted in the window (explanatory notes, later debate and reservations)
            loader.load_documents(bills)
        except Exception:
            log.exception("bill documents failed")
    # new titles and summaries get their en/ru/ar translations when the server has an API key; bills without an
    # official summary first get a description from their explanatory notes (hkv.notes), and contested final votes
    # the debate and the reservations (hkv.debate, hkv.reservations)
    if os.environ.get("ANTHROPIC_API_KEY"):
        files = (v4.raw_dir / "knesset_files") if getattr(v4, "raw_dir", None) else None
        try:
            from hkv.notes import ClaudeSummarizer, sync as sync_notes
            notes = sync_notes(conn, ClaudeSummarizer(), files, limit=NOTES_LIMIT)
            log.info("explanations: %s", notes)
            if notes["pending"] >= NOTES_LIMIT:
                log.warning("explanations: more than %d bills pending; the rest follow in later runs, or at once with `hkv notes --batch`", NOTES_LIMIT)
        except Exception:  # a description failure must not fail the vote update
            log.exception("explanations failed; votes are loaded")
        try:
            from hkv.debate import ClaudeSummarizer as DebateSummarizer, sync as sync_debates
            log.info("debates: %s", sync_debates(conn, DebateSummarizer(), files, limit=POSITIONS_LIMIT, loader=loader))
        except Exception:
            log.exception("debates failed; votes are loaded")
        try:
            from hkv.reservations import ClaudeExtractor, sync as sync_reservations
            log.info("reservations: %s", sync_reservations(conn, ClaudeExtractor(), files, limit=POSITIONS_LIMIT))
        except Exception:
            log.exception("reservations failed; votes are loaded")
        try:
            from hkv.translate import ClaudeTranslator, sync as sync_translations
            langs = [x for x in os.environ.get("HKV_TRANSLATE_LANGS", "en,ru,ar").split(",") if x]
            counts = sync_translations(conn, ClaudeTranslator(), langs, limit=TRANSLATE_LIMIT)
            log.info("translations: %s", counts)
            full = sorted(k for k in counts if not k.endswith("_failed") and counts[k] + counts[f"{k}_failed"] >= TRANSLATE_LIMIT)
            if full:
                log.warning("translations: backlog over %d texts per run (%s); the rest follow in later runs, or at once with "
                            "`hkv translate --batch`", TRANSLATE_LIMIT, ", ".join(full))
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
