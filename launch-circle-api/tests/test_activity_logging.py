from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.activity import UserActivityEvent
from app.models.admin import AdminAudit
from app.services import activity_logging
from app.services.admin_auth import password_hash
from tests.test_admin import HEADERS, PASSWORD
from tests.test_shared_pool import actor, campaign


def test_retention_cleanup_is_throttled_to_six_hours(monkeypatch):
    class RecordingSession:
        def __init__(self):
            self.statements = 0

        def execute(self, _statement):
            self.statements += 1

    monkeypatch.setattr(activity_logging, "_last_cleanup", None)
    db = RecordingSession()
    now = datetime.now(UTC)
    activity_logging._cleanup(db, now)
    activity_logging._cleanup(db, now + timedelta(minutes=1))
    assert db.statements == 2


def test_activity_metadata_admin_search_timeline_and_export(client, monkeypatch):
    from app.api import admin as admin_module
    from app.core.config import get_settings

    user_id, auth = actor()
    monkeypatch.setattr(get_settings(), "admin_password_hash", password_hash(PASSWORD))
    admin_module._attempts.clear()
    operator = client
    assert operator.post("/admin/api/login", json={"password": PASSWORD}, headers=HEADERS).status_code == 200

    response = client.get("/v1/me", headers={
        **auth,
        "X-Request-ID": "client-supplied-value-is-ignored",
        "X-Client-Version": "1.0.42",
        "X-Client-Platform": "android",
        "X-Device-Type": "mobile",
    })
    assert response.status_code == 200
    request_id = response.headers["x-request-id"]
    assert request_id != "client-supplied-value-is-ignored"

    result = operator.get(f"/admin/api/activity?user_id={user_id}&request_id={request_id}")
    assert result.status_code == 200
    event = result.json()["events"][0]
    assert event["event_name"] == "account.opened"
    assert event["outcome"] == "SUCCESS"
    assert event["client_version"] == "1.0.42"
    assert event["platform"] == "android" and event["device_type"] == "mobile"

    detail = operator.get(f"/admin/api/users/{user_id}")
    assert detail.status_code == 200
    assert any(row["request_id"] == request_id for row in detail.json()["activity"])
    exported = operator.get(f"/admin/api/activity/export.csv?user_id={user_id}")
    assert exported.status_code == 200 and request_id in exported.text

    with SessionLocal() as db:
        assert db.scalar(select(UserActivityEvent).where(
            UserActivityEvent.request_id == request_id
        )) is not None
        actions = set(db.scalars(select(AdminAudit.action)))
        assert {"ACTIVITY_QUERY", "USER_DETAIL_VIEW", "ACTIVITY_EXPORT"} <= actions


def test_legacy_client_without_diagnostic_headers_still_logs_and_is_searchable(client, monkeypatch):
    from app.api import admin as admin_module
    from app.core.config import get_settings

    user_id, auth = actor()
    monkeypatch.setattr(get_settings(), "admin_password_hash", password_hash(PASSWORD))
    admin_module._attempts.clear()
    assert client.post("/admin/api/login", json={"password": PASSWORD}, headers=HEADERS).status_code == 200

    # This reproduces the Play-installed legacy client: it sends only its normal auth.
    response = client.get("/v1/me", headers=auth)
    assert response.status_code == 200
    request_id = response.headers["x-request-id"]

    result = client.get(f"/admin/api/activity?user_id={user_id}&request_id={request_id}")
    assert result.status_code == 200
    event = result.json()["events"][0]
    assert event["user_id"] == user_id
    assert event["outcome"] == "SUCCESS"
    assert event["error_code"] is None
    assert event["request_id"] == request_id
    assert event["client_version"] is None
    assert event["platform"] == event["device_type"] == "unknown"

    detail = client.get(f"/admin/api/users/{user_id}")
    assert detail.status_code == 200
    timeline_event = next(row for row in detail.json()["activity"] if row["request_id"] == request_id)
    assert timeline_event["outcome"] == "SUCCESS"
    assert timeline_event["error_code"] is None


def test_authenticated_missing_app_read_logs_stable_not_found_without_business_writes(client):
    from sqlalchemy import func

    from app.core.database import Base
    from app.models.activity import UserActivityEvent

    user_id, auth = actor()
    missing_app_id = str(uuid4())
    business_tables = [
        table for table in Base.metadata.sorted_tables
        if table.name not in {"user_activity_events", "admin_audit"}
    ]

    def business_row_counts():
        with SessionLocal() as db:
            return {
                table.name: db.scalar(select(func.count()).select_from(table))
                for table in business_tables
            }

    before = business_row_counts()
    response = client.get(f"/apps/{missing_app_id}", headers=auth)
    assert response.status_code == 404
    request_id = response.headers["x-request-id"]

    with SessionLocal() as db:
        event = db.scalar(select(UserActivityEvent).where(
            UserActivityEvent.request_id == request_id
        ))
        assert event is not None
        assert event.user_id == user_id
        assert event.event_name == "app.opened"
        assert event.workflow == "app_management"
        assert event.outcome == "FAILURE"
        assert event.error_code == "NOT_FOUND"
        assert event.method == "GET"
        assert event.route_template == "/apps/{app_id}"
        assert event.object_type == "app"
        assert event.object_id == missing_app_id
        assert event.status_code == 404
        assert event.request_id == request_id

    assert business_row_counts() == before


