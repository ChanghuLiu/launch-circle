"""Add Google Play Managed Launch checkout records."""

import sqlalchemy as sa
from alembic import op

revision: str = "0009_managed_credits_and_checkouts"
down_revision: str | None = "0008_additional_app_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "managed_checkouts",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("app_id", sa.String(36), nullable=False),
        sa.Column("google_play_purchase_token", sa.String(512), nullable=True),
        sa.Column("google_play_order_id", sa.String(255), nullable=True),
        sa.Column("google_play_product_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(16), server_default="PENDING", nullable=False),
        sa.Column("amount_total", sa.Integer(), server_default="1500", nullable=False),
        sa.Column("currency", sa.String(3), server_default="usd", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('PENDING','PAID','FAILED','EXPIRED')", name="ck_managed_checkouts_status"),
        sa.CheckConstraint("amount_total = 1500 AND currency = 'usd'", name="ck_managed_checkouts_pricing"),
        sa.ForeignKeyConstraint(["app_id"], ["apps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_play_purchase_token", name="uq_managed_checkouts_play_token"),
        sa.UniqueConstraint("google_play_order_id", name="uq_managed_checkouts_play_order_id"),
    )
    op.create_index("ix_managed_checkouts_app_id", "managed_checkouts", ["app_id"])
    op.create_index(
        "uq_managed_checkouts_pending_app", "managed_checkouts", ["app_id"], unique=True,
        sqlite_where=sa.text("status = 'PENDING'"), postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.create_index(
        "uq_managed_checkouts_paid_app", "managed_checkouts", ["app_id"], unique=True,
        sqlite_where=sa.text("status = 'PAID'"), postgresql_where=sa.text("status = 'PAID'"),
    )


def downgrade() -> None:
    op.drop_table("managed_checkouts")
