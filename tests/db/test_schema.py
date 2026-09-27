"""Schema invariants from architecture.md §5 and §7, checked against a throwaway database."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "db"))
from migrate import DEFAULT_URL, migrate  # noqa: E402

ADMIN_URL = os.environ.get("DATABASE_URL", DEFAULT_URL)


@pytest.fixture(scope="session")
def db_url():
    name = f"test_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute(f"CREATE DATABASE {name}")
    url = psycopg.conninfo.make_conninfo(ADMIN_URL, dbname=name)
    try:
        yield url
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(f"DROP DATABASE {name} WITH (FORCE)")


@pytest.fixture(scope="session")
def migrated(db_url):
    assert migrate(db_url) == ["0001_core.sql"]
    return db_url


@pytest.fixture
def cur(migrated):
    """Each test runs in a transaction that is rolled back."""
    with psycopg.connect(migrated) as conn:
        with conn.cursor() as c:
            yield c
        conn.rollback()


def ok(cur, sql, params=()):
    cur.execute("SAVEPOINT s")
    cur.execute(sql, params)
    cur.execute("RELEASE SAVEPOINT s")


def rejected(cur, sql, params=()):
    cur.execute("SAVEPOINT s")
    with pytest.raises(psycopg.errors.IntegrityError):
        cur.execute(sql, params)
    cur.execute("ROLLBACK TO SAVEPOINT s")


@pytest.fixture
def world(cur):
    """A term, one MK, one faction and one vote."""
    cur.execute("INSERT INTO knesset_term (number, started_on, ended_on) VALUES (24, '2021-04-06', '2022-11-15'), (25, '2022-11-15', NULL)")
    cur.execute("INSERT INTO person (knesset_person_id, first_name_he, last_name_he) VALUES (1, 'א', 'ב') RETURNING id")
    person = cur.fetchone()[0]
    cur.execute("INSERT INTO faction (knesset_faction_id, term_number, name_he, valid) VALUES (1096, 25, 'הליכוד', '[2022-11-15,)'), (1097, 25, 'אחר', '[2022-11-15,)') RETURNING id")
    f1, f2 = (r[0] for r in cur.fetchall())
    cur.execute(
        """INSERT INTO vote (knesset_vote_id, term_number, occurred_at, occurred_on, title_he, method, present_in)
           VALUES (46699, 25, '2026-07-28T14:43:00+03:00', '2026-07-28', 'הצעת חוק', 'electronic', '{knesset_odata_v4}') RETURNING id"""
    )
    vote = cur.fetchone()[0]
    return {"person": person, "f1": f1, "f2": f2, "vote": vote}


def test_migrations_are_idempotent(migrated):
    assert migrate(migrated) == []


def test_faction_membership_cannot_overlap(cur, world):
    p, f1, f2 = world["person"], world["f1"], world["f2"]
    ok(cur, "INSERT INTO faction_membership (person_id, faction_id, valid) VALUES (%s, %s, '[2022-11-15,2024-01-01)')", (p, f1))
    # adjacent half-open interval is a valid switch of faction
    ok(cur, "INSERT INTO faction_membership (person_id, faction_id, valid) VALUES (%s, %s, '[2024-01-01,)')", (p, f2))
    rejected(cur, "INSERT INTO faction_membership (person_id, faction_id, valid) VALUES (%s, %s, '[2023-06-01,2023-07-01)')", (p, f2))


def test_zero_length_membership_rejected(cur, world):
    rejected(cur, "INSERT INTO faction_membership (person_id, faction_id, valid) VALUES (%s, %s, '[2020-03-29,2020-03-29)')", (world["person"], world["f1"]))


def test_mandates_may_touch_across_terms_but_not_overlap_within(cur, world):
    p = world["person"]
    # real case from audit: K23 mandate ends 2021-04-06, K24 starts 2021-04-05
    ok(cur, "INSERT INTO knesset_term (number, started_on) VALUES (23, '2020-03-16')")
    ok(cur, "INSERT INTO mandate (person_id, term_number, valid) VALUES (%s, 23, '[2020-03-16,2021-04-06)')", (p,))
    ok(cur, "INSERT INTO mandate (person_id, term_number, valid) VALUES (%s, 24, '[2021-04-05,2021-08-05)')", (p,))
    rejected(cur, "INSERT INTO mandate (person_id, term_number, valid) VALUES (%s, 24, '[2021-06-01,2021-07-01)')", (p,))


@pytest.mark.parametrize(
    ("choice", "participation", "allowed"),
    [
        ("for", "cast", True),
        ("abstain", "cast", True),
        (None, "cast", False),
        (None, "present_not_voting", True),
        ("for", "present_not_voting", False),
        ("against", "absent_reported", False),
        (None, "participated_choice_unavailable", True),
    ],
)
def test_ballot_choice_matches_participation(cur, world, choice, participation, allowed):
    sql = "INSERT INTO ballot (vote_id, person_id, choice, participation, source_result_code) VALUES (%s, %s, %s, %s, 7)"
    (ok if allowed else rejected)(cur, sql, (world["vote"], world["person"], choice, participation))


def test_one_ballot_per_person_per_vote(cur, world):
    sql = "INSERT INTO ballot (vote_id, person_id, choice, participation, source_result_code) VALUES (%s, %s, 'for', 'cast', 7)"
    ok(cur, sql, (world["vote"], world["person"]))
    rejected(cur, sql, (world["vote"], world["person"]))


def test_resolved_faction_requires_faction_id(cur, world):
    rejected(
        cur,
        "INSERT INTO ballot (vote_id, person_id, choice, participation, source_result_code, faction_method) VALUES (%s, %s, 'for', 'cast', 7, 'temporal_join')",
        (world["vote"], world["person"]),
    )


def test_vote_date_is_jerusalem_calendar_date(cur, world):
    # 22:30 UTC on 1 Jan is 00:30 on 2 Jan in Jerusalem
    sql = """INSERT INTO vote (knesset_vote_id, term_number, occurred_at, occurred_on, title_he, method, present_in)
             VALUES (%s, 25, '2024-01-01T22:30:00Z', %s, 't', 'electronic', '{knesset_odata_v4}')"""
    rejected(cur, sql, (1, "2024-01-01"))
    ok(cur, sql, (2, "2024-01-02"))


def test_vote_requires_known_source(cur, world):
    rejected(
        cur,
        "INSERT INTO vote (knesset_vote_id, term_number, occurred_on, title_he, method, present_in) VALUES (3, 25, '2024-01-01', 't', 'electronic', '{}')",
    )


def test_update_keeps_previous_version(cur, world):
    cur.execute(
        "INSERT INTO ballot (vote_id, person_id, choice, participation, source_result_code) VALUES (%s, %s, 'for', 'cast', 7) RETURNING id",
        (world["vote"], world["person"]),
    )
    ballot = cur.fetchone()[0]
    cur.execute("INSERT INTO source_snapshot (source, resource, request, content_sha256) VALUES ('knesset_odata_v4', 'x', 'x', 'h') RETURNING id")
    snap = cur.fetchone()[0]
    # re-import of identical content: only the snapshot pointer moves, no revision
    cur.execute("UPDATE ballot SET source_snapshot_id = %s WHERE id = %s", (snap, ballot))
    cur.execute("SELECT count(*) FROM row_revision WHERE row_id = %s", (ballot,))
    assert cur.fetchone()[0] == 0
    # an official correction keeps the old row
    cur.execute("UPDATE ballot SET choice = 'against', source_result_code = 8 WHERE id = %s", (ballot,))
    cur.execute("SELECT old_row->>'choice' FROM row_revision WHERE table_name = 'ballot' AND row_id = %s", (ballot,))
    assert cur.fetchall() == [("for",)]
