from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.evidence import EnrollmentEvidence
from app.services.clock import aware
from tests.test_pilot import create_launch, join_circle, register


@pytest.fixture
def pilot(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "cold_start_evidence_enabled", True)
    owner = register(client, "evidence-owner@example.com", "Owner")
    tester = register(client, "evidence-tester@example.com", "Tester")
    other = register(client, "evidence-other@example.com", "Other")
    launch = create_launch(client, owner)
    join_circle(client, owner, tester)
    response = client.post(f"/apps/{launch['id']}/assign/{tester['id']}", headers=owner["headers"])
    assert response.status_code == 201, response.text
    assignment = response.json()
    for action in ("opt-in", "installed"):
        response = client.patch(
            f"/assignments/{assignment['id']}/{action}", headers=tester["headers"]
        )
        assert response.status_code == 200, response.text
    mission = client.get(
        f"/assignments/{assignment['id']}/missions", headers=tester["headers"]
    ).json()[0]
    assert (
        client.post(
            f"/apps/{launch['id']}/evidence/build",
            headers=owner["headers"],
            json={"target_version_code": 1, "description": "Pilot candidate"},
        ).status_code
        == 200
    )
    return owner, tester, other, launch, assignment, mission


def run_body(mission, key="request-original", result="PASS", version=1, source="HUMAN_MANUAL"):
    return {
        "idempotency_key": key,
        "execution_source": source,
        "result": result,
        "package_name": "com.launchcircle.pilot",
        "version_code": version,
        "expected_version_code": version,
        "device_key": "pilot-device",
        "device_model": "Pilot Device",
        "android_api": 27,
        "steps": [
            {
                "instruction": step,
                "expected": "Task result is visible",
                "actual": "Observed task result",
                "result": result,
            }
            for step in mission["steps"]
        ],
        "note": "Synthetic integration evidence, not real customer testing",
    }


def test_run_idempotency_conflict_and_no_automatic_tester_rewards(client, pilot):
    owner, tester, _, launch, _, mission = pilot
    path = f"/missions/{mission['id']}/runs"
    body = run_body(mission)
    first = client.post(path, headers=tester["headers"], json=body)
    assert first.status_code == 201, first.text
    again = client.post(path, headers=tester["headers"], json=body)
    assert again.json()["id"] == first.json()["id"]
    body["note"] = "Conflicting mutation"
    assert client.post(path, headers=tester["headers"], json=body).status_code == 409
    summary = client.get(f"/apps/{launch['id']}/evidence-summary", headers=owner["headers"]).json()
    assert summary["total_runs"] == 1
    assert summary["reported_joined_participants"] == 0
    assert summary["current_build_results"]["PASS"] == 1
    assert summary["current_build_device_coverage"] == 1
    assert summary["google_eligibility_confirmed"] is False
    assert summary["internal_readiness"] == "REVIEW_REQUIRED"
    missions = client.get(
        f"/assignments/{mission['assignment_id']}/missions", headers=tester["headers"]
    ).json()
    assert missions[0]["status"] != "COMPLETED"


def test_wrong_source_tenant_package_and_incomplete_pass_rejected(client, pilot):
    owner, tester, other, launch, assignment, mission = pilot
    path = f"/missions/{mission['id']}/runs"
    body = run_body(mission)
    assert client.post(path, headers=other["headers"], json=body).status_code == 404
    assert client.post(path, headers=owner["headers"], json=body).status_code == 403
    assert (
        client.get(f"/apps/{launch['id']}/evidence-summary", headers=other["headers"]).status_code
        == 404
    )
    assert (
        client.post(
            f"/assignments/{assignment['id']}/enrollment-evidence",
            headers=tester["headers"],
            json={
                "event": "JOINED",
                "source": "OWNER_CONFIRMED",
                "note": "Attempted source forgery",
            },
        ).status_code
        == 403
    )
    body["package_name"] = "com.wrong.app"
    assert client.post(path, headers=tester["headers"], json=body).status_code == 409
    body["package_name"] = "com.launchcircle.pilot"
    body["steps"] = body["steps"][:1]
    assert client.post(path, headers=tester["headers"], json=body).status_code == 409


def test_wrong_build_and_blocked_steps_cannot_pass(client, pilot):
    owner, tester, _, launch, _, mission = pilot
    path = f"/missions/{mission['id']}/runs"
    body = run_body(mission, version=2)
    assert client.post(path, headers=tester["headers"], json=body).status_code == 409
    body = run_body(mission)
    body["steps"][0]["result"] = "BLOCKED"
    assert client.post(path, headers=tester["headers"], json=body).status_code == 422
    body = run_body(mission, result="BLOCKED", source="AUTOMATED_RUNNER")
    assert client.post(path, headers=owner["headers"], json=body).status_code == 201
    summary = client.get(f"/apps/{launch['id']}/evidence-summary", headers=owner["headers"]).json()
    assert summary["manual_reported_participants"] == 0
    assert summary["current_build_device_coverage"] == 0
    assert summary["current_build_results"]["BLOCKED"] == 1


