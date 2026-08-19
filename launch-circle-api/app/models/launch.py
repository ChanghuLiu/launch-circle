from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class App(Base):
    __tablename__ = "apps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    package_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    opt_in_url: Mapped[str] = mapped_column(Text, nullable=False)
    google_group_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_group_mode: Mapped[str] = mapped_column(
        String(24), default="LAUNCH_CIRCLE", nullable=False
    )
    google_group_configured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    google_group_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="WAITING_FOR_TESTERS", nullable=False)
    tester_target: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    testing_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    testing_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    report_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    owner = relationship("User", back_populates="owned_apps")
    assignments = relationship(
        "TesterAssignment", back_populates="app", cascade="all, delete-orphan"
    )
    feedback_entries = relationship("Feedback", back_populates="app", cascade="all, delete-orphan")
    changes = relationship("AppChange", back_populates="app", cascade="all, delete-orphan")
    events = relationship("BackendEvent", back_populates="app", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','WAITING_FOR_TESTERS','TESTING','AT_RISK',"
            "'TESTING_COMPLETE','PRODUCTION_READY')",
            name="ck_apps_status",
        ),
        CheckConstraint("tester_target > 0", name="ck_apps_tester_target"),
        CheckConstraint(
            "google_group_mode IN (\x27LAUNCH_CIRCLE\x27,\x27OWN_GROUP\x27,\x27EMAIL_LIST\x27)",
            name="ck_apps_google_group_mode",
        ),
    )


class TesterAssignment(Base):
    __tablename__ = "tester_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), index=True)
    tester_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="ASSIGNED", nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    opted_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dropped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    health_status: Mapped[str] = mapped_column(String(16), default="NEW", nullable=False)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    overdue_mission_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    replacement_for_id: Mapped[str | None] = mapped_column(
        ForeignKey("tester_assignments.id", ondelete="SET NULL"), nullable=True, index=True
    )

    app = relationship("App", back_populates="assignments")
    tester = relationship("User", back_populates="assignments")
    missions = relationship(
        "TestMission", back_populates="assignment", cascade="all, delete-orphan"
    )
    replacement_for = relationship(
        "TesterAssignment", remote_side=[id], foreign_keys=[replacement_for_id]
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('ASSIGNED','OPTED_IN','INSTALLED','ACTIVE','COMPLETED','DROPPED')",
            name="ck_assignments_status",
        ),
        CheckConstraint(
            "health_status IN ('NEW','GOOD','AT_RISK','INACTIVE','DROPPED')",
            name="ck_assignments_health_status",
        ),
        Index(
            "uq_active_assignment",
            "app_id",
            "tester_id",
            unique=True,
            sqlite_where=text("status != 'DROPPED'"),
        ),
    )


class TestMission(Base):
    __tablename__ = "test_missions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("tester_assignments.id", ondelete="CASCADE"), index=True
    )
    mission_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scheduled_day: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assignment = relationship("TesterAssignment", back_populates="missions")
    feedback_entry = relationship(
        "Feedback", back_populates="mission", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','AVAILABLE','COMPLETED','MISSED')", name="ck_missions_status"
        ),
        Index("uq_assignment_mission_day", "assignment_id", "scheduled_day", unique=True),
    )


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("test_missions.id", ondelete="CASCADE"), unique=True, index=True
    )
    tester_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), index=True)
    launch_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    core_feature_ok: Mapped[str | None] = mapped_column(String(12), nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issue_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestion_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    mission = relationship("TestMission", back_populates="feedback_entry")
    tester = relationship("User", back_populates="feedback_entries")
    app = relationship("App", back_populates="feedback_entries")

    __table_args__ = (
        CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_feedback_rating"
        ),
        CheckConstraint(
            "core_feature_ok IS NULL OR core_feature_ok IN ('YES','PARTLY','NO')",
            name="ck_feedback_core_feature_ok",
        ),
    )


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    inviter_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    invited_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    joined_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    inviter = relationship("User", foreign_keys=[inviter_id], back_populates="sent_invites")
    joined_user = relationship(
        "User", foreign_keys=[joined_user_id], back_populates="accepted_invites"
    )

    __table_args__ = (
        CheckConstraint("status IN ('PENDING','ACCEPTED','CANCELLED')", name="ck_invites_status"),
    )


class AppChange(Base):
    __tablename__ = "app_changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    app = relationship("App", back_populates="changes")


class BackendEvent(Base):
    __tablename__ = "backend_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), index=True)
    assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("tester_assignments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    dedupe_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    app = relationship("App", back_populates="events")
    assignment = relationship("TesterAssignment", foreign_keys=[assignment_id])


class PilotEvent(Base):
    """Lightweight user/app events that are not always tied to an assignment."""

    __tablename__ = "pilot_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    app_id: Mapped[str | None] = mapped_column(
        ForeignKey("apps.id", ondelete="CASCADE"), nullable=True, index=True
    )
    assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("tester_assignments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    invite_id: Mapped[str | None] = mapped_column(
        ForeignKey("invites.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    dedupe_key: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
