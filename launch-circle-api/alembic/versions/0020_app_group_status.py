"""Add explicit App Group availability state."""

import sqlalchemy as sa

from alembic import op

revision = "0020_app_group_status"
down_revision = "0019_user_activity_events"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "app_groups" not in tables:
        op.create_table(
            "app_groups",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="OPEN"),
        )
        tables.add("app_groups")
    elif "status" not in {column["name"] for column in inspector.get_columns("app_groups")}:
        op.add_column(
            "app_groups",
            sa.Column("status", sa.String(16), nullable=False, server_default="OPEN"),
        )
    op.execute("UPDATE app_groups SET status = 'OPEN' WHERE status IS NULL OR status = ''")

    if "app_group_apps" not in tables:
        op.create_table(
            "app_group_apps",
            sa.Column(
                "app_id",
                sa.String(36),
                sa.ForeignKey("apps.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "group_id",
                sa.String(36),
                sa.ForeignKey("app_groups.id", ondelete="CASCADE"),
                nullable=False,
            ),
        )
    if "ix_app_group_apps_group_id" not in {
        index["name"] for index in inspector.get_indexes("app_group_apps")
    }:
        op.create_index("ix_app_group_apps_group_id", "app_group_apps", ["group_id"])
    if "app_group_members" not in tables:
        op.create_table(
            "app_group_members",
            sa.Column(
                "group_id",
                sa.String(36),
                sa.ForeignKey("app_groups.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("app_groups")}
    if "status" in columns:
        op.drop_column("app_groups", "status")
