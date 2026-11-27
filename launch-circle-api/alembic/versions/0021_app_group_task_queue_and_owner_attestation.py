"""Queue consented App Group tasks and store owner attestations."""

import sqlalchemy as sa

from alembic import op

revision = "0021_group_task_queue"
down_revision = "0020_app_group_status"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    app_columns = {column["name"] for column in inspector.get_columns("apps")}
    if "ownership_authorized" not in app_columns:
        op.add_column(
            "apps",
            sa.Column("ownership_authorized", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if "ownership_attested_at" not in app_columns:
        op.add_column("apps", sa.Column("ownership_attested_at", sa.DateTime(timezone=True)))
    if "ownership_attestation_status" not in app_columns:
        op.add_column(
            "apps",
            sa.Column(
                "ownership_attestation_status",
                sa.String(32),
                nullable=False,
                server_default="PENDING_ATTESTATION",
            ),
        )
    op.execute(
        "UPDATE apps SET ownership_attestation_status = "
        "CASE WHEN ownership_authorized = 1 THEN 'CONFIRMED' "
        "ELSE 'PENDING_ATTESTATION' END"
    )

    if "app_group_task_queue" not in set(inspector.get_table_names()):
        op.create_table(
            "app_group_task_queue",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("group_id", sa.String(36), sa.ForeignKey("app_groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("app_id", sa.String(36), sa.ForeignKey("apps.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tester_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("dispatched_at", sa.DateTime(timezone=True)),
            sa.Column("assignment_id", sa.String(36), sa.ForeignKey("tester_assignments.id", ondelete="SET NULL")),
            sa.UniqueConstraint("group_id", "app_id", "tester_id", name="uq_app_group_task_queue_scope"),
        )
        op.create_index(
            "ix_app_group_task_queue_user_status",
            "app_group_task_queue",
            ["tester_id", "status", "created_at"],
        )
        op.create_index(
            "ix_app_group_task_queue_group_status",
            "app_group_task_queue",
            ["group_id", "status"],
        )

    # Also install the guard when upgrading from an earlier local 0020 build
    # that already had the status column but not the legacy-write trigger.
    if op.get_bind().dialect.name == "sqlite":
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_no_group_join_without_owner_attestation
            BEFORE INSERT ON app_group_apps
            WHEN EXISTS (
                SELECT 1 FROM apps WHERE id = NEW.app_id AND ownership_authorized = 0
            )
            BEGIN
                SELECT RAISE(ABORT, 'APP_OWNER_ATTESTATION_REQUIRED');
            END
        """)
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_no_assignment_without_owner_attestation
            BEFORE INSERT ON tester_assignments
            WHEN EXISTS (
                SELECT 1 FROM apps WHERE id = NEW.app_id AND ownership_authorized = 0
            )
            BEGIN
                SELECT RAISE(ABORT, 'APP_OWNER_ATTESTATION_REQUIRED');
            END
        """)
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_no_new_assignment_for_closed_app_group
            BEFORE INSERT ON tester_assignments
            WHEN EXISTS (
                SELECT 1 FROM app_group_apps AS group_app
                JOIN app_groups AS group_row ON group_row.id = group_app.group_id
                WHERE group_app.app_id = NEW.app_id AND group_row.status = 'CLOSED'
            )
            BEGIN
                SELECT RAISE(ABORT, 'APP_GROUP_CLOSED');
            END
        """)
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_two_new_assignments_per_user_day
            BEFORE INSERT ON tester_assignments
            WHEN NEW.assignment_day IS NOT NULL AND (
                SELECT COUNT(*) FROM tester_assignments
                WHERE tester_id = NEW.tester_id
                  AND assignment_day = NEW.assignment_day
            ) >= 2
            BEGIN
                SELECT RAISE(ABORT, 'DAILY_ASSIGNMENT_LIMIT_REACHED');
            END
        """)


def downgrade():
    inspector = sa.inspect(op.get_bind())
    bind = op.get_bind()
    closed_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM app_groups WHERE status = 'CLOSED'")
    ).scalar_one()
    queue_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM app_group_task_queue")
    ).scalar_one() if "app_group_task_queue" in set(inspector.get_table_names()) else 0
    attested_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM apps WHERE ownership_authorized = 1")
    ).scalar_one() if "ownership_authorized" in {c["name"] for c in inspector.get_columns("apps")} else 0
    if closed_count or queue_count or attested_count:
        raise RuntimeError(
            "Refusing to remove App Group queue/attestation schema while CLOSED groups, "
            "queued tasks, or owner declarations exist; retain the expanded database schema "
            "for application rollback."
        )
    if "app_group_task_queue" in set(inspector.get_table_names()):
        op.drop_table("app_group_task_queue")
    if bind.dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_no_assignment_without_owner_attestation")
        op.execute("DROP TRIGGER IF EXISTS trg_no_group_join_without_owner_attestation")
        op.execute("DROP TRIGGER IF EXISTS trg_two_new_assignments_per_user_day")
    app_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("apps")}
    with op.batch_alter_table("apps") as batch:
        if "ownership_attested_at" in app_columns:
            batch.drop_column("ownership_attested_at")
        if "ownership_attestation_status" in app_columns:
            batch.drop_column("ownership_attestation_status")
        if "ownership_authorized" in app_columns:
            batch.drop_column("ownership_authorized")
