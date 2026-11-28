from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import pytest
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.admin import AdminAppControl
from app.models.launch import App, TesterAssignment
from app.models.pool import AppGroup, AppGroupApp, AppGroupMember, PoolListing
from app.models.user import User
from tests.test_shared_pool import actor, campaign, post


def make_group(name: str, status: str = "OPEN") -> str:
    from uuid import uuid4

    with SessionLocal() as db:
        group = AppGroup(id=str(uuid4()), name=name, status=status, created_at=datetime.now(UTC))
        db.add(group)
        db.commit()
        return group.id


def select_group(client, app_id: str, group_id: str, owner, consent: bool = True):
    return post(client, f"/apps/{app_id}/app-groups/{group_id}/join", owner, {"consent": consent})


def test_owner_can_choose_daycare_or_usb_without_category_filter(client):
    owner = actor()
    app_id = campaign(owner)
    daycare, usb = make_group("Daycare"), make_group("USB")

    options = client.get(f"/apps/{app_id}/app-groups", headers=owner[1])
    assert options.status_code == 200
    rows = {row["name"]: row for row in options.json()["groups"]}
    assert set(rows) == {"Daycare", "USB"}
    assert rows["Daycare"]["remaining_app_slots"] == 15
    assert rows["USB"]["member_count"] == 0

    response = select_group(client, app_id, daycare, owner)
    assert response.status_code == 200, response.text
    assert response.json()["active_app_testers"] == 0
    assert response.json()["new_app_tasks"] == 0
    with SessionLocal() as db:
        assert db.get(AppGroupApp, app_id).group_id == daycare
        assert db.get(AppGroupMember, (daycare, owner[0])) is not None
        assert db.get(AppGroupApp, app_id).group_id != usb
        assert db.get(PoolListing, app_id).enabled
        assert db.scalar(select(func.count(TesterAssignment.id))) == 0


@pytest.mark.parametrize("selected_name", ["Daycare", "USB"])
def test_josh_chooses_group_and_sees_real_counts_and_progress(client, selected_name):
    josh = actor()
    with SessionLocal() as db:
        db.get(User, josh[0]).display_name = "Josh Rogers"
        db.commit()
    app_id = campaign(josh)
    with SessionLocal() as db:
        app = db.get(App, app_id)
        app.name = "Pegs and Jokers"
        app.package_name = "net.joshrogers.pegsandjokers"
        app.opt_in_url = "https://play.google.com/apps/testing/net.joshrogers.pegsandjokers"
        db.commit()

    daycare_id, usb_id = make_group("Daycare"), make_group("USB")
    for index in range(12):
        owner = actor()
        peer_app = campaign(owner)
        with SessionLocal() as db:
            db.get(App, peer_app).no_test_required = True
            db.add(AppGroupApp(app_id=peer_app, group_id=daycare_id))
            db.add(PoolListing(app_id=peer_app, enabled=True, updated_at=datetime.now(UTC)))
            db.commit()
    usb_owner = actor()
    usb_app = campaign(usb_owner)
    with SessionLocal() as db:
        db.add(AppGroupApp(app_id=usb_app, group_id=usb_id))
        db.add(PoolListing(app_id=usb_app, enabled=True, updated_at=datetime.now(UTC)))
        db.commit()

    daycare_members = [actor() for _ in range(2)]
    usb_members = [actor()]
    with SessionLocal() as db:
        db.add_all([
            AppGroupMember(group_id=daycare_id, user_id=member[0], joined_at=datetime.now(UTC))
            for member in daycare_members
        ] + [
            AppGroupMember(group_id=usb_id, user_id=member[0], joined_at=datetime.now(UTC))
            for member in usb_members
        ])
        db.commit()

    options = client.get(f"/apps/{app_id}/app-groups", headers=josh[1])
    assert options.status_code == 200, options.text
    data = options.json()
    rows = {row["name"]: row for row in data["groups"]}
    assert rows["Daycare"]["remaining_app_slots"] == 3
    assert rows["Daycare"]["test_required_app_count"] == 0
    assert rows["Daycare"]["exempt_app_count"] == 12
    assert rows["Daycare"]["member_count"] == 2
    assert rows["USB"]["remaining_app_slots"] == 14
    assert rows["USB"]["test_required_app_count"] == 1
    assert rows["USB"]["exempt_app_count"] == 0
    assert rows["USB"]["member_count"] == 1
    assert data["app_progress"]["qualified_tester_count"] == 0
    assert data["app_progress"]["testing_started_at"] is None
    assert data["app_progress"]["day"] == 0
    assert data["app_progress"]["no_test_required"] is False

    selected_id = daycare_id if selected_name == "Daycare" else usb_id
    response = select_group(client, app_id, selected_id, josh)
    assert response.status_code == 200, response.text
    assert response.json()["group_id"] == selected_id
    assert response.json()["qualified_tester_count"] == 0
    assert response.json()["testing_started_at"] is None
    assert response.json()["day"] == 0

    with SessionLocal() as db:
        assert db.get(AppGroupApp, app_id).group_id == selected_id
        assert db.get(AppGroupMember, (selected_id, josh[0])) is not None
        other_id = usb_id if selected_id == daycare_id else daycare_id
        assert db.get(AppGroupMember, (other_id, josh[0])) is None
        app = db.get(App, app_id)
        assert app.testing_start_at is None
        assert app.status == "WAITING_FOR_TESTERS"
        assert not any(
            row.app_id == app_id and row.tester_id == josh[0]
            for row in db.scalars(select(TesterAssignment)).all()
        )

    home = client.get("/app-groups", headers=josh[1])
    assert home.status_code == 200, home.text
    selected = next(row for row in home.json() if row["id"] == selected_id)
    assert selected["test_required_app_count"] == (1 if selected_name == "Daycare" else 2)
    assert selected["member_count"] == (3 if selected_name == "Daycare" else 2)
    if selected_name == "Daycare":
        assert len([app for app in selected["apps"] if app["no_test_required"]]) == 12
        assert any(app["app_id"] == app_id and app["no_test_required"] is False for app in selected["apps"])


