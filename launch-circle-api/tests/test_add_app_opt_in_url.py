import pytest

APP_ICON = "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGPUjTrBwMDAxMDAwMDAAAAPQwFTH4I6DQAAAABJRU5ErkJggg=="


def register(client, email: str) -> dict:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "strong-password", "display_name": "Developer"},
    )
    assert response.status_code == 201, response.text
    return {"headers": {"Authorization": f"Bearer {response.json()['access_token']}"}}


def create_app(client, owner: dict, package_name: str, ownership_authorized: bool = True):
    return client.post(
        "/apps",
        headers=owner["headers"],
        json={
            "name": "Link normalization test",
            "package_name": package_name,
            "opt_in_url": f"https://play.google.com/apps/testing/{package_name}",
            "icon_data": APP_ICON,
            "ownership_authorized": ownership_authorized,
            "core_workflow_steps": ["Open the app", "Try the main feature"],
        },
    )


def test_create_app_persists_canonical_opt_in_url_and_keeps_duplicate_guard(client):
    owner = register(client, "link-owner@example.com")
    duplicate_owner = register(client, "link-duplicate@example.com")
    package_name = "com.esim.checker"
    expected_url = "https://play.google.com/apps/testing/com.esim.checker"

    created = create_app(client, owner, package_name)
    assert created.status_code == 201, created.text
    assert created.json()["ownership_authorized"] is True
    assert created.json()["ownership_attested_at"]
    assert created.json()["ownership_attestation_status"] == "CONFIRMED"
    assert created.json()["package_name"] == package_name
    assert created.json()["opt_in_url"] == expected_url

    duplicate = create_app(client, duplicate_owner, package_name)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Package name is already registered"


def test_legacy_app_create_without_owner_declaration_is_saved_but_gated(client):
    owner = register(client, "attestation-owner@example.com")
    request = {
        "name": "Legacy client app",
        "package_name": "com.example.legacyattestation",
        "opt_in_url": "https://play.google.com/apps/testing/com.example.legacyattestation",
        "icon_data": APP_ICON,
        "core_workflow_steps": ["Open the app", "Try its main feature"],
    }
    response = client.post("/apps", headers=owner["headers"], json=request)
    assert response.status_code == 201, response.text
    app = response.json()
    assert app["ownership_authorized"] is False
    assert app["ownership_attested_at"] is None
    assert app["ownership_attestation_status"] == "PENDING_ATTESTATION"
    assert app["status"] == "DRAFT"
    assert client.post(f"/apps/{app['id']}/google-group/confirm", headers=owner["headers"], json={"configured": True}).status_code == 200
    assert client.get(f"/apps/{app['id']}/app-groups", headers=owner["headers"]).status_code == 409

    denied = client.post(
        f"/apps/{app['id']}/ownership-attestation",
        headers=owner["headers"], json={"confirmed": False},
    )
    assert denied.status_code == 422
    confirmed = client.post(
        f"/apps/{app['id']}/ownership-attestation",
        headers=owner["headers"], json={"confirmed": True},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["ownership_authorized"] is True
    assert confirmed.json()["ownership_attested_at"]
    assert confirmed.json()["ownership_attestation_status"] == "CONFIRMED"
    assert confirmed.json()["status"] == "WAITING_FOR_TESTERS"
    assert client.get(f"/apps/{app['id']}/app-groups", headers=owner["headers"]).status_code == 200
    replay = client.post(
        f"/apps/{app['id']}/ownership-attestation",
        headers=owner["headers"], json={"confirmed": True},
    )
    assert replay.json()["ownership_attested_at"] == confirmed.json()["ownership_attested_at"]


def test_missing_owner_declaration_cannot_join_or_dispatch(client):
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.api.pool import accept_app
    from app.core.database import SessionLocal
    from app.models.launch import App, CircleMember
    from app.models.pool import AppGroup, AppGroupApp, AppGroupMember, PoolListing
    from app.models.user import User
    from app.services.matching import match_testers
    from fastapi import HTTPException
    from tests.test_shared_pool import actor, campaign

    owner, tester = actor(), actor()
    app_id = campaign(owner)
    with SessionLocal() as db:
        app = db.get(App, app_id)
        app.ownership_authorized = False
        app.ownership_attested_at = None
        group = AppGroup(id=str(uuid4()), name="Pending owner statement", status="OPEN", created_at=datetime.now(UTC))
        db.add(group)
        db.flush()
        db.add_all([
            AppGroupApp(app_id=app.id, group_id=group.id),
            AppGroupMember(group_id=group.id, user_id=owner[0], joined_at=datetime.now(UTC)),
            AppGroupMember(group_id=group.id, user_id=tester[0], joined_at=datetime.now(UTC)),
            PoolListing(app_id=app.id, enabled=True, updated_at=datetime.now(UTC)),
            CircleMember(
                circle_id=app.circle_id,
                user_id=tester[0],
                role="MEMBER",
                status="ACTIVE",
                joined_at=datetime.now(UTC),
            ),
        ])
        db.commit()
        assert match_testers(db, db.get(App, app_id)) == []
        with pytest.raises(HTTPException) as denied:
            accept_app(app_id, db.get(User, tester[0]), db, datetime.now(UTC))
        assert denied.value.status_code == 404
        db.rollback()
    admin_manual = client.post(
        f"/apps/{app_id}/assign/{tester[0]}", headers=owner[1],
    )
    assert admin_manual.status_code == 409
    assert admin_manual.json()["detail"] == "APP_OWNER_ATTESTATION_REQUIRED"
