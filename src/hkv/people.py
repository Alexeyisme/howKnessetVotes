"""Members by name as printed in Knesset documents (transcripts, committee versions), resolved on a given date.

Documents print names their own way: with a title ("השר לביטחון לאומי איתמר בן גביר", "היו\"ר אמיר אוחנה"), with a
middle name the person table lacks ("מכלוף מיקי זוהר"), and PDF text extraction sometimes glues words together
("ציפילבני"). Only members serving on the date are candidates, so namesakes from other Knessets do not interfere,
and a name is resolved only when exactly one member fits: an ambiguous or unknown name stays unresolved (shown as
printed) rather than guessed. Ministers who gave up their seat (the Norwegian law) still speak in the plenum, so
holders of a government post on the date are candidates too.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import psycopg

from hkv.topics import he_norm


@dataclass(frozen=True)
class Member:
    person_id: object
    faction_id: object | None    # faction on the date


class Roster:
    def __init__(self, conn: psycopg.Connection, on: dt.date):
        rows = conn.execute(
            """SELECT p.id, p.first_name_he, p.last_name_he,
                      (SELECT fm.faction_id FROM faction_membership fm WHERE fm.person_id = p.id AND fm.valid @> %(d)s::date LIMIT 1) AS faction,
                      coalesce((SELECT array_agg(a.full_name) FROM person_alias a WHERE a.person_id = p.id AND a.language = 'he'), '{}') AS aliases
               FROM person p WHERE EXISTS (SELECT 1 FROM mandate m WHERE m.person_id = p.id AND m.valid @> %(d)s::date)
                                OR EXISTS (SELECT 1 FROM gov_position g WHERE g.person_id = p.id AND g.valid @> %(d)s::date)""",
            {"d": on}).fetchall()
        self.members: list[tuple[Member, set[str], list[set[str]]]] = []
        for pid, first, last, faction, aliases in rows:
            variants = {he_norm(f"{first} {last}"), *(he_norm(a) for a in aliases)} - {""}
            self.members.append((Member(pid, faction), {v.replace(" ", "") for v in variants}, [set(v.split()) for v in variants]))

    def find(self, name: str) -> Member | None:
        """The one member the printed name fits: the whole name, else the name ending a title, else every word of a
        known name among the printed words."""
        n = he_norm(name)
        if not n:
            return None
        glued, words = n.replace(" ", ""), set(n.split())
        for test in (lambda squashed, _: glued in squashed,
                     lambda squashed, _: any(glued.endswith(s) and len(s) >= 5 for s in squashed),
                     lambda _, sets: any(len(s) >= 2 and s <= words for s in sets)):
            hits = [m for m, squashed, sets in self.members if test(squashed, sets)]
            if len(hits) == 1:
                return hits[0]
            if hits:
                return None
        return None