def test_fix_requires_matching_build_and_retest_not_owner_declaration(client, pilot):
    owner, tester, _other, launch, _, mission = pilot
    body = run_body(mission, result="FAIL")
    failed = client.post(
        f"/missions/{mission['id']}/runs", headers=tester["headers"], json=body
    ).json()
    fix = {"target_version_code": 2, "description": "Synthetic issue fix"}
    assert (
        client.post(f"/runs/{failed['id']}/fix", headers=tester["headers"], json=fix).status_code
        == 404
    )
    declared = client.post(f"/runs/{failed['id']}/fix", headers=owner["headers"], json=fix)
    assert declared.json()["verified_fixed"] is False
    retest = run_body(mission, key="request-retest", version=1)
    retest["retest_of_id"] = failed["id"]
    assert (
        client.post(
            f"/missions/{mission['id']}/runs", headers=tester["headers"], json=retest
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/apps/{launch['id']}/evidence/build", headers=owner["headers"], json=fix
        ).status_code
        == 200
    )
    retest["version_code"] = retest["expected_version_code"] = 2
    response = client.post(
        f"/missions/{mission['id']}/runs", headers=tester["headers"], json=retest
    )
    assert response.status_code == 201, response.text
    summary = client.get(f"/apps/{launch['id']}/evidence-summary", headers=owner["headers"]).json()
    assert summary["issues"][0]["state"] == "VERIFIED_FIXED"
    assert summary["current_build_results"] == {"PASS": 1, "FAIL": 0, "BLOCKED": 0, "NOT_RUN": 0}


def test_enrollment_rejoin_clock_unknown_and_no_backdating(client, pilot):
    owner, tester, _, launch, assignment, _ = pilot
    path = f"/assignments/{assignment['id']}/enrollment-evidence"
    response = client.post(
        path, headers=tester["headers"], json={"event": "JOINED", "note": "Tester self report"}
    )
    assert response.status_code == 201
    with SessionLocal() as db:
        row = db.scalar(select(EnrollmentEvidence))
        row.recorded_at = aware(row.recorded_at) - timedelta(days=15)
        db.commit()
    summary_path = f"/apps/{launch['id']}/evidence-summary"
    summary = client.get(summary_path, headers=owner["headers"]).json()
    assert summary["reported_continuous_14_days"] == 1
    assert summary["estimated_eligibility_at"] is None
    assert (
        client.post(
            path, headers=tester["headers"], json={"event": "LEFT", "note": "Tester left"}
        ).status_code
        == 201
    )
    assert (
        client.post(
            path, headers=tester["headers"], json={"event": "JOINED", "note": "Tester rejoined"}
        ).status_code
        == 201
    )
    summary = client.get(summary_path, headers=owner["headers"]).json()
    assert summary["reported_joined_participants"] == 1
    assert summary["reported_continuous_14_days"] == 0
    assert (
        client.post(
            path,
            headers=owner["headers"],
            json={
                "event": "UNKNOWN",
                "source": "OWNER_CONFIRMED",
                "note": "Not currently confirmed",
            },
        ).status_code
        == 201
    )
    assert (
        client.get(summary_path, headers=owner["headers"]).json()["reported_joined_participants"]
        == 0
    )
    assert (
        client.post(
            path,
            headers=tester["headers"],
            json={
                "event": "JOINED",
                "note": "Cannot backdate",
                "recorded_at": "2020-01-01T00:00:00Z",
            },
        ).status_code
        == 422
    )


def test_feature_disabled_by_default(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "cold_start_evidence_enabled", False)
    assert client.get("/apps/unknown/evidence-summary").status_code == 404


def test_assignment_status_and_export_do_not_confuse_daily_todo_with_enrollment(client, pilot):
    owner, tester, other, launch, assignment, mission = pilot
    status_path = f"/assignments/{assignment['id']}/evidence-status"
    assert (
        client.get(status_path, headers=tester["headers"]).json()["assignment_status"] == "ACTIVE"
    )
    assert client.get(status_path, headers=other["headers"]).status_code == 404
    body = run_body(mission, source="CODEX_ASSISTED")
    saved = client.post(f"/missions/{mission['id']}/runs", headers=owner["headers"], json=body)
    assert saved.status_code == 201
    report_path = f"/apps/{launch['id']}/evidence-report"
    assert client.get(report_path, headers=tester["headers"]).status_code == 404
    report = client.get(report_path, headers=owner["headers"]).json()
    assert report["runs"][0]["details"]["steps"] == body["steps"]
    assert report["runs"][0]["execution_source"] == "CODEX_ASSISTED"
    assert report["summary"]["manual_reported_participants"] == 0
    assert "submitted_by_id" not in report["runs"][0]
