import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.launch import BackendEvent, PilotEvent


def emit_event(
    db: Session,
    app_id: str,
    event_type: str,
    dedupe_key: str,
    assignment_id: str | None = None,
    payload: dict | None = None,
) -> BackendEvent:
    existing = db.scalar(select(BackendEvent).where(BackendEvent.dedupe_key == dedupe_key))
    if existing:
        return existing
    event = BackendEvent(
        app_id=app_id,
        assignment_id=assignment_id,
        event_type=event_type,
        dedupe_key=dedupe_key,
        payload_json=json.dumps(payload or {}, sort_keys=True),
    )
    db.add(event)
    return event


def emit_pilot_event(
    db: Session,
    actor_user_id: str,
    event_type: str,
    dedupe_key: str,
    *,
    app_id: str | None = None,
    assignment_id: str | None = None,
    invite_id: str | None = None,
    payload: dict | None = None,
) -> PilotEvent:
    existing = db.scalar(select(PilotEvent).where(PilotEvent.dedupe_key == dedupe_key))
    if existing:
        return existing
    event = PilotEvent(
        actor_user_id=actor_user_id,
        app_id=app_id,
        assignment_id=assignment_id,
        invite_id=invite_id,
        event_type=event_type,
        dedupe_key=dedupe_key,
        payload_json=json.dumps(payload or {}, sort_keys=True),
    )
    db.add(event)
    return event
