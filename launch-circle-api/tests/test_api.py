from app.api import auth as auth_api


def fake_google_payload(_token: str) -> dict:
    return {
        "sub": "google-user-1",
        "email": "login@example.com",
        "email_verified": True,
        "name": "Launch Tester",
    }


def login(client, monkeypatch):
    monkeypatch.setattr(auth_api, "verify_google_id_token", fake_google_payload)
    response = client.post("/v1/auth/google", json={"id_token": "valid"})
    assert response.status_code == 200
    return response.json()


def auth_headers(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_invalid_google_token_rejected(client, monkeypatch):
    def reject(_token: str):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid Google token")

    monkeypatch.setattr(auth_api, "verify_google_id_token", reject)
    response = client.post("/v1/auth/google", json={"id_token": "bad"})
    assert response.status_code == 401


def test_profile_requires_auth(client):
    assert client.get("/v1/me").status_code == 401


def test_authenticated_user_retrieval(client, monkeypatch):
    tokens = login(client, monkeypatch)
    response = client.get("/v1/me", headers=auth_headers(tokens))
    assert response.status_code == 200
    assert response.json()["login_email"] == "login@example.com"
    assert response.json()["profile_ready"] is False


def test_profile_and_tester_email_consent(client, monkeypatch):
    tokens = login(client, monkeypatch)
    headers = auth_headers(tokens)
    response = client.put(
        "/v1/me",
        headers=headers,
        json={"display_name": "Chang", "country": "ca", "languages": ["EN", "fr"]},
    )
    assert response.status_code == 200
    assert response.json()["country"] == "CA"
    assert response.json()["languages"] == ["en", "fr"]

    denied = client.put(
        "/v1/me/tester-email",
        headers=headers,
        json={"tester_email": "tester@gmail.com", "sharing_consent": False},
    )
    assert denied.status_code == 422

    accepted = client.put(
        "/v1/me/tester-email",
        headers=headers,
        json={"tester_email": "tester@gmail.com", "sharing_consent": True},
    )
    assert accepted.status_code == 200
    assert accepted.json()["tester_email_sharing_consent"] is True
    assert accepted.json()["profile_ready"] is True


def test_device_upsert(client, monkeypatch):
    tokens = login(client, monkeypatch)
    headers = auth_headers(tokens)
    body = {
        "installation_id": "installation-123",
        "manufacturer": "Samsung",
        "model": "SM-S911W",
        "android_api": 35,
        "capabilities": ["esim", "bluetooth"],
    }
    first = client.put("/v1/me/device", headers=headers, json=body)
    second = client.put("/v1/me/device", headers=headers, json={**body, "android_api": 36})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["android_api"] == 36


def test_refresh_rotation_and_logout(client, monkeypatch):
    tokens = login(client, monkeypatch)
    refreshed = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != tokens["refresh_token"]

    old_reuse = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert old_reuse.status_code == 401

    new_refresh = refreshed.json()["refresh_token"]
    logout = client.post("/v1/auth/logout", json={"refresh_token": new_refresh})
    assert logout.status_code == 204
    after_logout = client.post("/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert after_logout.status_code == 401
