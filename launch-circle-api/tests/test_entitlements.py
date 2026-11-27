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
    result = {"id": me.json()["id"], "headers": headers}
    # Existing scenario explicitly starts with a synthetic confirmed Play account.
    confirmed = client.put("/tester-group-access", headers=result["headers"], json={"status": "SELF_CONFIRMED", "play_email": email})
    assert confirmed.status_code == 200, confirmed.text
    return result


def app_payload(package_name: str, developer_account_id: str) -> dict:
    return {"ownership_authorized": True, "icon_data": 'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGPUjTrBwMDAxMDAwMDAAAAPQwFTH4I6DQAAAABJRU5ErkJggg==',
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

def test_one_app_per_person_even_with_allowlisted_publisher(client, monkeypatch):
    monkeypatch.setattr(phase0_settings, "google_play_unlimited_developer_account_ids", "1234567890123456789")
    first = register(client, "first@example.com", "First")
    second = register(client, "second@example.com", "Second")
    assert create_app(client, first, "com.example.first", "1234567890123456789").status_code == 201
    denied = create_app(client, first, "com.example.second", "1234567890123456789")
    assert denied.status_code == 409 and "one app" in denied.json()["detail"]
    assert create_app(client, second, "com.example.otherperson", "1234567890123456789").status_code == 201


def test_manager_can_add_multiple_apps(client, monkeypatch):
    owner = register(client, "manager@example.com", "Manager")
    monkeypatch.setattr("app.api.phase0.is_app_admin", lambda user: user.id == owner["id"])
    for i in range(3):
        response = create_app(client, owner, f"com.example.manager{i}", "1234567890123456789")
        assert response.status_code == 201, response.text


def test_legacy_app_also_uses_person_quota(client):
    owner = register(client, "legacy@example.com", "Legacy")
    with SessionLocal() as db:
        user = db.get(User, owner["id"])
        circle = ensure_owner_circle(db, user)
        db.add(App(owner_id=user.id, circle_id=circle.id, name="Legacy", package_name="com.example.legacy", opt_in_url="https://play.google.com/apps/testing/com.example.legacy"))
        db.commit()
    assert create_app(client, owner, "com.example.new", "1234567890123456789").status_code == 409


def test_external_customer_registration_in_production(client, monkeypatch):
    from app.models.launch import DeveloperAccount
    owner = register(client, "selena@regevidencehub.com", "Selena")
    monkeypatch.setattr(phase0_settings, "app_env", "production")
    monkeypatch.setattr(phase0_settings, "google_play_developer_account_id", "123456789")
    def reject_operator_lookup(*args):
        raise AssertionError("External packages must not use operator publisher credentials")
    monkeypatch.setattr("app.api.phase0.verify_app_package_ownership", reject_operator_lookup)
    response = create_app(client, owner, "com.external.customer", "987654321")
    assert response.status_code == 201, response.text
    assert response.json()["play_developer_account_id"] is None
    assert response.json()["entitlement_status"] == "FIRST_APP_FREE"
    with SessionLocal() as db:
        item = db.get(App, response.json()["id"])
        account = db.get(DeveloperAccount, item.developer_account_id)
        assert account.verification_status == "UNVERIFIED"
        assert account.identity_method == "USER_PROVIDED"
        assert account.play_developer_account_id == "user:" + owner["id"]
    assert create_app(client, owner, "com.external.second", "987654321").status_code == 409


def test_customer_without_publisher_configuration_can_submit(client, monkeypatch):
    owner = register(client, "simple@example.com", "Simple")
    monkeypatch.setattr(phase0_settings, "app_env", "production")
    monkeypatch.setattr(phase0_settings, "google_play_developer_account_id", "")
    payload = app_payload("com.external.simple", "")
    response = client.post("/apps", headers=owner["headers"], json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["play_developer_account_id"] is None
