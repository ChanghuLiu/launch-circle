"""store app workflows and structured mission outcomes"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_workflows_outcomes"
down_revision: str | None = "0004a_core_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(table)
    return column in {item["name"] for item in columns}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("apps") and not _has_column("apps", "core_workflow_steps"):
        op.add_column(
            "apps",
            sa.Column(
                "core_workflow_steps",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            ),
        )
    if inspector.has_table("feedback") and not _has_column("feedback", "completion_result"):
        op.add_column(
            "feedback",
            sa.Column("completion_result", sa.String(length=32), nullable=True),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("feedback") and _has_column("feedback", "completion_result"):
        op.drop_column("feedback", "completion_result")
    if inspector.has_table("apps") and _has_column("apps", "core_workflow_steps"):
        op.drop_column("apps", "core_workflow_steps")
