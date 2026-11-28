"""Append-only pilot evidence, separate from legacy completion/health counters."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.launch import new_id, utcnow


class EnrollmentEvidence(Base):
    __tablename__ = "enrollment_evidence"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(36), unique=True, default=new_id)
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("tester_assignments.id", ondelete="CASCADE"), index=True
    )
    recorded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    event: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(24))
    note: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("event IN ('JOINED','LEFT','UNKNOWN')", name="ck_enrollment_event"),
        CheckConstraint(
            "source IN ('SELF_REPORTED','OWNER_CONFIRMED')", name="ck_enrollment_source"
        ),
    )


class MissionRun(Base):
    __tablename__ = "mission_runs"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(36), unique=True, default=new_id)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("test_missions.id", ondelete="CASCADE"), index=True
    )
    submitted_by_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    idempotency_key: Mapped[str] = mapped_column(String(80))
    payload_hash: Mapped[str] = mapped_column(String(64))
    execution_source: Mapped[str] = mapped_column(String(24))
    result: Mapped[str] = mapped_column(String(16))
    package_name: Mapped[str] = mapped_column(String(255))
    version_code: Mapped[int] = mapped_column(Integer)
    device_key: Mapped[str] = mapped_column(String(120))
    device_model: Mapped[str] = mapped_column(String(120))
    android_api: Mapped[int] = mapped_column(Integer)
    details: Mapped[dict] = mapped_column(JSON)
    retest_of_id: Mapped[str | None] = mapped_column(
        ForeignKey("mission_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("mission_id", "idempotency_key", name="uq_mission_run_request"),
        CheckConstraint(
            "execution_source IN ('HUMAN_MANUAL','CODEX_ASSISTED','AUTOMATED_RUNNER')",
            name="ck_mission_run_source",
        ),
        CheckConstraint(
            "result IN ('PASS','FAIL','BLOCKED','NOT_RUN')", name="ck_mission_run_result"
        ),
        CheckConstraint("version_code > 0 AND android_api > 0", name="ck_mission_run_build"),
    )


class MissionRunFix(Base):
    __tablename__ = "mission_run_fixes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("mission_runs.id", ondelete="CASCADE"), unique=True
    )
    recorded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    target_version_code: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (CheckConstraint("target_version_code > 0", name="ck_mission_run_fix_build"),)


class CampaignBuild(Base):
    __tablename__ = "campaign_builds"

    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), primary_key=True)
    version_code: Mapped[int] = mapped_column(Integer)
    recorded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (CheckConstraint("version_code > 0", name="ck_campaign_build_version"),)
