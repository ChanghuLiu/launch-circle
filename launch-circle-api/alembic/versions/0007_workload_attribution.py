"""capture workload and acquisition attribution"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_workload_attribution"
down_revision: str | None = "0006_developer_accounts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("users"):
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "acquisition_source" not in columns:
            op.add_column(
                "users",
                sa.Column(
                    "acquisition_source",
                    sa.String(length=120),
                    nullable=False,
                    server_default=sa.text("'UNKNOWN'"),
                ),
            )
        if "acquisition_medium" not in columns:
            op.add_column("users", sa.Column("acquisition_medium", sa.String(length=120)))
        if "acquisition_campaign" not in columns:
            op.add_column("users", sa.Column("acquisition_campaign", sa.String(length=120)))
        if "attribution_captured_at" not in columns:
            op.add_column(
                "users",
                sa.Column("attribution_captured_at", sa.DateTime(timezone=True)),
            )
    inspector = sa.inspect(bind)
    if inspector.has_table("feedback"):
        columns = {column["name"] for column in inspector.get_columns("feedback")}
        if "time_spent_minutes" not in columns:
            op.add_column("feedback", sa.Column("time_spent_minutes", sa.Integer()))
    inspector = sa.inspect(bind)
    if not inspector.has_table("developer_coordination_logs"):
        op.create_table(
            "developer_coordination_logs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "app_id",
                sa.String(length=36),
                sa.ForeignKey("apps.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "owner_id",
                sa.String(length=36),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("minutes", sa.Integer(), nullable=False),
            sa.Column("category", sa.String(length=24), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.CheckConstraint(
                "minutes >= 1 AND minutes <= 480",
                name="ck_coordination_log_minutes",
            ),
            sa.CheckConstraint(
                "category IN ('COORDINATION','REPLACEMENT','RETEST','OTHER')",
                name="ck_coordination_log_category",
            ),
        )
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("developer_coordination_logs")}
    if "ix_developer_coordination_logs_app_id" not in indexes:
        op.create_index(
            "ix_developer_coordination_logs_app_id",
            "developer_coordination_logs",
            ["app_id"],
        )
    if "ix_developer_coordination_logs_owner_id" not in indexes:
        op.create_index(
            "ix_developer_coordination_logs_owner_id",
            "developer_coordination_logs",
            ["owner_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("developer_coordination_logs"):
        indexes = {index["name"] for index in inspector.get_indexes("developer_coordination_logs")}
        for index in (
            "ix_developer_coordination_logs_app_id",
            "ix_developer_coordination_logs_owner_id",
        ):
            if index in indexes:
                op.drop_index(index, table_name="developer_coordination_logs")
        op.drop_table("developer_coordination_logs")
    inspector = sa.inspect(bind)
    if inspector.has_table("feedback"):
        columns = {column["name"] for column in inspector.get_columns("feedback")}
        if "time_spent_minutes" in columns:
            op.drop_column("feedback", "time_spent_minutes")
    if sa.inspect(bind).has_table("users"):
        columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
        for column in (
            "attribution_captured_at",
            "acquisition_campaign",
            "acquisition_medium",
            "acquisition_source",
        ):
            if column in columns:
                op.drop_column("users", column)
