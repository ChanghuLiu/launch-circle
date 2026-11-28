"""Add explicit voluntary pool consent and owner-published app listings."""

import sqlalchemy as sa

from alembic import op

revision = "0016_shared_tester_pool"
down_revision = "0015_cold_start_evidence"
branch_labels = None
depends_on = None


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "tester_pool_preferences" not in tables:
        op.create_table(
            "tester_pool_preferences",
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("consent_at", sa.DateTime(timezone=True)),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "pool_listings" not in tables:
        op.create_table(
            "pool_listings",
            sa.Column(
                "app_id",
                sa.String(36),
                sa.ForeignKey("apps.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade():
    op.drop_table("pool_listings")
    op.drop_table("tester_pool_preferences")
