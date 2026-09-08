"""persisted circles, memberships, and circle-scoped invites"""
from datetime import datetime, timedelta, timezone
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "0002_circles"
down_revision: Union[str, None] = "0001_phase01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if not _has_table("circles"):
        op.create_table(
            "circles",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("owner_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("max_members", sa.Integer(), nullable=False, server_default="15"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("max_members = 15", name="ck_circles_max_members"),
            sa.UniqueConstraint("owner_id"),
        )
        op.create_index("ix_circles_owner_id", "circles", ["owner_id"], unique=True)

    if not _has_table("circle_members"):
        op.create_table(
            "circle_members",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("circle_id", sa.String(length=36), sa.ForeignKey("circles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(length=16), nullable=False, server_default="MEMBER"),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
            sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("left_at", sa.DateTime(timezone=True)),
            sa.CheckConstraint("role IN ('OWNER','MEMBER')", name="ck_circle_members_role"),
            sa.CheckConstraint("status IN ('ACTIVE','LEFT','REMOVED')", name="ck_circle_members_status"),
            sa.UniqueConstraint("circle_id", "user_id", name="uq_circle_member_user"),
        )
        op.create_index("ix_circle_members_circle_id", "circle_members", ["circle_id"])
        op.create_index("ix_circle_members_user_id", "circle_members", ["user_id"])

    if _has_table("apps") and "circle_id" not in {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("apps")
    }:
        op.add_column(
            "apps",
            sa.Column("circle_id", sa.String(length=36), sa.ForeignKey("circles.id", ondelete="SET NULL")),
        )
        op.create_index("ix_apps_circle_id", "apps", ["circle_id"])

    if _has_table("invites"):
        invite_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("invites")}
        if "circle_id" not in invite_columns:
            op.add_column(
                "invites",
                sa.Column("circle_id", sa.String(length=36), sa.ForeignKey("circles.id", ondelete="SET NULL")),
            )
            op.create_index("ix_invites_circle_id", "invites", ["circle_id"])
        if "expires_at" not in invite_columns:
            op.add_column("invites", sa.Column("expires_at", sa.DateTime(timezone=True)))

    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    if _has_table("users"):
        users = bind.execute(sa.text('SELECT id, display_name FROM "users"')).all()
        for user_id, display_name in users:
            circle_id = bind.execute(
                sa.text('SELECT id FROM "circles" WHERE owner_id = :owner_id'),
                {"owner_id": user_id},
            ).scalar()
            if circle_id is None:
                circle_id = str(uuid4())
                label = (display_name or "Developer").strip()
                bind.execute(
                    sa.text(
                        'INSERT INTO "circles" '
                        '(id, owner_id, name, max_members, created_at, updated_at) '
                        'VALUES (:id, :owner_id, :name, 15, :created_at, :updated_at)'
                    ),
                    {"id": circle_id, "owner_id": user_id, "name": f"{label}'s Launch Circle", "created_at": now, "updated_at": now},
                )
            member = bind.execute(
                sa.text(
                    'SELECT id FROM "circle_members" '
                    'WHERE circle_id = :circle_id AND user_id = :user_id'
                ),
                {"circle_id": circle_id, "user_id": user_id},
            ).scalar()
            if member is None:
                bind.execute(
                    sa.text(
                        'INSERT INTO "circle_members" '
                        '(id, circle_id, user_id, role, status, joined_at) '
                        'VALUES (:id, :circle_id, :user_id, \'OWNER\', \'ACTIVE\', :joined_at)'
                    ),
                    {"id": str(uuid4()), "circle_id": circle_id, "user_id": user_id, "joined_at": now},
                )
            if _has_table("apps"):
                bind.execute(
                    sa.text('UPDATE "apps" SET circle_id = :circle_id WHERE owner_id = :owner_id AND circle_id IS NULL'),
                    {"circle_id": circle_id, "owner_id": user_id},
                )
            if _has_table("invites"):
                bind.execute(
                    sa.text('UPDATE "invites" SET circle_id = :circle_id WHERE inviter_id = :owner_id AND circle_id IS NULL'),
                    {"circle_id": circle_id, "owner_id": user_id},
                )
        if _has_table("invites"):
            # SQLite and PostgreSQL both accept the Python value for remaining rows.
            rows = bind.execute(sa.text('SELECT id, created_at FROM "invites" WHERE expires_at IS NULL')).all()
            for invite_id, created_at in rows:
                created = created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                bind.execute(
                    sa.text('UPDATE "invites" SET expires_at = :expires_at WHERE id = :id'),
                    {"expires_at": created + timedelta(days=7), "id": invite_id},
                )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table("invites"):
        columns = {column["name"] for column in sa.inspect(bind).get_columns("invites")}
        if "expires_at" in columns:
            op.drop_column("invites", "expires_at")
        if "circle_id" in columns:
            op.drop_index("ix_invites_circle_id", table_name="invites")
            op.drop_column("invites", "circle_id")
    if _has_table("apps"):
        columns = {column["name"] for column in sa.inspect(bind).get_columns("apps")}
        if "circle_id" in columns:
            op.drop_index("ix_apps_circle_id", table_name="apps")
            op.drop_column("apps", "circle_id")
    if _has_table("circle_members"):
        op.drop_table("circle_members")
    if _has_table("circles"):
        op.drop_table("circles")
