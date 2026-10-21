import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, get_current_user
from app.models.launch import (
    AdditionalAppPurchase,
    App,
    AppChange,
    BackendEvent,
    Circle,
    CircleMember,
    DeveloperAccount,
    DeveloperCoordinationLog,
    Feedback,
    Invite,
    ManagedCheckout,
    ManagedCredit,
    TesterAssignment,
    TestMission,
)
from app.models.user import User
from app.schemas.auth import TokenPair
from app.schemas.phase0 import (
    AdditionalAppCheckoutCreate,
    AdditionalAppCheckoutRead,
    AppChangeCreate,
    AppChangeRead,
    AppCreate,
    AppRead,
    AppUpdate,
    AssignmentCoverageRead,
    AssignmentRead,
    CircleMemberRead,
    CircleRead,
    CoordinationTimeCreate,
    DashboardRead,
    DevelopmentUserRead,
    DropAssignmentRequest,
    FeedbackCreate,
    FeedbackRead,
    GoogleGroupConfirmation,
    GooglePlayPurchaseVerify,
    HealthRefreshRead,
    InviteCreate,
    InviteRead,
    LoginRequest,
    ManagedCheckoutRead,
    ManagedOfferRead,
    ManagedOfferViewCreate,
    MatchingRead,
    MissionRead,
    PilotConfigRead,
    RegisterRequest,
    TestAssignmentRead,
    WorkloadRead,
)
from app.services.assignments import assignment_day, todays_assignments
from app.services.circles import (
    CIRCLE_MAX_MEMBERS,
    active_member,
    active_member_count,
    ensure_owner_circle,
)
from app.services.clock import aware, get_now
from app.services.commercial import (
    MANAGED_LIST_PRICE_CENTS,
    managed_offer_snapshot,
    workload_snapshot,
)
from app.services.events import emit_event, emit_pilot_event
from app.services.google_play_billing import (
    GooglePlayBillingUnavailable,
    GooglePlayPackageNotOwned,
    consume_product_purchase,
    get_one_time_product,
    get_product_purchase,
    product_for,
    validate_catalog_product,
    verify_app_package_ownership,
)
from app.services.lifecycle import evaluate_lifecycle
from app.services.matching import match_testers, matching_summary
from app.services.missions import (
    MISSION_MINUTES,
    generate_missions,
    mission_instructions,
    refresh_mission_availability,
)
from app.services.readiness import calculate_readiness
from app.services.recovery import evaluate_app_recovery, evaluate_circle_recovery
from app.services.reporting import production_application_draft, production_report
from app.services.tester_health import participation_state, record_activity, refresh_app_health

router = APIRouter()
settings = get_settings()


def require_development_auth(current: Settings = Depends(get_settings)) -> None:
    if current.is_deployment or not current.development_auth_enabled:
        raise HTTPException(status_code=404, detail="Not found")


def password_hash(password: str, salt: str | None = None) -> str:
    actual_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), actual_salt.encode(), 310_000).hex()
    return f"pbkdf2_sha256:{actual_salt}:{digest}"


def password_matches(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, salt, _expected = encoded.split(":", 2)
    except ValueError:
        return False
    return algorithm == "pbkdf2_sha256" and hmac.compare_digest(
        password_hash(password, salt), encoded
    )


def user_read(user: User) -> DevelopmentUserRead:
    return DevelopmentUserRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        country=user.country,
        reliability_score=user.reliability_score,
        created_at=user.created_at,
    )


def member_label(user: User) -> str:
    return (user.display_name or f"Developer #{user.id[-4:].upper()}").strip()


def circle_read(db: Session, circle: Circle) -> CircleRead:
    members = sorted(
        circle.members,
        key=lambda member: (
            member.status != "ACTIVE",
            member.role != "OWNER",
            aware(member.joined_at),
            member.id,
        ),
    )
    return CircleRead(
        id=circle.id,
        owner_id=circle.owner_id,
        name=circle.name,
        max_members=circle.max_members,
        active_member_count=sum(member.status == "ACTIVE" for member in members),
        members=[
            CircleMemberRead(
                id=member.id,
                user_id=member.user_id,
                display_name=member.user.display_name,
                member_label=member_label(member.user),
                role=member.role,
                status=member.status,
                joined_at=member.joined_at,
            )
            for member in members
        ],
    )


