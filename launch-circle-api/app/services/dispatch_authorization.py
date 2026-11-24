"""Dispatch authorization scoped to an app or an explicitly joined App Group."""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin import AdminAppControl
from app.models.launch import BackendEvent, TesterAssignment
from app.models.pool import AppGroup, AppGroupApp, AppGroupMember, PoolListing


def app_group_member_ids(db: Session, app_id: str) -> set[str]:
    group_id = db.scalar(
        select(AppGroupApp.group_id).where(AppGroupApp.app_id == app_id)
    )
    if group_id is None:
        return set()
    return set(
        db.scalars(
            select(AppGroupMember.user_id).where(AppGroupMember.group_id == group_id)
        )
    )


def has_app_group_consent(db: Session, app_id: str, tester_id: str) -> bool:
    return tester_id in app_group_member_ids(db, app_id)


def app_group_recruitment_open(db: Session, app_id: str) -> bool:
    if db.get(AppGroupApp, app_id) is None:
        return False
    listing = db.get(PoolListing, app_id)
    group = db.get(AppGroup, db.scalar(select(AppGroupApp.group_id).where(AppGroupApp.app_id == app_id)))
    control = db.get(AdminAppControl, app_id)
    return bool(
        listing
        and listing.enabled
        and group is not None
        and group.status == "OPEN"
        and not (control and (control.paused or control.kind == "SYNTHETIC"))
    )


def explicitly_consented_assignment_ids(
    db: Session,
    user_id: str,
    assignment_ids: list[str],
) -> set[str]:
    """Return direct per-app accepts; legacy implicit rows have no such evidence."""
    if not assignment_ids:
        return set()
    consented: set[str] = set()
    events = db.scalars(
        select(BackendEvent)
        .join(TesterAssignment, TesterAssignment.id == BackendEvent.assignment_id)
        .where(
            BackendEvent.assignment_id.in_(assignment_ids),
            BackendEvent.event_type.in_({"TESTER_ASSIGNED", "APP_TEST_ACCEPTED"}),
            TesterAssignment.tester_id == user_id,
        )
    )
    for event in events:
        try:
            payload = json.loads(event.payload_json)
        except (TypeError, json.JSONDecodeError):
            continue
        if payload.get("source") != "VOLUNTARY_SHARED_POOL":
            continue
        # New events name the scope. The missing value is accepted only for
        # legacy per-App voluntary joins; Group sync now records APP_GROUP.
        if payload.get("consent_scope", "APP") != "APP":
            continue
        consented.add(event.assignment_id)
    return consented


def has_direct_app_consent(db: Session, assignment_id: str, tester_id: str) -> bool:
    return assignment_id in explicitly_consented_assignment_ids(
        db, tester_id, [assignment_id]
    )


def app_group_member_app_ids(db: Session, user_id: str) -> set[str]:
    return set(
        db.scalars(
            select(AppGroupApp.app_id)
            .join(AppGroupMember, AppGroupMember.group_id == AppGroupApp.group_id)
            .where(AppGroupMember.user_id == user_id)
        )
    )
