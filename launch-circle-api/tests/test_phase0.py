from app.services.missions import MISSION_SCHEDULE


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
    me = client.get("/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    return {
        "id": me.json()["id"],
        "headers": {"Authorization": f"Bearer {tokens['access_token']}"},
    }


def create_launch(client, owner: dict) -> dict:
    response = client.post(
        "/apps",
        headers=owner["headers"],
        json={
            "name": "BLE Signal Analyzer",
            "package_name": "com.example.bleanalyzer",
            "opt_in_url": "https://play.google.com/apps/testing/com.example.bleanalyzer",
            "google_group_url": "https://groups.google.com/g/ble-testers",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_phase0_vertical_slice_and_cold_start_dashboard(client):
    owner = register(client, "owner@example.com", "Developer A")
    tester = register(client, "tester@example.com", "Developer B")
    app = create_launch(client, owner)

    cold = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"])
    assert cold.status_code == 200
    assert cold.json()["active_testers"] == 0
    assert cold.json()["testers_needed_for_minimum"] == 12
    assert cold.json()["production_readiness"] == 15
    assert "does not guarantee" in cold.json()["approval_disclaimer"]

    assigned = client.post(f"/apps/{app['id']}/assign/{tester['id']}", headers=owner["headers"])
    assert assigned.status_code == 201, assigned.text
    assignment = assigned.json()
    assert assignment["status"] == "ASSIGNED"

    opt_in = client.patch(f"/assignments/{assignment['id']}/opt-in", headers=tester["headers"])
    assert opt_in.status_code == 200
    assert opt_in.json()["status"] == "OPTED_IN"

    installed = client.patch(
        f"/assignments/{assignment['id']}/installed", headers=tester["headers"]
    )
    assert installed.status_code == 200, installed.text
    assert installed.json()["status"] == "ACTIVE"
    assert installed.json()["total_missions"] == 6

    missions = client.get(f"/assignments/{assignment['id']}/missions", headers=tester["headers"])
    assert missions.status_code == 200
    assert [(row["scheduled_day"], row["mission_type"]) for row in missions.json()] == list(
        MISSION_SCHEDULE
    )
    first = missions.json()[0]
    assert first["status"] == "AVAILABLE"

    today = client.get("/test-missions/today", headers=tester["headers"])
    assert today.status_code == 200
    assert [row["id"] for row in today.json()] == [first["id"]]

    completed = client.patch(f"/missions/{first['id']}/complete", headers=tester["headers"])
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"

    submitted = client.post(
        f"/missions/{first['id']}/feedback",
        headers=tester["headers"],
        json={
            "launch_ok": True,
            "core_feature_ok": "partly",
            "rating": 4,
            "issue_text": "Permission explanation was unclear.",
            "suggestion_text": "Add a short onboarding note.",
        },
    )
    assert submitted.status_code == 201, submitted.text
    assert submitted.json()["core_feature_ok"] == "PARTLY"
    assert submitted.json()["tester_label"].startswith("Tester #")

    feedback = client.get(f"/apps/{app['id']}/feedback", headers=owner["headers"])
    assert feedback.status_code == 200
    assert len(feedback.json()) == 1
    assert "email" not in feedback.json()[0]

    dashboard = client.get(f"/apps/{app['id']}/dashboard", headers=owner["headers"])
    assert dashboard.status_code == 200
    data = dashboard.json()
    assert data["status"] == "WAITING_FOR_TESTERS"
    assert data["active_testers"] == 1
    assert data["assigned_testers"] == 1
    assert data["testers_needed_for_minimum"] == 11
    assert data["completed_missions"] == 1
    assert data["feedback_count"] == 1
    assert data["production_readiness"] == 30


def test_owner_assignment_and_duplicate_assignment_are_rejected(client):
    owner = register(client, "owner@example.com", "Owner")
    tester = register(client, "tester@example.com", "Tester")
    app = create_launch(client, owner)

    own_assignment = client.post(
        f"/apps/{app['id']}/assign/{owner['id']}", headers=owner["headers"]
    )
    assert own_assignment.status_code == 422

    first = client.post(f"/apps/{app['id']}/assign/{tester['id']}", headers=owner["headers"])
    assert first.status_code == 201
    duplicate = client.post(f"/apps/{app['id']}/assign/{tester['id']}", headers=owner["headers"])
    assert duplicate.status_code == 409


def test_invite_code_can_be_created_listed_and_accepted(client):
    inviter = register(client, "inviter@example.com", "Inviter")
    joiner = register(client, "joiner@example.com", "Joiner")

    created = client.post(
        "/invites",
        headers=inviter["headers"],
        json={"invited_email": "joiner@example.com"},
    )
    assert created.status_code == 201
    invite = created.json()
    assert invite["invite_code"].startswith("LC-")
    assert invite["share_url"].endswith(invite["invite_code"])

    visible = client.get("/invites/me", headers=joiner["headers"])
    assert [row["id"] for row in visible.json()] == [invite["id"]]

    accepted = client.post(f"/invites/{invite['invite_code']}/accept", headers=joiner["headers"])
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "ACCEPTED"
    assert accepted.json()["joined_user_id"] == joiner["id"]
