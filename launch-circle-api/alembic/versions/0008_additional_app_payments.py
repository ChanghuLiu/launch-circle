"""Track Google Play purchases that grant additional app entitlements."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_additional_app_payments"
down_revision: str | None = "0007_workload_attribution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "additional_app_purchases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("developer_account_id", sa.String(36), sa.ForeignKey("developer_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("google_play_purchase_token", sa.String(512), nullable=True),
        sa.Column("google_play_order_id", sa.String(255), nullable=True),
        sa.Column("google_play_product_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(16), server_default="PENDING", nullable=False),
        sa.Column("amount_total", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("app_id", sa.String(36), sa.ForeignKey("apps.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('PENDING','PAID','CONSUMED','FAILED','EXPIRED')", name="ck_additional_app_purchases_status"),
        sa.UniqueConstraint("google_play_purchase_token", name="uq_additional_app_purchases_play_token"),
        sa.UniqueConstraint("google_play_order_id", name="uq_additional_app_purchases_play_order_id"),
        sa.UniqueConstraint("app_id", name="uq_additional_app_purchases_app"),
    )
    op.create_index("ix_additional_app_purchases_owner_id", "additional_app_purchases", ["owner_id"])
    op.create_index("ix_additional_app_purchases_developer_account_id", "additional_app_purchases", ["developer_account_id"])
    op.create_index("ix_additional_app_purchases_owner_status", "additional_app_purchases", ["owner_id", "developer_account_id", "status"])


def downgrade() -> None:
    op.drop_table("additional_app_purchases")
