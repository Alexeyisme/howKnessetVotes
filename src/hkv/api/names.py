"""English and Russian names for members and factions, attached to response models after the main query.

Models that carry a member or faction mix in PersonNames / FactionNames and say which attribute holds the
Knesset ID. `fill_names(conn, payload)` walks the response, looks all IDs up in two queries and sets the
fields. Hebrew names stay in the endpoint queries; en/ru come from person_name (0006) and faction_label.
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, ClassVar

from pydantic import BaseModel


class PersonNames(BaseModel):
    _person_key: ClassVar[str] = "id"
    name_en: str | None = None
    name_ru: str | None = None


class FactionNames(BaseModel):
    """name_* = full name (e.g. the list name), short_* = for tables and charts."""
    _faction_key: ClassVar[str] = "id"
    _faction_prefix: ClassVar[str] = ""
    name_ru: str | None = None
    short_ru: str | None = None
    name_en: str | None = None
    short_en: str | None = None


class BallotFactionNames(BaseModel):
    """Faction names on a model that also carries a member's names (fields prefixed faction_)."""
    _faction_key: ClassVar[str] = "faction_id"
    _faction_prefix: ClassVar[str] = "faction_"
    faction_name_ru: str | None = None
    faction_short_ru: str | None = None
    faction_name_en: str | None = None
    faction_short_en: str | None = None


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


def fill_names(conn, payload: Any) -> Any:
    models: list[BaseModel] = []
    _walk(payload, models)
    people = [m for m in models if isinstance(m, PersonNames)]
    factions = [m for m in models if isinstance(m, (FactionNames, BallotFactionNames))]
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
    if fids:
        found = {r["id"]: r for r in conn.execute(
            """SELECT f.knesset_faction_id AS id, ru.name AS ru, ru.short_name AS ru_short, en.name AS en, en.short_name AS en_short
               FROM faction f LEFT JOIN faction_label ru ON ru.faction_id = f.id AND ru.language = 'ru'
               LEFT JOIN faction_label en ON en.faction_id = f.id AND en.language = 'en'
               WHERE f.knesset_faction_id = ANY(%s)""", (list(fids),))}
        for m in factions:
            r = found.get(getattr(m, m._faction_key))
            if r:
                p = m._faction_prefix
                setattr(m, f"{p}name_ru", r["ru"])
                setattr(m, f"{p}short_ru", r["ru_short"] or r["ru"])
                setattr(m, f"{p}name_en", r["en"])
                setattr(m, f"{p}short_en", r["en_short"] or r["en"])
    return payload


def with_names(fn):
    """Endpoint decorator: fill en/ru names into the returned payload (the endpoint must take `conn`).
    The signature is resolved here so FastAPI does not evaluate string annotations in this module."""
    sig = inspect.signature(fn, eval_str=True)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        return fill_names(kwargs["conn"], result) if "conn" in kwargs else result

    wrapper.__signature__ = sig
    return wrapper
