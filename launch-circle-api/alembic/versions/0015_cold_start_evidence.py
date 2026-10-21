"""Add isolated pilot enrollment, build and immutable run evidence."""

import sqlalchemy as sa

from alembic import op

revision = "0015_cold_start_evidence"
down_revision = "0014_publisher_unlimited_app_entitlement"
branch_labels = None
depends_on = None


def upgrade():
    # Runtime create_all may already have created these additive tables.
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "enrollment_evidence" not in tables:
        op.create_table(
            "enrollment_evidence",
            sa.Column("sequence", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("id", sa.String(36), nullable=False, unique=True),
            sa.Column("assignment_id", sa.String(36), sa.ForeignKey(
                "tester_assignments.id", ondelete="CASCADE"), nullable=False),
            sa.Column("recorded_by_id", sa.String(36), sa.ForeignKey(
                "users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("event", sa.String(16), nullable=False),
            sa.Column("source", sa.String(24), nullable=False),
            sa.Column("note", sa.Text(), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("event IN ('JOINED','LEFT','UNKNOWN')",
                               name="ck_enrollment_event"),
            sa.CheckConstraint("source IN ('SELF_REPORTED','OWNER_CONFIRMED')",
                               name="ck_enrollment_source"),
        )
        op.create_index("ix_enrollment_evidence_assignment_id", "enrollment_evidence",
                        ["assignment_id"])
    if "mission_runs" not in tables:
        op.create_table(
            "mission_runs",
            sa.Column("sequence", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("id", sa.String(36), nullable=False, unique=True),
            sa.Column("mission_id", sa.String(36), sa.ForeignKey(
                "test_missions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("submitted_by_id", sa.String(36), sa.ForeignKey(
                "users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("idempotency_key", sa.String(80), nullable=False),
            sa.Column("payload_hash", sa.String(64), nullable=False),
            sa.Column("execution_source", sa.String(24), nullable=False),
            sa.Column("result", sa.String(16), nullable=False),
            sa.Column("package_name", sa.String(255), nullable=False),
            sa.Column("version_code", sa.Integer(), nullable=False),
            sa.Column("device_key", sa.String(120), nullable=False),
            sa.Column("device_model", sa.String(120), nullable=False),
            sa.Column("android_api", sa.Integer(), nullable=False),
            sa.Column("details", sa.JSON(), nullable=False),
            sa.Column("retest_of_id", sa.String(36), sa.ForeignKey(
                "mission_runs.id", ondelete="SET NULL"), nullable=True),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("mission_id", "idempotency_key", name="uq_mission_run_request"),
            sa.CheckConstraint(
                "execution_source IN ('HUMAN_MANUAL','CODEX_ASSISTED','AUTOMATED_RUNNER')",
                name="ck_mission_run_source"),
            sa.CheckConstraint("result IN ('PASS','FAIL','BLOCKED','NOT_RUN')",
                               name="ck_mission_run_result"),
            sa.CheckConstraint("version_code > 0 AND android_api > 0",
                               name="ck_mission_run_build"),
        )
        op.create_index("ix_mission_runs_mission_id", "mission_runs", ["mission_id"])
        op.create_index("ix_mission_runs_retest_of_id", "mission_runs", ["retest_of_id"])
    if "mission_run_fixes" not in tables:
        op.create_table(
            "mission_run_fixes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("run_id", sa.String(36), sa.ForeignKey(
                "mission_runs.id", ondelete="CASCADE"), unique=True, nullable=False),
            sa.Column("recorded_by_id", sa.String(36), sa.ForeignKey(
                "users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("target_version_code", sa.Integer(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("target_version_code > 0", name="ck_mission_run_fix_build"),
        )
    if "campaign_builds" not in tables:
        op.create_table(
            "campaign_builds",
            sa.Column("app_id", sa.String(36), sa.ForeignKey(
                "apps.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("version_code", sa.Integer(), nullable=False),
            sa.Column("recorded_by_id", sa.String(36), sa.ForeignKey(
                "users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("version_code > 0", name="ck_campaign_build_version"),
        )


def downgrade():
    for table in ("campaign_builds", "mission_run_fixes", "mission_runs", "enrollment_evidence"):
        op.drop_table(table)