def test_exact_activity_csv_export_returns_one_event_and_records_matching_audit(client, monkeypatch):
    from csv import DictReader
    from io import StringIO

    from sqlalchemy import select

    from app.api import admin as admin_module
    from app.core.config import get_settings
    from app.models.admin import AdminAudit

    user_id, auth = actor()
    success = client.get("/v1/me", headers=auth)
    assert success.status_code == 200
    request_id = success.headers["x-request-id"]
    failure = client.get(f"/apps/{uuid4()}", headers=auth)
    assert failure.status_code == 404

    monkeypatch.setattr(get_settings(), "admin_password_hash", password_hash(PASSWORD))
    admin_module._attempts.clear()
    assert client.post("/admin/api/login", json={"password": PASSWORD}, headers=HEADERS).status_code == 200
    filters = {
        "user_id": user_id,
        "request_id": request_id,
        "event_name": "account.opened",
        "outcome": "SUCCESS",
    }
    response = client.get("/admin/api/activity/export.csv", params=filters, headers=HEADERS)
    assert response.status_code == 200
    export_request_id = response.headers["x-request-id"]
    rows = list(DictReader(StringIO(response.text)))
    assert len(rows) == 1
    assert rows[0]["user_id"] == user_id
    assert rows[0]["request_id"] == request_id
    assert rows[0]["event_name"] == "account.opened"
    assert rows[0]["outcome"] == "SUCCESS"

    with SessionLocal() as db:
        audit_row = db.scalar(select(AdminAudit).where(
            AdminAudit.action == "ACTIVITY_EXPORT",
            AdminAudit.target_id == "activity-export",
        ))
        assert audit_row is not None
        assert audit_row.detail["request_id"] == export_request_id
        assert audit_row.detail["result_count"] == 1
        assert audit_row.detail["filters"] == {
            "user_id": user_id,
            "start_at": None,
            "end_at": None,
            "event_name": "account.opened",
            "outcome": "SUCCESS",
            "request_id": request_id,
        }

def test_repeated_read_events_are_deduplicated_and_client_request_id_is_not_used(client):
    user_id, auth = actor()
    first = client.get("/v1/me", headers={**auth, "X-Request-ID": "bad request id"})
    second = client.get("/v1/me", headers={**auth, "X-Request-ID": "bad request id"})
    assert first.status_code == second.status_code == 200
    assert first.headers["x-request-id"] != "bad request id"
    assert second.headers["x-request-id"] != "bad request id"
    with SessionLocal() as db:
        events = list(db.scalars(select(UserActivityEvent).where(
            UserActivityEvent.user_id == user_id,
            UserActivityEvent.event_name == "account.opened",
        )))
        assert len(events) == 1


def test_user_app_correction_uses_owner_scope_and_redacts_audit(client, monkeypatch):
    from app.api import admin as admin_module
    from app.core.config import get_settings
    from app.models.launch import App

    owner = actor()
    other = actor()
    app_id = campaign(owner)
    with SessionLocal() as db:
        package_name = db.get(App, app_id).package_name
    monkeypatch.setattr(get_settings(), "admin_password_hash", password_hash(PASSWORD))
    admin_module._attempts.clear()
    assert client.post("/admin/api/login", json={"password": PASSWORD}, headers=HEADERS).status_code == 200

    path = f"/admin/api/users/{owner[0]}/apps/{app_id}"
    new_link = f"https://play.google.com/apps/testing/{package_name}"
    body = {"changes": {"opt_in_url": new_link},
            "reason": "Correct closed test join link"}
    assert client.patch(path, json=body, headers=HEADERS).status_code == 200
    assert client.patch(f"/admin/api/users/{other[0]}/apps/{app_id}", json=body,
                        headers=HEADERS).status_code == 404

    with SessionLocal() as db:
        app = db.get(App, app_id)
        assert app.opt_in_url == new_link
        audit_row = db.scalar(select(AdminAudit).where(AdminAudit.action == "APP_UPDATE"))
        rendered = str(audit_row.detail)
        assert "play.google.com/apps/testing" not in rendered
        assert "sha256" in rendered and audit_row.detail["reason"] == body["reason"]
