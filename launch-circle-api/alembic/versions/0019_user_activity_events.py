"""Add privacy-minimized user-flow diagnostics."""
import sqlalchemy as sa

from alembic import op

revision = "0019_user_activity_events"
down_revision = "0018_operator_console"
branch_labels = None
depends_on = None


def upgrade():
    if "user_activity_events" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "user_activity_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_name", sa.String(80), nullable=False),
        sa.Column("workflow", sa.String(40), nullable=False),
        sa.Column("object_type", sa.String(40), nullable=True),
        sa.Column("object_id", sa.String(36), nullable=True),
        sa.Column("outcome", sa.String(12), nullable=False),
        sa.Column("error_code", sa.String(40), nullable=True),
        sa.Column("support_summary", sa.String(240), nullable=False),
        sa.Column("request_id", sa.String(80), nullable=False),
        sa.Column("client_version", sa.String(32), nullable=True),
        sa.Column("platform", sa.String(12), nullable=False),
        sa.Column("device_type", sa.String(12), nullable=False),
        sa.Column("method", sa.String(8), nullable=False),
        sa.Column("route_template", sa.String(200), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("dedupe_key", sa.String(64), nullable=True),
        sa.UniqueConstraint("dedupe_key", name="uq_user_activity_dedupe_key"),
    )
    op.create_index("ix_user_activity_events_user_id", "user_activity_events", ["user_id"])
    op.create_index("ix_user_activity_events_request_id", "user_activity_events", ["request_id"])
    op.create_index("ix_user_activity_time", "user_activity_events", ["occurred_at"])
    op.create_index("ix_user_activity_user_time", "user_activity_events", ["user_id", "occurred_at"])
    op.create_index("ix_user_activity_event_time", "user_activity_events", ["event_name", "occurred_at"])
    op.create_index("ix_user_activity_result_time", "user_activity_events", ["outcome", "occurred_at"])


def downgrade():
    op.drop_table("user_activity_events")
