"""Voluntary shared supply. Neither preferences nor assignments prove Google enrollment."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
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
