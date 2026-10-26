"""Private, cookie-authenticated operator console with audited dispatch controls."""
import hashlib
import secrets
import threading
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.pool import active_work, current_assignments, ready, supply
from app.core.config import get_settings
from app.core.database import get_db
from app.models.admin import AdminAppControl, AdminAudit, AdminRecommendation, AdminSession
from app.models.launch import App, Circle, CircleMember, Feedback, TesterAssignment
from app.models.pool import AppIntake, PoolListing, TesterPoolPreference
from app.models.user import User
from app.services.admin_auth import password_matches
from app.services.circles import active_member_count

router = APIRouter(prefix="/admin", tags=["operator"])
DB = Annotated[Session, Depends(get_db)]
ASSETS = Path(__file__).resolve().parent.parent / "static" / "admin"
COOKIE = "lc_operator"
_attempts = deque()
_attempt_lock = threading.Lock()


def now():
    return datetime.now(UTC)


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
    if not get_settings().admin_password_hash or not row or expiry <= now():
        raise HTTPException(401, "Operator login required")
    if request.method not in {"GET", "HEAD"}:
        guard_write(request)


Admin = Annotated[None, Depends(operator)]


def audit(db, action, target, detail):
    db.add(AdminAudit(created_at=now(), action=action, target_id=target, detail=detail))


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
    configured = get_settings().admin_password_hash
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
    db.add(AdminSession(token_hash=digest(raw), expires_at=now() + timedelta(hours=8)))
    audit(db, "LOGIN", "operator", {})
    db.commit()
    response.set_cookie(COOKIE, raw, max_age=8 * 3600, httponly=True,
                        secure=get_settings().is_deployment, samesite="strict", path="/admin")
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
                  "status": a.status, "group_configured": a.google_group_configured,
                  "opt_in_url": a.opt_in_url, "control": config(a), **supply(db, a)}
                 for a in apps[:500]],
        "assignments": [{"id": a.id, "app_id": a.app_id, "tester_id": a.tester_id,
                         "status": a.status, "health": a.health_status,
                         "opted_in_at": a.opted_in_at, "installed_at": a.installed_at,
                         "last_activity_at": a.last_activity_at, "completed_at": a.completed_at,
                         "completed_missions": sum(m.status == "COMPLETED" for m in a.missions),
                         "total_missions": len(a.missions), "source": "USER_REPORTED"}
                        for a in assignments[:2000]],
        "intakes": [{"id": i.id, "owner_id": i.owner_id, "name": i.name,
                     "package_name": i.package_name, "status": i.status,
                     "submitted_at": i.submitted_at} for i in intakes],
        "recommendations": [{"app_id": r.app_id, "tester_id": r.tester_id,
                             "created_at": r.created_at}
                            for r in db.scalars(select(AdminRecommendation).limit(2000))],
        "google_eligibility_confirmed": False,
    }


class Control(BaseModel):
    kind: Literal["UNCLASSIFIED", "CUSTOMER", "OWN", "SYNTHETIC"]
    priority: int = Field(ge=0, le=100)
    paused: bool
    note: str = Field(default="", max_length=500)


@router.post("/api/apps/{app_id}/control")
def control(app_id: str, body: Control, db: DB, admin: Admin):
    if not db.get(App, app_id):
        raise HTTPException(404, "App not found")
    row = db.get(AdminAppControl, app_id)
    before = {k: getattr(row, k) for k in Control.model_fields} if row else {}
    if not row:
        row = AdminAppControl(app_id=app_id)
        db.add(row)
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    audit(db, "APP_CONTROL", app_id, {"before": before, "after": body.model_dump()})
    db.commit()
    return {"ok": True}


class Recommend(BaseModel):
    tester_id: str = Field(min_length=1, max_length=36)
    enabled: bool = True


@router.post("/api/apps/{app_id}/recommend")
def recommend(app_id: str, body: Recommend, db: DB, admin: Admin):
    item, user = db.get(App, app_id), db.get(User, body.tester_id)
    if not item or not user:
        raise HTTPException(404, "App or tester not found")
    key = {"app_id": app_id, "tester_id": user.id}
    row = db.get(AdminRecommendation, key)
    if body.enabled:
        pref, listing = db.get(TesterPoolPreference, user.id), db.get(PoolListing, app_id)
        cfg = db.get(AdminAppControl, app_id)
        if (not user.is_active or item.owner_id == user.id or not pref or not pref.enabled
                or not db.get(User, item.owner_id).is_active or not listing or not listing.enabled
                or not ready(item) or (cfg and (cfg.paused or cfg.kind == "SYNTHETIC"))
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
          {"tester_id": user.id})
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
