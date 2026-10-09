"""IDs for the load test (load.js): votes with a roll call, members, bills, factions, parties and topics of the
database copy, written to pools.json. Usage: uv run infra/loadtest/pools.py postgresql://knesset:knesset@localhost:5433/hkvlt"""

import json
import sys
from pathlib import Path

import psycopg


def column(conn, sql: str) -> list:
    return [r[0] for r in conn.execute(sql)]


with psycopg.connect(sys.argv[1]) as conn:
    pools = {
        "votes": column(conn, "SELECT v.knesset_vote_id FROM vote v WHERE EXISTS (SELECT 1 FROM ballot b WHERE b.vote_id = v.id) ORDER BY random() LIMIT 3000"),
        "finalVotes": column(conn, "SELECT knesset_vote_id FROM vote WHERE stage = 'third' AND motion_type = 'adopt_bill' ORDER BY occurred_on DESC LIMIT 40"),
        "members": column(conn, "SELECT p.knesset_person_id FROM person p WHERE EXISTS (SELECT 1 FROM ballot b WHERE b.person_id = p.id) ORDER BY random()"),
        "bills": column(conn, "SELECT knesset_bill_id FROM bill ORDER BY random() LIMIT 2000"),
        "factions": column(conn, "SELECT knesset_faction_id FROM faction"),
        "parties": column(conn, "SELECT slug FROM party"),
        "topics": column(conn, "SELECT slug FROM topic"),
    }
Path(__file__).with_name("pools.json").write_text(json.dumps(pools))
print({k: len(v) for k, v in pools.items()})
