"""Member and faction names in he/en/ru (docs/roadmap.md L1, L2).

Members: link each person to the Knesset website ID, then take the official English and Russian names
from the website API. The link is made in this order, and the first match wins:
  1. curated/mk_names.toml   (hand-maintained `site_id`, for people the automatic steps cannot match)
  2. KNS_MkSiteCode          (official PersonID -> website ID; covers MKs up to ~2019)
  3. website's current MK list and its replacement list, matched by normalised Hebrew name
  4. Wikidata P9770 ("Knesset member ID" = website ID), matched by Hebrew label
If the website has no names for an ID, Wikidata labels are used (origin 'wikidata'); a curated name, when
present, is stored too (origin 'curated'). Wikidata alternative labels become search variants.

Factions: curated/factions.toml (ru/en full and short names per Knesset faction ID). For the current
Knesset, the website's official faction names are stored as well and win (view priority in 0006).
"""

from __future__ import annotations

import json
import logging
import re
import tomllib
import urllib.parse
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import psycopg

from hkv.sources.odata import ODataClient, Page
from hkv.topics import he_norm

log = logging.getLogger("hkv.names")
CURATED = Path(__file__).parent / "curated"
SITE_API = "https://knesset.gov.il/WebSiteApi/knessetapi"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
WIKIDATA_QUERY = """SELECT ?item ?kid ?he ?en ?ru
  (GROUP_CONCAT(DISTINCT ?enAlt; separator="|") AS ?enAlts) (GROUP_CONCAT(DISTINCT ?ruAlt; separator="|") AS ?ruAlts)
WHERE { ?item wdt:P9770 ?kid .
  OPTIONAL { ?item rdfs:label ?he FILTER(lang(?he) = "he") }
  OPTIONAL { ?item rdfs:label ?en FILTER(lang(?en) = "en") }
  OPTIONAL { ?item rdfs:label ?ru FILTER(lang(?ru) = "ru") }
  OPTIONAL { ?item skos:altLabel ?enAlt FILTER(lang(?enAlt) = "en") }
  OPTIONAL { ?item skos:altLabel ?ruAlt FILTER(lang(?ruAlt) = "ru") }
} GROUP BY ?item ?kid ?he ?en ?ru"""


@dataclass(frozen=True)
class SiteMk:
    site_id: int
    name_he: str


@dataclass(frozen=True)
class WikidataMk:
    qid: str
    site_id: int
    he: str | None
    en: str | None
    ru: str | None
    en_alts: tuple[str, ...]
    ru_alts: tuple[str, ...]


@dataclass(frozen=True)
class MkDetails:
    name: str | None
    faction: str | None
    photo: str | None = None


class NameSources(Protocol):
    def site_codes(self) -> dict[int, int]: ...                      # KNS person id -> website id
    def current_mks(self) -> list[SiteMk]: ...
    def wikidata_mks(self) -> list[WikidataMk]: ...
    def mk_details(self, site_id: int, lang: str) -> MkDetails | None: ...


class LiveSources:
    """Network sources; every response is kept under raw_dir like OData pages."""

    def __init__(self, raw_dir: Path | None, v4: ODataClient | None = None) -> None:
        self.v4 = v4 or ODataClient(raw_dir=raw_dir)
        self.http = ODataClient(base_url=SITE_API, source="knesset_site_api", raw_dir=raw_dir, delay_s=0.3, timeout_s=60)
        self._details: dict[tuple[int, str], MkDetails | None] = {}

    def _json(self, url: str, source: str, resource: str):
        body = self.http._get(url)
        self.http._store(Page(source, resource, url, body, []))
        return json.loads(body)

    def site_codes(self) -> dict[int, int]:
        return {int(r["KnsID"]): int(r["SiteId"]) for r in self.v4.rows("KNS_MkSiteCode", {}) if r.get("KnsID") and r.get("SiteId")}

    def current_mks(self) -> list[SiteMk]:
        """Current MKs plus everyone in the current Knesset's replacement list (MKs who left or entered mid-term)."""
        d = self._json(f"{SITE_API}/MKs/GetMks?languageKey=he", "knesset_site_api", "GetMks")
        out = {int(m["MkID"]): m["FullName"] for m in d["Mks"]}
        for r in d.get("ReplacedMks") or []:
            for key, name in (("mk_individual_id", "FullName"), ("mk_individual_replaced_id", "FullNameReplaced")):
                if r.get(key) and r.get(name):
                    out.setdefault(int(r[key]), r[name])
        return [SiteMk(k, v) for k, v in out.items()]

    def wikidata_mks(self) -> list[WikidataMk]:
        url = f"{WIKIDATA_SPARQL}?" + urllib.parse.urlencode({"query": WIKIDATA_QUERY, "format": "json"})
        d = self._json(url, "wikidata", "P9770")
        out = []
        for b in d["results"]["bindings"]:
            v = lambda k: b[k]["value"] if k in b and b[k]["value"] else None  # noqa: E731
            if not (v("kid") or "").isdigit():
                continue
            out.append(WikidataMk(qid=v("item").rsplit("/", 1)[-1], site_id=int(v("kid")), he=v("he"), en=v("en"), ru=v("ru"),
                                  en_alts=tuple(filter(None, (v("enAlts") or "").split("|"))),
                                  ru_alts=tuple(filter(None, (v("ruAlts") or "").split("|")))))
        return out

    def mk_details(self, site_id: int, lang: str) -> MkDetails | None:
        if (site_id, lang) not in self._details:
            self._details[(site_id, lang)] = self._fetch_details(site_id, lang)
        return self._details[(site_id, lang)]

    def _fetch_details(self, site_id: int, lang: str) -> MkDetails | None:
        d = self._json(f"{SITE_API}/MKs/GetMkdetailsHeader?mkId={site_id}&languageKey={lang}", "knesset_site_api", "GetMkdetailsHeader")
        if not d:
            return None
        photo = clean(d.get("MkImage")) or clean(d.get("LobbyImage"))
        return MkDetails(name=clean(d.get("Name")), faction=clean(d.get("Faction")),
                         photo=photo if photo and photo.startswith("https://") else None)


