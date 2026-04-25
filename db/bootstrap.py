from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR.parent / "app.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"
SEED_PATH = BASE_DIR / "seed.sql"


def read_sql(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {path}")

    return path.read_text(encoding="utf-8")


def bootstrap_database(
    db_path: Path = DEFAULT_DB_PATH,
    *,
    with_seed: bool = False,
    reset: bool = False,
) -> None:
    if reset and db_path.exists():
        db_path.unlink()

    schema_sql = read_sql(SCHEMA_PATH)
    seed_sql = read_sql(SEED_PATH) if with_seed else None

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(schema_sql)

        if seed_sql:
            conn.executescript(seed_sql)

        conn.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap the SQLite database from schema.sql and optional seed.sql."
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to SQLite database file.",
    )

    parser.add_argument(
        "--seed",
        action="store_true",
        help="Load starter seed data after creating schema.",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the existing database before bootstrapping.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    bootstrap_database(
        db_path=args.db,
        with_seed=args.seed,
        reset=args.reset,
    )

    print(f"Database bootstrapped successfully: {args.db}")


if __name__ == "__main__":
    main()