def app_read(app: App) -> AppRead:
    return AppRead(
        id=app.id,
        owner_id=app.owner_id,
        circle_id=app.circle_id,
        play_developer_account_id=(
            app.developer_account.play_developer_account_id if app.developer_account else None
        ),
        entitlement_status=app.entitlement_status,
        developer_account_unlimited=(
            app.developer_account.verification_status == "VERIFIED"
            and settings.has_unlimited_play_developer_account(
                app.developer_account.play_developer_account_id
            )
            if app.developer_account
            else False
        ),
        name=app.name,
        package_name=app.package_name,
        opt_in_url=app.opt_in_url,
        core_workflow_steps=app.core_workflow_steps or [],
        google_group_url=app.google_group_url,
        google_group_mode=app.google_group_mode,
        google_group_configured=app.google_group_configured,
        google_group_confirmed_at=app.google_group_confirmed_at,
        status=app.status,
        tester_target=app.tester_target,
        testing_start_at=aware(app.testing_start_at) if app.testing_start_at else None,
        testing_end_at=aware(app.testing_end_at) if app.testing_end_at else None,
        testing_completed_at=aware(app.testing_completed_at) if app.testing_completed_at else None,
        production_ready_at=aware(app.production_ready_at) if app.production_ready_at else None,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


def tester_label(user: User) -> str:
    return f"Tester #{user.id[-4:].upper()}"


def assignment_read(item: TesterAssignment, now: datetime | None = None) -> AssignmentRead:
    current = now or get_now()
    testing_day = (
        0 if item.installed_at is None
        else min(14, max(1, (current.date() - aware(item.installed_at).date()).days + 1))
    )
    completed = sum(mission.status == "COMPLETED" for mission in item.missions)
    return AssignmentRead(
        id=item.id,
        app_id=item.app_id,
        tester_id=item.tester_id,
        tester_label=tester_label(item.tester),
        status=item.status,
        assigned_at=item.assigned_at,
        opted_in_at=item.opted_in_at,
        installed_at=item.installed_at,
        completed_at=item.completed_at,
        health_status={
            "GOOD": "HEALTHY",
            "INACTIVE": "CRITICAL",
        }.get(item.health_status, item.health_status),
        is_replacement=item.replacement_for_id is not None,
        replacement_for_id=item.replacement_for_id,
        last_activity_at=item.last_activity_at,
        testing_day=testing_day,
        completed_missions=completed,
        total_missions=len(item.missions),
        circle_id=item.circle_id,
        assignment_day=item.assignment_day,
        test_type=item.test_type,
        participation_state=participation_state(item),
    )


def test_assignment_read(
    item: TesterAssignment,
    *,
    include_tester: bool = False,
) -> TestAssignmentRead:
    return TestAssignmentRead(
        id=item.id,
        circle_id=item.circle_id or item.app.circle_id or "",
        app_id=item.app_id,
        tester_user_id=item.tester_id if include_tester else None,
        app_name=item.app.name,
        package_name=item.app.package_name,
        opt_in_url=item.app.opt_in_url,
        test_type=item.test_type,
        status="COMPLETED" if item.status == "COMPLETED" else "ASSIGNED",
        assignment_day=item.assignment_day,
        assigned_at=item.assigned_at,
        completed_at=item.completed_at,
    )


def mission_read(mission: TestMission) -> MissionRead:
    assignment = mission.assignment
    app = assignment.app
    goal, steps = mission_instructions(
        mission.mission_type, app.name, app.core_workflow_steps
    )
    return MissionRead(
        id=mission.id,
        assignment_id=assignment.id,
        assignment_status=assignment.status,
        app_id=app.id,
        app_name=app.name,
        opt_in_url=app.opt_in_url,
        mission_type=mission.mission_type,
        scheduled_day=mission.scheduled_day,
        status=mission.status,
        due_at=mission.due_at,
        completed_at=mission.completed_at,
        estimated_minutes=MISSION_MINUTES[mission.mission_type],
        goal=goal,
        steps=steps,
    )


def feedback_read(item: Feedback) -> FeedbackRead:
    return FeedbackRead(
        id=item.id,
        mission_id=item.mission_id,
        tester_label=tester_label(item.tester),
        app_id=item.app_id,
        mission_type=item.mission.mission_type,
        launch_ok=item.launch_ok,
        core_feature_ok=item.core_feature_ok,
        rating=item.rating,
        issue_text=item.issue_text,
        suggestion_text=item.suggestion_text,
        completion_result=item.completion_result,
        time_spent_minutes=item.time_spent_minutes,
        created_at=item.created_at,
    )


def invite_read(item: Invite) -> InviteRead:
    invite_base_url = settings.launch_circle_invite_base_url.rstrip("/")
    return InviteRead(
        id=item.id,
        circle_id=item.circle_id,
        invite_code=item.invite_code,
        invited_email=item.invited_email,
        joined_user_id=item.joined_user_id,
        status=item.status,
        created_at=item.created_at,
        expires_at=item.expires_at,
        accepted_at=item.accepted_at,
        share_url=f"{invite_base_url}/{item.invite_code}",
    )


def owned_app(db: Session, app_id: str, user: User) -> App:
    app = db.get(App, app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="App not found")
    if app.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the app owner can perform this action")
    return app


def assigned_to(db: Session, assignment_id: str, user: User) -> TesterAssignment:
    assignment = db.get(TesterAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.tester_id != user.id:
        raise HTTPException(status_code=403, detail="Assignment belongs to another tester")
    return assignment


@router.get("/pilot-config", response_model=PilotConfigRead)
def pilot_config() -> PilotConfigRead:
    return PilotConfigRead(
        cold_start_evidence_enabled=get_settings().cold_start_evidence_enabled,
        product_name="Launch Circle: 12 Testers",
        google_group_email=settings.launch_circle_google_group_email,
        google_group_join_url=settings.launch_circle_google_group_join_url,
        invite_base_url=settings.launch_circle_invite_base_url,
    )


@router.post(
    "/auth/register",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=settings.development_auth_enabled and not settings.is_deployment,
)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
    _development_auth: None = Depends(require_development_auth),
) -> TokenPair:
    email = str(body.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = User(
        email=email,
        login_email=email,
        password_hash=password_hash(body.password),
        display_name=body.display_name,
        country=body.country,
    )
    db.add(user)
    db.flush()
    ensure_owner_circle(db, user)
    db.commit()
    db.refresh(user)
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(db, user.id),
    )


@router.post(
    "/auth/login",
    response_model=TokenPair,
    include_in_schema=settings.development_auth_enabled and not settings.is_deployment,
)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
    _development_auth: None = Depends(require_development_auth),
) -> TokenPair:
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    if user is None or not password_matches(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(db, user.id),
    )


@router.get("/me", response_model=DevelopmentUserRead)
def me(current_user: User = Depends(get_current_user)) -> DevelopmentUserRead:
    return user_read(current_user)


@router.get("/circles", response_model=list[CircleRead])
def list_circles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CircleRead]:
    circles = db.scalars(
        select(Circle)
        .join(CircleMember, CircleMember.circle_id == Circle.id)
        .where(
            CircleMember.user_id == current_user.id,
            CircleMember.status == "ACTIVE",
        )
        .order_by(CircleMember.joined_at.desc(), Circle.id)
    ).all()
    return [circle_read(db, circle) for circle in circles]


