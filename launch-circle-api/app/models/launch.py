from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class DeveloperAccount(Base):
    __tablename__ = "developer_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    play_developer_account_id: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    identity_method: Mapped[str] = mapped_column(
        String(24), default="USER_PROVIDED", server_default=text("'USER_PROVIDED'"), nullable=False
    )
    verification_status: Mapped[str] = mapped_column(
        String(24), default="UNVERIFIED", server_default=text("'UNVERIFIED'"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    first_free_claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    apps = relationship("App", back_populates="developer_account")

    __table_args__ = (
        UniqueConstraint(
            "play_developer_account_id",
            name="uq_developer_accounts_play_developer_account_id",
        ),
        CheckConstraint(
            "identity_method IN ('USER_PROVIDED','PUBLIC_PUBLISHER')",
            name="ck_developer_accounts_identity_method",
        ),
        CheckConstraint(
            "verification_status IN ('UNVERIFIED','VERIFIED')",
            name="ck_developer_accounts_verification_status",
        ),
    )


class App(Base):
    __tablename__ = "apps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    developer_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("developer_accounts.id", ondelete="SET NULL"), index=True, nullable=True
    )
    entitlement_status: Mapped[str] = mapped_column(
        String(24), default="LEGACY", server_default=text("'LEGACY'"), nullable=False
    )
    circle_id: Mapped[str | None] = mapped_column(
        ForeignKey("circles.id", ondelete="SET NULL"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    package_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    opt_in_url: Mapped[str] = mapped_column(Text, nullable=False)
    core_workflow_steps: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    google_group_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_group_mode: Mapped[str] = mapped_column(
        String(24), default="LAUNCH_CIRCLE", nullable=False
    )
    google_group_configured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    google_group_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="WAITING_FOR_TESTERS", nullable=False)
    tester_target: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    testing_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    testing_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    testing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    production_ready_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
    developer_account = relationship("DeveloperAccount", back_populates="apps")
    circle = relationship("Circle", back_populates="apps")
    assignments = relationship(
        "TesterAssignment", back_populates="app", cascade="all, delete-orphan"
    )
    feedback_entries = relationship("Feedback", back_populates="app", cascade="all, delete-orphan")
    changes = relationship("AppChange", back_populates="app", cascade="all, delete-orphan")
    events = relationship("BackendEvent", back_populates="app", cascade="all, delete-orphan")
    coordination_logs = relationship(
        "DeveloperCoordinationLog", back_populates="app", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "entitlement_status IN ('LEGACY','FIRST_APP_FREE','ADDITIONAL_PAID','MANAGED','PUBLISHER_UNLIMITED')",
            name="ck_apps_entitlement_status",
        ),
        Index(
            "uq_apps_first_app_free_per_developer_account",
            "developer_account_id",
            unique=True,
            sqlite_where=text("entitlement_status = 'FIRST_APP_FREE'"),
            postgresql_where=text("entitlement_status = 'FIRST_APP_FREE'"),
        ),
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


class AdditionalAppPurchase(Base):
    __tablename__ = "additional_app_purchases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    developer_account_id: Mapped[str] = mapped_column(
        ForeignKey("developer_accounts.id", ondelete="CASCADE"), index=True
    )
    google_play_purchase_token: Mapped[str | None] = mapped_column(String(512), unique=True, nullable=True)
    google_play_order_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    google_play_product_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default="PENDING", server_default=text("'PENDING'"), nullable=False
    )
    amount_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    app_id: Mapped[str | None] = mapped_column(
        ForeignKey("apps.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','PAID','CONSUMED','FAILED','EXPIRED')",
            name="ck_additional_app_purchases_status",
        ),
        Index(
            "ix_additional_app_purchases_owner_status",
            "owner_id",
            "developer_account_id",
            "status",
        ),
    )


