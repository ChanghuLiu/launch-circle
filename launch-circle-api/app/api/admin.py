"""Private, cookie-authenticated operator console with audited dispatch controls."""
import csv
import hashlib
import io
import secrets
import threading
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.api.pool import active_work, current_assignments, ready, supply
from app.core.config import get_settings
from app.core.database import get_db
from app.models.activity import UserActivityEvent
from app.models.admin import (
    AdminAppControl,
    AdminAudit,
    AdminCredential,
    AdminRecommendation,
    AdminSession,
)
from app.models.device import Device
from app.models.launch import (
    App,
    BackendEvent,
    Circle,
    CircleMember,
    Feedback,
    PilotEvent,
    TesterAssignment,
    TestMission,
)
from app.models.pool import (
    AppGroup,
    AppGroupApp,
    AppGroupMember,
    AppGroupTaskQueue,
    AppIntake,
    PoolListing,
    TesterPoolPreference,
)
from app.models.user import User
from app.schemas.phase0 import AppUpdate
from app.services.admin_auth import password_hash, password_matches
from app.services.apps import apply_app_update
from app.services.circles import active_member_count
from app.services.dispatch_authorization import app_group_is_closed

router = APIRouter(prefix="/admin", tags=["operator"])
DB = Annotated[Session, Depends(get_db)]
ASSETS = Path(__file__).resolve().parent.parent / "static" / "admin"
COOKIE = "lc_operator"
ADMIN_SESSION_TTL = timedelta(hours=8)
_attempts = deque()
_attempt_lock = threading.Lock()


def now():
    return datetime.now(UTC)


def configured_password(db):
    credential = db.get(AdminCredential, "operator")
    return credential.password_hash if credential else get_settings().admin_password_hash


def digest(value):
    return hashlib.sha256((value + get_settings().admin_password_hash).encode()).hexdigest()


def guard_write(request: Request):
    if request.headers.get("X-Admin-Action") != "1":
        raise HTTPException(403, "Missing same-origin action header")
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Cross-origin action denied")


def operator(request: Request, db: DB):
    raw = request.cookies.get(COOKIE, "")
    row = db.get(AdminSession, digest(raw)) if raw else None
    expiry = row.expires_at.replace(tzinfo=UTC) if row else None
    if not configured_password(db) or not row or expiry <= now():
        raise HTTPException(401, "Operator login required")
    request.state.admin_authenticated = True
    if request.method not in {"GET", "HEAD"}:
        guard_write(request)


Admin = Annotated[None, Depends(operator)]


def audit(db, action, target, detail, *, reason=None, request_id=None):
    record = {"actor": "operator", "result": "SUCCESS", **detail}
    if reason is not None:
        record["reason"] = reason
    if request_id:
        record["request_id"] = request_id
    db.add(AdminAudit(created_at=now(), action=action, target_id=target, detail=record))


@router.get("/password", include_in_schema=False)
@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
def page():
    return FileResponse(ASSETS / "index.html", media_type="text/html")


@router.get("/assets/{name}", include_in_schema=False)
def asset(name: Literal["admin.js", "admin.css"]):
    return FileResponse(ASSETS / name)


class Login(BaseModel):
    password: str = Field(min_length=1, max_length=256)


@router.post("/api/login")
def login(body: Login, request: Request, response: Response, db: DB):
    guard_write(request)
    configured = configured_password(db)
    if not configured:
        raise HTTPException(503, "Operator login is not configured")
    with _attempt_lock:
        stamp = time.monotonic()
        while _attempts and stamp - _attempts[0] > 60:
            _attempts.popleft()
        if len(_attempts) >= 10:
            raise HTTPException(429, "Wait one minute before trying again")
        _attempts.append(stamp)
    if not password_matches(body.password, configured):
        raise HTTPException(401, "Incorrect operator password")
    raw = secrets.token_urlsafe(48)
    db.execute(delete(AdminSession).where(AdminSession.expires_at <= now()))
    db.add(AdminSession(token_hash=digest(raw), expires_at=now() + ADMIN_SESSION_TTL))
    audit(db, "LOGIN", "operator", {})
    db.commit()
    response.set_cookie(COOKIE, raw, max_age=int(ADMIN_SESSION_TTL.total_seconds()),
                        httponly=True, secure=get_settings().is_deployment,
                        samesite="strict", path="/admin")
    return {"ok": True}


