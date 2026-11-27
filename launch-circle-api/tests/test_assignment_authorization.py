from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.launch import App, BackendEvent
from app.models.launch import TesterAssignment as Assignment
from app.models.pool import TesterPoolPreference as PoolPreference
from app.services.assignments import assignment_day
from app.services.matching import assign_replacements
from tests.test_owner_app_group_selection import make_group
from tests.test_shared_pool import actor, campaign, open_app, post


def today(client, user):
    response = client.get("/test-assignments/today", headers=user[1])
    assert response.status_code == 200, response.text
    return response.json()


def test_single_app_join_does_not_authorize_circle_sibling_and_is_idempotent(client):
    owner, selena = actor(), actor()
    usb = campaign(owner)
    esim = campaign(owner)
    open_app(client, usb, owner)
    stale_time = datetime.now(UTC)
    with SessionLocal() as db:
        stale_app = db.get(App, esim)
        stale = Assignment(
            app_id=esim,
            circle_id=stale_app.circle_id,
            tester_id=selena[0],
            assignment_day=assignment_day(stale_time),
            test_type="APP_CHECK",
            status="ASSIGNED",
            assigned_at=stale_time,
            health_status="NEW",
        )
        db.add(stale)
        db.commit()
        stale_id = stale.id

    joined_usb = post(client, f"/apps/{usb}/tester-pool/accept", selena)
    assert joined_usb.status_code == 200, joined_usb.text
    assert post(client, f"/apps/{usb}/tester-pool/accept", selena).json() == joined_usb.json()

    with SessionLocal() as db:
        pref = db.get(PoolPreference, selena[0])
        assert pref is None or not pref.enabled
        usb_event = db.scalar(
            select(BackendEvent).where(
                BackendEvent.assignment_id == joined_usb.json()["assignment_id"]
            )
        )
        assert usb_event is not None
        assert '"consent_scope": "APP"' in usb_event.payload_json
        # Even an independently enabled pool preference is not per-App consent.
        if pref is None:
            preference_time = datetime.now(UTC)
            pref = PoolPreference(
                user_id=selena[0],
                enabled=True,
                consent_at=preference_time,
                updated_at=preference_time,
            )
            db.add(pref)
        else:
            pref.enabled = True
        db.commit()

    for _ in range(3):
        tasks = today(client, selena)
        assert [task["app_id"] for task in tasks] == [usb]
        with SessionLocal() as db:
            assert db.scalar(
                select(func.count(Assignment.id)).where(
                    Assignment.app_id == esim,
                    Assignment.tester_id == selena[0],
                )
            ) == 1
            assert db.scalar(
                select(BackendEvent.id).where(BackendEvent.assignment_id == stale_id)
            ) is None

    open_app(client, esim, owner)
    joined_esim = post(client, f"/apps/{esim}/tester-pool/accept", selena)
    assert joined_esim.status_code == 200, joined_esim.text
    assert joined_esim.json()["assignment_id"] == stale_id
    replay = post(client, f"/apps/{esim}/tester-pool/accept", selena)
    assert replay.json() == joined_esim.json()
    assert {task["app_id"] for task in today(client, selena)} == {usb, esim}

    with SessionLocal() as db:
        assert db.scalar(
            select(func.count(Assignment.id)).where(
                Assignment.tester_id == selena[0],
                Assignment.app_id.in_([usb, esim]),
            )
        ) == 2


def test_group_consent_covers_group_apps_only_and_auto_routes_check_scope(client):
    first_owner, second_owner = actor(), actor()
    first_app = campaign(first_owner)
    group_app = campaign(second_owner)
    outside_app = campaign(second_owner)
    group_id = make_group("Daycare")
    open_app(client, first_app, first_owner)
    open_app(client, group_app, second_owner)
    joined = post(client, f"/apps/{first_app}/app-groups/{group_id}/join", first_owner, {"consent": True})
    assert joined.status_code == 200, joined.text
    second_join = post(client, f"/apps/{group_app}/app-groups/{group_id}/join", second_owner, {"consent": True})
    assert second_join.status_code == 200, second_join.text

    tasks = today(client, first_owner)
    assert [task["app_id"] for task in tasks] == [group_app]
    with SessionLocal() as db:
        group_task = db.scalar(
            select(Assignment).where(
                Assignment.app_id == group_app,
                Assignment.tester_id == first_owner[0],
            )
        )
        group_event = db.scalar(
            select(BackendEvent).where(BackendEvent.assignment_id == group_task.id)
        )
        assert group_event is not None
        assert '"consent_scope": "APP_GROUP"' in group_event.payload_json
        outside = db.get(App, outside_app)
        outside.status = "AT_RISK"
        outside.testing_start_at = datetime.now(UTC)
        db.flush()
        assert assign_replacements(db, outside, datetime.now(UTC)) == []
        assert db.scalar(
            select(func.count(Assignment.id)).where(
                Assignment.app_id == outside_app,
                Assignment.tester_id == first_owner[0],
            )
        ) == 0

    matched = post(client, f"/apps/{outside_app}/match-testers", second_owner)
    assert matched.status_code == 200, matched.text
    assert matched.json()["assigned_now"] == 0
    manual = post(client, f"/apps/{outside_app}/assign/{first_owner[0]}", second_owner)
    assert manual.status_code == 409
    assert {task["app_id"] for task in today(client, first_owner)} == {group_app}


def test_saving_app_does_not_assign_existing_circle_members(client):
    owner, tester = actor(), actor()
    package = "com.example.saved" + uuid4().hex[:12]
    response = client.post(
        "/apps",
        headers=owner[1],
        json={
            "icon_data": "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGPUjTrBwMDAxMDAwMDAAAAPQwFTH4I6DQAAAABJRU5ErkJggg==",
            "ownership_authorized": True,
            "name": "Saved App",
            "package_name": package,
            "opt_in_url": f"https://play.google.com/apps/testing/{package}",
            "play_developer_account_id": str(1000000000000000000 + uuid4().int % 1000000),
        },
    )
    assert response.status_code == 201, response.text
    app_id = response.json()["id"]
    with SessionLocal() as db:
        assert db.scalar(
            select(func.count(Assignment.id)).where(Assignment.app_id == app_id)
        ) == 0
    assert today(client, tester) == []
