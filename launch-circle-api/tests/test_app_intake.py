from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from test_shared_pool import actor

from app.core.database import SessionLocal
from app.models.launch import App, DeveloperAccount
from app.models.pool import AppIntake
from app.services.intake import approve_intake


def body(package="com.external.first", publisher="98765432101234567"):
    return {
        "name": "External Customer",
        "package_name": package,
        "developer_account_id": publisher,
        "workflow_steps": ["Complete a real core action"],
    }


def test_external_customer_intake_is_private_idempotent_and_does_not_create_apps(client):
    owner, other = actor(), actor()
    result = client.post("/app-intakes", headers=owner[1], json=body())
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "PENDING" and result.json()["app_id"] is None
    assert client.post("/app-intakes", headers=owner[1], json=body()).json() == result.json()
    assert client.get("/app-intakes", headers=other[1]).json() == []
    assert client.get("/app-intakes").status_code == 401
    with SessionLocal() as db:
        assert db.scalar(select(func.count(App.id))) == 0
    assert (
        client.post("/app-intakes", headers=owner[1], json=body("com.external.second")).status_code
        == 200
    )
    assert (
        client.post("/app-intakes", headers=owner[1], json=body("com.external.third")).status_code
        == 409
    )
    assert client.delete("/v1/me", headers=owner[1]).status_code == 200
    with SessionLocal() as db:
        assert db.get(AppIntake, result.json()["id"]) is None


def test_operator_review_creates_first_app_without_faking_verified_publisher(client):
    owner = actor()
    item = client.post("/app-intakes", headers=owner[1], json=body()).json()
    with SessionLocal() as db:
        with pytest.raises(ValueError):
            approve_intake(
                db,
                item["id"],
                reviewer="Operator",
                proof_sha256="missing",
                note="Package permission reviewed",
                now=datetime.now(UTC),
            )
        row = approve_intake(
            db,
            item["id"],
            reviewer="Synthetic operator",
            proof_sha256="a" * 64,
            note="Synthetic test only: checked package authorization",
            now=datetime.now(UTC),
        )
        app_id = row.app_id
        db.commit()
        again = approve_intake(
            db,
            item["id"],
            reviewer="Synthetic operator",
            proof_sha256="a" * 64,
            note="Synthetic replay only",
            now=datetime.now(UTC),
        )
        assert again.app_id == app_id
        app = db.get(App, app_id)
        assert app.owner_id == owner[0] and app.entitlement_status == "FIRST_APP_FREE"
        assert not app.google_group_configured
        account = db.get(DeveloperAccount, app.developer_account_id)
        assert account.verification_status == "UNVERIFIED"
        assert account.identity_method == "USER_PROVIDED"
    assert client.get("/apps", headers=owner[1]).json()[0]["id"] == app_id
    second = client.post("/app-intakes", headers=owner[1], json=body("com.external.second")).json()
    with SessionLocal() as db:
        with pytest.raises(ValueError, match="entitlement"):
            approve_intake(
                db,
                second["id"],
                reviewer="Operator",
                proof_sha256="a" * 64,
                note="Synthetic review only",
                now=datetime.now(UTC),
            )
        db.rollback()
        assert db.scalar(select(func.count(App.id))) == 1


def test_invalid_intake_cannot_be_used_as_public_approval_api(client):
    owner = actor()
    assert (
        client.post("/app-intakes", headers=owner[1], json=body("https://evil.test/")).status_code
        == 422
    )
    assert (
        client.post("/app-intakes", headers=owner[1], json=body(publisher="not-an-id")).status_code
        == 422
    )
    data = body()
    data["workflow_steps"] = [" "]
    assert client.post("/app-intakes", headers=owner[1], json=data).status_code == 422
    assert client.post("/app-intakes/fake/approve", headers=owner[1], json={}).status_code == 404