def test_filling_fifteenth_app_slot_does_not_start_testing_clock(client):
    owner = actor()
    app_id = campaign(owner)
    group_id = make_group("Daycare")
    for _ in range(14):
        peer_owner = actor()
        peer_app = campaign(peer_owner)
        with SessionLocal() as db:
            db.get(App, peer_app).no_test_required = True
            db.add(AppGroupApp(app_id=peer_app, group_id=group_id))
            db.commit()

    before = client.get(f"/apps/{app_id}/app-groups", headers=owner[1]).json()
    assert before["groups"][0]["remaining_app_slots"] == 1
    response = select_group(client, app_id, group_id, owner)
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        assert db.scalar(select(func.count(AppGroupApp.app_id)).where(AppGroupApp.group_id == group_id)) == 15
        app = db.get(App, app_id)
        assert app.testing_start_at is None
        assert app.status == "WAITING_FOR_TESTERS"


def test_legacy_mapped_app_without_owner_consent_can_finish_group_join(client):
    owner = actor()
    app_id = campaign(owner)
    group_id = make_group("Daycare")
    with SessionLocal() as db:
        db.add(AppGroupApp(app_id=app_id, group_id=group_id))
        db.commit()

    options = client.get(f"/apps/{app_id}/app-groups", headers=owner[1])
    assert options.status_code == 200, options.text
    group = options.json()["groups"][0]
    assert group["already_selected"] is True
    assert group["owner_joined"] is False
    assert group["can_select"] is True

    response = select_group(client, app_id, group_id, owner)
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        assert db.get(AppGroupApp, app_id).group_id == group_id
        assert db.get(AppGroupMember, (group_id, owner[0])) is not None
        assert db.get(App, app_id).testing_start_at is None


def test_owner_can_select_usb_group_and_duplicate_submit_is_idempotent(client):
    peer, owner = actor(), actor()
    daycare_id, group_id = make_group("Daycare"), make_group("USB")
    peer_app, owner_app = campaign(peer), campaign(owner)
    with SessionLocal() as db:
        db.add_all(
            [
                AppGroupApp(app_id=peer_app, group_id=group_id),
                AppGroupMember(group_id=group_id, user_id=peer[0], joined_at=datetime.now(UTC)),
                PoolListing(app_id=peer_app, enabled=True, updated_at=datetime.now(UTC)),
            ]
        )
        db.add(AdminAppControl(app_id=peer_app, kind="CUSTOMER"))
        db.get(User, owner[0]).display_name = "Josh Rogers"
        db.commit()

    options = client.get(f"/apps/{owner_app}/app-groups", headers=owner[1])
    assert options.status_code == 200
    offered = {row["id"]: row for row in options.json()["groups"]}
    assert set(offered) == {daycare_id, group_id}
    assert offered[group_id]["can_select"] is True
    assert offered[group_id]["member_count"] == 1

    first = select_group(client, owner_app, group_id, owner)
    assert first.status_code == 200, first.text
    assert first.json()["active_app_testers"] == 1
    with SessionLocal() as db:
        assert db.get(AppGroupApp, owner_app).group_id == group_id
        assert db.get(AppGroupMember, (group_id, owner[0])) is not None
        rows = db.scalars(select(TesterAssignment)).all()
        assert len(rows) == 2
        assert {(row.app_id, row.tester_id) for row in rows} == {
            (owner_app, peer[0]),
            (peer_app, owner[0]),
        }
        assert all(row.app_id != owner_app or row.tester_id != owner[0] for row in rows)
        assert all(row.opted_in_at is None and row.installed_at is None for row in rows)

    replay = select_group(client, owner_app, group_id, owner)
    assert replay.status_code == 200 and replay.json()["already_joined"] is True
    assert replay.json()["qualified_tester_count"] == 0
    assert replay.json()["testing_started_at"] is None
    assert replay.json()["day"] == 0
    with SessionLocal() as db:
        assert db.scalar(select(func.count(TesterAssignment.id))) == 2
        assert db.get(App, owner_app).testing_start_at is None


