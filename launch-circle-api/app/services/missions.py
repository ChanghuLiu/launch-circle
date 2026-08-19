from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.launch import TesterAssignment, TestMission
from app.services.events import emit_event

MISSION_SCHEDULE = (
    (1, "INSTALL_FIRST_IMPRESSION"),
    (3, "CORE_FEATURE"),
    (5, "EDGE_CASE"),
    (8, "SECOND_USE"),
    (11, "RETEST"),
    (14, "FINAL_FEEDBACK"),
)
MISSION_MINUTES = {
    "INSTALL_FIRST_IMPRESSION": 3,
    "CORE_FEATURE": 5,
    "EDGE_CASE": 5,
    "SECOND_USE": 4,
    "RETEST": 5,
    "FINAL_FEEDBACK": 5,
}


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def generate_missions(
    db: Session, assignment: TesterAssignment, now: datetime | None = None
) -> list[TestMission]:
    existing = list(db.scalars(select(TestMission).where(TestMission.assignment_id == assignment.id)))
    if existing:
        return existing
    start = aware(assignment.installed_at or assignment.opted_in_at or now or datetime.now(timezone.utc))
    missions = []
    for day, mission_type in MISSION_SCHEDULE:
        available_at = start + timedelta(days=day - 1)
        mission = TestMission(
            assignment_id=assignment.id,
            mission_type=mission_type,
            scheduled_day=day,
            status="AVAILABLE" if available_at <= (now or datetime.now(timezone.utc)) else "PENDING",
            due_at=available_at + timedelta(days=1),
        )
        db.add(mission)
        missions.append(mission)
    db.flush()
    for mission in missions:
        if mission.status == "AVAILABLE":
            emit_event(
                db,
                assignment.app_id,
                "MISSION_AVAILABLE",
                f"mission-available:{mission.id}",
                assignment.id,
                {"mission_id": mission.id, "scheduled_day": mission.scheduled_day},
            )
    return missions


def refresh_mission_availability(
    db: Session, missions: list[TestMission], now: datetime | None = None
) -> None:
    current = now or datetime.now(timezone.utc)
    for mission in missions:
        if mission.status not in {"PENDING", "AVAILABLE"} or mission.due_at is None:
            continue
        available_at = aware(mission.due_at) - timedelta(days=1)
        if current > aware(mission.due_at) + timedelta(days=1):
            mission.status = "MISSED"
        elif mission.status == "PENDING" and available_at <= current:
            mission.status = "AVAILABLE"
            emit_event(
                db,
                mission.assignment.app_id,
                "MISSION_AVAILABLE",
                f"mission-available:{mission.id}",
                mission.assignment_id,
                {"mission_id": mission.id, "scheduled_day": mission.scheduled_day},
            )
    db.flush()
