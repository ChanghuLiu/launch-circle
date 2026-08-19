"""Repeatable isolated seed for Galaxy S10 Phase 1 UI acceptance only."""
import os
from datetime import datetime, timedelta, timezone

import app.models  # noqa: F401

from app.api.phase0 import password_hash
from app.core.database import Base, SessionLocal, engine
from app.models.launch import App, AppChange, Feedback, TesterAssignment, TestMission
from app.models.user import User
from app.services.missions import MISSION_SCHEDULE

OWNER_EMAIL = "phase1.developer.a@example.com"
TESTER_EMAIL = "phase1.tester01@example.com"


def mission_status(role: str, tester_number: int, day: int) -> str:
    if role == "replacement":
        return "COMPLETED" if day == 1 else "PENDING"
    if role == "new":
        return "PENDING"
    if role == "dropped":
        return "COMPLETED" if day in {1, 3} else ("MISSED" if day == 5 else "PENDING")
    if role == "inactive":
        return "COMPLETED" if day == 1 else ("MISSED" if day in {3, 5} else "PENDING")
    if role == "at_risk":
        return "COMPLETED" if day in {1, 3} else ("MISSED" if day == 5 else "PENDING")
    if tester_number == 1:
        return "COMPLETED" if day in {1, 3} else ("AVAILABLE" if day == 5 else "PENDING")
    return "COMPLETED" if day in {1, 3, 5} else "PENDING"