def test_missing_consent_does_not_add_app_member_or_tasks(client):
    owner = actor()
    app_id, group_id = campaign(owner), make_group("Daycare")
    response = select_group(client, app_id, group_id, owner, consent=False)
    assert response.status_code == 422
    with SessionLocal() as db:
        assert db.get(AppGroupApp, app_id) is None
        assert db.get(AppGroupMember, (group_id, owner[0])) is None
        assert db.get(PoolListing, app_id) is None
        assert db.scalar(select(func.count(TesterAssignment.id))) == 0
        assert db.get(App, app_id).testing_start_at is None


def test_full_and_closed_groups_are_rejected_without_partial_writes(client):
    candidate = actor()
    app_id = campaign(candidate)
    full_id = make_group("Daycare")
    closed_id = make_group("USB", status="CLOSED")
    members = [actor() for _ in range(15)]
    with SessionLocal() as db:
        for member in members:
            package = "com.capacity." + member[0].replace("-", "")
            existing = App(
                owner_id=member[0],
                name="Existing",
                package_name=package,
                opt_in_url=f"https://play.google.com/apps/testing/{package}",
                icon_url="https://example.invalid/icon.png",
                google_group_configured=True,
                core_workflow_steps=["Open app"],
            )
            db.add(existing)
            db.flush()
            db.add(AppGroupApp(app_id=existing.id, group_id=full_id))
        db.commit()

    for group_id, expected in ((full_id, "APP_GROUP_FULL"), (closed_id, "APP_GROUP_CLOSED")):
        response = select_group(client, app_id, group_id, candidate)
        assert response.status_code == 409
        assert response.json()["detail"] == expected
    with SessionLocal() as db:
        assert db.get(AppGroupApp, app_id) is None
        assert db.get(AppGroupMember, (full_id, candidate[0])) is None
        assert db.get(AppGroupMember, (closed_id, candidate[0])) is None
        assert db.scalar(select(func.count(TesterAssignment.id))) == 0
        assert db.get(App, app_id).testing_start_at is None


def test_two_owners_racing_for_last_slot_yields_exactly_one_winner(client):
    group_id = make_group("USB")
    members = [actor() for _ in range(14)]
    with SessionLocal() as db:
        for member in members:
            package = "com.race.existing." + member[0].replace("-", "")
            existing = App(
                owner_id=member[0],
                name="Existing",
                package_name=package,
                opt_in_url=f"https://play.google.com/apps/testing/{package}",
                icon_url="https://example.invalid/icon.png",
                google_group_configured=True,
                core_workflow_steps=["Open app"],
            )
            db.add(existing)
            db.flush()
            db.add(AppGroupApp(app_id=existing.id, group_id=group_id))
        db.commit()
    owners = [actor(), actor()]
    app_ids = [campaign(owner) for owner in owners]
    barrier = Barrier(2)

    def submit(index):
        barrier.wait()
        return select_group(client, app_ids[index], group_id, owners[index])

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, range(2)))
    assert sorted(response.status_code for response in responses) == [200, 409]
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count(AppGroupApp.app_id)).where(AppGroupApp.group_id == group_id)
            )
            == 15
        )
        winners = [app_id for app_id in app_ids if db.get(AppGroupApp, app_id) is not None]
        assert len(winners) == 1
        assert (
            sum(db.get(AppGroupMember, (group_id, owner[0])) is not None for owner in owners) == 1
        )


def test_admin_recruitment_open_does_not_auto_assign_or_create_group(client):
    from app.api.admin import RecruitmentUpdate, recruitment

    owner = actor()
    app_id = campaign(owner)
    with SessionLocal() as db:
        before = db.scalar(select(func.count(AppGroup.id)))
        assert recruitment(
            app_id, RecruitmentUpdate(enabled=True, reason="Approve recruitment for test"), db, True
        )["ok"]
        assert db.get(AppGroupApp, app_id) is None
        assert db.scalar(select(func.count(AppGroup.id))) == before
