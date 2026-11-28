"""add developer account identity and first-app entitlement"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_developer_accounts"
down_revision: str | None = "0005_workflows_outcomes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("developer_accounts"):
        op.create_table(
            "developer_accounts",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("play_developer_account_id", sa.String(length=64), nullable=False),
            sa.Column(
                "identity_method",
                sa.String(length=24),
                nullable=False,
                server_default=sa.text("'USER_PROVIDED'"),
            ),
            sa.Column(
                "verification_status",
                sa.String(length=24),
                nullable=False,
                server_default=sa.text("'UNVERIFIED'"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("first_free_claimed_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "identity_method IN ('USER_PROVIDED','PUBLIC_PUBLISHER')",
                name="ck_developer_accounts_identity_method",
            ),
            sa.CheckConstraint(
                "verification_status IN ('UNVERIFIED','VERIFIED')",
                name="ck_developer_accounts_verification_status",
            ),
            sa.UniqueConstraint(
                "play_developer_account_id",
                name="uq_developer_accounts_play_developer_account_id",
            ),
        )
    inspector = sa.inspect(bind)
    if inspector.has_table("apps"):
        columns = {column["name"] for column in inspector.get_columns("apps")}
        if "developer_account_id" not in columns:
            op.add_column(
                "apps",
                sa.Column(
                    "developer_account_id",
                    sa.String(length=36),
                    nullable=True,
                ),
            )
        if "entitlement_status" not in columns:
            op.add_column(
                "apps",
                sa.Column(
                    "entitlement_status",
                    sa.String(length=24),
                    nullable=False,
                    server_default=sa.text("'LEGACY'"),
                ),
            )
        indexes = {index["name"] for index in inspector.get_indexes("apps")}
        if "ix_apps_developer_account_id" not in indexes:
            op.create_index("ix_apps_developer_account_id", "apps", ["developer_account_id"])
        if "uq_apps_first_app_free_per_developer_account" not in indexes:
            op.create_index(
                "uq_apps_first_app_free_per_developer_account",
                "apps",
                ["developer_account_id"],
                unique=True,
                sqlite_where=sa.text("entitlement_status = 'FIRST_APP_FREE'"),
                postgresql_where=sa.text("entitlement_status = 'FIRST_APP_FREE'"),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("apps"):
        indexes = {index["name"] for index in inspector.get_indexes("apps")}
        if "ix_apps_developer_account_id" in indexes:
            op.drop_index("ix_apps_developer_account_id", table_name="apps")
        if "uq_apps_first_app_free_per_developer_account" in indexes:
            op.drop_index("uq_apps_first_app_free_per_developer_account", table_name="apps")
        columns = {column["name"] for column in inspector.get_columns("apps")}
        if "entitlement_status" in columns:
            op.drop_column("apps", "entitlement_status")
        if "developer_account_id" in columns:
            op.drop_column("apps", "developer_account_id")
    if sa.inspect(bind).has_table("developer_accounts"):
        op.drop_table("developer_accounts")
