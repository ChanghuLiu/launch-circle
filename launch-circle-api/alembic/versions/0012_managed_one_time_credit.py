"""Create one-time Managed credits linked to Additional App Play purchases."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_managed_one_time_credit"
down_revision: str | None = "0010_google_play_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    missing_tables = {
        table
        for table in ("apps", "additional_app_purchases", "managed_checkouts")
        if not inspector.has_table(table)
    }
    if missing_tables:
        missing = ", ".join(sorted(missing_tables))
        raise RuntimeError(
            "Managed credit migration requires the core app and purchase tables first; "
            f"missing: {missing}"
        )

    op.create_table(
        "managed_credits",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("developer_account_id", sa.String(36), nullable=False),
        sa.Column("source_additional_app_purchase_id", sa.String(36), nullable=False),
        sa.Column("source_google_play_order_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(16), server_default="AVAILABLE", nullable=False),
        sa.Column("redeemed_app_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('AVAILABLE','REDEEMED')", name="ck_managed_credits_status"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["developer_account_id"], ["developer_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_additional_app_purchase_id"], ["additional_app_purchases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["redeemed_app_id"], ["apps.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_additional_app_purchase_id", name="uq_managed_credits_source_purchase"),
        sa.UniqueConstraint("source_google_play_order_id", name="uq_managed_credits_play_order_id"),
    )
    op.create_index("ix_managed_credits_owner_id", "managed_credits", ["owner_id"])
    op.create_index("ix_managed_credits_developer_account_id", "managed_credits", ["developer_account_id"])
    op.create_index("ix_managed_credits_owner_status", "managed_credits", ["owner_id", "status"])

    constraints = {item.get("name") for item in sa.inspect(bind).get_check_constraints("managed_checkouts")}
    with op.batch_alter_table("managed_checkouts", recreate="always" if bind.dialect.name == "sqlite" else "auto") as batch:
        if "ck_managed_checkouts_pricing" in constraints:
            batch.drop_constraint("ck_managed_checkouts_pricing", type_="check")
        batch.add_column(sa.Column("managed_credit_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("list_price_total", sa.Integer(), server_default="1500", nullable=False))
        batch.add_column(sa.Column("credit_amount", sa.Integer(), server_default="0", nullable=False))
        batch.create_foreign_key(
            "fk_managed_checkouts_managed_credit_id_managed_credits",
            "managed_credits", ["managed_credit_id"], ["id"], ondelete="CASCADE",
        )
        batch.create_check_constraint(
            "ck_managed_checkouts_pricing",
            "list_price_total = 1500 AND credit_amount IN (0,100) "
            "AND amount_total = list_price_total - credit_amount AND currency = 'usd' "
            "AND ((credit_amount = 0 AND managed_credit_id IS NULL) "
            "OR (credit_amount = 100 AND managed_credit_id IS NOT NULL))",
        )
    op.create_index("ix_managed_checkouts_managed_credit_id", "managed_checkouts", ["managed_credit_id"])
    op.create_index(
        "uq_managed_checkouts_pending_credit", "managed_checkouts", ["managed_credit_id"], unique=True,
        sqlite_where=sa.text("managed_credit_id IS NOT NULL AND status = 'PENDING'"),
        postgresql_where=sa.text("managed_credit_id IS NOT NULL AND status = 'PENDING'"),
    )


def downgrade() -> None:
    # Preserve one-time purchase and credit audit records on rollback.
    pass
