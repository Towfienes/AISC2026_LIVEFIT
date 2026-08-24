"""Tiny, dependable SQL migration runner (acceptance E1-02: up AND down work).

Migrations are ``NNNN_name.up.sql`` / ``NNNN_name.down.sql`` files packaged in
:mod:`livelift.migrations`. State lives in the ``schema_migrations`` table.

    livelift-migrate up            # apply all pending
    livelift-migrate down [N]      # roll back N migrations (default 1)
    livelift-migrate status
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from importlib import resources

import psycopg

from livelift.config import get_settings

_NAME_RE = re.compile(r"^(\d{4})_(.+)\.(up|down)\.sql$")


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    up_sql: str
    down_sql: str


def load_migrations() -> list[Migration]:
    files: dict[tuple[int, str], dict[str, str]] = {}
    root = resources.files("livelift.migrations")
    for entry in root.iterdir():
        m = _NAME_RE.match(entry.name)
        if not m:
            continue
        version, name, direction = int(m.group(1)), m.group(2), m.group(3)
        files.setdefault((version, name), {})[direction] = entry.read_text(encoding="utf-8")
    migrations = []
    for (version, name), sqls in sorted(files.items()):
        if "up" not in sqls or "down" not in sqls:
            raise RuntimeError(f"migration {version:04d}_{name} missing up or down file")
        migrations.append(Migration(version, name, sqls["up"], sqls["down"]))
    versions = [m.version for m in migrations]
    if len(versions) != len(set(versions)):
        raise RuntimeError("duplicate migration versions")
    return migrations


def _ensure_table(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    integer PRIMARY KEY,
            name       text NOT NULL,
            applied_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


def applied_versions(conn: psycopg.Connection) -> list[int]:
    _ensure_table(conn)
    rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    return [r[0] for r in rows]


def migrate_up(conn: psycopg.Connection, migrations: list[Migration]) -> list[int]:
    done = set(applied_versions(conn))
    applied = []
    for m in migrations:
        if m.version in done:
            continue
        with conn.transaction():
            conn.execute(m.up_sql)  # type: ignore[arg-type]
            conn.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
                (m.version, m.name),
            )
        applied.append(m.version)
    return applied


def migrate_down(
    conn: psycopg.Connection, migrations: list[Migration], steps: int = 1
) -> list[int]:
    done = applied_versions(conn)
    by_version = {m.version: m for m in migrations}
    rolled = []
    for version in reversed(done[-steps:] if steps else []):
        m = by_version.get(version)
        if m is None:
            raise RuntimeError(f"no local files for applied migration {version}")
        with conn.transaction():
            conn.execute(m.down_sql)  # type: ignore[arg-type]
            conn.execute("DELETE FROM schema_migrations WHERE version = %s", (version,))
        rolled.append(version)
    return rolled


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="livelift-migrate", description=__doc__)
    parser.add_argument("command", choices=["up", "down", "status"])
    parser.add_argument("steps", nargs="?", type=int, default=1)
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args(argv)

    url = args.database_url or get_settings().database_url
    migrations = load_migrations()
    with psycopg.connect(url) as conn:
        if args.command == "up":
            applied = migrate_up(conn, migrations)
            print(f"applied: {applied or 'nothing (up to date)'}")
        elif args.command == "down":
            rolled = migrate_down(conn, migrations, args.steps)
            print(f"rolled back: {rolled or 'nothing'}")
        else:
            done = set(applied_versions(conn))
            for m in migrations:
                mark = "x" if m.version in done else " "
                print(f"[{mark}] {m.version:04d} {m.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
