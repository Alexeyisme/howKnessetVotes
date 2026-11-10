"""New Knesset readiness (docs/roadmap.md O7, docs/new-term.md): what the source has published for the newest term
and what is still to be done by hand.

Read-only. The MKs, factions, memberships and votes come in by themselves with `hkv update`; the curated parts do
not: ru/en/ar faction names (curated/factions.toml), the factions' parties (curated/parties.toml) and the few MKs the
name steps cannot match (curated/mk_names.toml). `hkv newterm` lists them, with entries ready to fill in and paste.
"""

from __future__ import annotations

import datetime as dt
import re
import tomllib
from collections import Counter
from dataclasses import dataclass, field

import psycopg

from hkv.names import CURATED, load_curated
from hkv.topics import he_norm

LANGS = ("en", "ru", "ar")


def _ord(n: int | None) -> str:
    return "?" if n is None else f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


@dataclass
class NewFaction:
    knesset_id: int
    name_he: str
    members: int
    curated: bool                       # has an entry in factions.toml
    labels: dict[str, str]              # language -> origin of the stored label
    parties: list[str]                  # party slugs linked in parties.toml
    alignment: str | None               # role today
    came_from: list[tuple[str, int]] = field(default_factory=list)   # (party slug, members) by the members' previous faction
    name_match: list[str] = field(default_factory=list)              # party slugs whose Hebrew name is in the faction's name


@dataclass
class Report:
    term: int
    started_on: dt.date
    votes: int
    mandates: int
    factions: list[NewFaction]
    no_site_id: list[tuple[int, str]]                 # (KNS person id, Hebrew name)
    missing_names: dict[str, int]                     # language -> MKs without a display name
    no_photo: int
    government: tuple[int, int | None] | None         # (number, term it was formed in) of today's government

    @property
    def published(self) -> bool:
        return self.mandates > 0 and bool(self.factions)

    @property
    def todo(self) -> list[str]:
        out = []
        if not self.published:
            return ["wait: the source has no MKs or factions for this term yet (hkv update loads them when it does)"]
        if n := sum(not f.curated for f in self.factions):
            out.append(f"factions.toml: {n} factions without ru/en/ar names")
        if n := sum(not f.parties for f in self.factions):
            out.append(f"parties.toml: {n} factions not in any party")
        if self.no_site_id:
            out.append(f"hkv names, then mk_names.toml: {len(self.no_site_id)} MKs not linked to the Knesset website")
        if n := max(self.missing_names.values(), default=0):
            out.append(f"hkv names: up to {n} MKs without a name in some language")
        if self.no_photo:
            out.append(f"hkv names: {self.no_photo} MKs without a photo")
        if self.government and self.government[1] is not None and self.government[1] < self.term:
            out.append(f"after the new government is sworn in: hkv coalition, then check overrides.toml "
                       f"(government {self.government[0]} is the outgoing one)")
        return out


def report(conn: psycopg.Connection) -> Report:
    term, started = conn.execute("SELECT number, started_on FROM knesset_term ORDER BY number DESC LIMIT 1").fetchone()
    votes = conn.execute("SELECT count(*) FROM vote WHERE occurred_on >= %s", (started,)).fetchone()[0]
    people = [r[0] for r in conn.execute("SELECT DISTINCT person_id FROM mandate WHERE term_number = %s", (term,))]
    _, curated = load_curated()
    parties = tomllib.loads((CURATED / "parties.toml").read_text(encoding="utf-8"))["party"]
    party_of: dict[int, list[str]] = {}
    for slug, p in parties.items():
        for kid in p["factions"]:
            party_of.setdefault(kid, []).append(slug)

    factions = []
    for fid, kid, name, members, align in conn.execute(
            """SELECT f.id, f.knesset_faction_id, btrim(f.name_he),
                      (SELECT count(DISTINCT fm.person_id) FROM faction_membership fm WHERE fm.faction_id = f.id),
                      (SELECT a.role FROM faction_alignment a WHERE a.faction_id = f.id AND a.valid @> current_date)
               FROM faction f WHERE f.term_number = %s ORDER BY 4 DESC, 2""", (term,)).fetchall():
        labels = dict(conn.execute("SELECT language, origin FROM faction_label WHERE faction_id = %s", (fid,)).fetchall())
        # the party of each member's faction in the previous Knesset: where the list most likely continues
        came: Counter[str] = Counter()
        for (prev,) in conn.execute(
                """SELECT DISTINCT ON (fm.person_id) pf.knesset_faction_id FROM faction_membership fm
                   JOIN faction pf ON pf.id = fm.faction_id
                   WHERE pf.term_number < %s AND fm.person_id IN (SELECT person_id FROM faction_membership WHERE faction_id = %s)
                   ORDER BY fm.person_id, lower(fm.valid) DESC""", (term, fid)):
            for slug in party_of.get(prev, []):
                came[slug] += 1
        # a party's Hebrew name as whole words of the list name ("חדש" is not in "סיעה חדשה")
        n = f" {re.sub(r'[^\w]+', ' ', he_norm(name))} "
        factions.append(NewFaction(kid, name, members, kid in curated, labels, party_of.get(kid, []), align, came.most_common(3),
                                   [slug for slug, p in parties.items()
                                    if (w := re.sub(r"[^\w]+", " ", he_norm(p["he"])).strip()) and f" {w} " in n]))

    no_site = conn.execute(
        """SELECT p.knesset_person_id, p.first_name_he || ' ' || p.last_name_he FROM person p WHERE p.id = ANY(%s)
             AND NOT EXISTS (SELECT 1 FROM person_external_id e WHERE e.person_id = p.id AND e.scheme = 'knesset_site')
           ORDER BY 2""", (people,)).fetchall()
    missing = {lang: conn.execute(
        """SELECT count(*) FROM unnest(%s::uuid[]) AS x(pid) WHERE NOT EXISTS (
             SELECT 1 FROM person_alias a WHERE a.person_id = x.pid AND a.language = %s AND a.alias_type = 'official')""",
        (people, lang)).fetchone()[0] for lang in LANGS}
    no_photo = conn.execute(
        """SELECT count(*) FROM unnest(%s::uuid[]) AS x(pid)
           WHERE NOT EXISTS (SELECT 1 FROM person_photo ph WHERE ph.person_id = x.pid)""", (people,)).fetchone()[0]
    gov = conn.execute("SELECT number, term_number FROM government WHERE valid @> current_date").fetchone()
    return Report(term, started, votes, len(people), factions, [tuple(r) for r in no_site], missing, no_photo,
                  tuple(gov) if gov else None)


