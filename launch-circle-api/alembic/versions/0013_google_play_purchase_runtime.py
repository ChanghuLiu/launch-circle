"""Add Google Play purchase identifiers to the purchase tables."""

import sqlalchemy as sa

from alembic import op

revision: str = "0013_google_play_purchase_runtime"
down_revision: str | None = "0012_managed_one_time_credit"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    result = {index["name"] for index in inspector.get_indexes(table)}
    result.update(
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table)
        if constraint.get("name")
    )
    return result


def _has_unique_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if any(
        constraint.get("column_names") == [column]
        for constraint in inspector.get_unique_constraints(table)
    ):
        return True
    return any(
        index.get("unique") and index.get("column_names") == [column]
        for index in inspector.get_indexes(table)
    )


def _upgrade_table(table: str) -> None:
    columns = _columns(table)
    with op.batch_alter_table(table) as batch:
        if "google_play_purchase_token" not in columns:
            batch.add_column(sa.Column("google_play_purchase_token", sa.String(512), nullable=True))
        if "google_play_order_id" not in columns:
            batch.add_column(sa.Column("google_play_order_id", sa.String(255), nullable=True))
        if "google_play_product_id" not in columns:
            batch.add_column(sa.Column("google_play_product_id", sa.String(255), nullable=True))
    if not _has_unique_column(table, "google_play_purchase_token"):
        op.create_index(
            "uq_" + table + "_play_purchase_token",
            table,
            ["google_play_purchase_token"],
            unique=True,
        )
    if not _has_unique_column(table, "google_play_order_id"):
        op.create_index(
            "uq_" + table + "_play_order_id", table, ["google_play_order_id"], unique=True
        )


def upgrade() -> None:
    _upgrade_table("additional_app_purchases")
    _upgrade_table("managed_checkouts")
    if "source_google_play_order_id" not in _columns("managed_credits"):
        op.add_column(
            "managed_credits",
            sa.Column("source_google_play_order_id", sa.String(255), nullable=True),
        )
    if "uq_managed_credits_play_order_id" not in _indexes("managed_credits"):
        op.create_index(
            "uq_managed_credits_play_order_id",
            "managed_credits",
            ["source_google_play_order_id"],
            unique=True,
        )


def downgrade() -> None:
    # Purchase records must remain verifiable after rolling application code back.
    pass
