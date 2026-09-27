"""Checks that loaded data matches the source and the audit's expectations."""

from __future__ import annotations

import datetime as dt
import random

import psycopg

from hkv.sources.odata import PageSource


def coverage(conn: psycopg.Connection, date_from: dt.date, date_to: dt.date) -> dict:
    period = (date_from, date_to)
    q = lambda sql: conn.execute(sql, period).fetchall()  # noqa: E731
    return {
        "votes_by_method": q("""SELECT method, count(*), count(*) FILTER (WHERE EXISTS (SELECT 1 FROM ballot b WHERE b.vote_id = v.id))
                                FROM vote v WHERE occurred_on BETWEEN %s AND %s GROUP BY 1 ORDER BY 2 DESC"""),
        "votes_by_motion": q("""SELECT coalesce(k.motion_type, 'no_option') || ' / ' || coalesce(k.stage, '-'), count(*)
                                FROM vote v LEFT JOIN vote_option_kind k ON k.knesset_option_id = v.for_option_id
                                WHERE occurred_on BETWEEN %s AND %s GROUP BY 1 ORDER BY 2 DESC"""),
        "votes_linked_to_bill": q("""SELECT count(*) FILTER (WHERE EXISTS (SELECT 1 FROM vote_subject s WHERE s.vote_id = v.id)), count(*)
                                     FROM vote v WHERE occurred_on BETWEEN %s AND %s"""),
        "ballots_by_participation": q("""SELECT participation || coalesce(':' || choice, ''), count(*) FROM ballot b JOIN vote v ON v.id = b.vote_id
                                         WHERE occurred_on BETWEEN %s AND %s GROUP BY 1 ORDER BY 2 DESC"""),
        "ballot_faction": q("""SELECT CASE WHEN faction_id IS NULL THEN 'unresolved' WHEN faction_ambiguous THEN 'ambiguous' ELSE 'resolved' END,
                                      count(*), count(*) FILTER (WHERE mandate_id IS NULL)
                               FROM ballot b JOIN vote v ON v.id = b.vote_id WHERE occurred_on BETWEEN %s AND %s GROUP BY 1"""),
    }


def sample_against_source(conn: psycopg.Connection, v4: PageSource, date_from: dt.date, date_to: dt.date, n: int, seed: int = 0) -> list[dict]:
    """Refetch ballots for n random votes and compare (MK, code) sets with the database."""
    ids = [r[0] for r in conn.execute("SELECT knesset_vote_id FROM vote WHERE occurred_on BETWEEN %s AND %s ORDER BY 1", (date_from, date_to))]
    out = []
    for vid in random.Random(seed).sample(ids, min(n, len(ids))):
        src = {(r["MkId"], r["ResultCode"]) for p in v4.pages("KNS_PlenumVoteResult", {"$filter": f"VoteID eq {vid}"}) for r in p.rows
               if r["VoteID"] == vid}
        db = set(conn.execute(
            """SELECT p.knesset_person_id, b.source_result_code FROM ballot b JOIN vote v ON v.id = b.vote_id
               JOIN person p ON p.id = b.person_id WHERE v.knesset_vote_id = %s""", (vid,)).fetchall())
        out.append({"vote": vid, "source": len(src), "db": len(db), "missing_in_db": len(src - db), "extra_in_db": len(db - src)})
    return out