def clean(s: str | None) -> str | None:
    s = " ".join((s or "").split())
    return s or None


def strip_qualifier(label: str) -> str:
    """'אלי כהן (פוליטיקאי)' -> 'אלי כהן'"""
    return re.sub(r"\s*\([^)]*\)\s*$", "", label).strip()


def name_tokens(name: str) -> frozenset[str]:
    return frozenset(he_norm(name).replace("-", " ").split())


def load_curated() -> tuple[dict[int, dict], dict[int, dict]]:
    mks = tomllib.loads((CURATED / "mk_names.toml").read_text())
    factions = tomllib.loads((CURATED / "factions.toml").read_text())
    return ({int(k): v for k, v in mks.get("mk", {}).items()}, {int(k): v for k, v in factions.get("faction", {}).items()})


def match_by_name(name_he: str, candidates: dict[int, str]) -> int | None:
    """Unique candidate whose normalised name equals ours; otherwise a unique one whose tokens are a subset of ours
    (or ours of theirs) with at least two tokens in common, e.g. 'מירי מרים רגב' ~ 'מירי רגב'."""
    norm = he_norm(name_he)
    exact = [k for k, n in candidates.items() if he_norm(n) == norm]
    if len(exact) == 1:
        return exact[0]
    if exact:
        return None
    ours = name_tokens(name_he)
    loose = [k for k, n in candidates.items() if len(ours & (t := name_tokens(n))) >= 2 and (t <= ours or ours <= t)]
    return loose[0] if len(loose) == 1 else None


def open_issue(conn: psycopg.Connection, issue_type: str, entity_table: str, entity_id, external_ref: str, details: dict) -> None:
    if not conn.execute("""SELECT 1 FROM data_issue WHERE status = 'open' AND issue_type = %s AND entity_id IS NOT DISTINCT FROM %s""",
                        (issue_type, entity_id)).fetchone():
        conn.execute("""INSERT INTO data_issue (entity_table, entity_id, external_ref, issue_type, severity, details)
                        VALUES (%s, %s, %s, %s, 'warning', %s)""",
                     (entity_table, entity_id, external_ref, issue_type, json.dumps(details, ensure_ascii=False)))


def close_issue(conn: psycopg.Connection, issue_type: str, entity_id) -> None:
    conn.execute("""UPDATE data_issue SET status = 'resolved', resolved_at = now()
                    WHERE status = 'open' AND issue_type = %s AND entity_id = %s""", (issue_type, entity_id))


def _set_alias(conn: psycopg.Connection, person_id, language: str, name: str | None, alias_type: str, origin: str) -> int:
    name = clean(name)
    if not name:
        return 0
    return conn.execute("""INSERT INTO person_alias (person_id, language, full_name, alias_type, origin) VALUES (%s, %s, %s, %s, %s)
                           ON CONFLICT (person_id, language, full_name) DO NOTHING""",
                        (person_id, language, name, alias_type, origin)).rowcount


