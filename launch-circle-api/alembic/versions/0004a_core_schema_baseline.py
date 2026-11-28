"""Create the application-owned schema omitted by the original runtime baseline.

The original 0001-0004 migrations covered identity and circles, while the app
and testing tables were created only by ORM startup. This frozen migration fills
that gap so Alembic can initialize an empty database without runtime startup.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004a_core_schema"
down_revision: str | None = "0004_lifecycle_timestamps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_index(bind, table: str, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in {item["name"] for item in inspector.get_indexes(table)} or name in {
        item.get("name") for item in inspector.get_unique_constraints(table)
    }


def upgrade() -> None:
    bind = op.get_bind()
    users_columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    # These identity fields were added to the runtime model after 0001. Fill
    # legacy rows from the already-unique login email before creating the index.
    if "email" not in users_columns:
        op.add_column("users", sa.Column("email", sa.String(320), nullable=False, server_default=""))
        bind.execute(
            sa.text("UPDATE users SET email = login_email WHERE email = :empty"),
            {"empty": ""},
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)
    if "password_hash" not in users_columns:
        op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    if "reliability_score" not in users_columns:
        op.add_column("users", sa.Column("reliability_score", sa.Integer(), nullable=False, server_default="0"))
    if "is_active" not in users_columns:
        op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "last_successful_test_at" not in users_columns:
        op.add_column("users", sa.Column("last_successful_test_at", sa.DateTime(timezone=True), nullable=True))

    if not sa.inspect(bind).has_table('developer_accounts'):
        op.create_table('developer_accounts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('play_developer_account_id', sa.String(length=64), nullable=False),
        sa.Column('identity_method', sa.String(length=24), server_default=sa.text("'USER_PROVIDED'"), nullable=False),
        sa.Column('verification_status', sa.String(length=24), server_default=sa.text("'UNVERIFIED'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('first_free_claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("identity_method IN ('USER_PROVIDED','PUBLIC_PUBLISHER')", name='ck_developer_accounts_identity_method'),
        sa.CheckConstraint("verification_status IN ('UNVERIFIED','VERIFIED')", name='ck_developer_accounts_verification_status'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('play_developer_account_id', name='uq_developer_accounts_play_developer_account_id')
        )
    if not sa.inspect(bind).has_table('apps'):
        op.create_table('apps',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('developer_account_id', sa.String(length=36), nullable=True),
        sa.Column('entitlement_status', sa.String(length=24), server_default=sa.text("'LEGACY'"), nullable=False),
        sa.Column('circle_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('package_name', sa.String(length=255), nullable=False),
        sa.Column('opt_in_url', sa.Text(), nullable=False),
        sa.Column('core_workflow_steps', sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column('google_group_url', sa.Text(), nullable=True),
        sa.Column('google_group_mode', sa.String(length=24), nullable=False),
        sa.Column('google_group_configured', sa.Boolean(), nullable=False),
        sa.Column('google_group_confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('tester_target', sa.Integer(), nullable=False),
        sa.Column('testing_start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('testing_end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('testing_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('production_ready_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('report_generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("entitlement_status IN ('LEGACY','FIRST_APP_FREE','ADDITIONAL_PAID','MANAGED')", name='ck_apps_entitlement_status'),
        sa.CheckConstraint("google_group_mode IN ('LAUNCH_CIRCLE','OWN_GROUP','EMAIL_LIST')", name='ck_apps_google_group_mode'),
        sa.CheckConstraint("status IN ('DRAFT','WAITING_FOR_TESTERS','TESTING','AT_RISK','TESTING_COMPLETE','PRODUCTION_READY')", name='ck_apps_status'),
        sa.CheckConstraint('tester_target > 0', name='ck_apps_tester_target'),
        sa.ForeignKeyConstraint(['circle_id'], ['circles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['developer_account_id'], ['developer_accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_index(bind, 'apps', 'ix_apps_circle_id'):
        op.create_index(op.f('ix_apps_circle_id'), 'apps', ['circle_id'], unique=False)
        op.create_index(op.f('ix_apps_developer_account_id'), 'apps', ['developer_account_id'], unique=False)
    if not _has_index(bind, 'apps', 'ix_apps_owner_id'):
        op.create_index(op.f('ix_apps_owner_id'), 'apps', ['owner_id'], unique=False)
        op.create_index(op.f('ix_apps_package_name'), 'apps', ['package_name'], unique=True)
    if not _has_index(bind, 'apps', 'uq_apps_first_app_free_per_developer_account'):
        op.create_index('uq_apps_first_app_free_per_developer_account', 'apps', ['developer_account_id'], unique=True, sqlite_where=sa.text("entitlement_status = 'FIRST_APP_FREE'"), postgresql_where=sa.text("entitlement_status = 'FIRST_APP_FREE'"))
        op.create_table('invites',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('inviter_id', sa.String(length=36), nullable=False),
        sa.Column('circle_id', sa.String(length=36), nullable=True),
        sa.Column('invite_code', sa.String(length=16), nullable=False),
        sa.Column('invited_email', sa.String(length=320), nullable=True),
        sa.Column('joined_user_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('PENDING','ACCEPTED','CANCELLED','EXPIRED')", name='ck_invites_status'),
        sa.ForeignKeyConstraint(['circle_id'], ['circles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['inviter_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['joined_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    if not _has_index(bind, 'invites', 'ix_invites_circle_id'):
        op.create_index(op.f('ix_invites_circle_id'), 'invites', ['circle_id'], unique=False)
        op.create_index(op.f('ix_invites_invite_code'), 'invites', ['invite_code'], unique=True)
    if not _has_index(bind, 'invites', 'ix_invites_inviter_id'):
        op.create_index(op.f('ix_invites_inviter_id'), 'invites', ['inviter_id'], unique=False)
        op.create_index(op.f('ix_invites_joined_user_id'), 'invites', ['joined_user_id'], unique=False)
    if not sa.inspect(bind).has_table('app_changes'):
        op.create_table('app_changes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('app_id', sa.String(length=36), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_index(bind, 'app_changes', 'ix_app_changes_app_id'):
        op.create_index(op.f('ix_app_changes_app_id'), 'app_changes', ['app_id'], unique=False)
        op.create_table('developer_coordination_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('app_id', sa.String(length=36), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('minutes', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=24), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("category IN ('COORDINATION','REPLACEMENT','RETEST','OTHER')", name='ck_coordination_log_category'),
        sa.CheckConstraint('minutes >= 1 AND minutes <= 480', name='ck_coordination_log_minutes'),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    if not _has_index(bind, 'developer_coordination_logs', 'ix_developer_coordination_logs_app_id'):
        op.create_index(op.f('ix_developer_coordination_logs_app_id'), 'developer_coordination_logs', ['app_id'], unique=False)
        op.create_index(op.f('ix_developer_coordination_logs_owner_id'), 'developer_coordination_logs', ['owner_id'], unique=False)
    if not sa.inspect(bind).has_table('tester_assignments'):
        op.create_table('tester_assignments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('app_id', sa.String(length=36), nullable=False),
        sa.Column('circle_id', sa.String(length=36), nullable=True),
        sa.Column('tester_id', sa.String(length=36), nullable=False),
        sa.Column('assignment_day', sa.Date(), nullable=True),
        sa.Column('test_type', sa.String(length=40), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('opted_in_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('installed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dropped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('health_status', sa.String(length=16), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('overdue_mission_count', sa.Integer(), nullable=False),
        sa.Column('replacement_for_id', sa.String(length=36), nullable=True),
        sa.CheckConstraint("health_status IN ('NEW','GOOD','AT_RISK','INACTIVE','DROPPED')", name='ck_assignments_health_status'),
        sa.CheckConstraint("status IN ('ASSIGNED','OPTED_IN','INSTALLED','ACTIVE','COMPLETED','DROPPED')", name='ck_assignments_status'),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['circle_id'], ['circles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['replacement_for_id'], ['tester_assignments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tester_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_index(bind, 'tester_assignments', 'ix_tester_assignments_app_id'):
        op.create_index(op.f('ix_tester_assignments_app_id'), 'tester_assignments', ['app_id'], unique=False)
        op.create_index(op.f('ix_tester_assignments_assignment_day'), 'tester_assignments', ['assignment_day'], unique=False)
    if not _has_index(bind, 'tester_assignments', 'ix_tester_assignments_circle_id'):
        op.create_index(op.f('ix_tester_assignments_circle_id'), 'tester_assignments', ['circle_id'], unique=False)
        op.create_index(op.f('ix_tester_assignments_replacement_for_id'), 'tester_assignments', ['replacement_for_id'], unique=False)
    if not _has_index(bind, 'tester_assignments', 'ix_tester_assignments_tester_id'):
        op.create_index(op.f('ix_tester_assignments_tester_id'), 'tester_assignments', ['tester_id'], unique=False)
        op.create_index('uq_assignment_day', 'tester_assignments', ['app_id', 'tester_id', 'assignment_day', 'test_type'], unique=True, sqlite_where=sa.text("status != 'DROPPED'"))
    if not sa.inspect(bind).has_table('backend_events'):
        op.create_table('backend_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('app_id', sa.String(length=36), nullable=False),
        sa.Column('assignment_id', sa.String(length=36), nullable=True),
        sa.Column('event_type', sa.String(length=40), nullable=False),
        sa.Column('dedupe_key', sa.String(length=160), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assignment_id'], ['tester_assignments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dedupe_key')
        )
    if not _has_index(bind, 'backend_events', 'ix_backend_events_app_id'):
        op.create_index(op.f('ix_backend_events_app_id'), 'backend_events', ['app_id'], unique=False)
        op.create_index(op.f('ix_backend_events_assignment_id'), 'backend_events', ['assignment_id'], unique=False)
    if not _has_index(bind, 'backend_events', 'ix_backend_events_event_type'):
        op.create_index(op.f('ix_backend_events_event_type'), 'backend_events', ['event_type'], unique=False)
        op.create_table('pilot_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('actor_user_id', sa.String(length=36), nullable=False),
        sa.Column('app_id', sa.String(length=36), nullable=True),
        sa.Column('assignment_id', sa.String(length=36), nullable=True),
        sa.Column('invite_id', sa.String(length=36), nullable=True),
        sa.Column('event_type', sa.String(length=40), nullable=False),
        sa.Column('dedupe_key', sa.String(length=180), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assignment_id'], ['tester_assignments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['invite_id'], ['invites.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dedupe_key')
    )
    if not _has_index(bind, 'pilot_events', 'ix_pilot_events_actor_user_id'):
        op.create_index(op.f('ix_pilot_events_actor_user_id'), 'pilot_events', ['actor_user_id'], unique=False)
        op.create_index(op.f('ix_pilot_events_app_id'), 'pilot_events', ['app_id'], unique=False)
    if not _has_index(bind, 'pilot_events', 'ix_pilot_events_assignment_id'):
        op.create_index(op.f('ix_pilot_events_assignment_id'), 'pilot_events', ['assignment_id'], unique=False)
        op.create_index(op.f('ix_pilot_events_event_type'), 'pilot_events', ['event_type'], unique=False)
    if not _has_index(bind, 'pilot_events', 'ix_pilot_events_invite_id'):
        op.create_index(op.f('ix_pilot_events_invite_id'), 'pilot_events', ['invite_id'], unique=False)
        op.create_table('test_missions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('assignment_id', sa.String(length=36), nullable=False),
        sa.Column('mission_type', sa.String(length=40), nullable=False),
        sa.Column('scheduled_day', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('PENDING','AVAILABLE','COMPLETED','MISSED')", name='ck_missions_status'),
        sa.ForeignKeyConstraint(['assignment_id'], ['tester_assignments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    if not _has_index(bind, 'test_missions', 'ix_test_missions_assignment_id'):
        op.create_index(op.f('ix_test_missions_assignment_id'), 'test_missions', ['assignment_id'], unique=False)
        op.create_index('uq_assignment_mission_day', 'test_missions', ['assignment_id', 'scheduled_day'], unique=True)
    if not sa.inspect(bind).has_table('feedback'):
        op.create_table('feedback',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('mission_id', sa.String(length=36), nullable=False),
        sa.Column('tester_id', sa.String(length=36), nullable=False),
        sa.Column('app_id', sa.String(length=36), nullable=False),
        sa.Column('launch_ok', sa.Boolean(), nullable=True),
        sa.Column('core_feature_ok', sa.String(length=12), nullable=True),
        sa.Column('completion_result', sa.String(length=32), nullable=True),
        sa.Column('time_spent_minutes', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('issue_text', sa.Text(), nullable=True),
        sa.Column('suggestion_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("completion_result IS NULL OR completion_result IN ('COMPLETED','COMPLETED_WITH_DIFFICULTY','COULD_NOT_COMPLETE')", name='ck_feedback_completion_result'),
        sa.CheckConstraint("core_feature_ok IS NULL OR core_feature_ok IN ('YES','PARTLY','NO')", name='ck_feedback_core_feature_ok'),
        sa.CheckConstraint('rating IS NULL OR (rating >= 1 AND rating <= 5)', name='ck_feedback_rating'),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['mission_id'], ['test_missions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tester_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
    if not _has_index(bind, 'feedback', 'ix_feedback_app_id'):
        op.create_index(op.f('ix_feedback_app_id'), 'feedback', ['app_id'], unique=False)
        op.create_index(op.f('ix_feedback_mission_id'), 'feedback', ['mission_id'], unique=True)
    if not _has_index(bind, 'feedback', 'ix_feedback_tester_id'):
        op.create_index(op.f('ix_feedback_tester_id'), 'feedback', ['tester_id'], unique=False)
        # ### end Alembic commands ###

def downgrade() -> None:
    # This baseline fills tables absent from the pre-Alembic ORM bootstrap.
    # Keep it irreversible so rollback cannot drop application records.
    pass
