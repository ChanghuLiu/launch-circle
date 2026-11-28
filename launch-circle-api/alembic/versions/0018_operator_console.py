"""Additive operator console tables."""
import sqlalchemy as sa

from alembic import op

revision = "0018_operator_console"
down_revision = "0017_assisted_app_intake"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "admin_sessions" not in existing:
        op.create_table("admin_sessions", sa.Column("token_hash", sa.String(64), primary_key=True),
                        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    if "admin_app_controls" not in existing:
        op.create_table(
            "admin_app_controls",
            sa.Column("app_id", sa.String(36), sa.ForeignKey("apps.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("kind", sa.String(20), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("paused", sa.Boolean(), nullable=False),
            sa.Column("note", sa.String(500), nullable=False),
        )
    if "admin_recommendations" not in existing:
        op.create_table(
            "admin_recommendations",
            sa.Column("app_id", sa.String(36), sa.ForeignKey("apps.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("tester_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "admin_audits" not in existing:
        op.create_table(
            "admin_audits", sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("action", sa.String(40), nullable=False),
            sa.Column("target_id", sa.String(100), nullable=False),
            sa.Column("detail", sa.JSON(), nullable=False),
        )


def downgrade():
    for name in ("admin_audits", "admin_recommendations", "admin_app_controls", "admin_sessions"):
        op.drop_table(name)
