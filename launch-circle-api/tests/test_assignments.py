from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app as fastapi_app
from app.models.launch import CircleMember, TesterAssignment as DbTesterAssignment
from app.services.clock import get_now


def register(client: TestClient, email: str, name: str) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password",
            "display_name": name,
            "country": "CA",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    profile = client.get("/me", headers={"Authorization": f"Bearer {token}"}).json()
    return {
        "id": profile["id"],
        "email": email,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def create_app(client: TestClient, owner: dict, suffix: str) -> dict:
    package_suffix = suffix.replace("-", "")
    response = client.post(
        "/apps",
        headers=owner["headers"],
        json={
            "name": f"Assignment App {suffix}",
            "package_name": f"com.example.assignment{package_suffix}",
            "opt_in_url": f"https://play.google.com/apps/testing/com.example.assignment{package_suffix}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def join_circle(client: TestClient, owner: dict, member: dict) -> None:
    invite = client.post(
        "/invites",
        headers=owner["headers"],
        json={"invited_email": member["email"]},
    )
    assert invite.status_code == 201, invite.text
    accepted = client.post(
        f"/invites/{invite.json()['invite_code']}/accept",
        headers=member["headers"],
    )
    assert accepted.status_code == 200, accepted.text


def today(client: TestClient, user: dict) -> list[dict]:
    response = client.get("/test-assignments/today", headers=user["headers"])
    assert response.status_code == 200, response.text
    return response.json()


def test_active_member_receives_persisted_assignment_and_outsider_does_not(client):
    owner = register(client, "assignment-owner@example.com", "Owner")
    member = register(client, "assignment-member@example.com", "Member")
    outsider = register(client, "assignment-outsider@example.com", "Outsider")
    join_circle(client, owner, member)
    app = create_app(client, owner, "active")

    assignments = today(client, member)
    assert len(assignments) == 1
    assert assignments[0]["app_id"] == app["id"]
    assert assignments[0]["circle_id"] == app["circle_id"]
    assert assignments[0]["status"] == "ASSIGNED"

    with SessionLocal() as db:
        row = db.scalar(select(DbTesterAssignment).where(DbTesterAssignment.id == assignments[0]["id"]))
        assert row is not None
        assert row.tester_id == member["id"]
        assert row.assignment_day == date.fromisoformat(assignments[0]["assignment_day"])

    assert today(client, outsider) == []


def test_left_member_and_owner_never_receive_new_assignment(client):
    owner = register(client, "assignment-left-owner@example.com", "Owner")
    left = register(client, "assignment-left@example.com", "Left")
    join_circle(client, owner, left)
    app = create_app(client, owner, "left")

    with SessionLocal() as db:
        member = db.scalar(
            select(CircleMember).where(
                CircleMember.circle_id == app["circle_id"],
                CircleMember.user_id == left["id"],
            )
        )
        assert member is not None
        member.status = "LEFT"
        db.commit()

    assert today(client, left) == []
    assert today(client, owner) == []


def test_daily_limit_and_refresh_are_idempotent(client):
    owner = register(client, "assignment-limit-owner@example.com", "Owner")
    member = register(client, "assignment-limit-member@example.com", "Member")
    join_circle(client, owner, member)
    apps = [create_app(client, owner, str(index)) for index in range(3)]

    first = today(client, member)
    second = today(client, member)
    assert len(first) == 2
    assert [item["id"] for item in second] == [item["id"] for item in first]

    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(DbTesterAssignment).where(
                    DbTesterAssignment.tester_id == member["id"],
                    DbTesterAssignment.assignment_day == date.fromisoformat(first[0]["assignment_day"]),
                )
            )
        )
        assert len(rows) == 2
        assert {row.app_id for row in rows} == {app["id"] for app in apps[:2]}


def test_completion_is_persisted_authorized_and_idempotent(client):
    owner = register(client, "assignment-complete-owner@example.com", "Owner")
    member = register(client, "assignment-complete-member@example.com", "Member")
    other = register(client, "assignment-complete-other@example.com", "Other")
    join_circle(client, owner, member)
    join_circle(client, owner, other)
    create_app(client, owner, "complete")
    assignment = today(client, member)[0]

    forbidden = client.post(
        f"/test-assignments/{assignment['id']}/complete",
        headers=other["headers"],
    )
    assert forbidden.status_code == 403

    completed = client.post(
        f"/test-assignments/{assignment['id']}/complete",
        headers=member["headers"],
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["completed_at"] is not None

    repeated = client.post(
        f"/test-assignments/{assignment['id']}/complete",
        headers=member["headers"],
    )
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "COMPLETED"

    with SessionLocal() as db:
        row = db.get(DbTesterAssignment, assignment["id"])
        assert row is not None
        assert row.status == "COMPLETED"
        assert row.completed_at is not None


def test_assignments_stay_in_app_circle_and_coverage_is_real(client):
    owner = register(client, "assignment-scope-owner@example.com", "Owner")
    member = register(client, "assignment-scope-member@example.com", "Member")
    other_owner = register(client, "assignment-scope-other@example.com", "Other Owner")
    other_member = register(client, "assignment-scope-other-member@example.com", "Other Member")
    join_circle(client, owner, member)
    join_circle(client, other_owner, other_member)
    own_app = create_app(client, owner, "scope-own")
    other_app = create_app(client, other_owner, "scope-other")

    assignments = today(client, member)
    assert [row["app_id"] for row in assignments] == [own_app["id"]]
    assert other_app["id"] not in {row["app_id"] for row in assignments}

    coverage = client.get(
        f"/apps/{own_app['id']}/assignment-coverage",
        headers=owner["headers"],
    )
    assert coverage.status_code == 200
    assert coverage.json() == {
        "app_id": own_app["id"],
        "assignment_count": 1,
        "completed_count": 0,
        "participating_members": 1,
    }


def test_fairness_prefers_available_member_and_fifteen_member_circle_is_supported(client):
    owner = register(client, "assignment-fair-owner@example.com", "Owner")
    members = [
        register(client, f"assignment-fair-{index}@example.com", f"Member {index}")
        for index in range(14)
    ]
    for member in members:
        join_circle(client, owner, member)
    app = create_app(client, owner, "fair")

    # A prior assignment makes the first member less preferred for this app.
    with SessionLocal() as db:
        db.add(
                DbTesterAssignment(
                app_id=app["id"],
                circle_id=app["circle_id"],
                tester_id=members[0]["id"],
                assignment_day=date(2026, 8, 19),
                test_type="APP_CHECK",
                assigned_at=datetime(2026, 8, 19, tzinfo=timezone.utc),
                status="ASSIGNED",
            )
        )
        db.commit()

    fixed_now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    fastapi_app.dependency_overrides[get_now] = lambda: fixed_now
    try:
        first = today(client, members[0])
        second = today(client, members[1])
    finally:
        fastapi_app.dependency_overrides.pop(get_now, None)

    assert len(first) <= 1
    assert len(second) == 1
    assert second[0]["app_id"] == app["id"]

    with SessionLocal() as db:
        active_members = db.scalars(
            select(CircleMember).where(
                CircleMember.circle_id == app["circle_id"], CircleMember.status == "ACTIVE"
            )
        )
        assert len(list(active_members)) == 15
