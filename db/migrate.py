"""Apply db/migrations/*.sql in filename order, each once, each in its own transaction.

Usage: DATABASE_URL=postgresql://knesset:knesset@localhost:5433/knesset uv run db/migrate.py
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import psycopg

MIGRATIONS = Path(__file__).parent / "migrations"
DEFAULT_URL = "postgresql://knesset:knesset@localhost:5433/knesset"


def migrate(conninfo: str) -> list[str]:
    applied_now: list[str] = []
    with psycopg.connect(conninfo, autocommit=True) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migration (
                   name text PRIMARY KEY,
                   sha256 text NOT NULL,
                   applied_at timestamptz NOT NULL DEFAULT now())"""
        )
        done = dict(conn.execute("SELECT name, sha256 FROM schema_migration").fetchall())
        for path in sorted(MIGRATIONS.glob("*.sql")):
            sql = path.read_text(encoding="utf-8")
            digest = hashlib.sha256(sql.encode()).hexdigest()
            if path.name in done:
                if done[path.name] != digest:
                    raise RuntimeError(f"{path.name} was edited after being applied; add a new migration instead")
                continue
            with conn.transaction():
                conn.execute(sql)
                conn.execute("INSERT INTO schema_migration (name, sha256) VALUES (%s, %s)", (path.name, digest))
            applied_now.append(path.name)
    return applied_now


if __name__ == "__main__":
    for name in migrate(os.environ.get("DATABASE_URL", DEFAULT_URL)):
        print(f"applied {name}")
