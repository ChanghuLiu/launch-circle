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
from app.models.pool import PoolListing, TesterPoolPreference
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
    pref = db.get(TesterPoolPreference, actor.id)
    if pref is None or not pref.enabled or active_work(db, actor.id) >= MAX_CONCURRENT_APPS:
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
    db.commit()
    return supply(db, item)


@router.post("/apps/{app_id}/tester-pool/accept")
def accept_opportunity(app_id: str, actor: Actor, db: Database, now: Clock):
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
    if not pref or not pref.enabled:
        raise HTTPException(409, "Join the voluntary tester pool first")
    existing = db.scalar(
        select(TesterAssignment).where(
            TesterAssignment.app_id == app_id, TesterAssignment.tester_id == actor.id
        )
    )
    if existing:
        if existing.status == "DROPPED":
            raise HTTPException(409, "A previous assignment was dropped; contact the owner")
        return {"assignment_id": existing.id, "status": existing.status}
    if active_work(db, actor.id) >= MAX_CONCURRENT_APPS:
        raise HTTPException(409, "Two concurrent app limit reached")
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
    db.commit()
    # This is task acceptance only. Existing Play opt-in and installation
    # confirmations remain separate, with no fabricated dates or headcount.
    return {"assignment_id": assignment.id, "status": assignment.status}
