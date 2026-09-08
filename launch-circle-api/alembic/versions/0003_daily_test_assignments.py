"""add circle-scoped daily assignment identity"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_daily_assignments"
down_revision: Union[str, None] = "0002_circles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("tester_assignments"):
        return
    if not _has_column("tester_assignments", "circle_id"):
        op.add_column(
            "tester_assignments",
            sa.Column(
                "circle_id",
                sa.String(length=36),
                sa.ForeignKey("circles.id", ondelete="SET NULL"),
            ),
        )
        op.create_index("ix_tester_assignments_circle_id", "tester_assignments", ["circle_id"])
    if not _has_column("tester_assignments", "assignment_day"):
        op.add_column("tester_assignments", sa.Column("assignment_day", sa.Date()))
        op.create_index("ix_tester_assignments_assignment_day", "tester_assignments", ["assignment_day"])
    if not _has_column("tester_assignments", "test_type"):
        op.add_column(
            "tester_assignments",
            sa.Column("test_type", sa.String(length=40), nullable=False, server_default="APP_CHECK"),
        )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            'UPDATE "tester_assignments" SET circle_id = '
            '(SELECT circle_id FROM "apps" WHERE apps.id = tester_assignments.app_id) '
            'WHERE circle_id IS NULL'
        )
    )
    rows = bind.execute(
        sa.text('SELECT id, assigned_at FROM "tester_assignments" WHERE assignment_day IS NULL')
    ).all()
    for assignment_id, assigned_at in rows:
        if assigned_at is None:
            assigned_at = datetime.now(timezone.utc)
        if assigned_at.tzinfo is None:
            assigned_at = assigned_at.replace(tzinfo=timezone.utc)
        bind.execute(
            sa.text('UPDATE "tester_assignments" SET assignment_day = :day WHERE id = :id'),
            {"day": assigned_at.date(), "id": assignment_id},
        )

    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("tester_assignments")}
    if "uq_active_assignment" in indexes:
        op.drop_index("uq_active_assignment", table_name="tester_assignments")
    if "uq_assignment_day" not in indexes:
        op.create_index(
            "uq_assignment_day",
            "tester_assignments",
            ["app_id", "tester_id", "assignment_day", "test_type"],
            unique=True,
            postgresql_where=sa.text("status != 'DROPPED'"),
            sqlite_where=sa.text("status != 'DROPPED'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("tester_assignments"):
        return
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("tester_assignments")}
    if "uq_assignment_day" in indexes:
        op.drop_index("uq_assignment_day", table_name="tester_assignments")
    if not _has_column("tester_assignments", "test_type"):
        pass
    else:
        op.drop_column("tester_assignments", "test_type")
    if _has_column("tester_assignments", "assignment_day"):
        op.drop_index("ix_tester_assignments_assignment_day", table_name="tester_assignments")
        op.drop_column("tester_assignments", "assignment_day")
    if _has_column("tester_assignments", "circle_id"):
        op.drop_index("ix_tester_assignments_circle_id", table_name="tester_assignments")
        op.drop_column("tester_assignments", "circle_id")
    op.create_index(
        "uq_active_assignment",
        "tester_assignments",
        ["app_id", "tester_id"],
        unique=True,
        sqlite_where=sa.text("status != 'DROPPED'"),
    )