class ManagedCredit(Base):
    """A single Managed Launch discount earned from one paid Additional App test payment."""

    __tablename__ = "managed_credits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    developer_account_id: Mapped[str] = mapped_column(
        ForeignKey("developer_accounts.id", ondelete="CASCADE"), index=True
    )
    source_additional_app_purchase_id: Mapped[str] = mapped_column(
        ForeignKey("additional_app_purchases.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    source_google_play_order_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default="AVAILABLE", server_default=text("'AVAILABLE'"), nullable=False
    )
    redeemed_app_id: Mapped[str | None] = mapped_column(
        ForeignKey("apps.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('AVAILABLE','REDEEMED')", name="ck_managed_credits_status"),
        Index("ix_managed_credits_owner_status", "owner_id", "status"),
    )


class ManagedCheckout(Base):
    """A one-time Google Play Managed Launch purchase for one app."""

    __tablename__ = "managed_checkouts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), index=True)
    managed_credit_id: Mapped[str | None] = mapped_column(
        ForeignKey("managed_credits.id", ondelete="CASCADE"), nullable=True, index=True
    )
    google_play_purchase_token: Mapped[str | None] = mapped_column(String(512), unique=True, nullable=True)
    google_play_order_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    google_play_product_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default="PENDING", server_default=text("'PENDING'"), nullable=False
    )
    list_price_total: Mapped[int] = mapped_column(Integer, default=1500, server_default=text("1500"), nullable=False)
    amount_total: Mapped[int] = mapped_column(Integer, default=1500, nullable=False)
    credit_amount: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','PAID','FAILED','EXPIRED')",
            name="ck_managed_checkouts_status",
        ),
        CheckConstraint(
            "list_price_total = 1500 AND credit_amount IN (0,100) "
            "AND amount_total = list_price_total - credit_amount AND currency = 'usd' "
            "AND ((credit_amount = 0 AND managed_credit_id IS NULL) "
            "OR (credit_amount = 100 AND managed_credit_id IS NOT NULL))",
            name="ck_managed_checkouts_pricing",
        ),
        Index(
            "uq_managed_checkouts_pending_credit",
            "managed_credit_id",
            unique=True,
            sqlite_where=text("managed_credit_id IS NOT NULL AND status = 'PENDING'"),
            postgresql_where=text("managed_credit_id IS NOT NULL AND status = 'PENDING'"),
        ),
        Index(
            "uq_managed_checkouts_pending_app",
            "app_id",
            unique=True,
            sqlite_where=text("status = 'PENDING'"),
            postgresql_where=text("status = 'PENDING'"),
        ),
        Index(
            "uq_managed_checkouts_paid_app",
            "app_id",
            unique=True,
            sqlite_where=text("status = 'PAID'"),
            postgresql_where=text("status = 'PAID'"),
        ),
    )


class TesterAssignment(Base):
    __tablename__ = "tester_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), index=True)
    circle_id: Mapped[str | None] = mapped_column(
        ForeignKey("circles.id", ondelete="SET NULL"), index=True, nullable=True
    )
    tester_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    assignment_day: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    test_type: Mapped[str] = mapped_column(String(40), default="APP_CHECK", nullable=False)
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
    circle = relationship("Circle")
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
            "uq_assignment_day",
            "app_id",
            "tester_id",
            "assignment_day",
            "test_type",
            unique=True,
            sqlite_where=text("status != 'DROPPED'"),
        ),
    )

    @property
    def tester_user_id(self) -> str:
        return self.tester_id

    @tester_user_id.setter
    def tester_user_id(self, value: str) -> None:
        self.tester_id = value


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
    completion_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    time_spent_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
        CheckConstraint(
            "completion_result IS NULL OR completion_result IN "
            "('COMPLETED','COMPLETED_WITH_DIFFICULTY','COULD_NOT_COMPLETE')",
            name="ck_feedback_completion_result",
        ),
    )


class DeveloperCoordinationLog(Base):
    __tablename__ = "developer_coordination_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    app = relationship("App", back_populates="coordination_logs")
    owner = relationship("User")

    __table_args__ = (
        CheckConstraint("minutes >= 1 AND minutes <= 480", name="ck_coordination_log_minutes"),
        CheckConstraint(
            "category IN ('COORDINATION','REPLACEMENT','RETEST','OTHER')",
            name="ck_coordination_log_category",
        ),
    )


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    inviter_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    circle_id: Mapped[str | None] = mapped_column(
        ForeignKey("circles.id", ondelete="SET NULL"), index=True, nullable=True
    )
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    invited_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    joined_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    inviter = relationship("User", foreign_keys=[inviter_id], back_populates="sent_invites")
    circle = relationship("Circle", back_populates="invites")
    joined_user = relationship(
        "User", foreign_keys=[joined_user_id], back_populates="accepted_invites"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','ACCEPTED','CANCELLED','EXPIRED')",
            name="ck_invites_status",
        ),
    )


class Circle(Base):
    __tablename__ = "circles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    max_members: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    owner = relationship("User", back_populates="owned_circles")
    members = relationship(
        "CircleMember", back_populates="circle", cascade="all, delete-orphan"
    )
    apps = relationship("App", back_populates="circle")
    invites = relationship("Invite", back_populates="circle", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("max_members = 15", name="ck_circles_max_members"),
    )


class CircleMember(Base):
    __tablename__ = "circle_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    circle_id: Mapped[str] = mapped_column(
        ForeignKey("circles.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16), default="MEMBER", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    circle = relationship("Circle", back_populates="members")
    user = relationship("User", back_populates="circle_memberships")

    __table_args__ = (
        CheckConstraint("role IN ('OWNER','MEMBER')", name="ck_circle_members_role"),
        CheckConstraint(
            "status IN ('ACTIVE','LEFT','REMOVED')", name="ck_circle_members_status"
        ),
        UniqueConstraint("circle_id", "user_id", name="uq_circle_member_user"),
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
