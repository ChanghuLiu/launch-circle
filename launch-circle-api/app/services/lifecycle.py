from datetime import datetime, timedelta

from app.models.launch import App, TesterAssignment
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
        and assignment.installed_at is not None
    )


def active_qualifying(assignments: list[TesterAssignment]) -> list[TesterAssignment]:
    return [assignment for assignment in assignments if assignment_qualifies(assignment)]


def continuous_qualifying(app: App) -> list[TesterAssignment]:
    if app.testing_start_at is None:
        return active_qualifying(app.assignments)
    start = aware(app.testing_start_at)
    return [
        assignment
        for assignment in active_qualifying(app.assignments)
        if aware(assignment.installed_at) <= start
    ]


def establish_timeline(db, app: App, now: datetime) -> bool:
    if app.testing_start_at is not None:
        return False
    if len(active_qualifying(app.assignments)) < GOOGLE_MINIMUM:
        app.status = "WAITING_FOR_TESTERS"
        return False
    app.testing_start_at = now
    app.testing_end_at = now + timedelta(days=TOTAL_DAYS)
    app.status = "TESTING"
    emit_event(db, app.id, "GOOGLE_MINIMUM_REACHED", f"minimum:{app.id}")
    return True


def timeline_values(app: App, now: datetime) -> dict:
    if app.testing_start_at is None:
        return {
            "day": 0,
            "elapsed_days": 0,
            "days_remaining": TOTAL_DAYS,
            "estimated_ready_date": (now + timedelta(days=TOTAL_DAYS)).date().isoformat(),
            "lifecycle_complete": False,
        }
    start = aware(app.testing_start_at)
    elapsed = max(0, (now.date() - start.date()).days)
    day = min(TOTAL_DAYS, elapsed + 1)
    complete = now >= start + timedelta(days=TOTAL_DAYS)
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
    qualifying = len(active_qualifying(app.assignments))
    continuous = len(continuous_qualifying(app))
    if timeline["lifecycle_complete"]:
        emit_event(db, app.id, "DAY_14_COMPLETED", f"day14:{app.id}")
    if app.testing_start_at is None:
        status = "WAITING_FOR_TESTERS"
    elif timeline["lifecycle_complete"] and evidence_complete:
        status = "PRODUCTION_READY" if app.report_generated_at else "TESTING_COMPLETE"
    elif qualifying < GOOGLE_MINIMUM or continuous < GOOGLE_MINIMUM:
        status = "AT_RISK"
    else:
        status = "TESTING"
    app.status = status
    return status
