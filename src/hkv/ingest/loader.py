"""Load Knesset OData into the core schema.

Every step: fetch pages -> store a source_snapshot per page -> upsert rows keyed by official IDs.
Re-running a step is idempotent; real changes are kept in row_revision by trigger.
Rows that cannot be stored cleanly become data_issue rows instead of being dropped silently.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import time
from collections import Counter
from contextlib import contextmanager
from typing import Iterator
from uuid import UUID

import psycopg

from hkv.ingest import mapping as m
from hkv.sources.odata import Page, PageSource, chunks, or_filter

log = logging.getLogger("hkv.ingest")


class Loader:
    def __init__(self, conn: psycopg.Connection, v4: PageSource) -> None:
        # Autocommit, so every `with conn.transaction()` below is a real transaction that commits on exit.
        # Without it the first bare SELECT opens an implicit transaction and every block becomes a mere
        # savepoint: nothing is durable until the connection closes, and a killed worker loses everything.
        conn.autocommit = True
        self.conn = conn
        self.v4 = v4
        self.run_id: UUID | None = None
        self.counts: Counter[str] = Counter()

    # -- bookkeeping ------------------------------------------------------------------------------

    @contextmanager
    def run(self, resource: str, watermark: dict | None = None, atomic: bool = True,
            source: str = "knesset_odata_v4") -> Iterator[None]:
        """One ingestion_run. atomic=True: everything in one transaction. atomic=False: the body commits
        its own batches (long steps, resumable), and the run row records the outcome."""
        self.counts = Counter()
        with self.conn.transaction():
            self.run_id = self.conn.execute(
                "INSERT INTO ingestion_run (source, resource, watermark_before) VALUES (%s, %s, %s) RETURNING id",
                (source, resource, json.dumps(watermark) if watermark else None),
            ).fetchone()[0]
        try:
            if atomic:
                with self.conn.transaction():
                    yield
            else:
                yield
            with self.conn.transaction():
                self.conn.execute(
                    "UPDATE ingestion_run SET status = 'succeeded', finished_at = now(), counts = %s, watermark_after = %s WHERE id = %s",
                    (json.dumps(self.counts), json.dumps(watermark) if watermark else None, self.run_id),
                )
        except Exception as e:
            with self.conn.transaction():
                self.conn.execute(
                    "UPDATE ingestion_run SET status = 'failed', finished_at = now(), counts = %s, error = %s WHERE id = %s",
                    (json.dumps(self.counts), repr(e)[:2000], self.run_id),
                )
            raise

    def snapshot(self, page: Page) -> UUID:
        key = getattr(self.v4, "object_key", lambda p: None)(page)
        self.counts["pages"] += 1
        return self.conn.execute(
            """INSERT INTO source_snapshot (source, resource, request, content_sha256, object_key, row_count, ingestion_run_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (page.source, page.resource, page.request, page.sha256, key, len(page.rows), self.run_id),
        ).fetchone()[0]

    def issue(self, issue_type: str, severity: str, details: dict, *, table: str | None = None,
              entity_id: UUID | None = None, external_ref: str | None = None, snapshot: UUID | None = None) -> None:
        """Record once per (type, entity/external ref) while open."""
        exists = self.conn.execute(
            """SELECT 1 FROM data_issue WHERE status = 'open' AND issue_type = %s
               AND entity_id IS NOT DISTINCT FROM %s AND external_ref IS NOT DISTINCT FROM %s""",
            (issue_type, entity_id, external_ref),
        ).fetchone()
        if not exists:
            self.conn.execute(
                """INSERT INTO data_issue (entity_table, entity_id, external_ref, issue_type, severity, details, source_snapshot_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (table, entity_id, external_ref, issue_type, severity, json.dumps(details, ensure_ascii=False, default=str), snapshot),
            )
        self.counts[f"issue:{issue_type}"] += 1

    # -- reference data ---------------------------------------------------------------------------

    def load_reference(self) -> None:
        self.load_terms()
        self.load_statuses()
        self.load_people()
        self.load_factions()
        self.load_positions()

    def load_terms(self) -> None:
        with self.run("KNS_KnessetDates"):
            rows: list[dict] = []
            for page in self.v4.pages("KNS_KnessetDates", {"$orderby": "Id"}):
                self.snapshot(page)
                rows += page.rows
            starts: dict[int, str] = {}
            names: dict[int, str] = {}
            for r in rows:
                n = r["KnessetNum"]
                if r["PlenumStart"] and (n not in starts or r["PlenumStart"][:10] < starts[n]):
                    starts[n] = r["PlenumStart"][:10]
                names.setdefault(n, m.strip(r["Name"]))
            ordered = sorted(starts)
            for i, n in enumerate(ordered):
                ended = starts[ordered[i + 1]] if i + 1 < len(ordered) else None
                self.conn.execute(
                    """INSERT INTO knesset_term (number, name_he, started_on, ended_on) VALUES (%s, %s, %s, %s)
                       ON CONFLICT (number) DO UPDATE SET name_he = EXCLUDED.name_he, started_on = EXCLUDED.started_on, ended_on = EXCLUDED.ended_on""",
                    (n, names[n], starts[n], ended),
                )
                self.counts["terms"] += 1

    def load_statuses(self) -> None:
        with self.run("KNS_Status"):
            for page in self.v4.pages("KNS_Status", {"$orderby": "Id"}):
                self.snapshot(page)
                for r in page.rows:
                    self.conn.execute(
                        """INSERT INTO bill_status (knesset_status_id, label_he, is_active) VALUES (%s, %s, %s)
                           ON CONFLICT (knesset_status_id) DO UPDATE SET label_he = EXCLUDED.label_he, is_active = EXCLUDED.is_active""",
                        (r["Id"], m.strip(r["Desc"]), r["IsActive"]),
                    )
                    self.counts["statuses"] += 1

    def load_people(self) -> None:
        with self.run("KNS_Person"):
            for page in self.v4.pages("KNS_Person", {"$orderby": "Id"}):
                snap = self.snapshot(page)
                for r in page.rows:
                    self.conn.execute(
                        """INSERT INTO person (knesset_person_id, first_name_he, last_name_he, gender, source_updated_at, source_snapshot_id)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           ON CONFLICT (knesset_person_id) DO UPDATE SET first_name_he = EXCLUDED.first_name_he,
                             last_name_he = EXCLUDED.last_name_he, gender = EXCLUDED.gender,
                             source_updated_at = EXCLUDED.source_updated_at, source_snapshot_id = EXCLUDED.source_snapshot_id""",
                        (r["Id"], m.strip(r["FirstName"]) or "", m.strip(r["LastName"]) or "", m.GENDERS.get(r["GenderDesc"]),
                         r["LastUpdatedDate"], snap),
                    )
                    self.counts["people"] += 1

    def load_factions(self) -> None:
        with self.run("KNS_Faction"):
            for page in self.v4.pages("KNS_Faction", {"$orderby": "Id"}):
                snap = self.snapshot(page)
                for r in page.rows:
                    start, finish = m.day(r["StartDate"]), m.day(r["FinishDate"])
                    bounds = "[]" if finish is not None and finish <= start else "[)"
                    self.conn.execute(
                        """INSERT INTO faction (knesset_faction_id, term_number, name_he, valid, source_updated_at, source_snapshot_id)
                           VALUES (%s, %s, %s, daterange(%s::date, %s::date, %s), %s, %s)
                           ON CONFLICT (knesset_faction_id) DO UPDATE SET term_number = EXCLUDED.term_number, name_he = EXCLUDED.name_he,
                             valid = EXCLUDED.valid, source_updated_at = EXCLUDED.source_updated_at, source_snapshot_id = EXCLUDED.source_snapshot_id""",
                        (r["Id"], r["KnessetNum"], m.strip(r["Name"]), start, finish, bounds, r["LastUpdatedDate"], snap),
                    )
                    self.counts["factions"] += 1

    def load_positions(self) -> None:
        positions = sorted(m.MANDATE_POSITIONS | {m.FACTION_MEMBER_POSITION})
        with self.run("KNS_PersonToPosition"):
            people = dict(self.conn.execute("SELECT knesset_person_id, id FROM person").fetchall())
            factions = dict(self.conn.execute("SELECT knesset_faction_id, id FROM faction").fetchall())
            for page in self.v4.pages("KNS_PersonToPosition", {"$filter": or_filter("PositionID", positions), "$orderby": "Id"}):
                snap = self.snapshot(page)
                for r in page.rows:
                    if r["PositionID"] not in positions:
                        continue
                    self._position(r, snap, people, factions)

    def _position(self, r: dict, snap: UUID, people: dict, factions: dict) -> None:
        ref = f"KNS_PersonToPosition:{r['Id']}"
        start, finish = m.day(r["StartDate"]), m.day(r["FinishDate"])
        person = people.get(r["PersonID"])
        # 1900-01-01 is used by the source as a placeholder for an unknown start date
        if person is None or start is None or start < "1948-01-01" or r["KnessetNum"] is None:
            self.issue("position_unresolvable", "warning", {"row": r}, external_ref=ref, snapshot=snap)
            return
        if finish is not None and finish <= start:
            self.issue("zero_length_position", "info", {"row": r}, external_ref=ref, snapshot=snap)
            return
        if r["PositionID"] in m.MANDATE_POSITIONS:
            sql = """INSERT INTO mandate (person_id, term_number, valid, knesset_position_row_id, source_updated_at, source_snapshot_id)
                     VALUES (%s, %s, daterange(%s::date, %s::date), %s, %s, %s)
                     ON CONFLICT (knesset_position_row_id) DO UPDATE SET person_id = EXCLUDED.person_id, term_number = EXCLUDED.term_number,
                       valid = EXCLUDED.valid, source_updated_at = EXCLUDED.source_updated_at, source_snapshot_id = EXCLUDED.source_snapshot_id"""
            params = (person, r["KnessetNum"], start, finish, r["Id"], r["LastUpdatedDate"], snap)
            kind = "mandates"
        else:
            faction = factions.get(r["FactionID"])
            if faction is None:
                self.issue("position_unknown_faction", "warning", {"row": r}, external_ref=ref, snapshot=snap)
                return
            sql = """INSERT INTO faction_membership (person_id, faction_id, valid, knesset_position_row_id, source_updated_at, source_snapshot_id)
                     VALUES (%s, %s, daterange(%s::date, %s::date), %s, %s, %s)
                     ON CONFLICT (knesset_position_row_id) DO UPDATE SET person_id = EXCLUDED.person_id, faction_id = EXCLUDED.faction_id,
                       valid = EXCLUDED.valid, source_updated_at = EXCLUDED.source_updated_at, source_snapshot_id = EXCLUDED.source_snapshot_id"""
            params = (person, faction, start, finish, r["Id"], r["LastUpdatedDate"], snap)
            kind = "faction_memberships"
        try:
            with self.conn.transaction():  # savepoint: one conflicting row must not abort the run
                self.conn.execute(sql, params)
            self.counts[kind] += 1
        except psycopg.errors.ExclusionViolation as e:
            self.issue("overlapping_interval", "warning", {"row": r, "error": str(e).splitlines()[0]}, external_ref=ref, snapshot=snap)
        except psycopg.errors.IntegrityError as e:
            self.issue("position_rejected", "warning", {"row": r, "error": str(e).splitlines()[0]}, external_ref=ref, snapshot=snap)

    # -- votes ------------------------------------------------------------------------------------

    def load_votes(self, date_from: dt.date, date_to: dt.date, *, resume: bool = False, label: str | None = None) -> list[int]:
        """Votes with date_from <= local vote date <= date_to, their sessions, bills and ballots.
        resume=True skips votes that already have ballots (ballots are committed per batch of votes)."""
        window = {"from": date_from.isoformat(), "to": date_to.isoformat()}
        flt = (f"VoteDateTime ge {date_from.isoformat()}T00:00:00+03:00 and "
               f"VoteDateTime lt {(date_to + dt.timedelta(days=1)).isoformat()}T00:00:00+02:00")
        with self.run("KNS_PlenumVote", window):
            rows: list[tuple[dict, UUID]] = []
            for page in self.v4.pages("KNS_PlenumVote", {"$filter": flt, "$orderby": "Id"}):
                snap = self.snapshot(page)
                rows += [(r, snap) for r in page.rows if date_from.isoformat() <= m.day(r["VoteDateTime"]) <= date_to.isoformat()]
            options = {r["ForOptionID"]: (r["ForOptionDesc"], snap) for r, snap in rows if r["ForOptionID"] is not None}
            for option_id in sorted(options):
                self._option(option_id, *options[option_id])
            self._load_sessions(sorted({r["SessionID"] for r, _ in rows}))
            sessions = {k: (i, t) for k, i, t in self.conn.execute("SELECT knesset_session_id, id, term_number FROM plenum_session")}
            for r, snap in rows:
                self._vote(r, snap, sessions)
        vote_ids = [r["Id"] for r, _ in rows]
        items = sorted({r["ItemID"] for r, _ in rows if r["ItemID"]})
        with self.run("KNS_Bill", {"items": len(items)}):
            self._load_bills(items)
            self.conn.execute(
                """INSERT INTO vote_subject (vote_id, bill_id, link_method)
                   SELECT v.id, b.id, 'item_id' FROM vote v JOIN bill b ON b.knesset_bill_id = v.knesset_item_id
                   WHERE v.knesset_vote_id = ANY(%s) ON CONFLICT DO NOTHING""",
                (vote_ids,),
            )
        with self.run("KNS_PlenumVoteResult", window, atomic=False):
            self._load_ballots(vote_ids, resume=resume, label=label or f"{date_from}..{date_to}")
        return vote_ids

    def _load_sessions(self, session_ids: list[int]) -> None:
        for chunk in chunks(session_ids):
            for page in self.v4.pages("KNS_PlenumSession", {"$filter": or_filter("Id", chunk)}):
                snap = self.snapshot(page)
                for r in page.rows:
                    self.conn.execute(
                        """INSERT INTO plenum_session (knesset_session_id, term_number, official_number, started_at, source_updated_at, source_snapshot_id)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           ON CONFLICT (knesset_session_id) DO UPDATE SET term_number = EXCLUDED.term_number, official_number = EXCLUDED.official_number,
                             started_at = EXCLUDED.started_at, source_updated_at = EXCLUDED.source_updated_at, source_snapshot_id = EXCLUDED.source_snapshot_id""",
                        (r["Id"], r["KnessetNum"], r["Number"], r["StartDate"], r["LastUpdatedDate"], snap),
                    )
                    self.counts["sessions"] += 1

    def _option(self, option_id: int, label: str | None, snap: UUID) -> None:
        kind = m.option_kind(option_id)
        self.conn.execute(
            """INSERT INTO vote_option_kind (knesset_option_id, label_he, motion_type, stage) VALUES (%s, %s, %s, %s)
               ON CONFLICT (knesset_option_id) DO UPDATE SET label_he = EXCLUDED.label_he
               WHERE vote_option_kind.label_he IS DISTINCT FROM EXCLUDED.label_he""",
            (option_id, m.strip(label) or "", kind.motion_type, kind.stage),
        )
        if kind.motion_type == "unknown":
            self.issue("unclassified_vote_option", "info", {"option": option_id, "label": label}, external_ref=f"ForOptionID:{option_id}", snapshot=snap)

    def _vote(self, r: dict, snap: UUID, sessions: dict) -> None:
        session = sessions.get(r["SessionID"])
        if session is None:
            self.issue("vote_without_session", "error", {"vote": r["Id"], "session": r["SessionID"]}, external_ref=f"KNS_PlenumVote:{r['Id']}", snapshot=snap)
            return
        session_id, term = session
        method = m.VOTE_METHODS.get(r["VoteMethodID"], "unknown")
        at, on = m.vote_time(r["VoteDateTime"])
        status = "valid" if r["VoteStatusCode"] == 7 else "pending_verification"
        self.conn.execute(
            """INSERT INTO vote (knesset_vote_id, session_id, knesset_item_id, term_number, occurred_at, occurred_on, ordinal,
                                 title_he, subject_he, for_option_id, for_option_he, against_option_id, against_option_he,
                                 method, is_no_confidence, status, source_status_code, present_in, source_updated_at, source_snapshot_id)
               VALUES (%(id)s, %(session)s, %(item)s, %(term)s, %(at)s, %(on)s,
                       %(ord)s, %(title)s, %(subject)s, %(for_id)s, %(for_he)s, %(against_id)s, %(against_he)s, %(method)s, %(noconf)s,
                       %(status)s, %(status_code)s, '{knesset_odata_v4}', %(updated)s, %(snap)s)
               ON CONFLICT (knesset_vote_id) DO UPDATE SET session_id = EXCLUDED.session_id, knesset_item_id = EXCLUDED.knesset_item_id,
                 term_number = EXCLUDED.term_number, occurred_at = EXCLUDED.occurred_at, occurred_on = EXCLUDED.occurred_on,
                 ordinal = EXCLUDED.ordinal, title_he = EXCLUDED.title_he, subject_he = EXCLUDED.subject_he,
                 for_option_id = EXCLUDED.for_option_id, for_option_he = EXCLUDED.for_option_he,
                 against_option_id = EXCLUDED.against_option_id, against_option_he = EXCLUDED.against_option_he,
                 method = EXCLUDED.method, is_no_confidence = EXCLUDED.is_no_confidence,
                 status = CASE WHEN vote.status IN ('cancelled', 'superseded') THEN vote.status ELSE EXCLUDED.status END,
                 source_status_code = EXCLUDED.source_status_code,
                 present_in = ARRAY(SELECT DISTINCT unnest(vote.present_in || EXCLUDED.present_in) ORDER BY 1),
                 source_updated_at = EXCLUDED.source_updated_at, source_snapshot_id = EXCLUDED.source_snapshot_id""",
            {"id": r["Id"], "session": session_id, "item": r["ItemID"], "term": term, "at": at, "on": on, "ord": r["Ordinal"],
             "title": m.strip(r["VoteTitle"]) or "", "subject": m.strip(r["VoteSubject"]) or None,
             "for_id": r["ForOptionID"], "for_he": m.strip(r["ForOptionDesc"]), "against_id": r["AgainstOptionID"],
             "against_he": m.strip(r["AgainstOptionDesc"]), "method": method, "noconf": r["IsNoConfidenceInGov"],
             "status": status, "status_code": r["VoteStatusCode"], "updated": r["LastUpdatedDate"], "snap": snap},
        )
        self.counts["votes"] += 1

    def _load_bills(self, bill_ids: list[int]) -> None:
        wanted = set(bill_ids)
        for chunk in chunks(bill_ids):
            for page in self.v4.pages("KNS_Bill", {"$filter": or_filter("Id", chunk)}):
                snap = self.snapshot(page)
                for r in page.rows:
                    if r["Id"] not in wanted:
                        continue
                    self.conn.execute(
                        """INSERT INTO bill (knesset_bill_id, term_number, title_he, origin_type, bill_number, private_number, status_id,
                                             is_continuation, published_on, summary_he, source_updated_at, source_snapshot_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (knesset_bill_id) DO UPDATE SET term_number = EXCLUDED.term_number, title_he = EXCLUDED.title_he,
                             origin_type = EXCLUDED.origin_type, bill_number = EXCLUDED.bill_number, private_number = EXCLUDED.private_number,
                             status_id = EXCLUDED.status_id, is_continuation = EXCLUDED.is_continuation, published_on = EXCLUDED.published_on,
                             summary_he = EXCLUDED.summary_he, source_updated_at = EXCLUDED.source_updated_at, source_snapshot_id = EXCLUDED.source_snapshot_id""",
                        (r["Id"], r["KnessetNum"], m.strip(r["Name"]) or "", m.BILL_ORIGINS.get(m.strip(r["SubTypeDesc"])), r["Number"],
                         r["PrivateNumber"], r["StatusID"], r["IsContinuationBill"], m.day(r["PublicationDate"]), m.strip(r["SummaryLaw"]),
                         r["LastUpdatedDate"], snap),
                    )
                    self.counts["bills"] += 1

    def _load_ballots(self, vote_ids: list[int], *, resume: bool = False, label: str = "") -> None:
        votes = dict(self.conn.execute("SELECT knesset_vote_id, id FROM vote WHERE knesset_vote_id = ANY(%s)", (vote_ids,)).fetchall())
        people = dict(self.conn.execute("SELECT knesset_person_id, id FROM person").fetchall())
        todo = sorted(vote_ids)
        if resume:
            done = {r[0] for r in self.conn.execute(
                "SELECT DISTINCT v.knesset_vote_id FROM ballot b JOIN vote v ON v.id = b.vote_id WHERE v.knesset_vote_id = ANY(%s)", (vote_ids,))}
            todo = [v for v in todo if v not in done]
            if done:
                log.info("%s ballots: resume, %d of %d votes already loaded", label, len(done), len(vote_ids))
        batches = list(chunks(todo, 10))
        started = time.monotonic()
        for i, chunk in enumerate(batches, 1):
            with self.conn.transaction():  # a batch is all-or-nothing, so resume can trust "has ballots"
                self._ballot_batch(chunk, votes, people)
            elapsed = time.monotonic() - started
            log.info("%s ballots: batch %d/%d, votes %d/%d, ballots %d, pages %d, %.1f s/page",
                     label, i, len(batches), min(i * 10, len(todo)), len(todo), self.counts["ballots"], self.counts["pages"],
                     elapsed / max(self.counts["pages"], 1))

    def _ballot_batch(self, chunk: list[int], votes: dict, people: dict) -> None:
        for page in self.v4.pages("KNS_PlenumVoteResult", {"$filter": or_filter("VoteID", chunk), "$orderby": "Id"}):
            snap = self.snapshot(page)
            for r in page.rows:
                vote = votes.get(r["VoteID"])
                if vote is None or r["VoteID"] not in chunk:
                    continue
                person = people.get(r["MkId"])
                ref = f"KNS_PlenumVoteResult:{r['Id']}"
                if person is None:
                    self.issue("ballot_unknown_person", "error", {"row": r}, external_ref=ref, snapshot=snap)
                    continue
                choice, participation = m.ballot_values(r["ResultCode"])
                if participation == "unknown":
                    self.issue("unknown_result_code", "warning", {"code": r["ResultCode"], "desc": r["ResultDesc"]},
                               external_ref=f"ResultCode:{r['ResultCode']}", snapshot=snap)
                self.conn.execute(
                    """INSERT INTO ballot (vote_id, person_id, choice, participation, source_result_code, knesset_ballot_id, voted_at,
                                           source_updated_at, source_snapshot_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (vote_id, person_id) DO UPDATE SET choice = EXCLUDED.choice, participation = EXCLUDED.participation,
                         source_result_code = EXCLUDED.source_result_code, knesset_ballot_id = EXCLUDED.knesset_ballot_id,
                         voted_at = EXCLUDED.voted_at, source_updated_at = EXCLUDED.source_updated_at,
                         source_snapshot_id = EXCLUDED.source_snapshot_id""",
                    (vote, person, choice, participation, r["ResultCode"], r["Id"], r["VoteDate"], r["LastUpdatedDate"], snap),
                )
                self.counts["ballots"] += 1

    # -- derived: faction and mandate at vote time -----------------------------------------------

    def resolve_affiliations(self, vote_ids: list[int]) -> None:
        with self.run("resolve_affiliations", {"votes": len(vote_ids)}):
            scope = "v.knesset_vote_id = ANY(%(ids)s) AND b.faction_method IN ('unresolved', 'temporal_join')"
            # 1. membership interval contains the vote date; ambiguous if another membership ends that same day
            n1 = self.conn.execute(
                f"""UPDATE ballot b SET faction_id = fm.faction_id, faction_method = 'temporal_join',
                      faction_ambiguous = EXISTS (SELECT 1 FROM faction_membership o WHERE o.person_id = b.person_id
                                                  AND o.id <> fm.id AND upper(o.valid) = v.occurred_on)
                    FROM vote v, faction_membership fm, faction f
                    WHERE b.vote_id = v.id AND {scope} AND fm.person_id = b.person_id AND fm.valid @> v.occurred_on
                      AND f.id = fm.faction_id AND f.term_number = v.term_number""",
                {"ids": vote_ids},
            ).rowcount
            # 2. vote on the last day of a membership with no successor: [start, finish) excludes it; take it, flag ambiguous
            n2 = self.conn.execute(
                f"""UPDATE ballot b SET faction_id = fm.faction_id, faction_method = 'temporal_join', faction_ambiguous = true
                    FROM vote v, faction_membership fm, faction f
                    WHERE b.vote_id = v.id AND {scope} AND b.faction_id IS NULL AND fm.person_id = b.person_id
                      AND upper(fm.valid) = v.occurred_on AND f.id = fm.faction_id AND f.term_number = v.term_number""",
                {"ids": vote_ids},
            ).rowcount
            self.conn.execute(
                """UPDATE ballot b SET mandate_id = md.id FROM vote v, mandate md
                   WHERE b.vote_id = v.id AND v.knesset_vote_id = ANY(%s) AND md.person_id = b.person_id
                     AND md.term_number = v.term_number AND md.valid @> v.occurred_on""",
                (vote_ids,),
            )
            unresolved = self.conn.execute(
                """SELECT b.id, v.knesset_vote_id, p.knesset_person_id, v.occurred_on FROM ballot b
                   JOIN vote v ON v.id = b.vote_id JOIN person p ON p.id = b.person_id
                   WHERE v.knesset_vote_id = ANY(%s) AND b.faction_id IS NULL""",
                (vote_ids,),
            ).fetchall()
            for ballot_id, vote, person, on in unresolved:
                self.issue("no_faction_on_vote_date", "warning", {"vote": vote, "person": person, "date": on}, table="ballot", entity_id=ballot_id)
            self.counts.update(resolved=n1, resolved_last_day=n2, unresolved=len(unresolved))
