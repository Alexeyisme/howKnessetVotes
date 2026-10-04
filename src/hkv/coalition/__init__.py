"""Governments and coalition membership, derived from official government posts (docs/roadmap.md D3).

KNS_PersonToPosition lists ministers, deputy ministers and prime ministers with the government number and dates
(gov_position). From it:

- government: number, the Knesset it started in, dates (from its first post to the next government's first post)
  and the prime minister;
- faction_alignment: a faction is 'coalition' on the days one of its members holds a post in that day's government,
  'opposition' on its other days within the government. Short gaps (a minister replaced within MERGE_GAP_DAYS) do
  not flip the faction. Days on which the government has no posts at all - after an election, before the new
  government is sworn in - are 'unknown': there is no coalition then. A minister who left the Knesset under the
  "Norwegian law" still counts for their last faction while in office.

Known exceptions are curated in overrides.toml (origin 'curated') and replace the derived role for their dates.
"""

from __future__ import annotations

import datetime as dt
import logging
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

import psycopg

from hkv.sources.odata import PageSource

log = logging.getLogger("hkv.coalition")

# KNS_Position: prime minister, alternate/acting/deputy PMs, ministers, deputy ministers
GOV_POSITIONS = {45, 73, 51, 31, 50, 65, 39, 57, 40, 59, 285079}
PRIME_MINISTER = 45
MERGE_GAP_DAYS = 30
NORWEGIAN_LAW = dt.date(2015, 1, 1)
OVERRIDES = Path(__file__).with_name("overrides.toml")

Span = tuple[dt.date, dt.date]  # [start, end), end exclusive


def load_positions(conn: psycopg.Connection, v4: PageSource) -> int:
    """Refresh gov_position from the source (all governments; a few thousand rows)."""
    people = dict(conn.execute("SELECT knesset_person_id, id FROM person").fetchall())
    n = 0
    with conn.transaction():
        conn.execute("DELETE FROM gov_position")
        for page in v4.pages("KNS_PersonToPosition", {"$filter": "GovernmentNum gt 0", "$orderby": "Id"}):
            for r in page.rows:
                if r["PositionID"] not in GOV_POSITIONS or not r.get("StartDate") or r["StartDate"][:10] < "1948-01-01":
                    continue
                start, finish = r["StartDate"][:10], (r["FinishDate"] or "")[:10] or None
                if finish is not None and finish <= start:
                    continue
                conn.execute(
                    """INSERT INTO gov_position (knesset_position_row_id, person_id, knesset_person_id, government_number, position_id,
                                                ministry_he, duty_he, valid, source_updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, daterange(%s::date, %s::date), %s)""",
                    (r["Id"], people.get(r["PersonID"]), r["PersonID"], r["GovernmentNum"], r["PositionID"],
                     _clean(r.get("GovMinistryName")), _clean(r.get("DutyDesc")), start, finish, r.get("LastUpdatedDate")))
                n += 1
    log.info("government posts: %d", n)
    return n


def _clean(s: str | None) -> str | None:
    s = " ".join((s or "").split())
    return s or None