def sync_members(conn: psycopg.Connection, src: NameSources, *, refresh: bool = False) -> dict[str, int]:
    """Names for every person who has ballots. Without `refresh`, people who already have official names are skipped."""
    curated, _ = load_curated()
    people = conn.execute(
        """SELECT p.id, p.knesset_person_id, p.first_name_he || ' ' || p.last_name_he AS name_he,
                  (SELECT value FROM person_external_id e WHERE e.person_id = p.id AND e.scheme = 'knesset_site') AS site_id,
                  EXISTS (SELECT 1 FROM person_alias a WHERE a.person_id = p.id AND a.language = 'ru' AND a.alias_type = 'official'
                          AND a.origin IN ('official', 'curated', 'human')) AS named
           FROM person p WHERE EXISTS (SELECT 1 FROM ballot b WHERE b.person_id = p.id)""").fetchall()
    todo = [p for p in people if refresh or not p[4]]
    counts: Counter[str] = Counter(people=len(people), todo=len(todo))
    if not todo:
        return dict(counts)

    codes = src.site_codes()
    current = {m.site_id: m.name_he for m in src.current_mks()}
    wikidata = src.wikidata_mks()
    wd_by_site = {w.site_id: w for w in wikidata}
    wd_names = {w.site_id: strip_qualifier(w.he) for w in wikidata if w.he}
    taken = {int(r[0]) for r in conn.execute("SELECT value FROM person_external_id WHERE scheme = 'knesset_site'")}

    for pid, kid, name_he, site_id, _ in todo:
        method = "existing" if site_id else None
        site = int(site_id) if site_id else None
        if kid in curated and curated[kid].get("site_id"):
            site, method = int(curated[kid]["site_id"]), "curated"
        elif site is None and kid in codes:
            site, method = codes[kid], "kns_mksitecode"
        elif site is None and (m := match_by_name(name_he, {k: v for k, v in current.items() if k not in taken})):
            site, method = m, "site_current_list"
        elif site is None and (m := match_by_name(name_he, {k: v for k, v in wd_names.items() if k not in taken})):
            site, method = m, "wikidata_label"

        with conn.transaction():
            if site is not None and method != "existing":
                conn.execute("""INSERT INTO person_external_id (person_id, scheme, value, method) VALUES (%s, 'knesset_site', %s, %s)
                                ON CONFLICT (person_id, scheme) DO UPDATE SET value = EXCLUDED.value, method = EXCLUDED.method""",
                             (pid, str(site), method))
                taken.add(site)
            if site is not None:
                counts[f"site_id:{method}"] += 1
            wd = wd_by_site.get(site) if site is not None else None
            if wd:
                conn.execute("""INSERT INTO person_external_id (person_id, scheme, value, method) VALUES (%s, 'wikidata', %s, 'p9770')
                                ON CONFLICT DO NOTHING""", (pid, wd.qid))
            named: dict[str, str] = {}
            for lang in ("en", "ru"):
                det = src.mk_details(site, lang) if site is not None else None
                if det and det.name:
                    _set_alias(conn, pid, lang, det.name, "official", "official")
                    named[lang] = "official"
                elif wd and getattr(wd, lang):
                    _set_alias(conn, pid, lang, strip_qualifier(getattr(wd, lang)), "official", "wikidata")
                    named[lang] = "wikidata"
                if kid in curated and curated[kid].get(lang):
                    _set_alias(conn, pid, lang, curated[kid][lang], "official", "curated")
                    named.setdefault(lang, "curated")
                if det and det.photo:
                    counts["photos"] += _set_photo(conn, pid, det.photo)
            if wd:
                for alt in wd.en_alts:
                    counts["variants"] += _set_alias(conn, pid, "en", alt, "variant", "wikidata")
                for alt in wd.ru_alts:
                    counts["variants"] += _set_alias(conn, pid, "ru", alt, "variant", "wikidata")
            if site in current and he_norm(current[site]) != he_norm(name_he):
                _set_alias(conn, pid, "he", current[site], "variant", "official")
            for lang in ("en", "ru"):
                counts[f"{lang}:{named.get(lang, 'missing')}"] += 1
            if "en" in named and "ru" in named:
                close_issue(conn, "person_name_missing", pid)
            else:
                open_issue(conn, "person_name_missing", "person", pid, str(kid),
                           {"name_he": name_he, "site_id": site, "missing": [lg for lg in ("en", "ru") if lg not in named],
                            "fix": "add [mk.<knesset person id>] to src/hkv/names/curated/mk_names.toml"})
    log.info("member names: %s", dict(counts))
    return dict(counts)


def _set_photo(conn: psycopg.Connection, pid, url: str) -> int:
    return conn.execute("""INSERT INTO person_photo (person_id, url) VALUES (%s, %s) ON CONFLICT (person_id) DO UPDATE
                           SET url = EXCLUDED.url, fetched_at = now() WHERE person_photo.url <> EXCLUDED.url""", (pid, url)).rowcount


