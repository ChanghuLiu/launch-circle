from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.launch import (
    App,
    AppChange,
    AdditionalAppPurchase,
    DeveloperCoordinationLog,
    Feedback,
    ManagedCredit,
    ManagedCheckout,
    TesterAssignment,
    TestMission,
)
from app.services.missions import MISSION_MINUTES

WORKLOAD_OFFER_MINUTES = 60
MANAGED_LIST_PRICE_CENTS = 1500


def workload_snapshot(db: Session, app: App) -> dict[str, int]:
    completed_rows = db.execute(
        select(TestMission.mission_type, Feedback.time_spent_minutes)
        .join(TesterAssignment, TestMission.assignment_id == TesterAssignment.id)
        .outerjoin(Feedback, Feedback.mission_id == TestMission.id)
        .where(TesterAssignment.app_id == app.id, TestMission.status == "COMPLETED")
    ).all()
    completed_missions = len(completed_rows)
    reported_minutes = sum(minutes or 0 for _mission_type, minutes in completed_rows)
    feedback_with_time = db.scalar(
        select(func.count(Feedback.id)).where(
            Feedback.app_id == app.id, Feedback.time_spent_minutes.is_not(None)
        )
    ) or 0
    feedback_without_time = db.scalar(
        select(func.count(Feedback.id)).where(
            Feedback.app_id == app.id, Feedback.time_spent_minutes.is_(None)
        )
    ) or 0
    estimated_unreported = sum(
        MISSION_MINUTES.get(mission_type, 0)
        for mission_type, minutes in completed_rows
        if minutes is None
    )
    coordination_rows = list(
        db.scalars(
            select(DeveloperCoordinationLog).where(
                DeveloperCoordinationLog.app_id == app.id
            )
        )
    )
    return {
        "completed_missions": completed_missions,
        "tester_minutes_reported": reported_minutes,
        "tester_feedback_with_time": feedback_with_time,
        "tester_feedback_without_time": feedback_without_time,
        "estimated_unreported_tester_minutes": estimated_unreported,
        "developer_coordination_minutes": sum(row.minutes for row in coordination_rows),
        "coordination_entries": len(coordination_rows),
    }


def managed_offer_snapshot(db: Session, app: App) -> dict:
    managed_purchase_complete = db.scalar(
        select(ManagedCheckout.id)
        .where(
            ManagedCheckout.app_id == app.id,
            ManagedCheckout.status == "PAID",
            ManagedCheckout.google_play_purchase_token.is_not(None),
        )
        .limit(1)
    ) is not None
    pending_credit_amount = db.scalar(
        select(ManagedCheckout.credit_amount).where(
            ManagedCheckout.app_id == app.id,
            ManagedCheckout.status == "PENDING",
        )
    )
    if pending_credit_amount is not None:
        credit_amount = pending_credit_amount
    else:
        available_managed_credit = db.scalar(
            select(ManagedCredit.id).join(
                AdditionalAppPurchase,
                AdditionalAppPurchase.id == ManagedCredit.source_additional_app_purchase_id,
            )
            .where(
                ManagedCredit.owner_id == app.owner_id,
                ManagedCredit.status == "AVAILABLE",
                ManagedCredit.source_google_play_order_id.is_not(None),
                AdditionalAppPurchase.app_id == app.id,
                AdditionalAppPurchase.developer_account_id == app.developer_account_id,
                AdditionalAppPurchase.status == "CONSUMED",
                ~select(ManagedCheckout.id)
                .where(
                    ManagedCheckout.managed_credit_id == ManagedCredit.id,
                    ManagedCheckout.status == "PENDING",
                )
                .exists(),
            )
            .limit(1)
        ) is not None
        credit_amount = 100 if available_managed_credit else 0
    remaining_rows = db.execute(
        select(TestMission.mission_type)
        .join(TesterAssignment, TestMission.assignment_id == TesterAssignment.id)
        .where(
            TesterAssignment.tester_id == app.owner_id,
            TesterAssignment.circle_id == app.circle_id,
            TesterAssignment.status.not_in(("DROPPED", "COMPLETED")),
            TestMission.status.in_(("PENDING", "AVAILABLE")),
        )
    ).all()
    remaining_minutes = sum(
        MISSION_MINUTES.get(row.mission_type, 0) for row in remaining_rows
    )
    completed_reciprocal = db.scalar(
        select(func.count(TestMission.id))
        .join(TesterAssignment, TestMission.assignment_id == TesterAssignment.id)
        .where(
            TesterAssignment.tester_id == app.owner_id,
            TesterAssignment.circle_id == app.circle_id,
            TestMission.status == "COMPLETED",
        )
    ) or 0
    triggers: list[str] = []
    if app.entitlement_status != "MANAGED" and not managed_purchase_complete:
        if completed_reciprocal > 0 and remaining_minutes >= WORKLOAD_OFFER_MINUTES:
            triggers.append("WORKLOAD")
        replaced_assignment_ids = {
            assignment.replacement_for_id
            for assignment in app.assignments
            if assignment.replacement_for_id and assignment.status != "DROPPED"
        }
        if any(
            (
                assignment.status == "DROPPED"
                or assignment.health_status in {"INACTIVE", "DROPPED"}
            )
            and assignment.id not in replaced_assignment_ids
            for assignment in app.assignments
        ):
            triggers.append("DROPOUT")
        has_change = db.scalar(
            select(AppChange.id).where(AppChange.app_id == app.id).limit(1)
        ) is not None
        has_available_retest = db.scalar(
            select(TestMission.id)
            .join(TesterAssignment, TestMission.assignment_id == TesterAssignment.id)
            .where(
                TesterAssignment.app_id == app.id,
                TestMission.mission_type == "RETEST",
                TestMission.status == "AVAILABLE",
            )
            .limit(1)
        ) is not None
        if has_change and has_available_retest:
            triggers.append("RETEST")
    return {
        "triggers": triggers,
        "remaining_reciprocal_missions": len(remaining_rows),
        "remaining_reciprocal_minutes": remaining_minutes,
        "managed_list_price_cents": MANAGED_LIST_PRICE_CENTS,
        "managed_checkout_amount_cents": MANAGED_LIST_PRICE_CENTS - credit_amount,
        "managed_credit_amount_cents": credit_amount,
        "managed_launch_purchased": managed_purchase_complete,
    }
