"""Read-only, fail-closed feature capability negotiation."""

from fastapi import APIRouter, Depends
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter()
SUPPORTED_REVISION = "0021_group_task_queue"


@router.get("/capabilities")
def capabilities(db: Session = Depends(get_db)) -> dict:  # noqa: B008 - FastAPI dependency injection
    """Report only capabilities proven by the current schema revision.

    This endpoint intentionally performs no writes and is not included in user
    activity logging. Any missing/unknown database state is reported as false.
    """
    revision = None
    supported = False
    try:
        revisions = db.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        inspector = inspect(db.get_bind())
        app_columns = {column["name"] for column in inspector.get_columns("apps")}
        group_columns = {column["name"] for column in inspector.get_columns("app_groups")}
        tables = set(inspector.get_table_names())
        if len(revisions) == 1:
            revision = revisions[0]
        supported = (
            revision == SUPPORTED_REVISION
            and {"ownership_authorized", "ownership_attestation_status"}.issubset(app_columns)
            and "status" in group_columns
            and "app_group_task_queue" in tables
        )
    except (SQLAlchemyError, KeyError):
        # Missing migration metadata or schema inspection errors must never
        # accidentally enable new client write paths.
        revision = None
        supported = False
    return {
        "schema_version": 1,
        "migration_revision": revision,
        "capabilities": {
            "owner_attestation": supported,
            "app_group_selection": supported,
        },
    }
