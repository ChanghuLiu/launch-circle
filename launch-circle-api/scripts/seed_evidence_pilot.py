"""Seed one explicitly synthetic campaign in a separate local-development database.

No Google enrollment, external customer identity, or real tester count is asserted.
The private session file is for the parallel debug app only; never commit it.
"""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal, sqlite_database_path
from app.core.security import create_access_token, create_refresh_token
from app.models.evidence import CampaignBuild
from app.models.launch import App, CircleMember, TesterAssignment
from app.models.user import User
from app.services.circles import ensure_owner_circle
from app.services.missions import generate_missions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-file", required=True, type=Path)
    parser.add_argument("--version-code", required=True, type=int)
    args = parser.parse_args()
    settings = get_settings()
    path = sqlite_database_path(settings.database_url)
    if (
        settings.app_env != "development"
        or not settings.cold_start_evidence_enabled
        or path is None
        or not path.is_absolute()
        or not path.name.startswith("launch-circle-evidence-pilot-")
        or args.version_code <= 0
    ):
        parser.error(
            "Use the isolated evidence-pilot development database with the pilot flag enabled"
        )
    if args.session_file.exists():
        parser.error("Session file exists; use a new private path")
    from app.main import app as _app  # noqa: F401

    now = datetime.now(UTC)
    with SessionLocal() as db:
        users = []
        for role in ("owner", "tester"):
            email = f"internal-evidence-{role}@example.com"
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    email=email,
                    login_email=email,
                    display_name=f"INTERNAL PILOT {role}",
                    tester_email=email,
                    country="CA",
                    languages_csv="en",
                    tester_email_sharing_consent=True,
                )
                db.add(user)
                db.flush()
            users.append(user)
        owner, tester = users
        circle = ensure_owner_circle(db, owner)
        ensure_owner_circle(db, tester)
        membership = db.scalar(
            select(CircleMember).where(
                CircleMember.circle_id == circle.id, CircleMember.user_id == tester.id
            )
        )
        if membership is None:
            db.add(
                CircleMember(circle_id=circle.id, user_id=tester.id, role="MEMBER", status="ACTIVE")
            )
        app = db.scalar(select(App).where(App.package_name == "com.notesescape.sdocx"))
        if app is None:
            app = App(
                owner_id=owner.id,
                circle_id=circle.id,
                name="Notes Escape - INTERNAL PILOT",
                package_name="com.notesescape.sdocx",
                opt_in_url="https://play.google.com/apps/testing/com.notesescape.sdocx",
                core_workflow_steps=[
                    "Open the file picker, cancel selection, and return to Notes Escape.",
                    "Confirm the app remains usable without selecting a file.",
                ],
            )
            db.add(app)
            db.flush()
        assignment = db.scalar(
            select(TesterAssignment).where(
                TesterAssignment.app_id == app.id, TesterAssignment.tester_id == tester.id
            )
        )
        if assignment is None:
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
        missions = generate_missions(db, assignment, now)
        build = db.get(CampaignBuild, app.id)
        if build is None:
            build = CampaignBuild(
                app_id=app.id,
                version_code=args.version_code,
                recorded_by_id=owner.id,
                recorded_at=now,
            )
            db.add(build)
        db.commit()
        owner_id, tester_id = owner.id, tester.id
        ids = {"app_id": app.id, "assignment_id": assignment.id, "mission_id": missions[0].id}
        tester_session = {
            "access_token": create_access_token(tester_id),
            "refresh_token": create_refresh_token(db, tester_id),
        }
        owner_session = {
            "access_token": create_access_token(owner_id),
            "refresh_token": create_refresh_token(db, owner_id),
        }
    args.session_file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(args.session_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump({**ids, "tester_session": tester_session, "owner_session": owner_session}, handle)
    print(
        json.dumps(
            {
                **ids,
                "internal_pilot_only": True,
                "google_enrollment_confirmed": False,
                "private_session_file": str(args.session_file),
            }
        )
    )


if __name__ == "__main__":
    main()