class ChangePassword(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


@router.post("/api/password")
def change_password(body: ChangePassword, request: Request, response: Response, db: DB, admin: Admin):
    with _attempt_lock:
        stamp = time.monotonic()
        while _attempts and stamp - _attempts[0] > 60:
            _attempts.popleft()
        if len(_attempts) >= 10:
            raise HTTPException(429, "请稍等一分钟再试")
        _attempts.append(stamp)
    if not password_matches(body.current_password, configured_password(db)):
        raise HTTPException(400, "当前密码不正确")
    if body.current_password == body.new_password:
        raise HTTPException(400, "新密码不能与当前密码相同")
    credential = db.get(AdminCredential, "operator")
    encoded = password_hash(body.new_password)
    if credential:
        credential.password_hash = encoded
    else:
        db.add(AdminCredential(id="operator", password_hash=encoded))
    db.execute(delete(AdminSession))
    audit(db, "PASSWORD_CHANGED", "operator", {})
    db.commit()
    response.delete_cookie(COOKIE, path="/admin")
    return {"ok": True}


@router.post("/api/logout")
def logout(request: Request, response: Response, db: DB, admin: Admin):
    db.execute(delete(AdminSession).where(AdminSession.token_hash == digest(request.cookies[COOKIE])))
    audit(db, "LOGOUT", "operator", {})
    db.commit()
    response.delete_cookie(COOKIE, path="/admin")
    return {"ok": True}


@router.get("/api/overview")
def overview(db: DB, admin: Admin):
    users = db.scalars(select(User).order_by(User.created_at.desc()).limit(501)).all()
    apps = db.scalars(select(App).order_by(App.created_at.desc()).limit(501)).all()
    assignments = db.scalars(select(TesterAssignment).order_by(
        TesterAssignment.assigned_at.desc()).limit(2001)).all()
    controls = {c.app_id: c for c in db.scalars(select(AdminAppControl))}
    prefs = {p.user_id: p.enabled for p in db.scalars(select(TesterPoolPreference))}
    intakes = db.scalars(select(AppIntake).order_by(AppIntake.submitted_at.desc()).limit(200)).all()
    groups = db.scalars(select(AppGroup).order_by(AppGroup.created_at, AppGroup.id)).all()
    def config(a):
        c = controls.get(a.id)
        return {"kind": c.kind if c else "UNCLASSIFIED", "priority": c.priority if c else 50,
                "paused": bool(c and c.paused), "note": c.note if c else ""}
    return {
        "truncated": len(users) > 500 or len(apps) > 500 or len(assignments) > 2000,
        "customer_count": len({a.owner_id for a in apps[:500]
                               if config(a)["kind"] == "CUSTOMER"}),
        "users": [{"id": u.id, "name": u.display_name or u.email, "email": u.email,
                   "active": u.is_active, "pool_enabled": prefs.get(u.id, False),
                   "active_apps": active_work(db, u.id), "last_test_at": u.last_successful_test_at,
                   "created_at": u.created_at} for u in users[:500]],
        "apps": [{"id": a.id, "owner_id": a.owner_id, "package_name": a.package_name,
                  "status": a.status, "no_test_required": a.no_test_required,
                  "group_configured": a.google_group_configured,
                  "opt_in_url": a.opt_in_url, "control": config(a), **supply(db, a)}
                 for a in apps[:500]],
        "assignments": [{"id": a.id, "app_id": a.app_id, "tester_id": a.tester_id,
                         "status": a.status, "health": a.health_status,
                         "opted_in_at": a.opted_in_at, "installed_at": a.installed_at,
                         "last_activity_at": a.last_activity_at, "completed_at": a.completed_at,
                         "completed_missions": sum(m.status == "COMPLETED" for m in a.missions),
                         "waived_missions": sum(m.waived_at is not None for m in a.missions),
                         "total_missions": len(a.missions), "source": "USER_REPORTED"}
                        for a in assignments[:2000]],
        "intakes": [{"id": i.id, "owner_id": i.owner_id, "name": i.name,
                     "package_name": i.package_name, "status": i.status,
                     "submitted_at": i.submitted_at} for i in intakes],
        "app_groups": [{
            "id": group.id,
            "name": group.name,
            "status": group.status,
            "app_count": db.scalar(select(func.count(AppGroupApp.app_id)).where(AppGroupApp.group_id == group.id)) or 0,
            "member_count": db.scalar(select(func.count(AppGroupMember.user_id)).join(User, User.id == AppGroupMember.user_id).where(AppGroupMember.group_id == group.id, User.is_active.is_(True))) or 0,
        } for group in groups],
        "recommendations": [{"app_id": r.app_id, "tester_id": r.tester_id,
                             "created_at": r.created_at}
                            for r in db.scalars(select(AdminRecommendation).limit(2000))],
        "google_eligibility_confirmed": False,
    }


def _user_summary(user: User, db):
    pref = db.get(TesterPoolPreference, user.id)
    return {"id": user.id, "name": user.display_name or user.email, "email": user.email,
            "active": user.is_active, "created_at": user.created_at,
            "active_apps": active_work(db, user.id),
            "pool_enabled": bool(pref and pref.enabled)}


@router.get("/api/users")
def search_users(
    request: Request,
    db: DB,
    admin: Admin,
    query: str = Query(default="", min_length=0, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
):
    value = query.strip()
    stmt = select(User).order_by(User.created_at.desc())
    if value:
        term = f"%{value}%"
        stmt = stmt.where(or_(User.email.ilike(term), User.login_email.ilike(term),
                              User.display_name.ilike(term), User.id == value))
    count = len(db.scalars(stmt.limit(10001)).all())
    rows = list(db.scalars(stmt.offset(offset).limit(limit)))
    audit(db, "USER_SEARCH", "user-search", {
        "query_present": bool(value), "result_count": len(rows), "offset": offset,
        "limit": limit, "more_results": (count is not None and offset + len(rows) < count),
    }, request_id=getattr(request.state, "request_id", None))
    db.commit()
    return {"users": [_user_summary(user, db) for user in rows],
            "offset": offset, "limit": limit,
            "has_more": offset + len(rows) < count}


def _audit_timeline_record(row: AdminAudit):
    detail = row.detail if isinstance(row.detail, dict) else {}
    item = {"at": row.created_at, "event_name": row.action.lower(),
            "workflow": "operator", "object_type": "operator_action",
            "object_id": row.target_id, "outcome": detail.get("result", "SUCCESS"),
            "request_id": detail.get("request_id"), "summary": "Operator support action or query."}
    if detail.get("reason"):
        item["summary"] = "Operator action: " + str(detail["reason"])[:200]
    if row.action in {"APP_UPDATE", "RECRUITMENT_CHANGED", "APP_CONTROL", "TASKS_WAIVED_NO_TEST", "RECOMMEND", "CANCEL_RECOMMENDATION"}:
        item["summary"] = f"Operator changed {row.action.lower().replace('_', ' ')}."
        item["reason"] = str(detail.get("reason") or "")[:200]
        item["before"] = detail.get("before")
        item["after"] = detail.get("after")
    return item


@router.get("/api/users/{user_id}")
def user_detail(user_id: str, request: Request, db: DB, admin: Admin):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    owned_apps = list(db.scalars(select(App).where(App.owner_id == user.id).order_by(App.created_at.desc())))
    app_ids = [app.id for app in owned_apps]
    preference = db.get(TesterPoolPreference, user.id)
    circle_memberships = list(db.scalars(select(CircleMember).where(CircleMember.user_id == user.id)))
    circle_rows = []
    for member in circle_memberships:
        circle = db.get(Circle, member.circle_id)
        if circle:
            circle_rows.append({"circle_id": circle.id, "name": circle.name,
                                "owner_id": circle.owner_id, "role": member.role,
                                "status": member.status, "joined_at": member.joined_at,
                                "left_at": member.left_at,
                                "active_members": active_member_count(db, circle.id),
                                "max_members": circle.max_members})
    group_ids = set(db.scalars(select(AppGroupMember.group_id).where(AppGroupMember.user_id == user.id)))
    if app_ids:
        group_ids.update(db.scalars(select(AppGroupApp.group_id).where(AppGroupApp.app_id.in_(app_ids))))
    groups = []
    for group_id in sorted(group_ids):
        group = db.get(AppGroup, group_id)
        if not group:
            continue
        memberships = list(db.scalars(select(AppGroupApp).where(AppGroupApp.group_id == group_id)))
        group_apps = [db.get(App, row.app_id) for row in memberships]
        groups.append({"group_id": group.id, "name": group.name,
                       "joined": db.get(AppGroupMember, (group.id, user.id)) is not None,
                       "created_at": group.created_at,
                       "apps": [{"app_id": app.id, "name": app.name,
                                 "package_name": app.package_name} for app in group_apps if app]})
    query = select(TesterAssignment).where(
        or_(TesterAssignment.tester_id == user.id,
            TesterAssignment.app_id.in_(app_ids) if app_ids else False)
    ).order_by(TesterAssignment.assigned_at.desc()).limit(1000)
    assignments = list(db.scalars(query))
    assignment_rows = []
    assignment_ids = [assignment.id for assignment in assignments]
    for assignment in assignments:
        app = db.get(App, assignment.app_id)
        tester = db.get(User, assignment.tester_id)
        missions = list(db.scalars(select(TestMission).where(TestMission.assignment_id == assignment.id)))
        assignment_rows.append({
            "assignment_id": assignment.id, "app_id": assignment.app_id,
            "app_name": app.name if app else "Unknown app",
            "tester_id": assignment.tester_id,
            "tester_name": (tester.display_name or tester.email) if tester else "Deleted user",
            "is_selected_user_tester": assignment.tester_id == user.id,
            "status": assignment.status, "health": assignment.health_status,
            "assigned_at": assignment.assigned_at,
            "opted_in_at": assignment.opted_in_at, "installed_at": assignment.installed_at,
            "completed_at": assignment.completed_at, "dropped_at": assignment.dropped_at,
            "last_activity_at": assignment.last_activity_at,
            "play_account_email": assignment.play_account_email if assignment.tester_id == user.id else None,
            "missions": [{"mission_id": mission.id, "type": mission.mission_type,
                          "day": mission.scheduled_day, "status": mission.status,
                          "completed_at": mission.completed_at, "waived_at": mission.waived_at}
                         for mission in missions],
        })
    historical = list(db.scalars(select(PilotEvent).where(PilotEvent.actor_user_id == user.id)
                                  .order_by(PilotEvent.created_at.desc()).limit(250)))
    app_activity = list(db.scalars(select(UserActivityEvent).where(UserActivityEvent.user_id == user.id)
                                   .order_by(UserActivityEvent.occurred_at.desc()).limit(500)))
    object_targets = {user.id, *app_ids, *assignment_ids}
    audit_target_filters = [AdminAudit.target_id.in_(object_targets)]
    for linked_app_id in app_ids:
        audit_target_filters.extend([
            AdminAudit.target_id == f"{linked_app_id}",
            AdminAudit.target_id.like(f"{linked_app_id},%"),
            AdminAudit.target_id.like(f"%,{linked_app_id},%"),
            AdminAudit.target_id.like(f"%,{linked_app_id}"),
        ])
    admin_records = list(db.scalars(select(AdminAudit).where(or_(*audit_target_filters))
                                    .order_by(AdminAudit.created_at.desc()).limit(250))) if object_targets else []
    timeline = [
        {"at": row.occurred_at, "event_name": row.event_name, "workflow": row.workflow,
         "object_type": row.object_type, "object_id": row.object_id, "outcome": row.outcome,
         "error_code": row.error_code, "summary": row.support_summary,
         "request_id": row.request_id, "client_version": row.client_version,
         "platform": row.platform, "device_type": row.device_type}
        for row in app_activity
    ]
    timeline += [
        {"at": row.created_at, "event_name": row.event_type.lower(), "workflow": "legacy_event",
         "object_type": "app" if row.app_id else "assignment" if row.assignment_id else "invite",
         "object_id": row.app_id or row.assignment_id or row.invite_id,
         "outcome": "SUCCESS", "summary": "Historical product event (legacy record)."}
        for row in historical
    ]
    timeline += [_audit_timeline_record(row) for row in admin_records]
    timeline.sort(key=lambda row: row["at"], reverse=True)
    audit(db, "USER_DETAIL_VIEW", user.id, {"linked_apps": len(app_ids),
          "linked_assignments": len(assignments)}, request_id=getattr(request.state, "request_id", None))
    db.commit()
    return {
        "user": {"id": user.id, "display_name": user.display_name, "email": user.email,
                 "login_email": user.login_email, "active": user.is_active,
                 "created_at": user.created_at, "updated_at": user.updated_at,
                 "country": user.country, "languages": [x for x in user.languages_csv.split(",") if x],
                 "tester_email": user.tester_email,
                 "tester_email_sharing_consent": user.tester_email_sharing_consent,
                 "tester_email_sharing_consent_at": user.tester_email_sharing_consent_at,
                 "tester_group_status": user.tester_group_status,
                 "tester_group_play_email": user.tester_group_play_email,
                 "tester_group_confirmed_at": user.tester_group_confirmed_at,
                 "reliability_score": user.reliability_score},
        "devices": [{"manufacturer": device.manufacturer, "model": device.model,
                     "android_api": device.android_api,
                     "capabilities": [x for x in device.capabilities_csv.split(",") if x],
                     "last_seen_at": device.last_seen_at}
                    for device in db.scalars(select(Device).where(Device.user_id == user.id))],
        "consents": {"tester_email_sharing": {"enabled": user.tester_email_sharing_consent,
                         "at": user.tester_email_sharing_consent_at},
                     "tester_group": {"status": user.tester_group_status,
                         "play_email": user.tester_group_play_email,
                         "confirmed_at": user.tester_group_confirmed_at,
                         "meaning": "User-reported; not Google eligibility verification."},
                     "tester_pool": {"enabled": bool(preference and preference.enabled),
                         "consent_at": preference.consent_at if preference else None,
                         "updated_at": preference.updated_at if preference else None},
                     "circles": circle_rows,
                     "app_groups": [{"group_id": group["group_id"], "joined": group["joined"]} for group in groups]},
        "apps": [{"id": app.id, "name": app.name, "package_name": app.package_name,
                  "opt_in_url": app.opt_in_url, "status": app.status,
                  "tester_target": app.tester_target, "no_test_required": app.no_test_required,
                  "google_group_configured": app.google_group_configured,
                  "google_group_confirmed_at": app.google_group_confirmed_at,
                  "entitlement_status": app.entitlement_status, "created_at": app.created_at,
                  "updated_at": app.updated_at} for app in owned_apps],
        "circles": circle_rows, "app_groups": groups, "assignments": assignment_rows,
        "activity": timeline[:500], "activity_truncated": len(timeline) > 500,
    }


def _activity_query(user_id, start_at, end_at, event_name, outcome, request_id):
    stmt = select(UserActivityEvent)
    if user_id:
        stmt = stmt.where(UserActivityEvent.user_id == user_id)
    if start_at:
        stmt = stmt.where(UserActivityEvent.occurred_at >= start_at)
    if end_at:
        stmt = stmt.where(UserActivityEvent.occurred_at <= end_at)
    if event_name:
        stmt = stmt.where(UserActivityEvent.event_name == event_name)
    if outcome:
        stmt = stmt.where(UserActivityEvent.outcome == outcome)
    if request_id:
        stmt = stmt.where(UserActivityEvent.request_id == request_id)
    return stmt


def _activity_read(row):
    return {"id": row.id, "at": row.occurred_at, "user_id": row.user_id,
            "event_name": row.event_name, "workflow": row.workflow,
            "object_type": row.object_type, "object_id": row.object_id,
            "outcome": row.outcome, "error_code": row.error_code,
            "summary": row.support_summary, "request_id": row.request_id,
            "client_version": row.client_version, "platform": row.platform,
            "device_type": row.device_type, "method": row.method,
            "route": row.route_template, "status_code": row.status_code}


@router.get("/api/activity")
def search_activity(
    request: Request, db: DB, admin: Admin,
    user_id: str | None = None, start_at: datetime | None = None,
    end_at: datetime | None = None, event_name: str | None = Query(default=None, max_length=80),
    outcome: str | None = Query(default=None, pattern="^(SUCCESS|FAILURE)$"),
    request_id: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0, le=10000),
):
    if start_at and end_at and start_at > end_at:
        raise HTTPException(422, "start_at must be before end_at")
    rows = list(db.scalars(_activity_query(user_id, start_at, end_at, event_name, outcome, request_id)
                           .order_by(UserActivityEvent.occurred_at.desc()).offset(offset).limit(limit)))
    filters = {"user_id": user_id, "start_at": start_at.isoformat() if start_at else None,
               "end_at": end_at.isoformat() if end_at else None, "event_name": event_name,
               "outcome": outcome, "request_id": request_id, "limit": limit, "offset": offset}
    audit(db, "ACTIVITY_QUERY", "activity-search", {"filters": filters,
          "result_count": len(rows)}, request_id=getattr(request.state, "request_id", None))
    db.commit()
    return {"events": [_activity_read(row) for row in rows], "limit": limit,
            "offset": offset, "has_more": len(rows) == limit}


@router.get("/api/activity/export.csv")
def export_activity(
    request: Request, db: DB, admin: Admin,
    user_id: str | None = None, start_at: datetime | None = None,
    end_at: datetime | None = None, event_name: str | None = Query(default=None, max_length=80),
    outcome: str | None = Query(default=None, pattern="^(SUCCESS|FAILURE)$"),
    request_id: str | None = Query(default=None, max_length=80),
):
    if start_at and end_at and start_at > end_at:
        raise HTTPException(422, "start_at must be before end_at")
    stmt = _activity_query(user_id, start_at, end_at, event_name, outcome, request_id)
    rows = list(db.scalars(stmt.order_by(UserActivityEvent.occurred_at.desc()).limit(10000)))
    audit(db, "ACTIVITY_EXPORT", "activity-export", {"result_count": len(rows),
          "filters": {"user_id": user_id, "start_at": start_at.isoformat() if start_at else None,
                      "end_at": end_at.isoformat() if end_at else None,
                      "event_name": event_name, "outcome": outcome, "request_id": request_id}},
          request_id=getattr(request.state, "request_id", None))
    db.commit()
    output = io.StringIO()
    columns = ["at", "user_id", "event_name", "workflow", "object_type", "object_id",
               "outcome", "error_code", "summary", "request_id", "client_version",
               "platform", "device_type", "method", "route", "status_code"]
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: (value.isoformat() if hasattr(value, "isoformat") else value)
                         for key, value in _activity_read(row).items() if key != "id"})
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": "attachment; filename=launch-circle-activity.csv"})


