"""persist server-controlled lifecycle completion timestamps"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_lifecycle_timestamps"
down_revision: Union[str, None] = "0003_daily_assignments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("apps"):
        return
    if not _has_column("apps", "testing_completed_at"):
        op.add_column("apps", sa.Column("testing_completed_at", sa.DateTime(timezone=True)))
    if not _has_column("apps", "production_ready_at"):
        op.add_column("apps", sa.Column("production_ready_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("apps"):
        return
    if _has_column("apps", "production_ready_at"):
        op.drop_column("apps", "production_ready_at")
    if _has_column("apps", "testing_completed_at"):
        op.drop_column("apps", "testing_completed_at")