def main() -> None:
    password = os.getenv("ACCEPTANCE_TEST_PASSWORD")
    if password is None or len(password) < 8:
        raise RuntimeError(
            "ACCEPTANCE_TEST_PASSWORD must be set to a temporary value of at least 8 characters"
        )
    opt_in_url = os.getenv(
        "ACCEPTANCE_OPT_IN_URL",
        "https://play.google.com/apps/testing/com.launchcircle.acceptance.phase1",
    )

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    testing_start = now - timedelta(days=5)

    with SessionLocal() as db:
        owner = User(
            email=OWNER_EMAIL,
            login_email=OWNER_EMAIL,
            password_hash=password_hash(password),
            display_name="Developer A",
            country="CA",
            reliability_score=10,
            is_active=True,
        )
        db.add(owner)
        testers: list[User] = []
        for number in range(1, 19):
            email = f"phase1.tester{number:02d}@example.com"
            tester = User(
                email=email,
                login_email=email,
                password_hash=password_hash(password),
                display_name=f"Acceptance Tester {number:02d}",
                country="CA",
                reliability_score=20 - number,
                is_active=True,
            )
            db.add(tester)
            testers.append(tester)
        db.flush()

        launch = App(
            owner_id=owner.id,
            name="Phase 1 Signal Analyzer",
            package_name="com.launchcircle.acceptance.phase1",
            opt_in_url=opt_in_url,
            google_group_url=None,
            status="TESTING",
            tester_target=18,
            testing_start_at=testing_start,
            testing_end_at=testing_start + timedelta(days=14),
        )
        db.add(launch)
        db.flush()

        assignments: list[tuple[TesterAssignment, str, int]] = []
        for number in range(1, 13):
            assignment = TesterAssignment(
                app_id=launch.id,
                tester_id=testers[number - 1].id,
                status="ACTIVE",
                assigned_at=testing_start - timedelta(days=1),
                opted_in_at=testing_start - timedelta(hours=2),
                installed_at=testing_start - timedelta(hours=1),
                health_status="GOOD",
                last_activity_at=now,
            )
            db.add(assignment)
            assignments.append((assignment, "good", number))

        new_assignment = TesterAssignment(
            app_id=launch.id,
            tester_id=testers[12].id,
            status="ASSIGNED",
            assigned_at=now - timedelta(hours=6),
            health_status="NEW",
        )
        at_risk = TesterAssignment(
            app_id=launch.id,
            tester_id=testers[13].id,
            status="ACTIVE",
            assigned_at=testing_start - timedelta(days=1),
            opted_in_at=testing_start,
            installed_at=testing_start,
            health_status="AT_RISK",
            last_activity_at=now - timedelta(days=3),
            overdue_mission_count=1,
        )
        inactive = TesterAssignment(
            app_id=launch.id,
            tester_id=testers[14].id,
            status="ACTIVE",
            assigned_at=testing_start - timedelta(days=1),
            opted_in_at=testing_start,
            installed_at=testing_start,
            health_status="INACTIVE",
            last_activity_at=now - timedelta(days=5),
            overdue_mission_count=2,
        )
        dropped = TesterAssignment(
            app_id=launch.id,
            tester_id=testers[15].id,
            status="DROPPED",
            assigned_at=testing_start - timedelta(days=1),
            opted_in_at=testing_start,
            installed_at=testing_start,
            dropped_at=now - timedelta(days=1),
            health_status="DROPPED",
            last_activity_at=now - timedelta(days=1),
            overdue_mission_count=1,
        )
        db.add_all([new_assignment, at_risk, inactive, dropped])
        db.flush()
        replacement = TesterAssignment(
            app_id=launch.id,
            tester_id=testers[16].id,
            status="ACTIVE",
            assigned_at=now - timedelta(days=1),
            opted_in_at=now - timedelta(days=1),
            installed_at=now - timedelta(days=1),
            health_status="GOOD",
            last_activity_at=now,
            replacement_for_id=dropped.id,
        )
        db.add(replacement)
        assignments.extend(
            [
                (at_risk, "at_risk", 14),
                (inactive, "inactive", 15),
                (dropped, "dropped", 16),
                (replacement, "replacement", 17),
            ]
        )
        db.flush()

        first_feedback_mission = None
        second_feedback_mission = None
        for assignment, role, number in assignments:
            start = assignment.installed_at or now
            for day, mission_type in MISSION_SCHEDULE:
                status = mission_status(role, number, day)
                due_at = start + timedelta(days=day)
                mission = TestMission(
                    assignment_id=assignment.id,
                    mission_type=mission_type,
                    scheduled_day=day,
                    status=status,
                    due_at=due_at,
                    completed_at=now - timedelta(days=max(0, 6 - day))
                    if status == "COMPLETED"
                    else None,
                )
                db.add(mission)
                db.flush()
                if role == "good" and number == 1 and day == 1:
                    first_feedback_mission = mission
                if role == "good" and number == 2 and day == 3:
                    second_feedback_mission = mission

        db.add_all(
            [
                Feedback(
                    mission_id=first_feedback_mission.id,
                    tester_id=first_feedback_mission.assignment.tester_id,
                    app_id=launch.id,
                    launch_ok=True,
                    core_feature_ok="PARTLY",
                    rating=4,
                    issue_text="Dark mode contrast was low on the results card.",
                    suggestion_text="Increase contrast for the primary result.",
                ),
                Feedback(
                    mission_id=second_feedback_mission.id,
                    tester_id=second_feedback_mission.assignment.tester_id,
                    app_id=launch.id,
                    launch_ok=True,
                    core_feature_ok="YES",
                    rating=5,
                    issue_text=None,
                    suggestion_text="Clarify the scan action label.",
                ),
                AppChange(
                    app_id=launch.id,
                    description="Improved dark mode result-card contrast from tester feedback.",
                    created_at=now - timedelta(days=1),
                ),
            ]
        )
        db.commit()

        counts = {
            "app_id": launch.id,
            "owner_email": OWNER_EMAIL,
            "active_tester_email": TESTER_EMAIL,
            "testing_start_at": testing_start.isoformat(),
            "expected_day": 6,
            "target": launch.tester_target,
            "initial_non_dropped_assignments": 16,
            "eligible_spares": 1,
        }
        print(counts)


if __name__ == "__main__":
    main()
