from datetime import date, datetime, timezone
import hashlib

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app as fastapi_app
from app.models.launch import CircleMember, TesterAssignment as DbTesterAssignment
from app.services.clock import get_now


def play_account_id_for_test(owner: dict, suffix: str) -> str:
    digest = hashlib.sha256(f"{owner['id']}:{suffix}".encode()).digest()[:8]
    return str(int.from_bytes(digest, "big"))


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
    result = {
        "id": profile["id"],
        "email": email,
        "headers": {"Authorization": f"Bearer {token}"},
    }
    # Existing scenario explicitly starts with a synthetic confirmed Play account.
    confirmed = client.put("/tester-group-access", headers=result["headers"], json={"status": "SELF_CONFIRMED", "play_email": email})
    assert confirmed.status_code == 200, confirmed.text
    return result


def create_app(client: TestClient, owner: dict, suffix: str) -> dict:
    package_suffix = suffix.replace("-", "")
    response = client.post(
        "/apps",
        headers=owner["headers"],
        json={"ownership_authorized": True, "icon_data": 'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGPUjTrBwMDAxMDAwMDAAAAPQwFTH4I6DQAAAABJRU5ErkJggg==',
            "name": f"Assignment App {suffix}",
            "package_name": f"com.example.assignment{package_suffix}",
            "opt_in_url": f"https://play.google.com/apps/testing/com.example.assignment{package_suffix}",
            "play_developer_account_id": play_account_id_for_test(owner, package_suffix),
        },
    )
    assert response.status_code == 201, response.text
    confirmed = client.post(
        f"/apps/{response.json()['id']}/google-group/confirm",
        headers=owner["headers"],
        json={"configured": True},
    )
    assert confirmed.status_code == 200, confirmed.text
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


def test_circle_membership_alone_does_not_authorize_an_assignment(client):
    owner = register(client, "assignment-owner@example.com", "Owner")
    member = register(client, "assignment-member@example.com", "Member")
    outsider = register(client, "assignment-outsider@example.com", "Outsider")
    join_circle(client, owner, member)
    app = create_app(client, owner, "active")

    assert today(client, member) == []
    assert today(client, outsider) == []
    with SessionLocal() as db:
        assert db.scalar(select(DbTesterAssignment.id).where(DbTesterAssignment.app_id == app["id"])) is None


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


def test_opening_tests_does_not_create_implicit_daily_assignments(client, monkeypatch):
    owner = register(client, "assignment-limit-owner@example.com", "Owner")
    member = register(client, "assignment-limit-member@example.com", "Member")
    join_circle(client, owner, member)
    monkeypatch.setattr("app.api.phase0.is_app_admin", lambda user: user.id == owner["id"])
    apps = [create_app(client, owner, str(index)) for index in range(3)]

    assert today(client, member) == []
    assert today(client, member) == []

    with SessionLocal() as db:
        rows = list(db.scalars(select(DbTesterAssignment).where(DbTesterAssignment.tester_id == member["id"])))
        assert rows == []


def test_completion_is_persisted_authorized_and_idempotent(client):
    owner = register(client, "assignment-complete-owner@example.com", "Owner")
    member = register(client, "assignment-complete-member@example.com", "Member")
    other = register(client, "assignment-complete-other@example.com", "Other")
    join_circle(client, owner, member)
    join_circle(client, owner, other)
    app = create_app(client, owner, "complete")
    from app.api.admin import RecruitmentUpdate, recruitment
    with SessionLocal() as db:
        recruitment(app["id"], RecruitmentUpdate(enabled=True, reason="Complete app setup for recruitment"), db, True)
    accepted = client.post(f"/apps/{app['id']}/tester-pool/accept", headers=member["headers"])
    assert accepted.status_code == 200, accepted.text
    assignment = today(client, member)[0]

    forbidden = client.post(
        f"/test-assignments/{assignment['id']}/complete",
        headers=other["headers"],
    )
    assert forbidden.status_code == 403

    blocked = client.post(f"/test-assignments/{assignment['id']}/complete", headers=member["headers"])
    assert blocked.status_code == 409
    with SessionLocal() as db:
        row = db.get(DbTesterAssignment, assignment["id"])
        assert row.status == "ASSIGNED"
        assert row.opted_in_at is None and row.installed_at is None and row.completed_at is None
        # Historical completion remains idempotently readable.
        row.status = "COMPLETED"
        row.completed_at = datetime.now(timezone.utc)
        db.commit()
    for _ in range(2):
        repeated = client.post(f"/test-assignments/{assignment['id']}/complete", headers=member["headers"])
        assert repeated.status_code == 200
        assert repeated.json()["status"] == "COMPLETED" and repeated.json()["completed_at"]


def test_assignments_stay_in_app_circle_and_coverage_is_real(client):
    owner = register(client, "assignment-scope-owner@example.com", "Owner")
    member = register(client, "assignment-scope-member@example.com", "Member")
    other_owner = register(client, "assignment-scope-other@example.com", "Other Owner")
    other_member = register(client, "assignment-scope-other-member@example.com", "Other Member")
    join_circle(client, owner, member)
    join_circle(client, other_owner, other_member)
    own_app = create_app(client, owner, "scope-own")
    other_app = create_app(client, other_owner, "scope-other")

    assert today(client, member) == []
    assert today(client, other_member) == []

    coverage = client.get(
        f"/apps/{own_app['id']}/assignment-coverage",
        headers=owner["headers"],
    )
    assert coverage.status_code == 200
    assert coverage.json() == {
        "app_id": own_app["id"],
        "assignment_count": 0,
        "completed_count": 0,
        "participating_members": 0,
    }


def test_fifteen_member_circle_does_not_implicitly_assign_its_members(client):
    owner = register(client, "assignment-fair-owner@example.com", "Owner")
    members = [
        register(client, f"assignment-fair-{index}@example.com", f"Member {index}")
        for index in range(14)
    ]
    for member in members:
        join_circle(client, owner, member)
    app = create_app(client, owner, "fair")

    assert all(today(client, member) == [] for member in members)

    with SessionLocal() as db:
        active_members = db.scalars(
            select(CircleMember).where(
                CircleMember.circle_id == app["circle_id"], CircleMember.status == "ACTIVE"
            )
        )
        assert len(list(active_members)) == 15
