#!/usr/bin/env python3
"""Command-line entry point for verified Launch Circle SQLite backups."""

import argparse
import os
import sys
from pathlib import Path

from app.services.sqlite_backup import create_backup, database_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.getenv("SQLITE_DATABASE_URL", ""),
        help="SQLite SQLAlchemy URL (defaults to SQLITE_DATABASE_URL)",
    )
    parser.add_argument(
        "--destination",
        default=os.getenv("BACKUP_DESTINATION", "/var/backups/launch-circle"),
    )
    parser.add_argument(
        "--keep", type=int, default=int(os.getenv("BACKUP_RETENTION", "14"))
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if not args.database_url:
            raise ValueError("SQLITE_DATABASE_URL is required")
        backup = create_backup(
            database_path(args.database_url), Path(args.destination), args.keep
        )
    except Exception as exc:
        print(f"backup failed: {exc}", file=sys.stderr)
        return 1
    print(f"backup created: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
