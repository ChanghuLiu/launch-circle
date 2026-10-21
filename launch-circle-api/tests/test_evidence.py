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


def test_run_detail_scopes_original_observations_and_fix_context(client, pilot):
    owner, tester, other, launch, _, mission = pilot
    body = run_body(mission, result="FAIL")
    failed = client.post(
        f"/missions/{mission['id']}/runs", headers=tester["headers"], json=body
    ).json()
    path = f"/runs/{failed['id']}/detail"
    assert client.get(path, headers=other["headers"]).status_code == 404
    detail = client.get(path, headers=owner["headers"]).json()
    assert detail["run"]["details"]["steps"] == body["steps"]
    assert detail["can_submit_manual"] is False
    assert detail["retest_context"] is None
    assert client.get(path, headers=tester["headers"]).json()["can_submit_manual"] is True
    fix = {"target_version_code": 2, "description": "Synthetic fix declaration"}
    assert (
        client.post(f"/runs/{failed['id']}/fix", headers=owner["headers"], json=fix).status_code
        == 200
    )
    assert client.get(path, headers=owner["headers"]).json()["retest_context"] is None
    client.post(f"/apps/{launch['id']}/evidence/build", headers=owner["headers"], json=fix)
    detail = client.get(path, headers=owner["headers"]).json()
    assert detail["fix"] == fix
    assert detail["retest_context"]["steps"] == [s["instruction"] for s in body["steps"]]
    assert detail["retest_context"]["expected_version_code"] == 2


def test_partial_failure_retest_repeats_original_scope_without_claiming_full_mission(client, pilot):
    owner, tester, _, launch, _, mission = pilot
    body = run_body(mission, result="FAIL")
    body["steps"] = body["steps"][:1]
    failed = client.post(
        f"/missions/{mission['id']}/runs", headers=tester["headers"], json=body
    ).json()
    fix = {"target_version_code": 2, "description": "Synthetic partial failure fix"}
    client.post(f"/runs/{failed['id']}/fix", headers=owner["headers"], json=fix)
    client.post(f"/apps/{launch['id']}/evidence/build", headers=owner["headers"], json=fix)
    retest = run_body(mission, key="partial-retest", version=2)
    retest["retest_of_id"] = failed["id"]
    assert (
        client.post(
            f"/missions/{mission['id']}/runs", headers=tester["headers"], json=retest
        ).status_code
        == 409
    )
    retest["steps"] = retest["steps"][:1]
    saved = client.post(f"/missions/{mission['id']}/runs", headers=tester["headers"], json=retest)
    assert saved.status_code == 201, saved.text
    assert len(saved.json()["details"]["steps"]) == 1
    summary = client.get(f"/apps/{launch['id']}/evidence-summary", headers=owner["headers"]).json()
    assert summary["issues"][0]["state"] == "VERIFIED_FIXED"
    assert summary["internal_readiness"] == "REVIEW_REQUIRED"


def test_valid_linked_retest_survives_original_missed_window_without_rewriting_history(
    client, pilot
):
    from app.models.launch import TestMission as Mission

    owner, tester, _, launch, _, mission = pilot
    body = run_body(mission, result="FAIL")
    failure = client.post(
        f"/missions/{mission['id']}/runs", headers=tester["headers"], json=body
    ).json()
    fix = {"target_version_code": 2, "description": "Synthetic delayed fix"}
    client.post(f"/runs/{failure['id']}/fix", headers=owner["headers"], json=fix)
    client.post(f"/apps/{launch['id']}/evidence/build", headers=owner["headers"], json=fix)
    with SessionLocal() as db:
        db.get(Mission, mission["id"]).status = "MISSED"
        db.commit()
    retry = run_body(mission, key="after-window", version=2)
    path = f"/missions/{mission['id']}/runs"
    assert client.post(path, headers=tester["headers"], json=retry).status_code == 409
    retry["retest_of_id"] = failure["id"]
    saved = client.post(path, headers=tester["headers"], json=retry)
    assert saved.status_code == 201, saved.text
    with SessionLocal() as db:
        assert db.get(Mission, mission["id"]).status == "MISSED"


