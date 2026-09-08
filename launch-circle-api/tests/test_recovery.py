from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app as fastapi_app
from app.models.launch import App, CircleMember, TesterAssignment
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


def create_app(client: TestClient, owner: dict, suffix: str, target: int = 12) -> dict:
    response = client.post(
        "/apps",
        headers=owner["headers"],
        json={
            "name": f"Recovery App {suffix}",
            "package_name": f"com.example.recovery{suffix}",
            "opt_in_url": f"https://play.google.com/apps/testing/com.example.recovery{suffix}",
            "tester_target": target,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def build_cycle(
    client: TestClient,
    now: datetime,
    *,
    member_count: int = 14,
) -> tuple[dict, dict, list[dict], list[dict]]:
    owner = register(client, f"recovery-owner-{member_count}@example.com", "Owner")
    members = [
        register(
            client,
            f"recovery-{member_count}-{index}@example.com",
            f"Tester {index}",
        )
        for index in range(member_count)
    ]
    for member in members:
        join_circle(client, owner, member)
    app = create_app(client, owner, str(member_count))
    matched = client.post(f"/apps/{app['id']}/match-testers", headers=owner["headers"])
    assert matched.status_code == 200, matched.text
    rows = client.get(f"/apps/{app['id']}/testers", headers=owner["headers"])
    assert rows.status_code == 200, rows.text
    assignments = rows.json()
    assert len(assignments) == 12
    member_by_id = {member["id"]: member for member in members}
    for row in assignments:
        tester = member_by_id[row["tester_id"]]
        assert client.patch(
            f"/assignments/{row['id']}/opt-in", headers=tester["headers"]
        ).status_code == 200
        installed = client.patch(
            f"/assignments/{row['id']}/installed", headers=tester["headers"]
        )
        assert installed.status_code == 200, installed.text
    return owner, app, members, assignments


def set_clock(now: datetime):
    fastapi_app.dependency_overrides[get_now] = lambda: now


def clear_clock():
    fastapi_app.dependency_overrides.pop(get_now, None)


def test_health_states_are_server_evaluated_and_deterministic(client):
    now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    set_clock(now)
    try:
        owner = register(client, "health-owner@example.com", "Owner")
        member = register(client, "health-member@example.com", "Member")
        join_circle(client, owner, member)
        app = create_app(client, owner, "states", target=1)
        matched = client.post(f"/apps/{app['id']}/match-testers", headers=owner["headers"])
        assert matched.status_code == 200
        row = client.get(f"/apps/{app['id']}/testers", headers=owner["headers"]).json()[0]
        client.patch(f"/assignments/{row['id']}/opt-in", headers=member["headers"])
        client.patch(f"/assignments/{row['id']}/installed", headers=member["headers"])
        with SessionLocal() as db:
            saved = db.get(TesterAssignment, row["id"])
            assert saved is not None
            saved.last_activity_at = now - timedelta(days=2)
            saved.health_status = "GOOD"
            db.commit()
        attention = client.get(f"/apps/{app['id']}/testers", headers=owner["headers"]).json()[0]
        assert attention["participation_state"] == "NEEDS_ATTENTION"
        with SessionLocal() as db:
            saved = db.get(TesterAssignment, row["id"])
            assert saved is not None
            saved.last_activity_at = now - timedelta(days=4)
            saved.health_status = "GOOD"
            db.commit()
        inactive = client.get(f"/apps/{app['id']}/testers", headers=owner["headers"]).json()[0]
        assert inactive["participation_state"] == "INACTIVE"
    finally:
        clear_clock()


def test_dropout_assigns_one_same_circle_replacement_once_and_restores_coverage(client):
    now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    set_clock(now)
    try:
        owner, app, members, assignments = build_cycle(client, now, member_count=14)
        original_id = assignments[0]["id"]
        original_tester_id = assignments[0]["tester_id"]
        outsider = register(client, "recovery-outsider@example.com", "Outsider")
        with SessionLocal() as db:
            original = db.get(TesterAssignment, original_id)
            assert original is not None
            original.last_activity_at = now - timedelta(days=4)
            original.health_status = "GOOD"
            db.commit()

        first = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"])
        assert first.status_code == 200, first.text
        data = first.json()
        assert data["status"] == "AT_RISK"
        assert data["qualifying_tester_count"] == 11
        assert data["coverage_shortage"] == 1
        assert data["replacement_status"] == "REPLACEMENT_ASSIGNED"
        assert data["replacement_testers"] == 1

        with SessionLocal() as db:
            saved = db.get(App, app["id"])
            assert saved is not None
            original = db.get(TesterAssignment, original_id)
            replacements = [
                row for row in saved.assignments if row.replacement_for_id == original_id
            ]
            assert original is not None
            assert original.tester_id == original_tester_id
            assert original.health_status == "INACTIVE"
            assert len(replacements) == 1
            replacement = replacements[0]
            replacement_tester = db.scalar(
                select(CircleMember).where(
                    CircleMember.circle_id == saved.circle_id,
                    CircleMember.user_id == replacement.tester_id,
                )
            )
            assert replacement_tester is not None
            assert replacement_tester.circle_id == saved.circle_id
            assert replacement.tester_id != owner["id"]
            assert replacement.tester_id != outsider["id"]
            replacement_id = replacement.id
            replacement_tester_id = replacement.tester_id

        repeated = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"])
        assert repeated.json()["replacement_testers"] == 1
        with SessionLocal() as db:
            assert len(
                list(
                    db.scalars(
                        select(TesterAssignment).where(
                            TesterAssignment.app_id == app["id"],
                            TesterAssignment.replacement_for_id == original_id,
                        )
                    )
                )
            ) == 1

        member_by_id = {member["id"]: member for member in members}
        completed = client.post(
            f"/test-assignments/{replacement_id}/complete",
            headers=member_by_id[replacement_tester_id]["headers"],
        )
        assert completed.status_code == 200, completed.text
        restored = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"]).json()
        assert restored["qualifying_tester_count"] == 12
        assert restored["coverage_shortage"] == 0
        assert restored["replacement_status"] == "COVERAGE_RESTORED"
        assert restored["status"] == "TESTING"
    finally:
        clear_clock()


def test_replacement_respects_daily_limit_and_no_candidate_is_truthfully_at_risk(client):
    now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    set_clock(now)
    try:
        owner, app, members, assignments = build_cycle(client, now, member_count=13)
        spare = next(member for member in members if member["id"] not in {row["tester_id"] for row in assignments})
        other_one = create_app(client, owner, "workloadone", target=1)
        other_two = create_app(client, owner, "workloadtwo", target=1)
        with SessionLocal() as db:
            for other_app in (other_one, other_two):
                db.add(
                    TesterAssignment(
                        app_id=other_app["id"],
                        circle_id=app["circle_id"],
                        tester_id=spare["id"],
                        assignment_day=date(2026, 8, 20),
                        test_type="APP_CHECK",
                        status="ASSIGNED",
                        assigned_at=now,
                    )
                )
            original = db.get(TesterAssignment, assignments[0]["id"])
            assert original is not None
            original.last_activity_at = now - timedelta(days=4)
            original.health_status = "GOOD"
            db.commit()
        data = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"]).json()
        assert data["coverage_shortage"] == 1
        assert data["replacement_testers"] == 0
        assert data["replacement_status"] == "COVERAGE_AT_RISK"
        assert "1 qualifying tester" in data["risk_reason"]
        with SessionLocal() as db:
            replacements = list(
                db.scalars(
                    select(TesterAssignment).where(
                        TesterAssignment.app_id == app["id"],
                        TesterAssignment.replacement_for_id.is_not(None),
                    )
                )
            )
            assert replacements == []
    finally:
        clear_clock()


def test_leaving_member_drops_participation_and_triggers_replacement(client):
    now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    set_clock(now)
    try:
        owner, app, members, assignments = build_cycle(client, now, member_count=14)
        leaving = next(member for member in members if member["id"] == assignments[0]["tester_id"])
        response = client.post(
            f"/circles/{app['circle_id']}/leave", headers=leaving["headers"]
        )
        assert response.status_code == 200, response.text
        assert any(
            row["user_id"] == leaving["id"] and row["status"] == "LEFT"
            for row in response.json()["members"]
        )
        with SessionLocal() as db:
            original = db.get(TesterAssignment, assignments[0]["id"])
            assert original is not None
            assert original.status == "DROPPED"
            replacements = list(
                db.scalars(
                    select(TesterAssignment).where(
                        TesterAssignment.app_id == app["id"],
                        TesterAssignment.replacement_for_id == original.id,
                    )
                )
            )
            assert len(replacements) == 1
            assert replacements[0].tester_id != leaving["id"]
    finally:
        clear_clock()


def test_day_fourteen_with_unresolved_shortage_stays_at_risk_and_keeps_start(client):
    now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    set_clock(now)
    try:
        owner, app, members, assignments = build_cycle(client, now, member_count=12)
        with SessionLocal() as db:
            original = db.get(TesterAssignment, assignments[0]["id"])
            assert original is not None
            original.last_activity_at = now - timedelta(days=4)
            original.health_status = "GOOD"
            for row in db.scalars(select(TesterAssignment).where(TesterAssignment.app_id == app["id"])).all():
                if row.id != original.id:
                    row.last_activity_at = now
                    row.health_status = "GOOD"
            saved = db.get(App, app["id"])
            assert saved is not None and saved.testing_start_at is not None
            started_at = saved.testing_start_at
            db.commit()
        end = now + timedelta(days=14)
        set_clock(end)
        with SessionLocal() as db:
            saved = db.get(App, app["id"])
            assert saved is not None
            for row in saved.assignments:
                if row.id != assignments[0]["id"]:
                    row.last_activity_at = end
                    row.health_status = "GOOD"
                    for mission in row.missions:
                        mission.status = "COMPLETED"
                        mission.completed_at = end
            db.commit()
        data = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"]).json()
        assert data["status"] == "AT_RISK"
        assert data["internally_production_ready"] is False
        assert data["coverage_shortage"] == 1
        with SessionLocal() as db:
            saved = db.get(App, app["id"])
            assert saved is not None
            assert saved.testing_start_at.replace(tzinfo=timezone.utc) == started_at.replace(tzinfo=timezone.utc)
    finally:
        clear_clock()
