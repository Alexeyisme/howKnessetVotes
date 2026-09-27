"""Legacy Votes.svc (OData v3, frozen at 2021-07): what OData v4 does not have.

1. Official totals (for/against/abstain, accepted) -> vote_result_official.
2. Votes missing from v4 (330 since 2015, audit §5) -> vote + ballots from vote_rslts_kmmbr_shadow.
3. Per-MK `reason` flags -> ballot.legacy_reason / counted_in_official_total
   (reason 5 = not in the official totals, audit §4; 3/4 = unclear -> NULL).

Legacy MK IDs (kmmbr_id, "vip") are not KNS_Person IDs for newer MKs, so people are resolved by name
among MKs holding a mandate in that term, and the ID is only trusted when the name agrees.

Run after the v4 load of the same period: flags can only be attached to ballots that exist.
Re-running is safe.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from collections import Counter
from typing import Iterator
from uuid import UUID

import psycopg

from hkv.ingest import mapping as m
from hkv.ingest.loader import Loader
from hkv.sources.odata import PageSource, chunks, or_filter

log = logging.getLogger("hkv.legacy")
SOURCE = "knesset_votes_legacy"

# legacy vote_result -> (choice, participation)
LEGACY_RESULTS: dict[int, tuple[str | None, str]] = {
    1: ("for", "cast"), 2: ("against", "cast"), 3: ("abstain", "cast"), 4: (None, "present_not_voting"), 0: (None, "unknown"),
}

# vote_item_dscr of legacy-only votes -> (motion_type, stage)
LEGACY_ITEMS: dict[str, tuple[str, str]] = {
    "הסתייגות": ("reservation", "second"),
    "קריאה שנייה": ("adopt_section", "second"),
    "אישור החוק": ("adopt_bill", "third"),
    "להעביר את הצעת החוק לוועדה": ("adopt_bill", "unknown"),
    "הצעת ועדה": ("procedural", "not_applicable"),
    "שם החוק": ("adopt_section", "second"),
    "הודעת הממשלה": ("other", "not_applicable"),
}

_PUNCT = re.compile(r"[`'׳\"״\-־.,()]")


def norm_tokens(name: str) -> frozenset[str]:
    return frozenset(_PUNCT.sub(" ", name).split())


def skeleton(tokens: frozenset[str]) -> frozenset[str]:
    """Tokens without the matres lectionis י/ו: plene and defective spellings of a name collapse together."""
    return frozenset(t.replace("י", "").replace("ו", "") for t in tokens)


def clean_title(s: str | None) -> str:
    """Legacy text encodes geresh as ` and en dash as ? ('תיקון מס` 50 ? הוראת שעה'); v4 uses ' and –."""
    return re.sub(r"\s\?\s", " – ", (s or "").replace("`", "'")).strip()


def counted_flag(reason: int | None) -> bool | None:
    if reason is None:
        return True
    return False if reason == 5 else None


class LegacyLoader:
    def __init__(self, conn: psycopg.Connection, legacy: PageSource, v4: PageSource) -> None:
        self.base = Loader(conn, v4)  # bookkeeping, sessions, bills, affiliations
        self.conn = conn
        self.legacy = legacy
        self.v4 = v4
        self._people: dict[tuple[int, str], list[tuple[UUID, int, frozenset[str], frozenset[str]]]] = {}

    @property
    def counts(self) -> Counter[str]:
        return self.base.counts

    # -- people -----------------------------------------------------------------------------------

    def _candidates(self, term: int, on: str) -> list[tuple[UUID, int, frozenset[str], frozenset[str]]]:
        key = (term, on)
        if key not in self._people:
            self._people[key] = [
                (pid, kid, norm_tokens(f"{first} {last}"), norm_tokens(last))
                for pid, kid, first, last in self.conn.execute(
                    """SELECT DISTINCT p.id, p.knesset_person_id, p.first_name_he, p.last_name_he FROM person p
                       JOIN mandate md ON md.person_id = p.id WHERE md.term_number = %s AND md.valid @> %s::date""", (term, on))
            ]
        return self._people[key]

    def resolve_person(self, vip: str, name: str, term: int, on: str) -> tuple[UUID, str] | None:
        vip_id = int(vip)
        cached = self.conn.execute("SELECT person_id, method FROM legacy_person_map WHERE vip_id = %s", (vip_id,)).fetchone()
        if cached:
            return cached[0], cached[1]
        tokens = norm_tokens(name)
        cands = self._candidates(term, on)
        found: tuple[UUID, str] | None = None
        by_id = [c for c in cands if c[1] == vip_id and c[3] <= tokens]
        full = [c for c in cands if c[2] == tokens]
        last = [c for c in cands if c[3] and c[3] <= tokens]
        if len(by_id) == 1:
            found = by_id[0][0], "id_and_name"
        elif len(full) == 1:
            found = full[0][0], "full_name"
        elif len(last) == 1:
            found = last[0][0], "last_name"
        else:
            sk = skeleton(tokens)
            variant = [c for c in cands if len(sk) >= 2 and sk <= skeleton(c[2])]
            if len(variant) == 1:
                found = variant[0][0], "spelling_variant"
        if found:
            self.conn.execute(
                "INSERT INTO legacy_person_map (vip_id, person_id, name_he, method) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (vip_id, found[0], name, found[1]))
        return found

    # -- main -------------------------------------------------------------------------------------

    def load(self, date_from: dt.date, date_to: dt.date) -> dict:
        window = {"from": date_from.isoformat(), "to": date_to.isoformat()}
        flt = f"vote_date ge datetime'{date_from.isoformat()}T00:00:00' and vote_date le datetime'{date_to.isoformat()}T00:00:00'"
        headers: dict[int, tuple[dict, UUID]] = {}
        with self.base.run("View_vote_rslts_hdr_Approved", window, source=SOURCE):
            for page in self.legacy.pages("View_vote_rslts_hdr_Approved", {"$filter": flt, "$orderby": "vote_id"}):
                snap = self.base.snapshot(page)
                for h in page.rows:
                    if date_from.isoformat() <= h["vote_date"][:10] <= date_to.isoformat():
                        headers[h["vote_id"]] = (h, snap)
        log.info("legacy %s..%s: %d headers", date_from, date_to, len(headers))

        legacy_only = self._legacy_only(sorted(headers))
        log.info("legacy-only votes (absent from v4): %d", len(legacy_only))
        with self.base.run("legacy_votes", {**window, "votes": len(legacy_only)}, source=SOURCE):
            self._create_votes([headers[v] for v in legacy_only])
        with self.base.run("vote_rslts_kmmbr_shadow", {**window, "votes": len(legacy_only)}, atomic=False, source=SOURCE):
            self._legacy_ballots([headers[v][0] for v in legacy_only])
        with self.base.run("legacy_totals", window, source=SOURCE):
            self._totals(headers)
        with self.base.run("legacy_reason_flags", window, atomic=False, source=SOURCE):
            self._reason_flags(headers)
        if legacy_only:
            self.base.resolve_affiliations(legacy_only)
        with self.base.run("legacy_totals_check", window, source=SOURCE):
            self._close_resolved_person_issues()
            result = self._check_totals(sorted(headers))
        log.info("legacy %s..%s done: %s", date_from, date_to, result)
        return {"headers": len(headers), "legacy_only": len(legacy_only), **result}

    def _legacy_only(self, vote_ids: list[int]) -> list[int]:
        """Header IDs that OData v4 does not have (checked against the source, not our DB, so the
        result does not depend on how far the v4 backfill has got)."""
        known = dict(self.conn.execute(
            "SELECT knesset_vote_id, 'knesset_odata_v4' = ANY(present_in) FROM vote WHERE knesset_vote_id = ANY(%s)", (vote_ids,)).fetchall())
        already_legacy_only = [v for v, in_v4 in known.items() if not in_v4]  # created by an earlier run; legacy is frozen
        unknown = [v for v in vote_ids if v not in known]
        in_v4: set[int] = set()
        batches = list(chunks(unknown))
        for i, chunk in enumerate(batches, 1):
            in_v4 |= {r["Id"] for r in self.v4_rows("KNS_PlenumVote", {"$filter": or_filter("Id", chunk), "$select": "Id"})}
            if i % 50 == 0 or i == len(batches):
                log.info("checking v4 for %d candidate votes: batch %d/%d, %d found in v4", len(unknown), i, len(batches), len(in_v4))
        return sorted(already_legacy_only + [v for v in unknown if v not in in_v4])

    def v4_rows(self, resource: str, params: dict[str, str]) -> list[dict]:
        return [r for page in self.v4.pages(resource, params) for r in page.rows]

    def _create_votes(self, rows: list[tuple[dict, UUID]]) -> None:
        if not rows:
            return
        self.base._load_sessions(sorted({int(h["session_id"]) for h, _ in rows}))
        self.base._load_bills(sorted({int(h["sess_item_id"]) for h, _ in rows}))
        sessions = {k: i for k, i in self.conn.execute("SELECT knesset_session_id, id FROM plenum_session")}
        for h, snap in rows:
            item = (h["vote_item_dscr"] or "").strip()
            motion, stage = LEGACY_ITEMS.get(item, ("unknown", "unknown"))
            session = sessions.get(int(h["session_id"]))
            if session is None:
                self.base.issue("legacy_vote_unknown_session", "info", {"vote": h["vote_id"], "session": h["session_id"]},
                                external_ref=f"legacy_vote:{h['vote_id']}", snapshot=snap)
            at = None
            if h["vote_time"] and re.fullmatch(r"\d{1,2}:\d{2}", h["vote_time"].strip()):
                at = f"{h['vote_date'][:10]} {h['vote_time'].strip()}"
            self.conn.execute(
                """INSERT INTO vote (knesset_vote_id, session_id, knesset_item_id, term_number, occurred_at, occurred_on, ordinal,
                                     title_he, method, motion_type, stage, legacy_item_he, status, present_in, source_snapshot_id)
                   VALUES (%(id)s, %(session)s, %(item)s, %(term)s,
                           CASE WHEN %(at)s::text IS NULL THEN NULL ELSE (%(at)s::timestamp AT TIME ZONE 'Asia/Jerusalem') END,
                           %(on)s, %(ord)s, %(title)s, %(method)s, %(motion)s, %(stage)s, %(item_he)s, 'valid', '{knesset_votes_legacy}', %(snap)s)
                   ON CONFLICT (knesset_vote_id) DO UPDATE SET
                     motion_type = EXCLUDED.motion_type, stage = EXCLUDED.stage, legacy_item_he = EXCLUDED.legacy_item_he,
                     title_he = CASE WHEN 'knesset_odata_v4' = ANY(vote.present_in) THEN vote.title_he ELSE EXCLUDED.title_he END,
                     present_in = ARRAY(SELECT DISTINCT unnest(vote.present_in || EXCLUDED.present_in) ORDER BY 1)""",
                {"id": h["vote_id"], "session": session, "item": int(h["sess_item_id"]), "term": h["knesset_num"], "at": at,
                 "on": h["vote_date"][:10], "ord": h["vote_nbr_in_sess"], "title": clean_title(h["sess_item_dscr"]),
                 "method": "electronic" if h["is_elctrnc_vote"] == 1 else "unknown", "motion": motion, "stage": stage,
                 "item_he": item or None, "snap": snap},
            )
            self.base.counts["legacy_votes"] += 1
        self.conn.execute(
            """INSERT INTO vote_subject (vote_id, bill_id, link_method)
               SELECT v.id, b.id, 'item_id' FROM vote v JOIN bill b ON b.knesset_bill_id = v.knesset_item_id
               WHERE v.knesset_vote_id = ANY(%s) ON CONFLICT DO NOTHING""", ([h["vote_id"] for h, _ in rows],))

    def _shadow(self, vote_ids: list[int]) -> Iterator:
        for page in self.legacy.pages("vote_rslts_kmmbr_shadow", {"$filter": or_filter("vote_id", vote_ids)}):
            snap = self.base.snapshot(page)
            for r in page.rows:
                if r["vote_id"] in vote_ids:
                    yield r, snap

    def _legacy_ballots(self, headers: list[dict]) -> None:
        by_id = {h["vote_id"]: h for h in headers}
        votes = dict(self.conn.execute("SELECT knesset_vote_id, id FROM vote WHERE knesset_vote_id = ANY(%s)", (list(by_id),)).fetchall())
        batches = list(chunks(sorted(by_id)))
        for i, chunk in enumerate(batches, 1):
            with self.conn.transaction():
                for r, snap in self._shadow(chunk):
                    h = by_id[r["vote_id"]]
                    person = self.resolve_person(r["kmmbr_id"], r["kmmbr_name"], h["knesset_num"], h["vote_date"][:10])
                    if person is None:
                        self.base.issue("legacy_person_unresolved", "error", {"row": r}, external_ref=f"vip:{int(r['kmmbr_id'])}", snapshot=snap)
                        continue
                    choice, participation = LEGACY_RESULTS.get(r["vote_result"], (None, "unknown"))
                    self.conn.execute(
                        """INSERT INTO ballot (vote_id, person_id, choice, participation, source_result_code, source,
                                               legacy_reason, counted_in_official_total, source_snapshot_id)
                           VALUES (%s, %s, %s, %s, %s, 'knesset_votes_legacy', %s, %s, %s)
                           ON CONFLICT (vote_id, person_id) DO UPDATE SET choice = EXCLUDED.choice, participation = EXCLUDED.participation,
                             source_result_code = EXCLUDED.source_result_code, legacy_reason = EXCLUDED.legacy_reason,
                             counted_in_official_total = EXCLUDED.counted_in_official_total, source_snapshot_id = EXCLUDED.source_snapshot_id
                           WHERE ballot.source = 'knesset_votes_legacy'""",
                        (votes[r["vote_id"]], person[0], choice, participation, r["vote_result"], r["reason"], counted_flag(r["reason"]), snap),
                    )
                    self.base.counts["legacy_ballots"] += 1
            log.info("legacy ballots: batch %d/%d, %d ballots", i, len(batches), self.base.counts["legacy_ballots"])

    def _totals(self, headers: dict[int, tuple[dict, UUID]]) -> None:
        votes = dict(self.conn.execute("SELECT knesset_vote_id, id FROM vote WHERE knesset_vote_id = ANY(%s)", (list(headers),)).fetchall())
        for vid, (h, snap) in headers.items():
            vote = votes.get(vid)
            if vote is None:
                self.base.counts["totals_vote_not_loaded"] += 1
                continue
            self.conn.execute(
                """INSERT INTO vote_result_official (vote_id, for_count, against_count, abstain_count, is_accepted, source, source_snapshot_id)
                   VALUES (%s, %s, %s, %s, %s, 'knesset_votes_legacy', %s)
                   ON CONFLICT (vote_id) DO UPDATE SET for_count = EXCLUDED.for_count, against_count = EXCLUDED.against_count,
                     abstain_count = EXCLUDED.abstain_count, is_accepted = EXCLUDED.is_accepted, source_snapshot_id = EXCLUDED.source_snapshot_id""",
                (vote, h["total_for"], h["total_against"], h["total_abstain"], None if h["is_accepted"] is None else bool(h["is_accepted"]), snap),
            )
            self.conn.execute(
                """UPDATE vote SET present_in = ARRAY(SELECT DISTINCT unnest(present_in || '{knesset_votes_legacy}'::text[]) ORDER BY 1)
                   WHERE id = %s AND NOT 'knesset_votes_legacy' = ANY(present_in)""", (vote,))
            self.base.counts["totals"] += 1

    def _reason_flags(self, headers: dict[int, tuple[dict, UUID]]) -> None:
        """Flag v4 ballots the legacy source marks with a reason; all other ballots of votes with
        legacy totals count as included."""
        if not headers:
            return
        lo, hi = min(headers), max(headers)
        flagged = 0
        with self.conn.transaction():
            for page in self.legacy.pages("vote_rslts_kmmbr_shadow", {"$filter": f"vote_id ge {lo} and vote_id le {hi} and reason ne null"}):
                snap = self.base.snapshot(page)
                for r in page.rows:
                    h = headers.get(r["vote_id"], (None,))[0]
                    if h is None:
                        continue
                    person = self.resolve_person(r["kmmbr_id"], r["kmmbr_name"], h["knesset_num"], h["vote_date"][:10])
                    if person is None:
                        self.base.issue("legacy_person_unresolved", "error", {"row": r}, external_ref=f"vip:{int(r['kmmbr_id'])}", snapshot=snap)
                        continue
                    n = self.conn.execute(
                        """UPDATE ballot b SET legacy_reason = %s, counted_in_official_total = %s FROM vote v
                           WHERE b.vote_id = v.id AND v.knesset_vote_id = %s AND b.person_id = %s""",
                        (r["reason"], counted_flag(r["reason"]), r["vote_id"], person[0])).rowcount
                    flagged += n
                    if n == 0:
                        self.base.counts["flag_ballot_not_loaded"] += 1
            self.conn.execute(
                """UPDATE ballot b SET counted_in_official_total = true FROM vote v
                   WHERE b.vote_id = v.id AND v.knesset_vote_id = ANY(%s) AND b.legacy_reason IS NULL
                     AND b.counted_in_official_total IS DISTINCT FROM true""", (list(headers),))
        self.base.counts["flagged"] = flagged

    def _close_resolved_person_issues(self) -> None:
        """The same vip can appear under several spellings; once any of them resolved, the issue is closed."""
        self.conn.execute(
            """UPDATE data_issue SET status = 'resolved', resolved_at = now()
               WHERE issue_type = 'legacy_person_unresolved' AND status = 'open'
                 AND substr(external_ref, 5)::int IN (SELECT vip_id FROM legacy_person_map)""")

    def _check_totals(self, vote_ids: list[int]) -> dict:
        rows = self.conn.execute(
            """SELECT v.id, v.knesset_vote_id, o.for_count, o.against_count, o.abstain_count,
                      count(*) FILTER (WHERE b.choice = 'for' AND b.counted_in_official_total IS NOT FALSE),
                      count(*) FILTER (WHERE b.choice = 'against' AND b.counted_in_official_total IS NOT FALSE),
                      count(*) FILTER (WHERE b.choice = 'abstain' AND b.counted_in_official_total IS NOT FALSE),
                      count(b.id)
               FROM vote v JOIN vote_result_official o ON o.vote_id = v.id LEFT JOIN ballot b ON b.vote_id = v.id
               WHERE v.knesset_vote_id = ANY(%s) GROUP BY 1, 2, 3, 4, 5""", (vote_ids,)).fetchall()
        result = Counter()
        for vote, vid, of, oa, ob, bf, ba, bb, n in rows:
            if n == 0:
                result["no_ballots_yet"] += 1
            elif (of, oa, ob) == (bf, ba, bb):
                result["match"] += 1
                self.conn.execute(
                    """UPDATE data_issue SET status = 'resolved', resolved_at = now()
                       WHERE issue_type = 'totals_mismatch' AND entity_id = %s AND status = 'open'""", (vote,))
            else:
                result["mismatch"] += 1
                self.base.issue("totals_mismatch", "warning", {"vote": vid, "official": [of, oa, ob], "roll_call_counted": [bf, ba, bb]},
                                table="vote", entity_id=vote)
        self.base.counts.update(result)
        return dict(result)
