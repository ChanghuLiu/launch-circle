"""Owner-published opportunities, voluntary per-app acceptance, bounded shared supply."""

from datetime import datetime
from typing import Annotated
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.admin import AdminAppControl, AdminRecommendation
from app.models.launch import App, BackendEvent, Circle, CircleMember, TesterAssignment
from app.models.pool import (
    AppGroup,
    AppGroupApp,
    AppGroupMember,
    AppGroupTaskQueue,
    PoolListing,
    TesterPoolPreference,
)
from app.models.user import User
from app.services.assignments import assignment_day
from app.services.circles import active_member_count
from app.services.clock import get_now
from app.services.dispatch_authorization import (
    app_group_is_closed,
    explicitly_consented_assignment_ids,
    has_app_group_consent,
    has_direct_app_consent,
)
from app.services.events import emit_event
from app.services.lifecycle import GOOGLE_MINIMUM, TOTAL_DAYS, active_qualifying, timeline_values

router = APIRouter(tags=["shared-tester-pool"])


def active_actor(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_active:
        raise HTTPException(403, "Account is not active")
    return user


Actor = Annotated[User, Depends(active_actor)]
Database = Annotated[Session, Depends(get_db)]
Clock = Annotated[datetime, Depends(get_now)]
OPEN_STATES = {"WAITING_FOR_TESTERS", "TESTING", "AT_RISK"}
MAX_CONCURRENT_APPS = 2


class OptIn(BaseModel):
    enabled: bool


class AppGroupJoinConsent(BaseModel):
    consent: bool


def lock_writes(db: Session, actor: User):
    # Acquire the SQLite writer lock before checking quotas, preventing two
    # concurrent acceptances from passing the same user/circle capacity check.
    db.execute(update(User).where(User.id == actor.id).values(is_active=User.is_active))


def owned(db: Session, app_id: str, actor: User) -> App:
    item = db.get(App, app_id)
    if item is None or item.owner_id != actor.id:
        raise HTTPException(404, "App not found")
    return item


def active_work(db: Session, user_id: str) -> int:
    return (
        db.scalar(
            select(func.count(TesterAssignment.id))
            .join(App)
            .where(
                TesterAssignment.tester_id == user_id,
                TesterAssignment.status.in_({"ASSIGNED", "OPTED_IN", "INSTALLED", "ACTIVE"}),
                App.status.in_(OPEN_STATES),
            )
        )
        or 0
    )


def current_assignments(item: App):
    return [a for a in item.assignments if a.status != "DROPPED"]


def profile_complete(item: App) -> bool:
    url = urlparse(item.opt_in_url)
    return bool(
        item.ownership_authorized
        and item.google_group_configured
        and bool(item.icon_url and item.icon_url.strip())
        and item.core_workflow_steps
        and url.scheme == "https"
        and url.netloc == "play.google.com"
        and url.path.rstrip("/") == "/apps/testing/" + item.package_name
    )


def ready(item: App) -> bool:
    return item.status in OPEN_STATES and profile_complete(item)


def supply(db: Session, item: App) -> dict:
    assignments = [a for a in current_assignments(item) if a.tester_id != item.owner_id]
    joined = sum(
        a.opted_in_at is not None
        and a.installed_at is not None
        and a.health_status not in {"DROPPED", "INACTIVE"}
        for a in assignments
    )
    listing = db.get(PoolListing, item.id)
    return {
        "app_id": item.id,
        "name": item.name,
        "listed": bool(listing and listing.enabled),
        "ready_to_list": ready(item),
        "accepted_participants": len(assignments),
        "reported_joined_and_installed": joined,
        "minimum": 12,
        "buffer_target": 14,
        "missing_to_minimum": max(0, 12 - joined),
        "google_eligibility_confirmed": False,
    }


@router.get("/tester-pool/me")
def my_pool(actor: Actor, db: Database):
    pref = db.get(TesterPoolPreference, actor.id)
    return {
        "enabled": bool(pref and pref.enabled),
        "active_apps": active_work(db, actor.id),
        "max_concurrent_apps": MAX_CONCURRENT_APPS,
    }


@router.post("/tester-pool/me")
def set_pool(body: OptIn, actor: Actor, db: Database, now: Clock):
    lock_writes(db, actor)
    pref = db.get(TesterPoolPreference, actor.id)
    if pref is None:
        pref = TesterPoolPreference(user_id=actor.id, updated_at=now)
        db.add(pref)
    if body.enabled and not pref.enabled:
        pref.consent_at = now
    pref.enabled, pref.updated_at = body.enabled, now
    db.commit()
    return my_pool(actor, db)


@router.get("/tester-pool/opportunities")
def opportunities(actor: Actor, db: Database):
    return opportunities_for_browse(actor, db)


def opportunities_for_browse(actor: User, db: Session):
    if active_work(db, actor.id) >= MAX_CONCURRENT_APPS:
        return []
    # Bounded discovery, no emails, participant IDs or private access credentials.
    rows = db.scalars(
        select(App)
        .join(PoolListing)
        .join(User, User.id == App.owner_id)
        .outerjoin(AdminAppControl, AdminAppControl.app_id == App.id)
        .outerjoin(AdminRecommendation, and_(
            AdminRecommendation.app_id == App.id, AdminRecommendation.tester_id == actor.id
        ))
        .where(
            or_(AdminAppControl.app_id.is_(None), and_(
                AdminAppControl.paused.is_(False), AdminAppControl.kind != "SYNTHETIC"
            )),
            PoolListing.enabled.is_(True),
            App.owner_id != actor.id,
            User.is_active.is_(True),
            App.status.in_(OPEN_STATES),
        )
        .order_by(
            AdminRecommendation.tester_id.is_(None),
            func.coalesce(AdminAppControl.priority, 50).desc(),
            PoolListing.updated_at, App.id,
        )
        .limit(100)
    ).all()
    assignment_ids = [
        assignment.id
        for item in rows
        for assignment in item.assignments
        if assignment.tester_id == actor.id
    ]
    direct_consent_ids = explicitly_consented_assignment_ids(db, actor.id, assignment_ids)
    result = []
    for item in rows:
        prior = [a for a in item.assignments if a.tester_id == actor.id]
        has_authorized_prior = (
            has_app_group_consent(db, item.id, actor.id)
            or any(a.id in direct_consent_ids for a in prior)
        )
        if item.no_test_required or not ready(item) or has_authorized_prior:
            continue
        circle = db.get(Circle, item.circle_id)
        member = db.scalar(
            select(CircleMember).where(
                CircleMember.circle_id == item.circle_id, CircleMember.user_id == actor.id
            )
        )
        if (
            circle is None
            or (not member or member.status != "ACTIVE")
            and (active_member_count(db, circle.id) >= min(circle.max_members, 15))
        ):
            continue
        if len(current_assignments(item)) >= min(item.tester_target, 14):
            continue
        result.append(
            {
                "app_id": item.id,
                "name": item.name,
                "package_name": item.package_name,
                "workflow_steps": item.core_workflow_steps,
            }
        )
    return result


@router.get("/tester-pool/apps")
def community_apps(actor: Actor, db: Database):
    eligible = {row["app_id"] for row in opportunities_for_browse(actor, db)}
    # Discovery includes all real apps; recruitment only controls acceptance.
    rows = db.scalars(select(App).join(User, User.id == App.owner_id)
        .outerjoin(AdminAppControl, AdminAppControl.app_id == App.id)
        .where(User.is_active.is_(True),
            or_(AdminAppControl.app_id.is_(None), AdminAppControl.kind != "SYNTHETIC"))
        .order_by(App.created_at.desc(), App.id)).all()
    assignment_ids = [
        assignment.id
        for item in rows
        for assignment in item.assignments
        if assignment.tester_id == actor.id
    ]
    direct_consent_ids = explicitly_consented_assignment_ids(db, actor.id, assignment_ids)
    return [{"app_id": item.id, "name": item.name, "package_name": item.package_name,
             "workflow_steps": item.core_workflow_steps, "icon_url": item.icon_url,
             "owned": item.owner_id == actor.id,
             "joined": has_app_group_consent(db, item.id, actor.id) or any(
                 a.tester_id == actor.id and a.id in direct_consent_ids for a in item.assignments
             ),
             "available": item.id in eligible} for item in rows if profile_complete(item)]


@router.get("/apps/{app_id}/supply")
def get_supply(app_id: str, actor: Actor, db: Database):
    return supply(db, owned(db, app_id, actor))


@router.post("/apps/{app_id}/pool-listing")
def set_listing(app_id: str, body: OptIn, actor: Actor, db: Database, now: Clock):
    owned(db, app_id, actor)
    raise HTTPException(403, "Recruitment is managed by the administrator. Complete app setup to appear on Home.")


@router.post("/apps/{app_id}/tester-pool/accept")
def accept_opportunity(app_id: str, actor: Actor, db: Database, now: Clock):
    return accept_app(app_id, actor, db, now)


def accept_app(
    app_id: str,
    actor: User,
    db: Session,
    now: datetime,
    *,
    max_apps: int = MAX_CONCURRENT_APPS,
    commit: bool = True,
    consent_scope: str = "APP",
):
    lock_writes(db, actor)
    item = db.get(App, app_id)
    listing = db.get(PoolListing, app_id)
    control = db.get(AdminAppControl, app_id)
    if (
        (control and (control.paused or control.kind == "SYNTHETIC"))
        or item is None
        or item.no_test_required
        or not listing
        or not listing.enabled
        or not ready(item)
        or not db.get(User, item.owner_id).is_active
    ):
        raise HTTPException(404, "Opportunity not available")
    if app_group_is_closed(db, app_id):
        raise HTTPException(409, "APP_GROUP_CLOSED")
    if item.owner_id == actor.id:
        raise HTTPException(422, "You cannot accept your own app")
    # This accepts this app only. Circle membership added below is for this
    # app's circle and must never be treated as consent to other circle apps.
    existing = db.scalar(
        select(TesterAssignment).where(
            TesterAssignment.app_id == app_id, TesterAssignment.tester_id == actor.id
        )
    )
    if existing:
        if existing.status == "DROPPED":
            raise HTTPException(409, "A previous assignment was dropped; contact the owner")
        if not has_app_group_consent(db, item.id, actor.id) and not has_direct_app_consent(
            db, existing.id, actor.id
        ):
            # A fresh explicit Join testing action can authorize an old implicit
            # row without deleting its history or creating a duplicate task.
            emit_event(
                db,
                item.id,
                "APP_TEST_ACCEPTED",
                "APP_TEST_ACCEPTED:" + existing.id,
                existing.id,
                {"source": "VOLUNTARY_SHARED_POOL", "consent_scope": "APP"},
            )
            if commit:
                db.commit()
        return {"assignment_id": existing.id, "status": existing.status}
    if active_work(db, actor.id) >= max_apps:
        raise HTTPException(409, "Concurrent app limit reached")
    todays_created_count = db.scalar(
        select(func.count(TesterAssignment.id)).where(
            TesterAssignment.tester_id == actor.id,
            TesterAssignment.assignment_day == assignment_day(now),
        )
    ) or 0
    if todays_created_count >= 2:
        raise HTTPException(409, "DAILY_ASSIGNMENT_LIMIT_REACHED")
    if len(current_assignments(item)) >= min(item.tester_target, 14):
        raise HTTPException(409, "This app has enough accepted participants")
    circle = db.get(Circle, item.circle_id)
    if circle is None:
        raise HTTPException(409, "Circle unavailable")
    member = db.scalar(
        select(CircleMember).where(
            CircleMember.circle_id == circle.id, CircleMember.user_id == actor.id
        )
    )
    if not member or member.status != "ACTIVE":
        if active_member_count(db, circle.id) >= min(circle.max_members, 15):
            raise HTTPException(409, "Circle is full")
        if member is None:
            db.add(
                CircleMember(
                    circle_id=circle.id,
                    user_id=actor.id,
                    role="MEMBER",
                    status="ACTIVE",
                    joined_at=now,
                )
            )
        else:
            member.status, member.joined_at, member.left_at = "ACTIVE", now, None
    assignment = TesterAssignment(
        app=item,
        circle_id=circle.id,
        tester_id=actor.id,
        assignment_day=assignment_day(now),
        assigned_at=now,
        test_type="APP_CHECK",
        status="ASSIGNED",
        health_status="NEW",
    )
    db.add(assignment)
    db.flush()
    emit_event(
        db,
        item.id,
        "TESTER_ASSIGNED",
        "TESTER_ASSIGNED:" + assignment.id,
        assignment.id,
        {"source": "VOLUNTARY_SHARED_POOL", "consent_scope": consent_scope},
    )
    if commit:
        db.commit()
    # This is task acceptance only. Existing Play opt-in and installation
    # confirmations remain separate, with no fabricated dates or headcount.
    return {"assignment_id": assignment.id, "status": assignment.status}


GROUP_CAPACITY = 15


def app_group_status(group: AppGroup, app_count: int) -> str:
    if group.status != "OPEN":
        return "CLOSED"
    return "FULL" if app_count >= GROUP_CAPACITY else "FORMING"


def app_group_member_count(db: Session, group_id: str) -> int:
    return int(db.scalar(
        select(func.count(AppGroupMember.user_id))
        .join(User, User.id == AppGroupMember.user_id)
        .where(AppGroupMember.group_id == group_id, User.is_active.is_(True))
    ) or 0)


def app_group_test_counts(db: Session, group_id: str) -> tuple[int, int]:
    apps = db.scalars(
        select(App).join(AppGroupApp, AppGroupApp.app_id == App.id)
        .where(AppGroupApp.group_id == group_id)
    ).all()
    exempt = sum(bool(item.no_test_required) for item in apps)
    return len(apps) - exempt, exempt


def app_group_app_progress(db: Session, item: App, now: datetime) -> dict:
    timeline = timeline_values(item, now)
    return {
        "no_test_required": bool(item.no_test_required),
        "qualified_tester_count": len(active_qualifying(db, item)),
        "required_tester_count": GOOGLE_MINIMUM,
        "testing_started_at": item.testing_start_at,
        "day": timeline["day"],
        "total_days": TOTAL_DAYS,
        "status": item.status,
    }


@router.get("/apps/{app_id}/app-groups")
def app_groups_for_owned_app(app_id: str, actor: Actor, db: Database, now: Clock):
    item = owned(db, app_id, actor)
    if not ready(item):
        raise HTTPException(409, "APP_SETUP_INCOMPLETE")
    control = db.get(AdminAppControl, item.id)
    if item.no_test_required or (control and (control.paused or control.kind == "SYNTHETIC")):
        raise HTTPException(409, "APP_ADMIN_REVIEW_REQUIRED")

    existing = db.get(AppGroupApp, item.id)
    owner_joined = bool(existing and db.get(AppGroupMember, (existing.group_id, actor.id)))
    groups = ([db.get(AppGroup, existing.group_id)] if existing else
              list(db.scalars(select(AppGroup).order_by(AppGroup.created_at, AppGroup.id))))
    result = []
    for group in groups:
        if group is None:
            continue
        test_required_app_count, exempt_app_count = app_group_test_counts(db, group.id)
        app_count = test_required_app_count + exempt_app_count
        same_owner_app = db.scalar(
            select(AppGroupApp.app_id)
            .join(App, App.id == AppGroupApp.app_id)
            .where(AppGroupApp.group_id == group.id, App.owner_id == actor.id, App.id != item.id)
            .limit(1)
        )
        status = app_group_status(group, app_count)
        can_select = (
            group.status == "OPEN"
            and (existing is not None or (app_count < GROUP_CAPACITY and same_owner_app is None))
        )
        result.append({
            "id": group.id,
            "name": group.name,
            "status": status,
            "capacity": GROUP_CAPACITY,
            "occupied_slots": app_count,
            "remaining_app_slots": max(0, GROUP_CAPACITY - app_count),
            "test_required_app_count": test_required_app_count,
            "exempt_app_count": exempt_app_count,
            "member_count": app_group_member_count(db, group.id),
            "can_select": can_select,
            "already_selected": existing is not None and existing.group_id == group.id,
            "owner_joined": owner_joined and existing is not None and existing.group_id == group.id,
        })
    return {
        "app_id": item.id,
        "app_name": item.name,
        "groups": result,
        "app_progress": app_group_app_progress(db, item, now),
    }


@router.post("/apps/{app_id}/app-groups/{group_id}/join")
def join_app_group_for_app(
    app_id: str,
    group_id: str,
    body: AppGroupJoinConsent,
    actor: Actor,
    db: Database,
    now: Clock,
):
    if not body.consent:
        raise HTTPException(422, "APP_GROUP_CONSENT_REQUIRED")

    # End the authentication read transaction before acquiring the write lock.
    # SQLite serializes writers globally; databases with row locks also lock the
    # selected group so two owners cannot claim its last App slot concurrently.
    actor_id = actor.id
    db.commit()
    db.execute(update(User).where(User.id == actor_id).values(is_active=User.is_active))
    item = owned(db, app_id, actor)
    if not ready(item):
        raise HTTPException(409, "APP_SETUP_INCOMPLETE")
    control = db.get(AdminAppControl, item.id)
    if item.no_test_required or (control and (control.paused or control.kind == "SYNTHETIC")):
        raise HTTPException(409, "APP_ADMIN_REVIEW_REQUIRED")

    group = db.scalar(select(AppGroup).where(AppGroup.id == group_id).with_for_update())
    if group is None:
        raise HTTPException(404, "APP_GROUP_NOT_FOUND")

    mapping = db.get(AppGroupApp, item.id)
    if mapping and mapping.group_id != group.id:
        raise HTTPException(409, "APP_ALREADY_IN_ANOTHER_GROUP")
    member = db.get(AppGroupMember, (group.id, actor_id))
    if mapping and member:
        result = {
            "ok": True,
            "group_id": group.id,
            "already_joined": True,
            "active_app_testers": sum(
                assignment.tester_id != actor_id
                and assignment.status not in {"DROPPED", "COMPLETED"}
                and assignment.health_status not in {"DROPPED", "INACTIVE"}
                for assignment in item.assignments
            ),
            "qualified_tester_count": len(active_qualifying(db, item)),
            "testing_started_at": item.testing_start_at,
            "day": timeline_values(item, now)["day"],
        }
        db.rollback()
        return result

    other_group = db.scalar(select(AppGroupMember.group_id).where(
        AppGroupMember.user_id == actor_id, AppGroupMember.group_id != group.id
    ).limit(1))
    if other_group:
        raise HTTPException(409, "OWNER_ALREADY_IN_ANOTHER_APP_GROUP")

    if group.status != "OPEN":
        raise HTTPException(409, "APP_GROUP_CLOSED")
    app_count = int(db.scalar(
        select(func.count(AppGroupApp.app_id)).where(AppGroupApp.group_id == group.id)
    ) or 0)
    if mapping is None and app_count >= GROUP_CAPACITY:
        raise HTTPException(409, "APP_GROUP_FULL")
    same_owner_app = db.scalar(
        select(AppGroupApp.app_id)
        .join(App, App.id == AppGroupApp.app_id)
        .where(AppGroupApp.group_id == group.id, App.owner_id == actor_id, App.id != item.id)
        .limit(1)
    )
    if same_owner_app:
        raise HTTPException(409, "OWNER_ALREADY_HAS_APP_IN_GROUP")

    listing = db.get(PoolListing, item.id)
    if listing is None:
        listing = PoolListing(app_id=item.id, updated_at=now)
        db.add(listing)
    listing.enabled, listing.updated_at = True, now
    if mapping is None:
        db.add(AppGroupApp(app_id=item.id, group_id=group.id))
    if member is None:
        db.add(AppGroupMember(group_id=group.id, user_id=actor_id, joined_at=now))
    db.flush()

    # Existing group consent authorizes sync. The owner is included as a group
    # member but accept_app excludes the owner's own App.
    before_ids = set(db.scalars(
        select(TesterAssignment.id).where(TesterAssignment.app_id == item.id)
    ))
    sync_group(db, group.id, now)
    db.flush()
    after_ids = set(db.scalars(
        select(TesterAssignment.id).where(TesterAssignment.app_id == item.id)
    ))
    active_app_testers = int(db.scalar(
        select(func.count(TesterAssignment.id)).where(
            TesterAssignment.app_id == item.id,
            TesterAssignment.tester_id != actor_id,
            TesterAssignment.status.notin_(["DROPPED", "COMPLETED"]),
            TesterAssignment.health_status.notin_(["DROPPED", "INACTIVE"]),
        )
    ) or 0)
    db.commit()
    return {
        "ok": True,
        "group_id": group.id,
        "already_joined": False,
        "new_app_tasks": len(after_ids - before_ids),
        "active_app_testers": active_app_testers,
        "qualified_tester_count": len(active_qualifying(db, item)),
        "testing_started_at": item.testing_start_at,
        "day": timeline_values(item, now)["day"],
    }


def group_apps(db: Session, group_id: str):
    return db.scalars(select(App).join(AppGroupApp, AppGroupApp.app_id == App.id)
        .where(AppGroupApp.group_id == group_id).order_by(App.created_at, App.id)).all()


def visible_group_apps(db: Session, group_id: str):
    group = db.get(AppGroup, group_id)
    if group is None or group.status != "OPEN":
        return []
    result = []
    for item in group_apps(db, group_id):
        listing = db.get(PoolListing, item.id)
        control = db.get(AdminAppControl, item.id)
        if listing and listing.enabled and ready(item) and db.get(User, item.owner_id).is_active and not (control and (control.paused or control.kind == "SYNTHETIC")):
            result.append(item)
    return result


def _queue_group_tasks(db: Session, group_id: str, now: datetime) -> None:
    group = db.scalar(select(AppGroup).where(AppGroup.id == group_id).with_for_update())
    if group is None or group.status != "OPEN":
        return
    for member in db.scalars(select(AppGroupMember).where(AppGroupMember.group_id == group_id)):
        actor = db.get(User, member.user_id)
        if not actor or not actor.is_active:
            continue
        for item in visible_group_apps(db, group_id):
            if item.no_test_required or item.owner_id == actor.id:
                continue
            queued = db.scalar(select(AppGroupTaskQueue).where(
                AppGroupTaskQueue.group_id == group_id,
                AppGroupTaskQueue.app_id == item.id,
                AppGroupTaskQueue.tester_id == actor.id,
            ))
            if queued is None:
                db.add(AppGroupTaskQueue(
                    id=str(uuid4()), group_id=group_id, app_id=item.id,
                    tester_id=actor.id, status="PENDING", created_at=now,
                ))
            elif queued.status == "CANCELLED":
                queued.status = "PENDING"
                queued.created_at = now
                queued.dispatched_at = None
                queued.assignment_id = None
    db.flush()


def _resume_left_assignment(db: Session, group_id: str, item: App, actor: User, now: datetime) -> None:
    import json

    previous = db.scalar(select(TesterAssignment).where(
        TesterAssignment.app_id == item.id,
        TesterAssignment.tester_id == actor.id,
        TesterAssignment.status == "DROPPED",
    ).order_by(TesterAssignment.assigned_at.desc()))
    if previous is None or active_work(db, actor.id) >= MAX_CONCURRENT_APPS:
        return
    event = db.scalar(select(BackendEvent).where(
        BackendEvent.assignment_id == previous.id,
        BackendEvent.event_type == "APP_GROUP_LEFT",
    ).order_by(BackendEvent.created_at.desc()).limit(1))
    if event is None:
        return
    saved = json.loads(event.payload_json)
    if saved.get("group_id") != group_id:
        return
    circle = db.get(Circle, previous.circle_id)
    membership = db.scalar(select(CircleMember).where(
        CircleMember.circle_id == previous.circle_id,
        CircleMember.user_id == actor.id,
    ))
    if membership is None or membership.status != "ACTIVE":
        if circle is None or active_member_count(db, circle.id) >= min(circle.max_members, 15):
            return
        if membership:
            membership.status, membership.joined_at, membership.left_at = "ACTIVE", now, None
        else:
            db.add(CircleMember(
                circle_id=circle.id, user_id=actor.id, role="MEMBER",
                status="ACTIVE", joined_at=now,
            ))
    previous.status = saved.get("previous_status", "ASSIGNED")
    previous.health_status = saved.get("previous_health", "NEW")
    previous.dropped_at = None
    db.flush()


def dispatch_group_tasks(db: Session, now: datetime, *, group_id: str | None = None, tester_id: str | None = None) -> int:
    """Dispatch consented FIFO tasks within per-day and active-work limits."""
    if group_id:
        groups = [group_id]
    elif tester_id:
        groups = list(db.scalars(
            select(AppGroupMember.group_id)
            .join(AppGroup, AppGroup.id == AppGroupMember.group_id)
            .where(AppGroupMember.user_id == tester_id, AppGroup.status == "OPEN")
        ))
    else:
        groups = list(db.scalars(select(AppGroup.id).where(AppGroup.status == "OPEN")))
    if tester_id:
        for current_group_id in groups:
            _queue_group_tasks(db, current_group_id, now)
    dispatched = 0
    for current_group_id in groups:
        group = db.scalar(select(AppGroup).where(AppGroup.id == current_group_id).with_for_update())
        if group is None or group.status != "OPEN":
            db.execute(update(AppGroupTaskQueue).where(
                AppGroupTaskQueue.group_id == current_group_id,
                AppGroupTaskQueue.status == "PENDING",
            ).values(status="CANCELLED"))
            continue
        query = select(AppGroupTaskQueue).where(
            AppGroupTaskQueue.group_id == current_group_id,
            AppGroupTaskQueue.status == "PENDING",
        ).join(App, App.id == AppGroupTaskQueue.app_id).order_by(
            AppGroupTaskQueue.created_at, App.created_at, App.id,
        )
        if tester_id:
            query = query.where(AppGroupTaskQueue.tester_id == tester_id)
        for queued in db.scalars(query):
            member = db.get(AppGroupMember, (current_group_id, queued.tester_id))
            mapping = db.get(AppGroupApp, queued.app_id)
            actor = db.get(User, queued.tester_id)
            item = db.get(App, queued.app_id)
            if not member or not mapping or mapping.group_id != current_group_id or not actor or not actor.is_active:
                queued.status = "CANCELLED"
                continue
            if item is None or item.owner_id == actor.id or item.no_test_required:
                queued.status = "CANCELLED"
                continue
            _resume_left_assignment(db, current_group_id, item, actor, now)
            try:
                result = accept_app(
                    item.id, actor, db, now, max_apps=MAX_CONCURRENT_APPS,
                    commit=False, consent_scope="APP_GROUP",
                )
            except HTTPException as error:
                if error.status_code in {404, 409}:
                    # A quota/capacity issue remains queued; an invalid app is
                    # cancelled and can be re-enqueued after an explicit change.
                    if error.detail in {"Opportunity not available", "APP_GROUP_CLOSED"}:
                        queued.status = "CANCELLED"
                    elif error.detail == "A previous assignment was dropped; contact the owner":
                        queued.status = "SKIPPED"
                    continue
                raise
            queued.status = "DISPATCHED"
            queued.dispatched_at = now
            queued.assignment_id = result["assignment_id"]
            dispatched += 1
    db.flush()
    return dispatched


def sync_group(db: Session, group_id: str, now: datetime):
    # Explicit group consent authorizes these peer tasks, while the dispatcher
    # enforces both the two-per-day rule and the existing active-work ceiling.
    _queue_group_tasks(db, group_id, now)
    return dispatch_group_tasks(db, now, group_id=group_id)


@router.get("/app-groups")
def list_app_groups(actor: Actor, db: Database):
    result = []
    for group in db.scalars(select(AppGroup).order_by(AppGroup.created_at, AppGroup.id)):
        slots = group_apps(db, group.id)
        apps = visible_group_apps(db, group.id)
        own = any(app.owner_id == actor.id for app in slots)
        joined = db.get(AppGroupMember, (group.id, actor.id)) is not None
        if not apps and not own and not joined:
            continue
        result.append({"id": group.id, "name": (f"{slots[0].name} Group" if group.name.startswith("App Group ") and group.name[10:].isdigit() and slots else group.name), "capacity": max(GROUP_CAPACITY, len(slots)),
            "status": app_group_status(group, len(slots)),
            "occupied_slots": len(slots), "ready_to_join": any(app.owner_id == actor.id for app in apps),
            "test_required_app_count": sum(not app.no_test_required for app in slots),
            "exempt_app_count": sum(bool(app.no_test_required) for app in slots),
            "member_count": app_group_member_count(db, group.id),
            "my_group": own, "joined": joined,
            "apps": [{"app_id": app.id, "name": app.name, "package_name": app.package_name,
                "icon_url": app.icon_url, "owned": app.owner_id == actor.id,
                "no_test_required": bool(app.no_test_required),
                "workflow_steps": app.core_workflow_steps} for app in apps]})
    return result


@router.post("/app-groups/{group_id}/join")
def join_app_group(group_id: str, actor: Actor, db: Database, now: Clock):
    lock_writes(db, actor)
    apps = visible_group_apps(db, group_id)
    if not any(app.owner_id == actor.id for app in apps):
        raise HTTPException(409, "Add and configure your app first; it is matched to a group automatically")
    other = db.scalar(select(AppGroupMember).where(AppGroupMember.user_id == actor.id, AppGroupMember.group_id != group_id))
    if other:
        raise HTTPException(409, "You already joined another App Group")
    if db.get(AppGroupMember, (group_id, actor.id)) is None:
        db.add(AppGroupMember(group_id=group_id, user_id=actor.id, joined_at=now))
        db.flush()
    sync_group(db, group_id, now)
    db.commit()
    return {"ok": True, "group_id": group_id}


@router.post("/app-groups/{group_id}/leave")
def leave_app_group(group_id: str, actor: Actor, db: Database, now: Clock):
    lock_writes(db, actor)
    member = db.get(AppGroupMember, (group_id, actor.id))
    owned_apps = [app for app in group_apps(db, group_id) if app.owner_id == actor.id]
    if member is None and not owned_apps:
        return {"ok": True, "already_left": True}
    app_ids = [app.id for app in group_apps(db, group_id)]
    owned_ids = [app.id for app in owned_apps]
    db.execute(update(AppGroupTaskQueue).where(
        AppGroupTaskQueue.group_id == group_id,
        or_(AppGroupTaskQueue.tester_id == actor.id, AppGroupTaskQueue.app_id.in_(owned_ids or ["__none__"])),
        AppGroupTaskQueue.status.in_({"PENDING", "DISPATCHED"}),
    ).values(status="CANCELLED"))
    rows = db.scalars(select(TesterAssignment).where(
        TesterAssignment.app_id.in_(app_ids),
        or_(TesterAssignment.tester_id == actor.id, TesterAssignment.app_id.in_(owned_ids)),
        TesterAssignment.status.notin_(["DROPPED", "COMPLETED"]))).all()
    for row in rows:
        emit_event(db, row.app_id, "APP_GROUP_LEFT", f"group-left:{group_id}:{row.id}:{now.isoformat()}", row.id,
            {"group_id": group_id, "previous_status": row.status, "previous_health": row.health_status})
        row.status, row.health_status, row.dropped_at = "DROPPED", "DROPPED", now
    db.flush()
    for circle_id, tester_id in {(row.circle_id, row.tester_id) for row in rows}:
        circle = db.get(Circle, circle_id)
        if circle is None or circle.owner_id == tester_id:
            continue
        remaining = db.scalar(select(TesterAssignment.id).where(TesterAssignment.circle_id == circle_id,
            TesterAssignment.tester_id == tester_id, TesterAssignment.status.notin_(["DROPPED", "COMPLETED"])).limit(1))
        if remaining is None:
            membership = db.scalar(select(CircleMember).where(CircleMember.circle_id == circle_id, CircleMember.user_id == tester_id))
            if membership:
                membership.status, membership.left_at = "LEFT", now
    if member:
        db.delete(member)
    for item in owned_apps:
        mapping = db.get(AppGroupApp, item.id)
        if mapping:
            db.delete(mapping)
    db.flush()
    from app.services.recovery import evaluate_app_recovery
    for item in db.scalars(select(App).where(App.id.in_(app_ids))):
        evaluate_app_recovery(db, item, now)
    db.commit()
    return {"ok": True, "already_left": False}
