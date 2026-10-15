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


def create_launch(
    client, owner: dict, core_workflow_steps: list[str] | None = None
) -> dict:
    request_body = {
        "name": "BLE Signal Analyzer",
        "package_name": "com.example.bleanalyzer",
        "opt_in_url": "https://play.google.com/apps/testing/com.example.bleanalyzer",
        "play_developer_account_id": "1000000000000000001",
        "google_group_url": "https://groups.google.com/g/ble-testers",
    }
    if core_workflow_steps is not None:
        request_body["core_workflow_steps"] = core_workflow_steps
    response = client.post(
        "/apps",
        headers=owner["headers"],
        json=request_body,
    )
    assert response.status_code == 201, response.text
    return response.json()


def join_circle(client, owner: dict, member: dict) -> None:
    invite = client.post(
        "/invites",
        headers=owner["headers"],
        json={"invited_email": "tester@example.com"},
    )
    assert invite.status_code == 201, invite.text
    accepted = client.post(
        f"/invites/{invite.json()['invite_code']}/accept",
        headers=member["headers"],
    )
    assert accepted.status_code == 200, accepted.text


def test_phase0_vertical_slice_and_cold_start_dashboard(client):
    owner = register(client, "owner@example.com", "Developer A")
    tester = register(client, "tester@example.com", "Developer B")
    workflow = [
        "Open the signal scan screen.",
        "Scan for nearby BLE devices.",
        "Open a device and inspect its signal details.",
    ]
    app = create_launch(client, owner, workflow)
    assert app["core_workflow_steps"] == workflow
    join_circle(client, owner, tester)

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
    core_mission = missions.json()[1]
    assert core_mission["goal"] == "Complete the main workflow in BLE Signal Analyzer."
    assert core_mission["steps"] == workflow
    assert len(first["steps"]) <= 4

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
            "completion_result": "completed_with_difficulty",
            "rating": 4,
            "issue_text": "Permission explanation was unclear.",
            "suggestion_text": "Add a short onboarding note.",
            "time_spent_minutes": 7,
        },
    )
    assert submitted.status_code == 201, submitted.text
    assert submitted.json()["core_feature_ok"] == "PARTLY"
    assert submitted.json()["completion_result"] == "COMPLETED_WITH_DIFFICULTY"
    assert submitted.json()["time_spent_minutes"] == 7
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
    assert data["tester_minutes_reported"] == 7

    coordination = client.post(
        f"/apps/{app['id']}/coordination-time",
        headers=owner["headers"],
        json={"minutes": 13, "category": "COORDINATION"},
    )
    assert coordination.status_code == 201, coordination.text
    assert coordination.json()["developer_coordination_minutes"] == 13
    assert coordination.json()["coordination_entries"] == 1

    workload = client.get(f"/apps/{app['id']}/workload", headers=owner["headers"])
    assert workload.status_code == 200, workload.text
    assert workload.json()["tester_minutes_reported"] == 7
    assert workload.json()["developer_coordination_minutes"] == 13

    viewed = client.post(
        f"/apps/{app['id']}/managed-offer/viewed",
        headers=owner["headers"],
        json={"trigger": "PRIORITY"},
    )
    assert viewed.status_code == 200, viewed.text


def test_owner_assignment_and_duplicate_assignment_are_rejected(client):
    owner = register(client, "owner@example.com", "Owner")
    tester = register(client, "tester@example.com", "Tester")
    app = create_launch(client, owner)
    join_circle(client, owner, tester)

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