def state(r: Report) -> str:
    """One line that changes only at the stages someone acts on: scripts/newterm-check.sh sends it to Telegram when
    it changes (the source publishes the MKs and factions; a government of the new Knesset is sworn in)."""
    if not r.published:
        return f"{_ord(r.term)} Knesset: waiting for the source"
    if r.government and r.government[1] is not None and r.government[1] >= r.term:
        return f"{_ord(r.term)} Knesset: government {r.government[0]} sworn in"
    return f"{_ord(r.term)} Knesset: MKs and factions published"


def render(r: Report) -> str:
    """The report, then entries to fill in and paste into the curated files."""
    out = [f"{_ord(r.term)} Knesset, sworn in {r.started_on}: {r.votes} votes, {r.mandates} MKs, {len(r.factions)} factions in the source",
           f"government today: {r.government[0]} (formed in the {_ord(r.government[1])} Knesset)" if r.government else "government today: none recorded"]
    if r.factions:
        out.append("\nfactions:")
        for f in r.factions:
            names = ",".join(f"{lang}:{f.labels.get(lang, '-')}" for lang in LANGS)
            party = ",".join(f.parties) or "NO PARTY"
            out.append(f"  {f.knesset_id:>6}  {f.members:>3} MKs  {'curated' if f.curated else 'NOT CURATED':<11}  {names:<40}  "
                       f"party: {party:<20}  role today: {f.alignment or '-'}  {f.name_he}")
    if r.mandates:
        out.append(f"\nMKs: {len(r.no_site_id)} not linked to the website; without a name: "
                   + ", ".join(f"{lang} {n}" for lang, n in r.missing_names.items()) + f"; without a photo: {r.no_photo}")
    out.append("\nto do:" + "".join(f"\n  - {t}" for t in r.todo) if r.todo else "\nto do: nothing, the new Knesset is complete")

    todo_factions = [f for f in r.factions if not f.curated]
    if todo_factions:
        out.append("\n# --- src/hkv/names/curated/factions.toml: fill in every language, then append ---")
        out.append(f"\n# --- {_ord(r.term)} Knesset ({r.started_on.year}–) ---")
        for f in todo_factions:
            out.append(f"[faction.{f.knesset_id}]  # {f.name_he} ({f.members} MKs)\n"
                       f'ru = ""\nen = ""\nar = ""\n# he_short = ""  # only when the official Hebrew name is a long list name; '
                       f"then also ru_short / en_short / ar_short")
    no_party = [f for f in r.factions if not f.parties]
    if no_party:
        out.append("\n# --- src/hkv/names/curated/parties.toml: add each faction to its party (a joint list to every member party) ---")
        for f in no_party:
            hints = [f"{slug} ({n} of {f.members} MKs were in it last time)" for slug, n in f.came_from]
            hints += [f"{slug} (name)" for slug in f.name_match if slug not in dict(f.came_from)]
            out.append(f"# {f.knesset_id} {f.name_he}: " + ("; ".join(hints) if hints else "no hint: probably a new party"))
            if not hints:
                out.append(f'# [party.<slug>]\n# he = "{f.name_he}"\n# ru = ""\n# en = ""\n# ar = ""\n# factions = [{f.knesset_id}]')
    if r.no_site_id:
        out.append("\n# --- src/hkv/names/curated/mk_names.toml: only for MKs `hkv names` could not link; site_id from "
                   "main.knesset.gov.il/mk/apps/mk/mk-personal-details/<site_id> ---")
        for pid, name in r.no_site_id:
            out.append(f"[mk.{pid}]  # {name}\nsite_id = ")
    return "\n".join(out)
