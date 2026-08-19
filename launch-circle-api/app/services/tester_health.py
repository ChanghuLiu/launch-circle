from datetime import datetime, timedelta

from app.models.launch import App, TesterAssignment
from app.services.clock import aware
from app.services.events import emit_event
from app.services.missions import refresh_mission_availability

MISSION_GRACE = timedelta(days=1)
AT_RISK_INACTIVITY = timedelta(days=2)
INACTIVE_AFTER = timedelta(days=4)


def record_activity(assignment: TesterAssignment, now: datetime) -> None:
    assignment.last_activity_at = now
    if assignment.status != "DROPPED":
        assignment.health_status = "GOOD" if assignment.installed_at else "NEW"


def evaluate_assignment(db, assignment: TesterAssignment, now: datetime) -> str:
    old = assignment.health_status
    if assignment.status == "DROPPED" or assignment.dropped_at:
        new = "DROPPED"
    elif assignment.status not in {"ACTIVE", "COMPLETED"}:
        new = "NEW"
    else:
        refresh_mission_availability(db, assignment.missions, now)
        overdue = sum(
            mission.status == "MISSED"
            or (
                mission.status == "AVAILABLE"
                and mission.due_at is not None
                and now > aware(mission.due_at) + MISSION_GRACE
            )
            for mission in assignment.missions
        )
        activity = aware(
            assignment.last_activity_at
            or assignment.installed_at
            or assignment.opted_in_at
            or assignment.assigned_at
        )
        idle = now - activity
        if idle >= INACTIVE_AFTER or overdue >= 2:
            new = "INACTIVE"
        elif idle >= AT_RISK_INACTIVITY or overdue >= 1:
            new = "AT_RISK"
        else:
            new = "GOOD"
        if overdue > assignment.overdue_mission_count:
            assignment.tester.reliability_score -= overdue - assignment.overdue_mission_count
        assignment.overdue_mission_count = overdue
    assignment.health_status = new
    if new in {"AT_RISK", "INACTIVE", "DROPPED"} and new != old:
        emit_event(
            db,
            assignment.app_id,
            "TESTER_AT_RISK",
            f"health:{assignment.id}:{new}",
            assignment.id,
            {"health_status": new},
        )
    return new


def refresh_app_health(db, app: App, now: datetime) -> list[TesterAssignment]:
    newly_inactive = []
    for assignment in app.assignments:
        old = assignment.health_status
        new = evaluate_assignment(db, assignment, now)
        if new in {"INACTIVE", "DROPPED"} and old not in {"INACTIVE", "DROPPED"}:
            newly_inactive.append(assignment)
    return newly_inactive
