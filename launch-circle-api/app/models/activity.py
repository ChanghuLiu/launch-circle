"""Privacy-minimized user flow diagnostics."""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserActivityEvent(Base):
    __tablename__ = "user_activity_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    event_name: Mapped[str] = mapped_column(String(80), nullable=False)
    workflow: Mapped[str] = mapped_column(String(40), nullable=False)
    object_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    object_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    outcome: Mapped[str] = mapped_column(String(12), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    support_summary: Mapped[str] = mapped_column(String(240), nullable=False)
    request_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    client_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    platform: Mapped[str] = mapped_column(String(12), nullable=False)
    device_type: Mapped[str] = mapped_column(String(12), nullable=False)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    route_template: Mapped[str] = mapped_column(String(200), nullable=False)
    status_code: Mapped[int] = mapped_column(nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)

    __table_args__ = (
        Index("ix_user_activity_time", "occurred_at"),
        Index("ix_user_activity_user_time", "user_id", "occurred_at"),
        Index("ix_user_activity_event_time", "event_name", "occurred_at"),
        Index("ix_user_activity_result_time", "outcome", "occurred_at"),
    )
