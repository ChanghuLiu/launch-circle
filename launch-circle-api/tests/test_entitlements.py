from app.core.database import SessionLocal
from app.models.launch import App
from app.models.user import User
from app.api.phase0 import settings as phase0_settings
from app.services.google_play_billing import GooglePlayPackageNotOwned
from app.services.circles import ensure_owner_circle


def register(client, email: str, display_name: str) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password",
            "display_name": display_name,
            "country": "CA",
        },
    )
    assert response.status_code == 201, response.text
    tokens = response.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = client.get("/me", headers=headers)
    assert me.status_code == 200, me.text
    return {"id": me.json()["id"], "headers": headers}


def app_payload(package_name: str, developer_account_id: str) -> dict:
    return {
        "name": "Entitlement Test App",
        "package_name": package_name,
        "opt_in_url": f"https://play.google.com/apps/testing/{package_name}",
        "play_developer_account_id": developer_account_id,
    }


def create_app(client, owner: dict, package_name: str, developer_account_id: str):
    return client.post(
        "/apps",
        headers=owner["headers"],
        json=app_payload(package_name, developer_account_id),
    )

def test_first_app_free_is_anchored_to_developer_account_not_login_email(client):
    owner = register(client, "first@example.com", "First")
    created = create_app(
        client, owner, "com.example.firstfree", "1234567890123456789"
    )
    assert created.status_code == 201, created.text
    assert created.json()["entitlement_status"] == "FIRST_APP_FREE"
    assert created.json()["play_developer_account_id"] == "1234567890123456789"

    second_login = register(client, "second@example.com", "Second")
    denied = create_app(
        client, second_login, "com.example.secondfree", "1234567890123456789"
    )
    assert denied.status_code == 402
    assert "$1" in denied.json()["detail"]
    assert client.get("/apps", headers=second_login["headers"]).json() == []


def test_allowlisted_play_publisher_can_add_multiple_apps_without_additional_app_purchase(
    client, monkeypatch
):
    owner = register(client, "unlimited@example.com", "Unlimited Publisher")
    publisher_id = "8195223677488114201"
    monkeypatch.setattr(
        phase0_settings,
        "google_play_unlimited_developer_account_ids",
        publisher_id,
    )
    assert phase0_settings.has_unlimited_play_developer_account(publisher_id)

    first = create_app(client, owner, "com.example.publisherone", publisher_id)
    second = create_app(client, owner, "com.example.publishertwo", publisher_id)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["entitlement_status"] == "PUBLISHER_UNLIMITED"
    assert second.json()["entitlement_status"] == "PUBLISHER_UNLIMITED"
    assert first.json()["developer_account_unlimited"] is True
    assert second.json()["developer_account_unlimited"] is True
    assert len(client.get("/apps", headers=owner["headers"]).json()) == 2


def test_unlisted_play_publisher_still_has_additional_app_limit(client, monkeypatch):
    owner = register(client, "limited@example.com", "Limited Publisher")
    monkeypatch.setattr(
        phase0_settings,
        "google_play_unlimited_developer_account_ids",
        "8195223677488114201",
    )
    publisher_id = "9988776655443322110"
    first = create_app(client, owner, "com.example.firstlimited", publisher_id)
    second = create_app(client, owner, "com.example.secondlimited", publisher_id)

    assert first.status_code == 201, first.text
    assert first.json()["developer_account_unlimited"] is False
    assert second.status_code == 402, second.text


def test_first_free_claim_survives_app_removal(client):
    owner = register(client, "claim@example.com", "Claim")
    created = create_app(
        client, owner, "com.example.claimfree", "9876543210123456789"
    )
    assert created.status_code == 201, created.text
    app_id = created.json()["id"]

    with SessionLocal() as db:
        db.delete(db.get(App, app_id))
        db.commit()

    replacement_login = register(client, "replacement@example.com", "Replacement")
    denied = create_app(
        client, replacement_login, "com.example.afterdelete", "9876543210123456789"
    )
    assert denied.status_code == 402

def test_legacy_apps_are_linked_before_granting_a_new_free_app(client):
    owner = register(client, "legacy@example.com", "Legacy")
    with SessionLocal() as db:
        user = db.get(User, owner["id"])
        circle = ensure_owner_circle(db, user)
        db.add(
            App(
                owner_id=owner["id"],
                circle_id=circle.id,
                name="Existing App",
                package_name="com.example.legacy",
                opt_in_url="https://play.google.com/apps/testing/com.example.legacy",
            )
        )
        db.commit()

    denied = create_app(
        client, owner, "com.example.legacysecond", "1122334455667788990"
    )
    assert denied.status_code == 402

    apps = client.get("/apps", headers=owner["headers"]).json()
    legacy = next(item for item in apps if item["package_name"] == "com.example.legacy")
    assert legacy["play_developer_account_id"] == "1122334455667788990"
    assert legacy["entitlement_status"] == "LEGACY"


def test_production_first_app_requires_canonical_account_and_verified_package(
    client, monkeypatch
):
    owner = register(client, "publisher@example.com", "Publisher")
    monkeypatch.setattr(phase0_settings, "app_env", "production")
    monkeypatch.setattr(
        phase0_settings, "google_play_developer_account_id", "123456789"
    )

    wrong_account = create_app(
        client, owner, "com.example.wrongaccount", "987654321"
    )
    assert wrong_account.status_code == 403

    monkeypatch.setattr(
        "app.api.phase0.verify_app_package_ownership",
        lambda *_args: (_ for _ in ()).throw(GooglePlayPackageNotOwned()),
    )
    wrong_package = create_app(
        client, owner, "com.example.notowned", "123456789"
    )
    assert wrong_package.status_code == 403

    monkeypatch.setattr(
        "app.api.phase0.verify_app_package_ownership", lambda *_args: None
    )
    verified = create_app(
        client, owner, "com.example.verified", "123456789"
    )
    assert verified.status_code == 201, verified.text
    assert verified.json()["entitlement_status"] == "FIRST_APP_FREE"
