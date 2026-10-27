"""Owner-published opportunities, voluntary per-app acceptance, bounded shared supply."""

from datetime import datetime
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.admin import AdminAppControl, AdminRecommendation
from app.models.launch import App, Circle, CircleMember, TesterAssignment
from app.models.pool import PoolListing, TesterPoolPreference, AppGroup, AppGroupApp, AppGroupMember
from app.models.user import User
from app.services.assignments import assignment_day
from app.services.circles import active_member_count
from app.services.clock import get_now
from app.services.events import emit_event

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
                TesterAssignment.status != "DROPPED",
                App.status.in_(OPEN_STATES),
            )
        )
        or 0
    )


def current_assignments(item: App):
    return [a for a in item.assignments if a.status != "DROPPED"]


def ready(item: App) -> bool:
    url = urlparse(item.opt_in_url)
    return bool(
        item.status in OPEN_STATES
        and item.google_group_configured
        and item.core_workflow_steps
        and url.scheme == "https"
        and url.netloc == "play.google.com"
        and url.path.rstrip("/") == "/apps/testing/" + item.package_name
    )


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
    result = []
    for item in rows:
        if not ready(item) or any(a.tester_id == actor.id for a in item.assignments):
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
    rows = db.scalars(select(App).join(PoolListing).join(User, User.id == App.owner_id)
        .outerjoin(AdminAppControl, AdminAppControl.app_id == App.id)
        .where(PoolListing.enabled.is_(True), User.is_active.is_(True), App.status.in_(OPEN_STATES),
            or_(AdminAppControl.app_id.is_(None), and_(AdminAppControl.paused.is_(False), AdminAppControl.kind != "SYNTHETIC")))
        .order_by(PoolListing.updated_at.desc(), App.id).limit(100)).all()
    return [{"app_id": item.id, "name": item.name, "package_name": item.package_name,
             "workflow_steps": item.core_workflow_steps, "icon_url": item.icon_url,
             "owned": item.owner_id == actor.id,
             "joined": any(a.tester_id == actor.id for a in item.assignments),
             "available": item.id in eligible} for item in rows if ready(item)]


@router.get("/apps/{app_id}/supply")
def get_supply(app_id: str, actor: Actor, db: Database):
    return supply(db, owned(db, app_id, actor))


@router.post("/apps/{app_id}/pool-listing")
def set_listing(app_id: str, body: OptIn, actor: Actor, db: Database, now: Clock):
    lock_writes(db, actor)
    item = owned(db, app_id, actor)
    if body.enabled and not ready(item):
        raise HTTPException(409, "Confirm Google Group setup, Play test link and core steps first")
    listing = db.get(PoolListing, app_id)
    if listing is None:
        listing = PoolListing(app_id=app_id, updated_at=now)
        db.add(listing)
    listing.enabled, listing.updated_at = body.enabled, now
    db.flush()
    if body.enabled:
        place_in_group(db, item, now)
    db.commit()
    return supply(db, item)


@router.post("/apps/{app_id}/tester-pool/accept")
def accept_opportunity(app_id: str, actor: Actor, db: Database, now: Clock):
    return accept_app(app_id, actor, db, now)