class AdminAppUpdate(BaseModel):
    changes: AppUpdate
    reason: str = Field(min_length=8, max_length=500)


def _app_audit_state(values):
    """Keep free text and full Play links out of durable operator logs."""
    result = {}
    for key, value in values.items():
        if key == "opt_in_url":
            raw = str(value or "")
            result[key] = {"host": "play.google.com" if "play.google.com" in raw.lower() else "other",
                           "sha256": hashlib.sha256(raw.encode()).hexdigest() if raw else None}
        elif key == "core_workflow_steps":
            raw = "\n".join(value or [])
            result[key] = {"count": len(value or []),
                           "sha256": hashlib.sha256(raw.encode()).hexdigest() if raw else None}
        elif key == "name":
            result[key] = str(value)[:120]
        else:
            result[key] = value
    return result


@router.patch("/api/users/{user_id}/apps/{app_id}")
def support_update_app(user_id: str, app_id: str, body: AdminAppUpdate,
                       request: Request, db: DB, admin: Admin):
    app = db.get(App, app_id)
    if app is None or app.owner_id != user_id:
        raise HTTPException(404, "App not found for this user")
    if not db.get(User, user_id):
        raise HTTPException(404, "User not found")
    before = {"name": app.name, "core_workflow_steps": app.core_workflow_steps,
              "opt_in_url": app.opt_in_url, "tester_target": app.tester_target}
    values = body.changes.model_dump(exclude_unset=True)
    if not values:
        raise HTTPException(422, "Provide at least one App field to change")
    apply_app_update(app, body.changes)
    after = {key: getattr(app, key) for key in before}
    after["opt_in_url"] = str(after["opt_in_url"])
    audit(db, "APP_UPDATE", app_id, {"target_user_id": user_id,
          "before": _app_audit_state(before), "after": _app_audit_state(after)},
          reason=body.reason, request_id=getattr(request.state, "request_id", None))
    db.commit()
    return {"ok": True, "app_id": app_id, "owner_id": user_id,
            "before": before, "after": after}


