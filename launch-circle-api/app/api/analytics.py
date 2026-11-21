from datetime import datetime, timedelta, timezone
from html import escape
import json
import secrets
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.launch import PilotEvent
from app.models.user import User

router = APIRouter()
basic_auth = HTTPBasic()


class AnalyticsEventRequest(BaseModel):
    event_id: UUID
    event_name: Literal["screen_view", "action_started", "action_failed", "blocker_reason"]
    screen_name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    control_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,39}$")
    reason_code: Literal[
        "validation_error",
        "permission_denied",
        "network_error",
        "service_error",
        "no_testers_available",
        "cannot_find_app",
        "cannot_join_group",
        "opt_in_issue",
        "install_issue",
        "unclear_instructions",
        "no_time",
        "other",
    ] | None = None


def require_analytics_admin(
    credentials: HTTPBasicCredentials = Depends(basic_auth),
) -> None:
    settings = get_settings()
    if not settings.analytics_admin_username or not settings.analytics_admin_password:
        raise HTTPException(status_code=404, detail="Not found")
    valid_username = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.analytics_admin_username.encode("utf-8"),
    )
    valid_password = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        settings.analytics_admin_password.encode("utf-8"),
    )
    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid analytics credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


@router.post("/analytics/events", status_code=status.HTTP_202_ACCEPTED)
def collect_analytics_event(
    body: AnalyticsEventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    payload = {
        "screen_name": body.screen_name,
        "control_id": body.control_id,
        "reason_code": body.reason_code,
    }
    event = PilotEvent(
        actor_user_id=current_user.id,
        event_type=body.event_name,
        dedupe_key=f"ui:{current_user.id}:{body.event_id}",
        payload_json=json.dumps(payload, sort_keys=True),
    )
    db.add(event)
    try:
        db.commit()
    except Exception:
        db.rollback()
        # Repeated event IDs are idempotent; other database errors still fail closed.
        existing = db.scalar(
            select(PilotEvent).where(
                PilotEvent.dedupe_key == f"ui:{current_user.id}:{body.event_id}"
            )
        )
        if existing is None:
            raise
    return {"status": "accepted"}


def analytics_summary(db: Session) -> dict[str, dict[str, int]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    rows = db.scalars(
        select(PilotEvent)
        .where(PilotEvent.created_at >= cutoff)
        .order_by(PilotEvent.created_at.desc())
        .limit(10000)
    )
    screens: dict[str, int] = {}
    actions: dict[str, int] = {}
    reasons: dict[str, int] = {}
    for row in rows:
        try:
            payload = json.loads(row.payload_json or "{}")
        except (TypeError, json.JSONDecodeError):
            payload = {}
        if row.event_type == "screen_view":
            key = payload.get("screen_name")
            if isinstance(key, str):
                screens[key] = screens.get(key, 0) + 1
        elif row.event_type == "action_started":
            key = payload.get("control_id") or payload.get("screen_name")
            if isinstance(key, str):
                actions[key] = actions.get(key, 0) + 1
        elif row.event_type in {"action_failed", "blocker_reason"}:
            key = payload.get("reason_code")
            if isinstance(key, str):
                reasons[key] = reasons.get(key, 0) + 1
    return {"screens": screens, "actions": actions, "reasons": reasons}


@router.get("/admin/analytics", response_class=HTMLResponse)
def analytics_dashboard(
    _admin: None = Depends(require_analytics_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    summary = analytics_summary(db)

    def rows(values: dict[str, int]) -> str:
        if not values:
            return "<tr><td colspan='2'>No events in the last 30 days.</td></tr>"
        return "".join(
            f"<tr><td>{escape(name)}</td><td>{count}</td></tr>"
            for name, count in sorted(values.items(), key=lambda pair: (-pair[1], pair[0]))
        )

    html = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Launch Circle user flow</title>
<style>
body{{font:16px system-ui,sans-serif;max-width:900px;margin:32px auto;padding:0 16px;color:#17202a}}
table{{border-collapse:collapse;width:100%;margin:12px 0 28px}}th,td{{border-bottom:1px solid #ddd;padding:9px;text-align:left}}
h1{{margin-bottom:4px}}.muted{{color:#566573}}
</style>
<h1>Launch Circle user flow</h1><p class="muted">Aggregated events from the last 30 days. User emails and free-text fields are not shown.</p>
<h2>Screen views</h2><table><thead><tr><th>Screen</th><th>Events</th></tr></thead><tbody>{rows(summary["screens"])}</tbody></table>
<h2>Primary actions</h2><table><thead><tr><th>Control</th><th>Events</th></tr></thead><tbody>{rows(summary["actions"])}</tbody></table>
<h2>Failures and reported blockers</h2><table><thead><tr><th>Reason</th><th>Events</th></tr></thead><tbody>{rows(summary["reasons"])}</tbody></table>
</html>"""
    return HTMLResponse(html)
