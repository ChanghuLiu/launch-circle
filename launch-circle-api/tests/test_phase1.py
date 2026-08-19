from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.main import app as fastapi_app
from app.core.database import SessionLocal, engine
from app.models.launch import App, Feedback, TesterAssignment as AssignmentModel
from app.models.user import User
from app.services.clock import get_now

PASSWORD = "strong-password"


def register(client, index: int, name: str | None = None) -> dict:
    email = f"phase1-{index}@example.com"
    response = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": name or f"Tester {index}"},
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    me = client.get("/me", headers={"Authorization": f"Bearer {token}"}).json()
    return {"id": me["id"], "headers": {"Authorization": f"Bearer {token}"}}


def create_app(client, owner: dict, target: int = 15, suffix: str = "main") -> dict:
    response = client.post(
        "/apps",
        headers=owner["headers"],
        json={
            "name": "Phase 1 Analyzer",
            "package_name": f"com.launchcircle.phase1.{suffix}",
            "opt_in_url": f"https://play.google.com/apps/testing/com.launchcircle.phase1.{suffix}",
            "tester_target": target,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def test_clock():
    state = {"now": datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)}
    fastapi_app.dependency_overrides[get_now] = lambda: state["now"]
    yield state
    fastapi_app.dependency_overrides.pop(get_now, None)


def activate(client, assignment: dict, tester: dict) -> None:
    assert client.patch(
        f"/assignments/{assignment['id']}/opt-in", headers=tester["headers"]
    ).status_code == 200
    installed = client.patch(
        f"/assignments/{assignment['id']}/installed", headers=tester["headers"]
    )
    assert installed.status_code == 200, installed.text


def test_matching_fills_15_excludes_owner_and_existing_assignment(client):
    owner = register(client, 0, "Owner")
    testers = [register(client, index) for index in range(1, 17)]
    launch = create_app(client, owner)
    manual = client.post(
        f"/apps/{launch['id']}/assign/{testers[0]['id']}", headers=owner["headers"]
    )
    assert manual.status_code == 201

    matched = client.post(f"/apps/{launch['id']}/match-testers", headers=owner["headers"])
    assert matched.status_code == 200, matched.text
    assert matched.json() == {
        "assigned_now": 14,
        "assigned_total": 15,
        "active_testers": 0,
        "minimum_needed": 12,
        "target": 15,
        "remaining_to_target": 0,
    }
    rows = client.get(f"/apps/{launch['id']}/testers", headers=owner["headers"]).json()
    assert len(rows) == 15
    assert owner["id"] not in {row["tester_id"] for row in rows}
    assert sum(row["tester_id"] == testers[0]["id"] for row in rows) == 1


def test_matching_small_pool_succeeds_and_cold_dashboard_remains_valid(client):
    owner = register(client, 0)
    for index in range(1, 6):
        register(client, index)
    launch = create_app(client, owner)
    matched = client.post(f"/apps/{launch['id']}/match-testers", headers=owner["headers"])
    assert matched.status_code == 200
    assert matched.json()["assigned_now"] == 5
    assert matched.json()["remaining_to_target"] == 10
    dashboard = client.get(f"/apps/{launch['id']}/dashboard", headers=owner["headers"])
    assert dashboard.status_code == 200
    assert dashboard.json()["status"] == "WAITING_FOR_TESTERS"
    assert dashboard.json()["testers_needed_for_minimum"] == 12


def test_matching_orders_reliability_then_workload(client):
    owner = register(client, 0)
    candidates = [register(client, index) for index in range(1, 5)]
    launch = create_app(client, owner, target=2)
    with SessionLocal() as db:
        users = [db.get(User, item["id"]) for item in candidates]
        users[0].reliability_score = 20
        users[1].reliability_score = 20
        users[2].reliability_score = 5
        users[3].reliability_score = 0
        other = App(
            owner_id=owner["id"], name="Other", package_name="com.phase1.other",
            opt_in_url="https://play.google.com/apps/testing/com.phase1.other", tester_target=15,
        )
        db.add(other)
        db.flush()
        db.add(AssignmentModel(app_id=other.id, tester_id=users[1].id, status="ACTIVE"))
        db.commit()
    response = client.post(f"/apps/{launch['id']}/match-testers", headers=owner["headers"])
    assert response.status_code == 200
    selected = {
        row["tester_id"]
        for row in client.get(f"/apps/{launch['id']}/testers", headers=owner["headers"]).json()
    }
    assert selected == {candidates[0]["id"], candidates[1]["id"]}


def test_date_driven_mission_availability_with_test_clock(client, test_clock):
    owner = register(client, 0)
    tester = register(client, 1)
    launch = create_app(client, owner)
    assignment = client.post(
        f"/apps/{launch['id']}/assign/{tester['id']}", headers=owner["headers"]
    ).json()
    activate(client, assignment, tester)

    day1 = client.get(f"/assignments/{assignment['id']}/missions", headers=tester["headers"]).json()
    assert day1[0]["status"] == "AVAILABLE"
    assert all(row["status"] == "PENDING" for row in day1[1:])

    test_clock["now"] += timedelta(days=2)
    day3 = client.get(f"/assignments/{assignment['id']}/missions", headers=tester["headers"]).json()
    assert day3[1]["mission_type"] == "CORE_FEATURE"
    assert day3[1]["status"] == "AVAILABLE"
    assert day3[2]["status"] == "PENDING"


def test_health_replacement_and_status_transitions(client, test_clock):
    owner = register(client, 0)
    testers = [register(client, index) for index in range(1, 17)]
    launch = create_app(client, owner)
    assert client.post(
        f"/apps/{launch['id']}/match-testers", headers=owner["headers"]
    ).json()["assigned_now"] == 15
    rows = client.get(f"/apps/{launch['id']}/testers", headers=owner["headers"]).json()
    by_id = {tester["id"]: tester for tester in testers}
    for row in rows:
        activate(client, row, by_id[row["tester_id"]])

    initial = client.get(f"/apps/{launch['id']}/dashboard", headers=owner["headers"]).json()
    assert initial["status"] == "TESTING"
    assert initial["continuous_qualifying_testers"] == 15

    test_clock["now"] += timedelta(days=5)
    victim_id = rows[0]["id"]
    with SessionLocal() as db:
        assignments = list(db.scalars(select(AssignmentModel).where(AssignmentModel.app_id == launch["id"])))
        for assignment in assignments:
            if assignment.id != victim_id:
                assignment.last_activity_at = test_clock["now"]
                for mission in assignment.missions:
                    if mission.scheduled_day <= 3:
                        mission.status = "COMPLETED"
                        mission.completed_at = test_clock["now"]
        db.commit()

    health = client.post(f"/apps/{launch['id']}/refresh-health", headers=owner["headers"])
    assert health.status_code == 200, health.text
    assert health.json()["inactive"] == 1
    assert health.json()["replacements_assigned"] == 1
    after = client.get(f"/apps/{launch['id']}/testers", headers=owner["headers"]).json()
    replacements = [row for row in after if row["is_replacement"]]
    assert len(replacements) == 1
    assert replacements[0]["replacement_for_id"] == victim_id
    assert replacements[0]["total_missions"] == 0
    dashboard = client.get(f"/apps/{launch['id']}/dashboard", headers=owner["headers"]).json()
    assert dashboard["status"] == "TESTING"
    assert dashboard["continuous_qualifying_testers"] == 14
    assert dashboard["replacement_testers"] == 1

    healthy_originals = [
        row for row in after if not row["is_replacement"] and row["id"] != victim_id
    ][:3]
    for row in healthy_originals:
        tester = by_id[row["tester_id"]]
        dropped = client.patch(
            f"/assignments/{row['id']}/drop", headers=tester["headers"], json={"reason": "left"}
        )
        assert dropped.status_code == 200
    risk = client.get(f"/apps/{launch['id']}/dashboard", headers=owner["headers"]).json()
    assert risk["status"] == "AT_RISK"
    assert risk["continuous_qualifying_testers"] == 11


def test_phase1_accelerated_acceptance_report_and_evidence_only_draft(client, test_clock):
    owner = register(client, 0, "Developer A")
    testers = [register(client, index) for index in range(1, 14)]
    launch = create_app(client, owner, target=12, suffix="acceptance")
    assert client.post(
        f"/apps/{launch['id']}/match-testers", headers=owner["headers"]
    ).json()["assigned_now"] == 12
    rows = client.get(f"/apps/{launch['id']}/testers", headers=owner["headers"]).json()
    by_id = {tester["id"]: tester for tester in testers}
    for row in rows:
        activate(client, row, by_id[row["tester_id"]])

    test_clock["now"] += timedelta(days=14)
    with SessionLocal() as db:
        assignments = list(db.scalars(select(AssignmentModel).where(AssignmentModel.app_id == launch["id"])))
        first_mission = None
        for assignment in assignments:
            assignment.status = "COMPLETED"
            assignment.health_status = "GOOD"
            assignment.last_activity_at = test_clock["now"]
            assignment.completed_at = test_clock["now"]
            for mission in assignment.missions:
                mission.status = "COMPLETED"
                mission.completed_at = test_clock["now"]
                first_mission = first_mission or mission
        db.add(
            Feedback(
                mission_id=first_mission.id,
                tester_id=first_mission.assignment.tester_id,
                app_id=launch["id"],
                launch_ok=True,
                core_feature_ok="PARTLY",
                issue_text="Dark mode contrast",
                suggestion_text="Rename the primary action button",
            )
        )
        db.commit()

    for description in (
        "Improved dark mode contrast based on tester feedback.",
        "Renamed the primary action button.",
    ):
        response = client.post(
            f"/apps/{launch['id']}/changes",
            headers=owner["headers"],
            json={"description": description},
        )
        assert response.status_code == 201

    before_report = client.get(f"/apps/{launch['id']}/dashboard", headers=owner["headers"]).json()
    assert before_report["status"] == "TESTING_COMPLETE"
    report_response = client.get(
        f"/apps/{launch['id']}/production-report", headers=owner["headers"]
    )
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["continuous_testers"] == 12
    assert report["completed_missions"] == 72
    assert report["feedback_count"] == 1
    assert report["common_issues"] == ["Dark mode contrast"]
    assert len(report["changes_recorded"]) == 2
    assert "does not guarantee" in report["approval_disclaimer"]
    draft = client.get(
        f"/apps/{launch['id']}/production-application-draft", headers=owner["headers"]
    ).json()
    assert draft["evidence_only"] is True
    assert "Dark mode contrast" in draft["feedback_received"]
    assert "Improved dark mode" in draft["changes_made"]
    ready = client.get(f"/apps/{launch['id']}/dashboard", headers=owner["headers"]).json()
    assert ready["status"] == "PRODUCTION_READY"

    empty = create_app(client, owner, suffix="empty")
    empty_draft = client.get(
        f"/apps/{empty['id']}/production-application-draft", headers=owner["headers"]
    ).json()
    assert empty_draft["how_testers_were_recruited"] == "Insufficient recorded evidence"
    assert empty_draft["feedback_received"] == "Insufficient recorded evidence"
    assert empty_draft["changes_made"] == "Insufficient recorded evidence"


def test_sqlite_data_survives_engine_restart(client):
    owner = register(client, 0)
    launch = create_app(client, owner, suffix="persistence")
    engine.dispose()
    with SessionLocal() as db:
        persisted = db.get(App, launch["id"])
        assert persisted is not None
        assert persisted.package_name == "com.launchcircle.phase1.persistence"


def test_phase1_full_matching_replacement_day14_acceptance(client, test_clock):
    """Repeatable A -> 15 testers -> Day 5 replacement -> Day 14 evidence workflow."""
    owner = register(client, 100, "Acceptance Developer A")
    testers = [register(client, index) for index in range(101, 117)]
    launch = create_app(client, owner, target=15, suffix="full_acceptance")
    matched = client.post(f"/apps/{launch['id']}/match-testers", headers=owner["headers"])
    assert matched.json()["assigned_now"] == 15
    rows = client.get(f"/apps/{launch['id']}/testers", headers=owner["headers"]).json()
    by_id = {tester["id"]: tester for tester in testers}
    for row in rows:
        activate(client, row, by_id[row["tester_id"]])

    # Day 5: preserve completed Day 1/3 evidence for 14 testers and let one go inactive.
    test_clock["now"] += timedelta(days=4)
    victim_id = rows[0]["id"]
    with SessionLocal() as db:
        assignments = list(db.scalars(select(AssignmentModel).where(AssignmentModel.app_id == launch["id"])))
        for assignment in assignments:
            if assignment.id == victim_id:
                continue
            assignment.last_activity_at = test_clock["now"]
            for mission in assignment.missions:
                if mission.scheduled_day <= 3:
                    mission.status = "COMPLETED"
                    mission.completed_at = test_clock["now"]
        db.commit()
    health = client.post(f"/apps/{launch['id']}/refresh-health", headers=owner["headers"])
    assert health.json()["replacements_assigned"] == 1
    after_health = client.get(f"/apps/{launch['id']}/testers", headers=owner["headers"]).json()
    replacement = next(row for row in after_health if row["is_replacement"])
    assert replacement["replacement_for_id"] == victim_id
    assert replacement["total_missions"] == 0
    activate(client, replacement, by_id[replacement["tester_id"]])

    # App Day 15 boundary (14 elapsed days): original healthy testers have full history;
    # the Day 5 replacement has only the missions genuinely available on their own clock.
    test_clock["now"] += timedelta(days=10)
    with SessionLocal() as db:
        assignments = list(db.scalars(select(AssignmentModel).where(AssignmentModel.app_id == launch["id"])))
        evidence_mission = None
        for assignment in assignments:
            if assignment.id == victim_id:
                continue
            assignment.health_status = "GOOD"
            assignment.last_activity_at = test_clock["now"]
            allowed_day = 11 if assignment.replacement_for_id else 14
            for mission in assignment.missions:
                if mission.scheduled_day <= allowed_day:
                    mission.status = "COMPLETED"
                    mission.completed_at = test_clock["now"]
                    evidence_mission = evidence_mission or mission
            if not assignment.replacement_for_id:
                assignment.status = "COMPLETED"
                assignment.completed_at = test_clock["now"]
        db.add(
            Feedback(
                mission_id=evidence_mission.id,
                tester_id=evidence_mission.assignment.tester_id,
                app_id=launch["id"],
                launch_ok=True,
                core_feature_ok="PARTLY",
                issue_text="Dark mode contrast",
                suggestion_text="Clarify primary action wording",
            )
        )
        db.commit()

    for description in (
        "Improved dark mode contrast based on tester feedback.",
        "Renamed the primary action button.",
    ):
        assert client.post(
            f"/apps/{launch['id']}/changes",
            headers=owner["headers"],
            json={"description": description},
        ).status_code == 201
    before = client.get(f"/apps/{launch['id']}/dashboard", headers=owner["headers"]).json()
    assert before["status"] == "TESTING_COMPLETE"
    assert before["continuous_qualifying_testers"] == 14
    assert before["replacement_testers"] == 1
    report = client.get(f"/apps/{launch['id']}/production-report", headers=owner["headers"]).json()
    assert report["replacements"] == 1
    assert report["continuous_testers"] == 14
    assert report["common_issues"] == ["Dark mode contrast"]
    assert report["changes_recorded"] == [
        "Improved dark mode contrast based on tester feedback.",
        "Renamed the primary action button.",
    ]
    draft = client.get(
        f"/apps/{launch['id']}/production-application-draft", headers=owner["headers"]
    ).json()
    assert draft["evidence_only"] is True
    assert "Dark mode contrast" in draft["feedback_received"]
    assert client.get(
        f"/apps/{launch['id']}/dashboard", headers=owner["headers"]
    ).json()["status"] == "PRODUCTION_READY"


def test_dropped_tester_assigns_fresh_replacement(client, test_clock):
    owner = register(client, 200)
    first = register(client, 201)
    spare = register(client, 202)
    launch = create_app(client, owner, target=1, suffix="drop_replacement")
    assert client.post(
        f"/apps/{launch['id']}/match-testers", headers=owner["headers"]
    ).json()["assigned_now"] == 1
    original = client.get(f"/apps/{launch['id']}/testers", headers=owner["headers"]).json()[0]
    users = {first["id"]: first, spare["id"]: spare}
    activate(client, original, users[original["tester_id"]])
    dropped = client.patch(
        f"/assignments/{original['id']}/drop",
        headers=users[original["tester_id"]]["headers"],
        json={"reason": "Unable to continue"},
    )
    assert dropped.status_code == 200
    rows = client.get(f"/apps/{launch['id']}/testers", headers=owner["headers"]).json()
    replacement = next(row for row in rows if row["is_replacement"])
    assert replacement["tester_id"] != original["tester_id"]
    assert replacement["replacement_for_id"] == original["id"]
    assert replacement["status"] == "ASSIGNED"
    assert replacement["completed_missions"] == 0
    assert replacement["total_missions"] == 0
