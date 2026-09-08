from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

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
            "testing_completed_at": "DATETIME",
            "production_ready_at": "DATETIME",
            "circle_id": "VARCHAR(36) REFERENCES circles(id) ON DELETE SET NULL",
            "google_group_mode": "VARCHAR(24) NOT NULL DEFAULT \x27LAUNCH_CIRCLE\x27",
            "google_group_configured": "BOOLEAN NOT NULL DEFAULT 0",
            "google_group_confirmed_at": "DATETIME",
        },
        "tester_assignments": {
            "circle_id": "VARCHAR(36) REFERENCES circles(id) ON DELETE SET NULL",
            "assignment_day": "DATE",
            "test_type": "VARCHAR(40) NOT NULL DEFAULT \'APP_CHECK\'",
            "health_status": "VARCHAR(16) NOT NULL DEFAULT \x27NEW\x27",
            "last_activity_at": "DATETIME",
            "overdue_mission_count": "INTEGER NOT NULL DEFAULT 0",
            "replacement_for_id": "VARCHAR(36) REFERENCES tester_assignments(id) ON DELETE SET NULL",
        },
        "invites": {
            "circle_id": "VARCHAR(36) REFERENCES circles(id) ON DELETE SET NULL",
            "expires_at": "DATETIME",
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
        # Backfill one durable owner circle and owner membership for existing
        # accounts, then associate legacy apps and invites with that circle.
        users = connection.exec_driver_sql('SELECT id, display_name FROM "users"').all()
        now = datetime.now(timezone.utc)
        for user_id, display_name in users:
            circle_id = connection.exec_driver_sql(
                'SELECT id FROM "circles" WHERE owner_id = :owner_id',
                {"owner_id": user_id},
            ).scalar()
            if circle_id is None:
                circle_id = str(uuid4())
                label = (display_name or "Developer").strip()
                connection.exec_driver_sql(
                    'INSERT INTO "circles" '
                    '(id, owner_id, name, max_members, created_at, updated_at) '
                    'VALUES (:id, :owner_id, :name, 15, :created_at, :updated_at)',
                    {
                        "id": circle_id,
                        "owner_id": user_id,
                        "name": f"{label}\'s Launch Circle",
                        "created_at": now,
                        "updated_at": now,
                    },
                )
            member_exists = connection.exec_driver_sql(
                'SELECT id FROM "circle_members" '
                'WHERE circle_id = :circle_id AND user_id = :user_id',
                {"circle_id": circle_id, "user_id": user_id},
            ).scalar()
            if member_exists is None:
                connection.exec_driver_sql(
                    'INSERT INTO "circle_members" '
                    '(id, circle_id, user_id, role, status, joined_at) '
                    'VALUES (:id, :circle_id, :user_id, \'OWNER\', \'ACTIVE\', :joined_at)',
                    {
                        "id": str(uuid4()),
                        "circle_id": circle_id,
                        "user_id": user_id,
                        "joined_at": now,
                    },
                )
            connection.exec_driver_sql(
                'UPDATE "apps" SET circle_id = :circle_id '
                'WHERE owner_id = :owner_id AND circle_id IS NULL',
                {"circle_id": circle_id, "owner_id": user_id},
            )
            connection.exec_driver_sql(
                'UPDATE "invites" SET circle_id = :circle_id '
                'WHERE inviter_id = :owner_id AND circle_id IS NULL',
                {"circle_id": circle_id, "owner_id": user_id},
            )
        connection.exec_driver_sql(
            'UPDATE "invites" SET expires_at = datetime(created_at, \'+7 days\') '
            'WHERE expires_at IS NULL'
        )
        connection.exec_driver_sql(
            'UPDATE "tester_assignments" SET circle_id = '
            '(SELECT circle_id FROM "apps" WHERE apps.id = tester_assignments.app_id) '
            'WHERE circle_id IS NULL'
        )
        connection.exec_driver_sql(
            'UPDATE "tester_assignments" SET assignment_day = date(assigned_at) '
            'WHERE assignment_day IS NULL'
        )
        connection.exec_driver_sql(
            'DROP INDEX IF EXISTS uq_active_assignment'
        )
        connection.exec_driver_sql(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_assignment_day '
            'ON "tester_assignments" (app_id, tester_id, assignment_day, test_type) '
            "WHERE status != 'DROPPED'"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_tester_assignments_replacement_for_id "
            "ON tester_assignments (replacement_for_id)"
        )
