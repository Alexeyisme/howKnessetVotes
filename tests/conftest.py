from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "db"))
from migrate import DEFAULT_URL, migrate  # noqa: E402

ADMIN_URL = os.environ.get("DATABASE_URL", DEFAULT_URL)


@pytest.fixture(scope="session")
def new_database():
    """Factory: create an empty, migrated throwaway database; all are dropped at session end."""
    created: list[str] = []

    def make(migrated: bool = True) -> str:
        name = f"test_{uuid.uuid4().hex[:12]}"
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(f"CREATE DATABASE {name}")
        created.append(name)
        url = psycopg.conninfo.make_conninfo(ADMIN_URL, dbname=name)
        if migrated:
            migrate(url)
        return url

    yield make
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        for name in created:
            admin.execute(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")


@pytest.fixture(scope="session")
def db_url(new_database):
    return new_database(migrated=False)


@pytest.fixture(scope="session")
def migrated(db_url):
    assert migrate(db_url) == ["0001_core.sql", "0002_source_realities.sql", "0003_legacy_votes.sql", "0004_legacy_fuzzy_names.sql", "0005_topics_search.sql", "0006_names.sql", "0007_official_law_topics.sql", "0008_person_photo.sql", "0009_faction_label_he.sql", "0010_coalition_parties.sql", "0011_vote_bloc.sql", "0012_arabic.sql", "0013_text_translation.sql", "0014_person_photo_image.sql", "0015_bill_documents.sql", "0016_person_photo_sizes.sql"]
    return db_url
