"""Payment milestone marker; Google Play is the only payment provider."""


revision: str = "0010_google_play_billing"
down_revision: str | None = "0009_managed_credits_and_checkouts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