class Control(BaseModel):
    kind: Literal["UNCLASSIFIED", "CUSTOMER", "OWN", "SYNTHETIC"]
    priority: int = Field(ge=0, le=100)
    paused: bool
    note: str = Field(default="", max_length=500)
    reason: str = Field(min_length=8, max_length=500)


class WaiveTasks(BaseModel):
    app_ids: list[str] = Field(min_length=1, max_length=12)
    reason: str = Field(min_length=8, max_length=500)


@router.post("/api/tasks/waive")
def waive_tasks(body: WaiveTasks, db: DB, admin: Admin, request: Request = None):
    app_ids = list(dict.fromkeys(body.app_ids))
    if len(app_ids) != len(body.app_ids):
        raise HTTPException(422, "Remove duplicate apps from the selection")
    apps = db.scalars(select(App).where(App.id.in_(app_ids))).all()
    if len(apps) != len(app_ids):
        raise HTTPException(404, "One or more selected apps were not found")
    controls = {c.app_id: c for c in db.scalars(
        select(AdminAppControl).where(AdminAppControl.app_id.in_(app_ids))
    )}
    blocked = [a.name for a in apps if controls.get(a.id) and controls[a.id].kind in {"CUSTOMER", "SYNTHETIC"}]
    if blocked:
        raise HTTPException(409, "Customer or simulated apps cannot use this action: " + ", ".join(blocked))

    stamp = now()
    changed_assignments = 0
    changed_missions = 0
    before_states = []
    after_states = []
    for item in apps:
        before_states.append({"app_id": item.id, "no_test_required": item.no_test_required,
                              "status": item.status})
        item.no_test_required = True
        assignments = db.scalars(select(TesterAssignment).where(
            TesterAssignment.app_id == item.id,
        )).all()
        for assignment in assignments:
            open_missions = [m for m in assignment.missions if m.status in {"PENDING", "AVAILABLE"}]
            assignment_closed = False
            for mission in open_missions:
                mission.status = "MISSED"
                mission.waived_at = stamp
                mission.waiver_reason = "NO_TEST_REQUIRED"
                changed_missions += 1
            if open_missions or assignment.status not in {"COMPLETED", "DROPPED"}:
                assignment.waived_at = stamp
                assignment.waiver_reason = "NO_TEST_REQUIRED"
                if assignment.status != "COMPLETED":
                    if assignment.status != "DROPPED":
                        assignment.status = "DROPPED"
                        assignment.health_status = "DROPPED"
                        assignment.dropped_at = stamp
                        assignment_closed = True
                    assignment.last_activity_at = stamp
                changed_assignments += 1
                db.add(BackendEvent(
                    app_id=item.id,
                    assignment_id=assignment.id,
                    event_type="TASKS_WAIVED",
                    dedupe_key=f"admin-waive:{assignment.id}:{stamp.isoformat()}",
                    payload_json='{"reason":"NO_TEST_REQUIRED","test_performed":false}',
                    created_at=stamp,
                ))
            if open_missions or assignment.status in {"DROPPED", "COMPLETED"}:
                after_states.append({"app_id": item.id, "assignment_id": assignment.id,
                                     "status": assignment.status,
                                     "open_missions_waived": len(open_missions),
                                     "assignment_closed": assignment_closed})
    detail = {
        "app_ids": app_ids,
        "app_count": len(apps),
        "before": before_states,
        "after": [{"app_id": item.id, "no_test_required": True, "status": item.status}
                  for item in apps] + after_states,
        "assignments_closed": changed_assignments,
        "missions_waived": changed_missions,
        "reason": body.reason,
        "test_performed": False,
        "google_play_data_sent": False,
    }
    audit(db, "TASKS_WAIVED_NO_TEST", ",".join(app_ids), detail,
          reason=body.reason, request_id=getattr(getattr(request, "state", None), "request_id", None))
    db.commit()
    return {"ok": True, **detail}


