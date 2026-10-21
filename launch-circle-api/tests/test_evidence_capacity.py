from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.evidence import EnrollmentEvidence
from app.models.launch import App, TesterAssignment
from app.models.user import User
from tests.test_pilot import register


def test_twelve_people_three_apps_independent_clocks_and_daily_assignments(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "cold_start_evidence_enabled", True)
    owner = register(client, "capacity-owner@example.com", "Capacity Owner")
    now = datetime.now(UTC)
    old = now - timedelta(days=16)
    with SessionLocal() as db:
        users = [
            User(
                email=f"capacity-{i}@example.com",
                login_email=f"capacity-{i}@example.com",
                display_name=f"Synthetic {i}",
            )
            for i in range(12)
        ]
        apps = [
            App(
                owner_id=owner["id"],
                name=f"Internal app {i}",
                package_name=f"com.evidence.synthetic{i}",
                opt_in_url=f"https://play.google.com/apps/testing/com.evidence.synthetic{i}",
            )
            for i in range(3)
        ]
        db.add_all(users + apps)
        db.flush()
        app_ids = [app.id for app in apps]
        rows = []
        for app in apps:
            app_rows = []
            for user in users:
                assignment = TesterAssignment(
                    app_id=app.id,
                    tester_id=user.id,
                    status="ACTIVE",
                    opted_in_at=old,
                    installed_at=old,
                )
                db.add(assignment)
                db.flush()
                db.add(
                    EnrollmentEvidence(
                        assignment_id=assignment.id,
                        recorded_by_id=user.id,
                        event="JOINED",
                        source="SELF_REPORTED",
                        note="Synthetic capacity test",
                        recorded_at=old,
                    )
                )
                app_rows.append(assignment)
            rows.append(app_rows)
        # A daily assignment is not a new person or a fresh Play opt-in interval.
        duplicate = TesterAssignment(
            app_id=apps[0].id,
            tester_id=users[0].id,
            status="ACTIVE",
            opted_in_at=old,
            installed_at=old,
        )
        db.add(duplicate)
        db.flush()
        db.add(
            EnrollmentEvidence(
                assignment_id=duplicate.id,
                recorded_by_id=users[0].id,
                event="JOINED",
                source="SELF_REPORTED",
                note="Another daily assignment, same participant",
                recorded_at=now,
            )
        )
        db.commit()
        first_assignment_id = duplicate.id
    for app_id in app_ids:
        report = client.get(f"/apps/{app_id}/evidence-summary", headers=owner["headers"]).json()
        assert report["assigned_participants"] == 12
        assert report["reported_joined_participants"] == 12
        assert report["reported_continuous_14_days"] == 12
        assert report["estimated_eligibility_at"] is not None
        assert report["manual_reported_participants"] == 0
        assert report["google_eligibility_confirmed"] is False
    assert (
        client.post(
            f"/assignments/{first_assignment_id}/enrollment-evidence",
            headers=owner["headers"],
            json={"event": "LEFT", "source": "OWNER_CONFIRMED", "note": "Synthetic leave event"},
        ).status_code
        == 201
    )
    first_report = client.get(
        f"/apps/{app_ids[0]}/evidence-summary", headers=owner["headers"]
    ).json()
    assert first_report["reported_joined_participants"] == 11
    assert first_report["estimated_eligibility_at"] is None
    for app_id in app_ids[1:]:
        assert (
            client.get(f"/apps/{app_id}/evidence-summary", headers=owner["headers"]).json()[
                "reported_continuous_14_days"
            ]
            == 12
        )
