from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.launch import App, Feedback, TesterAssignment, TestMission
from app.services.lifecycle import (
    GOOGLE_MINIMUM,
    TOTAL_DAYS,
    active_qualifying,
    calculate_app_status,
    continuous_qualifying,
    timeline_values,
)


def calculate_readiness(db: Session, app: App, now: datetime | None = None) -> dict:
    current = now or datetime.now(timezone.utc)
    assignments = list(app.assignments)
    active = len(active_qualifying(assignments))
    continuous = len(continuous_qualifying(app))
    assigned = sum(item.status != "DROPPED" for item in assignments)
    feedback_count = db.scalar(select(func.count(Feedback.id)).where(Feedback.app_id == app.id)) or 0
    completed_missions = db.scalar(
        select(func.count(TestMission.id))
        .join(TesterAssignment)
        .where(TesterAssignment.app_id == app.id, TestMission.status == "COMPLETED")
    ) or 0
    available_missions = db.scalar(
        select(func.count(TestMission.id))
        .join(TesterAssignment)
        .where(TesterAssignment.app_id == app.id, TestMission.status != "PENDING")
    ) or 0
    retest_complete = bool(
        db.scalar(
            select(TestMission.id)
            .join(TesterAssignment)
            .where(
                TesterAssignment.app_id == app.id,
                TestMission.mission_type == "RETEST",
                TestMission.status == "COMPLETED",
            )
            .limit(1)
        )
    )
    final_complete = bool(
        db.scalar(
            select(TestMission.id)
            .join(TesterAssignment)
            .where(
                TesterAssignment.app_id == app.id,
                TestMission.mission_type == "FINAL_FEEDBACK",
                TestMission.status == "COMPLETED",
            )
            .limit(1)
        )
    )
    timeline = timeline_values(app, current)
    evidence_complete = bool(feedback_count and completed_missions and final_complete)
    app_status = calculate_app_status(db, app, current, evidence_complete)
    summary_available = app.report_generated_at is not None
    setup_complete = bool(app.name and app.package_name and app.opt_in_url)
    breakdown = {
        "app_setup_complete": 15 if setup_complete else 0,
        "google_minimum_testers": 20 if active >= GOOGLE_MINIMUM else 0,
        "target_testers": 5 if active >= app.tester_target else 0,
        "fourteen_day_testing": 30 if timeline["lifecycle_complete"] else 0,
        "feedback_received": 15 if feedback_count > 0 else 0,
        "retest_completed": 5 if retest_complete else 0,
        "testing_summary_available": 10 if summary_available else 0,
    }
    risk = sum(a.health_status in {"AT_RISK", "INACTIVE"} for a in assignments)
    replacements = sum(a.replacement_for_id is not None and a.status != "DROPPED" for a in assignments)
    today_tasks = sum(
        mission.status == "AVAILABLE" for assignment in assignments for mission in assignment.missions
    )
    return {
        "status": app_status,
        "active_testers": active,
        "assigned_testers": assigned,
        "continuous_qualifying_testers": continuous,
        "replacement_testers": replacements,
        "tester_target": app.tester_target,
        "google_minimum": GOOGLE_MINIMUM,
        "testers_needed_for_minimum": max(0, GOOGLE_MINIMUM - active),
        "day": timeline["day"],
        "elapsed_days": timeline["elapsed_days"],
        "total_days": TOTAL_DAYS,
        "days_remaining": timeline["days_remaining"],
        "production_readiness": sum(breakdown.values()),
        "readiness_breakdown": breakdown,
        "today_tasks": today_tasks,
        "at_risk_testers": risk,
        "circle_health": "AT_RISK" if app_status == "AT_RISK" or risk else "GOOD",
        "feedback_count": feedback_count,
        "completed_missions": completed_missions,
        "missions_completed": completed_missions,
        "missions_total_available": available_missions,
        "estimated_ready_date": timeline["estimated_ready_date"],
        "approval_disclaimer": (
            "Readiness is guidance only and does not guarantee Google Play production approval."
        ),
    }
