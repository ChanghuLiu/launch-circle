from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.launch import App, CircleMember, TesterAssignment
from app.services.clock import aware
from app.services.events import emit_event

GOOGLE_MINIMUM = 12
TOTAL_DAYS = 14
QUALIFYING_STATES = {"ACTIVE", "COMPLETED"}
HEALTHY_STATES = {"NEW", "GOOD"}


def assignment_qualifies(assignment: TesterAssignment) -> bool:
    return (
        assignment.status in QUALIFYING_STATES
        and assignment.health_status in HEALTHY_STATES
        and assignment.opted_in_at is not None
        and assignment.installed_at is not None
    )


def lifecycle_qualifying(db, app: App) -> list[TesterAssignment]:
    active_members = set(
        db.scalars(
            select(CircleMember.user_id).where(
                CircleMember.circle_id == app.circle_id,
                CircleMember.status == "ACTIVE",
            )
        )
    )
    return [
        assignment
        for assignment in app.assignments
        if assignment.tester_id != app.owner_id
        and assignment.tester_id in active_members
        and assignment.status in QUALIFYING_STATES
        and assignment.opted_in_at is not None
        and assignment.installed_at is not None
    ]


def active_qualifying(db, app: App) -> list[TesterAssignment]:
    return [
        assignment
        for assignment in lifecycle_qualifying(db, app)
        if assignment.health_status in HEALTHY_STATES
    ]


def continuous_qualifying(db, app: App) -> list[TesterAssignment]:
    if app.testing_start_at is None:
        return active_qualifying(db, app)
    start = aware(app.testing_start_at)
    return [
        assignment
        for assignment in active_qualifying(db, app)
        if aware(assignment.installed_at) <= start
    ]


def establish_timeline(db, app: App, now: datetime) -> bool:
    if app.testing_start_at is not None:
        return False
    if len(active_qualifying(db, app)) < GOOGLE_MINIMUM:
        app.status = "WAITING_FOR_TESTERS"
        return False
    app.testing_start_at = now
    app.testing_end_at = now + timedelta(days=TOTAL_DAYS)
    app.status = "TESTING"
    emit_event(db, app.id, "GOOGLE_MINIMUM_REACHED", f"minimum:{app.id}")
    return True


def evaluate_lifecycle(db, app: App, now: datetime) -> bool:
    """Evaluate server-owned lifecycle state without resetting its start."""
    started = establish_timeline(db, app, now)
    if app.testing_start_at is None:
        return started
    timeline = timeline_values(app, now)
    if not timeline["lifecycle_complete"]:
        return started
    app.testing_completed_at = app.testing_completed_at or now
    if app.status != "PRODUCTION_READY":
        qualifying = len(active_qualifying(db, app))
        app.status = (
            "TESTING_COMPLETE"
            if qualifying >= GOOGLE_MINIMUM
            else "AT_RISK"
        )
    return True


def timeline_values(app: App, now: datetime) -> dict:
    if app.testing_start_at is None:
        return {
            "day": 0,
            "elapsed_days": 0,
            "days_remaining": TOTAL_DAYS,
            "estimated_ready_date": "",
            "lifecycle_complete": False,
        }
    start = aware(app.testing_start_at)
    current = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    elapsed = max(0, int((current - start).total_seconds() // 86400))
    day = min(TOTAL_DAYS, elapsed + 1)
    complete = current >= start + timedelta(days=TOTAL_DAYS)
    return {
        "day": day,
        "elapsed_days": min(TOTAL_DAYS, elapsed),
        "days_remaining": max(0, TOTAL_DAYS - elapsed),
        "estimated_ready_date": (start + timedelta(days=TOTAL_DAYS)).date().isoformat(),
        "lifecycle_complete": complete,
    }


def calculate_app_status(db, app: App, now: datetime, evidence_complete: bool = False) -> str:
    establish_timeline(db, app, now)
    timeline = timeline_values(app, now)
    qualifying = len(active_qualifying(db, app))
    continuous = len(continuous_qualifying(db, app))
    if timeline["lifecycle_complete"]:
        app.testing_completed_at = app.testing_completed_at or now
        emit_event(db, app.id, "DAY_14_COMPLETED", f"day14:{app.id}")
    if app.testing_start_at is None:
        status = "WAITING_FOR_TESTERS"
    elif timeline["lifecycle_complete"]:
        if qualifying >= GOOGLE_MINIMUM:
            if evidence_complete and app.report_generated_at:
                status = "PRODUCTION_READY"
                app.production_ready_at = app.production_ready_at or now
            else:
                status = "TESTING_COMPLETE"
        else:
            status = "AT_RISK"
    elif qualifying < GOOGLE_MINIMUM:
        status = "AT_RISK"
    else:
        status = "TESTING"
    app.status = status
    return status
