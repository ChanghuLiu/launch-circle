"""Create and retain verified SQLite backups without copying a live database file."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import make_url


def database_path(database_url: str) -> Path:
    url = make_url(database_url)
    if url.drivername != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("SQLITE_DATABASE_URL must identify a file-backed SQLite database")
    return Path(url.database).expanduser().resolve()


def create_backup(source: Path, destination: Path, keep: int = 14) -> Path:
    source = source.resolve()
    destination = destination.resolve()
    if keep < 1:
        raise ValueError("retention must be at least 1")
    if not source.is_file():
        raise FileNotFoundError(f"live database not found: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    if destination == source.parent:
        raise ValueError("backup destination must differ from the live database directory")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    final_path = destination / f"launch_circle-{timestamp}.db"
    temporary_path = destination / f".{final_path.name}.tmp"
    if final_path.exists() or temporary_path.exists():
        raise FileExistsError(f"backup path collision: {final_path}")

    try:
        with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as source_db:
            with sqlite3.connect(temporary_path) as backup_db:
                source_db.backup(backup_db)
                result = backup_db.execute("PRAGMA integrity_check").fetchone()
                if result != ("ok",):
                    raise RuntimeError(f"backup integrity check failed: {result}")
        temporary_path.replace(final_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    backups = sorted(destination.glob("launch_circle-*.db"), reverse=True)
    for expired in backups[keep:]:
        expired.unlink()
    return final_path
