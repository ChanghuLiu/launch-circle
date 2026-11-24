from datetime import UTC, date, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.launch import App, CircleMember, TesterAssignment
from app.models.pool import AppGroupApp
from app.services.dispatch_authorization import (
    app_group_member_app_ids,
    explicitly_consented_assignment_ids,
)

DAILY_ASSIGNMENT_LIMIT = 2
DEFAULT_TEST_TYPE = "APP_CHECK"


def assignment_day(now: datetime) -> date:
    """P0-2 uses the backend UTC date as the assignment-day boundary."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return now.astimezone(UTC).date()


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
    """Keep the legacy entry point inert: Circle membership is not app consent.

    Per-app acceptance creates its task in the acceptance transaction. App Group
    consent is applied by sync_group. No test-screen read may grant either scope.
    """
    return []


def todays_assignments(
    db: Session,
    requester_id: str,
    now: datetime,
) -> list[TesterAssignment]:
    day = assignment_day(now)
    circle_ids = _active_circle_ids(db, requester_id)
    if not circle_ids:
        return []
    from app.services.recovery import evaluate_app_recovery

    apps = list(db.scalars(select(App).where(App.circle_id.in_(circle_ids))))
    for app in apps:
        evaluate_app_recovery(db, app, now)
    rows = list(
        db.scalars(
            select(TesterAssignment)
            .where(
                TesterAssignment.tester_id == requester_id,
                TesterAssignment.circle_id.in_(circle_ids),
                or_(TesterAssignment.assignment_day == day,
                    TesterAssignment.app_id.in_(select(AppGroupApp.app_id))),
                TesterAssignment.status != "DROPPED",
            )
            .order_by(TesterAssignment.status, TesterAssignment.assigned_at, TesterAssignment.id)
        )
    )
    group_app_ids = app_group_member_app_ids(db, requester_id)
    direct_consent_ids = explicitly_consented_assignment_ids(
        db, requester_id, [row.id for row in rows]
    )
    return [
        row for row in rows
        if row.status == "COMPLETED"
        or row.app_id in group_app_ids
        or row.id in direct_consent_ids
    ]
