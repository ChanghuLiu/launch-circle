from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal, engine
from app.main import app as fastapi_app
from app.models.launch import App, CircleMember
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
    return {"id": profile["id"], "email": email, "headers": {"Authorization": f"Bearer {token}"}}


def join_circle(client: TestClient, owner: dict, member: dict) -> None:
    invite = client.post(
        "/invites", headers=owner["headers"], json={"invited_email": member["email"]}
    )
    assert invite.status_code == 201, invite.text
    accepted = client.post(
        f"/invites/{invite.json()['invite_code']}/accept", headers=member["headers"]
    )
    assert accepted.status_code == 200, accepted.text


def create_app(client: TestClient, owner: dict, suffix: str) -> dict:
    response = client.post(
        "/apps",
        headers=owner["headers"],
        json={
            "name": f"Lifecycle App {suffix}",
            "package_name": f"com.example.lifecycle{suffix}",
            "opt_in_url": f"https://play.google.com/apps/testing/com.example.lifecycle{suffix}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def build_started_app(client: TestClient, total_circle_members: int = 13) -> tuple[dict, dict, list[dict]]:
    owner = register(client, f"lifecycle-owner-{total_circle_members}@example.com", "Owner")
    members = [
        register(client, f"lifecycle-{total_circle_members}-{index}@example.com", f"Tester {index}")
        for index in range(total_circle_members - 1)
    ]
    for member in members:
        join_circle(client, owner, member)
    app = create_app(client, owner, str(total_circle_members))
    matched = client.post(f"/apps/{app['id']}/match-testers", headers=owner["headers"])
    assert matched.status_code == 200, matched.text
    rows = client.get(f"/apps/{app['id']}/testers", headers=owner["headers"]).json()
    by_id = {member["id"]: member for member in members}
    for row in rows:
        tester = by_id[row["tester_id"]]
        assert client.patch(f"/assignments/{row['id']}/opt-in", headers=tester["headers"]).status_code == 200
        installed = client.patch(f"/assignments/{row['id']}/installed", headers=tester["headers"])
        assert installed.status_code == 200, installed.text
    assert len(rows) == total_circle_members - 1
    return owner, app, members


@pytest.fixture
def lifecycle_clock():
    state = {"now": datetime(2026, 8, 20, 12, tzinfo=timezone.utc)}
    fastapi_app.dependency_overrides[get_now] = lambda: state["now"]
    yield state
    fastapi_app.dependency_overrides.pop(get_now, None)


def test_eleven_qualifying_testers_wait_and_unrelated_circle_does_not_help(client, lifecycle_clock):
    owner = register(client, "lifecycle-eleven-owner@example.com", "Owner")
    members = [register(client, f"lifecycle-eleven-{index}@example.com", f"Tester {index}") for index in range(11)]
    for member in members:
        join_circle(client, owner, member)
    app = create_app(client, owner, "eleven")
    assert client.post(f"/apps/{app['id']}/match-testers", headers=owner["headers"]).json()["assigned_now"] == 11
    rows = client.get(f"/apps/{app['id']}/testers", headers=owner["headers"]).json()
    by_id = {member["id"]: member for member in members}
    for row in rows:
        tester = by_id[row["tester_id"]]
        client.patch(f"/assignments/{row['id']}/opt-in", headers=tester["headers"])
        client.patch(f"/assignments/{row['id']}/installed", headers=tester["headers"])
    data = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"]).json()
    assert data["status"] == "WAITING_FOR_TESTERS"
    assert data["testing_started_at"] is None
    assert data["qualifying_tester_count"] == 11
    assert data["day"] == 0

    other_owner = register(client, "lifecycle-other-owner@example.com", "Other Owner")
    other_member = register(client, "lifecycle-other-member@example.com", "Other Member")
    join_circle(client, other_owner, other_member)
    other_app = create_app(client, other_owner, "other")
    assert other_app["circle_id"] != app["circle_id"]
    assert data["testing_started_at"] is None


@pytest.mark.parametrize("total_circle_members", [13, 14, 15])
def test_twelve_or_more_qualifying_testers_start_once(client, lifecycle_clock, total_circle_members):
    owner, app, _members = build_started_app(client, total_circle_members)
    data = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"]).json()
    assert data["status"] == "TESTING"
    assert data["qualifying_tester_count"] == total_circle_members - 1
    assert data["required_tester_count"] == 12
    assert data["day"] == 1
    assert data["days_remaining"] == 14
    assert data["testing_started_at"] == "2026-08-20T12:00:00Z"
    assert data["testing_target_end_at"] == "2026-09-03T12:00:00Z"
    repeated = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"])
    assert repeated.json()["testing_started_at"] == data["testing_started_at"]


def test_elapsed_day_boundaries_and_completion_are_server_controlled(client, lifecycle_clock):
    owner, app, _members = build_started_app(client)
    start = lifecycle_clock["now"]

    def record_normal_participation():
        with SessionLocal() as db:
            saved = db.get(App, app["id"])
            assert saved is not None
            for assignment in saved.assignments:
                assignment.last_activity_at = lifecycle_clock["now"]
                assignment.health_status = "GOOD"
                for mission in assignment.missions:
                    mission.status = "COMPLETED"
                    mission.completed_at = lifecycle_clock["now"]
            db.commit()

    lifecycle_clock["now"] = start + timedelta(hours=23, minutes=59)
    record_normal_participation()
    day_one = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"]).json()
    assert day_one["day"] == 1
    lifecycle_clock["now"] = start + timedelta(days=1)
    record_normal_participation()
    day_two = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"]).json()
    assert day_two["day"] == 2
    assert day_two["days_remaining"] == 13
    lifecycle_clock["now"] = start + timedelta(days=13)
    record_normal_participation()
    day_fourteen = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"]).json()
    assert day_fourteen["day"] == 14
    assert day_fourteen["days_remaining"] == 1
    assert day_fourteen["status"] == "TESTING"
    lifecycle_clock["now"] = start + timedelta(days=14)
    record_normal_participation()
    complete = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"]).json()
    assert complete["day"] == 14
    assert complete["days_remaining"] == 0
    assert complete["status"] == "TESTING_COMPLETE"
    assert complete["internally_production_ready"] is False
    with SessionLocal() as db:
        saved = db.get(App, app["id"])
        assert saved is not None
        assert saved.testing_start_at.replace(tzinfo=timezone.utc) == start
        assert saved.testing_completed_at.replace(tzinfo=timezone.utc) == lifecycle_clock["now"]


def test_owner_cannot_write_lifecycle_fields_and_reload_preserves_start(client, lifecycle_clock):
    owner, app, _members = build_started_app(client)
    original = client.get(f"/apps/{app['id']}", headers=owner["headers"]).json()
    attempted = client.patch(
        f"/apps/{app['id']}",
        headers=owner["headers"],
        json={"status": "PRODUCTION_READY", "testing_start_at": "2000-01-01T00:00:00Z", "testing_end_at": "2000-01-15T00:00:00Z"},
    )
    assert attempted.status_code == 200
    assert attempted.json()["status"] == original["status"]
    assert attempted.json()["testing_start_at"] == original["testing_start_at"]
    engine.dispose()
    with SessionLocal() as db:
        saved = db.get(App, app["id"])
        assert saved is not None
        assert saved.testing_start_at.replace(tzinfo=timezone.utc) == lifecycle_clock["now"]


def test_below_twelve_at_day_fourteen_is_not_production_ready(client, lifecycle_clock):
    owner, app, members = build_started_app(client)
    with SessionLocal() as db:
        member = db.scalar(select(CircleMember).where(CircleMember.circle_id == app["circle_id"], CircleMember.user_id == members[0]["id"]))
        assert member is not None
        member.status = "LEFT"
        db.commit()
    lifecycle_clock["now"] += timedelta(days=14)
    with SessionLocal() as db:
        saved = db.get(App, app["id"])
        assert saved is not None
        for assignment in saved.assignments:
            if assignment.tester_id != members[0]["id"]:
                assignment.last_activity_at = lifecycle_clock["now"]
                assignment.health_status = "GOOD"
                for mission in assignment.missions:
                    mission.status = "COMPLETED"
                    mission.completed_at = lifecycle_clock["now"]
        db.commit()
    data = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"]).json()
    assert data["status"] == "AT_RISK"
    assert data["qualifying_tester_count"] == 11
    assert data["internally_production_ready"] is False


def test_client_supplied_date_cannot_advance_lifecycle(client, lifecycle_clock):
    owner, app, _members = build_started_app(client)
    original = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"]).json()
    fake_date = client.get(f"/apps/{app['id']}/dashboard?now=2099-01-01T00:00:00Z", headers=owner["headers"])
    assert fake_date.status_code == 200
    assert fake_date.json()["testing_started_at"] == original["testing_started_at"]
    assert fake_date.json()["day"] == original["day"]