@router.post("/api/apps/{app_id}/control")
def control(app_id: str, body: Control, db: DB, admin: Admin, request: Request = None):
    if not db.get(App, app_id):
        raise HTTPException(404, "App not found")
    row = db.get(AdminAppControl, app_id)
    mutable = body.model_dump(exclude={"reason"})
    before = {k: getattr(row, k) for k in mutable} if row else {}
    if not row:
        row = AdminAppControl(app_id=app_id)
        db.add(row)
    for k, v in mutable.items():
        setattr(row, k, v)
    audit(db, "APP_CONTROL", app_id, {"before": before, "after": mutable},
          reason=body.reason, request_id=getattr(getattr(request, "state", None), "request_id", None))
    db.commit()
    return {"ok": True}


class RecruitmentUpdate(BaseModel):
    enabled: bool
    reason: str = Field(min_length=8, max_length=500)


@router.post("/api/apps/{app_id}/recruitment")
def recruitment(app_id: str, body: RecruitmentUpdate, db: DB, admin: Admin, request: Request = None):
    item = db.get(App, app_id)
    if item is None:
        raise HTTPException(404, "App not found")
    control = db.get(AdminAppControl, app_id)
    if body.enabled and (not ready(item) or not db.get(User, item.owner_id).is_active
            or (control and (control.paused or control.kind == "SYNTHETIC"))):
        raise HTTPException(409, "Complete app setup and remove administrative pause before recruitment")
    listing = db.get(PoolListing, app_id)
    before_enabled = bool(listing and listing.enabled)
    if listing is None:
        listing = PoolListing(app_id=app_id)
        db.add(listing)
    listing.enabled, listing.updated_at = body.enabled, now()
    audit(db, "RECRUITMENT_CHANGED", app_id, {"before": {"enabled": before_enabled},
          "after": {"enabled": body.enabled}}, reason=body.reason,
          request_id=getattr(getattr(request, "state", None), "request_id", None))
    db.commit()
    group_id = db.scalar(select(AppGroupApp.group_id).where(AppGroupApp.app_id == app_id))
    if body.enabled and group_id:
        from app.api.pool import sync_group

        sync_group(db, group_id, now())
        db.commit()
    return {"ok": True, "enabled": body.enabled}


