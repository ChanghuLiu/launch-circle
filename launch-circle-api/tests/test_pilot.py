from sqlalchemy import select

from app.core.database import SessionLocal, engine
from app.models.launch import App, PilotEvent


PASSWORD = "pilot-password"


def register(client, email: str, name: str) -> dict:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": name},
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    profile = client.get(
        "/me", headers={"Authorization": f"Bearer {token}"}
    ).json()
    return {
        "id": profile["id"],
        "headers": {"Authorization": f"Bearer {token}"},
    }


def create_launch(client, owner: dict) -> dict:
    response = client.post(
        "/apps",
        headers=owner["headers"],
        json={
            "name": "Pilot App",
            "package_name": "com.launchcircle.pilot",
            "opt_in_url": "https://play.google.com/apps/testing/com.launchcircle.pilot",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_pilot_config_and_google_group_confirmation_persist(client):
    owner = register(client, "pilot-owner@example.com", "Pilot Owner")
    launch = create_launch(client, owner)

    config = client.get("/pilot-config")
    assert config.status_code == 200
    assert config.json()["product_name"] == "Launch Circle: 12 Testers"
    assert (
        config.json()["google_group_email"]
        == "launch-circle-12-testers@googlegroups.com"
    )
    assert launch["google_group_mode"] == "LAUNCH_CIRCLE"
    assert launch["google_group_configured"] is False

    confirmed = client.post(
        f"/apps/{launch['id']}/google-group/confirm",
        headers=owner["headers"],
        json={"configured": True},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["google_group_configured"] is True
    assert confirmed.json()["google_group_confirmed_at"] is not None

    engine.dispose()
    with SessionLocal() as db:
        saved = db.get(App, launch["id"])
        assert saved is not None
        assert saved.google_group_configured is True
        events = list(
            db.scalars(
                select(PilotEvent).where(
                    PilotEvent.event_type == "google_group_confirmed"
                )
            )
        )
        assert len(events) == 1
        assert events[0].app_id == launch["id"]


def test_invite_creation_acceptance_and_duplicate_are_idempotent(client):
    inviter = register(client, "pilot-inviter@example.com", "Inviter")
    joiner = register(client, "pilot-joiner@example.com", "Joiner")

    created = client.post("/invites", headers=inviter["headers"], json={})
    assert created.status_code == 201, created.text
    invite = created.json()
    assert invite["invite_code"].startswith("LC-")
    assert invite["share_url"].endswith(invite["invite_code"])

    accepted = client.post(
        f"/invites/{invite['invite_code'].lower()}/accept",
        headers=joiner["headers"],
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["joined_user_id"] == joiner["id"]

    duplicate = client.post(
        f"/invites/{invite['invite_code']}/accept",
        headers=joiner["headers"],
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["accepted_at"] == accepted.json()["accepted_at"]

    with SessionLocal() as db:
        events = list(
            db.scalars(
                select(PilotEvent)
                .where(PilotEvent.invite_id == invite["id"])
                .order_by(PilotEvent.created_at)
            )
        )
        assert [event.event_type for event in events] == [
            "invite_created",
            "invite_accepted",
        ]


def test_core_pilot_events_are_recorded(client):
    owner = register(client, "event-owner@example.com", "Owner")
    tester = register(client, "event-tester@example.com", "Tester")
    launch = create_launch(client, owner)

    assignment = client.post(
        f"/apps/{launch['id']}/assign/{tester['id']}",
        headers=owner["headers"],
    ).json()
    client.patch(
        f"/assignments/{assignment['id']}/opt-in",
        headers=tester["headers"],
    )
    client.patch(
        f"/assignments/{assignment['id']}/installed",
        headers=tester["headers"],
    )
    mission = client.get(
        f"/assignments/{assignment['id']}/missions",
        headers=tester["headers"],
    ).json()[0]
    assert client.post(
        f"/missions/{mission['id']}/start", headers=tester["headers"]
    ).status_code == 200
    assert client.patch(
        f"/missions/{mission['id']}/complete", headers=tester["headers"]
    ).status_code == 200
    assert client.post(
        f"/missions/{mission['id']}/feedback",
        headers=tester["headers"],
        json={"launch_ok": True, "core_feature_ok": "YES"},
    ).status_code == 201

    with SessionLocal() as db:
        event_types = set(
            db.scalars(
                select(PilotEvent.event_type).where(PilotEvent.app_id == launch["id"])
            )
        )
    assert {
        "tester_assigned",
        "tester_opted_in",
        "tester_installed",
        "mission_started",
        "mission_completed",
        "feedback_submitted",
    }.issubset(event_types)
