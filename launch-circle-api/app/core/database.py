from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def sqlite_database_path(database_url: str) -> Path | None:
    """Return the filesystem path for a file-backed SQLite URL."""
    url = make_url(database_url)
    if url.drivername != "sqlite" or not url.database or url.database == ":memory:":
        return None
    return Path(url.database).expanduser()


def ensure_sqlite_parent(database_url: str) -> Path | None:
    path = sqlite_database_path(database_url)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


settings = get_settings()
ensure_sqlite_parent(settings.database_url)
connect_args = {"check_same_thread": False, "timeout": 30} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        if sqlite_database_path(settings.database_url) is not None:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_sqlite_phase1_schema() -> None:
    """Additive upgrade for existing Phase 0/1 SQLite files."""
    if not settings.database_url.startswith("sqlite"):
        return
    additions = {
        "users": {
            "is_active": "BOOLEAN NOT NULL DEFAULT 1",
            "last_successful_test_at": "DATETIME",
        },
        "apps": {
            "report_generated_at": "DATETIME",
            "google_group_mode": "VARCHAR(24) NOT NULL DEFAULT \x27LAUNCH_CIRCLE\x27",
            "google_group_configured": "BOOLEAN NOT NULL DEFAULT 0",
            "google_group_confirmed_at": "DATETIME",
        },
        "tester_assignments": {
            "health_status": "VARCHAR(16) NOT NULL DEFAULT \x27NEW\x27",
            "last_activity_at": "DATETIME",
            "overdue_mission_count": "INTEGER NOT NULL DEFAULT 0",
            "replacement_for_id": "VARCHAR(36) REFERENCES tester_assignments(id) ON DELETE SET NULL",
        },
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            existing = {
                row[1]
                for row in connection.exec_driver_sql(f"PRAGMA table_info(\"{table}\")").all()
            }
            for column, definition in columns.items():
                if column not in existing:
                    connection.exec_driver_sql(
                        f"ALTER TABLE \"{table}\" ADD COLUMN \"{column}\" {definition}"
                    )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_tester_assignments_replacement_for_id "
            "ON tester_assignments (replacement_for_id)"
        )
