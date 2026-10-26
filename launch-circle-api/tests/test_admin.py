"""Security, evidence separation and manual dispatch integration coverage."""
import pytest
from sqlalchemy import func, select

from app.api import admin as module
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.admin import AdminAudit, AdminRecommendation
from app.models.launch import TesterAssignment
from app.services.admin_auth import password_hash, password_matches
from tests.test_shared_pool import actor, campaign, open_app, post

PASSWORD = "SYNTHETIC-operator-test-password"
HEADERS = {"X-Admin-Action": "1"}


@pytest.fixture
def operator(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_password_hash", password_hash(PASSWORD))
    module._attempts.clear()
    res = client.post("/admin/api/login", json={"password": PASSWORD}, headers=HEADERS)
    assert res.status_code == 200, res.text
    return client


def test_operator_boundary_csrf_cookie_and_logout(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_password_hash", password_hash(PASSWORD))
    module._attempts.clear()
    assert client.get("/admin/api/overview").status_code == 401
    regular = actor()
    assert client.get("/admin/api/overview", headers=regular[1]).status_code == 401
    assert client.post("/admin/api/login", json={"password": PASSWORD}).status_code == 403
    assert client.post("/admin/api/login", json={"password": PASSWORD},
                       headers={**HEADERS, "Origin": "https://evil.example"}).status_code == 403
    bad = client.post("/admin/api/login", json={"password": "wrong"}, headers=HEADERS)
    assert bad.status_code == 401
    good = client.post("/admin/api/login", json={"password": PASSWORD}, headers=HEADERS)
    cookie = good.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/admin" in cookie
    assert client.get("/admin/api/overview").status_code == 200
    assert client.post("/admin/api/logout", json={}).status_code == 403
    assert client.post("/admin/api/logout", json={}, headers=HEADERS).status_code == 200
    assert client.get("/admin/api/overview").status_code == 401


def test_disabled_rate_limit_and_password_verification(client, monkeypatch):
    assert password_matches(PASSWORD, password_hash(PASSWORD))
    assert not password_matches("wrong", password_hash(PASSWORD))
    assert not password_matches(PASSWORD, "invalid")
    monkeypatch.setattr(get_settings(), "admin_password_hash", "")
    assert client.post("/admin/api/login", json={"password": PASSWORD}, headers=HEADERS).status_code == 503
    monkeypatch.setattr(get_settings(), "admin_password_hash", password_hash(PASSWORD))
    module._attempts.clear()
    for _ in range(10):
        assert client.post("/admin/api/login", json={"password": "wrong"}, headers=HEADERS).status_code == 401
    assert client.post("/admin/api/login", json={"password": PASSWORD}, headers=HEADERS).status_code == 429
    module._attempts.clear()


def test_recommendation_is_not_assignment_and_pause_preserves_work(operator):
    owner, tester = actor(), actor()
    aid = campaign(owner)
    open_app(operator, aid, owner)
    post(operator, "/tester-pool/me", tester, {"enabled": True})
    control = {"kind": "CUSTOMER", "priority": 95, "paused": False, "note": "First real customer"}
    assert operator.post(f"/admin/api/apps/{aid}/control", json=control, headers=HEADERS).status_code == 200
    path = f"/admin/api/apps/{aid}/recommend"
    body = {"tester_id": tester[0], "enabled": True}
    for _ in range(2):
        r = operator.post(path, json=body, headers=HEADERS)
        assert r.status_code == 200 and r.json()["assignment_created"] is False
    with SessionLocal() as db:
        assert db.scalar(select(func.count(AdminRecommendation.app_id))) == 1
        assert db.scalar(select(func.count(TesterAssignment.id))) == 0
    overview = operator.get("/admin/api/overview").json()
    assert overview["customer_count"] == 1 and not overview["google_eligibility_confirmed"]
    a = overview["apps"][0]
    assert a["missing_to_minimum"] == 12 and a["reported_joined_and_installed"] == 0
    assert "password" not in str(overview) and "token_hash" not in str(overview)
    control["paused"] = True
    operator.post(f"/admin/api/apps/{aid}/control", json=control, headers=HEADERS)
    assert operator.get("/tester-pool/opportunities", headers=tester[1]).json() == []
    assert post(operator, f"/apps/{aid}/tester-pool/accept", tester).status_code == 404
    control["paused"] = False
    operator.post(f"/admin/api/apps/{aid}/control", json=control, headers=HEADERS)
    assert post(operator, f"/apps/{aid}/tester-pool/accept", tester).status_code == 200
    control["paused"] = True
    operator.post(f"/admin/api/apps/{aid}/control", json=control, headers=HEADERS)
    with SessionLocal() as db:
        assignment = db.scalar(select(TesterAssignment))
        assert assignment.status == "ASSIGNED"
        assert assignment.installed_at is None and assignment.opted_in_at is None
        assert db.scalar(select(func.count(AdminAudit.id))) >= 6
    body["enabled"] = False
    assert operator.post(path, json=body, headers=HEADERS).status_code == 200
    assert operator.get("/admin/api/overview").json()["recommendations"] == []


def test_consent_ready_limits_and_classification(operator):
    owner, tester = actor(), actor()
    aids = [campaign(owner) for _ in range(3)]
    path = f"/admin/api/apps/{aids[0]}/recommend"
    assert operator.post(path, json={"tester_id": tester[0]}, headers=HEADERS).status_code == 409
    for aid in aids:
        open_app(operator, aid, owner)
    post(operator, "/tester-pool/me", tester, {"enabled": True})
    cfg = {"kind": "OWN", "priority": 10, "paused": False}
    operator.post(f"/admin/api/apps/{aids[0]}/control", json=cfg, headers=HEADERS)
    assert operator.get("/admin/api/overview").json()["customer_count"] == 0
    cfg["kind"] = "SYNTHETIC"
    operator.post(f"/admin/api/apps/{aids[0]}/control", json=cfg, headers=HEADERS)
    assert operator.post(path, json={"tester_id": tester[0]}, headers=HEADERS).status_code == 409
    assert aids[0] not in [a["app_id"] for a in operator.get("/tester-pool/opportunities", headers=tester[1]).json()]
    for aid in aids[1:]:
        assert post(operator, f"/apps/{aid}/tester-pool/accept", tester).status_code == 200
    cfg["kind"] = "OWN"
    operator.post(f"/admin/api/apps/{aids[0]}/control", json=cfg, headers=HEADERS)
    assert operator.post(path, json={"tester_id": tester[0]}, headers=HEADERS).status_code == 409
    cfg["priority"] = 101
    assert operator.post(f"/admin/api/apps/{aids[0]}/control", json=cfg, headers=HEADERS).status_code == 422


def test_assets_safe_headers_and_unknown_paths(client):
    page = client.get("/admin")
    assert page.status_code == 200 and "管理后台" in page.text
    assert page.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert page.headers["x-content-type-options"] == "nosniff"
    assert client.get("/admin/assets/admin.js").status_code == 200
    assert client.get("/admin/assets/admin.css").status_code == 200
    assert client.get("/admin/assets/config.py").status_code == 422


def test_recommendation_order_priority_and_expiry(operator, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from app.models.admin import AdminSession

    owner, tester = actor(), actor()
    aids = [campaign(owner) for _ in range(3)]
    for aid in aids:
        open_app(operator, aid, owner)
    post(operator, "/tester-pool/me", tester, {"enabled": True})
    for aid, priority in zip(aids, [5, 90, 50], strict=True):
        operator.post(f"/admin/api/apps/{aid}/control", json={
            "kind": "OWN", "priority": priority, "paused": False}, headers=HEADERS)
    def found():
        return [r["app_id"] for r in operator.get("/tester-pool/opportunities", headers=tester[1]).json()]
    assert found() == [aids[1], aids[2], aids[0]]
    operator.post(f"/admin/api/apps/{aids[0]}/recommend", json={"tester_id": tester[0]}, headers=HEADERS)
    assert found() == [aids[0], aids[1], aids[2]]
    with SessionLocal() as db:
        db.scalar(select(AdminSession)).expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert operator.get("/admin/api/overview").status_code == 401


def test_production_secure_cookie_and_rotation(operator, monkeypatch):
    monkeypatch.setattr(get_settings(), "app_env", "production")
    r = operator.post("/admin/api/login", json={"password": PASSWORD}, headers=HEADERS)
    assert "secure" in r.headers["set-cookie"].lower()
    monkeypatch.setattr(get_settings(), "app_env", "development")
    monkeypatch.setattr(get_settings(), "admin_password_hash", password_hash("ROTATED-synthetic-password"))
    assert operator.get("/admin/api/overview").status_code == 401
