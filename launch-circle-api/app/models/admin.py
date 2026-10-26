"""Operator access, dispatch preferences and audit; never Google eligibility proof."""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AdminSession(Base):
    __tablename__ = "admin_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdminAppControl(Base):
    __tablename__ = "admin_app_controls"
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), default="UNCLASSIFIED", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str] = mapped_column(String(500), default="", nullable=False)


class AdminRecommendation(Base):
    __tablename__ = "admin_recommendations"
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), primary_key=True)
    tester_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdminAudit(Base):
    __tablename__ = "admin_audits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False)