@router.get("/circles/{circle_id}", response_model=CircleRead)
def get_circle(
    circle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> CircleRead:
    circle = db.get(Circle, circle_id)
    if circle is None:
        raise HTTPException(status_code=404, detail="Circle not found")
    if active_member(db, circle.id, current_user.id) is None:
        raise HTTPException(status_code=403, detail="You are not an active member of this circle")
    evaluate_circle_recovery(db, circle.id, now)
    db.commit()
    return circle_read(db, circle)


@router.post("/circles/{circle_id}/leave", response_model=CircleRead)
def leave_circle(
    circle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> CircleRead:
    circle = db.get(Circle, circle_id)
    if circle is None:
        raise HTTPException(status_code=404, detail="Circle not found")
    member = db.scalar(
        select(CircleMember).where(
            CircleMember.circle_id == circle.id,
            CircleMember.user_id == current_user.id,
            CircleMember.status == "ACTIVE",
        )
    )
    if member is None:
        raise HTTPException(status_code=403, detail="You are not an active member of this circle")
    if member.role == "OWNER":
        raise HTTPException(status_code=409, detail="Circle owners cannot leave their Circle")
    member.status = "LEFT"
    member.left_at = now
    for app in db.scalars(select(App).where(App.circle_id == circle.id)):
        for assignment in app.assignments:
            if assignment.tester_id == current_user.id and assignment.status != "DROPPED":
                assignment.status = "DROPPED"
                assignment.health_status = "DROPPED"
                assignment.dropped_at = assignment.dropped_at or now
                assignment.last_activity_at = now
                emit_event(
                    db,
                    assignment.app_id,
                    "TESTER_DROPPED",
                    f"health:{assignment.id}:DROPPED",
                    assignment.id,
                    {"health_status": "DROPPED", "reason": "circle_member_left"},
                )
    evaluate_circle_recovery(db, circle.id, now)
    db.commit()
    db.refresh(circle)
    return circle_read(db, circle)


def additional_app_checkout_read(purchase: AdditionalAppPurchase) -> AdditionalAppCheckoutRead:
    product_id, amount = product_for(settings, "ADDITIONAL_APP")
    return AdditionalAppCheckoutRead(
        id=purchase.id,
        status=(
            "EXPIRED"
            if purchase.status in {"PAID", "CONSUMED"} and not purchase.google_play_purchase_token
            else purchase.status
        ),
        product_id=product_id,
        amount_total=amount, currency="USD", app_id=purchase.app_id,
    )


@router.post("/payments/additional-app-checkout", response_model=AdditionalAppCheckoutRead)
def start_additional_app_checkout(
    body: AdditionalAppCheckoutCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdditionalAppCheckoutRead:
    canonical_developer_id = settings.google_play_developer_account_id.strip()
    if settings.is_deployment and (
        not canonical_developer_id
        or body.play_developer_account_id.strip() != canonical_developer_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The Play developer account is not verified for this service.",
        )
    developer_account = db.scalar(
        select(DeveloperAccount)
        .where(DeveloperAccount.play_developer_account_id == body.play_developer_account_id.strip())
        .with_for_update()
    )
    if developer_account is None:
        raise HTTPException(status_code=409, detail="Create the first free app before buying an additional-app entitlement.")
    if developer_account.verification_status != "VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify this app through the connected Google Play developer account first.",
        )
    if settings.has_unlimited_play_developer_account(
        developer_account.play_developer_account_id
    ):
        raise HTTPException(
            status_code=409,
            detail="This verified Google Play developer account has unlimited app registration; no purchase is required.",
        )
    linked_app_count = db.scalar(
        select(func.count(App.id)).where(App.developer_account_id == developer_account.id)
    ) or 0
    if linked_app_count == 0 and developer_account.first_free_claimed_at is None:
        raise HTTPException(status_code=409, detail="The first app for this Developer Account is free.")
    paid_purchase = db.scalar(
        select(AdditionalAppPurchase.id).where(
            AdditionalAppPurchase.owner_id == current_user.id,
            AdditionalAppPurchase.developer_account_id == developer_account.id,
            AdditionalAppPurchase.status.in_({"PAID", "CONSUMED"}),
            AdditionalAppPurchase.app_id.is_(None),
            AdditionalAppPurchase.google_play_purchase_token.is_not(None),
        )
    )
    if paid_purchase is not None:
        raise HTTPException(status_code=409, detail="An additional-app entitlement is already available.")
    purchase = db.scalar(
        select(AdditionalAppPurchase)
        .where(
            AdditionalAppPurchase.owner_id == current_user.id,
            AdditionalAppPurchase.developer_account_id == developer_account.id,
            AdditionalAppPurchase.status == "PENDING",
            AdditionalAppPurchase.google_play_product_id == settings.google_play_additional_app_product_id,
        )
        .order_by(AdditionalAppPurchase.created_at.desc()).limit(1).with_for_update()
    )
    if purchase is None:
        purchase = AdditionalAppPurchase(
            owner_id=current_user.id, developer_account_id=developer_account.id,
            google_play_product_id=settings.google_play_additional_app_product_id,
            amount_total=100, currency="usd",
        )
        db.add(purchase)
        db.commit()
        db.refresh(purchase)
    return additional_app_checkout_read(purchase)


@router.get("/payments/additional-app-checkout/{purchase_id}", response_model=AdditionalAppCheckoutRead)
def get_additional_app_checkout(
    purchase_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> AdditionalAppCheckoutRead:
    purchase = db.get(AdditionalAppPurchase, purchase_id)
    if purchase is None or purchase.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return additional_app_checkout_read(purchase)


def _consume_verified_product(product_id: str | None, purchase_token: str) -> None:
    if not product_id:
        raise HTTPException(status_code=409, detail="Verified Google Play purchase is missing its product ID")
    try:
        purchase = get_product_purchase(settings, product_id, purchase_token)
        if purchase.get("productId") != product_id or int(purchase.get("purchaseState", -1)) != 0:
            raise HTTPException(status_code=409, detail="Google Play purchase is no longer valid")
        if int(purchase.get("consumptionState", 0)) != 1:
            consume_product_purchase(settings, product_id, purchase_token)
    except GooglePlayBillingUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


def managed_checkout_read(checkout: ManagedCheckout) -> ManagedCheckoutRead:
    product_id, _ = product_for(settings, "MANAGED_LAUNCH", checkout.credit_amount > 0)
    return ManagedCheckoutRead(
        id=checkout.id,
        status=(
            "EXPIRED"
            if checkout.status == "PAID" and not checkout.google_play_purchase_token
            else checkout.status
        ),
        app_id=checkout.app_id,
        product_id=product_id, amount_total=checkout.amount_total,
        list_product_id=settings.google_play_managed_product_id,
        currency="USD", list_price_total=checkout.list_price_total,
        credit_amount=checkout.credit_amount,
    )


@router.post("/apps/{app_id}/managed-checkout", response_model=ManagedCheckoutRead)
def start_managed_checkout(
    app_id: str, current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db), now: datetime = Depends(get_now),
) -> ManagedCheckoutRead:
    app = owned_app(db, app_id, current_user)
    already_purchased = db.scalar(select(ManagedCheckout.id).where(
        ManagedCheckout.app_id == app.id, ManagedCheckout.status == "PAID",
        ManagedCheckout.google_play_purchase_token.is_not(None),
    ))
    if already_purchased:
        raise HTTPException(status_code=409, detail="Managed Launch is already paid for this app")
    checkout = db.scalar(
        select(ManagedCheckout).where(
            ManagedCheckout.app_id == app.id, ManagedCheckout.status == "PENDING"
        ).order_by(ManagedCheckout.created_at.desc()).limit(1).with_for_update()
    )
    if checkout is not None and checkout.google_play_product_id is None:
        checkout.status = "EXPIRED"
        db.flush()
        checkout = None
    if checkout is None:
        credit = db.scalar(
            select(ManagedCredit)
            .join(
                AdditionalAppPurchase,
                AdditionalAppPurchase.id == ManagedCredit.source_additional_app_purchase_id,
            )
            .where(
                ManagedCredit.owner_id == current_user.id,
                ManagedCredit.status == "AVAILABLE",
                ManagedCredit.source_google_play_order_id.is_not(None),
                AdditionalAppPurchase.app_id == app.id,
                AdditionalAppPurchase.developer_account_id == app.developer_account_id,
                AdditionalAppPurchase.status == "CONSUMED",
                ~select(ManagedCheckout.id).where(
                    ManagedCheckout.managed_credit_id == ManagedCredit.id,
                    ManagedCheckout.status == "PENDING",
                ).exists(),
            ).order_by(ManagedCredit.created_at, ManagedCredit.id).limit(1).with_for_update()
        )
        credit_amount = 100 if credit is not None else 0
        checkout = ManagedCheckout(
            app_id=app.id, managed_credit_id=credit.id if credit else None,
            google_play_product_id=product_for(
                settings, "MANAGED_LAUNCH", bool(credit)
            )[0],
            list_price_total=MANAGED_LIST_PRICE_CENTS, credit_amount=credit_amount,
            amount_total=MANAGED_LIST_PRICE_CENTS-credit_amount, currency="usd",
        )
        db.add(checkout)
        db.commit()
        db.refresh(checkout)
    return managed_checkout_read(checkout)


@router.get("/payments/managed-checkout/{checkout_id}", response_model=ManagedCheckoutRead)
def get_managed_checkout(
    checkout_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> ManagedCheckoutRead:
    checkout = db.get(ManagedCheckout, checkout_id)
    app = db.get(App, checkout.app_id) if checkout is not None else None
    if checkout is None or app is None or app.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Managed purchase not found")
    if checkout.status == "PAID" and checkout.google_play_purchase_token:
        _consume_verified_product(checkout.google_play_product_id, checkout.google_play_purchase_token)
    return managed_checkout_read(checkout)


@router.post("/payments/google-play/verify")
def verify_google_play_purchase(
    body: GooglePlayPurchaseVerify, current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db), now: datetime = Depends(get_now),
) -> dict[str, str | int]:
    if body.purchase_type == "ADDITIONAL_APP":
        record = db.scalar(
            select(AdditionalAppPurchase)
            .where(AdditionalAppPurchase.id == body.purchase_id)
            .with_for_update()
        )
        if record is None or record.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Purchase not found")
        expected_product_id, expected_amount = product_for(settings, "ADDITIONAL_APP")
        app = None
    else:
        record = db.scalar(
            select(ManagedCheckout)
            .where(ManagedCheckout.id == body.purchase_id)
            .with_for_update()
        )
        app = db.get(App, record.app_id) if record else None
        if record is None or app is None or app.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Managed purchase not found")
        expected_product_id, expected_amount = product_for(
            settings, "MANAGED_LAUNCH", record.credit_amount > 0
        )
    if record.amount_total != expected_amount or (record.currency or "").lower() != "usd":
        raise HTTPException(status_code=409, detail="Purchase amount does not match the configured Google Play product")
    if record.status not in {"PENDING", "PAID", "CONSUMED"}:
        raise HTTPException(status_code=409, detail="Purchase is no longer payable")
    if record.status in {"PAID", "CONSUMED"}:
        if record.google_play_purchase_token != body.purchase_token:
            raise HTTPException(status_code=409, detail="Purchase intent is already linked to another token")
        _consume_verified_product(expected_product_id, body.purchase_token)
        return {"status": record.status, "product_id": expected_product_id, "amount_total": expected_amount}
    token_owner = db.scalar(select(AdditionalAppPurchase.id).where(
        AdditionalAppPurchase.google_play_purchase_token == body.purchase_token
    )) or db.scalar(select(ManagedCheckout.id).where(
        ManagedCheckout.google_play_purchase_token == body.purchase_token
    ))
    if token_owner:
        raise HTTPException(status_code=409, detail="Google Play purchase token is already linked")
    try:
        purchase = get_product_purchase(settings, expected_product_id, body.purchase_token)
    except GooglePlayBillingUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if purchase.get("productId") != expected_product_id:
        raise HTTPException(status_code=400, detail="Google Play product does not match this purchase")
    if int(purchase.get("purchaseState", -1)) != 0:
        raise HTTPException(status_code=409, detail="Google Play purchase is not complete")
    if int(purchase.get("quantity", 1)) != 1:
        raise HTTPException(status_code=400, detail="Only single-quantity Google Play purchases are accepted")
    is_test_purchase = purchase.get("purchaseType") == 0
    if is_test_purchase and settings.app_env.lower() != "pilot":
        raise HTTPException(
            status_code=403,
            detail="Google Play test purchases are only accepted by the pilot service.",
        )
    region_code = purchase.get("regionCode")
    if not region_code and not is_test_purchase:
        raise HTTPException(status_code=400, detail="Google Play purchase is missing its region")
    try:
        catalog_product = get_one_time_product(settings, expected_product_id)
    except GooglePlayBillingUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    catalog_is_valid = catalog_product.get("productId") == expected_product_id
    if region_code:
        catalog_is_valid = catalog_is_valid and validate_catalog_product(
            catalog_product, region_code, expected_amount
        )
    elif not is_test_purchase:
        catalog_is_valid = False
    if not catalog_is_valid:
        raise HTTPException(
            status_code=503,
            detail="Google Play product is unavailable or its configured price does not match this offer",
        )
    expected_binding = hashlib.sha256(f"launch-circle:{record.id}".encode()).hexdigest()
    if purchase.get("obfuscatedExternalAccountId") != expected_binding:
        raise HTTPException(status_code=403, detail="Google Play purchase is not bound to this purchase intent")
    order_id = purchase.get("orderId")
    if not order_id and is_test_purchase:
        # Test orders may not have a Google order ID. Use a stable, non-secret
        # identifier for bookkeeping; never store the raw purchase token here.
        order_id = f"TEST-GPLAY-{hashlib.sha256(body.purchase_token.encode()).hexdigest()}"
    if not order_id:
        raise HTTPException(status_code=400, detail="Google Play purchase is missing its order ID")
    record.google_play_purchase_token = body.purchase_token
    record.google_play_order_id = order_id
    record.google_play_product_id = expected_product_id
    record.amount_total = expected_amount
    record.currency = "usd"
    record.status = "PAID"
    record.paid_at = now
    if body.purchase_type == "ADDITIONAL_APP":
        credit = db.scalar(select(ManagedCredit).where(
            ManagedCredit.source_additional_app_purchase_id == record.id
        ).with_for_update())
        if credit is None:
            db.add(ManagedCredit(
                owner_id=record.owner_id, developer_account_id=record.developer_account_id,
                source_additional_app_purchase_id=record.id,
                source_google_play_order_id=order_id,
            ))
        owner_id = record.owner_id
    else:
        credit = db.get(ManagedCredit, record.managed_credit_id) if record.managed_credit_id else None
        if record.credit_amount and credit is None:
            db.rollback()
            raise HTTPException(status_code=409, detail="Reserved Managed credit is unavailable")
        if credit is not None:
            if credit.status == "AVAILABLE":
                credit.status = "REDEEMED"
                credit.redeemed_app_id = record.app_id
                credit.redeemed_at = now
            elif credit.status != "REDEEMED" or credit.redeemed_app_id != record.app_id:
                db.rollback()
                raise HTTPException(status_code=409, detail="Reserved Managed credit was already used")
        app.entitlement_status = "MANAGED"
        owner_id = app.owner_id
    emit_pilot_event(
        db, owner_id,
        "additional_app_payment_success" if body.purchase_type == "ADDITIONAL_APP" else "managed_payment_success",
        f"google-play-purchase-paid:{body.purchase_type}:{record.id}",
        app_id=record.app_id if body.purchase_type == "MANAGED_LAUNCH" else None,
        payload={"google_play_order_id": order_id, "google_play_product_id": expected_product_id,
                 "amount_total": expected_amount, "currency": "USD", "payment_channel": "GOOGLE_PLAY",
                 "same_app_additional_app_purchase_applied": (
                     body.purchase_type == "MANAGED_LAUNCH" and record.credit_amount == 100
                 )},
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        saved_record = (
            db.get(AdditionalAppPurchase, body.purchase_id)
            if body.purchase_type == "ADDITIONAL_APP"
            else db.get(ManagedCheckout, body.purchase_id)
        )
        if (
            saved_record is None
            or saved_record.status not in {"PAID", "CONSUMED"}
            or saved_record.google_play_purchase_token != body.purchase_token
            or saved_record.google_play_order_id != order_id
        ):
            raise HTTPException(status_code=409, detail="Google Play purchase is already linked")
        _consume_verified_product(expected_product_id, body.purchase_token)
        return {
            "status": saved_record.status,
            "product_id": expected_product_id,
            "amount_total": expected_amount,
        }
    _consume_verified_product(expected_product_id, body.purchase_token)
    return {"status": record.status, "product_id": expected_product_id, "amount_total": expected_amount}


@router.post("/apps", response_model=AppRead, status_code=status.HTTP_201_CREATED)
def create_app(
    body: AppCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> AppRead:
    canonical_developer_id = settings.google_play_developer_account_id.strip()
    if settings.is_deployment and (
        not canonical_developer_id
        or body.play_developer_account_id != canonical_developer_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The Play developer account is not verified for this service.",
        )
    try:
        verify_app_package_ownership(settings, body.package_name)
    except GooglePlayPackageNotOwned as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This app package is not accessible in the connected Google Play developer account.",
        ) from exc
    except GooglePlayBillingUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Play account verification is temporarily unavailable. Try again later.",
        ) from exc

    selected_circle = None
    if body.circle_id is not None:
        selected_circle = db.get(Circle, body.circle_id)
        if selected_circle is None:
            raise HTTPException(status_code=404, detail="Circle not found")
        if active_member(db, selected_circle.id, current_user.id) is None:
            raise HTTPException(status_code=403, detail="You are not an active member of this circle")

    if db.scalar(select(App.id).where(App.package_name == body.package_name)):
        raise HTTPException(status_code=409, detail="Package name is already registered")

    developer_account = db.scalar(
        select(DeveloperAccount)
        .where(
            DeveloperAccount.play_developer_account_id == body.play_developer_account_id
        )
        .with_for_update()
    )
    if developer_account is None:
        developer_account = DeveloperAccount(
            play_developer_account_id=body.play_developer_account_id,
            identity_method="PUBLIC_PUBLISHER",
            verification_status="VERIFIED",
        )
        db.add(developer_account)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            developer_account = db.scalar(
                select(DeveloperAccount)
                .where(
                    DeveloperAccount.play_developer_account_id
                    == body.play_developer_account_id
                )
                .with_for_update()
            )
            if developer_account is None:
                raise

    # A package access check above is the evidence for these fields. Never
    # convert an unverified client claim into a verified publisher identity.
    developer_account.identity_method = "PUBLIC_PUBLISHER"
    developer_account.verification_status = "VERIFIED"

    legacy_apps = list(
        db.scalars(
            select(App).where(
                App.owner_id == current_user.id,
                App.developer_account_id.is_(None),
            )
        )
    )
    for legacy_app in legacy_apps:
        legacy_app.developer_account = developer_account
    if legacy_apps and developer_account.first_free_claimed_at is None:
        developer_account.first_free_claimed_at = now

    linked_app_count = db.scalar(
        select(func.count(App.id)).where(App.developer_account_id == developer_account.id)
    ) or 0
    paid_purchase = None
    developer_account_unlimited = settings.has_unlimited_play_developer_account(
        developer_account.play_developer_account_id
    )
    if not developer_account_unlimited and (
        linked_app_count > 0 or developer_account.first_free_claimed_at is not None
    ):
        paid_purchase = db.scalar(
            select(AdditionalAppPurchase)
            .where(
                AdditionalAppPurchase.owner_id == current_user.id,
                AdditionalAppPurchase.developer_account_id == developer_account.id,
                AdditionalAppPurchase.status == "PAID",
                AdditionalAppPurchase.app_id.is_(None),
                AdditionalAppPurchase.google_play_purchase_token.is_not(None),
            )
            .order_by(AdditionalAppPurchase.created_at, AdditionalAppPurchase.id)
            .with_for_update()
        )
        if paid_purchase is None:
            first_app = db.scalar(
                select(App)
                .where(App.developer_account_id == developer_account.id)
                .order_by(App.created_at, App.id)
                .limit(1)
            )
            emit_pilot_event(
                db,
                current_user.id,
                "additional_app_paywall_viewed",
                f"additional-app-paywall:{developer_account.id}:{linked_app_count + 1}",
                app_id=first_app.id if first_app else None,
                payload={
                    "app_index": linked_app_count + 1,
                    "source": current_user.acquisition_source or "UNKNOWN",
                    "developer_identity_method": developer_account.identity_method,
                },
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    "This Developer Account has already used its first free app. "
                    "An additional app requires the $1 Google Play entitlement."
                ),
            )

    app = App(
        owner_id=current_user.id,
        developer_account=developer_account,
        entitlement_status=(
            "PUBLISHER_UNLIMITED"
            if developer_account_unlimited
            else "ADDITIONAL_PAID" if paid_purchase else "FIRST_APP_FREE"
        ),
        circle_id=(selected_circle or ensure_owner_circle(db, current_user)).id,
        name=body.name,
        package_name=body.package_name,
        opt_in_url=str(body.opt_in_url),
        core_workflow_steps=body.core_workflow_steps,
        google_group_url=str(body.google_group_url) if body.google_group_url else (
            settings.launch_circle_google_group_join_url
            if body.google_group_mode == "LAUNCH_CIRCLE" else None
        ),
        google_group_mode=body.google_group_mode,
        status="WAITING_FOR_TESTERS",
        tester_target=body.tester_target,
    )
    developer_account.first_free_claimed_at = now
    db.add(app)
    try:
        db.flush()
        if paid_purchase is not None:
            paid_purchase.status = "CONSUMED"
            paid_purchase.app_id = app.id
        submission_event = (
            "additional_app_submitted" if paid_purchase is not None else "first_app_submitted"
        )
        submission_prefix = "additional" if paid_purchase is not None else "first"
        emit_pilot_event(
            db,
            current_user.id,
            submission_event,
            f"{submission_prefix}-app-submitted:{app.id}",
            app_id=app.id,
            payload={
                "source": current_user.acquisition_source or "UNKNOWN",
                "package": body.package_name,
                "developer_identity_method": developer_account.identity_method,
                "entitlement_status": app.entitlement_status,
            },
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if db.scalar(select(App.id).where(App.package_name == body.package_name)):
            raise HTTPException(
                status_code=409, detail="Package name is already registered"
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                "This Developer Account has already used its first free app. "
                "An additional app requires the $1 Google Play entitlement."
            ),
        ) from exc
    db.refresh(app)
    return app_read(app)


@router.get("/apps/{app_id}/circle", response_model=CircleRead)
def get_app_circle(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> CircleRead:
    app = db.get(App, app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="App not found")
    if active_member(db, app.circle_id, current_user.id) is None:
        raise HTTPException(status_code=403, detail="You are not an active member of this circle")
    evaluate_circle_recovery(db, app.circle_id, now)
    db.commit()
    return circle_read(db, app.circle)


@router.get("/apps", response_model=list[AppRead])
def list_apps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AppRead]:
    apps = db.scalars(
        select(App).where(App.owner_id == current_user.id).order_by(App.created_at.desc())
    )
    return [app_read(app) for app in apps]


@router.get("/apps/{app_id}", response_model=AppRead)
def get_app(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppRead:
    return app_read(owned_app(db, app_id, current_user))


@router.patch("/apps/{app_id}", response_model=AppRead)
def update_app(
    app_id: str,
    body: AppUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppRead:
    app = owned_app(db, app_id, current_user)
    values = body.model_dump(exclude_unset=True)
    for name, value in values.items():
        if name == "core_workflow_steps" and value is None:
            continue
        if name in {"opt_in_url", "google_group_url"} and value is not None:
            value = str(value)
        setattr(app, name, value)
    db.commit()
    db.refresh(app)
    return app_read(app)


@router.post("/apps/{app_id}/google-group/confirm", response_model=AppRead)
def confirm_google_group(
    app_id: str,
    body: GoogleGroupConfirmation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> AppRead:
    app = owned_app(db, app_id, current_user)
    first_confirmation = body.configured and not app.google_group_configured
    app.google_group_configured = body.configured
    app.google_group_confirmed_at = now if body.configured else None
    if first_confirmation:
        emit_pilot_event(
            db, current_user.id, "google_group_confirmed",
            f"google-group-confirmed:{app.id}", app_id=app.id,
        )
    db.commit()
    db.refresh(app)
    return app_read(app)


@router.get("/apps/{app_id}/testers", response_model=list[AssignmentRead])
def list_testers(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> list[AssignmentRead]:
    app = owned_app(db, app_id, current_user)
    evaluate_app_recovery(db, app, now)
    db.commit()
    return [assignment_read(item, now) for item in app.assignments]


@router.post(
    "/apps/{app_id}/assign/{tester_id}",
    response_model=AssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def assign_tester(
    app_id: str,
    tester_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> AssignmentRead:
    app = owned_app(db, app_id, current_user)
    if tester_id == app.owner_id:
        raise HTTPException(status_code=422, detail="An owner cannot test their own app")
    tester = db.get(User, tester_id)
    if tester is None:
        raise HTTPException(status_code=404, detail="Tester not found")
    member = db.scalar(
        select(CircleMember).where(
            CircleMember.circle_id == app.circle_id,
            CircleMember.user_id == tester_id,
            CircleMember.status == "ACTIVE",
        )
    )
    if member is None or not tester.is_active:
        raise HTTPException(status_code=422, detail="Tester must be an active member of the app circle")
    daily_count = db.scalar(
        select(func.count(TesterAssignment.id)).where(
            TesterAssignment.tester_id == tester_id,
            TesterAssignment.assignment_day == assignment_day(now),
            TesterAssignment.status != "DROPPED",
        )
    ) or 0
    if daily_count >= 2:
        raise HTTPException(status_code=409, detail="Tester has reached the daily assignment limit")
    duplicate = db.scalar(
        select(TesterAssignment).where(
            TesterAssignment.app_id == app_id,
            TesterAssignment.tester_id == tester_id,
            TesterAssignment.status != "DROPPED",
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Tester already has an active assignment")
    assignment = TesterAssignment(
        app_id=app_id,
        circle_id=app.circle_id,
        tester_id=tester_id,
        assignment_day=assignment_day(now),
        test_type="APP_CHECK",
        status="ASSIGNED",
    )
    db.add(assignment)
    db.flush()
    emit_event(db, app.id, "TESTER_ASSIGNED", f"TESTER_ASSIGNED:{assignment.id}", assignment.id)
    emit_pilot_event(
        db, current_user.id, "tester_assigned", f"pilot:tester-assigned:{assignment.id}",
        app_id=app.id, assignment_id=assignment.id,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Tester already has an active assignment"
        ) from exc
    db.refresh(assignment)
    return assignment_read(assignment, now)


@router.patch("/assignments/{assignment_id}/opt-in", response_model=AssignmentRead)
def confirm_opt_in(
    assignment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> AssignmentRead:
    assignment = assigned_to(db, assignment_id, current_user)
    if assignment.status == "DROPPED":
        raise HTTPException(status_code=409, detail="Dropped assignment cannot be resumed")
    first_opt_in = assignment.opted_in_at is None
    if first_opt_in:
        assignment.opted_in_at = now
    if assignment.status == "ASSIGNED":
        assignment.status = "OPTED_IN"
    if assignment.last_activity_at is None:
        current_user.reliability_score += 1
    record_activity(assignment, now)
    if first_opt_in:
        emit_pilot_event(
            db, current_user.id, "tester_opted_in", f"tester-opted-in:{assignment.id}",
            app_id=assignment.app_id, assignment_id=assignment.id,
        )
    db.commit()
    db.refresh(assignment)
    return assignment_read(assignment, now)


@router.patch("/assignments/{assignment_id}/installed", response_model=AssignmentRead)
def confirm_installed(
    assignment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> AssignmentRead:
    assignment = assigned_to(db, assignment_id, current_user)
    if assignment.opted_in_at is None:
        raise HTTPException(status_code=409, detail="Confirm opt-in before installation")
    if assignment.status in {"DROPPED", "COMPLETED"}:
        raise HTTPException(status_code=409, detail="Assignment cannot be activated")
    first_install = assignment.installed_at is None
    assignment.installed_at = assignment.installed_at or now
    assignment.status = "ACTIVE"
    record_activity(assignment, now)
    if first_install:
        current_user.reliability_score += 1
        emit_pilot_event(
            db, current_user.id, "tester_installed", f"tester-installed:{assignment.id}",
            app_id=assignment.app_id, assignment_id=assignment.id,
        )
    generate_missions(db, assignment, now)
    evaluate_lifecycle(db, assignment.app, now)
    db.commit()
    db.refresh(assignment)
    return assignment_read(assignment, now)


@router.get("/test-missions/today", response_model=list[MissionRead])
def todays_missions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> list[MissionRead]:
    missions = list(
        db.scalars(
            select(TestMission)
            .join(TesterAssignment)
            .where(TesterAssignment.tester_id == current_user.id)
            .order_by(TestMission.due_at)
        )
    )
    refresh_mission_availability(db, missions, now)
    db.commit()
    return [mission_read(item) for item in missions if item.status == "AVAILABLE"]


@router.get("/test-assignments/today", response_model=list[TestAssignmentRead])
def todays_test_assignments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> list[TestAssignmentRead]:
    rows = todays_assignments(db, current_user.id, now)
    db.commit()
    return [test_assignment_read(row) for row in rows]


@router.post("/test-assignments/{assignment_id}/complete", response_model=TestAssignmentRead)
def complete_test_assignment(
    assignment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> TestAssignmentRead:
    assignment = db.get(TesterAssignment, assignment_id)
    if assignment is None or assignment.assignment_day is None:
        raise HTTPException(status_code=404, detail="Test assignment not found")
    if assignment.tester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Test assignment belongs to another tester")
    if assignment.status == "COMPLETED":
        evaluate_app_recovery(db, assignment.app, now)
        db.commit()
        return test_assignment_read(assignment)
    if assignment.status != "ASSIGNED":
        raise HTTPException(status_code=409, detail="Test assignment is not completable")
    assignment.status = "COMPLETED"
    assignment.completed_at = now
    assignment.opted_in_at = assignment.opted_in_at or now
    assignment.installed_at = assignment.installed_at or now
    assignment.last_activity_at = now
    assignment.health_status = "GOOD"
    evaluate_app_recovery(db, assignment.app, now)
    emit_pilot_event(
        db,
        current_user.id,
        "test_assignment_completed",
        f"test-assignment-completed:{assignment.id}",
        app_id=assignment.app_id,
        assignment_id=assignment.id,
        payload={"assignment_day": str(assignment.assignment_day)},
    )
    db.commit()
    db.refresh(assignment)
    return test_assignment_read(assignment)


@router.get("/apps/{app_id}/assignment-coverage", response_model=AssignmentCoverageRead)
def assignment_coverage(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssignmentCoverageRead:
    app = owned_app(db, app_id, current_user)
    rows = list(
        db.scalars(
            select(TesterAssignment).where(
                TesterAssignment.app_id == app.id,
                TesterAssignment.circle_id == app.circle_id,
                TesterAssignment.status != "DROPPED",
            )
        )
    )
    return AssignmentCoverageRead(
        app_id=app.id,
        assignment_count=len(rows),
        completed_count=sum(row.status == "COMPLETED" for row in rows),
        participating_members=len({row.tester_id for row in rows}),
    )


@router.get("/assignments/{assignment_id}/missions", response_model=list[MissionRead])
def assignment_missions(
    assignment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> list[MissionRead]:
    assignment = db.get(TesterAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if current_user.id not in {assignment.tester_id, assignment.app.owner_id}:
        raise HTTPException(status_code=403, detail="Not permitted")
    refresh_mission_availability(db, assignment.missions, now)
    db.commit()
    return [
        mission_read(item)
        for item in sorted(assignment.missions, key=lambda item: item.scheduled_day)
    ]


@router.post("/missions/{mission_id}/start", response_model=MissionRead)
def start_mission(
    mission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> MissionRead:
    mission = db.get(TestMission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission.assignment.tester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Mission belongs to another tester")
    refresh_mission_availability(db, [mission], now)
    if mission.status not in {"AVAILABLE", "COMPLETED"}:
        raise HTTPException(status_code=409, detail="Mission is not available")
    emit_pilot_event(
        db, current_user.id, "mission_started", f"mission-started:{mission.id}",
        app_id=mission.assignment.app_id, assignment_id=mission.assignment_id,
        payload={"mission_id": mission.id},
    )
    db.commit()
    return mission_read(mission)


@router.patch("/missions/{mission_id}/complete", response_model=MissionRead)
def complete_mission(
    mission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> MissionRead:
    mission = db.get(TestMission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission.assignment.tester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Mission belongs to another tester")
    refresh_mission_availability(db, [mission], now)
    if mission.status not in {"AVAILABLE", "COMPLETED"}:
        raise HTTPException(status_code=409, detail="Mission is not available")
    first_completion = mission.completed_at is None
    if first_completion:
        mission.completed_at = now
        mission.status = "COMPLETED"
        mission.assignment.tester.reliability_score += 2
        mission.assignment.tester.last_successful_test_at = now
        record_activity(mission.assignment, now)
        emit_pilot_event(
            db, current_user.id, "mission_completed", f"mission-completed:{mission.id}",
            app_id=mission.assignment.app_id, assignment_id=mission.assignment_id,
            payload={"mission_id": mission.id},
        )
    if all(item.status == "COMPLETED" for item in mission.assignment.missions):
        mission.assignment.status = "COMPLETED"
        mission.assignment.completed_at = now
        mission.assignment.tester.reliability_score += 5
    evaluate_app_recovery(db, mission.assignment.app, now)
    db.commit()
    db.refresh(mission)
    return mission_read(mission)


@router.post(
    "/missions/{mission_id}/feedback",
    response_model=FeedbackRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    mission_id: str,
    body: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> FeedbackRead:
    mission = db.get(TestMission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission.assignment.tester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Mission belongs to another tester")
    if mission.status != "COMPLETED":
        raise HTTPException(status_code=409, detail="Complete the mission before feedback")
    if mission.feedback_entry is not None:
        raise HTTPException(status_code=409, detail="Feedback was already submitted")
    feedback = Feedback(
        mission_id=mission.id,
        tester_id=current_user.id,
        app_id=mission.assignment.app_id,
        **body.model_dump(),
    )
    db.add(feedback)
    current_user.reliability_score += 2
    current_user.last_successful_test_at = now
    record_activity(mission.assignment, now)
    emit_pilot_event(
        db, current_user.id, "feedback_submitted", f"feedback-submitted:{mission.id}",
        app_id=mission.assignment.app_id, assignment_id=mission.assignment_id,
        payload={"mission_id": mission.id},
    )
    db.commit()
    db.refresh(feedback)
    return feedback_read(feedback)


@router.get("/apps/{app_id}/feedback", response_model=list[FeedbackRead])
def app_feedback(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FeedbackRead]:
    owned_app(db, app_id, current_user)
    rows = db.scalars(
        select(Feedback).where(Feedback.app_id == app_id).order_by(Feedback.created_at.desc())
    )
    return [feedback_read(item) for item in rows]


def generate_invite_code(db: Session) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "LC-" + "".join(secrets.choice(alphabet) for _ in range(5))
        if not db.scalar(select(Invite.id).where(Invite.invite_code == code)):
            return code


INVITE_TTL = timedelta(days=7)


def create_circle_invite(
    body: InviteCreate,
    circle: Circle,
    current_user: User,
    db: Session,
    now: datetime,
) -> InviteRead:
    if active_member(db, circle.id, current_user.id) is None:
        raise HTTPException(status_code=403, detail="You are not an active member of this circle")
    invite = Invite(
        inviter_id=current_user.id,
        circle_id=circle.id,
        invite_code=generate_invite_code(db),
        invited_email=str(body.invited_email).lower() if body.invited_email else None,
        status="PENDING",
        created_at=now,
        expires_at=now + INVITE_TTL,
    )
    db.add(invite)
    db.flush()
    emit_pilot_event(
        db, current_user.id, "invite_created", f"invite-created:{invite.id}",
        invite_id=invite.id, payload={"circle_id": circle.id},
    )
    db.commit()
    db.refresh(invite)
    return invite_read(invite)


@router.post("/apps/{app_id}/invites", response_model=InviteRead, status_code=status.HTTP_201_CREATED)
def create_app_invite(
    app_id: str,
    body: InviteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> InviteRead:
    app = owned_app(db, app_id, current_user)
    return create_circle_invite(body, app.circle, current_user, db, now)


@router.post("/invites", response_model=InviteRead, status_code=status.HTTP_201_CREATED)
def create_invite(
    body: InviteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> InviteRead:
    if body.circle_id:
        circle = db.get(Circle, body.circle_id)
        if circle is None:
            raise HTTPException(status_code=404, detail="Circle not found")
    else:
        circle = ensure_owner_circle(db, current_user)
    return create_circle_invite(body, circle, current_user, db, now)


@router.get("/invites/me", response_model=list[InviteRead])
def my_invites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InviteRead]:
    rows = db.scalars(
        select(Invite)
        .where(
            or_(
                Invite.inviter_id == current_user.id,
                Invite.joined_user_id == current_user.id,
                Invite.invited_email == current_user.email,
            )
        )
        .order_by(Invite.created_at.desc())
    )
    return [invite_read(item) for item in rows]


@router.post("/invites/{invite_code}/accept", response_model=InviteRead)
def accept_invite(
    invite_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> InviteRead:
    invite = db.scalar(
        select(Invite)
        .where(Invite.invite_code == invite_code.upper())
        .with_for_update()
    )
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.inviter_id == current_user.id:
        raise HTTPException(status_code=422, detail="You cannot accept your own invite")
    if invite.status == "ACCEPTED" and invite.joined_user_id != current_user.id:
        raise HTTPException(status_code=409, detail="Invite was already accepted")
    if invite.status in {"CANCELLED", "EXPIRED"}:
        raise HTTPException(status_code=409, detail="Invite is no longer active")
    if invite.invited_email and invite.invited_email != current_user.email:
        raise HTTPException(status_code=403, detail="Invite is intended for another email")
    if (
        invite.status == "PENDING"
        and invite.expires_at is not None
        and aware(invite.expires_at) <= aware(now)
    ):
        invite.status = "EXPIRED"
        try:
            db.commit()
        except IntegrityError:
            # Older SQLite files may still have the pre-circle status CHECK;
            # expiration enforcement remains effective even if that legacy row
            # cannot be rewritten until the additive migration is applied.
            db.rollback()
        raise HTTPException(status_code=410, detail="Invite has expired")

    circle = db.scalar(
        select(Circle).where(Circle.id == invite.circle_id).with_for_update()
    )
    if circle is None:
        raise HTTPException(status_code=409, detail="Invite circle is no longer available")

    member = db.scalar(
        select(CircleMember)
        .where(
            CircleMember.circle_id == circle.id,
            CircleMember.user_id == current_user.id,
        )
        .with_for_update()
    )
    if member is None:
        if active_member_count(db, circle.id) >= min(circle.max_members, CIRCLE_MAX_MEMBERS):
            raise HTTPException(status_code=409, detail="This Launch Circle is full")
        member = CircleMember(
            circle_id=circle.id,
            user_id=current_user.id,
            role="MEMBER",
            status="ACTIVE",
            joined_at=now,
        )
        db.add(member)
    elif member.status != "ACTIVE":
        if active_member_count(db, circle.id) >= min(circle.max_members, CIRCLE_MAX_MEMBERS):
            raise HTTPException(status_code=409, detail="This Launch Circle is full")
        member.status = "ACTIVE"
        member.joined_at = now
        member.left_at = None

    first_acceptance = invite.status != "ACCEPTED"
    invite.status = "ACCEPTED"
    invite.joined_user_id = current_user.id
    invite.accepted_at = invite.accepted_at or now
    if first_acceptance:
        emit_pilot_event(
            db, current_user.id, "invite_accepted", f"invite-accepted:{invite.id}",
            invite_id=invite.id, payload={"inviter_id": invite.inviter_id},
        )
    evaluate_circle_recovery(db, circle.id, now)
    db.commit()
    db.refresh(invite)
    return invite_read(invite)


@router.post("/apps/{app_id}/match-testers", response_model=MatchingRead)
def auto_match_testers(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> MatchingRead:
    app = owned_app(db, app_id, current_user)
    assigned = match_testers(db, app, now=now)
    for assignment in assigned:
        emit_pilot_event(
            db, current_user.id, "tester_assigned", f"pilot:tester-assigned:{assignment.id}",
            app_id=app.id, assignment_id=assignment.id,
        )
    db.commit()
    db.refresh(app)
    return MatchingRead(**matching_summary(app, len(assigned)))


@router.patch("/assignments/{assignment_id}/drop", response_model=AssignmentRead)
def drop_assignment(
    assignment_id: str,
    _body: DropAssignmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> AssignmentRead:
    assignment = assigned_to(db, assignment_id, current_user)
    if assignment.status != "DROPPED":
        assignment.status = "DROPPED"
        assignment.health_status = "DROPPED"
        assignment.dropped_at = now
        assignment.last_activity_at = now
        current_user.reliability_score -= 5
        emit_event(
            db,
            assignment.app_id,
            "TESTER_AT_RISK",
            f"health:{assignment.id}:DROPPED",
            assignment.id,
            {"health_status": "DROPPED"},
        )
        emit_pilot_event(
            db, current_user.id, "tester_dropped", f"tester-dropped:{assignment.id}",
            app_id=assignment.app_id, assignment_id=assignment.id,
        )
        match_testers(db, assignment.app, limit=1, replacement_for=assignment, now=now)
        evaluate_app_recovery(db, assignment.app, now)
    db.commit()
    db.refresh(assignment)
    return assignment_read(assignment, now)


@router.post("/apps/{app_id}/refresh-health", response_model=HealthRefreshRead)
def refresh_health(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> HealthRefreshRead:
    app = owned_app(db, app_id, current_user)
    newly_inactive = refresh_app_health(db, app, now)
    replacements = 0
    for inactive in newly_inactive:
        replacements += len(match_testers(db, app, limit=1, replacement_for=inactive, now=now))
    replacements += len(evaluate_app_recovery(db, app, now))
    readiness = calculate_readiness(db, app, now)
    counts = {
        "at_risk": sum(a.health_status == "AT_RISK" for a in app.assignments),
        "inactive": sum(a.health_status == "INACTIVE" for a in app.assignments),
        "dropped": sum(a.health_status == "DROPPED" for a in app.assignments),
        "replacements_assigned": replacements,
        "coverage_shortage": readiness["coverage_shortage"],
        "replacement_status": readiness["replacement_status"],
    }
    db.commit()
    return HealthRefreshRead(**counts)


@router.post("/apps/{app_id}/changes", response_model=AppChangeRead, status_code=201)
def record_app_change(
    app_id: str,
    body: AppChangeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> AppChangeRead:
    app = owned_app(db, app_id, current_user)
    change = AppChange(app=app, description=body.description.strip(), created_at=now)
    db.add(change)
    db.commit()
    db.refresh(change)
    return AppChangeRead(
        id=change.id, app_id=change.app_id, description=change.description, created_at=change.created_at
    )


@router.get("/apps/{app_id}/changes", response_model=list[AppChangeRead])
def list_app_changes(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AppChangeRead]:
    app = owned_app(db, app_id, current_user)
    return [
        AppChangeRead(id=row.id, app_id=row.app_id, description=row.description, created_at=row.created_at)
        for row in sorted(app.changes, key=lambda item: item.created_at)
    ]


@router.get("/apps/{app_id}/production-report")
def get_production_report(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> dict:
    app = owned_app(db, app_id, current_user)
    report = production_report(db, app, now)
    calculate_readiness(db, app, now)
    db.commit()
    return report


@router.get("/apps/{app_id}/production-application-draft")
def get_production_application_draft(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> dict:
    app = owned_app(db, app_id, current_user)
    return production_application_draft(db, app, now)


@router.get("/apps/{app_id}/workload", response_model=WorkloadRead)
def app_workload(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkloadRead:
    app = owned_app(db, app_id, current_user)
    return WorkloadRead(app_id=app.id, **workload_snapshot(db, app))


@router.post(
    "/apps/{app_id}/coordination-time",
    response_model=WorkloadRead,
    status_code=status.HTTP_201_CREATED,
)
def record_coordination_time(
    app_id: str,
    body: CoordinationTimeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> WorkloadRead:
    app = owned_app(db, app_id, current_user)
    entry = DeveloperCoordinationLog(
        app_id=app.id,
        owner_id=current_user.id,
        minutes=body.minutes,
        category=body.category,
        created_at=now,
    )
    db.add(entry)
    db.flush()
    emit_pilot_event(
        db,
        current_user.id,
        "developer_coordination_time_logged",
        f"coordination-time:{entry.id}",
        app_id=app.id,
        payload={"minutes": body.minutes, "category": body.category},
    )
    db.commit()
    return WorkloadRead(app_id=app.id, **workload_snapshot(db, app))


@router.get("/apps/{app_id}/managed-offer", response_model=ManagedOfferRead)
def app_managed_offer(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ManagedOfferRead:
    app = owned_app(db, app_id, current_user)
    return ManagedOfferRead(app_id=app.id, **managed_offer_snapshot(db, app))


@router.post(
    "/apps/{app_id}/managed-offer/viewed",
    response_model=ManagedOfferRead,
)
def record_managed_offer_view(
    app_id: str,
    body: ManagedOfferViewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> ManagedOfferRead:
    app = owned_app(db, app_id, current_user)
    snapshot = managed_offer_snapshot(db, app)
    if body.trigger != "PRIORITY" and body.trigger not in snapshot["triggers"]:
        raise HTTPException(status_code=409, detail="This Managed offer is no longer active")
    identity_method = (
        app.developer_account.identity_method if app.developer_account else "UNKNOWN"
    )
    emit_pilot_event(
        db,
        current_user.id,
        "managed_offer_viewed",
        f"managed-offer-viewed:{app.id}:{current_user.id}:{body.trigger}:{now.date().isoformat()}",
        app_id=app.id,
        payload={
            "trigger": body.trigger,
            "source": current_user.acquisition_source or "UNKNOWN",
            "developer_identity_method": identity_method,
        },
    )
    db.commit()
    return ManagedOfferRead(app_id=app.id, **snapshot)


@router.get("/apps/{app_id}/events")
def list_app_events(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    owned_app(db, app_id, current_user)
    rows = db.scalars(
        select(BackendEvent).where(BackendEvent.app_id == app_id).order_by(BackendEvent.created_at)
    )
    return [
        {
            "id": row.id,
            "event_type": row.event_type,
            "assignment_id": row.assignment_id,
            "payload_json": row.payload_json,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/apps/{app_id}/dashboard", response_model=DashboardRead)
def dashboard(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> DashboardRead:
    app = owned_app(db, app_id, current_user)
    for assignment in app.assignments:
        refresh_mission_availability(db, assignment.missions, now)
    evaluate_app_recovery(db, app, now, include_readiness=False)
    result = calculate_readiness(db, app, now)
    db.commit()
    return DashboardRead(**result)
