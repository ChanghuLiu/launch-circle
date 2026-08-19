from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    google_subject: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    login_email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tester_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    tester_email_sharing_consent: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    tester_email_sharing_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    reliability_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_successful_test_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    languages_csv: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    owned_apps = relationship("App", back_populates="owner", cascade="all, delete-orphan")
    assignments = relationship(
        "TesterAssignment", back_populates="tester", cascade="all, delete-orphan"
    )
    feedback_entries = relationship(
        "Feedback", back_populates="tester", cascade="all, delete-orphan"
    )
    sent_invites = relationship(
        "Invite",
        foreign_keys="Invite.inviter_id",
        back_populates="inviter",
        cascade="all, delete-orphan",
    )
    accepted_invites = relationship(
        "Invite", foreign_keys="Invite.joined_user_id", back_populates="joined_user"
    )
