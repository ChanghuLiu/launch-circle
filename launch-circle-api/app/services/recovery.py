from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.launch import App, TesterAssignment
from app.services.lifecycle import evaluate_lifecycle
from app.services.matching import assign_replacements
from app.services.readiness import calculate_readiness
from app.services.tester_health import refresh_app_health


def evaluate_app_recovery(
    db: Session,
    app: App,
    now: datetime,
    *,
    include_readiness: bool = True,
) -> list[TesterAssignment]:
    """Refresh health, preserve history, and idempotently fill active-cycle shortage."""
    refresh_app_health(db, app, now)
    evaluate_lifecycle(db, app, now)
    replacements = assign_replacements(db, app, now)
    if include_readiness:
        calculate_readiness(db, app, now)
    return replacements


def evaluate_circle_recovery(db: Session, circle_id: str, now: datetime) -> int:
    replacements = 0
    apps = list(db.scalars(select(App).where(App.circle_id == circle_id)))
    for app in apps:
        replacements += len(evaluate_app_recovery(db, app, now, include_readiness=True))
    return replacements
