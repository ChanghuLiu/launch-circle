from sqlalchemy import select

from app.api import auth as auth_api
from app.core.database import SessionLocal
from app.models.launch import (
    App,
    AppChange,
    BackendEvent,
    Feedback,
    Invite,
    PilotEvent,
)
from app.models.launch import TesterAssignment as AssignmentModel
from app.models.launch import TestMission as MissionModel
from app.models.user import User


def login_as(client, monkeypatch, subject: str, email: str) -> dict:
    monkeypatch.setattr(
        auth_api,
        "verify_google_id_token",
        lambda _token: {
            "sub": subject,
            "email": email,
            "email_verified": True,
            "name": subject,
        },
    )
    response = client.post("/v1/auth/google", json={"id_token": "valid"})
    assert response.status_code == 200
    return response.json()


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_authenticated_user_deletion_removes_related_data_only(client, monkeypatch):
    deleted_tokens = login_as(client, monkeypatch, "delete-me", "delete@example.com")
    survivor_tokens = login_as(client, monkeypatch, "keep-me", "keep@example.com")

    with SessionLocal() as db:
        deleted_user = db.scalar(select(User).where(User.email == "delete@example.com"))
        survivor = db.scalar(select(User).where(User.email == "keep@example.com"))
        assert deleted_user is not None
        assert survivor is not None
        deleted_app = App(
            owner_id=deleted_user.id, name="Deleted app",
            package_name="com.example.deleted", opt_in_url="https://example.com/deleted",
        )
        survivor_app = App(
            owner_id=survivor.id, name="Survivor app",
            package_name="com.example.survivor", opt_in_url="https://example.com/survivor",
        )
        db.add_all([deleted_app, survivor_app])
        db.flush()
        deleted_assignment = AssignmentModel(
            app_id=survivor_app.id, tester_id=deleted_user.id,
        )
        survivor_assignment = AssignmentModel(
            app_id=survivor_app.id, tester_id=survivor.id,
        )
        db.add_all([deleted_assignment, survivor_assignment])
        db.flush()
        deleted_mission = MissionModel(
            assignment_id=deleted_assignment.id, mission_type="DAY_1_SMOKE", scheduled_day=1,
        )
        survivor_mission = MissionModel(
            assignment_id=survivor_assignment.id, mission_type="DAY_1_SMOKE", scheduled_day=1,
        )
        db.add_all([deleted_mission, survivor_mission])
        db.flush()
        deleted_feedback = Feedback(
            mission_id=deleted_mission.id, tester_id=deleted_user.id,
            app_id=survivor_app.id, launch_ok=True,
        )
        survivor_feedback = Feedback(
            mission_id=survivor_mission.id, tester_id=survivor.id,
            app_id=survivor_app.id, launch_ok=True,
        )
        deleted_change = AppChange(app_id=deleted_app.id, description="Delete with app")
        survivor_change = AppChange(app_id=survivor_app.id, description="Keep with app")
        deleted_invite = Invite(inviter_id=deleted_user.id, invite_code="DELETE01")
        accepted_invite = Invite(
            inviter_id=survivor.id, joined_user_id=deleted_user.id,
            invite_code="DELETE02", status="ACCEPTED",
        )
        survivor_invite = Invite(inviter_id=survivor.id, invite_code="KEEP0001")
        db.add_all([
            deleted_feedback, survivor_feedback, deleted_change, survivor_change,
            deleted_invite, accepted_invite, survivor_invite,
        ])
        db.flush()
        deleted_event = BackendEvent(
            app_id=survivor_app.id, assignment_id=deleted_assignment.id,
            event_type="deleted_tester_event", dedupe_key="deleted-tester-event",
        )
        survivor_event = BackendEvent(
            app_id=survivor_app.id, assignment_id=survivor_assignment.id,
            event_type="survivor_event", dedupe_key="survivor-event",
        )
        deleted_pilot_event = PilotEvent(
            actor_user_id=deleted_user.id, app_id=survivor_app.id,
            event_type="deleted_actor_event", dedupe_key="deleted-actor-event",
        )
        survivor_pilot_event = PilotEvent(
            actor_user_id=survivor.id, app_id=survivor_app.id,
            assignment_id=survivor_assignment.id, invite_id=survivor_invite.id,
            event_type="survivor_pilot_event", dedupe_key="survivor-pilot-event",
        )
        db.add_all([deleted_event, survivor_event, deleted_pilot_event, survivor_pilot_event])
        db.flush()
        deleted_ids = {
            App: deleted_app.id, AppChange: deleted_change.id,
            AssignmentModel: deleted_assignment.id, MissionModel: deleted_mission.id,
            Feedback: deleted_feedback.id, BackendEvent: deleted_event.id,
            PilotEvent: deleted_pilot_event.id,
        }
        survivor_ids = {
            User: survivor.id, App: survivor_app.id, AppChange: survivor_change.id,
            AssignmentModel: survivor_assignment.id, MissionModel: survivor_mission.id,
            Feedback: survivor_feedback.id, BackendEvent: survivor_event.id,
            PilotEvent: survivor_pilot_event.id, Invite: survivor_invite.id,
        }
        deleted_user_id = deleted_user.id
        deleted_invite_ids = [deleted_invite.id, accepted_invite.id]
        db.commit()

    response = client.delete("/v1/me", headers=auth_headers(deleted_tokens))
    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}
    assert client.get("/v1/me", headers=auth_headers(deleted_tokens)).status_code == 401
    assert client.get("/v1/me", headers=auth_headers(survivor_tokens)).status_code == 200

    with SessionLocal() as db:
        assert db.get(User, deleted_user_id) is None
        for model, row_id in deleted_ids.items():
            assert db.get(model, row_id) is None
        for invite_id in deleted_invite_ids:
            assert db.get(Invite, invite_id) is None
        for model, row_id in survivor_ids.items():
            assert db.get(model, row_id) is not None


def test_delete_account_requires_authentication(client):
    response = client.delete("/v1/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing access token"