@pytest.mark.parametrize("deleted_role", ["owner", "tester"])
def test_account_deletion_cascades_evidence_without_touching_other_campaign(
    client, pilot, deleted_role
):
    from app.models.evidence import CampaignBuild, MissionRun, MissionRunFix
    from app.models.launch import App
    from app.models.launch import TesterAssignment as Assignment
    from app.models.launch import TestMission as Mission

    owner, tester, other, launch, assignment, mission = pilot
    enrollment = client.post(
        f"/assignments/{assignment['id']}/enrollment-evidence",
        headers=tester["headers"],
        json={"event": "JOINED", "note": "Synthetic deletion test"},
    ).json()
    failure = client.post(
        f"/missions/{mission['id']}/runs",
        headers=tester["headers"],
        json=run_body(mission, result="FAIL"),
    ).json()
    fix = {"target_version_code": 2, "description": "Synthetic deletion test fix"}
    client.post(f"/runs/{failure['id']}/fix", headers=owner["headers"], json=fix)
    client.post(f"/apps/{launch['id']}/evidence/build", headers=owner["headers"], json=fix)
    retest_body = run_body(mission, key="deletion-retest", version=2, source="CODEX_ASSISTED")
    retest_body["retest_of_id"] = failure["id"]
    retest = client.post(
        f"/missions/{mission['id']}/runs", headers=owner["headers"], json=retest_body
    )
    assert retest.status_code == 201, retest.text
    with SessionLocal() as db:
        unrelated_app = App(
            owner_id=other["id"],
            name="Unrelated synthetic app",
            package_name="com.example.unrelated.deletion",
            opt_in_url="https://example.com/test",
        )
        db.add(unrelated_app)
        db.flush()
        unrelated_assignment = Assignment(app_id=unrelated_app.id, tester_id=other["id"])
        db.add(unrelated_assignment)
        db.flush()
        unrelated_mission = Mission(
            assignment_id=unrelated_assignment.id, mission_type="DAY_1_SMOKE", scheduled_day=1
        )
        db.add(unrelated_mission)
        db.flush()
        unrelated_run = MissionRun(
            mission_id=unrelated_mission.id,
            submitted_by_id=other["id"],
            idempotency_key="unrelated-test-run",
            payload_hash="0" * 64,
            execution_source="AUTOMATED_RUNNER",
            result="FAIL",
            package_name=unrelated_app.package_name,
            version_code=5,
            device_key="unrelated-synthetic-device",
            device_model="Synthetic",
            android_api=27,
            details={"steps": [], "note": "Synthetic deletion isolation test"},
        )
        unrelated_enrollment = EnrollmentEvidence(
            assignment_id=unrelated_assignment.id,
            recorded_by_id=other["id"],
            event="JOINED",
            source="SELF_REPORTED",
            note="Synthetic",
        )
        unrelated_build = CampaignBuild(
            app_id=unrelated_app.id, version_code=5, recorded_by_id=other["id"]
        )
        db.add_all([unrelated_run, unrelated_enrollment, unrelated_build])
        db.flush()
        unrelated_fix = MissionRunFix(
            run_id=unrelated_run.id,
            recorded_by_id=other["id"],
            target_version_code=6,
            description="Unrelated synthetic fix",
        )
        db.add(unrelated_fix)
        db.commit()
        keep = (unrelated_app.id, unrelated_run.id, unrelated_enrollment.id, unrelated_fix.id)
    deleted = owner if deleted_role == "owner" else tester
    response = client.delete("/v1/me", headers=deleted["headers"])
    assert response.status_code == 200, response.text
    assert client.get("/v1/me", headers=deleted["headers"]).status_code == 401
    with SessionLocal() as db:
        assert (
            db.scalar(select(EnrollmentEvidence).where(EnrollmentEvidence.id == enrollment["id"]))
            is None
        )
        assert db.scalar(select(MissionRun).where(MissionRun.id == failure["id"])) is None
        assert db.scalar(select(MissionRun).where(MissionRun.id == retest.json()["id"])) is None
        assert db.scalar(select(MissionRunFix).where(MissionRunFix.run_id == failure["id"])) is None
        assert (db.get(CampaignBuild, launch["id"]) is None) == (deleted_role == "owner")
        assert db.get(App, keep[0]) is not None
        assert db.get(CampaignBuild, keep[0]) is not None
        assert db.scalar(select(MissionRun).where(MissionRun.id == keep[1])) is not None
        assert (
            db.scalar(select(EnrollmentEvidence).where(EnrollmentEvidence.id == keep[2]))
            is not None
        )
        assert db.get(MissionRunFix, keep[3]) is not None