def accept_app(app_id: str, actor: User, db: Session, now: datetime, *, max_apps: int = MAX_CONCURRENT_APPS, commit: bool = True):
    lock_writes(db, actor)
    item = db.get(App, app_id)
    listing = db.get(PoolListing, app_id)
    control = db.get(AdminAppControl, app_id)
    if (
        (control and (control.paused or control.kind == "SYNTHETIC"))
        or item is None
        or not listing
        or not listing.enabled
        or not ready(item)
        or not db.get(User, item.owner_id).is_active
    ):
        raise HTTPException(404, "Opportunity not available")
    if item.owner_id == actor.id:
        raise HTTPException(422, "You cannot accept your own app")
    pref = db.get(TesterPoolPreference, actor.id)
    # Clicking Join testing is explicit consent; no separate pool-enrollment step.
    if pref is None:
        pref = TesterPoolPreference(user_id=actor.id, enabled=True, consent_at=now, updated_at=now)
        db.add(pref)
    elif not pref.enabled:
        pref.enabled, pref.consent_at, pref.updated_at = True, now, now
    existing = db.scalar(
        select(TesterAssignment).where(
            TesterAssignment.app_id == app_id, TesterAssignment.tester_id == actor.id
        )
    )
    if existing:
        if existing.status == "DROPPED":
            raise HTTPException(409, "A previous assignment was dropped; contact the owner")
        return {"assignment_id": existing.id, "status": existing.status}
    if active_work(db, actor.id) >= max_apps:
        raise HTTPException(409, "Concurrent app limit reached")
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
        {"source": "VOLUNTARY_SHARED_POOL"},
    )
    if commit:
        db.commit()
    # This is task acceptance only. Existing Play opt-in and installation
    # confirmations remain separate, with no fabricated dates or headcount.
    return {"assignment_id": assignment.id, "status": assignment.status}


GROUP_CAPACITY = 13


def group_apps(db: Session, group_id: str):
    return db.scalars(select(App).join(AppGroupApp, AppGroupApp.app_id == App.id)
        .where(AppGroupApp.group_id == group_id).order_by(App.created_at, App.id)).all()


def place_in_group(db: Session, item: App, now: datetime):
    existing = db.get(AppGroupApp, item.id)
    if existing:
        return existing.group_id
    # Caller holds the writer lock. Never put two apps by one owner in a group.
    for group in db.scalars(select(AppGroup).order_by(AppGroup.created_at, AppGroup.id)):
        apps = group_apps(db, group.id)
        if len(apps) < GROUP_CAPACITY and all(app.owner_id != item.owner_id for app in apps):
            break
    else:
        from uuid import uuid4
        number = (db.scalar(select(func.count(AppGroup.id))) or 0) + 1
        group = AppGroup(id=str(uuid4()), name=f"App Group {number}", created_at=now)
        db.add(group)
        db.flush()
    db.add(AppGroupApp(app_id=item.id, group_id=group.id))
    db.flush()
    sync_group(db, group.id, now)
    return group.id


def visible_group_apps(db: Session, group_id: str):
    result = []
    for item in group_apps(db, group_id):
        listing = db.get(PoolListing, item.id)
        control = db.get(AdminAppControl, item.id)
        if listing and listing.enabled and ready(item) and db.get(User, item.owner_id).is_active and not (control and (control.paused or control.kind == "SYNTHETIC")):
            result.append(item)
    return result


def sync_group(db: Session, group_id: str, now: datetime):
    # Joining explicitly covers this group's present and future apps, up to 12 other owners.
    items = visible_group_apps(db, group_id)
    for member in db.scalars(select(AppGroupMember).where(AppGroupMember.group_id == group_id)):
        actor = db.get(User, member.user_id)
        if not actor or not actor.is_active:
            continue
        for item in items:
            if item.owner_id == actor.id:
                continue
            with db.begin_nested():
                try:
                    accept_app(item.id, actor, db, now, max_apps=12, commit=False)
                except HTTPException as error:
                    if error.status_code not in {404, 409}:
                        raise
                    # Existing outside work/capacity is never silently dropped.
                    continue


@router.get("/app-groups")
def list_app_groups(actor: Actor, db: Database):
    result = []
    for group in db.scalars(select(AppGroup).order_by(AppGroup.created_at, AppGroup.id)):
        apps = visible_group_apps(db, group.id)
        if not apps:
            continue
        own = any(app.owner_id == actor.id for app in apps)
        joined = db.get(AppGroupMember, (group.id, actor.id)) is not None
        result.append({"id": group.id, "name": group.name, "capacity": GROUP_CAPACITY,
            "status": "FORMING" if len(apps) < GROUP_CAPACITY else "FULL",
            "my_group": own, "joined": joined,
            "apps": [{"app_id": app.id, "name": app.name, "package_name": app.package_name,
                "icon_url": app.icon_url, "owned": app.owner_id == actor.id,
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
