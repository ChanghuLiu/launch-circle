from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.launch import App, BackendEvent, CircleMember, TesterAssignment
from app.models.pool import AppGroupApp, AppGroupMember
from app.models.user import User
from app.services.assignments import assignment_day
from app.services.dispatch_authorization import app_group_recruitment_open
from app.services.events import emit_event
from app.services.lifecycle import GOOGLE_MINIMUM

MINIMUM_RELIABILITY = -10
ACTIVE_WORK_STATES = {"ASSIGNED", "OPTED_IN", "INSTALLED", "ACTIVE"}
ACTIVE_COVERAGE_STATES = {"ACTIVE", "COMPLETED"}


def _timestamp(value: datetime | None) -> float:
    if value is None:
        return 0.0
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.timestamp()


def match_testers(
    db: Session,
    app: App,
    *,
    limit: int | None = None,
    replacement_for: TesterAssignment | None = None,
    now: datetime | None = None,
) -> list[TesterAssignment]:
    if app.no_test_required or not app_group_recruitment_open(db, app.id):
        return []
    current = [
        a
        for a in app.assignments
        if a.status != "DROPPED" and a.health_status not in {"INACTIVE", "DROPPED"}
    ]
    needed = max(0, app.tester_target - len(current))
    if limit is not None:
        needed = min(needed, limit)
    if needed == 0:
        return []

    circle_member_ids = select(CircleMember.user_id).where(
        CircleMember.circle_id == app.circle_id,
        CircleMember.status == "ACTIVE",
    )
    app_group_member_ids = (
        select(AppGroupMember.user_id)
        .join(AppGroupApp, AppGroupApp.group_id == AppGroupMember.group_id)
        .where(AppGroupApp.app_id == app.id)
    )
    users = list(
        db.scalars(
            select(User).where(
                User.id != app.owner_id,
                User.is_active.is_(True),
                User.id.in_(circle_member_ids),
                User.id.in_(app_group_member_ids),
            )
        )
    )
    active_for_app = {a.tester_id for a in app.assignments}
    current_time = now or datetime.now(UTC)
    current_day = assignment_day(current_time)
    workloads: dict[str, int] = {}
    for assignment in db.scalars(select(TesterAssignment)):
        if assignment.status in ACTIVE_WORK_STATES:
            workloads[assignment.tester_id] = workloads.get(assignment.tester_id, 0) + 1
    daily_workloads: dict[str, int] = {}
    for assignment in db.scalars(
        select(TesterAssignment).where(
            TesterAssignment.assignment_day == current_day,
        )
    ):
        daily_workloads[assignment.tester_id] = daily_workloads.get(assignment.tester_id, 0) + 1

    eligible = [
        user
        for user in users
        if (
            user.id not in active_for_app
            and user.reliability_score >= MINIMUM_RELIABILITY
            and daily_workloads.get(user.id, 0) < 2
        )
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
        db.execute(update(User).where(User.id == user.id).values(is_active=User.is_active))
        current_user_today = db.scalar(select(func.count(TesterAssignment.id)).where(
            TesterAssignment.tester_id == user.id,
            TesterAssignment.assignment_day == current_day,
        )) or 0
        current_user_work = db.scalar(select(func.count(TesterAssignment.id)).where(
            TesterAssignment.tester_id == user.id,
            TesterAssignment.status.in_(ACTIVE_WORK_STATES),
        )) or 0
        if current_user_today >= 2 or current_user_work >= 2:
            continue
        assignment = TesterAssignment(
            app=app,
            circle_id=app.circle_id,
            tester_id=user.id,
            assignment_day=current_day,
            test_type="APP_CHECK",
            status="ASSIGNED",
            health_status="NEW",
            replacement_for_id=replacement_for.id if replacement_for else None,
        )
        db.add(assignment)
        db.flush()
        assigned.append(assignment)
        daily_workloads[user.id] = daily_workloads.get(user.id, 0) + 1
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


def effective_coverage(app: App) -> int:
    return sum(
        assignment.status in ACTIVE_COVERAGE_STATES
        and assignment.health_status in {"NEW", "GOOD"}
        and assignment.opted_in_at is not None
        and assignment.installed_at is not None
        and assignment.status != "DROPPED"
        for assignment in app.assignments
    )


def assign_replacements(
    db: Session,
    app: App,
    now: datetime,
    *,
    limit: int | None = None,
) -> list[TesterAssignment]:
    """Assign missing coverage from the app's Circle without rewriting history."""
    if app.no_test_required or not app_group_recruitment_open(db, app.id):
        return []
    if app.testing_start_at is None or app.status not in {"TESTING", "AT_RISK"}:
        return []
    shortage = max(0, GOOGLE_MINIMUM - effective_coverage(app))
    pending = sum(
        assignment.replacement_for_id is not None
        and assignment.status != "DROPPED"
        and not (
            assignment.status in ACTIVE_COVERAGE_STATES
            and assignment.opted_in_at is not None
            and assignment.installed_at is not None
        )
        for assignment in app.assignments
    )
    needed = max(0, shortage - pending)
    if limit is not None:
        needed = min(needed, limit)
    if needed == 0:
        return []

    current_day = assignment_day(now)
    existing_tester_ids = {assignment.tester_id for assignment in app.assignments}
    consented_member_ids = (
        select(AppGroupMember.user_id)
        .join(AppGroupApp, AppGroupApp.group_id == AppGroupMember.group_id)
        .where(AppGroupApp.app_id == app.id)
    )
    member_rows = list(
        db.scalars(
            select(CircleMember)
            .join(User, User.id == CircleMember.user_id)
            .where(
                CircleMember.circle_id == app.circle_id,
                CircleMember.status == "ACTIVE",
                User.is_active.is_(True),
                User.id.in_(consented_member_ids),
                User.id != app.owner_id,
            )
        )
    )
    today_workload: dict[str, int] = {}
    for row in db.scalars(
        select(TesterAssignment).where(
            TesterAssignment.assignment_day == current_day,
        )
    ):
        today_workload[row.tester_id] = today_workload.get(row.tester_id, 0) + 1
    app_history: dict[str, int] = {}
    for row in db.scalars(
        select(TesterAssignment).where(
            TesterAssignment.app_id == app.id,
            TesterAssignment.status != "DROPPED",
        )
    ):
        app_history[row.tester_id] = app_history.get(row.tester_id, 0) + 1
    candidates = [
        member
        for member in member_rows
        if member.user_id not in existing_tester_ids
        and member.user.reliability_score >= MINIMUM_RELIABILITY
        and today_workload.get(member.user_id, 0) < 2
    ]
    candidates.sort(
        key=lambda member: (
            today_workload.get(member.user_id, 0),
            app_history.get(member.user_id, 0),
            member.joined_at,
            member.user_id,
        )
    )

    assigned: list[TesterAssignment] = []
    assignments_with_replacements = {
        row.replacement_for_id
        for row in app.assignments
        if row.replacement_for_id is not None and row.status != "DROPPED"
    }
    system_ended_ids = set(db.scalars(
        select(BackendEvent.assignment_id).where(
            BackendEvent.app_id == app.id,
            BackendEvent.event_type == "ASSIGNMENT_ENDED_NO_CONSENT",
        )
    ))
    inactive = [
        row
        for row in app.assignments
        if (row.health_status in {"INACTIVE", "DROPPED"} or row.status == "DROPPED")
        and row.id not in assignments_with_replacements
        and row.id not in system_ended_ids
    ]
    inactive.sort(key=lambda row: (_timestamp(row.assigned_at), row.id), reverse=True)
    for member, replaced in zip(candidates[:needed], inactive):
        db.execute(update(User).where(User.id == member.user_id).values(is_active=User.is_active))
        current_user_today = db.scalar(select(func.count(TesterAssignment.id)).where(
            TesterAssignment.tester_id == member.user_id,
            TesterAssignment.assignment_day == current_day,
        )) or 0
        current_user_work = db.scalar(select(func.count(TesterAssignment.id)).where(
            TesterAssignment.tester_id == member.user_id,
            TesterAssignment.status.in_(ACTIVE_WORK_STATES),
        )) or 0
        if current_user_today >= 2 or current_user_work >= 2:
            continue
        assignment = TesterAssignment(
            app=app,
            circle_id=app.circle_id,
            tester_id=member.user_id,
            assignment_day=current_day,
            test_type="APP_CHECK",
            status="ASSIGNED",
            health_status="NEW",
            replacement_for_id=replaced.id,
            assigned_at=now,
        )
        db.add(assignment)
        db.flush()
        assigned.append(assignment)
        today_workload[member.user_id] = today_workload.get(member.user_id, 0) + 1
        existing_tester_ids.add(member.user_id)
        emit_event(
            db,
            app.id,
            "REPLACEMENT_ASSIGNED",
            f"REPLACEMENT_ASSIGNED:{assignment.id}",
            assignment.id,
            {"replacement_for_id": replaced.id},
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
