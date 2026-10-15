from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app as fastapi_app
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


def create_circle_invite(client: TestClient, owner: dict, email: str | None = None) -> dict:
    response = client.post(
        "/invites",
        headers=owner["headers"],
        json={"invited_email": email} if email else {},
    )
    assert response.status_code == 201, response.text
    return response.json()


def accept(client: TestClient, invite: dict, member: dict):
    return client.post(
        f"/invites/{invite['invite_code']}/accept",
        headers=member["headers"],
    )


def test_owner_circle_persists_and_fifteen_active_members_are_capacity_bound(client):
    owner = register(client, "circle-owner@example.com", "Circle Owner")
    members = [
        register(client, f"circle-member-{index}@example.com", f"Member {index}")
        for index in range(1, 16)
    ]
    app_response = client.post(
        "/apps",
        headers=owner["headers"],
        json={
            "name": "Circle App",
            "package_name": "com.example.circleapp",
            "opt_in_url": "https://play.google.com/apps/testing/com.example.circleapp",
            "play_developer_account_id": "1000000000000000003",
        },
    )
    assert app_response.status_code == 201, app_response.text
    circle_id = app_response.json()["circle_id"]

    for member in members[:14]:
        invite = create_circle_invite(client, owner, member["email"])
        response = accept(client, invite, member)
        assert response.status_code == 200, response.text

    circle = client.get(f"/circles/{circle_id}", headers=owner["headers"])
    assert circle.status_code == 200
    assert circle.json()["active_member_count"] == 15
    assert len(circle.json()["members"]) == 15
    assert circle.json()["members"][0]["role"] == "OWNER"

    full_invite = create_circle_invite(client, owner, members[14]["email"])
    full = accept(client, full_invite, members[14])
    assert full.status_code == 409
    assert "full" in full.json()["detail"].lower()


def test_invite_rejects_self_reuse_and_expiry_and_acceptance_is_idempotent(client):
    owner = register(client, "invite-owner@example.com", "Owner")
    member = register(client, "invite-member@example.com", "Member")
    other = register(client, "invite-other@example.com", "Other")

    own_invite = create_circle_invite(client, owner)
    assert accept(client, own_invite, owner).status_code == 422

    invite = create_circle_invite(client, owner, member["email"])
    accepted = accept(client, invite, member)
    assert accepted.status_code == 200, accepted.text
    duplicate = accept(client, invite, member)
    assert duplicate.status_code == 200
    reused = accept(client, invite, other)
    assert reused.status_code == 409

    created_at = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    fastapi_app.dependency_overrides[get_now] = lambda: created_at
    try:
        expired_invite = create_circle_invite(client, owner, other["email"])
        fastapi_app.dependency_overrides[get_now] = lambda: created_at + timedelta(days=8)
        expired = accept(client, expired_invite, other)
        assert expired.status_code == 410
    finally:
        fastapi_app.dependency_overrides.pop(get_now, None)


def test_joined_member_can_create_an_app_in_shared_circle_with_fourteen_tester_target(client):
    owner = register(client, "shared-circle-owner@example.com", "Owner")
    member = register(client, "shared-circle-member@example.com", "Member")
    invite = create_circle_invite(client, owner, member["email"])
    accepted = accept(client, invite, member)
    assert accepted.status_code == 200, accepted.text
    circle_id = accepted.json()["circle_id"]

    member_circles = client.get("/circles", headers=member["headers"])
    assert member_circles.status_code == 200
    assert circle_id in {circle["id"] for circle in member_circles.json()}

    created = client.post(
        "/apps",
        headers=member["headers"],
        json={
            "name": "Shared Circle App",
            "package_name": "com.example.sharedcircleapp",
            "opt_in_url": "https://play.google.com/apps/testing/com.example.sharedcircleapp",
            "play_developer_account_id": "1000000000000000024",
            "circle_id": circle_id,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["circle_id"] == circle_id
    assert created.json()["tester_target"] == 14

    matched = client.post(
        f"/apps/{created.json()['id']}/match-testers",
        headers=member["headers"],
    )
    assert matched.status_code == 200, matched.text
    assert matched.json()["assigned_now"] == 1
    testers = client.get(
        f"/apps/{created.json()['id']}/testers",
        headers=member["headers"],
    )
    assert [row["tester_id"] for row in testers.json()] == [owner["id"]]

    outsider = register(client, "shared-circle-outsider@example.com", "Outsider")
    denied = client.post(
        "/apps",
        headers=outsider["headers"],
        json={
            "name": "Unauthorized Circle App",
            "package_name": "com.example.unauthorizedcircleapp",
            "opt_in_url": "https://play.google.com/apps/testing/com.example.unauthorizedcircleapp",
            "play_developer_account_id": "1000000000000000025",
            "circle_id": circle_id,
        },
    )
    assert denied.status_code == 403


def test_matching_only_uses_active_members_of_the_app_circle(client):
    owner = register(client, "matching-owner@example.com", "Owner")
    member = register(client, "matching-member@example.com", "Member")
    register(client, "matching-outsider@example.com", "Outsider")
    invite = create_circle_invite(client, owner, member["email"])
    assert accept(client, invite, member).status_code == 200

    app_response = client.post(
        "/apps",
        headers=owner["headers"],
        json={
            "name": "Matching App",
            "package_name": "com.example.matchingapp",
            "opt_in_url": "https://play.google.com/apps/testing/com.example.matchingapp",
            "play_developer_account_id": "1000000000000000004",
            "tester_target": 15,
        },
    )
    assert app_response.status_code == 201, app_response.text
    app_id = app_response.json()["id"]

    matched = client.post(f"/apps/{app_id}/match-testers", headers=owner["headers"])
    assert matched.status_code == 200
    assert matched.json()["assigned_now"] == 1
    rows = client.get(f"/apps/{app_id}/testers", headers=owner["headers"]).json()
    assert [row["tester_id"] for row in rows] == [member["id"]]
