"""English and Russian names for members, factions and topics, attached to response models after the main query.

Models that carry a member, faction or topic mix in PersonNames / FactionNames / TopicLabels and say which attribute
holds the key. `fill_names(conn, payload, lang)` walks the response, looks all keys up in one query per kind and sets
the fields. Hebrew names stay in the endpoint queries; en/ru come from person_name (0006), faction_label and
topic_label. The display fields (`name`, `short`, `faction_name`, `label`) carry the name in the `?lang=` language,
falling back to Hebrew (docs/roadmap.md L8).
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, ClassVar, Literal

from fastapi import Query
from pydantic import BaseModel

Lang = Literal["he", "en", "ru"]


class PersonNames(BaseModel):
    _person_key: ClassVar[str] = "id"
    name: str | None = None          # in the requested language (?lang=), else Hebrew
    name_en: str | None = None
    name_ru: str | None = None


class FactionNames(BaseModel):
    """name_* = full name (e.g. the list name), short_* = for tables and charts."""
    _faction_key: ClassVar[str] = "id"
    _faction_prefix: ClassVar[str] = ""
    name: str | None = None          # in the requested language (?lang=), else Hebrew
    short: str | None = None
    name_ru: str | None = None
    short_ru: str | None = None
    name_en: str | None = None
    short_en: str | None = None
    short_he: str | None = None      # only where the official Hebrew name is a long list name


class BallotFactionNames(BaseModel):
    """Faction names on a model that also carries a member's names (fields prefixed faction_)."""
    _faction_key: ClassVar[str] = "faction_id"
    _faction_prefix: ClassVar[str] = "faction_"
    faction_name: str | None = None  # short name in the requested language (?lang=), else Hebrew
    faction_name_ru: str | None = None
    faction_short_ru: str | None = None
    faction_name_en: str | None = None
    faction_short_en: str | None = None
    faction_short_he: str | None = None


class TopicLabels(BaseModel):
    _topic_key: ClassVar[str] = "slug"
    label: str | None = None         # in the requested language (?lang=)
    label_en: str | None = None


def _walk(obj: Any, out: list[BaseModel]) -> None:
    if isinstance(obj, BaseModel):
        out.append(obj)
        for name in type(obj).model_fields:
            _walk(getattr(obj, name), out)
    elif isinstance(obj, dict):
        for v in obj.values():
            _walk(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _walk(v, out)


def fill_names(conn, payload: Any, lang: Lang = "he") -> Any:
    models: list[BaseModel] = []
    _walk(payload, models)
    people = [m for m in models if isinstance(m, PersonNames)]
    factions = [m for m in models if isinstance(m, (FactionNames, BallotFactionNames))]
    topics = [m for m in models if isinstance(m, TopicLabels)]
    pids = {getattr(m, m._person_key) for m in people} - {None}
    fids = {getattr(m, m._faction_key) for m in factions} - {None}
    if pids:
        found = {r["id"]: r for r in conn.execute(
            """SELECT p.knesset_person_id AS id, n.en, n.ru FROM person p JOIN person_name n ON n.person_id = p.id
               WHERE p.knesset_person_id = ANY(%s)""", (list(pids),))}
        for m in people:
            r = found.get(getattr(m, m._person_key))
            if r:
                m.name_en, m.name_ru = r["en"], r["ru"]
        for m in people:
            m.name = (lang != "he" and getattr(m, f"name_{lang}")) or getattr(m, "name_he", None)
    if fids:
        found = {r["id"]: r for r in conn.execute(
            """SELECT f.knesset_faction_id AS id, ru.name AS ru, ru.short_name AS ru_short, en.name AS en, en.short_name AS en_short,
                      he.short_name AS he_short
               FROM faction f LEFT JOIN faction_label ru ON ru.faction_id = f.id AND ru.language = 'ru'
               LEFT JOIN faction_label en ON en.faction_id = f.id AND en.language = 'en'
               LEFT JOIN faction_label he ON he.faction_id = f.id AND he.language = 'he'
               WHERE f.knesset_faction_id = ANY(%s)""", (list(fids),))}
        for m in factions:
            r = found.get(getattr(m, m._faction_key))
            if r:
                p = m._faction_prefix
                setattr(m, f"{p}name_ru", r["ru"])
                setattr(m, f"{p}short_ru", r["ru_short"] or r["ru"])
                setattr(m, f"{p}name_en", r["en"])
                setattr(m, f"{p}short_en", r["en_short"] or r["en"])
                setattr(m, f"{p}short_he", r["he_short"])
        for m in factions:
            p = m._faction_prefix
            he = getattr(m, f"{p}name_he", None)
            full = (lang != "he" and getattr(m, f"{p}name_{lang}")) or he
            short = getattr(m, f"{p}short_{lang}") or he
            if p:
                m.faction_name = short
            else:
                m.name, m.short = full, short
    slugs = {getattr(m, m._topic_key) for m in topics} - {None}
    if slugs:
        found = {(r["slug"], r["language"]): r["label"] for r in conn.execute(
            "SELECT t.slug, l.language, l.label FROM topic t JOIN topic_label l ON l.topic_id = t.id WHERE t.slug = ANY(%s)", (list(slugs),))}
        for m in topics:
            slug = getattr(m, m._topic_key)
            m.label_en = found.get((slug, "en"))
            m.label = found.get((slug, lang)) or found.get((slug, "he"))
    return payload


LANG_PARAM = inspect.Parameter(
    "lang", inspect.Parameter.KEYWORD_ONLY, annotation=Lang,
    default=Query("he", description="language of the display fields name / short / faction_name / label (Hebrew fallback)"))


def with_names(fn):
    """Endpoint decorator: fill en/ru names into the returned payload (the endpoint must take `conn`) and add the
    `?lang=` query parameter. The signature is resolved here so FastAPI does not evaluate string annotations in this
    module."""
    sig = inspect.signature(fn, eval_str=True)
    params = list(sig.parameters.values())
    params.insert(next((i for i, p in enumerate(params) if p.kind == p.VAR_KEYWORD), len(params)), LANG_PARAM)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        lang = kwargs.pop("lang", "he")
        result = fn(*args, **kwargs)
        return fill_names(kwargs["conn"], result, lang) if "conn" in kwargs else result

    wrapper.__signature__ = sig.replace(parameters=params)
    return wrapper