class AppGroupStatusUpdate(BaseModel):
    status: Literal["OPEN", "CLOSED"]
    reason: str = Field(min_length=8, max_length=500)


@router.post("/api/app-groups/{group_id}/status")
def update_app_group_status(group_id: str, body: AppGroupStatusUpdate, db: DB, admin: Admin, request: Request = None):
    group = db.get(AppGroup, group_id)
    if group is None:
        raise HTTPException(404, "App Group not found")
    before = {"status": group.status}
    group.status = body.status
    if body.status == "CLOSED":
        db.execute(update(AppGroupTaskQueue).where(
            AppGroupTaskQueue.group_id == group_id,
            AppGroupTaskQueue.status == "PENDING",
        ).values(status="CANCELLED"))
    audit(db, "APP_GROUP_STATUS_CHANGED", group_id,
          {"before": before, "after": {"status": group.status}},
          reason=body.reason,
          request_id=getattr(getattr(request, "state", None), "request_id", None))
    db.commit()
    if body.status == "OPEN":
        from app.api.pool import sync_group

        sync_group(db, group_id, now())
        db.commit()
    return {"ok": True, "group_id": group.id, "status": group.status}


class Recommend(BaseModel):
    tester_id: str = Field(min_length=1, max_length=36)
    enabled: bool = True
    reason: str = Field(min_length=8, max_length=500)


