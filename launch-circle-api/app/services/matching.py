from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.launch import App, TesterAssignment
from app.models.user import User
from app.services.events import emit_event

MINIMUM_RELIABILITY = -10
ACTIVE_WORK_STATES = {"ASSIGNED", "OPTED_IN", "INSTALLED", "ACTIVE"}
ACTIVE_COVERAGE_STATES = {"ACTIVE", "COMPLETED"}


def _timestamp(value: datetime | None) -> float:
    if value is None:
        return 0.0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def match_testers(
    db: Session,
    app: App,
    *,
    limit: int | None = None,
    replacement_for: TesterAssignment | None = None,
) -> list[TesterAssignment]:
    current = [
        a for a in app.assignments
        if a.status != "DROPPED" and a.health_status not in {"INACTIVE", "DROPPED"}
    ]
    needed = max(0, app.tester_target - len(current))
    if limit is not None:
        needed = min(needed, limit)
    if needed == 0:
        return []

    users = list(db.scalars(select(User).where(User.id != app.owner_id, User.is_active.is_(True))))
    active_for_app = {a.tester_id for a in app.assignments}
    workloads: dict[str, int] = {}
    for assignment in db.scalars(select(TesterAssignment)):
        if assignment.status in ACTIVE_WORK_STATES:
            workloads[assignment.tester_id] = workloads.get(assignment.tester_id, 0) + 1

    eligible = [
        user
        for user in users
        if user.id not in active_for_app and user.reliability_score >= MINIMUM_RELIABILITY
    ]
    eligible.sort(
        key=lambda user: (
            -user.reliability_score,
            workloads.get(user.id, 0),
            -_timestamp(user.last_successful_test_at),
            _timestamp(user.created_at),
            user.id,
        )
    )

    assigned: list[TesterAssignment] = []
    for user in eligible[:needed]:
        assignment = TesterAssignment(
            app=app,
            tester_id=user.id,
            status="ASSIGNED",
            health_status="NEW",
            replacement_for_id=replacement_for.id if replacement_for else None,
        )
        db.add(assignment)
        db.flush()
        assigned.append(assignment)
        event_type = "REPLACEMENT_ASSIGNED" if replacement_for else "TESTER_ASSIGNED"
        emit_event(
            db,
            app.id,
            event_type,
            f"{event_type}:{assignment.id}",
            assignment.id,
            {"replacement_for_id": assignment.replacement_for_id},
        )
    return assigned


def matching_summary(app: App, assigned_now: int) -> dict[str, int]:
    active = sum(
        a.status in ACTIVE_COVERAGE_STATES
        and a.health_status in {"NEW", "GOOD"}
        and a.installed_at is not None
        for a in app.assignments
    )
    assigned_total = sum(a.status != "DROPPED" for a in app.assignments)
    return {
        "assigned_now": assigned_now,
        "assigned_total": assigned_total,
        "active_testers": active,
        "minimum_needed": max(0, 12 - active),
        "target": app.tester_target,
        "remaining_to_target": max(0, app.tester_target - assigned_total),
    }