def derive(conn: psycopg.Connection) -> dict[str, int]:
    """Rebuild government and the derived faction_alignment rows, then apply curated overrides."""
    counts: Counter[str] = Counter()
    with conn.transaction():
        govs = conn.execute(
            """SELECT government_number, min(lower(valid)) AS start FROM gov_position WHERE government_number > 0 GROUP BY 1 ORDER BY 2""").fetchall()
        conn.execute("DELETE FROM faction_alignment")
        conn.execute("DELETE FROM government")
        spans: dict[int, Span] = {}
        for i, (num, start) in enumerate(govs):
            end = govs[i + 1][1] if i + 1 < len(govs) else dt.date(9999, 1, 1)
            spans[num] = (start, end)
            term = conn.execute("SELECT max(number) FROM knesset_term WHERE started_on <= %s", (start,)).fetchone()[0]
            pm = conn.execute(
                """SELECT person_id FROM gov_position WHERE government_number = %s AND position_id = %s AND person_id IS NOT NULL
                   ORDER BY lower(valid) LIMIT 1""", (num, PRIME_MINISTER)).fetchone()
            conn.execute("INSERT INTO government (number, term_number, valid, prime_minister_person_id) VALUES (%s, %s, daterange(%s, %s), %s)",
                         (num, term, start, None if end.year == 9999 else end, pm[0] if pm else None))
            counts["governments"] += 1

        posts: dict[int, dict] = defaultdict(lambda: defaultdict(list))   # government -> person -> [spans]
        any_post: dict[int, list[Span]] = defaultdict(list)                 # government -> spans with any post
        for num, pid, lo, hi in conn.execute("SELECT government_number, person_id, lower(valid), upper(valid) FROM gov_position"):
            if num not in spans:
                continue
            s = _clip((lo, hi or spans[num][1]), spans[num])
            if s:
                any_post[num].append(s)
                if pid:
                    posts[num][pid].append(s)

        members: dict = defaultdict(list)   # faction -> [(person, span)]
        lifetimes: dict = {}
        for fid, lo, hi in conn.execute("SELECT id, lower(valid), upper(valid) FROM faction WHERE lower(valid) >= '1999-01-01'"):
            lifetimes[fid] = (lo, hi or dt.date(9999, 1, 1))
        for fid, pid, lo, hi in conn.execute(
                "SELECT faction_id, person_id, lower(valid), upper(valid) FROM faction_membership WHERE faction_id = ANY(%s)", (list(lifetimes),)):
            members[fid].append((pid, (lo, hi or dt.date(9999, 1, 1))))
        starts: dict = defaultdict(list)    # person -> membership start dates (any faction)
        for pid, lo in conn.execute("SELECT person_id, lower(valid) FROM faction_membership"):
            starts[pid].append(lo)

        for num, gspan in spans.items():
            active = _merge(any_post[num], gap=1)
            for fid, life in lifetimes.items():
                within = _clip(life, gspan)
                if not within:
                    continue
                held: list[Span] = []
                for pid, mspan in members[fid]:
                    for p in posts[num].get(pid, []):
                        x = _clip(_norwegian(mspan, p, starts[pid]), p)
                        if x and (x := _clip(x, within)):
                            held.append(x)
                coalition = _merge(held, gap=MERGE_GAP_DAYS)
                for role, parts in (("coalition", coalition),
                                    ("unknown", _subtract([within], active)),
                                    ("opposition", _subtract(_subtract([within], coalition), _subtract([within], active)))):
                    for lo, hi in parts:
                        conn.execute(
                            """INSERT INTO faction_alignment (faction_id, government_number, valid, role, evidence, origin)
                               VALUES (%s, %s, daterange(%s, %s), %s, %s, 'derived')""",
                            (fid, num, lo, None if hi.year == 9999 else hi, role,
                             "members holding government posts (KNS_PersonToPosition)" if role == "coalition"
                             else "no member holds a government post" if role == "opposition" else "no government posts recorded on these dates"))
                        counts[role] += 1
        counts.update(apply_overrides(conn))
        counts["vote_blocs"] = refresh_blocs(conn)
    log.info("coalition: %s", dict(counts))
    return dict(counts)


def _norwegian(membership: Span, post: Span, person_starts: list[dt.date]) -> Span:
    """A minister who gives up the Knesset seat while in office (the "Norwegian law") still serves for the faction:
    a membership that ends during a post is extended to the post's end, unless the person joins another faction
    before then. Only from 2015, when the law was passed: earlier, a minister who resigned the seat had left the
    party (e.g. Hanegbi, Likud -> Kadima, December 2005)."""
    lo, hi = membership
    if hi >= NORWEGIAN_LAW and post[0] < hi < post[1] and not any(hi <= s < post[1] for s in person_starts):
        return lo, post[1]
    return membership