@router.post("/api/apps/{app_id}/recommend")
def recommend(app_id: str, body: Recommend, db: DB, admin: Admin, request: Request = None):
    item, user = db.get(App, app_id), db.get(User, body.tester_id)
    if not item or not user:
        raise HTTPException(404, "App or tester not found")
    if body.enabled and app_group_is_closed(db, item.id):
        raise HTTPException(409, "APP_GROUP_CLOSED")
    key = {"app_id": app_id, "tester_id": user.id}
    row = db.get(AdminRecommendation, key)
    if body.enabled:
        pref, listing = db.get(TesterPoolPreference, user.id), db.get(PoolListing, app_id)
        cfg = db.get(AdminAppControl, app_id)
        if (not user.is_active or item.owner_id == user.id or not pref or not pref.enabled
                or not db.get(User, item.owner_id).is_active or not listing or not listing.enabled
                or item.no_test_required or not ready(item) or (cfg and (cfg.paused or cfg.kind == "SYNTHETIC"))
                or active_work(db, user.id) >= 2
                or len(current_assignments(item)) >= min(item.tester_target, 14)
                or any(a.tester_id == user.id for a in item.assignments)):
            raise HTTPException(409, "Requires owner-enabled recruitment, a ready app and an available consenting tester")
        circle = db.get(Circle, item.circle_id) if item.circle_id else None
        member = db.scalar(select(CircleMember).where(
            CircleMember.circle_id == item.circle_id, CircleMember.user_id == user.id
        ))
        if not circle or ((not member or member.status != "ACTIVE") and
                          active_member_count(db, circle.id) >= min(circle.max_members, 15)):
            raise HTTPException(409, "Circle is full or unavailable")
        if not row:
            db.add(AdminRecommendation(**key, created_at=now()))
    elif row:
        db.delete(row)
    audit(db, "RECOMMEND" if body.enabled else "CANCEL_RECOMMENDATION", app_id,
          {"tester_id": user.id, "before": {"recommended": row is not None},
           "after": {"recommended": body.enabled}}, reason=body.reason,
          request_id=getattr(getattr(request, "state", None), "request_id", None))
    db.commit()
    return {"ok": True, "assignment_created": False, "requires_tester_acceptance": True}


@router.get("/api/apps/{app_id}/feedback")
def feedback(app_id: str, db: DB, admin: Admin):
    if not db.get(App, app_id):
        raise HTTPException(404, "App not found")
    return [{"tester_id": f.tester_id, "at": f.created_at, "launch_ok": f.launch_ok,
             "core_feature_ok": f.core_feature_ok, "result": f.completion_result,
             "minutes": f.time_spent_minutes, "issue": (f.issue_text or "")[:2000],
             "suggestion": (f.suggestion_text or "")[:2000]}
            for f in db.scalars(select(Feedback).where(Feedback.app_id == app_id)
                                .order_by(Feedback.created_at.desc()).limit(200))]


@router.get("/api/audit")
def history(db: DB, admin: Admin):
    return [{"at": r.created_at, "action": r.action, "target": r.target_id, "detail": r.detail}
            for r in db.scalars(select(AdminAudit).order_by(AdminAudit.created_at.desc()).limit(100))]
