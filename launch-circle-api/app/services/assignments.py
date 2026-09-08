from collections import defaultdict
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.launch import App, CircleMember, TesterAssignment
from app.services.lifecycle import evaluate_lifecycle
from app.models.user import User

DAILY_ASSIGNMENT_LIMIT = 2
DEFAULT_TEST_TYPE = "APP_CHECK"


def assignment_day(now: datetime) -> date:
    """P0-2 uses the backend UTC date as the assignment-day boundary."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc).date()


def _active_circle_ids(db: Session, user_id: str) -> list[str]:
    return list(
        db.scalars(
            select(CircleMember.circle_id).where(
                CircleMember.user_id == user_id,
                CircleMember.status == "ACTIVE",
            )
        )
    )


def generate_daily_assignments(
    db: Session,
    requester_id: str,
    now: datetime,
) -> list[TesterAssignment]:
    """Create today's assignments for the requester's active circles.

    Generation is deliberately synchronous and deterministic. It fills each
    app for eligible active members in fair order, and the unique daily key
    makes repeated refreshes idempotent.
    """
    day = assignment_day(now)
    circle_ids = _active_circle_ids(db, requester_id)
    if not circle_ids:
        return []

    apps = list(
        db.scalars(
            select(App)
            .where(App.circle_id.in_(circle_ids))
            .order_by(App.circle_id, App.created_at, App.id)
        )
    )
    if not apps:
        return []
    for app in apps:
        evaluate_lifecycle(db, app, now)

    active_members = list(
        db.scalars(
            select(CircleMember)
            .join(User, User.id == CircleMember.user_id)
            .where(
                CircleMember.circle_id.in_(circle_ids),
                CircleMember.status == "ACTIVE",
                User.is_active.is_(True),
            )
        )
    )
    members_by_circle: dict[str, list[CircleMember]] = defaultdict(list)
    for member in active_members:
        members_by_circle[member.circle_id].append(member)

    today_rows = list(
        db.scalars(
            select(TesterAssignment).where(
                TesterAssignment.circle_id.in_(circle_ids),
                TesterAssignment.assignment_day == day,
                TesterAssignment.status != "DROPPED",
            )
        )
    )
    today_count: dict[str, int] = defaultdict(int)
    app_history: dict[tuple[str, str], int] = defaultdict(int)
    existing_keys: set[tuple[str, str, str]] = set()
    for row in today_rows:
        today_count[row.tester_id] += 1
        existing_keys.add((row.app_id, row.tester_id, row.test_type))
    historical = db.execute(
        select(
            TesterAssignment.app_id,
            TesterAssignment.tester_id,
            func.count(TesterAssignment.id),
        )
        .where(TesterAssignment.status != "DROPPED")
        .group_by(TesterAssignment.app_id, TesterAssignment.tester_id)
    )
    for app_id, tester_id, count in historical:
        app_history[(app_id, tester_id)] = int(count)

    created: list[TesterAssignment] = []
    for app in apps:
        if app.circle_id is None:
            continue
        members = members_by_circle.get(app.circle_id, [])
        unavailable_for_app = {
            row.tester_id
            for row in app.assignments
            if row.status == "DROPPED" or row.health_status in {"INACTIVE", "DROPPED"}
        }
        candidates = [
            member
            for member in members
            if member.user_id != app.owner_id
            and member.user_id not in unavailable_for_app
            and today_count[member.user_id] < DAILY_ASSIGNMENT_LIMIT
            and (app.id, member.user_id, DEFAULT_TEST_TYPE) not in existing_keys
        ]
        candidates.sort(
            key=lambda member: (
                today_count[member.user_id],
                app_history[(app.id, member.user_id)],
                member.joined_at,
                member.user_id,
            )
        )
        for member in candidates:
            row = TesterAssignment(
                app_id=app.id,
                circle_id=app.circle_id,
                tester_id=member.user_id,
                assignment_day=day,
                test_type=DEFAULT_TEST_TYPE,
                assigned_at=now,
                status="ASSIGNED",
            )
            db.add(row)
            db.flush()
            created.append(row)
            today_count[member.user_id] += 1
            app_history[(app.id, member.user_id)] += 1
            existing_keys.add((app.id, member.user_id, DEFAULT_TEST_TYPE))
    return created


def todays_assignments(
    db: Session,
    requester_id: str,
    now: datetime,
) -> list[TesterAssignment]:
    day = assignment_day(now)
    generate_daily_assignments(db, requester_id, now)
    circle_ids = _active_circle_ids(db, requester_id)
    if not circle_ids:
        return []
    from app.services.recovery import evaluate_app_recovery

    apps = list(db.scalars(select(App).where(App.circle_id.in_(circle_ids))))
    for app in apps:
        evaluate_app_recovery(db, app, now)
    return list(
        db.scalars(
            select(TesterAssignment)
            .where(
                TesterAssignment.tester_id == requester_id,
                TesterAssignment.circle_id.in_(circle_ids),
                TesterAssignment.assignment_day == day,
                TesterAssignment.status != "DROPPED",
            )
            .order_by(TesterAssignment.status, TesterAssignment.assigned_at, TesterAssignment.id)
        )
    )
