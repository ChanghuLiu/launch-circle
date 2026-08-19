from collections import Counter
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.launch import App, Feedback, TestMission, TesterAssignment
from app.services.clock import aware
from app.services.events import emit_event
from app.services.lifecycle import continuous_qualifying, timeline_values

MISSING = "Insufficient recorded evidence"


def _themes(values: list[str | None]) -> list[str]:
    normalized = [value.strip() for value in values if value and value.strip()]
    return [text for text, _count in Counter(normalized).most_common(5)]


def production_report(db: Session, app: App, now: datetime, mark_generated: bool = True) -> dict:
    assignments = list(app.assignments)
    feedback = list(db.scalars(select(Feedback).where(Feedback.app_id == app.id)))
    completed = db.scalar(
        select(func.count(TestMission.id))
        .join(TesterAssignment)
        .where(TesterAssignment.app_id == app.id, TestMission.status == "COMPLETED")
    ) or 0
    retests = db.scalar(
        select(func.count(TestMission.id))
        .join(TesterAssignment)
        .where(
            TesterAssignment.app_id == app.id,
            TestMission.mission_type == "RETEST",
            TestMission.status == "COMPLETED",
        )
    ) or 0
    completed_types = list(
        db.scalars(
            select(TestMission.mission_type)
            .join(TesterAssignment)
            .where(
                TesterAssignment.app_id == app.id,
                TestMission.status == "COMPLETED",
            )
            .distinct()
            .order_by(TestMission.scheduled_day)
        )
    )
    timeline = timeline_values(app, now)
    report = {
        "title": "Production testing summary",
        "purpose": "Production access preparation",
        "app_id": app.id,
        "app_name": app.name,
        "testing_period": {
            "started_at": aware(app.testing_start_at).isoformat() if app.testing_start_at else None,
            "ended_at": aware(app.testing_end_at).isoformat() if app.testing_end_at else None,
            "day": timeline["day"],
            "lifecycle_complete": timeline["lifecycle_complete"],
        },
        "assigned_testers": len(assignments),
        "continuous_testers": len(continuous_qualifying(app)),
        "replacements": sum(a.replacement_for_id is not None for a in assignments),
        "dropped_testers": sum(a.status == "DROPPED" for a in assignments),
        "completed_missions": completed,
        "completed_mission_types": completed_types,
        "feedback_count": len(feedback),
        "retest_activity": retests,
        "common_issues": _themes([item.issue_text for item in feedback]),
        "suggestions": _themes([item.suggestion_text for item in feedback]),
        "changes_recorded": [item.description for item in sorted(app.changes, key=lambda x: x.created_at)],
        "approval_disclaimer": (
            "This summary records Launch Circle testing evidence and does not guarantee "
            "Google Play production approval."
        ),
    }
    if mark_generated:
        app.report_generated_at = now
        emit_event(db, app.id, "PRODUCTION_REPORT_READY", f"report:{app.id}")
    return report


def production_application_draft(db: Session, app: App, now: datetime) -> dict:
    report = production_report(db, app, now, mark_generated=False)
    recruited = (
        f"Launch Circle matched {report['assigned_testers']} eligible developers; "
        f"{report['continuous_testers']} remained continuous qualifying testers."
        if report["assigned_testers"]
        else MISSING
    )
    completed_labels = [value.lower().replace("_", " ") for value in report["completed_mission_types"]]
    usage = (
        f"Testers completed {report['completed_missions']} scheduled missions. "
        f"Recorded completed checkpoints: {', '.join(completed_labels)}."
        if report["completed_missions"]
        else MISSING
    )
    evidence = report["common_issues"] + report["suggestions"]
    feedback = "; ".join(evidence) if evidence else MISSING
    changes = "; ".join(report["changes_recorded"]) if report["changes_recorded"] else MISSING
    return {
        "title": "Production access preparation draft",
        "how_testers_were_recruited": recruited,
        "how_testers_used_the_app": usage,
        "feedback_received": feedback,
        "changes_made": changes,
        "evidence_only": True,
        "approval_disclaimer": report["approval_disclaimer"],
    }