def refresh_blocs(conn: psycopg.Connection) -> int:
    """Rebuild vote_bloc: cast votes by coalition and opposition members per vote, and whether the blocs' strict
    majorities differed (a contested vote)."""
    conn.execute("DELETE FROM vote_bloc")
    return conn.execute("""
        INSERT INTO vote_bloc
        SELECT vote_id, cf, ca, cab, of_, oa, oab,
               coalesce(CASE WHEN cf * 2 > cf + ca + cab THEN 'for' WHEN ca * 2 > cf + ca + cab THEN 'against' END
                        <> CASE WHEN of_ * 2 > of_ + oa + oab THEN 'for' WHEN oa * 2 > of_ + oa + oab THEN 'against' END, false)
        FROM (SELECT b.vote_id,
                     count(*) FILTER (WHERE a.role = 'coalition' AND b.choice = 'for') AS cf,
                     count(*) FILTER (WHERE a.role = 'coalition' AND b.choice = 'against') AS ca,
                     count(*) FILTER (WHERE a.role = 'coalition' AND b.choice = 'abstain') AS cab,
                     count(*) FILTER (WHERE a.role = 'opposition' AND b.choice = 'for') AS of_,
                     count(*) FILTER (WHERE a.role = 'opposition' AND b.choice = 'against') AS oa,
                     count(*) FILTER (WHERE a.role = 'opposition' AND b.choice = 'abstain') AS oab
              FROM ballot b JOIN vote v ON v.id = b.vote_id
              JOIN faction_alignment a ON a.faction_id = b.faction_id AND a.valid @> v.occurred_on
              WHERE b.choice IS NOT NULL AND a.role IN ('coalition', 'opposition')
              GROUP BY b.vote_id) x""").rowcount


def apply_overrides(conn: psycopg.Connection, path: Path = OVERRIDES) -> Counter[str]:
    """Curated roles replace derived ones for their dates: the derived rows are cut around the override."""
    counts: Counter[str] = Counter()
    entries = tomllib.loads(path.read_text(encoding="utf-8")).get("override", []) if path.exists() else []
    for e in entries:
        fid = conn.execute("SELECT id FROM faction WHERE knesset_faction_id = %s", (e["faction"],)).fetchone()
        if fid is None:
            counts["override_unknown_faction"] += 1
            continue
        lo = dt.date.fromisoformat(e["from"])
        hi = dt.date.fromisoformat(e["to"]) if e.get("to") else None
        rows = conn.execute(
            """DELETE FROM faction_alignment WHERE faction_id = %s AND valid && daterange(%s, %s)
               RETURNING government_number, lower(valid), upper(valid), role, evidence, origin""", (fid[0], lo, hi)).fetchall()
        for gov, rlo, rhi, role, evidence, origin in rows:
            for plo, phi in _subtract([(rlo, rhi or dt.date(9999, 1, 1))], [(lo, hi or dt.date(9999, 1, 1))]):
                conn.execute("""INSERT INTO faction_alignment (faction_id, government_number, valid, role, evidence, origin)
                                VALUES (%s, %s, daterange(%s, %s), %s, %s, %s)""",
                             (fid[0], gov, plo, None if phi.year == 9999 else phi, role, evidence, origin))
            span = _clip((lo, hi or dt.date(9999, 1, 1)), (rlo, rhi or dt.date(9999, 1, 1)))
            if span:
                conn.execute("""INSERT INTO faction_alignment (faction_id, government_number, valid, role, evidence, origin)
                                VALUES (%s, %s, daterange(%s, %s), %s, %s, 'curated')""",
                             (fid[0], gov, span[0], None if span[1].year == 9999 else span[1], e["role"], e["evidence"]))
        counts["overrides"] += 1
    return counts


# -- date spans [start, end) --------------------------------------------------------------------------

def _clip(a: Span, b: Span) -> Span | None:
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return (lo, hi) if lo < hi else None


def _merge(spans: list[Span], gap: int) -> list[Span]:
    out: list[list[dt.date]] = []
    for lo, hi in sorted(spans):
        if out and (lo - out[-1][1]).days < gap:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [(a, b) for a, b in out]


def _subtract(spans: list[Span], cut: list[Span]) -> list[Span]:
    out = spans
    for clo, chi in cut:
        nxt: list[Span] = []
        for lo, hi in out:
            if chi <= lo or clo >= hi:
                nxt.append((lo, hi))
                continue
            if lo < clo:
                nxt.append((lo, clo))
            if chi < hi:
                nxt.append((chi, hi))
        out = nxt
    return out
