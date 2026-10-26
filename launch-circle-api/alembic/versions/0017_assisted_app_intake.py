"""Private customer intake with operator-reviewed first-app provisioning."""

import sqlalchemy as sa

from alembic import op

revision = "0017_assisted_app_intake"
down_revision = "0016_shared_tester_pool"
branch_labels = None
depends_on = None


def upgrade():
    if "app_intakes" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "app_intakes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("package_name", sa.String(255), nullable=False),
        sa.Column("developer_account_id", sa.String(64), nullable=False),
        sa.Column("workflow_steps", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("app_id", sa.String(36), sa.ForeignKey("apps.id", ondelete="SET NULL")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewer", sa.String(100)),
        sa.Column("proof_sha256", sa.String(64)),
        sa.Column("review_note", sa.Text()),
        sa.UniqueConstraint("owner_id", "package_name", name="uq_app_intake_owner_package"),
    )


def downgrade():
    op.drop_table("app_intakes")
