"""Create labeled synthetic failure data in the isolated local evidence pilot only."""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.database import SessionLocal, sqlite_database_path
from app.core.security import create_access_token, create_refresh_token
from app.models.evidence import CampaignBuild
from app.models.launch import App, CircleMember, TesterAssignment
from app.models.user import User
from app.services.circles import ensure_owner_circle
from app.services.missions import generate_missions, mission_instructions
from scripts.submit_device_evidence import api


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-file", required=True, type=Path)
    args = parser.parse_args()
    settings = get_settings()
    path = sqlite_database_path(settings.database_url)
    if (
        settings.app_env != "development"
        or not settings.cold_start_evidence_enabled
        or path is None
        or not path.is_absolute()
        or not path.name.startswith("launch-circle-evidence-pilot-")
        or args.session_file.exists()
    ):
        parser.error(
            "Use an isolated development evidence-pilot database and new private session path"
        )
    from app.main import app as _app  # noqa: F401

    now = datetime.now(UTC)
    suffix = uuid4().hex[:8]
    with SessionLocal() as db:
        owner = User(
            email=f"ui-fixture-owner-{suffix}@example.com",
            display_name="SYNTHETIC UI FIXTURE OWNER",
        )
        tester = User(
            email=f"ui-fixture-tester-{suffix}@example.com",
            display_name="SYNTHETIC UI FIXTURE TESTER",
        )
        for user in (owner, tester):
            user.login_email = user.email
            user.tester_email = user.email
        db.add_all([owner, tester])
        db.flush()
        circle = ensure_owner_circle(db, owner)
        ensure_owner_circle(db, tester)
        db.add(CircleMember(circle_id=circle.id, user_id=tester.id, role="MEMBER", status="ACTIVE"))
        app = App(
            owner_id=owner.id,
            circle_id=circle.id,
            name="SYNTHETIC UI FIXTURE - NOT CUSTOMER TESTING",
            package_name="com.launchcircle.testers.evidencepilot",
            opt_in_url="https://play.google.com/apps/testing/com.launchcircle.testers",
            core_workflow_steps=["Exercise the labeled synthetic evidence UI fixture only."],
        )
        db.add(app)
        db.flush()
        assignment = TesterAssignment(
            app_id=app.id,
            tester_id=tester.id,
            circle_id=circle.id,
            assignment_day=now.date(),
            status="ACTIVE",
            opted_in_at=now,
            installed_at=now,
        )
        db.add(assignment)
        db.flush()
        mission = generate_missions(db, assignment, now)[0]
        db.add(
            CampaignBuild(app_id=app.id, version_code=10, recorded_by_id=owner.id, recorded_at=now)
        )
        db.commit()
        token = create_access_token(owner.id)
        state = {
            "app_id": app.id,
            "mission_id": mission.id,
            "assignment_id": assignment.id,
            "owner_session": {
                "access_token": token,
                "refresh_token": create_refresh_token(db, owner.id),
            },
        }
        _, steps = mission_instructions(mission.mission_type, app.name, app.core_workflow_steps)
    body = {
        "idempotency_key": "synthetic-ui-fixture-" + suffix,
        "execution_source": "AUTOMATED_RUNNER",
        "result": "FAIL",
        "package_name": "com.launchcircle.testers.evidencepilot",
        "version_code": 10,
        "expected_version_code": 10,
        "device_key": "synthetic-fixture-no-real-device",
        "device_model": "SYNTHETIC FIXTURE",
        "android_api": 36,
        "steps": [
            {
                "instruction": step,
                "expected": "Synthetic fixture validation only",
                "actual": "Pre-seeded synthetic failure, not an observed customer or device defect",
                "result": "FAIL",
            }
            for step in steps
        ],
        "note": "SYNTHETIC UI FIXTURE ONLY. Never count as a real bug, enrollment or customer campaign.",
    }
    result = api("http://127.0.0.1:8786", f"/missions/{state['mission_id']}/runs", token, body)
    state["failure_id"] = result["id"]
    args.session_file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(args.session_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(state, handle)
    print(json.dumps({key: value for key, value in state.items() if key != "owner_session"}))


if __name__ == "__main__":
    main()