def sync_photos(conn: psycopg.Connection, src: NameSources) -> dict[str, int]:
    """Website photo URLs for members who have a website ID but no photo yet."""
    rows = conn.execute(
        """SELECT e.person_id, e.value FROM person_external_id e
           WHERE e.scheme = 'knesset_site' AND NOT EXISTS (SELECT 1 FROM person_photo ph WHERE ph.person_id = e.person_id)""").fetchall()
    counts: Counter[str] = Counter(todo=len(rows))
    for pid, site in rows:
        det = src.mk_details(int(site), "en")
        counts["photos" if det and det.photo and _set_photo(conn, pid, det.photo) else "none"] += 1
    log.info("member photos: %s", dict(counts))
    return dict(counts)


def sync_factions(conn: psycopg.Connection, src: NameSources | None = None) -> dict[str, int]:
    """Curated ru/en labels for every faction; official current-Knesset names from the website when `src` is given."""
    _, curated = load_curated()
    counts: Counter[str] = Counter()
    ids = {kid: fid for fid, kid in conn.execute("SELECT id, knesset_faction_id FROM faction")}
    with conn.transaction():
        for kid, entry in curated.items():
            fid = ids.get(kid)
            if fid is None:
                counts["curated_unknown_faction"] += 1
                continue
            for lang in ("ru", "en"):
                if entry.get(lang):
                    conn.execute("""INSERT INTO faction_label (faction_id, language, name, short_name, origin) VALUES (%s, %s, %s, %s, 'curated')
                                    ON CONFLICT (faction_id, language) DO UPDATE SET name = EXCLUDED.name, short_name = EXCLUDED.short_name, origin = 'curated'
                                    WHERE faction_label.origin IN ('machine', 'wikidata', 'curated')""",
                                 (fid, lang, entry[lang], entry.get(f"{lang}_short")))
                    counts[f"curated:{lang}"] += 1
            if entry.get("he_short"):
                conn.execute("""INSERT INTO faction_label (faction_id, language, name, short_name, origin)
                                SELECT id, 'he', btrim(name_he), %s, 'curated' FROM faction WHERE id = %s
                                ON CONFLICT (faction_id, language) DO UPDATE SET name = EXCLUDED.name, short_name = EXCLUDED.short_name""",
                             (entry["he_short"], fid))
                counts["curated:he_short"] += 1
        # nothing machine-made stays once a curated label exists for that language
        counts["machine_left"] = conn.execute("SELECT count(*) FROM faction_label WHERE origin = 'machine'").fetchone()[0]
    if src is not None:
        counts.update(_official_current_factions(conn, src))
    missing = conn.execute(
        """SELECT f.id, f.knesset_faction_id, f.name_he FROM faction f WHERE EXISTS (SELECT 1 FROM ballot b WHERE b.faction_id = f.id)
             AND NOT EXISTS (SELECT 1 FROM faction_label l WHERE l.faction_id = f.id AND l.language = 'en' AND l.origin <> 'machine')""").fetchall()
    for fid, kid, name in missing:
        open_issue(conn, "faction_name_missing", "faction", fid, str(kid),
                   {"name_he": name.strip(), "fix": "add [faction.<knesset faction id>] to src/hkv/names/curated/factions.toml"})
    counts["missing"] = len(missing)
    log.info("faction names: %s", dict(counts))
    return dict(counts)


def _official_current_factions(conn: psycopg.Connection, src: NameSources) -> dict[str, int]:
    """The website gives each current MK's faction name per language; take the most common name per open faction."""
    rows = conn.execute(
        """SELECT f.id, e.value FROM faction_membership fm JOIN faction f ON f.id = fm.faction_id
           JOIN person_external_id e ON e.person_id = fm.person_id AND e.scheme = 'knesset_site'
           WHERE upper(fm.valid) IS NULL AND f.term_number = (SELECT max(term_number) FROM faction)""").fetchall()
    names: dict[tuple, Counter] = defaultdict(Counter)
    for fid, site in rows:
        for lang in ("ru", "en"):
            det = src.mk_details(int(site), lang)
            if det and det.faction:
                names[(fid, lang)][det.faction] += 1
    n = 0
    with conn.transaction():
        for (fid, lang), c in names.items():
            name = c.most_common(1)[0][0]
            # the official full name replaces ours; the short name stays curated so a party reads the same across Knessets
            n += conn.execute("""INSERT INTO faction_label (faction_id, language, name, origin) VALUES (%s, %s, %s, 'official')
                                 ON CONFLICT (faction_id, language) DO UPDATE SET name = EXCLUDED.name, origin = 'official',
                                     short_name = CASE WHEN faction_label.origin = 'official' THEN faction_label.short_name
                                                       ELSE coalesce(faction_label.short_name, faction_label.name) END
                                 WHERE faction_label.origin <> 'human'""", (fid, lang, name)).rowcount
    return {"official_current": n}
