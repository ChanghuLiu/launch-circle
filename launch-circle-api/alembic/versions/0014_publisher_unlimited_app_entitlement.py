"""Allow verified first-party publishers to register unlimited apps."""

from alembic import op

revision: str = "0014_publisher_unlimited_app_entitlement"
down_revision: str | None = "0013_google_play_purchase_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("apps") as batch:
        batch.drop_constraint("ck_apps_entitlement_status", type_="check")
        batch.create_check_constraint(
            "ck_apps_entitlement_status",
            "entitlement_status IN ('LEGACY','FIRST_APP_FREE','ADDITIONAL_PAID','MANAGED','PUBLISHER_UNLIMITED')",
        )


def downgrade() -> None:
    # Keep the expanded constraint: publisher-unlimited app records may exist.
    pass
