from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=200)
    country: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class DevelopmentUserRead(BaseModel):
    id: str
    email: EmailStr
    display_name: str | None
    country: str | None
    reliability_score: int
    created_at: datetime


class AppCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    package_name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$", max_length=255)
    opt_in_url: HttpUrl
    play_developer_account_id: str = Field(pattern=r"^\d{1,32}$", min_length=1, max_length=32)
    core_workflow_steps: list[str] = Field(
        default_factory=lambda: [
            "Open the app and complete its main task.",
            "Check that the task result is clear and correct.",
        ],
        min_length=2,
        max_length=4,
    )
    google_group_url: HttpUrl | None = None
    google_group_mode: str = Field(default="LAUNCH_CIRCLE", pattern="^(LAUNCH_CIRCLE|OWN_GROUP|EMAIL_LIST)$")
    tester_target: int = Field(default=14, ge=1, le=100)
    circle_id: str | None = None

    @field_validator("play_developer_account_id", mode="before")
    @classmethod
    def normalize_play_developer_account_id(cls, value: str) -> str:
        normalized = str(value).strip() if value is not None else ""
        if not normalized:
            raise ValueError("play_developer_account_id is required")
        return normalized

    @field_validator("core_workflow_steps")
    @classmethod
    def valid_core_workflow_steps(cls, value: list[str]) -> list[str]:
        steps = [step.strip() for step in value if step.strip()]
        if not 2 <= len(steps) <= 4:
            raise ValueError("core_workflow_steps must contain 2 to 4 non-empty steps")
        if any(len(step) > 200 for step in steps):
            raise ValueError("each core workflow step must be 200 characters or fewer")
        return steps


class AdditionalAppCheckoutCreate(BaseModel):
    play_developer_account_id: str = Field(pattern=r"^\d{1,32}$", min_length=1, max_length=32)


class AdditionalAppCheckoutRead(BaseModel):
    id: str
    status: str
    product_id: str
    amount_total: int = 100
    currency: str = "USD"
    app_id: str | None = None


class GooglePlayPurchaseVerify(BaseModel):
    purchase_id: str
    purchase_type: str = Field(pattern="^(ADDITIONAL_APP|MANAGED_LAUNCH)$")
    purchase_token: str = Field(min_length=16, max_length=512)


class AppUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    core_workflow_steps: list[str] | None = Field(default=None, min_length=2, max_length=4)
    opt_in_url: HttpUrl | None = None
    google_group_url: HttpUrl | None = None
    google_group_mode: str | None = Field(default=None, pattern="^(LAUNCH_CIRCLE|OWN_GROUP|EMAIL_LIST)$")
    tester_target: int | None = Field(default=None, ge=1, le=100)

    @field_validator("core_workflow_steps")
    @classmethod
    def valid_core_workflow_steps(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        steps = [step.strip() for step in value if step.strip()]
        if not 2 <= len(steps) <= 4:
            raise ValueError("core_workflow_steps must contain 2 to 4 non-empty steps")
        if any(len(step) > 200 for step in steps):
            raise ValueError("each core workflow step must be 200 characters or fewer")
        return steps




class AppRead(BaseModel):
    id: str
    owner_id: str
    circle_id: str
    play_developer_account_id: str | None = None
    entitlement_status: str = "LEGACY"
    developer_account_unlimited: bool = False
    name: str
    package_name: str
    opt_in_url: str
    core_workflow_steps: list[str] = Field(default_factory=list)
    google_group_url: str | None
    google_group_mode: str = "LAUNCH_CIRCLE"
    google_group_configured: bool = False
    google_group_confirmed_at: datetime | None = None
    status: str
    tester_target: int
    testing_start_at: datetime | None
    testing_end_at: datetime | None
    testing_completed_at: datetime | None = None
    production_ready_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AssignmentRead(BaseModel):
    id: str
    app_id: str
    tester_id: str
    tester_label: str
    status: str
    assigned_at: datetime
    opted_in_at: datetime | None
    installed_at: datetime | None
    completed_at: datetime | None
    health_status: str = "NEW"
    is_replacement: bool = False
    replacement_for_id: str | None = None
    last_activity_at: datetime | None = None
    testing_day: int = 0
    completed_missions: int = 0
    total_missions: int = 0
    circle_id: str | None = None
    assignment_day: date | None = None
    test_type: str = "APP_CHECK"
    participation_state: str = "ACTIVE"


class TestAssignmentRead(BaseModel):
    id: str
    circle_id: str
    app_id: str
    tester_user_id: str | None = None
    app_name: str
    package_name: str
    opt_in_url: str
    test_type: str
    status: str
    assignment_day: date
    assigned_at: datetime
    completed_at: datetime | None
    estimated_minutes: int = 5


class AssignmentCoverageRead(BaseModel):
    app_id: str
    assignment_count: int
    completed_count: int
    participating_members: int


class MissionRead(BaseModel):
    id: str
    assignment_id: str
    assignment_status: str
    app_id: str
    app_name: str
    opt_in_url: str
    mission_type: str
    scheduled_day: int
    status: str
    due_at: datetime | None
    completed_at: datetime | None
    estimated_minutes: int
    goal: str = ""
    steps: list[str] = Field(default_factory=list)


class FeedbackCreate(BaseModel):
    launch_ok: bool | None = None
    core_feature_ok: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    issue_text: str | None = Field(default=None, max_length=4000)
    suggestion_text: str | None = Field(default=None, max_length=4000)
    completion_result: str | None = None
    time_spent_minutes: int | None = Field(default=None, ge=1, le=240)

    @field_validator("completion_result")
    @classmethod
    def valid_completion_result(cls, value: str | None) -> str | None:
        normalized = value.upper() if value else None
        allowed = {"COMPLETED", "COMPLETED_WITH_DIFFICULTY", "COULD_NOT_COMPLETE"}
        if normalized is not None and normalized not in allowed:
            raise ValueError("completion_result must be COMPLETED, COMPLETED_WITH_DIFFICULTY, or COULD_NOT_COMPLETE")
        return normalized

    @field_validator("core_feature_ok")
    @classmethod
    def valid_core_feature(cls, value: str | None) -> str | None:
        normalized = value.upper() if value else None
        if normalized is not None and normalized not in {"YES", "PARTLY", "NO"}:
            raise ValueError("core_feature_ok must be YES, PARTLY, or NO")
        return normalized


class FeedbackRead(BaseModel):
    id: str
    mission_id: str
    tester_label: str
    app_id: str
    mission_type: str
    launch_ok: bool | None
    core_feature_ok: str | None
    rating: int | None
    issue_text: str | None
    suggestion_text: str | None
    completion_result: str | None = None
    time_spent_minutes: int | None = None
    created_at: datetime


class CoordinationTimeCreate(BaseModel):
    minutes: int = Field(ge=1, le=480)
    category: str = Field(default="COORDINATION", pattern="^(COORDINATION|REPLACEMENT|RETEST|OTHER)$")


class WorkloadRead(BaseModel):
    app_id: str
    completed_missions: int = 0
    tester_minutes_reported: int = 0
    tester_feedback_with_time: int = 0
    tester_feedback_without_time: int = 0
    estimated_unreported_tester_minutes: int = 0
    developer_coordination_minutes: int = 0
    coordination_entries: int = 0


class ManagedOfferRead(BaseModel):
    app_id: str
    triggers: list[str] = Field(default_factory=list)
    remaining_reciprocal_missions: int = 0
    remaining_reciprocal_minutes: int = 0
    managed_list_price_cents: int = 1500
    managed_checkout_amount_cents: int = 1500
    managed_credit_amount_cents: int = 0
    managed_launch_purchased: bool = False


class ManagedCheckoutRead(BaseModel):
    id: str
    status: str
    app_id: str
    product_id: str
    list_product_id: str = "managed_launch_15"
    amount_total: int = 1500
    currency: str = "USD"
    list_price_total: int = 1500
    credit_amount: int = 0


class ManagedOfferViewCreate(BaseModel):
    trigger: str = Field(pattern="^(WORKLOAD|DROPOUT|RETEST|PRIORITY)$")


class GoogleGroupConfirmation(BaseModel):
    configured: bool = True


class PilotConfigRead(BaseModel):
    product_name: str
    google_group_email: str
    google_group_join_url: str
    invite_base_url: str


class InviteCreate(BaseModel):
    invited_email: EmailStr | None = None
    circle_id: str | None = None


class CircleMemberRead(BaseModel):
    id: str
    user_id: str
    display_name: str | None
    member_label: str
    role: str
    status: str
    joined_at: datetime


class CircleRead(BaseModel):
    id: str
    owner_id: str
    name: str
    max_members: int
    active_member_count: int
    members: list[CircleMemberRead]


class InviteRead(BaseModel):
    id: str
    circle_id: str
    invite_code: str
    invited_email: EmailStr | None
    joined_user_id: str | None
    status: str
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None
    share_url: str


class DashboardRead(BaseModel):
    status: str
    active_testers: int
    assigned_testers: int
    continuous_qualifying_testers: int = 0
    replacement_testers: int = 0
    tester_target: int
    google_minimum: int
    testers_needed_for_minimum: int
    day: int
    elapsed_days: int = 0
    total_days: int
    days_remaining: int = 14
    production_readiness: int
    readiness_breakdown: dict[str, int]
    today_tasks: int
    at_risk_testers: int
    circle_health: str = "GOOD"
    feedback_count: int
    completed_missions: int
    tester_minutes_reported: int = 0
    developer_coordination_minutes: int = 0
    coordination_entries: int = 0
    remaining_reciprocal_missions: int = 0
    remaining_reciprocal_minutes: int = 0
    managed_offer_triggers: list[str] = Field(default_factory=list)
    managed_list_price_cents: int = 1500
    managed_checkout_amount_cents: int = 1500
    managed_launch_purchased: bool = False
    missions_completed: int = 0
    missions_total_available: int = 0
    estimated_ready_date: str
    approval_disclaimer: str
    testing_started_at: datetime | None = None
    testing_target_end_at: datetime | None = None
    lifecycle_complete: bool = False
    qualifying_tester_count: int = 0
    required_tester_count: int = 12
    internally_production_ready: bool = False
    internal_production_ready_reason: str = ""
    coverage_shortage: int = 0
    replacement_status: str = "NONE"
    risk_reason: str = ""


class MatchingRead(BaseModel):
    assigned_now: int
    assigned_total: int
    active_testers: int
    minimum_needed: int
    target: int
    remaining_to_target: int


class AppChangeCreate(BaseModel):
    description: str = Field(min_length=1, max_length=4000)


class AppChangeRead(BaseModel):
    id: str
    app_id: str
    description: str
    created_at: datetime


class DropAssignmentRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class HealthRefreshRead(BaseModel):
    at_risk: int
    inactive: int
    dropped: int
    replacements_assigned: int
    coverage_shortage: int = 0
    replacement_status: str = "NONE"
