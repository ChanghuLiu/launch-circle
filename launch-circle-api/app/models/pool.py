"""Voluntary shared supply. Neither preferences nor assignments prove Google enrollment."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TesterPoolPreference(Base):
    __tablename__ = "tester_pool_preferences"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PoolListing(Base):
    __tablename__ = "pool_listings"
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AppIntake(Base):
    __tablename__ = "app_intakes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    developer_account_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_steps: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    app_id: Mapped[str | None] = mapped_column(ForeignKey("apps.id", ondelete="SET NULL"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer: Mapped[str | None] = mapped_column(String(100))
    proof_sha256: Mapped[str | None] = mapped_column(String(64))
    review_note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("owner_id", "package_name", name="uq_app_intake_owner_package"),
    )


class AppGroup(Base):
    __tablename__ = "app_groups"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN", server_default="OPEN")


class AppGroupApp(Base):
    __tablename__ = "app_group_apps"
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("app_groups.id", ondelete="CASCADE"), index=True)


class AppGroupMember(Base):
    __tablename__ = "app_group_members"
    group_id: Mapped[str] = mapped_column(ForeignKey("app_groups.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AppGroupTaskQueue(Base):
    """Idempotent future task consent for a tester and peer app in a group."""

    __tablename__ = "app_group_task_queue"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("app_groups.id", ondelete="CASCADE"), nullable=False)
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), nullable=False)
    tester_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING", server_default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assignment_id: Mapped[str | None] = mapped_column(ForeignKey("tester_assignments.id", ondelete="SET NULL"))

    __table_args__ = (
        UniqueConstraint("group_id", "app_id", "tester_id", name="uq_app_group_task_queue_scope"),
        Index("ix_app_group_task_queue_user_status", "tester_id", "status", "created_at"),
        Index("ix_app_group_task_queue_group_status", "group_id", "status"),
    )
