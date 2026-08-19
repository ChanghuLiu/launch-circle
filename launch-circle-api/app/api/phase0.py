import hashlib
import hmac
import secrets
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, get_current_user
from app.models.launch import (
    App, AppChange, BackendEvent, Feedback, Invite, TesterAssignment, TestMission,
)
from app.models.user import User
from app.schemas.auth import TokenPair
from app.schemas.phase0 import (
    AppChangeCreate,
    AppChangeRead,
    AppCreate,
    AppRead,
    AppUpdate,
    AssignmentRead,
    DashboardRead,
    DropAssignmentRequest,
    DevelopmentUserRead,
    FeedbackCreate,
    FeedbackRead,
    InviteCreate,
    InviteRead,
    HealthRefreshRead,
    GoogleGroupConfirmation,
    LoginRequest,
    MatchingRead,
    MissionRead,
    PilotConfigRead,
    RegisterRequest,
)
from app.services.clock import aware, get_now
from app.services.events import emit_event, emit_pilot_event
from app.services.lifecycle import establish_timeline
from app.services.matching import match_testers, matching_summary
from app.services.missions import MISSION_MINUTES, generate_missions, refresh_mission_availability
from app.services.reporting import production_application_draft, production_report
from app.services.tester_health import record_activity, refresh_app_health
from app.services.readiness import calculate_readiness

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


def app_read(app: App) -> AppRead:
    return AppRead(
        id=app.id,
        owner_id=app.owner_id,
        name=app.name,
        package_name=app.package_name,
        opt_in_url=app.opt_in_url,
        google_group_url=app.google_group_url,
        google_group_mode=app.google_group_mode,
        google_group_configured=app.google_group_configured,
        google_group_confirmed_at=app.google_group_confirmed_at,
        status=app.status,
        tester_target=app.tester_target,
        testing_start_at=app.testing_start_at,
        testing_end_at=app.testing_end_at,
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
        health_status=item.health_status,
        is_replacement=item.replacement_for_id is not None,
        replacement_for_id=item.replacement_for_id,
        last_activity_at=item.last_activity_at,
        testing_day=testing_day,
        completed_missions=completed,
        total_missions=len(item.missions),
    )


def mission_read(mission: TestMission) -> MissionRead:
    assignment = mission.assignment
    app = assignment.app
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
        created_at=item.created_at,
    )


def invite_read(item: Invite) -> InviteRead:
    invite_base_url = settings.launch_circle_invite_base_url.rstrip("/")
    return InviteRead(
        id=item.id,
        invite_code=item.invite_code,
        invited_email=item.invited_email,
        joined_user_id=item.joined_user_id,
        status=item.status,
        created_at=item.created_at,
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


@router.post("/apps", response_model=AppRead, status_code=status.HTTP_201_CREATED)
def create_app(
    body: AppCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppRead:
    app = App(
        owner_id=current_user.id,
        name=body.name,
        package_name=body.package_name,
        opt_in_url=str(body.opt_in_url),
        google_group_url=str(body.google_group_url) if body.google_group_url else (
            settings.launch_circle_google_group_join_url
            if body.google_group_mode == "LAUNCH_CIRCLE" else None
        ),
        google_group_mode=body.google_group_mode,
        status="WAITING_FOR_TESTERS",
        tester_target=body.tester_target,
    )
    db.add(app)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Package name is already registered") from exc
    db.refresh(app)
    return app_read(app)


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
    duplicate = db.scalar(
        select(TesterAssignment).where(
            TesterAssignment.app_id == app_id,
            TesterAssignment.tester_id == tester_id,
            TesterAssignment.status != "DROPPED",
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Tester already has an active assignment")
    assignment = TesterAssignment(app_id=app_id, tester_id=tester_id, status="ASSIGNED")
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
    establish_timeline(db, assignment.app, now)
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


@router.post("/invites", response_model=InviteRead, status_code=status.HTTP_201_CREATED)
def create_invite(
    body: InviteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InviteRead:
    invite = Invite(
        inviter_id=current_user.id,
        invite_code=generate_invite_code(db),
        invited_email=str(body.invited_email).lower() if body.invited_email else None,
        status="PENDING",
    )
    db.add(invite)
    db.flush()
    emit_pilot_event(
        db, current_user.id, "invite_created", f"invite-created:{invite.id}",
        invite_id=invite.id,
    )
    db.commit()
    db.refresh(invite)
    return invite_read(invite)


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
) -> InviteRead:
    invite = db.scalar(select(Invite).where(Invite.invite_code == invite_code.upper()))
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.inviter_id == current_user.id:
        raise HTTPException(status_code=422, detail="You cannot accept your own invite")
    if invite.status == "ACCEPTED" and invite.joined_user_id != current_user.id:
        raise HTTPException(status_code=409, detail="Invite was already accepted")
    if invite.status == "CANCELLED":
        raise HTTPException(status_code=409, detail="Invite is no longer active")
    if invite.invited_email and invite.invited_email != current_user.email:
        raise HTTPException(status_code=403, detail="Invite is intended for another email")
    first_acceptance = invite.status != "ACCEPTED"
    invite.status = "ACCEPTED"
    invite.joined_user_id = current_user.id
    invite.accepted_at = invite.accepted_at or datetime.now(timezone.utc)
    if first_acceptance:
        emit_pilot_event(
            db, current_user.id, "invite_accepted", f"invite-accepted:{invite.id}",
            invite_id=invite.id, payload={"inviter_id": invite.inviter_id},
        )
    db.commit()
    db.refresh(invite)
    return invite_read(invite)


@router.post("/apps/{app_id}/match-testers", response_model=MatchingRead)
def auto_match_testers(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatchingRead:
    app = owned_app(db, app_id, current_user)
    assigned = match_testers(db, app)
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
        match_testers(db, assignment.app, limit=1, replacement_for=assignment)
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
        replacements += len(match_testers(db, app, limit=1, replacement_for=inactive))
    calculate_readiness(db, app, now)
    counts = {
        "at_risk": sum(a.health_status == "AT_RISK" for a in app.assignments),
        "inactive": sum(a.health_status == "INACTIVE" for a in app.assignments),
        "dropped": sum(a.health_status == "DROPPED" for a in app.assignments),
        "replacements_assigned": replacements,
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
    refresh_app_health(db, app, now)
    result = calculate_readiness(db, app, now)
    db.commit()
    return DashboardRead(**result)
